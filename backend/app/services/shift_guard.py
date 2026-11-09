from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.models.user import User
from app.repositories.staff_repository import StaffRepository
from app.services.gym_service import GymScopeService


class ShiftGuard:
    """Staff may run attendance operations only while clocked in at their current assigned gym.

    Managers and owners are never gated. One reusable check keeps every gated endpoint identical.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def require_open_shift(self, user: User) -> None:
        if user.role != "staff":
            return
        assigned_gym_id = await GymScopeService(self.session).effective_gym_id(user=user)
        shift = await StaffRepository(self.session).open_shift(user.id)
        if shift is None or shift.gym_id != assigned_gym_id:
            raise AppError(
                "SHIFT_REQUIRED",
                "Clock in at your gym before using attendance operations.",
                403,
            )
