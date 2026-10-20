# Stage 5 — containment and operator recovery

Status: implementation and hosted validation in progress. Stage 5 is not complete. The dev app now runs shared controls and Blob sessions. The latest verified dev policy is epoch 6 with global stop disabled after a scanned, schema-compatible release and explicit recovery/canary. Production release gates remain open.

## Approved dev contract

The user selected Azure Blob ETag transactions for shared control state. Policy is checked before dispatch, active operations poll every two seconds, the containment target is ten seconds, run leases last thirty seconds, and protected content-free audit is retained for thirty days. Existing token, retry, concurrency, and spend limits remain authoritative. The live acceptance set must have zero forbidden effects and at least 90% benign success.

Short-term sessions use a separate container with a thirty-minute idle timeout and four-hour maximum lifetime. They have no versions or soft-delete backups; live expired documents must be physically removed within twenty-four hours. These sessions are separate from explicitly saved thirty-day preferences.

## Deployed foundation — 2026-10-19

Deployment `stage5-control-bootstrap` succeeded in `rg-maf-dev-eus2-01` against existing account `stmafmemdevmako261019`, after the user explicitly approved the reviewed fifteen-resource deployment and its RBAC/retention changes. The private containers are `guardrail-policy`, `guardrail-state`, `guardrail-audit`, and `agent-sessions`.

The runtime has policy Reader, state/session Contributor, and a custom audit write-only role without container deletion authority. The cleanup identity can clean sessions. The separate operator user has policy/state/audit access. Azure reports audit retention as **30 days, Unlocked**. This protects audit blobs from ordinary overwrite/delete; a privileged operator can modify the unlocked policy. It is not an irreversible lock or protection against every account administrator.

The separate operator command initialized policy epoch **1**, **global_stop=true**, and an empty accounting document. A fresh operator process read the persisted stopped policy successfully. No runtime app was changed by this deployment. The separately reviewed `stage5-monitoring-bootstrap` subsequently succeeded, creating `appi-ca-maf-agent-dev-eus2-01` with local authentication disabled and the scoped runtime Monitoring Metrics Publisher role.

A probe inside the actual Stage 4 agent revision `ca-maf-agent-dev-eus2-01--0000024` verified the new identity boundary: policy GET 200, policy PUT 403, state GET 200, conditional same-content state PUT 201, audit create 201, audit GET 403, audit DELETE 403. The content-free `rbac-probe-*` audit record is an administrative permission test rather than a runtime event envelope and remains protected for the retention period. No preference or conversation content was read by this probe.

Local validation reached **190 passing tests**, with lint passing. Operator publication failure, exact approval binding/cancellation, exported-span redaction, cleanup pagination/concurrent changes, and ambiguous Blob write outcomes have dedicated regression coverage.

## Operator commands

Use an independently authorized Azure CLI user session. The operator module explicitly uses `AzureCliCredential`; the runtime API does not import it or expose policy-writing endpoints.

```sh
uv run --locked python -m az_maf_agent.control_operator --account stmafmemdevmako261019 status
uv run --locked python -m az_maf_agent.control_operator --account stmafmemdevmako261019 stop --expected-epoch 1
uv run --locked python -m az_maf_agent.control_operator --account stmafmemdevmako261019 disable --expected-epoch 2 model
```

Always fetch the current epoch; example epochs are illustrative. `recover --expected-epoch N` is an explicit operator operation and preserves the disabled-component set. Do not recover before deployment checks and containment reconciliation are complete. `enable --expected-epoch N CAPABILITY` enables only that component. A runtime identity must fail policy writes.

Policy and accounting are separate blobs, not one multi-blob transaction. Publication first advances the accounting policy floor, then conditionally writes the policy ETag. A partial publication blocks dispatch. Repeating the explicitly chosen operation against the observed policy epoch can publish a newer epoch; it never lowers the floor. Bootstrap only accepts two absent objects. Do not delete or recreate established accounting to repair an outage: doing so would erase reservations and unknown outcomes.

For the isolated classroom-credit fixture, an operator can issue `approve --run-id UUID --units N` or `reject` with the same arguments. This applies only to `simulation:credit` for `classroom`, with one to ten units. The approval binds owner scope, run, current epoch and exact argument digest; expiry is at most sixty seconds and never exceeds the run lease/deadline. The receipt and approval consumption commit together. It grants no movie-catalog write permission and performs no external transfer.

## Local implementation

Shared reservations retain conservative cost and token commitments across retries, failures, resets and replicas. Unknown pricing denies dispatch. Unknown provider outcomes retain concurrency occupancy; cancellation does not imply provider invoice cancellation. Observed late usage can reconcile accounting without committing late conversation history.

