# 09 — Architecture review evidence register

Prepared 2026-10-20. This register links claims to retained source artifacts, with their tested scope. Evidence is pinned to repository snapshot `d65b5fc480a6eb8e593ac9fe0fd020dffd644b50`; the latest recorded runtime source is `681e8407a4097a243156d3d184d14cf7f67e37d4`. It is not a new live re-audit of Azure or directory configuration.

## Claim-to-evidence matrix

| ID | Claim supported | Evidence class and boundary | Artifact |
| --- | --- | --- | --- |
| E01 | Agent revision 31 / MCP revision 29, selected images, successful gated dev deployment | Hosted recorded release; does not establish current health forever | [Release digests](../stages/stage-6/validation/stage-6-release.json), deployment run 39388288350 |
| E02 | Authenticated owned sessions, bounded history, reset and scope/fence behavior | Local fixtures plus separately dated hosted user/auth checks; final topology and real multi-user/replica races open | [Stage 1 acceptance](../tasks/stage-1-chat.md), [expired-token record](../stages/stage-5/validation/stage-5-evidence/expired-token.json), [memory/auth validation](../stages/stage-4/validation/stage-4-validation.md) |
| E03 | Current-source TMDB movie reads work within budgets | 50 direct queries across ten sessions; not 50-user or throughput evidence | [Direct MCP test](../stages/stage-2/validation/mcp-50-query-results.md) |
| E04 | Approved skills load with pinned versions/digests; unknown/write/integrity/revocation cases deny | Hosted Stage 3 release plus local fixtures; not broad multi-operator control proof | [Skill validation](../stages/stage-3/validation/stage-3-validation.md), [redacted hosted skill metadata](../stages/stage-3/validation/stage-3-hosted-results.json) |
| E05 | Explicit-consent preferences persist, correct, expire and delete with generation fencing | Hosted same-user lifecycle/restart/cleanup; local cross-user/tenant fixtures | [Memory validation](../stages/stage-4/validation/stage-4-validation.md), [hosted metadata](../stages/stage-4/validation/stage-4-hosted-results.json) |
| E06 | Stopped ingress survives restart; separate operator can stop synthetic unresponsive workers | Hosted isolated two-revision fixture, 2.299 seconds; not universal provider termination or full kill SLA | [Stopped restart](../stages/stage-5/validation/stage-5-stopped-after-restart.md), [manual stop](../stages/stage-5/validation/stage-5-evidence/manual-stop.json), [synthetic watchdog](../stages/stage-5/validation/stage-5-evidence/watchdog-stop.json) |
| E07 | Actual Entra agent tokens used for inference/MCP; tokens cached; agent/model/tool spans ingested and redacted | Hosted dev; portal visibility additionally user-confirmed; not all governance/revocation features | [Acceptance](../stages/stage-5/validation/stage-5-agent-id-observability.md), [selected token claims](../stages/stage-5/validation/stage-5-evidence/agent-id-runtime-token-claims.json), [Azure spans](../stages/stage-5/validation/stage-5-evidence/agent-id-correlated-azure-spans.json) |
| E08 | Bounded 50-session behavior and read-only enforcement under adversarial requests | One Entra identity, not 50 distinct users; 47 final successes, 2 tool-budget stops, 1 provider rejection; initial overload retained | [Behavior report](../stages/stage-5/validation/movie-agent-50-users.md), [state checks](../stages/stage-5/validation/movie-agent-50-users-state.json) |
| E09 | Selected routing, finite quality/cost comparison, route-history transitions and zero observed forbidden dispatches | Current recorded dev release, fixed 20-case evaluation plus 3 same-user probes; no universal quality/grounding guarantee | [Routing acceptance](../stages/stage-6/validation/stage-6-model-routing.md), [Azure model traces](../stages/stage-6/validation/stage-6-traces.json), [protected audit/state verification](../stages/stage-6/validation/stage-6-security.json) |
| E10 | Both release images passed unresolved High/Critical gate | Time-specific local Grype/SBOM scan; lower severities remain | [Scan summary](../stages/stage-6/validation/stage-6-image-scans.json), workflow artifact `image-security-39388288350` |
| E11 | Final network topology is not yet accepted | Open gate; earlier isolated controlled-destination deny is historical, not final current egress enforcement | [Migration review](../stages/stage-5/stage-5-network-migration-review.md), [Stage 5 release checklist](../tasks/stage-5-production-guardrails.md) |
| E12 | Hosted distinct-user data-access exercise remains pending | Explicit missing evidence, not a passed test | [SEC-001](../../cybersecurity.md) |

