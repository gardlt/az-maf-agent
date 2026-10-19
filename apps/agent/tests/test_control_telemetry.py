import json

from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from az_maf_agent.control_telemetry import ControlTelemetry


def test_exported_span_excludes_content_and_arbitrary_metadata():
    exporter = InMemorySpanExporter()
    provider = TracerProvider(resource=Resource({"service.name": "test"}))
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    telemetry = ControlTelemetry(provider)
    secret = "PROMPT_SECRET_CANARY"
    telemetry.record(
        {
            "event": "dispatch_authorized",
            "epoch": 2,
            "capability": "model",
            "scope_ref": "a" * 64,
            "prompt": secret,
            "error": secret,
            "run_id": secret,
            "status": secret,
        }
    )
    telemetry.record({"event": secret})
    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    exported = json.loads(spans[0].to_json())
    assert secret not in json.dumps(exported)
    assert exported["attributes"]["control.epoch"] == 2
    assert exported["events"] == []
    telemetry.close()


def test_actual_azure_exporter_constructs_without_network_or_auxiliary_telemetry(monkeypatch):
    from az_maf_agent.control_telemetry import azure_telemetry

    monkeypatch.delenv("APPLICATIONINSIGHTS_CONNECTION_STRING", raising=False)
    for name in (
        "APPLICATIONINSIGHTS_STATSBEAT_DISABLED_ALL",
        "APPLICATIONINSIGHTS_SDKSTATS_DISABLED",
        "APPLICATIONINSIGHTS_CONTROLPLANE_DISABLED",
    ):
        monkeypatch.setenv(name, "true")
    telemetry = azure_telemetry(
        "InstrumentationKey=00000000-0000-0000-0000-000000000000;"
        "IngestionEndpoint=https://example.invalid/"
    )
    telemetry.close()  # No spans: construction/shutdown must not need a token or endpoint.
