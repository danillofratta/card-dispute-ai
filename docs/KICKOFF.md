# card-dispute-ai — Kickoff

Portfolio project: an AI-powered card dispute analyst, built as a public monorepo and explained in a series of Medium articles. The goal is to demonstrate production-grade RAG, multi-agent orchestration, evals, security and operations, always backed by measured results.

## Key decisions

- Python 3.12 with a uv workspace; LangGraph at the core, LangChain only for models and integrations; FastAPI and Pydantic
- The product follows DDD, light CQRS, vertical slices and ports & adapters; labs, evals and ingestion stay outside this pattern
- "The agent proposes, the domain decides": business invariants live in the `Dispute` aggregate, never only in a prompt
- Postgres with pgvector; Kafka for domain events; RabbitMQ for commands; Redis for semantic caching, rate limiting, circuit breaker state, idempotency and real-time status; transactional outbox and inbox
- Docker Compose with a light profile by default and a full profile (`--profile full`) that adds the brokers
- `AGENTS.md`, `CLAUDE.md` and `.claude/skills/` in the repo; specialist playbooks as `SKILL.md` files at runtime
- Code and folder names in English
- Public or synthetic data only

## Workflow

- Step by step, one module at a time, in scope order
- Development with Claude Code in VS Code; planning, ADRs and articles drafted alongside
- Every step ends with green tests and a commit

## Status

- Scope finalized on 2026-10-21
- Module 1 — Core and infrastructure, in progress: domain, API, Postgres, Docker Compose and synthetic data done; next: swappable LLM client, simulated tools, tracing and the Streamlit queue