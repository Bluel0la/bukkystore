from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from httpx import AsyncClient
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from bukkystore_api.admin_settings import router as settings_router
from bukkystore_api.admin_settings.models import StoreSetting
from bukkystore_api.admin_settings.schemas import (
    AdminDeliveryAreaCreate,
    AdminDeliveryAreaUpdate,
    BusinessHours,
    StoreSettingUpdate,
)
from bukkystore_api.admin_settings.service import (
    create_delivery_area,
    get_public_store_settings,
    get_store_settings,
    list_admin_delivery_areas,
    normalize_nigerian_phone,
    update_delivery_area,
    update_store_settings,
)
from bukkystore_api.auth.dependencies import require_admin, require_csrf
from bukkystore_api.commerce.models import DeliveryArea
from bukkystore_api.errors import ApiError


def _settings_row(**overrides: Any) -> StoreSetting:
    now = datetime.now(UTC)
    values: dict[str, Any] = {
        "id": uuid4(),
        "store_name": "Atiten Kids Store",
        "logo_ref": None,
        "whatsapp_number": "+2348121531909",
        "phone_number": "+2348121531909",
        "instagram_url": None,
        "tiktok_url": "https://www.tiktok.com/@bookie_kiddiestore",
        "address": "Emily Bus-stop by Dikram Filling Station",
        "city": "Lagos",
        "currency": "NGN",
        "minimum_order_minor": None,
        "business_hours": BusinessHours().model_dump(mode="json"),
        "last_idempotency_key_hash": None,
        "last_request_fingerprint": None,
        "created_at": now,
        "updated_at": now,
    }
    values.update(overrides)
    return StoreSetting(**values)


def _settings_payload() -> dict[str, Any]:
    return {
        "store_name": "Atiten Kids Store",
        "whatsapp_number": "08121531909",
        "phone_number": "+2348121531909",
        "address": "Emily Bus-stop by Dikram Filling Station",
        "city": "Lagos",
        "currency": "NGN",
        "tiktok_url": "https://www.tiktok.com/@bookie_kiddiestore",
        "business_hours": BusinessHours().model_dump(mode="json"),
    }


def _mock_session(*, scalar_result: Any = None, scalars_result: Any = None) -> Any:
    session = MagicMock(spec=AsyncSession)
    session.scalar = AsyncMock(return_value=scalar_result)
    items = scalars_result if scalars_result is not None else []
    session.scalars = AsyncMock(return_value=SimpleNamespace(all=lambda: items))
    session.get = AsyncMock(return_value=None)
    session.commit = AsyncMock()
    session.rollback = AsyncMock()

    async def commit() -> None:
        if session.add.called:
            added = session.add.call_args.args[0]
            if getattr(added, "id", None) is None:
                added.id = uuid4()

    session.commit.side_effect = commit
    return session


def test_phone_normalization_converts_local_prefix() -> None:
    assert normalize_nigerian_phone("08121531909") == "+2348121531909"
    assert normalize_nigerian_phone("+2348121531909") == "+2348121531909"


def test_settings_update_rejects_bad_phone_and_hours() -> None:
    with pytest.raises(ValidationError):
        StoreSettingUpdate(**{**_settings_payload(), "whatsapp_number": "not-a-number"})
    with pytest.raises(ValidationError):
        StoreSettingUpdate(
            **{
                **_settings_payload(),
                "business_hours": {
                    **BusinessHours().model_dump(mode="json"),
                    "monday": {"closed": False, "open": "18:00", "close": "09:00"},
                },
            }
        )
    with pytest.raises(ValidationError):
        StoreSettingUpdate(**{**_settings_payload(), "unexpected": "field"})


async def test_get_store_settings_returns_singleton() -> None:
    row = _settings_row()
    response = await get_store_settings(_mock_session(scalar_result=row))

    assert response.store_name == "Atiten Kids Store"
    assert response.whatsapp_number == "+2348121531909"
    assert response.business_hours.sunday.closed is True


async def test_get_store_settings_missing_row_is_not_found() -> None:
    with pytest.raises(ApiError) as error:
        await get_store_settings(_mock_session(scalar_result=None))

    assert error.value.status_code == 404
    assert error.value.code == "settings_not_configured"


async def test_get_public_store_settings_hides_nothing_secret() -> None:
    row = _settings_row()
    response = await get_public_store_settings(_mock_session(scalar_result=row))

    assert response.store_name == "Atiten Kids Store"
    assert "last_idempotency" not in response.model_dump()


async def test_update_store_settings_normalizes_and_commits() -> None:
    row = _settings_row()
    session = _mock_session(scalar_result=row)

    response = await update_store_settings(
        session,
        StoreSettingUpdate(**_settings_payload()),
        idempotency_key="settings-update-key-0001",
        secret="test-secret-value-with-at-least-32-characters",
    )

    assert response.whatsapp_number == "+2348121531909"
    assert row.last_idempotency_key_hash is not None
    assert row.last_request_fingerprint is not None
    session.commit.assert_awaited_once()


async def test_update_store_settings_replays_identical_retry() -> None:
    row = _settings_row()
    session = _mock_session(scalar_result=row)
    payload = StoreSettingUpdate(**_settings_payload())

    await update_store_settings(
        session, payload, idempotency_key="settings-update-key-0002", secret="test-secret"
    )
    session.commit.reset_mock()
    response = await update_store_settings(
        session, payload, idempotency_key="settings-update-key-0002", secret="test-secret"
    )

    assert response.store_name == "Atiten Kids Store"
    session.commit.assert_not_awaited()


