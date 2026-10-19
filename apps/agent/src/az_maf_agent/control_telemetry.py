"""Explicit metadata-only tracing. No HTTP, model, or logging instrumentation."""

import re

EVENTS = frozenset(
    {
        "run_admission_authorized",
        "dispatch_authorized",
        "run_terminal",
        "session_registration_authorized",
        "simulated_action_authorized",
        "operator_bootstrap",
        "operator_policy_change",
    }
)
HEX = re.compile(r"^[0-9a-f]{64}$")
UUID = re.compile(r"^[0-9a-f-]{36}$")


class ControlTelemetry:
    def __init__(self, provider):
        self.provider = provider
        self.tracer = provider.get_tracer("az_maf_agent.controls", "1")

    def record(self, event):
        from .guardrails import CAPABILITIES

        name = event.get("event")
        if name not in EVENTS:
            return
        attributes = {"control.event": name}
        for key, pattern in (("run_id", UUID), ("scope_ref", HEX)):
            value = event.get(key)
            if isinstance(value, str) and pattern.fullmatch(value):
                attributes["control." + key] = value
        epoch = event.get("epoch")
        if type(epoch) is int and 0 < epoch < 2**63:
            attributes["control.epoch"] = epoch
        if event.get("capability") in CAPABILITIES:
            attributes["control.capability"] = event["capability"]
        if event.get("status") in {"requested", "active", "completed", "cancelled", "failed"}:
            attributes["control.status"] = event["status"]
        # No ambient parent context, exception recording, arbitrary names or attributes.
        from opentelemetry.context import Context

        with self.tracer.start_as_current_span(
            "control." + name,
            context=Context(),
            attributes=attributes,
            record_exception=False,
            set_status_on_exception=False,
        ):
            pass

    def close(self):
        self.provider.shutdown()


def azure_telemetry(connection_string):
    from azure.identity import ManagedIdentityCredential
    from azure.monitor.opentelemetry.exporter import (
        ApplicationInsightsSampler,
        AzureMonitorTraceExporter,
    )
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    exporter = AzureMonitorTraceExporter(
        connection_string=connection_string,
        credential=ManagedIdentityCredential(),
        disable_offline_storage=True,
        connection_timeout=2,
        read_timeout=2,
        retry_total=0,
    )
    provider = TracerProvider(
        resource=Resource({"service.name": "az-maf-agent-controls"}),
        sampler=ApplicationInsightsSampler(1.0),
    )
    provider.add_span_processor(
        BatchSpanProcessor(
            exporter,
            max_queue_size=256,
            max_export_batch_size=32,
            schedule_delay_millis=1000,
            export_timeout_millis=3000,
        )
    )
    return ControlTelemetry(provider)
