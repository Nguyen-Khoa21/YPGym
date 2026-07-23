from datetime import UTC, date, datetime
from math import ceil
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError, ConflictError, ResourceNotFoundError
from app.models.enums import MembershipStatus
from app.models.membership import UserMembership
from app.models.operations import MembershipCancellationRequest, MembershipFreezeRequest
from app.models.user import User
from app.repositories.operations_repository import AuditRepository, MembershipOperationsRepository
from app.schemas.operations_schema import (
    CancellationRequestCreate,
    FreezeDecision,
    FreezeRequestCreate,
    MembershipApprovalItem,
    MembershipApprovalPage,
    MembershipRequestItem,
    OperationMessage,
    PageInfo,
    RequestDecision,
)


TERMINAL_MEMBERSHIP_STATUSES = {
    MembershipStatus.CANCELLED.value,
    MembershipStatus.REVOKED.value,
}
ELIGIBLE_MEMBERSHIP_STATUSES = {
    MembershipStatus.ACTIVE.value,
    MembershipStatus.EXPIRING_SOON.value,
}


def derive_membership_status(
    *,
    stored_status: str,
    is_email_verified: bool,
    expiry_date: date,
    today: date,
    frozen_from: date | None = None,
    frozen_until: date | None = None,
) -> str:
    if stored_status in TERMINAL_MEMBERSHIP_STATUSES:
        return stored_status
    if not is_email_verified:
        return MembershipStatus.PENDING_VERIFICATION.value
    if frozen_from and frozen_until and frozen_from <= today <= frozen_until:
        return MembershipStatus.FROZEN.value
    if expiry_date < today:
        return MembershipStatus.EXPIRED.value
    if (expiry_date - today).days <= 7:
        return MembershipStatus.EXPIRING_SOON.value
    return MembershipStatus.ACTIVE.value


def membership_access_message(status: str) -> str:
    messages = {
        "pending_verification": "Verify your email before using membership access.",
        "frozen": "Membership access is paused while your freeze is active.",
        "expired": "Renew your expired membership to restore access.",
        "cancelled": "This membership has been cancelled.",
        "revoked": "This membership was revoked by gym management.",
    }
    return messages.get(status, "Membership access is currently unavailable.")


