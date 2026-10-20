# Stage 6 task — Application-controlled model routing

Status: complete for the selected dev teaching scope, 2026-10-20. Local and hosted evidence: [Stage 6 acceptance](../stages/stage-6/validation/stage-6-model-routing.md). This stage adds the requested cost-aware model selection to the Python agent. It does not close outstanding [Stage 5 release gates](stage-5-production-guardrails.md).

## Goal and outcome

Use an approved smaller model for routine movie assistance and an approved stronger model when application policy requires it. Select the model in application code while preserving conversation history, Entra Agent ID, read-only MCP permissions, governed memory, shared budgets and operator controls.

The [.NET runtime model routing feature](https://learn.microsoft.com/en-us/agent-framework/concepts/agents/runtime-model-routing) is the reference behavior. Its documentation currently states that Python support is unavailable. Implement an application-owned equivalent around this agent's existing bounded model/tool loop; do not assume the .NET client is available in Python.

Implementation details and operator procedures: [routing architecture](../stages/stage-6/stage-6-model-routing.md).

## Implementation tasks

- [x] Inventory existing Foundry deployments, verify model/tool compatibility, current pricing and capacity, and record the selected smaller and stronger models. Do not provision a deployment or change the default based on an unverified model name or price.
- [x] Add a strict, versioned configuration of named approved model routes, including deployment, API compatibility, context limits and input/output pricing. Preserve existing single-model configurations.
- [x] Define deterministic routing criteria and precedence: routine reads use the smaller route; reviewed complex-work criteria select the stronger route. Document examples and ambiguous cases before evaluation. Client prompts, MCP content and saved preferences cannot supply deployments, endpoints, prices or authority.
- [x] Integrate route selection into the actual Python inference/tool loop and the text-only path. Keep one route stable within a run initially and retain caller-managed conversation history across runs that choose different models.
- [x] Resolve route pricing from trusted server configuration in both local and shared accounting. Every dispatch and retry must reserve against the same run/user/day budgets; routing must not reset aggregate counters or permit unpriced calls.
- [x] Preserve current permission checks, policy epochs, cancellation, leases, late-result fences, MCP schemas and tool limits for every route. Provider rejection, content filtering and permission denial must not trigger stronger-model retries.
- [x] Define fail-closed behavior for unavailable routes and unknown provider outcomes. Any future fallback must be explicitly configured, bounded, separately reserved and tested.
- [x] Emit content-free route ID, selected deployment, policy version and bounded selection reason on correlated agent/model traces. Keep prompts, tokens, private preferences and tool payloads out of routing evidence.
- [x] Add local regression coverage for route decisions, invalid configuration, cross-route history, concurrent isolation, route-specific pricing, aggregate limits, cancellation and unchanged forbidden-tool enforcement.
- [x] Run a fixed benign/adversarial comparison against the current GPT-5 baseline. Freeze dataset, grader, quality threshold, routing expectations and cost/latency measurement method before scoring. Do not change thresholds merely to pass the cheaper model.
- [x] Deploy through the existing per-application CI, vulnerability gate and dev workflow. Verify actual smaller/stronger downstream model use with Entra Agent ID and correlated Application Insights traces.
- [x] Document configuration, local use, operator override/rollback, measured tradeoffs and residual limitations; update the architecture and stage index with evidence.

## Acceptance criteria

- [x] Routine fixtures select the approved smaller model; declared complex fixtures select the approved stronger model, with repeatable bounded reasons.
- [x] Hosted evidence identifies the actual deployed model for both paths, not only the intended routing decision.
- [x] Context remains available after route changes without exposing another user's history or saved preferences.
- [x] All routes retain authorization, read-only MCP enforcement, cancellation and shared accounting. Adversarial fixtures produce zero forbidden effects.
- [x] Unknown pricing, invalid/unapproved routes and unavailable control state prevent billable dispatch. Retries and model changes cannot bypass limits or resurrect cancelled work.
- [x] The frozen benign set meets the existing 90% success floor, with a separate qualitative review and zero forbidden effects. Report baseline and routed results, failures, latency and token usage; distinguish actual usage estimates from conservative reservations and invoices.
- [x] Comparable routine workloads show lower estimated inference cost using verified prices. Record the stronger-model tradeoff and any workload where routing does not save money.
- [x] Both release images satisfy the existing unresolved High/Critical vulnerability gate; the new agent revision passes hosted canaries and has a schema-compatible rollback path.

## Scope boundaries

Start with application policy and a small approved route catalog in the existing Foundry inference path. An additional LLM router, automatic model provisioning, arbitrary caller-selected models, model-granted permissions and permission-bypassing fallback are outside this first implementation. Stage/prod promotion and outstanding Stage 5 network/isolation acceptance remain separate gates.

## Evidence to retain

Versioned routing configuration and decision fixtures; verified pricing references and date; baseline/routed evaluation reports; redacted route/model/usage/timing traces; release image digests; local and hosted results; and documented rollback and remaining limitations.

Completion is bounded to the evidence above: 215 local tests, a fixed 20-case comparison, actual model traces, three same-user history probes and protected audit/state checks. Distinct-user hosted isolation and final network/operational acceptance remain Stage 5 work.
