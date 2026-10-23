# ADR 0004 — Queries read through the repository

- **Status:** Accepted
- **Date:** 2026-10-23
- **Amends:** the read side of [ADR 0001](0001-ddd-light-cqrs-no-event-sourcing.md); supersedes the read ports of [ADR 0003](0003-hexagonal-layout-with-vertical-slices.md)

## Context

ADR 0001 planned queries over Postgres read models, and ADR 0003 gave each query slice its own read port (`DisputeDetailsReader`, `DisputeQueueReader`) with one infrastructure module and one wiring module per query. Writing the first two queries showed the cost: three files in three packages for every query, while the read models had nothing to hold that the aggregate does not already have. The previous project this layout comes from reads through the repository, and that stayed simpler to follow.

## Decision

- Query handlers receive `DisputeRepository` (a domain port) and any shared port they need, such as `CoreBanking`. They load aggregates, map them to the slice's `result`, and never change them.
- The repository gains the query methods the slices need: `list_by_status` (oldest first, paginated) and `count_by_status`.
- Queries get the repository straight from `bootstrap/dependencies.py`. Commands keep using the repository inside the `UnitOfWork`, because only writes need a transaction.
- Commands and queries stay separate handlers and separate slices: CQRS by use case, one model.
- A dedicated read model comes back, as a port inside the slice that needs it, when a query needs something the aggregate cannot give cheaply: a projection fed by Kafka events (module 10), a heavy JOIN, or a measured latency problem.

## Alternatives considered

- **A read port per query slice** (ADR 0003, first revision). Clean dependency direction and room for JOINs and projections, but three files per query before any query needs them.
- **One shared read model in `application/ports/`.** Every new screen would change a global interface and its DTOs.

## Consequences

- **Positive:** a query is one slice plus, at most, a repository method. Handlers still depend only on ports, so they are tested with the in-memory repository.
- **Negative:** queries load whole aggregates, and the repository carries query methods next to `get_by_id` and `add`. The details screen asks the core bank for the merchant and card on every read; with Postgres that becomes a JOIN or a column stored when the dispute is opened.
