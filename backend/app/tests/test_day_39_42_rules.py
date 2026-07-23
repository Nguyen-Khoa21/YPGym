from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.core.exceptions import AppError, ConflictError
from app.schemas.class_schema import TrainerCreate
from app.schemas.attendance_schema import CrowdednessResponse
from app.schemas.class_schema import MemberBookings
from app.repositories.operations_repository import NotificationRepository
from app.services.class_service import BookingService, TrainerService, can_cancel_class_booking
from app.services.dashboard_service import DashboardService
from app.services.notification_service import NotificationService


def test_trainer_profile_accepts_member_safe_fields() -> None:
    profile = TrainerCreate(
        display_name="Jordan Trainer",
        bio="Strength coaching with practical progressions.",
        specialty="Strength and mobility",
        availability_summary="Weekday mornings",
    )
    assert profile.specialty == "Strength and mobility"


def test_trainer_profile_rejects_empty_name() -> None:
    with pytest.raises(ValidationError):
        TrainerCreate(display_name="")


@pytest.mark.asyncio
async def test_trainer_deactivation_is_blocked_by_future_class() -> None:
    trainer = SimpleNamespace(id=uuid4(), display_name="Jordan", is_active=True)
    upcoming = SimpleNamespace(id=uuid4())

    class FakeTrainers:
        async def get_trainer(self, *_: object, **__: object) -> object:
            return trainer

        async def upcoming_for_trainer(self, _: object) -> list[object]:
            return [upcoming]

    service = object.__new__(TrainerService)
    service.trainers = FakeTrainers()

    with pytest.raises(ConflictError) as exc_info:
        await service.deactivate(trainer_id=trainer.id, actor=SimpleNamespace(id=uuid4()))
    assert exc_info.value.details == {"upcoming_class_ids": [str(upcoming.id)]}


@pytest.mark.parametrize(
    ("eligible", "confirmed", "booking_status", "waitlist_status", "class_status", "expected"),
    [
        (True, 0, None, None, "scheduled", "available"),
        (True, 1, "booked", None, "scheduled", "booked"),
        (True, 10, None, None, "scheduled", "full"),
        (False, 0, None, None, "scheduled", "ineligible"),
        (True, 0, None, None, "cancelled", "cancelled"),
    ],
)
def test_member_class_state_is_derived_from_server_records(
    eligible: bool,
    confirmed: int,
    booking_status: str | None,
    waitlist_status: str | None,
    class_status: str,
    expected: str,
) -> None:
    gym_class = SimpleNamespace(
        id=uuid4(),
        title="Strength",
        class_type="Strength",
        description=None,
        start_at=datetime.now(UTC) + timedelta(days=1),
        end_at=datetime.now(UTC) + timedelta(days=1, hours=1),
        capacity=10,
        status=class_status,
        location="Studio A",
    )
    item = BookingService._member_class(
        (gym_class, None, confirmed, uuid4() if booking_status else None, booking_status, waitlist_status, None),
        eligible=eligible,
    )
    assert item.member_state == expected


@pytest.mark.asyncio
async def test_full_class_rejects_confirmed_booking() -> None:
    gym_class = SimpleNamespace(
        id=uuid4(),
        status="scheduled",
        start_at=datetime.now(UTC) + timedelta(days=1),
        capacity=1,
    )

    class FakeLifecycle:
        async def require_eligible_membership(self, _: object) -> object:
            return SimpleNamespace()

    class FakeClasses:
        async def get_class(self, *_: object, **__: object) -> object:
            return gym_class

        async def get_booking_for_user(self, **_: object) -> None:
            return None

        async def get_waitlist_for_user(self, **_: object) -> None:
            return None

        async def confirmed_booking_count(self, _: object) -> int:
            return 1

    service = object.__new__(BookingService)
    service.lifecycle = FakeLifecycle()
    service.classes = FakeClasses()
    with pytest.raises(AppError) as exc_info:
        await service.book(class_id=gym_class.id, user=SimpleNamespace(id=uuid4()))
    assert getattr(exc_info.value, "code", None) == "CLASS_FULL"


def test_cancellation_cutoff_is_inclusive() -> None:
    start = datetime(2026, 8, 1, 12, tzinfo=UTC)
    cutoff = start - timedelta(hours=12)
    assert can_cancel_class_booking(now=cutoff, start_at=start, window_hours=12)
    assert not can_cancel_class_booking(now=cutoff + timedelta(microseconds=1), start_at=start, window_hours=12)


