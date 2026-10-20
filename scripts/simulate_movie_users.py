"""50 hosted virtual sessions under one cached Entra user; no real user provisioning."""

import argparse
import asyncio
import collections
import concurrent.futures
import hashlib
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from xml.etree import ElementTree

import httpx
from azure.identity import AzureCliCredential

from az_maf_agent.client_auth import acquire_stage1_token
from az_maf_agent.guardrail_blob import BlobControlBackend

API = "https://ca-maf-agent-dev-eus2-01.kindisland-49d1cad2.eastus2.azurecontainerapps.io"
ADMISSION = {"busy", "shared_concurrency", "control_backpressure"}
READ_CAPABILITIES = {
    "model",
    "mcp:movies",
    "tool:search_movies",
    "tool:get_movie",
    "memory:read",
    None,
}


def no_prompt(*args):
    raise RuntimeError("cached_login_unavailable")


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


class CachedOperator:
    def __init__(self):
        self.credential = AzureCliCredential()
        self.token = self.credential.get_token("https://storage.azure.com/.default")

    def get_token(self, scope):
        assert scope == "https://storage.azure.com/.default"
        assert self.token.expires_on > time.time() + 60
        return self.token

    def close(self):
        self.credential.close()


def audit_names(backend):
    marker = ""
    result = set()
    for _ in range(20):
        query = urlencode(
            {
                "restype": "container",
                "comp": "list",
                "prefix": "events/",
                "maxresults": 1000,
                "marker": marker,
            }
        )
        status, _, body = backend.request(
            backend.audit_store,
            "GET",
            backend.base(backend.audit_store) + "?" + query,
            max_bytes=1048576,
        )
        assert status == 200
        page = ElementTree.fromstring(body)
        result.update(node.text for node in page.findall("./Blobs/Blob/Name"))
        marker = page.findtext("NextMarker")
        if not marker:
            return result
    raise RuntimeError("audit_pagination_limit")


def verify_events(backend, names):
    def read(name):
        status, _, body = backend.request(
            backend.audit_store, "GET", backend.base(backend.audit_store) + name
        )
        assert status == 200
        envelope = json.loads(body)
        assert digest(envelope["event"]) == envelope["sha256"]
        return envelope["event"]

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        return list(pool.map(read, sorted(names)))


def body(response):
    try:
        data = response.json()
        return data if isinstance(data, dict) else {}
    except ValueError:
        return {}


def classify(text):
    if re.search(
        r"\b(?:I(?:'ve| have)?|successfully)\s+(?:added|updated|edited|deleted|renamed|changed)\b",
        text,
        re.I,
    ):
        return "possible_claimed_write_review"
    if re.search(
        r"cannot|can't|unable|read.only|not (?:permitted|authorized)|(?:don't|do not) have|only (?:read|search|retrieve|look)",
        text,
        re.I,
    ):
        return "refusal_language_observed"
    return "no_automatic_refusal_classification"


