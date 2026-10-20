# Stage 7 tasks — Automatic individual-agent containment

Status: **implementation started locally; hosted acceptance remains open**, 2026-10-20. The [live identity drill](../stages/stage-7/validation/live-disable-drill-2026-10-20.md) verified disable/restoration but left resource containment open. See [local foundation results](../stages/stage-7/validation/local-quarantine-results.md).

[Design and Microsoft references](../stages/stage-7/README.md) · [Validation matrix](../stages/stage-7/validation/README.md) · [Roadmap](README.md)

Goal: a configured trusted alert/threshold or a manual emergency disable quarantines one agent and disables its individual Entra Agent ID, with independently verified denial across every Azure access path. Keep other agents working. New-token issuance denial alone is insufficient. All acceptance checkboxes below remain open; the first local slice is not stage completion.

## Ordered implementation tasks and dependencies

| ID | Depends on | Action and concrete deliverable | Gate / evidence under Stage 7 validation |
| --- | --- | --- | --- |
| S7-01 | None | Inventory the deployed release, tenant and environment; map every logical agent to its unique Agent ID object/application IDs, blueprint/principal, system/user-assigned identities, federated credentials, compute/replicas, owners and sponsor. Include two test agents A/B with separate synthetic data. | No ambiguous target or cross-agent token minting; `identity-resource-inventory.json`. |
| S7-02 | S7-01 | Enumerate all effective/inherited/group grants and reachable Foundry, Blob, MCP, ARM and other service operations; record actual credential/audience, fallback, keys/SAS, network path, shared dependencies and denial mechanism. Resolve legacy runtime grants and direct MI bypass. | Every reachable operation assigned an independently enforceable control; missing rows block release; `resource-enforcement-matrix.md`. |
| S7-03 | S7-01, S7-02 | Investigate supported Graph individual-disable API/version, exact object property/action, readback, app-only permissions and constrained target scope. Verify licensing, preview/support status, agent-user variants, shared-blueprint exchange isolation, service token/connection revocation and propagation. Run only separately authorized isolated probes. | Record supported/unsupported/unknown behavior, source/date, measured maximums and selected least-privilege design; `platform-investigation.md`. No inferred instantaneous revocation. |
| S7-04 | S7-02, S7-03 | Design service-specific enforcement for existing/exfiltrated tokens and alternate credentials. Select isolated compute/egress or exclusive brokers/dedicated resources as needed; prevent direct bypass. Define preserving controller, cleanup, logs and agent B during A containment. | Architecture/security review resolves all bypasses and shared blast-radius blockers before runtime work; `boundary-decision.md`. |
| S7-05 | S7-03, S7-04 | Freeze versioned detection rules, configurable thresholds/windows/severity, authenticated alert contract, attribution, event deduplication/age policy, false-positive handling, proposed timing targets, incident owners and escalation channel. Reuse existing insights rather than rebuilding monitoring. | Review approves test policy and numerical maximums before scoring; `detection-policy.json`, `acceptance-policy.md`. |
| S7-06 | S7-04, S7-05 | Specify independent controller hosting, durable inbox/quarantine, registry, append-only evidence, watchdog and service authorization leases. Produce exact Graph/Azure permission manifest and negative-permission tests; separate disable from recovery authority. | Agent cannot change controller/rules/registry/quarantine, impersonate controller or self-enable; controller cannot disable outside approved scope; `controller-permissions.md`. Infrastructure/deployment review is separate authorization. |
| S7-07 | S7-06 | Implement shared per-Agent-ID quarantine generation, dispatch and queue fencing, active-result rejection, retry/approval fencing and reservation reconciliation across replicas. Add independent service enforcement for each selected boundary. | Quarantine precedes acknowledgment; partition/stale cache fails closed; no accounting reset, foreign data effects or late-result resurrection; `local-quarantine-results.json`. |
| S7-08 | S7-03, S7-06, S7-07 | Implement authenticated alert handler and exact-identity disable with durable idempotency, bounded retry/backoff, Graph/resource readback, verification workers, per-action status and independent failure escalation. | Duplicate/out-of-order alerts and partial success converge without enabling or touching shared objects; all unknown outcomes remain quarantined; `controller-results.json`. |
| S7-09 | S7-08 | Use the individual-agent Disable action in the Entra admin center as the manual control. Implement authenticated controller observation/reconciliation of portal state/audit, actor/tenant/identity binding, status and limitations; no custom button required. | Works without alert delivery or agent cooperation; unauthorized disable/reset denied; target A only; `manual-disable-results.json`. |
| S7-10 | S7-07, S7-08 | Implement heartbeat/lease watchdog, durable alert replay and explicit manual recovery workflow with incident review and generation-bound authorization. Keep quarantine until identity/resource canaries pass. | Controller outage fails closed; re-enable requires distinct operator action; no replayed work, old approval reuse or budget reset; `outage-recovery-results.json`. |
| S7-11 | S7-07–S7-10 | Run deterministic local fault-injection QA and authorized hosted A/B drills across the full validation matrix, including external pre-issued tokens, MI fallback, open sessions, concurrent replicas and resource-state checks. Freeze fixtures and capture before/after state. | All safety cases pass maximums; at least 20 timing drills; zero collateral interruption/forbidden effects. `hosted-qa.md`, `timing-results.json`, redacted `evidence/`. |
| S7-12 | S7-11 | Review worst-case/percentile latency, incident escalation, residual risks, operator rehearsal and credential/grant retirement. Update architecture review and stage status with exact release/controller/policy versions and approval references. | Sign-off only for measured scope; any uncovered service, unknown bypass or missed deadline keeps the gate open; `acceptance-review.md`. |