## Quantified results that may be quoted

- The current local regression is **215 passing tests** at the recorded release. Earlier 47/81/126/190-test counts are historical milestones.
- The fixed Stage 6 benign set passed **10/10** on both model paths. Marker matching and three manually reviewed history-probe replies are bounded quality evidence, not full factuality/faithfulness scoring.
- Estimated benign inference cost: **$0.02214625 → $0.00496**, or **77.6% lower**. Median latency: **3.7395 → 5.146 seconds**. Prices are list-price estimates; inter-case pacing is excluded from latency.
- Actual current-version provider responses in routed/probe traces: **38 GPT-5 mini calls, 1 GPT-5 call**, across 23 runs. The baseline's 34 calls predate provider-model-field instrumentation and identify its pinned GPT-5 deployment.
- Latest security verification: **490 hash-verified audit envelopes**, **328 new dispatch checks**, including **230 checks** attributable to the 23 routed/probe runs; **zero forbidden capabilities** observed. Sampled TMDB fields, per-case saved preferences and the simulated-action receipts remained unchanged.
- **$0.21460975** is the conservative reservation total across the 23 routed/probe runs, not their observed token bill or an invoice.
- **Zero High/Critical** scan matches in both release images; 14 Medium, 1 Low and 1 Negligible remain per image at that scan.

## Evidence handling and refresh

Keep prompts, model answers, memory values, raw tool payloads and tokens out of routine review attachments. Use fixed synthetic/public movie fixtures, hashes, bounded expected fields, selected claims, run/trace IDs, exact versions, HTTP/error outcomes and before/after effects. SHA-256 checks detect changed event content; do not imply they prove an adversarial administrator cannot replace the entire evidence chain.

For repeatability, retain fixture/grader/configuration hashes, source and image digests, test command, observation time, principal type/count, policy epoch and environment. Evidence must include failures and the final result, with retries distinguished from separate experiments. A new revision/topology/identity/pricing change requires proportional revalidation; old screenshots alone do not refresh acceptance.

The full source scan/SBOM artifact has finite workflow retention. Archive an approved copy to the review evidence repository before it expires if a formal review needs longer retention. Do not claim the full artifact remains permanently available solely because its summary is committed.

## Source and evidence references

- [Recorded latest acceptance](https://github.com/gardlt/az-maf-agent/blob/d65b5fc480a6eb8e593ac9fe0fd020dffd644b50/docs/validation/stage-6-model-routing.md)
- [Release source and workflow](https://github.com/gardlt/az-maf-agent/blob/d65b5fc480a6eb8e593ac9fe0fd020dffd644b50/docs/validation/stage-6-release.json)
- [Latest security JSON](https://github.com/gardlt/az-maf-agent/blob/d65b5fc480a6eb8e593ac9fe0fd020dffd644b50/docs/validation/stage-6-security.json)
- [Latest trace JSON](https://github.com/gardlt/az-maf-agent/blob/d65b5fc480a6eb8e593ac9fe0fd020dffd644b50/docs/validation/stage-6-traces.json)
- [Stage 5 open release gates](https://github.com/gardlt/az-maf-agent/blob/d65b5fc480a6eb8e593ac9fe0fd020dffd644b50/docs/tasks/stage-5-production-guardrails.md)

Related: [review index](README.md), [evidence register](09-evidence-register.md), [open review gates](10-review-gaps.md).
