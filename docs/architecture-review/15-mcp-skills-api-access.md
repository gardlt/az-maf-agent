# 15 — Open architecture issue: MCP, skills, and direct API access

**Status:** open for discussion; no implementation or security-boundary change is approved by this note.

## Issue

Decide where the agent should execute TMDB requests and what role reviewed skills should have. The question has two related but separate parts:

1. Should the TMDB integration remain a separately deployed MCP service, or should the agent service call TMDB through application-owned tools?
2. Should skills remain reviewed guidance that selects among existing tools, or should they gain executable/network capabilities?

MCP and skills are not mutually exclusive. A skill can guide the agent to use a bounded tool that is backed by MCP. It can also guide the agent to use an equivalent bounded tool implemented inside the agent service. Making skill content executable is a different capability and security decision.

## Current design

- Reviewed skills are digest-pinned Markdown. They guide tasks such as movie research and movie-night recommendations; they do not execute code, fetch credentials, or make HTTP requests.
- The skill manifest can only request the existing `search_movies` and `get_movie` capabilities. Skill permissions intersect caller, application, and agent permissions; a skill cannot create a new capability.
- Application code validates model-proposed tool calls and dispatches the two read operations through the agent's FastMCP client.
- The separately deployed MCP service owns the TMDB API Read Access Token and makes fixed, read-only requests to TMDB. It independently authenticates the agent caller and enforces its `Catalog.Read` permission.
- The TMDB token is an application credential. TMDB documents sending its API Read Access Token as a Bearer token for v3 and v4 application API calls. It is not the user's Entra token and does not require a TMDB user session for the current read-only search/details use.

See [agent to movie MCP](02-agent-to-mcp.md), [agent to reviewed skills](03-agent-to-skills.md), [identity and access](07-identity-and-access.md), and the [TMDB integration guide](../tmdb-integration.md).

## What MCPs and skills are good at

| Concept | Good fit | Not a good fit / limitation |
| --- | --- | --- |
| **MCP** | A standard interface for exposing tools or data to agents; connecting an agent to a separately owned service; reusing an integration across compatible clients; keeping an API credential and network path behind a narrow service boundary. | Describing a multi-step task or deciding which workflow is appropriate. MCP is a protocol and service pattern, not a guarantee that a tool is safe. The server still needs authentication, authorization, input/output validation, least privilege, limits, and operational controls. |
| **Skill** | Reviewed task guidance: the steps to follow, which existing tools to consider, what to ask the user, how to interpret results, and how to present an answer. A skill can make behavior more consistent and reusable without duplicating tool implementation. | Executing HTTP requests, fetching or protecting secrets, or enforcing authorization by itself. Instructions are model context, not a permission boundary; the model may not follow them exactly. A skill should not grant a capability that the application has not independently approved. |

They work well together: a movie skill can guide the agent to compare synopsis and release year and label ratings, while a bounded tool—served through MCP or implemented in the agent—retrieves the TMDB data. Skills shape the task; application code and infrastructure decide which effects are allowed.

## Context windows: original purpose and current relevance

The idea that **MCP was created to solve context-window limits** is not supported by the original announcement. Anthropic introduced MCP in November 2024 to standardize connections from AI applications to external data and tools and reduce one-off integrations. MCP can provide context to a model, but it does not inherently reduce how many tokens a host sends to the model.

There is a real, related context problem at scale. Depending on the host, tool names, descriptions, and schemas may be sent to the model up front. Tool results and intermediate data may also be inserted into the conversation. With hundreds of tools or very large results, this can use substantial context, increase cost and latency, and make relevant details harder to find. The protocol itself does not require every host to expose every tool definition on every turn; this cost depends on the client's discovery and context-management strategy.

