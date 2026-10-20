# Secure Agent Teaching Application Specification

Status: proposed design; application implementation is outside this document's scope. Reviewed against the project brief and official source pages on 2026-10-14.

## Purpose and scope

Build one evolving Python command-line application using **Microsoft Agent Framework**. Learners extend the same application through six stages: basic chat, approved MCP tools, approved Markdown-defined skills, scoped memory, production guardrails with emergency controls, and application-controlled model routing. The user added Stage 6 on 2026-10-19. Each stage preserves the controls and tests introduced earlier; these are not independent demos.

This document defines required behavior, security boundaries, deployment portability, operational controls, and acceptance evidence. **MUST** denotes a release requirement; **SHOULD** denotes a recommendation whose exceptions require a recorded rationale. Product and SDK capabilities must be verified against the selected, pinned versions during implementation. The supplied references are design inputs, not a claim that this specification or an implementation has been certified.

### Goals

- Teach progressively richer agent behavior while making authorization, trust boundaries, and failure handling visible.
- Deploy a CLI calling an HTTPS Python API on Azure Container Apps, protected by Microsoft Entra built-in authentication (Easy Auth), backed by a shared Microsoft Agent Framework Python core. Keep local test adapters and a future Foundry hosting option possible.
- Make security controls enforceable in application code and deployment policy, independently of model compliance.
- Provide reproducible demonstrations, automated evaluations, adversarial exercises, and auditable acceptance evidence.
- Demonstrate practical containment and recovery when an agent proposes unsafe behavior or encounters hostile content.

### Non-goals

- Building an unrestricted autonomous agent, arbitrary shell executor, general plugin marketplace, or self-modifying application.
- Allowing a model to create its own permissions, approve consequential actions, change policy, or grant trust to retrieved content.
- Treating prompt wording, model refusals, content filters, or an MCP transport connection as sufficient authorization.
- Guaranteeing complete protection against prompt injection, data leakage, supply-chain compromise, or harmful behavior. The design provides layered risk reduction and measurable containment, with documented residual risks.

## Architecture and trust model

The selected path is CLI -> HTTPS Python API on Azure Container Apps -> shared Microsoft Agent Framework Python agent core. Entra Easy Auth authenticates inbound API callers before application authorization. The CLI does not hold downstream workload credentials or enforce the server's security boundary. Local fake-model execution remains available for offline teaching and tests. Microsoft Agent Framework supplies agent/model integration; application-owned wrappers enforce policy, budgets, approvals, tool dispatch, skill loading, memory access, and cancellation. Framework-specific code belongs behind adapters to make a future hosting change assessable without promising plug-and-play portability.

```text
CLI -> HTTPS Container Apps ingress -> Entra Easy Auth
  -> Python API: caller claims, permissions, tenant/session context
  -> policy snapshot, admission gate, budgets, run controller
  -> Microsoft Agent Framework orchestration / model adapter
       -> guarded tool dispatcher -> approved MCP servers
       -> approved skill registry
       -> scoped memory service
  -> output validation and redaction -> caller

Central approved configuration -> all admission and dispatch gates
All gates -> redacted telemetry and protected audit sink
Operator control plane -> revoke / disable / cancel / global stop
```

The agent runtime and the model endpoint are separate architectural choices. The Container Apps agent can call an Azure-hosted model through its model adapter; using that model does not require hosting the agent in Foundry. The model, deployment, and authentication capabilities must be selected and verified separately.

## Architecture decision and alternatives register

Teach each choice with its rationale, costs and limitations, alternatives, and observable reasons to revisit it. These decisions apply to this experiment, not to every agent application. Selected choices below reflect user direction; open choices require an explicit implementation decision before the relevant capability ships.

| Decision and chosen approach | Rationale for this experiment | Credible alternatives and tradeoffs | Reconsider when |
| --- | --- | --- | --- |
| Interface: CLI calling an HTTPS API | Keeps the lesson focused on agent behavior and supports repeatable scripted exercises. | A web UI makes interactive approvals and nontechnical access easier but adds frontend, browser-session, and UI security work; an in-process-only CLI is simpler locally but cannot demonstrate the selected hosted boundary. | Learners need browser access, rich approval views, or shared-session workflows that the CLI cannot serve well. |
| Agent hosting: Container Apps Python API with shared core | Makes HTTP, identity, scaling, and enforcement boundaries explicit in an ordinary container deployment. | Foundry hosted agents offer an agent-focused hosting/integration path; adopting it requires validating its supported runtime, lifecycle, identity, cancellation, and observability contracts. Container Apps leaves more API/lifecycle integration to the application. | Managed agent lifecycle or Foundry integration materially reduces measured operational work, and a prototype passes the same security contracts. |
| Caller authentication: Entra Easy Auth | Delegates inbound authentication to the platform while keeping application permissions visible in code. | App-managed authentication with a maintained identity library offers finer protocol/control portability but adds token-validation configuration, maintenance, and security testing. | Required identity providers, token flows, claim handling, or hosting targets cannot be supported by the tested Easy Auth configuration. |
| API boundary: direct authenticated Container Apps HTTPS ingress; no API Management initially | Follows the user's preference to limit initial complexity and cost exposure by omitting another service to configure and operate. This is not a claim that one deployment is always cheaper. | API Management can add centralized API governance and supported request/concurrency/token policies, with additional configuration, operations, and service-specific costs to evaluate. | Multiple clients/APIs need shared gateway policy, subscription governance, or measured traffic controls beyond the chosen ingress and application design. |
| Enforcement: application-owned authorization, budgets, approvals, and shutdown | Makes deterministic guarantees testable and preserves them independent of model compliance. | Managed content-safety, gateway, monitoring, or evaluation services can supplement detection and operations; they introduce coverage limits, latency, dependencies, and possible costs, and cannot replace domain authorization. | Adversarial evaluations or operational evidence identify a gap a specific service can measurably reduce. |
| Model: one approved Azure-hosted deployment selected through configuration, not hardcoded; actual model choice open | Keeps initial behavior and evaluation simple while separating agent hosting from inference. | Compare suitable deployments for tool support, context, identity, region, quotas, quality, and measured usage. Later application-owned routing or an Azure model router endpoint adds flexibility but also evaluation and operational complexity; fake models remain the deterministic test baseline. | Workload complexity, measured quality/latency, availability, or cost justifies evaluating routing or another deployment. |
| Stage 2 MCP domain: bundled synthetic movie catalog; read-only agent tools and an admin-only HTTP PUT exercise | Familiar IMDb-style records teach lookup and the distinction between endpoint existence and permission without external data/accounts. | Omitting PUT would simplify the fixture but miss the selected negative authorization lesson; a live catalog adds licensing, credentials, and availability work. | A learning objective requires external-service behavior or richer queries; agent write access would require a separate explicit scope decision and is not selected. |
| Stage 3 teaching skills: movie research and movie-night planning, selected by the user | Reviewed guidance structures comparisons and preference-based shortlists over the same two TMDB reads. | Direct tool use remains an alternative; use a repository-reviewed digest index, immutable bytes, and no composition. Dev control tags provide read-only workload gates. | Revisit if evaluation shows no benefit over direct tools, or if composition, more artifacts, or production shared controls are needed. |
| Memory backend: user-approved Azure Blob document per tenant/user/purpose for explicit-consent movie preferences | Exact genre/language preferences need no similarity index. Use 30-day expiry, ETag concurrency, immediate retrieval exclusion, hourly cleanup within 24 hours, and no dev versions or soft-delete backups. See [Stage 4](stage-4-memory.md). | Table/key-value records remain viable; vectors, graphs, and hybrids add derived-data synchronization/deletion work and require measured justification. | Query quality, relationship needs, volume, backups, or deployment scope exceeds the bounded dev design. Reapprove backup/restore fencing before enabling it. |
| Control-plane product: open; shared durable policy, leases, approvals, and run registry required | Fixes safety semantics without assuming an unapproved Azure product. | A transactional database, or a configuration service plus transactional state store and optional notification channel, has different consistency and operational tradeoffs; a local fixture is sufficient only offline. | Before multi-replica stage-5 release, select and prove a backend meeting atomic reservation, fencing, audit, and freshness requirements under partitions. |
| Network topology and egress control product: open; deployed destination restrictions required | Teaches defense against network bypass without silently selecting additional infrastructure. | Assess supported Container Apps networking with a routed firewall/network appliance or another verified architecture; compare environment constraints, operational dependencies, cost, and evidence quality. Application allowlists alone cannot prove network enforcement. | Select before deployed network acceptance; revisit when destinations, environment type, or operational requirements change. |

