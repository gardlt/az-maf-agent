# Stage 5 dev Agent ID and generative AI tracing acceptance

Validated on 2026-10-19, America/Chicago. Scope: the existing dev Container Apps environment. Stage/prod directory provisioning and rollout are not included.

Source release: `e038ca38b7f5ee20263250d49a07839e572316a1`. [Deployment workflow](https://github.com/gardlt/az-maf-agent/actions/runs/39356709651) succeeded after both built images passed the existing High/Critical gate. The earlier `bad38a7` attempt stopped at an MCP smoke-test configuration error before app rollout; its successful agent scan alone was not counted as a complete release.

## Verified results

| Check | Observed result | Evidence |
| --- | --- | --- |
| Dev Agent ID provisioning | Blueprint and agent created; repeat run reused them | [Directory objects and scoped MCP role](stage-5-evidence/agent-id-provisioning.json) |
| Actual deployed token acquisition | Both Cognitive Services and MCP tokens identify agent `94a137c6-e4fc-481c-b45d-f2a03d868ba4`; no raw tokens retained | [Selected claims from revision 30](stage-5-evidence/agent-id-runtime-token-claims.json) |
| Token caching | Repeated requests reused the actual agent token for both resource audiences | [Runtime cache checks](stage-5-evidence/agent-id-runtime-token-claims.json) |
| Controlled recovery | Epoch 5 → 6; all 187 existing run records and daily accounting preserved; no runs still marked unresolved; prior contained unknown usage retained | [Recovery](stage-5-evidence/agent-id-recovery.json) |
| Actual downstream use | Hosted authorized chat completed two model calls and one MCP read; runtime inference/MCP adapters have no workload-token fallback | [Hosted canary](stage-5-evidence/agent-id-hosted-canary.json) |
| Ingress | Missing user token 401; authorized canary 200 | [Hosted canary](stage-5-evidence/agent-id-hosted-canary.json) |
| Azure trace correlation | One `invoke_agent`, two `chat`, one `execute_tool` span; all children reference the same agent root | [Actual Azure-ingested spans](stage-5-evidence/agent-id-correlated-azure-spans.json) |
| Observed usage | Root reports 617 input / 47 output tokens, aggregated from actual model responses | [Actual Azure-ingested spans](stage-5-evidence/agent-id-correlated-azure-spans.json) |
| Content exclusion | Synthetic prompt canary and forbidden message/tool-content attributes absent from ingested trace | [Redaction checks](stage-5-evidence/agent-id-correlated-azure-spans.json) |
| Supply-chain gate | Both built images: zero High / Critical; remaining lower-severity findings retained | [Scan summaries](stage-5-evidence/agent-id-image-scans.json) |
| Local regression | 190 tests pass; lint and formatting pass; CI passed | [CI run](https://github.com/gardlt/az-maf-agent/actions/runs/39356709563) |
| Application Insights Agents (Preview) portal | Pending browser sign-in and visual verification | Open acceptance item below |

Trace ID: `757f1ad59529577c74c644d043f9da06`. Run ID: `32b944a6-28aa-463f-adc1-36613e3af165`. No answer or conversation content is retained in this report.

## Remaining portal check

Sign in to Azure portal, open `appi-ca-maf-agent-dev-eus2-01`, select **Agents (Preview)**, and select `agent-maf-dev`. Use the last 24 hours and inspect the trace above. Confirm the agent, model and MCP tool are rendered in the same transaction. Actual Azure ingestion is already verified programmatically; it is not substituted for this portal check.

## Reproduce

```sh
uv run --locked python scripts/test_agent_identity_observability.py --report /private/tmp/agent-id-canary.json
uv run --locked python scripts/verify_agent_traces.py --canary-report /private/tmp/agent-id-canary.json --workspace 244ef22a-576b-4e7d-a41e-d64884fb7def --report /private/tmp/agent-id-spans.json
```

The canary requires cached user authentication, an explicitly recovered policy and the configured dev release. Wait for ingestion before running the trace verifier. Each canary makes bounded billable model calls; do not repeat merely to poll telemetry.

The agent identity has scoped Foundry User and MCP Catalog.Read access. Infrastructure access remains on managed identity, and legacy grants are retained for controlled rollback. This report does not establish retirement of every old workload permission, instant token revocation, Agent 365 governance, or completion of the other Stage 5 release gates.
