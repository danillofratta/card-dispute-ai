# ADR 0001 — DDD with light CQRS, without event sourcing

- **Status:** Accepted
- **Date:** 2026-10-21

## Context

The product decides on money: whether a customer gets a refund. Its rules (the approval limit, an approved amount never above the disputed amount, no approval without a cited source) must hold whatever LLM, prompt or orchestration strategy is in use. Later modules add three analysis strategies, brokers and failure handling around those rules, so the rules need one home that none of that can bypass.

The system also needs an audit trail of every dispute and a dispute queue that is cheap to read.

## Decision

- **DDD for the product.** A `Dispute` aggregate with an explicit state machine owns every business rule. Value objects (`Money`, `Cpf`, `ApprovalLimit`) are immutable and validated on creation. The domain is pure Python: standard library only, no I/O.
- **Light CQRS.** Commands load and save the aggregate through `DisputeRepository` inside a `UnitOfWork`. Queries read Postgres read models through `DisputeReadModel`, kept up to date by projections.
- **Domain events, stored state.** Every state change raises a domain event. Events are written to an outbox in the same transaction as the aggregate's current state, then published to Kafka. The aggregate's current state is the source of truth; events are notifications and the audit trail.
- **Boundaries checked by machine.** import-linter contracts and a domain purity test run in CI, so a framework import in the domain or a slice importing another slice breaks the build.

## Alternatives considered

- **Event sourcing** (rebuild the aggregate from its events). It gives a complete history by construction and lets you query past states. Rejected for now: it brings event versioning, upcasting and snapshots, and raises the learning curve for every reader of the repo. The audit need is met by the outbox events plus the history of each analysis kept by the LangGraph checkpointer. Revisit if past decisions must be replayed exactly.
- **Transaction script** (rules inside the use-case handlers). Less code at first. Rejected: the rules would be repeated across the three analysis strategies of module 7, and sooner or later one would end up living only in a prompt.
- **Full CQRS with a separate read database.** Not needed at this scale: one Postgres with read-model tables is enough.

## Consequences

- **Positive:** the rules are tested with no infrastructure, and the whole domain suite runs in under a second. The deterministic, autonomous and hybrid strategies share one set of invariants. Read models can be rebuilt by replaying Kafka topics (module 10).
- **Negative:** more types and folders than a CRUD application. Read models are eventually consistent with the aggregate. Because events are not the source of truth, a publishing bug could leave gaps in the audit trail; the transactional outbox is the mitigation.
