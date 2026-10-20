"""Verify correlated model routing and compare observed token costs in Azure traces."""

import argparse
import json
import re
import statistics
import subprocess
from pathlib import Path
from uuid import UUID

PRICES = {"gpt-5": (1.25, 10.0), "gpt-5-mini": (0.25, 2.0)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--routed", type=Path, required=True)
    parser.add_argument("--probes", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    groups = {
        name: json.loads(getattr(args, name).read_text())
        for name in ("baseline", "routed", "probes")
    }
    ids = [str(UUID(r["run_id"])) for rows in groups.values() for r in rows if r.get("run_id")]
    query = (
        "let spans = AppDependencies | where TimeGenerated > ago(1d); "
        'let roots = spans | where tostring(Properties["agent.run_id"]) in ('
        + ",".join("'" + i + "'" for i in ids)
        + ") | distinct OperationId; "
        "spans | where OperationId in (roots) "
        "| project OperationId, Id, ParentId, Properties"
    )
    result = subprocess.run(
        [
            "az",
            "monitor",
            "log-analytics",
            "query",
            "--workspace",
            args.workspace,
            "--analytics-query",
            query,
            "-o",
            "json",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    spans = json.loads(result.stdout)
    forbidden = {
        "gen_ai.input.messages",
        "gen_ai.output.messages",
        "gen_ai.system_instructions",
        "gen_ai.tool.call.arguments",
        "gen_ai.tool.call.result",
    }
    roots = {}
    for span in spans:
        props = span["Properties"]
        if isinstance(props, str):
            props = json.loads(props)
        span["Properties"] = props
        assert not forbidden.intersection(props), "content_attributes_exported"
        run_id = props.get("agent.run_id")
        if run_id in ids:
            assert run_id not in roots, "duplicate_root"
            roots[run_id] = span
    report = {"azure_ingested": True, "content_attributes_present": False, "groups": {}}
    for name, rows in groups.items():
        checked = []
        for row in rows:
            if not row.get("run_id"):
                continue
            root = roots[row["run_id"]]
            props = root["Properties"]
            expected = (
                "gpt-5"
                if name == "baseline"
                else ("gpt-5" if row.get("expected_route") == "reasoning" else "gpt-5-mini")
            )
            if name != "baseline":
                assert props["maf.routing.route"] == row.get("expected_route", "routine")
                assert props["gen_ai.request.model"] == expected
            assert props["gen_ai.agent.id"] == "94a137c6-e4fc-481c-b45d-f2a03d868ba4"
            children = [
                s
                for s in spans
                if s["OperationId"] == root["OperationId"] and s["ParentId"] == root["Id"]
            ]
            models = [s for s in children if s["Properties"].get("gen_ai.operation.name") == "chat"]
            assert len(models) == row["calls"], "missing_model_spans"
            cost = 0.0
            observations = []
            for model in models:
                p = model["Properties"]
                assert p["gen_ai.request.model"] == expected
                if name != "baseline":
                    assert re.fullmatch(
                        re.escape(expected) + r"-\d{4}-\d{2}-\d{2}", p["gen_ai.response.model"]
                    ), "actual_model_missing"
                inputs, outputs = (
                    int(p["gen_ai.usage.input_tokens"]),
                    int(p["gen_ai.usage.output_tokens"]),
                )
                cost += (inputs * PRICES[expected][0] + outputs * PRICES[expected][1]) / 1e6
                observations.append(
                    dict(
                        model=p.get("gen_ai.response.model", expected),
                        input_tokens=inputs,
                        output_tokens=outputs,
                    )
                )
            checked.append(
                dict(
                    case=row.get("id", row.get("expected_route")),
                    kind=row.get("kind"),
                    run_id=row["run_id"],
                    trace_id=root["OperationId"],
                    route=props.get("maf.routing.route"),
                    model=expected,
                    estimated_usd=round(cost, 8),
                    usage=observations,
                )
            )
        report["groups"][name] = checked
    for name in ("baseline", "routed"):
        benign = [r for r in groups[name] if r["kind"] == "benign"]
        assert sum(r["benign_success"] for r in benign) / len(benign) >= 0.9
    totals = {
        name: sum(r["estimated_usd"] for r in rows if r["kind"] == "benign")
        for name, rows in report["groups"].items()
        if name != "probes"
    }
    report["benign_estimated_usd"] = totals
    report["benign_savings_fraction"] = 1 - totals["routed"] / totals["baseline"]
    report["benign_median_seconds"] = {
        name: statistics.median(r["seconds"] for r in groups[name] if r["kind"] == "benign")
        for name in ("baseline", "routed")
    }
    assert report["benign_savings_fraction"] > 0, "no_observed_cost_saving"
    args.report.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "groups"}))


if __name__ == "__main__":
    main()
