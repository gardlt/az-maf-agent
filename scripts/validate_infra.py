"""Compile the infrastructure and verify deployment selection and security contracts offline."""

import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DUMMY = {
    "AZURE_ENV_NAME": "dev",
    "AZURE_LOCATION": "eastus2",
    "MAF_REGISTRY_NAME": "crmafvalidation123",
    "MAF_REGISTRY_SKU": "Basic",
    "MAF_AGENT_IMAGE": "example.azurecr.io/agent@sha256:" + "a" * 64,
    "MAF_MCP_IMAGE": "example.azurecr.io/mcp@sha256:" + "b" * 64,
    "MAF_CONTAINMENT_IMAGE": "example.azurecr.io/fixture@sha256:" + "c" * 64,
    "MAF_TENANT_ID": "00000000-0000-0000-0000-000000000000",
    "MAF_AGENT_AUDIENCE": "00000000-0000-0000-0000-000000000001",
    "MAF_ALLOWED_USERS": "00000000-0000-0000-0000-000000000002",
    "MAF_API_CLIENT_ID": "00000000-0000-0000-0000-000000000003",
    "MAF_CLI_CLIENT_ID": "00000000-0000-0000-0000-000000000004",
    "MAF_AUTH_CLIENT_SECRET": "validation-only",
    "MAF_MCP_AUDIENCE": "00000000-0000-0000-0000-000000000005",
    "TMDB_API_READ_ACCESS_TOKEN": "validation-only",
    "MAF_MEMORY_ACCOUNT_NAME": "stmafmemvalidation123",
    "MAF_INSIGHTS_INGESTION_HOST": "eastus2.example.invalid",
    "MAF_ENABLE_AGENT_IDENTITY": "false",
    "MAF_ENABLE_AGENT_TRACING": "false",
}


def compiler():
    executable = shutil.which("bicep") or str(Path.home() / ".azure/bin/bicep")
    if not Path(executable).is_file():
        subprocess.run(["az", "bicep", "install"], check=True, capture_output=True)
        executable = str(Path.home() / ".azure/bin/bicep")
    return executable


def clean(resource):
    return {k: v for k, v in resource.items() if k not in ("dependsOn", "condition", "metadata")}


def bound_resource(module):
    """Expand a resource wrapper's direct parameters, preserving its caller expressions."""
    bindings = {k: v["value"] for k, v in module["properties"]["parameters"].items()}

    def bind(value):
        if isinstance(value, dict):
            return {k: bind(v) for k, v in value.items()}
        if isinstance(value, list):
            return [bind(v) for v in value]
        if isinstance(value, str):
            match = re.fullmatch(r"\[parameters\('([^']+)'\)\]", value)
            if match:
                return bindings.get(match[1], value)
        return value

    return [clean(bind(r)) for r in module["properties"]["template"]["resources"]]


def verify_resource_contracts(compiled):
    snapshots = json.loads((ROOT / "infra/tests/resource-contracts.json").read_text())["resources"]

    def expected(group, kind):
        return [v for k, v in snapshots.items() if k.startswith(group + ":") and v["type"] == kind]

    def direct(path):
        return [clean(r) for r in compiled[path]["resources"]]

    def wrapper(path, name):
        module = next(r for r in compiled[path]["resources"] if r["name"] == name)
        return bound_resource(module)

    checks = [
        (
            expected("agent", "Microsoft.App/containerApps"),
            wrapper("patterns/agent.bicep", "agent-container-app"),
        ),
        (
            expected("agent", "Microsoft.App/containerApps/authConfigs"),
            wrapper("patterns/agent.bicep", "authentication"),
        ),
        (
            expected("movieMcp", "Microsoft.App/containerApps"),
            wrapper("patterns/movie-mcp.bicep", "movie-mcp-container-app"),
        ),
        (expected("memoryCleanup", "Microsoft.App/jobs"), direct("modules/cleanup-job.bicep")),
        (
            expected("memoryHealth", "Microsoft.Insights/scheduledQueryRules"),
            wrapper("patterns/memory-cleanup-monitor.bicep", "heartbeat-alert"),
        ),
        (
            expected("controlMonitoring", "Microsoft.Insights/components"),
            direct("modules/application-insights.bicep"),
        ),
        (
            expected("controlMonitoring", "Microsoft.Insights/scheduledQueryRules"),
            wrapper("patterns/control-monitoring.bicep", "fault-alert"),
        ),
        (
            expected("foundation", "Microsoft.ContainerRegistry/registries"),
            direct("modules/container-registry.bicep"),
        ),
        (
            expected("foundation", "Microsoft.OperationalInsights/workspaces"),
            direct("modules/log-analytics-workspace.bicep"),
        ),
        (
            expected("foundation", "Microsoft.ManagedIdentity/userAssignedIdentities"),
            direct("modules/managed-identity.bicep"),
        ),
    ]
    for kind in [
        "Microsoft.Storage/storageAccounts",
        "Microsoft.Storage/storageAccounts/blobServices",
        "Microsoft.Storage/storageAccounts/blobServices/containers",
    ]:
        checks.append(
            (
                expected("memory", kind),
                [r for r in direct("modules/storage-account.bicep") if r["type"] == kind],
            )
        )
    old_storage = [
        v
        for k, v in snapshots.items()
        if k.startswith("controlStorage:") and v["type"].startswith("Microsoft.Storage/")
    ]
    checks.append((old_storage, direct("modules/guardrail-storage.bicep")))
    checks.append(
        (
            expected("memoryRoles", "Microsoft.Authorization/roleAssignments"),
            direct("modules/blob-data-roles.bicep"),
        )
    )
    old_roles = [
        v
        for k, v in snapshots.items()
        if k.startswith("controlStorage:") and v["type"].startswith("Microsoft.Authorization/")
    ]
    checks.append((old_roles, direct("modules/guardrail-roles.bicep")))
    for i, (before, after) in enumerate(checks):
        if before != after:
            raise AssertionError("resource_contract_changed:" + str(i))
    return len(checks)


