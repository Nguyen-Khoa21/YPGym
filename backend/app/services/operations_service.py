import csv
import io
from datetime import date, datetime
from math import ceil
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ResourceNotFoundError
from app.models.user import User
from app.repositories.operations_repository import (
    AuditRepository,
    BillingAdminRepository,
    CrmRepository,
    MembershipOperationsRepository,
)
from app.schemas.auth_schema import UserPublic
from app.schemas.operations_schema import (
    AdminBillingInvoiceItem,
    AdminBillingInvoicePage,
    AdminBillingPaymentItem,
    AdminBillingPaymentPage,
    AdminInvoiceRecord,
    AdminMemberDetailResponse,
    AdminMemberListItem,
    AdminMemberListResponse,
    AdminPaymentRecord,
    AttendanceHistorySummaryItem,
    AttendanceSummary,
    AuditListItem,
    AuditLogPage,
    BookingSummary,
    MemberCrmSummary,
    MembershipRecord,
    MembershipRequestItem,
    PageInfo,
)
from app.services.lifecycle_service import MembershipLifecycleService


def page_info(*, page: int, page_size: int, total: int) -> PageInfo:
    return PageInfo(page=page, page_size=page_size, total=total, pages=ceil(total / page_size) if total else 0)


def csv_safe_cell(value: object) -> str:
    text = "" if value is None else str(value)
    if text.lstrip().startswith(("=", "+", "-", "@")):
        return f"'{text}"
    return text


def write_csv(headers: list[str], rows: list[list[object]]) -> str:
    stream = io.StringIO(newline="")
    writer = csv.writer(stream)
    writer.writerow(headers)
    writer.writerows([[csv_safe_cell(value) for value in row] for row in rows])
    return stream.getvalue()


