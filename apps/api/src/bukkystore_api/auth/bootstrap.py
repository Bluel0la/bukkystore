from __future__ import annotations

import argparse
import asyncio
import getpass

from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from bukkystore_api.auth.models import AdminUser, UserRole
from bukkystore_api.auth.schemas import LoginRequest
from bukkystore_api.auth.security import hash_password
from bukkystore_api.config import get_settings
from bukkystore_api.database import Database


async def create_admin_user(
    session: AsyncSession,
    *,
    email: str,
    display_name: str,
    role: UserRole,
    password: str,
) -> AdminUser:
    """Create an administrator through a trusted local bootstrap boundary."""

    validated = LoginRequest(email=email, password=password)
    name = display_name.strip()
    if not name or len(name) > 120:
        raise ValueError("Display name must contain between 1 and 120 characters")
    user_count = await session.scalar(select(func.count(AdminUser.id)))
    if not user_count and role is not UserRole.OWNER:
        raise ValueError("The first administrator must have the OWNER role")
    user = AdminUser(
        email=validated.email,
        password_hash=hash_password(validated.password),
        display_name=name,
        role=role,
        is_active=True,
    )
    session.add(user)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise ValueError("An administrator with that email already exists") from exc
    return user


async def _run(args: argparse.Namespace, password: str) -> None:
    database = Database(str(get_settings().database_url))
    try:
        async with database.session_factory() as session:
            user = await create_admin_user(
                session,
                email=args.email,
                display_name=args.display_name,
                role=UserRole(args.role),
                password=password,
            )
        print(f"Created {user.role.value} administrator: {user.email}")
    finally:
        await database.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a Bukky Store administrator")
    parser.add_argument("--email", required=True)
    parser.add_argument("--display-name", required=True)
    parser.add_argument("--role", choices=[role.value for role in UserRole], default="ADMIN")
    args = parser.parse_args()
    password = getpass.getpass("Password (12-128 characters): ")
    if password != getpass.getpass("Confirm password: "):
        raise SystemExit("Passwords do not match")
    try:
        asyncio.run(_run(args, password))
    except (ValidationError, ValueError) as exc:
        raise SystemExit(str(exc)) from None


if __name__ == "__main__":
    main()
