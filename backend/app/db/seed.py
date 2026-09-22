import argparse
import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from urllib.parse import urlsplit
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import AsyncSessionLocal
from app.models.attendance import AttendanceEvent, AttendanceSession, IoTDevice
from app.models.billing import Invoice, Payment
from app.models.classes import ClassBooking, ClassWaitlist, GymClass, PersonalTrainer
from app.models.membership import MembershipPlan, UserMembership
from app.models.operations import BroadcastAnnouncement, Notification, NotificationPreference
from app.models.system_configuration import SystemConfiguration
from app.models.training import TrainingExercise, TrainingExerciseMuscle
from app.models.user import User
from app.services.invoice_service import InvoicePdfService
from app.utils.security import hash_password, hash_token


PLAN_SEEDS = [
    {
        "name": "1 Month",
        "duration_months": 1,
        "duration_days": 30,
        "base_price": Decimal("720000.00"),
        "discount_percent": Decimal("0.00"),
        "benefits": "Gym floor access\nMember dashboard\nInvoice history",
        "display_order": 1,
    },
    {
        "name": "3 Months",
        "duration_months": 3,
        "duration_days": 90,
        "base_price": Decimal("1980000.00"),
        "discount_percent": Decimal("5.00"),
        "benefits": "Gym floor access\nMember dashboard\nPriority renewal reminder",
        "display_order": 2,
    },
    {
        "name": "6 Months",
        "duration_months": 6,
        "duration_days": 180,
        "base_price": Decimal("3600000.00"),
        "discount_percent": Decimal("10.00"),
        "benefits": "Gym floor access\nMember dashboard\nRenewal savings",
        "display_order": 3,
    },
    {
        "name": "1 Year",
        "duration_months": 12,
        "duration_days": 365,
        "base_price": Decimal("6480000.00"),
        "discount_percent": Decimal("15.00"),
        "benefits": "Gym floor access\nBest annual value\nInvoice history",
        "display_order": 4,
    },
    {
        "name": "2 Years",
        "duration_months": 24,
        "duration_days": 730,
        "base_price": Decimal("11880000.00"),
        "discount_percent": Decimal("20.00"),
        "benefits": "Long-term membership rate\nMember dashboard\nRenewal savings",
        "display_order": 5,
    },
    {
        "name": "3 Years",
        "duration_months": 36,
        "duration_days": 1095,
        "base_price": Decimal("16200000.00"),
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

DEMO_MEMBERS = [
    ("advance", "Advance Member", "advance", "active"),
    ("normal", "Normal Member", "normal", "active"),
    ("frozen", "Frozen Member", "advance", "frozen"),
    ("expired", "Expired Member", "normal", "expired"),
    ("revoked", "Revoked Member", "normal", "revoked"),
    ("cancelled", "Cancelled Member", "normal", "cancelled"),
    ("newmember", "New Member", "normal", None),
]

ILLUSTRATIVE_EXERCISES = [
    ("Push-up", "upper", "A bodyweight pressing exercise for upper-body strength.", "Start in a plank with hands below shoulders. Lower with control, then press back up.", "Keep your trunk steady and use an incline if the floor version is too demanding.", ["chest", "triceps"], ["shoulders", "core"]),
    ("Lat pulldown", "upper", "An illustrative cable-machine pulling exercise; equipment availability is unconfirmed.", "Adjust the thigh pad. Pull the bar toward the upper chest without leaning far back, then return slowly.", "Avoid pulling behind the neck and stop if movement causes pain.", ["back"], ["biceps", "forearms"]),
    ("Bodyweight squat", "lower", "A bodyweight lower-body squat.", "Stand with feet comfortable apart. Bend hips and knees, then stand back up with control.", "Keep heels grounded and use a comfortable depth.", ["quadriceps", "glutes"], ["hamstrings", "core"]),
    ("Leg press", "lower", "An illustrative machine-based leg press; equipment availability is unconfirmed.", "Adjust the seat and place feet on the platform. Extend the legs without locking knees, then lower slowly.", "Keep your lower back on the pad and use a manageable load.", ["quadriceps", "glutes"], ["hamstrings", "calves"]),
]


async def seed_development_data(*, demo: bool = False, now: datetime | None = None) -> None:
    settings = get_settings()
    if settings.ENVIRONMENT not in {"development", "test"}:
        raise ValueError("Development seeds must not run in a production environment.")
    if demo:
        database = urlsplit(settings.DATABASE_URL)
        redis = urlsplit(settings.REDIS_URL)
        allowed_storage = {
            ("postgres-db", "/ypgym_demo", "redis-cache"),
            ("test-postgres", "/ypgym_test", "test-redis"),
        }
        if settings.ENVIRONMENT not in {"development", "test"} or (
            database.hostname, database.path, redis.hostname
        ) not in allowed_storage:
            raise ValueError("Full demo seeding requires compose.demo.yml or compose.test.yml isolated storage.")
    now = now or datetime.now(UTC)
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
        ("class_reminder_lead_minutes", "120", "integer", "Lead time for booked-class reminders."),
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
                    email_verified_at=now,
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
                start_date=now.date() - timedelta(days=45),
                expiry_date=now.date() + timedelta(days=320),
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
                amount=Decimal("5508000.00"),
                discount_amount=Decimal("972000.00"),
                status="succeeded",
                mock_reference="MOCK-DEVELOPMENT-SEED",
            )
            session.add(seeded_payment)
            await session.flush()

        seeded_invoice = (
            await session.execute(select(Invoice).where(Invoice.payment_id == seeded_payment.id))
        ).scalar_one_or_none()
        if not seeded_invoice:
            transaction_date = now
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
                    delivered_at=now,
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
                bio="A practical coach focused on safe, repeatable progress for every experience level.",
                specialty="Strength and mobility",
                availability_summary="Weekday mornings and selected evening classes",
                is_active=True,
            )
            session.add(trainer)
            await session.flush()
        else:
            trainer.bio = trainer.bio or "A practical coach focused on safe, repeatable progress for every experience level."
            trainer.availability_summary = trainer.availability_summary or "Weekday mornings and selected evening classes"

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
                    starts_at=now - timedelta(hours=1),
                    ends_at=now + timedelta(days=30),
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
            check_in_at = now - timedelta(days=1, hours=2)
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
            start_at = now + timedelta(days=2)
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
        elif gym_class.status == "scheduled" and gym_class.start_at <= now:
            start_at = now + timedelta(days=2)
            gym_class.start_at = start_at
            gym_class.end_at = start_at + timedelta(minutes=60)

        for name, region, description, steps, safety, primary, secondary in ILLUSTRATIVE_EXERCISES:
            exercise_id = uuid5(NAMESPACE_URL, f"ypgym:illustrative-exercise:{name}")
            existing = (await session.execute(select(TrainingExercise.id).where(TrainingExercise.id == exercise_id))).scalar_one_or_none()
            if not existing:
                session.add(TrainingExercise(id=exercise_id, name=name, region=region, description=description, usage_steps=steps, safety_note=safety, is_illustrative=True))
                session.add_all([TrainingExerciseMuscle(exercise_id=exercise_id, muscle=muscle, role=role) for role, values in (("primary", primary), ("secondary", secondary)) for muscle in values])

        if demo:
            await _seed_demo_scenarios(session, users, plans, trainer, membership, now)
        await session.commit()


