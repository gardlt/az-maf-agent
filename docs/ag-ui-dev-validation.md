# AG-UI and Entra sign-in: dev validation

Validated on October 21, 2026. This records the local browser client connecting to
the Azure dev agent API. Static UI hosting and hosted origin configuration remain open.

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
