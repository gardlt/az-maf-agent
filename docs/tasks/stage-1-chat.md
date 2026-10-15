# Stage 1 task — Chat and bounded session history

## Goal and outcome

Deliver the first runnable slice of the [specification](../secure-agent-teaching-spec.md): one Python CLI and Microsoft Agent Framework core with safe multi-turn chat and explicit short-term history. Follow the [shared task conventions](README.md).

## Scope

Local deterministic fake-model mode, configured live-model adapter, bounded sessions, and the Container Apps/Easy Auth hosted API. Session history starts here; durable user memory does not.

## Prerequisites and dependencies

- No preceding stage. Local work requires no cloud credentials.
- Select and pin supported Python/Agent Framework versions and an API framework; document compatibility.
- Choose the actual approved model deployment only before live tests; resolve it through configuration, never source-code constants.
- Decide session resumption/backend behavior before hosted session acceptance. RAM is adequate for an offline single process; shared TTL storage or validated rehydration needs a separate decision for replicas.

## Ordered work checklist

1. [ ] Establish one installable package, CLI, core/model adapters, validated configuration, credential-free examples, dependency lock/integrity checks, and test fixtures with injectable clock and deterministic fake model.
2. [ ] Implement run identity/scope, policy version, budget ledger, cancellation, safe output rendering, stable errors, and redacted audit. Adopt all applicable finite limits from the spec; missing policy or required limits denies admission.
3. [ ] Implement explicit Python `AgentSession`/history-provider configuration. Enforce authenticated tenant/user/session ownership on creation, load, update, reset, and resume.
4. [ ] Bound history bytes/tokens, idle TTL, maximum lifetime, and processing deadlines. Add reset/expiry and prevent late writes from resurrecting cleared history. Trim/summarize within the same budgets, preserving tool-message structure for later stages.
5. [ ] Keep summaries untrusted and minimize sensitive content. Store authoritative permissions, approvals, cancellation, and counters outside history; reset/compaction cannot reset aggregate security limits or promote content into durable memory.
6. [ ] Add HTTPS Python API and Container Apps deployment instructions/configuration with Entra Easy Auth, authenticated-only ingress, HTTPS enforcement, API 401 responses, and application 403 permission checks. Protect trusted identity headers from alternate ingress paths.
7. [ ] Separate caller auth from dedicated workload identity/RBAC; use approved secret resolution without exposing credentials to CLI prompts/logs. Validate session concurrency/resumption across replicas if enabled; never rely on sticky routing for correctness.
8. [ ] Run local and hosted checks separately and produce learner material and decision evidence.

## Acceptance criteria

- [ ] Local multi-turn chat runs with the built-in fake model and no Azure credentials; only one approved configured model is used in live mode.
- [ ] Oversized input, missing limits, context overflow, retry exhaustion, timeout, token/spend exhaustion, and cancellation stop at the prescribed bounds without bypasses.
- [ ] Session/user isolation, reset, TTL expiry, context reduction, and poisoned summaries pass. Restart either loses context explicitly or resumes it correctly under the chosen contract.
- [ ] Shared/resumable session tests cover duplicate requests, concurrent writes, replica changes, and reset races; no leakage, history resurrection, or aggregate counter reset occurs.
- [ ] Hosted authorized caller succeeds; missing/expired/wrong-issuer/wrong-audience tokens and spoofed identity headers fail. Authenticated forbidden actions return 403. No public alternate API route bypasses authentication.
- [ ] Tools, skill execution, and durable memory are disabled; chat content is not persisted by default, including logs. Any selected TTL persistence is explicit and governed.

## Security and negative scenarios

Inject instructions to reveal seeded fake secrets, change identity/policy, or invoke absent tools. Assert zero external tool effects and no secret leakage even when a fake model follows malicious text. Test malformed provider responses, unavailable required policy, terminal control characters, and history that claims a past approval. Model output never supplies authority.

## Documentation and evidence to produce

- Local/hosted setup, normal chat, cancellation/reset walkthrough, expected failures, and restart limitations.
- Version/configuration manifest, auth boundary review, model/session decisions with alternatives, and redacted test/audit results.
- Dependency/secret scan evidence and reusable fixtures for [Stage 2](stage-2-movie-mcp.md).

## Out of scope

Durable memory, MCP execution, skills, web UI, multi-model routing, Foundry hosting, API Management, and claims of production readiness. These tasks do not select a model or session-store product on the user's behalf.