def expression(text, params, variables):
    """Evaluate only the pure Boolean functions used by the main target selectors."""
    tokens = re.findall(r"'[^']*'|[A-Za-z_][A-Za-z_0-9]*|[(),.]", text.strip("[]"))
    cursor = 0

    def parse():
        nonlocal cursor
        token = tokens[cursor]
        cursor += 1
        if token.startswith("'"):
            return token[1:-1]
        if token in ("true", "false"):
            return token == "true"
        assert tokens[cursor] == "("
        cursor += 1
        args = []
        while tokens[cursor] != ")":
            args.append(parse())
            if tokens[cursor] == ",":
                cursor += 1
        cursor += 1
        functions = {
            "parameters": lambda key: params[key],
            "variables": lambda key: expression(variables[key], params, variables),
            "createArray": lambda *items: list(items),
            "contains": lambda items, value: value in items,
            "and": lambda *items: all(items),
            "or": lambda *items: any(items),
            "equals": lambda a, b: a == b,
            "not": lambda value: not value,
        }
        return functions[token](*args)

    result = parse()
    assert cursor == len(tokens)
    return result


def verify_selection(main):
    params = {k: v.get("defaultValue") for k, v in main["parameters"].items()}
    params.update(enableMemory=True, enableGuardrails=True)
    expected = {
        "all": {
            "foundation",
            "agent",
            "movieMcp",
            "memory-storage",
            "guardrail-storage",
            "control-monitoring",
        },
        "foundation": {"foundation"},
        "agent": {"agent"},
        "movie-mcp": {"movieMcp"},
        "memory": {"memory-storage"},
        "controls": {"guardrail-storage", "control-monitoring"},
        "network": {"controlled-egress"},
        "model": {"foundry-model"},
        "access": set(),
        "containment": {"containment-fixture"},
    }
    for target, wanted in expected.items():
        params["deploymentTarget"] = target
        actual = {
            r["name"]
            for r in main["resources"]
            if expression(r["condition"], params, main["variables"])
        }
        assert actual == wanted, (target, actual, wanted)
    assert params["registrySku"] == "Basic"
    assert main["parameters"]["authClientSecret"]["type"].lower() == "securestring"
    assert main["parameters"]["tmdbApiReadAccessToken"]["type"].lower() == "securestring"
    return len(expected)


def main():
    infra = ROOT / "infra"
    assert [p.name for p in infra.glob("*.bicep")] == ["main.bicep"]
    for file in (infra / "modules").glob("*.bicep"):
        assert not re.search(r"^module\s", file.read_text(), re.M), file
    for file in infra.glob("*.bicepparam"):
        assert file.read_text().startswith("using './main.bicep'"), file
    env = dict(os.environ, **DUMMY)
    # The Azure CLI container omits ICU; Bicep compilation uses invariant identifiers.
    env.setdefault("DOTNET_SYSTEM_GLOBALIZATION_INVARIANT", "1")
    command = compiler()
    compiled = {}
    with tempfile.TemporaryDirectory(prefix="maf-infra-") as temp:
        for file in sorted(infra.rglob("*.bicep")):
            output = Path(temp) / (str(file.relative_to(infra)).replace("/", "_") + ".json")
            result = subprocess.run(
                [command, "build", str(file), "--outfile", str(output)],
                env=env,
                capture_output=True,
                text=True,
            )
            if result.returncode:
                raise RuntimeError(result.stderr)
            if "Warning " in result.stderr:
                print(result.stderr.strip())
            compiled[str(file.relative_to(infra))] = json.loads(output.read_text())
        profiles = list(infra.glob("*.bicepparam"))
        for file in sorted(profiles):
            result = subprocess.run(
                [
                    command,
                    "build-params",
                    str(file),
                    "--outfile",
                    str(Path(temp) / (file.name + ".json")),
                ],
                env=env,
                capture_output=True,
                text=True,
            )
            if result.returncode:
                raise RuntimeError(result.stderr)
        app_deployments = [
            r["name"]
            for pattern in ("patterns/agent.bicep", "patterns/movie-mcp.bicep")
            for r in compiled[pattern]["resources"]
        ]
        assert len(app_deployments) == len(set(app_deployments)), "application_deployment_name_collision"
        contracts = verify_resource_contracts(compiled)
        selectors = verify_selection(compiled["main.bicep"])
    print(
        json.dumps(
            dict(
                compiled_bicep_files=len(compiled),
                parameter_profiles=len(profiles),
                preserved_resource_contracts=contracts,
                deployment_target_checks=selectors,
            )
        )
    )


if __name__ == "__main__":
    main()
