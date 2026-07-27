#!/usr/bin/env python3
"""Tests for the minimal D7Y eval runner.

These tests verify safe workspace handling, runtime-state separation,
target-skill treatment isolation, and safe failure on malformed executor output.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

# Import the runner module
sys.path.insert(0, str(Path(__file__).parent))
from run_eval import (
    EvalConfig,
    RunResult,
    load_suite,
    find_case,
    resolve_git_object,
    verify_commit,
    create_isolated_workspace,
    create_session_plugin,
    build_scrubbed_env,
    verify_isolation,
    parse_stream_json,
    validate_required_events,
    check_skill_invocation,
    run_deterministic_checks,
)


class FakeClaudeCode:
    """A fake Claude Code executable for testing."""

    def __init__(self, temp_dir: Path):
        self.temp_dir = temp_dir
        self.executable_path = temp_dir / "fake-claude"
        self.invocation_log = temp_dir / "invocations.jsonl"
        self._create_fake_executable()

    def _create_fake_executable(self):
        """Create a fake Claude Code executable that logs invocations."""
        script = f"""#!/usr/bin/env python3
import json
import sys
import os
from pathlib import Path

invocation_log = Path("{self.invocation_log}")
invocation_count = 0

if invocation_log.exists():
    for line in invocation_log.read_text().splitlines():
        if line.strip():
            invocation_count += 1

# Log invocation
invocation_data = {{
    "invocation": invocation_count + 1,
    "args": sys.argv[1:],
    "env": {{k: v for k, v in os.environ.items() if k not in ["PATH", "HOME", "USER", "LANG"]}},
}}

with open(invocation_log, "a") as f:
    f.write(json.dumps(invocation_data) + "\\n")

# Emit minimal valid stream-json output
events = [
    {{"type": "system", "subtype": "init", "session_id": f"fixture-session-{{invocation_count}}", "tools": ["Skill", "Read", "Write", "Edit", "Bash"], "model": "claude-sonnet-5", "skills": ["doctor"], "plugins": [{{"name": "d7y-eval-session", "path": "/eval/plugin", "source": "d7y-eval-session@inline", "version": "0.0.1"}}], "mcp_servers": [], "permissionMode": "dontAsk"}},
    {{"type": "result", "subtype": "success", "result": "Fake execution complete", "is_error": False, "num_turns": 1, "permission_denials": [], "modelUsage": {{"claude-sonnet-5": {{"provider": "firstParty", "canonicalModel": "claude-sonnet-5"}}}}}}
]

for event in events:
    print(json.dumps(event))

