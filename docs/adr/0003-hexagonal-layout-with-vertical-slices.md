# ADR 0003 — Hexagonal layout with vertical slices

- **Status:** Accepted; the read ports (`DisputeDetailsReader`, `DisputeQueueReader`) are superseded by [ADR 0004](0004-queries-read-through-the-repository.md)
- **Date:** 2026-10-21 (revised 2026-10-22: read ports move into the slices)
- **Supersedes:** the `ports/`, `adapters/`, `infra/` and `entrypoints/` layout in the first version of `AGENTS.md`

## Context

The first layout split the product into technical packages (`ports/`, `adapters/`, `infra/`, `entrypoints/`, `agents/`, `knowledge/`). Before the first slices were written, we compared it with a layout already used in a previous project: domain with repository interfaces, `features/<context>/<slice>/` with the endpoint inside the slice, `infrastructure/` for implementations, `bootstrap/` as composition root and `main.py`. We kept that shape, and evaluated where each interface belongs under DDD and hexagonal architecture.

## Decision

**Where each interface lives.** The rule is dependency inversion: an interface belongs to its consumer.

| Interface | What it is | Consumer | Location |
|---|---|---|---|
| `DisputeRepository` | DDD repository of the aggregate | Command handlers | `domain/repositories/` |
| `UnitOfWork` | Transaction boundary (PoEAA, not a DDD pattern) | Command handlers | `application/ports/` |
| `CoreBanking` | Integration with another bounded context | Several slices | `application/ports/` |
| `DisputeDetailsReader`, `DisputeQueueReader` | Read side of one query | One query slice each | `features/disputes/<slice>/ports.py` |
| `DisputeAnalyzer` | Port of one slice | `analyze_dispute` | `features/disputes/analyze_dispute/ports.py` |

The domain never calls the core bank: `Dispute.open()` receives a `Transaction` already loaded by the handler. So `CoreBanking` is an application port, not a domain concept. Its implementation in `infrastructure/core_banking/` is the anti-corruption layer that translates the bank's model into ours.

`application/` holds only ports shared by several slices. It has no use cases: those stay in the slices. It is not a `shared/` utilities folder.

**Each query owns its read port.** A query slice declares a port that returns its own `result` type. The infrastructure implements it in one module for that slice and builds the slice's result directly. There is no shared read model: changing one query touches only its slice and its infrastructure module. This follows the hexagonal rule that adapters depend on the ports they implement; what infrastructure must never import is a slice's HTTP side (`endpoint`, `models`) or its `handler`.

**A slice has a core and an HTTP adapter.** The core (`command`, `query`, `handler`, `ports`, `result`) depends only on `domain` and `application`. The adapter (`endpoint`, `models`) depends on the core and on `bootstrap`. Because a slice spans both sides, `features` is not one of the layers.

**Layers** (high → low): `main` → `bootstrap` → `infrastructure` → `application` → `domain`, enforced by import-linter together with the slice contracts listed in `AGENTS.md`.

**Wiring.** `bootstrap/dependencies.py` provides only shared ports, typed by their interfaces (`get_unit_of_work() -> UnitOfWork`). A slice with its own ports has its own provider module, `bootstrap/<context>/<slice>.py`. Each endpoint builds its handler in a small `get_handler` function from those providers.

**Two rules keep slices independent**, both checked by the independence contract, which follows indirect imports:

1. One infrastructure module per slice port. A module that served two slices would link them.
2. Shared modules (`bootstrap/dependencies.py`, shared infrastructure such as the unit of work) never import a slice.

**Two changes from the previous project**, for the same reason:

1. In the previous project, `dependencies.py` imported every handler and every endpoint imported `dependencies.py`: a cycle between features and bootstrap that also chained every slice to every other. Checked with import-linter: that shape breaks the layers and slice independence contracts.
2. Each endpoint maps its own errors to HTTP. A shared exception-handler module would import the exceptions of every slice and couple them again.

## Alternatives considered

- **Every persistence port in `domain/repositories/`, as in the previous project.** Pragmatic, but it puts a non-domain concept (the unit of work) in the domain and leaves no home for external-system ports such as `CoreBanking`.
- **One shared read model in `application/ports/`** (`DisputeReadModel` with a method per query and shared view DTOs). It was the first version of this ADR. Rejected: every new screen would change a global interface and its DTOs, and each query would return a shared view that its slice then maps again to its own result.
- **Queries that load the aggregate through the repository**, as in the previous project. Simplest today, but it mixes the read side with the write model, loads the whole aggregate to read a few fields, and cannot join data the aggregate only references by id (merchant, card).
- **Interfaces of external systems in the domain, as a domain service** (Vernon's approach to integrating bounded contexts). Right when the domain itself needs the collaborator; here only handlers do.

## Consequences

- **Positive:** the domain holds only the business model. Handlers depend on interfaces only, so they are tested with in-memory implementations. Each slice keeps its endpoint, models, ports and errors in one folder, and a query evolves without touching any other. Seven import-linter contracts check all of this in CI.
- **Negative:** a slice with its own port has code in three places: the slice, its infrastructure module and its provider module in `bootstrap`. There is also one more package (`application/`) than in the previous project.
