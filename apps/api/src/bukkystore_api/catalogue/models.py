from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bukkystore_api.auth.models import AdminUser
from bukkystore_api.database import Base

if TYPE_CHECKING:
    from collections.abc import Sequence


class ProductStatus(enum.StrEnum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"


class VariantStatus(enum.StrEnum):
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"


class InventoryMovementType(enum.StrEnum):
    INITIAL_STOCK = "INITIAL_STOCK"
    ADMIN_ADJUSTMENT = "ADMIN_ADJUSTMENT"
    SALE = "SALE"
    CANCELLATION_RESTOCK = "CANCELLATION_RESTOCK"
    RETURN_RESTOCK = "RETURN_RESTOCK"


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class Category(TimestampMixin, Base):
    __tablename__ = "categories"
    __table_args__ = (
        UniqueConstraint("slug", name="uq_categories_slug"),
        CheckConstraint("length(name) BETWEEN 1 AND 100", name="name_length"),
        CheckConstraint("length(slug) BETWEEN 1 AND 120", name="slug_length"),
        CheckConstraint("parent_id IS NULL OR parent_id <> id", name="not_own_parent"),
        Index("ix_categories_active_position", "is_active", "display_position"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), nullable=False)
    display_position: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )

    parent: Mapped[Category | None] = relationship(
        "Category", remote_side="Category.id", back_populates="children"
    )
    children: Mapped[list[Category]] = relationship("Category", back_populates="parent")
    products: Mapped[list[Product]] = relationship(back_populates="category")


class Product(TimestampMixin, Base):
    __tablename__ = "products"
    __table_args__ = (
        UniqueConstraint("slug", name="uq_products_slug"),
        CheckConstraint("length(name) BETWEEN 1 AND 180", name="name_length"),
        CheckConstraint("length(slug) BETWEEN 1 AND 200", name="slug_length"),
        CheckConstraint("base_price_minor >= 0", name="base_price_non_negative"),
        CheckConstraint(
            "compare_at_price_minor IS NULL OR compare_at_price_minor > base_price_minor",
            name="compare_at_price_above_price",
        ),
        Index("ix_products_public_listing", "status", "featured", "created_at"),
        Index("ix_products_category_status", "category_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    slug: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("''"))
    base_price_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    compare_at_price_minor: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    currency: Mapped[str] = mapped_column(
        String(3), nullable=False, default="NGN", server_default=text("'NGN'")
    )
    status: Mapped[ProductStatus] = mapped_column(
        Enum(ProductStatus, name="product_status", native_enum=True),
        nullable=False,
        default=ProductStatus.DRAFT,
        server_default=text("'DRAFT'"),
    )
    featured: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )

    category: Mapped[Category] = relationship(back_populates="products")
    images: Mapped[list[ProductImage]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
        order_by="ProductImage.position",
    )
    variants: Mapped[list[ProductVariant]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )

    @property
    def active_variants(self) -> Sequence[ProductVariant]:
        return tuple(variant for variant in self.variants if variant.status is VariantStatus.ACTIVE)


class ProductImage(TimestampMixin, Base):
    __tablename__ = "product_images"
    __table_args__ = (
        UniqueConstraint("product_id", "position", name="uq_product_images_product_position"),
        UniqueConstraint("cloudinary_public_id", name="uq_product_images_cloudinary_public_id"),
        CheckConstraint("position >= 0", name="position_non_negative"),
        CheckConstraint("width > 0", name="width_positive"),
        CheckConstraint("height > 0", name="height_positive"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    cloudinary_public_id: Mapped[str] = mapped_column(String(255), nullable=False)
    secure_url: Mapped[str] = mapped_column(Text, nullable=False)
    alt_text: Mapped[str] = mapped_column(String(255), nullable=False)
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)
    position: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )

    product: Mapped[Product] = relationship(back_populates="images")


class ProductVariant(TimestampMixin, Base):
    __tablename__ = "product_variants"
    __table_args__ = (
        UniqueConstraint("sku", name="uq_product_variants_sku"),
        CheckConstraint("stock_on_hand >= 0", name="stock_on_hand_non_negative"),
        CheckConstraint("reserved_quantity >= 0", name="reserved_quantity_non_negative"),
        CheckConstraint(
            "reserved_quantity <= stock_on_hand", name="reserved_not_above_stock_on_hand"
        ),
        CheckConstraint("low_stock_threshold >= 0", name="low_stock_threshold_non_negative"),
        CheckConstraint(
            "price_override_minor IS NULL OR price_override_minor >= 0",
            name="price_override_non_negative",
        ),
        Index("ix_product_variants_product_status", "product_id", "status"),
        Index(
            "uq_product_variants_option_combination",
            "product_id",
            func.coalesce(func.lower(text("colour")), ""),
            func.coalesce(func.lower(text("size")), ""),
            unique=True,
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    sku: Mapped[str] = mapped_column(String(80), nullable=False)
    colour: Mapped[str | None] = mapped_column(String(80), nullable=True)
    size: Mapped[str | None] = mapped_column(String(40), nullable=True)
    display_name: Mapped[str] = mapped_column(String(140), nullable=False)
    price_override_minor: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    stock_on_hand: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    reserved_quantity: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    low_stock_threshold: Mapped[int] = mapped_column(
        Integer, nullable=False, default=2, server_default=text("2")
    )
    status: Mapped[VariantStatus] = mapped_column(
        Enum(VariantStatus, name="variant_status", native_enum=True),
        nullable=False,
        default=VariantStatus.ACTIVE,
        server_default=text("'ACTIVE'"),
    )

    product: Mapped[Product] = relationship(back_populates="variants")
    movements: Mapped[list[InventoryMovement]] = relationship(back_populates="variant")

    @property
    def available_quantity(self) -> int:
        return self.stock_on_hand - self.reserved_quantity

    @property
    def effective_price_minor(self) -> int:
        if self.price_override_minor is not None:
            return self.price_override_minor
        return self.product.base_price_minor


class InventoryMovement(Base):
    __tablename__ = "inventory_movements"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_inventory_movements_idempotency_key"),
        CheckConstraint("quantity_delta <> 0", name="quantity_delta_non_zero"),
        CheckConstraint("length(reason) BETWEEN 1 AND 500", name="reason_length"),
        Index("ix_inventory_movements_variant_created", "variant_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    variant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("product_variants.id", ondelete="RESTRICT"), nullable=False
    )
    movement_type: Mapped[InventoryMovementType] = mapped_column(
        Enum(InventoryMovementType, name="inventory_movement_type", native_enum=True),
        nullable=False,
    )
    quantity_delta: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(120), nullable=False)
    order_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    reservation_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    variant: Mapped[ProductVariant] = relationship(back_populates="movements")
    actor: Mapped[AdminUser | None] = relationship()
