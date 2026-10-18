"""Offline default; hosted mode sends only a bearer token, never a claimed identity."""

import argparse
import asyncio
import logging
import os
import sys

import httpx
from azure.core.exceptions import ClientAuthenticationError

from .client_auth import acquire_stage1_token
from .config import load_settings
from .core import LOCAL, Service, safe_text
from .model import Denied


def device_code_prompt(verification_uri, user_code, expires_on):
    print(f"Open {verification_uri} and enter code {user_code}.", file=sys.stderr)
    print(
        f"The code expires at {expires_on.astimezone().isoformat(timespec='minutes')}",
        file=sys.stderr,
    )


async def run(args):
    settings = load_settings(args.config)
    if not args.api and settings.mode != "fake":
        raise Denied("live_requires_authenticated_api")
    if args.api and (not args.api.startswith("https://") or "@" in args.api):
        raise Denied("https_api_required")
    service = None if args.api else Service(settings)
    client = None
    if args.api:
        token = os.environ.get("AGENT_ACCESS_TOKEN")
        if not token:
            token = acquire_stage1_token(device_code_prompt)
        client = httpx.AsyncClient(
            base_url=args.api,
            headers={"Authorization": "Bearer " + token},
            follow_redirects=False,
            timeout=settings.limits.run_seconds + 10,
        )

    async def remote(path, body=None):
        response = await client.post(path, json=body)
        if response.status_code in (401, 403):
            raise Denied(
                "authenticate_again" if response.status_code == 401 else "permission_denied"
            )
        if response.status_code != 200:
            raise Denied("api_request_failed")
        return response.json()

    try:
        session = await remote("/sessions") if client else service.create(LOCAL)
        sid, revision = session["session_id"], session["revision"]
        print("Text-only chat. /reset clears history; /quit exits. Ctrl-C cancels the active run.")
        while True:
            # Blocking input is only used when no model operation is active.
            try:
                text = input("> ")
            except EOFError:
                break
            if text == "/quit":
                break
            if text == "/reset":
                result = (
                    await remote(f"/sessions/{sid}/reset") if client else service.reset(LOCAL, sid)
                )
                revision = result["revision"]
                print("History reset; usage limits remain.")
                continue
            try:
                result = (
                    await remote(f"/sessions/{sid}/chat", {"text": text, "revision": revision})
                    if client
                    else await service.chat(LOCAL, sid, text, revision)
                )
                revision = result["revision"]
                print(safe_text(result["text"]))
            except Denied as exc:
                print(exc.code, file=sys.stderr)
            except asyncio.CancelledError:
                if client:
                    # Explicit server cancellation; disconnect alone is not a cancellation receipt.
                    try:
                        await asyncio.shield(remote(f"/sessions/{sid}/cancel"))
                    except Exception:
                        print(
                            "Cancellation unconfirmed; server deadline still applies.",
                            file=sys.stderr,
                        )
                raise
    finally:
        if service:
            await service.close()
        if client:
            await client.aclose()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/offline.json")
    parser.add_argument(
        "--api", help="Approved HTTPS API origin; uses an encrypted local Entra token cache"
    )
    args = parser.parse_args()
    # Do not allow third-party diagnostics to emit provider payloads.
    logging.getLogger("agent_framework").setLevel(logging.CRITICAL)
    logging.getLogger("azure").setLevel(logging.CRITICAL)
    try:
        asyncio.run(run(args))
    except KeyboardInterrupt:
        print("Cancelled.", file=sys.stderr)
        raise SystemExit(130)
    except (ClientAuthenticationError, Denied, OSError, ValueError, httpx.HTTPError):
        print(
            "Unable to start/continue chat; check approved configuration and authentication.",
            file=sys.stderr,
        )
        raise SystemExit(2)


if __name__ == "__main__":
    main()
