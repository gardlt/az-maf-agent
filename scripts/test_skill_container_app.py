#!/usr/bin/env python3
"""Hosted Stage 3 checks. Prints status/counters/digests, never tokens or model text."""

import argparse
import json
from pathlib import Path

import httpx
from test_container_app import acquire_token, validate_origin, validate_stage1_claims


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api", required=True)
    parser.add_argument("--skill", choices=["movie-research", "movie-night"])
    parser.add_argument("--expect-disabled", action="store_true")
    args = parser.parse_args()
    token = acquire_token("AGENT_ACCESS_TOKEN")
    validate_stage1_claims(token)
    manifests = {
        item["skill_id"]: item for item in json.loads(Path("skills/approved.json").read_text())
    }
    with httpx.Client(
        base_url=validate_origin(args.api),
        timeout=130,
        headers={"Authorization": f"Bearer {token}"},
        follow_redirects=False,
    ) as client:
        for skill_id in [args.skill] if args.skill else ["movie-research", "movie-night"]:
            created = client.post("/sessions")
            created.raise_for_status()
            sid = created.json()["session_id"]
            path = f"/sessions/{sid}/chat"
            response = client.post(
                path,
                json={
                    "text": "Use get_movie exactly once for tmdb_11. Then give a short TMDB-attributed movie recommendation.",
                    "revision": 0,
                    "skill_id": skill_id,
                    "skill_version": "1.0.0",
                },
            )
            print(f"{skill_id}: HTTP {response.status_code}")
            if args.expect_disabled:
                assert response.status_code == 409 and response.json()["error"] == "skill_disabled"
                continue
            if response.status_code != 200:
                raise RuntimeError(f"{skill_id}: {response.text[:200]}")
            data = response.json()
            assert data["skill"]["sha256"] == manifests[skill_id]["sha256"]
            assert data["movie_reads"] == 1
            print(
                json.dumps(
                    {
                        "skill": data["skill"],
                        "movie_reads": data["movie_reads"],
                        "revision": data["revision"],
                        "run_id": data["run_id"],
                    }
                )
            )
            unknown = client.post(
                path,
                json={
                    "text": "Hello",
                    "revision": 1,
                    "skill_id": "unapproved",
                    "skill_version": "1.0.0",
                },
            )
            assert unknown.status_code == 409 and unknown.json()["error"] == "skill_not_approved"
            print(f"{skill_id} unknown skill: HTTP {unknown.status_code}")
            write = client.post(f"/sessions/{sid}/movies/put_movie", json={"catalog_id": "tmdb_11"})
            assert write.status_code == 403
            print(f"{skill_id} forbidden write: HTTP {write.status_code}")


if __name__ == "__main__":
    main()