async def test_update_store_settings_rejects_key_reuse_with_changes() -> None:
    row = _settings_row()
    session = _mock_session(scalar_result=row)

    await update_store_settings(
        session,
        StoreSettingUpdate(**_settings_payload()),
        idempotency_key="settings-update-key-0003",
        secret="test-secret",
    )
    changed = StoreSettingUpdate(**{**_settings_payload(), "store_name": "Another Name"})
    with pytest.raises(ApiError) as error:
        await update_store_settings(
            session, changed, idempotency_key="settings-update-key-0003", secret="test-secret"
        )

    assert error.value.status_code == 409
    assert error.value.code == "idempotency_conflict"


async def test_list_admin_delivery_areas_returns_display_order() -> None:
    areas = [
        DeliveryArea(
            id=uuid4(),
            name="B",
            fee_minor=1,
            currency="NGN",
            display_position=1,
            is_active=False,
        ),
        DeliveryArea(
            id=uuid4(),
            name="A",
            fee_minor=2,
            currency="NGN",
            display_position=0,
            is_active=True,
        ),
    ]
    response = await list_admin_delivery_areas(_mock_session(scalars_result=areas))

    assert [(area.name, area.is_active) for area in response] == [("B", False), ("A", True)]


async def test_create_delivery_area_persists_new_area() -> None:
    session = _mock_session(scalar_result=None)

    response = await create_delivery_area(
        session, AdminDeliveryAreaCreate(name="Ikeja", fee_minor=200_000)
    )

    assert response.name == "Ikeja"
    assert response.fee_minor == 200_000
    session.commit.assert_awaited_once()


async def test_create_delivery_area_replays_identical_name() -> None:
    existing = DeliveryArea(
        id=uuid4(),
        name="Ikeja",
        fee_minor=200_000,
        currency="NGN",
        display_position=0,
        is_active=True,
    )
    session = _mock_session(scalar_result=existing)

    response = await create_delivery_area(
        session, AdminDeliveryAreaCreate(name="Ikeja", fee_minor=200_000)
    )

    assert response.name == "Ikeja"
    session.commit.assert_not_awaited()


async def test_create_delivery_area_conflicts_on_different_fee() -> None:
    existing = DeliveryArea(
        id=uuid4(),
        name="Ikeja",
        fee_minor=200_000,
        currency="NGN",
        display_position=0,
        is_active=True,
    )
    session = _mock_session(scalar_result=existing)

    with pytest.raises(ApiError) as error:
        await create_delivery_area(
            session, AdminDeliveryAreaCreate(name="Ikeja", fee_minor=999_000)
        )

    assert error.value.status_code == 409
    assert error.value.code == "delivery_area_exists"


async def test_update_delivery_area_missing_is_not_found() -> None:
    session = _mock_session()
    session.get.return_value = None

    with pytest.raises(ApiError) as error:
        await update_delivery_area(session, uuid4(), AdminDeliveryAreaUpdate(fee_minor=250_000))

    assert error.value.status_code == 404


async def test_update_delivery_area_handles_rename_conflict() -> None:
    area = DeliveryArea(
        id=uuid4(),
        name="Ikeja",
        fee_minor=200_000,
        currency="NGN",
        display_position=0,
        is_active=True,
    )
    session = _mock_session()
    session.get.return_value = area
    session.commit.side_effect = IntegrityError("stmt", "params", Exception("unique"))

    with pytest.raises(ApiError) as error:
        await update_delivery_area(session, uuid4(), AdminDeliveryAreaUpdate(name="Yaba"))

    assert error.value.status_code == 409


async def test_admin_settings_routes_require_authentication(client: AsyncClient) -> None:
    settings_get = await client.get("/api/v1/admin/store-settings")
    delivery_get = await client.get("/api/v1/admin/delivery-areas")
    settings_patch = await client.patch(
        "/api/v1/admin/store-settings",
        headers={"Idempotency-Key": "settings-auth-probe-0001"},
        json=_settings_payload(),
    )
    delivery_post = await client.post(
        "/api/v1/admin/delivery-areas",
        headers={"Idempotency-Key": "settings-auth-probe-0002"},
        json={"name": "Ikeja", "fee_minor": 200_000},
    )
    delivery_patch = await client.patch(
        f"/api/v1/admin/delivery-areas/{uuid4()}",
        headers={"Idempotency-Key": "settings-auth-probe-0003"},
        json={"fee_minor": 250_000},
    )

    for response in (settings_get, delivery_get, settings_patch, delivery_post, delivery_patch):
        assert response.status_code == 401
        assert response.json()["code"] == "authentication_required"


async def test_public_store_settings_missing_row_is_not_found(client: AsyncClient) -> None:
    response = await client.get("/api/v1/store-settings")

    assert response.status_code == 404
    assert response.json()["code"] == "settings_not_configured"


async def test_admin_settings_wiring_returns_strict_shapes(
    client: AsyncClient, app: Any, monkeypatch: Any
) -> None:
    expected = await get_store_settings(_mock_session(scalar_result=_settings_row()))
    monkeypatch.setattr(settings_router, "get_store_settings", AsyncMock(return_value=expected))
    app.dependency_overrides[require_admin] = lambda: SimpleNamespace()
    app.dependency_overrides[require_csrf] = lambda: SimpleNamespace()

    response = await client.get("/api/v1/admin/store-settings")

    assert response.status_code == 200
    assert response.json()["store_name"] == "Atiten Kids Store"
