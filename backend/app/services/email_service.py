import asyncio
import html
import logging
import smtplib
import ssl
from datetime import UTC, datetime, timedelta
from email.message import EmailMessage
from email.utils import format_datetime, formataddr
from mailbox import Maildir
from pathlib import Path
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.models.operations import Notification
from app.models.user import User
from app.repositories.operations_repository import NotificationRepository

logger = logging.getLogger(__name__)


class EmailTransport(Protocol):
    def send(self, message: EmailMessage) -> None: ...


class ConfiguredEmailTransport:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def send(self, message: EmailMessage) -> None:
        if self.settings.EMAIL_DELIVERY_MODE == "development":
            self._write_development_message(message)
            return
        self._send_smtp(message)

    def _write_development_message(self, message: EmailMessage) -> None:
        directory = Path(self.settings.DEVELOPMENT_MAIL_DIR)
        directory.parent.mkdir(parents=True, exist_ok=True)
        outbox = Maildir(directory, create=True)
        try:
            outbox.add(message)
        finally:
            outbox.close()

    def _send_smtp(self, message: EmailMessage) -> None:
        settings = self.settings
        context = ssl.create_default_context()
        smtp_type = smtplib.SMTP_SSL if settings.SMTP_TLS_MODE == "ssl" else smtplib.SMTP
        kwargs = {
            "host": settings.SMTP_HOST,
            "port": settings.SMTP_PORT,
            "timeout": settings.SMTP_TIMEOUT_SECONDS,
        }
        if settings.SMTP_TLS_MODE == "ssl":
            kwargs["context"] = context
        with smtp_type(**kwargs) as client:
            if settings.SMTP_TLS_MODE == "starttls":
                client.starttls(context=context)
            if settings.SMTP_USERNAME:
                client.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD.get_secret_value())
            client.send_message(message)


class EmailDeliveryService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        settings: Settings | None = None,
        transport: EmailTransport | None = None,
    ) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.notifications = NotificationRepository(session)
        self.transport = transport or ConfiguredEmailTransport(self.settings)

    async def deliver_pending_welcome_emails(self) -> int:
        delivered = 0
        for _ in range(self.settings.EMAIL_DELIVERY_BATCH_SIZE):
            now = datetime.now(UTC)
            candidate = await self.notifications.next_welcome_email_for_delivery(
                retry_before=now - timedelta(seconds=self.settings.EMAIL_RETRY_DELAY_SECONDS),
                max_attempts=self.settings.EMAIL_MAX_DELIVERY_ATTEMPTS,
            )
            if candidate is None:
                await self.session.rollback()
                break

            notification, user = candidate
            notification.delivery_attempts += 1
            notification.last_delivery_attempt_at = now
            try:
                message = self._welcome_message(notification, user)
                await asyncio.to_thread(self.transport.send, message)
            except Exception as exc:  # Transport failures must not expose recipient or credentials.
                if notification.delivery_attempts >= self.settings.EMAIL_MAX_DELIVERY_ATTEMPTS:
                    notification.delivery_state = "skipped"
                await self.session.commit()
                logger.warning(
                    "welcome_email_delivery_failed notification_id=%s attempt=%s exception_type=%s",
                    notification.id,
                    notification.delivery_attempts,
                    type(exc).__name__,
                )
                continue

            notification.delivery_state = "delivered"
            notification.delivered_at = datetime.now(UTC)
            await self.session.commit()
            delivered += 1
        return delivered

    def _welcome_message(self, notification: Notification, user: User) -> EmailMessage:
        login_url = f"{self.settings.FRONTEND_URL.rstrip('/')}/login"
        sender = formataddr((self.settings.EMAIL_SENDER_NAME, self.settings.EMAIL_SENDER_ADDRESS))
        sender_domain = self.settings.EMAIL_SENDER_ADDRESS.rsplit("@", 1)[-1] or "example.com"
        safe_name = html.escape(user.name, quote=True)
        safe_login_url = html.escape(login_url, quote=True)

        message = EmailMessage()
        message["From"] = sender
        message["To"] = user.email
        message["Subject"] = notification.title
        message["Date"] = format_datetime(datetime.now(UTC))
        message["Message-ID"] = f"<registration-welcome.{user.id}@{sender_domain}>"
        message.set_content(
            f"Hi {user.name},\n\n"
            "Welcome to YPGym. Verify your email using the separate verification message, then sign in to "
            "view membership plans and member features.\n\n"
            f"Sign in: {login_url}\n\n"
            "YPGym Team\n",
        )
        message.add_alternative(
            "<!doctype html><html><body>"
            f"<p>Hi {safe_name},</p>"
            "<p>Welcome to YPGym. Verify your email using the separate verification message, then sign in "
            "to view membership plans and member features.</p>"
            f'<p><a href="{safe_login_url}">Sign in to YPGym</a></p>'
            "<p>YPGym Team</p>"
            "</body></html>",
            subtype="html",
        )
        return message
