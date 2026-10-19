# Stage 4 task — Governed durable memory

## Current status

**Complete for the selected single-process dev teaching scope.** User-approved,
explicit-consent genre/language preferences use Blob Storage across the same user's
sessions with 30-day expiry and no dev backups/version history. Bounded async access,
governed recall, inspection/correction/deletion, ETag/generation fencing, hourly
physical cleanup and overdue-cleanup monitoring are deployed. All **126 tests pass**;
CI, infrastructure validation, restart persistence and the stable hosted lifecycle
passed. Stage 3 case 4 is resolved at the memory layer. See the
[guide](../stage-4-memory.md) and [validation evidence](../stage-4-validation.md).

Stage 1's shared/resumable-session and expired-ingress-token gaps are unchanged;
Stage 5 production controls remain separate.

## Goal and outcome

Add consented durable facts/preferences while preserving bounded short-term session history and all prior security gates. Implement [Stage 4 of the specification](../secure-agent-teaching-spec.md) under [shared conventions](README.md).

## Scope

Authenticated memory APIs, approved persistence/retrieval, lifecycle controls, inspection/correction/deletion, and the deferred skill memory-boundary tests. Only selected backend patterns need implementation.

## Prerequisites and dependencies

- [Stage 3](stage-3-markdown-skills.md), including tested skill capabilities and the now-completed boundary case 4.
- Select durable backend, allowed categories, consent policy, retention/deletion values, and any derived-data design before enabling persistence. Keep the session backend/resumption decision distinct.
- Recommend the simplest adequate design without treating that recommendation as user approval of a product. Record rationale, alternatives, tradeoffs, and reconsideration triggers.

## Ordered work checklist

1. [x] Define session history versus durable fact contracts. “Chose comedy this session” and already-suggested movies are working context; consented “prefers comedy” is a durable personal preference. Actor/movie relationships are catalog knowledge, not automatically personal memory.
2. [x] Evaluate structured key/value/document records for exact preferences, vectors for similarity over approved memories, graphs for explicit relationships, or a hybrid only if measured needs justify its complexity. Graph/vector do not dictate lifetime or supply governance by themselves.
3. [x] Implement typed memory APIs deriving tenant/user/session/purpose from trusted authenticated scope. Enforce filtering in storage queries, caches, and every graph hop before data can be disclosed; no model-supplied identity is authoritative.
4. [x] Approve per-environment backend/endpoint/identity/namespace/operation allowlists. Reject arbitrary connection strings, endpoints, credentials, SQL/Gremlin, and uncontrolled traversals. Bound result count, depth/fan-out, query time, embedding calls, and spend under shared budgets.
5. [x] Validate consent and category before writes or derived-data creation. Store provenance, timestamps, expiry, and source metadata; exclude secrets, tokens, hidden reasoning, and unrestricted transcripts. Recalled content remains untrusted and cannot grant permissions.
6. [x] Implement inspect, correct, forget-record, and forget-all controls; encrypt/restrict access and propagate lifecycle actions to records, embeddings, graph nodes/edges, indexes, caches, replicas, and backups as applicable. Keep source-to-derived mappings and restore/rebuild tombstones.
7. [x] Enforce immediate retrieval exclusion for expiry/deletion and physical cleanup within the spec's approved SLA. Document bounded backup expiry and separately retained content-free audit metadata.
8. [x] Complete Stage 3 case 4 and all memory tests below; retain session, skill, catalog, network, and budget regression coverage.

## Acceptance criteria

- [x] Consented allowed preference survives a session boundary only in its approved scope; session history is not automatically promoted into durable memory.
- [x] Another tenant/user or non-owned session cannot retrieve or modify protected memory through APIs, indexes, caches, concurrent requests, semantic matches, or graph paths.
- [x] Missing consent/category authorization denies before source or derived persistence. Poisoned memory never becomes policy, approval, or authority.
- [x] Inspect/correct/delete and expiry work across enabled source/derived stores; reset/restore/rebuild cannot resurrect deleted data. Tests prove immediate retrieval exclusion and cleanup within declared SLA.
- [x] Unapproved backends/endpoints and arbitrary query text fail; retrieval, traversal, embedding, and retry consumption stay bounded and cancel correctly.
- [x] Stage 3 memory case 4 passes at the memory layer for a skill requesting another user's records or writing without consent, with no disclosure/change.
- [x] Short-term isolation/reset/expiry, summary poisoning, context limits, and applicable restart/concurrency tests still pass. Catalog records remain separate from user memory; agent PUT stays forbidden.

Same-user owned sessions intentionally share approved preferences. Vector/graph/
embedding paths are not enabled. Backup restore/rebuild is not exposed; no dev
versions or soft-delete copies exist. The lifecycle tests cover every enabled store
and retain empty generation fences instead of private deleted content.

## Security and negative scenarios

Test forged scopes, consent withdrawal, secret-bearing writes, instruction-laden recalled facts, stale indexes, cross-partition graph edges, unapproved embedding destinations, retrieval storms, and deletion racing with an update. For each enabled pattern, prove absence of forbidden reads/writes using storage effects and returned data, not a model refusal. Fail closed on unavailable authorization or ambiguous scope.

## Documentation and evidence to produce

- Backend decision and approved environment inventory, data-flow/source-derived map, consent/lifecycle contract, retention/deletion/backup policy, and permission review.
- Learner preference save/inspect/forget exercise distinguishing catalog knowledge and session context.
- Redacted isolation, no-consent, poisoning, deletion/restore, limit, and deferred skill-test results; evidence must not preserve deleted content.

## Out of scope

An implicitly selected Azure memory product, implementing every store pattern, automatic transcript persistence, unrestricted retrieval/query APIs, storing credentials, or converting catalog relationships into personal memory without policy/consent. No change to the read-only agent catalog role.
