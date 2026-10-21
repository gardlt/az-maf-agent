# Agent Bones web UI

This is the first browser client for the agent's AG-UI endpoint. It uses the official
`@ag-ui/client` HTTP agent, creates or resumes an owner-scoped session, streams AG-UI
events into a plain text transcript, and supports stop and history reset.

## Run locally

Start the Python API with `AGENT_CONFIG=config/offline.json` and the required Entra
configuration (`ENTRA_TENANT_ID`, `ENTRA_AUDIENCE`, and `ENTRA_ALLOWED_USERS`). The API
still verifies an Entra `Chat.Access` bearer token even in fake-model mode. Use a valid
short-lived token for that audience; the UI holds it in memory for the current tab only.

Then, in another terminal:

```sh
cd apps/web
pnpm install --frozen-lockfile
pnpm dev
```

Open the local Vite URL, enter the agent API token, and connect. The development server
proxies `/api` requests to `http://127.0.0.1:8000`; set `AGENT_API_URL` to proxy to another
local API address. To resume a session, paste its session ID before connecting. Earlier
transcript messages are not currently exposed by the API, so a resumed UI starts with an
empty visible transcript while the server retains its bounded session history.

The browser UI does not save tokens or transcripts in local storage. It renders all agent
text as plain text. Browser-based Entra sign-in, hosted UI origins/CORS, and incremental
token delivery are future work.

Build the static UI with:

```sh
pnpm build
```
