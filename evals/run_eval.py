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
"""

from __future__ import annotations

import argparse
import json
import os
import pwd
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

# ---------------------------------------------------------------------------
# Runtime contract constants (Claude Code 2.1.218 spike).
# ---------------------------------------------------------------------------

CLAUDE_VERSION = "2.1.218"
EXPECTED_MODEL = "claude-sonnet-5"
# Permitted routed assistant model under this user's z.ai routing. Canonical /
# requested model stays claude-sonnet-5; routed assistant events may identify
# this model and must not be rejected as a mismatch.
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

# Required result-event fields.
REQUIRED_RESULT_FIELDS = ("result", "is_error", "num_turns", "permission_denials", "modelUsage")

# Canaries test suppression. They are placed only in locations the selected
# posture should suppress and are never passed as positive agent input.
PROJECT_INSTRUCTION_CANARY = "D7Y-EVAL-PROJECT-INSTRUCTION-SUPPRESSION-CANARY"
FAKE_GLOBAL_SKILL_NAME = "d7y-eval-fake-global-skill"
GLOBAL_SKILL_CANARY = "D7Y-EVAL-GLOBAL-SKILL-SUPPRESSION-CANARY"

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


# ---------------------------------------------------------------------------
# Errors.
# ---------------------------------------------------------------------------


class PreflightError(Exception):
    """A blocking preflight failure."""


# ---------------------------------------------------------------------------
# Git helpers: every run input comes from immutable objects.
# ---------------------------------------------------------------------------


def _git(repo: Path, args: list[str], *, binary: bool = False, check: bool = True) -> subprocess.CompletedProcess:
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
        raise PreflightError(f"resolved ref {ref!r} is not a commit: {sha}")
    return sha


def git_blob_id(repo: Path, commit: str, path: str) -> str:
    result = _git(repo, ["rev-parse", "--verify", "--quiet", f"{commit}:{path}"])
    if result.returncode != 0:
        raise PreflightError(f"object not found at {commit}:{path}")
    return result.stdout.strip()


def git_show(repo: Path, commit: str, path: str) -> bytes:
    result = _git(repo, ["cat-file", "-p", f"{commit}:{path}"], binary=True)
    if result.returncode != 0:
        raise PreflightError(f"cannot read object {commit}:{path}")
    return result.stdout


def git_entry_mode(repo: Path, commit: str, path: str) -> str:
    """Return the git tree-entry mode for a path (e.g. '100644', '120000')."""
    result = _git(repo, ["ls-tree", "-d", commit, "--", path])
    if result.returncode != 0 or not result.stdout.strip():
        # Path may be a file inside a tree; query its containing entry directly.
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
    # Non-zero means the prefix is absent or is a blob; nothing to scan.
    for line in result.stdout.splitlines():
        parts = line.split(None, 3)
        if len(parts) >= 4 and parts[0] == "120000":
            raise PreflightError(f"committed symlink rejected in {tree_prefix}: {parts[3]}")


def source_status(repo: Path) -> str:
    return _git(repo, ["status", "--porcelain"]).stdout


def verify_output_root(output_dir: Path, source_repo: Path) -> None:
    output_abs = output_dir.resolve()
    source_abs = source_repo.resolve()
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
    if output_dir.exists() and any(output_dir.rglob("*")):
        raise PreflightError("output root already exists and is not empty")


# ---------------------------------------------------------------------------
# Path safety primitives.
# ---------------------------------------------------------------------------


def safe_relative_path(value: str) -> Path:
    """A path that is relative, has parts, and never escapes via '..'."""
    path = Path(value)
    if path.is_absolute():
        raise PreflightError(f"absolute path not allowed: {value}")
    if ".." in path.parts:
        raise PreflightError(f"path traversal not allowed: {value}")
    if not path.parts:
        raise PreflightError(f"empty path not allowed: {value}")
    # Collapse any '.' segments and re-check containment semantics.
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

    Each entry is (source_rel_to_skill_dir, destination_rel_to_workspace).
    Returns validated (destination_path, source) pairs in order.
    """
    seen: dict[Path, str] = {}
    validated: list[tuple[Path, str]] = []
    for source, destination in entries:
        src_path = safe_relative_path(source)
        dest_path = safe_relative_path(destination)
        if is_control_destination(dest_path):
            raise PreflightError(f"control-path collision in destination: {destination}")
        # Containment of the resolved destination under the workspace.
        resolved = (workspace / dest_path).resolve()
        try:
            resolved.relative_to(workspace.resolve())
        except ValueError:
            raise PreflightError(f"destination escapes workspace: {destination}")
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
    """Repo-relative suite path -> repo-relative skill directory.

    ``skills/<skill>/evals/evals.json`` -> ``skills/<skill>``.
    """
    parts = Path(suite_repo_path).parts
    if len(parts) < 3 or parts[-1] != "evals.json" or parts[-2] != "evals":
        raise PreflightError(f"suite path must be .../<skill>/evals/evals.json: {suite_repo_path}")
    return Path(*parts[:-2]).as_posix()


