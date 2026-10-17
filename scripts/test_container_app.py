#!/usr/bin/env python3
"""Exercise the protected Stage 1 Container App without persisting bearer tokens."""

import argparse
import base64
import json
import os
import sys
from datetime import datetime, timezone
from urllib.parse import urlsplit

import httpx
from azure.core.exceptions import ClientAuthenticationError
from azure.identity import DeviceCodeCredential

TENANT_ID = "c57afb80-6b3d-4bae-a466-e4d217bcb4a2"
API_APP_ID = "e7898571-069f-49c7-91b5-4b08a9edcb30"
CLI_APP_ID = "df915b12-fb46-48d7-a80f-6f2e8e9ef487"
SCOPE = f"api://{API_APP_ID}/Chat.Access"
DEFAULT_API = "https://ca-az-maf-stage1.purplehill-879f4f4f.eastus2.azurecontainerapps.io"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api", default=DEFAULT_API, help="HTTPS Container App origin")
    parser.add_argument(
        "--token-env",
        default="AGENT_ACCESS_TOKEN",
        help="environment variable containing an already-acquired token",
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
    credential = DeviceCodeCredential(
        tenant_id=TENANT_ID,
        client_id=CLI_APP_ID,
        prompt_callback=device_code_prompt,
    )
    try:
        return credential.get_token(SCOPE).token
    except ClientAuthenticationError as exc:
        raise RuntimeError("Entra device-code sign-in did not complete") from exc
    finally:
        credential.close()


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
    if claims.get("aud") != f"api://{API_APP_ID}":
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


def test_container_app(origin: str, token: str) -> None:
    with httpx.Client(timeout=30, follow_redirects=False) as public_client:
        unauthenticated = public_client.post(f"{origin}/sessions")
        require_status(unauthenticated, 401, "unauthenticated create")

    with httpx.Client(
        base_url=origin,
        timeout=30,
        follow_redirects=False,
        headers={"Authorization": f"Bearer {token}"},
    ) as client:
        session = require_status(client.post("/sessions"), 200, "authenticated create")
        session_id = session["session_id"]
        revision = session["revision"]

        first = require_status(
            client.post(
                f"/sessions/{session_id}/chat", json={"text": "hello", "revision": revision}
            ),
            200,
            "first chat",
        )
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
        reset = require_status(client.post(f"/sessions/{session_id}/reset"), 200, "reset")
        after_reset = require_status(
            client.post(
                f"/sessions/{session_id}/chat",
                json={"text": "hello", "revision": reset["revision"]},
            ),
            200,
            "chat after reset",
        )
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
        test_container_app(origin, token)
    except (RuntimeError, ValueError, httpx.HTTPError, KeyError) as exc:
        print(f"Container App test failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
