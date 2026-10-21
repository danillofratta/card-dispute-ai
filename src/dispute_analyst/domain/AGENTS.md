# AGENTS.md — domain

Refines the root [`AGENTS.md`](../../../AGENTS.md) for `src/dispute_analyst/domain/`. The root rules still apply.

## What lives here

The business rules of a card dispute, in pure Python. Nothing here knows about HTTP, databases, brokers or LLMs.

| Folder | Holds | Examples |
|---|---|---|
| `value_objects/` | Immutable values, compared by value and validated on creation | `Money`, `Cpf`, `ApprovalLimit`, `DecisionProposal` |
| `enums/` | Closed sets of values, as `StrEnum` | `DisputeStatus`, `DisputeReason`, `ProposalOutcome` |
| `entities/` | Read-only snapshots of data owned by the core bank | `Customer`, `Card`, `Transaction` |
| `aggregates/` | Objects with identity and a lifecycle; the only place where state changes | `Dispute` |
| `events/` | What happened, as frozen dataclasses | `DisputeOpened`, `DisputeApproved` |
| `exceptions.py` | Errors the domain raises on its own | `DomainError`, `InvalidTransitionError` |

## Rules

- Standard library and `dispute_analyst.domain` only. Enforced by `tests/test_domain_is_pure.py` and import-linter contract 1.
- No I/O: no files, network, environment variables or logging. Datetimes are always timezone-aware.
- Value objects and entities are `@dataclass(frozen=True, slots=True)` and validate in `__post_init__`, so an invalid object never exists. Text input goes through a factory (`Money.of`, `Cpf.parse`).
- Amounts are always `Money`, never `float` or a bare `Decimal`.
- Aggregates reference other objects by id; they never hold them.
- Every status change goes through the state machine in `DisputeStatus` and records exactly one event. Callers collect events with `pull_events()`.
- The agent proposes, the domain decides ([ADR 0002](../../../docs/adr/0002-agent-proposes-domain-decides.md)): a bad `DecisionProposal` sends the dispute to `manual_review` and never raises. Exceptions are for programming mistakes (`InvalidTransitionError`) and invalid input (`ValueError`, `TypeError`).
- The domain never corrects a proposal silently, for example by capping an amount.
- Personal data never reaches `repr`, `str` or error messages: mask it (`Cpf.masked()`), keep it out of `repr` (`field(repr=False)`), or leave it out.
- Every package folder has an `__init__.py` (ruff `INP001`). Without it, import-linter silently skips the folder.

## Tests

- Live in `tests/domain/`, one file per concept. Plain unit tests: no fakes, no I/O.
- Every invariant has a test that tries to break it.
- Decision tables use `pytest.param(..., id="...")` so a failure names the broken case.
