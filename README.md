# card-dispute-ai

An end-to-end AI analyst for credit-card disputes: it classifies the dispute, consults regulations and policies, investigates the customer's history and proposes a decision with cited sources, escalating to a human above the approval limit.
Each module demonstrates one capability expected from a production AI system (retrieval, multi-agent orchestration, evaluation, security and operations), always backed by measured numbers.

## How it works

```mermaid
flowchart LR
    IN["UI / API / MCP"] --> T["Triage"]
    T --> S["Specialists<br/>fraud · duplicate · not delivered"]
    S -->|consult| KB[("Knowledge base<br/>adaptive RAG")]
    S --> R["Reviewer"]
    R --> D{"Above the<br/>approval limit?"}
    D -->|yes| H["Human approval"]
    D -->|no| X[".NET agent via A2A<br/>executes the refund"]
    H --> X
```

## Modules

| Module | What it proves | Status |
| --- | --- | --- |
| 1. Core and infrastructure | DDD domain, swappable LLM provider and one-command infrastructure | 🚧 |
| 2. Knowledge base and ingestion | A realistic regulatory corpus with a ground truth for retrieval | ⬜ |
| 3. RAG Lab — ranking benchmark | Retrieval strategy chosen by benchmark, not opinion | ⬜ |
| 4. Adaptive RAG and GraphRAG | Spending more only on the questions that need it | ⬜ |
| 5. Supervisor with human approval | Multi-agent flow with human-in-the-loop and durable checkpoints | ⬜ |
| 6. Evals in CI | Quality as a merge criterion | ⬜ |
| 7. Deterministic vs autonomous vs hybrid | When to use a workflow and when to use an agent | ⬜ |
| 8. Guardrails and LGPD | Safety in a regulated context: PII masking and prompt-injection defense | ⬜ |
| 9. Observability, cost and cache | Operating the system with data: traces, cost per dispute, semantic cache | ⬜ |
| 10. Messaging, resilience and durable execution | Surviving failures without losing work or duplicating effects | ⬜ |
| 11. MCP server | Exposing the analyst to any MCP client | ⬜ |
| 12. .NET agent via A2A | Interoperability across Python and .NET agent stacks | ⬜ |

🚧 in progress · ⬜ not started

## Read more

- [docs/SCOPE.md](docs/SCOPE.md): full scope, what each module delivers and when it counts as done
- [docs/KICKOFF.md](docs/KICKOFF.md): summary of the decisions taken at kickoff
- [AGENTS.md](AGENTS.md): architecture rules, dependency contracts, commands and conventions

## Articles
