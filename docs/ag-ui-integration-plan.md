# AG-UI integration plan

**Status:** implementation started on `feat/ag-ui-integration`. The backend exposes `POST /ag-ui` using the official Python event models and encoder. A local React/Vite client now supports Entra bearer-token entry, session creation/resume, chat, stop, and reset. Browser-based Entra sign-in, hosted origin configuration, and incremental token streaming remain planned.

## Goal

Give the movie assistant a browser UI using AG-UI’s event-based, bidirectional agent ↔ user protocol. Keep authentication, owner-scoped sessions, model/tool policy, memory consent, budgets, audit and cancellation in the existing Python service. AG-UI is the transport and interaction contract, not an authorization layer.

## Current starting point

- The agent is a Python/FastAPI service in `apps/agent`; it has authenticated session create/status/chat/reset/cancel routes.
- Chat is currently request/response. `Service.chat` runs the existing guarded model/tool loop and commits session history under a revision/run fence.
- The hosted CLI uses Entra bearer tokens. Optional shared Blob sessions and shared safety controls support hosted operation.
- The local web frontend is `apps/web`; hosted deployment and browser sign-in are not configured yet. The terminal interface and CLI remain available.
- Existing standalone endpoints handle explicit movie reads, memory operations, and approval simulations. Those actions must not be made implicitly available merely because the new client uses AG-UI.

## Proposed first slice

Implement an authenticated AG-UI-compatible HTTP streaming endpoint in the existing FastAPI service and a small React browser client. Use AG-UI’s standard run lifecycle, text-message and error events first. The server should adapt the current governed run to protocol events; it must not create a second model/tool loop. The endpoint emits lifecycle events and one completed text delta through the existing `Service.chat`; it does not yet provide incremental token delivery. The first browser client is under `apps/web` and holds the bearer token only in tab memory.

The initial vertical slice should support:

1. Entra sign-in and bearer-token forwarding from the browser client.
2. Create/resume an owned session and display its stable session ID and revision.
3. Submit a user message and stream assistant text while the run is active.
4. Cancel the active run and show completion, cancellation, or a sanitized error.
5. Preserve existing skill selection only as an explicit, validated request option.

## Work sequence

### 1. Confirm protocol and runtime compatibility

- Read the AG-UI event specification and current Python/React SDK guidance before selecting package versions. Pin compatible versions in the respective lockfiles.
- Confirm whether the current Microsoft Agent Framework version has a supported AG-UI adapter. Prefer an adapter only if it can invoke the existing `Service` policy and commit path; otherwise build a narrow adapter at the FastAPI boundary.
- Decide the browser app location and build tooling after inspecting repository conventions; add a dedicated `apps/web` package if no existing frontend is present.

### 2. Define the server protocol adapter

- Add a dedicated AG-UI route that authenticates exactly as existing API routes do and resolves the session through the existing owner check.
- Validate message size, event types, session ID, revision and optional skill fields. Reject unsupported frontend tool/state commands.
- Map lifecycle and assistant text to AG-UI events. Do not emit prompts, raw model reasoning, credentials, private memory values, or unrestricted tool payloads. Tool activity may be represented by safe status labels and bounded public movie results where the existing product already permits their display.
- Make the run ID, session ID and revision relationship explicit. Preserve current fencing, budgets, audit, and history commit semantics. On disconnect/cancel, cancel the governed run and ensure uncommitted history is discarded.
- Return protocol-compliant content types, framing, terminal events and sanitized error behavior; support CORS only for configured UI origins.

### 3. Build the browser UI

- Add a basic chat screen with streaming transcript, pending state, cancel, retry after recoverable transport failure, and session reset.
- Use the AG-UI client SDK if it supports the selected server contract; keep the UI’s state minimal and derive durable conversation state from the server session.
- Do not put Entra client secrets in the browser. Use the approved public-client flow and existing API audience/scope. Apply secure token storage and origin restrictions consistent with the deployment model.
- Show explicit controls for skills and any memory actions. Keep memory inspect/save/correct/delete on their dedicated APIs and require the existing consent semantics.

### 4. Verify behavior and security boundaries

- Protocol conformance: ordered lifecycle events, text deltas, one terminal event, malformed request rejection, disconnect and cancellation behavior.
- Session safety: owner isolation, stale revision conflict, concurrent run rejection, reset/cancel fencing, and no partial history commit after interrupted runs.
- Governance: model/tool budgets, kill switch/capability disable, audit availability, skill allowlist, and memory consent remain enforced through the AG-UI path.
- Browser boundary: origin/CORS policy, token audience, no credential leakage, XSS-safe rendering, and no unintended HTML execution.
- Exercise both deterministic fake mode locally and an authorized hosted canary. Record protocol versions, exact commands, environment and limits in versioned evidence.

## Phased rollout

| Phase | Deliverable | Exit condition |
| --- | --- | --- |
| 0. Design spike | Confirm current AG-UI events, SDK compatibility, auth flow and deploy topology | Small end-to-end fake-mode proof; no governance bypass identified |
| 1. Text streaming | Authenticated stream route and browser chat | Session ownership, revisions, cancellation and terminal events verified |
| 2. Existing agent features | Explicit skills, safe movie tool status/results, reset and supported errors | Feature behavior matches existing CLI/API semantics |
| 3. Hosted readiness | UI hosting, Entra registration/origin config, telemetry and operator runbook | Authorized canary plus security and operational review |
| 4. Optional AG-UI capabilities | Human approval interrupts, shared state or richer multimodal UI, if product needs justify them | Separate design, threat review and acceptance criteria for each capability |

## Explicitly deferred

Do not include generative UI, arbitrary frontend-executed tools, agent-writable shared state, raw chain-of-thought, voice/media, or sub-agent composition in the first release. AG-UI supports a wider set of interaction patterns, but each would require new product contracts and threat analysis. The initial UI should represent the current assistant behavior faithfully.

## Decisions to resolve during Phase 0

- Whether the current Agent Framework exposes a compatible AG-UI adapter at the installed version, versus a custom event adapter around `Service`.
- UI package/build framework and hosting location.
- Whether streaming runs can be driven from a streaming model API without changing budget reservation, cancellation, and final commit semantics. If not, start with evented status plus a final text event and treat token streaming as a later improvement.
- Entra browser redirect origins, API scope, and hosting topology.

## Source

AG-UI describes itself as a lightweight, event-based, bidirectional protocol connecting an agent backend and user-facing applications. Its overview distinguishes AG-UI from MCP (agent ↔ tools/data) and A2A (agent ↔ agent), and lists streaming chat, cancellation/resume, human interrupts, shared state and other capabilities. This plan uses only the text interaction and cancellation subset initially: [AG-UI overview](https://docs.ag-ui.com/introduction).