Document further material implementation decisions in this register with the same four elements. The MCP teaching domain and Stage 4 Blob memory design are selected; the production control-plane product remains open. Stage 3 skill selection and its bounded dev control mechanism are recorded above. An open product choice is not permission to omit its required controls.

### Network bypass boundaries

“Tool gateway” means the guarded application MCP dispatcher, not Azure API Management. No generic model-controlled HTTP/shell tool, arbitrary URL argument, or alternate client path may bypass mandatory gates. Egress destination restrictions independently limit which services agent and MCP runtimes can reach. Downstream service authorization controls which operations those identities may perform. A host allowlist generally cannot distinguish allowed GET from forbidden PUT at the same host: the reachable movie catalog MUST still deny writes from agent/MCP workload identities. Removing PUT from discovery is insufficient, and human approval does not change that prohibition.

Maintain an approved operational destination inventory covering the catalog/MCP service, selected model endpoint, identity/token services, DNS, configuration/control state, secrets, telemetry/audit, and required platform/image-registry dependencies. Validate dependency-specific rules; do not replace them with an unusable blanket block or unrestricted internet access. Protect internal/private MCP ingress from public unauthenticated access, and require service authentication on permitted internal paths as well.

Disable automatic redirects unless required and controlled; if enabled, revalidate every redirect destination before connecting. Any future URL tool needs validated bounded URL handling, approved schemes/ports/destinations, redirect-count and response-size limits, and checks on resolved addresses to prevent escape to unapproved networks or metadata services. Neither model-provided endpoints nor tool results may reconfigure trusted clients. Controlled test probes may exercise bypass paths without exposing those probes as agent tools.

### Stage 6 application-controlled model routing

Stages 1–5 use one approved model deployment resolved from validated configuration. The user subsequently requested application-owned routing as Stage 6 to reduce routine inference costs. [Stage 6 tasks](tasks/stage-6-model-routing.md) and [routing architecture](stage-6-model-routing.md) define the extension: approved smaller/stronger deployments, a stable selection per run, shared accounting and caller-managed history. Automatic alternate-model fallback remains outside its initial scope. This extension does not waive any earlier release gate.

Two alternatives are explicit application-owned routing among approved models, giving direct control with additional implementation/testing work, or [Azure model router](https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/model-router) as a separate inference endpoint, delegating model selection within a verified approved subset while the agent remains in Container Apps. Evaluate supported capabilities, routing visibility, and actual quality/latency/cost rather than assuming savings. Model routing selects the inference model; tool selection proposes actions and remains subject to the existing tool gateway.

As checked on 2026-10-14, Microsoft's [Agent Framework runtime routing documentation](https://learn.microsoft.com/en-us/agent-framework/concepts/agents/runtime-model-routing) describes an experimental .NET routing client and says that built-in routing support is unavailable in Python. This is SDK- and version-dependent: recheck the pinned release before implementing. It does not prevent Python from calling an Azure model router inference endpoint through a compatible client/API.

Any future route MUST preserve application-owned authorization, model/endpoint allowlists, capability compatibility (including tool calls and structured outputs), and one shared budget/cancellation ledger across steps, retries, and fallbacks. Evaluate each permitted route and transitions between routes. Trace routing-policy version, selection reason, configured endpoint and resolved model when exposed, usage, and outcome without logging sensitive content; any visibility gap needs explicit review. Verify that managed routing cannot select an unapproved model. Preserve scoped context/history across transitions: caller-managed history must retain compatible roles and tool-result associations within context limits; service-owned conversation IDs are not portable by assumption. Reconstruct or migrate history through a tested authorized path, or deny the transition. Routing must never reset budgets or relax approval requirements.

### Principles and mandatory boundaries

1. **Every external input is untrusted:** user text, tool responses, retrieved content, Markdown skills, and recalled memory. Approval of a source permits use; it does not turn source content into system instructions or authorization. Preserve provenance, label data boundaries, cap size, and validate structure before use.
2. **Application-enforced authorization:** derive the authenticated principal, tenant, user, and session outside the model. Evaluate permission at admission and again immediately before any tool dispatch or memory operation. Never accept model-supplied identity or scope as authoritative.
3. **Default deny and fail closed:** unknown tools, missing policy, invalid schemas, expired approvals, unavailable authorization, and ambiguous scope produce a structured denial. Cancellation and incident controls remain usable during dependency failures.
4. **Least privilege:** use explicit tool/MCP allowlists and narrow operation scopes. A permitted server does not imply permission for every tool it advertises. No automatic discovery-to-execution, arbitrary endpoint selection, filesystem traversal, or unrestricted outbound networking.
5. **Defense in depth:** prompts explain policy; deterministic gates enforce it. Content screening supplements authorization and schema validation. No model output is executed as code, shell, SQL, HTML, or a downstream instruction without an appropriate safe interpreter or parameterized interface.
6. **Reproducibility:** pin Python, framework, model configuration, adapters, tools, and dependencies. Commit a dependency lockfile, verify integrity, generate an SBOM, scan dependencies and images, and block releases with unresolved findings above the approved severity threshold. Pin production images by digest.
7. **Centrally managed approved configuration:** use versioned, reviewed policy bundles with integrity verification, rollout history, and rollback. Reject unauthorized configuration changes. Emergency revocations override a run's policy snapshot at every dispatch gate.

### Run and control contracts

Each run MUST carry an immutable run ID, authenticated scope, policy version, model configuration, allowed capabilities, budget ledger, cancellation handle, and trace correlation ID. Audit records capture decisions rather than chain-of-thought. Only the control plane can grant capabilities or change policy.

Before work begins, resolve finite limits for input bytes, context tokens, output tokens, turns, tool calls, retries, wall-clock timeout, parallelism, and spend. Limits apply per run and aggregate per principal/tenant where relevant. Missing limits deny admission. Reserve resources atomically before concurrent dispatch, reconcile actual usage afterward, and never allow retries or nested calls to reset counters. Use conservative cost estimates when exact billing is delayed; the spend budget is an admission bound, not a guarantee about provider invoices. On exhaustion, stop new work, cancel pending work where supported, and record a terminal reason.

Tool contracts MUST define server identity, tool name/version, input and output schemas, side-effect class, required permissions, timeout, response-size cap, destination scope, and whether approval is required. Validate both schema and semantic safety, including path containment, destination allowlists, numeric bounds, and ownership. Validate returned data and treat errors as untrusted output too.

Consequential actions include sending messages, publishing, changing permissions, deleting records, making purchases, and external state changes identified by policy. Obtain explicit confirmation from an authorized human through a trusted interface before dispatch. Bind approval to principal, tenant, run, exact normalized arguments or their digest, tool/version, consequence summary, expiry, and a single use. Argument changes, expired approval, or permission changes require a new decision. An approval cannot bypass other policy gates. Use idempotency keys and execution receipts where supported; ambiguous completion requires reconciliation before retrying.

Permission is required first. Human approval can further restrict an otherwise permitted consequential action; it never grants a forbidden operation. A disallowed proposal is denied rather than offered an approval path. In particular, even explicit human approval cannot override the agent's read-only catalog permissions.

Generate the approval display from canonical validated arguments, including the exact target and effect; do not substitute the model's description for the action being approved. The model and tool servers cannot access the approval or operator control surface. Recheck cancellation, current revocations, permissions, and budgets immediately before dispatch. Serialize consequential dispatch reservations against control changes using a policy epoch or equivalent fencing mechanism: a revocation committed before reservation MUST prevent dispatch. Consume approval atomically with the reservation. An action already accepted downstream remains subject to reconciliation, not a promise of rollback.

### Teaching defaults

The following proposed defaults make the exercises reproducible. They are application choices, not Azure or model-provider limits. Approved configuration may change them, but every value must remain finite and production must satisfy the release gates.

| Resource | Default |
| --- | --- |
| User input / skill / tool result | 16 KiB / 32 KiB / 64 KiB per item, checked before parsing or context insertion |
| Model input / output | 16,000 / 2,000 tokens per call, additionally constrained by the selected model's context window |
| Aggregate tokens / turns / tool attempts | 24,000 tokens / 8 model calls / 12 tool attempts per run, including retries and rejected attempts where applicable |
| Retries | At most 2 per transient operation, inside the same run budget; no retry for policy failures or ambiguous consequential effects |
| Execution deadlines | 120 seconds active run, 30 seconds model call, 10 seconds tool call |
| Approval expiry | 5 minutes; waiting releases execution capacity and never resets consumed budgets |
| Parallelism | 2 active runs per principal, 10 per deployment, 2 tool calls per run |
| Spend | USD 0.25 per run and USD 5 per principal per day, using approved pricing and conservative reservation; unknown pricing denies billable dispatch |
| Repeated violations / identical call loop | Cancel after 3 policy violations or 3 repeated canonical call fingerprints |
| Control freshness | Poll at most every 2 seconds; expire execution leases after 5 seconds without a verified refresh |
| Cancellation | Target acknowledgement within 5 seconds under healthy conditions; terminate an isolated non-cooperative worker after a further 5-second grace period |
| Durable memory | Opt-in; default retention 30 days, immediate retrieval exclusion on expiry/deletion, active-store purge within 24 hours |

