from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.billing import Invoice, Payment
from app.models.classes import ClassBooking, GymClass
from app.models.email_delivery import EmailDelivery
from app.models.membership import MembershipPlan
from app.models.user import User


class BillingAdminRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _conditions(
        self,
        *,
        member: str | None,
        status: str | None,
        date_from: datetime | None,
        date_to: datetime | None,
        plan: str | None,
        tier: str | None,
        product_type: str | None,
    ) -> list[Any]:
        conditions: list[Any] = []
        if member:
            term = f"%{member.strip()}%"
            conditions.append(or_(User.name.ilike(term), User.email.ilike(term)))
        if status:
            conditions.append(Payment.status == status)
        if date_from:
            conditions.append(Payment.created_at >= date_from)
        if date_to:
            conditions.append(Payment.created_at <= date_to)
        if plan:
            term = f"%{plan.strip()}%"
            conditions.append(or_(MembershipPlan.name.ilike(term), Invoice.product_name.ilike(term)))
        if tier:
            conditions.append(User.tier == tier)
        if product_type:
            conditions.append(Payment.product_type == product_type)
        return conditions

    async def list_payments(
        self,
        *,
        page: int,
        page_size: int,
        member: str | None,
        status: str | None,
        date_from: datetime | None,
        date_to: datetime | None,
        plan: str | None,
        tier: str | None,
        product_type: str | None,
        paginate: bool = True,
    ) -> tuple[list[tuple[Payment, User, str, UUID | None, str | None, str | None]], int, Decimal]:
        conditions = self._conditions(
            member=member,
            status=status,
            date_from=date_from,
            date_to=date_to,
            plan=plan,
            tier=tier,
            product_type=product_type,
        )
        base = (
            Payment.__table__
            .join(User, User.id == Payment.user_id)
            .outerjoin(MembershipPlan, MembershipPlan.id == Payment.plan_id)
            .outerjoin(Invoice, Invoice.payment_id == Payment.id)
            .outerjoin(ClassBooking, ClassBooking.id == Payment.class_booking_id)
            .outerjoin(GymClass, GymClass.id == ClassBooking.class_id)
        )
        email_state = (
            select(EmailDelivery.status)
            .where(
                EmailDelivery.payment_id == Payment.id,
                EmailDelivery.template_type.in_(("membership_invoice", "class_booking_invoice")),
            )
            .order_by(EmailDelivery.created_at.desc())
            .limit(1)
            .scalar_subquery()
        )
        summary = (
            await self.session.execute(
                select(func.count(Payment.id), func.coalesce(func.sum(Payment.amount), 0))
                .select_from(base)
                .where(*conditions),
            )
        ).one()
        query = (
            select(
                Payment,
                User,
                func.coalesce(MembershipPlan.name, GymClass.title),
                Invoice.id,
                email_state,
                ClassBooking.refund_status,
            )
            .select_from(base)
            .where(*conditions)
            .order_by(Payment.created_at.desc(), Payment.id.desc())
        )
        if paginate:
            query = query.offset((page - 1) * page_size).limit(page_size)
        rows = (await self.session.execute(query)).all()
        return [tuple(row) for row in rows], int(summary[0]), Decimal(summary[1])

    async def list_invoices(
        self,
        *,
        page: int,
        page_size: int,
        member: str | None,
        status: str | None,
        date_from: datetime | None,
        date_to: datetime | None,
        plan: str | None,
        tier: str | None,
        product_type: str | None,
        paginate: bool = True,
    ) -> tuple[list[tuple[Invoice, User]], int, Decimal]:
        conditions = self._conditions(
            member=member,
            status=status,
            date_from=date_from,
            date_to=date_to,
            plan=plan,
            tier=tier,
            product_type=product_type,
        )
        base = (
            Invoice.__table__
            .join(User, User.id == Invoice.user_id)
            .join(Payment, Payment.id == Invoice.payment_id)
            .outerjoin(MembershipPlan, MembershipPlan.id == Payment.plan_id)
        )
        summary = (
            await self.session.execute(
                select(func.count(Invoice.id), func.coalesce(func.sum(Invoice.amount), 0))
                .select_from(base)
                .where(*conditions),
            )
        ).one()
        query = (
            select(Invoice, User)
            .select_from(base)
            .where(*conditions)
            .order_by(Invoice.transaction_date.desc(), Invoice.id.desc())
        )
        if paginate:
            query = query.offset((page - 1) * page_size).limit(page_size)
        rows = (await self.session.execute(query)).all()
        return [(row[0], row[1]) for row in rows], int(summary[0]), Decimal(summary[1])
