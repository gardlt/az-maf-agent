#!/usr/bin/env python3
"""Operator-only dev skill controls in an existing Container App's ARM tags.

Requires Azure CLI operator sign-in with tags/write. The app only needs Reader.
Do not grant this capability to the workload. Run one operator at a time.
"""

import argparse
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

from az_maf_agent.skills import parse_control, reviewed_registry

TAG = "maf-skill-control"


def az(*args):
    result = subprocess.run(["az", *args, "-o", "json"], capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError("Azure control operation failed; check operator authorization")
    return json.loads(result.stdout) if result.stdout.strip() else None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["init", "status", "disable", "enable", "revoke"])
    parser.add_argument("--resource-id", required=True)
    parser.add_argument("--skill", choices=["movie-research", "movie-night"])
    parser.add_argument("--version", default="1.0.0")
    parser.add_argument("--bundle", type=Path, default=Path("skills"))
    args = parser.parse_args()
    # Lock serializes invocations on this operator workstation; multiple operators
    # require a future control backend with conditional writes.
    import fcntl

    lock_path = Path(tempfile.gettempdir()) / (
        "maf-skill-" + hashlib.sha256(args.resource_id.encode()).hexdigest() + ".lock"
    )
    with lock_path.open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        tags = az("tag", "list", "--resource-id", args.resource_id)["properties"]["tags"] or {}
        if args.action == "init":
            if TAG in tags:
                state = parse_control(tags[TAG])  # Never reset existing controls.
            else:
                state = {"generation": 0, "disabled": [], "revoked": []}
        else:
            state = parse_control(tags[TAG])
        if args.action in ("disable", "enable", "revoke"):
            registry = reviewed_registry(args.bundle)
            if (args.skill, args.version) not in registry.approved:
                raise ValueError("unapproved version")
            key = f"{args.skill}@{args.version}"
            if args.action == "enable" and key in state["revoked"]:
                raise ValueError("revoked version cannot be enabled")
            if args.action == "enable":
                state["disabled"] = sorted(set(state["disabled"]) - {key})
            else:
                field = "revoked" if args.action == "revoke" else "disabled"
                state[field] = sorted(set(state[field]) | {key})
            state["generation"] += 1
        encoded = json.dumps(state, separators=(",", ":"))
        parse_control(encoded)
        if len(encoded) > 256:
            raise ValueError("control tag capacity exceeded")
        if args.action != "status":
            az(
                "tag",
                "update",
                "--resource-id",
                args.resource_id,
                "--operation",
                "Merge",
                "--tags",
                f"{TAG}={encoded}",
            )
        print(
            json.dumps(
                {
                    "action": args.action,
                    "skill_id": args.skill,
                    "version": args.version,
                    "control": state,
                }
            )
        )


if __name__ == "__main__":
    main()
