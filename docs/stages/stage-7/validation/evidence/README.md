# Stage 7 retained evidence

These artifacts record local fixtures and one explicitly approved live dev identity drill on 2026-10-20. They do not prove an independently deployed controller or all-resource containment. [Results and limitations](../live-disable-drill-2026-10-20.md) · [QA matrix](../README.md) · [Architecture](../../../../architecture-review/14-agent-containment.md).

| Artifact | Observation and scope |
| --- | --- |
| [Initial containment JUnit](local-containment-initial.junit.xml) | 18 local containment cases; before the live response-projection correction. |
| [Initial full JUnit](local-regression-initial.junit.xml) | 233 passing local tests at the start of this test request. |
| [Final full JUnit](local-regression-final.junit.xml) | 235 passing tests, including 20 containment cases after actual Graph-shape regressions were added. |
| [Local test summary](local-test-summary.json) | Actual counts/time, commands, code hashes, original JUnit hashes and normalization disclosure. |
| [Graph preflight observations](graph-projection-preflight.json) | Read-only selected response fields exposed the real default-projection mismatch before disable. |
| [Live drill observations](../live-disable-drill-2026-10-20.json) | Baseline, disabled/repeated and restored token/service outcomes; negative resource-containment findings. |
| [Restoration receipt](restore-receipt.json) | Exact metadata-only HTTP statuses, enabled readback and observation time from explicit restoration. |
| [Chat recovery result](chat-recovery-canary.json) | Existing shared_daily_budget 429; not a passed recovery chat. |
| [Final in-container probe source](container-probe-source.txt) | Final source used for disabled-final/restored probes; earlier probes omitted the optional selected-claims diagnostics. No tokens are embedded. |
| [Artifact manifest](artifact-manifest.json) | SHA-256 and size for retained artifacts/reports, excluding the manifest itself. |

JUnit XML was copied from actual test-run output with only the local hostname removed. The original capture hashes are retained in the summary. Live JSON contains selected observations from the executed commands; it is not a complete signed Graph/Azure transcript. No raw token, private credential, preference record, provider body or unrestricted prompt is retained. Token cache deletion was observed inside the dev container; it does not revoke already issued tokens.

Hashes detect later byte changes relative to this manifest; they are not a trusted timestamp, externally signed provenance or protection from a privileged repository administrator. Preserve earlier artifacts when adding new captures, and record the current source/deployment/policy versions for each new run.