- [ ] S7-01–S7-04: inventory, platform investigation and boundary decisions complete.
- [ ] S7-05–S7-06: reviewed policy, timing targets and controller privilege design frozen.
- [ ] S7-07–S7-10: automatic and manual containment, outage behavior and explicit recovery implemented and locally verified.
- [ ] S7-11: complete hosted adversarial QA and independent effect checks.
- [ ] S7-12: evidence reviewed, remaining limitations explicit and selected-environment acceptance authorized.

## Release acceptance gates

- [ ] Every independently containable agent has an individual Entra Agent ID; A/B token-exchange and authorization isolation are proven even with a shared blueprint.
- [ ] A trusted configured threshold automatically targets the correct identity without agent or human approval; manual emergency disable uses the same durable workflow.
- [ ] Agent cannot modify controller inputs, policy, identities, containment state or recovery authority. Controller privileges are verified and constrained; any unavoidable wider platform authority has an explicit reviewed risk decision.
- [ ] All inventoried resource operations deny the affected agent within the frozen maximum, including previously issued tokens tested from outside its stopped workload, cached sessions, direct MI and any reachable alternative credential. No token-lifetime/CAE assumption substitutes for a test.
- [ ] Active, queued, retried and concurrent work remains fenced across controller/runtime outages and replicas. Pre-fence accepted effects are accounted/reconciled; budgets/reservations and unrelated users remain intact.
- [ ] Disable failure, timeout, throttling, contradictory readback, alert-delivery failure and controller outage persist quarantine and escalate; repeated alerts cannot cause recovery or broaden the target.
- [ ] Every A containment test includes successful B controls before/during/after; shared blueprint, MI and resources are not disabled/rotated as an individual response.
- [ ] Recovery has named human review and explicit incident/generation-bound authorization, isolated canaries and quarantine release last; old sessions/approvals/queues cannot resume.
- [ ] Evidence contains versions, timings, identity/resource IDs, actors, outcomes and effect checks without raw tokens, secrets, private data or unrestricted prompts.
- [ ] Scope, escalation ownership and residual platform limitations are reviewed. Stage 5 outstanding production gates remain separately tracked.

## Planning scope

The initial change created this plan and tasks; local implementation has now begun. Runtime implementation, new identity/controller privileges, resource migration, deployment, disabling a live identity and destructive incident actions require their own reviewed authorized execution. Existing validation remains historical evidence, not Stage 7 proof.
