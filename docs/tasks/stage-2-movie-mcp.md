# Stage 2 task — Movie catalog MCP and forbidden writes

## Goal and outcome

Extend [Stage 1](stage-1-chat.md) with approved read-only movie tools and demonstrate independent service authorization. Implement the [specification's Stage 2 and network contracts](../secure-agent-teaching-spec.md), following [shared conventions](README.md).

## Scope

A small bundled synthetic IMDb-style catalog, guarded MCP dispatcher, and admin-only HTTP PUT exercise. There is no IMDb affiliation, scraping, account, or API integration.

Current implementation status: the versioned catalog, strict read-only dispatcher, FastMCP stdio and hosted HTTP server, and separate local admin-only PUT adapter are in the `movie-catalog-mcp` workspace package. The agent calls the pinned read tools from explicit CLI commands, an authenticated API route, and an opt-in model tool loop. The MCP is deployed as an internal second app in the existing Container Apps environment with separate identity and Entra application-role authentication. Stage 2 is **in progress**, not accepted: hosted model-selected reads and private-ingress/authentication checks passed, while deployed admin authorization and controlled-egress evidence remain pending. See [Stage 2 validation](../stage-2-validation.md).

## Verified status — 2026-10-18

| Area | Result | Evidence and limit |
| --- | --- | --- |
| Local FastMCP and catalog contracts | Passed | Only `search_movies` and `get_movie` are registered; local read, malformed-input/result, revocation, and denied-write tests pass. |
| Hosted agent → internal MCP read | Passed | Agent revision `ca-az-maf-stage1--0000009` used its managed identity and `Catalog.Read` application role; `get_movie(movie_000103)` returned `200`. |
| Ingress and unauthenticated caller | Passed | Public request to the internal MCP hostname returned `404`; a no-token request from inside the agent container returned `401`. |
| Agent write proposal | Passed at agent boundary | Hosted `put_movie` proposal returned `403` before MCP dispatch. This does **not** prove a direct PUT to a deployed catalog service is denied. |
| Stage 1 regression | Passed | Live Foundry chats, stale-revision rejection, reset, and unauthenticated ingress behaved as before. |
| Model-selected tool invocation | Passed for one hosted lookup | Revision `ca-az-maf-stage1--0000010` returned a live answer after exactly one managed-identity-backed MCP read of `movie_000103`. The loop permits only two sequential read attempts per run. |
| Deployed admin and direct-identity PUT | Pending | The separate admin PUT adapter has local authorization tests but is not deployed with independent authentication. |
| Controlled outbound network | Pending | The existing environment has no VNet or workload profiles, so an egress-rule block cannot be demonstrated there. |

The next implementation work is to deploy the admin test surface with separate authorization and run the remaining network exercises in an environment that supports controlled outbound routing. Do not treat ingress `401`/`404` or the agent's `403` as proof of an outbound firewall rule or downstream PUT denial.

## Prerequisites and dependencies

- Stage 1 core, scope, budgets, cancellation, audit, and hosted auth contracts.
- Separate read-only agent/MCP workload identities and an authorized test/admin principal whose credentials never enter agent context/runtime.
- Approve server/tool contracts and select network topology/control before deployed network acceptance. Local fixtures can proceed first; no firewall product is implicitly selected.

## Ordered work checklist

1. [x] Bundle versioned invented records with stable IDs, title, year, genre, short synopsis, and clearly labeled synthetic rating. Keep a reproducible baseline and isolated writable test copy.
2. [x] Implement only `search_movies(query, limit)` and `get_movie(catalog_id)` as agent read operations. Enforce spec schemas: trimmed query 1–120 characters, limit 1–10/default 5, and `movie_` plus six digits. Reject pagination/extra arguments. No arbitrary SQL, URL, filesystem path, or credential selector.
3. [x] Validate outputs: title 1–200 characters, year 1888–2100, fixed genre enum, synopsis at most 1,000 characters, rating 0–10, global byte cap, bounded not-found response, and deterministic search ordering/truncation flag.
4. [ ] Gate every dispatch on approved server/tool/version, strict schema and semantic validation, caller permission, current revocation, and remaining budgets. Authenticate services, constrain credentials/egress, and reject contract drift.
5. [ ] Implement `PUT /movies/{catalog_id}` only for authorized test/admin replacement of existing synthetic records. Validate matching path/body IDs and full schema before mutation. Downstream service denies agent and MCP identities, including direct calls; discovery visibility is not authorization.
6. [ ] Add malicious synopsis, malformed/oversized result, forged identity, and mock write-proposal fixtures. No generic HTTP/shell tool or dynamic write registration may bypass the dispatcher.
7. [ ] Configure and execute all five deployed network checks below from actual runtime contexts. Approved reads and private ingress/authentication have passed; outbound blocking, direct downstream PUT, and hosted redirect escape remain open. Inventory allowed model, identity, DNS, configuration, secrets, telemetry, registry/platform, and catalog dependencies.
8. [ ] Document layered evidence and pass retained Stage 1 regressions. Stage 1 regression passed on the updated agent; finish the remaining Stage 2 evidence before closing this item.

## Acceptance criteria

- [ ] Authorized search/read succeeds; no-match, invalid/absent ID, excessive query/result limits, malformed output, and unknown tools are handled without unsafe effects.
- [ ] Authorized test/admin PUT succeeds and subsequent read confirms it. Direct agent/MCP PUT, guessed URL, mock MCP write, forged admin claims, and purported human approval all fail; catalog state/version remains unchanged for each denial.
- [ ] Permission precedes approval: approval cannot grant PUT. No admin credential is held by agent/MCP workers; method overrides/alternative mutation paths do not evade service policy.
- [ ] All five deployed network exercises pass with evidence, not just dispatcher mocks: approved MCP reads/dependencies work; a test-owned unapproved destination is blocked by egress rules; reachable catalog host denies actual-identity PUT; endpoint/redirect escape is rejected; private/internal MCP has no public unauthenticated bypass and denies unauthenticated internal callers.
- [ ] Redirects are disabled or every hop is revalidated before connection. Deployment verification distinguishes network blocks from service 401/403 and dispatcher denials. Easy Auth/ingress alone is not described as outbound enforcement.

## Security and negative scenarios

Exercise valid-shaped synopsis injection that a fake model obeys; authority must remain unchanged and unauthorized effects must be absent. Test stale contracts, cross-scope arguments, loop/retry bounds, and credential forwarding on redirects. Egress destination rules generally do not distinguish GET from PUT at one host: prove downstream authorization separately. Any probe that bypasses the dispatcher is a controlled test, never an agent tool.

## Documentation and evidence to produce

- Catalog schema/provenance, read-only tool tutorial, admin-versus-agent demonstration, network decisions and rule versions.
- Before/after state, backend invocation counts, and correlated redacted policy/network/service evidence with identities, rules, method, safe resource identifiers, and outcomes; omit payloads/tokens.
- Local and hosted test commands/results. Record deployed tests as pending until actually run; they are mandatory before production.

## Out of scope

Agent catalog writes even with approval, real external writes, IMDb integration, arbitrary queries/HTTP, user-memory persistence, API Management, and an implicitly selected network product. A separate Stage 5 permitted ledger simulator teaches approval; it must not wrap PUT.
