# Stage 1 validation and limits

This records local implementation evidence, not completion of every hosted milestone in [the task](tasks/stage-1-chat.md). No Azure deployment or live model invocation was performed; no model/deployment was chosen. Application changes are intentionally uncommitted for review.

## Recorded results

On 2026-10-15, Python 3.12.12 with Agent Framework core 1.22.0 passed 27 tests. Ruff lint/format, Python compilation, and wheel/source builds passed; the interactive CLI smoke test produced the expected 1/2/1 context counts. The final dependency audit reported no known vulnerabilities (the local editable project is not in the advisory database). Source/configuration review found no embedded credentials or executable model-output path. This is a review and dependency scan, not a comprehensive secret-scanner certification.

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
- Deploy the API behind real Container Apps HTTPS/Easy Auth, verify JWT/token-flow configuration and 401/403 behavior, and prove no alternative ingress.
- Choose shared session and authoritative daily-ledger/control storage before replicas, cross-process resumption, or production use. RAM restart loses usage counters and sessions; no sticky-routing correctness claim is made.
- Validate actual platform/SDK telemetry redaction, pinned non-root image build/provenance, workload identity/secret handling, network dependencies and later-stage containment controls.
- Summary generation is not implemented; complete-pair trimming avoids generating a new source of asserted authority. Tests treat instruction-like recalled/output text as inert, not as permissions.

Limits remain material: cooperative asyncio cancellation is not worker termination; downstream requests can continue charging. No raw credentials are put into context, but the application is not a universal secret detector for user text. The UTF-8 token bound and conservative cost reservations trade utilization for a simple teaching control, and require selected-model validation before live acceptance.
