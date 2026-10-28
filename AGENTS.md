# AGENTS.md — card-dispute-ai

Single source of truth for coding agents and humans working in this repo. `CLAUDE.md` only imports this file.

## Project overview

An AI analyst for credit-card disputes ("I don't recognize this charge", "charged twice", "never delivered").
The system classifies the dispute, consults regulations and internal policies (RAG), investigates the
customer's history and **proposes** a decision with cited sources. Above the approval limit a human approves;
then a .NET agent executes the refund via A2A.

- Public portfolio monorepo, explained in an article series. Every architecture choice comes with measured numbers (accuracy, cost, latency).
- Runs with one command and with any LLM provider, including a local model.
- Public or synthetic data only.
- Summary and decisions: `docs/KICKOFF.md`. Full scope: `docs/SCOPE.md`. The repo is built one module at a time, so some folders and commands below may not exist yet.

## Stack

| Concern | Choice |
|---|---|
| Language / packaging | Python 3.12, uv workspace |
| Orchestration | LangGraph; LangChain only for models and integrations |
| API / contracts | FastAPI, Pydantic |
| Database | Postgres + pgvector (vectors, read models, LangGraph checkpointer) |
| Messaging | Kafka in KRaft mode (domain events), RabbitMQ (commands, work queues) |
| Cache / coordination | Redis |
| Retrieval | pgvector (dense), bm25s (lexical), BGE reranker (Cohere optional) |
| Observability | OpenTelemetry + self-hosted Langfuse |
| UI | Streamlit |
| Quality | pytest, ruff, mypy, import-linter, GitHub Actions |
| Models | Configurable: OpenAI, Anthropic, or local Ollama |
| Interop | .NET 10 + Microsoft Agent Framework, via A2A |

## Architecture rules

DDD, light CQRS, vertical slices and ports & adapters apply to the product (`src/dispute_analyst/`) only.
`labs/`, `evals/` and `ingestion/` are plain pipelines: no DDD ceremony there.

### The agent proposes, the domain decides
- The LLM returns a structured `DecisionProposal`. The `Dispute` aggregate validates it and decides.
- Invariants live in the aggregate: approved amount never exceeds the disputed amount; above the
  `ApprovalLimit` the dispute goes to human approval; no citation means no approval.
- Never encode a business invariant only in a prompt. A prompt may repeat a rule; the domain enforces it.

### Domain (DDD)
- `Dispute` aggregate with an explicit state machine:
  - `open → under_analysis`
  - `under_analysis → approved` (below the limit) `| denied | awaiting_approval | manual_review` (graceful degradation)
  - `awaiting_approval → approved | denied`
  - `manual_review → approved | denied`
  - `approved → refunded | refund_failed` (refund saga)
  - `refund_failed → refunded` (retry) `| manual_review`
- Value objects: `Money`, `Cpf`, `ApprovalLimit`, `DisputeReason`. Every state change raises a domain event.

### Light CQRS
- Commands load and save the aggregate through `DisputeRepository` inside a `UnitOfWork`.
- Queries read through `DisputeRepository` and map the aggregate to their own `result`; they never change it.
  Dedicated read models arrive only when a query needs one ([ADR 0004](docs/adr/0004-queries-read-through-the-repository.md)).
- No event sourcing (see [ADR 0001](docs/adr/0001-ddd-light-cqrs-no-event-sourcing.md)).

### Vertical slices
- One folder per use case under `features/<context>/`, for example `features/disputes/open_dispute/`:
  - core: `command.py` or `query.py`, `handler.py`, `result.py` (what the handler returns, in domain types),
    and, when needed, `ports.py` (ports only this slice uses) and `exceptions.py`;
  - HTTP adapter: `endpoint.py` (the FastAPI router) and `models.py` (Pydantic request and response).
- The endpoint maps request → command or query, and result → response. It also maps the slice's own errors
  to HTTP; there is no shared exception handler, because it would import every slice and couple them.
- Each endpoint builds its handler in a small `get_handler` function from the providers in
  `bootstrap/dependencies.py`; a slice with ports of its own gets them from `bootstrap/<context>/<slice>.py`.
- Slices do not import each other. Shared behavior belongs in `domain/` or behind a port in `application/ports/`.
- Slice tests live in `tests/features/<context>/<slice>/`.

### Ports & adapters (hexagonal)
- Ports are `typing.Protocol`s, and each one lives with its consumer ([ADR 0003](docs/adr/0003-hexagonal-layout-with-vertical-slices.md)):
  - `domain/repositories/`: `DisputeRepository`, the DDD repository of the aggregate.
  - `application/ports/`: ports shared by several slices that return domain types: `UnitOfWork`, `CoreBanking`,
    and later `LLM`, `KnowledgeBase`, `MessageBus`, `EventStream`, `Cache`.
  - `features/<context>/<slice>/gateway.py`: ports only that slice uses, such as `AnalyzeDisputeGateway` in `analyze_dispute/`.
  - Inside `infrastructure/`: abstractions only infrastructure uses, such as `VectorStore`, `Reranker` and `PlaybookRepository`.
