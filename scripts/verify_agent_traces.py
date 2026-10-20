"""Verify actual Azure-ingested agent/model/MCP spans for a hosted canary."""

import argparse
import json
import re
import subprocess
from pathlib import Path

CANARY = "AGENT_TRACE_PRIVATE_CANARY_9d9d45f0"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--canary-report", type=Path, required=True)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    canary = json.loads(args.canary_report.read_text())
    trace_id = canary["trace_id"]
    if not re.fullmatch("[a-f0-9]{32}", trace_id):
        raise ValueError("invalid trace ID")
    query = (
        "union isfuzzy=true AppDependencies, AppRequests, AppTraces, AppExceptions "
        "| where TimeGenerated > ago(2h) "
        f"| where OperationId == '{trace_id}' "
        '| project TimeGenerated, Type, Name=column_ifexists("Name", ""), '
        'Id=column_ifexists("Id", ""), ParentId=column_ifexists("ParentId", ""), '
        'Properties, Message=column_ifexists("Message", ""), '
        'Details=column_ifexists("Details", dynamic(null))'
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
    rows = json.loads(result.stdout)
    assert rows, "trace_not_ingested_yet"
    assert CANARY not in result.stdout, "sensitive_canary_exported"
    forbidden = {
        "gen_ai.input.messages",
        "gen_ai.output.messages",
        "gen_ai.system_instructions",
        "gen_ai.tool.call.arguments",
        "gen_ai.tool.call.result",
        "http.request.header.authorization",
    }
    spans = []
    for row in rows:
        props = row.get("Properties") or {}
        if isinstance(props, str):
            props = json.loads(props)
        assert not forbidden.intersection(props), "content_attribute_exported"
        operation = props.get("gen_ai.operation.name")
        if operation:
            spans.append(
                {
                    "name": row["Name"],
                    "id": row["Id"],
                    "parent_id": row["ParentId"],
                    "attributes": props,
                }
            )
    roots = [s for s in spans if s["attributes"]["gen_ai.operation.name"] == "invoke_agent"]
    assert len(roots) == 1
    root = roots[0]
    children = [s for s in spans if s["parent_id"] == root["id"]]
    operations = {s["attributes"]["gen_ai.operation.name"] for s in children}
    assert {"chat", "execute_tool"} <= operations, "model_or_mcp_correlation_missing"
    assert root["attributes"]["agent.run_id"] == canary["run_id"]
    assert root["attributes"]["gen_ai.agent.id"] == "94a137c6-e4fc-481c-b45d-f2a03d868ba4"
    assert int(root["attributes"]["gen_ai.usage.input_tokens"]) > 0
    assert int(root["attributes"]["gen_ai.usage.output_tokens"]) > 0
    report = {
        "trace_id": trace_id,
        "run_id": canary["run_id"],
        "azure_ingested": True,
        "agent_model_mcp_correlated": True,
        "sensitive_canary_present": False,
        "content_attributes_present": False,
        "spans": spans,
    }
    args.report.write_text(json.dumps(report, indent=2) + "\n")
    print(
        json.dumps(
            {
                "trace_id": trace_id,
                "azure_spans": len(spans),
                "agent_model_mcp_correlated": True,
                "sensitive_canary_present": False,
            }
        )
    )


if __name__ == "__main__":
    main()
