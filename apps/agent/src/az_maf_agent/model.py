"""Text-only clients: no function invocation wrapper and no tool registration."""

import asyncio
import json
import random
from contextvars import ContextVar
from dataclasses import dataclass
from decimal import Decimal

import httpx
from agent_framework import BaseChatClient, ChatResponse, Message
from azure.identity.aio import ManagedIdentityCredential

from .config import Settings


class Denied(Exception):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


class ProviderRejected(Denied):
    def __init__(self, status, category="request_rejected"):
        self.status = status
        self.category = category
        super().__init__("provider_rejected")


class Transient(Exception):
    def __init__(self, rejected=False):
        self.rejected = rejected


def tokens(text: str) -> int:
    # Conservative UTF-8 byte bound for supported text/BPE models, not exact billing.
    try:
        return len(text.encode("utf-8"))
    except UnicodeEncodeError:
        raise Denied("invalid_encoding") from None


def message_tokens(messages) -> int:
    return 512 + sum(tokens(m.text) + 16 for m in messages)


@dataclass
class Ledger:
    settings: Settings
    reserve_daily: object
    calls: int = 0
    reserved_tokens: int = 0
    reserved_usd: Decimal = Decimal(0)
    actual_tokens: int = 0
    shared_reserve: object = None
    shared_reconcile: object = None
    shared_reject: object = None

    def reserve(self, count: int):
        s, lim = self.settings, self.settings.limits
        total = count + lim.output_tokens
        cost = (
            Decimal(str(s.input_usd_per_million or 0)) * count
            + Decimal(str(s.output_usd_per_million or 0)) * lim.output_tokens
        ) / 1_000_000
        if (
            self.calls >= lim.turns
            or self.reserved_tokens + total > lim.run_tokens
            or self.reserved_usd + cost > Decimal(str(lim.run_usd))
        ):
            raise Denied("run_budget")
        self.reserve_daily(cost)
        self.calls += 1
        self.reserved_tokens += total
        self.reserved_usd += cost
        # Reservations are never refunded: failed/ambiguous requests may be billed.

    async def areserve(self, count):
        self.reserve(count)
        if self.shared_reserve is not None:
            return await self.shared_reserve(count)
        return self.calls

    async def reconcile(self, call_number, actual):
        if self.shared_reconcile is not None:
            await self.shared_reconcile(call_number, actual)
        self.actual_tokens += actual

    async def reject(self, call_number, status):
        if self.shared_reject is not None:
            await self.shared_reject(call_number, status)


async def isolated_provider_call(awaitable, ledger, call_number):
    """A cancellation-resistant adapter cannot hold its parent or commit history."""
    task = asyncio.create_task(awaitable)
    try:
        return await asyncio.shield(task)
    except asyncio.CancelledError:
        task.cancel()

        def settled(done):
            if done.cancelled():
                return
            error = done.exception()
            reconciliation = None
            if isinstance(error, ProviderRejected) and ledger.shared_reject is not None:
                reconciliation = asyncio.create_task(
                    ledger.shared_reject(call_number, error.status)
                )
            elif (
                isinstance(error, Transient) and error.rejected and ledger.shared_reject is not None
            ):
                reconciliation = asyncio.create_task(ledger.shared_reject(call_number, 429))
            elif error is None and ledger.shared_reconcile is not None:
                result = done.result()
                actual = result[-1] if isinstance(result, tuple) else None
                if type(actual) is int and actual >= 0:
                    reconciliation = asyncio.create_task(
                        ledger.shared_reconcile(call_number, actual)
                    )
            if reconciliation is not None:
                reconciliation.add_done_callback(
                    lambda completed: completed.exception() if not completed.cancelled() else None
                )

        task.add_done_callback(settled)
        raise


CURRENT_LEDGER: ContextVar[Ledger] = ContextVar("ledger")


class FakeTransport:
    async def complete(self, messages, settings):
        turns = sum(m.role == "user" for m in messages)
        return f"Offline reply: {turns} user message(s) in bounded context. No tools available.", 0

    async def close(self):
        pass


