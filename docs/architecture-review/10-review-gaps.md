# 10 — Open architecture review gates and decisions

Status: **open review register**, 2026-10-20. No architecture-board approval, production authorization, risk acceptance, named accountable owner or remediation deadline has been recorded here. Roles below are proposed responsibilities to assign, not existing commitments by a named person.

## Readiness by area

| Area | Evidence-backed position | Remaining review boundary |
| --- | --- | --- |
| Chat/session foundation | Implemented; local isolation/fencing plus hosted auth/chat checks | Real distinct-user and replica/race tests; final bypass tests |
| Movie MCP | Dev teaching scope complete, bounded read-only tools | Final network topology and broader factual grounding |
| Reviewed skills | Dev teaching scope complete | Multi-operator/revocation and final production operations |
| Preferences | Selected dev policy complete | Real hosted cross-user proof; future backup/restore policy |
| Guardrails | Implemented milestones with hosted/synthetic evidence | Stage 5 is not complete |
| Model routing | Stage 6 selected dev acceptance complete | Broader workloads, effective production rates and inherited release gates |
| Identity/monitoring | Dev Agent ID downstream use and trace ingestion proved | Legacy grants, revocation, richer failure/outage cases and governance |
| Production promotion | Not established by this package | Review approval, environment controls, current inventory and all applicable gates |

## Action register

| ID | Open item / type | Required evidence or decision | Proposed accountable role |
| --- | --- | --- | --- |
| R01 | Final network enforcement — existing release gate | Choose app cutover/image delivery compatible with ACR Basic; validate authorized paths, unapproved destination deny, reachable-host write deny, endpoint/redirect escape deny, internal MCP ingress/auth and absence of alternate public API bypass under final topology | Cloud/platform owner, to assign |
| R02 | Two real hosted users — existing security gate | Execute SEC-001 with owned synthetic A/B data, positive owner controls, foreign read/write/reset/cancel/receipt denials, spoof/tamper probes, before/after state and cleanup | Application security owner, to assign |
| R03 | Replica, revision and shared-state races — existing release gate | Exercise duplicate requests, concurrent commits, reset races, restarts/revisions, active revocation, outages/partitions and late completions with persisted counters and zero history resurrection | Application/platform owner, to assign |
| R04 | Answer grounding/faithfulness — proposed assurance extension | Define broader versioned public/synthetic facts, expected source IDs/fields, source-use rules and predeclared unsupported-claim/abstention metrics; test missing, ambiguous, irrelevant, stale and poisoned data across both routes | AI quality and domain owner, to assign |
| R05 | Hosted operational recovery/secret lifecycle — existing release gates | Complete remaining hosted approval/outage/control cases, scoped secret-store/rotation evidence, identity revocation, legacy-grant disposition, schema-compatible rollback and incident rehearsal | Security and operations owners, to assign |
| R06 | Observability and cleanup response — existing operational gaps | Verify failure/denial/cancellation and exporter outage/backpressure under load; confirm redaction/retention, cleanup physical-expiry targets, named on-call and alert acknowledgement/escalation | Operations owner, to assign |
| R07 | Stage/prod promotion controls — review confirmation | Inspect actual GitHub protections, reviewer settings, OIDC subjects, deployment-role scope, directory/bootstrap boundary and separately provisioned environment resources | Release/platform owner, to assign |
| R08 | Production compatibility, cost and capacity — review decision | Verify deployment availability/version retirement, effective token prices, rate/quota behavior, request/concurrency needs, storage growth limits, usage/cost alerts and measurable service objectives | Cloud/application owner, to assign |
| R10 | Provider data handling — proposed review confirmation | Verify the selected GlobalStandard service/configuration against required data location, provider retention/monitoring, classification and permitted model-context policy; record approved terms and scope | Data/privacy and cloud owners, to assign |
| R09 | Residual vulnerability and evidence lifecycle — review disposition | Assign lower-severity findings an owner/disposition; refresh scan database/results, retain required SBOM/evidence beyond workflow expiration and validate dependency/secret response procedures | Supply-chain/security owner, to assign |

**Due dates: unassigned.** Set named owners, review dates and closure evidence before approving the corresponding release. Do not silently mark a gate accepted because an implementation milestone or the Stage 6 dev task is complete.

## Proposed review outcomes

The review can acknowledge the demonstrated dev baseline and its chosen architecture while leaving production promotion pending. Any conditional approval must identify the exact environment, scope, risks, compensating controls, accountable person and expiry/review date. These documents do not grant that approval.

For the initial review, resolve whether the required claim is an enforceable read-only agent architecture, a domain-grounded answering product, or both. They need different evidence. Source retrieval and tool authorization are substantially evidenced; sentence-level factual grounding is not universally enforced. R04 is an added review proposal, not an undisclosed failure of the already-completed Stage 6 fixed evaluation.

## Closure template

For each item record: decision ID; named owner; environment/source/image/policy versions; fixture and threshold fixed before execution; exact test and observation time; expected/observed results; backend effects; evidence link; remaining limitations; reviewer; and closure or risk-acceptance date. A disagreement remains open until its disposition is explicit.

No risky live exercise, new permission, changed cost limit or new platform dependency is authorized just by adding a row to this register. Prepare the concrete change/test and use the existing authorization process.

## Source and evidence references

- [Existing production checklist](https://github.com/gardlt/az-maf-agent/blob/d65b5fc480a6eb8e593ac9fe0fd020dffd644b50/docs/tasks/stage-5-production-guardrails.md)
- [Two-user scenario and completion criteria](https://github.com/gardlt/az-maf-agent/blob/d65b5fc480a6eb8e593ac9fe0fd020dffd644b50/cybersecurity.md)
- [Selected network decision and remaining cutover](https://github.com/gardlt/az-maf-agent/blob/d65b5fc480a6eb8e593ac9fe0fd020dffd644b50/docs/stage-5-network-migration-review.md)
- [Remaining telemetry cases](https://github.com/gardlt/az-maf-agent/blob/d65b5fc480a6eb8e593ac9fe0fd020dffd644b50/docs/azure-monitor-agents-view.md)

Related: [review index](README.md), [evidence register](09-evidence-register.md), [open review gates](10-review-gaps.md).

## Planned Stage 7 containment extension

[Stage 7 plan](../stages/stage-7/README.md) and [ordered tasks](../tasks/stage-7-agent-containment.md) track automatic/manual disable of one agent, resource-specific stale-token enforcement, independent controller authority and failure/recovery QA. Status is planned only. This adds no completion evidence and does not close R01–R05 or the existing identity/operations gates.