@pytest.mark.asyncio
async def test_promotion_skips_ineligible_member_and_uses_next_entry() -> None:
    class_id = uuid4()
    first_user = SimpleNamespace(id=uuid4())
    second_user = SimpleNamespace(id=uuid4())
    first = SimpleNamespace(id=uuid4(), user_id=first_user.id, position=1, status="waiting")
    second = SimpleNamespace(id=uuid4(), user_id=second_user.id, position=2, status="waiting")
    gym_class = SimpleNamespace(id=class_id, capacity=1, title="Mobility", start_at=datetime.now(UTC) + timedelta(days=1))

    class FakeLifecycle:
        async def require_eligible_membership(self, user: object) -> object:
            if user is first_user:
                raise AppError("MEMBERSHIP_INELIGIBLE", "Expired", 403)
            return SimpleNamespace()

    class FakeClasses:
        async def confirmed_booking_count(self, _: object) -> int:
            return 0

        async def waiting_entries_for_update(self, _: object) -> list[tuple[object, object]]:
            return [(first, first_user), (second, second_user)]

        async def get_booking_for_user(self, **_: object) -> None:
            return None

        async def create_booking(self, **values: object) -> object:
            return SimpleNamespace(id=uuid4(), status="booked", **values)

    class FakeNotifications:
        def __init__(self) -> None:
            self.user_id = None

        async def queue_class_promotion(self, *, user: object, **_: object) -> int:
            self.user_id = user.id
            return 1

    service = object.__new__(BookingService)
    service.lifecycle = FakeLifecycle()
    service.classes = FakeClasses()
    service.notifications = FakeNotifications()
    promoted = await service._promote(gym_class)
    assert first.status == "cancelled"
    assert second.status == "promoted"
    assert promoted.user_id == second_user.id
    assert service.notifications.user_id == second_user.id


@pytest.mark.asyncio
async def test_promotion_notification_respects_preferences_and_deduplicates() -> None:
    user = SimpleNamespace(id=uuid4())

    class FakeNotifications:
        def __init__(self) -> None:
            self.keys: set[str] = set()

        async def get_or_create_preferences(self, _: object) -> object:
            return SimpleNamespace(in_app_enabled=True, email_enabled=False)

        async def notification_exists(self, key: str) -> bool:
            return key in self.keys

        async def create_notification(self, **values: object) -> object:
            self.keys.add(str(values["dedupe_key"]))
            return SimpleNamespace(**values)

    service = object.__new__(NotificationService)
    service.notifications = FakeNotifications()
    values = {
        "user": user,
        "class_id": uuid4(),
        "class_title": "Mobility",
        "class_start": datetime.now(UTC) + timedelta(days=1),
        "waitlist_id": uuid4(),
        "waitlist_position": 1,
    }
    assert await service.queue_class_promotion(**values) == 1
    assert await service.queue_class_promotion(**values) == 0
    assert len(service.notifications.keys) == 1


@pytest.mark.asyncio
async def test_recent_unread_repository_filters_and_orders_preview() -> None:
    class ScalarResult:
        def scalar_one(self) -> int:
            return 4

    class ItemsResult:
        def scalars(self) -> "ItemsResult":
            return self

        def all(self) -> list[str]:
            return ["newest", "older"]

    class FakeSession:
        def __init__(self) -> None:
            self.statements: list[object] = []
            self.results = iter((ScalarResult(), ItemsResult()))

        async def execute(self, statement: object) -> object:
            self.statements.append(statement)
            return next(self.results)

    session = FakeSession()
    items, unread = await NotificationRepository(session).list_recent_unread(uuid4(), 3)
    queries = [str(statement) for statement in session.statements]
    assert items == ["newest", "older"]
    assert unread == 4
    assert all("notifications.read_at IS NULL" in query for query in queries)
    assert "ORDER BY notifications.created_at DESC, notifications.id DESC" in queries[1]
    assert "LIMIT" in queries[1]


@pytest.mark.asyncio
async def test_notification_service_returns_bounded_unread_preview() -> None:
    user = SimpleNamespace(id=uuid4())
    notification = SimpleNamespace(
        id=uuid4(),
        category="class_booking",
        notification_type="waitlist_promoted",
        title="You're booked",
        message="A place opened.",
        channel="in_app",
        delivery_state="delivered",
        read_at=None,
        created_at=datetime.now(UTC),
    )

    class FakeNotifications:
        async def list_recent_unread(self, user_id: object, limit: int) -> tuple[list[object], int]:
            assert user_id == user.id
            assert limit == 3
            return [notification], 4

    service = object.__new__(NotificationService)
    service.notifications = FakeNotifications()
    items, unread = await service.list_recent_unread(user=user, limit=3)
    assert [item.id for item in items] == [notification.id]
    assert unread == 4


@pytest.mark.asyncio
async def test_dashboard_uses_authenticated_member_and_handles_missing_membership() -> None:
    user = SimpleNamespace(id=uuid4(), name="Dashboard Member", tier="vip")

    class FakeLifecycle:
        async def access_snapshot(self, _: object) -> tuple[None, str, bool, str]:
            return None, "none", False, "Buy a membership before booking a class."

    class FakeBookings:
        async def list_my(self, _: object) -> MemberBookings:
            return MemberBookings(bookings=[], waitlists=[], cancellation_window_hours=12)

    class FakeNotifications:
        async def list_recent_unread(self, **_: object) -> tuple[list[object], int]:
            return [], 0

        async def list_active_broadcasts(self, _: object) -> list[object]:
            return []

    class FakeCrowdedness:
        async def get(self) -> CrowdednessResponse:
            return CrowdednessResponse(
                active_count=3,
                capacity=100,
                percentage=3,
                status="Low",
                calculated_at=datetime.now(UTC),
            )

    service = object.__new__(DashboardService)
    service.lifecycle = FakeLifecycle()
    service.bookings = FakeBookings()
    service.notifications = FakeNotifications()
    service.crowdedness = FakeCrowdedness()
    dashboard = await service.get(user)
    assert dashboard.member.id == user.id
    assert dashboard.membership is None
    assert not dashboard.qr_access.eligible
    assert dashboard.quick_actions[0].label == "Buy membership"
