# Stage 4 memory — implementation checkpoint

Stage 4 is in progress. The user approved explicitly saved movie genre/language
preferences following the same authenticated user across sessions, with a 30-day
expiry. `config/memory-policy.json` records that policy. Hosted storage selection,
backup/deletion SLAs, and hosted acceptance are still open. No cloud memory resources
have been created, and the running app does not enable memory persistence.

## Contracts implemented

Session chat history remains separate from personal preferences. Neither ordinary
chat text, a movie lookup, nor a skill's purported approval supplies write consent.
The initial preference vocabulary is deliberately bounded:

- `preferred_genre`: action, animation, comedy, documentary, drama, science_fiction.
- `preferred_language`: en, es, fr, ja.

There is one record per category, at most two records per user/purpose namespace.
Arbitrary free text, credentials, transcripts, movie synopses, and catalog relationships
cannot fit this schema. Expanding categories or vocabulary requires policy review.
Each record includes a stable ID, revision, source session, explicit-consent policy
version, created/updated/expiry timestamps, user-declared provenance/confidence, and
an `untrusted` marker. Correction requires fresh explicit consent and renews expiry
from that write. Recall integration will treat the values as evidence, never authority.

The service derives tenant/user/session from authenticated identity and owned sessions.
Purpose is the fixed application value `movie_preferences`. Bodies cannot choose an
identity, namespace, backend, endpoint, query, or purpose. The selected user scope
allows another owned session for that same user to access the preferences. A separate
session-scoped fixture verifies the narrower policy remains enforceable.

## Authenticated API groundwork

These routes are implemented but return `403 memory_not_enabled` in the default
hosted configuration. The tests inject the explicitly non-durable local adapter and
an application-owned permission callback to exercise them:

| Route | Purpose |
| --- | --- |
| `GET /sessions/{sid}/memory` | Inspect records and the namespace generation |
| `POST /sessions/{sid}/memory` | Explicitly save an allowed preference |
| `PUT /sessions/{sid}/memory/{record_id}` | Correct a record using its revision and namespace generation |
| `DELETE /sessions/{sid}/memory/{record_id}` | Forget one owned record |
| `DELETE /sessions/{sid}/memory` | Forget all preferences in the owned namespace |

A save body contains category, value, `consent: true`, and the `expected_generation`
returned by inspection. Correction also requires `expected_revision`. This is a
separate explicit user action, not consent inferred from chat. Only a trusted API
adapter constructs user-origin access; never register that write adapter as a model
or skill tool. Skill-origin access is restricted to inspection even if it supplies
`consent: true`; another user's namespace remains inaccessible.

A generation fence rejects stale creates/corrections after deletion. Corrections
never recreate a missing record. Deletion atomically removes values and advances the
namespace generation; tombstone/effect metadata contains no preference values.
Owner deletion stays available after the eight-operation session read/write budget is
exhausted. Chat reset does not reset that counter or automatically save/delete preferences.

## Local storage and lifecycle limits

`FixtureMemoryStore` is an in-process, lock-protected test store. Queries select the
owner/purpose partition before inspecting records. There is no general query API,
network client, embedding, graph, derived index, cache, or disk backup. Expired records
are immediately excluded and removed on a scoped operation. It does not provide an
idle-data cleanup schedule, encryption at rest, persistence across process restarts,
a hosted deletion SLA, or backup restore guarantees. Those are acceptance work for
the selected durable adapter; the fixture does not satisfy hosted durability.

Audit callbacks contain policy/operation, origin, and hashed scope references without
preference content. Delivery failure before access prevents storage effects. Protected
hosted audit retention and reconciliation of ambiguous durable commits are still to
be implemented with the durable backend.

## Backend design proposal — not a product approval

Start with exact structured records; there is no measured need for vectors, embeddings,
graph traversal, or a hybrid store. This preserves simple consent, correction, and
forget-all operations without introducing derived copies of personal data.

My proposed hosted design is one bounded JSON document per user/purpose in Azure Blob
Storage. Its document contains the two preferences, namespace generation, and deletion
metadata. Scope-derived object names avoid a broad listing query. Conditional ETag
updates can implement the same optimistic-concurrency contract: Azure documents a
failed `If-Match` update returning `412` when another writer has changed the blob.
This is a design inference from [Microsoft's Blob concurrency documentation](https://learn.microsoft.com/en-us/azure/storage/blobs/concurrency-manage).

Azure Table Storage is a credible row-based alternative. It supports Entra data
access and table-scoped data roles, including read/write/delete through Storage Table
Data Contributor; the shared generation/forget-all contract would need a coordinated
row design. See [Microsoft's Table authorization documentation](https://learn.microsoft.com/en-us/azure/storage/tables/authorize-access-azure-active-directory).
Microsoft recommends managed identities for storage data access where possible;
[its authorization guide](https://learn.microsoft.com/en-us/azure/storage/common/authorize-data-access)
describes the identity-based boundary. Neither product is provisioned or enabled by
this checkpoint. Revisit a database/vector/graph option only when measured query or
scale requirements justify it.

The durable design still needs the approved environment endpoint/namespace/identity,
encryption and access restrictions, a physical deletion/cleanup SLA, backup expiry
and restore fencing, bounded network operations, and complete shared run accounting
for model recall. The session-resumption backend remains a separate decision.

## Validation checkpoint

Run `uv run --locked pytest -q` and `uv run --locked ruff check apps scripts`.
The full suite currently passes **95 tests**, retaining the Stage 1–3 regressions.
The new tests cover consent/category denial before storage, user/tenant/session
isolation, forged API scope, correction and expiry, deletion/stale-write fences,
concurrent correction/delete and duplicate creates, audit failure, reset/counter
behavior, and chat text not promoting transcripts into preferences.

Stage 3 memory case 4 now has local memory-layer fixtures proving that skill-origin
writes deny even with purported consent and that another user's records are not
returned. Actual model-to-memory integration and durable/hosted versions of those
cases remain mandatory Stage 4 acceptance work. No acceptance checkbox is closed on
the strength of a fake model refusing an operation.
