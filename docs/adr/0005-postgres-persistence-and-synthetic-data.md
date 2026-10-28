# ADR 0005 — Postgres persistence and deterministic synthetic data

- **Status:** Accepted
- **Date:** 2026-10-28

## Context

Module 1 is done when `docker compose up` brings the API up with data. That needs a real database, a way to evolve its schema, data for the core bank and the merchants (two systems this product does not own), and a set of disputes whose correct decision is known in advance, so later modules can measure the analyst against it.

## Decision

**Persistence**

- One Postgres (the pgvector image, ready for module 2), with **one schema per bounded context**: `public` for disputes and the outbox, `core_banking` for customers, cards and transactions, `merchants` for orders and their delivery proof. There are no foreign keys across schemas: contexts reference each other by id only, as they would across real systems.
- **SQLAlchemy 2 (async) with asyncpg.** Table models live in `infrastructure/persistence/sqlalchemy/`; a mapper converts rows to and from the aggregate through its rebuild constructor, so the domain never sees the ORM.
- **Transactional outbox:** the unit of work writes the dispute and its domain events in the same transaction. A relay publishes them in module 10.
- **Alembic migrations, written to be read.** `alembic check` runs in CI, so a table model cannot change without a migration. Migrations run in their own compose service; the API never changes the schema on startup.
- **Memory or Postgres by configuration:** `bootstrap` picks the implementations from `DATABASE_URL`. Unit tests always run in memory; tests marked `integration` run against a real Postgres, in a separate CI job.

**Synthetic data**

- `scripts/seed.py` generates everything from one `random.Random(42)`: ids, amounts and dates included, never the clock. The same seed always gives the same data, so evals stay comparable over time.
- Six scenarios with 50 disputes each, two per reason. Each has a rule that can be checked in the data (a twin charge minutes away, a merchant never used before, a subscription paid every month, a tracking code), and a test checks that rule for every case.
- The customer's description does not reveal the answer: both duplicate-charge scenarios read alike, and only the data tells them apart.
- `evals/datasets/disputes_v1.jsonl` is versioned. A test fails if it no longer matches the generator.
- Loading opens each dispute through the domain and the unit of work, so the domain rules apply and the outbox holds real events. Loading is idempotent.

## Alternatives considered

- **psycopg with plain SQL.** Fewer layers, but no migration autogeneration or model-versus-schema check, and more mapping code by hand.
- **One schema for everything, with foreign keys to the core bank.** Simpler queries, but it hides that the bank and the merchants are separate systems, and would make the anti-corruption layer look unnecessary.
- **LLM-generated cases.** More varied text, but not reproducible, and the expected decision would be an opinion instead of a fact in the data.

## Consequences

- **Positive:** one command brings up a realistic system; every expected decision can be traced to data; the same dataset drives the evals of modules 6 and 7.
- **Negative:** templated descriptions are less varied than real customers; module 8 adds hostile ones (prompt injection). The approval limit used for expected statuses (R$ 500) is a constant in the script until the analysis makes it a setting.
