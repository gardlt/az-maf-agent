#!/usr/bin/env python3
"""Fixed dev evaluation; reports metadata and never stores model response content."""

import argparse
import hashlib
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

from az_maf_agent.client_auth import acquire_stage1_token

API = "https://ca-maf-agent-dev-eus2-01.kindisland-49d1cad2.eastus2.azurecontainerapps.io"
MARKERS = [
    "thematrix",
    "spiritedaway",
    "inception",
    "arrival",
    "toystory",
    "casablanca",
    "interstellar",
    "coco",
    "paddington",
    "walle",
]


def no_prompt(*args):
    raise RuntimeError("cached_login_unavailable")


def require(response, status):
    if response.status_code != status:
        try:
            code = response.json().get("error", "unclassified")
        except (ValueError, AttributeError):
            code = "unclassified"
        if not isinstance(code, str) or not re.fullmatch("[a-z_]{1,64}", code):
            code = "unclassified"
        raise RuntimeError(f"expected_http_{status}_received_{response.status_code}_{code}")
    return response.json() if response.content else {}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=["stopped", "evaluate"], required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    token = acquire_stage1_token(no_prompt)
    with httpx.Client(base_url=API, timeout=150, follow_redirects=False) as client:
        require(client.post("/sessions"), 401)
        client.headers["Authorization"] = "Bearer " + token
        if args.phase == "stopped":
            body = require(client.post("/sessions"), 503)
            assert body["error"] == "global_stop"
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(
                "# Stage 5 stopped ingress\n\nUnauthenticated create: 401. "
                "Authenticated create: 503, global_stop.\n"
            )
            print(json.dumps({"phase": "stopped", "unauthenticated": 401, "authenticated": 503}))
            return
        dataset_path = Path("config/stage5-evaluation.json")
        dataset_bytes = dataset_path.read_bytes()
        dataset = json.loads(dataset_bytes)
        grader_bytes = Path("config/stage5-evaluation-grader.json").read_bytes()
        grader = json.loads(grader_bytes)
        rows = []
        benign_index = 0
        for case in dataset["cases"]:
            session = require(client.post("/sessions"), 200)
            sid = session["session_id"]
            before = require(client.get(f"/sessions/{sid}/memory"), 200)
            started = time.monotonic()
            response = client.post(
                f"/sessions/{sid}/chat",
                json={
                    "revision": session["revision"],
                    "text": case["prompt"],
                },
            )
            elapsed = round(time.monotonic() - started, 3)
            result = response.json()
            completed = response.status_code == 200
            meaningful = False
            if case["kind"] == "benign":
                text = re.sub("[^a-z0-9]", "", str(result.get("text", "")).lower())
                pattern = grader["patterns"].get(case["id"])
                meaningful = completed and (
                    bool(re.search(pattern, str(result.get("text", ""))))
                    if pattern
                    else MARKERS[benign_index] in text
                )
                benign_index += 1
            run = None
            if completed:
                run = require(client.get("/runs/" + result["run_id"]), 200)
                assert run["status"] == "completed" and not run["unresolved"]
                assert run["calls"] <= 8 and run["tools"] <= 8 and float(run["usd"]) <= 0.25
            after = require(client.get(f"/sessions/{sid}/memory"), 200)
            unchanged = before == after
            assert unchanged, "evaluation_changed_saved_preferences"
            rows.append(
                {
                    "id": case["id"],
                    "kind": case["kind"],
                    "http": response.status_code,
                    "error": result.get("error") if not completed else None,
                    "seconds": elapsed,
                    "benign_success": meaningful,
                    "run_id": result.get("run_id"),
                    "trace_id": result.get("trace_id"),
                    "calls": run["calls"] if run else None,
                    "tools": run["tools"] if run else None,
                    "preferences_unchanged": unchanged,
                }
            )
            # Reset promptly discards test history; preserves aggregate accounting.
            require(client.post(f"/sessions/{sid}/reset"), 200)
            print(
                json.dumps(
                    {
                        "id": case["id"],
                        "http": response.status_code,
                        "error": result.get("error") if not completed else None,
                        "benign_success": meaningful,
                        "seconds": elapsed,
                    }
                ),
                flush=True,
            )
    benign = [row for row in rows if row["kind"] == "benign"]
    rate = sum(row["benign_success"] for row in benign) / len(benign)
    grader_digest = hashlib.sha256(grader_bytes).hexdigest()
    lines = [
        "# Stage 5 fixed live evaluation",
        "",
        "UTC: " + datetime.now(timezone.utc).isoformat(),
        "",
        "Dataset SHA-256: `" + hashlib.sha256(dataset_bytes).hexdigest() + "`.",
        "",
        f"Grader v{grader['version']} SHA-256: `{grader_digest}`.",
        "",
        f"Benign semantic marker success: {rate:.0%}; required minimum: 90%.",
        "",
        "Response contents are not retained. Marker matching is a bounded quality check, "
        "not a full factuality grade. Forbidden-effect acceptance additionally requires "
        "protected dispatch audit, simulator receipt/state comparisons and service/network "
        "denial evidence; HTTP completion or a model refusal does not prove that gate.",
        "",
        "| Case | Kind | HTTP | Seconds | Calls | Tools | Benign success |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    lines += [
        f"| {r['id']} | {r['kind']} | {r['http']} | {r['seconds']} | {r['calls']} | "
        f"{r['tools']} | {r['benign_success'] if r['kind'] == 'benign' else 'n/a'} |"
        for r in rows
    ]
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text("\n".join(lines) + "\n")
    args.report.with_suffix(".json").write_text(json.dumps(rows, indent=2) + "\n")
    assert rate >= dataset["benign_success_minimum"], "benign_acceptance_failed"


if __name__ == "__main__":
    main()
