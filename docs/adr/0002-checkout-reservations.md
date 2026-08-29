# ADR 0002: Reserve inventory when checkout starts

- Status: Accepted
- Date: 2026-08-28

## Context

Cart-time deduction makes abandoned carts hide real stock. Payment-time-only
deduction allows two customers to pay for the last unit.

## Decision

Do not reserve stock in the cart. Create a short, expiring reservation during
server-side checkout and convert it exactly once after verified payment.

## Consequences

- The store avoids ordinary overselling without permanently reducing stock for
  abandoned checkouts.
- Reservation expiry and reconciliation are required from the first commerce
  release.
- A late successful payment may still require a refund if stock was sold after the
  reservation expired; this is made an explicit admin exception.
