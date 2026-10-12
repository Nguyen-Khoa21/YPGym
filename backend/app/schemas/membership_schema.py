from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class MembershipPlanResponse(BaseModel):
    id: UUID
    name: str
    duration_months: int
    duration_days: int
    base_price: Decimal
    discount_percent: Decimal
    final_price: Decimal
    is_active: bool
    tier_availability: str | None
    benefits: list[str]


class MembershipDiscountPricing(BaseModel):
    rule: Literal["better_of"] = "better_of"
    consumption_rule: Literal["first_successful_renewal"] = "first_successful_renewal"
    transaction_kind: Literal["purchase", "renewal"]
    base_price: Decimal
    plan_discount_percent: Decimal
    attendance_discount_percent: Decimal
    applied_discount_percent: Decimal
    attendance_benefit_selected: bool
    discount_amount: Decimal
    final_amount: Decimal


class AttendanceBenefitQuote(BaseModel):
    gym_timezone: str
    period_start: date
    period_end: date
    attended_days: int = Field(ge=0)
    period_days: int = Field(ge=28, le=31)
    attendance_percentage: Decimal
    threshold_percentage: Decimal = Decimal("80.00")
    benefit_discount_percent: Decimal = Decimal("10.00")
    attendance_qualified: bool
    available: bool
    status: Literal["eligible", "not_qualified", "not_renewal", "pending", "consumed"]
    pricing: MembershipDiscountPricing


class MembershipSummary(BaseModel):
    id: UUID
    plan_id: UUID
    plan_name: str
    status: str
    start_date: date
    expiry_date: date


class PurchaseMembershipRequest(BaseModel):
    plan_id: UUID
    idempotency_key: str = Field(min_length=8, max_length=120)
    mock_payment_confirmed: bool


class AdminMembershipEnrollmentRequest(BaseModel):
    plan_id: UUID
    idempotency_key: str = Field(min_length=8, max_length=120)
    reason: str = Field(min_length=10, max_length=500)


class PaymentSummary(BaseModel):
    id: UUID
    amount: Decimal
    discount_amount: Decimal
    status: str
    mock_reference: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InvoiceSummary(BaseModel):
    id: UUID
    invoice_number: str
    amount: Decimal
    discount_amount: Decimal
    transaction_date: datetime
    membership_start_date: date
    membership_expiry_date: date
    download_url: str


class PurchaseMembershipResponse(BaseModel):
    message: str
    membership: MembershipSummary
    payment: PaymentSummary
    invoice: InvoiceSummary
