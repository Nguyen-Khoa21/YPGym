from pathlib import Path
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import PermissionDeniedError, ResourceNotFoundError
from app.models.user import User
from app.repositories.billing_repository import InvoiceRepository, PaymentRepository
from app.schemas.billing_schema import (
    AdminBillingItem,
    InvoiceHistoryItem,
    PaymentHistoryItem,
)
from app.services.invoice_service import InvoicePdfService


class BillingService:
    def __init__(self, session: AsyncSession) -> None:
        self.payments = PaymentRepository(session)
        self.invoices = InvoiceRepository(session)
        self.invoice_pdf = InvoicePdfService()

    async def list_my_payments(self, user: User) -> list[PaymentHistoryItem]:
        payments = await self.payments.list_for_user(user.id)
        return [
            PaymentHistoryItem(
                id=payment.id,
                plan_name=payment.plan.name,
                amount=payment.amount,
                discount_amount=payment.discount_amount,
                status=payment.status,
                mock_reference=payment.mock_reference,
                created_at=payment.created_at,
            )
            for payment in payments
        ]

    async def list_my_invoices(self, user: User) -> list[InvoiceHistoryItem]:
        invoices = await self.invoices.list_for_user(user.id)
        return [self._invoice_history_item(invoice) for invoice in invoices]

    async def get_invoice_file(self, *, user: User, invoice_id: UUID) -> Path:
        invoice = await self.invoices.get_for_user(user_id=user.id, invoice_id=invoice_id)
        if not invoice:
            raise ResourceNotFoundError("Invoice was not found.")

        return Path(
            self.invoice_pdf.generate_pdf(
                invoice_number=invoice.invoice_number,
                member_name=invoice.user.name,
                member_email=invoice.user.email,
                plan_name=invoice.plan_name,
                amount=invoice.amount,
                discount_amount=invoice.discount_amount,
                transaction_date=invoice.transaction_date,
                membership_start_date=invoice.membership_start_date,
                membership_expiry_date=invoice.membership_expiry_date,
            ),
        )

    async def list_admin_billing(self, user: User) -> list[AdminBillingItem]:
        if user.role not in {"admin", "manager", "staff"}:
            raise PermissionDeniedError()

        payments = await self.payments.list_recent()
        return [
            AdminBillingItem(
                payment_id=payment.id,
                user_id=payment.user_id,
                member_name=payment.user.name,
                member_email=payment.user.email,
                plan_name=payment.plan.name,
                amount=payment.amount,
                status=payment.status,
                created_at=payment.created_at,
            )
            for payment in payments
        ]

    def _invoice_history_item(self, invoice) -> InvoiceHistoryItem:
        return InvoiceHistoryItem(
            id=invoice.id,
            invoice_number=invoice.invoice_number,
            plan_name=invoice.plan_name,
            amount=invoice.amount,
            discount_amount=invoice.discount_amount,
            transaction_date=invoice.transaction_date,
            membership_start_date=invoice.membership_start_date,
            membership_expiry_date=invoice.membership_expiry_date,
            download_url=f"/api/v1/billing/me/invoices/{invoice.id}",
        )
