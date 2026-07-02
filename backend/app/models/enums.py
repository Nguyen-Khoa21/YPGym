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
