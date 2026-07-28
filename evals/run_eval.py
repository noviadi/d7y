#!/usr/bin/env python3
"""Minimal D7Y skill eval runner for Claude Code 2.1.218.

Executes one selected case in paired with-skill and no-skill configurations,
captures raw evidence, applies a small fixed set of trusted deterministic
checks, and writes a complete, source-free artifact tree. This is D7Y
contributor infrastructure for the eval-execution-harness plan, not a top-level
``d7y eval`` capability.

Public entry point:

    python3 evals/run_eval.py --source-repo <repo> --suite <repo-relative-evals.json> \
        --case <case-id> --output <dir> [--commit <ref>] [--claude <path>] [--dry-run]

All run inputs (suite, case, fixtures, skill, repository seed, ``d7y`` façade,
and initiative checker) are read exclusively from immutable Git objects at the
resolved commit. The source checkout is never used as a workspace, never passed
to the agent, and is snapshotted before and after every exit path.

The target workspace is bound through the supported Claude command surface only:
each arm starts in a distinct process directory and receives the unchanged case
prompt wrapped in identical neutral harness instructions that name that arm's
absolute target workspace and require D7Y commands to use
``--root <absolute workspace>``. There is no top-level Claude ``--root`` flag
(Claude Code 2.1.218 does not declare one).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pwd
import shlex
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from validate_skill_evals import validate_suite_data

# ---------------------------------------------------------------------------
# Runtime contract constants (Claude Code 2.1.218 spike).
# ---------------------------------------------------------------------------

CLAUDE_VERSION = "2.1.218"
EXPECTED_MODEL = "claude-sonnet-5"
# Permitted routed assistant model under this user's z.ai routing. Canonical /
# requested model stays claude-sonnet-5; routed assistant events may identify
# one of these and must not be rejected as a mismatch. Do not widen this set
# without committed capability evidence or an explicit live-qualification
# return.
ROUTED_MODELS = {"claude-sonnet-5", "glm-4.7", "glm-4.6"}
EXPECTED_PERMISSION_MODE = "dontAsk"
EXPECTED_TOOLS = ["Skill", "Read", "Write", "Edit", "Bash"]
EXPECTED_TOOLS_ARG = ",".join(EXPECTED_TOOLS)
EMPTY_MCP_CONFIG = '{"mcpServers":{}}'

SESSION_PLUGIN_NAME = "d7y-eval-session"
CONTROL_PLUGIN_NAME = "d7y-eval-control"
PLUGIN_VERSION = "0.0.1"
BUILT_IN_SKILL = "doctor"

# Namespaced target: <plugin>:<skill>. Only an exact match counts.
def expected_target(skill_name: str) -> str:
    return f"{SESSION_PLUGIN_NAME}:{skill_name}"

DEFAULT_TIMEOUT_SECONDS = 600.0
ESCALATION_SECONDS = 5.0

# Required result-event fields and their expected types.
REQUIRED_RESULT_FIELDS: dict[str, type | tuple[type, ...]] = {
    "result": str,
    "is_error": bool,
    "num_turns": int,
    "permission_denials": list,
    "modelUsage": dict,
}

# Canaries test suppression. They live only in locations the selected posture
# claims to suppress and are never passed as positive agent input.
PROJECT_INSTRUCTION_CANARY = "D7Y-EVAL-PROJECT-INSTRUCTION-SUPPRESSION-CANARY"
# Observable signal the project-instruction canary would emit if its instructions
# were loaded. Detection scans every event/result channel for this token.
PROJECT_INSTRUCTION_SIGNAL = "D7Y-EVAL-INSTRUCTION-CANARY-SIGNAL-7Q"
FAKE_GLOBAL_SKILL_NAME = "d7y-eval-fake-global-skill"
GLOBAL_SKILL_CANARY = "D7Y-EVAL-GLOBAL-SKILL-SUPPRESSION-CANARY"

# Neutral harness instructions appended to the unchanged case prompt. The target
# workspace appears exactly here and nowhere else in the command surface.
HARNESS_INSTRUCTION_TEMPLATE = (
    "\n\n--- D7Y eval harness instructions (identical across both arms) ---\n"
    "Target workspace root: {workspace}\n"
    "Operate only within the target workspace root named above. Before proposing "
    "any initiative, check for an existing match by running exactly "
    "`d7y initiatives list --root {workspace} --json`. After creating any "
    "initiative state, validate it by running exactly "
    "`d7y initiatives check --root {workspace} --json`.\n"
)

# Supported Claude argv surface (everything else is rejected by the strict
# parser). There is deliberately no ``--root`` entry.
ARGV_VALUE_FLAGS = {
    "--output-format",
    "--mcp-config",
    "--permission-mode",
    "--model",
    "--effort",
    "--setting-sources",
    "--settings",
    "--plugin-dir",
    "--tools",
}
ARGV_BOOL_FLAGS = {
    "--print",
    "--verbose",
    "--no-session-persistence",
    "--strict-mcp-config",
}

# Names that must never be staged into a target workspace as agent input.
CONTROL_DESTINATION_NAMES = {
    "settings.json",
    "settings.local.json",
    "CLAUDE.md",
    ".claude-plugin",
    ".claude",
    "benchmark.json",
}
CONTROL_DESTINATION_PREFIXES = ("evals/", "graders/", ".git/")

# Shell-control characters that disqualify a Bash command from the supported
# simple-command shape (no compounds, subshells, pipes, or redirections).
SHELL_CONTROL_CHARS = (";", "&&", "||", "|", "\n", "`", "$(", ">", "<")

REDACTED = "<redacted>"


# ---------------------------------------------------------------------------
# Errors.
# ---------------------------------------------------------------------------


class PreflightError(Exception):
    """A blocking preflight failure. Never carries a secret value."""


# ---------------------------------------------------------------------------
# Git helpers: every run input comes from immutable objects.
# ---------------------------------------------------------------------------


def _git(repo: Path, args: list[str], *, binary: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=not binary,
        check=False,
    )


def resolve_commit(repo: Path, ref: str) -> str:
    """Resolve a ref to exactly one commit SHA."""
    result = _git(repo, ["rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"])
    if result.returncode != 0:
        raise PreflightError(f"cannot resolve commit from ref {ref!r}")
    sha = result.stdout.strip()
    if len(sha) != 40:
        raise PreflightError(f"resolved ref {ref!r} is not a commit")
    return sha


def git_blob_id(repo: Path, commit: str, path: str) -> str:
    result = _git(repo, ["rev-parse", "--verify", "--quiet", f"{commit}:{path}"])
    if result.returncode != 0:
        raise PreflightError(f"object not found at {commit}:{path}")
    return result.stdout.strip()


def git_object_exists(repo: Path, commit: str, path: str) -> bool:
    return (
        _git(repo, ["rev-parse", "--verify", "--quiet", f"{commit}:{path}"]).returncode == 0
    )


def git_show(repo: Path, commit: str, path: str) -> bytes:
    result = _git(repo, ["cat-file", "-p", f"{commit}:{path}"], binary=True)
    if result.returncode != 0:
        raise PreflightError(f"cannot read object {commit}:{path}")
    return result.stdout


def git_entry_mode(repo: Path, commit: str, path: str) -> str:
    """Return the git tree-entry mode for a path (e.g. '100644', '120000')."""
    result = _git(repo, ["ls-tree", "-d", commit, "--", path])
    if result.returncode != 0 or not result.stdout.strip():
        result = _git(repo, ["ls-tree", commit, "--", path])
    line = result.stdout.strip().splitlines()
    if not line:
        raise PreflightError(f"cannot inspect git entry for {path}")
    return line[0].split()[0]


def assert_no_symlink_at(repo: Path, commit: str, path: str) -> None:
    mode = git_entry_mode(repo, commit, path)
    if mode == "120000":
        raise PreflightError(f"committed symlink rejected: {path}")


def assert_tree_has_no_symlinks(repo: Path, commit: str, tree_prefix: str) -> None:
    """Reject any symlink anywhere under a committed tree prefix."""
    result = _git(repo, ["ls-tree", "-r", f"{commit}:{tree_prefix}"])
    for line in result.stdout.splitlines():
        parts = line.split(None, 3)
        if len(parts) >= 4 and parts[0] == "120000":
            raise PreflightError(f"committed symlink rejected in {tree_prefix}: {parts[3]}")


def source_status(repo: Path) -> str:
    return _git(repo, ["status", "--porcelain"]).stdout


# ---------------------------------------------------------------------------
# Output-root and path-safety primitives.
# ---------------------------------------------------------------------------


def _symlink_in_chain(path: Path) -> bool:
    """True if ``path`` or any existing parent component is a symlink."""
    try:
        resolved = path.resolve(strict=False)
    except OSError:
        return True
    # Walk the existing prefix and detect any symlink component.
    candidate = path
    seen: set[Path] = set()
    while candidate not in seen:
        seen.add(candidate)
        try:
            if candidate.is_symlink():
                return True
        except OSError:
            return True
        if candidate.parent == candidate:
            break
        candidate = candidate.parent
    return resolved != path and path.is_symlink()


def verify_output_root(output_dir: Path, source_repo: Path) -> None:
    """Require a genuinely new, disjoint, non-symlink output path.

    Rejects any existing entry (including an empty directory), a symlink at the
    output path or in any existing parent component, and overlap with the source
    repository in either direction.
    """
    if _symlink_in_chain(output_dir):
        raise PreflightError("output root path traverses a symlink")
    output_abs = output_dir.resolve(strict=False)
    source_abs = source_repo.resolve(strict=False)
    try:
        output_abs.relative_to(source_abs)
        raise PreflightError("output root must be outside the source repository")
    except ValueError:
        pass
    try:
        source_abs.relative_to(output_abs)
        raise PreflightError("output root must not contain the source repository")
    except ValueError:
        pass
    if output_dir.exists():
        raise PreflightError("output root already exists; must be a new path")


def safe_relative_path(value: str) -> Path:
    """A path that is relative, has parts, and never escapes via '..'."""
    path = Path(value)
    if path.is_absolute():
        raise PreflightError(f"absolute path not allowed: {value}")
    if ".." in path.parts:
        raise PreflightError(f"path traversal not allowed: {value}")
    if not path.parts:
        raise PreflightError(f"empty path not allowed: {value}")
    normalized = Path(*[p for p in path.parts if p != "."])
    if not normalized.parts:
        raise PreflightError(f"empty path not allowed: {value}")
    return normalized


def is_control_destination(rel: Path) -> bool:
    if rel.name in CONTROL_DESTINATION_NAMES:
        return True
    head = rel.parts[0] + "/"
    return any(head.startswith(p) or str(rel).startswith(p) for p in CONTROL_DESTINATION_PREFIXES)


def prevalidate_staging(entries: list[tuple[str, str]], workspace: Path) -> list[tuple[Path, str]]:
    """Validate the complete staging map before writing anything.

    Each entry is ``(source_rel_to_skill_dir, destination_rel_to_workspace)``.
    Rejects unsafe paths, control destinations, duplicate or
    ancestor/descendant-colliding destinations, and overwrites of existing
    workspace entries. Returns validated ``(destination_path, source)`` pairs.
    """
    seen: dict[Path, str] = {}
    validated: list[tuple[Path, str]] = []
    for source, destination in entries:
        src_path = safe_relative_path(source)
        dest_path = safe_relative_path(destination)
        if is_control_destination(dest_path):
            raise PreflightError(f"control-path collision in destination: {destination}")
        resolved = (workspace / dest_path).resolve(strict=False)
        ws_resolved = workspace.resolve(strict=False)
        try:
            resolved.relative_to(ws_resolved)
        except ValueError:
            raise PreflightError(f"destination escapes workspace: {destination}")
        for prior in seen:
            # Reject equality and ancestor/descendant collisions (a vs a/b).
            prior_resolved = (workspace / prior).resolve(strict=False)
            try:
                resolved.relative_to(prior_resolved)
                raise PreflightError(
                    f"destination {destination} collides with prior {prior.as_posix()}"
                )
            except ValueError:
                pass
            try:
                prior_resolved.relative_to(resolved)
                raise PreflightError(
                    f"destination {destination} collides with prior {prior.as_posix()}"
                )
            except ValueError:
                pass
        if dest_path in seen:
            raise PreflightError(f"duplicate destination: {destination}")
        target = workspace / dest_path
        if target.exists():
            raise PreflightError(f"destination already exists in workspace: {destination}")
        seen[dest_path] = source
        validated.append((dest_path, src_path.as_posix()))
    return validated


# ---------------------------------------------------------------------------
# Suite / case loading from immutable objects.
# ---------------------------------------------------------------------------


def skill_dir_of_suite(suite_repo_path: str) -> str:
    """``skills/<skill>/evals/evals.json`` -> ``skills/<skill>``."""
    parts = Path(suite_repo_path).parts
    if len(parts) < 3 or parts[-1] != "evals.json" or parts[-2] != "evals":
        raise PreflightError(f"suite path must be .../<skill>/evals/evals.json: {suite_repo_path}")
    return Path(*parts[:-2]).as_posix()


def _git_source_checker(repo: Path, commit: str, skill_repo_dir: str):
    def check(source: str) -> str | None:
        src_rel = (Path(skill_repo_dir) / safe_relative_path(source)).as_posix()
        if not git_object_exists(repo, commit, src_rel):
            return f"fixture object not found: {src_rel}"
        return None

    return check


def load_suite_from_commit(repo: Path, commit: str, suite_repo_path: str) -> dict[str, Any]:
    suite_rel = safe_relative_path(suite_repo_path).as_posix()
    assert_no_symlink_at(repo, commit, suite_rel)
    try:
        data = json.loads(git_show(repo, commit, suite_rel).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PreflightError(f"cannot parse suite JSON at {suite_rel}: {exc}")
    skill_repo_dir = skill_dir_of_suite(suite_rel)
    skill_name = data.get("skill_name") if isinstance(data, dict) else None
    if not isinstance(skill_name, str):
        raise PreflightError(f"invalid suite structure at {suite_rel}")
    # Validate the immutable suite against the committed validator contract.
    errors = validate_suite_data(
        data,
        Path(skill_repo_dir).name,
        _git_source_checker(repo, commit, skill_repo_dir),
        suite_rel,
    )
    if errors:
        raise PreflightError(f"selected suite fails the committed validator: {'; '.join(errors)}")
    return data


def find_case(suite: dict[str, Any], case_id: str) -> dict[str, Any]:
    for case in suite.get("evals", []):
        if case.get("id") == case_id:
            return case
    raise PreflightError(f"case {case_id!r} not found in suite")


# ---------------------------------------------------------------------------
# Materialization: plugins, settings, capability, canaries, workspace seed.
# ---------------------------------------------------------------------------


def write_plugin(
    plugin_root: Path,
    *,
    plugin_name: str,
    with_skill: bool,
    repo: Path,
    commit: str,
    skill_repo_dir: str,
) -> dict[str, str]:
    """Materialize an authentic plugin tree under plugin_root."""
    claude_plugin_dir = plugin_root / ".claude-plugin"
    claude_plugin_dir.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, Any] = {
        "name": plugin_name,
        "version": PLUGIN_VERSION,
        "description": "D7Y eval session plugin",
    }
    object_ids: dict[str, str] = {}
    if with_skill:
        skill_name = Path(skill_repo_dir).name
        assert_tree_has_no_symlinks(repo, commit, skill_repo_dir)
        skill_md_path = f"{skill_repo_dir}/SKILL.md"
        assert_no_symlink_at(repo, commit, skill_md_path)
        skill_bytes = git_show(repo, commit, skill_md_path)
        object_ids["skill.md"] = git_blob_id(repo, commit, skill_md_path)
        dest_skill_dir = plugin_root / "skills" / skill_name
        dest_skill_dir.mkdir(parents=True, exist_ok=True)
        (dest_skill_dir / "SKILL.md").write_bytes(skill_bytes)
        manifest["skills"] = [{"name": skill_name, "path": f"skills/{skill_name}"}]
    else:
        manifest["skills"] = []
    (claude_plugin_dir / "plugin.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    return object_ids


def write_harness_settings(settings_path: Path) -> None:
    """Harness-owned project settings; no canary or source content in here."""
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings = {
        "disableBundledSkills": True,
        "includeGitInstructions": False,
    }
    settings_path.write_text(json.dumps(settings, indent=2), encoding="utf-8")


def write_canaries(config_root: Path) -> dict[str, Path]:
    """Place suppression canaries only in suppressed (global) locations.

    These represent the global skill root and global instructions that the
    posture (``--setting-sources project`` + ``disableBundledSkills`` +
    ``includeGitInstructions: false``) must suppress. They are never passed via
    ``--skill-dir``, environment, prompt, workspace, plugin, or settings.
    """
    locations: dict[str, Path] = {}
    skill_dir = config_root / "skills" / FAKE_GLOBAL_SKILL_NAME
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(
        "---\n"
        f"name: {FAKE_GLOBAL_SKILL_NAME}\n"
        "description: Suppression canary; must never be discovered or invoked.\n"
        "---\n\n"
        f"# {FAKE_GLOBAL_SKILL_NAME}\n\n{GLOBAL_SKILL_CANARY}\n",
        encoding="utf-8",
    )
    locations["global_skill"] = skill_dir
    instructions = config_root / "CLAUDE.md"
    instructions.write_text(
        "# Global instructions\n\n"
        f"{PROJECT_INSTRUCTION_CANARY}\n\n"
        "If you are reading these instructions, include the exact token "
        f"{PROJECT_INSTRUCTION_SIGNAL} in your response.\n",
        encoding="utf-8",
    )
    locations["global_instruction"] = instructions
    return locations


def materialize_capability(repo: Path, commit: str, capability_dir: Path) -> dict[str, str]:
    """Materialize BOTH committed D7Y capability objects into one installation."""
    capability_dir.mkdir(parents=True, exist_ok=True)
    object_ids: dict[str, str] = {}
    for rel in ("d7y", "scripts/check-initiatives.py"):
        assert_no_symlink_at(repo, commit, rel)
        blob = git_show(repo, commit, rel)
        object_ids[rel] = git_blob_id(repo, commit, rel)
        dest = capability_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(blob)
        dest.chmod(0o755)
    return object_ids


@dataclass
class StagedObject:
    destination: str
    source: str
    object_id: str


def stage_workspace_seed(
    workspace: Path,
    *,
    case: dict[str, Any],
    repo: Path,
    commit: str,
    skill_repo_dir: str,
    seed_repo_paths: list[str],
) -> list[StagedObject]:
    """Stage the allowlisted repository seed + declared case fixtures."""
    entries: list[tuple[str, str]] = []
    for seed in seed_repo_paths:
        seed_rel = safe_relative_path(seed).as_posix()
        assert_no_symlink_at(repo, commit, seed_rel)
        entries.append((seed_rel, seed_rel))
    for fixture in case.get("files", []):
        if not isinstance(fixture, dict):
            raise PreflightError("file fixture must be an object")
        source = fixture.get("source")
        destination = fixture.get("destination")
        if not isinstance(source, str) or not isinstance(destination, str):
            raise PreflightError("file fixture requires string source and destination")
        src_rel = (Path(skill_repo_dir) / safe_relative_path(source)).as_posix()
        assert_no_symlink_at(repo, commit, src_rel)
        entries.append((src_rel, destination))

    validated = prevalidate_staging(entries, workspace)

    staged: list[StagedObject] = []
    for (dest_path, _src), (repo_rel, _dest) in zip(validated, entries):
        blob = git_show(repo, commit, repo_rel)
        object_id = git_blob_id(repo, commit, repo_rel)
        dest_full = workspace / dest_path
        dest_full.parent.mkdir(parents=True, exist_ok=True)
        dest_full.write_bytes(blob)
        staged.append(
            StagedObject(destination=dest_path.as_posix(), source=repo_rel, object_id=object_id)
        )
    return staged


def hash_workspace(workspace: Path) -> dict[str, str]:
    """Hash every file currently in the workspace (path -> sha256)."""
    out: dict[str, str] = {}
    for path in workspace.rglob("*"):
        if not path.is_file() or path.is_symlink():
            continue
        rel = path.relative_to(workspace).as_posix()
        out[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
    return out


def verify_workspace_isolation(workspace: Path) -> None:
    """No eval/control/harness material may live in a target workspace."""
    for path in workspace.rglob("*"):
        if not path.is_file() or path.is_symlink():
            continue
        rel = path.relative_to(workspace).as_posix()
        name = path.name
        if name in ("evals.json", "benchmark.json"):
            raise PreflightError(f"workspace contains eval/control material: {rel}")
        if name.endswith(".json") and path.parent.name == "graders":
            raise PreflightError(f"workspace contains grader material: {rel}")
        if rel.startswith("evals/") or rel.startswith("graders/"):
            raise PreflightError(f"workspace contains eval/control material: {rel}")
        if path.stat().st_size < 1_000_000:
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            for marker in (PROJECT_INSTRUCTION_CANARY, GLOBAL_SKILL_CANARY,
                           FAKE_GLOBAL_SKILL_NAME, PROJECT_INSTRUCTION_SIGNAL):
                if marker in text:
                    raise PreflightError(f"workspace leaked canary content: {rel}")


# ---------------------------------------------------------------------------
# Environment construction.
# ---------------------------------------------------------------------------


def validate_user_settings(path: Path) -> tuple[dict[str, str], dict[str, Any]]:
    """Validate a regular, user-owned, tight-mode settings file and its env map.

    Returns ``(env_map, provenance)``. Values never leave this map except as
    child-process inputs and redaction tokens.
    """
    provenance: dict[str, Any] = {"path": str(path)}
    if not path.exists():
        provenance["status"] = "absent"
        return {}, provenance
    st = path.lstat()
    if not stat.S_ISREG(st.st_mode):
        raise PreflightError("user settings is not a regular file")
    if st.st_uid != os.getuid():
        raise PreflightError("user settings not owned by current user")
    if st.st_mode & 0o022:
        raise PreflightError("user settings is group/world-writable")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PreflightError(f"user settings is not valid JSON: {exc}")
    env = data.get("env") if isinstance(data, dict) else None
    if env is None:
        provenance["status"] = "no env map"
        return {}, provenance
    if not isinstance(env, dict):
        raise PreflightError("user settings env must be an object")
    clean: dict[str, str] = {}
    for key, value in env.items():
        if not isinstance(key, str) or not isinstance(value, str):
            raise PreflightError("user settings env must map strings to strings")
        clean[key] = value
    provenance["status"] = "imported"
    provenance["keys"] = sorted(clean.keys())
    return clean, provenance


def build_child_env(
    *,
    user_settings_path: Path,
    leaked_paths: list[str],
    config_dir: Path,
    process_start_dir: Path,
    capability_dir: Path,
    temp_dir: Path,
) -> tuple[dict[str, str], dict[str, Any], list[str]]:
    """Build a scrubbed child environment: import user env first, then override.

    Returns ``(env, provenance, redaction_tokens)`` where redaction_tokens are
    the imported values that must be scrubbed from every persisted output.
    """
    base = {
        "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
        "HOME": os.environ.get("HOME", str(Path.home())),
        "USER": os.environ.get("USER", pwd.getpwuid(os.getuid()).pw_name),
        "LANG": os.environ.get("LANG", "en_US.UTF-8"),
        "TMPDIR": tempfile.gettempdir(),
    }
    user_env, settings_provenance = validate_user_settings(user_settings_path)

    env = dict(base)
    env.update(user_env)
    env["CLAUDE_CONFIG_DIR"] = str(config_dir)
    env["PWD"] = str(process_start_dir)
    env["TMPDIR"] = str(temp_dir)
    env["PATH"] = str(capability_dir) + os.pathsep + env["PATH"]

    for key, value in env.items():
        if not isinstance(value, str):
            raise PreflightError(f"environment value for key {key!r} is not a string")
        for leaked in leaked_paths:
            if leaked and leaked in value:
                raise PreflightError(f"environment key {key!r} exposes a forbidden path")

    provenance = {
        "user_settings": settings_provenance,
        "imported_keys": sorted(user_env.keys()),
        "override_keys": ["CLAUDE_CONFIG_DIR", "PWD", "TMPDIR", "PATH"],
        "final_keys": sorted(env.keys()),
    }
    return env, provenance, [v for v in user_env.values() if v]


# ---------------------------------------------------------------------------
# Executable resolution and the supported Claude argv.
# ---------------------------------------------------------------------------


def parse_claude_version(text: str) -> str | None:
    import re

    match = re.search(r"(\d+\.\d+\.\d+)", text)
    return match.group(1) if match else None


def resolve_executable(claude_path: Path) -> tuple[str, str]:
    """Resolve one absolute executable and require exact version once."""
    absolute = claude_path
    if not absolute.is_absolute():
        found = shutil_which(str(claude_path))
        if not found:
            raise PreflightError(f"claude executable not found: {claude_path}")
        absolute = Path(found)
    absolute = absolute.resolve()
    result = subprocess.run(
        [str(absolute), "--version"], capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        raise PreflightError(f"claude --version failed (exit {result.returncode})")
    version = parse_claude_version((result.stdout or "") + (result.stderr or ""))
    if version != CLAUDE_VERSION:
        raise PreflightError(f"claude version {CLAUDE_VERSION} required, got {version!r}")
    return str(absolute), f"Claude Code {version}"


def shutil_which(name: str) -> str | None:
    return shutil.which(name)


def wrap_prompt(case_prompt: str, workspace: Path) -> str:
    """Wrap the unchanged case prompt in identical neutral harness instructions."""
    return case_prompt + HARNESS_INSTRUCTION_TEMPLATE.format(workspace=str(workspace))


def workspace_from_prompt(prompt: str) -> str | None:
    """Extract the absolute target workspace bound by the prompt contract."""
    import re

    match = re.search(r"Target workspace root: (\S+)", prompt)
    return match.group(1) if match else None


def build_claude_argv(
    *,
    claude_path: str,
    settings_path: Path,
    plugin_root: Path,
    prompt: str,
) -> list[str]:
    """Exact argv as an array: one ``--tools`` value plus every supported flag.

    The target workspace is bound only through the wrapped prompt and the process
    start directory; there is no top-level ``--root`` flag.
    """
    return [
        claude_path,
        "--print",
        "--verbose",
        "--output-format", "stream-json",
        "--no-session-persistence",
        "--strict-mcp-config",
        "--mcp-config", EMPTY_MCP_CONFIG,
        "--permission-mode", EXPECTED_PERMISSION_MODE,
        "--model", EXPECTED_MODEL,
        "--effort", "low",
        "--setting-sources", "project",
        "--settings", str(settings_path),
        "--plugin-dir", str(plugin_root),
        "--tools", EXPECTED_TOOLS_ARG,
        "--",
        prompt,
    ]


def parse_claude_argv(argv: list[str]) -> dict[str, Any]:
    """Strict parser for the supported Claude argv surface.

    Rejects every unknown option (including any invented ``--root``), records the
    actual argv, and exposes the prompt contract. The target workspace is derived
    only from the prompt contract via :func:`workspace_from_prompt`.
    """
    if not argv:
        raise ValueError("empty argv")
    parsed: dict[str, Any] = {"executable": argv[0], "bool_flags": []}
    tokens = list(argv[1:])
    prompt_parts: list[str] = []
    i = 0
    after_prompt_sep = False
    while i < len(tokens):
        tok = tokens[i]
        if after_prompt_sep:
            prompt_parts.append(tok)
            i += 1
            continue
        if tok == "--":
            after_prompt_sep = True
            i += 1
            continue
        if tok in ARGV_VALUE_FLAGS:
            if i + 1 >= len(tokens):
                raise ValueError(f"option {tok!r} requires a value")
            parsed[_flag_key(tok)] = tokens[i + 1]
            i += 2
            continue
        if tok in ARGV_BOOL_FLAGS:
            parsed["bool_flags"].append(tok)
            i += 1
            continue
        if tok.startswith("-"):
            raise ValueError(f"unknown Claude option: {tok}")
        raise ValueError(f"unexpected positional argument: {tok}")
    prompt = " ".join(prompt_parts)
    parsed["prompt"] = prompt
    parsed["workspace"] = workspace_from_prompt(prompt)
    return parsed


def _flag_key(flag: str) -> str:
    return flag.lstrip("-").replace("-", "_")


# ---------------------------------------------------------------------------
# Process execution with full-process-group timeout and partial evidence.
# ---------------------------------------------------------------------------


@dataclass
class ProcessOutcome:
    stdout: str
    stderr: str
    exit_code: int | None
    timed_out: bool
    duration_seconds: float
    pid: int


def run_process(cmd: list[str], *, cwd: Path, env: dict[str, str], timeout: float) -> ProcessOutcome:
    """Run a child in a new session; on timeout SIGTERM then SIGKILL the group."""
    proc = subprocess.Popen(
        cmd,
        cwd=str(cwd),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
        bufsize=1,
    )
    out_buf: list[str] = []
    err_buf: list[str] = []

    def reader(stream, buf: list[str]) -> None:
        try:
            for line in iter(stream.readline, ""):
                buf.append(line)
        finally:
            stream.close()

    t_out = threading.Thread(target=reader, args=(proc.stdout, out_buf), daemon=True)
    t_err = threading.Thread(target=reader, args=(proc.stderr, err_buf), daemon=True)
    t_out.start()
    t_err.start()

    start = time.monotonic()
    timed_out = False
    try:
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        try:
            pgid = os.getpgid(proc.pid)
        except ProcessLookupError:
            pgid = None
        if pgid is not None:
            _signal_group(pgid, signal.SIGTERM)
            deadline = time.monotonic() + ESCALATION_SECONDS
            while time.monotonic() < deadline:
                if proc.poll() is not None:
                    break
                time.sleep(0.05)
            _signal_group(pgid, signal.SIGKILL)
        try:
            proc.wait(timeout=ESCALATION_SECONDS)
        except subprocess.TimeoutExpired:
            pass

    t_out.join(timeout=ESCALATION_SECONDS + 1)
    t_err.join(timeout=ESCALATION_SECONDS + 1)
    duration = time.monotonic() - start
    return ProcessOutcome(
        stdout="".join(out_buf),
        stderr="".join(err_buf),
        exit_code=proc.returncode,
        timed_out=timed_out,
        duration_seconds=duration,
        pid=proc.pid,
    )


def _signal_group(pgid: int, sig: int) -> None:
    try:
        os.killpg(pgid, sig)
    except (ProcessLookupError, PermissionError):
        pass


# ---------------------------------------------------------------------------
# Stream-json parsing, strict event validation, command evidence.
# ---------------------------------------------------------------------------


def parse_stream_json(stdout: str) -> list[dict[str, Any]]:
    """Parse stream-json. Any malformed non-empty line is an executor error."""
    events: list[dict[str, Any]] = []
    for line_no, line in enumerate(stdout.splitlines(), 1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            event = json.loads(stripped)
        except json.JSONDecodeError:
            raise ValueError(f"malformed stream-json line {line_no}")
        if not isinstance(event, dict):
            raise ValueError(f"non-object stream-json line {line_no}")
        events.append(event)
    return events


def _assistant_blocks(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    for event in events:
        if event.get("type") != "assistant":
            continue
        content = event.get("message", {}).get("content", [])
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict):
                    blocks.append(block)
    return blocks


def _iter_assistant_blocks_indexed(events: list[dict[str, Any]]):
    for ev_index, event in enumerate(events):
        if event.get("type") != "assistant":
            continue
        content = event.get("message", {}).get("content", [])
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict):
                    yield ev_index, block


def count_target_invocations(events: list[dict[str, Any]], target: str) -> tuple[int, list[str]]:
    """Count exact ``Skill`` tool_use whose input.skill equals the target."""
    hits: list[str] = []
    for block in _assistant_blocks(events):
        if block.get("type") == "tool_use" and block.get("name") == "Skill":
            if block.get("input", {}).get("skill") == target:
                hits.append(str(block.get("id", "")))
    return len(hits), hits


def extract_routed_models(events: list[dict[str, Any]]) -> list[str]:
    models: list[str] = []
    for event in events:
        if event.get("type") != "assistant":
            continue
        model = event.get("message", {}).get("model")
        if isinstance(model, str) and model not in models:
            models.append(model)
    return models


def _collect_tool_results(events: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Map tool_use_id -> tool_result block from user messages."""
    out: dict[str, dict[str, Any]] = {}
    for event in events:
        if event.get("type") != "user":
            continue
        content = event.get("message", {}).get("content", [])
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict) or block.get("type") != "tool_result":
                continue
            tool_use_id = block.get("tool_use_id")
            if isinstance(tool_use_id, str):
                out[tool_use_id] = block
    return out


