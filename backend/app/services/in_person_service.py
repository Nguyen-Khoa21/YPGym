"""Staff-assisted registration and payment for walk-in members.

Every gym decision is made on the server from the actor's assignment; the client never chooses the
gym for staff or managers, and never supplies an amount.
"""
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError, PermissionDeniedError, ResourceNotFoundError
from app.models.enums import MemberTier, UserRole
from app.models.user import User
from app.repositories.billing_repository import PaymentRepository
from app.repositories.gym_repository import GymRepository
from app.repositories.membership_repository import UserMembershipRepository
from app.repositories.operations_repository import AuditRepository
from app.repositories.user_repository import UserRepository
from app.schemas.membership_schema import PurchaseMembershipRequest, PurchaseMembershipResponse
from app.schemas.payment_schema import PayOSCreateRequest, PayOSCreateResponse
from app.schemas.staff_schema import (
    InPersonMemberItem,
    InPersonMemberRegister,
    InPersonMemberRegistered,
    StaffMembershipPaymentRequest,
    StaffPaymentStatus,
)
from app.services.auth_service import AuthService
from app.services.gym_service import GymScopeService
from app.services.membership_service import MembershipService
from app.services.payment_service import PayOSPaymentService
from app.services.shift_guard import ShiftGuard
from app.services.staff_service import StaffOperationsService
from app.utils.security import hash_password

STAFF_QR_KEY_PREFIX = "staff-qr:"


class InPersonMemberService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.gym_scope = GymScopeService(session)
        self.gyms = GymRepository(session)
        self.audit = AuditRepository(session)
        self.memberships = UserMembershipRepository(session)
        self.payments = PaymentRepository(session)

    async def register(self, *, actor: User, payload: InPersonMemberRegister) -> InPersonMemberRegistered:
        await ShiftGuard(self.session).require_open_shift(actor)
        gym = await self._actor_gym(actor, payload.gym_id)
        email = payload.email.lower()
        phone = payload.phone.strip()
        await AuthService(self.session).ensure_identity_available(email=email, phone=phone)

        temporary_password = StaffOperationsService._temporary_password()
        try:
            member = await self.users.create(
                name=payload.name.strip(),
                email=email,
                phone=phone,
                password_hash=hash_password(temporary_password),
                role=UserRole.MEMBER.value,
                tier=MemberTier.NORMAL.value,
                is_email_verified=True,
                must_change_password=True,
            )
            member.email_verified_at = datetime.now(UTC)
            member.registration_channel = "in_person"
            member.registered_by_user_id = actor.id
            await self.audit.create(
                actor_user_id=actor.id,
                target_user_id=member.id,
                action="member.registered_in_person",
                entity_type="user",
                entity_id=str(member.id),
                reason="Walk-in member registered at the gym",
                outcome="created",
                summary=f"A member account was registered in person at {gym.name}.",
                after_data={"registration_channel": "in_person", "gym_id": str(gym.id)},
            )
            await self.session.commit()
            await self.session.refresh(member)
        except IntegrityError as exc:
            await self.session.rollback()
            raise AppError(
                "REGISTRATION_CONFLICT",
                "The account could not be registered because the email or phone is already used.",
                409,
            ) from exc
        return InPersonMemberRegistered(
            member=InPersonMemberItem(
                id=member.id, name=member.name, email=member.email, phone=member.phone,
                gym_id=gym.id, gym_name=gym.name,
            ),
            temporary_password=temporary_password,
            message="Give the member this temporary password now. It is not stored or shown again.",
        )

    async def create_qr_checkout(
        self, *, actor: User, user_id: UUID, payload: StaffMembershipPaymentRequest,
    ) -> PayOSCreateResponse:
        await ShiftGuard(self.session).require_open_shift(actor)
        target = await self._serviceable_member(actor, user_id)
        checkout = await PayOSPaymentService(self.session).create_payment(
            user=target,
            actor=actor,
            idempotency_key=payload.idempotency_key,
            payload=PayOSCreateRequest(
                membership_plan_id=payload.plan_id,
                gym_id=payload.gym_id,
                client_platform="web",
            ),
        )
        await self.audit.create(
            actor_user_id=actor.id,
            target_user_id=target.id,
            action="member.qr_checkout.created",
            entity_type="payment",
            entity_id=str(checkout.transaction_id),
            reason="QR checkout created for a walk-in member",
            outcome="pending",
            summary=f"Staff created a payOS QR checkout at {checkout.gym_name}.",
        )
        await self.session.commit()
        return checkout

    async def record_cash(
        self, *, actor: User, user_id: UUID, payload: StaffMembershipPaymentRequest,
    ) -> PurchaseMembershipResponse:
        await ShiftGuard(self.session).require_open_shift(actor)
        target = await self._serviceable_member(actor, user_id)
        gym = await self._actor_gym(actor, payload.gym_id)
        return await MembershipService(self.session).purchase(
            current_user=target,
            actor=actor,
            cash=True,
            manual_reason=f"Cash payment received at {gym.name}",
            payload=PurchaseMembershipRequest(
                plan_id=payload.plan_id,
                gym_id=gym.id,
                idempotency_key=payload.idempotency_key,
                mock_payment_confirmed=True,
            ),
        )

    async def payment_status(self, *, actor: User, payment_id: UUID) -> StaffPaymentStatus:
        await ShiftGuard(self.session).require_open_shift(actor)
        payment = await self.payments.get_by_id(payment_id)
        not_found = ResourceNotFoundError("Payment was not found.")
        if (
            payment is None
            or payment.provider != "payos"
            or not payment.idempotency_key.startswith(STAFF_QR_KEY_PREFIX)
        ):
            raise not_found
        if actor.role != "admin" and payment.gym_id != await self.gym_scope.effective_gym_id(user=actor):
            raise not_found
        member = await self.users.get_by_id(payment.user_id)
        return StaffPaymentStatus(
            id=payment.id,
            status=payment.status,
            member_name=member.name if member else "",
            plan_name=payment.plan.name if payment.plan else None,
            gym_name=payment.gym.name,
        )

    async def _actor_gym(self, actor: User, requested_gym_id: UUID | None):
        gym_id = await self.gym_scope.resolve_gym_id(user=actor, requested_gym_id=requested_gym_id)
        gym = await self.gyms.get_location(gym_id, active_only=True)
        if gym is None:
            raise ResourceNotFoundError("The gym location was not found or is inactive.")
        return gym

    async def _serviceable_member(self, actor: User, user_id: UUID) -> User:
        target = await self.users.get_by_id(user_id)
        if target is None or target.role != UserRole.MEMBER.value:
            raise ResourceNotFoundError("Member was not found.")
        if actor.role == "admin":
            return target
        # Staff and managers serve walk-ins they can see at their own gym, not other gyms' members.
        if target.registration_channel != "in_person":
            raise ResourceNotFoundError("Member was not found.")
        latest = await self.memberships.get_latest_for_user(target.id)
        if latest is not None and latest.home_gym_id != await self.gym_scope.effective_gym_id(user=actor):
            raise PermissionDeniedError("This member belongs to another gym location.")
        return target
