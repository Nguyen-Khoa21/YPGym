from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, user_id: UUID) -> User | None:
        return await self.session.get(User, user_id)

    async def get_by_email(self, email: str) -> User | None:
        result = await self.session.execute(
            select(User).where(func.lower(User.email) == email.lower()),
        )
        return result.scalar_one_or_none()

    async def get_by_phone(self, phone: str) -> User | None:
        result = await self.session.execute(select(User).where(User.phone == phone))
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        name: str,
        email: str,
        phone: str,
        password_hash: str,
        role: str,
        tier: str,
        is_email_verified: bool = False,
    ) -> User:
        user = User(
            name=name,
            email=email,
            phone=phone,
            password_hash=password_hash,
            role=role,
            tier=tier,
            is_email_verified=is_email_verified,
        )
        self.session.add(user)
        await self.session.flush()
        return user
