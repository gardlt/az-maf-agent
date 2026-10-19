"""Local operator tool. Run under an OS identity allowed to write the control file."""

import argparse
import fcntl
import json
import os
import tempfile
from pathlib import Path

from .model import Denied
from .skills import read_control, reviewed_registry


def update_control(path, action, skill_id, version):
    """Serialize operators and atomically replace state; app needs read permission only."""
    path = Path(path)
    key = f"{skill_id}@{version}"
    with open(str(path) + ".lock", "a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        state = read_control(path)
        if action == "enable" and key in state["revoked"]:
            raise Denied("skill_revoked")
        if action == "revoke":
            state["revoked"] = sorted(set(state["revoked"]) | {key})
        elif action == "disable":
            state["disabled"] = sorted(set(state["disabled"]) | {key})
        elif action == "enable":
            state["disabled"] = sorted(set(state["disabled"]) - {key})
        else:
            raise ValueError("unknown action")
        state["generation"] += 1
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as stream:
                temporary = stream.name
                json.dump(state, stream)
                stream.flush()
                os.fsync(stream.fileno())
            # Validate before publication, including key/size bounds.
            read_control(Path(temporary))
            os.replace(temporary, path)
        finally:
            if temporary and os.path.exists(temporary):
                os.unlink(temporary)
    return state["generation"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["validate", "disable", "enable", "revoke"])
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--control", type=Path, required=True)
    parser.add_argument("--skill")
    parser.add_argument("--version")
    args = parser.parse_args()
    registry = reviewed_registry(args.bundle, args.control)
    try:
        if args.action == "validate":
            for manifest in registry.approved.values():
                registry.load(manifest.skill_id, manifest.version, (), (), ())
            print("Approved bundle and control state validated.")
        else:
            if (args.skill, args.version) not in registry.approved:
                raise Denied("skill_not_approved")
            generation = update_control(args.control, args.action, args.skill, args.version)
            print(
                json.dumps(
                    {
                        "action": args.action,
                        "skill_id": args.skill,
                        "version": args.version,
                        "control_generation": generation,
                    }
                )
            )
    except (Denied, ValueError, OSError):
        parser.exit(1, "Skill operation denied; check reviewed bundle and operator access.\n")


if __name__ == "__main__":
    main()
