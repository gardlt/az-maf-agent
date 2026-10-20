# Stage 6 — Application-controlled model routing

The Python application selects an approved Foundry deployment once per run. Routine movie reads use `gpt-5-mini`; comparison/analysis requests and an authorized, hash-verified `movie-research` skill use `gpt-5`. Conversation history stays in the application session, so a later run can change models without losing bounded context.

## Policy v1

Selection order is: operator override, verified research skill, comparison/analysis keyword, routine default. The bounded whole-word expression recognizes compare, contrast, tradeoff/trade-off (including plurals), analyze/analyse and analysis, ignoring case. Ambiguous and non-English requests default to mini. This is a predictable teaching policy, not a semantic complexity classifier. A caller can request comparison work and thereby incur the approved stronger-model price within the same hard limits; this grants no additional capability. Names of models in a prompt do not select arbitrary deployments.

`config/foundry-stage1.json` retains its historical filename for deployment compatibility and adds `routing.version`, `routing.mode`, `routing.routine` and `routing.reasoning`. Each route pins deployment, API version, reasoning effort, context window and positive finite input/output prices. Routes inherit the same validated resource origin, identity and limits. They cannot specify another endpoint, token audience or permission set. Configurations without `routing` retain single-model behavior.

| Route | Deployment/version | Context | Reasoning | Input/output USD per million tokens |
| --- | --- | --- | --- | --- |
| routine | gpt-5-mini / 2025-08-07 | 400,000 | minimal | 0.25 / 2.00 |
| reasoning | gpt-5 / 2025-08-07 | 400,000 | minimal | 1.25 / 10.00 |

Rates are published list-price estimates, not an invoice or a contractual price. [Microsoft's published Foundry table](https://devblogs.microsoft.com/foundry/whats-new-in-azure-ai-foundry-august-2025/) and the [current model vendor pricing](https://developers.openai.com/api/docs/models/gpt-5-mini) agree on mini's rates. Azure's pricing page rendered placeholders and the queried retail API meters returned no matches during this check; review the subscription's effective rates before billing-sensitive promotion. Cached-input discounts are not assumed. For identical input/output token counts mini costs 80% less; actual savings also depend on token use, model choices and retries.

## Enforcement and identity

The actual bounded movie/model loop and framework text-only client both use the per-run selection. The selected settings live in the request's ledger, avoiding shared mutable client state. Both local accounting and Blob transactional accounting resolve the selected price from trusted configuration. All attempts share existing run/user/day counters, turns, concurrency and deadlines. Reservations remain conservative and are never refunded, including ambiguous failures. No state-schema change is introduced.

No fallback is enabled. An unavailable deployment fails under the existing bounded retry rules; content-policy and known terminal provider rejections do not cause a stronger-model retry. Existing unknown-outcome reconciliation, cancellation, session/reset fences, global stop and tool validation remain in force. Switching models cannot add a tool, write TMDB, choose a different user or clear policy. Entra Agent ID supplies the same scoped downstream token for both deployments in the account; no new runtime role is needed.

Agent spans include route, bounded reason and policy version; model spans include requested deployment, validated provider-reported model when supplied and observed input/output usage. Protected dispatch audit includes the selected route. Routing telemetry never includes the triggering prompt or saved preferences.

## Reproduce and operate

The standalone `infra/modules/foundry-routing-model.bicep` and `infra/routing-model.dev.bicepparam` provision only mini in the existing account's resource group:

```sh
az deployment group what-if -g rg-homelab-foundry --parameters infra/routing-model.dev.bicepparam
az deployment group create -g rg-homelab-foundry --name stage6-routing-model --parameters infra/routing-model.dev.bicepparam
uv run --locked pytest -q
uv run --locked agent-chat --config config/foundry-stage1.json --api https://ca-maf-agent-dev-eus2-01.kindisland-49d1cad2.eastus2.azurecontainerapps.io
```

For a local single-model baseline, use a separate trusted copy with `routing` removed. For a controlled dev override set `routing.mode` to `routine` or `reasoning`, commit and deploy through the existing gated agent workflow; restore `auto` afterward. Requests cannot set this override. Do not increase budgets for evaluation or reset quotas to make a test pass.

For rollback, prefer a routing-capable image with `routing.mode=reasoning`. If reverting to an older schema-2-compatible application image, use its matching configuration without `routing`; older strict configuration parsers reject the new field. Never revert to a schema-1-only control-state reader. Retain policy epochs, reservations, sessions and audit; do not delete the mini deployment while an active revision references it. Stage/prod deployment requires environment-specific model/price validation.

## Acceptance

Track tasks in [Stage 6](tasks/stage-6-model-routing.md). The frozen evaluation reuses `config/stage5-evaluation.json`, grader v3 and the existing 90% benign floor. Compare against a fresh GPT-5 baseline before changing the default. Inspect actual traces, protected dispatch events and before/after state; a refusal or HTTP 200 alone does not prove safety. The new route does not close remaining Stage 5 cross-user, network or operational release gates.
