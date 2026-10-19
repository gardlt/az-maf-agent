# Stage 3 task — Approved Markdown skills

## Current status

**Complete for the single-replica teaching scope.** Both user-selected skills are implemented and validated locally and in dev. All 81 local tests pass. Hosted skill reads, exact digest binding, downstream write denial, and disable-without-redeploy passed. Case 4 remains mandatory Stage 4 memory integration work. See [validation evidence](../stage-3-validation.md) and [the operator guide](../stage-3-skills.md).

## Goal and outcome

Add reviewed Markdown skill guidance without granting new authority. Implement [Stage 3 of the specification](../secure-agent-teaching-spec.md) and preserve [shared conventions](README.md).

## Scope

Approved skill registry/loader, capability intersection, integrity/revocation gates, and all six skill-boundary cases, with durable-memory integration completed in Stage 4.

## Prerequisites and dependencies

- [Stage 2](stage-2-movie-mcp.md) read-only catalog, dispatcher, service permissions, budgets, and audit.
- Selected by the user: movie research assistant and movie-night planner, each limited to read-only TMDB tools. Bundles and digests are recorded in `skills/approved.json`.
- Selected trust: repository-reviewed approval index and SHA-256-pinned immutable bytes in the agent image. Composition/dependencies are disabled. Dev revocation uses operator-managed Azure tags with workload read-only access.

## Ordered work checklist

1. [x] Define validated metadata: stable ID/version, owner, purpose, capabilities/tools, input/output expectations, Markdown instructions, and pinned content digest.
2. [x] Load only approved versions/bundles; validate dependencies and safe paths. Reject oversized, unknown, revoked, unsigned/integrity-invalid artifacts under the chosen trust mechanism.
3. [x] Intersect authenticated principal, application, agent, and approved skill policies. Treat skill text as instructions/data, never authority; do not alter approval rules or catalog write permissions.
4. [x] Prevent time-of-check/time-of-use races by verifying and consuming the same immutable bytes. Bind run use to version/digest; apply current revocation at load and subsequent gates under existing freshness/propagation and fencing rules.
5. [x] Deny unapproved files, other skills, URLs, and bundle escapes before access. If composition is approved, validate every child, intersect permissions, bound depth, and share run budgets/deadline/cancellation.
6. [x] Implement review/publication/rollback and disable-without-redeploy flow; rollback only to a currently approved, non-revoked artifact.
7. [x] Run the boundary matrix below with deterministic model and backend fixtures, retain earlier regressions, and record Stage 4 follow-up explicitly.

## Acceptance criteria

- [x] Approved selected skill works with chat and read-only catalog; unknown/tampered/revoked/path-escaping skills fail closed.
- [x] Cases 1–3 and 5–6 below pass now with absence-of-effects evidence. Case 4 is tracked as mandatory [Stage 4](stage-4-memory.md) integration work, not marked passed prematurely.
- [x] Unavailable durable-memory operations already deny in Stage 3; isolated Stage 1 session history continues working.
- [x] No policy expansion, unauthorized dispatch, private-file read, network fetch, or catalog mutation occurs in negative cases.

## Security and negative scenarios

| Case | Test and required result |
| --- | --- |
| 1. Forbidden catalog write | Request PUT/update with and without purported human approval. Dispatcher denies; reuse direct service test proving actual agent identity remains read-only and records unchanged. |
| 2. Injection | Malicious Markdown or movie synopsis asks to override policy/identity. Even a complying fake model cannot change permissions or cause unauthorized dispatch. |
| 3. Unapproved loading | Request files, another unapproved skill, external URL, or escaping reference. Deny before access/fetch; approved composition, if enabled, cannot widen permissions or grant arbitrary filesystem/network access. |
| 4. Memory boundary — Stage 4 follow-up | With durable memory enabled, request another user's data or a durable write without consent. Memory layer denies; assert no disclosure or persistence. Model restraint is not enforcement. |
| 5. Recursion/repeats | Recursive invocation or repeated searches either fail composition policy or consume the same counters/deadline. Stop at limits/cancellation with no reset or subsequent dispatch. |
| 6. Integrity/revocation | Swap content after validation, load tampered/unknown/revoked artifacts, and revoke an active skill. Only verified immutable bytes may be consumed; subsequent work blocks within existing bounds. |

## Documentation and evidence to produce

- Approved skill format, selection rationale/alternatives, review/update/rollback procedure, and normal/negative learner walkthrough.
- Loader/network spies, backend invocation counts, state/version comparisons, and redacted run/skill/policy/revocation IDs, rule decisions, and timing. Do not retain private content or raw malicious payloads in logs.
- Explicit Stage 4 follow-up for case 4 and limits on cancellation of accepted external work.

## Out of scope

Unreviewed marketplace installation, arbitrary executable Markdown/code, permission escalation, agent PUT, automatic durable writes, required composition, or production shared-control guarantees. Both teaching skills were explicitly selected by the user. The existing approved Foundry model is reused; no durable memory backend is selected.
