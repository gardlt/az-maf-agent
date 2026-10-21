# AG-UI and Entra sign-in: dev validation

Validated on October 21, 2026. This records both the local browser client and the
hosted Azure UI connecting to the Azure dev agent API. The browser's interactive
hosted Microsoft sign-in remains a user action; automated hosted canaries use the
existing CLI user's delegated token.

## Deployed source and result

- Branch: `feat/ag-ui-integration`.
- Entra UI implementation: `dc4744c`.
- Deployed source: `53646ed`, including the patched `certifi` dependency.
- Successful [agent-only dev deployment](https://github.com/gardlt/az-maf-agent/actions/runs/39683115332).
- Azure reported ready revision `ca-maf-agent-dev-eus2-01--0000036` and provisioning state `Succeeded` during verification.
- The user subsequently confirmed that the browser flow worked.

The initial deployment was blocked by a Critical image-scan finding for
`certifi==2026.7.22`. Updating the lockfile to `2026.10.19` resolved the finding;
the successful retry passed the existing security gate. The gate was not bypassed.

## Request routing and authentication

The browser calls `http://127.0.0.1:5173/api/ag-ui`. Vite removes `/api` and forwards
the request to the approved Azure dev API:
`https://ca-maf-agent-dev-eus2-01.kindisland-49d1cad2.eastus2.azurecontainerapps.io/ag-ui`.
Seeing a localhost request URL is expected for this development proxy.

The local `.env.local` configures `AGENT_API_URL` as that Azure API origin and
`VITE_AGENT_API_URL=/api`. It is ignored by Git. The checked-in `.env.example`
contains only public authentication identifiers; another checkout must copy it
and configure its approved backend target.

The dedicated dev SPA requests the API's delegated `Chat.Access` scope through
MSAL Browser. The deployed Easy Auth configuration was read back and admitted
exactly the existing CLI client and the dedicated web client. Its API audience
remained the existing agent API application. Application-level user and scope
checks remain required.

## Verification

- Frontend TypeScript compilation and production build passed, including the
  separate MSAL redirect bridge page.
- Six focused authentication checks passed: invalid configuration/API targets,
  delegated scope and account selection, renewed token acquisition, required
  interactive renewal, empty-token rejection, and local cache cleanup after a
  failed sign-out popup.
- All 238 backend tests passed; Ruff lint and formatting checks passed.
- Infrastructure validation compiled 39 Bicep files and nine parameter profiles,
  preserving 16 resource contracts and passing ten deployment-target checks.
- An authenticated direct Azure `OPTIONS /ag-ui` returned `405` with `Allow: POST`;
  an invalid POST body returned `422`, confirming the previously missing route.
- The local proxy returned `204` for OPTIONS, which Vite may answer locally, and
  forwarded the invalid POST to the API, which returned `422`.
- A session created through the local proxy returned `200`. A bounded greeting
  request through that same proxy returned `200` and the complete event sequence:
  `RUN_STARTED`, `TEXT_MESSAGE_START`, `TEXT_MESSAGE_CONTENT`, `TEXT_MESSAGE_END`,
  `RUN_FINISHED`, with no `RUN_ERROR` event.

The automated hosted canary used the existing CLI authentication helper and cached
user sign-in; it did not automate browser credentials or consent. Token values and
conversation contents were not printed or retained in this report. The user’s
browser confirmation supplements these API and configuration checks.

See the [web setup guide](../apps/web/README.md) for sign-in, proxy configuration,
the client allowlist, and the remaining hosted UI requirements.

## Hosted UI rollout

The [Azure dev UI](https://ca-maf-web-dev-eus2-01.kindisland-49d1cad2.eastus2.azurecontainerapps.io/)
was deployed from `6ab6fc4` through the successful
[web-only deployment](https://github.com/gardlt/az-maf-agent/actions/runs/39688712693).
Azure reported provisioning `Succeeded` and ready revision
`ca-maf-web-dev-eus2-01--llpyodc`.

The first web image was blocked by High/Critical findings in the bundled Caddy
runtime and its Alpine/Go components. The replacement uses pinned
`nginx:1.31.7-alpine-slim`, with patched `zlib==1.3.2-r1`, and passed the unchanged
High/Critical image security gate. The frontend build stage remains a separately
pinned Node image; the final image serves only the built assets and API proxy.

Verification against the deployed site established:

- The home page, `/redirect.html`, and both referenced JavaScript entry assets returned `200`.
- Browser inspection showed the movie guide's Microsoft sign-in screen without a configuration error.
- The callback page had no Cross-Origin-Opener-Policy header, as required by the MSAL redirect bridge.
- Unauthenticated POST `/api/ag-ui` returned `401`; an authenticated malformed request returned `422`.
- Source/configuration paths `/.env.local` and `/src/auth.ts` returned `404`.
- Session creation returned `200`; a bounded greeting through the hosted `/api/ag-ui`
  returned `200` with the complete run/message event sequence and no `RUN_ERROR`.
- Azure readback confirmed `allowInsecure=false`, scale limits of zero to one replica,
  and the registry identity's `lifecycle=None`. That identity is available to the
  platform for image pulls, not to application code.
- Entra readback confirmed the exact hosted HTTPS `/redirect.html` callback alongside
  both existing localhost callbacks. The API continues to admit only the configured
  CLI/web clients and approved users with delegated `Chat.Access`.

Infrastructure validation passed for 40 Bicep files, nine parameter profiles,
16 existing resource contracts, and 12 target-selection checks. The final identity
lifecycle setting was additionally compiled through the main entry point. Local
production-container tests also passed for the replacement runtime with upstream
TLS certificate verification enabled. These deployment and canary checks do not
establish production readiness or automated browser consent/cancellation coverage.
