from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.membership_repository import MembershipPlanRepository
from app.schemas.membership_schema import MembershipPlanResponse


class MembershipPlanService:
    def __init__(self, session: AsyncSession) -> None:
        self.plans = MembershipPlanRepository(session)

    async def list_active_plans(self) -> list[MembershipPlanResponse]:
        plans = await self.plans.list_active()
        return [self._to_response(plan) for plan in plans]

    def _to_response(self, plan) -> MembershipPlanResponse:
        discount_amount = (
            plan.base_price * plan.discount_percent / Decimal("100")
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        final_price = (plan.base_price - discount_amount).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )
        benefits = [
            item.strip()
            for item in (plan.benefits or "").splitlines()
            if item.strip()
        ]
        return MembershipPlanResponse(
            id=plan.id,
            name=plan.name,
            duration_months=plan.duration_months,
            duration_days=plan.duration_days,
            base_price=plan.base_price,
            discount_percent=plan.discount_percent,
            final_price=final_price,
            is_active=plan.is_active,
            tier_availability=plan.tier_availability,
            benefits=benefits,
        )