class MembershipLifecycleService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.operations = MembershipOperationsRepository(session)
        self.audit = AuditRepository(session)

    async def require_eligible_membership(self, user: User) -> UserMembership:
        membership = await self.operations.get_current_for_update(user.id)
        if not membership:
            raise AppError("MEMBERSHIP_REQUIRED", "An active membership is required.", 403)
        status = derive_membership_status(
            stored_status=membership.status,
            is_email_verified=user.is_email_verified,
            expiry_date=membership.expiry_date,
            today=date.today(),
            frozen_from=membership.frozen_from,
            frozen_until=membership.frozen_until,
        )
        if membership.status != status:
            membership.status = status
            await self.session.flush()
        if status not in ELIGIBLE_MEMBERSHIP_STATUSES:
            raise AppError("MEMBERSHIP_INELIGIBLE", membership_access_message(status), 403, {"status": status})
        return membership

    async def access_snapshot(self, user: User) -> tuple[UserMembership | None, str, bool, str | None]:
        membership = await self.operations.get_latest(user.id)
        if not membership:
            return None, "none", False, "Buy a membership before booking a class."
        status = derive_membership_status(
            stored_status=membership.status,
            is_email_verified=user.is_email_verified,
            expiry_date=membership.expiry_date,
            today=date.today(),
            frozen_from=membership.frozen_from,
            frozen_until=membership.frozen_until,
        )
        eligible = status in ELIGIBLE_MEMBERSHIP_STATUSES
        return membership, status, eligible, None if eligible else membership_access_message(status)

    async def create_freeze_request(
        self,
        *,
        user: User,
        payload: FreezeRequestCreate,
    ) -> MembershipRequestItem:
        if payload.requested_start_date < date.today():
            raise AppError("FREEZE_START_IN_PAST", "A freeze cannot start in the past.", 400)
        membership = await self.operations.get_current_for_update(user.id)
        if not membership:
            raise AppError("MEMBERSHIP_REQUIRED", "A membership is required to request a freeze.", 409)
        effective = derive_membership_status(
            stored_status=membership.status,
            is_email_verified=user.is_email_verified,
            expiry_date=membership.expiry_date,
            today=date.today(),
            frozen_from=membership.frozen_from,
            frozen_until=membership.frozen_until,
        )
        if effective not in ELIGIBLE_MEMBERSHIP_STATUSES:
            raise ConflictError("Only active or expiring-soon memberships can be frozen.", {"status": effective})
        try:
            request = await self.operations.create_freeze_request(
                membership=membership,
                start_date=payload.requested_start_date,
                end_date=payload.requested_end_date,
                reason=payload.reason.strip(),
            )
            await self.audit.create(
                actor_user_id=user.id,
                target_user_id=user.id,
                action="membership.freeze.requested",
                entity_type="membership_freeze_request",
                entity_id=str(request.id),
                reason=request.reason,
                summary="Member submitted a membership freeze request.",
            )
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ConflictError("An open freeze request already exists for this membership.") from exc
        return self._freeze_item(request)

    async def decide_freeze_request(
        self,
        *,
        request_id: UUID,
        reviewer: User,
        payload: FreezeDecision,
    ) -> MembershipRequestItem:
        request = await self.operations.get_freeze_request_for_update(request_id)
        if not request:
            raise ResourceNotFoundError("Freeze request was not found.")
        if request.status != "pending":
            raise ConflictError("This freeze request has already been decided.")
        membership = await self._membership_for_update(request.membership_id)
        now = datetime.now(UTC)
        request.status = "approved" if payload.approve else "rejected"
        request.reviewer_id = reviewer.id
        request.decision_reason = payload.decision_reason.strip()
        request.reviewed_at = now
        if payload.approve:
            membership.frozen_from = request.requested_start_date
            membership.frozen_until = request.requested_end_date
            membership.status = derive_membership_status(
                stored_status=membership.status,
                is_email_verified=True,
                expiry_date=membership.expiry_date,
                today=date.today(),
                frozen_from=membership.frozen_from,
                frozen_until=membership.frozen_until,
            )
        await self.audit.create(
            actor_user_id=reviewer.id,
            target_user_id=request.user_id,
            action=f"membership.freeze.{request.status}",
            entity_type="membership_freeze_request",
            entity_id=str(request.id),
            reason=request.decision_reason,
            outcome=request.status,
            summary=f"Membership freeze request was {request.status}.",
        )
        await self.session.commit()
        return self._freeze_item(request)

    async def create_cancellation_request(
        self,
        *,
        user: User,
        payload: CancellationRequestCreate,
    ) -> MembershipRequestItem:
        membership = await self.operations.get_current_for_update(user.id)
        if not membership:
            raise ConflictError("There is no cancellable membership on this account.")
        effective = derive_membership_status(
            stored_status=membership.status,
            is_email_verified=user.is_email_verified,
            expiry_date=membership.expiry_date,
            today=date.today(),
            frozen_from=membership.frozen_from,
            frozen_until=membership.frozen_until,
        )
        if effective not in ELIGIBLE_MEMBERSHIP_STATUSES | {MembershipStatus.FROZEN.value}:
            raise ConflictError(
                "There is no cancellable membership on this account.",
                {"status": effective},
            )
        try:
            request = await self.operations.create_cancellation_request(
                membership=membership,
                reason=payload.reason.strip(),
            )
            await self.audit.create(
                actor_user_id=user.id,
                target_user_id=user.id,
                action="membership.cancellation.requested",
                entity_type="membership_cancellation_request",
                entity_id=str(request.id),
                reason=request.reason,
                summary="Member submitted a membership cancellation request.",
            )
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ConflictError("An open cancellation request already exists for this membership.") from exc
        return self._cancellation_item(request)

    async def decide_cancellation_request(
        self,
        *,
        request_id: UUID,
        reviewer: User,
        payload: RequestDecision,
    ) -> MembershipRequestItem:
        request = await self.operations.get_cancellation_request_for_update(request_id)
        if not request:
            raise ResourceNotFoundError("Cancellation request was not found.")
        if request.status != "pending":
            raise ConflictError("This cancellation request has already been decided.")
        membership = await self._membership_for_update(request.membership_id)
        now = datetime.now(UTC)
        request.status = "approved" if payload.approve else "rejected"
        request.outcome = payload.outcome
        request.reviewer_id = reviewer.id
        request.decision_reason = payload.decision_reason.strip()
        request.reviewed_at = now
        if payload.approve:
            membership.status = MembershipStatus.CANCELLED.value
            membership.cancelled_at = now
        await self.audit.create(
            actor_user_id=reviewer.id,
            target_user_id=request.user_id,
            action=f"membership.cancellation.{request.status}",
            entity_type="membership_cancellation_request",
            entity_id=str(request.id),
            reason=request.decision_reason,
            outcome=request.outcome or request.status,
            summary=f"Cancellation request was {request.status} with outcome {request.outcome or 'none'}.",
            after_data={"membership_status": membership.status, "financial_outcome": request.outcome},
        )
        await self.session.commit()
        return self._cancellation_item(request)

    async def revoke_membership(self, *, user_id: UUID, reviewer: User, reason: str) -> OperationMessage:
        membership = await self.operations.get_current_for_update(user_id)
        if not membership:
            raise ResourceNotFoundError("Membership was not found.")
        if membership.status == MembershipStatus.REVOKED.value:
            raise ConflictError("This membership is already revoked.")
        before = membership.status
        membership.status = MembershipStatus.REVOKED.value
        membership.revoked_at = datetime.now(UTC)
        membership.revoked_by_id = reviewer.id
        membership.revoked_reason = reason.strip()
        await self.audit.create(
            actor_user_id=reviewer.id,
            target_user_id=user_id,
            action="membership.revoked",
            entity_type="user_membership",
            entity_id=str(membership.id),
            reason=reason.strip(),
            outcome="revoked",
            summary="Membership access was revoked.",
            before_data={"status": before},
            after_data={"status": membership.status},
        )
        await self.session.commit()
        return OperationMessage(message="Membership revoked.", code="MEMBERSHIP_REVOKED")

    async def list_my_requests(self, user: User) -> list[MembershipRequestItem]:
        freezes, cancellations = await self.operations.list_requests_for_user(user.id)
        items = [self._freeze_item(item) for item in freezes]
        items.extend(self._cancellation_item(item) for item in cancellations)
        return sorted(items, key=lambda item: item.created_at, reverse=True)

    async def list_approval_requests(
        self,
        *,
        status: str | None,
        page: int,
        page_size: int,
    ) -> MembershipApprovalPage:
        freezes, cancellations = await self.operations.list_approval_requests(status)
        items = [
            MembershipApprovalItem(
                **self._freeze_item(request).model_dump(),
                user_id=user.id,
                user_name=user.name,
                user_email=user.email,
            )
            for request, user in freezes
        ]
        items.extend(
            MembershipApprovalItem(
                **self._cancellation_item(request).model_dump(),
                user_id=user.id,
                user_name=user.name,
                user_email=user.email,
            )
            for request, user in cancellations
        )
        items.sort(key=lambda item: item.created_at, reverse=True)
        total = len(items)
        start = (page - 1) * page_size
        return MembershipApprovalPage(
            items=items[start:start + page_size],
            page=PageInfo(
                page=page,
                page_size=page_size,
                total=total,
                pages=ceil(total / page_size) if total else 0,
            ),
        )

    async def synchronize_membership_statuses(self) -> int:
        changed = 0
        for membership, verified in await self.operations.list_lifecycle_candidates():
            next_status = derive_membership_status(
                stored_status=membership.status,
                is_email_verified=verified,
                expiry_date=membership.expiry_date,
                today=date.today(),
                frozen_from=membership.frozen_from,
                frozen_until=membership.frozen_until,
            )
            if membership.status != next_status:
                membership.status = next_status
                changed += 1
        await self.session.commit()
        return changed

    async def _membership_for_update(self, membership_id: UUID) -> UserMembership:
        result = await self.session.execute(
            select(UserMembership).where(UserMembership.id == membership_id).with_for_update(),
        )
        membership = result.scalar_one_or_none()
        if not membership:
            raise ResourceNotFoundError("Membership was not found.")
        return membership

    @staticmethod
    def _freeze_item(item: MembershipFreezeRequest) -> MembershipRequestItem:
        return MembershipRequestItem(
            id=item.id,
            membership_id=item.membership_id,
            request_type="freeze",
            status=item.status,
            reason=item.reason,
            decision_reason=item.decision_reason,
            requested_start_date=item.requested_start_date,
            requested_end_date=item.requested_end_date,
            created_at=item.created_at,
            reviewed_at=item.reviewed_at,
        )

    @staticmethod
    def _cancellation_item(item: MembershipCancellationRequest) -> MembershipRequestItem:
        return MembershipRequestItem(
            id=item.id,
            membership_id=item.membership_id,
            request_type="cancellation",
            status=item.status,
            reason=item.reason,
            outcome=item.outcome,
            decision_reason=item.decision_reason,
            created_at=item.created_at,
            reviewed_at=item.reviewed_at,
        )
