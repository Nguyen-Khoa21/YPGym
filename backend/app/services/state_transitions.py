from collections.abc import Mapping, Set
from enum import StrEnum
from typing import Protocol

from app.core.exceptions import InvalidStateTransitionError
from app.models.enums import (
    AttendanceSessionStatus,
    ClassBookingStatus,
    ClassStatus,
    MembershipStatus,
    PaymentStatus,
    RefundStatus,
    RequestStatus,
    WaitlistStatus,
)


class HasStatus(Protocol):
    status: str


class HasRefundStatus(Protocol):
    refund_status: str


TransitionTable = Mapping[str, Set[str]]


MEMBERSHIP_TRANSITIONS: TransitionTable = {
    MembershipStatus.PENDING_VERIFICATION: {
        MembershipStatus.ACTIVE,
        MembershipStatus.EXPIRING_SOON,
        MembershipStatus.EXPIRED,
        MembershipStatus.FROZEN,
        MembershipStatus.CANCELLED,
        MembershipStatus.REVOKED,
    },
    MembershipStatus.ACTIVE: {
        MembershipStatus.EXPIRING_SOON,
        MembershipStatus.EXPIRED,
        MembershipStatus.FROZEN,
        MembershipStatus.CANCELLED,
        MembershipStatus.REVOKED,
    },
    MembershipStatus.EXPIRING_SOON: {
        MembershipStatus.ACTIVE,
        MembershipStatus.EXPIRED,
        MembershipStatus.FROZEN,
        MembershipStatus.CANCELLED,
        MembershipStatus.REVOKED,
    },
    MembershipStatus.EXPIRED: {MembershipStatus.ACTIVE, MembershipStatus.REVOKED},
    MembershipStatus.FROZEN: {
        MembershipStatus.ACTIVE,
        MembershipStatus.EXPIRING_SOON,
        MembershipStatus.EXPIRED,
        MembershipStatus.CANCELLED,
        MembershipStatus.REVOKED,
    },
    MembershipStatus.CANCELLED: set(),
    MembershipStatus.REVOKED: set(),
}

PAYMENT_TRANSITIONS: TransitionTable = {
    PaymentStatus.PENDING: {
        PaymentStatus.PAID,
        PaymentStatus.FAILED,
        PaymentStatus.CANCELLED,
        PaymentStatus.EXPIRED,
        PaymentStatus.PAID_REVIEW,
    },
    PaymentStatus.FAILED: {PaymentStatus.PAID_REVIEW},
    PaymentStatus.CANCELLED: {PaymentStatus.PAID_REVIEW},
    PaymentStatus.EXPIRED: {PaymentStatus.PAID_REVIEW},
    PaymentStatus.PAID: set(),
    PaymentStatus.SUCCEEDED: set(),
    PaymentStatus.PAID_REVIEW: set(),
}

CLASS_TRANSITIONS: TransitionTable = {
    ClassStatus.SCHEDULED: {ClassStatus.CANCELLED, ClassStatus.COMPLETED},
    ClassStatus.CANCELLED: set(),
    ClassStatus.COMPLETED: set(),
}

BOOKING_TRANSITIONS: TransitionTable = {
    ClassBookingStatus.PENDING_PAYMENT: {
        ClassBookingStatus.CONFIRMED,
        ClassBookingStatus.CANCELLED,
        ClassBookingStatus.EXPIRED,
        ClassBookingStatus.PAYMENT_FAILED,
    },
    ClassBookingStatus.CONFIRMED: {ClassBookingStatus.CANCELLED},
    ClassBookingStatus.CANCELLED: {
        ClassBookingStatus.PENDING_PAYMENT,
        ClassBookingStatus.REFUNDED,
    },
    ClassBookingStatus.EXPIRED: {
        ClassBookingStatus.PENDING_PAYMENT,
        ClassBookingStatus.CANCELLED,
    },
    ClassBookingStatus.PAYMENT_FAILED: {
        ClassBookingStatus.PENDING_PAYMENT,
        ClassBookingStatus.CANCELLED,
    },
    ClassBookingStatus.REFUNDED: {ClassBookingStatus.PENDING_PAYMENT},
}

