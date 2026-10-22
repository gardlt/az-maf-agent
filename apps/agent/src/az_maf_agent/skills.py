"""Reviewed, digest-pinned Markdown guidance; never an authority source."""

import hashlib
import json
import os
import re
import stat
import threading
from dataclasses import dataclass
from pathlib import Path

import yaml

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
            or not (
                re.fullmatch(r"[a-zA-Z0-9_-]+\.md", self.filename)
                or self.filename == f"{self.skill_id}/SKILL.md"
            )
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

    def __init__(self, root: Path, control_path: Path | None = None, control_reader=None):
        self.root = Path(root)
        self.control_path = control_path
        self.control_reader = control_reader
        self.approved: dict[tuple[str, str], Manifest] = {}
        self.revoked: set[tuple[str, str]] = set()
        self.generation = 0
        self.control_generation = None
        self._generation_lock = threading.Lock()

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
        if self.control_path is None and self.control_reader is None:
            return
        state = self.control_reader() if self.control_reader else read_control(self.control_path)
        with self._generation_lock:
            if (
                self.control_generation is not None
                and state["generation"] < self.control_generation
            ):
                raise Denied("skill_control_stale")
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
        directory = package = descriptor = None
        try:
            directory = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            filename = manifest.filename
            if "/" in filename:
                package = os.open(
                    manifest.skill_id,
                    os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                    dir_fd=directory,
                )
                filename = "SKILL.md"
            descriptor = os.open(
                filename,
                os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                dir_fd=package if package is not None else directory,
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
            if package is not None:
                markdown = package_body(markdown, manifest)
        except (OSError, ValueError):
            raise Denied("skill_integrity") from None
        finally:
            if descriptor is not None:
                os.close(descriptor)
            if package is not None:
                os.close(package)
            if directory is not None:
                os.close(directory)
        tools = (
            manifest.tools
            & frozenset(principal_tools)
            & frozenset(application_tools)
            & frozenset(agent_tools)
        )
        skill = Skill(manifest, markdown, tools)
        self.check(skill)
        return skill


class _UniqueLoader(yaml.SafeLoader):
    """Reject duplicate metadata keys rather than silently accepting the last one."""

    def construct_mapping(self, node, deep=False):
        mapping = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            if not isinstance(key, str) or key in mapping:
                raise ValueError("invalid metadata key")
            mapping[key] = self.construct_object(value_node, deep=deep)
        return mapping


def package_body(markdown: str, manifest: Manifest) -> str:
    """Validate the supported standard fields; metadata never grants authority."""
    try:
        if not markdown.startswith("---\n"):
            raise ValueError("missing frontmatter")
        header, body = markdown[4:].split("\n---\n", 1)
        if any(isinstance(token, yaml.tokens.AliasToken) for token in yaml.scan(header)):
            raise ValueError("aliases unsupported")
        data = yaml.load(header, Loader=_UniqueLoader)
        if not isinstance(data, dict) or set(data) - {
            "name",
            "description",
            "license",
            "compatibility",
            "metadata",
            "allowed-tools",
        }:
            raise ValueError("unsupported metadata")
        name = data.get("name")
        if (
            name != manifest.skill_id
            or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name)
            or len(name) > 64
        ):
            raise ValueError("name mismatch")
        description = data.get("description")
        if not isinstance(description, str) or not 1 <= len(description.strip()) <= 1024:
            raise ValueError("invalid description")
        for field, limit in (("license", 1024), ("compatibility", 500)):
            if field in data and (
                not isinstance(data[field], str) or not 1 <= len(data[field].strip()) <= limit
            ):
                raise ValueError("invalid optional field")
        metadata = data.get("metadata", {})
        if not isinstance(metadata, dict) or any(
            not isinstance(k, str) or not isinstance(v, str) for k, v in metadata.items()
        ):
            raise ValueError("invalid metadata")
        if "version" in metadata and metadata["version"] != manifest.version:
            raise ValueError("version mismatch")
        if "allowed-tools" in data and (
            not isinstance(data["allowed-tools"], str)
            or frozenset(data["allowed-tools"].split()) != manifest.tools
        ):
            raise ValueError("tool declaration mismatch")
        if not body.strip():
            raise ValueError("empty instructions")
        return body.lstrip("\n")
    except (yaml.YAMLError, ValueError, TypeError):
        raise ValueError("invalid skill package") from None


def reviewed_registry(root: Path, control_path: Path | None = None) -> SkillRegistry:
    """Load the operator-reviewed bundle index. Never accept this path from a user."""
    root = Path(root)
    index = root / "approved.json"
    entries = json.loads(read_regular(index, 16384))
    if not isinstance(entries, list) or len(entries) > 16:
        raise ValueError("invalid approval index")
    registry = SkillRegistry(root, control_path)
    seen = set()
    for entry in entries:
        key = (entry["skill_id"], entry["version"])
        if key in seen:
            raise ValueError("duplicate approved skill")
        seen.add(key)
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


def parse_control(content: bytes | str) -> dict:
    try:
        state = json.loads(content)
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


def read_control(path: Path) -> dict:
    try:
        return parse_control(read_regular(path, 16384))
    except (OSError, ValueError):
        raise Denied("skill_control_unavailable") from None
