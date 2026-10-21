# Agent Bones web UI

This is the first browser client for the agent's AG-UI endpoint. It uses the official
`@ag-ui/client` HTTP agent, creates or resumes an owner-scoped session, consumes AG-UI
events into a plain text transcript, and supports stop and history reset. The server
currently sends lifecycle events plus one completed text delta, so the assistant response
appears when the governed backend call finishes rather than token by token.

## Run locally

Start the Python API as described in the [agent API guide](../agent/README.md#api-configuration-and-deployment),
using `AGENT_CONFIG=config/offline.json` and the required Entra configuration
(`ENTRA_TENANT_ID`, `ENTRA_AUDIENCE`, and `ENTRA_ALLOWED_USERS`). The API still verifies
an Entra `Chat.Access` bearer token even in fake-model mode. Use a valid short-lived token
for that audience; the UI holds it in memory for the current tab only.

Then, in another terminal:

```sh
cd apps/web
pnpm install --frozen-lockfile
pnpm dev
```

Open the local Vite URL, enter the agent API token, and connect. The development server
proxies `/api` requests to `http://127.0.0.1:8000`; set `AGENT_API_URL` when starting Vite
to proxy to another API address. To resume a session, paste its session ID before
connecting. The API does not expose prior transcript messages yet, so a resumed UI starts
with an empty visible transcript while the server retains its bounded session history.

The browser UI does not save tokens or transcripts in local storage. It renders all agent
text as plain text and does not invoke frontend tools. Browser-based Entra sign-in, hosted
UI origin/CORS configuration, incremental token delivery, and transcript history loading
are future work. Until then, use a trusted local development environment and an authorized
short-lived token.

Build the static UI with:

```sh
pnpm build
```
