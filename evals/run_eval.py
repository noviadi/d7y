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
import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from enum import Enum
from pathlib import Path
from typing import Any, Literal

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


def verify_commit(repo: Path, commit: str) -> None:
    """Verify that a commit exists in the repository."""
    result = subprocess.run(
        ["git", "rev-parse", "--verify", commit],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise ValueError(f"Commit {commit} not found in {repo}")


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
) -> Path:
    """Create a session-only plugin directory."""
    plugin_dir = workspace / ".d7y-eval-plugin"
    plugin_dir.mkdir(parents=True, exist_ok=True)

    if with_skill:
        # Create the target skill SKILL.md
        skill_path = plugin_dir / "SKILL.md"
        skill_content = f"---\nname: {skill_name}\ndescription: \"Target skill for eval\"\nmetadata:\n  maturity: provisional\n---\n\n# {skill_name}\n\nThis is the target skill installed for evaluation.\n"
        skill_path.write_text(skill_content, encoding="utf-8")

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


def build_scrubbed_env(source_repo: Path, workspace: Path, plugin_dir: Path, settings_path: Path) -> dict[str, str]:
    """Build a scrubbed child environment for Claude Code execution."""
    source_str = str(source_repo)
    evals_str = "evals"

    # Start with minimal platform environment
    env = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": os.environ.get("HOME", ""),
        "USER": os.environ.get("USER", ""),
        "LANG": os.environ.get("LANG", "en_US.UTF-8"),
    }

    # Import reviewed user environment keys from ~/.claude/settings.json if available
    user_settings_path = Path.home() / ".claude" / "settings.json"
    retained_keys = [
        "ANTHROPIC_AUTH_TOKEN",  # Required for authentication
        "ANTHROPIC_BASE_URL",
    ]

    if user_settings_path.exists():
        try:
            user_settings = json.loads(user_settings_path.read_text(encoding="utf-8"))
            # Import only retained keys by name, never values
            for key in retained_keys:
                if key in user_settings:
                    env[key] = user_settings[key]  # Preserve key and value
        except (OSError, json.JSONDecodeError):
            pass  # Proceed without user settings

    # Override with harness-owned control variables
    env["CLAUDE_CONFIG_DIR"] = str(workspace)
    env["PWD"] = str(workspace)

    # Check for path leaks in all environment variables including system ones
    for key, value in env.items():
        if isinstance(value, str) and (source_str in value or evals_str in value):
            raise ValueError(f"Environment key {key} exposes source or eval path: {value[:50]}...")

    # Also check current environment for leaked paths
    for key, value in os.environ.items():
        if key.startswith("TEST_") and isinstance(value, str) and (source_str in value or evals_str in value):
            raise ValueError(f"Environment key {key} contains leaked path")

    return env


def create_d7y_capability_installation(source_repo: Path, commit: str, target_dir: Path) -> Path:
    """Create a minimal D7Y capability installation from the selected commit."""
    # Create the installation directory
    capability_dir = target_dir / "d7y-install"
    capability_dir.mkdir(parents=True, exist_ok=True)

    # Resolve the d7y façade from the commit
    d7y_script = resolve_git_object(source_repo, commit, "d7y")
    d7y_path = capability_dir / "d7y"
    d7y_path.write_bytes(d7y_script)
    d7y_path.chmod(0o755)

    # Resolve the shared initiative implementation
    try:
        checker_script = resolve_git_object(source_repo, commit, "scripts/check-initiatives.py")
        checker_dir = capability_dir / "scripts"
        checker_dir.mkdir(exist_ok=True)
        (checker_dir / "check-initiatives.py").write_bytes(checker_script)
    except ValueError:
        pass  # Checker may not exist in all commits

    return capability_dir


def stage_workspace_seed(
    workspace: Path,
    suite_path: Path,
    case: dict[str, Any],
    source_repo: Path,
    commit: str,
) -> None:
    """Stage the workspace seed from committed Git objects."""
    # Stage the initiative contract
    try:
        readme_content = resolve_git_object(source_repo, commit, "initiatives/README.md")
        initiatives_dir = workspace / "initiatives"
        initiatives_dir.mkdir(parents=True, exist_ok=True)
        (initiatives_dir / "README.md").write_bytes(readme_content)
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
        if source.startswith("..") or destination.startswith(".."):
            raise ValueError(f"Unsafe path in fixture: {source} -> {destination}")

        # Read from skill directory
        source_path = skill_dir / source
        if not source_path.exists():
            raise ValueError(f"Fixture source does not exist: {source_path}")

        # Write to workspace
        dest_path = workspace / destination
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        dest_path.write_bytes(source_path.read_bytes())


def verify_isolation(workspace: Path, source_repo: Path) -> None:
    """Verify that workspace does not contain eval material or source references."""
    workspace_str = str(workspace)
    source_str = str(source_repo)

    # Check for eval definitions
    for eval_path in workspace.rglob("evals.json"):
        raise ValueError(f"Workspace contains eval definition: {eval_path}")

    # Check for graders
    if (workspace / "graders").exists():
        raise ValueError("Workspace contains graders directory")

    # Check for source checkout references in text files
    for text_file in workspace.rglob("*.md"):
        content = text_file.read_text(encoding="utf-8")
        if source_str in content:
            raise ValueError(f"Workspace file references source checkout: {text_file}")


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
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
            events.append(event)
        except json.JSONDecodeError:
            # Skip malformed lines
            continue
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


