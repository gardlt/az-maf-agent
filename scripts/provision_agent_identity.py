"""Repeatable operator-only Agent ID provisioning. Default is read-only planning."""

import argparse
import json
from pathlib import Path
from urllib.parse import urlsplit
from uuid import UUID

import httpx
from azure.identity import AzureCliCredential

GRAPH = "https://graph.microsoft.com/"


class Graph:
    def __init__(self, tenant):
        self.credential = AzureCliCredential(tenant_id=tenant)
        self.http = httpx.Client(timeout=20, follow_redirects=False)

    def request(self, method, path, body=None):
        url = GRAPH + path
        token = self.credential.get_token("https://graph.microsoft.com/.default")
        response = self.http.request(
            method,
            url,
            headers={"Authorization": "Bearer " + token.token, "OData-Version": "4.0"},
            json=body,
        )
        if not response.is_success:
            # No response body or credentials in operator logs.
            raise RuntimeError(f"graph_{response.status_code}_{method}_{path.split('?')[0]}")
        return response.json() if response.content else {}

    def collection(self, path):
        values = []
        for _ in range(20):
            page = self.request("GET", path)
            values.extend(page["value"])
            next_url = page.get("@odata.nextLink")
            if next_url is None:
                return values
            parsed = urlsplit(next_url)
            if parsed.scheme != "https" or parsed.netloc != "graph.microsoft.com":
                raise RuntimeError("invalid_graph_pagination")
            path = parsed.path.lstrip("/") + ("?" + parsed.query if parsed.query else "")
        raise RuntimeError("graph_inventory_limit")

    def close(self):
        self.http.close()
        self.credential.close()


def one(values, **match):
    matches = [value for value in values if all(value.get(k) == v for k, v in match.items())]
    if len(matches) > 1:
        raise RuntimeError("duplicate_agent_identity_objects")
    return matches[0] if matches else None


def provision(graph, *, environment, tenant, sponsor, managed_identity, apply=False):
    blueprint_name = "bp-maf-agent-" + environment
    agent_name = "agent-maf-" + environment
    blueprints = graph.collection("beta/applications/microsoft.graph.agentIdentityBlueprint")
    identities = graph.collection(
        "beta/servicePrincipals/microsoft.graph.agentIdentity?$select=id,appId,displayName,agentIdentityBlueprintId"
    )
    blueprint = one(blueprints, displayName=blueprint_name)
    agent = one(identities, displayName=agent_name)
    plan = {
        "environment": environment,
        "tenant_id": tenant,
        "blueprint_name": blueprint_name,
        "agent_name": agent_name,
        "sponsor_and_owner_id": sponsor,
        "federated_managed_identity_principal_id": managed_identity,
        "blueprint_exists": blueprint is not None,
        "agent_exists": agent is not None,
        "apply": apply,
    }
    if not apply:
        return plan
    binding = [GRAPH + "v1.0/users/" + sponsor]
    if blueprint is None:
        blueprint = graph.request(
            "POST",
            "v1.0/applications/microsoft.graph.agentIdentityBlueprint",
            {
                "displayName": blueprint_name,
                "owners@odata.bind": binding,
                "sponsors@odata.bind": binding,
            },
        )
    blueprint_id = str(UUID(blueprint["id"]))
    blueprint_client = str(UUID(blueprint["appId"]))
    principals = graph.collection(
        "beta/servicePrincipals/microsoft.graph.agentIdentityBlueprintPrincipal"
    )
    parent = one(principals, appId=blueprint_client)
    if parent is None:
        parent = graph.request(
            "POST",
            "v1.0/servicePrincipals/microsoft.graph.agentIdentityBlueprintPrincipal",
            {"appId": blueprint_client},
        )
    credential_path = "v1.0/applications/" + blueprint_id + "/federatedIdentityCredentials"
    credentials = graph.collection(credential_path)
    desired = {
        "name": "container-app-managed-identity",
        "issuer": "https://login.microsoftonline.com/" + tenant + "/v2.0",
        "subject": managed_identity,
        "audiences": ["api://AzureADTokenExchange"],
    }
    existing = one(credentials, name=desired["name"])
    if existing is None:
        graph.request("POST", credential_path, desired)
    elif any(existing.get(k) != v for k, v in desired.items()):
        raise RuntimeError("federated_credential_conflict")
    if agent is None:
        agent = graph.request(
            "POST",
            "beta/servicePrincipals/microsoft.graph.agentIdentity",
            {
                "displayName": agent_name,
                "agentIdentityBlueprintId": blueprint_client,
                "owners@odata.bind": binding,
                "sponsors@odata.bind": binding,
            },
        )
    if agent.get("agentIdentityBlueprintId") != blueprint_client:
        raise RuntimeError("agent_blueprint_mismatch")
    return {
        **plan,
        "blueprint_object_id": blueprint_id,
        "blueprint_client_id": blueprint_client,
        "blueprint_principal_id": str(UUID(parent["id"])),
        "agent_object_id": str(UUID(agent["id"])),
        "agent_client_id": str(UUID(agent["appId"])),
    }


def mcp_read_role(graph, audience, agent_id, *, apply=False):
    resource = one(
        graph.collection("v1.0/servicePrincipals?$filter=appId%20eq%20'" + audience + "'"),
        appId=audience,
    )
    if resource is None:
        raise RuntimeError("mcp_service_principal_missing")
    role = one(resource["appRoles"], value="Catalog.Read")
    if not role or not role["isEnabled"] or "Application" not in role["allowedMemberTypes"]:
        raise RuntimeError("mcp_read_role_missing")
    plan = {"resourceId": resource["id"], "appRoleId": role["id"], "principalId": agent_id}
    if agent_id is not None:
        path = "v1.0/servicePrincipals/" + agent_id + "/appRoleAssignments"
        existing = one(graph.collection(path), resourceId=resource["id"], appRoleId=role["id"])
        if apply and existing is None:
            graph.request("POST", path, plan)
    return plan


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--environment", choices=["dev", "stage", "prod"], required=True)
    parser.add_argument("--tenant", type=lambda v: str(UUID(v)), required=True)
    parser.add_argument("--sponsor", type=lambda v: str(UUID(v)), required=True)
    parser.add_argument(
        "--managed-identity-principal-id", type=lambda v: str(UUID(v)), required=True
    )
    parser.add_argument("--mcp-audience", type=lambda v: str(UUID(v)))
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    graph = Graph(args.tenant)
    try:
        result = provision(
            graph,
            environment=args.environment,
            tenant=args.tenant,
            sponsor=args.sponsor,
            managed_identity=args.managed_identity_principal_id,
            apply=args.apply,
        )
        if args.mcp_audience:
            result["mcp_catalog_read_assignment"] = mcp_read_role(
                graph, args.mcp_audience, result.get("agent_object_id"), apply=args.apply
            )
        args.output.write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result))
    finally:
        graph.close()


if __name__ == "__main__":
    main()
