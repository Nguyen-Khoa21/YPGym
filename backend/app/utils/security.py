from datetime import UTC, datetime, timedelta
from hashlib import sha256
from secrets import token_urlsafe
from typing import Any
from uuid import UUID

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings
from app.core.exceptions import AuthenticationError

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def generate_url_token() -> str:
    return token_urlsafe(32)


def hash_token(token: str) -> str:
    return sha256(token.encode("utf-8")).hexdigest()


def create_access_token(
    *,
    user_id: UUID,
    role: str,
    tier: str,
) -> tuple[str, datetime]:
    settings = get_settings()
    expires_at = datetime.now(UTC) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
    )
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "role": role,
        "tier": tier,
        "type": "access",
        "exp": expires_at,
    }
    token = jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    return token, expires_at


def decode_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        # Older access tokens predate the type claim; retain those until expiry.
        # QR tokens share the signing key but must never authenticate API calls.
        if (
            payload.get("type") not in (None, "access")
            or "exp" not in payload
            or not all(isinstance(payload.get(claim), str) for claim in ("sub", "role", "tier"))
        ):
            raise JWTError("Invalid access token claims")
        return payload
    except (JWTError, TypeError, ValueError) as exc:
        raise AuthenticationError("The access token is invalid or expired.") from exc
