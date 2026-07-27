#!/usr/bin/env python3
"""Minimal D7Y skill eval runner for Claude Code 2.1.218.

This runner executes paired with-skill and no-skill configurations for one
selected case, captures raw evidence, and applies deterministic checks.

This implements the eval-execution-harness plan vertical slice: one selected
case, one proven executor (Claude Code 2.1.218), sequential execution, and
trusted built-in checks only.
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import shutil
import subprocess
import sys
import tempfile
import time
from enum import Enum
from pathlib import Path
from typing import Any

# Session-only plugin contract
SESSION_PLUGIN_NAME = "d7y-eval-session"
SESSION_PLUGIN_VERSION = "0.0.1"

# Expected tool sets for the first vertical slice
POSITIVE_TOOLS = ["Skill", "Read", "Write", "Edit", "Bash"]
BASELINE_TOOLS = ["Skill", "Read", "Write", "Edit", "Bash"]

# Expected model and permissions
EXPECTED_MODEL = "claude-sonnet-5"
EXPECTED_PERMISSION_MODE = "dontAsk"
EXPECTED_MCP_SERVERS: list[str] = []

# Timeout configuration
DEFAULT_TIMEOUT_SECONDS = 600
ESCALATION_SECONDS = 5


class EvalConfig:
    """Eval execution configuration."""

    def __init__(
        self,
        *,
        source_repo: Path,
        commit: str,
        suite_path: Path,
        case_id: str,
        output_dir: Path,
        skill_name: str,
        claude_path: Path | None = None,
        dry_run: bool = False,
    ):
        self.source_repo = source_repo
        self.commit = commit
        self.suite_path = suite_path
        self.case_id = case_id
        self.output_dir = output_dir
        self.skill_name = skill_name
        self.claude_path = claude_path or Path("claude")
        self.dry_run = dry_run


class RunResult:
    """Result of a single eval arm execution."""

    def __init__(self, config: str, success: bool):
        self.config = config  # "with-skill" or "baseline"
        self.success = success
        self.events: list[dict[str, Any]] = []
        self.stderr: str = ""
        self.stdout: str = ""
        self.exit_code: int | None = None
        self.duration_seconds: float = 0.0
        self.timed_out = False
        self.workspace_changes: dict[str, Any] = {}
        self.metadata: dict[str, Any] = {}


class CheckResult(Enum):
    """Deterministic check result."""
    PASS = "pass"
    FAIL = "fail"
    ERROR = "error"
    UNGRADABLE = "ungradable"
    PENDING = "pending"


def load_suite(suite_path: Path) -> dict[str, Any]:
    """Load and validate an evals.json suite."""
    try:
        data = json.loads(suite_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or "evals" not in data:
            raise ValueError("Invalid suite structure")
        return data
    except (OSError, json.JSONDecodeError) as e:
        raise ValueError(f"Cannot load suite from {suite_path}: {e}")


def find_case(suite: dict[str, Any], case_id: str) -> dict[str, Any]:
    """Find a case by ID in the suite."""
    for case in suite.get("evals", []):
        if case.get("id") == case_id:
            return case
    raise ValueError(f"Case {case_id} not found in suite")


def resolve_commit(repo: Path, ref: str) -> str:
    """Resolve a git ref to a full commit SHA."""
    result = subprocess.run(
        ["git", "rev-parse", "--verify", f"{ref}^{{commit}}"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise ValueError(f"Cannot resolve ref {ref} in {repo}")
    return result.stdout.strip()


def verify_commit_exists(repo: Path, commit: str) -> None:
    """Verify that a commit exists in the repository."""
    result = subprocess.run(
        ["git", "rev-parse", "--verify", f"{commit}^{{commit}}"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise ValueError(f"Commit {commit} not found in {repo}")


def get_source_status(repo: Path) -> str:
    """Get the current git status of the source repository."""
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout


def resolve_git_object(repo: Path, commit: str, object_path: str) -> bytes:
    """Read a Git object from the repository at a specific commit."""
    result = subprocess.run(
        ["git", "cat-file", "-p", f"{commit}:{object_path}"],
        cwd=repo,
        capture_output=True,
        text=False,
        check=False,
    )
    if result.returncode != 0:
        raise ValueError(f"Cannot resolve {object_path} at {commit}")
    return result.stdout


def check_git_tree_mode(repo: Path, commit: str, tree_path: str) -> None:
    """Check if any path in the git tree is a symlink."""
    result = subprocess.run(
        ["git", "ls-tree", "-r", f"{commit}:{tree_path}"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        # Path might not exist, which is fine for some cases
        return

    for line in result.stdout.splitlines():
        # Each line is: mode type hash    path
        parts = line.split(None, 3)
        if len(parts) >= 2:
            mode = parts[0]
            obj_type = parts[1]
            if mode == "120000":  # Git mode for symlink
                raise ValueError(f"Symlink detected in committed tree: {parts[3]}")


def validate_path_for_source(path: Path, source_repo: Path) -> None:
    """Validate that a path is safe for reading from source."""
    if path.is_absolute():
        raise ValueError(f"Absolute path not allowed for source: {path}")

    # Check for traversal
    if ".." in path.parts:
        raise ValueError(f"Path traversal not allowed: {path}")

    # Check if path would be outside source repo
    try:
        resolved = (source_repo / path).resolve()
        if not str(resolved).startswith(str(source_repo)):
            raise ValueError(f"Path escapes source repository: {path}")
    except OSError:
        raise ValueError(f"Invalid path: {path}")


def validate_path_for_destination(path: Path) -> None:
    """Validate that a path is safe for writing to destination."""
    if path.is_absolute():
        raise ValueError(f"Absolute path not allowed for destination: {path}")

    # Check for traversal
    if ".." in path.parts:
        raise ValueError(f"Path traversal not allowed: {path}")

    # Check for control-path collisions
    dangerous_names = {"settings.json", "CLAUDE.md", ".claude-plugin"}
    if path.name in dangerous_names:
        raise ValueError(f"Control-path collision not allowed: {path}")


def create_isolated_workspace(
    base_dir: Path,
    config: str,
    case_id: str,
) -> Path:
    """Create an isolated workspace for one configuration."""
    workspace = base_dir / f"{config}-{case_id}"
    workspace.mkdir(parents=True, exist_ok=True)
    return workspace


def create_session_plugin(
    workspace: Path,
    skill_name: str,
    with_skill: bool,
    source_repo: Path,
    commit: str,
) -> Path:
    """Create a session-only plugin directory."""
    plugin_dir = workspace / ".d7y-eval-plugin"
    plugin_dir.mkdir(parents=True, exist_ok=True)

    # Create plugin.json manifest
    plugin_manifest = {
        "name": SESSION_PLUGIN_NAME,
        "version": SESSION_PLUGIN_VERSION,
        "description": "D7Y eval session plugin",
        "skills": []
    }

    if with_skill:
        # Materialize the target skill from committed Git objects
        skill_path = f"skills/{skill_name}/SKILL.md"
        try:
            skill_content = resolve_git_object(source_repo, commit, skill_path)
            skill_path_local = plugin_dir / "SKILL.md"
            skill_path_local.write_bytes(skill_content)
            plugin_manifest["skills"].append({
                "name": skill_name,
                "source": f"{skill_name}@inline"
            })
        except ValueError as e:
            raise ValueError(f"Cannot materialize target skill: {e}")

    # Write plugin manifest
    plugin_json = plugin_dir / "plugin.json"
    plugin_json.write_text(json.dumps(plugin_manifest, indent=2), encoding="utf-8")

    return plugin_dir


def create_control_plugin(workspace: Path) -> Path:
    """Create a control plugin for baseline (no target skill)."""
    plugin_dir = workspace / ".d7y-eval-control"
    plugin_dir.mkdir(parents=True, exist_ok=True)

    # Create minimal plugin.json manifest
    plugin_manifest = {
        "name": "d7y-eval-control",
        "version": SESSION_PLUGIN_VERSION,
        "description": "D7Y eval control plugin",
        "skills": []
    }

    plugin_json = plugin_dir / "plugin.json"
    plugin_json.write_text(json.dumps(plugin_manifest, indent=2), encoding="utf-8")

    return plugin_dir


def create_settings_file(workspace: Path) -> Path:
    """Create a Claude Code settings file with project-only configuration."""
    settings_path = workspace / "settings.json"
    settings = {
        "disableBundledSkills": True,
        "includeGitInstructions": False,
    }
    settings_path.write_text(json.dumps(settings), encoding="utf-8")
    return settings_path


def build_scrubbed_env(
    source_repo: Path,
    workspace: Path,
    plugin_dir: Path,
    settings_path: Path,
    d7y_install: Path,
) -> dict[str, str]:
    """Build a scrubbed child environment for Claude Code execution."""
    source_str = str(source_repo)
    evals_str = "evals"
    workspace_str = str(workspace)

    # Start with minimal platform environment
    env = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": os.environ.get("HOME", ""),
        "USER": os.environ.get("USER", ""),
        "LANG": os.environ.get("LANG", "en_US.UTF-8"),
        "TMPDIR": tempfile.gettempdir(),
    }

    # Import reviewed user environment keys from ~/.claude/settings.json if available
    user_settings_path = Path.home() / ".claude" / "settings.json"
    retained_keys = [
        "ANTHROPIC_AUTH_TOKEN",  # Required for authentication
        "ANTHROPIC_BASE_URL",
    ]

    env_source = "minimal platform"
    if user_settings_path.exists():
        try:
            user_settings = json.loads(user_settings_path.read_text(encoding="utf-8"))
            # Import only retained keys by name, never values
            for key in retained_keys:
                if key in user_settings:
                    env[key] = user_settings[key]  # Preserve key and value
            env_source = f"{env_source}, user keys: {sorted(set(user_settings.keys()) & set(retained_keys))}"
        except (OSError, json.JSONDecodeError):
            pass  # Proceed without user settings

    # Override with harness-owned control variables
    env["CLAUDE_CONFIG_DIR"] = workspace_str
    env["PWD"] = workspace_str

    # Prepend D7Y capability installation to PATH
    d7y_bin = str(d7y_install)
    env["PATH"] = f"{d7y_bin}:{env.get('PATH', '')}"

    # Check for path leaks in all environment variables including system ones
    for key, value in list(env.items()):
        if isinstance(value, str) and (source_str in value or evals_str in value):
            raise ValueError(f"Environment key {key} exposes source or eval path")

    # Also check current environment for leaked paths (excluding TEST_ variables used for testing)
    for key, value in os.environ.items():
        if not key.startswith("TEST_") and isinstance(value, str) and (source_str in value or evals_str in value):
            raise ValueError(f"Environment key {key} contains leaked path")

    # Record environment provenance (key names only, never values)
    env["__D7Y_ENV_SOURCE"] = env_source
    env["__D7Y_ENV_KEYS"] = ",".join(sorted(env.keys()))

    return env


def create_d7y_capability_installation(source_repo: Path, commit: str, target_dir: Path) -> Path:
    """Create a minimal D7Y capability installation from the selected commit."""
    # Create the installation directory
    capability_dir = target_dir / "d7y-install"
    capability_dir.mkdir(parents=True, exist_ok=True)

    # Resolve the d7y façade from the commit
    try:
        d7y_script = resolve_git_object(source_repo, commit, "d7y")
        d7y_path = capability_dir / "d7y"
        d7y_path.write_bytes(d7y_script)
        d7y_path.chmod(0o755)
    except ValueError as e:
        raise ValueError(f"Cannot materialize d7y capability: {e}")

    # Resolve the shared initiative implementation
    try:
        checker_script = resolve_git_object(source_repo, commit, "scripts/check-initiatives.py")
        checker_dir = capability_dir / "scripts"
        checker_dir.mkdir(exist_ok=True)
        (checker_dir / "check-initiatives.py").write_bytes(checker_script)
        (checker_dir / "check-initiatives.py").chmod(0o755)
    except ValueError:
        pass  # Checker may not exist in all commits

    return capability_dir


def stage_workspace_seed(
    workspace: Path,
    suite_path: Path,
    case: dict[str, Any],
    source_repo: Path,
    commit: str,
) -> dict[str, str]:
    """Stage the workspace seed from committed Git objects."""
    selected_objects = {}

    # Stage the initiative contract
    try:
        readme_content = resolve_git_object(source_repo, commit, "initiatives/README.md")
        initiatives_dir = workspace / "initiatives"
        initiatives_dir.mkdir(parents=True, exist_ok=True)
        readme_path = initiatives_dir / "README.md"
        readme_path.write_bytes(readme_content)
        selected_objects["initiatives/README.md"] = f"{commit}:initiatives/README.md"
    except ValueError:
        pass  # Initiatives may not exist in all commits

    # Stage case files
    skill_dir = suite_path.parent.parent
    for file_fixture in case.get("files", []):
        source = file_fixture.get("source")
        destination = file_fixture.get("destination")

        # Validate safe relative paths
        if not source or not destination:
            continue

        source_path = Path(source)
        dest_path = Path(destination)

        validate_path_for_source(source_path, source_repo)
        validate_path_for_destination(dest_path)

        # Read from skill directory using Git objects
        source_full = f"skills/{source_repo.name}/{skill_dir.name}/{source}"
        try:
            content = resolve_git_object(source_repo, commit, source_full)
        except ValueError:
            # Try relative to skill directory
            try:
                content = resolve_git_object(source_repo, commit, f"skills/{source}")
            except ValueError:
                raise ValueError(f"Cannot resolve fixture source: {source}")

        # Write to workspace
        dest_path_full = workspace / dest_path
        dest_path_full.parent.mkdir(parents=True, exist_ok=True)
        dest_path_full.write_bytes(content)

        selected_objects[source_full] = f"{commit}:{source}"

    return selected_objects


def verify_isolation(workspace: Path, source_repo: Path) -> None:
    """Verify that workspace does not contain eval material or source references."""
    workspace_str = str(workspace)
    source_str = str(source_repo)

    # Check for eval definitions
    for eval_path in workspace.rglob("evals.json"):
        raise ValueError(f"Workspace contains eval definition: {eval_path.relative_to(workspace)}")

    # Check for graders
    if (workspace / "graders").exists():
        raise ValueError("Workspace contains graders directory")

    # Check for benchmark files
    for benchmark_path in workspace.rglob("benchmark.json"):
        raise ValueError(f"Workspace contains benchmark file: {benchmark_path.relative_to(workspace)}")


def verify_no_control_collisions(workspace: Path) -> None:
    """Verify workspace doesn't collide with control files."""
    dangerous = {"settings.json", "CLAUDE.md", ".claude-plugin"}
    for path in dangerous:
        if (workspace / path).exists():
            raise ValueError(f"Workspace contains control file: {path}")


