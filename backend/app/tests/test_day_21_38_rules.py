from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.core.exceptions import AppError, ConflictError, ResourceNotFoundError
from app.schemas.class_schema import ClassCreate
from app.schemas.notification_schema import BroadcastCreate
from app.schemas.operations_schema import FreezeRequestCreate, RequestDecision
from app.services.attendance_service import crowdedness_status
from app.services.class_service import ClassService, validate_class_times
from app.services.configuration_service import CONFIGURATION_RULES, validate_configuration_value
from app.services.invoice_service import format_vnd
from app.services.lifecycle_service import derive_membership_status, membership_access_message
from app.services.notification_service import NotificationService


TODAY = date(2026, 7, 18)


def test_vnd_invoice_amount_has_grouping_and_no_fraction() -> None:
    assert format_vnd(Decimal("5508000.00")) == "VND 5,508,000"


def membership_status(**overrides: object) -> str:
    values = {
        "stored_status": "active",
        "is_email_verified": True,
        "expiry_date": TODAY + timedelta(days=30),
        "today": TODAY,
        "frozen_from": None,
        "frozen_until": None,
    }
    values.update(overrides)
    return derive_membership_status(**values)


@pytest.mark.parametrize("terminal", ["cancelled", "revoked"])
def test_terminal_membership_status_is_immutable(terminal: str) -> None:
    assert membership_status(stored_status=terminal, expiry_date=TODAY - timedelta(days=1)) == terminal


def test_unverified_membership_is_pending_verification() -> None:
    assert membership_status(is_email_verified=False) == "pending_verification"


def test_current_freeze_takes_precedence_over_expiry_window() -> None:
    assert membership_status(
        expiry_date=TODAY + timedelta(days=2),
        frozen_from=TODAY - timedelta(days=1),
        frozen_until=TODAY + timedelta(days=1),
    ) == "frozen"


@pytest.mark.parametrize(
    ("days_remaining", "expected"),
    [(-1, "expired"), (0, "expiring_soon"), (7, "expiring_soon"), (8, "active")],
)
def test_membership_expiry_boundaries(days_remaining: int, expected: str) -> None:
    assert membership_status(expiry_date=TODAY + timedelta(days=days_remaining)) == expected


@pytest.mark.parametrize("status", ["pending_verification", "frozen", "expired", "cancelled", "revoked"])
def test_ineligible_status_has_actionable_access_message(status: str) -> None:
    assert membership_access_message(status) != "Membership access is currently unavailable."


def test_freeze_request_accepts_ninety_days() -> None:
    request = FreezeRequestCreate(
        requested_start_date=TODAY,
        requested_end_date=TODAY + timedelta(days=89),
        reason="Extended travel for work obligations.",
    )
    assert request.requested_end_date == TODAY + timedelta(days=89)


@pytest.mark.parametrize("end_offset", [-1, 90])
def test_freeze_request_rejects_invalid_period(end_offset: int) -> None:
    with pytest.raises(ValidationError):
        FreezeRequestCreate(
            requested_start_date=TODAY,
            requested_end_date=TODAY + timedelta(days=end_offset),
            reason="Extended travel for work obligations.",
        )


@pytest.mark.parametrize("outcome", ["refund", "account_credit", "forfeit"])
def test_approved_cancellation_requires_supported_outcome(outcome: str) -> None:
    decision = RequestDecision(
        approve=True,
        decision_reason="Reviewed against the membership policy.",
        outcome=outcome,
    )
    assert decision.outcome == outcome


