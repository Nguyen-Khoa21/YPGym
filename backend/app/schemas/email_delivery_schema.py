from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class EmailDeliveryItem(BaseModel):
    id: UUID
    user_id: UUID
    member_name: str
    recipient_masked: str
    template_type: str
    status: str
    attempt_count: int
    queued_at: datetime
    last_attempt_at: datetime | None
    sent_to_provider_at: datetime | None
    next_attempt_at: datetime | None
    last_error_category: str | None
    invoice_id: UUID
    invoice_number: str


class EmailDeliveryPage(BaseModel):
    items: list[EmailDeliveryItem]
    page: int
    page_size: int
    total: int
    pages: int


class EmailDeliveryRetryResponse(BaseModel):
    message: str
    delivery: EmailDeliveryItem
