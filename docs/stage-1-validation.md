# Stage 1 validation and limits

This records local and test-hosted implementation evidence, not completion of every hosted milestone in [the task](tasks/stage-1-chat.md). No live model invocation was performed; no model/deployment was chosen.

## Recorded results

On 2026-10-15, Python 3.12.12 with Agent Framework core 1.22.0 passed 27 tests. Ruff lint/format, Python compilation, and wheel/source builds passed; the interactive CLI smoke test produced the expected 1/2/1 context counts. The final dependency audit reported no known vulnerabilities (the local editable project is not in the advisory database). Source/configuration review found no embedded credentials or executable model-output path. This is a review and dependency scan, not a comprehensive secret-scanner certification.

On 2026-10-16, an approved test foundation was deployed in `rg-az-maf-stage1` in East US 2: a Container Apps environment, Basic private registry, image-pull identity with `AcrPull`, and a 30-day Log Analytics workspace. On 2026-10-17 the pinned Linux/amd64 image was pushed to the private registry at digest `sha256:9aee3d497a5a46dd5169c698d0d92b8a2be7e35e1ab588ab21040645f14dfdfa`. The external Docker Scout scan was skipped at the user's direction.

The Container App was then deployed with one replica, digest-pinned image pull, Entra Easy Auth, exact API audience, allowed CLI client, and HTTPS required. It was verified ready with no restarts. Public ingress was enabled only after that authentication readback. The public URL returned 401 for missing bearer tokens, invalid bearer tokens, and forged identity headers; plain HTTP returned 301. A signed-in positive flow and authenticated forbidden-user check remain pending.

On 2026-10-17, signed-in testing initially returned 403 because the API registration's access-token version was unset, causing Entra to issue a v1 token. The registration was corrected to `requestedAccessTokenVersion: 2`. The corresponding v2 access token uses the API application ID as its audience, so Easy Auth and the application must be configured with that exact value; acquire a fresh token before rerunning the acceptance script.

## Local checks

Run from the repository root:

```sh
uv sync --locked
uv run --locked pytest -q
uv run --locked ruff check src tests
uv run --locked ruff format --check src tests
printf 'hello\nagain\n/reset\nhello\n/quit\n' | uv run --locked agent-chat
uv run --locked pip-audit --local
```

Tests use the real pinned Agent Framework core/history provider, deterministic injected transports, an injectable clock, mock HTTP transport for the model adapter, and generated RSA signing keys for API-token validation. They require no Azure credentials or model service. The fake returns message counts and never echoes input.

Coverage includes isolation/replay, reset/cancel races, idle/lifetime expiry, restart session loss, bounded history and untrusted instruction-like output, input/context/output/run-token/turn/spend caps, concurrent user admission, bounded retries, call/run timeouts, metadata-only audit and audit failure, strict configuration, forged identity headers, signed wrong-audience/issuer/tenant/expired tokens, permission denials, rejected body identities, request-size limits, malformed/oversized/provider tool output, and disabled redirect following.

The CLI smoke exercise returns context counts 1, 2, then 1 after reset. Expected audit lines contain event/run/policy/counter metadata only. Source review confirms there is no subprocess, shell, tool dispatcher, tool registry, filesystem tool, or model-driven client selection.

## Supply-chain evidence

`uv.lock` pins the complete dependency graph and artifact hashes. Install with `--locked`. A local vulnerability audit found issues in an initial cryptography compatibility pin; the implementation upgraded to 50.0.2 and re-runs the audit. The local editable project is not itself covered by the public package database. Generate a CycloneDX report with `pip-audit --local --format cyclonedx-json --output PATH` when collecting release evidence; keep reports outside prompt/content logs. No claim is made that a clean dependency scan proves source or runtime security.

## Acceptance still requiring environment decisions/evidence

- Select/evaluate an approved live model, endpoint/API version, prices and context/token-bound compatibility. Test managed identity RBAC and actual provider billing categories.
- Complete signed-in hosted tests through the CLI and API: allowed multi-turn/reset, expired or wrong-audience token rejection, authenticated 403 for a disallowed user, replay denial, and restart behavior. The negative 401 probes and ingress readback are recorded above, but do not complete this gate.
- Choose shared session and authoritative daily-ledger/control storage before replicas, cross-process resumption, or production use. RAM restart loses usage counters and sessions; no sticky-routing correctness claim is made.
- Validate actual platform/SDK telemetry redaction, pinned non-root image build/provenance, workload identity/secret handling, network dependencies and later-stage containment controls.
- Summary generation is not implemented; complete-pair trimming avoids generating a new source of asserted authority. Tests treat instruction-like recalled/output text as inert, not as permissions.

Limits remain material: cooperative asyncio cancellation is not worker termination; downstream requests can continue charging. No raw credentials are put into context, but the application is not a universal secret detector for user text. The UTF-8 token bound and conservative cost reservations trade utilization for a simple teaching control, and require selected-model validation before live acceptance.
