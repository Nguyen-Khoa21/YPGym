from payos import APIError, AsyncPayOS, PayOSError
from payos.types import CreatePaymentLinkRequest

from app.core.config import Settings
from app.core.exceptions import AppError


class PayOSClient:
    def __init__(self, settings: Settings, client: AsyncPayOS | None = None) -> None:
        self.settings = settings
        self.client = client or AsyncPayOS(
            client_id=settings.PAYOS_CLIENT_ID.get_secret_value(),
            api_key=settings.PAYOS_API_KEY.get_secret_value(),
            checksum_key=settings.PAYOS_CHECKSUM_KEY.get_secret_value(),
            timeout=float(settings.PAYOS_TIMEOUT_SECONDS),
            max_retries=1,
        )

    async def create_payment_link(self, *, order_code: int, amount: int, description: str, expired_at: int):
        try:
            return await self.client.payment_requests.create(
                CreatePaymentLinkRequest(
                    order_code=order_code,
                    amount=amount,
                    description=description,
                    cancel_url=self.settings.PAYOS_CANCEL_URL,
                    return_url=self.settings.PAYOS_RETURN_URL,
                    expired_at=expired_at,
                )
            )
        except (APIError, PayOSError, OSError) as exc:
            raise AppError("PAYOS_UNAVAILABLE", "Payment checkout is temporarily unavailable.", 503) from exc

    async def verify_webhook(self, payload: bytes):
        return await self.client.webhooks.verify(payload)
