from collections.abc import Callable
from typing import Annotated
from uuid import UUID

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationError, PermissionDeniedError
from app.db.session import get_db_session
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.utils.security import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> User:
    payload = decode_access_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise AuthenticationError("The access token is invalid.")

    try:
        parsed_user_id = UUID(user_id)
    except ValueError as exc:
        raise AuthenticationError("The access token is invalid.") from exc

    user = await UserRepository(session).get_by_id(parsed_user_id)
    if not user:
        raise AuthenticationError("The authenticated user could not be found.")

    return user


def require_roles(*allowed_roles: str) -> Callable[[User], User]:
    async def role_dependency(
        current_user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        if current_user.role not in allowed_roles:
            raise PermissionDeniedError()
        return current_user

    return role_dependency
