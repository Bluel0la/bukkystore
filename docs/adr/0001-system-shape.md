# ADR 0001: Monorepo with a modular monolith

- Status: Accepted
- Date: 2026-08-28

## Context

The store needs one public interface, one small admin interface, and a coherent set
of tightly related commerce rules maintained by a small team.

## Decision

Use one repository containing a Next.js application and a FastAPI modular monolith.
PostgreSQL remains the system of record. Backend modules communicate through
domain services inside one deployable application rather than through networked
microservices.

## Consequences

- Domain transactions such as payment confirmation and inventory conversion can
  use one database transaction.
- Frontend and API contracts can change atomically in one pull request.
- Module boundaries still need enforcement to prevent an unstructured monolith.
- Services may be extracted later only when demonstrated scale or ownership needs
  outweigh the operational cost.
