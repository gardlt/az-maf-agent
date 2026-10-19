#!/usr/bin/env python3
"""Exercise the protected Stage 1 Container App without persisting bearer tokens."""

import argparse
import base64
import json
import os
import sys
import time
from datetime import datetime, timezone
from urllib.parse import urlsplit

import httpx
from azure.core.exceptions import ClientAuthenticationError

from az_maf_agent.client_auth import API_APP_ID, CLI_APP_ID, TENANT_ID, acquire_stage1_token


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api", required=True, help="HTTPS Container App origin")
    parser.add_argument(
        "--token-env",
        default="AGENT_ACCESS_TOKEN",
        help="environment variable containing an already-acquired token",
    )
    parser.add_argument(
        "--expect-forbidden",
        action="store_true",
        help="expect the approved test token to be denied with HTTP 403",
    )
    parser.add_argument(
        "--wait-before-create",
        type=int,
        default=0,
        choices=range(0, 121),
        metavar="SECONDS",
        help="wait after token validation before creating a session",
    )
    return parser.parse_args()


def validate_origin(origin: str) -> str:
    parsed = urlsplit(origin)
    if parsed.scheme != "https" or not parsed.netloc or parsed.path not in ("", "/"):
        raise ValueError("--api must be an HTTPS origin without a path")
    return origin.rstrip("/")


def device_code_prompt(verification_uri: str, user_code: str, expires_on: datetime) -> None:
    print(f"Open {verification_uri} and enter code {user_code}.", file=sys.stderr)
    print(
        f"The code expires at {expires_on.astimezone().isoformat(timespec='minutes')}.",
        file=sys.stderr,
    )


def acquire_token(environment_name: str) -> str:
    existing = os.environ.get(environment_name)
    if existing:
        return existing
    try:
        return acquire_stage1_token(device_code_prompt)
    except ClientAuthenticationError as exc:
        raise RuntimeError("Entra device-code sign-in did not complete") from exc


def unverified_claims(token: str) -> dict[str, object]:
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        return json.loads(base64.urlsafe_b64decode(payload))
    except (IndexError, ValueError, UnicodeDecodeError) as exc:
        raise RuntimeError("access token is not a readable JWT") from exc


def show_safe_claims(token: str) -> None:
    claims = unverified_claims(token)
    expires = claims.get("exp")
    if isinstance(expires, int):
        expires = datetime.fromtimestamp(expires, timezone.utc).isoformat()
    print(
        "token claims:",
        json.dumps(
            {
                key: (expires if key == "exp" else claims.get(key))
                for key in ("aud", "tid", "oid", "scp", "azp", "appid", "exp")
            },
            sort_keys=True,
        ),
    )


def validate_stage1_claims(token: str) -> None:
    claims = unverified_claims(token)
    if claims.get("aud") != API_APP_ID:
        raise RuntimeError("token audience is not the Stage 1 API")
    if claims.get("tid") != TENANT_ID:
        raise RuntimeError("token tenant is not the Stage 1 tenant")
    expected_issuer = f"https://login.microsoftonline.com/{TENANT_ID}/v2.0"
    if claims.get("iss") != expected_issuer:
        raise RuntimeError("token issuer is not the Entra v2 issuer; acquire a fresh token")
    if "Chat.Access" not in str(claims.get("scp", "")).split():
        raise RuntimeError("token does not include the Chat.Access scope")
    caller = claims.get("azp") or claims.get("appid")
    if caller != CLI_APP_ID:
        raise RuntimeError(
            "token was minted for a different client application; unset AGENT_ACCESS_TOKEN "
            "and rerun this script to use the dedicated Stage 1 device-code client"
        )
    expires = claims.get("exp")
    if not isinstance(expires, int) or expires <= datetime.now(timezone.utc).timestamp():
        raise RuntimeError("token is expired")


def require_status(response: httpx.Response, expected: int, label: str) -> dict[str, object]:
    print(f"{label}: HTTP {response.status_code}")
    if response.status_code != expected:
        raise RuntimeError(f"{label} expected HTTP {expected}, received {response.status_code}")
    return response.json() if response.content else {}


def require_live_model_response(result: dict[str, object], label: str) -> None:
    text = result.get("text")
    if not isinstance(text, str) or not text.strip():
        raise RuntimeError(f"{label} returned no model text")
    if text.startswith("Offline reply:"):
        raise RuntimeError(f"{label} used the offline model")
    print(f"{label} live model response: {len(text)} characters")


def test_container_app(
    origin: str, token: str, expect_forbidden: bool = False, wait_before_create: int = 0
) -> None:
    with httpx.Client(timeout=30, follow_redirects=False) as public_client:
        unauthenticated = public_client.post(f"{origin}/sessions")
        require_status(unauthenticated, 401, "unauthenticated create")

    with httpx.Client(
        base_url=origin,
        timeout=30,
        follow_redirects=False,
        headers={"Authorization": f"Bearer {token}"},
    ) as client:
        if wait_before_create:
            print(f"waiting {wait_before_create} seconds before authenticated create")
            time.sleep(wait_before_create)
        session = require_status(
            client.post("/sessions"), 403 if expect_forbidden else 200, "authenticated create"
        )
        if expect_forbidden:
            return
        session_id = session["session_id"]
        revision = session["revision"]

        first = require_status(
            client.post(
                f"/sessions/{session_id}/chat", json={"text": "hello", "revision": revision}
            ),
            200,
            "first chat",
        )
        require_live_model_response(first, "first chat")
        stale = client.post(
            f"/sessions/{session_id}/chat", json={"text": "replay", "revision": revision}
        )
        require_status(stale, 409, "stale replay")
        revision = first["revision"]

        second = require_status(
            client.post(
                f"/sessions/{session_id}/chat", json={"text": "again", "revision": revision}
            ),
            200,
            "second chat",
        )
        require_live_model_response(second, "second chat")
        reset = require_status(client.post(f"/sessions/{session_id}/reset"), 200, "reset")
        after_reset = require_status(
            client.post(
                f"/sessions/{session_id}/chat",
                json={"text": "hello", "revision": reset["revision"]},
            ),
            200,
            "chat after reset",
        )
        require_live_model_response(after_reset, "chat after reset")
        print(
            "completed revision sequence:",
            first["revision"],
            second["revision"],
            after_reset["revision"],
        )


def main() -> int:
    args = parse_args()
    try:
        origin = validate_origin(args.api)
        token = acquire_token(args.token_env)
        show_safe_claims(token)
        validate_stage1_claims(token)
        test_container_app(origin, token, args.expect_forbidden, args.wait_before_create)
    except (RuntimeError, ValueError, httpx.HTTPError, KeyError) as exc:
        print(f"Container App test failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
