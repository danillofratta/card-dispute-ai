# ADR 0003 — Hexagonal layout with vertical slices

- **Status:** Accepted
- **Date:** 2026-10-21
- **Supersedes:** the `ports/`, `adapters/`, `infra/` and `entrypoints/` layout in the first version of `AGENTS.md`

## Context

The first layout split the product into technical packages (`ports/`, `adapters/`, `infra/`, `entrypoints/`, `agents/`, `knowledge/`). Before the first slices were written, we compared it with a layout already used in a previous project: domain with repository interfaces, `features/<context>/<slice>/` with the endpoint inside the slice, `infrastructure/` for implementations, `bootstrap/` as composition root and `main.py`. We kept that shape, and evaluated where each interface belongs under DDD and hexagonal architecture.

## Decision

**Where each interface lives.** The rule is dependency inversion: an interface belongs to its consumer.

| Interface | What it is | Consumer | Location |
|---|---|---|---|
| `DisputeRepository` | DDD repository of the aggregate | Handlers | `domain/repositories/` |
| `UnitOfWork` | Transaction boundary (PoEAA, not a DDD pattern) | Handlers | `application/ports/` |
| `DisputeReadModel` and its views | CQRS read side | Query handlers | `application/ports/` |
| `CoreBanking` | Integration with another bounded context | Handlers | `application/ports/` |
| `DisputeAnalyzer` | Port of one slice | `analyze_dispute` | Inside the slice |

The domain never calls the core bank: `Dispute.open()` receives a `Transaction` already loaded by the handler. So `CoreBanking` is an application port, not a domain concept. Its implementation in `infrastructure/core_banking/` is the anti-corruption layer that translates the bank's model into ours.

`application/` holds only ports shared by several slices and their DTOs. It has no use cases: those stay in the slices. It is not a `shared/` utilities folder.

**Layers** (high → low): `main` → `features` → `bootstrap` → `infrastructure` → `application` → `domain`, enforced by import-linter.

**Two changes from the previous project**, both needed for the slices to stay independent:

1. `bootstrap/dependencies.py` provides only infrastructure behind port types, such as `get_unit_of_work() -> UnitOfWork`. Each endpoint builds its own handler in a small `get_handler` function. In the previous project, `dependencies.py` imported every handler and every endpoint imported `dependencies.py`: a cycle between `features` and `bootstrap` that also chained every slice to every other. Checked with import-linter: that shape breaks the layers contract and the slice independence contract.
2. Each endpoint maps its own errors to HTTP. A shared exception-handler module would import the exceptions of every slice and couple them again.

## Alternatives considered

- **Every persistence port in `domain/repositories/`, as in the previous project.** Pragmatic, but it puts a non-domain concept (the unit of work) in the domain and leaves no home for external-system ports such as `CoreBanking`.
- **Every port inside the slice that uses it (pure vertical slices).** Python protocols are structural, so one infrastructure class can satisfy several slice-local protocols. Rejected for shared ports: `UnitOfWork` would be repeated in every command slice, and `bootstrap` would have to expose concrete types to the endpoints. Kept for ports that only one slice uses.
- **Interfaces of external systems in the domain, as a domain service** (Vernon's approach to integrating bounded contexts). Right when the domain itself needs the collaborator; here only handlers do.

## Consequences

- **Positive:** the domain holds only the business model. Handlers depend on interfaces only, so they are tested with in-memory implementations. Each slice keeps its endpoint, models and errors in one folder. Six import-linter contracts check all of this in CI.
- **Negative:** one more package (`application/`) than the previous project, and a small `get_handler` function in every endpoint instead of one central list of providers.
