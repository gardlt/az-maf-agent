# Stage 2 task — TMDB movie MCP

**Hosting status:** The dedicated agent and MCP Container Apps, Foundry project, and Entra registrations were removed on 2026-10-18. The completed hosted checks below are historical evidence; the local FastMCP implementation remains.

## Goal

Extend Stage 1 with a separate, authenticated FastMCP service that exposes only bounded TMDB movie search and details reads. The user selected TMDB as the sole movie source on 2026-10-18. This supersedes the earlier synthetic catalog and admin PUT exercise; historical results remain in [the change log](../change-log.md), not in the current acceptance criteria.

The [TMDB integration record](../tmdb-integration.md) describes credentials, API endpoints, result labels, and attribution. [Stage 2 architecture](../stage-2-architecture.md) and [network design](../stage-2-network-design.md) describe the deployed boundary and the completed controlled-egress test.

## Current status

**Status: complete for the non-commercial teaching scope; hosting retired.** The repository has a read-only TMDB adapter and two FastMCP tools, `search_movies` and `get_movie`. The agent-side contract expects `tmdb_<id>`, `tmdb-v1`, and a labeled TMDB rating. The locked local suite passed 47 tests. Both working images were deployed by digest, and signed-in hosted reads and a model-selected read passed against real TMDB data. Internal missing-token and wrong-audience requests returned `401`; the external internal-hostname request returned `404`. An authenticated hosted `/about` Credits page showed the required notice and approved logo. The rotated TMDB token passed a live hosted movie read. A separate short-lived VNet/NSG environment demonstrated a network-rule deny to one test-owned destination while TMDB and Foundry stayed healthy; all temporary resources and grants were then removed. This was a controlled one-destination test, not a production-wide outbound allowlist.

## Implementation checklist

1. [x] Keep two pinned read operations with strict query, limit, and TMDB ID validation. No generic HTTP, URL, filesystem, arbitrary API path, account-session, or write tool is exposed.
2. [x] Use only TMDB movie search and details GET endpoints with a bearer API Read Access Token; pin the origin, disable redirects, bound time and response bytes, request non-adult English results, and handle `404`/`429` without leaking upstream payloads.
3. [x] Normalize untrusted TMDB fields to a bounded source-labeled result; reject malformed and adult details. Use mocked local tests for approved reads, invalid inputs, response bounds, redirects, and forbidden tools.
4. [x] Verify the agent-visible schema, CLI display, and local FastMCP transport end to end with a real TMDB token. The hosted model-selected read and Stage 1 regressions also passed.
5. [x] Add the TMDB API Read Access Token as a Container App secret and deploy digest-pinned MCP and agent images. The agent managed identity completed live hosted TMDB reads through the private MCP; the two-tool registry and schema limits pass local tests. No token appeared in Git or command output.
6. [x] Confirm non-commercial teaching use, add the required notice and approved logo to the repository Credits page, and deploy an authenticated hosted `/about` page with the same attribution.
7. [x] Hosted approved search/details, no match/404, bad IDs, over-limit requests, missing and wrong-audience MCP tokens, and unknown/write tool proposals passed. Rate-limit/unavailable-upstream and redirect cases passed local mocked tests; intentionally forcing failures against the live TMDB service is not required for this adapter contract.
8. [x] Deployed a separate Consumption workload-profile VNet/NSG test environment. A direct HTTPS connection from the test agent reached the test-owned destination while the rule allowed it, then timed out after the `/32` deny rule was applied; TMDB and Foundry remained healthy. The separate test environment, apps, role grants, VNet, and NSG were removed after evidence capture.
9. [x] Delete the temporary synthetic admin probe, role assignment, and identity. The old synthetic MCP revisions were inactive before the dedicated resource group was removed.
10. [x] Commit and push the code, templates, documentation, and redacted test evidence to `gardlt/az-maf-agent`.

## Acceptance

An approved user can search for a real TMDB movie and look up a returned `tmdb_<id>` through the agent. The result is explicitly attributed to TMDB and the rating is labeled as TMDB's vote average. Malformed or unauthorized tool calls fail before an upstream request; unknown or write tools never reach TMDB. Hosted auth, workload identity, destination pinning, redirect refusal, and result bounds are verified with actual runtime contexts. A test-owned unapproved outbound destination is blocked by a deployed network rule while required TMDB, Foundry, identity, platform, registry, DNS, and telemetry paths continue to work.

The previous admin PUT/read-after-write check does not apply to TMDB: the new MCP is read-only and holds no TMDB user session or write capability. Approval cannot create a write path. The live TMDB, attribution, credential, and controlled network evidence is recorded in [Stage 2 validation](../stage-2-validation.md). A broad production egress policy remains a future hardening decision outside this teaching-stage acceptance.
