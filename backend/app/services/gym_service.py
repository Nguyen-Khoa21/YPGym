from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError, ConflictError, PermissionDeniedError, ResourceNotFoundError
from app.models.gym import GymLocation
from app.models.user import User
from app.repositories.gym_repository import GymRepository
from app.repositories.membership_repository import UserMembershipRepository
from app.repositories.operations_repository import AuditRepository
from app.repositories.user_repository import UserRepository
from app.schemas.gym_schema import (
    GymLocationCreate,
    GymLocationItem,
    GymLocationUpdate,
    WorkforceAssignmentCreate,
    WorkforceAssignmentItem,
)


class GymLocationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.gyms = GymRepository(session)
        self.audit = AuditRepository(session)

    async def list_active(self) -> list[GymLocationItem]:
        return [GymLocationItem.model_validate(item) for item in await self.gyms.list_locations(active_only=True)]

    async def get_active(self, gym_id: UUID) -> GymLocationItem:
        return GymLocationItem.model_validate(await self._get(gym_id, active_only=True))

    async def list_admin(self) -> list[GymLocationItem]:
        return [GymLocationItem.model_validate(item) for item in await self.gyms.list_locations(active_only=False)]

    async def create(self, *, actor: User, payload: GymLocationCreate) -> GymLocationItem:
        if await self.gyms.get_by_slug(payload.slug):
            raise ConflictError("A gym location with this slug already exists.")
        location = await self.gyms.create_location(**payload.model_dump())
        await self.audit.create(
            actor_user_id=actor.id,
            action="gym_location.created",
            entity_type="gym_location",
            entity_id=str(location.id),
            outcome="active" if location.is_active else "inactive",
            summary=f"Gym location '{location.name}' was created.",
            after_data=self._audit_data(location),
        )
        await self.session.commit()
        await self.session.refresh(location)
        return GymLocationItem.model_validate(location)

    async def update(self, *, gym_id: UUID, actor: User, payload: GymLocationUpdate) -> GymLocationItem:
        location = await self._get(gym_id)
        changes = payload.model_dump(exclude_unset=True)
        if "slug" in changes and changes["slug"] != location.slug:
            existing = await self.gyms.get_by_slug(changes["slug"])
            if existing:
                raise ConflictError("A gym location with this slug already exists.")
        before = self._audit_data(location)
        for key, value in changes.items():
            setattr(location, key, value)
        await self.session.flush()
        await self.audit.create(
            actor_user_id=actor.id,
            action="gym_location.updated",
            entity_type="gym_location",
            entity_id=str(location.id),
            outcome="active" if location.is_active else "inactive",
            summary=f"Gym location '{location.name}' was updated.",
            before_data=before,
            after_data=self._audit_data(location),
        )
        await self.session.commit()
        await self.session.refresh(location)
        return GymLocationItem.model_validate(location)

    async def assign_workforce(
        self,
        *,
        actor: User,
        payload: WorkforceAssignmentCreate,
    ) -> WorkforceAssignmentItem:
        gym = await self._get(payload.gym_id, active_only=True)
        user = await UserRepository(self.session).get_by_id_for_update(payload.user_id)
        if not user:
            raise ResourceNotFoundError("The workforce account could not be found.")
        if user.role not in {"manager", "staff", "pt"}:
            raise AppError(
                "INVALID_WORKFORCE_ROLE",
                "Only manager, staff, and personal-trainer accounts can be assigned to a gym.",
                422,
            )
        previous = await self.gyms.active_assignment(user.id)
        assignment = await self.gyms.assign(user=user, gym=gym)
        await self.audit.create(
            actor_user_id=actor.id,
            target_user_id=user.id,
            action="workforce_gym_assignment.updated",
            entity_type="workforce_gym_assignment",
            entity_id=str(assignment.id),
            outcome="active",
            summary=f"{user.name} was assigned to {gym.name}.",
            before_data={"gym_id": str(previous.gym_id)} if previous else None,
            after_data={"gym_id": str(gym.id), "assigned_role": user.role},
        )
        await self.session.commit()
        await self.session.refresh(assignment)
        return self._assignment_item(assignment, user, gym)

    async def list_assignments(self, *, gym_id: UUID | None = None) -> list[WorkforceAssignmentItem]:
        if gym_id is not None:
            await self._get(gym_id)
        return [self._assignment_item(*row) for row in await self.gyms.list_assignments(gym_id=gym_id)]

    async def _get(self, gym_id: UUID, *, active_only: bool = False) -> GymLocation:
        location = await self.gyms.get_location(gym_id, active_only=active_only)
        if not location:
            raise ResourceNotFoundError("The gym location could not be found.")
        return location

    @staticmethod
    def _audit_data(location: GymLocation) -> dict[str, object]:
        return {
            "name": location.name,
            "slug": location.slug,
            "district": location.district,
            "timezone": location.timezone,
            "capacity": location.capacity,
            "is_active": location.is_active,
        }

    @staticmethod
    def _assignment_item(assignment, user: User, gym: GymLocation) -> WorkforceAssignmentItem:
        return WorkforceAssignmentItem(
            id=assignment.id,
            user_id=user.id,
            user_name=user.name,
            user_email=user.email,
            gym_id=gym.id,
            gym_name=gym.name,
            assigned_role=assignment.assigned_role,
            is_active=assignment.is_active,
            created_at=assignment.created_at,
        )


class GymScopeService:
    def __init__(self, session: AsyncSession) -> None:
        self.gyms = GymRepository(session)
        self.memberships = UserMembershipRepository(session)

    async def require_access(self, *, user: User, requested_gym_id: UUID) -> GymLocation:
        gym = await self.gyms.get_location(requested_gym_id, active_only=True)
        if not gym:
            raise ResourceNotFoundError("The gym location could not be found.")
        if user.role == "admin":
            return gym
        effective_gym_id = await self.effective_gym_id(user=user)
        if effective_gym_id != gym.id:
            raise PermissionDeniedError("You do not have access to this gym location.")
        return gym

    async def effective_gym_id(self, *, user: User) -> UUID:
        if user.role in {"manager", "staff", "pt"}:
            assignment = await self.gyms.active_assignment(user.id)
            if not assignment:
                raise AppError(
                    "GYM_ASSIGNMENT_REQUIRED",
                    "This workforce account does not have an active gym assignment.",
                    403,
                )
            return assignment.gym_id
        if user.role == "member":
            membership = await self.memberships.get_latest_for_user(user.id)
            if not membership:
                raise AppError(
                    "GYM_MEMBERSHIP_REQUIRED",
                    "This member does not have a gym-linked membership.",
                    403,
                )
            return membership.home_gym_id
        raise AppError("GYM_SCOPE_REQUIRED", "Select a gym location for this operation.", 422)