- `infrastructure/` implements the ports, so it may import a slice's core (`ports`, `result`, `query`, `command`),
  never its endpoint, models or handler. One infrastructure module per slice port: a module serving two slices
  would couple them.
- `bootstrap/dependencies.py` provides the shared ports and never imports a slice. Each slice with its own ports
  gets `bootstrap/<context>/<slice>.py`. `main.py` creates the app and includes the routers.
- `UnitOfWork` persists the aggregate and its outbox events in one transaction. Commands use the repository inside it;
  queries get the repository directly from `bootstrap`, because reading needs no transaction.
- `infrastructure/core_banking/` is the anti-corruption layer: it translates the bank's model into our `Customer`, `Card` and `Transaction`.
- The deterministic, autonomous and hybrid strategies are three `DisputeAnalyzer` implementations in
  `infrastructure/agents/`, chosen by configuration. Agents reach RAG only through `KnowledgeBase`,
  implemented in `infrastructure/knowledge/`.
- On the `LLM` port: PII masking as a decorator, circuit breaker (state in Redis) and provider fallback (primary → secondary → local).

### Messaging and resilience
- Domain events → Kafka (key = dispute id, to keep per-dispute ordering). Work commands (analyze, refund) → RabbitMQ (priority by amount, dead-letter, delayed retry).
- Outbox: events are written in the same transaction as the aggregate (via `UnitOfWork`) and published by a relay. Inbox: every consumer, Kafka or RabbitMQ, deduplicates by message id.
- Graceful degradation: if the LLM, RAG or the .NET agent is down, the dispute goes to `manual_review`; it never fails.
- Redis holds: semantic cache for RAG queries (never for the dispute decision), per-provider rate limits and token budgets, circuit-breaker state, idempotency keys, real-time status.

### Where each rule lives
| Layer | Answers | Example |
|---|---|---|
| Skill (`SKILL.md` playbook) | How to analyze | Fraud investigation checklist |
| RAG | What the regulation says | Legal deadline to dispute |
| Domain | What must never fail | Approval limit |

## Dependency rules (enforced by import-linter)

Contracts live in the import-linter config and run in CI. All paths are under `dispute_analyst`.

1. **Pure core** — `domain` and `application` import no framework (pydantic, langchain*, langgraph, fastapi,
   sqlalchemy/psycopg, kafka/rabbitmq clients, redis, httpx, LLM SDKs) and no outer layer. The domain is stricter:
   standard library only (`tests/test_domain_is_pure.py`).
2. **Layers** (high → low): `main` → `bootstrap` → `infrastructure` → `application` → `domain`. Slices are not a
   layer: their core sits beside `application`, their endpoint beside `main`.
3. **Independent slices** — `features.<context>.<slice>` never import each other, directly or indirectly
   (through `bootstrap` or `infrastructure` too).
4. **No direct infrastructure in features** — endpoints reach implementations only through `bootstrap`.
5. **Slice core knows only the core** — `command`, `query`, `handler`, `ports` and `result` import `domain` and
   `application` only: no FastAPI, Pydantic, `bootstrap` or `infrastructure`.
6. **Infrastructure implements ports** — it never imports a slice's endpoint, models or handler, nor `bootstrap` or `main`.
7. **Product isolation** — `dispute_analyst` never imports `labs`, `evals`, `ingestion` or `ui`.

When `infrastructure/agents/` and `infrastructure/knowledge/` arrive, a contract keeps agents from importing knowledge directly.

Never weaken, ignore or delete a contract to make the build pass. Change the design, or write an ADR and get approval first.

## Folder structure

