from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from bukkystore_api.catalogue.models import ProductStatus, VariantStatus
from bukkystore_api.catalogue.schemas import CategoryResponse, Slug

ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class AdminCatalogueSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AdminCategoryCreate(AdminCatalogueSchema):
    name: Annotated[ShortText, StringConstraints(max_length=100)]
    slug: Slug
    parent_id: UUID | None = None
    display_position: int = Field(default=0, ge=0, le=10_000)


class AdminCategoryUpdate(AdminCatalogueSchema):
    name: Annotated[ShortText, StringConstraints(max_length=100)] | None = None
    slug: Slug | None = None
    display_position: int | None = Field(default=None, ge=0, le=10_000)
    is_active: bool | None = None

    @model_validator(mode="after")
    def reject_empty_or_null_fields(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("At least one category field must be provided")
        if any(getattr(self, field) is None for field in self.model_fields_set):
            raise ValueError("Category fields cannot be null")
        return self


class AdminVariantCreate(AdminCatalogueSchema):
    sku: Annotated[ShortText, StringConstraints(max_length=80)] | None = Field(
        default=None,
        description="Optional explicit SKU. When omitted, the backend generates one.",
    )
    colour: (
        Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)] | None
    ) = None
    size: (
        Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=40)] | None
    ) = None
    display_name: Annotated[ShortText, StringConstraints(max_length=140)]
    price_override_minor: int | None = Field(default=None, ge=0)
    initial_stock: int = Field(default=0, ge=0, le=1_000_000)
    low_stock_threshold: int = Field(default=2, ge=0, le=100_000)


class AdminProductCreate(AdminCatalogueSchema):
    category_id: UUID
    name: Annotated[ShortText, StringConstraints(max_length=180)]
    slug: Slug
    description: Annotated[str, StringConstraints(strip_whitespace=True, max_length=10_000)] = ""
    base_price_minor: int = Field(ge=0)
    compare_at_price_minor: int | None = Field(default=None, ge=0)
    status: ProductStatus = ProductStatus.DRAFT
    featured: bool = False
    variants: list[AdminVariantCreate] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def validate_price_and_variants(self) -> Self:
        if self.status is ProductStatus.ARCHIVED:
            raise ValueError("Use the archive action to archive a product")
        if (
            self.compare_at_price_minor is not None
            and self.compare_at_price_minor <= self.base_price_minor
        ):
            raise ValueError("compare_at_price_minor must exceed base_price_minor")
        skus = [variant.sku.casefold() for variant in self.variants if variant.sku]
        if len(skus) != len(set(skus)):
            raise ValueError("Variant SKUs must be unique")
        options = [
            ((variant.colour or "").casefold(), (variant.size or "").casefold())
            for variant in self.variants
        ]
        if len(options) != len(set(options)):
            raise ValueError("Variant colour and size combinations must be unique")
        return self


class AdminProductUpdate(AdminCatalogueSchema):
    category_id: UUID | None = None
    name: Annotated[ShortText, StringConstraints(max_length=180)] | None = None
    slug: Slug | None = None
    description: (
        Annotated[str, StringConstraints(strip_whitespace=True, max_length=10_000)] | None
    ) = None
    base_price_minor: int | None = Field(default=None, ge=0)
    compare_at_price_minor: int | None = Field(default=None, ge=0)
    status: ProductStatus | None = None
    featured: bool | None = None

    @model_validator(mode="after")
    def reject_empty_null_or_archive(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("At least one product field must be provided")
        nullable_fields = {"compare_at_price_minor"}
        if any(getattr(self, field) is None for field in self.model_fields_set - nullable_fields):
            raise ValueError("Product fields cannot be null")
        if self.status is ProductStatus.ARCHIVED:
            raise ValueError("Use the archive action to archive a product")
        return self


class AdminVariantResponse(AdminCatalogueSchema):
    id: UUID
    sku: str
    colour: str | None
    size: str | None
    display_name: str
    price_override_minor: int | None
    stock_on_hand: int
    reserved_quantity: int
    available_quantity: int
    low_stock_threshold: int
    status: VariantStatus


class AdminProductImageResponse(AdminCatalogueSchema):
    id: UUID
    public_id: str
    url: str
    alt_text: str
    width: int
    height: int
    position: int


class ImageUploadSignatureResponse(AdminCatalogueSchema):
    upload_url: str
    cloud_name: str
    api_key: str
    timestamp: int
    public_id: str
    signature: str
    signature_algorithm: Literal["sha256"] = "sha256"
    max_bytes: int
    allowed_mime_types: list[str]


class ProductImageRegisterRequest(AdminCatalogueSchema):
    public_id: Annotated[str, StringConstraints(min_length=20, max_length=255)]
    version: int = Field(gt=0)
    signature: Annotated[str, StringConstraints(pattern=r"^(?:[a-f0-9]{40}|[a-f0-9]{64})$")]
    width: int = Field(gt=0, le=20_000)
    height: int = Field(gt=0, le=20_000)
    bytes: int = Field(gt=0, le=10_000_000)
    format: Literal["jpg", "jpeg", "png", "webp", "avif"]
    alt_text: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=255)]


class ProductImageUpdateRequest(AdminCatalogueSchema):
    alt_text: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=255)]


class ProductImageReorderRequest(AdminCatalogueSchema):
    image_ids: list[UUID] = Field(min_length=1, max_length=10)

    @model_validator(mode="after")
    def reject_duplicate_images(self) -> Self:
        if len(self.image_ids) != len(set(self.image_ids)):
            raise ValueError("Image identifiers must be unique")
        return self


class AdminProductResponse(AdminCatalogueSchema):
    id: UUID
    category: CategoryResponse
    name: str
    slug: str
    description: str
    base_price_minor: int
    compare_at_price_minor: int | None
    currency: str
    status: ProductStatus
    featured: bool
    variants: list[AdminVariantResponse]
    images: list[AdminProductImageResponse]
    created_at: datetime
    updated_at: datetime


class AdminProductPage(AdminCatalogueSchema):
    items: list[AdminProductResponse]
    next_cursor: str | None


class AdminProductListQuery(AdminCatalogueSchema):
    search: Annotated[
        str | None, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)
    ] = None
    status: ProductStatus | None = None
    category_id: UUID | None = None
    cursor: Annotated[str | None, StringConstraints(max_length=500)] = None
    limit: int = Field(default=50, ge=1, le=100)


class StockAdjustmentRequest(AdminCatalogueSchema):
    quantity_delta: int = Field(ge=-1_000_000, le=1_000_000)
    reason: Annotated[ShortText, StringConstraints(max_length=500)]

    @model_validator(mode="after")
    def reject_zero_delta(self) -> Self:
        if self.quantity_delta == 0:
            raise ValueError("quantity_delta must not be zero")
        return self


class StockAdjustmentResponse(AdminCatalogueSchema):
    variant: AdminVariantResponse
    idempotent_replay: bool
