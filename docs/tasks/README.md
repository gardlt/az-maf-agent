# Stage implementation tasks

These task files track implementation against the [secure agent teaching specification](../secure-agent-teaching-spec.md). The specification remains authoritative, including its numeric teaching defaults, security contracts, decision register, and release gates. A checked implementation item does not mean every acceptance gate for that stage has passed.

1. [Stage 1: chat and session history](stage-1-chat.md)
2. [Stage 2: movie catalog MCP](stage-2-movie-mcp.md)
3. [Stage 3: Markdown skills](stage-3-markdown-skills.md)
4. [Stage 4: governed memory](stage-4-memory.md)
5. [Stage 5: production guardrails](stage-5-production-guardrails.md)

| Stage | Current state | Next acceptance work |
| --- | --- | --- |
| 1 — Chat | Hosted live-model chat works; some acceptance gates remain open. | Shared/resumable session behavior and deployed expired-token rejection. |
| 2 — Movie MCP | In progress. FastMCP reads, managed-identity service authentication, private ingress, and one hosted model-selected read passed. | Deployed admin/direct-identity PUT authorization and controlled outbound-network exercises. See [validation evidence](../stage-2-validation.md). |
| 3 — Markdown skills | Not started. | Complete Stage 2 gates and select the teaching skill. |
| 4 — Governed memory | Not started. | Complete Stage 3 and select a durable backend. |
| 5 — Production guardrails | Not started. | Complete prior stages and select shared control-state hosting. |

Extend the agent application and its separately packaged services in one workspace; retain previous controls and tests at every stage. The hosted path is CLI → HTTPS Python API in Azure Container Apps → shared agent core, with Microsoft Entra Easy Auth for caller authentication and application code for permissions. The movie catalog MCP service is a separate workspace package and deployment boundary. Workload managed identity is separate from caller identity. No API Management is required initially; Foundry hosting and API Management remain future alternatives. One approved model deployment comes from validated configuration; the actual model is open and runtime routing is deferred.

The built-in deterministic fake model and local fixtures work without Azure credentials. The selected live inference path uses the configured `gpt-5` deployment in the existing Foundry account. Track local and hosted acceptance separately: passing mocks does not satisfy deployed networking or emergency-control gates. Skill, shared session/durable backend, network topology, and control-state choices block only their dependent work. Record rationale, alternatives, tradeoffs, and reconsideration triggers when resolving them; do not turn an example into an approved selection.

For every task, retain versioned synthetic fixtures, exact test commands/results, configuration versions, redacted audit evidence, learner instructions, and residual limitations. Keep raw secrets, private memory, and unrestricted prompts/tool payloads out of evidence. A model refusal is not proof of enforcement; inspect backend effects. Apply the spec's OWASP-aligned threat model, dependency locking/integrity checks, SBOM/scanning, least privilege, and fail-closed rules throughout. Finite passing tests do not guarantee complete protection.
