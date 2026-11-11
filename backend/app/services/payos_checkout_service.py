from datetime import UTC, datetime, timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.exceptions import AppError, ResourceNotFoundError
from app.models.enums import PaymentStatus
from app.models.user import User
from app.repositories.billing_repository import PaymentRepository
from app.repositories.membership_repository import MembershipPlanRepository
from app.schemas.payment_schema import PayOSCreateRequest, PayOSCreateResponse
from app.services.membership_service import MembershipService
from app.services.payos_service import require_payos_client


STAFF_QR_KEY_PREFIX = "staff-qr:"


class PayOSCheckoutService:
    """Creates pending payOS membership checkouts (self-service, or staff on behalf of a member)."""

    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.payments = PaymentRepository(session)
        self.plans = MembershipPlanRepository(session)
        self.memberships = MembershipService(session, self.settings)

    async def create_payment(
        self,
        *,
        user: User,
        payload: PayOSCreateRequest,
        actor: User | None = None,
        idempotency_key: str | None = None,
        commit: bool = True,
    ) -> PayOSCreateResponse:
        """Create a pending payOS checkout. With `actor`, staff create it on behalf of `user` at the actor's gym.

        With `commit=False` the caller owns the transaction (e.g. to add an audit row before one commit).
        """
        client = require_payos_client(self.settings)
        stored_key = f"{STAFF_QR_KEY_PREFIX}{idempotency_key}" if actor and idempotency_key else None
        if stored_key:
            existing = await self.payments.get_by_idempotency_key(user_id=user.id, idempotency_key=stored_key)
            if existing:
                if existing.plan_id != payload.membership_plan_id:
                    raise AppError(
                        "IDEMPOTENCY_KEY_REUSED",
                        "Use a new payment key when changing the membership plan.",
                        409,
                    )
                return PayOSCreateResponse(
                    transaction_id=existing.id,
                    order_code=existing.payos_order_code,
                    checkout_url=existing.checkout_url,
                    amount_vnd=existing.amount_vnd,
                    expires_at=existing.expires_at,
                    gym_id=existing.gym_id,
                    gym_name=existing.gym.name,
                )
        await self.memberships.validate_self_service_eligibility(user)
        plan = await self.plans.get_by_id(payload.membership_plan_id)
        if not plan or not plan.is_active:
            raise ResourceNotFoundError("Membership plan was not found.")
        gym = await self.memberships.resolve_purchase_gym(
            user=user,
            requested_gym_id=payload.gym_id,
            actor=actor,
        )
        current_membership = await self.memberships.memberships.get_current_for_user(user.id)
        quote = await self.memberships.attendance_benefit_quote(
            user=user,
            plan=plan,
            current_membership=current_membership,
            gym=gym,
        )
        if quote.status == "pending":
            raise AppError(
                "ATTENDANCE_BENEFIT_PENDING",
                "A discounted renewal checkout is already pending. Complete it or wait for it to expire.",
                409,
            )
        discount_amount = quote.pricing.discount_amount
        final_amount = quote.pricing.final_amount
        integral_amount = final_amount.to_integral_value()
        if final_amount != integral_amount or integral_amount <= 0:
            raise AppError("INVALID_PLAN_PRICE", "The selected plan has an invalid VND price.", 409)
        now = datetime.now(UTC)
        order_code = await self.payments.next_payos_order_code()
        try:
            payment = await self.payments.create(
                gym_id=gym.id,
                user_id=user.id,
                membership_id=current_membership.id if quote.pricing.transaction_kind == "renewal" else None,
                plan_id=plan.id,
                product_type="membership",
                idempotency_key=stored_key or f"payos:{order_code}",
                amount=final_amount,
                amount_vnd=int(integral_amount),
                discount_amount=discount_amount,
                status=PaymentStatus.PENDING.value,
                mock_reference=str(order_code),
                provider="payos",
                txn_ref=str(order_code),
                payos_order_code=order_code,
                expires_at=now + timedelta(minutes=self.settings.PAYOS_TRANSACTION_TTL_MINUTES),
                client_platform=payload.client_platform,
                attendance_benefit_period_start=quote.period_start if quote.available else None,
                discount_details=quote.model_dump(mode="json"),
            )
        except IntegrityError as exc:
            await self.session.rollback()
            if quote.available:
                raise AppError(
                    "ATTENDANCE_BENEFIT_ALREADY_USED",
                    "This attendance benefit is already reserved or consumed.",
                    409,
                ) from exc
            raise
        qr_code = await client.attach_payment_link(payment)
        if commit:
            await self._commit_payment()
        return PayOSCreateResponse(
            transaction_id=payment.id,
            order_code=payment.payos_order_code,
            checkout_url=payment.checkout_url,
            amount_vnd=payment.amount_vnd,
            expires_at=payment.expires_at,
            gym_id=gym.id,
            gym_name=gym.name,
            qr_code=qr_code,
        )

    async def _commit_payment(self) -> None:
        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise AppError("PAYMENT_REFERENCE_CONFLICT", "Please start the payment again.", 409) from exc
