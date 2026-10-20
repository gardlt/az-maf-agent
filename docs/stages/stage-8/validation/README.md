# Stage 8 validation and evidence plan

Status: **planned; no Stage 8 results exist**. [Stage guide](../README.md) · [Ordered tasks](../../../tasks/stage-8-operational-readiness.md).

## Planned evidence

| Artifact | Required content |
| --- | --- |
| `readiness-scope.md` | Environment/release, gate mapping, named owners/reviewers, dependencies, dates, thresholds and explicit decisions |
| `containment-closure.md` | Links to Stage 7 evidence and remaining limitations; no duplicate or retroactive success claims |
| `hosted-isolation.md`, `concurrency-results.json` | Real A/B user/agent counts, positive controls, foreign-data denials, replica/race/restart behavior and before/after effects |
| `network-acceptance.md` | Actual deployed topology, required/forbidden routes, all five network cases and bypass/operation denials |
| `grounding-policy.md`, `grounding-results.json` | Frozen dataset/grader/config hashes, source IDs/facts, supported/unsupported claims, citations, abstention, both routes and failures |
| `acceptance-workflow.md`, `release-evidence-manifest.json` | Reproduction commands, safety modes, versions, durations, hashes, retained failures and local/hosted classification |
| `operations-rehearsal.md`, `promotion-review.md` | Rotation/rollback/outage/recovery observations, incident ownership, measured objectives and actual environment protections |
| `repository-readiness.md` | Maintainer license decision, contribution/security/code-owner guidance and fresh-setup smoke evidence |
| `streaming-results.md` | Owner-isolated events, bounded chunks/backpressure, safe cancellation/reconnect and no sensitive/hidden-reasoning disclosure |
| `workflow-policy.md`, `workflow-results.json` | Reviewed checkpoint storage/retention, restart/resume/race fences, unknown outcomes and accounting preservation |
| `source-response-results.json` | Validated source attribution, supported claims, retrieval time, abstention and safe source links; feeds grounding results |
| `action-approval-results.md`, `delegation-results.md` | Conditional scope decisions or approved action/handoff binding, isolation, bounded authority and failure tests |
| `injection-results.json`, `dlp-results.json`, `data-egress-policy.md` | Poisoned-input/context and exfiltration fixtures, coverage/false positives, destination/data rules and safe failure behavior |
| `output-safety-results.md`, `action-authority-results.json` | Render/schema/URL safety, per-action principal/resource/purpose binding and confused-deputy/replay denials |
| `abuse-admission-results.json`, `tool-change-results.md` | Frozen distributed admission/queue limits and reviewed tool/delegation identity/schema/permission changes |
| `acceptance-review.md` | Per-gate outcome, reviewer/approval scope, residual risks, unresolved blockers and review dates |

All artifacts above are future deliverables, not existing files or passed results. Add links when genuine evidence is captured. Existing [Stage 7 evidence](../../stage-7/validation/evidence/README.md) and [architecture gap register](../../../architecture-review/10-review-gaps.md) remain authoritative inputs within their recorded scope.

## Required test categories

- Security: foreign-user data access, cross-agent token use, existing token/session and direct managed-identity bypass, unapproved tool/destination, forged approval and policy tampering.
- Concurrency/resilience: duplicate requests, simultaneous writes, replica/revision changes, reset/delete races, late completion, controller/storage/provider outages and queue replay after recovery.
- Grounding: correct-source factual answers, unsupported claim detection, correct attribution, uncertainty/abstention, missing/stale/conflicting/poisoned evidence and routing differences.
- Additional features/security: stream-fragment injection, foreign event subscribers, duplicate checkpoint resumes, forged/expired action approval, delegated authority escalation, encoded secret canaries, dangerous links/images, unauthenticated floods and tool contract drift. Conditional features require an explicit tested scope or documented deferral.
- Operations/delivery: locked clean setup, repeatable CI acceptance, credential rotation, rollback, budget exhaustion, alert failure/escalation, data cleanup and retained evidence verification.

Do not infer read-denial from unchanged stored bytes alone. Retain independent authorization/audit observations without private record contents. A 429 budget block is a block, not a passed recovery chat. Failed, skipped and inconclusive cases must remain visible. Approve thresholds before scoring and preserve prior evidence rather than rewriting history to appear complete.