class AzureTransport:
    def __init__(self, settings: Settings, *, credential=None):
        self.credential = credential or ManagedIdentityCredential(
            client_id=settings.managed_identity_client_id
        )
        self.http = httpx.AsyncClient(follow_redirects=False, timeout=settings.limits.call_seconds)

    async def complete(self, messages, settings):
        payload = {
            "messages": [{"role": m.role, "content": m.text} for m in messages],
            "max_completion_tokens": settings.limits.output_tokens,
            "store": False,
        }
        obj = await self._request(payload, settings)
        try:
            choice = obj["choices"][0]
            message = choice["message"]
            if (
                message.get("tool_calls")
                or message.get("function_call")
                or choice.get("finish_reason") in ("tool_calls", "function_call")
            ):
                raise Denied("tools_disabled")
            if message.get("role") != "assistant":
                raise Denied("tools_disabled")
            return message["content"], self._usage(obj, settings)
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise Denied("provider_shape") from exc

    async def complete_tool_turn(self, messages, settings):
        """Return one raw tool-capable turn; the application validates its actions."""
        from .movie_mcp import CONTRACT

        payload = {
            "messages": messages,
            "tools": [
                {"type": "function", "function": {"name": name, "parameters": schema}}
                for name, schema in CONTRACT.items()
            ],
            "tool_choice": "auto",
            "parallel_tool_calls": False,
            "max_completion_tokens": settings.limits.output_tokens,
            "store": False,
        }
        obj = await self._request(payload, settings)
        try:
            choice = obj["choices"][0]
            return choice["message"], choice.get("finish_reason"), self._usage(obj, settings)
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise Denied("provider_shape") from exc

    @staticmethod
    def _usage(obj, settings):
        usage = obj["usage"]
        total, output = usage["total_tokens"], usage["completion_tokens"]
        if (
            type(total) is not int
            or type(output) is not int
            or total < output
            or output < 0
            or output > settings.limits.output_tokens
        ):
            raise Denied("provider_usage")
        return total

    async def _request(self, payload, settings):
        from .agent_telemetry import operation, record_usage

        with operation(
            "chat",
            settings.deployment,
            **{
                "gen_ai.system": "azure.ai.openai",
                "gen_ai.provider.name": "azure.ai.openai",
                "gen_ai.request.model": settings.deployment,
            },
        ) as span:
            result = await self._send_request(payload, settings)
            # Only validated observed usage; reservations are not usage metrics.
            try:
                total = self._usage(result, settings)
            except (KeyError, IndexError, TypeError, ValueError, Denied):
                pass  # Existing response validation retains its original denial precedence.
            else:
                output = result["usage"]["completion_tokens"]
                record_usage(span, {"prompt_tokens": total - output, "completion_tokens": output})
            return result

    async def _send_request(self, payload, settings):
        if settings.reasoning_effort is not None:
            payload["reasoning_effort"] = settings.reasoning_effort
        try:
            token = await self.credential.get_token("https://cognitiveservices.azure.com/.default")
            url = (
                settings.endpoint.rstrip("/")
                + "/openai/deployments/"
                + settings.deployment
                + "/chat/completions"
            )
            async with self.http.stream(
                "POST",
                url,
                params={"api-version": settings.api_version},
                headers={"Authorization": "Bearer " + token.token},
                json=payload,
            ) as response:
                if response.status_code == 429:
                    raise Transient(rejected=True)
                if response.status_code in {400, 401, 403, 404, 405, 413, 415, 422}:
                    error_bytes = bytearray()
                    async for chunk in response.aiter_bytes(chunk_size=4096):
                        error_bytes.extend(chunk)
                        if len(error_bytes) > 16384:
                            break
                    category = "request_rejected"
                    try:
                        error = json.loads(error_bytes).get("error", {})
                        codes = {error.get("code"), error.get("innererror", {}).get("code")}
                        if codes & {"content_filter", "ResponsibleAIPolicyViolation"}:
                            category = "content_policy"
                    except (ValueError, TypeError, AttributeError):
                        pass
                    print(
                        json.dumps(
                            {
                                "event": "provider_request_rejected",
                                "status": response.status_code,
                                "category": category,
                            }
                        ),
                        flush=True,
                    )
                    raise ProviderRejected(response.status_code, category)
                if response.status_code in (500, 502, 503, 504):
                    raise Transient()
                if response.status_code != 200:
                    raise Denied("provider_failure")
                data = bytearray()
                async for chunk in response.aiter_bytes():
                    data.extend(chunk)
                    if len(data) > 65536:
                        raise Denied("provider_size")
            obj = json.loads(data)
            return obj
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            raise Transient() from exc
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise Denied("provider_shape") from exc

    async def close(self):
        await self.http.aclose()
        await self.credential.close()


class GuardedClient(BaseChatClient):
    def __init__(self, settings, transport):
        super().__init__()
        self.settings, self.transport = settings, transport

    async def _inner_get_response(self, *, messages, stream, options, **kwargs):
        if stream or options.get("tools"):
            raise Denied("tools_or_streaming_disabled")
        messages = list(messages)
        if options.get("instructions"):
            messages.insert(0, Message("system", [options["instructions"]]))
        if any(
            m.role not in ("system", "user", "assistant")
            or any(c.type != "text" for c in m.contents)
            for m in messages
        ):
            raise Denied("non_text_message")
        count = message_tokens(messages)
        lim = self.settings.limits
        if count > lim.context_tokens:
            raise Denied("context_limit")
        ledger = CURRENT_LEDGER.get()
        for attempt in range(lim.retries + 1):
            call_number = await ledger.areserve(count)
            try:
                async with asyncio.timeout(lim.call_seconds):
                    text, actual = await isolated_provider_call(
                        self.transport.complete(messages, self.settings), ledger, call_number
                    )
                if not isinstance(text, str) or not text or tokens(text) > lim.output_tokens:
                    raise Denied("output_limit")
                if type(actual) is not int or actual < 0 or actual > count + lim.output_tokens:
                    raise Denied("provider_usage")
                await ledger.reconcile(call_number, actual)
                return ChatResponse(messages=[Message("assistant", [text])])
            except ProviderRejected as exc:
                await ledger.reject(call_number, exc.status)
                raise
            except Transient as exc:
                if exc.rejected:
                    await ledger.reject(call_number, 429)
                if attempt == lim.retries:
                    raise Denied("retry_exhausted") from None
                await asyncio.sleep(random.uniform(0, min(0.1 * 2**attempt, 1.0)))
            except TimeoutError:
                raise Denied("call_timeout") from None