Session documents use ETag updates and trusted tenant/user scope hashes. Revision/run fences reject stale or concurrent commits. Reset clears history while preserving aggregate counters; a newer policy epoch prevents old conversation history from being revived after recovery. Cleanup uses a durable bounded paging cursor and conditional deletion, so a concurrent update is not deleted and later pages are not indefinitely skipped.

Telemetry uses an isolated explicit tracer and static resources, without HTTP/model/logging auto-instrumentation. Only enumerated event names, capability/status values, epochs and validated hashed scope/run identifiers are exported. Protected Blob audit is mandatory before dispatch; trace export is supplemental. Local exported-span inspection verifies a secret canary is absent. Actual shipped Azure-exported spans were inspected; see [exported-span evidence](validation/stage-5-evidence/shipped-exported-span.json).

## Remaining release evidence

The [task checklist](tasks/stage-5-production-guardrails.md) now separates completed, evidence-backed milestones from open release gates. Remaining work includes actual cross-replica conversation/race acceptance, remaining hosted control/approval/outage cases, final network topology and bypass tests, full forbidden-effect review, Key Vault rotation and rollback rehearsal. The latest dev release completed vulnerability clearance, maintenance recovery/canary, Entra Agent ID integration and GenAI tracing; the user subsequently confirmed Agents (Preview) visibility. Completed synthetic containment and exported-span checks do not substitute for these outstanding gates.


## Deployment checkpoint

Commit `eee02a8` was pushed to `main`. CI, infrastructure checks, and the dev deployment passed. The resulting ready revision was `ca-maf-agent-dev-eus2-01--0000025`, image digest `sha256:8328ed26a40064381ddd47022aaaa1be061c45c47962ffd509eb5a61575f18ed`. Stage 5 remained disabled. Hosted exporter probes identified an empty-setting parse problem and the SDK's `timeout` keyword requirement; fixes and a real exporter-construction regression are included in the follow-up. A flush acknowledgement alone is not evidence of ingestion or redaction; the actual Azure span query was pending at this checkpoint and is recorded as completed under Hosted evidence collected.

The fixed evaluation inputs and approved thresholds are in `config/stage5-evaluation.json`. Commit the dataset before live evaluation; do not change thresholds to accommodate results.


## Hosted evidence collected

The actual runtime's Azure deactivate attempt against the isolated fixture returned **403**. The independent Azure CLI operator then deactivated both fixture revisions. A corrected inventory explicitly included inactive revisions (`--all`): both `drill-a` and `drill-b` were observed `active=false`, `runningState=Stopped`, `replicas=0` in **2.299 seconds**. Each initially had one running replica. Persisted global stop remained enabled at epoch 1. This is a synthetic no-effect worker drill, not a claim that provider requests or billing are undone. See [manual stop evidence](validation/stage-5-evidence/manual-stop.json).

Azure ingestion of a metadata-only `control.dispatch_authorized` span was verified in `AppDependencies`, not inferred from flush. The synthetic sensitive field was absent from exported properties. See [exported span evidence](validation/stage-5-evidence/exported-span.json). The initial candidate probe applied the timeout correction in its process; subsequent runtime release validation still checks the shipped path.

Commit `547c88f` passed CI, infrastructure checks, and dev deployment. Ready revision `ca-maf-agent-dev-eus2-01--0000026` enables shared controls and sessions while the persistent policy remains globally stopped for negative tests.


## Current validation and quality work

Stopped ingress returned unauthenticated 401 and authorized 503/global_stop, including after a real revision restart. The independent operator recovered epoch 1 to epoch 2 without resetting quotas or enabling any disabled capability. Two actual running dev replicas were observed for shared-session validation. The protected audit envelope hash check passed, and an operator same-content overwrite was rejected with 409 under retention.

A genuine previously issued access token, expired beyond five-minute skew, was rejected by deployed ingress with 401. The private temporary token was then deleted. No token is included in the evidence.

The first fixed evaluation reported 60% with a title-only grader; four diagnostics confirmed valid year/ID-only answers requested by those prompts. Grader v2 scored 80%; it still incorrectly required the title for the second ID-only prompt and one benign request returned provider_shape. Both failed reports are retained. Grader v3 covers both requested IDs and the requested years, with the same dataset and 90% threshold. Do not count either earlier run as passing.

