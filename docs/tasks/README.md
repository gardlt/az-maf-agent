# Stage implementation tasks

These task files track implementation against the [secure agent teaching specification](../secure-agent-teaching-spec.md). The specification remains authoritative, including its numeric teaching defaults, security contracts, decision register, and release gates. A checked implementation item does not mean every acceptance gate for that stage has passed.

1. [Stage 1: chat and session history](stage-1-chat.md)
2. [Stage 2: movie catalog MCP](stage-2-movie-mcp.md)
3. [Stage 3: Markdown skills](stage-3-markdown-skills.md)
4. [Stage 4: governed memory](stage-4-memory.md)
5. [Stage 5: production guardrails](stage-5-production-guardrails.md)
6. [Stage 6: application-controlled model routing](stage-6-model-routing.md)

| Stage | Current state | Next acceptance work |
| --- | --- | --- |
| 1 — Chat | Dev hosting is active; some Stage 1 acceptance gates remain open. | Cross-replica session/race acceptance remains open; deployed expired-token rejection is recorded in Stage 5. |
| 2 — Movie MCP | Complete for the non-commercial TMDB teaching scope; dev agent/MCP hosting is active. The 50-query dev read test passed; earlier controlled egress evidence is historical. | No Stage 2 teaching acceptance work remains; runtime validation is recorded. See [validation evidence](../stage-2-validation.md). |
| 3 — Markdown skills | Complete for single-replica teaching; original hosted skill acceptance and integrated regressions pass. | Case 4 is resolved in Stage 4 at the memory layer; production shared controls remain Stage 5 work. |
| 4 — Governed memory | Complete for selected dev teaching scope: Blob preferences, bounded recall, lifecycle controls, hourly cleanup, monitoring, and 126 passing tests. | Restart persistence and stable hosted lifecycle passed. See [validation evidence](../stage-4-validation.md); retain the documented operational bounds. |
| 5 — Production guardrails | Implemented in dev with recorded milestones; broader release gates remain open. | Complete remaining hosted isolation/control cases, final network topology and operational rehearsals. |
| 6 — Model routing | Complete for selected dev teaching scope: 215 tests, both actual model routes, 10/10 benign checks and 77.6% lower estimated routine inference cost. | No Stage 6 dev acceptance work remains; see [evidence and limits](../validation/stage-6-model-routing.md). Stage 5 production gates remain separate. |

Extend the agent application and its separately packaged services in one workspace; retain previous controls and tests at every stage. The retired hosted path was CLI → HTTPS Python API in Azure Container Apps → shared agent core, with Microsoft Entra Easy Auth for caller authentication and application code for permissions. The movie catalog MCP service remains a separate workspace package and deployment boundary. Workload identity is separate from caller identity. No API Management is required initially; Foundry hosting and API Management remain future alternatives. Stage 6 adds application-controlled routing among approved deployments from validated configuration, as requested by the user.

The built-in deterministic fake model and local fixtures work without Azure credentials. The selected live inference path uses approved `gpt-5-mini` and `gpt-5` deployments in the existing Foundry account under the Stage 6 routing policy. Track local and hosted acceptance separately: passing mocks does not satisfy deployed networking or emergency-control gates. Skill, shared session/durable backend, network topology, and control-state choices block only their dependent work. Record rationale, alternatives, tradeoffs, and reconsideration triggers when resolving them; do not turn an example into an approved selection.

For every task, retain versioned test fixtures, exact test commands/results, configuration versions, redacted audit evidence, learner instructions, and residual limitations. Keep raw secrets, private memory, and unrestricted prompts/tool payloads out of evidence. A model refusal is not proof of enforcement; inspect backend effects. Apply the spec's OWASP-aligned threat model, dependency locking/integrity checks, SBOM/scanning, least privilege, and fail-closed rules throughout. Finite passing tests do not guarantee complete protection.
