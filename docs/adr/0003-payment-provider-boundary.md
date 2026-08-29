# ADR 0003: Isolate payment providers

- Status: Accepted
- Date: 2026-08-28

## Context

OPay is the preferred provider, but merchant developer access, enabled endpoints,
authentication, and testing arrangements are not yet confirmed.

## Decision

Checkout depends on a small internal payment-provider interface. Build and test
against a deterministic fake adapter first. Add an OPay adapter only after the
merchant's assigned integration details are verified.

## Consequences

- Catalogue and core commerce development are not blocked by onboarding.
- Provider payloads and credentials remain outside domain services.
- A different provider can be added without rewriting order or inventory logic.
- Provider parity is not assumed; each adapter must document and test its own
  initialization, verification, webhook, query, and refund capabilities.