Skills address a different but overlapping need: packaging procedural and domain knowledge so it can be loaded progressively. In common Agent Skills implementations, the host can start with a skill's small name/description metadata, load the main instructions when a task matches, then load referenced material or run a script only when needed. This keeps unrelated guidance out of the active prompt. The Agent Skills launch described progressive disclosure as a core design principle and explicitly described skills as complementary to MCP for workflows involving external tools. That supports saying context efficiency is a benefit of skills; it does **not** support saying skills were made simply to replace MCP or fix MCP's context usage.

The concern remains relevant today even as models accept larger contexts. Large contexts still compete with task instructions, conversation history, tool definitions, and retrieved data. Current context-engineering guidance continues to recommend selecting relevant information rather than sending everything. Tool search, deferred tool loading, code execution with MCP, concise server-side filtering, and skill-style progressive disclosure are different ways to manage that pressure; they can be combined.

### Examples in this project

- **One MCP with two small tools:** `search_movies(query)` and `get_movie(catalog_id)` expose a small schema, so their definition overhead is likely modest. The MCP's main value here is the separate service and TMDB credential boundary, not context savings.
- **A movie-research skill:** load its guidance only when requested; it can say to compare year and synopsis, distinguish missing data, and label TMDB ratings. That is task guidance, not another API connector.
- **A large catalog integration:** if an agent had hundreds of catalog, user, and administrative tools, listing every schema on every turn could waste context. A host could search tool names/descriptions and expose only the selected schemas, or let trusted application code filter the data before returning a compact result.
- **A long workflow:** a skill can refer to a detailed comparison rubric only when needed. A tool or controlled execution environment can process a large result set and return only the fields needed for the answer, rather than putting every row into model context.

In this repository specifically, skills are selected by ID/version and the selected Markdown is added to model instructions. The registry does not currently implement nested references, on-demand file navigation, or executable skill scripts. The broader Agent Skills format permits bundled references and scripts, but adopting those features here would require implementation and a separate security review. This distinction matters: progressive disclosure is a design option, not an automatic property of every skill system.

## Guidance from agent platform providers

These sources describe how their own agent products and APIs use MCP, tools, and skills. They are useful design guidance, not requirements imposed by the MCP or Agent Skills standards.