def verify_output_root(output_dir: Path, source_repo: Path) -> None:
    """Verify output root is separate from source repository."""
    try:
        output_abs = output_dir.resolve()
        source_abs = source_repo.resolve()

        # Check if output is within source
        is_within_source = False
        try:
            output_abs.relative_to(source_abs)
            is_within_source = True
        except ValueError:
            pass  # Not relative, so it's fine

        if is_within_source:
            raise ValueError("Output root must be outside source repository")

        # Also check if source is within output (reverse containment)
        is_containing_source = False
        try:
            source_abs.relative_to(output_abs)
            is_containing_source = True
        except ValueError:
            pass  # Not relative, so it's fine

        if is_containing_source:
            raise ValueError("Output root must not contain source repository")

        # Check if output already exists and has content
        if output_dir.exists():
            any_files = any(output_dir.rglob("*"))
            if any_files:
                raise ValueError("Output root already exists and contains files")

    except OSError as e:
        raise ValueError(f"Cannot verify output root: {e}")


def verify_executable(claude_path: Path) -> tuple[str, str]:
    """Verify Claude Code executable and capture version."""
    result = subprocess.run(
        [str(claude_path), "--version"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise ValueError(f"Claude Code executable failed: {claude_path}")

    version_output = result.stdout.strip()
    # Expected format: "Claude Code 2.1.218"
    if "2.1.218" not in version_output:
        raise ValueError(f"Claude Code version 2.1.218 required, got: {version_output}")

    return str(claude_path), version_output


def build_claude_command(
    claude_path: Path,
    workspace: Path,
    plugin_dir: Path,
    settings_path: Path,
    prompt: str,
    with_skill: bool,
) -> list[str]:
    """Build the Claude Code command for one configuration."""
    cmd = [
        str(claude_path),
        "--print",
        "--verbose",
        "--output-format", "stream-json",
        "--no-session-persistence",
        "--strict-mcp-config",
        "--mcp-config", '{"mcpServers":{}}',
        "--permission-mode", EXPECTED_PERMISSION_MODE,
        "--model", EXPECTED_MODEL,
        "--effort", "low",
        "--setting-sources", "project",
        "--settings", str(settings_path),
        "--plugin-dir", str(plugin_dir),
    ]

    # Add tools based on configuration
    tools = POSITIVE_TOOLS if with_skill else BASELINE_TOOLS
    for tool in tools:
        cmd.extend(["--allow-tool", tool])

    # Add the prompt
    cmd.append("--")
    cmd.append(prompt)

    return cmd


def parse_stream_json(stdout: str) -> list[dict[str, Any]]:
    """Parse Claude Code stream-json output into events."""
    events = []
    for line_number, line in enumerate(stdout.splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
            events.append(event)
        except json.JSONDecodeError:
            # Treat malformed non-empty lines as executor errors
            raise ValueError(f"Malformed JSONL at line {line_number}: {line[:100]}")
    return events


def validate_required_events(events: list[dict[str, Any]], with_skill: bool, skill_name: str) -> tuple[bool, list[str]]:
    """Validate required event shapes and content."""
    errors = []

    # Find system.init event
    init_event = None
    for event in events:
        if event.get("type") == "system" and event.get("subtype") == "init":
            init_event = event
            break

    if not init_event:
        errors.append("Missing system.init event")
        return False, errors

    # Validate init event fields
    if init_event.get("model") != EXPECTED_MODEL:
        errors.append(f"Wrong model: {init_event.get('model')} != {EXPECTED_MODEL}")

    if init_event.get("permissionMode") != EXPECTED_PERMISSION_MODE:
        errors.append(f"Wrong permission mode: {init_event.get('permissionMode')}")

    if init_event.get("mcp_servers") != EXPECTED_MCP_SERVERS:
        errors.append(f"Non-empty MCP servers: {init_event.get('mcp_servers')}")

    # Validate tools
    tools = init_event.get("tools", [])
    expected_tools = POSITIVE_TOOLS if with_skill else BASELINE_TOOLS
    if tools != expected_tools:
        errors.append(f"Wrong tools: {tools} != {expected_tools}")

    # Validate skills
    skills = init_event.get("skills", [])
    if with_skill:
        # Should contain target skill and doctor
        skill_names = [s.split(":")[0] if ":" in s else s for s in skills]
        if skill_name not in skill_names:
            errors.append(f"Target skill missing from: {skills}")
        if "doctor" not in skills:
            errors.append(f"Doctor skill missing from: {skills}")
    else:
        # Should only contain doctor
        if skills != ["doctor"]:
            errors.append(f"Baseline skills should only be doctor: {skills}")

    # Validate plugin
    plugins = init_event.get("plugins", [])
    expected_plugin = SESSION_PLUGIN_NAME if with_skill else "d7y-eval-control"
    plugin_found = False
    for plugin in plugins:
        if plugin.get("name") == expected_plugin:
            plugin_found = True
            break
    if not plugin_found:
        errors.append(f"Expected plugin {expected_plugin} not found")

    # Find result event
    result_event = None
    for event in events:
        if event.get("type") == "result":
            result_event = event
            break

    if not result_event:
        errors.append("Missing result event")
        return False, errors

    # Validate result event structure
    if "is_error" not in result_event:
        errors.append("Result event missing is_error field")

    return len(errors) == 0, errors


def check_skill_invocation(events: list[dict[str, Any]], skill_name: str) -> tuple[bool, str]:
    """Check if the target skill was invoked."""
    target_invoked = False
    evidence = "No target Skill invocation found"

    for event in events:
        if event.get("type") == "assistant":
            message = event.get("message", {})
            content = message.get("content", [])
            for item in content:
                if item.get("type") == "tool_use":
                    if item.get("name") == "Skill":
                        skill_input = item.get("input", {})
                        invoked_skill = skill_input.get("skill", "")
                        # Check exact match for namespaced target
                        if invoked_skill == skill_name or invoked_skill.startswith(f"{skill_name}:"):
                            target_invoked = True
                            evidence = f"Found target Skill invocation: {invoked_skill}"
                        elif invoked_skill == "list":
                            # Baseline fixture's Skill(list) should not count
                            pass
                        elif invoked_skill:
                            evidence = f"Found non-target Skill invocation: {invoked_skill}"

    return target_invoked, evidence


def run_arm(
    config: EvalConfig,
    workspace: Path,
    prompt: str,
    with_skill: bool,
    d7y_install: Path,
    process_start_dir: Path,
) -> RunResult:
    """Run one arm of the eval (with-skill or baseline)."""
    config_name = "with-skill" if with_skill else "baseline"
    result = RunResult(config=config_name, success=False)

    if config.dry_run:
        result.success = True
        result.metadata["dry_run"] = True
        return result

    # Create workspace setup
    if with_skill:
        plugin_dir = create_session_plugin(workspace, config.skill_name, True, config.source_repo, config.commit)
    else:
        plugin_dir = create_control_plugin(workspace)
    settings_path = create_settings_file(workspace)

    # Build environment
    try:
        env = build_scrubbed_env(config.source_repo, workspace, plugin_dir, settings_path, d7y_install)
    except ValueError as e:
        result.stderr = f"Environment build failed: {e}"
        return result

    # Verify Claude Code
    try:
        claude_path, version = verify_executable(config.claude_path)
    except ValueError as e:
        result.stderr = f"Claude Code verification failed: {e}"
        return result

    # Build command
    cmd = build_claude_command(
        config.claude_path,
        workspace,
        plugin_dir,
        settings_path,
        prompt,
        with_skill,
    )

    # Record metadata
    result.metadata["command"] = " ".join(cmd)
    result.metadata["claude_path"] = claude_path
    result.metadata["claude_version"] = version
    result.metadata["workspace"] = str(workspace)
    result.metadata["with_skill"] = with_skill
    result.metadata["env_source"] = env.get("__D7Y_ENV_SOURCE", "unknown")
    result.metadata["env_keys"] = env.get("__D7Y_ENV_KEYS", "")

    # Execute with timeout
    start_time = time.monotonic()
    try:
        process = subprocess.Popen(
            cmd,
            cwd=process_start_dir,  # Run from separate process start directory
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,  # Process group for timeout
        )

        try:
            stdout, stderr = process.communicate(timeout=DEFAULT_TIMEOUT_SECONDS)
            result.stdout = stdout
            result.stderr = stderr
            result.exit_code = process.returncode
            result.duration_seconds = time.monotonic() - start_time

            # Parse events
            try:
                result.events = parse_stream_json(stdout)
            except ValueError as e:
                result.stderr = f"Event parsing failed: {e}"
                result.success = False
                return result

            # Validate events
            valid, errors = validate_required_events(
                result.events,
                with_skill,
                config.skill_name,
            )
            result.success = valid and process.returncode == 0
            result.metadata["validation_errors"] = errors

        except subprocess.TimeoutExpired:
            # Escalate to process group termination
            try:
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                time.sleep(ESCALATION_SECONDS)
                # Try to reap the process group
                try:
                    process.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    # Force kill if still running
                    os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                    process.wait(timeout=1)
            except (ProcessLookupError, OSError):
                pass  # Process already terminated

            result.timed_out = True
            result.stderr = f"Timeout after {DEFAULT_TIMEOUT_SECONDS}s"
            result.success = False

    except Exception as e:
        result.stderr = f"Execution failed: {e}"
        result.duration_seconds = time.monotonic() - start_time
        result.success = False

    return result


def run_deterministic_checks(
    case: dict[str, Any],
    with_skill_result: RunResult,
    baseline_result: RunResult,
    skill_name: str,
) -> dict[str, Any]:
    """Run deterministic checks on the paired results."""
    checks = {
        "pair_validity": {"status": CheckResult.PENDING.value, "errors": []},
        "treatment_checks": {"status": CheckResult.PENDING.value, "errors": []},
        "with_skill_assertions": [],
        "baseline_observations": [],
    }

    # Pair validity checks
    pair_errors = []

    # Check both arms succeeded
    if not with_skill_result.success:
        pair_errors.append("With-skill arm failed")
    if not baseline_result.success:
        pair_errors.append("Baseline arm failed")

    if pair_errors:
        checks["pair_validity"]["status"] = CheckResult.FAIL.value
        checks["pair_validity"]["errors"] = pair_errors
    else:
        checks["pair_validity"]["status"] = CheckResult.PASS.value

    # Treatment checks
    treatment_errors = []

    # Check with-skill has target skill
    with_skill_events = with_skill_result.events
    target_found = False
    for event in with_skill_events:
        if event.get("type") == "system" and event.get("subtype") == "init":
            skills = event.get("skills", [])
            skill_names = [s.split(":")[0] if ":" in s else s for s in skills]
            if skill_name in skill_names:
                target_found = True
                break

    if not target_found:
        treatment_errors.append("Target skill not in with-skill init event")

    # Check baseline does not have target skill
    baseline_events = baseline_result.events
    target_in_baseline = False
    for event in baseline_events:
        if event.get("type") == "system" and event.get("subtype") == "init":
            skills = event.get("skills", [])
            skill_names = [s.split(":")[0] if ":" in s else s for s in skills]
            if skill_name in skill_names:
                target_in_baseline = True
                break

    if target_in_baseline:
        treatment_errors.append("Target skill present in baseline init event")

    if treatment_errors:
        checks["treatment_checks"]["status"] = CheckResult.FAIL.value
        checks["treatment_checks"]["errors"] = treatment_errors
    else:
        checks["treatment_checks"]["status"] = CheckResult.PASS.value

    # Process with-skill assertions
    for assertion in case.get("assertions", []):
        assertion_id = assertion.get("id", "unknown")
        dimension = assertion.get("dimension", "unknown")
        kind = assertion.get("kind", "unknown")
        required = assertion.get("required", False)
        description = assertion.get("description", "")

        result = {
            "id": assertion_id,
            "dimension": dimension,
            "kind": kind,
            "required": required,
            "description": description,
            "status": CheckResult.UNGRADABLE.value,
            "evidence": "Not yet implemented",
        }

        # Handle invocation checks
        if dimension == "invocation" and kind == "deterministic":
            should_trigger = case.get("should_trigger", True)
            invoked, evidence = check_skill_invocation(
                with_skill_result.events,
                skill_name,
            )
            if required and should_trigger and invoked:
                result["status"] = CheckResult.PASS.value
                result["evidence"] = evidence
            elif required and not should_trigger and not invoked:
                result["status"] = CheckResult.PASS.value
                result["evidence"] = evidence
            else:
                result["status"] = CheckResult.FAIL.value
                result["evidence"] = evidence

        checks["with_skill_assertions"].append(result)

    # Process baseline observations (simplified)
    checks["baseline_observations"] = [{
        "type": "exit_code",
        "value": baseline_result.exit_code,
        "observation": f"Baseline exited with code {baseline_result.exit_code}",
    }]

    return checks


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-repo", type=Path, default=Path.cwd(), help="Source repository path")
    parser.add_argument("--commit", type=str, help="Git commit to use")
    parser.add_argument("--suite", type=Path, required=True, help="Path to evals.json suite")
    parser.add_argument("--case", type=str, required=True, help="Case ID to run")
    parser.add_argument("--output", type=Path, required=True, help="Output directory")
    parser.add_argument("--claude", type=Path, help="Path to Claude Code executable")
    parser.add_argument("--dry-run", action="store_true", help="Dry run: validate setup without execution")

    args = parser.parse_args()

    # Load suite and case
    suite = load_suite(args.suite)
    case = find_case(suite, args.case)
    skill_name = suite.get("skill_name", args.suite.parent.parent.name)

    # Determine commit
    commit = args.commit
    if not commit:
        # Use current HEAD
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=args.source_repo,
            capture_output=True,
            text=True,
            check=True,
        )
        commit = result.stdout.strip()

    # Resolve and verify commit
    try:
        commit = resolve_commit(args.source_repo, commit)
        verify_commit_exists(args.source_repo, commit)
    except ValueError as e:
        print(f"Commit resolution failed: {e}", file=sys.stderr)
        return 1

    # Verify output root is separate from source
    try:
        verify_output_root(args.output, args.source_repo)
    except ValueError as e:
        print(f"Output root validation failed: {e}", file=sys.stderr)
        return 1

    # Create configuration
    config = EvalConfig(
        source_repo=args.source_repo,
        commit=commit,
        suite_path=args.suite,
        case_id=args.case,
        output_dir=args.output,
        skill_name=skill_name,
        claude_path=args.claude,
        dry_run=args.dry_run,
    )

    # Create output directory
    args.output.mkdir(parents=True, exist_ok=True)

    # Create workspaces
    workspace_base = args.output / "workspaces"
    workspace_base.mkdir(parents=True, exist_ok=True)

    with_skill_workspace = create_isolated_workspace(workspace_base, "with-skill", args.case)
    baseline_workspace = create_isolated_workspace(workspace_base, "baseline", args.case)

    # Create D7Y capability installation
    try:
        d7y_install = create_d7y_capability_installation(args.source_repo, commit, args.output)
    except ValueError as e:
        print(f"D7Y capability installation failed: {e}", file=sys.stderr)
        return 1

    # Create process start directory (separate from workspaces)
    process_start_dir = args.output / "process-start"
    process_start_dir.mkdir(parents=True, exist_ok=True)

    # Get source status before staging
    source_status_before = get_source_status(args.source_repo)

    # Stage workspace seeds
    try:
        with_skill_objects = stage_workspace_seed(with_skill_workspace, args.suite, case, args.source_repo, commit)
        baseline_objects = stage_workspace_seed(baseline_workspace, args.suite, case, args.source_repo, commit)
    except ValueError as e:
        print(f"Workspace staging failed: {e}", file=sys.stderr)
        return 1

    # Get source status after staging
    source_status_after = get_source_status(args.source_repo)
    if source_status_before != source_status_after:
        print("Source repository modified during staging", file=sys.stderr)
        return 1

    # Verify isolation
    try:
        verify_isolation(with_skill_workspace, args.source_repo)
        verify_isolation(baseline_workspace, args.source_repo)
        verify_no_control_collisions(with_skill_workspace)
        verify_no_control_collisions(baseline_workspace)
    except ValueError as e:
        print(f"Isolation verification failed: {e}", file=sys.stderr)
        return 1

    # Record selected objects and manifest
    manifest = {
        "source_repo": str(args.source_repo),
        "commit": commit,
        "case_id": args.case,
        "skill_name": skill_name,
        "with_skill_workspace": str(with_skill_workspace),
        "baseline_workspace": str(baseline_workspace),
        "d7y_install": str(d7y_install),
        "process_start_dir": str(process_start_dir),
        "with_skill_objects": with_skill_objects,
        "baseline_objects": baseline_objects,
        "source_status_before": source_status_before,
        "source_status_after": source_status_after,
    }

    # Report dry-run status
    if args.dry_run:
        print(f"Dry run for case {args.case} of skill {skill_name}")
        print(f"  Commit: {commit}")
        print(f"  With-skill workspace: {with_skill_workspace}")
        print(f"  Baseline workspace: {baseline_workspace}")
        print(f"  D7Y installation: {d7y_install}")
        print(f"  Process start directory: {process_start_dir}")
        print(f"  Selected objects: {len(with_skill_objects)}")
        print(f"  Prompt: {case.get('prompt', '')[:100]}...")
        print("Dry run complete: setup validated, no execution performed")

        # Write manifest for inspection
        manifest_path = args.output / "dry-run-manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        print(f"Manifest written to {manifest_path}")
        return 0

    # Run with-skill arm
    print(f"Running with-skill arm for {args.case}...")
    with_skill_result = run_arm(config, with_skill_workspace, case.get("prompt", ""), True, d7y_install, process_start_dir)

    # Run baseline arm
    print(f"Running baseline arm for {args.case}...")
    baseline_result = run_arm(config, baseline_workspace, case.get("prompt", ""), False, d7y_install, process_start_dir)

    # Run deterministic checks
    checks = run_deterministic_checks(case, with_skill_result, baseline_result, skill_name)

    # Write results
    results = {
        "case_id": args.case,
        "skill_name": skill_name,
        "commit": commit,
        "manifest": manifest,
        "with_skill": {
            "success": with_skill_result.success,
            "exit_code": with_skill_result.exit_code,
            "duration_seconds": with_skill_result.duration_seconds,
            "metadata": with_skill_result.metadata,
            "event_count": len(with_skill_result.events),
            "timed_out": with_skill_result.timed_out,
        },
        "baseline": {
            "success": baseline_result.success,
            "exit_code": baseline_result.exit_code,
            "duration_seconds": baseline_result.duration_seconds,
            "metadata": baseline_result.metadata,
            "event_count": len(baseline_result.events),
            "timed_out": baseline_result.timed_out,
        },
        "checks": checks,
    }

    results_path = args.output / f"{args.case}-results.json"
    results_path.write_text(json.dumps(results, indent=2), encoding="utf-8")

    print(f"Results written to {results_path}")
    print(f"Pair validity: {checks['pair_validity']['status']}")
    print(f"Treatment checks: {checks['treatment_checks']['status']}")

    return 0 if with_skill_result.success and baseline_result.success else 1


if __name__ == "__main__":
    raise SystemExit(main())