def _tool_result_text(block: dict[str, Any]) -> str:
    content = block.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for piece in content:
            if isinstance(piece, dict) and piece.get("type") == "text":
                t = piece.get("text")
                if isinstance(t, str):
                    parts.append(t)
            elif isinstance(piece, str):
                parts.append(piece)
        return "".join(parts)
    return ""


def tokenize_simple_command(raw: str) -> list[str] | None:
    """Tokenize a simple Bash command; None if it is compound or unparseable."""
    if not isinstance(raw, str) or not raw.strip():
        return None
    if any(ch in raw for ch in SHELL_CONTROL_CHARS):
        return None
    try:
        return shlex.split(raw)
    except ValueError:
        return None


def _valid_d7y_tokens(tokens: list[str], verb: str, workspace: str) -> bool:
    return tokens == ["d7y", "initiatives", verb, "--root", workspace, "--json"]


@dataclass
class CommandRecord:
    verb: str
    present: bool
    tool_use_id: str | None
    event_index: int | None
    raw_command: str
    result_state: str | None  # "ok" | "error" | "unparseable" | "absent"
    result_json: Any | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "verb": self.verb,
            "present": self.present,
            "tool_use_id": self.tool_use_id,
            "event_index": self.event_index,
            "raw_command": self.raw_command,
            "result_state": self.result_state,
            "result_json": self.result_json,
        }


