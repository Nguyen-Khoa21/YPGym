import asyncio
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import AsyncSessionLocal
from app.models.attendance import AttendanceEvent, AttendanceSession, IoTDevice
from app.models.billing import Invoice, Payment
from app.models.classes import GymClass, PersonalTrainer
from app.models.membership import MembershipPlan, UserMembership
from app.models.operations import BroadcastAnnouncement, Notification, NotificationPreference
from app.models.system_configuration import SystemConfiguration
from app.models.user import User
from app.services.invoice_service import InvoicePdfService
from app.utils.security import hash_password, hash_token


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

DEMO_USERS = [
    ("admin@ypgym.dev", "YPGym Admin", "+66000000001", "admin", "vip"),
    ("manager@ypgym.dev", "YPGym Manager", "+66000000002", "manager", "advance"),
    ("staff@ypgym.dev", "YPGym Staff", "+66000000003", "staff", "normal"),
    ("pt@ypgym.dev", "Jordan Trainer", "+66000000004", "pt", "advance"),
    ("member@ypgym.dev", "Maya Member", "+66000000005", "member", "vip"),
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
        # `.local` is rejected by the API's strict EmailStr validation. Preserve
        # existing development rows and their history while migrating them to a
        # syntactically valid, non-production demo domain.
        for email, *_ in DEMO_USERS:
            legacy_email = email.replace("@ypgym.dev", "@ypgym.local")
            current = (await session.execute(select(User).where(User.email == email))).scalar_one_or_none()
            legacy = (await session.execute(select(User).where(User.email == legacy_email))).scalar_one_or_none()
            if legacy and not current:
                legacy.email = email
        await session.flush()

        plans: dict[str, MembershipPlan] = {}
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
                plan = MembershipPlan(**plan_data)
                session.add(plan)
            plans[plan_data["name"]] = plan

        for key, value, value_type, description in configuration_seeds:
            result = await session.execute(
                select(SystemConfiguration).where(SystemConfiguration.key == key),
            )
            config = result.scalar_one_or_none()
            if config:
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

        await session.flush()

        users: dict[str, User] = {}
        for email, name, phone, role, tier in DEMO_USERS:
            user = (
                await session.execute(select(User).where(User.email == email))
            ).scalar_one_or_none()
            if not user:
                user = User(
                    name=name,
                    email=email,
                    phone=phone,
                    password_hash=hash_password(settings.DEVELOPMENT_SEED_PASSWORD),
                    role=role,
                    tier=tier,
                    is_email_verified=True,
                    email_verified_at=datetime.now(UTC),
                )
                session.add(user)
                await session.flush()
            users[role] = user

            preferences = (
                await session.execute(
                    select(NotificationPreference).where(NotificationPreference.user_id == user.id),
                )
            ).scalar_one_or_none()
            if not preferences:
                session.add(NotificationPreference(user_id=user.id))

        member = users["member"]
        membership = (
            await session.execute(
                select(UserMembership)
                .where(UserMembership.user_id == member.id)
                .order_by(UserMembership.expiry_date.desc()),
            )
        ).scalars().first()
        if not membership:
            membership = UserMembership(
                user_id=member.id,
                plan_id=plans["1 Year"].id,
                status="active",
                start_date=date.today() - timedelta(days=45),
                expiry_date=date.today() + timedelta(days=320),
            )
            session.add(membership)
            await session.flush()

        seeded_payment = (
            await session.execute(
                select(Payment).where(
                    Payment.user_id == member.id,
                    Payment.idempotency_key == "development-seed-payment-v1",
                ),
            )
        ).scalar_one_or_none()
        if not seeded_payment:
            seeded_payment = Payment(
                user_id=member.id,
                membership_id=membership.id,
                plan_id=plans["1 Year"].id,
                idempotency_key="development-seed-payment-v1",
                amount=Decimal("918.00"),
                discount_amount=Decimal("162.00"),
                status="succeeded",
                mock_reference="MOCK-DEVELOPMENT-SEED",
            )
            session.add(seeded_payment)
            await session.flush()

        seeded_invoice = (
            await session.execute(select(Invoice).where(Invoice.payment_id == seeded_payment.id))
        ).scalar_one_or_none()
        if not seeded_invoice:
            transaction_date = datetime.now(UTC)
            invoice_pdf = InvoicePdfService()
            invoice_number = invoice_pdf.build_invoice_number(seeded_payment.id, transaction_date)
            pdf_path = invoice_pdf.generate_pdf(
                invoice_number=invoice_number,
                member_name=member.name,
                member_email=member.email,
                plan_name="1 Year",
                amount=seeded_payment.amount,
                discount_amount=seeded_payment.discount_amount,
                transaction_date=transaction_date,
                membership_start_date=membership.start_date,
                membership_expiry_date=membership.expiry_date,
            )
            session.add(
                Invoice(
                    invoice_number=invoice_number,
                    user_id=member.id,
                    payment_id=seeded_payment.id,
                    plan_name="1 Year",
                    amount=seeded_payment.amount,
                    discount_amount=seeded_payment.discount_amount,
                    transaction_date=transaction_date,
                    membership_start_date=membership.start_date,
                    membership_expiry_date=membership.expiry_date,
                    pdf_path=str(pdf_path),
                ),
            )

        seeded_notification = (
            await session.execute(
                select(Notification).where(Notification.dedupe_key == "development-welcome-v1"),
            )
        ).scalar_one_or_none()
        if not seeded_notification:
            session.add(
                Notification(
                    user_id=member.id,
                    category="operations",
                    notification_type="welcome",
                    title="Your operations demo is ready",
                    message="Your rotating QR pass, attendance history and membership request workflows are connected.",
                    channel="in_app",
                    delivery_state="delivered",
                    delivered_at=datetime.now(UTC),
                    dedupe_key="development-welcome-v1",
                ),
            )

        device = (
            await session.execute(select(IoTDevice).where(IoTDevice.device_id == "local-simulator-1"))
        ).scalar_one_or_none()
        if not device:
            device = IoTDevice(
                device_id="local-simulator-1",
                display_name="Local scanner simulator",
                api_key_hash=hash_token(settings.IOT_DEVICE_API_KEY),
                is_active=True,
            )
            session.add(device)

        trainer = (
            await session.execute(select(PersonalTrainer).where(PersonalTrainer.user_id == users["pt"].id))
        ).scalar_one_or_none()
        if not trainer:
            trainer = PersonalTrainer(
                user_id=users["pt"].id,
                display_name=users["pt"].name,
                specialty="Strength and mobility",
                is_active=True,
            )
            session.add(trainer)
            await session.flush()

        broadcast = (
            await session.execute(
                select(BroadcastAnnouncement).where(BroadcastAnnouncement.title == "Welcome to the operations demo"),
            )
        ).scalar_one_or_none()
        if not broadcast:
            session.add(
                BroadcastAnnouncement(
                    audience="all",
                    title="Welcome to the operations demo",
                    message="QR attendance, notifications, CRM, billing exports and class scheduling are connected to live development data.",
                    starts_at=datetime.now(UTC) - timedelta(hours=1),
                    ends_at=datetime.now(UTC) + timedelta(days=30),
                    is_active=True,
                    creator_id=users["admin"].id,
                ),
            )

        attendance = (
            await session.execute(
                select(AttendanceSession).where(
                    AttendanceSession.user_id == member.id,
                    AttendanceSession.source == "development_seed",
                ),
            )
        ).scalars().first()
        if not attendance:
            check_in_at = datetime.now(UTC) - timedelta(days=1, hours=2)
            attendance = AttendanceSession(
                user_id=member.id,
                checked_in_at=check_in_at,
                closed_at=check_in_at + timedelta(minutes=75),
                status="checked_out",
                source="development_seed",
                device_id=device.device_id,
            )
            session.add(attendance)
            await session.flush()
            session.add_all(
                [
                    AttendanceEvent(
                        session_id=attendance.id,
                        user_id=member.id,
                        event_type="check_in",
                        event_at=check_in_at,
                        source="development_seed",
                        device_id=device.device_id,
                    ),
                    AttendanceEvent(
                        session_id=attendance.id,
                        user_id=member.id,
                        event_type="check_out",
                        event_at=check_in_at + timedelta(minutes=75),
                        source="development_seed",
                        device_id=device.device_id,
                    ),
                ],
            )

        gym_class = (
            await session.execute(select(GymClass).where(GymClass.title == "Strength Foundations Demo"))
        ).scalar_one_or_none()
        if not gym_class:
            start_at = datetime.now(UTC) + timedelta(days=2)
            session.add(
                GymClass(
                    title="Strength Foundations Demo",
                    class_type="Strength",
                    description="A seeded class for testing the Day 38 administration workflow.",
                    start_at=start_at,
                    end_at=start_at + timedelta(minutes=60),
                    capacity=16,
                    status="scheduled",
                    trainer_id=trainer.id,
                    location="Studio A",
                ),
            )

        await session.commit()


if __name__ == "__main__":
    asyncio.run(seed_development_data())
