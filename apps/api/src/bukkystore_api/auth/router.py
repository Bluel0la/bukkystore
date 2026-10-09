from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from bukkystore_api.auth.dependencies import (
    CSRF_COOKIE,
    SESSION_COOKIE,
    AdminContext,
    get_app_settings,
    require_admin,
    require_csrf,
)
from bukkystore_api.auth.schemas import AdminUserResponse, LoginRequest, LoginResponse
from bukkystore_api.auth.service import authenticate, revoke_session
from bukkystore_api.config import Settings
from bukkystore_api.dependencies import get_session
from bukkystore_api.schemas import ErrorResponse

router = APIRouter(
    prefix="/api/v1/admin/auth",
    tags=["Admin authentication"],
    responses={
        401: {"model": ErrorResponse, "description": "Authentication failed or is required."},
        403: {"model": ErrorResponse, "description": "The CSRF token is invalid."},
    },
)


@router.post(
    "/login",
    response_model=LoginResponse,
    responses={
        400: {"model": ErrorResponse, "description": "The request body is malformed."},
        401: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
    },
    summary="Sign in an administrator",
)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> LoginResponse:
    issued = await authenticate(
        session,
        settings,
        email=payload.email,
        password=payload.password,
        network_identifier=request.client.host if request.client else "unknown",
    )
    max_age = settings.admin_session_hours * 60 * 60
    secure = settings.environment in {"staging", "production"}
    response.set_cookie(
        SESSION_COOKIE,
        issued.session_token,
        max_age=max_age,
        httponly=True,
        secure=secure,
        samesite="strict",
        path="/",
    )
    response.set_cookie(
        CSRF_COOKIE,
        issued.csrf_token,
        max_age=max_age,
        httponly=False,
        secure=secure,
        samesite="strict",
        path="/",
    )
    return issued.response


@router.get("/me", response_model=AdminUserResponse, summary="Get the signed-in administrator")
async def me(context: Annotated[AdminContext, Depends(require_admin)]) -> AdminUserResponse:
    return AdminUserResponse(
        id=context.user.id,
        email=context.user.email,
        display_name=context.user.display_name,
        role=context.user.role,
    )


@router.post("/logout", status_code=204, summary="Revoke the current administrator session")
async def logout(
    response: Response,
    session: Annotated[AsyncSession, Depends(get_session)],
    context: Annotated[AdminContext, Depends(require_csrf)],
) -> None:
    await revoke_session(session, context.session)
    response.delete_cookie(SESSION_COOKIE, path="/")
    response.delete_cookie(CSRF_COOKIE, path="/")
