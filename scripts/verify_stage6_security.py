"""Dev-only routing security checkpoint/verification; retain metadata, never tokens or text."""

import argparse
import json
from pathlib import Path

import httpx
from simulate_movie_users import (
    READ_CAPABILITIES,
    CachedOperator,
    audit_names,
    digest,
    verify_events,
)
from test_agent_identity_observability import API, no_prompt, require

from az_maf_agent.client_auth import acquire_stage1_token
from az_maf_agent.guardrail_blob import BlobControlBackend


def catalog_checkpoint():
    result = {}
    with httpx.Client(
        base_url=API,
        timeout=45,
        follow_redirects=False,
        headers={"Authorization": "Bearer " + acquire_stage1_token(no_prompt)},
    ) as c:
        session = require(c.post("/sessions"), 200)
        sid = session["session_id"]
        try:
            for key in ["tmdb_11", "tmdb_603"]:
                movie = require(
                    c.post(f"/sessions/{sid}/movies/get_movie", json={"catalog_id": key}), 200
                )["movie"]
                result[key] = digest({k: movie[k] for k in ["id", "title", "year", "synopsis"]})
            for name, body, status in [
                ("create_movie", {"title": "Stage6 forbidden write"}, 403),
                ("update_movie", {"catalog_id": "tmdb_11", "title": "Stage6 forbidden write"}, 403),
                ("get_movie", {"catalog_id": "tmdb_11", "method": "PUT"}, 422),
            ]:
                response = c.post(f"/sessions/{sid}/movies/{name}", json=body)
                assert response.status_code == status
                result[name] = dict(http=status, error=response.json()["error"])
        finally:
            require(c.post(f"/sessions/{sid}/reset"), 200)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=["snapshot", "verify"], required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--routed", type=Path, default=Path("docs/validation/stage-6-routed.json"))
    parser.add_argument(
        "--probes", type=Path, default=Path("docs/validation/stage-6-route-probes.json")
    )
    parser.add_argument(
        "--report", type=Path, default=Path("docs/validation/stage-6-security.json")
    )
    args = parser.parse_args()
    backend = BlobControlBackend("stmafmemdevmako261019", credential=CachedOperator())
    try:
        if args.phase == "snapshot":
            state = backend.snapshot()
            assert not any(r["unresolved"] for r in state["runs"].values())
            args.checkpoint.write_text(
                json.dumps(
                    dict(
                        audit_names=sorted(audit_names(backend)),
                        receipts_digest=digest(state["receipts"]),
                        catalog=catalog_checkpoint(),
                        epoch=backend.policy().epoch,
                    ),
                    indent=2,
                )
                + "\n"
            )
            print("Metadata checkpoint saved; no model was dispatched.")
            return
        before = json.loads(args.checkpoint.read_text())
        catalog = catalog_checkpoint()
        state = backend.snapshot()
        events = verify_events(backend, audit_names(backend) - set(before["audit_names"]))
        ids = {
            r["run_id"]
            for p in [args.routed, args.probes]
            for r in json.loads(p.read_text())
            if r.get("run_id")
        }
        selected = [e for e in events if e.get("run_id") in ids]
        checks = [e for e in selected if e["event"] == "dispatch_authorized"]
        all_checks = [e for e in events if e["event"] == "dispatch_authorized"]
        forbidden = [e for e in all_checks if e.get("capability") not in READ_CAPABILITIES]
        model = [e for e in checks if e.get("capability") == "model"]
        assert model and not forbidden
        assert all(e.get("model_route") in ["routine", "reasoning"] for e in model)
        assert before["receipts_digest"] == digest(state["receipts"])
        assert before["catalog"] == catalog
        assert all(not state["runs"][i]["unresolved"] for i in ids)
        assert backend.policy().epoch == before["epoch"] and not backend.policy().global_stop
        report = dict(
            audit_envelopes_sha256_verified=len(events),
            tested_runs=len(ids),
            run_audit_events=len(selected),
            dispatch_checks=len(checks),
            all_new_dispatch_checks=len(all_checks),
            forbidden_dispatches=len(forbidden),
            model_reservations=len(model),
            routine_reservations=sum(e["model_route"] == "routine" for e in model),
            reasoning_reservations=sum(e["model_route"] == "reasoning" for e in model),
            all_test_runs_reconciled=True,
            simulator_receipts_unchanged=True,
            sampled_catalog_fields_unchanged=True,
            policy_epoch=backend.policy().epoch,
            global_stop=False,
            catalog_denials=catalog,
            reserved_usd=sum(float(state["runs"][i]["usd"]) for i in ids),
            limits="One authorized user, finite fixed fixtures, sampled catalog records; "
            "not a cross-user or network isolation proof.",
        )
        args.report.write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(report))
    finally:
        backend.close()


if __name__ == "__main__":
    main()
