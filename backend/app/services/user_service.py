from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth_schema import UserPublic
from app.schemas.user_schema import UserProfileUpdateRequest
from app.utils.security import hash_password, verify_password


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)

    async def update_profile(
        self,
        *,
        current_user: User,
        payload: UserProfileUpdateRequest,
    ) -> UserPublic:
        if payload.email and payload.email.lower() != current_user.email.lower():
            raise AppError(
                "EMAIL_CHANGE_NOT_ENABLED",
                "Email changes will require a re-verification flow and are not enabled yet.",
                400,
            )

        if payload.phone and payload.phone != current_user.phone:
            existing_phone = await self.users.get_by_phone(payload.phone)
            if existing_phone and existing_phone.id != current_user.id:
                raise AppError(
                    "PHONE_ALREADY_EXISTS",
                    "This phone number is already used by another account.",
                    409,
                )
            current_user.phone = payload.phone

        if payload.name:
            current_user.name = payload.name.strip()

        if payload.new_password:
            if not payload.current_password or not verify_password(
                payload.current_password,
                current_user.password_hash,
            ):
                raise AppError(
                    "CURRENT_PASSWORD_INCORRECT",
                    "The current password is incorrect.",
                    400,
                )
            current_user.password_hash = hash_password(payload.new_password)

        # TODO: write a profile-change audit log once the audit table is introduced.
        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise AppError(
                "PROFILE_UPDATE_CONFLICT",
                "The profile could not be updated because a value is already used.",
                409,
            ) from exc

        await self.session.refresh(current_user)
        return UserPublic.model_validate(current_user)