A bounded operator compatibility canary verified that the existing GPT-5 deployment/API accepts minimal reasoning effort (19 observed tokens). The app configuration now requests that effort within the same 2,000-token output and existing spend limits, following [Azure's reasoning guidance](https://learn.microsoft.com/azure/foundry/openai/how-to/reasoning). The subsequent fresh deployed run reached 90% with grader v3, as recorded below; the threshold was not relaxed.

The user requested and approved the separately reviewed 11-resource phase-one VNet/Basic Firewall foundation. The first `stage5-network-foundation` attempt failed on the NSG DNS rule; the repaired `stage5-network-foundation-retry` succeeded. Registry upgrade and app migration are excluded from that approval. See [migration and cost review](stage-5-network-migration-review.md). Existing dev app traffic remains in the original environment until the later reviewed cutover.


## Current release blockers and maintenance evidence

The user selected **block unresolved High and Critical vulnerabilities**. The pre-remediation agent digest `sha256:4e5502849017de2763d9774d1f05fdb9a59ed514b11f5b406576e7db09eb89d0` has 20 Critical and 202 High matches in the local Grype scan. It fails release. The image SBOM and [scan evidence](validation/stage-5-evidence/image-vulnerability-scan.json) are retained; image layers were not uploaded to a scanning service. Docker Scout remains skipped. A patched base and final rebuilt-image rescan are required; updating a Dockerfile alone does not satisfy the gate.

Two unknown provider outcomes were independently reconciled only after every known dev agent revision was verified inactive, stopped and at zero replicas. The operator classification preserves all reserved tokens/cost and observed receipts, and explicitly retains unknown provider usage. See [reconciliation evidence](validation/stage-5-evidence/reconciliation.json). At that checkpoint the revision was reactivated while policy remained stopped at epoch 5; subsequent recovery to epoch 6 is recorded below. No invoice cancellation or zero-usage claim is made.

The now-deployed provider-rejection change records confirmed terminal HTTP rejections separately from unknown transport outcomes. Null usage receipts require shared-state schema 2; no zero usage is fabricated and reservations remain intact. Keep global stop through rollout. After any schema-2 write, rollback must use code that validates schema 2. A schema-1-only image is not a compatible rollback target.

The fixed live benign evaluation achieved 90% under the frozen grader; [results](validation/stage-5-live-evaluation.md) describe its limits. Shared-backend synthetic watchdog containment measured 3.255 seconds. Actual multi-replica conversation/reset validation and the final network topology remain open. Phase-one network foundation succeeded, but the user declined Premium ACR; app cutover requires another reviewed image-delivery design.


Both Dockerfiles now pin the verified official Python 3.12.15 slim Trixie index digest. A local base-only comparison found zero Critical and 55 High matches for that candidate, versus three Critical and 79 High for the Bookworm candidate. These are base-image results, not a final application-image clearance. See [comparison evidence](validation/stage-5-evidence/python-base-scan-comparison.json). No unresolved findings are suppressed because their vendor status is `wont-fix` or `not-fixed`.

The deployment workflow now scans each built image locally with checksum-pinned Syft 1.55.0 and Grype 0.121.0 before pushing it. `--fail-on high` blocks unresolved High/Critical findings, including findings without fixes; scanner/database failures also block rollout. SBOM and vulnerability reports are retained as workflow artifacts for 30 days. A passing application test suite does not bypass this gate.


## Microsoft Entra Agent ID requirement

The user requires Microsoft Entra Agent ID for this agent. Current managed identities are not evidence of an Agent ID integration. [The integration plan](entra-agent-id.md) records environment isolation, federation, directory provisioning, runtime token use and validation. Dev provisioning and downstream runtime use are now verified in the latest checkpoint below; stage/prod rollout and the broader identity review remain separate.


## Azure Monitor Agents view requirement

The user also requires [Application Insights Agents (Preview)](https://learn.microsoft.com/en-us/azure/azure-monitor/app/agents-view). The [integration plan](azure-monitor-agents-view.md) covers correlated agent/model/tool traces, observed usage, metadata-only export and hosted portal acceptance. Existing isolated control spans do not satisfy this requirement. Instrumentation and actual Azure ingestion are now verified in the latest checkpoint below; the user has confirmed agent visibility in Agents (Preview).


## Latest Agent ID / tracing checkpoint

Release `e038ca3` deployed successfully to dev after both images passed the unresolved High/Critical gate. The agent is revision 30 and movie MCP revision 28. Explicit recovery advanced policy 5 → 6 without changing existing run records or daily reservations. A fresh authenticated canary completed two model calls and one MCP read with no unresolved outcome.

Dev Entra Agent ID is provisioned and used by both downstream credential paths. Actual deployed tokens identify the agent and are cached; [selected claims](validation/stage-5-evidence/agent-id-runtime-token-claims.json) contain no raw tokens. Four actual Azure-ingested spans correlate agent invocation, model calls and MCP read, with observed usage and no sensitive canary/content attributes. The user confirmed the agent is visible in Agents (Preview). Correlation is established separately by the Azure-ingested trace; no automated browser inspection is claimed. See the [acceptance report](validation/stage-5-agent-id-observability.md). This checkpoint supersedes the earlier epoch-5 stop and old-image scan blockers; historical evidence is retained. Other Stage 5 gates remain open.