```text
card-dispute-ai/
├── AGENTS.md                 # this file
├── CLAUDE.md                 # imports AGENTS.md
├── .claude/skills/           # dev skills: new-vertical-slice, new-adr, new-eval-case, new-rag-experiment
├── src/dispute_analyst/      # the product (DDD + light CQRS + vertical slices + hexagonal)
│   ├── domain/               # pure Python: aggregates, entities, value objects, enums, events
│   │   └── repositories/     # repository interfaces (DDD)
│   ├── application/
│   │   └── ports/            # interfaces shared by several slices (unit of work, core bank)
│   ├── features/             # vertical slices, grouped by context
│   │   └── disputes/
│   │       ├── open_dispute/       # command
│   │       ├── get_dispute/        # query
│   │       ├── list_queue/         # query
│   │       ├── analyze_dispute/    # command → DisputeAnalyzer (port inside the slice)
│   │       ├── approve_decision/   # command
│   │       └── execute_refund/     # command → A2A, .NET agent
│   ├── infrastructure/       # implementations of the ports
│   │   ├── persistence/      # memory/ (tests, quick runs) and sqlalchemy/ (Postgres): repository, unit of work, outbox
│   │   ├── core_banking/     # core bank adapters, in memory or Postgres (anti-corruption layer)
│   │   ├── agents/           # LangGraph graphs, the three strategies and skills/ (specialist playbooks)
│   │   ├── knowledge/        # runtime RAG: router, retrievers, rerankers
│   │   ├── llm/              # OpenAI, Anthropic, Ollama behind the LLM port
│   │   ├── messaging/        # Kafka, RabbitMQ, projections into read models
│   │   └── observability/    # tracing, metrics, logging
│   ├── bootstrap/            # composition root: dependencies.py (memory or Postgres) and settings.py
│   └── main.py               # FastAPI app; MCP server and workers join it as other entry points
├── tests/                    # mirrors src; @pytest.mark.integration tests need TEST_DATABASE_URL
├── migrations/               # Alembic; one schema per bounded context (public, core_banking, merchants)
├── scripts/                  # seed.py: deterministic synthetic data and the evals dataset
├── labs/                     # experiments, no DDD (rag_lab/, strategies/)
├── evals/                    # datasets (disputes_v1.jsonl: 300 cases with expected decisions), judges, CI suites
├── ingestion/                # regulation and policy ingestion pipeline
├── ui/                       # Streamlit
├── interop/dotnet/           # .NET refund agent, same pattern, in C#
├── docs/adr/                 # architecture decision records
└── docker-compose.yml        # postgres → migrate → seed → api; a full profile arrives in module 10
```

Folder-level `AGENTS.md` files refine these rules for `domain/` (pure Python, no I/O), `features/` (slice layout) and `labs/` (no DDD).

## Commands

```bash
uv sync                               # install the workspace
uv run pytest                         # all tests; integration tests skip without TEST_DATABASE_URL
uv run pytest -m "not integration"    # fast unit subset
uv run pytest -m integration          # Postgres tests: needs TEST_DATABASE_URL, a migrated database they may empty
uv run alembic upgrade head           # migrate DATABASE_URL
uv run alembic check                  # fails if a table model changed without a migration
uv run python -m scripts.seed dataset   # regenerate evals/datasets/disputes_v1.jsonl
uv run python -m scripts.seed database  # load the synthetic data into DATABASE_URL (once)
uv run ruff check . --fix             # lint
uv run ruff format .                  # format
uv run mypy src                       # type-check
uv run lint-imports                   # architecture contracts
uv run uvicorn dispute_analyst.main:app --reload   # API on http://localhost:8000/docs (Postgres if DATABASE_URL is set)
docker compose up --build             # Postgres, migrations, synthetic data and the API
```

Before every commit: `uv run ruff format . && uv run ruff check . && uv run mypy src && uv run lint-imports && uv run pytest`.

## Conventions

- Code, folders, identifiers and commit messages in English.
- Slice folders are `verb_noun` use cases in snake_case (`open_dispute`, `get_dispute`).
- Type hints everywhere; mypy runs in strict mode on `src/`.
- Pydantic at the boundaries (API, LLM structured output, messages); plain classes and frozen dataclasses in the domain.
- Money is always `Money` backed by `Decimal`; never `float`.
- Async for I/O (infrastructure, endpoints, handlers); the domain is synchronous and pure.
- Ports are `typing.Protocol`s. Implementations are created only in `bootstrap/` and reach features through dependencies; features never instantiate them.
- Unit tests never call a real LLM or network service: use fakes behind the ports. Real models run only in `evals/`.
- Tests live in `tests/`, mirroring `src/`. Domain tests are plain unit tests with no I/O. Mark tests that need containers with `@pytest.mark.integration`.
- Any change to a prompt or a runtime skill must pass the evals, like any code change.
- Runtime skills are written in this repo only; nothing from community hubs.
- Ask before adding a new dependency.
- Secrets never enter the repo: `.env.example` locally, secrets in CI.
- Public or synthetic data only; no proprietary or real customer data.
- Every architecture decision gets an ADR in `docs/adr/`.
- Small steps, one module at a time, in scope order. Conventional commits (`feat:`, `fix:`, `test:`, `docs:`, `refactor:`, `chore:`).

## Definition of done

Every change:
- [ ] Tests added or updated and green
- [ ] `ruff`, `mypy` and `lint-imports` green
- [ ] No business invariant living only in a prompt
- [ ] Committed

Every module:
- [ ] Runs with `docker compose up` and with a local model
- [ ] README with goal, diagram, decisions (ADRs) and GIF
- [ ] Measured numbers recorded in the README
- [ ] CI green
- [ ] Article published and linked both ways
