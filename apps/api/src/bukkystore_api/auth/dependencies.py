from __future__ import annotations

import hmac
from dataclasses import dataclass
from typing import Annotated, cast

from fastapi import Cookie, Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from bukkystore_api.auth.models import AdminSession, AdminUser
from bukkystore_api.auth.security import hash_token
from bukkystore_api.auth.service import resolve_session
from bukkystore_api.config import Settings
from bukkystore_api.dependencies import get_session
from bukkystore_api.errors import ApiError

SESSION_COOKIE = "bukky_admin_session"
CSRF_COOKIE = "bukky_admin_csrf"


@dataclass(frozen=True)
class AdminContext:
    user: AdminUser
    session: AdminSession


def get_app_settings(request: Request) -> Settings:
    return cast(Settings, request.app.state.settings)


async def require_admin(
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_app_settings)],
    session_token: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> AdminContext:
    admin_session = await resolve_session(session, settings, session_token)
    if admin_session is None:
        raise ApiError(401, "authentication_required", "Administrator sign-in is required.")
    return AdminContext(user=admin_session.user, session=admin_session)


async def require_csrf(
    context: Annotated[AdminContext, Depends(require_admin)],
    settings: Annotated[Settings, Depends(get_app_settings)],
    csrf_cookie: Annotated[str | None, Cookie(alias=CSRF_COOKIE)] = None,
    csrf_header: Annotated[str | None, Header(alias="X-CSRF-Token")] = None,
) -> AdminContext:
    if not csrf_cookie or not csrf_header or not hmac.compare_digest(csrf_cookie, csrf_header):
        raise ApiError(403, "csrf_failed", "The security token is missing or invalid.")
    provided_hash = hash_token(csrf_header, settings.session_secret.get_secret_value())
    if not hmac.compare_digest(provided_hash, context.session.csrf_token_hash):
        raise ApiError(403, "csrf_failed", "The security token is missing or invalid.")
    return context
