# Azure Monitor Agents view

Status: explicit GenAI tracing implemented and locally tested; hosted ingestion and portal acceptance pending. This is an additional Stage 5 release requirement alongside [Microsoft Entra Agent ID](entra-agent-id.md).

## Target experience

Use Application Insights **Agents (Preview)** to inspect agent runs, model/tool calls, failures, latency and reported token usage. Microsoft's experience relies on OpenTelemetry generative AI semantics and requires agent data collection first. Our app is a self-hosted Microsoft Agent Framework application, even though its model inference uses Foundry.

References: [Agents view](https://learn.microsoft.com/en-us/azure/azure-monitor/app/agents-view), [agent data collection](https://learn.microsoft.com/en-us/azure/azure-monitor/app/app-insights-overview?tabs=agents).

## Current gap

The existing `control_telemetry.py` exports isolated, content-free `control.*` spans to Application Insights. These verify control telemetry delivery; they do not establish Agents view compatibility. Their separate root contexts do not provide an agent/model/tool trace hierarchy. Entra Agent ID registration alone does not close this observability gap.

## Implementation requirements

- Reuse the existing dev Application Insights resource `appi-ca-maf-agent-dev-eus2-01`. Keep stage/prod destinations and agent names distinct and reproducible through infrastructure and environment configuration.
- Add explicit agent invocation, model and MCP/tool spans using supported generative AI semantic conventions. Verify the installed framework's supported instrumentation path against our custom guarded model transport; prevent duplicate or bypass instrumentation.
- Correlate approved child operations with each run. Capture bounded model/deployment identifiers, durations, status and observed token counts. Keep conservative budget reservations distinct from actual provider usage; unknown usage must remain unknown. Any cost estimate must identify its pricing basis.
- Keep prompt, completion, system instructions, tool arguments/results, memory values, tokens, authorization headers and raw exception content excluded. Sensitive-data capture stays disabled. Test actual exported spans with synthetic sensitive canaries before hosted acceptance.
- Preserve protected Blob audit and all dispatch controls. Telemetry export is supplemental; an exporter outage must neither bypass authorization nor create unbounded work.
- Where supported, add the provisioned Entra agent identifier as validated metadata. Do not equate directory identity with telemetry display name or assume Azure Monitor joins them automatically.

## Acceptance evidence

- [ ] A real authorized dev run appears under Application Insights > Agents (Preview).
- [ ] Its transaction shows the agent, actual model inference and MCP/tool operations with correct parent/child correlation.
- [ ] Success, model failure, tool denial and cancellation have bounded metadata and interpretable status; token reporting distinguishes observed and unavailable usage.
- [ ] Azure-exported evidence contains none of the sensitive canaries or credentials. Environment routing and agent names are verified.
- [ ] Export outage/backpressure tests preserve application limits and protected audit behavior.
- [ ] Operator instructions include the verified portal path, time range, trace lookup and any unavailable preview fields. No completion claim rests solely on local spans or an existing Application Insights resource.


## Implementation checkpoint

The application-owned chat loop emits an isolated `invoke_agent` root, child `chat` spans for actual model requests and `execute_tool` spans for validated MCP reads. It shares the existing managed-identity Azure exporter without enabling global HTTP/model instrumentation or sensitive-data capture. Root responses expose a trace ID for operator lookup. Tests exercise concurrent root isolation, the actual service/transport/tool hierarchy, observed usage aggregation and failure redaction. Directory identity metadata is emitted only when Agent ID authentication is enabled. Generic control spans retain their separate context.
