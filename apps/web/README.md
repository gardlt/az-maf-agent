# Agent Bones web UI

This is the first browser client for the agent's AG-UI endpoint. It uses the official
`@ag-ui/client` HTTP agent, creates or resumes an owner-scoped session, consumes AG-UI
events into a plain text transcript, and supports stop and history reset. The server
currently sends lifecycle events plus one completed text delta, so the assistant response
appears when the governed backend call finishes rather than token by token.

## Run locally

Use Node.js 24 or newer and pnpm. Copy `.env.example` to `.env.local` inside
`apps/web`. It contains public Entra identifiers, never a client secret.

Start the Python API as described in the [agent API guide](../agent/README.md#api-configuration-and-deployment),
using `AGENT_CONFIG=config/offline.json` and the required Entra configuration
(`ENTRA_TENANT_ID`, `ENTRA_AUDIENCE`, and `ENTRA_ALLOWED_USERS`). The API still verifies
the user's Entra `Chat.Access` bearer token even in fake-model mode.

Then, in another terminal:

```sh
cd apps/web
pnpm install --frozen-lockfile
pnpm dev
```

Open `http://127.0.0.1:5173`, select **Sign in with Microsoft**, complete the Microsoft
popup and any consent prompt, then select **Connect**. The development server proxies
`/api` requests to `http://127.0.0.1:8000`; set `AGENT_API_URL` in `.env.local` or the
shell to use an approved hosted API that includes this branch's `/ag-ui` endpoint.
The configured API address cannot be changed in the UI. To resume a session, paste its session ID before
connecting. The API does not expose prior transcript messages yet, so a resumed UI starts
with an empty visible transcript while the server retains its bounded session history.

MSAL Browser uses authorization code flow with PKCE and an in-memory token cache.
Before every session, chat, or reset request, it silently acquires a valid access token
for the selected user and the API's `Chat.Access` scope. When interaction is required,
the UI offers **Sign in again**. Switching users clears the visible conversation.
**Disconnect** leaves Microsoft sign-in active; **Sign out** clears the user's local
authentication state and conversation and opens Microsoft sign-out. Reloading the page
requires signing in again. The UI does not persist tokens or transcripts in local storage.

## Entra registration and API admission

The branch's agent API adapter is deployed to Azure dev. The local UI can connect
through its Vite proxy by setting `AGENT_API_URL` to the approved dev API origin.
See the [dev validation record](../../docs/ag-ui-dev-validation.md) for the deployed
source, successful live event stream, and verification limits.

The dedicated single-tenant dev SPA is `az-maf-agent-web-dev`, client ID
`a5d930a1-3d30-4d14-83d6-6992cb1bf626`, in tenant
`c57afb80-6b3d-4bae-a466-e4d217bcb4a2`. It requests delegated permission
`api://67b8f4b9-71e4-4815-b8b5-a0a4fd7bc0d7/Chat.Access`.
Its registered SPA redirect URIs are `http://127.0.0.1:5173/redirect.html`
and `http://localhost:5173/redirect.html`. Port 5173 is fixed to avoid callback mismatch.
The dedicated callback page contains only the MSAL redirect bridge and is included in
production builds. Do not add a Cross-Origin-Opener-Policy header to that page.

For another environment, create a dedicated single-tenant SPA, add its exact callback
URL under **Authentication → Single-page application**, and add this API's delegated
`Chat.Access` permission under **API permissions**. Users consent during sign-in when
tenant policy permits; otherwise a tenant administrator must grant consent. Do not
enable implicit grants or put a client secret in the frontend.

Set `VITE_ENTRA_TENANT_ID`, `VITE_ENTRA_CLIENT_ID`, and `VITE_ENTRA_API_CLIENT_ID`
before building. `VITE_AGENT_API_URL` defaults to `/api`. These values are compiled
into public JavaScript. `AGENT_API_URL` is the server-side development proxy target.

Container Apps Easy Auth must explicitly admit the SPA client ID as well as the CLI.
Set `MAF_WEB_CLIENT_ID` in the deployment environment to the approved SPA client ID;
the Bicep parameter defaults to empty, retaining CLI-only admission when no web client
is approved. Signing in does not admit new users: the API still validates tenant,
audience, scope, and `ENTRA_ALLOWED_USERS`. Downstream inference/tools continue using
the agent's separate identity.

## Deploy the UI to Azure

The [Azure dev UI](https://ca-maf-web-dev-eus2-01.kindisland-49d1cad2.eastus2.azurecontainerapps.io/)
is deployed. Select **Sign in with Microsoft**, then **Connect** using an approved
account. See the [dev validation record](../../docs/ag-ui-dev-validation.md) for
the deployed source and live proxy/chat checks.

The `web` service in the existing deployment workflow builds `Dockerfile.web` and
deploys `infra/patterns/web.bicep` through the shared Bicep entry point. The pinned
Node build stage compiles the frontend; the final pinned minimal Nginx image contains
the static build and production proxy. The workflow validates Nginx configuration
and scans the final image before pushing it by digest.

Select environment `dev` and service `web` to deploy just the UI. Set
`MAF_ENABLE_WEB=true` to include it in later all-service deployments. The build uses
`MAF_TENANT_ID`, `MAF_WEB_CLIENT_ID`, and `MAF_API_CLIENT_ID` as public frontend
configuration. `VITE_AGENT_API_URL` is fixed to `/api` in this image. At runtime,
`AGENT_API_HOST` comes from the approved agent app and environment domain in Bicep.

The web app has external HTTPS-only ingress, runs as a non-root user, and scales
from zero to one replica. Public assets include the sign-in screen; access to the
agent still requires a valid user token, admitted client, scope and user. The web
container app uses the existing ACR pull identity only for platform image pulls;
`identitySettings.lifecycle=None` keeps it unavailable to the running container.
No API credential or user
token is built into the image, and access logging is not enabled.

Nginx serves the UI and `/redirect.html`, and proxies `/api/*` to the fixed Azure
API host over HTTPS with explicit upstream certificate verification, bearer
authentication, and response buffering disabled for event streaming.
The proxy strips the `/api` prefix and does not forward browser cookies. Keeping
UI and API requests on one browser origin avoids adding CORS permissions to the
agent. The callback page receives no Cross-Origin-Opener-Policy header.

Add the resulting hosted `https://<web-host>/redirect.html` to the SPA registration
while retaining required localhost callbacks. This directory provisioning remains
separate from ordinary ARM deployment. The dev app is named `ca-maf-web-dev-eus2-01`;
the Bicep `webUrl` output gives its HTTPS address. A scaled-to-zero app may take a
moment to wake on its first request. Incremental token delivery and transcript
history loading remain open.

Build the static UI with:

```sh
pnpm build
```

Run the focused authentication checks with `pnpm test` (Node.js 24+).