class CrmService:
    SORT_FIELDS = {"name", "email", "created_at", "expiry_date", "status"}

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.crm = CrmRepository(session)
        self.operations = MembershipOperationsRepository(session)
        self.audit = AuditRepository(session)

    async def list_members(
        self,
        *,
        page: int,
        page_size: int,
        search: str | None,
        role: str | None,
        tier: str | None,
        status: str | None,
        expiry_from: date | None,
        expiry_to: date | None,
        sort_by: str,
        sort_order: str,
    ) -> AdminMemberListResponse:
        rows, total, summary = await self.crm.list_members(
            page=page,
            page_size=page_size,
            search=search,
            role=role,
            tier=tier,
            status=status,
            expiry_from=expiry_from,
            expiry_to=expiry_to,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        items = []
        for user, membership, plan in rows:
            record = None
            if membership and plan:
                record = MembershipRecord(
                    id=membership.id,
                    plan_id=membership.plan_id,
                    plan_name=plan.name,
                    status=membership.status,
                    start_date=membership.start_date,
                    expiry_date=membership.expiry_date,
                    frozen_from=membership.frozen_from,
                    frozen_until=membership.frozen_until,
                )
            items.append(
                AdminMemberListItem(
                    id=user.id,
                    name=user.name,
                    email=user.email,
                    phone=user.phone,
                    role=user.role,
                    tier=user.tier,
                    is_email_verified=user.is_email_verified,
                    membership=record,
                    created_at=user.created_at,
                ),
            )
        return AdminMemberListResponse(
            items=items,
            page=page_info(page=page, page_size=page_size, total=total),
            summary=MemberCrmSummary(
                total=summary[0],
                active=summary[1],
                expiring_soon=summary[2],
                frozen=summary[3],
                expired_or_inactive=summary[4],
            ),
        )

    async def member_detail(self, user_id: UUID) -> AdminMemberDetailResponse:
        user = await self.crm.get_user(user_id)
        if not user:
            raise ResourceNotFoundError("Member was not found.")
        memberships = await self.crm.list_memberships(user_id)
        payments = await self.crm.list_payments(user_id)
        invoices = await self.crm.list_invoices(user_id)
        attendance_count, active_count, last_check_in = await self.crm.attendance_summary(user_id)
        attendance_history = await self.crm.attendance_history(user_id)
        booking_total, booking_upcoming, waitlisted = await self.crm.booking_summary(user_id)
        freezes, cancellations = await self.operations.list_requests_for_user(user_id)
        audit_rows = await self.audit.list_for_target(user_id)

        request_items = [MembershipLifecycleService._freeze_item(item) for item in freezes]
        request_items.extend(MembershipLifecycleService._cancellation_item(item) for item in cancellations)
        request_items.sort(key=lambda item: item.created_at, reverse=True)
        return AdminMemberDetailResponse(
            profile=UserPublic.model_validate(user),
            memberships=[
                MembershipRecord(
                    id=item.id,
                    plan_id=item.plan_id,
                    plan_name=item.plan.name,
                    status=item.status,
                    start_date=item.start_date,
                    expiry_date=item.expiry_date,
                    frozen_from=item.frozen_from,
                    frozen_until=item.frozen_until,
                )
                for item in memberships
            ],
            payments=[
                AdminPaymentRecord(
                    id=item.id,
                    plan_name=item.plan.name,
                    amount=item.amount,
                    discount_amount=item.discount_amount,
                    status=item.status,
                    reference=item.mock_reference,
                    created_at=item.created_at,
                )
                for item in payments
            ],
            invoices=[
                AdminInvoiceRecord(
                    id=item.id,
                    invoice_number=item.invoice_number,
                    plan_name=item.plan_name,
                    amount=item.amount,
                    transaction_date=item.transaction_date,
                )
                for item in invoices
            ],
            attendance_summary=AttendanceSummary(
                total_visits=attendance_count,
                active_sessions=active_count,
                last_check_in_at=last_check_in,
            ),
            attendance_history=[
                AttendanceHistorySummaryItem(
                    id=item.id,
                    checked_in_at=item.checked_in_at,
                    closed_at=item.closed_at,
                    status=item.status,
                    source=item.source,
                    device_id=item.device_id,
                )
                for item in attendance_history
            ],
            booking_summary=BookingSummary(
                total=booking_total,
                upcoming=booking_upcoming,
                waitlisted=waitlisted,
            ),
            membership_requests=request_items,
            audit_logs=[self._audit_item(log, actor_name, user.name) for log, actor_name in audit_rows],
        )

    async def export_members_csv(
        self,
        *,
        actor: User,
        search: str | None,
        role: str | None,
        tier: str | None,
        status: str | None,
        expiry_from: date | None,
        expiry_to: date | None,
        sort_by: str,
        sort_order: str,
    ) -> str:
        response = await self.list_members(
            page=1,
            page_size=100_000,
            search=search,
            role=role,
            tier=tier,
            status=status,
            expiry_from=expiry_from,
            expiry_to=expiry_to,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        content = write_csv(
            ["Member ID", "Name", "Email", "Phone", "Role", "Tier", "Membership status", "Plan", "Expiry date"],
            [
                [
                    item.id,
                    item.name,
                    item.email,
                    item.phone,
                    item.role,
                    item.tier,
                    item.membership.status if item.membership else "none",
                    item.membership.plan_name if item.membership else "",
                    item.membership.expiry_date if item.membership else "",
                ]
                for item in response.items
            ],
        )
        await self.audit.create(
            actor_user_id=actor.id,
            action="crm.members.exported",
            entity_type="user",
            reason="Filtered CRM CSV export",
            outcome=f"{len(response.items)} rows",
            summary="Admin exported filtered member personal information.",
        )
        await self.session.commit()
        return content

    @staticmethod
    def _audit_item(log, actor_name: str | None, target_name: str | None) -> AuditListItem:
        return AuditListItem(
            id=log.id,
            action=log.action,
            actor_user_id=log.actor_user_id,
            actor_name=actor_name,
            target_user_id=log.target_user_id,
            target_name=target_name,
            entity_type=log.entity_type,
            entity_id=log.entity_id,
            reason=log.reason,
            outcome=log.outcome,
            summary=log.summary,
            created_at=log.created_at,
        )


class BillingAdminService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.billing = BillingAdminRepository(session)
        self.audit = AuditRepository(session)

    async def list_payments(self, **filters) -> AdminBillingPaymentPage:
        rows, total, total_amount = await self.billing.list_payments(**filters)
        return AdminBillingPaymentPage(
            items=[
                AdminBillingPaymentItem(
                    payment_id=payment.id,
                    user_id=user.id,
                    member_name=user.name,
                    member_email=user.email,
                    member_tier=user.tier,
                    plan_name=plan.name,
                    amount=payment.amount,
                    discount_amount=payment.discount_amount,
                    status=payment.status,
                    created_at=payment.created_at,
                )
                for payment, user, plan in rows
            ],
            page=page_info(page=filters["page"], page_size=filters["page_size"], total=total),
            total_amount=total_amount,
        )

    async def list_invoices(self, **filters) -> AdminBillingInvoicePage:
        rows, total, total_amount = await self.billing.list_invoices(**filters)
        return AdminBillingInvoicePage(
            items=[
                AdminBillingInvoiceItem(
                    invoice_id=invoice.id,
                    user_id=user.id,
                    member_name=user.name,
                    member_email=user.email,
                    invoice_number=invoice.invoice_number,
                    plan_name=invoice.plan_name,
                    amount=invoice.amount,
                    transaction_date=invoice.transaction_date,
                )
                for invoice, user in rows
            ],
            page=page_info(page=filters["page"], page_size=filters["page_size"], total=total),
            total_amount=total_amount,
        )

    async def export_csv(self, *, actor: User, export_type: str, **filters) -> str:
        filters["paginate"] = False
        if export_type == "payments":
            rows, _, _ = await self.billing.list_payments(**filters)
            content = write_csv(
                ["Payment ID", "Member", "Email", "Tier", "Plan", "Amount", "Discount", "Status", "Created"],
                [[p.id, u.name, u.email, u.tier, plan.name, p.amount, p.discount_amount, p.status, p.created_at] for p, u, plan in rows],
            )
        else:
            rows, _, _ = await self.billing.list_invoices(**filters)
            content = write_csv(
                ["Invoice ID", "Invoice number", "Member", "Email", "Plan", "Amount", "Transaction date"],
                [[invoice.id, invoice.invoice_number, user.name, user.email, invoice.plan_name, invoice.amount, invoice.transaction_date] for invoice, user in rows],
            )
        await self.audit.create(
            actor_user_id=actor.id,
            action=f"billing.{export_type}.exported",
            entity_type=export_type,
            reason="Filtered billing CSV export",
            outcome=f"{len(rows)} rows",
            summary=f"Admin exported filtered {export_type} data containing personal information.",
        )
        await self.session.commit()
        return content


class AuditService:
    def __init__(self, session: AsyncSession) -> None:
        self.audit = AuditRepository(session)

    async def list_logs(self, **filters) -> AuditLogPage:
        rows, total = await self.audit.list_filtered(**filters)
        items = [CrmService._audit_item(log, actor_name, target_name) for log, actor_name, target_name in rows]
        return AuditLogPage(
            items=items,
            page=page_info(page=filters["page"], page_size=filters["page_size"], total=total),
        )