@pytest.mark.parametrize(
    "payload",
    [
        {"approve": True, "decision_reason": "Reviewed against the membership policy.", "outcome": None},
        {"approve": False, "decision_reason": "Reviewed against the membership policy.", "outcome": "refund"},
    ],
)
def test_cancellation_rejects_inconsistent_financial_outcome(payload: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        RequestDecision(**payload)


@pytest.mark.parametrize("key", sorted(CONFIGURATION_RULES))
def test_configuration_bounds_are_accepted(key: str) -> None:
    rule = CONFIGURATION_RULES[key]
    assert validate_configuration_value(key, rule.minimum) == rule.minimum
    assert validate_configuration_value(key, rule.maximum) == rule.maximum


def test_configuration_out_of_range_is_structured_error() -> None:
    with pytest.raises(AppError) as exc_info:
        validate_configuration_value("gym_capacity", 0)
    assert exc_info.value.code == "CONFIGURATION_VALUE_OUT_OF_RANGE"
    assert exc_info.value.status_code == 422


def test_unknown_configuration_key_is_not_silently_accepted() -> None:
    with pytest.raises(ResourceNotFoundError):
        validate_configuration_value("unknown_key", 1)


@pytest.mark.parametrize(
    ("percentage", "expected"),
    [(0, "Low"), (30, "Low"), (30.1, "Moderate"), (60, "Moderate"), (60.1, "Busy"), (85, "Busy"), (85.1, "Very Crowded")],
)
def test_crowdedness_thresholds(percentage: float, expected: str) -> None:
    assert crowdedness_status(percentage) == expected


def test_class_time_validation_accepts_future_timezone_aware_range() -> None:
    start = datetime.now(UTC) + timedelta(days=1)
    validate_class_times(start, start + timedelta(hours=1))


def test_class_time_validation_rejects_naive_datetimes() -> None:
    start = datetime.now() + timedelta(days=1)
    with pytest.raises(AppError) as exc_info:
        validate_class_times(start, start + timedelta(hours=1))
    assert exc_info.value.code == "CLASS_TIMEZONE_REQUIRED"


def test_class_time_validation_rejects_past_start() -> None:
    start = datetime.now(UTC) - timedelta(minutes=1)
    with pytest.raises(AppError) as exc_info:
        validate_class_times(start, start + timedelta(hours=1))
    assert exc_info.value.code == "CLASS_START_IN_PAST"


def test_class_create_rejects_end_before_start() -> None:
    start = datetime.now(UTC) + timedelta(days=1)
    with pytest.raises(ValidationError):
        ClassCreate(
            title="Morning strength",
            class_type="Strength",
            start_at=start,
            end_at=start - timedelta(minutes=1),
            capacity=12,
            location="Studio A",
        )


def test_broadcast_rejects_end_before_start() -> None:
    start = datetime.now(UTC) + timedelta(hours=1)
    with pytest.raises(ValidationError):
        BroadcastCreate(
            title="Scheduled maintenance",
            message="The gym will close briefly for scheduled maintenance.",
            starts_at=start,
            ends_at=start - timedelta(minutes=1),
        )


@pytest.mark.asyncio
async def test_class_overlap_returns_conflict_context() -> None:
    conflict = SimpleNamespace(id=uuid4(), title="Existing class")
    service = object.__new__(ClassService)
    service.classes = SimpleNamespace(find_overlap=lambda **_: None)

    async def find_overlap(**_: object) -> object:
        return conflict

    service.classes.find_overlap = find_overlap
    with pytest.raises(ConflictError) as exc_info:
        await service._ensure_no_overlap(
            start_at=datetime.now(UTC) + timedelta(days=1),
            end_at=datetime.now(UTC) + timedelta(days=1, hours=1),
            location="Studio A",
            trainer_id=None,
        )
    assert exc_info.value.details["conflicting_class_id"] == str(conflict.id)


@pytest.mark.asyncio
async def test_expiry_reminders_are_deduplicated_per_channel() -> None:
    membership = SimpleNamespace(id=uuid4(), expiry_date=TODAY + timedelta(days=7))
    user = SimpleNamespace(id=uuid4())
    preferences = SimpleNamespace(
        expiry_reminders_enabled=True,
        in_app_enabled=True,
        email_enabled=True,
    )

    class FakeNotifications:
        def __init__(self) -> None:
            self.dedupe_keys: set[str] = set()

        async def reminder_candidates(self, expiry_date: date) -> list[tuple[object, object]]:
            return [(membership, user)] if expiry_date == membership.expiry_date else []

        async def get_or_create_preferences(self, _: object) -> object:
            return preferences

        async def notification_exists(self, dedupe_key: str) -> bool:
            return dedupe_key in self.dedupe_keys

        async def create_notification(self, **values: object) -> object:
            self.dedupe_keys.add(str(values["dedupe_key"]))
            return SimpleNamespace(**values)

    class FakeSession:
        async def commit(self) -> None:
            return None

    service = object.__new__(NotificationService)
    service.session = FakeSession()
    service.notifications = FakeNotifications()

    assert await service.send_expiry_reminders(today=TODAY) == 2
    assert await service.send_expiry_reminders(today=TODAY) == 0
    assert len(service.notifications.dedupe_keys) == 2
