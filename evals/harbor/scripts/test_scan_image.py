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
    return f"FILES\n{files}\nCONTENT\n{content}\nIDENTITY\n{identity}\n"


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

    def fake_run(cmd: list[str], **kwargs):
        sub = cmd[1] if len(cmd) > 1 else ""
        if sub == "build":
            for arg in cmd:
                if arg.startswith("ANTHROPIC_AUTH_TOKEN="):
                    state["token"] = arg.split("=", 1)[1]
            return _completed(cmd, build_returncode, "", build_stderr)
        if sub == "run":
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

    return fake_run


class TestScanClassification(unittest.TestCase):
    def test_clean_scan_decides_clean(self) -> None:
        runner = make_runner(scan_stdout=_scan_stdout(), env_json="[]")
        with mock.patch.object(scan_image, "_run", runner):
            result = scan_image.scan_image("img")
        self.assertEqual(scan_image.classify_scan(result), "clean")
        self.assertFalse(result["scan_command_failed"])

    def test_dirty_scan_decides_dirty(self) -> None:
        runner = make_runner(scan_stdout=_scan_stdout(files="/etc/evals.json"))
        with mock.patch.object(scan_image, "_run", runner):
            result = scan_image.scan_image("img")
        self.assertEqual(scan_image.classify_scan(result), "dirty")
        self.assertEqual(result["forbidden_files"], ["/etc/evals.json"])

    def test_dirty_content_decides_dirty(self) -> None:
        runner = make_runner(scan_stdout=_scan_stdout(content="/opt/d7y-eval-phase0-agent/Dockerfile: starting-initiatives"))
        with mock.patch.object(scan_image, "_run", runner):
            result = scan_image.scan_image("img")
        self.assertEqual(scan_image.classify_scan(result), "dirty")

    def test_identity_state_present_decides_dirty(self) -> None:
        # The installer's .claude/ or .claude.json surviving into the image is
        # forbidden generated identity state, not a clean image.
        runner = make_runner(scan_stdout=_scan_stdout(identity="present"))
        with mock.patch.object(scan_image, "_run", runner):
            result = scan_image.scan_image("img")
        self.assertEqual(scan_image.classify_scan(result), "dirty")
        self.assertTrue(result["identity_state_present"])

    def test_env_secret_hit_decides_dirty(self) -> None:
        runner = make_runner(env_json='["ANTHROPIC_AUTH_TOKEN=sk-canary-d7y-leaked"]')
        with mock.patch.object(scan_image, "_run", runner):
            result = scan_image.scan_image("img")
        self.assertEqual(scan_image.classify_scan(result), "dirty")

    def test_failed_scan_is_command_failure_not_clean(self) -> None:
        # Exit 125 from `docker run` (missing image, daemon error, ...) must not
        # become absence evidence.
        runner = make_runner(scan_returncode=125, scan_stdout="")
        with mock.patch.object(scan_image, "_run", runner):
            result = scan_image.scan_image("img")
        self.assertEqual(scan_image.classify_scan(result), "command_failure")
        self.assertTrue(result["scan_command_failed"])
        self.assertEqual(result["scan_exit_code"], 125)

    def test_failed_env_inspection_is_command_failure(self) -> None:
        runner = make_runner(env_returncode=1)
        with mock.patch.object(scan_image, "_run", runner):
            result = scan_image.scan_image("img")
        self.assertEqual(scan_image.classify_scan(result), "command_failure")
        self.assertTrue(result["scan_command_failed"])
        self.assertIsNotNone(result["env_inspect_error"])

    def test_command_failure_main_exits_nonzero(self) -> None:
        runner = make_runner(scan_returncode=125, scan_stdout="")
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
        runner = make_runner()
        with mock.patch.object(scan_image, "_run", runner):
            canary = scan_image.synthetic_secret_canary(self._dockerfile())
        self.assertEqual(canary["status"], "clean")
        self.assertFalse(canary["leaked"])
        self.assertEqual(canary["build_exit_code"], 0)

    def test_failed_build_is_build_failure_not_clean(self) -> None:
        runner = make_runner(build_returncode=1, build_stderr="simulated build error")
        with mock.patch.object(scan_image, "_run", runner):
            canary = scan_image.synthetic_secret_canary(self._dockerfile())
        self.assertEqual(canary["status"], "build_failure")
        self.assertEqual(canary["build_exit_code"], 1)
        self.assertTrue(canary["build_stderr_tail"])

    def test_failed_scan_is_scan_failure_not_clean(self) -> None:
        runner = make_runner(scan_returncode=125, scan_stdout="")
        with mock.patch.object(scan_image, "_run", runner):
            canary = scan_image.synthetic_secret_canary(self._dockerfile())
        self.assertEqual(canary["status"], "scan_failure")
        self.assertEqual(canary["scan_status"], "command_failure")

    def test_leaked_secret_is_leaked_not_clean(self) -> None:
        runner = make_runner(leak_token=True)
        with mock.patch.object(scan_image, "_run", runner):
            canary = scan_image.synthetic_secret_canary(self._dockerfile())
        self.assertEqual(canary["status"], "leaked")
        self.assertTrue(canary["leaked"])

    def test_failed_cleanup_is_cleanup_failure_not_clean(self) -> None:
        runner = make_runner(rmi_returncode=1)
        with mock.patch.object(scan_image, "_run", runner):
            canary = scan_image.synthetic_secret_canary(self._dockerfile())
        self.assertEqual(canary["status"], "cleanup_failure")
        self.assertTrue(canary["cleanup_error"])

    def test_canary_failure_main_exits_nonzero(self) -> None:
        runner = make_runner(build_returncode=1, build_stderr="simulated build error")
        with mock.patch.object(scan_image, "_run", runner):
            code = scan_image.main(["--canary"])
        self.assertNotEqual(code, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