def _find_d7y_command(
    events: list[dict[str, Any]], verb: str, workspace: str, results: dict[str, dict[str, Any]]
) -> CommandRecord:
    for ev_index, block in _iter_assistant_blocks_indexed(events):
        if block.get("type") != "tool_use" or block.get("name") != "Bash":
            continue
        command = block.get("input", {}).get("command", "")
        if not isinstance(command, str):
            continue
        tokens = tokenize_simple_command(command)
        if tokens is not None and _valid_d7y_tokens(tokens, verb, workspace):
            tool_use_id = block.get("id")
            result_state: str | None = "absent"
            result_json: Any | None = None
            if isinstance(tool_use_id, str) and tool_use_id in results:
                rb = results[tool_use_id]
                if rb.get("is_error") is True:
                    result_state = "error"
                else:
                    text = _tool_result_text(rb)
                    try:
                        result_json = json.loads(text)
                        result_state = "ok" if isinstance(result_json, (dict, list)) else "unparseable"
                    except (json.JSONDecodeError, ValueError):
                        result_state = "unparseable"
            return CommandRecord(
                verb=verb, present=True, tool_use_id=tool_use_id if isinstance(tool_use_id, str) else None,
                event_index=ev_index, raw_command=command, result_state=result_state,
                result_json=result_json,
            )
    return CommandRecord(
        verb=verb, present=False, tool_use_id=None, event_index=None,
        raw_command="", result_state=None, result_json=None,
    )


