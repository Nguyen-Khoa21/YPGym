import base64
import hashlib
import hmac
import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from secrets import token_urlsafe
from urllib.parse import urlencode
from uuid import UUID

import httpx
from jose import JWTError, jwk, jwt
from redis.asyncio import Redis
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.exceptions import AppError, AuthenticationError
from app.models.enums import MemberTier, UserRole
from app.models.identity import OAuthPendingLink
from app.models.user import User
from app.repositories.identity_repository import ExternalIdentityRepository, OAuthPendingLinkRepository
from app.repositories.operations_repository import AuditRepository, NotificationRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth_schema import LoginResponse, UserPublic
from app.schemas.identity_schema import IdentityItem, IdentityListResponse, OAuthStartResponse, ProviderStatus
from app.services.auth_service import AuthService
from app.utils.security import create_access_token, generate_url_token, hash_token, verify_password

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ProviderProfile:
    subject: str
    email: str | None
    name: str
    email_verified: bool


@dataclass(frozen=True)
class PendingLinkResult:
    code: str


class OAuthProviderClient:
    def __init__(self, settings: Settings, redis: Redis) -> None:
        self.settings = settings
        self.redis = redis

    async def validate(self, *, provider: str, code: str, redirect_uri: str, verifier: str, nonce: str) -> ProviderProfile:
        if provider == "google":
            return await self._google(code=code, redirect_uri=redirect_uri, verifier=verifier, nonce=nonce)
        return await self._facebook(code=code, redirect_uri=redirect_uri, verifier=verifier)

    async def _google(self, *, code: str, redirect_uri: str, verifier: str, nonce: str) -> ProviderProfile:
        settings = self.settings

        def validation_error(stage: str) -> AuthenticationError:
            logger.warning("oauth_google_validation_failed stage=%s", stage)
            return AuthenticationError("The Google sign-in response could not be validated.")

        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post("https://oauth2.googleapis.com/token", data={
                "client_id": settings.GOOGLE_OAUTH_WEB_CLIENT_ID,
                "client_secret": settings.GOOGLE_OAUTH_WEB_CLIENT_SECRET.get_secret_value(),
                "code": code,
                "code_verifier": verifier,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri,
            })
            if response.status_code != 200:
                raise validation_error("token_exchange")
            token_data = response.json()
            id_token = token_data.get("id_token")
            if not isinstance(id_token, str):
                raise validation_error("missing_id_token")
            access_token = token_data.get("access_token")
            if not isinstance(access_token, str):
                raise validation_error("missing_access_token")
            keys_raw = await self.redis.get("ypgym:oauth:google:jwks")
            if keys_raw:
                keys = json.loads(keys_raw)
            else:
                keys_response = await client.get("https://www.googleapis.com/oauth2/v3/certs")
                keys_response.raise_for_status()
                keys = keys_response.json()
                await self.redis.set("ypgym:oauth:google:jwks", json.dumps(keys), ex=3600)
        try:
            header = jwt.get_unverified_header(id_token)
            key_data = next((item for item in keys["keys"] if item.get("kid") == header.get("kid")), None)
            if key_data is None:
                async with httpx.AsyncClient(timeout=10) as client:
                    keys_response = await client.get("https://www.googleapis.com/oauth2/v3/certs")
                    keys_response.raise_for_status()
                    keys = keys_response.json()
                    await self.redis.set("ypgym:oauth:google:jwks", json.dumps(keys), ex=3600)
                key_data = next(item for item in keys["keys"] if item.get("kid") == header.get("kid"))
            claims = jwt.decode(
                id_token,
                jwk.construct(key_data).to_pem(),
                algorithms=["RS256"],
                audience=settings.GOOGLE_OAUTH_WEB_CLIENT_ID,
                access_token=access_token,
            )
        except (JWTError, KeyError, StopIteration, TypeError, ValueError) as exc:
            await self.redis.delete("ypgym:oauth:google:jwks")
            raise validation_error("id_token_signature_or_claims") from exc
        if claims.get("iss") not in ("https://accounts.google.com", "accounts.google.com"):
            raise validation_error("issuer")
        if claims.get("nonce") != nonce or not isinstance(claims.get("sub"), str):
            raise validation_error("nonce_or_subject")
        issued_at = int(claims.get("iat", 0))
        if abs(int(datetime.now(UTC).timestamp()) - issued_at) > 600:
            raise validation_error("issued_at")
        return ProviderProfile(
            subject=claims["sub"],
            email=claims.get("email") if isinstance(claims.get("email"), str) else None,
            name=claims.get("name") if isinstance(claims.get("name"), str) else "YPGym member",
            email_verified=claims.get("email_verified") is True,
        )

    async def _facebook(self, *, code: str, redirect_uri: str, verifier: str) -> ProviderProfile:
        settings = self.settings
        version = settings.FACEBOOK_GRAPH_API_VERSION
        secret = settings.FACEBOOK_APP_SECRET.get_secret_value()
        async with httpx.AsyncClient(timeout=10) as client:
            token_response = await client.get(f"https://graph.facebook.com/{version}/oauth/access_token", params={
                "client_id": settings.FACEBOOK_APP_ID,
                "client_secret": secret,
                "redirect_uri": redirect_uri,
                "code": code,
                "code_verifier": verifier,
            })
            if token_response.status_code != 200:
                raise AuthenticationError("The Facebook sign-in response could not be validated.")
            access_token = token_response.json().get("access_token")
            if not isinstance(access_token, str):
                raise AuthenticationError("The Facebook sign-in response could not be validated.")
            debug = await client.get("https://graph.facebook.com/debug_token", params={
                "input_token": access_token,
                "access_token": f"{settings.FACEBOOK_APP_ID}|{secret}",
            })
            debug_data = debug.json().get("data", {}) if debug.status_code == 200 else {}
            if not debug_data.get("is_valid") or str(debug_data.get("app_id")) != settings.FACEBOOK_APP_ID:
                raise AuthenticationError("The Facebook sign-in response could not be validated.")
            subject = str(debug_data.get("user_id", ""))
            if not subject:
                raise AuthenticationError("The Facebook sign-in response could not be validated.")
            proof = hmac.new(secret.encode(), access_token.encode(), hashlib.sha256).hexdigest()
            profile_response = await client.get(f"https://graph.facebook.com/{version}/me", params={
                "fields": "id,name,email", "access_token": access_token, "appsecret_proof": proof,
            })
            profile = profile_response.json() if profile_response.status_code == 200 else {}
        if str(profile.get("id", "")) != subject:
            raise AuthenticationError("The Facebook sign-in response could not be validated.")
        return ProviderProfile(
            subject=subject,
            email=profile.get("email") if isinstance(profile.get("email"), str) else None,
            name=profile.get("name") if isinstance(profile.get("name"), str) else "YPGym member",
            # Meta returns this field only when the app has email permission and
            # the account has a usable confirmed email.
            email_verified=isinstance(profile.get("email"), str),
        )


