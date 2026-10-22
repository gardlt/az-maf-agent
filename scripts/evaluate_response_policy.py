"""Collect bounded hosted response-policy cases for human review; never auto-grade refusals."""

import argparse
import hashlib
import json
import os
from pathlib import Path

import httpx

from az_maf_agent.client_auth import acquire_stage1_token

API = "https://ca-maf-agent-dev-eus2-01.kindisland-49d1cad2.eastus2.azurecontainerapps.io"
DATASET = Path(__file__).resolve().parents[1] / "config/response-policy-evaluation.json"


def no_prompt(*_):
    raise RuntimeError("Sign in with the agent CLI before running this evaluation.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--report",
        type=Path,
        required=True,
        help="New private local JSON file; includes model answers for review.",
    )
    parser.add_argument("--skill", choices=["movie-night", "movie-research"])
    parser.add_argument("--skill-version", choices=["1.0.0", "1.1.0"], default="1.1.0")
    args = parser.parse_args()
    dataset_bytes = DATASET.read_bytes()
    dataset = json.loads(dataset_bytes)
    # Fixed approved dev destination; never send the token to a caller-supplied URL.
    token = acquire_stage1_token(no_prompt)
    report = {
        "dataset": dataset["version"],
        "dataset_sha256": hashlib.sha256(dataset_bytes).hexdigest(),
        "skill": args.skill,
        "skill_version": args.skill_version if args.skill else None,
        "assessment": "pending_human_review",
        "cases": [],
    }
    fd = os.open(args.report, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with (
        os.fdopen(fd, "w") as output,
        httpx.Client(
            base_url=API,
            timeout=150,
            follow_redirects=False,
            headers={"Authorization": "Bearer " + token},
        ) as client,
    ):
        try:
            for case in dataset["cases"]:
                created = client.post("/sessions")
                if created.status_code != 200:
                    report["blocked_http"] = created.status_code
                    break
                session = created.json()
                sid, revision = session["session_id"], session["revision"]
                row = {"id": case["id"], "expected": case["expected"], "turns": []}
                report["cases"].append(row)
                try:
                    for prompt in case["turns"]:
                        body = {"text": prompt, "revision": revision}
                        if args.skill:
                            body.update(skill_id=args.skill, skill_version=args.skill_version)
                        response = client.post(f"/sessions/{sid}/chat", json=body)
                        turn = {"http": response.status_code}
                        row["turns"].append(turn)
                        if response.status_code != 200:
                            # An HTTP failure is not a passed response-quality case.
                            report["blocked_http"] = response.status_code
                            return
                        result = response.json()
                        revision = result["revision"]
                        turn.update(
                            prompt=prompt,
                            answer=result["text"],
                            run_id=result["run_id"],
                            movie_reads=result.get("movie_reads"),
                            skill=result.get("skill"),
                        )
                finally:
                    # Clear only this evaluation session's history; budgets remain intact.
                    row["cleanup_http"] = client.post(f"/sessions/{sid}/reset").status_code
                    if row["cleanup_http"] != 200:
                        report["cleanup_requires_attention"] = True
                if report.get("cleanup_requires_attention"):
                    break
        finally:
            json.dump(report, output, indent=2)
            output.write("\n")
            print("Private report saved; human review required. No automatic pass is claimed.")


if __name__ == "__main__":
    main()
