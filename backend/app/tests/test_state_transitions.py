from dataclasses import dataclass

import pytest

from app.core.exceptions import InvalidStateTransitionError
from app.services.state_transitions import (
    ATTENDANCE_TRANSITIONS,
    BOOKING_TRANSITIONS,
    CLASS_TRANSITIONS,
    MEMBERSHIP_TRANSITIONS,
    PAYMENT_TRANSITIONS,
    REFUND_TRANSITIONS,
    REQUEST_TRANSITIONS,
    WAITLIST_TRANSITIONS,
    transition_attendance,
    transition_booking,
    transition_class,
    transition_membership,
    transition_payment,
    transition_refund,
    transition_request,
    transition_waitlist,
)


@dataclass
class StatusEntity:
    status: str


@dataclass
class RefundEntity:
    refund_status: str


STATUS_DOMAINS = (
    (MEMBERSHIP_TRANSITIONS, transition_membership),
    (PAYMENT_TRANSITIONS, transition_payment),
    (CLASS_TRANSITIONS, transition_class),
    (BOOKING_TRANSITIONS, transition_booking),
    (WAITLIST_TRANSITIONS, transition_waitlist),
    (ATTENDANCE_TRANSITIONS, transition_attendance),
    (REQUEST_TRANSITIONS, transition_request),
)


@pytest.mark.parametrize(("table", "transition"), STATUS_DOMAINS)
def test_every_declared_status_transition_is_permitted(table, transition) -> None:
    for current, targets in table.items():
        for target in targets:
            entity = StatusEntity(current)
            assert transition(entity, target) is True
            assert entity.status == target


@pytest.mark.parametrize(("table", "transition"), STATUS_DOMAINS)
def test_every_undeclared_status_transition_is_rejected(table, transition) -> None:
    states = set(table) | {target for targets in table.values() for target in targets}
    for current in states:
        for target in states - set(table.get(current, set())) - {current}:
            entity = StatusEntity(current)
            with pytest.raises(InvalidStateTransitionError) as caught:
                transition(entity, target)
            assert caught.value.code == "INVALID_STATE_TRANSITION"
            assert entity.status == current


@pytest.mark.parametrize(("table", "transition"), STATUS_DOMAINS)
def test_repeated_status_event_is_only_idempotent_when_explicit(table, transition) -> None:
    current = next(iter(table))
    entity = StatusEntity(current)
    with pytest.raises(InvalidStateTransitionError):
        transition(entity, current)
    assert transition(entity, current, idempotent=True) is False
    assert entity.status == current


def test_refund_transitions_cover_permitted_forbidden_and_idempotent_paths() -> None:
    states = set(REFUND_TRANSITIONS)
    for current in states:
        for target in states:
            entity = RefundEntity(current)
            if target in REFUND_TRANSITIONS[current]:
                assert transition_refund(entity, target) is True
                assert entity.refund_status == target
            elif target == current:
                with pytest.raises(InvalidStateTransitionError):
                    transition_refund(entity, target)
                assert transition_refund(entity, target, idempotent=True) is False
            else:
                with pytest.raises(InvalidStateTransitionError):
                    transition_refund(entity, target)
                assert entity.refund_status == current