Provider requests may continue to incur costs after cancellation. Reconcile reserved and actual usage, including configured tool charges and provider-billed token categories. Backup expiry and audit retention require explicit approved values before production; active-store deletion does not imply immediate deletion from backups.

## Stage 1 — Basic chat

### Requirements

- Provide a Python CLI for starting a session, sending text, viewing a response, and exiting or cancelling cleanly. Include deterministic mock-model mode for offline teaching and tests.
- Use Microsoft Agent Framework through a model adapter behind the Python API for hosted exercises, with a local adapter for offline tests. Keep tool dispatch, skill execution, and durable user-fact memory disabled; bounded session history starts here.
- Configure Python `AgentSession` and a history provider explicitly for the pinned SDK instead of relying on implicit storage defaults. Apply the short-term memory contract below from Stage 1; Stage 4 adds governed durable facts/preferences.
- Separate application instructions from user data. Explain that role boundaries help structure context but cannot eliminate prompt injection.
- Validate input encoding and size; enforce context/output-token limits, turn limits, timeout, retry bounds, and spend limits from the first stage.
- Load local credentials through an approved credential mechanism; never ask users to paste secrets into chat. Redact diagnostics and show understandable failure messages without internal secrets or raw provider payloads.

### Acceptance

A learner can run a multi-turn chat with reproducible setup. Tests demonstrate cancellation, oversized-input denial, bounded retry after a transient error, timeout, and budget termination. A prompt requesting tool use cannot cause any external execution. Chat content is not persisted by default, including in logs.

### Short-term working/session memory — applies from Stage 1

Use short-term context for the current task: for example, “chose comedy this session” and IDs of movies already suggested, once catalog tools are introduced. It is not an automatically saved long-term preference. Storage patterns such as graph/vector do not inherently determine lifetime; session history and Stage 4 durable memory have separate lifecycle policies.

Scope every session to authenticated tenant/user/session identity, with ownership checks on creation, load, update, reset, and resumption. Set finite history-byte/token limits, idle TTL and maximum lifetime in approved configuration; missing values deny session creation. Apply existing run deadlines to history processing. Expose explicit reset, reject expired sessions, and ensure late writes cannot resurrect reset/expired state. Minimize sensitive content and never automatically promote history or summaries into durable user memory.

Trim context or summarize within the same model/token/spend budgets before exceeding context limits. Preserve valid tool-call/result associations. Summaries remain untrusted data: they cannot turn quoted policy, approvals, or claimed permissions into authority. Keep authoritative security counters, current policy, cancellation, and approvals outside model-visible history; trimming, reset, expiry, or resumption must not erase security evidence or reset aggregate limits. Recheck authorization when resuming.

Process-local RAM suits the offline/single-process lesson but loses state on restart and cannot share it across replicas. A shared TTL session store is an alternative when Container Apps needs session resumption or multiple replicas; the backend remains open, with no newly required Azure product. Do not rely on sticky routing for correctness. Before enabling those hosted behaviors, choose explicit shared state or validated state rehydration, with atomic/versioned updates and duplicate-request handling. Otherwise document session loss and require a fresh session; never silently resume with incomplete state.

