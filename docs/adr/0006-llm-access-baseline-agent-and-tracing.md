# ADR 0006 — LLM access, the baseline agent and tracing

- **Status:** Accepted
- **Date:** 2026-10-28

## Context

Module 1 needs a first implementation of `AnalyzeDisputeGateway`: an agent that investigates a dispute and proposes a decision. It must run with any provider, including a local model, and be traced from day one. Later modules build on it: LangGraph and specialist playbooks (module 5), evals in CI (module 6), three strategies compared (module 7), guardrails against prompt injection and personal data in traces (module 8), full OpenTelemetry (module 9).

`AGENTS.md` planned an `LLM` port in `application/ports/`. Writing the agent showed that only infrastructure calls the model.

## Decision

- **Chat models through LangChain, in infrastructure.** `infrastructure/llm/chat_models.py` builds a `BaseChatModel` from the settings: `openai`, which also serves any OpenAI-compatible API such as Groq through `LLM_BASE_URL`; `anthropic`; or `ollama` for a local model. Temperature 0, a per-call timeout and two retries.
- **No `LLM` port in `application/ports/`.** Only the agents in `infrastructure/agents/` call a model, and `BaseChatModel` is already the common interface of the providers. A port of our own would rebuild that interface with our types and have no consumer outside infrastructure. The application sees only `AnalyzeDisputeGateway`. PII masking, the circuit breaker and provider fallback (modules 8 to 10) wrap the chat model inside `infrastructure/llm/`.
- **The baseline agent** (`infrastructure/agents/baseline/`) is a tool-calling loop written by hand: ask the model, run the tools it calls, return the results, at most six rounds. The decision is itself a tool call, `SubmitDecision`, validated by a Pydantic schema; an invalid decision goes back to the model as a tool error so it can fix it. A timeout, a provider error or no decision within the rounds becomes `AnalyzeDisputeUnavailableError`, and the dispute goes to manual review.
- **Read-only tools bound to the case.** `get_disputed_transaction`, `get_card_history` and `get_merchant_order` take no arguments: they read only the dispute under analysis. The action tools in the scope (block a card, open a chargeback, notify the customer) are not given to the model. They arrive in module 5, run by the flow after the domain decides.
- **Citations** are the evidence ids the tools return (`transaction:<id>`, `order:<id>`). Regulations join them with RAG in module 2.
- **A generic prompt.** It has no playbook per dispute reason, so the playbooks of module 5 can be measured against it. The customer's description goes inside tags and is declared data, not instructions.
- **Tracing through LangChain callbacks.** The analysis runs as one root run, so each analysis is one trace with every model and tool call nested in it, and the dispute id as the session. Bootstrap plugs in Langfuse's `CallbackHandler` when its keys are set; the agent knows only `BaseCallbackHandler`. Langfuse runs self-hosted behind the compose profile `tracing`.

## Alternatives considered

- **An `LLM` port with our own message types.** It duplicates LangChain's interface, adds code to maintain and has no consumer outside infrastructure.
- **LiteLLM or PydanticAI as the provider layer.** One more abstraction over the same providers; LangChain is already the stack for the LangGraph graphs of module 5.
- **LangGraph's prebuilt ReAct agent now.** Less code, but it hides the loop the first article explains. LangGraph arrives in module 5, and the evals compare both.
- **Structured output in a separate call** (`with_structured_output`). One more call per analysis, and providers differ in JSON-schema support: Groq offers strict schemas only for some models and not together with tools. A decision as a tool call works wherever tool calling works.
- **Tools with id arguments** (`get_transaction(id)`). A prompt injection could make the model read another customer's data, and small models mistype ids.
- **Langfuse Cloud.** No containers to run, but traces leave the machine. Self-hosted keeps everything in `docker compose`; the cloud remains one `LANGFUSE_BASE_URL` away.

## Consequences

- **Positive:** changing provider is configuration. Unit tests drive the loop with a scripted chat model, with no network. Every analysis is one trace. The model can read only its case and propose; it cannot act.
- **Negative:** the analysis runs inside the HTTP request and takes seconds; it becomes asynchronous in module 10. Free tiers cap how many cases can be measured per day (Groq's `openai/gpt-oss-120b`: 8K tokens per minute and 200K per day). The justification of an approval made by the agent is in the response and the trace, but not stored with the dispute until module 5. Traces carry the customer's description unmasked until module 8; the data is synthetic.
