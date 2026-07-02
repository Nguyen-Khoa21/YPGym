import asyncio
from decimal import Decimal

from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import AsyncSessionLocal
from app.models.membership import MembershipPlan
from app.models.system_configuration import SystemConfiguration


PLAN_SEEDS = [
    {
        "name": "1 Month",
        "duration_months": 1,
        "duration_days": 30,
        "base_price": Decimal("120.00"),
        "discount_percent": Decimal("0.00"),
        "benefits": "Gym floor access\nMember dashboard\nInvoice history",
        "display_order": 1,
    },
    {
        "name": "3 Months",
        "duration_months": 3,
        "duration_days": 90,
        "base_price": Decimal("330.00"),
        "discount_percent": Decimal("5.00"),
        "benefits": "Gym floor access\nMember dashboard\nPriority renewal reminder",
        "display_order": 2,
    },
    {
        "name": "6 Months",
        "duration_months": 6,
        "duration_days": 180,
        "base_price": Decimal("600.00"),
        "discount_percent": Decimal("10.00"),
        "benefits": "Gym floor access\nMember dashboard\nRenewal savings",
        "display_order": 3,
    },
    {
        "name": "1 Year",
        "duration_months": 12,
        "duration_days": 365,
        "base_price": Decimal("1080.00"),
        "discount_percent": Decimal("15.00"),
        "benefits": "Gym floor access\nBest annual value\nInvoice history",
        "display_order": 4,
    },
    {
        "name": "2 Years",
        "duration_months": 24,
        "duration_days": 730,
        "base_price": Decimal("1980.00"),
        "discount_percent": Decimal("20.00"),
        "benefits": "Long-term membership rate\nMember dashboard\nRenewal savings",
        "display_order": 5,
    },
    {
        "name": "3 Years",
        "duration_months": 36,
        "duration_days": 1095,
        "base_price": Decimal("2700.00"),
        "discount_percent": Decimal("25.00"),
        "benefits": "Largest plan discount\nMember dashboard\nInvoice history",
        "display_order": 6,
    },
]


async def seed_development_data() -> None:
    settings = get_settings()
    configuration_seeds = [
        ("gym_capacity", str(settings.GYM_CAPACITY), "integer", "Maximum gym capacity."),
        ("qr_token_ttl_seconds", str(settings.QR_TOKEN_TTL_SECONDS), "integer", "QR token time-to-live."),
        (
            "attendance_timeout_minutes",
            str(settings.ATTENDANCE_TIMEOUT_MINUTES),
            "integer",
            "Attendance session timeout.",
        ),
        ("duplicate_scan_window_seconds", "30", "integer", "Duplicate QR scan guard window."),
        ("class_cancellation_window_hours", "12", "integer", "Member class cancellation window."),
        ("waitlist_size", "10", "integer", "Default class waitlist size."),
    ]

    async with AsyncSessionLocal() as session:
        for plan_data in PLAN_SEEDS:
            result = await session.execute(
                select(MembershipPlan).where(MembershipPlan.name == plan_data["name"]),
            )
            plan = result.scalar_one_or_none()
            if plan:
                for key, value in plan_data.items():
                    setattr(plan, key, value)
                plan.is_active = True
            else:
                session.add(MembershipPlan(**plan_data))

        for key, value, value_type, description in configuration_seeds:
            result = await session.execute(
                select(SystemConfiguration).where(SystemConfiguration.key == key),
            )
            config = result.scalar_one_or_none()
            if config:
                config.value = value
                config.value_type = value_type
                config.description = description
            else:
                session.add(
                    SystemConfiguration(
                        key=key,
                        value=value,
                        value_type=value_type,
                        description=description,
                    ),
                )

        await session.commit()


if __name__ == "__main__":
    asyncio.run(seed_development_data())
