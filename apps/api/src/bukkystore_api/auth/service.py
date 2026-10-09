from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from bukkystore_api.auth.models import AdminLoginAttempt, AdminSession, AdminUser
from bukkystore_api.auth.schemas import AdminUserResponse, LoginResponse
from bukkystore_api.auth.security import hash_password, hash_token, new_token, verify_password
from bukkystore_api.config import Settings
from bukkystore_api.errors import ApiError

logger = logging.getLogger(__name__)
DUMMY_PASSWORD_HASH = hash_password("not-a-real-administrator-password")


@dataclass(frozen=True)
class IssuedSession:
    response: LoginResponse
    session_token: str
    csrf_token: str


def _public_user(user: AdminUser) -> AdminUserResponse:
    return AdminUserResponse(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        role=user.role,
    )


async def authenticate(
    session: AsyncSession,
    settings: Settings,
    *,
    email: str,
    password: str,
    network_identifier: str,
) -> IssuedSession:
    """Authenticate an admin, persist an opaque session, and audit the attempt."""

    secret = settings.session_secret.get_secret_value()
    email_hash = hash_token(email, secret)
    network_hash = hash_token(network_identifier or "unknown", secret)
    cutoff = datetime.now(UTC) - timedelta(minutes=settings.admin_login_window_minutes)
    failures = await session.scalar(
        select(func.count(AdminLoginAttempt.id)).where(
            AdminLoginAttempt.succeeded.is_(False),
            AdminLoginAttempt.created_at >= cutoff,
            or_(
                AdminLoginAttempt.email_hash == email_hash,
                AdminLoginAttempt.network_hash == network_hash,
            ),
        )
    )
    if failures is not None and failures >= settings.admin_login_max_failures:
        logger.warning("admin_login_throttled", extra={"email_hash": email_hash[:12]})
        raise ApiError(429, "login_throttled", "Too many sign-in attempts. Please try later.")

    user = await session.scalar(select(AdminUser).where(func.lower(AdminUser.email) == email))
    password_valid = verify_password(password, user.password_hash if user else DUMMY_PASSWORD_HASH)
    succeeded = bool(user and user.is_active and password_valid)
    session.add(
        AdminLoginAttempt(
            email_hash=email_hash,
            network_hash=network_hash,
            succeeded=succeeded,
        )
    )
    if not succeeded or user is None:
        await session.commit()
        logger.warning("admin_login_failed", extra={"email_hash": email_hash[:12]})
        raise ApiError(401, "invalid_credentials", "Email or password is incorrect.")

    now = datetime.now(UTC)
    expires_at = now + timedelta(hours=settings.admin_session_hours)
    session_token = new_token()
    csrf_token = new_token()
    session.add(
        AdminSession(
            user=user,
            token_hash=hash_token(session_token, secret),
            csrf_token_hash=hash_token(csrf_token, secret),
            expires_at=expires_at,
        )
    )
    user.last_login_at = now
    await session.commit()
    logger.info("admin_login_succeeded", extra={"actor_user_id": str(user.id)})
    return IssuedSession(
        response=LoginResponse(user=_public_user(user), expires_at=expires_at),
        session_token=session_token,
        csrf_token=csrf_token,
    )


async def resolve_session(
    session: AsyncSession, settings: Settings, raw_token: str | None
) -> AdminSession | None:
    if not raw_token:
        return None
    token_hash = hash_token(raw_token, settings.session_secret.get_secret_value())
    statement = (
        select(AdminSession)
        .where(
            AdminSession.token_hash == token_hash,
            AdminSession.revoked_at.is_(None),
            AdminSession.expires_at > datetime.now(UTC),
        )
        .options(joinedload(AdminSession.user))
    )
    admin_session = await session.scalar(statement)
    if admin_session is None or not admin_session.user.is_active:
        return None
    return admin_session


async def revoke_session(session: AsyncSession, admin_session: AdminSession) -> None:
    admin_session.revoked_at = datetime.now(UTC)
    await session.commit()
    logger.info("admin_logout", extra={"actor_user_id": str(admin_session.user_id)})
