from math import ceil
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError, ResourceNotFoundError
from app.models.user import User
from app.repositories.email_delivery_repository import EmailDeliveryRepository
from app.repositories.operations_repository import AuditRepository
from app.schemas.email_delivery_schema import EmailDeliveryItem, EmailDeliveryPage, EmailDeliveryRetryResponse


class EmailDeliveryAdminService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.deliveries = EmailDeliveryRepository(session)

    def _item(self, delivery, user, invoice) -> EmailDeliveryItem:
        return EmailDeliveryItem(
            id=delivery.id,
            user_id=user.id,
            member_name=user.name,
            recipient_masked=delivery.recipient_masked,
            template_type=delivery.template_type,
            status=delivery.status,
            attempt_count=delivery.attempt_count,
            queued_at=delivery.created_at,
            last_attempt_at=delivery.last_attempt_at,
            sent_to_provider_at=delivery.sent_to_provider_at,
            next_attempt_at=delivery.next_attempt_at,
            last_error_category=delivery.last_error_category,
            invoice_id=invoice.id,
            invoice_number=invoice.invoice_number,
        )

    async def list(self, *, page: int, page_size: int, status: str | None, template_type: str | None, member: str | None) -> EmailDeliveryPage:
        rows, total = await self.deliveries.list_admin(
            page=page, page_size=page_size, status=status, template_type=template_type, member=member
        )
        return EmailDeliveryPage(
            items=[self._item(*row) for row in rows],
            page=page,
            page_size=page_size,
            total=total,
            pages=ceil(total / page_size) if total else 0,
        )

    async def retry(self, *, delivery_id: UUID, actor: User) -> EmailDeliveryRetryResponse:
        delivery = await self.deliveries.get_for_update(delivery_id)
        if delivery is None:
            raise ResourceNotFoundError("Email delivery was not found.")
        if delivery.status != "failed":
            raise AppError("EMAIL_RETRY_NOT_ALLOWED", "Only failed email deliveries can be retried.", 409)
        delivery.status = "queued"
        delivery.next_attempt_at = None
        delivery.last_error_category = None
        delivery.last_error_code = None
        await AuditRepository(self.session).create(
            actor_user_id=actor.id,
            target_user_id=delivery.user_id,
            action="email_delivery.retry_queued",
            entity_type="email_delivery",
            entity_id=str(delivery.id),
            outcome="queued",
            summary="An authorized operator queued a failed transactional email for retry.",
        )
        await self.session.commit()
        context = await self.deliveries.get_context(delivery.id)
        if context is None:
            raise ResourceNotFoundError("Email delivery was not found.")
        delivery, user, _membership, _payment, invoice = context
        return EmailDeliveryRetryResponse(message="Email delivery queued for retry.", delivery=self._item(delivery, user, invoice))
