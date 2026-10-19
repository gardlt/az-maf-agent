#!/usr/bin/env python3
"""Confirm that a Stage 1 Container App restart loses its in-memory session."""

import argparse
import os
import sys
import time
from datetime import datetime

import httpx
from azure.core.exceptions import ClientAuthenticationError

from az_maf_agent.client_auth import acquire_stage1_token


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api", required=True, help="HTTPS Container App origin")
    parser.add_argument("--wait-after-create", type=int, default=90, choices=range(30, 121))
    return parser.parse_args()


def device_code_prompt(verification_uri: str, user_code: str, expires_on: datetime) -> None:
    print(f"Open {verification_uri} and enter code {user_code}.", file=sys.stderr)
    print(
        f"The code expires at {expires_on.astimezone().isoformat(timespec='minutes')}.",
        file=sys.stderr,
    )


def token() -> str:
    existing = os.environ.get("AGENT_ACCESS_TOKEN")
    if existing:
        return existing
    try:
        return acquire_stage1_token(device_code_prompt)
    except ClientAuthenticationError as exc:
        raise RuntimeError("Entra device-code sign-in did not complete") from exc


def main() -> int:
    args = parse_args()
    try:
        with httpx.Client(
            base_url=args.api.rstrip("/"),
            headers={"Authorization": f"Bearer {token()}"},
            follow_redirects=False,
            timeout=30,
        ) as client:
            created = client.post("/sessions")
            print(f"create before restart: HTTP {created.status_code}")
            if created.status_code != 200:
                raise RuntimeError("could not create restart-test session")
            session_id = created.json()["session_id"]
            print(f"waiting {args.wait_after_create} seconds for the controlled restart")
            time.sleep(args.wait_after_create)
            response = client.post(
                f"/sessions/{session_id}/chat", json={"text": "after restart", "revision": 0}
            )
            print(f"chat after restart: HTTP {response.status_code}")
            if response.status_code != 404:
                raise RuntimeError("expected the in-memory session to be lost after restart")
    except (RuntimeError, ValueError, httpx.HTTPError, KeyError) as exc:
        print(f"Restart test failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