def load_suite_from_commit(repo: Path, commit: str, suite_repo_path: str) -> dict[str, Any]:
    suite_rel = safe_relative_path(suite_repo_path).as_posix()
    assert_no_symlink_at(repo, commit, suite_rel)
    try:
        data = json.loads(git_show(repo, commit, suite_rel).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PreflightError(f"cannot parse suite JSON at {suite_rel}: {exc}")
    if not isinstance(data, dict) or "evals" not in data:
        raise PreflightError(f"invalid suite structure at {suite_rel}")
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
    """Materialize an authentic plugin tree under plugin_root.

    Layout: ``.claude-plugin/plugin.json`` and ``skills/<name>/SKILL.md`` for the
    target skill (with-skill only). Returns object IDs of materialized blobs.
    """
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
        # Reject symlinks anywhere in the committed skill tree before staging.
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
    ``--skill-dir``, environment, prompt, workspace, or plugin.
    """
    locations: dict[str, Path] = {}
    # Fake global skill canary in the config-dir skill root.
    skill_dir = config_root / "skills" / FAKE_GLOBAL_SKILL_NAME
    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text(
        "---\n"
        f"name: {FAKE_GLOBAL_SKILL_NAME}\n"
        "description: Suppression canary; must never be discovered or invoked.\n"
        "---\n\n"
        f"# {FAKE_GLOBAL_SKILL_NAME}\n\n{GLOBAL_SKILL_CANARY}\n",
        encoding="utf-8",
    )
    locations["global_skill"] = skill_dir
    # Project-instruction canary in a global instructions location.
    instructions = config_root / "CLAUDE.md"
    instructions.write_text(
        f"# Global instructions\n\n{PROJECT_INSTRUCTION_CANARY}\n", encoding="utf-8"
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
    """Stage the allowlisted repository seed + declared case fixtures.

    Returns the staged-object manifest with real blob object IDs.
    """
    # Each entry is (repo_relative_source, destination_relative_to_workspace).
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

    validated = prevalidate_staging(
        [(src, dest) for src, dest in entries], workspace
    )

    staged: list[StagedObject] = []
    for (dest_path, _src_for_validation), (repo_rel, _dest) in zip(validated, entries):
        blob = git_show(repo, commit, repo_rel)
        object_id = git_blob_id(repo, commit, repo_rel)
        dest_full = workspace / dest_path
        dest_full.parent.mkdir(parents=True, exist_ok=True)
        dest_full.write_bytes(blob)
        staged.append(
            StagedObject(destination=dest_path.as_posix(), source=repo_rel, object_id=object_id)
        )
    return staged


def verify_workspace_isolation(workspace: Path) -> None:
    """No eval/control/harness material may live in a target workspace."""
    for path in workspace.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(workspace).as_posix()
        name = path.name
        if name in ("evals.json", "benchmark.json"):
            raise PreflightError(f"workspace contains eval/control material: {rel}")
        if name.endswith(".json") and path.parent.name == "graders":
            raise PreflightError(f"workspace contains grader material: {rel}")
        if rel.startswith("evals/") or rel.startswith("graders/"):
            raise PreflightError(f"workspace contains eval/control material: {rel}")
        for marker in (PROJECT_INSTRUCTION_CANARY, GLOBAL_SKILL_CANARY):
            if path.stat().st_size < 1_000_000:
                try:
                    if marker in path.read_text(encoding="utf-8", errors="ignore"):
                        raise PreflightError(f"workspace leaked canary content: {rel}")
                except UnicodeDecodeError:
                    pass


# ---------------------------------------------------------------------------
# Environment construction.
# ---------------------------------------------------------------------------


def validate_user_settings(path: Path) -> tuple[dict[str, str], dict[str, Any]]:
    """Validate a regular, user-owned, tight-mode settings file and its env map.

    Returns (env_map, provenance). Never returns or logs values outside the map.
    """
    provenance: dict[str, Any] = {"path": str(path)}
    if not path.exists():
        provenance["status"] = "absent"
        return {}, provenance
    st = path.lstat()
    if not stat.S_ISREG(st.st_mode):
        raise PreflightError(f"user settings is not a regular file: {path}")
    if st.st_uid != os.getuid():
        raise PreflightError(f"user settings not owned by current user: {path}")
    if st.st_mode & 0o022:
        raise PreflightError(f"user settings is group/world-writable: {path}")
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
            raise PreflightError(f"user settings env key {key!r} must map to a string")
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
) -> tuple[dict[str, str], dict[str, Any]]:
    """Build a scrubbed child environment: import user env first, then override.

    ``leaked_paths`` are canonical absolute paths (source/eval/skill) that must
    never appear in any child value. Provenance records key names only.
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
    # Import user-provided values first.
    env.update(user_env)

    # Harness-owned overrides.
    env["CLAUDE_CONFIG_DIR"] = str(config_dir)
    env["PWD"] = str(process_start_dir)
    env["TMPDIR"] = str(temp_dir)
    env["PATH"] = str(capability_dir) + os.pathsep + env["PATH"]

    # Leak check over child values only.
    for key, value in env.items():
        if not isinstance(value, str):
            raise PreflightError(f"environment value for {key} is not a string")
        for leaked in leaked_paths:
            if leaked and leaked in value:
                # Name the key only; never the value.
                raise PreflightError(f"environment key {key!r} exposes a forbidden path")

    provenance = {
        "user_settings": settings_provenance,
        "imported_keys": sorted(user_env.keys()),
        "override_keys": ["CLAUDE_CONFIG_DIR", "PWD", "TMPDIR", "PATH"],
        "final_keys": sorted(env.keys()),
    }
    return env, provenance


# ---------------------------------------------------------------------------
# Executable resolution and exact command.
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
        raise PreflightError(
            f"claude version {CLAUDE_VERSION} required, got {version!r}"
        )
    return str(absolute), f"Claude Code {version}"


def shutil_which(name: str) -> str | None:
    import shutil

    return shutil.which(name)


def build_claude_argv(
    *,
    claude_path: str,
    settings_path: Path,
    plugin_root: Path,
    workspace: Path,
    prompt: str,
) -> list[str]:
    """Exact argv as an array: one --tools value plus every fixed flag."""
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
        "--root", str(workspace),
        "--",
        prompt,
    ]


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
    """Run a child in a new session; on timeout SIGTERM then SIGKILL the group.

    Reader threads retain partial stdout/stderr even when the process is killed.
    The whole process group is force-killed on timeout even if the parent has
    already exited, so forked grandchildren cannot survive.
    """
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
            # Always force-kill the group even if the parent exited.
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
# Stream-json parsing and strict event validation.
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


