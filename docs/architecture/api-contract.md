# API Contract Blueprint

All routes are rooted at `/api/v1`. Concrete implementation must generate and
version an OpenAPI document from strict Pydantic request and response models. Raw
dictionary parsing is not permitted at API or provider boundaries.

## Common rules

- UUIDs, slugs, Nigerian phone numbers, quantities, strings, and list sizes have
  explicit constraints.
- Unknown request fields are rejected unless a particular bounded metadata object
  intentionally allows them.
- Pagination is cursor-based for potentially growing admin and catalogue lists.
- Errors use a stable code, safe message, field details when relevant, and request
  correlation ID.
- `Idempotency-Key` is required for checkout and other effect-producing public
  operations that may be retried.
- Admin routes require an authenticated, active user and role authorization.
- All list queries use eager loading or projections; query-count tests guard
  against N+1 regressions.

## Public catalogue

```text
GET  /categories
GET  /products
GET  /products/{slug}
GET  /delivery-areas
```

Product responses expose availability, not internal reservation records or exact
stock counts unless the UI explicitly needs a bounded "few left" indicator.
Filtering initially supports category, search text, availability, size, and a
bounded price range. The catalogue implementation returns prices in integer kobo,
uses opaque cursor pagination, derives availability from `stock_on_hand -
reserved_quantity`, and never exposes either stock field publicly. Product detail
responses include variant SKU, colour, size, display name, effective price,
availability, and a bounded low-stock indicator.

## Checkout and payment status

```text
POST /checkout
GET  /orders/{order_number}/payment-status?token=...
POST /payments/{provider}/webhook
```

The checkout request contains:

```json
{
  "customer": {
    "full_name": "Customer Name",
    "phone": "+2348000000000",
    "email": null
  },
  "delivery": {
    "area_id": "00000000-0000-0000-0000-000000000000",
    "address": "Customer-provided address",
    "directions": null
  },
  "items": [
    {
      "variant_id": "00000000-0000-0000-0000-000000000000",
      "quantity": 1
    }
  ],
  "attribution": {
    "source": "tiktok",
    "campaign": null
  }
}
```

The response contains the public order number, reservation expiry, server-computed
summary, and hosted payment URL. It does not expose sequential database IDs or
provider secrets.

The public status route requires a high-entropy order access token, not merely an
order number, to prevent enumeration of customer purchase state.

## Analytics

```text
POST /analytics/events
```

The request supports only an allowlist of event types and bounded metadata. The
endpoint is rate-limited and returns success independently of downstream analytics
processing. It cannot update prices, stock, orders, or payments.

## Authentication

```text
POST /admin/auth/login
POST /admin/auth/refresh
POST /admin/auth/logout
GET  /admin/auth/me
```

Login and refresh responses set secure HTTP-only cookies. Mutating requests include
CSRF protection. Login attempts are rate-limited and security logs mask the email
and network identifiers.

## Admin catalogue and inventory

```text
GET    /admin/categories
POST   /admin/categories
PATCH  /admin/categories/{category_id}

GET    /admin/products
POST   /admin/products
GET    /admin/products/{product_id}
PATCH  /admin/products/{product_id}
POST   /admin/products/{product_id}/archive
POST   /admin/products/{product_id}/images/signature

POST   /admin/variants/{variant_id}/stock-adjustments
GET    /admin/inventory/low-stock
```

Stock adjustments accept a signed delta or a target quantity, a required reason,
and an idempotency key. They never accept a replacement product object as a raw
dictionary.

Cloudinary uploads use narrowly scoped signed parameters. The API verifies the
completed upload before persisting image metadata.

## Admin delivery and store settings

```text
GET    /admin/delivery-areas
POST   /admin/delivery-areas
PATCH  /admin/delivery-areas/{area_id}

GET    /admin/store-settings
PATCH  /admin/store-settings
```

Payment secrets are startup configuration, not editable store settings and never
appear in API responses.

## Admin orders and refunds

```text
GET  /admin/orders
GET  /admin/orders/{order_id}
POST /admin/orders/{order_id}/transitions
POST /admin/orders/{order_id}/cancellations
POST /admin/payments/{payment_id}/refunds
```

Transition requests state the intended action rather than patching a status field.
The API returns a conflict when current state, payment state, or inventory state
does not permit that action.

## Admin analytics

```text
GET /admin/analytics/overview
GET /admin/analytics/products/{product_id}
GET /admin/analytics/sources
```

Time ranges are bounded and validated. Aggregation queries must be indexed and
must not issue one query per product.

## Configuration boundary

FastAPI startup uses a typed `BaseSettings` configuration that fails fast. Expected
groups include database, CORS/site origins, cookie security, token lifetimes,
Cloudinary, reservation duration, logging, and payment-provider selection.

Provider-specific secrets are required only when that provider is selected. The
fake provider is forbidden in production.

## Contract verification

Every implemented endpoint requires:

- pytest happy-path, boundary, exception, authorization, and mocked-I/O coverage;
- OpenAPI descriptions and examples updated in the same change;
- Schemathesis coverage to detect schema violations and unhandled 500 responses;
- a synchronized Postman v2.1 collection and secret-free environment template;
- a passing local Postman CLI run before a pull request is opened.
