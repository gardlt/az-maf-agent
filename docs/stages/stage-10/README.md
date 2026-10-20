# Stage 10: Native Microsoft Agent Framework capabilities

Status: **planned**, 2026-10-20. No framework migration, dependency upgrade or new agent/tool authority is enabled.

[All stages](../README.md) · [Tasks](../../tasks/stage-10-framework-capabilities.md) · [Validation plan](validation/README.md)

## Goal

Evaluate and selectively adopt native Microsoft Agent Framework capabilities where they reduce application complexity or improve behavior without weakening ownership, budgets, identity, quarantine, data handling or evidence.

The inspected repository pins `agent-framework-core==1.22.0` and already uses `Agent`, `AgentSession`, history/context components and a custom `BaseChatClient`. A local import check on 2026-10-20 found workflow builders, agent/chat/function middleware, in-memory/file checkpoint stores, tool approval middleware and HTTP/stdio MCP adapters. Importability is not proof that an API meets our durability, security or deployment requirements. Re-check exact version/signatures and runtime behavior before implementation.

## Candidate capabilities

| Capability | Current application approach | Evaluation boundary |
| --- | --- | --- |
| Agent/chat/function middleware | Application-owned checks and wrappers | Prove coverage of every model/tool/context/output path, correct ordering, async cancellation, error propagation and required audit before effects |
| Workflows and checkpoints | Bounded chat/tool loop and shared session/control state | Use native orchestration only with reviewed durable persistence, owner/generation binding, expiry, safe serialization and unknown-outcome reconciliation |
| Tool approval middleware | Exact-bound application approval primitives and harmless simulation | Native UX/events must not replace independent authorization, argument/resource binding, expiry, single use or persisted receipts |
| Streaming | Guarded client intentionally rejects streams | Add safe progress/chunk publication with output checks, cancellation, backpressure and accounting; no hidden reasoning or private payload release |
| Native MCP adapters | FastMCP client with pinned schema, origin, response validation and read-only dispatch | Compare protocol behavior, token scope/cache, connection lifecycle, schema drift, response limits and tool auto-invocation; never enable unrestricted discovery/execution |
| Multi-agent orchestration (conditional) | One agent with reviewed skills/tools | Require a task benefit and independently containable identities; test handoff authority, parent/child cancellation, aggregate budgets and cross-agent disclosure |

Stage 8 defines product/security requirements for these features; Stage 9 specializes sensitive-data boundaries. Stage 10 is the SDK adoption/equivalence track, not a second implementation or a reason to close their gates. Framework middleware is an integration hook, not an independent resource security boundary.

## Adoption principles

Start with a compatibility inventory and middleware spike, then workflow/checkpoint and streaming evaluation. Compare native MCP/approval paths against existing contracts before replacing any custom code. Add multi-agent orchestration only for an explicitly selected use case; it is not necessary merely to exercise the SDK.

Use a fixture-first, opt-in migration with clear rollback. Do not remove existing controls before an alternative passes equivalent tests across both model routes and relevant service paths. Keep custom components wherever the SDK cannot preserve required semantics. A useful outcome can be a documented non-adoption decision, with evidence and a reconsideration trigger.

Checkpoint stores provided for local use do not automatically become an approved hosted shared backend. Likewise, workflow resume is not exactly-once execution, framework approval is not permission elevation, default telemetry is not privacy approval, and native tool calling is not a trusted tool allowlist. Persisted sessions, checkpoints and workflow state need explicit schema/retention/identity review.

No new package/provider/model, remote agent, hosted backend, arbitrary tool/shell, automatic deployment or sensitive action is authorized by this plan. Dependency changes require a separate tested decision; use the current pin where compatible.

## Primary references

Verify Python applicability against the selected pinned SDK, rather than assuming C# examples transfer directly.

- [Agent pipeline architecture](https://learn.microsoft.com/en-us/agent-framework/concepts/agents/agent-pipeline)
- [Workflow checkpoints](https://learn.microsoft.com/en-us/agent-framework/workflows/checkpoints)
- [Human-in-the-loop workflows](https://learn.microsoft.com/en-us/agent-framework/workflows/human-in-the-loop)
- [Official Python workflow samples](https://github.com/microsoft/agent-framework/blob/main/python/samples/03-workflows/README.md)
- [Observability](https://learn.microsoft.com/en-us/agent-framework/agents/observability)

## Selected domain scenario

[Stage 11 movie-theater orchestration](../stage-11/README.md) is the selected use case to evaluate the conditional orchestration track. Stage 10 keeps the common framework compatibility/equivalence work; Stage 11 owns concrete five-venue role contracts, identity/topology, movie/business facts, simulated bookings/pricing and end-to-end domain QA. This does not provision agents or waive earlier isolation/containment gates.
