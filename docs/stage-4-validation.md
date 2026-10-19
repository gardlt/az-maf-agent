# Stage 4 validation — 2026-10-19

Release scope: the selected single-process dev teaching deployment, explicit-consent
movie genre/language preferences, one Blob document per authenticated user/purpose,
and 30-day expiry. Vector/graph/embedding stores and backup restore are not enabled.

## Local enforcement evidence

`uv run --locked pytest -q`: **126 passed**. Ruff check and format checks pass.
Both infrastructure entry points and memory modules compile. Dev resource-group and
standalone memory parameter files compile with synthetic values. Infrastructure CI
now validates those parameter files and both entry points.

| Boundary | Evidence |
| --- | --- |
| Authenticated scope | Owned-session API fixtures reject extra/forged identity; storage fixtures isolate users/tenants while allowing approved same-user sessions. |
| Consent and minimization | No-consent writes deny before I/O. Unauthorized values/backends deny before mutation; corrupted documents are not disclosed to the model. No free-text memory or automatic transcript promotion. |
| Concurrency and deletion | Exact ETags, generation/revision checks, conditional creation, concurrent correction/delete, no retry after ambiguous PUT, and empty fencing documents prevent stale recreation. |
| Expiry | Read-time exclusion, persistence of expiry removal, expiry during a delayed remote read, and generation-based personalized-history invalidation pass. |
| Skill case 4 | Actual memory-layer tests deny skill writes before network effects and disclose no other user's records. Reviewed skills receive neither durable records nor earlier personalized history. Model-requested memory tools remain forbidden. |
| Cancellation and bounds | Canceled requests retain bounded worker slots until I/O settles; explicit cancellation fences pre-dispatch writes. Cleanup page/time bounds, malformed listings, oversized documents, and ETag conflicts fail closed. |
| Existing stages | Session/reset/expiry, summary poisoning, model context/spend/tool bounds, skill integrity/revocation, and MCP read-only tests remain in the full suite. |

Relevant fixtures: `test_memory.py`, `test_blob_memory.py`, `test_memory_config.py`,
`test_memory_runtime.py`, and authenticated memory lifecycle cases in `test_api.py`.
Tests inspect actual fixture storage effects, not model refusals.

## Hosted dev evidence

- Missing token: **401**. Spoofed identity header: **401**. Valid token with a
  management-service audience: **401**.
- Signed-in approved caller: **200**. Missing explicit consent: **403**.
  Caller-supplied identity field: **422** before persistence.
- A consented fixed teaching preference survived an explicit replica restart and
  subsequent deployment replacement; a fresh owned session inspected it successfully.
- Correction and a model recommendation using the corrected preference returned
  **200**. The API returned only recall count/generation as diagnostic metadata;
  raw model answers and preference records are not retained in this report.
- Final stable-rollout lifecycle exercise: **passed** on revision
  `ca-maf-agent-dev-eus2-01--0000024` after an explicit restart. Cross-session
  inspection, correction, model recall, reset, per-record deletion, forget-all, and
  chat after deletion returned **200**. Stale recreation returned **409**. Final
  generation: **7**; test preferences remaining: **0**.

The first combined lifecycle probe overlapped a deployment: persistence, correction,
and chat succeeded, then reset returned 404 after process-local session replacement.
This is the documented short-term session boundary, not loss of durable memory. The
subsequent stable-rollout probe passed independently before closing Stage 4.

## Physical expiry cleanup and operations

Operator validation seeded an isolated synthetic pre-expired record through the same
managed-identity Blob adapter; it did not change the approved 30-day policy. Job
`job-maf-memory-dev-eus2-01-jtibvd7` ran from **18:31:42 to 18:32:17 UTC**, succeeded,
and emitted counts: **2 documents examined, 1 expired record removed**. A separate
raw-document read confirmed an empty record list and the retained generation fence.
This validates cleanup of an already-expired fixture, not a 30-day wall-clock wait.
A second execution on the final image, `job-maf-memory-dev-eus2-01-de08dtn`, also
succeeded from **18:42:44 to 18:43:17 UTC** after the test preferences were removed.

The hourly schedule is `17 * * * *`, with a dedicated system identity, 600-second
replica timeout and one platform retry. The portal alert
`al-maf-memory-cleanup-dev-eus2-01` is enabled and evaluates hourly for no completion
in 20 hours. Cleanup console metadata reached the configured workspace. Its health
query returns no alert rows after successful cleanup. No notification recipients are
configured; operators must watch Azure alerts and maintain the 24-hour cleanup target.

Azure resource settings were read back: encryption enabled, HTTPS only, TLS 1.2,
Shared Key disabled, anonymous Blob access disabled, versioning disabled, blob soft
delete disabled, and container soft delete disabled. Agent and cleanup system
identities have Blob Data Contributor at the preference-container scope. Ordinary CI
does not assign roles. No additional storage secret is required.

## Inventory and release limits

- Storage: `stmafmemdevmako261019`, container `preferences`.
- Policy: `stage-4-movie-preferences-v1`; eight operations/session, with owner deletion
  exempt from exhaustion and two operations reserved per recalled run.
- Runtime commit: `c02d72ef7d081d3f1244a1613a53365799ef8a90`.
- Agent and cleanup image digest:
  `sha256:dbf44f40453e8aa6e3f7a008de35507c0d654fb40298f806b8c6ee4e35e9b8a8`.
- Ready revision: `ca-maf-agent-dev-eus2-01--0000024`.
- [Runtime CI](https://github.com/gardlt/az-maf-agent/actions/runs/39303915217): success.
- [Final runtime deployment](https://github.com/gardlt/az-maf-agent/actions/runs/39303915225): success.
- [Infrastructure validation](https://github.com/gardlt/az-maf-agent/actions/runs/39303276107): success.
- Repeat with `scripts/test_memory_container_app.py --api <dev-origin>`; use
  `--phase save`, restart the replica, then `--phase verify` to repeat persistence.
  The script refuses to replace existing preferences. It uses the encrypted auth
  cache and redacts identifiers, tokens, records, and model responses from output.
- Redacted machine-readable results: [stage-4-hosted-results.json](evidence/stage-4-hosted-results.json).

Stage 4 does not close Stage 1's shared/resumable-session or deployed expired-token
acceptance gaps. Short-term sessions remain process-local; multi-replica session,
distributed budget/control state, hardened durable audit, and production emergency
controls remain separate work. A dispatched storage write cannot always be undone;
inspect to reconcile ambiguous outcomes. Old backup restore is unsupported and must
not be enabled without deletion fencing. Cleanup has bounded scan/time capacity and
requires healthy platform scheduling plus operator response to overdue alerts.
