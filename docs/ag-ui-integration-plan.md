# AG-UI integration plan

**Status:** the initial local vertical slice is implemented. The authenticated FastAPI service exposes `POST /ag-ui` using the official Python event models and encoder, and `apps/web` provides a React/Vite client using `@ag-ui/client`. The browser client supports bearer-token entry, session creation/resume, chat, stop, and history reset. The server adapts the existing governed `Service.chat` path and emits lifecycle events with one completed text delta; it does not stream model tokens. Browser-based Entra sign-in, hosted origin configuration, and transcript history loading remain planned.

## Goal

Give the movie assistant a browser UI using AG-UI’s event-based, bidirectional agent ↔ user protocol. Keep authentication, owner-scoped sessions, model/tool policy, memory consent, budgets, audit and cancellation in the existing Python service. AG-UI is the transport and interaction contract, not an authorization layer.

## Current starting point

- The agent is a Python/FastAPI service in `apps/agent`; it has authenticated session create/status/chat/reset/cancel routes.
- Chat is currently request/response. `Service.chat` runs the existing guarded model/tool loop and commits session history under a revision/run fence.
- The hosted CLI uses Entra bearer tokens. Optional shared Blob sessions and shared safety controls support hosted operation.
- The local web frontend is `apps/web`; it keeps the bearer token in tab memory and uses Vite's `/api` proxy during development. Hosted deployment and browser sign-in are not configured. The terminal interface and CLI remain available.
- Existing standalone endpoints handle explicit movie reads, memory operations, and approval simulations. Those actions must not be made implicitly available merely because the new client uses AG-UI.

## Implemented local slice

The authenticated AG-UI endpoint and React browser client are implemented as a local first slice. The server adapts the current governed run to protocol events without creating a second model/tool loop. It emits lifecycle events and one completed text delta through the existing `Service.chat`; incremental token delivery is not available. The client is under `apps/web` and holds the bearer token only in tab memory.

The current local vertical slice supports:

1. Manually enter an Entra bearer token and forward it to the authenticated API. Browser sign-in is not included.
2. Create/resume an owned session and display its session ID and revision. Resumed sessions retain server history, but prior transcript messages are not loaded into the UI.
3. Submit a user message and consume AG-UI run events. Assistant text arrives as one completed delta after `Service.chat` returns, not incrementally while the run is active.
4. Abort the active request and show completion, cancellation, or a sanitized error.
5. Reset server-side session history. Skills remain unavailable in this client until explicit UI controls are designed.

## Work sequence

### 1. Protocol and runtime compatibility (done for the local slice)

- The backend uses the official Python event models/encoder; the browser uses the pinned `@ag-ui/client` SDK in `apps/web/pnpm-lock.yaml`.
- The adapter is at the FastAPI boundary and invokes the existing `Service.chat` path so governance and session commit behavior stay in the current service.
- The dedicated Vite/React app is in `apps/web`.

### 2. Server protocol adapter (implemented)

- `POST /ag-ui` authenticates through the API's existing Entra boundary and resolves the session through the existing owner check.
- The adapter accepts the supported plain-text request shape and rejects unsupported tool/state inputs. It uses the server-side session revision and preserves the governed service path.
- Lifecycle and assistant text are mapped to AG-UI events. Prompts, raw model reasoning, credentials, private memory values, and unrestricted tool payloads are not sent to the client.
- Existing run fencing, budgets, audit, and history commit semantics remain in the governed service. The client can abort an active request.
- The current local client uses Vite's same-origin `/api` proxy. Deployed CORS/origin policy remains part of hosted readiness.

### 3. Browser UI (initial client implemented; follow-up work remains)

- The client provides a chat screen, pending state, stop, session reset, and create/resume. It receives final text after the backend run completes; retry behavior and incremental tokens are not implemented.
- Use the AG-UI client SDK if it supports the selected server contract; keep the UI’s state minimal and derive durable conversation state from the server session.
- No Entra client secret is present. The current client accepts a manually supplied short-lived token in tab memory; public-client sign-in and deployed origin restrictions remain to be designed.
- Show explicit controls for skills and any memory actions. Keep memory inspect/save/correct/delete on their dedicated APIs and require the existing consent semantics.

### 4. Verify behavior and security boundaries (partial)

- Backend route tests cover the current event adaptation and supported request boundary; the web production build succeeds. Full protocol conformance, browser-origin testing, and end-to-end browser cancellation verification remain open.
- Session safety: owner isolation, stale revision conflict, concurrent run rejection, reset/cancel fencing, and no partial history commit after interrupted runs.
- Governance: model/tool budgets, kill switch/capability disable, audit availability, skill allowlist, and memory consent remain enforced through the AG-UI path.
- Browser boundary: origin/CORS policy, token audience, no credential leakage, XSS-safe rendering, and no unintended HTML execution.
- Exercise both deterministic fake mode locally and an authorized hosted canary. Record protocol versions, exact commands, environment and limits in versioned evidence.

## Phased rollout

| Phase | Deliverable | Exit condition |
| --- | --- | --- |
| 0. Design spike | Confirm AG-UI events, SDK compatibility, and the narrow adapter boundary | Completed for the current local implementation; hosted topology remains open |
| 1. Local AG-UI client | Authenticated route and browser chat using lifecycle events and a completed text delta | Implemented; backend route tests and the web production build pass. Incremental delivery is still open |
| 2. Existing agent features | Explicit skills, safe movie tool status/results, reset and supported errors | Reset is available; other UI feature contracts remain future work |
| 3. Hosted readiness | UI hosting, browser Entra registration/origin config, telemetry and operator runbook | Pending authorized canary plus security and operational review |
| 4. Optional AG-UI capabilities | Human approval interrupts, shared state or richer multimodal UI, if product needs justify them | Separate design, threat review and acceptance criteria for each capability |

## Explicitly deferred

Do not include generative UI, arbitrary frontend-executed tools, agent-writable shared state, raw chain-of-thought, voice/media, or sub-agent composition in the first release. AG-UI supports a wider set of interaction patterns, but each would require new product contracts and threat analysis. The initial UI should represent the current assistant behavior faithfully.

## Open decisions

- Whether the current Agent Framework exposes a compatible AG-UI adapter at the installed version, versus a custom event adapter around `Service`.
- Hosting location and browser Entra redirect origins, API scope, and hosting topology.
- Whether streaming runs can be driven from a streaming model API without changing budget reservation, cancellation, and final commit semantics. The current adapter sends a final text event and treats token streaming as a later improvement.

## Source

AG-UI describes itself as a lightweight, event-based, bidirectional protocol connecting an agent backend and user-facing applications. Its overview distinguishes AG-UI from MCP (agent ↔ tools/data) and A2A (agent ↔ agent), and lists streaming chat, cancellation/resume, human interrupts, shared state and other capabilities. This plan uses only the text interaction and cancellation subset initially: [AG-UI overview](https://docs.ag-ui.com/introduction).
