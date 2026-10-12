from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schemas.membership_schema import AttendanceBenefitQuote


class VNPayCreateRequest(BaseModel):
    membership_plan_id: UUID
    locale: Literal["vn", "en"] = "vn"
    bank_code: Literal["VNPAYQR", "VNBANK", "INTCARD"] | None = None
    client_platform: Literal["web", "mobile", "mobile_web"] = "web"

    model_config = ConfigDict(extra="forbid")


class VNPayCreateResponse(BaseModel):
    transaction_id: UUID
    txn_ref: str
    payment_url: str
    expires_at: datetime


class PaymentStatusResponse(BaseModel):
    id: UUID
    product_type: str
    membership_plan_id: UUID | None
    class_booking_id: UUID | None
    product_name: str
    plan_name: str | None
    provider: str
    txn_ref: str
    status: str
    amount_vnd: int
    currency: str
    membership_status: str | None
    membership_start_date: date | None
    membership_expiry_date: date | None
    booking_status: str | None
    refund_status: str | None
    class_start_at: datetime | None
    class_end_at: datetime | None
    invoice_id: UUID | None
    invoice_download_url: str | None
    created_at: datetime
    paid_at: datetime | None
    expires_at: datetime | None
    discount_details: AttendanceBenefitQuote | None


class VNPayIpnResponse(BaseModel):
    RspCode: str
    Message: str