Use the official [conversation storage guidance](https://learn.microsoft.com/en-us/agent-framework/agents/conversations/storage) and [self-hosting guidance](https://learn.microsoft.com/en-us/agent-framework/hosting/self-hosting/) to validate the pinned implementation. Session storage must be intentional; a remote conversation identifier does not establish ownership or portable history.

Acceptance covers session/user isolation, reset and TTL expiry, context bounds, poisoned summaries, and documented restart/resumption behavior. Where shared/resumable sessions are enabled, test concurrent updates, duplicate requests, replica changes, and reset racing with an active run. Assert no cross-session leakage, resurrected history, unauthorized action, or security-counter reset. Reuse these tests in Stage 4 alongside durable-memory tests; no durable backend is required merely to teach Stage 1 history.

## Stage 2 — Approved MCP tools

**2026-10-18 scope revision:** The user selected TMDB as the sole movie source. The synthetic catalog and admin PUT design below is retained as historical context and is no longer an active implementation or acceptance requirement. The current Stage 2 contract is in [the Stage 2 task](tasks/stage-2-movie-mcp.md) and [TMDB integration record](tmdb-integration.md): two read-only tools, `tmdb_<id>` identifiers, labeled TMDB ratings, no TMDB user session or write endpoint, and live credential/attribution/network acceptance. Stage 3 references to synthetic catalog PUT inherit this supersession; their active lesson is that skills cannot grant any unregistered or unauthorized write capability.

### Superseded synthetic-catalog design

### Requirements

- Add an approved MCP registry and guarded dispatcher exposing only the two read-only movie catalog tools below initially. Bundle a small versioned dataset of invented movie records with the application/fixture server. “IMDb-style” describes familiar record structure only: no IMDb affiliation, scraping, account requirement, or IMDb API integration is implied or required.
- Authenticate servers, constrain egress, enforce transport security for remote connections, and validate advertised tool definitions against approved pinned contracts. Treat contract drift as a denial requiring review.
- Validate model-proposed calls against the tool/MCP allowlists, schemas, semantic constraints, current permissions, remaining budgets, and emergency revocations before dispatch.
- Apply least-privilege credentials per tool or trust domain. Tool arguments cannot choose credentials, override identity, or escape allowed destinations.
- Bound response size, execution time, concurrent calls, and retries. Tool output cannot register tools, grant permission, approve an action, or modify policy.
- Treat movie synopses/descriptions as untrusted tool output. Use a separate controlled fixture variant containing injected instructions to demonstrate that catalog text cannot authorize actions, change policy, or grant tool access.

### Initial catalog contract

| Tool | Arguments and validation | Result |
| --- | --- | --- |
| `search_movies` | `query`: trimmed nonempty text, at most 120 characters and within global input-byte limits; `limit`: integer 1–10, default 5. Reject unknown arguments. | Deterministically ordered matching records, at most `limit`, plus a boolean `truncated`. Empty matches return an empty list. |
| `get_movie` | `catalog_id`: stable catalog ID matching `movie_` followed by six digits; reject unknown arguments. | One record, or a bounded structured `not_found` result for a well-formed absent ID. |

Records contain only validated fields: `id`, `title` (1–200 characters), `year` (integer 1888–2100), `genre` (a value from the bundled schema's fixed enumeration), `synopsis` (at most 1,000 characters), and `synthetic_rating` (number 0–10). Label ratings as synthetic in CLI output and documentation; they are not audience or IMDb ratings. Validate output schemas and enforce the global result-byte cap before adding results to context.

The initial interface has no pagination, offsets, or cursors; reject such arguments rather than accepting unbounded traversal. If pagination is added later, validate bounded page sizes and catalog-bound cursors under the same run budgets. Neither tool accepts executable SQL, arbitrary URLs, filesystem paths, or credential selectors as arguments. Query text is inert search data, never executed or dereferenced. Preserve all global permission, policy, schema, timeout, parallelism, and budget gates.

### Admin-only PUT: negative authorization exercise

The initial catalog service also exposes `PUT /movies/{catalog_id}` to prove that an existing endpoint can remain forbidden to the agent. An explicitly authorized test/admin principal may replace an existing synthetic record in an isolated writable fixture copy; validate the stable ID, full record schema, matching path/body IDs, and allowed synthetic-record scope. The bundled baseline remains reproducible and can reset the exercise. This endpoint has no IMDb or other real external effects.

The agent MUST NOT have PUT/update access. Enforce two independent boundaries: the agent dispatcher allows only `search_movies` and `get_movie`, and the catalog service authenticates the calling workload and denies writes from the agent workload identity. If an MCP adapter calls the catalog on the agent's behalf, its identity is also read-only. Authorization is checked before mutation on every request, including guessed endpoint URLs and direct HTTP outside MCP. A correctly authenticated agent receives HTTP 403; unauthenticated attempts receive HTTP 401. Hiding PUT from MCP discovery is not a security boundary.

No agent-held admin credential, dynamic write-tool registration, impersonation parameter, or approval-based escalation to PUT is allowed. Keep test/admin credentials outside the agent/MCP runtime and injected context. HTTP method overrides and alternative mutation routes must not bypass the same service policy. Human approval never grants this agent catalog-write permission.

Keep the Stage 5 approval-required action separate: an isolated simulated consequential ledger action may demonstrate exact-argument binding, one-use approval, receipts, and idempotency only when independently permitted by policy. It must not call or wrap the catalog PUT endpoint. Denial/cancellation causes no dispatch; ambiguous accepted operations require reconciliation before retry. This separate simulator does not expand the initial two-tool agent catalog surface.

### Acceptance

Movie search and stable-ID lookup succeed with correlated audit events. Test empty/no-match searches, maximum and excessive query length, invalid/absent IDs, result limits, rejected pagination/extra arguments, malformed outputs, and synthetic-rating labels. Unknown servers/tools, unsafe arguments, stale contracts, and cross-scope access fail before dispatch. A malicious synopsis cannot cause unauthorized tool use or policy changes.

Prove the PUT boundary with an authorized test/admin update of a synthetic record, followed by a read verifying the change. Then use a fresh fixture snapshot to test agent PUT denial via guessed URL/direct HTTP with its actual workload identity, a mocked MCP write proposal, forged admin claims, and a purported human approval. Direct-call tests deliberately exercise downstream authorization even though the real agent has no generic HTTP tool. Assert dispatcher denial for MCP proposals and service denial for direct requests; compare catalog state/version before and after each denied attempt to prove no mutation. Capture redacted actor/workload identity, method, stable resource ID, policy rule, decision, status, and correlation ID in audit evidence, without credentials or record payloads. Keep admin success evidence distinct from agent denial evidence.

When the separate Stage 5 approval simulator is introduced, test argument changes, duplicate approvals, retries, and at-most-once effects using receipts and idempotency keys. Re-run the agent PUT denial test after approval to prove that approval cannot elevate its catalog privileges.

## Stage 3 — Approved Markdown-defined skills

### Requirements

- Define a reviewed skill format containing stable ID, version, owner, purpose, required capabilities, allowed tools, input/output expectations, and Markdown instructions. Treat the entire file as untrusted content even after approval.
- Load only approved registry entries with pinned content digests. Reject unsigned or integrity-invalid bundles under the chosen registry trust mechanism, unknown versions, unsafe paths, oversized files, and unresolved references.
- Review skill updates like code: ownership, change diff, security review, tests, approval, versioned publication, and rollback. No runtime installation from user-provided URLs or arbitrary local paths.
- Skill content is instructions/data, not authority. Compute effective capabilities as the intersection of authenticated principal permissions, application policy, agent policy, and approved skill policy (including its declared capabilities). Skills cannot widen existing permissions, alter approval requirements, reset budgets, or write policy. Catalog PUT remains forbidden even if a skill claims human approval.
- Restrict included files to the approved bundle and validate each dependency. Deny unapproved files, external URL loads, escaping references, and loading another skill unless explicitly approved composition is supported. Composition must validate every child, intersect parent/child permissions, bound depth, and share the parent budgets, deadlines, and cancellation state; it never grants arbitrary network or filesystem access.
- Prevent integrity/revocation time-of-check/time-of-use gaps: verify and consume the same immutable skill/dependency bytes, not a mutable path re-read after verification. Bind use to approved version/digest and check current revocation at load and subsequent work gates under the existing policy freshness, propagation, and dispatch-fencing rules. Test replacement after verification and revocation during an active run; stale approval of an artifact cannot authorize new work.
- Record skill ID/version/digest with each run. Allow operators to disable a skill without redeploying the application.

### Acceptance

A pinned teaching skill works with the existing chat and approved tools. The user selected movie research and movie-night planning as the Stage 3 implementations. Rolling back a skill restores only a currently approved, non-revoked version with an audit trail.

Reuse the existing catalog, injection, memory, budget, and revocation fixtures for these six required skill-boundary cases; do not create weaker parallel enforcement paths.

| Case | Negative test and required enforcement evidence |
| --- | --- |
| 1. Forbidden catalog write | Skill requests catalog PUT/update, including purported human approval. Dispatcher denies the proposal; the existing direct-call fixture confirms independent catalog-service denial. Assert no mutation, including after approval. |
| 2. Policy override injection | Malicious Markdown or a movie synopsis requests a policy/identity override. Assert no permission change or unauthorized dispatch even when a deterministic model follows the injected instruction. A model refusal is not the security assertion. |
| 3. Unapproved loading | Skill tries an unapproved file, another unapproved skill, an external URL, or a reference escaping its bundle. Loader denies before content access or network fetch. If approved composition exists, verify depth bounds and permission intersection; it cannot create arbitrary file/network access. |
| 4. Memory boundary — Stage 4 | Once durable memory exists, skill requests another user's memory or a durable write without required consent. Memory-layer authorization denies access/write; assert no returned private records and no persisted change. Stage 3 keeps durable memory unavailable while retaining isolated Stage 1 session history; these durable-memory integration cases become mandatory in Stage 4, not dependent on model restraint. |
| 5. Recursive or repeated work | Attempt recursive skill invocation or repeated movie searches. Disallowed composition fails immediately; otherwise permitted invocations consume the same run counters, deadline, and cancellation state. Assert termination at configured limits, no counter reset, and no further dispatch after cancellation. |
| 6. Integrity and active revocation | Tampered, unknown, or revoked skills fail loading. Swap bytes after verification and revoke an active skill; verify immutable-byte use, rejection of the replacement, and blocking of subsequent work under the existing freshness/propagation bounds. Already accepted external effects retain the documented reconciliation limits. |

Each case MUST prove that disallowed side effects did not occur using backend invocation records, state/version comparisons, and loader/network spies as appropriate. Capture redacted run/principal references, skill version/digest, policy/revocation version, violated rule, decision, counters or cancellation timing, and downstream outcome. Do not log raw malicious content, credentials, or private memory. Reuse the protected audit requirements and verify the evidence, rather than accepting an explanatory response as proof.

## Stage 4 — Scoped, governed memory

### Purpose, lifetime, and storage choices

Separate **session conversation history**, introduced in Stage 1 under its short-term memory contract, from **consented durable user facts/preferences**, added in Stage 4 and retained across sessions under the stated scope and expiry rules. A storage/retrieval pattern does not decide purpose, consent, or lifetime. Graph and vector are options, not the only kinds of memory.

| Pattern eligible for explicit backend approval | Appropriate use and movie example | Tradeoffs and trigger to consider it |
| --- | --- | --- |
| Structured key/value or document records | Exact scoped facts, such as a user consenting to save “prefers comedy.” | Straightforward lookup, correction, and deletion; recommend starting here when exact facts suffice, without selecting a product. Reconsider when queries need more than known fields/keys. |
| Vector retrieval | Semantic similarity over approved memories, such as recalling a consented preference phrased differently in a later conversation. | Adds embedding generation, approximate matches, and index maintenance. Consider only when semantic-recall evaluations justify it; similarity is neither consent nor authorization. |
| Graph retrieval | Explicit approved relationships and bounded relationship queries. Actor/movie relationships generally belong to catalog domain knowledge, not automatically personal memory. | Adds node/edge modeling and traversal controls. Consider when multi-hop relationship questions are a real requirement, not merely because data can form a graph. |
| Hybrid combinations | Structured records plus justified vector and/or graph retrieval, with stable source-record links. | Adds synchronization, consistency, cost, and deletion complexity. Adopt only when measured needs cannot be met adequately by a simpler approved design. |

[Azure AI Search vector search](https://learn.microsoft.com/en-us/azure/search/vector-search-overview) and [Azure Cosmos DB for Apache Gremlin](https://learn.microsoft.com/en-us/azure/cosmos-db/gremlin/) are examples to evaluate, not chosen backends. Here “hybrid” means a combination of memory patterns; Azure AI Search also uses that term specifically for combined keyword/vector queries. Verify service/API identity support and SDK compatibility for any selected backend. [Agent Framework context providers](https://learn.microsoft.com/en-us/agent-framework/integrations/by-component/context-providers/) offer context integration patterns; integration alone does not establish governance or imply that every database API has a ready-made provider.

### Requirements

- Add a memory service whose storage and retrieval APIs require authenticated tenant, user, and session scope. Session memory is the default; broader user memory requires an explicit product policy and user control. Cross-tenant retrieval is prohibited.
- Keep the bundled movie catalog distinct from durable user memory. Searching or fetching a movie does not persist a user's preferences, history, or synopsis text as memory; any later durable preference write follows this stage's consent, scope, retention, and deletion rules.
- Enforce isolation in the storage/query layer before retrieval. Do not retrieve broadly and rely on the model to filter results. Include scope in cache keys, indexes, and background jobs.
- Treat recalled memory as untrusted evidence with provenance, timestamp, retention expiry, and confidence/source metadata. It cannot become authorization or override current policy. Detect or quarantine suspicious memory writes and prevent instructions from being promoted into trusted policy.
- Allowlist memory categories and minimize stored data. Do not store credentials, access tokens, secret-bearing tool output, hidden reasoning, or unrestricted transcripts. Require validation and appropriate consent before durable writes.
- Encrypt storage and transport, restrict service access, and define explicit retention periods, expiry enforcement, deletion workflows, and user-visible memory inspection/correction controls.
- Document deletion coverage for primary storage, indexes, caches, replicas, and backups. Define a deletion SLA and bounded backup expiry; ensure restored backups reapply deletion tombstones before serving data. Explain any separately retained audit metadata and its retention basis.
- A vector index or graph database alone is not complete governed memory. Apply isolation, consent, provenance, retention, deletion, authorization, and budgets to source records, embeddings, graph nodes/edges, and derived indexes/caches. Maintain source-to-derived-data mappings so correction, expiry, consent withdrawal, and deletion propagate; exclude ineligible data from retrieval immediately while physical cleanup follows the documented SLA. Reindexing or graph rebuilds must not resurrect deleted data.
- Maintain an administrator-approved per-environment/backend allowlist covering adapters, endpoints, identities, namespaces/indexes, permitted operations, and limits. Reject unapproved backends; the model and skills cannot supply arbitrary connection strings/endpoints or select credentials. Use typed bounded queries and application-owned query templates, never arbitrary model-supplied SQL/Gremlin or uncontrolled traversals. Enforce scope throughout vector queries and every graph hop, including cross-partition relationships; cap result count, traversal depth/fan-out, query time, and embedding/retrieval spend within shared budgets.

### Acceptance

Tests demonstrate tenant, user, and session isolation, including concurrent requests and cache reuse. Expired/deleted entries cannot be recalled after the documented SLA. Poisoned memory cannot authorize tools or expand scope. A deletion exercise verifies removal from active stores and records backup handling without retaining deleted content in the audit trail.

For each backend actually enabled, test rejection of unapproved endpoints/query operations, consent denial before persistence or derived-data creation, scope isolation through semantic results or graph paths, bounded queries, and correction/deletion across source and derived stores including rebuild/restore. Assert both immediate retrieval exclusion and cleanup within the SLA, with redacted evidence. Run Stage 3's memory-boundary case here. Only selected backends require implementation tests; this comparison does not require building vector, graph, or hybrid stores.

## Stage 5 — Production guardrails and emergency controls

### Requirements

Preserve all earlier gates and add authenticated operator controls, aggregate quotas, health monitoring, alerting, continuous evaluation, incident handling, and tested recovery. Model behavior alone MUST NOT decide whether a safety intervention occurs. Security policy failures must produce observable terminal or denied states rather than silent fallback to a less restricted mode.

### Four intervention layers

| Layer | Required behavior | Enforcement and scope |
| --- | --- | --- |
| Deny one call | Reject a single unsafe proposal before dispatch; return a bounded, safe denial. | Tool/memory/skill gate records reason and permits continuation only within remaining policy and budgets. Repeated denials may terminate the run. |
| Cancel a run | Stop scheduling model/tool work, cancel queued tasks, propagate cancellation to active operations, and suppress late results from causing follow-on actions. | Run controller records terminal state; already committed external effects require reconciliation or authorized compensation. |
| Disable a tool/server/skill without redeploy | Revoke the named capability centrally and block it in both new and existing runs. | Dispatch gates check current revocation state; queued calls are denied and affected active calls receive cancellation where supported. |
| Global kill switch | Stop new work and cancel active work across every active replica, tenant, and revision of the deployed application. | Admission gates deny starts, workers cancel active runs, queues stop dispatching, and model/tool adapters propagate cancellation. Management and audit access remain available for incident response. |

Configuration MUST specify a maximum revocation propagation delay and control-plane freshness interval, measured in release tests. On stale or unreachable control state beyond that interval, execution gates fail closed. Document the unavoidable gap for calls already accepted by external systems: cancellation is best effort at that boundary and cannot undo committed effects. Track such calls until reconciled. Global restart requires a separate authorized recovery action; process restart alone cannot clear the persisted kill-switch state.

Retain a manual stop path independent of the agent/API process, using separately authorized platform/operator controls to stop affected workloads or revoke their access when application cancellation is unavailable. Rehearse it with the application control path unresponsive; preserve audit access and reconcile accepted downstream effects. This supplements the four layers and does not require API Management.

### Required rogue scenarios

| Scenario | Signal | Automatic action | Operator control | Audit evidence | Recovery |
| --- | --- | --- | --- | --- | --- |
| Unauthorized tool | Proposed tool/server absent from allowlist, revoked, or outside current principal permissions. | Deny before dispatch; count violation and cancel run at the configured abuse threshold. | Disable tool/server or cancel run; use global stop if violations indicate broad compromise. | Run/scope IDs, policy version, tool identity, denial code, revocation version, and proof of no dispatch in test harness. | Correct approved configuration or identity assignment after review; rerun with fresh authorization and regression test. |
| Invalid/unsafe arguments | Schema failure, path traversal, forbidden destination, excess value, or ownership mismatch. | Deny call without echoing sensitive values; allow only bounded correction attempts charged to the same budget. | Cancel run, tighten argument policy, or disable the affected capability. | Schema/policy rule ID, redacted argument summary or protected digest, decision, and attempt counter. | Fix validated arguments or contract through review; repeat negative tests before re-enabling. |
| Loop/budget breach | Repeated call/turn pattern or exhausted input, token, turn, tool, retry, timeout, parallelism, or spend allowance. | Deny new reservations and terminate/cancel run; release pending reservations safely and flag unresolved external work. | Cancel run, lower tenant quotas, or activate global kill switch for systemic runaway behavior. | Ledger values, configured limits, loop signal, cancellation timestamps, active-call receipts, and final reason. | Reconcile spend/effects, fix loop cause, evaluate with reduced limits, and start a new run; never silently reset the failed run's budget. |
| Malicious tool/MCP output | Unexpected schema, oversize data, secret indicators, instruction injection, or attempted policy/identity override in returned content. | Reject structurally invalid output; quarantine detected malicious content, block its downstream use, and cancel or isolate the run according to policy. Deterministic authorization gates remain active even when detection misses an attack. | Disable server/tool, isolate its credentials, inspect protected evidence, and cancel affected runs. | Server/tool/version, response digest where safe, detector/rule outcome, quarantine reference, downstream denials, and operator action. | Investigate provider or contract compromise, rotate exposed credentials where warranted, validate sanitized output, and pass injection regressions before re-enable. |
| Approval-required consequential action | Allowed call has a consequential side-effect class and no valid argument-bound human approval. | Pause at an approval gate without dispatch; deny on rejection/expiry and cancel on run timeout. | Approve exact scoped action, reject it, cancel the run, or disable the capability. | Redacted consequence summary, normalized-argument digest, approver identity, decision/expiry, single-use consumption, and execution receipt if dispatched. | Obtain fresh approval after any argument/policy change; reconcile ambiguous outcomes before retry and require new approval for compensation when consequential. |

### Acceptance

All five scenarios are reproducible with deterministic fixtures. Tests prove all four intervention layers across multiple replicas, including queued tasks, active runs, late tool responses, control-plane outage, and process restart. Record observed cancellation and revocation latency against declared limits. Evidence distinguishes prevented dispatch from a cancellation request and from confirmed external cancellation. No exercise claims to reverse irreversible effects automatically.

## OWASP-aligned security coverage

Use the [OWASP Top 10 for Agentic Applications for 2026](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/), the [LLM Applications 2025 index](https://genai.owasp.org/llm-top-10/), and the [LLM Applications 2026 resource](https://genai.owasp.org/resource/owasp-genai-llm-top-10-2026/) as threat-model and evaluation inputs. The index still identifies its categories as 2025; do not reuse those numbers as 2026 rankings. The following is a thematic alignment, not a claim of exact category numbering or exhaustive compliance.

| Threat area | Required controls | Evidence |
| --- | --- | --- |
| Goal hijacking, prompt injection, and misplaced trust | Treat every external source as data; enforce policy outside the model; preserve provenance; gate every action. | Injection fixtures covering user, tool, retrieval, skill, and memory inputs. |
| Excessive agency, tool misuse, identity and privilege abuse | Least privilege, immutable authenticated scope, tool/MCP allowlists, semantic validation, human confirmation. | Unauthorized-operation, identity-spoofing, approval-binding, and cross-tenant tests. |
| Sensitive information disclosure and unsafe output handling | Secret exclusion, redaction, data minimization, scoped retrieval, parameterized downstream APIs, safe rendering. | Synthetic-secret canaries, log scans, output-consumer tests, and access-control tests. |
| Supply-chain compromise and unsafe skill/code execution | Locked/scanned dependencies, SBOM, reviewed registries, pinned digests, constrained network/runtime privileges. | Build attestations, scan results, skill tamper tests, and rejected contract drift. |
| Memory/context poisoning and retrieval weaknesses | Scoped storage filtering, source metadata, validated writes, expiry, deletion, and no policy derived from memory. | Poisoning tests, cache isolation tests, and deletion/restore drills. |
| Unbounded consumption and cascading failure | Atomic budgets, bounded retries/timeouts/parallelism, circuit breakers, backpressure, cancellation, and kill switch. | Load tests, failure injection, budget-race tests, and recovery drills. |
| Misleading outputs and unsafe human-agent interaction | Show uncertainty and provenance where useful, distinguish proposed from completed actions, and provide precise approval summaries. | Task-quality evaluations, receipt checks, and operator usability exercises. |

Maintain a threat model identifying assets, entry points, trust boundaries, abuse cases, owners, controls, and residual risks. Update it when adding a tool, skill, memory category, model, or hosting adapter. Multi-agent delegation is outside the initial scope; any future delegation must preserve identity, budgets, policy, and cancellation across agents.

## Selected Azure deployment and future portability

### Initial deployment contract

The initial release MUST implement and test only the selected Azure Container Apps deployment, plus local tests. Package the core as a reproducible artifact and use a thin Python API adapter for ingress, lifecycle, identity acquisition, telemetry, and cancellation. Keep approved configuration centrally managed, versioned, and auditable; do not embed environment secrets or hard-code resource IDs into prompts or skills. A Foundry hosted-agent adapter, deployment templates, and cloud validation are deferred, not initial acceptance requirements.

### Caller authentication and workload identity

Configure Container Apps ingress for HTTPS only (`allowInsecure` disabled), Entra Easy Auth, and Require authentication. Configure unauthenticated API requests to return HTTP 401 rather than an interactive sign-in redirect. Follow the official [Container Apps authentication](https://learn.microsoft.com/en-us/azure/container-apps/authentication) and [Entra configuration](https://learn.microsoft.com/en-us/azure/container-apps/authentication-entra) guidance, including the intended tenant/issuer, application registration, and allowed audience. The CLI uses an approved Entra client sign-in/token flow for this API; validate the chosen flow end to end and keep tokens out of prompts, logs, and command history. Do not embed a confidential client secret in the distributed CLI.

Easy Auth validates inbound caller authentication; application code still enforces per-user, tenant, tool, approval, and operator permissions. Derive caller identity only from the verified platform context on the protected ingress path, never request-body identities or arbitrary caller-supplied identity headers. Prevent alternate access paths from bypassing that boundary. Authenticated callers lacking permission receive HTTP 403. Authentication alone does not authorize every tenant user to use every operation. Keep health probes minimal and non-sensitive; any platform-required probe exception must not expose agent or operator endpoints.

Assign a dedicated Container Apps managed identity, distinct from deployment/operator identities, with least-privilege Azure RBAC for each supported downstream Azure resource. It represents the workload, not the signed-in CLI user. Use Key Vault references for required secrets, with rotation and access auditing. Never place secrets in prompts, logs, memory, source control, or skill files. For a downstream service without supported managed-identity access, explicitly review its scoped credential mechanism rather than assuming identity support.

Delegated downstream access on behalf of the caller is a separate optional requirement, not implied by Easy Auth or managed identity. If needed later, design consent, scopes, token audience, and an appropriate supported delegation flow; never forward the inbound API token indiscriminately. Application user/tenant authorization remains mandatory even when downstream calls use workload RBAC.

Authentication acceptance MUST cover valid authorized callers, anonymous/expired/wrong-audience/wrong-issuer tokens, spoofed identity headers, authenticated-but-forbidden tool/operator calls, and absence of a public API route bypass. Confirm the CLI handles 401 and 403 distinctly without leaking tokens. Confirm the runtime identity cannot publish policy, grant itself permissions, or clear a kill switch.

### Deployed networking requirements

Container Apps ingress and Entra Easy Auth protect inbound access; they do not by themselves impose outbound destination restrictions. Select and verify a supported topology and enforcement mechanism before declaring deployed egress acceptance complete. The official [networking overview](https://learn.microsoft.com/en-us/azure/container-apps/networking), [outbound control with user-defined routes](https://learn.microsoft.com/en-us/azure/container-apps/user-defined-routes), and [Azure Firewall integration guidance](https://learn.microsoft.com/en-us/azure/container-apps/use-azure-firewall) describe options and required dependencies. As reviewed on 2026-10-14, the documented UDR approach requires a workload profiles environment rather than legacy Consumption-only. Routing through an appliance alone is insufficient: configure and test its actual allow/deny rules. No firewall product, private-network topology, or additional Azure service is selected here; verify environment/region support and costs during that decision.

### Future hosting option

The [Agent Framework hosting guidance](https://learn.microsoft.com/en-us/agent-framework/hosting/) and [Foundry hosted-agent concepts](https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/hosted-agents) describe options to assess if the hosting decision is revisited. Preserve interfaces and tests that support such an assessment; do not promise a zero-change migration. Azure-hosted model selection remains independent of this hosting decision.

| Concern | Microsoft Foundry hosted agent — future option | Azure Container Apps — initial target |
| --- | --- | --- |
| Runtime | Host the approved agent package through a supported hosted-agent adapter; verify framework/runtime compatibility for the pinned release. | Run the same core in a pinned container image with health probes, resource limits, and controlled scaling. |
| Identity and secrets | Use managed identity and approved Key Vault integration supported by the selected hosting configuration; verify required permissions during deployment. | Use managed identity and Key Vault-backed secrets; restrict which identities can resolve references. |
| Observability | Integrate Foundry tracing, monitoring, and evaluations, including deployed-interaction evaluation where applicable. | Export correlated application telemetry and audit events to the approved Azure observability stack; run the same evaluation fixtures. |
| Controls | Ensure hosted lifecycle and entry points honor admission, cancellation, revocation, and kill-switch contracts. | Ensure all replicas, queues, revisions, and scale events honor the same contracts. |
| Portability proof | If selected later, implement its adapter and pass the common contract, isolation, approval, and emergency-control suite before declaring support. | Run the release suite locally and in Container Apps; explain host-specific limitations before release. |

For the future hosting option, Foundry provides [hosted-agent tracing](https://learn.microsoft.com/en-us/azure/foundry/observability/quickstarts/quickstart-tracing-hosted-agent?tabs=azd), [agent monitoring guidance](https://learn.microsoft.com/en-us/azure/foundry/observability/how-to/how-to-monitor-agents-dashboard?view=foundry), [agent evaluation guidance](https://learn.microsoft.com/en-us/azure/foundry/observability/how-to/evaluate-agent), and [evaluation of deployed interactions](https://learn.microsoft.com/en-us/azure/foundry/observability/how-to/cloud-evaluation-deployed-interactions). Trace capture MUST be reviewed for sensitive content before enabling it; follow the [trace data guidance](https://learn.microsoft.com/en-us/azure/foundry/observability/concepts/trace-data) and configure redaction, access, sampling, and retention explicitly.

Container Apps secret configuration MUST follow the [Azure Container Apps secrets guidance](https://learn.microsoft.com/en-us/azure/container-apps/manage-secrets), including supported Key Vault-backed references and identity access. Test secret rotation behavior for the chosen configuration.

Foundry hosted tracing integrates with Application Insights; initial Container Apps telemetry must be configured and tested independently. Foundry-specific dashboards, hosted tracing, and evaluations are optional integrations, not initial release dependencies. The reviewed hosted-tracing and deployed trace-evaluation documentation marks features as preview. Record feature status, region availability, SDK compatibility, and production support in the deployment compatibility manifest. Evaluation and monitoring are asynchronous evidence, not synchronous authorization controls. Deployed-interaction evaluation should use stored responses/traces without replaying consequential actions.

Application redaction does not guarantee that automatically generated SDK or platform spans are redacted. Inspect actual exports for seeded-secret leakage, disable message-content capture where supported, and restrict telemetry-reader roles. If safe content exclusion cannot be demonstrated, keep the affected tracing feature disabled or use only synthetic data. Required security audit remains separate and mandatory.

Azure API Management is excluded from the initial deployment. The CLI calls the authenticated Container Apps HTTPS ingress directly. If later needs justify a gateway, API Management is an optional alternative for supported request/concurrency/token policies; evaluate its configuration, operating effort, and current pricing for the actual workload before adopting it. Review [API Management policies](https://learn.microsoft.com/en-us/azure/api-management/api-management-policies) and the [rate-limit policy](https://learn.microsoft.com/en-us/azure/api-management/rate-limit-policy). Gateway controls do not replace application budgets, approval gates, or authorization; internal tool calls may not traverse that gateway.

Request-rate limits do not themselves enforce token or spend limits. If a gateway is added later, route the intended traffic through it and prevent direct bypass; keep shared application accounting because gateway counters are not an exact global spend ledger.

## Implementation deliverables

### Delivery milestones and definitions of done

Deliver these milestones sequentially in the same application, retaining earlier controls and regression tests. Each includes learner setup, a normal-use walkthrough, a negative exercise, expected evidence, and limitations. Begin with a runnable local fake-model/MCP baseline requiring no Azure credentials; hosted acceptance uses only the selected Container Apps HTTPS API and Entra Easy Auth. Open choices are prerequisites for the indicated capability, not reasons to block unrelated local work. No dates or effort estimates are implied.

| Milestone / concrete deliverable | Dependencies and open decisions | Definition of done | Review and evidence |
| --- | --- | --- | --- |
| 1. Chat and short-term session history | Establish package/CLI/core and explicit history configuration. Choose a specific approved model deployment before live-model tests; choose short-term backend/resumption behavior before hosted session acceptance. Offline RAM/fake-model work can proceed first. | Stage 1 chat, bounds, isolation, reset/expiry, summary-poisoning and applicable restart/concurrency tests pass. Local walkthrough works without credentials; hosted API demonstrates Easy Auth 401/403 and per-user permissions. | Review configuration and identity boundaries; retain test results, redacted session traces, and learner instructions distinguishing session context from durable memory. |
| 2. Movie MCP and forbidden agent PUT | Requires milestone 1 and the bundled synthetic catalog. Configure agent/MCP read-only identities and a separate test/admin principal. Select and verify network topology/control before deployed network acceptance; local fixtures need not wait. | Search/lookup work; admin PUT updates synthetic data; direct and mock-MCP agent PUT fail even with human approval, leaving records unchanged. Stage 2 contract tests and the five deployed network exercises pass before declaring hosted network acceptance. | Review tool/service permission separation and deployed rules; retain positive/negative results, state comparisons, and distinct redacted policy/network/service evidence with a learner bypass exercise. |
| 3. Approved Markdown skill and six boundary cases | Requires milestones 1–2. Use the selected movie research and movie-night skills with approved manifests and registry rules; composition/dependencies are disabled. | Approved skill works; Stage 3 cases 1–3 and 5–6 pass, including integrity races, active revocation, budgets, and forbidden PUT. Case 4 remains explicitly deferred until Stage 4; attempts to use unavailable durable memory already deny. | Review skill content, effective capability intersection, and immutable artifact handling. Record no-side-effect/audit evidence and document the deferred memory test without marking it passed. |
| 4. Governed durable memory | Requires milestone 3. Select durable backend and consented categories; confirm short-term/durable separation, retention/deletion values, and any derived-index design before enabling persistence. | Stage 4 isolation, consent, bounded retrieval, correction, deletion/restore, and enabled-backend tests pass. Complete Stage 3 case 4 at the memory layer. Vector/graph/hybrid implementations are not required unless selected. | Review backend allowlist, lifecycle and data-flow design; retain isolation and deletion evidence across source/derived stores and teach inspection/forget controls. |
| 5. Production containment and operator recovery | Requires prior milestones and selected shared control-state hosting with demonstrated atomicity/freshness. Resolve remaining production network, identity, audit, and operational objectives; provision a separate operator identity inaccessible to agent/MCP workloads. | All stage/scenario regressions and deployed network gates pass. Demonstrate four shutdown layers, persistent stop/recovery, and the independent manual Azure stop drill below across all active revisions. Hosted global emergency tests must pass before production readiness is claimed. | Review incident/recovery runbooks and residual limitations. Retain revision inventory, operator/control audit, acknowledgements, observed timing, downstream reconciliation, canary recovery, and a learner/operator exercise report. |

For the final drill, deliberately make an isolated synthetic worker unresponsive to application cancellation. A separately authenticated operator must use Azure control-plane operations, outside the agent/API process, to stop or isolate every affected worker across all active revisions and prevent replacement work while stop state persists. Inventory active revisions/replicas and verify the resulting state rather than treating a submitted stop request as completion. Restart/recovery must not clear the persisted kill state or revive queued actions/approvals; reconcile already accepted downstream work, then require explicit authorized recovery and a clean canary. Test/admin/operator credentials are never available to the agent. This drill measures observed containment time; it does not guarantee instant termination or undo completed effects.

The sequence keeps local lessons small and adds hosted evidence as dependencies become available. A local-only simulator is an alternative for early teaching but cannot satisfy deployed network or production emergency gates. Foundry remains a future hosting alternative; a change would require host-specific revalidation. Automated Azure Monitor/Automation escalation is an optional future extension if incident frequency or response-time evidence justifies its added permissions and operational complexity; it is not required for the manual stop milestone. Revisit the open model, skill, memory, network, and control-state choices using the decision register rather than silently expanding scope.

The subsequent implementation MUST supply one installable Python package with a documented CLI, dependency lockfile, reproducible non-root container build, configuration schemas, credential-free examples, and separate development/test/production profiles. Production profiles reject debug bypasses. Choose and record tested Python and Microsoft Agent Framework versions using the [official framework overview](https://learn.microsoft.com/en-us/agent-framework/overview/?pivots=programming-language-python) and version-specific API documentation.

Keep explicit modules/interfaces for orchestration, model access, guarded MCP dispatch, policy, approvals, run supervision, skills, memory, audit, and host adapters. Raw MCP/model clients must not expose a path around mandatory gates. Provide an injectable clock and fake model, fixture MCP service, simulated consequential ledger, and local control/audit stores for offline tests. Default exercises must not need production credentials or real side effects.

Document CLI operations for chat/stage selection, skills, memory inspection/deletion, run status/cancellation, and a separately authorized operator command group for disable/enable/global stop/recovery. Supply deployment templates and setup/cleanup instructions for the Container Apps HTTPS Python API, Entra Easy Auth configuration and CLI authentication setup, a compatibility manifest, least-privilege role assignments, and runbooks for all four intervention layers. Foundry deployment artifacts are deferred until that option is explicitly selected. Teaching chapters extend this shared implementation rather than copy it into five applications.

## Production operations

- **Release controls:** require code/policy review, dependency and image scans, reproducible builds, threat-model updates, acceptance evidence, staged rollout, and rollback artifacts. Changes to prompts, models, skills, and tool contracts trigger relevant regressions.
- **Telemetry:** measure latency, errors, denials, approval outcomes, tool activity, budget utilization, estimated spend, cancellation latency, memory access/deletion, configuration freshness, and policy propagation. Distinguish model/provider faults from policy decisions.
- **Safe redacted logs:** omit raw prompts, responses, tool payloads, and memory by default. Use structured reason codes and minimal metadata. Apply redaction before export, protect identifiers, and prevent log injection. Exceptional content capture requires restricted access, documented purpose, and short retention. Do not expose hidden reasoning.
- **Audit:** use a restricted, tamper-resistant sink for admission, authorization, approval, dispatch, completion, memory changes, policy publication, emergency intervention, and recovery. Include UTC timestamp, actor/scope references, run/trace IDs, policy version, capability version, decision, and result. Avoid sensitive argument values; hashes may also require protection. For consequential actions, inability to persist required audit evidence denies dispatch.
- **Reliability:** bounded retries with backoff and jitter, circuit breakers, queue limits, backpressure, health checks, graceful shutdown, and explicit degraded modes that retain all security gates. Never retry non-idempotent actions blindly.
- **Incident response:** assign on-call and security owners, alert on repeated denials and runaway usage, preserve minimal evidence, contain using the four layers, reconcile external effects, rotate affected credentials, and record remediation. Exercise runbooks on the selected Container Apps deployment; repeat host-specific validation if another runtime is adopted later.
- **Recovery:** require an authorized operator to verify incident resolution, configuration integrity, queued-work disposition, and relevant regressions before re-enabling. Start fresh runs with fresh authorization; do not replay stale approvals. Roll out gradually and watch recurrence metrics.
- **Operational objectives:** before production, record numeric availability/latency objectives, alert thresholds, budget defaults, cancellation and revocation deadlines, retention/deletion SLAs, and audit delivery objectives. An unset required value blocks production release.

## Security exercises

Use synthetic identities, seeded fake secrets, mock destructive endpoints, and isolated test resources. No exercise sends real sensitive data or performs irreversible production actions.

| Exercise | Learner task | Expected result |
| --- | --- | --- |
| Chat injection | Ask the model to ignore policy and reveal credentials or invoke an absent tool. | No secrets or tool execution; safe response and bounded run. |
| Tool abuse | Propose unknown tools, unsafe paths, forbidden destinations, and forged tenant IDs. | Deterministic pre-dispatch denials with useful redacted evidence. |
| Forbidden catalog PUT | Verify an authorized test/admin PUT, then attempt agent writes through guessed URLs/direct HTTP, mock MCP proposals, or claimed approval. | Reads work; admin updates only synthetic records; dispatcher and downstream authorization deny agent writes, leave catalog state unchanged, and emit redacted evidence. |
| Approved network path | Run approved MCP movie search/lookup from the deployed application with the actual read-only workload identities; exercise required model, identity, DNS, configuration, secrets, and telemetry dependencies. | Authorized reads and operational dependencies work under the deployed restrictions; no general internet exception is needed. |
| Unapproved outbound destination | Use a controlled probe from each agent/MCP runtime network context to contact a test-owned destination outside the allowlist, bypassing the dispatcher for this test only. | Deployed egress enforcement blocks the connection; network rule evidence identifies the denial. A dispatcher mock or an unrelated connection failure is insufficient. |
| Reachable host, forbidden operation | Directly PUT to the reachable catalog with the actual agent/MCP read-only identity, including a guessed endpoint and purported approval. | Service authorization denies the operation while allowed reads still work. Catalog state/version is unchanged; service denial evidence is distinct from a network block. |
| Endpoint/redirect escape | Supply an unapproved endpoint in model/tool input, then have a controlled approved test endpoint redirect to an unapproved destination. | Application rejects endpoint substitution; redirects are disabled or each hop is revalidated. Deployed egress independently prevents escape; no credential forwarding or target connection occurs. |
| Internal MCP ingress bypass | Probe the internal/private MCP service from outside its permitted network and make an unauthenticated call from a permitted internal test client. | No public alternate MCP ingress exists; the internal unauthenticated request is denied by service authentication. The protected API cannot be bypassed to obtain tools. |
| Hostile MCP response | Return a synthetic movie synopsis containing exfiltration or approval-bypass instructions; also return malformed/oversized catalog records. | Unsafe structure rejected; embedded instructions cannot bypass authorization even if screening misses them. |
| Skill tampering | Modify a pinned skill, include a path escape, or request broader permissions. | Integrity/path failures deny loading; permission intersection prevents escalation. |
| Memory poisoning and isolation | Store a forged instruction, recall as another user/tenant/session, then delete and restore from backup. | No scope leakage or policy promotion; deletion tombstones survive restore. |
| Runaway execution | Trigger loops, retry storms, and concurrent budget reservations. | Limits hold atomically; run terminates with reconciled ledger. |
| Approval race | In the separate Stage 5 simulated consequential ledger, alter arguments after approval, reuse approval, revoke permission, or lose the execution response. | No stale/reused authorization; receipts and idempotency prevent duplicate effects; ambiguous effects reconciled before retry. Catalog PUT remains forbidden to the agent even with approval. |
| Emergency response | Disable a capability during execution, partition the control plane, then activate global stop across replicas. | Bounded propagation, fail-closed stale state, active cancellation, persisted stop, and controlled recovery. |

## Testing, evaluation, and release acceptance

Use unit tests for policy and schema checks, budget accounting, approval binding, redaction, scope derivation, and cancellation state transitions. Use integration tests with mock model/MCP services and storage to verify full runs and absence of forbidden dispatch. Use concurrency and fault-injection tests for budget races, duplicate requests, late responses, control-plane partitions, unavailable audit storage, and restart behavior.

Network acceptance MUST additionally run the five network exercises above in the configured Container Apps environment, covering agent and MCP runtime paths and active revisions. Save deployed configuration versions and correlated, redacted application-policy, network-rule, and downstream-service evidence: actor/workload reference, destination identifier, operation, decision/rule, time, and outcome, with no tokens, payloads, or sensitive URL query strings. Distinguish a pre-dispatch denial, blocked connection, service 401/403, and successful authorized read; verify catalog state for denied writes. Repeat after network/identity changes. Mocked dispatcher tests alone cannot satisfy this gate, and an open topology decision must be resolved before declaring it passed.

Maintain a versioned adversarial test suite covering every external-input surface and every rogue scenario. Evaluate task completion, answer grounding where applicable, unsafe-action attempts, unauthorized dispatches, leakage canaries, false-positive denials, budget adherence, and containment latency. Use deterministic assertions for authorization and side effects; model-based graders may supplement qualitative review but cannot certify security gates. Track attack attempts separately from successful violations.

Run contract tests locally and on the selected Container Apps deployment. Foundry validation becomes required only if a later release adds that hosting option. Keep deterministic fixtures separate from controlled live-model evaluations so tests remain reproducible while also detecting model behavior changes. Record model/version/configuration, policy/skill/tool versions, dataset version, seed where supported, environment, scores, and failures. Re-evaluate after model, prompt, dependency, skill, policy, or tool changes. Use production monitoring and sampled, privacy-reviewed evaluation to detect drift.

A release MUST provide:

1. A runnable, documented stage progression using CLI -> HTTPS Python API on Container Apps -> shared Microsoft Agent Framework core, with Entra Easy Auth and application permission tests passing and earlier controls retained at every stage.
2. Passing acceptance evidence for all five stages, all five rogue scenarios, and all four intervention layers.
3. Zero unauthorized dispatches, approval bypasses, cross-scope memory reads, or synthetic-secret leaks in the release suite. Passing a finite suite is necessary evidence, not proof of universal safety.
4. Verified finite budgets, no over-admission under tested concurrency, and cancellation/revocation results within declared limits on Container Apps, including multiple replicas and overlapping revisions.
5. Reviewed lockfile, SBOM, scan results, configuration/skill provenance, identity/RBAC configuration, and Key Vault access evidence.
6. Tested redaction, audit integrity/access, retention/deletion, backup restore handling, and incident/recovery runbooks.
7. Recorded quality and false-positive thresholds approved before evaluation; unresolved exceptions, limitations, and residual risks have named owners and remediation dates.

## References

These official source pages were checked on 2026-10-14 during specification review. The Agentic Applications landing page was accessible, but its linked download timed out; the thematic mapping does not claim a line-by-line audit of that download. Implementation must validate version-specific behavior before release.

- [OWASP Top 10 for Agentic Applications for 2026](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/)
- [OWASP Top 10 for LLM Applications](https://genai.owasp.org/llm-top-10/)
- [OWASP GenAI LLM Top 10 2026](https://genai.owasp.org/resource/owasp-genai-llm-top-10-2026/)
- [Microsoft Agent Framework overview, Python](https://learn.microsoft.com/en-us/agent-framework/overview/?pivots=programming-language-python)
- [Foundry hosted-agent tracing quickstart](https://learn.microsoft.com/en-us/azure/foundry/observability/quickstarts/quickstart-tracing-hosted-agent?tabs=azd)
- [Foundry agent monitoring dashboard](https://learn.microsoft.com/en-us/azure/foundry/observability/how-to/how-to-monitor-agents-dashboard?view=foundry)
- [Evaluate an agent](https://learn.microsoft.com/en-us/azure/foundry/observability/how-to/evaluate-agent)
- [Evaluate deployed interactions](https://learn.microsoft.com/en-us/azure/foundry/observability/how-to/cloud-evaluation-deployed-interactions)
- [Azure Container Apps secrets](https://learn.microsoft.com/en-us/azure/container-apps/manage-secrets)
- [Azure API Management policies](https://learn.microsoft.com/en-us/azure/api-management/api-management-policies)
- [Azure API Management rate-limit policy](https://learn.microsoft.com/en-us/azure/api-management/rate-limit-policy)
- [Foundry trace data guidance](https://learn.microsoft.com/en-us/azure/foundry/observability/concepts/trace-data)

- [Container Apps built-in authentication](https://learn.microsoft.com/en-us/azure/container-apps/authentication)
- [Container Apps Microsoft Entra authentication](https://learn.microsoft.com/en-us/azure/container-apps/authentication-entra)
- [Hosting Agent Framework applications](https://learn.microsoft.com/en-us/agent-framework/hosting/)
- [Foundry hosted-agent concepts](https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/hosted-agents)
