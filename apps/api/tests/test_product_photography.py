from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import httpx
import pytest
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from bukkystore_api.admin_catalogue import cloudinary
from bukkystore_api.admin_catalogue.schemas import (
    ProductImageRegisterRequest,
    ProductImageReorderRequest,
    ProductImageUpdateRequest,
)
from bukkystore_api.admin_catalogue.service import (
    create_image_upload_signature,
    register_product_image,
    remove_product_image,
    reorder_product_images,
    update_product_image,
)
from bukkystore_api.catalogue.models import Category, Product, ProductImage, ProductStatus
from bukkystore_api.config import Settings
from bukkystore_api.errors import ApiError


class ScalarItems:
    def __init__(self, items: list[Product]) -> None:
        self.items = items

    def unique(self) -> ScalarItems:
        return self

    def one_or_none(self) -> Product | None:
        return self.items[0] if self.items else None


def photography_settings() -> Settings:
    return Settings(
        environment="test",
        database_url="postgresql+asyncpg://test:test@localhost/test",
        session_secret="test-secret-value-with-at-least-32-characters",
        cloudinary_cloud_name="bukky-cloud",
        cloudinary_api_key="cloud-key",
        cloudinary_api_secret="cloud-secret",
    )


def product_with_images(count: int = 0) -> Product:
    product_id = uuid4()
    product = Product(
        id=product_id,
        category=Category(id=uuid4(), name="Dresses", slug="dresses"),
        name="Brown Dress",
        slug="brown-dress",
        description="A dress",
        base_price_minor=2_500_000,
        status=ProductStatus.ACTIVE,
    )
    product.created_at = datetime.now(UTC)
    product.updated_at = datetime.now(UTC)
    for position in range(count):
        product.images.append(
            ProductImage(
                id=uuid4(),
                cloudinary_public_id=f"bukkystore/products/{product_id}/{uuid4()}",
                secure_url=f"https://res.cloudinary.com/bukky/image/upload/v1/photo-{position}.jpg",
                alt_text=f"Photo {position + 1}",
                width=1000,
                height=1250,
                position=position,
            )
        )
    return product


def upload_payload(product_id: UUID, settings: Settings) -> ProductImageRegisterRequest:
    public_id = f"bukkystore/products/{product_id}/{uuid4()}"
    version = 123456
    secret = settings.cloudinary_api_secret
    assert secret is not None
    signature = cloudinary.sign_parameters(
        {"public_id": public_id, "version": version}, secret.get_secret_value()
    )
    return ProductImageRegisterRequest(
        public_id=public_id,
        version=version,
        signature=signature,
        width=1200,
        height=1500,
        bytes=900_000,
        format="jpg",
        alt_text="Brown linen dress front view",
    )


def test_cloudinary_signatures_delivery_url_and_configuration() -> None:
    settings = photography_settings()
    signature = cloudinary.sign_parameters({"timestamp": 1, "public_id": "sample"}, "secret")
    assert len(signature) == 64
    assert cloudinary.verify_upload_response(
        public_id="sample",
        version=1,
        signature=cloudinary.sign_parameters({"public_id": "sample", "version": 1}, "secret"),
        api_secret="secret",
    )
    assert not cloudinary.verify_upload_response(
        public_id="sample", version=1, signature="0" * 64, api_secret="secret"
    )
    sha1_response = "975c71eb8c7b190d4f0ab1b001fecc65d5393369"
    assert cloudinary.verify_upload_response(
        public_id="sample", version=1, signature=sha1_response, api_secret="secret"
    )
    assert (
        cloudinary.delivery_url(
            cloud_name="bukky cloud", public_id="folder/brown dress", version=4, image_format="webp"
        )
        == "https://res.cloudinary.com/bukky%20cloud/image/upload/v4/folder/brown%20dress.webp"
    )
    assert cloudinary.require_cloudinary(settings)[0] == "bukky-cloud"

    unconfigured = Settings(
        environment="test",
        database_url="postgresql+asyncpg://test:test@localhost/test",
        session_secret="test-secret-value-with-at-least-32-characters",
    )
    with pytest.raises(ApiError, match="not been configured"):
        cloudinary.require_cloudinary(unconfigured)


def test_image_schemas_reject_duplicates_and_invalid_uploads() -> None:
    image_id = uuid4()
    with pytest.raises(ValidationError):
        ProductImageReorderRequest(image_ids=[image_id, image_id])
    with pytest.raises(ValidationError):
        ProductImageRegisterRequest(
            public_id="too-short",
            version=0,
            signature="bad",
            width=0,
            height=0,
            bytes=10_000_001,
            format="gif",
            alt_text="x",
        )


async def test_signature_requires_product_and_returns_scoped_parameters() -> None:
    product = product_with_images()
    session = MagicMock(spec=AsyncSession)
    session.scalar = AsyncMock(return_value=product.id)
    signed = await create_image_upload_signature(session, product.id, photography_settings())
    assert str(product.id) in signed.public_id
    assert signed.upload_url.endswith("/bukky-cloud/image/upload")
    assert signed.signature_algorithm == "sha256"

    session.scalar = AsyncMock(return_value=None)
    with pytest.raises(ApiError) as error:
        await create_image_upload_signature(session, uuid4(), photography_settings())
    assert error.value.code == "product_not_found"