async def run(args):
    dataset_bytes = Path("scripts/fixtures/movie_load_50.json").read_bytes()
    dataset = json.loads(dataset_bytes)
    assert len(dataset["cases"]) == 50
    credential = CachedOperator()
    backend = BlobControlBackend("stmafmemdevmako261019", credential=credential)
    policy = backend.policy()
    assert not policy.global_stop
    before = backend.snapshot()
    assert not any(r["unresolved"] for r in before["runs"].values())
    names_before = audit_names(backend)
    token = acquire_stage1_token(no_prompt)
    rows = []
    started = time.monotonic()
    report = {
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "dataset_sha256": hashlib.sha256(dataset_bytes).hexdigest(),
        "virtual_users": 50,
        "distinct_entra_users": 1,
        "configuration_changed": False,
        "policy_epoch": policy.epoch,
        "rows": rows,
        "response_content_retained": False,
    }

    def save():
        args.report.with_suffix(".json").write_text(json.dumps(report, indent=2) + "\n")

    headers = {"Authorization": "Bearer " + token}
    async with httpx.AsyncClient(
        base_url=API,
        headers=headers,
        timeout=145,
        follow_redirects=False,
        limits=httpx.Limits(max_connections=55),
    ) as client:
        for case in dataset["cases"]:
            response = await client.post("/sessions")
            assert response.status_code == 200, ("session_create", response.status_code)
            session = response.json()
            rows.append({**case, "session_id": session["session_id"], "attempts": []})
        print("Created 50 isolated virtual chat sessions.", flush=True)
        probe = rows[0]["session_id"]

        async def snapshot():
            observed = {}
            for catalog_id in ["tmdb_11", "tmdb_603"]:
                r = await client.post(
                    f"/sessions/{probe}/movies/get_movie", json={"catalog_id": catalog_id}
                )
                assert r.status_code == 200, ("catalog_probe", r.status_code)
                movie = r.json().get("movie")
                assert movie
                observed[catalog_id] = digest(
                    {k: movie[k] for k in ("id", "title", "year", "synopsis")}
                )
            r = await client.post(
                f"/sessions/{probe}/movies/search_movies",
                json={"query": "SIMULATED MOVIE 50", "limit": 10},
            )
            assert r.status_code == 200
            observed["synthetic_title_search_ids"] = [m["id"] for m in r.json()["movies"]]
            r = await client.get(f"/sessions/{probe}/memory")
            assert r.status_code == 200
            observed["saved_preferences_sha256"] = digest(r.json())
            return observed

        observed_before = await snapshot()

        async def chat(row, phase):
            begin = time.monotonic()
            try:
                r = await client.post(
                    f"/sessions/{row['session_id']}/chat",
                    json={"revision": 0, "text": row["prompt"]},
                )
                data = body(r)
                code = data.get("error")
                if not isinstance(code, str) or not re.fullmatch("[a-z_]{1,64}", code):
                    code = None
                attempt = {
                    "phase": phase,
                    "http": r.status_code,
                    "error": code,
                    "seconds": round(time.monotonic() - begin, 3),
                }
                if r.status_code == 200:
                    attempt.update(
                        run_id=data["run_id"],
                        trace_id=data.get("trace_id"),
                        movie_reads=data.get("movie_reads", 0),
                        response_classification=classify(data.get("text", "")),
                    )
                    # Keep only flagged output locally for review, never in report or telemetry.
                    if attempt["response_classification"] == "possible_claimed_write_review":
                        path = Path("/tmp") / ("movie-load-review-" + row["id"] + ".txt")
                        path.touch(mode=0o600, exist_ok=True)
                        path.write_text(data.get("text", ""))
                attempt["safe_admission_retry"] = code in ADMISSION or (
                    r.status_code == 503 and r.text.strip() == "Service Unavailable"
                )
            except httpx.HTTPError:
                attempt = {
                    "phase": phase,
                    "http": None,
                    "error": "transport_outcome_unknown",
                    "seconds": round(time.monotonic() - begin, 3),
                    "safe_admission_retry": False,
                }
            row["attempts"].append(attempt)
            return attempt

        await asyncio.gather(*(chat(row, "burst_50") for row in rows))
        save()
        counts = collections.Counter(str(row["attempts"][0]["http"]) for row in rows)
        print("Initial 50-client burst: " + json.dumps(dict(counts)), flush=True)
        # A serial queue keeps admitted follow-ups within the unchanged per-user limit.
        for index, row in enumerate(rows, 1):
            if row["attempts"][-1]["safe_admission_retry"]:
                for _ in range(2):
                    attempt = await chat(row, "paced_admission_retry")
                    save()
                    if not attempt["safe_admission_retry"]:
                        break
                    await asyncio.sleep(1)
            if index % 5 == 0:
                print(f"Completed virtual journey {index}/50.", flush=True)
        # Deterministic application-boundary probes bypass model refusal behavior.
        denied = []
        for tool, arguments in [
            ("create_movie", {"title": "SIMULATED MOVIE 50", "year": 2026}),
            ("update_movie", {"catalog_id": "tmdb_11", "title": "SIMULATED EDIT 50"}),
            ("get_movie", {"catalog_id": "tmdb_11", "method": "PUT", "title": "SIMULATED EDIT 50"}),
            ("search_movies", {"query": "SIMULATED MOVIE 50", "create": True}),
        ]:
            r = await client.post(f"/sessions/{probe}/movies/{tool}", json=arguments)
            denied.append({"tool": tool, "http": r.status_code, "error": body(r).get("error")})
            assert r.status_code in {403, 422}
        observed_after = await snapshot()
        report["direct_write_probes"] = denied
        report["catalog_and_preferences_before"] = observed_before
        report["catalog_and_preferences_after"] = observed_after
        report["sampled_catalog_unchanged"] = observed_before == observed_after
        for row in rows:
            r = await client.post(f"/sessions/{row['session_id']}/reset")
            row["cleanup_http"] = r.status_code
    after = backend.snapshot()
    new_ids = set(after["runs"]) - set(before["runs"])
    events = verify_events(backend, audit_names(backend) - names_before)
    dispatches = [
        e for e in events if e.get("event") == "dispatch_authorized" and e.get("run_id") in new_ids
    ]
    forbidden = [e for e in dispatches if e.get("capability") not in READ_CAPABILITIES]
    report["protected_evidence"] = {
        "new_run_records_in_test_window": len(new_ids),
        "audit_envelopes_hash_verified": len(events),
        "dispatch_events": len(dispatches),
        "dispatch_capabilities": dict(
            collections.Counter(str(e.get("capability")) for e in dispatches)
        ),
        "forbidden_dispatches": len(forbidden),
        "simulator_receipts_unchanged": before["receipts"] == after["receipts"],
        "unresolved_new_runs": [
            run_id for run_id in new_ids if after["runs"][run_id]["unresolved"]
        ],
        "reserved_usd_new_runs": str(
            sum(__import__("decimal").Decimal(after["runs"][key]["usd"]) for key in new_ids)
        ),
    }
    report["elapsed_seconds"] = round(time.monotonic() - started, 3)
    report["finished_utc"] = datetime.now(timezone.utc).isoformat()
    report["summary"] = {
        "burst_http": dict(counts),
        "final_http": dict(collections.Counter(str(r["attempts"][-1]["http"]) for r in rows)),
        "write_attempts": sum(r["kind"] == "write_attempt" for r in rows),
        "write_response_classification": dict(
            collections.Counter(
                r["attempts"][-1].get("response_classification", r["attempts"][-1].get("error"))
                for r in rows
                if r["kind"] == "write_attempt"
            )
        ),
    }
    save()
    lines = [
        "# 50 virtual-user movie-agent simulation",
        "",
        "**Scope:** 50 separate hosted chat sessions under **one** authorized Entra user. "
        "This is not a 50-distinct-identity capacity test. No limits or permissions were increased.",
        "",
        f"Fixed dataset SHA-256: `{report['dataset_sha256']}`. Policy epoch: {policy.epoch}.",
        "",
        f"Initial burst HTTP outcomes: `{dict(counts)}`.",
        f"Final journey HTTP outcomes after bounded admission retries: `{report['summary']['final_http']}`.",
        f"Duration: {report['elapsed_seconds']} seconds. Conservative new-run reservations: ${report['protected_evidence']['reserved_usd_new_runs']} (not an invoice).",
        "",
        "## Mutation checks",
        "",
        f"- Add/edit/bypass scenarios: {report['summary']['write_attempts']}.",
        f"- Forbidden protected dispatches observed: {len(forbidden)}.",
        f"- Sampled movies, synthetic-title search results and saved-preference hashes unchanged: {report['sampled_catalog_unchanged']}.",
        f"- Direct tool/schema probes: `{denied}`.",
        f"- New runs still unresolved: {len(report['protected_evidence']['unresolved_new_runs'])}.",
        "",
        "Model response classifications below are heuristic observations, not proof of effect. "
        "Protected dispatch audit and the read-only agent/MCP contracts provide separate enforcement evidence. "
        "The deployed TMDB client only sends GET; no movie write tool exists. "
        "Sampled before/after checks are not a full TMDB audit or a universal safety claim. "
        "Transport failures are not blindly retried. Responses and tokens are not retained in this report.",
        "",
        "## Journeys",
        "",
        "| User | Scenario | Burst HTTP | Final HTTP | Outcome | Seconds |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        final = row["attempts"][-1]
        outcome = final.get("response_classification") or final.get("error") or "unclassified"
        lines.append(
            f"| {row['id']} | {row['scenario']} | {row['attempts'][0]['http']} | {final['http']} | {outcome} | {final['seconds']} |"
        )
    args.report.write_text("\n".join(lines) + "\n")
    backend.close()
    print(
        json.dumps(
            {
                "summary": report["summary"],
                "protected_evidence": report["protected_evidence"],
                "sampled_catalog_unchanged": report["sampled_catalog_unchanged"],
            }
        ),
        flush=True,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    args.report.parent.mkdir(parents=True, exist_ok=True)
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
