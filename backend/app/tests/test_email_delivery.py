from email.message import EmailMessage

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.services.email_service import ConfiguredEmailTransport


def test_smtp_transport_uses_starttls_and_configured_authentication(monkeypatch):
    calls = []

    class FakeSmtp:
        def __init__(self, **kwargs):
            calls.append(("connect", kwargs))

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            calls.append(("close",))

        def starttls(self, *, context):
            calls.append(("starttls", context is not None))

        def login(self, username, password):
            calls.append(("login", username, password))

        def send_message(self, message):
            calls.append(("send", message["Subject"]))

    monkeypatch.setattr("app.services.email_service.smtplib.SMTP", FakeSmtp)
    settings = Settings(
        _env_file=None,
        EMAIL_DELIVERY_MODE="smtp",
        EMAIL_SENDER_ADDRESS="team@example.com",
        SMTP_HOST="smtp.example.com",
        SMTP_PORT=587,
        SMTP_TLS_MODE="starttls",
        SMTP_USERNAME="mailer",
        SMTP_PASSWORD="test-app-password",
    )
    message = EmailMessage()
    message["From"] = "team@example.com"
    message["To"] = "member@example.com"
    message["Subject"] = "Welcome"
    message.set_content("Hello")

    ConfiguredEmailTransport(settings).send(message)

    assert calls[0] == (
        "connect",
        {"host": "smtp.example.com", "port": 587, "timeout": 10},
    )
    assert calls[1][0] == "starttls"
    assert calls[2] == ("login", "mailer", "test-app-password")
    assert calls[3] == ("send", "Welcome")
    assert calls[4] == ("close",)


def test_smtp_configuration_requires_host_and_paired_credentials():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, EMAIL_DELIVERY_MODE="smtp", SMTP_HOST="")
    with pytest.raises(ValidationError):
        Settings(_env_file=None, EMAIL_DELIVERY_MODE="smtp", SMTP_HOST="smtp.example.com", SMTP_USERNAME="mailer")
    with pytest.raises(ValidationError):
        Settings(_env_file=None, EMAIL_DELIVERY_MODE="smtp", SMTP_HOST="smtp.example.com", EMAIL_SENDER_ADDRESS="invalid")
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            EMAIL_DELIVERY_MODE="smtp",
            SMTP_HOST="smtp.example.com",
            SMTP_TLS_MODE="none",
            SMTP_USERNAME="mailer",
            SMTP_PASSWORD="test-app-password",
        )
