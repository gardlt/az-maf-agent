"""Explicit content-free GenAI spans for the application-owned agent/model/tool loop."""

import asyncio
import re
from contextlib import contextmanager, nullcontext
from contextvars import ContextVar

from opentelemetry.context import Context
from opentelemetry.trace import SpanKind, Status, StatusCode

ACTIVE_TELEMETRY = ContextVar("agent_telemetry", default=None)
CURRENT_AGENT_SPAN = ContextVar("current_agent_span", default=None)
SAFE_NAME = re.compile(r"^[a-zA-Z0-9_.-]{1,100}$")


class AgentTelemetry:
    def __init__(self, provider, name, *, agent_id=None):
        if not SAFE_NAME.fullmatch(name):
            raise ValueError("invalid telemetry agent name")
        self.tracer = provider.get_tracer("az_maf_agent.genai", "1")
        self.name = name
        self.agent_id = agent_id

    @contextmanager
    def operation(self, operation, name, *, attributes=None, root=False):
        attributes = dict(attributes or {})
        attributes["gen_ai.operation.name"] = operation
        attributes["gen_ai.agent.name"] = self.name
        if self.agent_id:
            attributes["gen_ai.agent.id"] = self.agent_id
        with self.tracer.start_as_current_span(
            operation + " " + name,
            kind=SpanKind.INTERNAL if root else SpanKind.CLIENT,
            context=Context() if root else None,
            attributes=attributes,
            record_exception=False,
            set_status_on_exception=False,
        ) as span:
            try:
                yield span
            except BaseException as exc:
                # Never export exception text, tool input, or arbitrary error codes.
                category = (
                    "cancelled" if isinstance(exc, asyncio.CancelledError) else "operation_failed"
                )
                span.set_attribute("error.type", category)
                span.set_status(Status(StatusCode.ERROR))
                raise

    @contextmanager
    def invocation(self):
        marker = ACTIVE_TELEMETRY.set(self)
        try:
            with self.operation("invoke_agent", self.name, root=True) as span:
                parent = CURRENT_AGENT_SPAN.set(span)
                try:
                    yield span
                finally:
                    CURRENT_AGENT_SPAN.reset(parent)
        finally:
            ACTIVE_TELEMETRY.reset(marker)


def operation(kind, name, **attributes):
    telemetry = ACTIVE_TELEMETRY.get()
    return (
        telemetry.operation(kind, name, attributes=attributes) if telemetry else nullcontext(None)
    )


def record_usage(span, usage):
    if span is None or not isinstance(usage, dict):
        return
    for source, target in (
        ("prompt_tokens", "input_tokens"),
        ("completion_tokens", "output_tokens"),
    ):
        value = usage.get(source)
        if type(value) is int and 0 <= value <= 24000:
            span.set_attribute("gen_ai.usage." + target, value)
            parent = CURRENT_AGENT_SPAN.get()
            if parent is not None:
                # Each invocation is one async task; child completions update serially.
                key = "gen_ai.usage." + target
                current = parent.attributes.get(key, 0) if parent.is_recording() else 0
                parent.set_attribute(key, current + value)
