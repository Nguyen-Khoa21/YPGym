from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.billing import Invoice, Payment


class PaymentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_idempotency_key(
        self,
        *,
        user_id: UUID,
        idempotency_key: str,
    ) -> Payment | None:
        result = await self.session.execute(
            select(Payment)
            .options(selectinload(Payment.plan), selectinload(Payment.membership))
            .where(
                Payment.user_id == user_id,
                Payment.idempotency_key == idempotency_key,
            ),
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        user_id: UUID,
        membership_id: UUID,
        plan_id: UUID,
        idempotency_key: str,
        amount,
        discount_amount,
        status: str,
        mock_reference: str,
    ) -> Payment:
        payment = Payment(
            user_id=user_id,
            membership_id=membership_id,
            plan_id=plan_id,
            idempotency_key=idempotency_key,
            amount=amount,
            discount_amount=discount_amount,
            status=status,
            mock_reference=mock_reference,
        )
        self.session.add(payment)
        await self.session.flush()
        return payment

    async def list_for_user(self, user_id: UUID) -> list[Payment]:
        result = await self.session.execute(
            select(Payment)
            .options(selectinload(Payment.plan))
            .where(Payment.user_id == user_id)
            .order_by(Payment.created_at.desc()),
        )
        return list(result.scalars().all())

    async def list_recent(self, limit: int = 50) -> list[Payment]:
        result = await self.session.execute(
            select(Payment)
            .options(selectinload(Payment.plan), selectinload(Payment.user))
            .order_by(Payment.created_at.desc())
            .limit(limit),
        )
        return list(result.scalars().all())


class InvoiceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        invoice_number: str,
        user_id: UUID,
        payment_id: UUID,
        plan_name: str,
        amount,
        discount_amount,
        transaction_date,
        membership_start_date,
        membership_expiry_date,
        pdf_path: str,
    ) -> Invoice:
        invoice = Invoice(
            invoice_number=invoice_number,
            user_id=user_id,
            payment_id=payment_id,
            plan_name=plan_name,
            amount=amount,
            discount_amount=discount_amount,
            transaction_date=transaction_date,
            membership_start_date=membership_start_date,
            membership_expiry_date=membership_expiry_date,
            pdf_path=pdf_path,
        )
        self.session.add(invoice)
        await self.session.flush()
        return invoice

    async def get_by_payment_id(self, payment_id: UUID) -> Invoice | None:
        result = await self.session.execute(
            select(Invoice).where(Invoice.payment_id == payment_id),
        )
        return result.scalar_one_or_none()

    async def get_for_user(self, *, user_id: UUID, invoice_id: UUID) -> Invoice | None:
        result = await self.session.execute(
            select(Invoice).where(Invoice.user_id == user_id, Invoice.id == invoice_id),
        )
        return result.scalar_one_or_none()

    async def list_for_user(self, user_id: UUID) -> list[Invoice]:
        result = await self.session.execute(
            select(Invoice)
            .where(Invoice.user_id == user_id)
            .order_by(Invoice.transaction_date.desc()),
        )
        return list(result.scalars().all())
