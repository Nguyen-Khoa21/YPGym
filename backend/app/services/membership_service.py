from calendar import monthrange
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal, ROUND_HALF_UP
from uuid import uuid4
from zoneinfo import ZoneInfo

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError, ResourceNotFoundError
from app.core.config import Settings, get_settings
from app.models.enums import MembershipStatus, PaymentStatus
from app.models.user import User
from app.repositories.billing_repository import InvoiceRepository, PaymentRepository
from app.repositories.attendance_repository import AttendanceRepository
from app.repositories.email_delivery_repository import EmailDeliveryRepository
from app.repositories.membership_repository import (
    MembershipPlanRepository,
    UserMembershipRepository,
)
from app.repositories.operations_repository import AuditRepository, NotificationRepository
from app.schemas.membership_schema import (
    AttendanceBenefitQuote,
    InvoiceSummary,
    MembershipDiscountPricing,
    MembershipSummary,
    PaymentSummary,
    PurchaseMembershipRequest,
    PurchaseMembershipResponse,
)
from app.services.invoice_service import InvoicePdfService


class MembershipService:
    ATTENDANCE_THRESHOLD_PERCENT = Decimal("80.00")
    ATTENDANCE_BENEFIT_PERCENT = Decimal("10.00")

    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.plans = MembershipPlanRepository(session)
        self.memberships = UserMembershipRepository(session)
        self.payments = PaymentRepository(session)
        self.attendance = AttendanceRepository(session)
        self.invoices = InvoiceRepository(session)
        self.invoice_pdf = InvoicePdfService()
        self.email_deliveries = EmailDeliveryRepository(session)
        self.notifications = NotificationRepository(session)

    @staticmethod
    def previous_complete_month(local_today: date) -> tuple[date, date, date]:
        period_end = local_today.replace(day=1) - timedelta(days=1)
        period_start = period_end.replace(day=1)
        next_month = period_end + timedelta(days=1)
        return period_start, period_end, next_month

    async def attendance_benefit_quote(
        self,
        *,
        user: User,
        plan,
        current_membership=None,
        now: datetime | None = None,
    ) -> AttendanceBenefitQuote:
        now = now or datetime.now(UTC)
        timezone = ZoneInfo(self.settings.GYM_TIMEZONE)
        local_today = now.astimezone(timezone).date()
        period_start, period_end, next_month = self.previous_complete_month(local_today)
        period_start_utc = datetime.combine(period_start, time.min, timezone).astimezone(UTC)
        next_month_utc = datetime.combine(next_month, time.min, timezone).astimezone(UTC)
        attended_days = await self.attendance.count_distinct_qr_visit_days(
            user_id=user.id,
            gym_timezone=self.settings.GYM_TIMEZONE,
            date_from=period_start_utc,
            date_to=next_month_utc,
        )
        period_days = monthrange(period_start.year, period_start.month)[1]
        attendance_percentage = (
            Decimal(attended_days) * Decimal("100") / Decimal(period_days)
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        attendance_qualified = attendance_percentage >= self.ATTENDANCE_THRESHOLD_PERCENT
        if current_membership is None:
            current_membership = await self.memberships.get_current_for_user(user.id)
        is_renewal = bool(current_membership and current_membership.expiry_date >= local_today)
        usage = await self.payments.get_active_attendance_benefit_payment(
            user_id=user.id,
            period_start=period_start,
        )
        if not attendance_qualified:
            status = "not_qualified"
        elif not is_renewal:
            status = "not_renewal"
        elif usage and usage.status == PaymentStatus.PENDING.value:
            status = "pending"
        elif usage:
            status = "consumed"
        else:
            status = "eligible"
        available = status == "eligible"
        attendance_discount = self.ATTENDANCE_BENEFIT_PERCENT if available else Decimal("0.00")
        applied_discount = max(Decimal(plan.discount_percent), attendance_discount)
        discount_amount, final_amount = self.calculate_amounts(plan.base_price, applied_discount)
        return AttendanceBenefitQuote(
            gym_timezone=self.settings.GYM_TIMEZONE,
            period_start=period_start,
            period_end=period_end,
            attended_days=attended_days,
            period_days=period_days,
            attendance_percentage=attendance_percentage,
            attendance_qualified=attendance_qualified,
            available=available,
            status=status,
            pricing=MembershipDiscountPricing(
                transaction_kind="renewal" if is_renewal else "purchase",
                base_price=plan.base_price,
                plan_discount_percent=plan.discount_percent,
                attendance_discount_percent=attendance_discount,
                applied_discount_percent=applied_discount,
                attendance_benefit_selected=(
                    available and self.ATTENDANCE_BENEFIT_PERCENT >= Decimal(plan.discount_percent)
                ),
                discount_amount=discount_amount,
                final_amount=final_amount,
            ),
        )

    async def validate_self_service_eligibility(self, user: User, *, for_update: bool = False) -> None:
        if not user.is_email_verified:
            raise AppError(
                "EMAIL_NOT_VERIFIED",
                "Please verify your email before purchasing a membership.",
                403,
            )
        latest = (
            await self.memberships.get_latest_for_user_for_update(user.id)
            if for_update
            else await self.memberships.get_latest_for_user(user.id)
        )
        if latest and latest.status == MembershipStatus.REVOKED.value:
            raise AppError(
                "MEMBERSHIP_REVOKED",
                "A revoked membership cannot be renewed through self-service.",
                403,
            )

    async def purchase(
        self,
        *,
        current_user: User,
        payload: PurchaseMembershipRequest,
        actor: User | None = None,
        manual_reason: str | None = None,
    ) -> PurchaseMembershipResponse:
        operator = actor or current_user
        manual = operator.id != current_user.id
        if not manual:
            await self.validate_self_service_eligibility(current_user)

        if not manual and not payload.mock_payment_confirmed:
            raise AppError(
                "PAYMENT_NOT_CONFIRMED",
                "Mock payment confirmation is required.",
                400,
            )

        existing_payment = await self.payments.get_by_idempotency_key(
            user_id=current_user.id,
            idempotency_key=payload.idempotency_key,
        )
        if existing_payment:
            existing_invoice = await self.invoices.get_by_payment_id(existing_payment.id)
            return self._purchase_response(
                message="Duplicate submission ignored. Returning the original purchase.",
                membership=existing_payment.membership,
                payment=existing_payment,
                invoice=existing_invoice,
            )

        plan = await self.plans.get_by_id(payload.plan_id)
        if not plan or not plan.is_active:
            raise ResourceNotFoundError("Membership plan was not found.")

        timezone = ZoneInfo(self.settings.GYM_TIMEZONE)
        today = datetime.now(UTC).astimezone(timezone).date()
        current_membership = await self.memberships.get_current_for_user_for_update(current_user.id)
        quote = None if manual else await self.attendance_benefit_quote(
            user=current_user,
            plan=plan,
            current_membership=current_membership,
        )
        if quote and quote.status == "pending":
            raise AppError(
                "ATTENDANCE_BENEFIT_PENDING",
                "A discounted renewal checkout is already pending. Complete it or wait for it to expire.",
                409,
            )
        if quote:
            discount_amount = quote.pricing.discount_amount
            final_amount = quote.pricing.final_amount
        else:
            discount_amount, final_amount = self.calculate_amounts(plan.base_price, plan.discount_percent)
        coverage_start_date = today

        transaction_kind = "purchase"
        if current_membership and current_membership.expiry_date >= today:
            transaction_kind = "renewal"
            coverage_start_date = current_membership.expiry_date + timedelta(days=1)
            current_membership.plan_id = plan.id
            current_membership.expiry_date = current_membership.expiry_date + timedelta(
                days=plan.duration_days,
            )
            current_membership.status = MembershipStatus.ACTIVE.value
            membership = current_membership
        else:
            membership = await self.memberships.create(
                user_id=current_user.id,
                plan_id=plan.id,
                status=MembershipStatus.ACTIVE.value,
                start_date=today,
                expiry_date=today + timedelta(days=plan.duration_days),
            )

        transaction_date = datetime.now(UTC)
        payment_reference = f"STAFF-{uuid4().hex[:12].upper()}" if manual else f"MOCK-{uuid4().hex[:12].upper()}"
        try:
            payment = await self.payments.create(
                user_id=current_user.id,
                membership_id=membership.id,
                plan_id=plan.id,
                idempotency_key=payload.idempotency_key,
                amount=final_amount,
                discount_amount=discount_amount,
                status=PaymentStatus.SUCCEEDED.value,
                mock_reference=payment_reference,
                attendance_benefit_period_start=quote.period_start if quote and quote.available else None,
                discount_details=quote.model_dump(mode="json") if quote else None,
            )
        except IntegrityError as exc:
            await self.session.rollback()
            if quote and quote.available:
                raise AppError(
                    "ATTENDANCE_BENEFIT_ALREADY_USED",
                    "This attendance benefit is already reserved or consumed.",
                    409,
                ) from exc
            raise

        invoice_number = self.invoice_pdf.build_invoice_number(
            payment.id,
            transaction_date,
        )
        pdf_path = self.invoice_pdf.generate_pdf(
            invoice_number=invoice_number,
            member_name=current_user.name,
            member_email=current_user.email,
            plan_name=plan.name,
            amount=final_amount,
            discount_amount=discount_amount,
            transaction_date=transaction_date,
            membership_start_date=coverage_start_date,
            membership_expiry_date=membership.expiry_date,
            discount_details=payment.discount_details,
        )
        invoice = await self.invoices.create(
            invoice_number=invoice_number,
            user_id=current_user.id,
            payment_id=payment.id,
            plan_name=plan.name,
            amount=final_amount,
            discount_amount=discount_amount,
            transaction_date=transaction_date,
            membership_start_date=coverage_start_date,
            membership_expiry_date=membership.expiry_date,
            pdf_path=pdf_path,
            discount_details=payment.discount_details,
        )

        recipient = current_user.email.lower()
        local, domain = recipient.rsplit("@", 1)
        masked_recipient = f"{local[:1]}{'*' * max(2, len(local) - 1)}@{domain}"
        for template_type in (f"membership_{transaction_kind}", "membership_invoice"):
            await self.email_deliveries.enqueue_once(
                idempotency_key=f"{template_type}:{invoice.id}:{recipient}:v1",
                template_type=template_type,
                template_version=1,
                user_id=current_user.id,
                membership_id=membership.id,
                payment_id=payment.id,
                invoice_id=invoice.id,
                recipient_email=recipient,
                recipient_masked=masked_recipient,
                status="queued",
            )

        if manual:
            await AuditRepository(self.session).create(
                actor_user_id=operator.id,
                target_user_id=current_user.id,
                action="membership.manual_enrollment.created",
                entity_type="membership",
                entity_id=str(membership.id),
                reason=manual_reason,
                outcome=f"{plan.name} · {final_amount}",
                summary="Staff manually enrolled a member and issued a membership invoice.",
            )

        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise AppError(
                "DUPLICATE_PAYMENT_REQUEST",
                "This payment request has already been processed.",
                409,
            ) from exc

        await self.session.refresh(membership)
        await self.session.refresh(payment)
        await self.session.refresh(invoice)

        return self._purchase_response(
            message="Membership manually enrolled successfully." if manual else "Membership purchase successful.",
            membership=membership,
            payment=payment,
            invoice=invoice,
            plan_name=plan.name,
        )

    @staticmethod
    def calculate_amounts(base_price, discount_percent) -> tuple[Decimal, Decimal]:
        discount_amount = (base_price * discount_percent / Decimal("100")).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )
        final_amount = (base_price - discount_amount).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )
        return discount_amount, final_amount

    async def finalize_vnpay_payment(self, *, user: User, plan, payment, transaction_date: datetime):
        await self.validate_self_service_eligibility(user, for_update=True)
        today = transaction_date.astimezone(ZoneInfo(self.settings.GYM_TIMEZONE)).date()
        current_membership = (
            await self.memberships.get_by_id(payment.membership_id, for_update=True)
            if payment.membership_id
            else await self.memberships.get_current_for_user_for_update(user.id)
        )
        coverage_start_date = today
        transaction_kind = "purchase"
        reserved_renewal = bool(
            current_membership
            and (payment.discount_details or {}).get("pricing", {}).get("transaction_kind") == "renewal"
        )
        if current_membership and (current_membership.expiry_date >= today or reserved_renewal):
            transaction_kind = "renewal"
            coverage_start_date = current_membership.expiry_date + timedelta(days=1)
            current_membership.plan_id = plan.id
            current_membership.expiry_date += timedelta(days=plan.duration_days)
            current_membership.status = MembershipStatus.ACTIVE.value
            membership = current_membership
        else:
            membership = await self.memberships.create(
                user_id=user.id,
                plan_id=plan.id,
                status=MembershipStatus.ACTIVE.value,
                start_date=today,
                expiry_date=today + timedelta(days=plan.duration_days),
            )

        payment.membership_id = membership.id
        invoice_number = self.invoice_pdf.build_invoice_number(payment.id, transaction_date)
        pdf_path = self.invoice_pdf.generate_pdf(
            invoice_number=invoice_number,
            member_name=user.name,
            member_email=user.email,
            plan_name=plan.name,
            amount=payment.amount,
            discount_amount=payment.discount_amount,
            transaction_date=transaction_date,
            membership_start_date=coverage_start_date,
            membership_expiry_date=membership.expiry_date,
            discount_details=payment.discount_details,
        )
        invoice = await self.invoices.create(
            invoice_number=invoice_number,
            user_id=user.id,
            payment_id=payment.id,
            plan_name=plan.name,
            amount=payment.amount,
            discount_amount=payment.discount_amount,
            transaction_date=transaction_date,
            membership_start_date=coverage_start_date,
            membership_expiry_date=membership.expiry_date,
            pdf_path=pdf_path,
            discount_details=payment.discount_details,
        )

        recipient = user.email.lower()
        local, domain = recipient.rsplit("@", 1)
        await self.email_deliveries.enqueue_once(
            idempotency_key=f"membership_invoice:{invoice.id}:{recipient}:v1",
            template_type="membership_invoice",
            template_version=1,
            user_id=user.id,
            membership_id=membership.id,
            payment_id=payment.id,
            invoice_id=invoice.id,
            recipient_email=recipient,
            recipient_masked=f"{local[:1]}{'*' * max(2, len(local) - 1)}@{domain}",
            status="queued",
        )
        await self.notifications.create_notification_once(
            user_id=user.id,
            category="billing",
            notification_type="membership_payment_confirmed",
            title="Membership payment confirmed",
            message=f"Your {plan.name} {transaction_kind} was confirmed and invoice {invoice_number} is ready.",
            channel="in_app",
            delivery_state="delivered",
            delivered_at=transaction_date,
            dedupe_key=f"vnpay-payment:{payment.id}:in_app",
            action_type="invoice",
            action_id=invoice.id,
        )
        await AuditRepository(self.session).create(
            target_user_id=user.id,
            action="payment.vnpay.confirmed",
            entity_type="payment",
            entity_id=str(payment.id),
            outcome="paid",
            summary="A verified VNPay IPN confirmed payment and activated membership coverage.",
            after_data={
                "provider": "vnpay",
                "transaction_kind": transaction_kind,
                "membership_id": str(membership.id),
                "invoice_id": str(invoice.id),
                "discount_details": payment.discount_details,
            },
        )
        return membership, invoice

    def _purchase_response(
        self,
        *,
        message: str,
        membership,
        payment,
        invoice,
        plan_name: str | None = None,
    ) -> PurchaseMembershipResponse:
        if invoice is None:
            raise AppError(
                "INVOICE_NOT_AVAILABLE",
                "The original invoice could not be found.",
                500,
            )

        return PurchaseMembershipResponse(
            message=message,
            membership=MembershipSummary(
                id=membership.id,
                plan_id=membership.plan_id,
                plan_name=plan_name or payment.plan.name,
                status=membership.status,
                start_date=membership.start_date,
                expiry_date=membership.expiry_date,
            ),
            payment=PaymentSummary.model_validate(payment),
            invoice=InvoiceSummary(
                id=invoice.id,
                invoice_number=invoice.invoice_number,
                amount=invoice.amount,
                discount_amount=invoice.discount_amount,
                transaction_date=invoice.transaction_date,
                membership_start_date=invoice.membership_start_date,
                membership_expiry_date=invoice.membership_expiry_date,
                download_url=f"/api/v1/billing/me/invoices/{invoice.id}",
            ),
        )