WAITLIST_TRANSITIONS: TransitionTable = {
    WaitlistStatus.WAITING: {WaitlistStatus.PROMOTED, WaitlistStatus.CANCELLED},
    WaitlistStatus.PROMOTED: {WaitlistStatus.WAITING},
    WaitlistStatus.CANCELLED: {WaitlistStatus.WAITING},
}

ATTENDANCE_TRANSITIONS: TransitionTable = {
    AttendanceSessionStatus.ACTIVE: {
        AttendanceSessionStatus.CHECKED_OUT,
        AttendanceSessionStatus.TIMED_OUT,
        AttendanceSessionStatus.MANUAL_CLOSED,
    },
    AttendanceSessionStatus.CHECKED_OUT: set(),
    AttendanceSessionStatus.TIMED_OUT: set(),
    AttendanceSessionStatus.MANUAL_CLOSED: set(),
}

REQUEST_TRANSITIONS: TransitionTable = {
    RequestStatus.PENDING: {RequestStatus.APPROVED, RequestStatus.REJECTED},
    RequestStatus.APPROVED: set(),
    RequestStatus.REJECTED: set(),
}

REFUND_TRANSITIONS: TransitionTable = {
    RefundStatus.NONE: {RefundStatus.REQUIRED},
    RefundStatus.REQUIRED: {RefundStatus.RESOLVED},
    RefundStatus.RESOLVED: {RefundStatus.NONE},
}


def _value(state: str | StrEnum) -> str:
    return state.value if isinstance(state, StrEnum) else state


def validate_transition(
    resource: str,
    current: str | StrEnum,
    target: str | StrEnum,
    table: TransitionTable,
    *,
    idempotent: bool = False,
) -> bool:
    current_value = _value(current)
    target_value = _value(target)
    if current_value == target_value:
        if idempotent:
            return False
        raise InvalidStateTransitionError(resource, current_value, target_value)
    if target_value not in table.get(current_value, set()):
        raise InvalidStateTransitionError(resource, current_value, target_value)
    return True


def _transition_status(
    entity: HasStatus,
    target: str | StrEnum,
    resource: str,
    table: TransitionTable,
    *,
    idempotent: bool = False,
) -> bool:
    target_value = _value(target)
    changed = validate_transition(resource, entity.status, target_value, table, idempotent=idempotent)
    if changed:
        entity.status = target_value
    return changed


def transition_membership(entity: HasStatus, target: str | StrEnum, *, idempotent: bool = False) -> bool:
    return _transition_status(entity, target, "membership", MEMBERSHIP_TRANSITIONS, idempotent=idempotent)


def transition_payment(entity: HasStatus, target: str | StrEnum, *, idempotent: bool = False) -> bool:
    return _transition_status(entity, target, "payment", PAYMENT_TRANSITIONS, idempotent=idempotent)


def transition_class(entity: HasStatus, target: str | StrEnum, *, idempotent: bool = False) -> bool:
    return _transition_status(entity, target, "class", CLASS_TRANSITIONS, idempotent=idempotent)


def transition_booking(entity: HasStatus, target: str | StrEnum, *, idempotent: bool = False) -> bool:
    return _transition_status(entity, target, "class booking", BOOKING_TRANSITIONS, idempotent=idempotent)


def transition_waitlist(entity: HasStatus, target: str | StrEnum, *, idempotent: bool = False) -> bool:
    return _transition_status(entity, target, "waitlist entry", WAITLIST_TRANSITIONS, idempotent=idempotent)


def transition_attendance(entity: HasStatus, target: str | StrEnum, *, idempotent: bool = False) -> bool:
    return _transition_status(entity, target, "attendance session", ATTENDANCE_TRANSITIONS, idempotent=idempotent)


def transition_request(entity: HasStatus, target: str | StrEnum, *, idempotent: bool = False) -> bool:
    return _transition_status(entity, target, "approval request", REQUEST_TRANSITIONS, idempotent=idempotent)


def transition_refund(entity: HasRefundStatus, target: str | StrEnum, *, idempotent: bool = False) -> bool:
    target_value = _value(target)
    changed = validate_transition(
        "class booking refund",
        entity.refund_status,
        target_value,
        REFUND_TRANSITIONS,
        idempotent=idempotent,
    )
    if changed:
        entity.refund_status = target_value
    return changed
