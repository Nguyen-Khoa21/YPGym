from enum import StrEnum


class UserRole(StrEnum):
    MEMBER = "member"
    STAFF = "staff"
    MANAGER = "manager"
    ADMIN = "admin"
    PT = "pt"


class MemberTier(StrEnum):
    NORMAL = "normal"
    ADVANCE = "advance"
    VIP = "vip"


class MembershipStatus(StrEnum):
    PENDING_VERIFICATION = "pending_verification"
    ACTIVE = "active"
    EXPIRING_SOON = "expiring_soon"
    EXPIRED = "expired"
    FROZEN = "frozen"
    CANCELLED = "cancelled"
    REVOKED = "revoked"


class PaymentStatus(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class SystemConfigurationValueType(StrEnum):
    STRING = "string"
    INTEGER = "integer"
    DECIMAL = "decimal"
    BOOLEAN = "boolean"


class RequestStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class CancellationOutcome(StrEnum):
    REFUND = "refund"
    ACCOUNT_CREDIT = "account_credit"
    FORFEIT = "forfeit"


class NotificationChannel(StrEnum):
    IN_APP = "in_app"
    EMAIL = "email"


class NotificationDeliveryState(StrEnum):
    PENDING = "pending"
    DELIVERED = "delivered"
    SKIPPED = "skipped"


class AttendanceSessionStatus(StrEnum):
    ACTIVE = "active"
    CHECKED_OUT = "checked_out"
    TIMED_OUT = "timed_out"
    MANUAL_CLOSED = "manual_closed"


class AttendanceEventType(StrEnum):
    CHECK_IN = "check_in"
    CHECK_OUT = "check_out"
    TIMEOUT = "timeout"
    MANUAL_CLOSE = "manual_close"


class ClassStatus(StrEnum):
    SCHEDULED = "scheduled"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
