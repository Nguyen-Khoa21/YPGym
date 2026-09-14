from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError, ResourceNotFoundError
from app.models.enums import MembershipStatus, PaymentStatus
from app.models.user import User
from app.repositories.billing_repository import InvoiceRepository, PaymentRepository
from app.repositories.membership_repository import (
    MembershipPlanRepository,
    UserMembershipRepository,
)
from app.schemas.membership_schema import (
    InvoiceSummary,
    MembershipSummary,
    PaymentSummary,
    PurchaseMembershipRequest,
    PurchaseMembershipResponse,
)
from app.services.invoice_service import InvoicePdfService


class MembershipService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.plans = MembershipPlanRepository(session)
        self.memberships = UserMembershipRepository(session)
        self.payments = PaymentRepository(session)
        self.invoices = InvoiceRepository(session)
        self.invoice_pdf = InvoicePdfService()

    async def purchase(
        self,
        *,
        current_user: User,
        payload: PurchaseMembershipRequest,
    ) -> PurchaseMembershipResponse:
        if not current_user.is_email_verified:
            raise AppError(
                "EMAIL_NOT_VERIFIED",
                "Please verify your email before purchasing a membership.",
                403,
            )

        if not payload.mock_payment_confirmed:
            raise AppError(
                "PAYMENT_NOT_CONFIRMED",
                "Mock payment confirmation is required.",
                400,
            )

        latest_membership = await self.memberships.get_latest_for_user(current_user.id)
        if latest_membership and latest_membership.status == MembershipStatus.REVOKED.value:
            raise AppError(
                "MEMBERSHIP_REVOKED",
                "A revoked membership cannot be renewed through self-service.",
                403,
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

        discount_amount, final_amount = self._calculate_amounts(
            plan.base_price,
            plan.discount_percent,
        )
        today = date.today()
        current_membership = await self.memberships.get_current_for_user(current_user.id)
        coverage_start_date = today

        if current_membership and current_membership.expiry_date >= today:
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
        mock_reference = f"MOCK-{uuid4().hex[:12].upper()}"
        payment = await self.payments.create(
            user_id=current_user.id,
            membership_id=membership.id,
            plan_id=plan.id,
            idempotency_key=payload.idempotency_key,
            amount=final_amount,
            discount_amount=discount_amount,
            status=PaymentStatus.SUCCEEDED.value,
            mock_reference=mock_reference,
        )

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
            message="Membership purchase successful.",
            membership=membership,
            payment=payment,
            invoice=invoice,
            plan_name=plan.name,
        )

    def _calculate_amounts(self, base_price, discount_percent) -> tuple[Decimal, Decimal]:
        discount_amount = (base_price * discount_percent / Decimal("100")).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )
        final_amount = (base_price - discount_amount).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )
        return discount_amount, final_amount

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
