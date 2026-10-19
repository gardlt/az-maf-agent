#!/usr/bin/env python3
"""Redacted Stage 4 dev acceptance; fixed teaching preferences, no tokens in output."""

import argparse
import json

import httpx
from test_container_app import acquire_token, validate_origin


def run(api, phase):
    token = acquire_token("AGENT_ACCESS_TOKEN")
    with httpx.Client(base_url=api, timeout=135, follow_redirects=False) as client:

        def request(method, path, expected=200, body=None, authenticated=True):
            response = client.request(
                method,
                path,
                json=body,
                headers={"Authorization": "Bearer " + token} if authenticated else {},
            )
            parts = path.split("/")
            if len(parts) > 2:
                parts[2] = "{session}"
            if len(parts) > 4 and parts[3] == "memory":
                parts[4] = "{record}"
            print(f"{method} {'/'.join(parts)}: HTTP {response.status_code}")
            if response.status_code != expected:
                raise RuntimeError(f"expected HTTP {expected}, received {response.status_code}")
            return response.json() if expected == 200 else {}

        request("POST", "/sessions", expected=401, authenticated=False)
        session = request("POST", "/sessions")
        sid = session["session_id"]
        path = f"/sessions/{sid}/memory"
        initial = request("GET", path)
        if phase in {"all", "save"}:
            if initial["memories"]:
                raise RuntimeError(
                    "Refusing to replace existing preferences; inspect and explicitly forget them first"
                )
            body = {
                "category": "preferred_genre",
                "value": "comedy",
                "consent": False,
                "expected_generation": initial["generation"],
            }
            request("POST", path, expected=403, body=body)
            request("POST", path, expected=422, body=body | {"tenant": "spoofed"})
            saved = request("POST", path, body=body | {"consent": True})
            assert saved["memory"]["revision"] == 1
            if phase == "save":
                print(
                    "Saved fixed test preference; run verify after a replica restart, then cleanup."
                )
                return
        if phase in {"all", "verify"}:
            another = request("POST", "/sessions")["session_id"]
            shared = request("GET", f"/sessions/{another}/memory")
            assert len(shared["memories"]) == 1
            record = shared["memories"][0]
            assert record["category"] == "preferred_genre" and record["value"] == "comedy"
            corrected = request(
                "PUT",
                path + "/" + record["id"],
                body={
                    "category": "preferred_genre",
                    "value": "drama",
                    "consent": True,
                    "expected_generation": shared["generation"],
                    "expected_revision": record["revision"],
                },
            )
            assert corrected["memory"]["revision"] == record["revision"] + 1
            chat = request(
                "POST",
                f"/sessions/{another}/chat",
                body={
                    "text": "Suggest one movie matching my saved genre preference. Keep it brief.",
                    "revision": 0,
                },
            )
            assert chat["memory"]["records"] == 1
            request("POST", f"/sessions/{another}/reset")
            assert len(request("GET", f"/sessions/{another}/memory")["memories"]) == 1
        if phase in {"all", "verify", "cleanup"}:
            if phase in {"all", "verify"}:
                removed = request("DELETE", path + "/" + record["id"])
                assert removed["forgotten"] is True
            result = request("DELETE", path)
            assert request("GET", path)["memories"] == []
            if phase in {"all", "verify"}:
                after = request(
                    "POST",
                    f"/sessions/{another}/chat",
                    body={
                        "text": "Do I have any saved movie preferences? Keep the answer brief.",
                        "revision": chat["revision"] + 1,
                    },
                )
                assert after["memory"]["records"] == 0
            request(
                "POST",
                path,
                expected=409,
                body={
                    "category": "preferred_genre",
                    "value": "comedy",
                    "consent": True,
                    "expected_generation": initial["generation"],
                },
            )
            print(
                json.dumps(
                    {
                        "memory_acceptance": "passed",
                        "final_generation": result["generation"],
                        "test_preferences_remaining": 0,
                    }
                )
            )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api", required=True)
    parser.add_argument("--phase", choices=["all", "save", "verify", "cleanup"], default="all")
    args = parser.parse_args()
    run(validate_origin(args.api), args.phase)


if __name__ == "__main__":
    main()