def count_target_invocations(events: list[dict[str, Any]], target: str) -> tuple[int, list[str]]:
    """Count exact ``Skill`` tool_use whose input.skill equals the target.

    Prefixes and ``Skill(list)`` never count.
    """
    hits: list[str] = []
    for block in _assistant_blocks(events):
        if block.get("type") == "tool_use" and block.get("name") == "Skill":
            skill = block.get("input", {}).get("skill")
            if skill == target:
                hits.append(str(block.get("id", "")))
    return len(hits), hits


def bash_d7y_commands(events: list[dict[str, Any]], workspace: str) -> dict[str, list[str]]:
    """Collect exact ``d7y initiatives list/check --root <workspace> --json`` commands."""
    evidence: dict[str, list[str]] = {"list": [], "check": []}
    for block in _assistant_blocks(events):
        if block.get("type") != "tool_use" or block.get("name") != "Bash":
            continue
        command = block.get("input", {}).get("command", "")
        if not isinstance(command, str):
            continue
        if "d7y initiatives list" in command and "--root" in command and "--json" in command:
            evidence["list"].append(command)
        if "d7y initiatives check" in command and "--root" in command and "--json" in command:
            evidence["check"].append(command)
    return evidence


def extract_routed_models(events: list[dict[str, Any]]) -> list[str]:
    models: list[str] = []
    for event in events:
        if event.get("type") != "assistant":
            continue
        model = event.get("message", {}).get("model")
        if isinstance(model, str) and model not in models:
            models.append(model)
    return models


