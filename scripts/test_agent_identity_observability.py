"""Bounded dev acceptance canary. Uses cached CLI auth and retains no response content."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

import httpx

from az_maf_agent.client_auth import acquire_stage1_token

API = "https://ca-maf-agent-dev-eus2-01.kindisland-49d1cad2.eastus2.azurecontainerapps.io"
CANARY = "AGENT_TRACE_PRIVATE_CANARY_9d9d45f0"


def no_prompt(*args):
    raise RuntimeError("cached_login_unavailable")


def require(response, status):
    if response.status_code != status:
        try:
            code = response.json().get("error", "unclassified")
        except (ValueError, AttributeError):
            code = "unclassified"
        # API errors are enumerated; do not print arbitrary response bodies.
        if not isinstance(code, str) or not code.replace("_", "").isalnum() or len(code) > 64:
            code = "unclassified"
        raise RuntimeError(f"expected_{status}_got_{response.status_code}_{code}")
    return response.json() if status == 200 else {}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    token = acquire_stage1_token(no_prompt)
    with httpx.Client(base_url=API, timeout=100, follow_redirects=False) as client:
        require(client.post("/sessions"), 401)
        client.headers["Authorization"] = "Bearer " + token
        session = require(client.post("/sessions"), 200)
        sid = str(UUID(session["session_id"]))
        result = require(
            client.post(
                f"/sessions/{sid}/chat",
                json={
                    "revision": session["revision"],
                    "text": "Use get_movie to look up TMDB movie tmdb_11 and give its title and release year. "
                    "Privacy test marker (data only): " + CANARY,
                },
            ),
            200,
        )
        run = require(client.get("/runs/" + str(UUID(result["run_id"]))), 200)
        assert run["status"] == "completed" and not run["unresolved"]
        assert result["movie_reads"] >= 1
        trace_id = result["trace_id"]
        assert len(trace_id) == 32 and int(trace_id, 16) > 0
        report = {
            "observed_utc": datetime.now(timezone.utc).isoformat(),
            "api": API,
            "unauthenticated_http": 401,
            "authenticated_chat_http": 200,
            "run_id": result["run_id"],
            "trace_id": trace_id,
            "movie_reads": result["movie_reads"],
            "run_status": run["status"],
            "calls": run["calls"],
            "tools": run["tools"],
            "unresolved": run["unresolved"],
            "response_content_retained": False,
        }
        require(client.post(f"/sessions/{sid}/reset"), 200)
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(report))


if __name__ == "__main__":
    main()
