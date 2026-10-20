# Stage 6 task — Application-controlled model routing

Status: discovery started; implementation and hosted acceptance remain open. This stage adds the requested cost-aware model selection to the Python agent. It does not close outstanding [Stage 5 release gates](stage-5-production-guardrails.md).

## Goal and outcome

Use an approved smaller model for routine movie assistance and an approved stronger model when application policy requires it. Select the model in application code while preserving conversation history, Entra Agent ID, read-only MCP permissions, governed memory, shared budgets and operator controls.

The [.NET runtime model routing feature](https://learn.microsoft.com/en-us/agent-framework/concepts/agents/runtime-model-routing) is the reference behavior. Its documentation currently states that Python support is unavailable. Implement an application-owned equivalent around this agent's existing bounded model/tool loop; do not assume the .NET client is available in Python.

## Implementation tasks

- [ ] Inventory existing Foundry deployments, verify model/tool compatibility, current pricing and capacity, and record the selected smaller and stronger models. Do not provision a deployment or change the default based on an unverified model name or price.
- [ ] Add a strict, versioned configuration of named approved model routes, including deployment, API compatibility, context limits and input/output pricing. Preserve existing single-model configurations.
- [ ] Define deterministic routing criteria and precedence: routine reads use the smaller route; reviewed complex-work criteria select the stronger route. Document examples and ambiguous cases before evaluation. Client prompts, MCP content and saved preferences cannot supply deployments, endpoints, prices or authority.
- [ ] Integrate route selection into the actual Python inference/tool loop and the text-only path. Keep one route stable within a run initially and retain caller-managed conversation history across runs that choose different models.
- [ ] Resolve route pricing from trusted server configuration in both local and shared accounting. Every dispatch and retry must reserve against the same run/user/day budgets; routing must not reset aggregate counters or permit unpriced calls.
- [ ] Preserve current permission checks, policy epochs, cancellation, leases, late-result fences, MCP schemas and tool limits for every route. Provider rejection, content filtering and permission denial must not trigger stronger-model retries.
- [ ] Define fail-closed behavior for unavailable routes and unknown provider outcomes. Any future fallback must be explicitly configured, bounded, separately reserved and tested.
- [ ] Emit content-free route ID, selected deployment, policy version and bounded selection reason on correlated agent/model traces. Keep prompts, tokens, private preferences and tool payloads out of routing evidence.
- [ ] Add local regression coverage for route decisions, invalid configuration, cross-route history, concurrent isolation, route-specific pricing, aggregate limits, cancellation and unchanged forbidden-tool enforcement.
- [ ] Run a fixed benign/adversarial comparison against the current GPT-5 baseline. Freeze dataset, grader, quality threshold, routing expectations and cost/latency measurement method before scoring. Do not change thresholds merely to pass the cheaper model.
- [ ] Deploy through the existing per-application CI, vulnerability gate and dev workflow. Verify actual smaller/stronger downstream model use with Entra Agent ID and correlated Application Insights traces.
- [ ] Document configuration, local use, operator override/rollback, measured tradeoffs and residual limitations; update the architecture and stage index with evidence.

## Acceptance criteria

- [ ] Routine fixtures select the approved smaller model; declared complex fixtures select the approved stronger model, with repeatable bounded reasons.
- [ ] Hosted evidence identifies the actual deployed model for both paths, not only the intended routing decision.
- [ ] Context remains available after route changes without exposing another user's history or saved preferences.
- [ ] All routes retain authorization, read-only MCP enforcement, cancellation and shared accounting. Adversarial fixtures produce zero forbidden effects.
- [ ] Unknown pricing, invalid/unapproved routes and unavailable control state prevent billable dispatch. Retries and model changes cannot bypass limits or resurrect cancelled work.
- [ ] The frozen benign set meets the existing 90% success floor, with a separate qualitative review and zero forbidden effects. Report baseline and routed results, failures, latency and token usage; distinguish actual usage estimates from conservative reservations and invoices.
- [ ] Comparable routine workloads show lower estimated inference cost using verified prices. Record the stronger-model tradeoff and any workload where routing does not save money.
- [ ] Both release images satisfy the existing unresolved High/Critical vulnerability gate; the new agent revision passes hosted canaries and has a schema-compatible rollback path.

## Scope boundaries

Start with application policy and a small approved route catalog in the existing Foundry inference path. An additional LLM router, automatic model provisioning, arbitrary caller-selected models, model-granted permissions and permission-bypassing fallback are outside this first implementation. Stage/prod promotion and outstanding Stage 5 network/isolation acceptance remain separate gates.

## Evidence to retain

Versioned routing configuration and decision fixtures; verified pricing references and date; baseline/routed evaluation reports; redacted route/model/usage/timing traces; release image digests; local and hosted results; and documented rollback and remaining limitations.
