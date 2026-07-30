#!/usr/bin/env python3
"""Deterministic tests for the Phase 0 image scanner and secret canary.

All Docker responses are supplied through the module-level ``_run`` seam. The
suite must not require a Docker daemon or leave temporary directories behind.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

import scan_image  # noqa: E402


def _completed(
    cmd: list[str],
    returncode: int,
    stdout: str = "",
    stderr: str = "",
) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(
        args=cmd,
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
    )


def _scan_stdout(
    files: str = "",
    content: str = "",
    identity: str = "absent",
    find_exit: int = 0,
    grep_exit: int = 1,
) -> str:
    return (
        f"FILES\n{files}\n"
        f"CONTENT\n{content}\n"
        f"IDENTITY\n{identity}\n"
        f"FIND_EXIT\n{find_exit}\n"
        f"GREP_EXIT\n{grep_exit}\n"
    )


def make_runner(
    *,
    scan_returncode: int = 0,
    scan_stdout: str | None = None,
    scan_stderr: str = "",
    env_returncode: int = 0,
    env_json: str = "[]",
    build_returncode: int = 0,
    build_stderr: str = "",
    rmi_returncode: int = 0,
    rmi_stderr: str = "",
    leak_token: bool = False,
):
    """Return a canned Docker runner and the commands it receives."""
    state: dict[str, str | None] = {"token": None}
    commands: list[list[str]] = []

    def fake_run(cmd: list[str], **_kwargs: object) -> subprocess.CompletedProcess:
        commands.append(cmd.copy())
        subcommand = cmd[1] if len(cmd) > 1 else ""
        if subcommand == "build":
            for argument in cmd:
                if argument.startswith("ANTHROPIC_AUTH_TOKEN="):
                    state["token"] = argument.split("=", 1)[1]
            stderr = build_stderr.replace("<TOKEN>", state["token"] or "")
            return _completed(cmd, build_returncode, stderr=stderr)
        if subcommand == "run":
            content = state["token"] if leak_token and state["token"] else ""
            stdout = scan_stdout if scan_stdout is not None else _scan_stdout(content=content)
            stderr = scan_stderr or (
                "docker run failed (simulated)" if scan_returncode else ""
            )
            return _completed(cmd, scan_returncode, stdout, stderr)
        if subcommand == "image" and len(cmd) > 2 and cmd[2] == "inspect":
            if env_returncode:
                return _completed(
                    cmd,
                    env_returncode,
                    stderr="docker inspect failed (simulated)",
                )
            return _completed(cmd, 0, env_json)
        if subcommand == "rmi":
            stderr = rmi_stderr.replace("<TOKEN>", state["token"] or "")
            return _completed(cmd, rmi_returncode, stderr=stderr)
        return _completed(cmd, 0)

    return fake_run, commands


class DockerfileFixture(unittest.TestCase):
    def setUp(self) -> None:
        self._tempdir = tempfile.TemporaryDirectory(prefix="d7y-canary-test-")
        self.addCleanup(self._tempdir.cleanup)
        self.dockerfile = Path(self._tempdir.name) / "Dockerfile"
        self.dockerfile.write_text("FROM scratch\n# synthetic fixture\n", encoding="utf-8")


class TestScanClassification(unittest.TestCase):
    def _scan(self, runner) -> dict:
        with mock.patch.object(scan_image, "_run", runner):
            return scan_image.scan_image("img")

    def test_clean_scan_decides_clean(self) -> None:
        runner, _ = make_runner()
        result = self._scan(runner)
        self.assertEqual(scan_image.classify_scan(result), "clean")
        self.assertFalse(result["scan_command_failed"])

    def test_dirty_file_decides_dirty(self) -> None:
        runner, _ = make_runner(scan_stdout=_scan_stdout(files="/etc/evals.json"))
        result = self._scan(runner)
        self.assertEqual(scan_image.classify_scan(result), "dirty")
        self.assertEqual(result["forbidden_files"], ["/etc/evals.json"])

    def test_dirty_content_decides_dirty(self) -> None:
        runner, _ = make_runner(scan_stdout=_scan_stdout(content="/opt/forbidden"))
        result = self._scan(runner)
        self.assertEqual(scan_image.classify_scan(result), "dirty")

    def test_identity_present_decides_dirty(self) -> None:
        runner, _ = make_runner(scan_stdout=_scan_stdout(identity="present"))
        result = self._scan(runner)
        self.assertEqual(scan_image.classify_scan(result), "dirty")
        self.assertTrue(result["identity_state_present"])

    def test_secret_environment_reports_key_only(self) -> None:
        secret = "sk-canary-d7y-do-not-report"
        runner, _ = make_runner(
            env_json=json.dumps([f"ANTHROPIC_AUTH_TOKEN={secret}"])
        )
        result = self._scan(runner)
        self.assertEqual(scan_image.classify_scan(result), "dirty")
        self.assertEqual(result["env_secret_hits"], ["ANTHROPIC_AUTH_TOKEN"])
        self.assertEqual(result["env_token_value_hits"], ["ANTHROPIC_AUTH_TOKEN"])
        self.assertNotIn(secret, json.dumps(result))

    def test_outer_docker_failure_is_command_failure(self) -> None:
        runner, _ = make_runner(scan_returncode=125, scan_stdout="")
        result = self._scan(runner)
        self.assertEqual(scan_image.classify_scan(result), "command_failure")
        self.assertEqual(result["scan_exit_code"], 125)

    def test_find_failure_is_command_failure(self) -> None:
        runner, _ = make_runner(scan_stdout=_scan_stdout(find_exit=1, grep_exit=1))
        result = self._scan(runner)
        self.assertTrue(result["internal_traversal_failed"])
        self.assertEqual(scan_image.classify_scan(result), "command_failure")

    def test_grep_no_match_is_valid(self) -> None:
        runner, _ = make_runner(scan_stdout=_scan_stdout(grep_exit=1))
        result = self._scan(runner)
        self.assertFalse(result["internal_traversal_failed"])
        self.assertEqual(scan_image.classify_scan(result), "clean")

    def test_grep_error_is_command_failure(self) -> None:
        runner, _ = make_runner(scan_stdout=_scan_stdout(grep_exit=2))
        result = self._scan(runner)
        self.assertTrue(result["internal_traversal_failed"])
        self.assertEqual(scan_image.classify_scan(result), "command_failure")

    def test_env_command_failure_fails_closed(self) -> None:
        runner, _ = make_runner(env_returncode=1)
        result = self._scan(runner)
        self.assertEqual(scan_image.classify_scan(result), "command_failure")
        self.assertIn("docker inspect failed", result["env_inspect_error"])

    def test_malformed_env_json_fails_closed(self) -> None:
        runner, _ = make_runner(env_json="{")
        result = self._scan(runner)
        self.assertEqual(scan_image.classify_scan(result), "command_failure")
        self.assertIn("malformed JSON", result["env_inspect_error"])

    def test_invalid_env_shape_fails_closed(self) -> None:
        runner, _ = make_runner(env_json='{"PATH": "/usr/bin"}')
        result = self._scan(runner)
        self.assertEqual(scan_image.classify_scan(result), "command_failure")
        self.assertIn("invalid environment data", result["env_inspect_error"])

    def test_main_returns_nonzero_for_command_failure(self) -> None:
        runner, _ = make_runner(scan_returncode=125, scan_stdout="")
        with mock.patch.object(scan_image, "_run", runner):
            code = scan_image.main([])
        self.assertNotEqual(code, 0)


class TestProtocol(unittest.TestCase):
    def _result(self, stdout: str) -> dict:
        runner, _ = make_runner(scan_stdout=stdout)
        with mock.patch.object(scan_image, "_run", runner):
            return scan_image.scan_image("img")

    def assert_protocol_failure(self, stdout: str) -> None:
        result = self._result(stdout)
        self.assertEqual(scan_image.classify_scan(result), "command_failure")
        self.assertIsNotNone(result["protocol_error"])

    def test_missing_section_is_failure(self) -> None:
        self.assert_protocol_failure("FILES\nCONTENT\nIDENTITY\nabsent\n")

    def test_duplicate_section_is_failure(self) -> None:
        self.assert_protocol_failure(
            "FILES\nCONTENT\nFILES\nIDENTITY\nabsent\n"
            "FIND_EXIT\n0\nGREP_EXIT\n1\n"
        )

    def test_out_of_order_sections_are_failure(self) -> None:
        self.assert_protocol_failure(
            "CONTENT\nFILES\nIDENTITY\nabsent\n"
            "FIND_EXIT\n0\nGREP_EXIT\n1\n"
        )

    def test_invalid_identity_is_failure(self) -> None:
        self.assert_protocol_failure(_scan_stdout(identity="unknown"))

    def test_duplicate_identity_value_is_failure(self) -> None:
        self.assert_protocol_failure(_scan_stdout(identity="absent\npresent"))

    def test_missing_exit_value_is_failure(self) -> None:
        self.assert_protocol_failure(
            "FILES\nCONTENT\nIDENTITY\nabsent\nFIND_EXIT\nGREP_EXIT\n1\n"
        )

    def test_non_integer_exit_is_failure(self) -> None:
        self.assert_protocol_failure(
            "FILES\nCONTENT\nIDENTITY\nabsent\n"
            "FIND_EXIT\nzero\nGREP_EXIT\n1\n"
        )

    def test_unexpected_prefix_is_failure(self) -> None:
        self.assert_protocol_failure("noise\n" + _scan_stdout())


class TestInvocation(unittest.TestCase):
    def test_scan_uses_root_without_status_masking_pipeline(self) -> None:
        runner, commands = make_runner()
        with mock.patch.object(scan_image, "_run", runner):
            scan_image.scan_image("img")
        docker_run = next(command for command in commands if command[1] == "run")
        user_index = docker_run.index("--user")
        self.assertEqual(docker_run[user_index + 1], "0:0")
        shell_script = docker_run[-1]
        self.assertIn("grep -rIl", shell_script)
        self.assertIn("|| grep_exit=$?", shell_script)
        self.assertNotIn("| head", shell_script)
        self.assertNotIn("2>/dev/null", shell_script)


class TestSyntheticSecretCanary(DockerfileFixture):
    TOKEN_HEX = "1234567890abcdef1234567890abcdef"
    TOKEN = f"sk-canary-d7y-{TOKEN_HEX}"

    def _canary(self, runner) -> dict:
        with (
            mock.patch.object(scan_image, "_run", runner),
            mock.patch.object(scan_image.secrets, "token_hex", return_value=self.TOKEN_HEX),
        ):
            return scan_image.synthetic_secret_canary(self.dockerfile)

    def test_clean_canary_decides_clean(self) -> None:
        runner, _ = make_runner()
        result = self._canary(runner)
        self.assertEqual(result["status"], "clean")
        self.assertEqual(result["canary_token"], "<redacted-canary-token>")
        self.assertNotIn(self.TOKEN, json.dumps(result))

    def test_build_failure_is_non_clean_and_redacted(self) -> None:
        runner, _ = make_runner(
            build_returncode=1,
            build_stderr="build rejected <TOKEN>",
        )
        result = self._canary(runner)
        self.assertEqual(result["status"], "build_failure")
        serialized = json.dumps(result)
        self.assertNotIn(self.TOKEN, serialized)
        self.assertNotIn(self.TOKEN_HEX, serialized)

    def test_scan_failure_is_non_clean(self) -> None:
        runner, _ = make_runner(scan_returncode=125, scan_stdout="")
        result = self._canary(runner)
        self.assertEqual(result["status"], "scan_failure")

    def test_leaked_secret_is_non_clean_without_echoing_token(self) -> None:
        runner, _ = make_runner(leak_token=True)
        result = self._canary(runner)
        self.assertEqual(result["status"], "leaked")
        self.assertNotIn(self.TOKEN, json.dumps(result))

    def test_cleanup_failure_is_non_clean_and_redacted(self) -> None:
        runner, _ = make_runner(
            rmi_returncode=1,
            rmi_stderr="cleanup rejected <TOKEN>",
        )
        result = self._canary(runner)
        self.assertEqual(result["status"], "cleanup_failure")
        serialized = json.dumps(result)
        self.assertNotIn(self.TOKEN, serialized)
        self.assertNotIn(self.TOKEN_HEX, serialized)

    def test_canary_failure_makes_main_nonzero(self) -> None:
        runner, _ = make_runner(build_returncode=1)
        with (
            mock.patch.object(scan_image, "_run", runner),
            mock.patch.object(scan_image.secrets, "token_hex", return_value=self.TOKEN_HEX),
        ):
            code = scan_image.main(["--canary"])
        self.assertNotEqual(code, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
