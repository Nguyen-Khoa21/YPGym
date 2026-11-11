from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.exceptions import AppError
from app.models.enums import PaymentStatus
from app.models.user import User
from app.repositories.audit_repository import AuditRepository
from app.repositories.billing_repository import PaymentRepository
from app.services.class_payment_service import ClassPaymentService
from app.services.membership_service import MembershipService
from app.services.payos_service import require_payos_client
from app.services.state_transitions import transition_payment


class PayOSWebhookService:
    """Verifies payOS webhooks and settles the matching membership or class payment exactly once."""

    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.payments = PaymentRepository(session)
        self.audit = AuditRepository(session)
        self.memberships = MembershipService(session, self.settings)
        self.class_payments = ClassPaymentService(session, self.settings)

    async def process_webhook(self, payload: bytes) -> dict[str, str]:
        data = await require_payos_client(self.settings).verify_webhook(payload)
        payment = await self.payments.get_by_payos_order_code(data.order_code, for_update=True)
        if not payment:
            return {"code": "00", "desc": "success"}
        if data.amount != payment.amount_vnd or data.currency != "VND":
            raise AppError("PAYOS_AMOUNT_MISMATCH", "The verified payment amount does not match the order.", 400)
        if payment.payment_link_id and data.payment_link_id != payment.payment_link_id:
            raise AppError("PAYOS_LINK_MISMATCH", "The verified payment link does not match the order.", 400)
        if data.code != "00":
            return {"code": "00", "desc": "success"}
        late_class_success = (
            payment.product_type == "class_booking"
            and payment.status in {
                PaymentStatus.EXPIRED.value,
                PaymentStatus.CANCELLED.value,
                PaymentStatus.FAILED.value,
            }
        )
        if payment.status in {PaymentStatus.PAID.value, PaymentStatus.PAID_REVIEW.value}:
            return {"code": "00", "desc": "success"}
        if payment.status != PaymentStatus.PENDING.value and not late_class_success:
            payment.provider_transaction_no = data.reference
            payment.paid_at = datetime.now(UTC)
            transition_payment(payment, PaymentStatus.PAID_REVIEW)
            await self.audit.create(
                target_user_id=payment.user_id,
                action="payment.payos.late_success",
                entity_type="payment",
                entity_id=str(payment.id),
                outcome="paid_review",
                summary="payOS reported payment after the local attempt reached a final state.",
                after_data={"provider": "payos", "product_type": payment.product_type},
            )
            await self.session.commit()
            return {"code": "00", "desc": "success"}

        payment.response_code = data.code
        payment.transaction_status = "PAID"
        payment.provider_transaction_no = data.reference
        payment.payment_link_id = data.payment_link_id
        try:
            payment.pay_date = datetime.strptime(data.transaction_date_time, "%Y-%m-%d %H:%M:%S").replace(
                tzinfo=ZoneInfo("Asia/Ho_Chi_Minh")
            )
        except ValueError:
            payment.pay_date = None
        now = datetime.now(UTC)
        user = (
            await self.session.execute(select(User).where(User.id == payment.user_id).with_for_update())
        ).scalar_one()
        payment.paid_at = payment.pay_date or now
        if payment.product_type == "membership" and payment.plan_id and not payment.class_booking_id:
            if not payment.gym.is_active:
                transition_payment(payment, PaymentStatus.PAID_REVIEW)
                await self.audit.create(
                    target_user_id=payment.user_id,
                    action="payment.payos.membership_resolution_required",
                    entity_type="payment",
                    entity_id=str(payment.id),
                    outcome="paid_review",
                    summary="The selected gym became inactive before membership payment settlement.",
                    after_data={"gym_id": str(payment.gym_id)},
                )
                await self.session.commit()
                return {"code": "00", "desc": "success"}
            transition_payment(payment, PaymentStatus.PAID)
            await self.memberships.finalize_provider_payment(
                user=user, plan=payment.plan, payment=payment, transaction_date=payment.paid_at
            )
        elif payment.product_type == "class_booking" and payment.class_booking_id and not payment.plan_id:
            await self.class_payments.finalize(payment=payment, user=user, now=now)
        else:
            raise AppError("PAYMENT_PRODUCT_INVALID", "The payment product mapping is invalid.", 409)
        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise AppError("PAYOS_REFERENCE_CONFLICT", "The payment reference was already processed.", 409) from exc
        return {"code": "00", "desc": "success"}
