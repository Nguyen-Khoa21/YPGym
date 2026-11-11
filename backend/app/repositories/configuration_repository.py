from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.system_configuration import SystemConfiguration


class ConfigurationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, key: str) -> SystemConfiguration | None:
        return (
            await self.session.execute(
                select(SystemConfiguration).where(SystemConfiguration.key == key),
            )
        ).scalar_one_or_none()

    async def list_keys(self, keys: tuple[str, ...]) -> list[SystemConfiguration]:
        return list(
            (
                await self.session.execute(
                    select(SystemConfiguration)
                    .where(SystemConfiguration.key.in_(keys))
                    .order_by(SystemConfiguration.key),
                )
            ).scalars().all(),
        )