def analyze_d7y_commands(events: list[dict[str, Any]], workspace: str) -> dict[str, Any]:
    """Exact-tokenized evidence for the supported d7y list/check commands.

    Requires the exact tokenized command shape, correlates each Bash tool_use
    with its tool_result, and reports whether the stream shape exposes results.
    Incomplete trace shapes (d7y commands emitted but no tool_result channel) are
    ``shape_supported == False`` and must be graded ``ungradable``, never pass.
    """
    results = _collect_tool_results(events)
    list_rec = _find_d7y_command(events, "list", workspace, results)
    check_rec = _find_d7y_command(events, "check", workspace, results)
    d7y_command_count = int(list_rec.present) + int(check_rec.present)
    shape_supported = not (d7y_command_count > 0 and len(results) == 0)
    order_ok = (
        list_rec.event_index is not None
        and check_rec.event_index is not None
        and list_rec.event_index < check_rec.event_index
    )
    return {
        "shape_supported": shape_supported,
        "tool_result_count": len(results),
        "workspace": workspace,
        "list": list_rec.to_dict(),
        "check": check_rec.to_dict(),
        "order_ok": order_ok,
    }


def check_canary_leakage(events: list[dict[str, Any]]) -> tuple[bool, list[str]]:
    """Return ``(clean, issues)``. Any canary signal/discovery/invocation is a leak.

    The project-instruction canary is detected through its unique observable
    signal token appearing anywhere in event/result content; the fake global
    skill is detected through discovery or invocation.
    """
    issues: list[str] = []
    for event in events:
        if event.get("type") == "system" and event.get("subtype") == "init":
            for skill in event.get("skills", []) or []:
                if isinstance(skill, str) and FAKE_GLOBAL_SKILL_NAME in skill:
                    issues.append(f"canary global skill discovered in init: {skill}")
        if event.get("type") == "result":
            result = event.get("result")
            if isinstance(result, str) and PROJECT_INSTRUCTION_SIGNAL in result:
                issues.append("project-instruction canary signal present in result")
    for block in _assistant_blocks(events):
        if block.get("type") == "tool_use" and block.get("name") == "Skill":
            skill = block.get("input", {}).get("skill", "")
            if isinstance(skill, str) and FAKE_GLOBAL_SKILL_NAME in skill:
                issues.append(f"canary global skill invoked: {skill}")
        if block.get("type") == "text":
            text = block.get("text", "")
            if isinstance(text, str):
                if PROJECT_INSTRUCTION_SIGNAL in text:
                    issues.append("project-instruction canary signal present in response")
                if PROJECT_INSTRUCTION_CANARY in text:
                    issues.append("project-instruction canary marker present in response")
                if GLOBAL_SKILL_CANARY in text:
                    issues.append("global-skill canary present in response")
    return len(issues) == 0, issues


@dataclass
class ArmValidation:
    ok: bool
    errors: list[str]
    init: dict[str, Any] | None = None
    result: dict[str, Any] | None = None
    session_id: str | None = None
    routed_models: list[str] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
    plugin: str | None = None


