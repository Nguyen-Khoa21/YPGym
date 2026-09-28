import asyncio
import html
import logging
import secrets
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
from app.repositories.email_delivery_repository import EmailDeliveryRepository
from app.repositories.identity_repository import OAuthPendingLinkRepository
from app.repositories.operations_repository import NotificationRepository
from app.services.invoice_service import format_vnd
from app.utils.security import generate_url_token, hash_token

logger = logging.getLogger(__name__)


class EmailTransport(Protocol):
    def send(self, message: EmailMessage) -> str | None: ...


class ConfiguredEmailTransport:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def send(self, message: EmailMessage) -> str | None:
        if self.settings.EMAIL_DELIVERY_MODE == "development":
            return self._write_development_message(message)
        return self._send_smtp(message)

    def _write_development_message(self, message: EmailMessage) -> str:
        directory = Path(self.settings.DEVELOPMENT_MAIL_DIR)
        directory.parent.mkdir(parents=True, exist_ok=True)
        outbox = Maildir(directory, create=True)
        try:
            return outbox.add(message)
        finally:
            outbox.close()

    def _send_smtp(self, message: EmailMessage) -> str | None:
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
            refused = client.send_message(message)
            if refused:
                raise smtplib.SMTPRecipientsRefused(refused)
        return message.get("Message-ID")


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
        self.deliveries = EmailDeliveryRepository(session)
        self.pending_links = OAuthPendingLinkRepository(session)
        self.transport = transport or ConfiguredEmailTransport(self.settings)

    async def deliver_pending_welcome_emails(self) -> int:
        delivered = 0
        for _ in range(self.settings.EMAIL_DELIVERY_BATCH_SIZE):
            now = datetime.now(UTC)
            candidate = await self.notifications.next_auth_email_for_delivery(
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
                message = self._welcome_message(notification, user) if notification.notification_type == "registration_welcome" else self._security_message(notification, user)
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

    async def deliver_pending_oauth_link_emails(self) -> int:
        delivered = 0
        for _ in range(self.settings.EMAIL_DELIVERY_BATCH_SIZE):
            now = datetime.now(UTC)
            item = await self.pending_links.claim_email(now=now, max_attempts=self.settings.EMAIL_MAX_DELIVERY_ATTEMPTS)
            if item is None:
                await self.session.rollback()
                break
            item_id = item.id
            token = generate_url_token()
            item.email_token_hash = hash_token(token)
            await self.session.commit()
            item = await self.pending_links.get_by_id(item_id)
            user = await self.session.get(User, item.user_id) if item else None
            if item is None or user is None:
                continue
            try:
                message = self._oauth_link_confirmation_message(item, user, token)
                await asyncio.to_thread(self.transport.send, message)
            except Exception as exc:
                locked = await self.pending_links.get_by_id(item_id, for_update=True)
                if locked is None:
                    await self.session.rollback()
                    continue
                exhausted = locked.email_attempt_count >= self.settings.EMAIL_MAX_DELIVERY_ATTEMPTS
                locked.email_delivery_state = "failed" if exhausted else "retrying"
                locked.email_error_code = type(exc).__name__[:64]
                if not exhausted:
                    locked.email_next_attempt_at = datetime.now(UTC) + timedelta(
                        seconds=self.settings.EMAIL_RETRY_DELAY_SECONDS,
                    )
                await self.session.commit()
                logger.warning(
                    "oauth_link_email_delivery_failed pending_id=%s attempt=%s exception_type=%s",
                    item_id,
                    locked.email_attempt_count,
                    type(exc).__name__,
                )
                continue
            locked = await self.pending_links.get_by_id(item_id, for_update=True)
            if locked is None:
                await self.session.rollback()
                continue
            locked.email_delivery_state = "sent"
            locked.email_sent_at = datetime.now(UTC)
            locked.email_next_attempt_at = None
            locked.email_error_code = None
            await self.session.commit()
            delivered += 1
        return delivered

    async def deliver_pending_membership_emails(self) -> int:
        sent = 0
        for _ in range(self.settings.EMAIL_DELIVERY_BATCH_SIZE):
            delivery = await self.deliveries.claim_next(max_attempts=self.settings.EMAIL_MAX_DELIVERY_ATTEMPTS)
            if delivery is None:
                await self.session.rollback()
                break
            delivery_id = delivery.id
            await self.session.commit()  # Release the row lock before external I/O.
            context = await self.deliveries.get_context(delivery_id)
            if context is None:
                continue
            delivery, user, membership, payment, invoice = context
            try:
                message = self._membership_message(delivery, user, membership, payment, invoice)
                provider_reference = await asyncio.to_thread(self.transport.send, message)
            except Exception as exc:  # Never persist provider text, recipient, or credentials.
                locked = await self.deliveries.get_for_update(delivery_id)
                if locked is None:
                    await self.session.rollback()
                    continue
                permanent = isinstance(exc, smtplib.SMTPRecipientsRefused)
                exhausted = locked.attempt_count >= self.settings.EMAIL_MAX_DELIVERY_ATTEMPTS
                locked.status = "failed" if permanent or exhausted else "retrying"
                locked.last_error_category = "invalid_recipient" if permanent else "provider_unavailable"
                locked.last_error_code = type(exc).__name__[:64]
                if locked.status == "retrying":
                    base_delay = min(
                        self.settings.EMAIL_RETRY_DELAY_SECONDS * (2 ** max(0, locked.attempt_count - 1)),
                        86400,
                    )
                    jitter = secrets.randbelow(min(60, max(1, base_delay // 4)) + 1)
                    delay = min(base_delay + jitter, 86400)
                    locked.next_attempt_at = datetime.now(UTC) + timedelta(seconds=delay)
                await self.session.commit()
                logger.warning(
                    "membership_email_delivery_failed delivery_id=%s attempt=%s exception_type=%s",
                    delivery_id,
                    locked.attempt_count,
                    type(exc).__name__,
                )
                continue

            locked = await self.deliveries.get_for_update(delivery_id)
            if locked is None:
                await self.session.rollback()
                continue
            locked.status = "sent_to_provider"
            locked.sent_to_provider_at = datetime.now(UTC)
            locked.next_attempt_at = None
            locked.last_error_category = None
            locked.last_error_code = None
            locked.provider_message_id = provider_reference[:255] if provider_reference else None
            await self.session.commit()
            sent += 1
        return sent

    def _membership_message(self, delivery, user, membership, payment, invoice) -> EmailMessage:
        is_invoice = delivery.template_type == "membership_invoice"
        action = "renewal" if delivery.template_type == "membership_renewal" else "purchase"
        invoice_url = f"{self.settings.FRONTEND_URL.rstrip('/')}/app/billing"
        duration_days = (invoice.membership_expiry_date - invoice.membership_start_date).days + 1
        total = format_vnd(invoice.amount)
        discount = format_vnd(invoice.discount_amount)
        title = f"YPGym invoice {invoice.invoice_number}" if is_invoice else f"YPGym membership {action} confirmed"
        sender_domain = self.settings.EMAIL_SENDER_ADDRESS.rsplit("@", 1)[-1] or "example.com"
        message = EmailMessage()
        message["From"] = formataddr((self.settings.EMAIL_SENDER_NAME, self.settings.EMAIL_SENDER_ADDRESS))
        message["To"] = delivery.recipient_email
        message["Subject"] = title
        message["Date"] = format_datetime(datetime.now(UTC))
        message["Message-ID"] = f"<{delivery.idempotency_key.replace(':', '.')}@{sender_domain}>"
        if self.settings.EMAIL_REPLY_TO:
            message["Reply-To"] = self.settings.EMAIL_REPLY_TO
        plain = (
            f"Hi {user.name},\n\n"
            f"Your YPGym membership {action} was successful.\n"
            f"Plan: {invoice.plan_name} ({duration_days} days)\n"
            f"Coverage: {invoice.membership_start_date.isoformat()} to {invoice.membership_expiry_date.isoformat()}\n"
            f"Membership status: {membership.status}\n"
            f"Invoice: {invoice.invoice_number}\n"
            f"Discount: {discount}\nTotal paid: {total}\n"
            f"Payment status/reference: {payment.status} / {payment.mock_reference}\n"
            f"Transaction: {invoice.transaction_date.isoformat()}\n"
            f"View your invoice and membership: {invoice_url}\n\n"
            "Contact the gym team if any detail is incorrect. This mailbox may not be monitored.\n\nYPGym Team\n"
        )
        message.set_content(plain)
        safe = {key: html.escape(str(value), quote=True) for key, value in {
            "name": user.name, "action": action, "plan": invoice.plan_name, "days": duration_days,
            "start": invoice.membership_start_date, "end": invoice.membership_expiry_date,
            "status": membership.status, "invoice": invoice.invoice_number, "discount": discount,
            "total": total, "payment": payment.status, "reference": payment.mock_reference,
            "transaction": invoice.transaction_date.isoformat(), "url": invoice_url,
        }.items()}
        message.add_alternative(
            "<!doctype html><html><body>"
            f"<p>Hi {safe['name']},</p><p>Your YPGym membership {safe['action']} was successful.</p>"
            f"<ul><li>Plan: {safe['plan']} ({safe['days']} days)</li><li>Coverage: {safe['start']} to {safe['end']}</li>"
            f"<li>Status: {safe['status']}</li><li>Invoice: {safe['invoice']}</li><li>Discount: {safe['discount']}</li>"
            f"<li>Total paid: {safe['total']}</li><li>Payment: {safe['payment']} / {safe['reference']}</li>"
            f"<li>Transaction: {safe['transaction']}</li></ul><p><a href=\"{safe['url']}\">View invoice and membership</a></p>"
            "<p>Contact the gym team if any detail is incorrect. This mailbox may not be monitored.</p><p>YPGym Team</p>"
            "</body></html>",
            subtype="html",
        )
        if is_invoice:
            pdf_path = Path(invoice.pdf_path)
            with pdf_path.open("rb") as attachment:
                message.add_attachment(
                    attachment.read(),
                    maintype="application",
                    subtype="pdf",
                    filename=f"{invoice.invoice_number}.pdf",
                )
        return message

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

    def _security_message(self, notification: Notification, user: User) -> EmailMessage:
        message = self._base_message(user.email, notification.title, f"security.{notification.id}")
        message.set_content(f"Hi {user.name},\n\n{notification.message}\n\nYPGym Team\n")
        message.add_alternative(
            "<!doctype html><html><body>"
            f"<p>Hi {html.escape(user.name, quote=True)},</p>"
            f"<p>{html.escape(notification.message, quote=True)}</p>"
            "<p>YPGym Team</p></body></html>",
            subtype="html",
        )
        return message

    def _oauth_link_confirmation_message(self, item, user: User, token: str) -> EmailMessage:
        link = f"{self.settings.FRONTEND_URL.rstrip('/')}/auth/link-account?email_token={token}"
        provider = item.provider.title()
        message = self._base_message(user.email, f"Confirm {provider} sign-in for YPGym", f"oauth-link.{item.id}")
        message.set_content(
            f"Hi {user.name},\n\nConfirm connecting {provider} sign-in to your YPGym account:\n{link}\n\n"
            "This single-use link expires shortly. If you did not request it, ignore this message.\n\nYPGym Team\n",
        )
        message.add_alternative(
            "<!doctype html><html><body>"
            f"<p>Hi {html.escape(user.name, quote=True)},</p>"
            f"<p>Confirm connecting {provider} sign-in to your YPGym account.</p>"
            f'<p><a href="{html.escape(link, quote=True)}">Confirm secure account link</a></p>'
            "<p>This single-use link expires shortly. If you did not request it, ignore this message.</p>"
            "<p>YPGym Team</p></body></html>",
            subtype="html",
        )
        return message

    def _base_message(self, recipient: str, subject: str, message_key: str) -> EmailMessage:
        sender_domain = self.settings.EMAIL_SENDER_ADDRESS.rsplit("@", 1)[-1] or "example.com"
        message = EmailMessage()
        message["From"] = formataddr((self.settings.EMAIL_SENDER_NAME, self.settings.EMAIL_SENDER_ADDRESS))
        message["To"] = recipient
        message["Subject"] = subject
        message["Date"] = format_datetime(datetime.now(UTC))
        message["Message-ID"] = f"<{message_key}@{sender_domain}>"
        if self.settings.EMAIL_REPLY_TO:
            message["Reply-To"] = self.settings.EMAIL_REPLY_TO
        return message
