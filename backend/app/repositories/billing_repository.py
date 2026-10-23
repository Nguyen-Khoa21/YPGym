from uuid import UUID

from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.billing import Invoice, Payment
from app.models.classes import ClassBooking


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
            .options(
                selectinload(Payment.plan),
                selectinload(Payment.membership),
                selectinload(Payment.class_booking).selectinload(ClassBooking.gym_class),
            )
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
        membership_id: UUID | None,
        plan_id: UUID | None,
        idempotency_key: str,
        amount,
        discount_amount,
        status: str,
        mock_reference: str,
        amount_vnd: int | None = None,
        provider: str = "mock",
        txn_ref: str | None = None,
        currency: str = "VND",
        expires_at: datetime | None = None,
        client_platform: str = "web",
        class_booking_id: UUID | None = None,
        product_type: str = "membership",
        attendance_benefit_period_start: date | None = None,
        discount_details: dict | None = None,
    ) -> Payment:
        payment = Payment(
            user_id=user_id,
            membership_id=membership_id,
            plan_id=plan_id,
            class_booking_id=class_booking_id,
            product_type=product_type,
            idempotency_key=idempotency_key,
            amount=amount,
            amount_vnd=amount_vnd if amount_vnd is not None else int(amount),
            discount_amount=discount_amount,
            status=status,
            mock_reference=mock_reference,
            provider=provider,
            txn_ref=txn_ref,
            currency=currency,
            expires_at=expires_at,
            client_platform=client_platform,
            attendance_benefit_period_start=attendance_benefit_period_start,
            discount_details=discount_details,
        )
        self.session.add(payment)
        await self.session.flush()
        return payment

    async def get_active_attendance_benefit_payment(
        self,
        *,
        user_id: UUID,
        period_start: date,
    ) -> Payment | None:
        return (
            await self.session.execute(
                select(Payment)
                .where(
                    Payment.user_id == user_id,
                    Payment.attendance_benefit_period_start == period_start,
                    Payment.status.in_(("pending", "paid", "succeeded")),
                )
                .order_by(Payment.created_at.desc())
                .limit(1),
            )
        ).scalar_one_or_none()

    async def get_by_txn_ref(self, txn_ref: str, *, for_update: bool = False) -> Payment | None:
        query = (
            select(Payment)
            .options(
                selectinload(Payment.plan),
                selectinload(Payment.membership),
                selectinload(Payment.invoice),
                selectinload(Payment.class_booking).selectinload(ClassBooking.gym_class),
            )
            .where(Payment.txn_ref == txn_ref)
        )
        if for_update:
            query = query.with_for_update()
        return (await self.session.execute(query)).scalar_one_or_none()

    async def get_for_user(self, *, payment_id: UUID, user_id: UUID, for_update: bool = False) -> Payment | None:
        query = (
            select(Payment)
            .options(
                selectinload(Payment.plan),
                selectinload(Payment.membership),
                selectinload(Payment.invoice),
                selectinload(Payment.class_booking).selectinload(ClassBooking.gym_class),
            )
            .where(Payment.id == payment_id, Payment.user_id == user_id)
        )
        if for_update:
            query = query.with_for_update()
        return (await self.session.execute(query)).scalar_one_or_none()

    async def list_expired_pending_for_update(self, now: datetime, limit: int = 100) -> list[Payment]:
        result = await self.session.execute(
            select(Payment)
            .options(selectinload(Payment.class_booking))
            .where(
                Payment.status == "pending",
                Payment.expires_at.is_not(None),
                Payment.expires_at <= now,
            )
            .order_by(Payment.expires_at, Payment.id)
            .with_for_update(skip_locked=True)
            .limit(limit),
        )
        return list(result.scalars().all())

    async def list_for_user(self, user_id: UUID) -> list[Payment]:
        result = await self.session.execute(
            select(Payment)
            .options(selectinload(Payment.plan), selectinload(Payment.class_booking).selectinload(ClassBooking.gym_class), selectinload(Payment.invoice))
            .where(Payment.user_id == user_id)
            .order_by(Payment.created_at.desc()),
        )
        return list(result.scalars().all())

    async def list_recent(self, limit: int = 50, product_type: str | None = None) -> list[Payment]:
        query = (
            select(Payment)
            .options(
                selectinload(Payment.plan),
                selectinload(Payment.user),
                selectinload(Payment.class_booking).selectinload(ClassBooking.gym_class),
                selectinload(Payment.invoice),
            )
            .order_by(Payment.created_at.desc())
            .limit(limit)
        )
        if product_type:
            query = query.where(Payment.product_type == product_type)
        return list((await self.session.execute(query)).scalars().all())


    async def get_by_id(self, payment_id: UUID, *, for_update: bool = False) -> Payment | None:
        query = (
            select(Payment)
            .options(
                selectinload(Payment.plan),
                selectinload(Payment.class_booking).selectinload(ClassBooking.gym_class),
                selectinload(Payment.invoice),
            )
            .where(Payment.id == payment_id)
        )
        if for_update:
            query = query.with_for_update()
        return (await self.session.execute(query)).scalar_one_or_none()


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
        product_type: str = "membership",
        product_name: str | None = None,
        class_booking_id: UUID | None = None,
        service_start_at=None,
        service_end_at=None,
        discount_details: dict | None = None,
    ) -> Invoice:
        invoice = Invoice(
            invoice_number=invoice_number,
            user_id=user_id,
            payment_id=payment_id,
            plan_name=plan_name,
            product_type=product_type,
            product_name=product_name or plan_name,
            class_booking_id=class_booking_id,
            amount=amount,
            discount_amount=discount_amount,
            transaction_date=transaction_date,
            membership_start_date=membership_start_date,
            membership_expiry_date=membership_expiry_date,
            service_start_at=service_start_at,
            service_end_at=service_end_at,
            discount_details=discount_details,
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
            select(Invoice)
            .options(selectinload(Invoice.user))
            .where(Invoice.user_id == user_id, Invoice.id == invoice_id),
        )
        return result.scalar_one_or_none()

    async def list_for_user(self, user_id: UUID) -> list[Invoice]:
        result = await self.session.execute(
            select(Invoice)
            .where(Invoice.user_id == user_id)
            .order_by(Invoice.transaction_date.desc()),
        )
        return list(result.scalars().all())
