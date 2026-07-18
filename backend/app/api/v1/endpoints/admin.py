from datetime import date, datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_roles
from app.db.redis import get_redis_client
from app.db.session import get_db_session
from app.models.user import User
from app.schemas.notification_schema import BroadcastCreate, BroadcastItem, BroadcastUpdate
from app.schemas.operations_schema import (
    AdminBillingInvoicePage,
    AdminBillingPaymentPage,
    AdminMemberDetailResponse,
    AdminMemberListResponse,
    AuditLogPage,
    ConfigurationItem,
    ConfigurationUpdateRequest,
    FreezeDecision,
    MembershipApprovalPage,
    MembershipRequestItem,
    OperationMessage,
    RequestDecision,
    RevokeMembershipRequest,
)
from app.services.configuration_service import ConfigurationService
from app.services.lifecycle_service import MembershipLifecycleService
from app.services.notification_service import NotificationService
from app.services.operations_service import AuditService, BillingAdminService, CrmService

router = APIRouter(prefix="/admin", tags=["admin operations"])


@router.get("/membership-requests", response_model=MembershipApprovalPage)
async def list_membership_requests(
    current_user: Annotated[User, Depends(require_roles("manager", "admin"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Literal["pending", "approved", "rejected"] | None = None,
) -> MembershipApprovalPage:
    return await MembershipLifecycleService(session).list_approval_requests(
        status=status,
        page=page,
        page_size=page_size,
    )


@router.get("/members", response_model=AdminMemberListResponse)
async def list_members(
    current_user: Annotated[User, Depends(require_roles("admin"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None, max_length=160),
    role: Literal["member", "staff", "manager", "admin", "pt"] | None = None,
    tier: Literal["normal", "advance", "vip"] | None = None,
    status: Literal["pending_verification", "active", "expiring_soon", "expired", "frozen", "cancelled", "revoked"] | None = None,
    expiry_from: date | None = None,
    expiry_to: date | None = None,
    sort_by: Literal["name", "email", "created_at", "expiry_date", "status"] = "created_at",
    sort_order: Literal["asc", "desc"] = "desc",
) -> AdminMemberListResponse:
    return await CrmService(session).list_members(
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


@router.get("/members/export.csv")
async def export_members(
    current_user: Annotated[User, Depends(require_roles("admin"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    search: str | None = Query(None, max_length=160),
    role: Literal["member", "staff", "manager", "admin", "pt"] | None = None,
    tier: Literal["normal", "advance", "vip"] | None = None,
    status: Literal["pending_verification", "active", "expiring_soon", "expired", "frozen", "cancelled", "revoked"] | None = None,
    expiry_from: date | None = None,
    expiry_to: date | None = None,
    sort_by: Literal["name", "email", "created_at", "expiry_date", "status"] = "created_at",
    sort_order: Literal["asc", "desc"] = "desc",
) -> StreamingResponse:
    content = await CrmService(session).export_members_csv(
        actor=current_user,
        search=search,
        role=role,
        tier=tier,
        status=status,
        expiry_from=expiry_from,
        expiry_to=expiry_to,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return _csv_response(content, "ypgym-members.csv")


@router.get("/members/{user_id}", response_model=AdminMemberDetailResponse)
async def member_detail(
    user_id: UUID,
    current_user: Annotated[User, Depends(require_roles("admin"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AdminMemberDetailResponse:
    return await CrmService(session).member_detail(user_id)


@router.post("/freeze-requests/{request_id}/decision", response_model=MembershipRequestItem)
async def decide_freeze(
    request_id: UUID,
    payload: FreezeDecision,
    current_user: Annotated[User, Depends(require_roles("manager", "admin"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> MembershipRequestItem:
    return await MembershipLifecycleService(session).decide_freeze_request(
        request_id=request_id,
        reviewer=current_user,
        payload=payload,
    )


@router.post("/cancellation-requests/{request_id}/decision", response_model=MembershipRequestItem)
async def decide_cancellation(
    request_id: UUID,
    payload: RequestDecision,
    current_user: Annotated[User, Depends(require_roles("manager", "admin"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> MembershipRequestItem:
    return await MembershipLifecycleService(session).decide_cancellation_request(
        request_id=request_id,
        reviewer=current_user,
        payload=payload,
    )


@router.post("/members/{user_id}/revoke", response_model=OperationMessage)
async def revoke_membership(
    user_id: UUID,
    payload: RevokeMembershipRequest,
    current_user: Annotated[User, Depends(require_roles("admin"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> OperationMessage:
    return await MembershipLifecycleService(session).revoke_membership(
        user_id=user_id,
        reviewer=current_user,
        reason=payload.reason,
    )


@router.get("/billing/payments", response_model=AdminBillingPaymentPage)
async def list_billing_payments(
    current_user: Annotated[User, Depends(require_roles("admin"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    member: str | None = Query(None, max_length=160),
    status: str | None = Query(None, max_length=32),
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    plan: str | None = Query(None, max_length=120),
    tier: Literal["normal", "advance", "vip"] | None = None,
) -> AdminBillingPaymentPage:
    return await BillingAdminService(session).list_payments(
        page=page,
        page_size=page_size,
        member=member,
        status=status,
        date_from=date_from,
        date_to=date_to,
        plan=plan,
        tier=tier,
    )


@router.get("/billing/invoices", response_model=AdminBillingInvoicePage)
async def list_billing_invoices(
    current_user: Annotated[User, Depends(require_roles("admin"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    member: str | None = Query(None, max_length=160),
    status: str | None = Query(None, max_length=32),
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    plan: str | None = Query(None, max_length=120),
    tier: Literal["normal", "advance", "vip"] | None = None,
) -> AdminBillingInvoicePage:
    return await BillingAdminService(session).list_invoices(
        page=page,
        page_size=page_size,
        member=member,
        status=status,
        date_from=date_from,
        date_to=date_to,
        plan=plan,
        tier=tier,
    )


@router.get("/billing/{export_type}/export.csv")
async def export_billing(
    export_type: Literal["payments", "invoices"],
    current_user: Annotated[User, Depends(require_roles("admin"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    member: str | None = Query(None, max_length=160),
    status: str | None = Query(None, max_length=32),
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    plan: str | None = Query(None, max_length=120),
    tier: Literal["normal", "advance", "vip"] | None = None,
) -> StreamingResponse:
    content = await BillingAdminService(session).export_csv(
        actor=current_user,
        export_type=export_type,
        page=1,
        page_size=100_000,
        member=member,
        status=status,
        date_from=date_from,
        date_to=date_to,
        plan=plan,
        tier=tier,
    )
    return _csv_response(content, f"ypgym-{export_type}.csv")


@router.get("/audit-logs", response_model=AuditLogPage)
async def list_audit_logs(
    current_user: Annotated[User, Depends(require_roles("manager", "admin"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    action: str | None = Query(None, max_length=100),
    actor: str | None = Query(None, max_length=160),
    target: str | None = Query(None, max_length=160),
    entity: str | None = Query(None, max_length=160),
) -> AuditLogPage:
    return await AuditService(session).list_logs(
        page=page,
        page_size=page_size,
        date_from=date_from,
        date_to=date_to,
        action=action,
        actor=actor,
        target=target,
        entity=entity,
    )


@router.get("/configuration", response_model=list[ConfigurationItem])
async def list_configuration(
    current_user: Annotated[User, Depends(require_roles("manager", "admin"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    redis: Annotated[Redis, Depends(get_redis_client)],
) -> list[ConfigurationItem]:
    return await ConfigurationService(session, redis).list_items()


@router.patch("/configuration/{key}", response_model=ConfigurationItem)
async def update_configuration(
    key: str,
    payload: ConfigurationUpdateRequest,
    current_user: Annotated[User, Depends(require_roles("manager", "admin"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    redis: Annotated[Redis, Depends(get_redis_client)],
) -> ConfigurationItem:
    return await ConfigurationService(session, redis).update(key=key, value=payload.value, actor=current_user)


@router.get("/broadcasts", response_model=list[BroadcastItem])
async def list_broadcasts(
    current_user: Annotated[User, Depends(require_roles("manager", "admin"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[BroadcastItem]:
    return await NotificationService(session).list_admin_broadcasts()


@router.post("/broadcasts", response_model=BroadcastItem)
async def create_broadcast(
    payload: BroadcastCreate,
    current_user: Annotated[User, Depends(require_roles("manager", "admin"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> BroadcastItem:
    return await NotificationService(session).create_broadcast(actor=current_user, payload=payload)


@router.patch("/broadcasts/{broadcast_id}", response_model=BroadcastItem)
async def update_broadcast(
    broadcast_id: UUID,
    payload: BroadcastUpdate,
    current_user: Annotated[User, Depends(require_roles("manager", "admin"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> BroadcastItem:
    return await NotificationService(session).update_broadcast(
        broadcast_id=broadcast_id,
        actor=current_user,
        payload=payload,
    )


def _csv_response(content: str, filename: str) -> StreamingResponse:
    return StreamingResponse(
        iter([content]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