def check_canary_leakage(events: list[dict[str, Any]]) -> tuple[bool, list[str]]:
    """Return (clean, issues). Any canary discovery/invocation/text is a leak."""
    issues: list[str] = []
    for event in events:
        if event.get("type") == "system" and event.get("subtype") == "init":
            for skill in event.get("skills", []) or []:
                if isinstance(skill, str) and (
                    FAKE_GLOBAL_SKILL_NAME in skill or skill == FAKE_GLOBAL_SKILL_NAME
                ):
                    issues.append(f"canary global skill discovered in init: {skill}")
    for block in _assistant_blocks(events):
        if block.get("type") == "tool_use" and block.get("name") == "Skill":
            skill = block.get("input", {}).get("skill", "")
            if isinstance(skill, str) and FAKE_GLOBAL_SKILL_NAME in skill:
                issues.append(f"canary global skill invoked: {skill}")
        if block.get("type") == "text":
            text = block.get("text", "")
            if isinstance(text, str):
                if PROJECT_INSTRUCTION_CANARY in text:
                    issues.append("project-instruction canary present in response")
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
) -> ArmValidation:
    """Require exactly one init and one successful terminal result, exact fields."""
    errors: list[str] = []
    target = expected_target(skill_name)

    init_events = [e for e in events if e.get("type") == "system" and e.get("subtype") == "init"]
    if len(init_events) == 0:
        return ArmValidation(False, ["missing system.init event"])
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
            errors.append(f"target skill {target!r} not in init skills {skills!r}")
        if BUILT_IN_SKILL not in skills_str:
            errors.append(f"built-in {BUILT_IN_SKILL!r} missing from init skills")
    else:
        if target in skills_str:
            errors.append(f"target skill leaked into baseline init skills {skills!r}")
    # Canary must never appear regardless of arm.
    for s in skills_str:
        if FAKE_GLOBAL_SKILL_NAME in s:
            errors.append(f"canary skill discovered in init: {s!r}")

    plugins = init.get("plugins", []) or []
    plugin_names = [p.get("name") for p in plugins if isinstance(p, dict)]
    if expected_plugin not in plugin_names:
        errors.append(f"expected plugin {expected_plugin!r} not in {plugin_names!r}")
    extra_plugins = [n for n in plugin_names if n not in (expected_plugin,)]
    if extra_plugins:
        errors.append(f"unexpected plugins: {extra_plugins!r}")

    session_id = init.get("session_id")
    if not isinstance(session_id, str) or not session_id:
        errors.append("init missing session_id")
    elif other_session_id is not None and session_id == other_session_id:
        errors.append("init session_id is not distinct across arms")

    result_events = [e for e in events if e.get("type") == "result"]
    if len(result_events) == 0:
        errors.append("missing result event")
        result = None
    else:
        if len(result_events) > 1:
            errors.append(f"multiple result events: {len(result_events)}")
        result = result_events[0]
        if result.get("is_error") not in (False,):
            errors.append(f"result is_error not false: {result.get('is_error')!r}")
        subtype = result.get("subtype")
        if subtype not in ("success", "result"):
            if result.get("is_error") is not False:
                errors.append(f"result not a successful terminal: subtype={subtype!r}")
        for field_name in REQUIRED_RESULT_FIELDS:
            if field_name not in result:
                errors.append(f"result missing required field {field_name!r}")
        # Telemetry modelUsage must keep canonical claude-sonnet-5.
        usage = result.get("modelUsage") or {}
        if not isinstance(usage, dict) or not usage:
            errors.append("result modelUsage empty or not an object")

    routed = extract_routed_models(events)
    for model in routed:
        if model not in ROUTED_MODELS:
            errors.append(f"unexpected routed assistant model {model!r}")

    return ArmValidation(
        ok=len(errors) == 0,
        errors=errors,
        init=init,
        result=result,
        session_id=session_id,
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
    argv: list[str]
    outcome: ProcessOutcome | None
    events: list[dict[str, Any]] = field(default_factory=list)
    validation: ArmValidation | None = None
    parse_error: str | None = None
    invocation_count: int = 0
    bash_commands: dict[str, list[str]] = field(default_factory=dict)
    checker: dict[str, Any] | None = None
    workspace_changes: dict[str, Any] = field(default_factory=dict)
    canary_clean: bool = True
    canary_issues: list[str] = field(default_factory=list)
    final_response: str | None = None
    telemetry: dict[str, Any] = field(default_factory=dict)


def compute_workspace_changes(workspace: Path, staged_destinations: set[str]) -> dict[str, Any]:
    added: list[str] = []
    modified: list[str] = []
    for path in workspace.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(workspace).as_posix()
        if rel in staged_destinations:
            continue
        added.append(rel)
    return {"added": sorted(added), "modified": sorted(modified)}


def count_initiatives_created(changes: dict[str, Any]) -> int:
    added = changes.get("added", [])
    return sum(
        1
        for rel in added
        if rel.startswith("initiatives/") and rel.endswith("/initiative.md")
    )


def evaluate_assertion(
    assertion: dict[str, Any],
    *,
    case: dict[str, Any],
    with_skill: ArmResult,
    baseline: ArmResult,
    skill_name: str,
) -> tuple[str, str]:
    """Resolve one assertion to (status, evidence). Never overclaim."""
    dimension = assertion.get("dimension")
    kind = assertion.get("kind")
    required = assertion.get("required", False)
    aid = assertion.get("id", "?")

    if kind not in ("deterministic", "rubric", "human"):
        return CHECK_UNGRADABLE, f"unknown kind {kind!r}"

    if kind in ("rubric", "human"):
        return CHECK_PENDING, f"{kind} assertion requires human judgment"

    # Deterministic assertions.
    target = expected_target(skill_name)

    if dimension == "invocation":
        if not (with_skill.validation and with_skill.validation.ok):
            return CHECK_ERROR, "with-skill arm evidence invalid"
        if case.get("should_trigger"):
            if with_skill.invocation_count > 0:
                return CHECK_PASS, f"target Skill invocation observed ({with_skill.invocation_count})"
            return CHECK_FAIL, "expected target invocation, none observed"
        # negative control: target absent while availability proven
        if with_skill.invocation_count > 0:
            return CHECK_FAIL, "target invoked in negative control"
        if target in (with_skill.validation.skills if with_skill.validation else []):
            return CHECK_PASS, "target available but not invoked in negative control"
        return CHECK_UNGRADABLE, "target availability unproven for negative control"

    if dimension == "process":
        # runs-checker-before-and-after: list before, check after, both present.
        if not (with_skill.validation and with_skill.validation.ok):
            return CHECK_ERROR, "with-skill arm evidence invalid"
        cmds = with_skill.bash_commands
        if cmds.get("list") and cmds.get("check"):
            return CHECK_PASS, f"d7y list ({len(cmds['list'])}) and check ({len(cmds['check'])}) commands observed"
        missing = []
        if not cmds.get("list"):
            missing.append("list")
        if not cmds.get("check"):
            missing.append("check")
        return CHECK_FAIL, f"missing d7y command events: {', '.join(missing)}"

    if dimension == "outcome":
        # creates-one-initiative / creates-no-duplicate / creates-no-initiative.
        if not (with_skill.validation and with_skill.validation.ok):
            return CHECK_ERROR, "with-skill arm evidence invalid"
        created = count_initiatives_created(with_skill.workspace_changes)
        checker_ok = bool(with_skill.checker and with_skill.checker.get("valid"))
        desc = assertion.get("description", "").lower()
        if case.get("should_trigger"):
            if created == 1 and checker_ok:
                return CHECK_PASS, f"exactly one initiative created and checker valid (created={created})"
            return CHECK_FAIL, f"expected one valid initiative (created={created}, checker_valid={checker_ok})"
        # negative: no initiative created
        if created == 0:
            return CHECK_PASS, "no initiative created in negative control"
        return CHECK_FAIL, f"unexpected initiative created in negative control (created={created})"

    # Any other deterministic dimension (e.g. efficiency) is ungradable offline.
    return CHECK_UNGRADABLE, f"deterministic {dimension!r} assertion {aid!r} unsupported offline"


def compute_checks(
    *,
    case: dict[str, Any],
    with_skill: ArmResult,
    baseline: ArmResult,
    skill_name: str,
) -> dict[str, Any]:
    target = expected_target(skill_name)

    # Pair validity: both arms produced valid executor evidence, distinct
    # sessions, target availability with-skill and absence in baseline, control
    # parity, and clean canaries.
    pair_errors: list[str] = []
    for label, arm in (("with-skill", with_skill), ("baseline", baseline)):
        if not (arm.validation and arm.validation.ok):
            pair_errors.append(f"{label} arm evidence invalid: {arm.validation.errors if arm.validation else 'no validation'}")
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

    # Treatment checks: harness-owned availability/absence evidence.
    treatment_errors: list[str] = []
    if target not in ws_skills:
        treatment_errors.append("target unavailable with-skill")
    if target in bl_skills:
        treatment_errors.append("target present in baseline")
    treatment = CHECK_PASS if not treatment_errors else CHECK_FAIL

    # With-skill assertions.
    assertion_results: list[dict[str, Any]] = []
    for assertion in case.get("assertions", []):
        status, evidence = evaluate_assertion(
            assertion,
            case=case,
            with_skill=with_skill,
            baseline=baseline,
            skill_name=skill_name,
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

    # Baseline observations (no pass/fail judgment that invalidates the pair).
    baseline_observations = [
        {
            "type": "exit_code",
            "value": baseline.outcome.exit_code if baseline.outcome else None,
            "timed_out": bool(baseline.outcome and baseline.outcome.timed_out),
            "duration_seconds": baseline.outcome.duration_seconds if baseline.outcome else None,
            "invocation_count": baseline.invocation_count,
        }
    ]

    # Required-assertion exit semantics: any required pending/ungradable/error/fail blocks pass.
    blocking = any(
        r["required"] and r["status"] in (CHECK_PENDING, CHECK_UNGRADABLE, CHECK_ERROR, CHECK_FAIL)
        for r in assertion_results
    )
    case_pass = (
        pair_validity == CHECK_PASS
        and treatment == CHECK_PASS
        and not blocking
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
# Artifact writing.
# ---------------------------------------------------------------------------


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_json(path: Path, data: Any) -> None:
    write_text(path, json.dumps(data, indent=2, sort_keys=False))


def sanitize_for_artifact(text: str, forbidden: list[str]) -> str:
    out = text
    for token in forbidden:
        if token:
            out = out.replace(token, "<redacted>")
    return out


def write_arm_artifacts(
    arm_dir: Path,
    arm: ArmResult,
    *,
    executable: str | None,
    executable_version: str | None,
    forbidden_paths: list[str],
) -> None:
    """Always write the complete per-arm artifact tree, even on failure."""
    if arm.outcome is not None:
        write_text(arm_dir / "trace.jsonl", sanitize_for_artifact(arm.outcome.stdout, forbidden_paths))
        write_text(arm_dir / "stderr.txt", sanitize_for_artifact(arm.outcome.stderr, forbidden_paths))
        write_json(
            arm_dir / "process.json",
            {
                "exit_code": arm.outcome.exit_code,
                "timed_out": arm.outcome.timed_out,
                "duration_seconds": arm.outcome.duration_seconds,
                "pid": arm.outcome.pid,
            },
        )
    write_json(
        arm_dir / "provenance.json",
        {
            "executable": executable,
            "executable_version": executable_version,
            "argv": arm.argv,
        },
    )
    if arm.final_response is not None:
        write_text(arm_dir / "final-response.txt", sanitize_for_artifact(arm.final_response, forbidden_paths))
    telemetry = dict(arm.telemetry)
    telemetry["routed_models"] = (
        arm.validation.routed_models if arm.validation and arm.validation.routed_models else []
    )
    telemetry["canonical_model"] = EXPECTED_MODEL
    telemetry["parse_error"] = arm.parse_error
    write_json(arm_dir / "telemetry.json", telemetry)
    write_json(arm_dir / "command-events.json", arm.bash_commands)
    if arm.checker is not None:
        write_json(arm_dir / "checker.json", arm.checker)
    write_json(arm_dir / "workspace-changes.json", arm.workspace_changes)
    write_json(
        arm_dir / "validation.json",
        {
            "ok": arm.validation.ok if arm.validation else False,
            "errors": arm.validation.errors if arm.validation else ["no validation"],
            "skills": arm.validation.skills if arm.validation else [],
            "session_id": arm.validation.session_id if arm.validation else None,
        },
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
    claude_path_arg: str
    dry_run: bool
    timeout_seconds: float


def run_preflight(args: argparse.Namespace) -> Preflight:
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
    output_dir.mkdir(parents=True, exist_ok=True)

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

    # Authentic plugins (outside target workspaces).
    plugin_object_ids = write_plugin(
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

    # Shared capability installation: both D7Y objects required.
    capability_object_ids = materialize_capability(repo, commit, roots["capability"])

    # Suppression canaries live in the suppressed (config) locations only.
    write_canaries(roots["with_skill_config"])
    write_canaries(roots["baseline_config"])

    source_status_before = source_status(repo)

    # Allowlisted repository seed for starting-initiatives: the org contract.
    seed_repo_paths = ["initiatives/README.md"]

    staged_with_skill = stage_workspace_seed(
        roots["with_skill_workspace"],
        case=case,
        repo=repo,
        commit=commit,
        skill_repo_dir=skill_repo_dir,
        seed_repo_paths=seed_repo_paths,
    )
    staged_baseline = stage_workspace_seed(
        roots["baseline_workspace"],
        case=case,
        repo=repo,
        commit=commit,
        skill_repo_dir=skill_repo_dir,
        seed_repo_paths=seed_repo_paths,
    )

    for workspace in (roots["with_skill_workspace"], roots["baseline_workspace"]):
        verify_workspace_isolation(workspace)

    # Canonical absolute paths that must never leak into child values.
    evals_abs = str((repo / "evals").resolve())
    skills_abs = str((repo / skill_repo_dir.split("/")[0]).resolve())
    leaked_paths = [str(repo.resolve()), evals_abs, skills_abs]

    user_settings_path = Path(
        os.environ.get("D7Y_EVAL_USER_SETTINGS", str(Path.home() / ".claude" / "settings.json"))
    )
    env_with_skill, env_prov = build_child_env(
        user_settings_path=user_settings_path,
        leaked_paths=leaked_paths,
        config_dir=roots["with_skill_config"],
        process_start_dir=roots["process_start"],
        capability_dir=roots["capability"],
        temp_dir=roots["with_skill_temp"],
    )
    env_baseline, _ = build_child_env(
        user_settings_path=user_settings_path,
        leaked_paths=leaked_paths,
        config_dir=roots["baseline_config"],
        process_start_dir=roots["process_start"],
        capability_dir=roots["capability"],
        temp_dir=roots["baseline_temp"],
    )

    return Preflight(
        repo=repo,
        commit=commit,
        suite_repo_path=suite_rel,
        skill_repo_dir=skill_repo_dir,
        skill_name=skill_name,
        case=case,
        output_dir=output_dir,
        leaked_paths=leaked_paths,
        roots=roots,
        with_skill_workspace=roots["with_skill_workspace"],
        baseline_workspace=roots["baseline_workspace"],
        settings_path=settings_path,
        with_skill_plugin=roots["with_skill_plugin"],
        baseline_plugin=roots["baseline_plugin"],
        capability_dir=roots["capability"],
        process_start_dir=roots["process_start"],
        staged_with_skill=staged_with_skill,
        staged_baseline=staged_baseline,
        plugin_object_ids=plugin_object_ids,
        capability_object_ids=capability_object_ids,
        source_status_before=source_status_before,
        env_with_skill=env_with_skill,
        env_baseline=env_baseline,
        env_provenance=env_prov,
        claude_path_arg=str(args.claude) if args.claude else "claude",
        dry_run=args.dry_run,
        timeout_seconds=float(args.timeout),
    )


# ---------------------------------------------------------------------------
# Arm execution.
# ---------------------------------------------------------------------------


def execute_arm(
    preflight: Preflight,
    *,
    with_skill: bool,
    executable: str | None,
    executable_version: str | None,
    other_session_id: str | None,
) -> ArmResult:
    label = "with-skill" if with_skill else "baseline"
    workspace = preflight.with_skill_workspace if with_skill else preflight.baseline_workspace
    plugin_root = preflight.with_skill_plugin if with_skill else preflight.baseline_plugin
    env = preflight.env_with_skill if with_skill else preflight.env_baseline
    expected_plugin = SESSION_PLUGIN_NAME if with_skill else CONTROL_PLUGIN_NAME
    arm_dir = preflight.roots["with_skill_artifacts" if with_skill else "baseline_artifacts"]

    argv = build_claude_argv(
        claude_path=executable or preflight.claude_path_arg,
        settings_path=preflight.settings_path,
        plugin_root=plugin_root,
        workspace=workspace,
        prompt=preflight.case.get("prompt", ""),
    )

    arm = ArmResult(config=label, workspace=workspace, argv=argv, outcome=None)

    try:
        outcome = run_process(
            argv,
            cwd=preflight.process_start_dir,
            env=env,
            timeout=preflight.timeout_seconds,
        )
    except OSError as exc:
        arm.parse_error = f"process spawn failed: {exc}"
        write_arm_artifacts(
            arm_dir, arm,
            executable=executable, executable_version=executable_version,
            forbidden_paths=preflight.leaked_paths,
        )
        return arm

    arm.outcome = outcome

    try:
        events = parse_stream_json(outcome.stdout)
        arm.events = events
    except ValueError as exc:
        arm.parse_error = str(exc)
        write_arm_artifacts(
            arm_dir, arm,
            executable=executable, executable_version=executable_version,
            forbidden_paths=preflight.leaked_paths,
        )
        return arm

    arm.canary_clean, arm.canary_issues = check_canary_leakage(events)
    arm.validation = validate_arm_events(
        events,
        with_skill=with_skill,
        skill_name=preflight.skill_name,
        expected_plugin=expected_plugin,
        other_session_id=other_session_id,
    )
    count, _ = count_target_invocations(events, expected_target(preflight.skill_name))
    arm.invocation_count = count
    arm.bash_commands = bash_d7y_commands(events, str(workspace))

    # Telemetry from result event.
    result = arm.validation.result if arm.validation else None
    if result:
        arm.final_response = result.get("result")
        arm.telemetry = {
            "num_turns": result.get("num_turns"),
            "permission_denials": result.get("permission_denials"),
            "is_error": result.get("is_error"),
            "modelUsage": result.get("modelUsage"),
        }

    # Independent post-arm checker evidence (separate from command events).
    arm.checker = run_independent_checker(
        d7y_executable=preflight.capability_dir / "d7y",
        workspace=workspace,
        process_start_dir=preflight.process_start_dir,
        env=env,
    )

    staged_destinations = {obj.destination for obj in (preflight.staged_with_skill if with_skill else preflight.staged_baseline)}
    arm.workspace_changes = compute_workspace_changes(workspace, staged_destinations)

    write_arm_artifacts(
        arm_dir, arm,
        executable=executable, executable_version=executable_version,
        forbidden_paths=preflight.leaked_paths,
    )
    return arm


# ---------------------------------------------------------------------------
# Main.
# ---------------------------------------------------------------------------


def write_run_manifest(preflight: Preflight, executable: str | None, executable_version: str | None) -> dict[str, Any]:
    manifest = {
        "commit": preflight.commit,
        "suite": preflight.suite_repo_path,
        "skill_name": preflight.skill_name,
        "case_id": preflight.case.get("id"),
        "should_trigger": preflight.case.get("should_trigger"),
        "roots": {k: str(v) for k, v in preflight.roots.items()},
        "executable": executable,
        "executable_version": executable_version,
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
        "source_status_before": preflight.source_status_before,
        "dry_run": preflight.dry_run,
    }
    write_json(preflight.output_dir / "manifest.json", manifest)
    return manifest


def write_summary(preflight: Preflight, checks: dict[str, Any] | None, source_mutation: bool) -> str:
    lines: list[str] = []
    lines.append(f"# Eval summary: {preflight.case.get('id')} ({preflight.skill_name})")
    lines.append("")
    lines.append(f"- commit: `{preflight.commit}`")
    lines.append(f"- suite: `{preflight.suite_repo_path}`")
    lines.append(f"- canonical model: `{EXPECTED_MODEL}`")
    lines.append(f"- dry run: {preflight.dry_run}")
    if checks is not None:
        lines.append(f"- pair validity: {checks['pair_validity']['status']}")
        lines.append(f"- treatment checks: {checks['treatment_checks']['status']}")
        lines.append(f"- case pass: {checks['case_pass']}")
        lines.append("- with-skill assertions:")
        for a in checks["with_skill_assertions"]:
            req = " (required)" if a["required"] else ""
            lines.append(f"  - {a['id']} [{a['dimension']}/{a['kind']}]: {a['status']}{req}")
    if source_mutation:
        lines.append("")
        lines.append("- WARNING: source checkout mutated during the run; result invalidated.")
    lines.append("")
    lines.append(
        "This summary reports observations from one paired run only. It makes no "
        "maturity recommendation and does not modify SKILL.md or accept a benchmark."
    )
    text = "\n".join(lines)
    write_text(preflight.output_dir / "summary.md", text)
    return text


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

    try:
        preflight = run_preflight(args)
    except PreflightError as exc:
        print(f"d7y-eval: preflight failed: {exc}", file=sys.stderr)
        return 2

    executable: str | None = None
    executable_version: str | None = None
    source_mutation = False
    checks: dict[str, Any] | None = None
    exit_code = 0

    try:
        if preflight.dry_run:
            # Dry-run performs the complete preflight only.
            write_run_manifest(preflight, executable=None, executable_version=None)
            write_summary(preflight, checks=None, source_mutation=False)
            print(f"dry-run complete: manifest at {preflight.output_dir / 'manifest.json'}")
            return 0

        # Live: resolve the executable exactly once for both arms.
        try:
            executable, executable_version = resolve_executable(
                Path(preflight.claude_path_arg)
            )
        except PreflightError as exc:
            print(f"d7y-eval: executable resolution failed: {exc}", file=sys.stderr)
            write_run_manifest(preflight, None, None)
            return 2

        with_skill = execute_arm(
            preflight, with_skill=True,
            executable=executable, executable_version=executable_version,
            other_session_id=None,
        )
        baseline = execute_arm(
            preflight, with_skill=False,
            executable=executable, executable_version=executable_version,
            other_session_id=(with_skill.validation.session_id if with_skill.validation else None),
        )

        checks = compute_checks(
            case=preflight.case,
            with_skill=with_skill,
            baseline=baseline,
            skill_name=preflight.skill_name,
        )
        write_json(preflight.output_dir / "checks.json", checks)
        write_run_manifest(preflight, executable, executable_version)
        exit_code = 0 if checks["case_pass"] else 1
    finally:
        after = source_status(preflight.repo)
        source_mutation = after != preflight.source_status_before
        write_summary(preflight, checks, source_mutation)
        if source_mutation and not preflight.dry_run:
            exit_code = 1

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
