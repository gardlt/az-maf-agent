#!/usr/bin/env python3
"""Verify the deployed agent can read the private movie MCP with its identity."""

import argparse
import sys

import httpx
from test_container_app import DEFAULT_API, acquire_token, validate_stage1_claims


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog-id", default="tmdb_11")
    parser.add_argument("--expect-title")
    return parser.parse_args()


def require(response: httpx.Response, status: int, label: str) -> dict:
    print(f"{label}: HTTP {response.status_code}")
    if response.status_code != status:
        raise RuntimeError(f"{label} expected HTTP {status}; body: {response.text[:300]}")
    return response.json() if response.content else {}


def main() -> int:
    args = parse_args()
    try:
        token = acquire_token("AGENT_ACCESS_TOKEN")
        validate_stage1_claims(token)
        with httpx.Client(base_url=DEFAULT_API, timeout=45, follow_redirects=False) as client:
            session = require(
                client.post("/sessions", headers={"Authorization": f"Bearer {token}"}),
                200,
                "authenticated create",
            )
            path = f"/sessions/{session['session_id']}/movies"
            require(
                client.post(f"{path}/get_movie", json={"catalog_id": args.catalog_id}),
                401,
                "unauthenticated movie read",
            )
            client.headers["Authorization"] = f"Bearer {token}"
            movie = require(
                client.post(f"{path}/get_movie", json={"catalog_id": args.catalog_id}),
                200,
                "authenticated MCP read",
            )
            if movie.get("movie", {}).get("id") != args.catalog_id:
                raise RuntimeError("MCP returned a different record")
            if args.expect_title is not None and movie["movie"]["title"] != args.expect_title:
                raise RuntimeError("MCP returned an unexpected title")
            require(
                client.post(f"{path}/put_movie", json={"catalog_id": args.catalog_id}),
                403,
                "forbidden write proposal",
            )
            print(
                "movie:",
                movie["movie"]["title"],
                "(TMDB rating)",
            )
    except (RuntimeError, httpx.HTTPError, KeyError, ValueError) as exc:
        print(f"Movie Container App test failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
