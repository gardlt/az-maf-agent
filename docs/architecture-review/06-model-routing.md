# 06 — Cost-aware model routing

**Review scope:** Stage 6. **Status:** complete for the selected dev teaching scope; stronger production/evaluation claims remain outside that evidence.

## Decision and execution

The Python application chooses one approved route per run, retaining caller-managed bounded history. It does not rely on a .NET routing helper being available in Python. Routine requests use GPT-5 mini; comparison/analysis keywords or an authorized reviewed research skill select GPT-5. A trusted operator may explicitly override the route in server configuration. Prompts cannot supply deployments, endpoints, prices or permission sets.

```mermaid
flowchart LR
  I[Validated request and approved skill] --> P[Versioned routing policy]
  P --> M[Routine: GPT-5 mini]
  P --> G[Reasoning: GPT-5]
  M --> C[Same shared controls and permissions]
  G --> C
  C --> H[Conditional session history commit]
```

Both selected deployments are version `2025-08-07` in the existing Foundry account. Strict configuration pins their compatibility, window, positive finite rates and reasoning effort. Routes inherit the resource origin, identity and hard limits. The deployed app context remains 16,000 tokens, despite a larger advertised model window.

Selection is deterministic and stable for a run. It is not a semantic complexity classifier: unfamiliar/non-English wording may take the default. A caller can request analysis and incur the approved stronger-model price within existing limits; the route is not a privilege escalation. Retrieved text, saved preferences and tool output cannot reroute a run. A provider/content-policy/permission failure does not trigger automatic stronger-model fallback.

## Accounting, visibility and rollback

The per-run ledger supplies the selected settings to both the bounded movie loop and text-only client. Blob accounting resolves prices from trusted server profiles. Attempts share the same run/user/day totals, deadlines and cancellation fences. No state schema or model permission is reset by a route change.

Agent traces record the bounded route/reason/version. Correlated model spans record requested deployment, validated provider model when available, observed usage and timing; protected dispatch audit records an approved route. Prompt/completion/tool/memory contents are excluded. Entra Agent ID remains the outbound inference/MCP identity.

Prefer a routing-capable reasoning-only configuration for rollback. An older strict configuration parser requires its matching configuration without `routing`, and any older image must remain shared-state-schema-2 compatible. Never repair a rollback by discarding accounting or reverting to a schema-1-only reader. Mini provisioning is a separate reproducible Bicep module/parameter file; other environments require validated model availability/rates and their own approval.

## Measured results and tradeoffs

**E09** compares the unchanged fixed dataset/grader: 10/10 benign marker checks passed with both GPT-5 and the routine mini route, above the existing 90% floor. Estimated benign inference cost fell from **$0.02214625 to $0.00496**, or **77.6%**. Median request latency rose from **3.7395 to 5.146 seconds**. Inter-case pacing is excluded. This is one serial finite workload, not a capacity benchmark or a general equality-of-quality claim.

Azure-ingested evidence confirms 38 mini and 1 GPT-5 provider-version calls across 23 routed/probe runs. A single owned conversation moved mini → GPT-5 → mini while retaining Star Wars (1977); only the first turn needed a lookup. The 20 evaluation responses and protected audit produced no forbidden dispatches.

Rates are published list-price estimates; effective billing, cache discounts and infrastructure charges are not established by the calculation. Mini was cheaper but slower in this batch. Review **R04/R08** for stronger grounding/evaluation breadth, production-specific compatibility and effective pricing before promotion. Stage 6 does not close Stage 5 gates.

## Source and evidence references

- [Routing architecture and configuration](https://github.com/gardlt/az-maf-agent/blob/d65b5fc480a6eb8e593ac9fe0fd020dffd644b50/docs/stage-6-model-routing.md)
- [Current routing acceptance](https://github.com/gardlt/az-maf-agent/blob/d65b5fc480a6eb8e593ac9fe0fd020dffd644b50/docs/validation/stage-6-model-routing.md)
- [Actual Azure model trace/usage evidence](https://github.com/gardlt/az-maf-agent/blob/d65b5fc480a6eb8e593ac9fe0fd020dffd644b50/docs/validation/stage-6-traces.json)
- [Strict server routing profiles](https://github.com/gardlt/az-maf-agent/blob/d65b5fc480a6eb8e593ac9fe0fd020dffd644b50/apps/agent/src/az_maf_agent/config.py)
- [Deterministic router](https://github.com/gardlt/az-maf-agent/blob/d65b5fc480a6eb8e593ac9fe0fd020dffd644b50/apps/agent/src/az_maf_agent/routing.py)
- [Routing regression tests](https://github.com/gardlt/az-maf-agent/blob/d65b5fc480a6eb8e593ac9fe0fd020dffd644b50/apps/agent/tests/test_routing.py)
- [Mini Bicep module](https://github.com/gardlt/az-maf-agent/blob/d65b5fc480a6eb8e593ac9fe0fd020dffd644b50/infra/modules/foundry-routing-model.bicep)
- [Dev mini parameters](https://github.com/gardlt/az-maf-agent/blob/d65b5fc480a6eb8e593ac9fe0fd020dffd644b50/infra/routing-model.dev.bicepparam)

Related: [review index](README.md), [evidence register](09-evidence-register.md), [open review gates](10-review-gaps.md).
