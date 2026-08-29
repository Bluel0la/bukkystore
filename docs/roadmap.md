# Delivery Roadmap

Development proceeds in deployable vertical releases. Each milestone includes
schemas, migrations, API contracts, UI, tests, observability, and documentation
for the behaviour it introduces.

## Release 0: Foundation

- Establish `apps/api` and `apps/web` in the monorepo.
- Add typed settings, JSON logging, correlation IDs, request metrics, database
  sessions, Alembic, pytest, OpenAPI, and CI.
- Add frontend linting, testing, accessibility checks, and API client generation.
- Create the Postman collection/environment skeleton and ignore secret-valued
  environment files.
- Prove frontend-to-backend communication in local and deployed environments.

Exit criteria: health/readiness endpoints work, migrations apply and downgrade,
tests pass, and Postman CLI passes against a running test deployment.

## Release 1: Usable catalogue

- Owner/admin authentication.
- Categories, products, colour/size variants, images, and stock adjustments.
- Mobile admin product workflow.
- Public home, product listing, product details, OpenGraph metadata, share links,
  and prefilled WhatsApp enquiries.
- Admin-managed store settings.

Exit criteria: an aunt can publish and share a dress from her phone, and a customer
can open the product and enquire through WhatsApp.

## Release 2: Commerce

- Client cart and Buy Now.
- Lagos delivery-area administration and guest address capture.
- Server-authoritative totals.
- Pending orders, timed inventory reservations, and expiry reconciliation.
- Provider-neutral payment service and deterministic fake provider.
- Real provider adapter after merchant access is confirmed.
- Verified, idempotent webhooks and payment-status reconciliation.
- Order management, cancellation, manual refund recording, and stock restoration.

Exit criteria: the agreed dress purchase succeeds end-to-end without overselling,
duplicate stock deductions, trusting redirects, or trusting browser totals.

## Release 3: Operations and analytics

- Anonymous session attribution and bounded best-effort analytics events.
- Dashboard cards, recent orders, low-stock warnings, top products, and sources.
- Product and conversion reporting.
- Retention, rate limits, bot handling, query performance checks, and privacy copy.

Exit criteria: the dashboard answers the aunt's daily operational questions without
analytics failures affecting checkout.

## Release 4: Production hardening

- Payment, reservation, cancellation, refund, and concurrent-checkout edge tests.
- Schemathesis API fuzzing and security review.
- Image and storefront performance budgets.
- Backup/restore exercise, alerting, operational runbooks, and admin audit review.
- Mobile-device and accessibility acceptance testing with the aunt.

Exit criteria: production readiness is evidence-backed and rollback procedures are
documented.

## Deferred deliberately

Customer accounts, reviews, wishlists, coupons, loyalty, multi-warehouse inventory,
dispatch integrations, live tracking, social-platform APIs, native mobile apps,
and automated marketing remain out of scope until real usage justifies them.
