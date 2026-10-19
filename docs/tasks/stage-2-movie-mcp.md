# Stage 2 task — TMDB movie MCP

## Goal

Extend Stage 1 with a separate, authenticated FastMCP service that exposes only bounded TMDB movie search and details reads. The user selected TMDB as the sole movie source on 2026-10-18. This supersedes the earlier synthetic catalog and admin PUT exercise; historical results remain in [the change log](../change-log.md), not in the current acceptance criteria.

The [TMDB integration record](../tmdb-integration.md) describes credentials, API endpoints, result labels, and attribution. [Stage 2 architecture](../stage-2-architecture.md) and [network design](../stage-2-network-design.md) describe the deployed boundary and open egress work.

## Current status

The repository now has a read-only TMDB adapter and two FastMCP tools, `search_movies` and `get_movie`. The agent-side contract expects `tmdb_<id>`, `tmdb-v1`, and a labeled TMDB rating. The locked local suite passes 46 tests with mocked TMDB responses. Both new images have been built and pushed privately by digest, but the hosted Container Apps still run the **older synthetic images**, so no hosted TMDB result has passed. A live TMDB token is not available in this task's shell yet. Stage 2 is **in progress**.

## Implementation checklist

1. [x] Keep two pinned read operations with strict query, limit, and TMDB ID validation. No generic HTTP, URL, filesystem, arbitrary API path, account-session, or write tool is exposed.
2. [x] Use only TMDB movie search and details GET endpoints with a bearer API Read Access Token; pin the origin, disable redirects, bound time and response bytes, request non-adult English results, and handle `404`/`429` without leaking upstream payloads.
3. [x] Normalize untrusted TMDB fields to a bounded source-labeled result; reject malformed and adult details. Use mocked local tests for approved reads, invalid inputs, response bounds, redirects, and forbidden tools.
4. [ ] Verify the agent-visible schema, CLI display, model-selected read loop, and local MCP transport end to end with a real TMDB token; retain the Stage 1 regressions.
5. [ ] Add the TMDB API Read Access Token as a Container App secret and deploy a digest-pinned MCP and agent image. Verify the actual agent managed identity can call only the two MCP tools and that the MCP can reach the pinned TMDB endpoint. No token may appear in Git, command output, logs, or model context.
6. [x] Confirm non-commercial teaching use and add TMDB's required notice and approved logo to the repository Credits page. Any separate hosted user interface must also display that attribution before release.
7. [ ] Run hosted positive and negative tests: approved search/details, no match/404, bad IDs, over-limit requests, unauthenticated and wrong-audience MCP calls, unknown/write tool proposals, rate-limit or unavailable-upstream behavior, and no redirected credential forwarding.
8. [ ] Complete controlled-egress deployment and tests. The current Container Apps environment has internal catalog ingress but no VNet/workload-profiles UDR policy. A network-rule block of an unapproved destination remains unproven.
9. [ ] The temporary synthetic admin probe, role assignment, and identity were deleted and recorded. Remove the old synthetic app revision as part of the TMDB rollout.
10. [ ] Commit and push the final code, templates, documentation, and redacted test evidence to `gardlt/az-maf-agent`.

## Acceptance

An approved user can search for a real TMDB movie and look up a returned `tmdb_<id>` through the agent. The result is explicitly attributed to TMDB and the rating is labeled as TMDB's vote average. Malformed or unauthorized tool calls fail before an upstream request; unknown or write tools never reach TMDB. Hosted auth, workload identity, destination pinning, redirect refusal, and result bounds are verified with actual runtime contexts. A test-owned unapproved outbound destination is blocked by a deployed network rule while required TMDB, Foundry, identity, platform, registry, DNS, and telemetry paths continue to work.

The previous admin PUT/read-after-write check does not apply to TMDB: the new MCP is read-only and holds no TMDB user session or write capability. Approval cannot create a write path. Stage 2 cannot be marked complete until live TMDB, attribution, credential, and network evidence is recorded.
