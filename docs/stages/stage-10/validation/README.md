# Stage 10 validation and evidence plan

Status: **planned; no SDK adoption tests executed**. [Guide](../README.md) · [Tasks](../../../tasks/stage-10-framework-capabilities.md).

| Planned artifact | Required evidence |
| --- | --- |
| `framework-inventory.md`, `equivalence-policy.md` | Exact Python package/version/API and baseline behavior; selected goals, invariants and compatibility/rollback decisions |
| `middleware-results.json` | Agent/chat/function hook ordering, path coverage, audit-before-effects, failure/cancellation/stream behavior and no bypass |
| `checkpoint-decision.md`, `workflow-framework-results.json` | Storage/retention/schema decisions, owner/generation binding, restart/races, safe serialization and unknown-outcome handling |
| `approval-framework-results.json` | Exact action/actor/version binding, expiry/single use, replay/mutation/revocation denial and harmless fixture receipts |
| `streaming-framework-results.json` | Safe chunk publication, owner-isolated events, backpressure/cancellation, refusals/errors and real usage reconciliation |
| `mcp-adapter-comparison.md`, `mcp-framework-results.json` | Current/native protocol and credential behavior, pinned read-only contracts, bounds and security equivalence |
| `orchestration-decision.md`, optional `orchestration-results.json` | Use-case selection or deferral, identity separation, bounded delegation/cost and failure/isolation tests |
| `framework-adoption-review.md` | Adopt/retain decisions, measured complexity/performance/cost, source/config hashes, exact release, regressions and rollback evidence |

Artifacts are future deliverables, not passed results. Use deterministic synthetic fixtures first, classify local versus hosted observations, and retain failed/blocked cases. No raw tokens, private prompts/receipts or protected memory values in artifacts. Review instrumentation defaults before enabling any framework content capture.

Compare current and candidate implementations against identical fixtures and budgets, not only happy-path SDK samples. Include direct provider calls, automatic tool invocation, paused/active/queued work, old checkpoints, refusal/failure, concurrent resumes and sensitive-output boundaries. A native feature passes only when its supported usage preserves the application's independent security contracts.
