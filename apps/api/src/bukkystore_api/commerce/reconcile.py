from __future__ import annotations

import asyncio

from bukkystore_api.commerce.service import expire_reservations
from bukkystore_api.config import get_settings
from bukkystore_api.database import Database


async def _run() -> int:
    database = Database(str(get_settings().database_url))
    try:
        async with database.session_factory() as session:
            return await expire_reservations(session)
    finally:
        await database.dispose()


def main() -> None:
    expired = asyncio.run(_run())
    print(f"Expired reservations: {expired}")


if __name__ == "__main__":
    main()
