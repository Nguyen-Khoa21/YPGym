from datetime import UTC, date, datetime, time, timedelta
from math import ceil
from secrets import SystemRandom, choice
from zoneinfo import ZoneInfo

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import AppError, ConflictError
from app.models.enums import MemberTier
from app.models.user import User
from app.repositories.class_repository import ClassRepository
from app.repositories.operations_repository import AuditRepository
from app.repositories.staff_repository import StaffRepository
from app.repositories.user_repository import UserRepository
from app.schemas.operations_schema import PageInfo
from app.schemas.staff_schema import (
    MyStaffShifts,
    StaffAccountCreate,
    StaffAccountCreated,
    StaffAccountItem,
    StaffAccountPage,
    StaffShiftItem,
    StaffShiftPage,
)
from app.utils.security import hash_password


class StaffOperationsService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.staff = StaffRepository(session)
        self.trainers = ClassRepository(session)
        self.audit = AuditRepository(session)
        self.settings = get_settings()

    async def create_account(self, *, actor: User, payload: StaffAccountCreate) -> StaffAccountCreated:
        email = f"{payload.login_name}@{self.settings.STAFF_ACCOUNT_EMAIL_DOMAIN}"
        if await self.users.get_by_email(email):
            raise ConflictError("That staff login name is already in use.")
        if payload.phone and await self.users.get_by_phone(payload.phone):
            raise ConflictError("That phone number is already in use.")
        temporary_password = self._temporary_password()
        try:
            user = await self.users.create(
                name=payload.name,
                email=email,
                phone=payload.phone,
                password_hash=hash_password(temporary_password),
                role=payload.role,
                tier=MemberTier.NORMAL.value,
                is_email_verified=True,
                must_change_password=True,
            )
            user.email_verified_at = datetime.now(UTC)
            trainer_profile_id = None
            if payload.role == "pt":
                trainer = await self.trainers.create_trainer(
                    user_id=user.id,
                    display_name=user.name,
                    is_active=True,
                )
                trainer_profile_id = trainer.id
            await self.audit.create(
                actor_user_id=actor.id,
                target_user_id=user.id,
                action="staff_account.created",
                entity_type="user",
                entity_id=str(user.id),
                reason="Manager-provisioned workforce account",
                outcome="created",
                summary=f"A distinct {user.role} account was created.",
                after_data={
                    "email": user.email,
                    "role": user.role,
                    "must_change_password": True,
                    "trainer_profile_id": str(trainer_profile_id) if trainer_profile_id else None,
                },
            )
            await self.session.commit()
            await self.session.refresh(user)
        except IntegrityError as exc:
            await self.session.rollback()
            raise ConflictError("The staff account conflicts with an existing login or phone number.") from exc
        return StaffAccountCreated(
            account=self._account_item(user, trainer_profile_id),
            temporary_password=temporary_password,
            message="Copy the temporary password now. It is not stored or shown again.",
        )

    async def list_accounts(
        self,
        *,
        page: int,
        page_size: int,
        search: str | None,
        role: str | None,
    ) -> StaffAccountPage:
        rows, total = await self.staff.list_accounts(
            page=page,
            page_size=page_size,
            search=search,
            role=role,
        )
        return StaffAccountPage(
            items=[self._account_item(user, trainer_id) for user, trainer_id in rows],
            page=PageInfo(
                page=page,
                page_size=page_size,
                total=total,
                pages=ceil(total / page_size) if total else 0,
            ),
            internal_email_domain=self.settings.STAFF_ACCOUNT_EMAIL_DOMAIN,
        )

    async def clock_in(self, *, user: User) -> StaffShiftItem:
        await self.users.get_by_id_for_update(user.id)
        if await self.staff.open_shift(user.id):
            raise ConflictError("You already have an open shift.")
        now = datetime.now(UTC)
        try:
            shift = await self.staff.create_shift(user_id=user.id, clocked_in_at=now)
            await self.audit.create(
                actor_user_id=user.id,
                target_user_id=user.id,
                action="staff_shift.clocked_in",
                entity_type="staff_shift",
                entity_id=str(shift.id),
                reason="Self-service staff time clock",
                outcome="open",
                summary="Staff member clocked in.",
                after_data={"clocked_in_at": now.isoformat()},
            )
            await self.session.commit()
            await self.session.refresh(shift)
        except IntegrityError as exc:
            await self.session.rollback()
            raise ConflictError("You already have an open shift.") from exc
        return self._shift_item(shift, user, now=now)

    async def clock_out(self, *, user: User) -> StaffShiftItem:
        await self.users.get_by_id_for_update(user.id)
        shift = await self.staff.open_shift(user.id, for_update=True)
        if not shift:
            raise ConflictError("You do not have an open shift.")
        now = datetime.now(UTC)
        shift.clocked_out_at = now
        await self.audit.create(
            actor_user_id=user.id,
            target_user_id=user.id,
            action="staff_shift.clocked_out",
            entity_type="staff_shift",
            entity_id=str(shift.id),
            reason="Self-service staff time clock",
            outcome="closed",
            summary="Staff member clocked out.",
            before_data={"clocked_out_at": None},
            after_data={"clocked_out_at": now.isoformat()},
        )
        await self.session.commit()
        await self.session.refresh(shift)
        return self._shift_item(shift, user, now=now)

    async def my_shifts(self, *, user: User) -> MyStaffShifts:
        shifts = await self.staff.recent_shifts(user.id)
        items = [self._shift_item(shift, user) for shift in shifts]
        return MyStaffShifts(
            open_shift=next((item for item in items if item.status == "open"), None),
            recent_shifts=items,
            gym_timezone=self.settings.GYM_TIMEZONE,
        )

    async def list_shifts(
        self,
        *,
        page: int,
        page_size: int,
        search: str | None,
        role: str | None,
        status: str | None,
        date_from: date | None,
        date_to: date | None,
    ) -> StaffShiftPage:
        if date_from and date_to and date_from > date_to:
            raise AppError("INVALID_DATE_RANGE", "The start date must not be after the end date.", 422)
        timezone = ZoneInfo(self.settings.GYM_TIMEZONE)
        date_from_utc = (
            datetime.combine(date_from, time.min, tzinfo=timezone).astimezone(UTC)
            if date_from
            else None
        )
        date_to_exclusive_utc = (
            datetime.combine(date_to + timedelta(days=1), time.min, tzinfo=timezone).astimezone(UTC)
            if date_to
            else None
        )
        rows, total = await self.staff.list_shifts(
            page=page,
            page_size=page_size,
            search=search,
            role=role,
            status=status,
            date_from=date_from_utc,
            date_to_exclusive=date_to_exclusive_utc,
        )
        return StaffShiftPage(
            items=[self._shift_item(shift, user) for shift, user in rows],
            page=PageInfo(
                page=page,
                page_size=page_size,
                total=total,
                pages=ceil(total / page_size) if total else 0,
            ),
            gym_timezone=self.settings.GYM_TIMEZONE,
        )

    @staticmethod
    def _temporary_password() -> str:
        characters = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789!@#$%*-_"
        password = [choice("ABCDEFGHJKLMNPQRSTUVWXYZ"), choice("abcdefghijkmnopqrstuvwxyz"), choice("23456789"), choice("!@#$%*-_")]
        password.extend(choice(characters) for _ in range(16))
        SystemRandom().shuffle(password)
        return "".join(password)

    @staticmethod
    def _account_item(user: User, trainer_profile_id) -> StaffAccountItem:
        return StaffAccountItem(
            id=user.id,
            name=user.name,
            email=user.email,
            phone=user.phone,
            role=user.role,
            must_change_password=user.must_change_password,
            trainer_profile_id=trainer_profile_id,
            created_at=user.created_at,
        )

    @staticmethod
    def _shift_item(shift, user: User, *, now: datetime | None = None) -> StaffShiftItem:
        end = shift.clocked_out_at or now or datetime.now(UTC)
        duration_minutes = max(0, int((end - shift.clocked_in_at).total_seconds() // 60))
        return StaffShiftItem(
            id=shift.id,
            user_id=user.id,
            staff_name=user.name,
            staff_email=user.email,
            role=user.role,
            clocked_in_at=shift.clocked_in_at,
            clocked_out_at=shift.clocked_out_at,
            duration_minutes=duration_minutes,
            status="closed" if shift.clocked_out_at else "open",
        )
