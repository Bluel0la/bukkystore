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

`GET /delivery-areas`, `POST /checkout`, and the private guest payment-status route
are implemented. Development and test environments also expose
`POST /payments/fake/confirm`; it accepts only the order number and guest access
token, derives all provider-owned values from the database, and feeds the same
idempotent confirmation transaction intended for real authenticated callbacks.
The OPay callback route remains deferred until merchant documentation and
credentials can be verified.

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
summary, high-entropy order access token, and hosted payment URL. It does not
expose sequential database IDs or provider secrets. Reusing an idempotency key
with the same request returns the same logical checkout; using it for a different
request returns a conflict.

Checkout locks variants in deterministic order, snapshots product and delivery
details, and increments reservation counters in the same transaction. Payment
initialization runs only after commit. A provider initialization failure cancels
the pending order and releases the reservation. The reconciliation command expires
overdue reservations in skip-locked batches and releases their counters exactly
once.

The public status route requires a high-entropy order access token, not merely an
order number, to prevent enumeration of customer purchase state.

Each normalized provider result is recorded as an append-only `payment_event`.
The transaction locks the payment and relevant variants, verifies provider
reference, amount, and currency, and creates idempotent `SALE` movements. A late
verified payment consumes only unreserved stock; if that stock is unavailable the
payment remains successful while the order moves to `REFUND_REQUIRED`.

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
POST /admin/auth/logout
GET  /admin/auth/me
```

These routes are implemented. Login creates a database-backed, expiring session and
sets a secure HTTP-only session cookie plus a SameSite CSRF cookie. Mutating requests
must bind the CSRF cookie to the `X-CSRF-Token` header. Logout revokes the current
session. Login attempts are rate-limited and security logs mask email and network
identifiers. Administrators are created through the trusted bootstrap CLI; there is
no public signup route.

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
POST   /admin/products/{product_id}/images/signatures
POST   /admin/products/{product_id}/images
PATCH  /admin/products/{product_id}/images/reorder
PATCH  /admin/products/{product_id}/images/{image_id}/alt-text
DELETE /admin/products/{product_id}/images/{image_id}

POST   /admin/variants/{variant_id}/stock-adjustments
```

These routes are implemented. Admin product responses expose exact on-hand,
reserved, and available quantities. Product creation requires one or more unique
colour-and-size variants. Archiving uses its dedicated action and archives the
variants atomically; ordinary updates cannot set `ARCHIVED` directly.

Stock adjustments accept a bounded signed delta, a required reason, and an
`Idempotency-Key`. They enforce the reserved-stock floor, record the acting user,
and return an idempotent replay for an identical retry. They never accept a
replacement product object as a raw dictionary.

Image management is implemented for up to ten photos per product. The signature
route chooses a product-scoped public identifier and returns a one-hour signed
direct-upload request without exposing the API secret. The registration route
verifies Cloudinary's signed response (SHA-1 default or SHA-256), dimensions, format, and byte
limit, then constructs the delivery URL server-side before persisting metadata.
Reordering requires the complete unique image set and updates positions in two
phases to preserve the database uniqueness constraint. Removal succeeds in
Cloudinary before metadata is deleted and positions are compacted; provider
failures leave catalogue state unchanged. Alternative text is required and can
be corrected independently.

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
POST /admin/refunds/{refund_id}/complete
```

The routes use session authentication and explicit eager loading. Order detail
includes payment state, immutable line-item snapshots, delivery details, refund
state, and the actions currently allowed by the domain service.

Transition requests state the intended action rather than patching a status field.
The API returns a conflict when current state, payment state, or inventory state
does not permit that action.

Every mutating request requires CSRF validation plus an `Idempotency-Key` header.
Paid orders advance only through `CONFIRMED` -> `PROCESSING` ->
`OUT_FOR_DELIVERY` -> `COMPLETED`. Cancellation is unavailable after dispatch.
Cancelling a paid, undispatched order restores item stock once and creates one
pending full manual refund. Refund completion records an optional external
reference and changes the associated payment to `REFUNDED`; it never repeats the
inventory mutation.

## Admin analytics

```text
GET /admin/analytics/overview
```

The overview is implemented as a single authenticated response containing the
selected period's order and sales totals, current fulfilment/refund workload,
low-stock variants, top products, and checkout-source breakdown. `days` is bounded
from 1 to 365. Sales include non-cancelled paid orders in `CONFIRMED`, `PROCESSING`,
`OUT_FOR_DELIVERY`, or `COMPLETED`; pending/refund and stock counts are current
operational totals rather than historical snapshots. Aggregate queries are indexed
and issue no query per product or order.

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
