"""Reviewed, digest-pinned Markdown guidance; never an authority source."""

import hashlib
import json
import os
import re
import stat
from dataclasses import dataclass
from pathlib import Path

from .model import Denied

READ_TOOLS = frozenset({"search_movies", "get_movie"})
MAX_SKILL_BYTES = 8192


@dataclass(frozen=True)
class Manifest:
    skill_id: str
    version: str
    owner: str
    purpose: str
    inputs: str
    outputs: str
    filename: str
    sha256: str
    tools: frozenset[str]

    def __post_init__(self):
        if (
            not re.fullmatch(r"[a-z][a-z0-9-]{0,63}", self.skill_id)
            or not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", self.version)
            or not re.fullmatch(r"[a-zA-Z0-9_-]+\.md", self.filename)
            or not re.fullmatch(r"[a-f0-9]{64}", self.sha256)
            or any(
                not isinstance(v, str) or not 1 <= len(v) <= 500
                for v in (self.owner, self.purpose, self.inputs, self.outputs)
            )
            or not isinstance(self.tools, frozenset)
            or not self.tools <= READ_TOOLS
        ):
            raise ValueError("invalid skill manifest")


@dataclass(frozen=True)
class Skill:
    manifest: Manifest
    markdown: str
    tools: frozenset[str]


class SkillRegistry:
    """Operator-owned process-local approvals. Composition and memory are unavailable.

    Approval digests must come from reviewed application configuration, never a caller
    or model. Revocations survive rollback within this registry, not process restart.
    Shared persistent control state is a Stage 5 dependency.
    """

    def __init__(self, root: Path, control_path: Path | None = None):
        self.root = Path(root)
        self.control_path = control_path
        self.approved: dict[tuple[str, str], Manifest] = {}
        self.revoked: set[tuple[str, str]] = set()
        self.generation = 0
        self.control_generation = None

    def publish(self, manifest: Manifest):
        key = (manifest.skill_id, manifest.version)
        if key in self.revoked:
            raise Denied("skill_revoked")
        if key in self.approved and self.approved[key] != manifest:
            raise Denied("skill_version_conflict")
        self.approved[key] = manifest
        self.generation += 1

    def revoke(self, skill_id: str, version: str):
        self.revoked.add((skill_id, version))
        self.generation += 1

    def control_check(self, skill_id, version):
        if self.control_path is None:
            return
        state = read_control(self.control_path)
        self.control_generation = state["generation"]
        key = f"{skill_id}@{version}"
        if key in state["revoked"]:
            raise Denied("skill_revoked")
        if key in state["disabled"]:
            raise Denied("skill_disabled")

    def check(self, skill: Skill):
        self.control_check(skill.manifest.skill_id, skill.manifest.version)
        key = (skill.manifest.skill_id, skill.manifest.version)
        if key in self.revoked or self.approved.get(key) != skill.manifest:
            raise Denied("skill_revoked")

    def load(self, skill_id, version, principal_tools, application_tools, agent_tools):
        # Lookup precedes all filesystem access; IDs never become filesystem paths.
        key = (skill_id, version)
        if key in self.revoked:
            raise Denied("skill_revoked")
        manifest = self.approved.get(key)
        if manifest is None:
            raise Denied("skill_not_approved")
        self.control_check(skill_id, version)
        directory = descriptor = None
        try:
            directory = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            descriptor = os.open(
                manifest.filename, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory
            )
            if not stat.S_ISREG(os.fstat(descriptor).st_mode):
                raise ValueError("not regular")
            with os.fdopen(descriptor, "rb") as stream:
                descriptor = None
                content = stream.read(MAX_SKILL_BYTES + 1)
            if not content or len(content) > MAX_SKILL_BYTES:
                raise ValueError("size")
            if hashlib.sha256(content).hexdigest() != manifest.sha256:
                raise ValueError("digest")
            markdown = content.decode("utf-8")
        except (OSError, ValueError):
            raise Denied("skill_integrity") from None
        finally:
            if descriptor is not None:
                os.close(descriptor)
            if directory is not None:
                os.close(directory)
        tools = (
            manifest.tools
            & frozenset(principal_tools)
            & frozenset(application_tools)
            & frozenset(agent_tools)
        )
        return Skill(manifest, markdown, tools)


def reviewed_registry(root: Path, control_path: Path | None = None) -> SkillRegistry:
    """Load the operator-reviewed bundle index. Never accept this path from a user."""
    root = Path(root)
    index = root / "approved.json"
    entries = json.loads(read_regular(index, 16384))
    if not isinstance(entries, list) or len(entries) > 16:
        raise ValueError("invalid approval index")
    registry = SkillRegistry(root, control_path)
    for entry in entries:
        registry.publish(Manifest(**{**entry, "tools": frozenset(entry["tools"])}))
    return registry


def read_regular(path: Path, limit: int) -> bytes:
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, "rb") as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise ValueError("not a regular file")
        content = stream.read(limit + 1)
    if len(content) > limit:
        raise ValueError("file too large")
    return content


def read_control(path: Path) -> dict:
    try:
        state = json.loads(read_regular(path, 16384))
        if (
            set(state) != {"generation", "disabled", "revoked"}
            or type(state["generation"]) is not int
            or state["generation"] < 0
        ):
            raise ValueError("invalid state")
        for field in ("disabled", "revoked"):
            if (
                not isinstance(state[field], list)
                or len(state[field]) > 128
                or any(
                    not isinstance(v, str)
                    or not re.fullmatch(r"[a-z][a-z0-9-]{0,63}@[0-9]+\.[0-9]+\.[0-9]+", v)
                    for v in state[field]
                )
            ):
                raise ValueError("invalid control keys")
        return state
    except (OSError, ValueError, TypeError, KeyError):
        raise Denied("skill_control_unavailable") from None
