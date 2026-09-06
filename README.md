# Atiten Kids Store

Atiten Kids Store is a mobile-first kids fashion storefront and operations dashboard for a
small Lagos retailer. It is designed around guest checkout, social-media product
links, WhatsApp enquiries, simple administration, variant-level inventory, and
provider-verified payments.

The project has its foundation, public catalogue, authenticated catalogue
management, payment-confirmation commerce, order-operations, and operations
dashboard slices. Customers can keep a local shopping bag, choose a simple Lagos
delivery area, create a server-priced order,
complete the deterministic development payment, and privately view its status.
Administrators can inspect recent orders, contact customers on WhatsApp, move paid
orders through fulfilment, cancel eligible orders with exactly-once stock
restoration, record completion of a manual refund, and monitor sales, fulfilment,
stock risk, top products, and checkout sources from the dashboard.

## Agreed product boundaries

- The public store and admin dashboard will be one Next.js application.
- Business rules and persistence will live in a FastAPI modular monolith.
- PostgreSQL is the system of record; Cloudinary is the preferred image store.
- Products may have colour-and-size combinations, with stock per combination.
- Adding to a cart does not reserve stock. Starting checkout does.
- Checkout is guest-first and prices are always calculated by the backend.
- Lagos delivery uses a simple admin-managed list of areas and flat fees.
- The initial administrators are an `OWNER` and an `ADMIN`.
- Payments use a provider boundary. OPay is preferred but not assumed to be
  available until merchant onboarding and developer access are confirmed.
- Analytics is useful but must never block commerce.

## Planned repository layout

```text
bukkystore/
  apps/
    api/                 FastAPI application
    web/                 Next.js storefront and admin
  docs/
    architecture/        Domain and API blueprints
    adr/                 Architecture decision records
  postman/               Versioned API contract collection
```

## Blueprint

- [Domain model](docs/architecture/domain-model.md)
- [Commerce flows](docs/architecture/commerce-flows.md)
- [API contract](docs/architecture/api-contract.md)
- [Delivery roadmap](docs/roadmap.md)

The original product discussion remains in [plan.txt](plan.txt). The documents
under `docs/` resolve ambiguities in that plan and are authoritative when the two
conflict.

## Local development

Prerequisites are Python 3.12+, `uv`, Node.js 22+, npm, Docker, and Postman CLI.

1. Copy `.env.example` to `.env` and replace the placeholder local secrets.
2. Start PostgreSQL with `docker compose up -d postgres`.
3. From the repository root, install and start the API:

   ```text
   uv sync --project apps/api
   uv run --project apps/api alembic -c apps/api/alembic.ini upgrade head
   uv run --project apps/api python -m bukkystore_api.seed
   uv run --project apps/api python -m bukkystore_api.auth.bootstrap --email owner@example.com --display-name "Store Owner" --role OWNER
   uv run --project apps/api uvicorn --factory bukkystore_api.main:create_app --app-dir apps/api/src --reload
   ```

4. From the repository root, run `npm install`, then `npm run web:dev`.

The storefront is available at `http://localhost:3000`, API documentation at
`http://localhost:8000/api/docs`, and liveness at
`http://localhost:8000/api/v1/health/live`.

The bootstrap command prompts for a password without echoing it. The first
administrator must be an `OWNER`; subsequent `OWNER` or `ADMIN` accounts can be
bootstrapped only from this trusted local command. There is no public admin signup.
The dashboard is available at `http://localhost:3000/admin/login`.

With the fake provider selected outside production, checkout redirects to a demo
payment page. Its confirmation button exercises the same idempotent stock and
order transaction used by a future authenticated provider callback; it does not
trust a browser-supplied amount or status. OPay credentials and callback
authentication remain intentionally deferred until merchant developer access is
confirmed.

The development seed is idempotent and creates the Atiten Kids Store business
settings (Emily Bus-stop by Dikram Filling Station, Mon–Sat 9am–6pm, WhatsApp
+2348121531909, TikTok @Bookie_kiddiestore), representative dresses, shoes, and
bags with colour-and-size stock variants, plus provisional Lagos Mainland and
Lagos Island delivery fees. Those fees are development defaults and must be
confirmed with the store owner before launch. Product photography remains
empty in the seed until real store photos are supplied. To enable the admin photo
uploader, set `APP_CLOUDINARY_CLOUD_NAME`, `APP_CLOUDINARY_API_KEY`, and
`APP_CLOUDINARY_API_SECRET`. The browser receives only a short-lived upload
signature; the API secret remains server-side. Product edit screens then support
upload progress, cover-photo ordering, accessible descriptions, and safe removal.

Run reservation expiry periodically so abandoned checkouts release their stock:

```text
uv run --project apps/api python -m bukkystore_api.commerce.reconcile
```

Run the quality gates with:

```text
cd apps/api
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest

cd ../..
npm run web:lint
npm run web:test
npm run web:build
```

For the Postman gate, copy the example environment to the ignored local filename,
start the API, and run:

```text
postman collection run ./postman/bukkystore.postman_collection.json -e ./postman/bukkystore.postman_environment.json --reporters "cli,junit"
```

## Commands

uv run --project apps/api uvicorn --factory bukkystore_api.main:create_app --app-dir apps/api/src --reload

npm run web:dev