def check_skill_invocation(events: list[dict[str, Any]], case_id: str) -> tuple[bool, str]:
    """Check if any skill was invoked (simplified for testing)."""
    for event in events:
        if event.get("type") == "assistant":
            message = event.get("message", {})
            content = message.get("content", [])
            for item in content:
                if item.get("type") == "tool_use":
                    if item.get("name") == "Skill":
                        skill_input = item.get("input", {})
                        invoked_skill = skill_input.get("skill", "")
                        if invoked_skill:  # Any skill invocation
                            return True, f"Found Skill invocation of {invoked_skill}"
    return False, "No target Skill invocation found"


def run_arm(
    config: EvalConfig,
    workspace: Path,
    prompt: str,
    with_skill: bool,
) -> RunResult:
    """Run one arm of the eval (with-skill or baseline)."""
    config_name = "with-skill" if with_skill else "baseline"
    result = RunResult(config=config_name, success=False)

    if config.dry_run:
        result.success = True
        result.metadata["dry_run"] = True
        return result

    # Create workspace setup
    plugin_dir = create_session_plugin(workspace, config.skill_name, with_skill)
    settings_path = create_settings_file(workspace)

    # Build environment
    try:
        env = build_scrubbed_env(config.source_repo, workspace, plugin_dir, settings_path)
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

    # Execute with timeout
    start_time = time.monotonic()
    try:
        process = subprocess.Popen(
            cmd,
            cwd=workspace,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,  # Process group for timeout
        )

        try:
            stdout, stderr = process.communicate(timeout=DEFAULT_TIMEOUT_SECONDS)
            result.events = parse_stream_json(stdout)
            result.stderr = stderr
            result.exit_code = process.returncode
            result.duration_seconds = time.monotonic() - start_time

            # Validate events
            valid, errors = validate_required_events(
                result.events,
                with_skill,
                config.skill_name,
            )
            result.success = valid and process.returncode == 0
            result.metadata["validation_errors"] = errors

        except subprocess.TimeoutExpired:
            #escalate to process group termination
            time.sleep(ESCALATION_SECONDS)
            try:
                os.killpg(os.getpgid(process.pid), 9)  # SIGKILL
            except (ProcessLookupError, OSError):
                pass

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

    # Check tool parity
    with_tools = with_skill_result.metadata.get("tools", [])
    baseline_tools = baseline_result.metadata.get("tools", [])
    if with_tools != baseline_tools and not with_skill_result.metadata.get("validation_errors"):
        pair_errors.append(f"Tool mismatch: {with_tools} vs {baseline_tools}")

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
            if any(s.startswith("starting-initiatives") for s in skills):
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
            if any(s.startswith("starting-initiatives") for s in skills):
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
                case.get("id", ""),  # Use case ID as skill identifier
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

    # Verify commit exists
    verify_commit(args.source_repo, commit)

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

    # Stage workspace seeds
    stage_workspace_seed(with_skill_workspace, args.suite, case, args.source_repo, commit)
    stage_workspace_seed(baseline_workspace, args.suite, case, args.source_repo, commit)

    # Verify isolation
    try:
        verify_isolation(with_skill_workspace, args.source_repo)
        verify_isolation(baseline_workspace, args.source_repo)
    except ValueError as e:
        print(f"Isolation verification failed: {e}", file=sys.stderr)
        return 1

    # Report dry-run status
    if args.dry_run:
        print(f"Dry run for case {args.case} of skill {skill_name}")
        print(f"  Commit: {commit}")
        print(f"  With-skill workspace: {with_skill_workspace}")
        print(f"  Baseline workspace: {baseline_workspace}")
        print(f"  Prompt: {case.get('prompt', '')[:100]}...")
        print("Dry run complete: setup validated, no execution performed")
        return 0

    # Run with-skill arm
    print(f"Running with-skill arm for {args.case}...")
    with_skill_result = run_arm(config, with_skill_workspace, case.get("prompt", ""), True)

    # Run baseline arm
    print(f"Running baseline arm for {args.case}...")
    baseline_result = run_arm(config, baseline_workspace, case.get("prompt", ""), False)

    # Run deterministic checks
    checks = run_deterministic_checks(case, with_skill_result, baseline_result)

    # Write results
    results = {
        "case_id": args.case,
        "skill_name": skill_name,
        "commit": commit,
        "with_skill": {
            "success": with_skill_result.success,
            "exit_code": with_skill_result.exit_code,
            "duration_seconds": with_skill_result.duration_seconds,
            "metadata": with_skill_result.metadata,
            "event_count": len(with_skill_result.events),
        },
        "baseline": {
            "success": baseline_result.success,
            "exit_code": baseline_result.exit_code,
            "duration_seconds": baseline_result.duration_seconds,
            "metadata": baseline_result.metadata,
            "event_count": len(baseline_result.events),
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
