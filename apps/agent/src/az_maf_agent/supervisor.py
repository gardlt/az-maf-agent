"""Async bounded supervision around the synchronous transactional control adapter."""

import asyncio
import contextlib
import uuid
from contextlib import asynccontextmanager

from .model import Denied


class SafetySupervisor:
    def __init__(self, controls):
        self.controls = controls
        self.pending = set()

    async def call(self, function, *args, **kwargs):
        if len(self.pending) >= 24:
            raise Denied("control_backpressure")
        task = asyncio.create_task(asyncio.to_thread(function, *args, **kwargs))
        self.pending.add(task)

        def settled(done):
            self.pending.discard(done)
            if not done.cancelled():
                done.exception()

        task.add_done_callback(settled)
        try:
            async with asyncio.timeout(5):
                return await asyncio.shield(task)
        except TimeoutError:
            # Do not retry: a reservation or receipt may have committed remotely.
            raise Denied("control_timeout") from None

    @asynccontextmanager
    async def run(self, principal, run_id=None, fence=None):
        run_id = run_id or str(uuid.uuid4())
        admitted = await self.call(self.controls.start, principal, run_id)
        run = SupervisedRun(self, principal, run_id, admitted["epoch"])
        run.fence = fence
        parent = asyncio.current_task()
        reason = []

        async def watchdog():
            try:
                while True:
                    await asyncio.sleep(admitted["poll_seconds"])
                    await run.gate()
            except Denied as exc:
                reason.append(exc.code)
                parent.cancel()
            except asyncio.CancelledError:
                raise
            except Exception:
                reason.append("control_unavailable")
                parent.cancel()

        watcher = asyncio.create_task(watchdog())
        status = "failed"
        try:
            yield run
            status = "completed"
        except asyncio.CancelledError:
            status = "cancelled"
            if reason:
                raise Denied(reason[0]) from None
            raise
        finally:
            watcher.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await watcher
            # Best-effort terminal bookkeeping cannot reopen authority or refund quotas.
            # Failure leaves a bounded lease, and admission/dispatch still fail closed.
            with contextlib.suppress(Denied):
                await self.call(self.controls.finish, principal, run_id, run.epoch, status)

    async def operation(self, principal, capabilities, callback, run_id=None, fence=None):
        async with self.run(principal, run_id, fence=fence) as run:
            for capability in capabilities:
                await run.gate(capability)
            result = await callback()
            await run.gate()
            return result

    async def close(self):
        if self.pending:
            await asyncio.gather(*list(self.pending), return_exceptions=True)
        await asyncio.to_thread(self.controls.backend.close)


class SupervisedRun:
    def __init__(self, supervisor, principal, run_id, epoch):
        self.supervisor, self.principal, self.run_id, self.epoch = (
            supervisor,
            principal,
            run_id,
            epoch,
        )

    async def gate(self, capability=None, **arguments):
        result = await self.supervisor.call(
            self.supervisor.controls.gate,
            self.principal,
            self.run_id,
            self.epoch,
            capability,
            **arguments,
        )

        if getattr(self, "fence", None) is not None:
            await self.fence()
        return result

    async def reserve(self, count):
        state = await self.gate("model", count=count)
        return state["calls"]

    async def reconcile(self, call_number, actual_tokens):
        return await self.supervisor.call(
            self.supervisor.controls.reconcile,
            self.principal,
            self.run_id,
            call_number,
            actual_tokens,
        )

    async def reject(self, call_number, status):
        return await self.supervisor.call(
            self.supervisor.controls.reject, self.principal, self.run_id, call_number, status
        )