| Source | Guidance | Application to this issue |
| --- | --- | --- |
| [Anthropic's MCP launch announcement](https://www.anthropic.com/news/model-context-protocol) | MCP was introduced to connect AI applications to external data and tools through a common protocol, reducing fragmented one-off integrations. | Treat MCP primarily as an integration and interoperability layer, not as a context-window optimization feature. |
| [Anthropic on code execution with MCP](https://www.anthropic.com/research/code-execution-with-mcp) | Large tool catalogs and intermediate results can consume context. Tool discovery on demand and filtering results in code can reduce token use, but require a capable execution environment and careful design. | Context overhead depends on the host and use pattern. For this agent's two small movie tools, focus on service boundary and credential ownership; if the catalog grows, evaluate deferred tool discovery and compact results. |
| [Anthropic on Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills) | Skills package specialized knowledge and workflows and use progressive disclosure; Anthropic describes them as complementary to MCP for more complex workflows. It also warns that skill instructions and bundled code can introduce vulnerabilities or exfiltration paths. | Use skills for movie workflow guidance and keep their capabilities bounded. If references or scripts are added, review them as code/content with provenance and sandbox controls, not as harmless prompt text. |
| [OpenAI's Skills guidance for MCP-backed plugins](https://developers.openai.com/plugins/concepts/skills) | OpenAI describes MCP as providing live data, authentication, authorization, and actions, while skills explain when and in what order to call tools, how to handle incomplete results, and how to format the result. Skills may also work without MCP if the workflow only needs packaged guidance and resources. | This directly supports keeping `movie-research` and `movie-night` as workflow guidance and `search_movies`/`get_movie` as the controlled data interface. The data interface could be MCP-backed or a fixed agent-owned tool. |
| [OpenAI's Agent Skills API guide](https://developers.openai.com/api/docs/guides/tools-skills) | OpenAI's implementation exposes skill metadata first and lets the model load full instructions and files as needed. It cautions developers to inspect skills and supporting files because they can enable prompt-injection-driven exfiltration. | “Skill” does not always mean passive Markdown: some platforms allow scripts and shell execution. This repository's registry is intentionally narrower; preserve that boundary unless executable skills have a separate threat review. |
| [OpenAI's MCP connection guide](https://developers.openai.com/api/docs/guides/agents-api/tools/mcp) | The host can restrict discoverable/callable tools with an allowlist; credentials should stay out of reusable definitions and logs, and a trusted proxy or server can supply secrets outside agent-generated code. | Keep TMDB credentials behind a server-side boundary and expose only the approved movie operations. A direct agent adapter would need equivalent secret handling and tool allowlisting. |
| [OpenAI on prompt-injection-resistant agent design](https://openai.com/index/designing-agents-to-resist-prompt-injection/) | The stated goal is to constrain the impact of manipulation, not rely only on detecting malicious text; sensitive transmission or dangerous actions need appropriate safeguards. | TMDB descriptions and other retrieved text remain untrusted. Enforce fixed hosts, read-only methods, budgets, and output validation in code/network policy; do not rely on a skill instruction to prevent misuse. |

Taken together, the vendor guidance reinforces the separation in this issue: use MCP or another application tool interface for controlled live data/actions; use skills for reusable procedures and domain context; and treat context efficiency as a property of discovery, loading, execution, and result shaping—not as a reason to replace one concept with the other.

## Options and tradeoffs

| Option | Benefits | Costs and security concerns |
| --- | --- | --- |
| **Reviewed skills + MCP-backed fixed tools** (current pattern) | Skills describe task behavior; MCP owns the TMDB credential and narrow API boundary. Agent and MCP can be deployed, monitored, and denied independently. MCP independently checks caller identity and `Catalog.Read`. | Adds a service, network hop, service-to-service identity, deployment/configuration, availability dependency, and duplicated protocol contracts. MCP schema drift or deployment failure can interrupt movie reads. |
| **Reviewed skills + fixed tools calling TMDB inside the agent** | Removes one service and a network hop. The same skills can guide use of fixed `search_movies` and `get_movie` tool contracts. One deployment may be simpler to operate for a small system. | The agent service now needs the TMDB token and outbound TMDB access. A compromise of the larger agent/API boundary may expose or misuse that credential. The separate MCP identity check and `Catalog.Read` boundary disappear; authorization, tool revocation, rate limits, and audit must be enforced in the agent service. Agent and catalog changes share a deployment and failure boundary. |
| **Executable skills with narrow, per-skill API capabilities** | Could package workflow-specific code and validation with a skill and make some integrations easier to add independently. | Requires an execution runtime, code provenance and supply-chain policy, dependency isolation, per-skill credential brokering, sandboxing, resource limits, audit, revocation, and network policy. A skill must not receive a raw shared token or be able to bypass the agent's common budgets and validation. This is not supported by the current Markdown skill registry. |
| **Skills using a generic HTTP tool** | Most flexible for many APIs and evolving workflows; avoids adding a named tool for every operation. | Highest exposure if the model or skill can influence URLs, methods, headers, or bodies. Risks include SSRF, calls to metadata/internal endpoints, writes, credential/header disclosure, unbounded data retrieval, response-based prompt injection, and data exfiltration. A domain allowlist alone is insufficient if paths, methods, redirects, DNS resolution, headers, and response size are not also constrained. |

## Security questions to resolve

### Credential ownership and flow

- Keep the TMDB API Read Access Token in a server-side secret store. Never put it in skill Markdown, model context, browser code, user-controlled headers, command-line arguments, or routine logs.
- If direct calls move into the agent, scope secret access to the agent workload, document who can read or rotate it, and ensure errors and traces cannot reveal it.
- Do not forward the user's Entra token to TMDB. It authenticates the caller to this application; it is not the TMDB application credential.
- Confirm whether TMDB's application-level access model and project terms meet the intended usage; the existing guide covers attribution and non-commercial scope.

### Network and request authority

- Keep the origin fixed to `https://api.themoviedb.org`, use only approved GET paths, disable redirects, and set connection/read timeouts.
- Bound query length, result count, response bytes, output size, language, and adult-content behavior. Validate returned fields and IDs before they enter model context.
- If any generic HTTP or executable-skill option is considered, require a reviewed capability contract and enforce network restrictions outside the model. Do not trust skill instructions or model-proposed URLs as security controls.

### Authorization, governance, and failure

- Preserve model-call and tool-call budgets, cancellation, per-run limits, rate-limit behavior, capability disable/revocation, owner scoping, and content-free audit on whichever side executes the request.
- Define how an operator blocks future TMDB calls and how quickly the block applies. With MCP, disable can be enforced at a separate service boundary; direct calls need an equivalent agent-side and, where required, egress control.
- Treat TMDB titles and synopses as untrusted data. Keep response text from changing tool permissions or causing the model to invoke broader network actions.
- Compare timeout, retry, rate-limit, and outage behavior. Direct calls reduce a hop but put upstream failure in the agent's request path; MCP adds an availability dependency but offers an independent boundary.

## Decision criteria

Evaluate the options against:

1. Least privilege and isolation of the TMDB token and egress.
2. Independent enforcement and revocation of movie-read permissions.
3. Preservation of the current bounded request/response contract and governance.
4. Operational cost: deployments, identities, networking, monitoring, and on-call ownership.
5. Ability to test and audit denied as well as successful requests.
6. Whether skills actually need executable code, or whether task guidance plus fixed tools meets the product need.

## Suggested evaluation before a decision

If reducing service count is the primary motivation, prototype only the **fixed application-owned tool** option. Keep the two current tool names and schemas, move or reuse the pinned TMDB adapter behind the agent-side dispatch boundary, and keep skills as Markdown guidance. Compare it with the MCP path using mocked upstream responses and tests for invalid arguments, fixed origin/path, redirects, timeouts, oversized or malformed responses, rate limits, secret redaction, cancellation, budgets, and revocation. Do not add arbitrary URL/method access or executable skill code as part of that prototype.

Before any hosted cutover, document the new secret location and rotation procedure, agent egress policy, independent disable behavior, audit evidence, deployment rollback, and the loss or replacement of the MCP `Catalog.Read` check. A local adapter test is not proof of hosted network isolation or runtime secret handling.

## Decision record

- **Selected option:** none; current MCP-backed fixed tools remain the recorded baseline.
- **Decision owner / reviewers:** to be assigned by the project.
- **Evidence needed:** comparative implementation and security review, local denial tests, and—if a hosted change is proposed—approved identity, secret, egress, revocation, and operational acceptance evidence.
- **Reconsider when:** service count or operations cost is a demonstrated problem, or requirements change to justify executable skills or broader API access.

## Sources

- [Anthropic: Introducing the Model Context Protocol (Nov 25, 2024)](https://www.anthropic.com/news/model-context-protocol)
- [Anthropic: Equipping agents for the real world with Agent Skills (Oct 16, 2025; updated Dec 18, 2025)](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)
- [Anthropic: Code execution with MCP for efficient agents](https://www.anthropic.com/research/code-execution-with-mcp)
- [Anthropic: Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- [OpenAI: Skills for MCP-backed plugins](https://developers.openai.com/plugins/concepts/skills)
- [OpenAI API: Agent Skills](https://developers.openai.com/api/docs/guides/tools-skills)
- [OpenAI API: MCP connections](https://developers.openai.com/api/docs/guides/agents-api/tools/mcp)
- [OpenAI: Designing AI agents to resist prompt injection](https://openai.com/index/designing-agents-to-resist-prompt-injection/)
- [TMDB application authentication](https://developer.themoviedb.org/docs/authentication-application)
- [TMDB movie search](https://developer.themoviedb.org/reference/search-movie)
- [TMDB movie details](https://developer.themoviedb.org/reference/movie-details)