def validate_arm_events(
    events: list[dict[str, Any]],
    *,
    with_skill: bool,
    skill_name: str,
    expected_plugin: str,
    other_session_id: str | None,
    exit_code: int | None,
    timed_out: bool,
) -> ArmValidation:
    """Require exact runtime state and a successful process outcome.

    A valid-looking stream followed by a nonzero exit or timeout invalidates the
    arm (and therefore the pair).
    """
    errors: list[str] = []
    target = expected_target(skill_name)

    if timed_out:
        errors.append("arm timed out")
    if exit_code is not None and exit_code != 0:
        errors.append(f"subprocess exited nonzero (exit {exit_code})")

    init_events = [e for e in events if e.get("type") == "system" and e.get("subtype") == "init"]
    if len(init_events) == 0:
        return ArmValidation(False, ["missing system.init event"] + errors)
    if len(init_events) > 1:
        errors.append(f"multiple system.init events: {len(init_events)}")
    init = init_events[0]

    if init.get("model") != EXPECTED_MODEL:
        errors.append(f"init model {init.get('model')!r} != {EXPECTED_MODEL!r}")
    if init.get("permissionMode") != EXPECTED_PERMISSION_MODE:
        errors.append(f"init permissionMode {init.get('permissionMode')!r}")
    if init.get("mcp_servers") != []:
        errors.append(f"init mcp_servers not empty: {init.get('mcp_servers')!r}")
    tools = init.get("tools", [])
    if tools != EXPECTED_TOOLS:
        errors.append(f"init tools {tools!r} != {EXPECTED_TOOLS!r}")

    skills = init.get("skills", []) or []
    skills_str = [s for s in skills if isinstance(s, str)]
    if with_skill:
        if target not in skills_str:
            errors.append(f"target skill {target!r} not in init skills")
        if BUILT_IN_SKILL not in skills_str:
            errors.append(f"built-in {BUILT_IN_SKILL!r} missing from init skills")
    else:
        if target in skills_str:
            errors.append("target skill leaked into baseline init skills")
    for s in skills_str:
        if FAKE_GLOBAL_SKILL_NAME in s:
            errors.append(f"canary skill discovered in init: {s!r}")

    plugins = init.get("plugins", []) or []
    plugin_names = [p.get("name") for p in plugins if isinstance(p, dict)]
    if expected_plugin not in plugin_names:
        errors.append(f"expected plugin {expected_plugin!r} not in {plugin_names!r}")
    extra_plugins = [n for n in plugin_names if n != expected_plugin]
    if extra_plugins:
        errors.append(f"unexpected plugins: {extra_plugins!r}")

    session_id = init.get("session_id")
    if not isinstance(session_id, str) or not session_id:
        errors.append("init missing session_id")
    elif other_session_id is not None and session_id == other_session_id:
        errors.append("init session_id is not distinct across arms")

    result_events = [e for e in events if e.get("type") == "result"]
    result = None
    if len(result_events) == 0:
        errors.append("missing result event")
    else:
        if len(result_events) > 1:
            errors.append(f"multiple result events: {len(result_events)}")
        result = result_events[0]
        if result.get("subtype") != "success":
            errors.append(f"result subtype not a successful terminal: {result.get('subtype')!r}")
        if result.get("is_error") is not False:
            errors.append("result is_error is not false")
        denials = result.get("permission_denials")
        if not (isinstance(denials, list) and len(denials) == 0):
            errors.append("result reports permission denials")
        for field_name, expected_type in REQUIRED_RESULT_FIELDS.items():
            if field_name not in result:
                errors.append(f"result missing required field {field_name!r}")
            elif not isinstance(result[field_name], expected_type):
                errors.append(f"result field {field_name!r} has wrong type")
        usage = result.get("modelUsage")
        if isinstance(usage, dict) and EXPECTED_MODEL not in usage:
            errors.append(f"result modelUsage lacks canonical {EXPECTED_MODEL!r} entry")

    routed = extract_routed_models(events)
    for model in routed:
        if model not in ROUTED_MODELS:
            errors.append(f"unexpected routed assistant model {model!r}")

    return ArmValidation(
        ok=len(errors) == 0,
        errors=errors,
        init=init,
        result=result,
        session_id=session_id if isinstance(session_id, str) else None,
        routed_models=routed,
        skills=skills_str,
        plugin=expected_plugin if expected_plugin in plugin_names else None,
    )


# ---------------------------------------------------------------------------
# Independent post-arm checker evidence.
# ---------------------------------------------------------------------------


