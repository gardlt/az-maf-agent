# Stage 5 — containment and operator recovery

Status: implementation and hosted validation in progress. Stage 5 is not complete. The working dev app remains on Stage 4; shared controls and shared sessions are disabled until hosted validation and an explicit recovery of the stopped policy.

## Approved dev contract

The user selected Azure Blob ETag transactions for shared control state. Policy is checked before dispatch, active operations poll every two seconds, the containment target is ten seconds, run leases last thirty seconds, and protected content-free audit is retained for thirty days. Existing token, retry, concurrency, and spend limits remain authoritative. The live acceptance set must have zero forbidden effects and at least 90% benign success.

Short-term sessions use a separate container with a thirty-minute idle timeout and four-hour maximum lifetime. They have no versions or soft-delete backups; live expired documents must be physically removed within twenty-four hours. These sessions are separate from explicitly saved thirty-day preferences.

## Deployed foundation — 2026-10-19

Deployment `stage5-control-bootstrap` succeeded in `rg-maf-dev-eus2-01` against existing account `stmafmemdevmako261019`, after the user explicitly approved the reviewed fifteen-resource deployment and its RBAC/retention changes. The private containers are `guardrail-policy`, `guardrail-state`, `guardrail-audit`, and `agent-sessions`.

The runtime has policy Reader, state/session Contributor, and a custom audit write-only role without container deletion authority. The cleanup identity can clean sessions. The separate operator user has policy/state/audit access. Azure reports audit retention as **30 days, Unlocked**. This protects audit blobs from ordinary overwrite/delete; a privileged operator can modify the unlocked policy. It is not an irreversible lock or protection against every account administrator.

The separate operator command initialized policy epoch **1**, **global_stop=true**, and an empty accounting document. A fresh operator process read the persisted stopped policy successfully. No runtime app was changed by this deployment.

A probe inside the actual Stage 4 agent revision `ca-maf-agent-dev-eus2-01--0000024` verified the new identity boundary: policy GET 200, policy PUT 403, state GET 200, conditional same-content state PUT 201, audit create 201, audit GET 403, audit DELETE 403. The content-free `rbac-probe-*` audit record is an administrative permission test rather than a runtime event envelope and remains protected for the retention period. No preference or conversation content was read by this probe.

Local validation reached **157 passing tests**, with lint passing. Operator publication failure, exact approval binding/cancellation, exported-span redaction, cleanup pagination/concurrent changes, and ambiguous Blob write outcomes have dedicated regression coverage.

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

Telemetry uses an isolated explicit tracer and static resources, without HTTP/model/logging auto-instrumentation. Only enumerated event names, capability/status values, epochs and validated hashed scope/run identifiers are exported. Protected Blob audit is mandatory before dispatch; trace export is supplemental. Local exported-span inspection verifies a secret canary is absent. Actual Azure-exported spans remain to be inspected.

## Remaining release evidence

The task checklist remains unchecked until complete evidence exists: hosted runtime integration, live cross-replica and stop/recovery timing, protected-audit outage behavior, final deployed network cases, independent Azure stop of an isolated unresponsive worker, reconciliation, fresh recovery canary, real exported spans and alert verification, the predeclared benign/adversarial evaluation, supply-chain/secret review, and rollback/incident runbooks. Local fixtures and historical Stage 2 network tests do not satisfy these hosted gates.
