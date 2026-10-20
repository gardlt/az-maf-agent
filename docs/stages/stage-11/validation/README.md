# Stage 11 validation and evidence plan

Status: **planned; no movie-theater multi-agent tests executed**. [Guide](../README.md) · [Tasks](../../../tasks/stage-11-movie-orchestration.md).

| Planned artifact | Evidence required |
| --- | --- |
| `scenario-policy.md`, fixture hashes | Selected two-small/two-medium/one-large configuration, both booking types, source/business facts, frozen quality/safety thresholds and simulation exclusions |
| `a2a-design.md`, `agent-identity-inventory.json`, `delegation-contract.md` | Actual protocol/version compatibility, independent service/identity/federation boundaries and authenticated owner/purpose binding |
| `task-schemas.md`, `movie-data-contract.md` | Strict role task/result/error schemas, source provenance, current/missing movie fields and any approved read-only extension |
| `specialist-results.json`, `orchestrator-results.json` | Actual role execution, bounded graph/fan-out, validated artifacts and deterministic final constraint checks |
| `root-accounting-results.json`, `workflow-lifecycle-results.json` | Parent/child aggregate limits, restart/retry/idempotency, cancellation/expiry, checkpoints, unknown outcomes and no quota reset |
| `program-quality-results.json` | Sourced film facts, synthetic screen/time arithmetic, uncertainty, both routes and single-agent comparison |
| `a2a-security-results.json` | Hostile peers/forged cards/tasks, ownership/auth denials, alternate credentials, one-agent quarantine and unaffected-peer positive controls |
| `hosted-orchestration.md`, release/evidence manifest | Real inter-service authenticated exchanges, identity/model/tool traces, exact versions/topology, budget/cost and failure/cleanup observations |
| `operations-backend-results.json`, `booking-results.json` | Authoritative synthetic showtimes/seats/holds/ticket and private-group appointments, per-venue roles, atomic allocation, locked quotes and actual commit receipts |
| `business-metrics-results.json`, `seasonality-results.json` | Deterministic venue/film metrics, known synthetic facts, cost completeness, regional calendar hypotheses and time-based holdouts without future leakage |
| `pricing-simulation-results.json` | Configured candidate grid/objective, fixed-point money arithmetic, ordinary/seasonal demand, sensitivity, owner-approved publication and protected existing quotes |
| `business-simulation-security-results.json` | Cross-venue write denial, exact approvals, forged price/forecast/context, double-booking/overlap, rollback and uncertain commits |
| `orchestration-review.md` | Measured value, latency/cost/quality tradeoffs, owners, scope, incident rehearsal and rollback |

All artifacts are future deliverables. Local fake agents can develop contracts but cannot establish hosted A2A identity isolation, networking or containment. Never retain raw tokens, private user preferences, unrestricted peer prompts or sensitive receipts in evidence. Record root/child task IDs and selected identity/model/source metadata instead.

## Scenario suite (all pending)

1. Successful five-location program/operations workflows using the selected size profiles, verified movie facts and stateful simulated showtimes/reservations; no live cinema booking/payment/rights claim.
2. Missing runtime/certification/source, conflicting constraints, unsupported theme, ambiguous date/time zone, empty results and missing specialist; clarify or return truthful partial output.
3. Concurrent users, foreign root/child/artifact IDs, forged caller/owner context, replayed/expired delegation and mismatched audience/purpose/version.
4. Malicious manager/researcher/analyst/strategist messages, prompt injection in movie/peer data, forged task completion, tool/agent card drift and unapproved endpoint/callback.
5. Parent/child retries, duplicate delivery, races, queued work, reconnect/checkpoint resume and delayed results; no duplicate authority, stale resurrection or budget reset.
6. Parent timeout/cancel, child outage, independently disabled specialist, cached/external token and direct-MI bypass; required peers remain authorized and quarantined work stays fenced.
7. Root cost/token/model-call/tool limits under fan-out, attempted re-delegation/cycles/new-root escape and stronger-model selection; no implicit limit multiplication.
8. Provider/MCP/controller/state/network failure, partial response and uncertain accepted work; preserve reservations and clear status, no policy/identity bypass fallback.
9. Recovery, role/schema upgrade and rollback; old task/approval/result replay cannot reopen authority, and unrelated agents/data remain intact.

10. Verify two small (2 × 80 seats each), two medium (4 × 150) and one large (8 × 250) venue: five locations, twenty screens and 3,520 seats before explicit unavailable-seat adjustments. Cross-location requests must not change the wrong theater.
11. Concurrent last-seat/slot holds, expiration, duplicate ticket confirmation/cancellation, private/group-event exclusivity, venue local-time/daylight-saving and screen turnaround/maintenance; no double booking or unverified success.
12. Ordinary, Halloween/horror and Christmas/holiday scenarios, sparse/cold-start data, local audience differences and corrupted cost/sales inputs; holdout scoring separates recommendations from observations and rejects guaranteed-profit claims.
13. Recompute bounded price candidates and expected contribution using declared synthetic inputs; test floor/ceiling/grid/currency/rounding, sold-out/zero demand, discounts/quotes if selected, stale owner approval, negative/missing costs and no repricing of held/confirmed reservations. No gateway or payment credential collection.
14. Read-only analyst/researcher credentials attempt schedule/price/reservation mutation; customer booking consent attempts to publish a program; an agent invents approval, real availability or financial settlement. Verify backend effects and appropriate denials.

[Simulation defaults](../simulation-defaults.json) and the [worked capacity/pricing examples](../README.md) are planning inputs, not passing acceptance artifacts. Price optimization must compare against current-price/simple-rule/nonseasonal baselines and report uncertainty.

Freeze comparative criteria before scoring; report the single-agent baseline as well as the multi-agent outcome. Better story structure or more agents is not proof of improved correctness, security or cost.
