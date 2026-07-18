from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.auth_schema import UserPublic


class PageInfo(BaseModel):
    page: int
    page_size: int
    total: int
    pages: int


class MembershipRecord(BaseModel):
    id: UUID
    plan_id: UUID
    plan_name: str
    status: str
    start_date: date
    expiry_date: date
    frozen_from: date | None = None
    frozen_until: date | None = None


class AdminMemberListItem(BaseModel):
    id: UUID
    name: str
    email: str
    phone: str
    role: str
    tier: str
    is_email_verified: bool
    membership: MembershipRecord | None
    created_at: datetime


class MemberCrmSummary(BaseModel):
    total: int
    active: int
    expiring_soon: int
    frozen: int
    expired_or_inactive: int


class AdminMemberListResponse(BaseModel):
    items: list[AdminMemberListItem]
    page: PageInfo
    summary: MemberCrmSummary


class AdminPaymentRecord(BaseModel):
    id: UUID
    plan_name: str
    amount: Decimal
    discount_amount: Decimal
    status: str
    reference: str
    created_at: datetime


class AdminInvoiceRecord(BaseModel):
    id: UUID
    invoice_number: str
    plan_name: str
    amount: Decimal
    transaction_date: datetime


class AttendanceSummary(BaseModel):
    total_visits: int = 0
    active_sessions: int = 0
    last_check_in_at: datetime | None = None


class AttendanceHistorySummaryItem(BaseModel):
    id: UUID
    checked_in_at: datetime
    closed_at: datetime | None
    status: str
    source: str
    device_id: str | None


class BookingSummary(BaseModel):
    total: int = 0
    upcoming: int = 0
    waitlisted: int = 0


class MembershipRequestItem(BaseModel):
    id: UUID
    membership_id: UUID
    request_type: str
    status: str
    reason: str
    outcome: str | None = None
    decision_reason: str | None = None
    requested_start_date: date | None = None
    requested_end_date: date | None = None
    created_at: datetime
    reviewed_at: datetime | None = None


class MembershipApprovalItem(MembershipRequestItem):
    user_id: UUID
    user_name: str
    user_email: str


class MembershipApprovalPage(BaseModel):
    items: list[MembershipApprovalItem]
    page: PageInfo


class AuditListItem(BaseModel):
    id: UUID
    action: str
    actor_user_id: UUID | None
    actor_name: str | None
    target_user_id: UUID | None
    target_name: str | None
    entity_type: str
    entity_id: str | None
    reason: str | None
    outcome: str | None
    summary: str
    created_at: datetime


class AdminMemberDetailResponse(BaseModel):
    profile: UserPublic
    memberships: list[MembershipRecord]
    payments: list[AdminPaymentRecord]
    invoices: list[AdminInvoiceRecord]
    attendance_summary: AttendanceSummary
    attendance_history: list[AttendanceHistorySummaryItem]
    booking_summary: BookingSummary
    membership_requests: list[MembershipRequestItem]
    audit_logs: list[AuditListItem]


class FreezeRequestCreate(BaseModel):
    requested_start_date: date
    requested_end_date: date
    reason: str = Field(min_length=10, max_length=1000)

    @model_validator(mode="after")
    def validate_dates(self) -> "FreezeRequestCreate":
        if self.requested_end_date < self.requested_start_date:
            raise ValueError("Freeze end date must be on or after the start date.")
        if (self.requested_end_date - self.requested_start_date).days + 1 > 90:
            raise ValueError("Freeze requests cannot exceed 90 days.")
        return self


class CancellationRequestCreate(BaseModel):
    reason: str = Field(min_length=10, max_length=1000)


class RequestDecision(BaseModel):
    approve: bool
    decision_reason: str = Field(min_length=10, max_length=1000)
    outcome: str | None = None

    @model_validator(mode="after")
    def validate_outcome(self) -> "RequestDecision":
        allowed = {"refund", "account_credit", "forfeit"}
        if self.approve and self.outcome not in allowed:
            raise ValueError("Approved cancellations require refund, account_credit, or forfeit.")
        if not self.approve and self.outcome is not None:
            raise ValueError("Rejected requests cannot have a financial outcome.")
        return self


class FreezeDecision(BaseModel):
    approve: bool
    decision_reason: str = Field(min_length=10, max_length=1000)


class RevokeMembershipRequest(BaseModel):
    reason: str = Field(min_length=10, max_length=1000)


class AdminBillingPaymentItem(BaseModel):
    payment_id: UUID
    user_id: UUID
    member_name: str
    member_email: str
    member_tier: str
    plan_name: str
    amount: Decimal
    discount_amount: Decimal
    status: str
    created_at: datetime


class AdminBillingInvoiceItem(BaseModel):
    invoice_id: UUID
    user_id: UUID
    member_name: str
    member_email: str
    invoice_number: str
    plan_name: str
    amount: Decimal
    transaction_date: datetime


class AdminBillingPaymentPage(BaseModel):
    items: list[AdminBillingPaymentItem]
    page: PageInfo
    total_amount: Decimal


class AdminBillingInvoicePage(BaseModel):
    items: list[AdminBillingInvoiceItem]
    page: PageInfo
    total_amount: Decimal


class AuditLogPage(BaseModel):
    items: list[AuditListItem]
    page: PageInfo


class ConfigurationItem(BaseModel):
    key: str
    value: int
    description: str | None
    updated_at: datetime


class ConfigurationUpdateRequest(BaseModel):
    value: int


class OperationMessage(BaseModel):
    message: str
    code: str


class ModelFromAttributes(BaseModel):
    model_config = ConfigDict(from_attributes=True)
