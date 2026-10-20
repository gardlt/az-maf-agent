# Stage 3 validation — 2026-10-19 CDT

**Scope:** approved Markdown skills in the single-replica dev teaching deployment.
Durable-memory integration case 4 is deferred to Stage 4; production shared controls
remain Stage 5 work. These results do not close those later gates.

[Redacted hosted result metadata](stage-3-hosted-results.json) retains the observed run/digest/control references.

## Local verification

`uv run --locked pytest -q`: **81 passed**. Ruff lint/format and `git diff --check`
passed. `infra/main.rg.bicep` compiled. Tests retain the earlier chat, API, MCP,
TMDB adapter, identity, context, session isolation, and reset regressions.

| Boundary | Evidence and absence of effects |
| --- | --- |
| 1: forbidden write | Requests with and without claimed approval fail before agent dispatch. Direct TMDB dispatcher tests record zero upstream requests for the proposals, only two GETs for before/after checks, with identical records. Hosted actual-identity check below also passes. |
| 2: injection | A complying fake model requests forbidden operations from malicious Markdown or a poisoned synopsis. No unauthorized backend call occurs; failed runs cannot commit history or alter permissions. |
| 3: unapproved loading | Unknown skill, external URL, and escaping ID fail before any file open. Symlinks, unsupported dependencies, private-file/URL/load-skill proposals, and widened capability manifests fail. Only the approved bounded artifact is read. |
| 4: durable memory | Unavailable memory read/write tools deny now. Cross-user durable reads and writes without consent are explicitly deferred to Stage 4's real memory backend. |
| 5: recursion/repetition | Recursive invocation denies with zero backend effects. Repeated reads stop after two attempts in a run, preserving charged session counters. Reset cancels a pending read, prevents history resurrection, and does not reset aggregate reads. |
| 6: integrity/revocation | Tampering, oversized/empty/invalid UTF-8 artifacts, rollback to a revoked version, and control-generation rollback fail closed. A file swap leaves the model consuming the original verified bytes and causes the next load to fail. Revocation during a read, provider retry, or final response blocks subsequent work/commit. Missing/failed/redirected control reads deny. |

## Hosted skills and runtime identity

GitHub deployment [39267507622](https://github.com/gardlt/az-maf-agent/actions/runs/39267507622)
succeeded for `915574a`. Agent revision `ca-maf-agent-dev-eus2-01--0000014` used
`sha256:da15c4805215eb62d6bdcfc168da4990027cb24e9b55c71ecf2150ad601b5672`.
The existing Foundry deployment was `gpt-5`, model version `2025-08-07`.

Both approved skills returned HTTP **200**, exactly **one private MCP read**, and
revision **1**, using a cached approved caller token. The response pinned these artifacts:

| Skill | Version | SHA-256 | Run reference |
| --- | --- | --- | --- |
| movie-research | 1.0.0 | `9b7e6f3f472375cc99fbfe61a570647163310bf424058379074db711d4dbe337` | `b29b2741-628d-4259-a9e8-1521c998d09b` |
| movie-night | 1.0.0 | `b013431d52c55e9fc091001fbc5387f579e0ff8783ff436937c127d171297761` | `36936d4c-c4b8-4091-a51d-290a06526e96` |

For each skill, an unknown skill request returned **409** and a write proposal returned
**403**. From inside the agent container, the actual MCP workload identity successfully
read `tmdb_11`, received an explicit MCP error result for `put_movie` with purported
approval, and read the identical record afterward. The protocol check used
`raise_on_error=False` and asserted `is_error`; transport failures were not counted as
a passing write denial. No token or model text was printed or retained.

An initial hosted request returned `skill_control_unavailable` and stopped before
inference. An in-container control probe verified the workload's Reader access with
HTTP 200; the subsequent two-skill test passed without weakening the fail-closed gate.
The later cold-revision regression identified `ServiceResponseTimeoutError` from a one-second managed-identity read timeout. The timeout was increased to five seconds within the ten-second gate; ARM reads permit one bounded transient retry. Failed probes are recorded as availability failures, not passing requests.

## Disable without redeploy

The operator changed the control record from generation **0** to **1**, disabling
`movie-night@1.0.0`. A new signed-in request returned **409 skill_disabled** in
**1.3 seconds** (client test duration measured after the operator update completed).
The operator restored the skill at generation **2**. The ready revision was unchanged
before and after: `ca-maf-agent-dev-eus2-01--0000014`. No redeploy was used for this
exercise. The record is stored on the existing dev resource group, independently of
app revision replacement. Permanent revocation and restart persistence were verified
with local fixtures to avoid retiring the approved teaching version.

Reproduce normal hosted checks with:

```sh
uv run --locked python scripts/test_skill_container_app.py --api https://ca-maf-agent-dev-eus2-01.kindisland-49d1cad2.eastus2.azurecontainerapps.io
```

Use `scripts/skill_control_azure.py` for the operator steps and add `--skill movie-night
--expect-disabled` to the hosted test while disabled. Always restore a temporarily
disabled approved skill after the exercise. See [the operator guide](../stage-3-skills.md)
for publication, rollback, trust boundaries, and limits.

## Final deployed regression

The final code commit `803a547` passed [CI](https://github.com/gardlt/az-maf-agent/actions/runs/39290604915)
and [dev deployment](https://github.com/gardlt/az-maf-agent/actions/runs/39290605122).
Revision `ca-maf-agent-dev-eus2-01--0000017` is ready with agent digest
`sha256:d0fd8605ea5308763ee915a2713d246bd67fffa70f2516e9dd1474ecc8e937ac`.
The first two-skill probe on this revision passed after the cold-token timeout fix:
both skills returned **200**, one MCP read, revision **1**, their exact approved digest,
and control generation **2**. Each unknown-skill probe returned **409**, and each write
proposal returned **403**. The run references were
`454effd5-09eb-44a7-9989-61355d4128da` (research) and
`1dfda034-4f6b-4327-93f6-4408b3796b4d` (movie-night). Generation 2 survived app revision
replacement, confirming that deployment did not reset the operator's control state.


## Stage 4 case 4 completion — 2026-10-19

The deferred memory boundary is now validated at the actual memory layer: no
other-user disclosure, no skill writes (including claimed consent), and no backend
I/O for denied writes. Reviewed skills cannot receive saved preferences or prior
personalized history. The integrated 126-test suite passes; see
[Stage 4 validation](../../stage-4/validation/stage-4-validation.md) for fixtures and hosted lifecycle evidence.
