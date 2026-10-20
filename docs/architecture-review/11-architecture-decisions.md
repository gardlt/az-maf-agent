# 11 — Architecture decision register

This register consolidates selected design decisions for review. **Selected** means implemented or user-selected in the recorded dev scope; it does not mean approved by an architecture board. The detailed integration pages and evidence remain authoritative for scope and limitations.

| Decision | Selected pattern and rationale | Alternatives / tradeoff | Reconsideration trigger |
| --- | --- | --- | --- |
| ADR01 — Hosting | CLI → authenticated Python API on Container Apps; separate agent core keeps teaching and deployment boundaries visible | Foundry-hosted agents, another app host or APIM introduce a different runtime/gateway boundary; no APIM is selected now | Required governance/gateway feature or a measured operations need |
| ADR02 — Service packaging | One monorepo with separate agent and FastMCP packages/images; the MCP isolates its TMDB credential and narrow contract | In-process tools reduce deployments but combine credentials/failure boundaries; separate repos add coordination cost | Independent ownership/release scaling beyond current workspace |
| ADR03 — Catalog | TMDB is the sole movie source; expose only bounded search/details GET operations | Synthetic writable catalog was retired; arbitrary HTTP/write tools would materially broaden authority | A separately approved domain/write requirement with a new control/evaluation design |
| ADR04 — Skills | Git-reviewed ID/version/digest registry and bounded Markdown; guidance intersects existing capabilities | Marketplace loading, executable/composed skills or external signing require additional integrity/provenance and supply-chain controls | Registry scale, artifact distribution or signing requirements |
| ADR05 — Preferences | Structured per-user/purpose Blob document, explicit consent, 30-day expiry, no dev backup/version history | AI Search/vector/graph storage adds derived copies, deletion semantics and retrieval uncertainty without improving exact enums | Semantic retrieval becomes a demonstrated requirement; evaluate tenant partition and full deletion first |
| ADR06 — Shared state | Blob ETag transactions for small-workload control/accounting and separate short-term sessions | Database/queue infrastructure may better support higher throughput/partitioning, but adds cost and operational scope | Measured contention, document growth, partitioning or stronger transactional requirements |
| ADR07 — Identity | User token for incoming scope; Agent ID for inference/MCP; workload identity for infrastructure; independent operator | A single all-purpose identity obscures least privilege and actor attribution; a user-token forwarding design changes consent/delegation | New downstream compatibility or on-behalf-of use case, reviewed explicitly |
| ADR08 — Observability | Explicit content-free correlated GenAI spans plus separate required protected audit | Broad auto-instrumentation/content capture risks secret/private payload exposure; trace-only logging is not authoritative dispatch audit | A concrete diagnostic requirement with reviewed minimization, retention and redaction |
| ADR09 — Routing | Deterministic per-run mini/GPT-5 selection; no automatic fallback; same history/accounting | Managed router endpoint or an extra model router may broaden capability/price uncertainty and cost more to decide; single GPT-5 is simpler but higher routine cost | Broader quality/latency/cost evidence shows the heuristic insufficient |
| ADR10 — Networking | Preserve working apps in current environment while separately preparing migration; keep ACR Basic per user choice | Premium registry/dedicated data endpoints were reviewed and declined; the parallel firewall foundation is not current app egress enforcement | Approved Basic-compatible image delivery and final-topology deployment/test plan |
| ADR11 — Release gate | Non-root digest-pinned images; unresolved High/Critical findings block release; local scanners before push | Accepting those severities or uploading image layers to Docker Scout is not selected; lower severities still need disposition | New findings, base/model/runtime changes or a reviewed exception process |
| ADR12 — Documentation | Local `docs/architecture-review/` package with stage pages and immutable evidence links, per current user direction | Confluence publication is deferred; no connection, destination or rendering assumption is needed for the local package | Explicit later publication request with selected site/space and verified integration |

## Consequences reviewers should retain

Application-owned controls provide inspection and testability, but also create implementation, review and operational obligations. A readable rule or a diagram does not establish deployed correctness. Independent packages do not guarantee independent auto-deploy on every merge: the current main deployment path targets the full dev environment, while manual targeted service deployment is available.

Blob ETags are per-object coordination, not a multi-object transaction. Audit retention is Unlocked. Dev omits backups by explicit decision. These are deliberate bounded choices, not generic enterprise defaults. Future backup, concurrency, throughput or privileged-write requirements need their own decisions and evidence.

Routing's measured 77.6% routine inference cost reduction comes with slower median latency in the fixed batch. Its keyword rule is explainable but not semantic certainty. Retain model-specific quality checks and do not use a stronger route to override a safety denial.

## Change procedure

Give new decisions an ID and state the concrete trigger, selected option, alternatives, impact on data/identity/network/cost, evidence needed and approval authority. Preserve superseded decisions and tested release boundaries. Do not rewrite historical experiment evidence to appear current.

## Source and evidence references

- [Initial specification and decision register, extended by Stage 6](https://github.com/gardlt/az-maf-agent/blob/d65b5fc480a6eb8e593ac9fe0fd020dffd644b50/docs/secure-agent-teaching-spec.md)
- [MCP/TMDB integration choice](https://github.com/gardlt/az-maf-agent/blob/d65b5fc480a6eb8e593ac9fe0fd020dffd644b50/docs/tmdb-integration.md)
- [Memory decision and lifecycle](https://github.com/gardlt/az-maf-agent/blob/d65b5fc480a6eb8e593ac9fe0fd020dffd644b50/docs/stage-4-memory.md)
- [Approved shared control contract](https://github.com/gardlt/az-maf-agent/blob/d65b5fc480a6eb8e593ac9fe0fd020dffd644b50/docs/stage-5-production-guardrails.md)
- [Selected registry/network decision](https://github.com/gardlt/az-maf-agent/blob/d65b5fc480a6eb8e593ac9fe0fd020dffd644b50/docs/stage-5-network-migration-review.md)
- [Routing tradeoffs and measurements](https://github.com/gardlt/az-maf-agent/blob/d65b5fc480a6eb8e593ac9fe0fd020dffd644b50/docs/validation/stage-6-model-routing.md)

Related: [review index](README.md), [evidence register](09-evidence-register.md), [open review gates](10-review-gaps.md).

## ADR13 — Per-agent containment (implementation started; hosted boundary open)

Select the individual Entra Agent ID as the directory disable target, with independent quarantine and service-specific denial as separate required controls. Never disable a shared blueprint or shared managed identity to contain one agent. Manual emergency disable uses the Entra portal; automated disable uses a verified typed Graph identity and disabled readback. Recovery requires explicit operator authorization.

The alternative of directory disable alone failed the all-resource objective in the [live drill](../stages/stage-7/validation/live-disable-drill-2026-10-20.md): cached Foundry/MCP tokens and native workload-identity Blob access continued. SQLite is a local development adapter only, not the selected hosted store. Reconsider isolation/broker/resource topology before controller deployment whenever credentials or services cannot meet the approved denial bound. Graph privilege scope, service enforcement and production backend are unresolved decisions, not board-approved architecture.