async def test_register_image_verifies_provider_and_is_idempotent() -> None:
    settings = photography_settings()
    product = product_with_images()
    payload = upload_payload(product.id, settings)
    session = MagicMock(spec=AsyncSession)
    session.scalars = AsyncMock(return_value=ScalarItems([product]))

    async def commit() -> None:
        image = session.add.call_args.args[0]
        image.id = image.id or uuid4()

    session.commit = AsyncMock(side_effect=commit)
    registered = await register_product_image(session, product.id, payload, settings)
    assert registered.position == 0
    assert registered.url.startswith("https://res.cloudinary.com/bukky-cloud/")

    replay = await register_product_image(session, product.id, payload, settings)
    assert replay.id == registered.id

    invalid = payload.model_copy(update={"signature": "0" * 64})
    with pytest.raises(ApiError) as error:
        await register_product_image(session, product.id, invalid, settings)
    assert error.value.code == "invalid_image_upload"

    wrong_product = payload.model_copy(
        update={"public_id": f"bukkystore/products/{uuid4()}/{uuid4()}"}
    )
    with pytest.raises(ApiError):
        await register_product_image(session, product.id, wrong_product, settings)


async def test_register_rejects_missing_product_and_photo_limit() -> None:
    settings = photography_settings()
    product = product_with_images(10)
    payload = upload_payload(product.id, settings)
    session = MagicMock(spec=AsyncSession)
    session.scalars = AsyncMock(return_value=ScalarItems([product]))
    with pytest.raises(ApiError) as limit_error:
        await register_product_image(session, product.id, payload, settings)
    assert limit_error.value.code == "image_limit_reached"

    session.scalars = AsyncMock(return_value=ScalarItems([]))
    with pytest.raises(ApiError) as missing_error:
        await register_product_image(session, product.id, payload, settings)
    assert missing_error.value.code == "product_not_found"


async def test_alt_text_reorder_and_removal(monkeypatch: pytest.MonkeyPatch) -> None:
    product = product_with_images(2)
    session = MagicMock(spec=AsyncSession)
    session.scalar = AsyncMock(return_value=product.images[0])
    session.commit = AsyncMock()
    updated = await update_product_image(
        session,
        product.id,
        product.images[0].id,
        ProductImageUpdateRequest(alt_text="Detailed front view"),
    )
    assert updated.alt_text == "Detailed front view"

    session.scalars = AsyncMock(return_value=ScalarItems([product]))
    session.flush = AsyncMock()
    reordered = await reorder_product_images(
        session,
        product.id,
        ProductImageReorderRequest(image_ids=[product.images[1].id, product.images[0].id]),
    )
    assert reordered[0].alt_text == "Photo 2"
    session.flush.assert_awaited_once()

    destroy = AsyncMock()
    monkeypatch.setattr("bukkystore_api.admin_catalogue.service.destroy_image", destroy)
    remaining = await remove_product_image(
        session, product.id, product.images[0].id, photography_settings()
    )
    assert len(remaining) == 1
    assert remaining[0].position == 0
    destroy.assert_awaited_once()


async def test_image_mutations_reject_wrong_membership() -> None:
    product = product_with_images(2)
    session = MagicMock(spec=AsyncSession)
    session.scalar = AsyncMock(return_value=None)
    with pytest.raises(ApiError) as missing_image:
        await update_product_image(
            session, product.id, uuid4(), ProductImageUpdateRequest(alt_text="Missing image")
        )
    assert missing_image.value.code == "image_not_found"

    session.scalars = AsyncMock(return_value=ScalarItems([product]))
    with pytest.raises(ApiError) as invalid_order:
        await reorder_product_images(
            session, product.id, ProductImageReorderRequest(image_ids=[product.images[0].id])
        )
    assert invalid_order.value.code == "invalid_image_order"

    with pytest.raises(ApiError) as missing_remove:
        await remove_product_image(session, product.id, uuid4(), photography_settings())
    assert missing_remove.value.code == "image_not_found"


async def test_destroy_image_maps_provider_results(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeResponse:
        def __init__(self, result: str, *, fails: bool = False) -> None:
            self.result = result
            self.fails = fails

        def raise_for_status(self) -> None:
            if self.fails:
                raise httpx.HTTPError("provider failure")

        def json(self) -> dict[str, str]:
            return {"result": self.result}

    class FakeClient:
        response = FakeResponse("ok")

        def __init__(self, *, timeout: int) -> None:
            assert timeout == 15

        async def __aenter__(self) -> FakeClient:
            return self

        async def __aexit__(self, *_args: object) -> None:
            return None

        async def post(self, url: str, *, data: dict[str, object]) -> FakeResponse:
            assert "bukky-cloud" in url
            assert data["api_key"] == "cloud-key"
            return self.response

    monkeypatch.setattr(cloudinary.httpx, "AsyncClient", FakeClient)
    await cloudinary.destroy_image("photo", photography_settings(), 123)
    FakeClient.response = FakeResponse("not found")
    await cloudinary.destroy_image("photo", photography_settings(), 123)
    FakeClient.response = FakeResponse("pending")
    with pytest.raises(ApiError):
        await cloudinary.destroy_image("photo", photography_settings(), 123)
    FakeClient.response = FakeResponse("failed", fails=True)
    with pytest.raises(ApiError):
        await cloudinary.destroy_image("photo", photography_settings(), 123)
