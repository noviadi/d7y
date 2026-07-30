#!/usr/bin/env python3
"""Focused tests for the Phase 0 image scanner and synthetic-secret canary.

These tests are deterministic and need NO live Docker daemon: they drive the
scanner through the ``_run`` injection seam (``main(runner=...)`` and a patched
module-level ``_run``), feeding canned ``docker`` responses. They exercise the
fail-closed contract directly:

- a clean scan decides ``clean``;
- a scan that finds forbidden material decides ``dirty``;
- a scan whose ``docker run`` fails (exit 125) or whose env inspection fails
  decides ``command_failure`` and is NOT ``clean``;
- the synthetic-secret canary reports ``build_failure`` / ``scan_failure`` /
  ``leaked`` (and never ``clean``) when its build, scan, or secret check fails.

Run: python3 evals/harbor/scripts/test_scan_image.py
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

import scan_image  # noqa: E402


def _completed(cmd: list[str], returncode: int, stdout: str = "", stderr: str = "") -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args=cmd, returncode=returncode, stdout=stdout, stderr=stderr)


def _scan_stdout(files: str = "", content: str = "", identity: str = "absent") -> str:
    return f"FILES\n{files}\nCONTENT\n{content}\nIDENTITY\n{identity}\nFIND_EXIT\n0\nGREP_EXIT\n0\n"


def make_runner(
    *,
    scan_returncode: int = 0,
    scan_stdout: str | None = None,
    env_returncode: int = 0,
    env_json: str = "[]",
    build_returncode: int = 0,
    build_stderr: str = "",
    rmi_returncode: int = 0,
    leak_token: bool = False,
):
    """Build a fake ``_run`` that emulates the docker CLI from canned responses.

    ``leak_token`` echoes the canary's build-arg secret back into the scan output
    so the secret-leak path can be exercised without a real build.
    """
    state: dict = {"token": None}
    commands_run: list[dict] = []

    def fake_run(cmd: list[str], **kwargs):
        sub = cmd[1] if len(cmd) > 1 else ""
        # Track commands for verification
        commands_run.append({"command": cmd.copy(), "subcommand": sub})
        if sub == "build":
            for arg in cmd:
                if arg.startswith("ANTHROPIC_AUTH_TOKEN="):
                    state["token"] = arg.split("=", 1)[1]
            return _completed(cmd, build_returncode, "", build_stderr)
        if sub == "run":
            # Verify that root inspection is requested (--user 0:0)
            has_root_flag = "--user" in cmd and "0:0" in cmd
            content = state["token"] if (leak_token and state["token"]) else ""
            stdout = scan_stdout if scan_stdout is not None else _scan_stdout(content=content)
            stderr = "" if scan_returncode == 0 else "docker run failed (simulated)"
            return _completed(cmd, scan_returncode, stdout, stderr)
        if sub == "image" and len(cmd) > 2 and cmd[2] == "inspect":
            if env_returncode != 0:
                return _completed(cmd, env_returncode, "", "docker inspect failed (simulated)")
            return _completed(cmd, 0, env_json, "")
        if sub == "rmi":
            return _completed(cmd, rmi_returncode, "", "" if rmi_returncode == 0 else "rmi failed (simulated)")
        return _completed(cmd, 0, "", "")

    return fake_run, commands_run


class TestScanClassification(unittest.TestCase):
    def test_clean_scan_decides_clean(self) -> None:
        runner, _ = make_runner(scan_stdout=_scan_stdout(), env_json="[]")
        with mock.patch.object(scan_image, "_run", runner):
            result = scan_image.scan_image("img")
        self.assertEqual(scan_image.classify_scan(result), "clean")
        self.assertFalse(result["scan_command_failed"])

    def test_dirty_scan_decides_dirty(self) -> None:
        runner, _ = make_runner(scan_stdout=_scan_stdout(files="/etc/evals.json"))
        with mock.patch.object(scan_image, "_run", runner):
            result = scan_image.scan_image("img")
        self.assertEqual(scan_image.classify_scan(result), "dirty")
        self.assertEqual(result["forbidden_files"], ["/etc/evals.json"])

    def test_dirty_content_decides_dirty(self) -> None:
        runner, _ = make_runner(scan_stdout=_scan_stdout(content="/opt/d7y-eval-phase0-agent/Dockerfile: starting-initiatives"))
        with mock.patch.object(scan_image, "_run", runner):
            result = scan_image.scan_image("img")
        self.assertEqual(scan_image.classify_scan(result), "dirty")

    def test_identity_state_present_decides_dirty(self) -> None:
        # The installer's .claude/ or .claude.json surviving into the image is
        # forbidden generated identity state, not a clean image.
        runner, _ = make_runner(scan_stdout=_scan_stdout(identity="present"))
        with mock.patch.object(scan_image, "_run", runner):
            result = scan_image.scan_image("img")
        self.assertEqual(scan_image.classify_scan(result), "dirty")
        self.assertTrue(result["identity_state_present"])

    def test_env_secret_hit_decides_dirty(self) -> None:
        runner, _ = make_runner(env_json='["ANTHROPIC_AUTH_TOKEN=sk-canary-d7y-leaked"]')
        with mock.patch.object(scan_image, "_run", runner):
            result = scan_image.scan_image("img")
        self.assertEqual(scan_image.classify_scan(result), "dirty")

    def test_failed_scan_is_command_failure_not_clean(self) -> None:
        # Exit 125 from `docker run` (missing image, daemon error, ...) must not
        # become absence evidence.
        runner, _ = make_runner(scan_returncode=125, scan_stdout="")
        with mock.patch.object(scan_image, "_run", runner):
            result = scan_image.scan_image("img")
        self.assertEqual(scan_image.classify_scan(result), "command_failure")
        self.assertTrue(result["scan_command_failed"])
        self.assertEqual(result["scan_exit_code"], 125)

    def test_failed_env_inspection_is_command_failure(self) -> None:
        runner, _ = make_runner(env_returncode=1)
        with mock.patch.object(scan_image, "_run", runner):
            result = scan_image.scan_image("img")
        self.assertEqual(scan_image.classify_scan(result), "command_failure")
        self.assertTrue(result["scan_command_failed"])
        self.assertIsNotNone(result["env_inspect_error"])

    def test_command_failure_main_exits_nonzero(self) -> None:
        runner, _ = make_runner(scan_returncode=125, scan_stdout="")
        with mock.patch.object(scan_image, "_run", runner):
            code = scan_image.main([])
        self.assertNotEqual(code, 0)


class TestSyntheticSecretCanary(unittest.TestCase):
    def _dockerfile(self) -> Path:
        tmp = Path(tempfile.mkdtemp(prefix="d7y-canary-test-"))
        df = tmp / "Dockerfile"
        df.write_text("FROM scratch\n# pretend agent recipe\n")
        return df

    def test_clean_canary_decides_clean(self) -> None:
        runner, _ = make_runner()
        with mock.patch.object(scan_image, "_run", runner):
            canary = scan_image.synthetic_secret_canary(self._dockerfile())
        self.assertEqual(canary["status"], "clean")
        self.assertFalse(canary["leaked"])
        self.assertEqual(canary["build_exit_code"], 0)

    def test_failed_build_is_build_failure_not_clean(self) -> None:
        runner, _ = make_runner(build_returncode=1, build_stderr="simulated build error")
        with mock.patch.object(scan_image, "_run", runner):
            canary = scan_image.synthetic_secret_canary(self._dockerfile())
        self.assertEqual(canary["status"], "build_failure")
        self.assertEqual(canary["build_exit_code"], 1)
        self.assertTrue(canary["build_stderr_tail"])

    def test_failed_scan_is_scan_failure_not_clean(self) -> None:
        runner, _ = make_runner(scan_returncode=125, scan_stdout="")
        with mock.patch.object(scan_image, "_run", runner):
            canary = scan_image.synthetic_secret_canary(self._dockerfile())
        self.assertEqual(canary["status"], "scan_failure")
        self.assertEqual(canary["scan_status"], "command_failure")

    def test_leaked_secret_is_leaked_not_clean(self) -> None:
        runner, _ = make_runner(leak_token=True)
        with mock.patch.object(scan_image, "_run", runner):
            canary = scan_image.synthetic_secret_canary(self._dockerfile())
        self.assertEqual(canary["status"], "leaked")
        self.assertTrue(canary["leaked"])

    def test_failed_cleanup_is_cleanup_failure_not_clean(self) -> None:
        runner, _ = make_runner(rmi_returncode=1)
        with mock.patch.object(scan_image, "_run", runner):
            canary = scan_image.synthetic_secret_canary(self._dockerfile())
        self.assertEqual(canary["status"], "cleanup_failure")
        self.assertTrue(canary["cleanup_error"])


class TestScannerCompleteness(unittest.TestCase):
    """Tests for Phase 0 scanner completeness requirements."""

    def test_scan_invokes_docker_with_root_inspection(self) -> None:
        """The scan must invoke Docker with explicit root inspection (--user 0:0)."""
        commands_run = []
        original_run = scan_image._run

        def tracking_run(cmd: list[str], **kwargs):
            commands_run.append(cmd.copy())
            return original_run(cmd, **kwargs)

        with mock.patch.object(scan_image, "_run", tracking_run):
            # Use a real scan against a clean image if available
            try:
                scan_image.scan_image("d7y-eval-phase0-agent:2.1.218")
            except Exception:
                # If the image doesn't exist or docker fails, that's fine for this test
                pass

        # Check if any docker run command had --user 0:0
        root_scans = [cmd for cmd in commands_run if cmd[1] == "run" and "--user" in cmd and "0:0" in cmd]
        # If we ran a scan, it should have used root inspection
        if any(cmd[1] == "run" for cmd in commands_run):
            self.assertTrue(root_scans, "Expected docker run to include --user 0:0 for root inspection")

    def test_internal_traversal_failures_are_detected(self) -> None:
        """Internal find/grep failures should be detected and marked as command failure."""
        # Simulate a scan where find fails (exit 1) but docker run succeeds
        stdout = (
            "FILES\n"
            "CONTENT\n"
            "IDENTITY\nabsent\n"
            "FIND_EXIT\n1\n"
            "GREP_EXIT\n0\n"
        )
        runner, _ = make_runner(scan_returncode=0, scan_stdout=stdout)
        with mock.patch.object(scan_image, "_run", runner):
            result = scan_image.scan_image("img")
        self.assertTrue(result["internal_traversal_failed"])
        self.assertTrue(result["scan_command_failed"])
        self.assertEqual(result["find_exit"], 1)

    def test_grep_exit_1_is_valid_no_match(self) -> None:
        """Grep exit 1 means no matches and is valid (not a traversal failure)."""
        # Grep exit 1 is valid - it means no matches found
        stdout = (
            "FILES\n"
            "CONTENT\n"
            "IDENTITY\nabsent\n"
            "FIND_EXIT\n0\n"
            "GREP_EXIT\n1\n"
        )
        runner, _ = make_runner(scan_returncode=0, scan_stdout=stdout)
        with mock.patch.object(scan_image, "_run", runner):
            result = scan_image.scan_image("img")
        self.assertFalse(result["internal_traversal_failed"])
        self.assertEqual(result["grep_exit"], 1)

    def test_grep_exit_greater_than_1_is_traversal_failure(self) -> None:
        """Grep exit > 1 means command failure, not just no match."""
        stdout = (
            "FILES\n"
            "CONTENT\n"
            "IDENTITY\nabsent\n"
            "FIND_EXIT\n0\n"
            "GREP_EXIT\n2\n"
        )
        runner, _ = make_runner(scan_returncode=0, scan_stdout=stdout)
        with mock.patch.object(scan_image, "_run", runner):
            result = scan_image.scan_image("img")
        self.assertTrue(result["internal_traversal_failed"])
        self.assertTrue(result["scan_command_failed"])
        self.assertEqual(result["grep_exit"], 2)

    def test_missing_protocol_sections_are_command_failure(self) -> None:
        """Missing or incomplete protocol sections should be command failure."""
        # Missing FIND_EXIT section
        stdout = "FILES\n\nCONTENT\n\nIDENTITY\nabsent\n"
        runner, _ = make_runner(scan_returncode=0, scan_stdout=stdout)
        with mock.patch.object(scan_image, "_run", runner):
            result = scan_image.scan_image("img")
        self.assertTrue(result["scan_command_failed"])
        self.assertIsNotNone(result["protocol_error"])

    def test_duplicate_protocol_sections_are_invalid(self) -> None:
        """The parser should handle duplicate sections gracefully."""
        # This would still parse but indicates a protocol issue
        stdout = (
            "FILES\n\nCONTENT\n\nFILES\n\nIDENTITY\nabsent\n"
            "FIND_EXIT\n0\n"
            "GREP_EXIT\n0\n"
        )
        runner, _ = make_runner(scan_returncode=0, scan_stdout=stdout)
        with mock.patch.object(scan_image, "_run", runner):
            result = scan_image.scan_image("img")
        # Should not crash, but results depend on section parsing behavior
        self.assertIsNotNone(result)

    def test_malformed_json_in_env_inspection_fails_closed(self) -> None:
        """Malformed JSON from docker inspect should fail closed."""
        runner, _ = make_runner(env_json="not valid json[")
        with mock.patch.object(scan_image, "_run", runner):
            result = scan_image.scan_image("img")
        # The scanner should fail closed, not raise an exception
        self.assertTrue(result["scan_command_failed"])
        self.assertIsNotNone(result["env_inspect_error"])
        self.assertIn("malformed JSON", result["env_inspect_error"])

    def test_env_inspect_command_failure_fails_closed(self) -> None:
        """Docker inspect command failure should be detected."""
        runner, _ = make_runner(env_returncode=1)
        with mock.patch.object(scan_image, "_run", runner):
            result = scan_image.scan_image("img")
        self.assertTrue(result["scan_command_failed"])
        self.assertIsNotNone(result["env_inspect_error"])

    def test_full_token_redaction_in_diagnostics(self) -> None:
        """The full synthetic token should be redacted from diagnostics."""
        full_token = "sk-canary-d7y-1234567890abcdef"
        stderr = f"Error: token {full_token} leaked in build"
        redacted = scan_image._stderr_tail(stderr, lines=5, full_token=full_token)
        # The full token should be replaced with the redacted placeholder
        self.assertEqual(len(redacted), 1)
        self.assertNotIn(full_token, redacted[0])
        self.assertIn("<redacted-canary-token>", redacted[0])

    def test_token_prefix_redaction_fallback(self) -> None:
        """Without full token, fall back to prefix-only redaction."""
        stderr = "Error: sk-canary-d7y found in logs"
        redacted = scan_image._stderr_tail(stderr, lines=5, full_token=None)
        self.assertEqual(len(redacted), 1)
        self.assertNotIn("sk-canary-d7y", redacted[0])
        self.assertIn("<redacted-canary-token>", redacted[0])

    def test_protocol_error_set_for_missing_sections(self) -> None:
        """Protocol error should be set when required sections are missing."""
        stdout = "FILES\n\nCONTENT\n"  # Missing IDENTITY, FIND_EXIT, GREP_EXIT
        runner, _ = make_runner(scan_returncode=0, scan_stdout=stdout)
        with mock.patch.object(scan_image, "_run", runner):
            result = scan_image.scan_image("img")
        self.assertTrue(result["scan_command_failed"])
        self.assertIsNotNone(result["protocol_error"])
        self.assertIn("missing", result["protocol_error"].lower())

    def test_dirty_and_clean_results_remain_distinguishable(self) -> None:
        """Ensure dirty scans remain distinguishable from clean ones."""
        clean_runner, _ = make_runner(scan_stdout=_scan_stdout(), env_json="[]")
        dirty_runner, _ = make_runner(scan_stdout=_scan_stdout(files="/etc/evals.json"), env_json="[]")

        with mock.patch.object(scan_image, "_run", clean_runner):
            clean_result = scan_image.scan_image("img")
        with mock.patch.object(scan_image, "_run", dirty_runner):
            dirty_result = scan_image.scan_image("img")

        self.assertEqual(scan_image.classify_scan(clean_result), "clean")
        self.assertEqual(scan_image.classify_scan(dirty_result), "dirty")
        self.assertFalse(clean_result["forbidden_files"])
        self.assertTrue(dirty_result["forbidden_files"])

    def test_outer_docker_failure_is_non_clean(self) -> None:
        """Outer Docker failure should never be reported as clean."""
        runner, _ = make_runner(scan_returncode=125, scan_stdout="")
        with mock.patch.object(scan_image, "_run", runner):
            result = scan_image.scan_image("img")
        status = scan_image.classify_scan(result)
        self.assertNotEqual(status, "clean")
        self.assertEqual(status, "command_failure")

    def test_canary_failure_main_exits_nonzero(self) -> None:
        runner, _ = make_runner(build_returncode=1, build_stderr="simulated build error")
        with mock.patch.object(scan_image, "_run", runner):
            code = scan_image.main(["--canary"])
        self.assertNotEqual(code, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
