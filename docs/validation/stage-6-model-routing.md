# Stage 6 dev acceptance — 2026-10-20

Stage 6 is complete for the selected dev teaching scope. Outstanding Stage 5 production release gates remain open.

## Release and behavior

[CI](https://github.com/gardlt/az-maf-agent/actions/runs/39388288318) and [dev deployment](https://github.com/gardlt/az-maf-agent/actions/runs/39388288350) passed for source `681e8407a4097a243156d3d184d14cf7f67e37d4`. Local verification: **215 tests passed**, Ruff lint/format passed for `apps scripts`, Bicep compiled and the model what-if showed only one deployment create, with existing resources ignored. Both shipped images have **zero High/Critical findings**; 14 Medium, 1 Low and 1 Negligible remain per image. Full SBOM/scan artifacts are retained by the workflow. See [image scan summary](stage-6-image-scans.json) and [actual ready revisions/image digests](stage-6-release.json).

The approved `gpt-5-mini` version `2025-08-07` deployment is GlobalStandard, capacity 30, in the existing Foundry account. The existing GPT-5 deployment remains unchanged. No runtime role, Entra identity, daily budget, registry tier or network topology was broadened. See [deployment configuration](stage-6-model-deployment.json).

The first attempted app rollout was cancelled before app cutover when review found that the protected Blob audit allowlist rejected route metadata. The fix adds only a bounded routine/reasoning/null field and regression tests; the corrected release above passed. The working revision remained unchanged during that cancellation.

## Frozen comparison

The same 20-case dataset, grader v3 and predeclared 90% benign floor were used without changing prompts or thresholds. [Baseline](stage-6-baseline.md) and [routed evaluation](stage-6-routed.md) retain dataset/grader hashes and per-case metadata. Each batch contains 10 benign and 10 adversarial requests. Both batches returned HTTP 200 for every case; this means the adversarial requests received answers, not that forbidden actions were executed.

| Measurement | GPT-5 baseline | Routed routine batch |
| --- | --- | --- |
| Benign marker checks | 10/10 | 10/10 |
| Total batch model calls | 34 | 35 |
| Total batch permitted tool reads | 14 | 15 |
| Median benign request latency | 3.7395 s | 5.146 s |
| Estimated benign inference cost | $0.02214625 | $0.00496000 |

Observed-token list-price estimates show **77.6% lower routine inference cost**. Median latency increased by about 37.6%; mini was cheaper, not faster in this batch. Six-second inter-case pacing respected the approved mini quota and is excluded from request latency. The baseline was not paced. This serial sample is not a throughput benchmark or statistically general model comparison. Cache discounts, negotiated rates, infrastructure charges and invoices are excluded. Published rates and their verification limitations are documented in the [routing guide](../stage-6-model-routing.md).

## Actual routes and context

The [Azure-ingested trace verification](stage-6-traces.json) covers all 43 runs: 20 baseline, 20 routed and 3 history probes. All model calls correlate to their agent root. The routed release reports **38 actual `gpt-5-mini-2025-08-07` calls and 1 actual `gpt-5-2025-08-07` call**. The baseline predates provider-model-field instrumentation and records its pinned GPT-5 deployment with observed usage. All agent roots use the existing Entra Agent ID. No content-capture attributes were present.

The same owned conversation changed **routine → reasoning → routine**. All three replies correctly retained Star Wars (1977); only the first needed a catalog read. Manual qualitative review found that the stronger route supplied a coherent short film analysis, and the final mini reply retained the requested title/year without another lookup. This is bounded qualitative/history evidence, not a full factuality assessment of every answer. Raw response contents are not saved in these reports. See [probe metadata](stage-6-route-probes.json).

## Enforcement and state

The [protected security verification](stage-6-security.json) validates **490 audit envelopes**, including **328 new dispatch checks**, of which **230** belong to the 23 routed/probe runs. There are **zero forbidden dispatches**. All 39 tested model reservations carry an approved route: 38 routine, 1 reasoning. Every tested run is reconciled. Epoch remains 6 and global stop remains false.

Direct create/update attempts returned **403 `tool_not_allowed`**; a write method hidden in read arguments returned **422 `invalid_tool_arguments`** before and after evaluation. Stable title/year/synopsis hashes for TMDB 11 and 603, the isolated simulator receipt digest and per-case saved preference snapshots remained unchanged. Test conversations were reset. Aggregate reservations were retained: **$0.21460975** across the 23 routed/probe runs; this conservative amount is not observed usage or an invoice.

Local regressions also cover both routes' forbidden-tool enforcement, unavailable/invalid pricing and routes, shared mixed-model atomic budgets, cancellation/history fences, concurrent route isolation, text-only routing, protected Blob metadata validation and single-model compatibility.

This uses one authorized caller and finite fixtures with sampled catalog state. It does not prove distinct-user hosted isolation, cross-replica races, final network egress enforcement or universal prompt-injection resistance. Those existing Stage 5 gates remain open. Routing is a bounded deterministic policy; no automatic alternate-model fallback is enabled. Production promotion needs environment-specific compatibility/pricing review and the remaining production release gates.

## Reproduce

```sh
uv run --locked pytest -q
uv run --locked ruff check apps scripts
uv run --locked ruff format --check apps scripts
# Before evaluating the routed deployment, retain a metadata checkpoint locally:
uv run --locked python scripts/verify_stage6_security.py --phase snapshot --checkpoint /tmp/stage6-checkpoint.json
uv run --locked python scripts/test_stage5_container_app.py --phase evaluate --pause-seconds 6 --report docs/validation/stage-6-routed.md
uv run --locked python scripts/test_stage6_routes.py --report docs/validation/stage-6-route-probes.json
uv run --locked python scripts/verify_stage6_security.py --phase verify --checkpoint /tmp/stage6-checkpoint.json
uv run --locked python scripts/verify_stage6_traces.py --workspace 244ef22a-576b-4e7d-a41e-d64884fb7def --baseline docs/validation/stage-6-baseline.json --routed docs/validation/stage-6-routed.json --probes docs/validation/stage-6-route-probes.json --report docs/validation/stage-6-traces.json
```

Use the matching baseline release or an explicitly deployed reasoning-only configuration to obtain a fresh baseline. Baseline run IDs in this record refer to this acceptance window; the trace verifier queries the last day. Allow Azure ingestion to complete before checking new traces. Use cached caller login and the separate operator identity for audit reads; runtime cannot read protected audit. Keep checkpoints outside Git. Never reset quotas or weaken scan/quality gates to obtain a pass. See the [routing guide](../stage-6-model-routing.md) for configuration and schema-compatible rollback.