sys.exit(0)
"""
        self.executable_path.write_text(script)
        self.executable_path.chmod(0o755)

    def get_invocations(self) -> list[dict]:
        """Get logged invocations."""
        invocations = []
        if self.invocation_log.exists():
            for line in self.invocation_log.read_text().splitlines():
                if line.strip():
                    try:
                        invocations.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
        return invocations

    def create_with_skill_response(self, skill_name: str):
        """Create a fake with-skill response."""
        # This would be expanded for more sophisticated testing
        pass

    def create_baseline_response(self):
        """Create a fake baseline response."""
        # This would be expanded for more sophisticated testing
        pass


class TestEvalLoading(unittest.TestCase):
    """Test suite and case loading."""

    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.suite_path = self.temp_dir / "evals.json"
        self.valid_suite = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "schema_version": 1,
            "skill_name": "test-skill",
            "evals": [
                {
                    "id": "test-case",
                    "prompt": "Test prompt",
                    "should_trigger": True,
                    "expected_output": "Test output",
                    "files": [],
                    "assertions": [
                        {
                            "id": "test-assertion",
                            "dimension": "invocation",
                            "kind": "deterministic",
                            "required": True,
                            "description": "Test invocation check",
                        }
                    ],
                }
            ],
        }
        self.suite_path.write_text(json.dumps(self.valid_suite))

    def tearDown(self):
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_load_valid_suite(self):
        """Test loading a valid suite."""
        suite = load_suite(self.suite_path)
        self.assertEqual(suite["skill_name"], "test-skill")
        self.assertEqual(len(suite["evals"]), 1)

    def test_load_invalid_suite(self):
        """Test loading an invalid suite fails."""
        invalid_path = self.temp_dir / "invalid.json"
        invalid_path.write_text("not json")
        with self.assertRaises(ValueError):
            load_suite(invalid_path)

    def test_find_case(self):
        """Test finding a case by ID."""
        suite = load_suite(self.suite_path)
        case = find_case(suite, "test-case")
        self.assertEqual(case["id"], "test-case")

    def test_find_missing_case(self):
        """Test finding a missing case fails."""
        suite = load_suite(self.suite_path)
        with self.assertRaises(ValueError):
            find_case(suite, "missing-case")


class TestWorkspaceIsolation(unittest.TestCase):
    """Test workspace isolation and safety checks."""

    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.source_repo = Path(tempfile.mkdtemp())
        # Initialize a fake git repo
        subprocess.run(["git", "init"], cwd=self.source_repo, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=self.source_repo, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=self.source_repo, capture_output=True)

        # Create a minimal commit
        (self.source_repo / "test.txt").write_text("test")
        subprocess.run(["git", "add", "test.txt"], cwd=self.source_repo, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=self.source_repo, capture_output=True)

    def tearDown(self):
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
        if self.source_repo.exists():
            shutil.rmtree(self.source_repo)

    def test_create_isolated_workspace(self):
        """Test creating isolated workspaces."""
        workspace = create_isolated_workspace(self.temp_dir, "with-skill", "test-case")
        self.assertTrue(workspace.exists())
        self.assertTrue(workspace.is_dir())

    def test_verify_isolation_passes_clean_workspace(self):
        """Test isolation verification passes for clean workspace."""
        workspace = self.temp_dir / "clean-workspace"
        workspace.mkdir()
        # Should not raise
        verify_isolation(workspace, self.source_repo)

    def test_verify_isolation_fails_with_eval_definitions(self):
        """Test isolation verification fails with eval definitions."""
        workspace = self.temp_dir / "dirty-workspace"
        workspace.mkdir()
        (workspace / "evals.json").write_text("{}")

        with self.assertRaises(ValueError) as context:
            verify_isolation(workspace, self.source_repo)
        self.assertIn("eval definition", str(context.exception))

    def test_verify_isolation_fails_with_graders(self):
        """Test isolation verification fails with graders."""
        workspace = self.temp_dir / "grader-workspace"
        workspace.mkdir()
        (workspace / "graders").mkdir()

        with self.assertRaises(ValueError) as context:
            verify_isolation(workspace, self.source_repo)
        self.assertIn("graders", str(context.exception))

    def test_build_scrubbed_env_rejects_path_leaks(self):
        """Test environment scrubbing rejects path leaks."""
        workspace = self.temp_dir / "workspace"
        workspace.mkdir()
        plugin_dir = workspace / "plugin"
        plugin_dir.mkdir()
        settings_path = workspace / "settings.json"
        settings_path.write_text("{}")

        # Create environment with leaked paths
        os.environ["TEST_VAR"] = f"leaked={self.source_repo}"

        with self.assertRaises(ValueError) as context:
            build_scrubbed_env(self.source_repo, workspace, plugin_dir, settings_path)
        self.assertIn("Environment key", str(context.exception))


class TestEventParsing(unittest.TestCase):
    """Test event parsing and validation."""

    def test_parse_stream_json_valid(self):
        """Test parsing valid stream-json."""
        stdout = '{"type": "system", "subtype": "init"}\n{"type": "result"}'
        events = parse_stream_json(stdout)
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0]["type"], "system")
        self.assertEqual(events[1]["type"], "result")

    def test_parse_stream_json_malformed(self):
        """Test parsing malformed stream-json skips bad lines."""
        stdout = '{"type": "system"}\ninvalid line\n{"type": "result"}'
        events = parse_stream_json(stdout)
        self.assertEqual(len(events), 2)  # Skips malformed line

    def test_validate_required_events_missing_init(self):
        """Test validation fails without init event."""
        events = [{"type": "result"}]
        valid, errors = validate_required_events(events, True, "test-skill")
        self.assertFalse(valid)
        self.assertIn("Missing system.init event", errors)

    def test_validate_required_events_wrong_model(self):
        """Test validation fails with wrong model."""
        events = [
            {"type": "system", "subtype": "init", "model": "wrong-model", "tools": ["Skill"], "skills": ["doctor"], "mcp_servers": [], "permissionMode": "dontAsk"},
            {"type": "result"}
        ]
        valid, errors = validate_required_events(events, True, "test-skill")
        self.assertFalse(valid)
        self.assertTrue(any("Wrong model" in e for e in errors))

    def test_check_skill_invocation_positive(self):
        """Test skill invocation detection for positive case."""
        events = [
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "Skill",
                            "input": {"skill": "test-skill:invoke"}
                        }
                    ]
                }
            }
        ]
        invoked, evidence = check_skill_invocation(events, "test-skill")
        self.assertTrue(invoked)
        self.assertIn("test-skill", evidence)

    def test_check_skill_invocation_negative(self):
        """Test skill invocation detection for negative case."""
        events = [
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "text",
                            "text": "No skill used"
                        }
                    ]
                }
            }
        ]
        invoked, evidence = check_skill_invocation(events, "test-skill")
        self.assertFalse(invoked)
        self.assertIn("No target Skill invocation", evidence)


class TestDeterministicChecks(unittest.TestCase):
    """Test deterministic check execution."""

    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.case = {
            "id": "test-case",
            "prompt": "Test prompt",
            "should_trigger": True,
            "assertions": [
                {
                    "id": "invocation-check",
                    "dimension": "invocation",
                    "kind": "deterministic",
                    "required": True,
                    "description": "Should invoke skill",
                }
            ],
        }

    def tearDown(self):
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_pair_validity_both_succeed(self):
        """Test pair validity passes when both arms succeed."""
        with_skill_result = RunResult("with-skill", success=True)
        baseline_result = RunResult("baseline", success=True)

        checks = run_deterministic_checks(self.case, with_skill_result, baseline_result)
        self.assertEqual(checks["pair_validity"]["status"], "pass")

    def test_pair_validity_with_skill_fails(self):
        """Test pair validity fails when with-skill fails."""
        with_skill_result = RunResult("with-skill", success=False)
        baseline_result = RunResult("baseline", success=True)

        checks = run_deterministic_checks(self.case, with_skill_result, baseline_result)
        self.assertEqual(checks["pair_validity"]["status"], "fail")

    def test_invocation_assertion_pass(self):
        """Test invocation assertion passes when skill invoked."""
        with_skill_result = RunResult("with-skill", success=True)
        with_skill_result.events = [
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "Skill",
                            "input": {"skill": "test-skill:invoke"}
                        }
                    ]
                }
            }
        ]

        baseline_result = RunResult("baseline", success=True)
        baseline_result.events = []

        checks = run_deterministic_checks(self.case, with_skill_result, baseline_result)
        invocation_check = next(c for c in checks["with_skill_assertions"] if c["id"] == "invocation-check")
        self.assertEqual(invocation_check["status"], "pass")


class TestFakeClaudeExecution(unittest.TestCase):
    """Test execution with fake Claude Code."""

    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.fake_claude = FakeClaudeCode(self.temp_dir)

        # Create a minimal suite
        self.suite_path = self.temp_dir / "evals.json"
        suite = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "schema_version": 1,
            "skill_name": "test-skill",
            "evals": [
                {
                    "id": "fake-test",
                    "prompt": "Test with fake Claude",
                    "should_trigger": True,
                    "expected_output": "Success",
                    "files": [],
                    "assertions": [],
                }
            ],
        }
        self.suite_path.write_text(json.dumps(suite))

    def tearDown(self):
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_fake_claude_execution(self):
        """Test that fake Claude executes successfully."""
        # Run the fake Claude
        result = subprocess.run(
            [str(self.fake_claude.executable_path)],
            capture_output=True,
            text=True,
            timeout=5,
        )

        self.assertEqual(result.returncode, 0)
        self.assertIn("system", result.stdout)

    def test_fake_claude_logs_invocations(self):
        """Test that fake Claude logs invocations."""
        # Run the fake Claude twice
        subprocess.run([str(self.fake_claude.executable_path)], capture_output=True)
        subprocess.run([str(self.fake_claude.executable_path)], capture_output=True)

        invocations = self.fake_claude.get_invocations()
        self.assertEqual(len(invocations), 2)


if __name__ == "__main__":
    # Run tests
    unittest.main()
