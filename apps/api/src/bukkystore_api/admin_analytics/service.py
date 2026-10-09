from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bukkystore_api.admin_analytics.schemas import (
    AdminAnalyticsOverview,
    AnalyticsRangeQuery,
    LowStockMetric,
    ProductEngagementMetric,
    ProductEngagementResponse,
    SourceMetric,
    TopProductMetric,
)
from bukkystore_api.analytics.service import product_engagement_counts, top_engaged_products
from bukkystore_api.catalogue.models import Product, ProductStatus, ProductVariant, VariantStatus
from bukkystore_api.commerce.models import Order, OrderItem, OrderStatus, Refund, RefundStatus
from bukkystore_api.errors import ApiError

logger = logging.getLogger(__name__)

SALES_STATUSES = (
    OrderStatus.CONFIRMED,
    OrderStatus.PROCESSING,
    OrderStatus.OUT_FOR_DELIVERY,
    OrderStatus.COMPLETED,
)
OPEN_FULFILMENT_STATUSES = (
    OrderStatus.CONFIRMED,
    OrderStatus.PROCESSING,
    OrderStatus.OUT_FOR_DELIVERY,
)


async def get_admin_analytics_overview(
    session: AsyncSession,
    query: AnalyticsRangeQuery,
    *,
    now: datetime | None = None,
) -> AdminAnalyticsOverview:
    """Calculate a bounded operational snapshot without per-record queries."""

    generated_at = now or datetime.now(UTC)
    period_start = generated_at - timedelta(days=query.days)
    in_period = Order.created_at >= period_start
    is_sale = Order.status.in_(SALES_STATUSES)

    metrics = (
        await session.execute(
            select(
                func.count(Order.id).filter(in_period).label("total_orders"),
                func.count(Order.id).filter(in_period, is_sale).label("sales_orders"),
                func.coalesce(func.sum(Order.total_minor).filter(in_period, is_sale), 0).label(
                    "sales_minor"
                ),
                func.count(Order.id)
                .filter(Order.status == OrderStatus.AWAITING_PAYMENT)
                .label("awaiting_payment_orders"),
                func.count(Order.id)
                .filter(Order.status.in_(OPEN_FULFILMENT_STATUSES))
                .label("open_fulfilment_orders"),
            )
        )
    ).one()
    pending_refunds = int(
        await session.scalar(
            select(func.count(Refund.id)).where(Refund.status == RefundStatus.PENDING)
        )
        or 0
    )

    available_quantity = ProductVariant.stock_on_hand - ProductVariant.reserved_quantity
    low_stock_rows = (
        await session.execute(
            select(
                ProductVariant.id.label("variant_id"),
                Product.id.label("product_id"),
                Product.name.label("product_name"),
                ProductVariant.display_name.label("variant_name"),
                ProductVariant.sku,
                available_quantity.label("available_quantity"),
                ProductVariant.low_stock_threshold,
                func.count().over().label("total_low_stock"),
            )
            .join(Product, Product.id == ProductVariant.product_id)
            .where(
                Product.status == ProductStatus.ACTIVE,
                ProductVariant.status == VariantStatus.ACTIVE,
                available_quantity <= ProductVariant.low_stock_threshold,
            )
            .order_by(available_quantity.asc(), Product.name.asc(), ProductVariant.sku.asc())
            .limit(8)
        )
    ).all()

    top_product_rows = (
        await session.execute(
            select(
                OrderItem.product_id,
                OrderItem.product_name,
                func.sum(OrderItem.quantity).label("units_sold"),
                func.sum(OrderItem.line_subtotal_minor).label("sales_minor"),
            )
            .join(Order, Order.id == OrderItem.order_id)
            .where(in_period, is_sale)
            .group_by(OrderItem.product_id, OrderItem.product_name)
            .order_by(
                func.sum(OrderItem.quantity).desc(),
                func.sum(OrderItem.line_subtotal_minor).desc(),
            )
            .limit(5)
        )
    ).all()

    source_label = func.coalesce(
        func.nullif(func.trim(Order.attribution_source), ""), "Direct"
    ).label("source")
    source_rows = (
        await session.execute(
            select(
                source_label,
                func.count(Order.id).label("orders"),
                func.sum(Order.total_minor).label("sales_minor"),
            )
            .where(in_period, is_sale)
            .group_by(source_label)
            .order_by(func.count(Order.id).desc(), source_label.asc())
        )
    ).all()

    sales_orders = int(metrics.sales_orders)
    sales_minor = int(metrics.sales_minor)
    low_stock_total = int(low_stock_rows[0].total_low_stock) if low_stock_rows else 0
    engaged = await top_engaged_products(session, period_start=period_start)
    overview = AdminAnalyticsOverview(
        generated_at=generated_at,
        period_start=period_start,
        range_days=query.days,
        total_orders=int(metrics.total_orders),
        sales_orders=sales_orders,
        sales_minor=sales_minor,
        average_order_minor=sales_minor // sales_orders if sales_orders else 0,
        awaiting_payment_orders=int(metrics.awaiting_payment_orders),
        open_fulfilment_orders=int(metrics.open_fulfilment_orders),
        pending_refunds=pending_refunds,
        low_stock_variants=low_stock_total,
        top_products=[
            TopProductMetric(
                product_id=row.product_id,
                product_name=row.product_name,
                units_sold=int(row.units_sold),
                sales_minor=int(row.sales_minor),
            )
            for row in top_product_rows
        ],
        sources=[
            SourceMetric(
                source=row.source,
                orders=int(row.orders),
                sales_minor=int(row.sales_minor),
            )
            for row in source_rows
        ],
        low_stock=[
            LowStockMetric(
                variant_id=row.variant_id,
                product_id=row.product_id,
                product_name=row.product_name,
                variant_name=row.variant_name,
                sku=row.sku,
                available_quantity=int(row.available_quantity),
                low_stock_threshold=int(row.low_stock_threshold),
            )
            for row in low_stock_rows
        ],
        engagement=[
            ProductEngagementMetric(
                product_id=item["product_id"],
                product_name=item["product_name"],
                views=item["views"],
                whatsapp_clicks=item["whatsapp_clicks"],
            )
            for item in engaged
        ],
    )
    logger.info(
        "admin_analytics_calculated",
        extra={
            "generated_at": generated_at.isoformat(),
            "period_start": period_start.isoformat(),
            "range_days": query.days,
            "top_product_count": len(overview.top_products),
            "source_count": len(overview.sources),
        },
    )
    return overview


async def get_product_engagement(
    session: AsyncSession,
    product_id: UUID,
    query: AnalyticsRangeQuery,
    *,
    now: datetime | None = None,
) -> ProductEngagementResponse:
    """Return view, share, and WhatsApp counts for one product over a bounded window."""

    generated_at = now or datetime.now(UTC)
    period_start = generated_at - timedelta(days=query.days)
    product = await session.get(Product, product_id)
    if product is None:
        raise ApiError(404, "product_not_found", "The product was not found.")
    counts = await product_engagement_counts(
        session, product_id=product.id, period_start=period_start
    )
    return ProductEngagementResponse(
        product_id=product.id,
        product_name=product.name,
        range_days=query.days,
        period_start=period_start,
        views=counts["views"],
        shares=counts["shares"],
        whatsapp_clicks=counts["whatsapp_clicks"],
    )
