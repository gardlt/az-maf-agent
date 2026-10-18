#!/usr/bin/env python3
"""Verify a hosted model-selected catalog read without printing model text or tokens."""

import sys

import httpx
from test_container_app import DEFAULT_API, acquire_token, validate_stage1_claims


def main() -> int:
    try:
        token = acquire_token("AGENT_ACCESS_TOKEN")
        validate_stage1_claims(token)
        with httpx.Client(
            base_url=DEFAULT_API,
            timeout=140,
            follow_redirects=False,
            headers={"Authorization": f"Bearer {token}"},
        ) as client:
            created = client.post("/sessions")
            print("create:", created.status_code)
            if created.status_code != 200:
                raise RuntimeError("session creation failed")
            sid = created.json()["session_id"]
            response = client.post(
                f"/sessions/{sid}/chat",
                json={
                    "text": (
                        "Use the movie catalog tool to look up movie_000103. "
                        "What is its title and synthetic rating? Do not guess."
                    ),
                    "revision": 0,
                },
            )
            print("model-selected movie chat:", response.status_code)
            if response.status_code != 200:
                raise RuntimeError(f"chat failed: {response.text[:200]}")
            result = response.json()
            if result.get("movie_reads") != 1:
                raise RuntimeError(f"expected one MCP read, got {result.get('movie_reads')}")
            text = result.get("text")
            if not isinstance(text, str) or not text.strip() or text.startswith("Offline reply:"):
                raise RuntimeError("live model returned no answer")
            print("verified MCP reads:", result["movie_reads"])
            print("live model response length:", len(text))
    except (RuntimeError, httpx.HTTPError, KeyError, ValueError) as exc:
        print(f"Model-selected movie test failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
