"""Fixed hosted route/history canary; keep metadata and grades, never response text."""

import argparse
import json
from pathlib import Path

import httpx
from test_agent_identity_observability import API, no_prompt, require

from az_maf_agent.client_auth import acquire_stage1_token

CASES = [
    (
        "routine",
        "Use get_movie for tmdb_11 and give only the movie title and release year.",
        "Star Wars",
        "1977",
    ),
    (
        "reasoning",
        "Analyze that same movie briefly. Use its title and release year from our conversation.",
        "Star Wars",
        "1977",
    ),
    (
        "routine",
        "Repeat the title and year of the movie we just discussed. Do not use another lookup.",
        "Star Wars",
        "1977",
    ),
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    token = acquire_stage1_token(no_prompt)
    rows = []
    with httpx.Client(
        base_url=API,
        timeout=145,
        follow_redirects=False,
        headers={"Authorization": "Bearer " + token},
    ) as client:
        session = require(client.post("/sessions"), 200)
        sid, revision = session["session_id"], session["revision"]
        try:
            for expected, prompt, title, year in CASES:
                result = require(
                    client.post(
                        f"/sessions/{sid}/chat", json={"revision": revision, "text": prompt}
                    ),
                    200,
                )
                revision = result["revision"]
                run = require(client.get("/runs/" + result["run_id"]), 200)
                passed = title.lower() in result["text"].lower() and year in result["text"]
                rows.append(
                    dict(
                        expected_route=expected,
                        run_id=result["run_id"],
                        trace_id=result["trace_id"],
                        history_marker_passed=passed,
                        calls=run["calls"],
                        tools=run["tools"],
                        unresolved=run["unresolved"],
                    )
                )
                args.report.write_text(json.dumps(rows, indent=2) + "\n")
                assert passed and not run["unresolved"], "history_or_reconciliation_failed"
        finally:
            require(client.post(f"/sessions/{sid}/reset"), 200)
    print(json.dumps(rows))


if __name__ == "__main__":
    main()
