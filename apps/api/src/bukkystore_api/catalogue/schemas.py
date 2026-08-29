from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Slug = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=200,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
    ),
]


class CatalogueSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CategoryResponse(CatalogueSchema):
    id: UUID
    name: str
    slug: str
    parent_id: UUID | None


class ProductImageResponse(CatalogueSchema):
    url: str
    alt_text: str
    width: int
    height: int


class ProductVariantResponse(CatalogueSchema):
    id: UUID
    sku: str
    colour: str | None
    size: str | None
    display_name: str
    price_minor: int
    currency: Literal["NGN"] = "NGN"
    available: bool
    low_stock: bool


class ProductCardResponse(CatalogueSchema):
    id: UUID
    name: str
    slug: str
    category: CategoryResponse
    price_minor: int
    compare_at_price_minor: int | None
    currency: Literal["NGN"] = "NGN"
    featured: bool
    available: bool
    primary_image: ProductImageResponse | None
    colours: list[str]
    sizes: list[str]


class ProductDetailResponse(ProductCardResponse):
    description: str
    images: list[ProductImageResponse]
    variants: list[ProductVariantResponse]


class ProductPageResponse(CatalogueSchema):
    items: list[ProductCardResponse]
    next_cursor: str | None


class ProductListQuery(CatalogueSchema):
    category: Slug | None = None
    search: Annotated[
        str | None, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)
    ] = None
    size: Annotated[
        str | None, StringConstraints(strip_whitespace=True, min_length=1, max_length=40)
    ] = None
    available: bool | None = None
    featured: bool | None = None
    min_price_minor: int | None = Field(default=None, ge=0)
    max_price_minor: int | None = Field(default=None, ge=0)
    cursor: Annotated[str | None, StringConstraints(max_length=500)] = None
    limit: int = Field(default=24, ge=1, le=50)
