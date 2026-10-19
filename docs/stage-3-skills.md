# Stage 3 implementation checkpoint

The user selected both movie research and movie-night planning. Reviewed Markdown
bundles are in `skills/`; `approved.json` pins SHA-256 digests, metadata, and tools.
The trust mechanism is a repository-reviewed approval index, not artifact signatures.
Only operator configuration chooses the index; users and models cannot supply it.
Composition is disabled. Dependencies are unsupported and rejected as unknown metadata.

## Run and configure

The agent image includes `/app/skills`. Enable only on a server already configured
for live model tools and the private MCP. Supply these operator settings:

- `SKILL_BUNDLE=/app/skills`
- `SKILL_CONTROL=/operator-readonly-mount/skill-control.json`
- `SKILL_ALLOWED_USERS=<approved Entra user object IDs, comma separated>`

The control file must exist. Initialize it as an operator with:

```json
{"generation": 0, "disabled": [], "revoked": []}
```

Mount the operator-owned control directory read-only to the application. Operators
need write permission and the directory must support atomic file replacement. The
application identity must not be able to replace either approval or control files.
No new control-file mount or hosted enablement has been deployed in this checkpoint.

After server configuration, callers select one exact approved version:

```sh
uv run --locked agent-chat --api https://YOUR-APP.azurecontainerapps.io --skill movie-research
uv run --locked agent-chat --api https://YOUR-APP.azurecontainerapps.io --skill movie-night
```

The API accepts optional `skill_id` and `skill_version` on chat. Without configured
skills it denies these requests. Skill IDs never select local files or remote URLs.

## Review, publication, rollback, and containment

Review Markdown and metadata together, calculate the digest from the exact UTF-8
bytes, and review the `approved.json` change before publishing a new version.
Keep previously approved versions for rollback. A version cannot change digest.
The loader rejects metadata granting tools beyond the two movie reads.

Under a separate operator OS identity, validate the reviewed bundle:

```sh
uv run --locked python -m az_maf_agent.skill_operator validate --bundle skills --control /operator/skill-control.json
```

Disable an existing version without restarting the server:

```sh
uv run --locked python -m az_maf_agent.skill_operator disable --bundle skills --control /operator/skill-control.json --skill movie-night --version 1.0.0
```

Use `enable` to reverse a temporary disable, or `revoke` to permanently reject a
version. The tool serializes concurrent local operators and atomically replaces state.
Revoked versions cannot be enabled. Rollback means selecting an older reviewed,
non-revoked version; it does not remove revocations. Revocation state persists in the
operator file across application restart. Protect that file against manual rollback.

The local/mounted-file implementation reads control state at every model attempt,
tool dispatch, and final history commit. Missing, invalid, or unreadable state denies
work. It does not demonstrate cross-replica propagation or remote storage consistency;
shared control hosting and measured propagation remain Stage 5 work. External calls
already accepted cannot be undone by cancellation. No production containment claim
is made.

## Enforcement and evidence

The loader bounds regular-file reads to 8 KiB, rejects final-component symlinks and
path escapes, verifies the digest, and consumes the same immutable bytes. The approval
root and its ancestors must be operator-owned. Effective tools intersect caller,
application, agent, and manifest permissions; the caller policy defaults to empty.
Shared model/session budgets, deadlines, reset, and cancellation remain enforced.
Durable memory, recursive skill calls, and arbitrary file/network tools are unavailable.

Run audit events bind skill ID/version/digest and registry/control generations to the
run, policy, and hashed caller reference without retaining Markdown or model text.
Initial loader denials currently occur before run admission and have no skill audit
binding; full publication/load-denial audit evidence remains open.

Validation: `uv run --locked pytest -q` — **60 passed**;
`uv run --locked ruff check apps` and format/whitespace checks passed.
Tests cover both selected skills, empty caller permissions, tampering, immutable
content, symlinks/path escapes, unknown IDs before access, injected write/recursion/
memory requests with zero backend calls, repeat budgets, active revocation with no
follow-up model call or history commit, persistent operator controls, control outage,
and reset cancellation with no history resurrection or counter reset.

Still required: hosted skill validation, complete review/publication audit records,
additional retry/revocation race fixtures, and comprehensive boundary-matrix evidence.
Stage 4 must test cross-user durable memory and consent once that backend exists.
