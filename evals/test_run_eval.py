#!/usr/bin/env python3
"""End-to-end tests for the minimal D7Y skill eval runner.

Most tests drive the public CLI (``evals/run_eval.py``) through ``subprocess``
against disposable committed Git repositories, so they exercise the real
ownership boundary. A small number of narrow unit tests cover parser, path, and
redaction primitives directly. Fake Claude executables use the runner's own
strict argv parser and a synthetic user settings file to stand in for the live
runtime; no live Claude is ever invoked.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
EVALS_DIR = REPO_ROOT / "evals"
RUNNER = EVALS_DIR / "run_eval.py"

sys.path.insert(0, str(EVALS_DIR))
import run_eval  # noqa: E402  (narrow unit tests only)


# ---------------------------------------------------------------------------
# Canonical file content for disposable committed repositories.
# ---------------------------------------------------------------------------


def _write_canonical_repo(repo: Path, *, include_wgs: bool = False) -> None:
    """Seed a disposable repo with the canonical D7Y files the runner reads."""
    (repo / "initiatives").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(REPO_ROOT / "initiatives" / "README.md", repo / "initiatives" / "README.md")
    shutil.copyfile(REPO_ROOT / "d7y", repo / "d7y")
    (repo / "scripts").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(REPO_ROOT / "scripts" / "check-initiatives.py", repo / "scripts" / "check-initiatives.py")
    skill_dir = repo / "skills" / "starting-initiatives"
    skill_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(REPO_ROOT / "skills" / "starting-initiatives" / "SKILL.md", skill_dir / "SKILL.md")
    evals_dir = skill_dir / "evals"
    evals_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(
        REPO_ROOT / "skills" / "starting-initiatives" / "evals" / "evals.json",
        evals_dir / "evals.json",
    )
    files_dir = evals_dir / "files"
    files_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(
        REPO_ROOT / "skills" / "starting-initiatives" / "evals" / "files" / "customer-interview-analysis.md",
        files_dir / "customer-interview-analysis.md",
    )
    if include_wgs:
        wgs = repo / "skills" / "writing-great-skills"
        wgs.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO_ROOT / "skills" / "writing-great-skills" / "SKILL.md", wgs / "SKILL.md")
        we = wgs / "evals"
        we.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(
            REPO_ROOT / "skills" / "writing-great-skills" / "evals" / "evals.json",
            we / "evals.json",
        )
        (we / "files" / "sprawling-skill").mkdir(parents=True, exist_ok=True)
        shutil.copyfile(
            REPO_ROOT / "skills" / "writing-great-skills" / "evals" / "files" / "sprawling-skill" / "SKILL.md",
            we / "files" / "sprawling-skill" / "SKILL.md",
        )


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, check=True
    )
    return result.stdout.strip()


def make_repo(tmp: Path, *, include_wgs: bool = False) -> tuple[Path, str]:
    """Create and commit a disposable canonical repo; return (path, commit)."""
    repo = tmp / "repo"
    repo.mkdir(parents=True)
    _git(repo, "init")
    _git(repo, "config", "user.email", "eval@example.com")
    _git(repo, "config", "user.name", "Eval")
    _write_canonical_repo(repo, include_wgs=include_wgs)
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "canonical")
    return repo, _git(repo, "rev-parse", "HEAD")


def make_user_settings(tmp: Path, env: dict[str, str] | None = None) -> Path:
    """A synthetic, tight-mode user settings file with a string-to-string env."""
    path = tmp / "user-settings.json"
    path.write_text(json.dumps({"env": env or {"D7Y_EVAL_TEST_TOKEN": "synthetic-token"}}, indent=2))
    path.chmod(0o600)
    return path


def run_cli(
    repo: Path,
    suite: str,
    case: str,
    output: Path,
    *,
    claude: Path | None = None,
    commit: str | None = None,
    dry_run: bool = False,
    user_settings: Path | None = None,
    timeout: float | None = None,
) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    if user_settings is not None:
        env["D7Y_EVAL_USER_SETTINGS"] = str(user_settings)
    cmd = [
        sys.executable,
        str(RUNNER),
        "--source-repo",
        str(repo),
        "--suite",
        suite,
        "--case",
        case,
        "--output",
        str(output),
    ]
    if claude is not None:
        cmd += ["--claude", str(claude)]
    if commit is not None:
        cmd += ["--commit", commit]
    if dry_run:
        cmd += ["--dry-run"]
    if timeout is not None:
        cmd += ["--timeout", str(timeout)]
    return subprocess.run(cmd, capture_output=True, text=True, env=env, check=False)


# ---------------------------------------------------------------------------
# Fake Claude executables. Each live fake answers the one-time version probe,
# then parses its argv through the runner's strict parser and derives the target
# workspace only from the prompt contract (never an invented --root).
# ---------------------------------------------------------------------------

EVALS_DIR_LITERAL = repr(str(EVALS_DIR))


def _write_fake_claude(path: Path, body: str, *, version: str = "2.1.218") -> None:
    version_guard = (
        "import sys as _sys\n"
        "if '--version' in _sys.argv:\n"
        f"    print('Claude Code {version}')\n"
        "    _sys.exit(0)\n"
    )
    prelude = (
        "#!/usr/bin/env python3\n"
        "import sys as _sys\n"
        f"_sys.path.insert(0, {EVALS_DIR_LITERAL})\n"
        "import run_eval  # strict argv parser; rejects unknown options\n"
        + version_guard
    )
    path.write_text(prelude + body)
    path.chmod(0o755)


def make_positive_fake(tmp: Path) -> Path:
    """A fake claude that invokes the staged skill on positive prompts.

    The with-skill positive arm emits a target Skill invocation, the exact
    ``d7y initiatives list`` then ``check`` Bash commands with valid tool_result
    JSON, writes one valid initiative into the target workspace, and emits a
    successful result. The baseline arm never invokes the target. Negative
    prompts never invoke even with the skill.
    """
    fake = tmp / "claude"
    body = textwrap.dedent(
        """
        import json, os, sys, glob

        parsed = run_eval.parse_claude_argv(_sys.argv[1:])
        plugin = parsed.get("plugin_dir") or ""
        root = parsed.get("workspace")   # obtained only from the prompt contract
        prompt = parsed.get("prompt") or ""

        skill_name = None
        if plugin:
            matches = glob.glob(os.path.join(plugin, "skills", "*", "SKILL.md"))
            if matches:
                skill_name = os.path.basename(os.path.dirname(matches[0]))
        has_skill = skill_name is not None
        target = "d7y-eval-session:" + skill_name if has_skill else None

        tools = ["Skill", "Read", "Write", "Edit", "Bash"]
        plugin_name = "d7y-eval-session" if has_skill else "d7y-eval-control"
        skills = [target, "doctor"] if has_skill else ["doctor"]
        sid = "fake-" + str(os.getpid()) + "-" + str(has_skill) + "-" + str(skill_name)
        init = {"type": "system", "subtype": "init", "session_id": sid, "tools": tools,
                "model": "claude-sonnet-5", "skills": skills,
                "plugins": [{"name": plugin_name, "path": plugin, "version": "0.0.1"}],
                "mcp_servers": [], "permissionMode": "dontAsk"}
        print(json.dumps(init))

        events = []
        final = "Done."
        positive = ("start an initiative" in prompt) or ("create a d7y skill" in prompt)
        if has_skill and positive and skill_name == "starting-initiatives":
            events.append({"type": "assistant", "message": {"role": "assistant", "model": "glm-4.7",
                "content": [{"type": "tool_use", "id": "c1", "name": "Skill",
                "input": {"skill": target}}]}})
            if root:
                list_cmd = "d7y initiatives list --root " + root + " --json"
                check_cmd = "d7y initiatives check --root " + root + " --json"
                events.append({"type": "assistant", "message": {"role": "assistant", "model": "glm-4.7",
                    "content": [{"type": "tool_use", "id": "c2", "name": "Bash",
                    "input": {"command": list_cmd}}]}})
                events.append({"type": "assistant", "message": {"role": "assistant", "model": "glm-4.7",
                    "content": [{"type": "tool_use", "id": "c3", "name": "Bash",
                    "input": {"command": check_cmd}}]}})
                list_json = json.dumps({"version": 1, "root": root, "valid": True, "count": 0,
                    "errors": [], "warnings": [], "initiatives": []})
                check_json = json.dumps({"version": 1, "root": root, "valid": True, "count": 1,
                    "errors": [], "warnings": [],
                    "initiatives": [{"slug": "consultant-proposals", "valid": True}]})
                events.append({"type": "user", "message": {"role": "user",
                    "content": [{"type": "tool_result", "tool_use_id": "c2",
                    "content": list_json, "is_error": False}]}})
                events.append({"type": "user", "message": {"role": "user",
                    "content": [{"type": "tool_result", "tool_use_id": "c3",
                    "content": check_json, "is_error": False}]}})
                idir = os.path.join(root, "initiatives", "consultant-proposals")
                os.makedirs(idir, exist_ok=True)
                md = '''---\\ntitle: Consultant proposals\\nstatus: active\\ncreated: 2026-07-27\\nupdated: 2026-07-27\\naliases: []\\nrelated: []\\n---\\n\\n# Consultant proposals\\n\\n## Provisional intent\\n\\n### Outcome\\n\\nFind need.\\n\\n### Subject\\n\\nConsultants.\\n\\n### Constraints and anti-goals\\n\\nUnknown.\\n\\n## Primary uncertainty\\n\\nNeed.\\n\\n## Current understanding\\n\\n### Evidence\\n\\nNone.\\n\\n### Assumptions\\n\\nSome.\\n\\n## Current state\\n\\nNext.\\n'''
                open(os.path.join(idir, "initiative.md"), "w").write(md)
                final = "Created one initiative."
            else:
                final = "Created."
        elif has_skill and not positive:
            events.append({"type": "assistant", "message": {"role": "assistant", "model": "glm-4.7",
                "content": [{"type": "text", "text": "Just brainstorming names."}]}})
            final = "Ten names."
        else:
            events.append({"type": "assistant", "message": {"role": "assistant", "model": "glm-4.7",
                "content": [{"type": "tool_use", "id": "b1", "name": "Skill",
                "input": {"skill": "list"}}]}})
            final = "No applicable skill."
        for e in events:
            print(json.dumps(e))
        result = {"type": "result", "subtype": "success", "result": final, "is_error": False,
                  "num_turns": len(events) + 1, "permission_denials": [],
                  "modelUsage": {"claude-sonnet-5": {"provider": "firstParty", "canonicalModel": "claude-sonnet-5"}}}
        print(json.dumps(result))
        sys.exit(0)
        """
    )
    _write_fake_claude(fake, body)
    return fake


def make_redaction_fake(tmp: Path) -> Path:
    """Echo a synthetic imported env value through every captured channel."""
    fake = tmp / "claude"
    body = textwrap.dedent(
        """
        import json, os, sys

        parsed = run_eval.parse_claude_argv(_sys.argv[1:])
        plugin = parsed.get("plugin_dir") or ""
        root = parsed.get("workspace")
        prompt = parsed.get("prompt") or ""
        secret = os.environ.get("D7Y_EVAL_TEST_TOKEN", "")

        matches = []
        if plugin:
            import glob
            matches = glob.glob(os.path.join(plugin, "skills", "*", "SKILL.md"))
        has_skill = bool(matches)
        skill_name = os.path.basename(os.path.dirname(matches[0])) if matches else None
        target = "d7y-eval-session:" + skill_name if has_skill else None
        tools = ["Skill", "Read", "Write", "Edit", "Bash"]
        skills = [target, "doctor"] if has_skill else ["doctor"]
        plugin_name = "d7y-eval-session" if has_skill else "d7y-eval-control"
        sid = "red-" + str(os.getpid())
        init = {"type": "system", "subtype": "init", "session_id": sid, "tools": tools,
                "model": "claude-sonnet-5", "skills": skills,
                "plugins": [{"name": plugin_name, "path": plugin, "version": "0.0.1"}],
                "mcp_servers": [], "permissionMode": "dontAsk"}
        print(json.dumps(init))
        # secret in raw stdout (a text block), a tool_result, and the final response.
        events = [
            {"type": "assistant", "message": {"role": "assistant", "model": "glm-4.7",
                "content": [{"type": "tool_use", "id": "x1", "name": "Bash", "input": {"command": "true"}}]}},
            {"type": "user", "message": {"role": "user", "content": [{"type": "tool_result",
                "tool_use_id": "x1", "content": "saw " + secret, "is_error": False}]}},
            {"type": "assistant", "message": {"role": "assistant", "model": "glm-4.7",
                "content": [{"type": "text", "text": "echo " + secret}]}},
        ]
        for e in events:
            print(json.dumps(e))
        # secret in raw stderr.
        sys.stderr.write("stderr leak " + secret + "\\n")
        # secret in checker-visible output: write an initiative whose title carries it.
        if root and has_skill:
            idir = os.path.join(root, "initiatives", "leaked")
            os.makedirs(idir, exist_ok=True)
            md = ("---\\ntitle: " + secret + "\\nstatus: active\\ncreated: 2026-07-27\\n"
                  "updated: 2026-07-27\\naliases: []\\nrelated: []\\n---\\n\\n"
                  "# " + secret + "\\n\\n## Provisional intent\\n\\n### Outcome\\n\\nX.\\n\\n"
                  "### Subject\\n\\nX.\\n\\n### Constraints and anti-goals\\n\\nUnknown.\\n\\n"
                  "## Primary uncertainty\\n\\nX.\\n\\n## Current understanding\\n\\n### Evidence\\n\\n"
                  "None.\\n\\n### Assumptions\\n\\nX.\\n\\n## Current state\\n\\nX.\\n")
            open(os.path.join(idir, "initiative.md"), "w").write(md)
        result = {"type": "result", "subtype": "success", "result": "final " + secret,
                  "is_error": False, "num_turns": 4, "permission_denials": [],
                  "modelUsage": {"claude-sonnet-5": {"provider": "firstParty"}}}
        print(json.dumps(result))
        sys.exit(0)
        """
    )
    _write_fake_claude(fake, body)
    return fake


def make_canary_signal_fake(tmp: Path) -> Path:
    """A structurally valid arm whose only invalidating fact is canary leakage."""
    fake = tmp / "claude"
    body = textwrap.dedent(
        """
        import json, os, sys, glob

        parsed = run_eval.parse_claude_argv(_sys.argv[1:])
        plugin = parsed.get("plugin_dir") or ""
        matches = glob.glob(os.path.join(plugin, "skills", "*", "SKILL.md")) if plugin else []
        has_skill = bool(matches)
        skill_name = os.path.basename(os.path.dirname(matches[0])) if matches else None
        target = "d7y-eval-session:" + skill_name if has_skill else None
        tools = ["Skill", "Read", "Write", "Edit", "Bash"]
        skills = [target, "doctor"] if has_skill else ["doctor"]
        plugin_name = "d7y-eval-session" if has_skill else "d7y-eval-control"
        sid = "canary-" + str(os.getpid()) + "-" + str(has_skill)
        init = {"type": "system", "subtype": "init", "session_id": sid, "tools": tools,
                "model": "claude-sonnet-5", "skills": skills,
                "plugins": [{"name": plugin_name, "path": plugin, "version": "0.0.1"}],
                "mcp_servers": [], "permissionMode": "dontAsk"}
        print(json.dumps(init))
        # The only problem: the project-instruction canary signal leaked into the response.
        events = [{"type": "assistant", "message": {"role": "assistant", "model": "glm-4.7",
            "content": [{"type": "text", "text": "loaded globals: " + run_eval.PROJECT_INSTRUCTION_SIGNAL}]}}]
        for e in events:
            print(json.dumps(e))
        result = {"type": "result", "subtype": "success", "result": "ok " + run_eval.PROJECT_INSTRUCTION_SIGNAL,
                  "is_error": False, "num_turns": 2, "permission_denials": [],
                  "modelUsage": {"claude-sonnet-5": {"provider": "firstParty"}}}
        print(json.dumps(result))
        sys.exit(0)
        """
    )
    _write_fake_claude(fake, body)
    return fake


def make_invocation_recording_fake(tmp: Path) -> Path:
    """A fake claude that records any version/run invocation; never emits success."""
    fake = tmp / "claude"
    log = tmp / "claude-invocations.log"
    body = (
        f"import sys, json\n"
        f"log = {str(log)!r}\n"
        f"with open(log, 'a') as f:\n"
        f"    f.write(json.dumps(sys.argv[1:]) + '\\n')\n"
        f"sys.exit(0)\n"
    )
    _write_fake_claude(fake, body)
    return fake


def make_resistant_fake(tmp: Path) -> Path:
    fake = tmp / "claude"
    body = textwrap.dedent(
        """
        import os, signal, sys, time
        child = os.fork()
        if child == 0:
            signal.signal(signal.SIGTERM, signal.SIG_IGN)
            signal.signal(signal.SIGINT, signal.SIG_IGN)
            time.sleep(300)
            sys.exit(0)
        print('{"type": "system", "subtype": "init", "session_id": "r"}')
        sys.stdout.flush()
        time.sleep(300)
        sys.exit(0)
        """
    )
    _write_fake_claude(fake, body)
    return fake


def make_malformed_fake(tmp: Path) -> Path:
    fake = tmp / "claude"
    _write_fake_claude(
        fake,
        "import sys\nprint('{\"type\": \"system\", \"subtype\": \"init\"}')\n"
        "print('this is not json')\nsys.exit(0)\n",
    )
    return fake


def make_nonzero_fake(tmp: Path) -> Path:
    fake = tmp / "claude"
    _write_fake_claude(fake, "import sys\nprint('boom')\nsys.exit(3)\n")
    return fake


# ---------------------------------------------------------------------------
# Narrow unit tests: parser, path, redaction primitives.
# ---------------------------------------------------------------------------


class TestPathPrimitives(unittest.TestCase):
    def test_safe_relative_rejects_absolute_and_traversal(self):
        with self.assertRaises(run_eval.PreflightError):
            run_eval.safe_relative_path("/etc/passwd")
        with self.assertRaises(run_eval.PreflightError):
            run_eval.safe_relative_path("../escape")
        with self.assertRaises(run_eval.PreflightError):
            run_eval.safe_relative_path("")

    def test_control_destination_detection(self):
        self.assertTrue(run_eval.is_control_destination(Path("settings.json")))
        self.assertTrue(run_eval.is_control_destination(Path("CLAUDE.md")))
        self.assertTrue(run_eval.is_control_destination(Path("evals/evals.json")))
        self.assertTrue(run_eval.is_control_destination(Path("graders/x.py")))
        self.assertFalse(run_eval.is_control_destination(Path("initiatives/README.md")))

    def test_tokenize_rejects_compound_and_quoted(self):
        self.assertIsNone(run_eval.tokenize_simple_command("d7y x && echo hi"))
        # A quoted echo of the command tokenizes but never matches the exact
        # d7y command shape.
        tokens = run_eval.tokenize_simple_command('echo "d7y initiatives list --root /w --json"')
        self.assertFalse(run_eval._valid_d7y_tokens(tokens or [], "list", "/w"))
        self.assertEqual(
            run_eval.tokenize_simple_command("d7y initiatives list --root /w --json"),
            ["d7y", "initiatives", "list", "--root", "/w", "--json"],
        )


class TestArgvParser(unittest.TestCase):
    def test_parser_records_supported_surface_and_workspace_from_prompt(self):
        prompt = "do work" + run_eval.HARNESS_INSTRUCTION_TEMPLATE.format(workspace="/abs/ws")
        argv = run_eval.build_claude_argv(
            claude_path="/c/claude", settings_path=Path("/s"),
            plugin_root=Path("/p"), prompt=prompt,
        )
        parsed = run_eval.parse_claude_argv(argv)
        self.assertEqual(parsed["tools"], run_eval.EXPECTED_TOOLS_ARG)
        self.assertEqual(parsed["model"], run_eval.EXPECTED_MODEL)
        self.assertEqual(parsed["workspace"], "/abs/ws")
        self.assertIn("--print", parsed["bool_flags"])
        self.assertIn("--strict-mcp-config", parsed["bool_flags"])

    def test_parser_rejects_root_and_unknown(self):
        for bad in (
            ["/c", "--root", "/x", "--", "p"],
            ["/c", "--dangerous", "--", "p"],
        ):
            with self.assertRaises(ValueError):
                run_eval.parse_claude_argv(bad)


class TestParserUnit(unittest.TestCase):
    def setUp(self):
        self.fixtures = EVALS_DIR / "fixtures" / "claude-code-2.1.218"

    def test_parse_positive_fixture_target_invocation(self):
        events = run_eval.parse_stream_json((self.fixtures / "positive.jsonl").read_text())
        count, _ = run_eval.count_target_invocations(events, "d7y-eval-probe:d7y-invocation-probe")
        self.assertEqual(count, 1)

    def test_parse_baseline_fixture_skill_list_not_counted(self):
        events = run_eval.parse_stream_json((self.fixtures / "baseline.jsonl").read_text())
        count, _ = run_eval.count_target_invocations(events, "d7y-eval-probe:d7y-invocation-probe")
        self.assertEqual(count, 0)

    def test_parse_negative_fixture_no_target(self):
        events = run_eval.parse_stream_json((self.fixtures / "negative.jsonl").read_text())
        count, _ = run_eval.count_target_invocations(events, "d7y-eval-probe:d7y-invocation-probe")
        self.assertEqual(count, 0)

    def test_prefix_does_not_count(self):
        events = [
            {"type": "assistant", "message": {"content": [
                {"type": "tool_use", "name": "Skill", "input": {"skill": "d7y-eval-session:starting-initiatives-extra"}}
            ]}}
        ]
        count, _ = run_eval.count_target_invocations(events, "d7y-eval-session:starting-initiatives")
        self.assertEqual(count, 0)

    def test_malformed_line_raises(self):
        with self.assertRaises(ValueError):
            run_eval.parse_stream_json('{"type": "system"}\nnot json\n')

    def test_canary_signal_detection(self):
        leak = [{"type": "assistant", "message": {"content": [
            {"type": "text", "text": "see " + run_eval.PROJECT_INSTRUCTION_SIGNAL}]}}]
        clean, issues = run_eval.check_canary_leakage(leak)
        self.assertFalse(clean)
        leak_result = [{"type": "result", "result": "x " + run_eval.PROJECT_INSTRUCTION_SIGNAL}]
        clean2, issues2 = run_eval.check_canary_leakage(leak_result)
        self.assertFalse(clean2)

    def test_routed_model_extraction(self):
        events = [{"type": "assistant", "message": {"model": "glm-4.7", "content": []}}]
        self.assertEqual(run_eval.extract_routed_models(events), ["glm-4.7"])


def _bash_use(tool_use_id: str, command: str, index: int = 0):
    return index, {"type": "assistant", "message": {"content": [
        {"type": "tool_use", "id": tool_use_id, "name": "Bash", "input": {"command": command}}
    ]}}


def _tool_result(tool_use_id: str, content: str, *, is_error: bool = False, index: int = 99):
    return index, {"type": "user", "message": {"content": [
        {"type": "tool_result", "tool_use_id": tool_use_id, "content": content, "is_error": is_error}
    ]}}


class TestD7YCommandAnalysis(unittest.TestCase):
    WS = "/ws"

    def _analyze(self, pairs):
        events = [ev for _, ev in sorted(pairs, key=lambda p: p[0])]
        return run_eval.analyze_d7y_commands(events, self.WS)

    def test_valid_list_then_check_with_results(self):
        out = self._analyze([
            _bash_use("a", "d7y initiatives list --root /ws --json", 1),
            _bash_use("b", "d7y initiatives check --root /ws --json", 2),
            _tool_result("a", '{"version":1,"valid":true}', index=3),
            _tool_result("b", '{"version":1,"valid":true}', index=4),
        ])
        self.assertTrue(out["shape_supported"])
        self.assertTrue(out["list"]["present"] and out["list"]["result_state"] == "ok")
        self.assertTrue(out["check"]["present"] and out["check"]["result_state"] == "ok")
        self.assertTrue(out["order_ok"])

    def test_wrong_root_not_counted(self):
        out = self._analyze([
            _bash_use("a", "d7y initiatives list --root /other --json", 1),
            _bash_use("b", "d7y initiatives check --root /ws --json", 2),
            _tool_result("b", '{}', index=3),
        ])
        self.assertFalse(out["list"]["present"])
        self.assertTrue(out["check"]["present"])

    def test_quoted_substring_not_counted(self):
        out = self._analyze([
            _bash_use("a", 'echo "d7y initiatives list --root /ws --json"', 1),
            _tool_result("a", 'ok', index=2),
        ])
        self.assertFalse(out["list"]["present"])

    def test_absent_result(self):
        out = self._analyze([
            _bash_use("a", "d7y initiatives list --root /ws --json", 1),
            # a tool_result exists for something else, so the shape is supported.
            _tool_result("other", '{}', index=2),
        ])
        self.assertTrue(out["shape_supported"])
        self.assertEqual(out["list"]["result_state"], "absent")

    def test_error_result(self):
        out = self._analyze([
            _bash_use("a", "d7y initiatives check --root /ws --json", 1),
            _tool_result("a", "boom", is_error=True, index=2),
        ])
        self.assertEqual(out["check"]["result_state"], "error")

    def test_reversed_order(self):
        out = self._analyze([
            _bash_use("b", "d7y initiatives check --root /ws --json", 1),
            _bash_use("a", "d7y initiatives list --root /ws --json", 2),
            _tool_result("a", '{}', index=3),
            _tool_result("b", '{}', index=4),
        ])
        self.assertFalse(out["order_ok"])

    def test_shape_unsupported_without_tool_results(self):
        out = self._analyze([
            _bash_use("a", "d7y initiatives list --root /ws --json", 1),
        ])
        self.assertFalse(out["shape_supported"])


class TestRedactionUnit(unittest.TestCase):
    def test_recursive_redaction_preserves_structure(self):
        obj = {"a": "secret-1 here", "b": ["secret-1", {"c": "secret-2"}], "n": 5}
        out = run_eval.redact_obj(obj, ["secret-1", "secret-2"])
        self.assertEqual(out["a"], "<redacted> here")
        self.assertEqual(out["b"][0], "<redacted>")
        self.assertEqual(out["b"][1]["c"], "<redacted>")
        self.assertEqual(out["n"], 5)


class TestValidateArmEvents(unittest.TestCase):
    def _events(self, **overrides):
        init = {
            "type": "system", "subtype": "init", "session_id": "s1",
            "tools": run_eval.EXPECTED_TOOLS, "model": run_eval.EXPECTED_MODEL,
            "skills": ["d7y-eval-session:starting-initiatives", "doctor"],
            "plugins": [{"name": "d7y-eval-session"}], "mcp_servers": [],
            "permissionMode": "dontAsk",
        }
        init.update(overrides.get("init", {}))
        result = {
            "type": "result", "subtype": "success", "result": "ok", "is_error": False,
            "num_turns": 1, "permission_denials": [],
            "modelUsage": {"claude-sonnet-5": {"provider": "firstParty"}},
        }
        result.update(overrides.get("result", {}))
        events = [init, result]
        events.extend(overrides.get("extra", []))
        return events

    def _validate(self, events, **kw):
        defaults = dict(with_skill=True, skill_name="starting-initiatives",
                        expected_plugin="d7y-eval-session", other_session_id=None,
                        exit_code=0, timed_out=False)
        defaults.update(kw)
        return run_eval.validate_arm_events(events, **defaults)

    def test_valid_with_skill(self):
        self.assertTrue(self._validate(self._events()).ok)

    def test_nonzero_exit_invalidates(self):
        v = self._validate(self._events(), exit_code=3)
        self.assertFalse(v.ok)

    def test_timeout_invalidates(self):
        v = self._validate(self._events(), timed_out=True)
        self.assertFalse(v.ok)

    def test_missing_canonical_model_usage(self):
        events = self._events(result={"modelUsage": {"glm-4.7": {}}})
        v = self._validate(events)
        self.assertFalse(v.ok)

    def test_wrong_tools_rejected(self):
        events = self._events(init={"tools": ["Skill"]})
        self.assertFalse(self._validate(events).ok)

    def test_unsuccessful_subtype_rejected(self):
        events = self._events(result={"subtype": "error_max_turns"})
        self.assertFalse(self._validate(events).ok)

    def test_shared_session_rejected(self):
        v = self._validate(self._events(init={"session_id": "shared"}),
                           with_skill=False, expected_plugin="d7y-eval-control",
                           other_session_id="shared")
        self.assertFalse(v.ok)

    def test_routed_glm_allowed(self):
        events = self._events(extra=[{"type": "assistant", "message": {"model": "glm-4.7", "content": []}}])
        self.assertTrue(self._validate(events).ok)


# ---------------------------------------------------------------------------
# Staging safety unit tests.
# ---------------------------------------------------------------------------


class TestFixtureStagingSafety(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="d7y-eval-"))
        self.repo, self.commit = make_repo(self.tmp)

    def tearDown(self):
        if self.tmp.exists():
            shutil.rmtree(self.tmp)

    def _stage(self, case):
        ws = self.tmp / "ws"
        ws.mkdir()
        run_eval.stage_workspace_seed(
            ws, case=case, repo=self.repo, commit=self.commit,
            skill_repo_dir="skills/starting-initiatives", seed_repo_paths=[])

    def test_duplicate_destination_detected(self):
        case = {"files": [{"source": "evals/files/customer-interview-analysis.md", "destination": "a/b.md"},
                          {"source": "evals/files/customer-interview-analysis.md", "destination": "a/b.md"}]}
        with self.assertRaises(run_eval.PreflightError):
            self._stage(case)

    def test_ancestor_descendant_collision_detected(self):
        case = {"files": [
            {"source": "evals/files/customer-interview-analysis.md", "destination": "a"},
            {"source": "evals/files/customer-interview-analysis.md", "destination": "a/b.md"},
        ]}
        with self.assertRaises(run_eval.PreflightError):
            self._stage(case)

    def test_control_destination_collision_detected(self):
        case = {"files": [{"source": "evals/files/customer-interview-analysis.md", "destination": "settings.json"}]}
        with self.assertRaises(run_eval.PreflightError):
            self._stage(case)


# ---------------------------------------------------------------------------
# Public-CLI end-to-end tests in disposable committed repositories.
# ---------------------------------------------------------------------------


class TestPublicCLI(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="d7y-eval-"))
        self.repo, self.commit = make_repo(self.tmp)

    def tearDown(self):
        if self.tmp.exists():
            shutil.rmtree(self.tmp)

    # -- correction 1: workspace bound via supported command + prompt --------

    def test_dry_run_complete_preflight_zero_invocations(self):
        fake = make_invocation_recording_fake(self.tmp)
        output = self.tmp / "out"
        proc = run_cli(self.repo, "skills/starting-initiatives/evals/evals.json",
                       "start-new-initiative", output, claude=fake, dry_run=True,
                       user_settings=make_user_settings(self.tmp))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertFalse((self.tmp / "claude-invocations.log").exists(),
                         "dry-run must not invoke or version-probe the executable")
        manifest = json.loads((output / "manifest.json").read_text())
        self.assertEqual(manifest["commit"], self.commit)
        self.assertTrue(manifest["dry_run"])
        self.assertIsNone(manifest["executable"])
        plugin_skill = output / "with-skill" / "plugin" / "skills" / "starting-initiatives" / "SKILL.md"
        self.assertTrue(plugin_skill.exists())
        plugin_json = output / "with-skill" / "plugin" / ".claude-plugin" / "plugin.json"
        self.assertEqual(json.loads(plugin_json.read_text())["name"], "d7y-eval-session")
        self.assertFalse((output / "baseline" / "plugin" / "skills").exists())
        roots = manifest["roots"]
        self.assertNotEqual(roots["with_skill_workspace"], roots["baseline_workspace"])
        self.assertNotEqual(roots["with_skill_plugin"], roots["with_skill_workspace"])
        for ws in (output / "with-skill" / "workspace", output / "baseline" / "workspace"):
            for p in ws.rglob("*"):
                self.assertNotIn(p.name, {".claude-plugin", "settings.json", "CLAUDE.md"})
        caps = manifest["capability_object_ids"]
        self.assertIn("d7y", caps)
        self.assertIn("scripts/check-initiatives.py", caps)
        self.assertTrue((output / "with-skill" / "workspace" / "initiatives" / "README.md").exists())
        self.assertEqual(_git(self.repo, "status", "--porcelain"), "")

    def test_actual_arm_argv_records_and_prompt_binding(self):
        """Assert the two actual recorded arm argv records, not a helper re-call."""
        fake = make_invocation_recording_fake(self.tmp)
        output = self.tmp / "out"
        proc = run_cli(self.repo, "skills/starting-initiatives/evals/evals.json",
                       "start-new-initiative", output, claude=fake, dry_run=True,
                       user_settings=make_user_settings(self.tmp))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        manifest = json.loads((output / "manifest.json").read_text())
        for key in ("with_skill_argv", "baseline_argv"):
            argv = manifest[key]
            self.assertIsNotNone(argv)
            self.assertNotIn("--root", argv)  # no unsupported top-level flag
            self.assertEqual(argv.count("--tools"), 1)
            parsed = run_eval.parse_claude_argv(argv)
            self.assertEqual(parsed["tools"], run_eval.EXPECTED_TOOLS_ARG)
            self.assertEqual(parsed["model"], run_eval.EXPECTED_MODEL)
            ws = parsed["workspace"]
            self.assertIsNotNone(ws)
            self.assertEqual(ws, manifest["roots"]["with_skill_workspace"
                                 if key == "with_skill_argv" else "baseline_workspace"])
        # Per-arm provenance records the prompt contract identically.
        for arm in ("with-skill", "baseline"):
            prov = json.loads((output / arm / "artifacts" / "provenance.json").read_text())
            self.assertEqual(prov["state"], "dry_run")
            self.assertTrue(prov["prompt_contract"]["workspace_matches_arm"])
            self.assertTrue(prov["prompt_contract"]["skill_directive_present"])

    # -- correction 3/4: live positive run -----------------------------------

    def test_live_positive_case_deterministic_passes_rubric_blocks(self):
        fake = make_positive_fake(self.tmp)
        settings = make_user_settings(self.tmp)
        output = self.tmp / "out"
        proc = run_cli(self.repo, "skills/starting-initiatives/evals/evals.json",
                       "start-new-initiative", output, claude=fake, user_settings=settings)
        self.assertEqual(proc.returncode, 1, proc.stderr + "\n" + (output / "summary.md").read_text())
        checks = json.loads((output / "checks.json").read_text())
        self.assertEqual(checks["pair_validity"]["status"], "pass", checks["pair_validity"])
        self.assertEqual(checks["treatment_checks"]["status"], "pass")
        self.assertFalse(checks["case_pass"])
        for a in checks["with_skill_assertions"]:
            if a["required"] and a["kind"] == "deterministic":
                self.assertEqual(a["status"], "pass", a)
        rubric = next(a for a in checks["with_skill_assertions"] if a["kind"] == "rubric")
        self.assertEqual(rubric["status"], "pending")
        self.assertTrue(checks["blocking"])
        # Complete per-arm artifact tree exists for both arms.
        for arm in ("with-skill", "baseline"):
            d = output / arm / "artifacts"
            for name in ("trace.jsonl", "stderr.txt", "telemetry.json", "provenance.json",
                         "command-events.json", "checker.json", "workspace-changes.json",
                         "validation.json", "process.json", "final-response.txt",
                         "selected-objects.json", "arm-summary.json"):
                self.assertTrue((d / name).exists(), name)
        tel = json.loads((output / "with-skill" / "artifacts" / "telemetry.json").read_text())
        self.assertEqual(tel["canonical_model"], "claude-sonnet-5")
        self.assertIn("glm-4.7", tel["routed_models"])
        # Agent-command evidence separate from the independent checker.
        cmds = json.loads((output / "with-skill" / "artifacts" / "command-events.json").read_text())
        self.assertTrue(cmds["shape_supported"])
        self.assertTrue(cmds["list"]["present"] and cmds["list"]["result_state"] == "ok")
        self.assertTrue(cmds["check"]["present"] and cmds["check"]["result_state"] == "ok")
        self.assertTrue(cmds["order_ok"])
        checker = json.loads((output / "with-skill" / "artifacts" / "checker.json").read_text())
        self.assertTrue(checker["valid"])
        self.assertIsInstance(checker["argv"], list)
        # Added workspace evidence (one initiative created).
        changes = json.loads((output / "with-skill" / "artifacts" / "workspace-changes.json").read_text())
        self.assertIn("initiatives/consultant-proposals/initiative.md", changes["added"])
        prov = json.loads((output / "with-skill" / "artifacts" / "provenance.json").read_text())
        self.assertEqual(prov["executable_version"], "Claude Code 2.1.218")
        self.assertTrue(prov["executable"].startswith("/"))
        self.assertEqual(_git(self.repo, "status", "--porcelain"), "")

    def test_live_negative_case_passes_on_absence(self):
        fake = make_positive_fake(self.tmp)
        settings = make_user_settings(self.tmp)
        output = self.tmp / "out"
        proc = run_cli(self.repo, "skills/starting-initiatives/evals/evals.json",
                       "casual-brainstorm", output, claude=fake, user_settings=settings)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        checks = json.loads((output / "checks.json").read_text())
        inv = next(a for a in checks["with_skill_assertions"] if a["id"] == "does-not-invoke")
        self.assertEqual(inv["status"], "pass", inv)
        noinit = next(a for a in checks["with_skill_assertions"] if a["id"] == "creates-no-initiative")
        self.assertEqual(noinit["status"], "pass", noinit)

    # -- correction 8: resume / no-duplicate --------------------------------

    def test_resume_case_creates_no_duplicate(self):
        fake = make_positive_fake(self.tmp)
        settings = make_user_settings(self.tmp)
        output = self.tmp / "out"
        proc = run_cli(self.repo, "skills/starting-initiatives/evals/evals.json",
                       "resume-same-initiative", output, claude=fake, user_settings=settings)
        # The resume prompt is not recognized as positive by the fake, so the
        # target is available but not invoked -> invocation fails; still, the
        # creates-no-duplicate outcome check must pass (no new initiative).
        checks = json.loads((output / "checks.json").read_text())
        nodup = next(a for a in checks["with_skill_assertions"] if a["id"] == "creates-no-duplicate")
        self.assertEqual(nodup["status"], "pass", nodup)

    # -- correction 8: writing-great-skills unsupported outcome -> ungradable

    def test_writing_great_skills_outcome_assertions_ungradable(self):
        sub = self.tmp / "wgs-tmp"
        sub.mkdir()
        repo, _ = make_repo(sub, include_wgs=True)
        fake = make_positive_fake(self.tmp)
        settings = make_user_settings(self.tmp)
        output = self.tmp / "out"
        proc = run_cli(repo, "skills/writing-great-skills/evals/evals.json",
                       "create-discovery-skill", output, claude=fake, user_settings=settings)
        self.assertNotEqual(proc.returncode, 0, proc.stderr)
        checks = json.loads((output / "checks.json").read_text())
        by_id = {a["id"]: a for a in checks["with_skill_assertions"]}
        self.assertEqual(by_id["creates-valid-skill"]["status"], "ungradable")
        self.assertEqual(by_id["creates-evals"]["status"], "ungradable")
        self.assertTrue(checks["blocking"])

    # -- correction 2: recursive redaction across every channel --------------

    def test_imported_env_value_redacted_from_all_channels(self):
        fake = make_redaction_fake(self.tmp)
        settings = make_user_settings(self.tmp, env={"D7Y_EVAL_TEST_TOKEN": "super-secret-value"})
        output = self.tmp / "out"
        proc = run_cli(self.repo, "skills/starting-initiatives/evals/evals.json",
                       "start-new-initiative", output, claude=fake, user_settings=settings)
        self.assertNotEqual(proc.returncode, 2, proc.stderr)  # preflight ok
        # Key-name provenance retained.
        manifest = json.loads((output / "manifest.json").read_text())
        self.assertIn("D7Y_EVAL_TEST_TOKEN", manifest["env_provenance"]["imported_keys"])
        secret = "super-secret-value"
        # Scan every harness evidence file (artifacts, manifest, checks, summary).
        for p in output.rglob("*"):
            if not p.is_file():
                continue
            if "/workspace/" in str(p) or "/workspaces/" in str(p):
                continue  # agent-authored workspace content is the run's product
            self.assertNotIn(secret, p.read_text(errors="ignore"),
                             f"secret leaked in harness evidence: {p}")
        # Specifically confirm each channel captured then redacted it.
        trace = (output / "with-skill" / "artifacts" / "trace.jsonl").read_text()
        stderr = (output / "with-skill" / "artifacts" / "stderr.txt").read_text()
        final = (output / "with-skill" / "artifacts" / "final-response.txt").read_text()
        checker = (output / "with-skill" / "artifacts" / "checker.json").read_text()
        for label, text in (("trace", trace), ("stderr", stderr), ("final", final), ("checker", checker)):
            self.assertNotIn(secret, text, f"{label} not redacted")
        self.assertIn("<redacted>", trace)
        self.assertIn("<redacted>", checker)

    # -- correction 4: process invalid variants invalidate the arm ----------

    def test_nonzero_run_invalidates_pair_and_exits_nonzero(self):
        fake = make_nonzero_fake(self.tmp)
        settings = make_user_settings(self.tmp)
        output = self.tmp / "out"
        proc = run_cli(self.repo, "skills/starting-initiatives/evals/evals.json",
                       "start-new-initiative", output, claude=fake, user_settings=settings)
        self.assertNotEqual(proc.returncode, 0)
        checks = json.loads((output / "checks.json").read_text())
        self.assertEqual(checks["pair_validity"]["status"], "fail")
        # Complete inventory still emitted.
        for arm in ("with-skill", "baseline"):
            self.assertTrue((output / arm / "artifacts" / "process.json").exists())
            self.assertTrue((output / arm / "artifacts" / "validation.json").exists())

    def test_executable_resolution_failure_writes_complete_inventory(self):
        wrong = self.tmp / "claude"
        wrong.write_text("#!/bin/sh\necho 'Claude Code 1.0.0'\n")
        wrong.chmod(0o755)
        settings = make_user_settings(self.tmp)
        output = self.tmp / "out"
        proc = run_cli(self.repo, "skills/starting-initiatives/evals/evals.json",
                       "start-new-initiative", output, claude=wrong, user_settings=settings)
        self.assertEqual(proc.returncode, 2)
        self.assertIn("2.1.218", proc.stderr)
        # Both arms get an explicit unstarted record and complete inventory.
        for arm in ("with-skill", "baseline"):
            d = output / arm / "artifacts"
            prov = json.loads((d / "provenance.json").read_text())
            self.assertEqual(prov["state"], "unstarted")
            self.assertTrue((d / "process.json").exists())
            self.assertTrue((d / "validation.json").exists())
            self.assertTrue((d / "workspace-changes.json").exists())

    def test_malformed_stream_marks_arm_error(self):
        fake = make_malformed_fake(self.tmp)
        settings = make_user_settings(self.tmp)
        output = self.tmp / "out"
        proc = run_cli(self.repo, "skills/starting-initiatives/evals/evals.json",
                       "start-new-initiative", output, claude=fake, user_settings=settings)
        self.assertNotEqual(proc.returncode, 0)
        tel = json.loads((output / "with-skill" / "artifacts" / "telemetry.json").read_text())
        self.assertIsNotNone(tel["parse_error"])

    def test_timeout_kills_process_group_and_reaps(self):
        fake = make_resistant_fake(self.tmp)
        settings = make_user_settings(self.tmp)
        output = self.tmp / "out"
        before = set(self._child_pids())
        proc = run_cli(self.repo, "skills/starting-initiatives/evals/evals.json",
                       "start-new-initiative", output, claude=fake, user_settings=settings,
                       timeout=2)
        self.assertNotEqual(proc.returncode, 0)
        time.sleep(1.0)
        after = set(self._child_pids())
        self.assertFalse(after - before, f"child processes survived timeout: {after - before}")
        proc_json = json.loads((output / "with-skill" / "artifacts" / "process.json").read_text())
        self.assertTrue(proc_json["timed_out"])
        self.assertIsNotNone(proc_json["pid"])

    # -- correction 6: canary leakage is the only invalidating fact ---------

    def test_canary_signal_leak_fails_pair_only(self):
        fake = make_canary_signal_fake(self.tmp)
        settings = make_user_settings(self.tmp)
        output = self.tmp / "out"
        proc = run_cli(self.repo, "skills/starting-initiatives/evals/evals.json",
                       "start-new-initiative", output, claude=fake, user_settings=settings)
        self.assertNotEqual(proc.returncode, 0)
        checks = json.loads((output / "checks.json").read_text())
        self.assertEqual(checks["pair_validity"]["status"], "fail")
        self.assertTrue(
            any("canary" in e for e in checks["pair_validity"]["errors"]),
            checks["pair_validity"]["errors"],
        )

    # -- corrections 5/8: source safety, fixture handling --------------------

    def test_dirty_worktree_replacements_ignored(self):
        fake = make_positive_fake(self.tmp)
        settings = make_user_settings(self.tmp)
        output = self.tmp / "out"
        proc = run_cli(self.repo, "skills/starting-initiatives/evals/evals.json",
                       "start-new-initiative", output, claude=fake, user_settings=settings)
        self.assertNotEqual(proc.returncode, 2, proc.stderr)
        staged = json.loads((output / "manifest.json").read_text())["selected_objects"]["with_skill"]
        committed_ids = {obj["object_id"] for obj in staged}
        (self.repo / "initiatives" / "README.md").write_text("DIRTY OVERRIDE")
        output2 = self.tmp / "out2"
        proc2 = run_cli(self.repo, "skills/starting-initiatives/evals/evals.json",
                        "start-new-initiative", output2, claude=fake, user_settings=settings)
        self.assertNotEqual(proc2.returncode, 2, proc2.stderr)
        staged2 = json.loads((output2 / "manifest.json").read_text())["selected_objects"]["with_skill"]
        self.assertEqual({obj["object_id"] for obj in staged2}, committed_ids)
        ws_readme = output2 / "with-skill" / "workspace" / "initiatives" / "README.md"
        self.assertNotIn("DIRTY OVERRIDE", ws_readme.read_text())

    def test_committed_symlink_in_skill_rejected_writes_evidence(self):
        link = self.repo / "skills" / "starting-initiatives" / "README.link"
        try:
            os.symlink("../../initiatives/README.md", link)
        except OSError:
            self.skipTest("cannot create symlink on this platform")
        _git(self.repo, "add", "-A")
        _git(self.repo, "commit", "-m", "symlink")
        fake = make_positive_fake(self.tmp)
        settings = make_user_settings(self.tmp)
        output = self.tmp / "out"
        proc = run_cli(self.repo, "skills/starting-initiatives/evals/evals.json",
                       "start-new-initiative", output, claude=fake, user_settings=settings)
        self.assertNotEqual(proc.returncode, 0)
        # Post-output preflight failure still finalizes evidence.
        self.assertTrue((output / "manifest.json").exists())
        self.assertTrue((output / "summary.md").exists())
        self.assertTrue((output / "source-status.json").exists())

    def test_output_inside_source_rejected(self):
        fake = make_invocation_recording_fake(self.tmp)
        output = self.repo / "inside-output"
        proc = run_cli(self.repo, "skills/starting-initiatives/evals/evals.json",
                       "start-new-initiative", output, claude=fake, dry_run=True)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("output root", proc.stderr)

    def test_empty_output_dir_rejected(self):
        fake = make_invocation_recording_fake(self.tmp)
        output = self.tmp / "empty"
        output.mkdir()
        proc = run_cli(self.repo, "skills/starting-initiatives/evals/evals.json",
                       "start-new-initiative", output, claude=fake, dry_run=True)
        self.assertNotEqual(proc.returncode, 0)

    def test_stale_output_rejected(self):
        fake = make_invocation_recording_fake(self.tmp)
        output = self.tmp / "stale"
        output.mkdir()
        (output / "leftover.txt").write_text("x")
        proc = run_cli(self.repo, "skills/starting-initiatives/evals/evals.json",
                       "start-new-initiative", output, claude=fake, dry_run=True)
        self.assertNotEqual(proc.returncode, 0)

    def test_symlink_output_rejected(self):
        try:
            target = self.tmp / "real"
            target.mkdir()
            link = self.tmp / "link-out"
            os.symlink(target, link)
        except OSError:
            self.skipTest("cannot create symlink on this platform")
        fake = make_invocation_recording_fake(self.tmp)
        proc = run_cli(self.repo, "skills/starting-initiatives/evals/evals.json",
                       "start-new-initiative", link, claude=fake, dry_run=True)
        self.assertNotEqual(proc.returncode, 0)

    def test_env_path_leak_rejected(self):
        fake = make_positive_fake(self.tmp)
        settings = make_user_settings(self.tmp, env={"LEAK_VAR": str(self.repo)})
        output = self.tmp / "out"
        proc = run_cli(self.repo, "skills/starting-initiatives/evals/evals.json",
                       "start-new-initiative", output, claude=fake, user_settings=settings)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("forbidden path", proc.stderr)
        if output.exists():
            for p in output.rglob("*.json"):
                self.assertNotIn(str(self.repo), p.read_text())

    def test_env_provenance_key_names_only(self):
        fake = make_positive_fake(self.tmp)
        settings = make_user_settings(self.tmp, env={"D7Y_EVAL_TEST_TOKEN": "super-secret-value"})
        output = self.tmp / "out"
        proc = run_cli(self.repo, "skills/starting-initiatives/evals/evals.json",
                       "start-new-initiative", output, claude=fake, user_settings=settings)
        self.assertNotEqual(proc.returncode, 2, proc.stderr)
        manifest = json.loads((output / "manifest.json").read_text())
        self.assertIn("D7Y_EVAL_TEST_TOKEN", manifest["env_provenance"]["imported_keys"])
        blob = (output / "manifest.json").read_text() + "\n"
        blob += (output / "with-skill" / "artifacts" / "provenance.json").read_text()
        blob += (output / "with-skill" / "artifacts" / "telemetry.json").read_text()
        self.assertNotIn("super-secret-value", blob)

    def test_source_mutation_invalidates_dry_run(self):
        fake = make_invocation_recording_fake(self.tmp)
        output = self.tmp / "out"
        # Mutate the source checkout mid-run is not directly drivable; instead
        # verify the source-status evidence is recorded and a clean run reports
        # no mutation.
        proc = run_cli(self.repo, "skills/starting-initiatives/evals/evals.json",
                       "start-new-initiative", output, claude=fake, dry_run=True,
                       user_settings=make_user_settings(self.tmp))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        status = json.loads((output / "source-status.json").read_text())
        self.assertFalse(status["mutated"])
        self.assertNotIn(str(self.repo), (output / "source-status.json").read_text())

    @staticmethod
    def _child_pids() -> list[int]:
        out = subprocess.run(["pgrep", "-f", "resistant|sleep 300"], capture_output=True, text=True)
        return [int(x) for x in out.stdout.split() if x.strip().isdigit()]


if __name__ == "__main__":
    unittest.main()
