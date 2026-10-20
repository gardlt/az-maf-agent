# Stage 8: Operational readiness and assurance

Status: **planned**, 2026-10-20. This stage records the repository gap assessment; it does not implement controls, approve production or close earlier stages.

[All stages](../README.md) · [Actionable tasks](../../tasks/stage-8-operational-readiness.md) · [Validation plan](validation/README.md) · [Architecture review gaps](../../architecture-review/10-review-gaps.md)

## Outcome

Make the existing agent platform reproducible to operate and independently reviewable: finish the required security boundaries, prove hosted isolation and answer grounding, automate acceptance evidence, rehearse operations and provide clear repository contribution/security guidance.

This stage combines readiness closure with explicitly tracked application and security extensions. Existing Stage 5 production guardrails and Stage 7 containment remain their respective implementation owners. Stage 8 links their closure evidence into a final readiness decision; it does not move unchecked tasks out of those stages or treat a later stage number as acceptance.

## Workstreams and dependencies

| Workstream | Required result | Dependency / existing owner |
| --- | --- | --- |
| Individual-agent containment | Independent controller, authenticated alerts, service-level denial of cached tokens and alternate credentials, manual disable reconciliation and explicit recovery | Stage 7 implementation and hosted QA; Stage 8 consumes results, not a second controller design |
| Hosted user/agent isolation and concurrency | Two real users and two individual agents with positive controls, replica/revision/reset races, restart and late-response fences, preserved accounting | Stage 1 shared-session gates, Stage 5 controls and Stage 7 agent isolation |
| Final network enforcement | Approved deployed topology rejects forbidden destinations, alternate paths, redirect/endpoint escapes and unauthorized operations while required services remain available | Stage 5/network gate; retain the decision to keep ACR Basic unless separately changed by the user |
| Answer grounding | Versioned factual fixtures, source attribution, supported-claim checks, appropriate abstention and poisoned/stale/missing-source cases across both model routes | Existing TMDB/MCP retrieval and routing; retrieval success is not answer faithfulness |
| Repeatable release evidence | One documented acceptance workflow orchestrates existing scripts, bounded budgets, failure artifacts, link validation and evidence integrity/provenance | Current tests, infrastructure validator, hosted scripts and selected-environment permissions |
| Operations and promotion | Rehearsed outage/rotation/rollback/recovery, measurable objectives, named incident ownership, scoped deployment access and reviewed stage/prod promotion controls | Existing runtime controls, logs/alerts and applicable Stage 5/7 closure |
| Repository usability and governance | Owner-selected license, contribution/security reporting guidance, code ownership and reproducible newcomer setup | Maintainer decisions; do not invent a license grant, reporting contact or accountable owner |

## Additional application and guardrail scope

The [S8-10–20 tasks](../../tasks/stage-8-operational-readiness.md) add streaming/progress, durable pause/resume workflows, source-backed answer presentation, conditional real action approvals and conditional specialist-agent delegation. Security extensions cover indirect prompt injection/context poisoning, data-loss prevention, safe output rendering, per-action authority, ingress/queue abuse and tool/delegation contract changes.

Start with streaming/workflow design and adversarial injection/exfiltration fixtures. Source presentation extends the existing grounding workstream. Real consequential actions or extra agents require a selected use case and explicit authority review; they do not become enabled by appearing here. Keep arbitrary shell access, unrestricted browsing and autonomous write actions outside this scope. Existing approval simulations, pinned tool contracts, ownership checks and budgets must be extended rather than replaced.

## Scope boundaries

Keep the two existing service applications and their current feature contracts. No new model, writable movie tool, vector store, tenant-wide identity kill switch or autonomous recovery is implied. A license selection, new cloud privilege, network cutover, billable resource or disruptive hosted rehearsal requires its concrete reviewed execution scope. Ordinary planning and local validation can proceed independently.

No universal safety or factual accuracy claim follows from a finite evaluation. Record the exact release, environment, identity count, topology, provider configuration, fixture set and limits. Exclude private user data and credentials from evidence. Preserve failed attempts, unresolved effects, aggregate budgets and historical artifacts.

The observed Stage 7 live drill is a starting finding: directory disable eventually rejected fresh tokens, but cached Foundry/MCP and workload-identity Blob access continued. The ordinary chat recovery canary was budget-blocked. These are open readiness inputs, not Stage 8 passing results.

## Sensitive-data specialization

[Stage 9](../stage-9/README.md) extends the general Stage 8 DLP/output/authority interfaces with field-level PII/payment-data and receipt policies. It owns receipt intake, redaction-quality, sensitive storage/lifecycle and review gates; Stage 8 retains generic egress/injection controls. Neither plan enables real data collection or payment actions.

## Framework adoption track

[Stage 10](../stage-10/README.md) evaluates native SDK mechanisms for the Stage 8 feature contracts. Keep one implementation per selected feature: Stage 8 states required behavior and assurance; Stage 10 compares/adopts middleware, workflow, approval, streaming and MCP/orchestration APIs while preserving those controls. Native support alone does not close a readiness gate.

The conditional specialist-delegation feature now has a selected planning scenario in [Stage 11](../stage-11/README.md): a five-location owner orchestrator coordinating scoped theater managers plus movie/seasonality research, performance analytics and programming strategy. Its implementation remains dependent on Stage 8 authority/budget controls, Stage 10 framework selection and Stage 7 containment.