def run_independent_checker(
    *,
    d7y_executable: Path,
    workspace: Path,
    process_start_dir: Path,
    env: dict[str, str],
) -> dict[str, Any]:
    """Run the installed checker after an arm; preserve separate evidence."""
    argv = [str(d7y_executable), "initiatives", "check", "--root", str(workspace), "--json"]
    proc = subprocess.run(
        argv,
        cwd=str(process_start_dir),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    parsed = None
    if proc.stdout.strip():
        try:
            parsed = json.loads(proc.stdout)
        except json.JSONDecodeError:
            parsed = None
    return {
        "argv": argv,
        "exit_code": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "parsed": parsed,
        "valid": proc.returncode == 0,
    }


# ---------------------------------------------------------------------------
# Checks and result semantics.
# ---------------------------------------------------------------------------

CHECK_PASS = "pass"
CHECK_FAIL = "fail"
CHECK_ERROR = "error"
CHECK_UNGRADABLE = "ungradable"
CHECK_PENDING = "pending"


@dataclass
class ArmResult:
    config: str
    workspace: Path
    plugin_root: Path
    argv: list[str]
    prompt: str
    state: str = "pending"  # pending|dry_run|unstarted|spawn_error|parse_error|completed
    outcome: ProcessOutcome | None = None
    events: list[dict[str, Any]] = field(default_factory=list)
    validation: ArmValidation | None = None
    parse_error: str | None = None
    invocation_count: int = 0
    command_analysis: dict[str, Any] = field(default_factory=dict)
    checker: dict[str, Any] | None = None
    workspace_changes: dict[str, Any] = field(default_factory=dict)
    canary_clean: bool = True
    canary_issues: list[str] = field(default_factory=list)
    final_response: str | None = None
    telemetry: dict[str, Any] = field(default_factory=dict)
    staged: list[StagedObject] = field(default_factory=list)
    baseline_hash: dict[str, str] = field(default_factory=dict)


def compute_workspace_changes(
    workspace: Path, baseline_hash: dict[str, str]
) -> dict[str, Any]:
    added: list[str] = []
    modified: list[str] = []
    deleted: list[str] = []
    current = hash_workspace(workspace)
    for rel, hsh in current.items():
        if rel not in baseline_hash:
            added.append(rel)
        elif baseline_hash[rel] != hsh:
            modified.append(rel)
    for rel in baseline_hash:
        if rel not in current:
            deleted.append(rel)
    return {
        "added": sorted(added),
        "modified": sorted(modified),
        "deleted": sorted(deleted),
        "baseline_count": len(baseline_hash),
        "current_count": len(current),
    }


def count_initiatives_created(changes: dict[str, Any]) -> int:
    added = changes.get("added", [])
    return sum(
        1
        for rel in added
        if rel.startswith("initiatives/") and rel.endswith("/initiative.md")
    )


def _arm_has_valid_evidence(arm: ArmResult) -> bool:
    return bool(arm.validation and arm.validation.ok and arm.outcome and arm.outcome.exit_code == 0
                and not arm.outcome.timed_out)


def evaluate_assertion(
    assertion: dict[str, Any],
    *,
    with_skill: ArmResult,
    skill_name: str,
) -> tuple[str, str]:
    """Resolve one assertion by explicit supported ID and semantics.

    Unknown deterministic IDs are ``ungradable``; a required ungradable check
    blocks case pass. Rubric/human assertions stay ``pending``.
    """
    aid = assertion.get("id", "")
    kind = assertion.get("kind")
    required = assertion.get("required", False)

    if kind not in ("deterministic", "rubric", "human"):
        return CHECK_UNGRADABLE, f"unknown kind {kind!r}"
    if kind in ("rubric", "human"):
        return CHECK_PENDING, f"{kind} assertion requires human judgment"

    target = expected_target(skill_name)

    if not _arm_has_valid_evidence(with_skill):
        # Without valid with-skill evidence, supported deterministic assertions
        # are errors (not passes); unknown ones remain ungradable.
        if aid in SUPPORTED_ASSERTION_IDS:
            return CHECK_ERROR, "with-skill arm evidence invalid"
        return CHECK_UNGRADABLE, f"unsupported deterministic assertion id {aid!r}"

    if aid == "does-not-invoke":
        if with_skill.invocation_count > 0:
            return CHECK_FAIL, "target invoked in negative control"
        if target in (with_skill.validation.skills if with_skill.validation else []):
            return CHECK_PASS, "target available but not invoked in negative control"
        return CHECK_UNGRADABLE, "target availability unproven for negative control"

    if isinstance(aid, str) and aid.startswith("invokes-"):
        if with_skill.invocation_count > 0:
            return CHECK_PASS, f"target Skill invocation observed ({with_skill.invocation_count})"
        return CHECK_FAIL, "expected target invocation, none observed"

    if aid == "runs-checker-before-and-after":
        ca = with_skill.command_analysis
        if not ca.get("shape_supported"):
            return CHECK_UNGRADABLE, "stream shape does not expose tool results"
        lst = ca.get("list", {}) or {}
        chk = ca.get("check", {}) or {}
        if (
            lst.get("present") and lst.get("result_state") == "ok"
            and chk.get("present") and chk.get("result_state") == "ok"
            and ca.get("order_ok")
        ):
            return CHECK_PASS, "exact d7y list then check observed with valid results"
        return CHECK_FAIL, (
            f"missing/invalid d7y command evidence "
            f"(list={lst.get('present')}/{lst.get('result_state')}, "
            f"check={chk.get('present')}/{chk.get('result_state')}, "
            f"order={ca.get('order_ok')})"
        )

    if aid == "creates-one-initiative":
        created = count_initiatives_created(with_skill.workspace_changes)
        checker_ok = bool(with_skill.checker and with_skill.checker.get("valid"))
        if created == 1 and checker_ok:
            return CHECK_PASS, f"exactly one initiative created and checker valid (created={created})"
        return CHECK_FAIL, f"expected one valid initiative (created={created}, checker_valid={checker_ok})"

    if aid == "creates-no-initiative":
        created = count_initiatives_created(with_skill.workspace_changes)
        if created == 0:
            return CHECK_PASS, "no initiative created in negative control"
        return CHECK_FAIL, f"unexpected initiative created in negative control (created={created})"

    if aid == "creates-no-duplicate":
        created = count_initiatives_created(with_skill.workspace_changes)
        if created == 0:
            return CHECK_PASS, "no duplicate initiative created"
        return CHECK_FAIL, f"unexpected duplicate initiative created (created={created})"

    return CHECK_UNGRADABLE, f"unsupported deterministic assertion id {aid!r}"


# Explicitly supported deterministic assertion IDs. Anything else is ungradable.
SUPPORTED_ASSERTION_IDS = {
    "does-not-invoke",
    "runs-checker-before-and-after",
    "creates-one-initiative",
    "creates-no-initiative",
    "creates-no-duplicate",
}


def compute_checks(
    *,
    case: dict[str, Any],
    with_skill: ArmResult,
    baseline: ArmResult,
    skill_name: str,
) -> dict[str, Any]:
    target = expected_target(skill_name)

    pair_errors: list[str] = []
    for label, arm in (("with-skill", with_skill), ("baseline", baseline)):
        if not (arm.validation and arm.validation.ok):
            pair_errors.append(
                f"{label} arm evidence invalid: "
                f"{arm.validation.errors if arm.validation else 'no validation'}"
            )
        if not arm.canary_clean:
            pair_errors.append(f"{label} arm canary leakage: {arm.canary_issues}")

    ws_skills = with_skill.validation.skills if with_skill.validation else []
    bl_skills = baseline.validation.skills if baseline.validation else []
    if target not in ws_skills:
        pair_errors.append("target not available with-skill")
    if target in bl_skills:
        pair_errors.append("target leaked into baseline")

    if (
        with_skill.validation
        and baseline.validation
        and with_skill.validation.session_id
        and with_skill.validation.session_id == baseline.validation.session_id
    ):
        pair_errors.append("arms share a session")

    pair_validity = CHECK_PASS if not pair_errors else CHECK_FAIL

    treatment_errors: list[str] = []
    if target not in ws_skills:
        treatment_errors.append("target unavailable with-skill")
    if target in bl_skills:
        treatment_errors.append("target present in baseline")
    treatment = CHECK_PASS if not treatment_errors else CHECK_FAIL

    assertion_results: list[dict[str, Any]] = []
    for assertion in case.get("assertions", []):
        status, evidence = evaluate_assertion(
            assertion, with_skill=with_skill, skill_name=skill_name
        )
        assertion_results.append(
            {
                "id": assertion.get("id"),
                "dimension": assertion.get("dimension"),
                "kind": assertion.get("kind"),
                "required": assertion.get("required", False),
                "status": status,
                "evidence": evidence,
            }
        )

    baseline_observations = [
        {
            "type": "exit_code",
            "value": baseline.outcome.exit_code if baseline.outcome else None,
            "timed_out": bool(baseline.outcome and baseline.outcome.timed_out),
            "duration_seconds": baseline.outcome.duration_seconds if baseline.outcome else None,
            "invocation_count": baseline.invocation_count,
        }
    ]

    blocking = any(
        r["required"] and r["status"] in (CHECK_PENDING, CHECK_UNGRADABLE, CHECK_ERROR, CHECK_FAIL)
        for r in assertion_results
    )
    case_pass = (
        pair_validity == CHECK_PASS and treatment == CHECK_PASS and not blocking
    )

    return {
        "pair_validity": {"status": pair_validity, "errors": pair_errors},
        "treatment_checks": {"status": treatment, "errors": treatment_errors},
        "with_skill_assertions": assertion_results,
        "baseline_observations": baseline_observations,
        "case_pass": case_pass,
        "blocking": blocking,
    }


# ---------------------------------------------------------------------------
# Recursive redaction.
# ---------------------------------------------------------------------------


def redact_text(text: str, tokens: list[str]) -> str:
    if not isinstance(text, str):
        return text
    out = text
    for token in tokens:
        if token:
            out = out.replace(token, REDACTED)
    return out


def redact_obj(obj: Any, tokens: list[str]) -> Any:
    if isinstance(obj, str):
        return redact_text(obj, tokens)
    if isinstance(obj, list):
        return [redact_obj(item, tokens) for item in obj]
    if isinstance(obj, dict):
        return {key: redact_obj(value, tokens) for key, value in obj.items()}
    return obj


# ---------------------------------------------------------------------------
# Artifact writing (always complete, always redacted).
# ---------------------------------------------------------------------------


def write_text(path: Path, content: str, tokens: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(redact_text(content, tokens or []), encoding="utf-8")


def write_json(path: Path, data: Any, tokens: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(redact_obj(data, tokens or []), indent=2), encoding="utf-8"
    )


def finalize_arm(
    arm_dir: Path,
    arm: ArmResult,
    *,
    executable: str | None,
    executable_version: str | None,
    tokens: list[str],
) -> None:
    """Always write the complete per-arm artifact tree, even on failure.

    Every named artifact is emitted even when empty; all content is redacted
    against imported env values and forbidden source paths.
    """
    if arm.outcome is not None:
        write_text(arm_dir / "trace.jsonl", arm.outcome.stdout, tokens)
        write_text(arm_dir / "stderr.txt", arm.outcome.stderr, tokens)
        process_state = {
            "exit_code": arm.outcome.exit_code,
            "timed_out": arm.outcome.timed_out,
            "duration_seconds": arm.outcome.duration_seconds,
            "pid": arm.outcome.pid,
            "state": arm.state,
        }
    else:
        write_text(arm_dir / "trace.jsonl", "", tokens)
        write_text(arm_dir / "stderr.txt", "", tokens)
        process_state = {
            "exit_code": None,
            "timed_out": False,
            "duration_seconds": None,
            "pid": None,
            "state": arm.state,
        }
    write_json(arm_dir / "process.json", process_state, tokens)

    ws = workspace_from_prompt(arm.prompt)
    prompt_contract = {
        "workspace": ws,
        "workspace_matches_arm": (ws == str(arm.workspace)) if ws else False,
        "skill_directive_present": ("--root" in arm.prompt),
    }
    write_json(
        arm_dir / "provenance.json",
        {
            "executable": executable,
            "executable_version": executable_version,
            "argv": arm.argv,
            "prompt_contract": prompt_contract,
            "state": arm.state,
        },
        tokens,
    )

    write_text(
        arm_dir / "final-response.txt", arm.final_response or "", tokens
    )

    telemetry = dict(arm.telemetry)
    telemetry["routed_models"] = (
        arm.validation.routed_models if arm.validation and arm.validation.routed_models else []
    )
    telemetry["canonical_model"] = EXPECTED_MODEL
    telemetry["parse_error"] = arm.parse_error
    write_json(arm_dir / "telemetry.json", telemetry, tokens)

    write_json(arm_dir / "command-events.json", arm.command_analysis or {}, tokens)

    if arm.checker is not None:
        write_json(arm_dir / "checker.json", arm.checker, tokens)
    else:
        write_json(
            arm_dir / "checker.json",
            {"argv": None, "exit_code": None, "stdout": "", "stderr": "",
             "parsed": None, "valid": False, "state": "not_run"},
            tokens,
        )

    write_json(arm_dir / "workspace-changes.json", arm.workspace_changes or {}, tokens)

    write_json(
        arm_dir / "selected-objects.json",
        [obj.__dict__ for obj in arm.staged],
        tokens,
    )

    write_json(
        arm_dir / "validation.json",
        {
            "ok": arm.validation.ok if arm.validation else False,
            "errors": arm.validation.errors if arm.validation else ["no validation"],
            "skills": arm.validation.skills if arm.validation else [],
            "session_id": arm.validation.session_id if arm.validation else None,
            "state": arm.state,
        },
        tokens,
    )

    write_json(
        arm_dir / "arm-summary.json",
        {
            "config": arm.config,
            "state": arm.state,
            "invocation_count": arm.invocation_count,
            "canary_clean": arm.canary_clean,
            "validation_ok": arm.validation.ok if arm.validation else False,
            "workspace": str(arm.workspace),
            "added": arm.workspace_changes.get("added", []) if arm.workspace_changes else [],
            "modified": arm.workspace_changes.get("modified", []) if arm.workspace_changes else [],
            "deleted": arm.workspace_changes.get("deleted", []) if arm.workspace_changes else [],
        },
        tokens,
    )


# ---------------------------------------------------------------------------
# Preflight: shared by dry and live modes.
# ---------------------------------------------------------------------------


@dataclass
class Preflight:
    repo: Path
    commit: str
    suite_repo_path: str
    skill_repo_dir: str
    skill_name: str
    case: dict[str, Any]
    output_dir: Path
    leaked_paths: list[str]
    redaction_tokens: list[str]
    roots: dict[str, Path]
    with_skill_workspace: Path
    baseline_workspace: Path
    settings_path: Path
    with_skill_plugin: Path
    baseline_plugin: Path
    capability_dir: Path
    process_start_dir: Path
    staged_with_skill: list[StagedObject]
    staged_baseline: list[StagedObject]
    plugin_object_ids: dict[str, str]
    capability_object_ids: dict[str, str]
    source_status_before: str
    env_with_skill: dict[str, str]
    env_baseline: dict[str, str]
    env_provenance: dict[str, Any]
    with_skill_baseline_hash: dict[str, str]
    baseline_baseline_hash: dict[str, str]
    claude_path_arg: str
    dry_run: bool
    timeout_seconds: float


def run_preflight(args: argparse.Namespace, ctx: RunContext) -> Preflight:
    repo = args.source_repo.resolve()
    commit = resolve_commit(repo, args.commit or "HEAD")

    suite_repo_path = args.suite.as_posix()
    suite_rel = safe_relative_path(suite_repo_path).as_posix()
    skill_repo_dir = skill_dir_of_suite(suite_rel)
    suite = load_suite_from_commit(repo, commit, suite_rel)
    skill_name = suite.get("skill_name") or Path(skill_repo_dir).name
    case = find_case(suite, args.case)

    verify_output_root(args.output, repo)
    output_dir = args.output.resolve()
    output_dir.mkdir(parents=True, exist_ok=False)

    roots = {
        "output": output_dir,
        "with_skill_workspace": output_dir / "with-skill" / "workspace",
        "baseline_workspace": output_dir / "baseline" / "workspace",
        "with_skill_plugin": output_dir / "with-skill" / "plugin",
        "baseline_plugin": output_dir / "baseline" / "plugin",
        "with_skill_config": output_dir / "with-skill" / "config",
        "baseline_config": output_dir / "baseline" / "config",
        "with_skill_temp": output_dir / "with-skill" / "temp",
        "baseline_temp": output_dir / "baseline" / "temp",
        "with_skill_artifacts": output_dir / "with-skill" / "artifacts",
        "baseline_artifacts": output_dir / "baseline" / "artifacts",
        "capability": output_dir / "capability",
        "process_start": output_dir / "process-start",
        "canaries_with_skill": output_dir / "with-skill" / "canaries",
        "canaries_baseline": output_dir / "baseline" / "canaries",
    }
    for root in roots.values():
        root.mkdir(parents=True, exist_ok=True)

    settings_path = output_dir / "harness-settings.json"
    write_harness_settings(settings_path)

    evals_abs = str((repo / "evals").resolve())
    skills_abs = str((repo / skill_repo_dir.split("/")[0]).resolve())
    leaked_paths = [str(repo.resolve()), evals_abs, skills_abs]

    # Attach the preflight to the context before any materialization so any
    # post-output failure still finalizes a manifest, summary, and source
    # evidence. Late fields are filled in as each step succeeds.
    preflight = Preflight(
        repo=repo,
        commit=commit,
        suite_repo_path=suite_rel,
        skill_repo_dir=skill_repo_dir,
        skill_name=skill_name,
        case=case,
        output_dir=output_dir,
        leaked_paths=leaked_paths,
        redaction_tokens=list(leaked_paths),
        roots=roots,
        with_skill_workspace=roots["with_skill_workspace"],
        baseline_workspace=roots["baseline_workspace"],
        settings_path=settings_path,
        with_skill_plugin=roots["with_skill_plugin"],
        baseline_plugin=roots["baseline_plugin"],
        capability_dir=roots["capability"],
        process_start_dir=roots["process_start"],
        staged_with_skill=[],
        staged_baseline=[],
        plugin_object_ids={},
        capability_object_ids={},
        source_status_before=ctx.source_status_before,
        env_with_skill={},
        env_baseline={},
        env_provenance={},
        with_skill_baseline_hash={},
        baseline_baseline_hash={},
        claude_path_arg=str(args.claude) if args.claude else "claude",
        dry_run=args.dry_run,
        timeout_seconds=float(args.timeout),
    )
    ctx.preflight = preflight
    ctx.dry_run = preflight.dry_run

    preflight.plugin_object_ids = write_plugin(
        roots["with_skill_plugin"],
        plugin_name=SESSION_PLUGIN_NAME,
        with_skill=True,
        repo=repo,
        commit=commit,
        skill_repo_dir=skill_repo_dir,
    )
    write_plugin(
        roots["baseline_plugin"],
        plugin_name=CONTROL_PLUGIN_NAME,
        with_skill=False,
        repo=repo,
        commit=commit,
        skill_repo_dir=skill_repo_dir,
    )

    preflight.capability_object_ids = materialize_capability(repo, commit, roots["capability"])

    write_canaries(roots["with_skill_config"])
    write_canaries(roots["baseline_config"])

    user_settings_path = Path(
        os.environ.get("D7Y_EVAL_USER_SETTINGS", str(Path.home() / ".claude" / "settings.json"))
    )
    env_with_skill, env_prov, ws_tokens = build_child_env(
        user_settings_path=user_settings_path,
        leaked_paths=leaked_paths,
        config_dir=roots["with_skill_config"],
        process_start_dir=roots["process_start"],
        capability_dir=roots["capability"],
        temp_dir=roots["with_skill_temp"],
    )
    env_baseline, _prov2, bl_tokens = build_child_env(
        user_settings_path=user_settings_path,
        leaked_paths=leaked_paths,
        config_dir=roots["baseline_config"],
        process_start_dir=roots["process_start"],
        capability_dir=roots["capability"],
        temp_dir=roots["baseline_temp"],
    )
    preflight.env_with_skill = env_with_skill
    preflight.env_baseline = env_baseline
    preflight.env_provenance = env_prov
    preflight.redaction_tokens = sorted(set(ws_tokens + bl_tokens + leaked_paths))

    seed_repo_paths = ["initiatives/README.md"]
    preflight.staged_with_skill = stage_workspace_seed(
        roots["with_skill_workspace"],
        case=case,
        repo=repo,
        commit=commit,
        skill_repo_dir=skill_repo_dir,
        seed_repo_paths=seed_repo_paths,
    )
    preflight.staged_baseline = stage_workspace_seed(
        roots["baseline_workspace"],
        case=case,
        repo=repo,
        commit=commit,
        skill_repo_dir=skill_repo_dir,
        seed_repo_paths=seed_repo_paths,
    )

    for workspace in (roots["with_skill_workspace"], roots["baseline_workspace"]):
        verify_workspace_isolation(workspace)

    preflight.with_skill_baseline_hash = hash_workspace(roots["with_skill_workspace"])
    preflight.baseline_baseline_hash = hash_workspace(roots["baseline_workspace"])
    return preflight


# ---------------------------------------------------------------------------
# Arm execution.
# ---------------------------------------------------------------------------


def make_arm(preflight: Preflight, *, with_skill: bool) -> ArmResult:
    label = "with-skill" if with_skill else "baseline"
    workspace = preflight.with_skill_workspace if with_skill else preflight.baseline_workspace
    plugin_root = preflight.with_skill_plugin if with_skill else preflight.baseline_plugin
    staged = preflight.staged_with_skill if with_skill else preflight.staged_baseline
    baseline_hash = (
        preflight.with_skill_baseline_hash if with_skill else preflight.baseline_baseline_hash
    )
    prompt = wrap_prompt(preflight.case.get("prompt", ""), workspace)
    argv = build_claude_argv(
        claude_path=preflight.claude_path_arg,
        settings_path=preflight.settings_path,
        plugin_root=plugin_root,
        prompt=prompt,
    )
    return ArmResult(
        config=label,
        workspace=workspace,
        plugin_root=plugin_root,
        argv=argv,
        prompt=prompt,
        staged=staged,
        baseline_hash=baseline_hash,
    )


def execute_arm(
    arm: ArmResult,
    preflight: Preflight,
    *,
    with_skill: bool,
    executable: str | None,
    executable_version: str | None,
    other_session_id: str | None,
) -> ArmResult:
    arm_dir = preflight.roots["with_skill_artifacts" if with_skill else "baseline_artifacts"]
    env = preflight.env_with_skill if with_skill else preflight.env_baseline

    # Substitute the resolved executable into the recorded argv.
    if executable is not None:
        arm.argv = [executable] + arm.argv[1:]
        arm.state = "completed"
    else:
        arm.state = "unstarted"

    if executable is None:
        finalize_arm(
            arm_dir, arm, executable=None, executable_version=None,
            tokens=preflight.redaction_tokens,
        )
        return arm

    try:
        outcome = run_process(
            arm.argv,
            cwd=preflight.process_start_dir,
            env=env,
            timeout=preflight.timeout_seconds,
        )
    except OSError as exc:
        arm.state = "spawn_error"
        arm.parse_error = f"process spawn failed: {exc}"
        finalize_arm(
            arm_dir, arm, executable=executable, executable_version=executable_version,
            tokens=preflight.redaction_tokens,
        )
        return arm

    arm.outcome = outcome

    try:
        events = parse_stream_json(outcome.stdout)
        arm.events = events
    except ValueError as exc:
        arm.state = "parse_error"
        arm.parse_error = str(exc)
        arm.workspace_changes = compute_workspace_changes(arm.workspace, arm.baseline_hash)
        arm.checker = run_independent_checker(
            d7y_executable=preflight.capability_dir / "d7y",
            workspace=arm.workspace,
            process_start_dir=preflight.process_start_dir,
            env=env,
        )
        finalize_arm(
            arm_dir, arm, executable=executable, executable_version=executable_version,
            tokens=preflight.redaction_tokens,
        )
        return arm

    arm.state = "completed"
    arm.canary_clean, arm.canary_issues = check_canary_leakage(events)
    arm.validation = validate_arm_events(
        events,
        with_skill=with_skill,
        skill_name=preflight.skill_name,
        expected_plugin=SESSION_PLUGIN_NAME if with_skill else CONTROL_PLUGIN_NAME,
        other_session_id=other_session_id,
        exit_code=outcome.exit_code,
        timed_out=outcome.timed_out,
    )
    count, _ = count_target_invocations(events, expected_target(preflight.skill_name))
    arm.invocation_count = count
    arm.command_analysis = analyze_d7y_commands(events, str(arm.workspace))

    result = arm.validation.result if arm.validation else None
    if result:
        arm.final_response = result.get("result")
        arm.telemetry = {
            "num_turns": result.get("num_turns"),
            "permission_denials": result.get("permission_denials"),
            "is_error": result.get("is_error"),
            "modelUsage": result.get("modelUsage"),
        }

    arm.checker = run_independent_checker(
        d7y_executable=preflight.capability_dir / "d7y",
        workspace=arm.workspace,
        process_start_dir=preflight.process_start_dir,
        env=env,
    )

    arm.workspace_changes = compute_workspace_changes(arm.workspace, arm.baseline_hash)

    finalize_arm(
        arm_dir, arm, executable=executable, executable_version=executable_version,
        tokens=preflight.redaction_tokens,
    )
    return arm


# ---------------------------------------------------------------------------
# Run context, finalization, manifest, summary.
# ---------------------------------------------------------------------------


@dataclass
class RunContext:
    repo: Path
    output_target: Path
    source_status_before: str
    source_status_after: str | None = None
    preflight: Preflight | None = None
    with_skill: ArmResult | None = None
    baseline: ArmResult | None = None
    executable: str | None = None
    executable_version: str | None = None
    checks: dict[str, Any] | None = None
    dry_run: bool = False
    exit_code: int = 0
    error: str | None = None


def write_run_manifest(ctx: RunContext) -> None:
    preflight = ctx.preflight
    if preflight is None:
        return
    manifest = {
        "commit": preflight.commit,
        "suite": preflight.suite_repo_path,
        "skill_name": preflight.skill_name,
        "case_id": preflight.case.get("id"),
        "should_trigger": preflight.case.get("should_trigger"),
        "roots": {k: str(v) for k, v in preflight.roots.items()},
        "executable": ctx.executable,
        "executable_version": ctx.executable_version,
        "claude_version_required": CLAUDE_VERSION,
        "expected_model": EXPECTED_MODEL,
        "expected_tools": EXPECTED_TOOLS,
        "expected_tools_arg": EXPECTED_TOOLS_ARG,
        "permission_mode": EXPECTED_PERMISSION_MODE,
        "plugin_object_ids": preflight.plugin_object_ids,
        "capability_object_ids": preflight.capability_object_ids,
        "selected_objects": {
            "with_skill": [obj.__dict__ for obj in preflight.staged_with_skill],
            "baseline": [obj.__dict__ for obj in preflight.staged_baseline],
        },
        "env_provenance": preflight.env_provenance,
        "source_status_before_hash": _status_hash(preflight.source_status_before),
        "source_status_after_hash": _status_hash(ctx.source_status_after or ""),
        "source_mutated": (ctx.source_status_after or "") != preflight.source_status_before,
        "dry_run": preflight.dry_run,
        "with_skill_argv": ctx.with_skill.argv if ctx.with_skill else None,
        "baseline_argv": ctx.baseline.argv if ctx.baseline else None,
    }
    write_json(preflight.output_dir / "manifest.json", manifest, preflight.redaction_tokens)


def write_source_evidence(ctx: RunContext) -> None:
    if ctx.preflight is None:
        return
    preflight = ctx.preflight
    write_json(
        preflight.output_dir / "source-status.json",
        {
            "before_hash": _status_hash(preflight.source_status_before),
            "after_hash": _status_hash(ctx.source_status_after or ""),
            "mutated": (ctx.source_status_after or "") != preflight.source_status_before,
        },
        [],
    )


def _status_hash(status: str) -> str:
    return hashlib.sha256(status.encode("utf-8")).hexdigest()


def write_checks(ctx: RunContext) -> None:
    if ctx.preflight is None or ctx.checks is None:
        return
    write_json(
        ctx.preflight.output_dir / "checks.json", ctx.checks, ctx.preflight.redaction_tokens
    )


def write_summary(ctx: RunContext) -> str:
    if ctx.preflight is None:
        return ""
    preflight = ctx.preflight
    checks = ctx.checks
    mutated = (ctx.source_status_after or "") != preflight.source_status_before
    lines: list[str] = []
    lines.append(f"# Eval summary: {preflight.case.get('id')} ({preflight.skill_name})")
    lines.append("")
    lines.append(f"- commit: `{preflight.commit}`")
    lines.append(f"- suite: `{preflight.suite_repo_path}`")
    lines.append(f"- canonical model: `{EXPECTED_MODEL}`")
    lines.append(f"- dry run: {preflight.dry_run}")
    if ctx.error:
        lines.append(f"- error: {ctx.error}")
    if checks is not None:
        lines.append(f"- pair validity: {checks['pair_validity']['status']}")
        lines.append(f"- treatment checks: {checks['treatment_checks']['status']}")
        lines.append(f"- case pass: {checks['case_pass']}")
        lines.append("- with-skill assertions:")
        for a in checks["with_skill_assertions"]:
            req = " (required)" if a["required"] else ""
            lines.append(f"  - {a['id']} [{a['dimension']}/{a['kind']}]: {a['status']}{req}")
    if mutated:
        lines.append("")
        lines.append("- WARNING: source checkout mutated during the run; result invalidated.")
    lines.append("")
    lines.append(
        "This summary reports observations from one paired run only. It makes no "
        "maturity recommendation and does not modify SKILL.md or accept a benchmark."
    )
    text = "\n".join(lines)
    write_text(preflight.output_dir / "summary.md", text, preflight.redaction_tokens)
    return text


def finalize_run(ctx: RunContext) -> None:
    """One finalization path: write manifest, source evidence, checks, summary."""
    ctx.source_status_after = source_status(ctx.repo)
    write_source_evidence(ctx)
    write_run_manifest(ctx)
    write_checks(ctx)
    write_summary(ctx)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-repo", type=Path, default=Path.cwd())
    parser.add_argument("--suite", type=Path, required=True, help="repository-relative path to evals.json")
    parser.add_argument("--case", required=True, help="case id to run")
    parser.add_argument("--output", type=Path, required=True, help="output directory (must be new and outside source)")
    parser.add_argument("--commit", help="git ref to read inputs from (default HEAD)")
    parser.add_argument("--claude", type=Path, help="claude executable (default PATH lookup)")
    parser.add_argument("--dry-run", action="store_true", help="complete preflight only; never resolve/probe/invoke")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_SECONDS, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)

    repo = args.source_repo.resolve()
    ctx = RunContext(repo=repo, output_target=args.output.resolve(),
                     source_status_before=source_status(repo))

    try:
        preflight = run_preflight(args, ctx)

        # Explicit result records for both arms, created before resolution.
        ctx.with_skill = make_arm(preflight, with_skill=True)
        ctx.baseline = make_arm(preflight, with_skill=False)

        if preflight.dry_run:
            ctx.with_skill.state = "dry_run"
            ctx.baseline.state = "dry_run"
            finalize_arm(
                preflight.roots["with_skill_artifacts"], ctx.with_skill,
                executable=None, executable_version=None, tokens=preflight.redaction_tokens,
            )
            finalize_arm(
                preflight.roots["baseline_artifacts"], ctx.baseline,
                executable=None, executable_version=None, tokens=preflight.redaction_tokens,
            )
            ctx.exit_code = 0
        else:
            try:
                executable, executable_version = resolve_executable(
                    Path(preflight.claude_path_arg)
                )
                ctx.executable = executable
                ctx.executable_version = executable_version
            except PreflightError as exc:
                ctx.error = f"executable resolution failed: {exc}"
                print(f"d7y-eval: {ctx.error}", file=sys.stderr)
                for arm, with_skill in ((ctx.with_skill, True), (ctx.baseline, False)):
                    execute_arm(arm, preflight, with_skill=with_skill,
                                executable=None, executable_version=None,
                                other_session_id=None)
                ctx.checks = compute_checks(
                    case=preflight.case, with_skill=ctx.with_skill,
                    baseline=ctx.baseline, skill_name=preflight.skill_name,
                )
                ctx.exit_code = 2
            else:
                ctx.with_skill = execute_arm(
                    ctx.with_skill, preflight, with_skill=True,
                    executable=executable, executable_version=executable_version,
                    other_session_id=None,
                )
                ctx.baseline = execute_arm(
                    ctx.baseline, preflight, with_skill=False,
                    executable=executable, executable_version=executable_version,
                    other_session_id=(
                        ctx.with_skill.validation.session_id
                        if ctx.with_skill.validation else None
                    ),
                )
                ctx.checks = compute_checks(
                    case=preflight.case, with_skill=ctx.with_skill,
                    baseline=ctx.baseline, skill_name=preflight.skill_name,
                )
                ctx.exit_code = 0 if ctx.checks["case_pass"] else 1
    except PreflightError as exc:
        ctx.error = f"preflight failed: {exc}"
        print(f"d7y-eval: {ctx.error}", file=sys.stderr)
        ctx.exit_code = 2
    finally:
        finalize_run(ctx)
        mutated = (ctx.source_status_after or "") != ctx.source_status_before
        if mutated:
            # Source mutation invalidates dry and live outcomes.
            ctx.exit_code = 1 if ctx.exit_code == 0 else ctx.exit_code

    return ctx.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