async def _seed_demo_scenarios(
    session: AsyncSession, users: dict[str, User], plans: dict[str, MembershipPlan],
    trainer: PersonalTrainer, membership: UserMembership, now: datetime,
) -> None:
    """Refresh only explicitly seeded fixtures in the isolated demonstration database."""
    today = now.date()
    membership.status = "active"
    membership.start_date = today - timedelta(days=45)
    membership.expiry_date = max(membership.expiry_date, today + timedelta(days=320))
    membership.frozen_from = membership.frozen_until = None
    membership.cancelled_at = membership.revoked_at = membership.revoked_by_id = membership.revoked_reason = None
    members = {"member": users["member"]}
    for index, (slug, name, tier, status) in enumerate(DEMO_MEMBERS, start=6):
        email = f"{slug}@ypgym.dev"
        user = (await session.execute(select(User).where(User.email == email))).scalar_one_or_none()
        if not user:
            user = User(
                name=f"YPGym Demo {name}", email=email, phone=f"+660000000{index:02d}",
                password_hash=hash_password(get_settings().DEVELOPMENT_SEED_PASSWORD),
                role="member", tier=tier, is_email_verified=True, email_verified_at=now,
            )
            session.add(user)
            await session.flush()
            session.add(NotificationPreference(user_id=user.id))
        members[slug] = user
        if status:
            fixture_id = uuid5(NAMESPACE_URL, f"ypgym:demo:membership:{user.id}")
            fixture = await session.get(UserMembership, fixture_id)
            if not fixture:
                fixture = UserMembership(id=fixture_id, user_id=user.id, plan_id=plans["1 Year"].id)
                session.add(fixture)
            fixture.status = status
            fixture.start_date = today - timedelta(days=45 if status != "expired" else 366)
            fixture.expiry_date = today + timedelta(days=320 if status != "expired" else -1)
            fixture.frozen_from = today - timedelta(days=3) if status == "frozen" else None
            fixture.frozen_until = today + timedelta(days=4) if status == "frozen" else None
            fixture.cancelled_at = now - timedelta(days=2) if status == "cancelled" else None
            fixture.revoked_at = now - timedelta(days=2) if status == "revoked" else None
            fixture.revoked_by_id = users["admin"].id if status == "revoked" else None
            fixture.revoked_reason = "Synthetic release-demo restriction; no real member data." if status == "revoked" else None
        dedupe_key = f"release-demo-welcome-{slug}"
        if not (await session.execute(select(Notification).where(Notification.dedupe_key == dedupe_key))).scalar_one_or_none():
            session.add(Notification(
                user_id=user.id, category="operations", notification_type="welcome",
                title="Release demo account", message="This synthetic account demonstrates member self-service and access states.",
                channel="in_app", delivery_state="delivered", delivered_at=now, dedupe_key=dedupe_key,
            ))

    demo_classes = {}
    for day, title, capacity in [(3, "Capacity One Demo", 1), (4, "Upcoming Mobility Demo", 12)]:
        fixture = (await session.execute(select(GymClass).where(GymClass.title == title))).scalar_one_or_none()
        if not fixture:
            fixture = GymClass(title=title, class_type="Mobility", description="Synthetic release-demo booking scenario.",
                               location="Studio A", trainer_id=trainer.id, capacity=capacity)
            session.add(fixture)
        fixture.start_at = now + timedelta(days=day)
        fixture.end_at = fixture.start_at + timedelta(hours=1)
        fixture.status = "scheduled"
        demo_classes[title] = fixture
    await session.flush()
    for title, slug in [("Capacity One Demo", "advance"), ("Upcoming Mobility Demo", "member")]:
        fixture = (await session.execute(select(ClassBooking).where(
            ClassBooking.class_id == demo_classes[title].id, ClassBooking.user_id == members[slug].id,
        ))).scalar_one_or_none()
        if not fixture:
            fixture = ClassBooking(class_id=demo_classes[title].id, user_id=members[slug].id)
            session.add(fixture)
    # Re-seeding after interactive demo mutations is intentionally not a reset:
    # retain waitlist positions/decisions. Use the documented isolated-stack reset
    # to replay promotion from its original state without changing live records.
    waitlist = (await session.execute(select(ClassWaitlist).where(
        ClassWaitlist.class_id == demo_classes["Capacity One Demo"].id, ClassWaitlist.user_id == members["normal"].id,
    ))).scalar_one_or_none()
    if not waitlist:
        existing_positions = (await session.execute(select(ClassWaitlist.position).where(
            ClassWaitlist.class_id == demo_classes["Capacity One Demo"].id,
        ))).scalars().all()
        session.add(ClassWaitlist(class_id=demo_classes["Capacity One Demo"].id,
                                 user_id=members["normal"].id, position=max(existing_positions, default=0) + 1))

    for day in range(1, 8):
        for slug, hour in [("member", 8), ("advance", 12), ("normal", 18)]:
            user = members[slug]
            check_in = (now - timedelta(days=day)).replace(hour=hour, minute=0, second=0, microsecond=0)
            fixture_id = uuid5(NAMESPACE_URL, f"ypgym:demo:attendance:{user.id}:{day}")
            fixture = await session.get(AttendanceSession, fixture_id)
            if not fixture:
                fixture = AttendanceSession(id=fixture_id, user_id=user.id, source="release_demo", device_id="local-simulator-1")
                session.add(fixture)
            fixture.checked_in_at = check_in
            fixture.closed_at = check_in + timedelta(minutes=60 + day)
            fixture.status = "checked_out"
            await session.flush()
            for event_type, event_at in [("check_in", fixture.checked_in_at), ("check_out", fixture.closed_at)]:
                event_id = uuid5(NAMESPACE_URL, f"ypgym:demo:event:{fixture_id}:{event_type}")
                event = await session.get(AttendanceEvent, event_id)
                if not event:
                    event = AttendanceEvent(id=event_id, session_id=fixture_id, user_id=user.id,
                                            event_type=event_type, source="release_demo", device_id="local-simulator-1")
                    session.add(event)
                event.event_at = event_at
    broadcast = (await session.execute(select(BroadcastAnnouncement).where(
        BroadcastAnnouncement.title == "Welcome to the operations demo",
    ))).scalar_one()
    broadcast.starts_at = now - timedelta(hours=1)
    broadcast.ends_at = now + timedelta(days=30)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Idempotent local seeds; full scenarios require isolated demo/test storage.")
    parser.add_argument("--demo", action="store_true", help="Populate the Day58 synthetic release scenarios in isolated storage.")
    asyncio.run(seed_development_data(demo=parser.parse_args().demo))