class OAuthService:
    PROVIDERS = ("google", "facebook")

    def __init__(self, session: AsyncSession, redis: Redis, *, settings: Settings | None = None) -> None:
        self.session = session
        self.redis = redis
        self.settings = settings or get_settings()
        self.users = UserRepository(session)
        self.identities = ExternalIdentityRepository(session)
        self.pending_links = OAuthPendingLinkRepository(session)
        self.audit = AuditRepository(session)
        self.notifications = NotificationRepository(session)
        self.client = OAuthProviderClient(self.settings, redis)

    def providers(self) -> list[ProviderStatus]:
        return [ProviderStatus(provider=name, enabled=self._configured(name)) for name in self.PROVIDERS]

    def _configured(self, provider: str) -> bool:
        if provider == "google":
            return bool(self.settings.GOOGLE_OAUTH_WEB_CLIENT_ID and self.settings.GOOGLE_OAUTH_WEB_CLIENT_SECRET.get_secret_value())
        return bool(self.settings.FACEBOOK_APP_ID and self.settings.FACEBOOK_APP_SECRET.get_secret_value())

    def _callback_uri(self, provider: str) -> str:
        return f"{self.settings.OAUTH_CALLBACK_BASE_URL}/auth/oauth/{provider}/callback"

    async def start(self, *, provider: str, platform: str, purpose: str = "login", user_id: UUID | None = None) -> OAuthStartResponse:
        if provider not in self.PROVIDERS or not self._configured(provider):
            raise AppError("OAUTH_PROVIDER_UNAVAILABLE", "This sign-in provider is not configured.", 503)
        if platform not in ("web", "mobile", "mobile_web") or purpose not in ("login", "link"):
            raise AppError("INVALID_OAUTH_REQUEST", "The sign-in request is invalid.", 400)
        if purpose == "link" and user_id is None:
            raise AuthenticationError("Authentication is required to link a provider.")
        state_prefix = {"mobile": "m", "mobile_web": "x", "web": "w"}[platform]
        state = f"{state_prefix}.{generate_url_token()}"
        verifier, nonce = generate_url_token(), generate_url_token()
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
        correlation_id = token_urlsafe(12)
        payload = {"provider": provider, "platform": platform, "purpose": purpose, "user_id": str(user_id) if user_id else None, "verifier": verifier, "nonce": nonce, "correlation_id": correlation_id}
        await self.redis.set(f"ypgym:oauth:state:{hash_token(state)}", json.dumps(payload), ex=self.settings.OAUTH_STATE_TTL_SECONDS)
        logger.info("oauth_event event=start provider=%s correlation_id=%s platform=%s purpose=%s", provider, correlation_id, platform, purpose)
        redirect_uri = self._callback_uri(provider)
        if provider == "google":
            url = "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode({
                "client_id": self.settings.GOOGLE_OAUTH_WEB_CLIENT_ID, "redirect_uri": redirect_uri,
                "response_type": "code", "scope": "openid email profile", "state": state, "nonce": nonce,
                "code_challenge": challenge, "code_challenge_method": "S256", "prompt": "select_account",
            })
        else:
            url = f"https://www.facebook.com/{self.settings.FACEBOOK_GRAPH_API_VERSION}/dialog/oauth?" + urlencode({
                "client_id": self.settings.FACEBOOK_APP_ID, "redirect_uri": redirect_uri, "response_type": "code",
                "scope": "public_profile,email", "state": state, "code_challenge": challenge, "code_challenge_method": "S256",
            })
        return OAuthStartResponse(authorization_url=url)

    async def callback(self, *, provider: str, state: str, code: str | None, error: str | None) -> str:
        state_hash = hash_token(state)
        state_key = f"ypgym:oauth:state:{state_hash}"
        claim_key = f"ypgym:oauth:state-claim:{state_hash}"
        completed_key = f"ypgym:oauth:state-completed:{state_hash}"
        raw = await self.redis.get(state_key)
        if not raw:
            replayed = await self.redis.get(completed_key)
            return self._return_url(
                "mobile" if state.startswith("m.") else "mobile_web" if state.startswith("x.") else "web",
                error="oauth_callback_replayed" if replayed else "oauth_state_invalid",
            )
        if not await self.redis.set(claim_key, "1", ex=60, nx=True):
            return self._return_url("mobile" if state.startswith("m.") else "mobile_web" if state.startswith("x.") else "web", error="oauth_callback_replayed")
        flow = json.loads(raw)
        platform = flow.get("platform", "web")
        if flow.get("provider") != provider or error or not code:
            target = self._return_url(platform, error="oauth_provider_denied" if error else "oauth_state_invalid")
            await self._finish_callback(state_key, claim_key, completed_key)
            return target
        try:
            profile = await self.client.validate(
                provider=provider, code=code, redirect_uri=self._callback_uri(provider),
                verifier=flow["verifier"], nonce=flow["nonce"],
            )
            result = await self._resolve_user(provider=provider, profile=profile, flow=flow)
            if isinstance(result, PendingLinkResult):
                logger.info("oauth_event event=pending_link provider=%s correlation_id=%s", provider, flow.get("correlation_id", "unknown"))
                target = f"{self.settings.FRONTEND_URL.rstrip('/')}/auth/link-account?{urlencode({'code': result.code})}"
                await self._finish_callback(state_key, claim_key, completed_key)
                return target
            user = result
            if flow.get("purpose") == "link":
                await self._queue_security_notice(user, provider, "linked", flow.get("correlation_id", token_urlsafe(12)))
                await self.session.commit()
                target = self._return_url(platform, linked=provider)
                await self._finish_callback(state_key, claim_key, completed_key)
                return target
            exchange_code = token_urlsafe(32)
            await self.redis.set(
                f"ypgym:oauth:exchange:{hash_token(exchange_code)}",
                json.dumps({"user_id": str(user.id), "provider": provider, "platform": platform, "correlation_id": flow.get("correlation_id")}),
                ex=self.settings.OAUTH_EXCHANGE_TTL_SECONDS,
            )
            logger.info("oauth_event event=callback_success provider=%s correlation_id=%s", provider, flow.get("correlation_id", "unknown"))
            target = self._return_url(platform, provider=provider, code=exchange_code)
            await self._finish_callback(state_key, claim_key, completed_key)
            return target
        except AppError as exc:
            logger.warning("oauth_event event=callback_failed provider=%s correlation_id=%s result=%s", provider, flow.get("correlation_id", "unknown"), exc.code.lower())
            target = self._return_url(platform, error=exc.code.lower())
            await self._finish_callback(state_key, claim_key, completed_key)
            return target
        except (httpx.HTTPError, ValueError, KeyError, TypeError):
            logger.warning("oauth_event event=callback_failed provider=%s correlation_id=%s result=oauth_temporarily_unavailable", provider, flow.get("correlation_id", "unknown"))
            await self.redis.delete(claim_key)
            return self._return_url(platform, error="oauth_temporarily_unavailable")

    async def _finish_callback(self, state_key: str, claim_key: str, completed_key: str) -> None:
        async with self.redis.pipeline(transaction=True) as pipeline:
            pipeline.delete(state_key, claim_key)
            pipeline.set(completed_key, "1", ex=self.settings.OAUTH_STATE_TTL_SECONDS)
            await pipeline.execute()

    def _return_url(self, platform: str, **params: str) -> str:
        if platform == "web" and "linked" in params:
            return f"{self.settings.FRONTEND_URL.rstrip('/')}/app/security?{urlencode(params)}"
        base = (
            f"{self.settings.MOBILE_APP_URL.rstrip('/')}//oauth/callback"
            if platform == "mobile"
            else f"{self.settings.MOBILE_WEB_URL.rstrip('/')}/oauth/callback"
            if platform == "mobile_web"
            else f"{self.settings.FRONTEND_URL.rstrip('/')}/oauth/callback"
        )
        return f"{base}?{urlencode(params)}"

    async def _resolve_user(self, *, provider: str, profile: ProviderProfile, flow: dict) -> User | PendingLinkResult:
        identity = await self.identities.get_by_subject(provider, profile.subject)
        purpose = flow.get("purpose")
        if purpose == "link":
            user = await self.users.get_by_id(UUID(flow["user_id"]))
            if user is None:
                raise AuthenticationError()
            existing_owner = await self.identities.get_by_subject(provider, profile.subject, include_revoked=True)
            if existing_owner and existing_owner.user_id != user.id:
                raise AppError("IDENTITY_ALREADY_LINKED", "This provider identity is already linked.", 409)
            current = await self.identities.get_for_user_provider(user.id, provider)
            if current and current.revoked_at is None and current.provider_subject != profile.subject:
                raise AppError("PROVIDER_ALREADY_LINKED", "This account already has that provider linked.", 409)
            user_id = user.id
            try:
                await self.identities.attach(user_id=user.id, provider=provider, subject=profile.subject, email=profile.email, email_verified=profile.email_verified)
                await self.audit.create(actor_user_id=user.id, target_user_id=user.id, action="oauth.identity.linked", entity_type="external_identity", reason="Authenticated account security flow", outcome="success", summary=f"{provider.title()} sign-in was connected.")
                await self.session.flush()
                return user
            except IntegrityError:
                await self.session.rollback()
                owner = await self.identities.get_by_subject(provider, profile.subject, include_revoked=True)
                user = await self.users.get_by_id(user_id)
                if owner and owner.user_id == user_id and user:
                    return user
                raise AppError("OAUTH_IDENTITY_CONFLICT", "This provider identity is already connected to another account.", 409)
        if identity:
            user = await self.users.get_by_id(identity.user_id)
            if user is None:
                raise AuthenticationError()
            identity.provider_email = profile.email
            identity.provider_email_verified = profile.email_verified
            identity.last_login_at = datetime.now(UTC)
            await self.session.commit()
            return user
        if not profile.email:
            raise AppError("PROVIDER_EMAIL_REQUIRED", "The provider did not return a usable email address.", 400)
        if not profile.email_verified:
            raise AppError("OAUTH_EMAIL_UNVERIFIED", "The provider did not confirm this email address.", 403)
        email = profile.email.lower()
        existing_user = await self.users.get_by_email(email)
        if existing_user:
            return await self._create_pending_link(existing_user, provider, profile, flow.get("correlation_id", token_urlsafe(12)))
        try:
            user = await self.users.create(
                name=profile.name.strip()[:160] or "YPGym member", email=email, phone=None, password_hash=None,
                role=UserRole.MEMBER.value, tier=MemberTier.NORMAL.value, is_email_verified=profile.email_verified,
            )
            if profile.email_verified:
                user.email_verified_at = datetime.now(UTC)
            verification_token = None
            if not profile.email_verified:
                verification_token = await AuthService(self.session)._create_email_verification(user)
            await self.identities.attach(user_id=user.id, provider=provider, subject=profile.subject, email=email, email_verified=profile.email_verified)
            await self._queue_security_notice(user, provider, "account_created", flow.get("correlation_id", token_urlsafe(12)))
            await self.session.commit()
            if verification_token:
                try:
                    await AuthService(self.session)._prepare_development_email(
                        user.email, "Email verification", "/verify-email", verification_token
                    )
                except AppError as exc:
                    logger.warning("oauth_verification_email_failed user_id=%s exception_type=%s", user.id, type(exc).__name__)
            return user
        except IntegrityError as exc:
            await self.session.rollback()
            identity = await self.identities.get_by_subject(provider, profile.subject)
            if identity:
                user = await self.users.get_by_id(identity.user_id)
                if user:
                    return user
            existing_user = await self.users.get_by_email(email)
            if existing_user:
                return await self._create_pending_link(existing_user, provider, profile, flow.get("correlation_id", token_urlsafe(12)))
            raise AppError("OAUTH_IDENTITY_CONFLICT", "The provider account could not be attached safely.", 409) from exc

    async def _create_pending_link(
        self,
        user: User,
        provider: str,
        profile: ProviderProfile,
        correlation_id: str,
    ) -> PendingLinkResult:
        now = datetime.now(UTC)
        await self.pending_links.supersede_active(
            user_id=user.id,
            provider=provider,
            subject=profile.subject,
            now=now,
        )
        code = generate_url_token()
        self.session.add(OAuthPendingLink(
            user_id=user.id,
            provider=provider,
            provider_subject=profile.subject,
            provider_email=profile.email or user.email,
            code_hash=hash_token(code),
            correlation_id=correlation_id[:32],
            expires_at=now + timedelta(seconds=self.settings.OAUTH_LINK_TTL_SECONDS),
        ))
        await self.session.commit()
        return PendingLinkResult(code)

    @staticmethod
    def _masked_email(email: str) -> str:
        local, _, domain = email.partition("@")
        return f"{local[:1]}***@{domain}" if domain else "***"

    async def pending_link_status(self, code: str) -> dict:
        item = await self.pending_links.get_by_code_hash(hash_token(code))
        self._require_pending(item)
        user = await self.users.get_by_id(item.user_id)
        if user is None:
            raise AppError("OAUTH_LINK_EXPIRED", "This account-link request is no longer available.", 410)
        return {
            "provider": item.provider,
            "masked_email": self._masked_email(user.email),
            "password_confirmation_available": bool(user.password_hash),
            "email_confirmation_available": user.is_email_verified,
            "expires_at": item.expires_at,
        }

    def _require_pending(self, item: OAuthPendingLink | None) -> OAuthPendingLink:
        if item is None:
            raise AppError("OAUTH_LINK_EXPIRED", "This account-link request is invalid or expired.", 410)
        if item.consumed_at is not None:
            code = "OAUTH_LINK_ALREADY_USED" if item.link_method != "superseded" else "OAUTH_LINK_EXPIRED"
            raise AppError(code, "This account-link request has already been used or replaced.", 409)
        if item.expires_at <= datetime.now(UTC):
            raise AppError("OAUTH_LINK_EXPIRED", "This account-link request has expired.", 410)
        return item

    async def confirm_pending_with_password(self, *, code: str, password: str) -> LoginResponse:
        item = self._require_pending(await self.pending_links.get_by_code_hash(hash_token(code), for_update=True))
        user = await self.users.get_by_id(item.user_id)
        if user is None:
            raise AppError("OAUTH_LINK_EXPIRED", "This account-link request is no longer available.", 410)
        if item.password_attempts >= self.settings.OAUTH_LINK_MAX_PASSWORD_ATTEMPTS:
            raise AppError("RATE_LIMITED", "Too many password attempts. Start sign-in again.", 429, {"retry_after_seconds": 60})
        if not verify_password(password, user.password_hash):
            item.password_attempts += 1
            await self.session.commit()
            raise AppError("OAUTH_LINK_PASSWORD_INVALID", "The YPGym password is incorrect.", 401)
        return await self._complete_pending(item=item, user=user, method="password")

    async def queue_pending_email(self, *, code: str) -> None:
        item = self._require_pending(await self.pending_links.get_by_code_hash(hash_token(code), for_update=True))
        user = await self.users.get_by_id(item.user_id)
        if user is None or not user.is_email_verified:
            raise AppError("OAUTH_LINK_EMAIL_UNAVAILABLE", "Email confirmation is unavailable for this account.", 409)
        if item.email_delivery_state not in ("queued", "sending"):
            item.email_delivery_state = "queued"
            item.email_next_attempt_at = datetime.now(UTC)
            item.email_token_hash = None
            item.email_error_code = None
        await self.session.commit()

    async def confirm_pending_with_email(self, token: str) -> LoginResponse:
        item = self._require_pending(
            await self.pending_links.get_by_email_token_hash(hash_token(token), for_update=True),
        )
        user = await self.users.get_by_id(item.user_id)
        if user is None or not user.is_email_verified:
            raise AppError("OAUTH_LINK_EXPIRED", "This account-link request is no longer available.", 410)
        return await self._complete_pending(item=item, user=user, method="email")

    async def _complete_pending(self, *, item: OAuthPendingLink, user: User, method: str) -> LoginResponse:
        owner = await self.identities.get_by_subject(item.provider, item.provider_subject, include_revoked=True)
        if owner and owner.user_id != user.id:
            raise AppError("OAUTH_IDENTITY_CONFLICT", "This provider identity is already connected to another account.", 409)
        current = await self.identities.get_for_user_provider(user.id, item.provider)
        if current and current.revoked_at is None and current.provider_subject != item.provider_subject:
            raise AppError("OAUTH_IDENTITY_CONFLICT", "This account already has another identity from that provider.", 409)
        pending_id = item.id
        user_id = user.id
        provider = item.provider
        subject = item.provider_subject
        provider_email = item.provider_email
        try:
            identity = await self.identities.attach(
                user_id=user_id,
                provider=provider,
                subject=subject,
                email=provider_email,
                email_verified=True,
            )
        except IntegrityError:
            await self.session.rollback()
            owner = await self.identities.get_by_subject(provider, subject, include_revoked=True)
            if owner is None or owner.user_id != user_id:
                raise AppError("OAUTH_IDENTITY_CONFLICT", "This provider identity is already connected to another account.", 409)
            identity = owner
            item = self._require_pending(await self.pending_links.get_by_id(pending_id, for_update=True))
            user = await self.users.get_by_id(user_id)
            if user is None:
                raise AppError("OAUTH_LINK_EXPIRED", "This account-link request is no longer available.", 410)
        item.consumed_at = datetime.now(UTC)
        item.link_method = method
        item.email_delivery_state = "cancelled" if item.email_delivery_state != "sent" else item.email_delivery_state
        await self.audit.create(
            actor_user_id=user.id,
            target_user_id=user.id,
            action="oauth.identity.linked",
            entity_type="external_identity",
            entity_id=str(identity.id),
            reason=f"Existing-account ownership confirmed by {method}",
            outcome="success",
            summary=f"{item.provider.title()} sign-in was connected.",
        )
        await self._queue_security_notice(user, provider, "linked", str(item.id))
        await self.session.commit()
        token, expires_at = create_access_token(user_id=user.id, role=user.role, tier=user.tier)
        logger.info("oauth_event event=link_success provider=%s correlation_id=%s method=%s", provider, item.correlation_id, method)
        return LoginResponse(access_token=token, expires_at=expires_at, user=UserPublic.model_validate(user))

    async def _queue_security_notice(self, user: User, provider: str, action: str, event_key: str) -> None:
        occurred_at = datetime.now(UTC).isoformat()
        action_text = {
            "linked": "connected",
            "unlinked": "disconnected",
            "account_created": "used to create your YPGym account",
        }[action]
        await self.notifications.create_notification_once(
            user_id=user.id,
            category="security",
            notification_type=f"oauth_provider_{action}",
            title=f"YPGym {provider.title()} security notice",
            message=(
                f"{provider.title()} sign-in was {action_text} at {occurred_at}. "
                "If this was not you, reset your password and contact YPGym support immediately."
            ),
            channel="email",
            delivery_state="pending",
            dedupe_key=f"oauth:{action}:{provider}:{event_key}"[:220],
        )

    async def exchange(self, *, provider: str, platform: str, code: str) -> LoginResponse:
        raw = await self.redis.getdel(f"ypgym:oauth:exchange:{hash_token(code)}")
        if not raw:
            raise AuthenticationError("The sign-in exchange code is invalid or expired.")
        data = json.loads(raw)
        if data.get("provider") != provider or data.get("platform") != platform:
            raise AuthenticationError("The sign-in exchange code is invalid or expired.")
        user = await self.users.get_by_id(UUID(data["user_id"]))
        if user is None:
            raise AuthenticationError()
        token, expires_at = create_access_token(user_id=user.id, role=user.role, tier=user.tier)
        logger.info("oauth_event event=login_complete provider=%s correlation_id=%s platform=%s", provider, data.get("correlation_id", "unknown"), platform)
        return LoginResponse(access_token=token, expires_at=expires_at, user=UserPublic.model_validate(user))

    async def list_identities(self, user: User) -> IdentityListResponse:
        identities = await self.identities.list_active(user.id)
        return IdentityListResponse(
            password_enabled=bool(user.password_hash),
            identities=[IdentityItem(provider=item.provider, email=item.provider_email, email_verified=item.provider_email_verified, last_login_at=item.last_login_at) for item in identities],
        )

    async def unlink(self, *, user: User, provider: str) -> IdentityListResponse:
        identity = await self.identities.get_for_user_provider(user.id, provider)
        if identity is None or identity.revoked_at is not None:
            raise AppError("IDENTITY_NOT_LINKED", "This provider is not linked.", 404)
        active = await self.identities.list_active(user.id)
        if not user.password_hash and len(active) <= 1:
            raise AppError("LAST_SIGN_IN_METHOD", "Add another sign-in method before disconnecting this provider.", 409)
        identity.revoked_at = datetime.now(UTC)
        await self.audit.create(actor_user_id=user.id, target_user_id=user.id, action="oauth.identity.unlinked", entity_type="external_identity", entity_id=str(identity.id), reason="Authenticated account security flow", outcome="success", summary=f"{provider.title()} sign-in was disconnected.")
        await self._queue_security_notice(user, provider, "unlinked", token_urlsafe(12))
        await self.session.commit()
        logger.info("oauth_event event=unlink_success provider=%s", provider)
        return await self.list_identities(user)

    def require_recent_auth(self, token: str) -> None:
        from app.utils.security import decode_access_token
        claims = decode_access_token(token)
        issued_at = claims.get("iat")
        if not isinstance(issued_at, int) or int(datetime.now(UTC).timestamp()) - issued_at > self.settings.OAUTH_RECENT_AUTH_SECONDS:
            raise AppError("RECENT_AUTH_REQUIRED", "Sign in again before changing sign-in methods.", 403)
