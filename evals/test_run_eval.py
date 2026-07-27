#!/usr/bin/env python3
"""End-to-end tests for the minimal D7Y skill eval runner.

Most tests drive the public CLI (``evals/run_eval.py``) through ``subprocess``
against disposable committed Git repositories, so they exercise the real
ownership boundary. A small number of narrow unit tests cover parser and path
primitives directly. Fake Claude executables and a synthetic user settings file
stand in for the live runtime; no live Claude is ever invoked.
"""

from __future__ import annotations

import json
import os
import shutil
import signal
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

VALID_INITIATIVE_MD = textwrap.dedent(
    """\
    ---
    title: Consultant call-to-proposal discovery
    status: active
    created: 2026-07-27
    updated: 2026-07-27
    aliases: []
    related: []
    ---

    # Consultant call-to-proposal discovery

    ## Provisional intent

    ### Outcome

    Investigate whether independent consultants need an agent-assisted way to turn
    client calls into scoped proposals.

    ### Subject

    Independent consultants who sell scoped work.

    ### Constraints and anti-goals

    Unknown.

    ## Primary uncertainty

    Whether the bottleneck is capturing call content or scoping it into a proposal.

    ## Current understanding

    ### Evidence

    None yet.

    ### Assumptions

    Consultants lose dealable context between call and proposal.

    ## Current state

    Next move: interview three consultants about their call-to-proposal handoff.
    """
)


def _write_canonical_repo(repo: Path) -> None:
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


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, check=True
    )
    return result.stdout.strip()


def make_repo(tmp: Path) -> tuple[Path, str]:
    """Create and commit a disposable canonical repo; return (path, commit)."""
    repo = tmp / "repo"
    repo.mkdir(parents=True)
    _git(repo, "init")
    _git(repo, "config", "user.email", "eval@example.com")
    _git(repo, "config", "user.name", "Eval")
    _write_canonical_repo(repo)
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
# Fake Claude executables.
# ---------------------------------------------------------------------------


def _write_fake_claude(path: Path, body: str, *, version: str = "2.1.218") -> None:
    # Every live-run fake must answer the one-time executable version probe so
    # the harness resolves it once for both arms, then do its real behavior.
    version_guard = (
        "import sys as _sys\n"
        "if '--version' in _sys.argv:\n"
        f"    print('Claude Code {version}')\n"
        "    _sys.exit(0)\n"
    )
    full = "#!/usr/bin/env python3\n" + version_guard + body
    path.write_text(full)
    path.chmod(0o755)


def make_positive_fake(tmp: Path) -> Path:
    """A fake claude that invokes the skill on positive prompts and does the work.

    The with-skill arm on a positive prompt: emits target Skill invocation, the
    required d7y list/check Bash commands, writes one valid initiative into the
    target workspace, and emits a successful result. The baseline arm emits no
    target invocation. Negative prompts never invoke even with the skill.
    """
    fake = tmp / "claude"
    _write_fake_claude(
        fake,
        textwrap.dedent(
            """
            import json, os, sys

            argv = sys.argv[1:]
            plugin = None
            root = None
            prompt = ""
            after = False
            for i, a in enumerate(argv):
                if a == "--plugin-dir" and i + 1 < len(argv):
                    plugin = argv[i + 1]
                elif a == "--root" and i + 1 < len(argv):
                    root = argv[i + 1]
                elif a == "--":
                    after = True
                elif after:
                    prompt += a + " "

            has_skill = bool(plugin and os.path.exists(os.path.join(plugin, "skills", "starting-initiatives", "SKILL.md")))
            positive = "start an initiative" in prompt
            sid = f"fake-{os.getpid()}-{has_skill}"
            tools = ["Skill", "Read", "Write", "Edit", "Bash"]
            plugin_name = "d7y-eval-session" if has_skill else "d7y-eval-control"
            skills = ["doctor"]
            if has_skill:
                skills = ["d7y-eval-session:starting-initiatives", "doctor"]
            init = {"type": "system", "subtype": "init", "session_id": sid, "tools": tools,
                    "model": "claude-sonnet-5", "skills": skills,
                    "plugins": [{"name": plugin_name, "path": plugin or "", "version": "0.0.1"}],
                    "mcp_servers": [], "permissionMode": "dontAsk"}
            print(json.dumps(init))
            events = []
            if has_skill and positive:
                events.append({"type": "assistant", "message": {"role": "assistant", "model": "glm-4.7",
                    "content": [{"type": "tool_use", "id": "c1", "name": "Skill",
                    "input": {"skill": "d7y-eval-session:starting-initiatives"}}]}})
                if root:
                    events.append({"type": "assistant", "message": {"role": "assistant", "model": "glm-4.7",
                        "content": [{"type": "tool_use", "id": "c2", "name": "Bash",
                        "input": {"command": f"d7y initiatives list --root {root} --json"}}]}})
                    events.append({"type": "assistant", "message": {"role": "assistant", "model": "glm-4.7",
                        "content": [{"type": "tool_use", "id": "c3", "name": "Bash",
                        "input": {"command": f"d7y initiatives check --root {root} --json"}}]}})
                    slug = "consultant-proposals"
                    idir = os.path.join(root, "initiatives", slug)
                    os.makedirs(idir, exist_ok=True)
                    md = ("---\\ntitle: Consultant proposals\\nstatus: active\\ncreated: 2026-07-27\\n"
                          "updated: 2026-07-27\\naliases: []\\nrelated: []\\n---\\n\\n"
                          "# Consultant proposals\\n\\n## Provisional intent\\n\\n### Outcome\\n\\nFind need.\\n\\n"
                          "### Subject\\n\\nConsultants.\\n\\n### Constraints and anti-goals\\n\\nUnknown.\\n\\n"
                          "## Primary uncertainty\\n\\nNeed.\\n\\n## Current understanding\\n\\n### Evidence\\n\\n"
                          "None.\\n\\n### Assumptions\\n\\nSome.\\n\\n## Current state\\n\\nNext.\\n")
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
                    "content": [{"type": "tool_use", "id": "b1", "name": "Skill", "input": {"skill": "list"}}]}})
                final = "No applicable skill."
            for e in events:
                print(json.dumps(e))
            result = {"type": "result", "subtype": "success", "result": final, "is_error": False,
                      "num_turns": len(events) + 1, "permission_denials": [],
                      "modelUsage": {"claude-sonnet-5": {"provider": "firstParty", "canonicalModel": "claude-sonnet-5"}}}
            print(json.dumps(result))
            sys.exit(0)
            """
        ),
    )
    return fake


def make_invocation_recording_fake(tmp: Path) -> Path:
    """A fake claude that records any version/run invocation; never emits success."""
    fake = tmp / "claude"
    log = tmp / "claude-invocations.log"
    _write_fake_claude(
        fake,
        textwrap.dedent(
            f"""
            import sys, os, json
            log = {str(log)!r}
            with open(log, "a") as f:
                f.write(json.dumps(sys.argv[1:]) + "\\n")
            sys.exit(0)
            """
        ),
    )
    return fake


def make_resistant_fake(tmp: Path) -> Path:
    """A fake claude that forks a SIGTERM-resistant child and hangs."""
    fake = tmp / "claude"
    _write_fake_claude(
        fake,
        textwrap.dedent(
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
        ),
    )
    return fake


def make_malformed_fake(tmp: Path) -> Path:
    fake = tmp / "claude"
    _write_fake_claude(
        fake,
        textwrap.dedent(
            """
            import sys
            print('{"type": "system", "subtype": "init"}')
            print('this is not json')
            sys.exit(0)
            """
        ),
    )
    return fake


def make_nonzero_fake(tmp: Path) -> Path:
    fake = tmp / "claude"
    _write_fake_claude(fake, "import sys\nprint('boom')\nsys.exit(3)\n")
    return fake


# ---------------------------------------------------------------------------
# Narrow unit tests: parser and path primitives.
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

    def test_canary_leakage_detection(self):
        leak_init = [{"type": "system", "subtype": "init",
                      "skills": ["doctor", run_eval.FAKE_GLOBAL_SKILL_NAME]}]
        clean, issues = run_eval.check_canary_leakage(leak_init)
        self.assertFalse(clean)
        leak_text = [{"type": "assistant", "message": {"content": [
            {"type": "text", "text": "see " + run_eval.PROJECT_INSTRUCTION_CANARY}]}}]
        clean2, issues2 = run_eval.check_canary_leakage(leak_text)
        self.assertFalse(clean2)

    def test_routed_model_extraction(self):
        events = [{"type": "assistant", "message": {"model": "glm-4.7", "content": []}}]
        self.assertEqual(run_eval.extract_routed_models(events), ["glm-4.7"])


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
        return [init, result]

    def test_valid_with_skill(self):
        v = run_eval.validate_arm_events(
            self._events(), with_skill=True, skill_name="starting-initiatives",
            expected_plugin="d7y-eval-session", other_session_id=None)
        self.assertTrue(v.ok, v.errors)

    def test_duplicate_init_rejected(self):
        events = self._events() + [{"type": "system", "subtype": "init", "session_id": "s2",
                                    "tools": [], "model": "x", "skills": [], "plugins": [],
                                    "mcp_servers": [], "permissionMode": "x"}]
        v = run_eval.validate_arm_events(events, with_skill=True, skill_name="starting-initiatives",
                                        expected_plugin="d7y-eval-session", other_session_id=None)
        self.assertFalse(v.ok)

    def test_shared_session_rejected(self):
        v = run_eval.validate_arm_events(
            self._events(init={"session_id": "shared"}),
            with_skill=False, skill_name="starting-initiatives",
            expected_plugin="d7y-eval-control", other_session_id="shared")
        self.assertFalse(v.ok)

    def test_full_tool_set_required(self):
        events = self._events(init={"tools": ["Skill"]})
        v = run_eval.validate_arm_events(events, with_skill=True, skill_name="starting-initiatives",
                                        expected_plugin="d7y-eval-session", other_session_id=None)
        self.assertFalse(v.ok)

    def test_routed_glm_allowed(self):
        events = self._events()
        events.insert(1, {"type": "assistant", "message": {"model": "glm-4.7", "content": []}})
        v = run_eval.validate_arm_events(events, with_skill=True, skill_name="starting-initiatives",
                                        expected_plugin="d7y-eval-session", other_session_id=None)
        self.assertTrue(v.ok, v.errors)


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

    def test_dry_run_complete_preflight_zero_invocations(self):
        fake = make_invocation_recording_fake(self.tmp)
        output = self.tmp / "out"
        proc = run_cli(self.repo, "skills/starting-initiatives/evals/evals.json",
                       "start-new-initiative", output, claude=fake, dry_run=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        log = self.tmp / "claude-invocations.log"
        self.assertFalse(log.exists(), "dry-run must not invoke or version-probe the executable")
        manifest = json.loads((output / "manifest.json").read_text())
        self.assertEqual(manifest["commit"], self.commit)
        self.assertTrue(manifest["dry_run"])
        self.assertIsNone(manifest["executable"])
        # Authentic plugin tree with .claude-plugin/plugin.json + skills/.../SKILL.md.
        plugin_skill = output / "with-skill" / "plugin" / "skills" / "starting-initiatives" / "SKILL.md"
        self.assertTrue(plugin_skill.exists())
        plugin_json = output / "with-skill" / "plugin" / ".claude-plugin" / "plugin.json"
        self.assertEqual(json.loads(plugin_json.read_text())["name"], "d7y-eval-session")
        self.assertFalse((output / "baseline" / "plugin" / "skills").exists())
        # Roots are distinct.
        roots = manifest["roots"]
        self.assertNotEqual(roots["with_skill_workspace"], roots["baseline_workspace"])
        self.assertNotEqual(roots["with_skill_plugin"], roots["with_skill_workspace"])
        # No plugin/settings/canary/control file inside a target workspace.
        for ws in (output / "with-skill" / "workspace", output / "baseline" / "workspace"):
            for p in ws.rglob("*"):
                self.assertNotIn(p.name, {".claude-plugin", "settings.json", "CLAUDE.md"})
        # Both D7Y capability objects materialized with real object IDs.
        caps = manifest["capability_object_ids"]
        self.assertIn("d7y", caps)
        self.assertIn("scripts/check-initiatives.py", caps)
        # Seed README staged in both workspaces.
        self.assertTrue((output / "with-skill" / "workspace" / "initiatives" / "README.md").exists())
        # Source checkout unchanged.
        self.assertEqual(_git(self.repo, "status", "--porcelain"), "")

    def test_dry_run_argv_uses_one_tools_value_and_root(self):
        fake = make_invocation_recording_fake(self.tmp)
        output = self.tmp / "out"
        proc = run_cli(self.repo, "skills/starting-initiatives/evals/evals.json",
                       "start-new-initiative", output, claude=fake, dry_run=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        # Dry-run records intended argv (no probe): reconstruct from build helper.
        argv = run_eval.build_claude_argv(
            claude_path=str(fake),
            settings_path=output / "harness-settings.json",
            plugin_root=output / "with-skill" / "plugin",
            workspace=output / "with-skill" / "workspace",
            prompt="anything",
        )
        self.assertEqual(argv.count("--tools"), 1)
        tools_idx = argv.index("--tools")
        self.assertEqual(argv[tools_idx + 1], run_eval.EXPECTED_TOOLS_ARG)
        self.assertNotIn("--allow-tool", argv)
        self.assertIn("--root", argv)
        self.assertIn("--plugin-dir", argv)
        self.assertIn("--model", argv)
        self.assertEqual(argv[argv.index("--model") + 1], run_eval.EXPECTED_MODEL)

    def test_live_positive_case_passes_end_to_end(self):
        fake = make_positive_fake(self.tmp)
        settings = make_user_settings(self.tmp)
        output = self.tmp / "out"
        proc = run_cli(self.repo, "skills/starting-initiatives/evals/evals.json",
                       "start-new-initiative", output, claude=fake, user_settings=settings)
        # The positive case has a required rubric assertion that stays pending,
        # which by contract blocks case pass and a zero exit even when every
        # deterministic assertion passes.
        self.assertEqual(proc.returncode, 1, proc.stderr + "\n" + (output / "summary.md").read_text())
        checks = json.loads((output / "checks.json").read_text())
        self.assertEqual(checks["pair_validity"]["status"], "pass", checks["pair_validity"])
        self.assertEqual(checks["treatment_checks"]["status"], "pass")
        self.assertFalse(checks["case_pass"])
        # Every required deterministic assertion passed.
        for a in checks["with_skill_assertions"]:
            if a["required"] and a["kind"] == "deterministic":
                self.assertEqual(a["status"], "pass", a)
        # The only blocker is the required rubric pending assertion.
        rubric = next(a for a in checks["with_skill_assertions"] if a["kind"] == "rubric")
        self.assertEqual(rubric["status"], "pending")
        self.assertTrue(checks["blocking"])
        # Complete per-arm artifact tree exists.
        for arm in ("with-skill", "baseline"):
            d = output / arm / "artifacts"
            for name in ("trace.jsonl", "stderr.txt", "telemetry.json", "provenance.json",
                         "command-events.json", "checker.json", "workspace-changes.json",
                         "validation.json", "process.json"):
                self.assertTrue((d / name).exists(), name)
        # Routed model recorded separately from canonical.
        tel = json.loads((output / "with-skill" / "artifacts" / "telemetry.json").read_text())
        self.assertEqual(tel["canonical_model"], "claude-sonnet-5")
        self.assertIn("glm-4.7", tel["routed_models"])
        # Command-event evidence separate from independent checker evidence.
        cmds = json.loads((output / "with-skill" / "artifacts" / "command-events.json").read_text())
        self.assertTrue(cmds["list"] and cmds["check"])
        checker = json.loads((output / "with-skill" / "artifacts" / "checker.json").read_text())
        self.assertTrue(checker["valid"])
        self.assertIsInstance(checker["argv"], list)
        # Version probed exactly once (both arms share one executable record).
        prov = json.loads((output / "with-skill" / "artifacts" / "provenance.json").read_text())
        self.assertEqual(prov["executable_version"], "Claude Code 2.1.218")
        self.assertEqual(prov["executable"], prov["executable"])  # absolute, reused
        # The committed D7Y capability bound exactly one absolute executable path.
        self.assertTrue(prov["executable"].startswith("/"))
        # Source unchanged.
        self.assertEqual(_git(self.repo, "status", "--porcelain"), "")

    def test_live_negative_case_requires_absence(self):
        fake = make_positive_fake(self.tmp)
        settings = make_user_settings(self.tmp)
        output = self.tmp / "out"
        proc = run_cli(self.repo, "skills/starting-initiatives/evals/evals.json",
                       "casual-brainstorm", output, claude=fake, user_settings=settings)
        # Negative control: skill available but not invoked -> case still passes
        # because absence is the expected deterministic outcome.
        self.assertEqual(proc.returncode, 0, proc.stderr)
        checks = json.loads((output / "checks.json").read_text())
        inv = next(a for a in checks["with_skill_assertions"] if a["id"] == "does-not-invoke")
        self.assertEqual(inv["status"], "pass", inv)

    def test_dirty_worktree_replacements_ignored(self):
        fake = make_positive_fake(self.tmp)
        settings = make_user_settings(self.tmp)
        output = self.tmp / "out"
        proc = run_cli(self.repo, "skills/starting-initiatives/evals/evals.json",
                       "start-new-initiative", output, claude=fake, user_settings=settings)
        self.assertNotEqual(proc.returncode, 2, proc.stderr)  # preflight ok
        staged = json.loads((output / "manifest.json").read_text())["selected_objects"]["with_skill"]
        committed_ids = {obj["object_id"] for obj in staged}
        # Now dirty the working tree; rerun uses committed objects only.
        (self.repo / "initiatives" / "README.md").write_text("DIRTY OVERRIDE")
        output2 = self.tmp / "out2"
        proc2 = run_cli(self.repo, "skills/starting-initiatives/evals/evals.json",
                        "start-new-initiative", output2, claude=fake, user_settings=settings)
        self.assertNotEqual(proc2.returncode, 2, proc2.stderr)
        staged2 = json.loads((output2 / "manifest.json").read_text())["selected_objects"]["with_skill"]
        self.assertEqual({obj["object_id"] for obj in staged2}, committed_ids)
        # The staged README in the workspace matches committed content, not dirty.
        ws_readme = output2 / "with-skill" / "workspace" / "initiatives" / "README.md"
        self.assertNotIn("DIRTY OVERRIDE", ws_readme.read_text())

    def test_committed_symlink_in_skill_rejected(self):
        # Add a symlink inside the skill tree and commit it.
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

    def test_output_inside_source_rejected(self):
        fake = make_invocation_recording_fake(self.tmp)
        output = self.repo / "inside-output"
        proc = run_cli(self.repo, "skills/starting-initiatives/evals/evals.json",
                       "start-new-initiative", output, claude=fake, dry_run=True)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("output root", proc.stderr)

    def test_stale_output_rejected(self):
        fake = make_invocation_recording_fake(self.tmp)
        output = self.tmp / "stale"
        output.mkdir()
        (output / "leftover.txt").write_text("x")
        proc = run_cli(self.repo, "skills/starting-initiatives/evals/evals.json",
                       "start-new-initiative", output, claude=fake, dry_run=True)
        self.assertNotEqual(proc.returncode, 0)

    def test_env_path_leak_rejected(self):
        fake = make_positive_fake(self.tmp)
        # User settings whose value contains the source repo path -> rejected.
        settings = make_user_settings(self.tmp, env={"LEAK_VAR": str(self.repo)})
        output = self.tmp / "out"
        proc = run_cli(self.repo, "skills/starting-initiatives/evals/evals.json",
                       "start-new-initiative", output, claude=fake, user_settings=settings)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("forbidden path", proc.stderr)
        # Artifacts never contain the value.
        if output.exists():
            for p in output.rglob("*.json"):
                self.assertNotIn(str(self.repo), p.read_text())

    def test_env_provenance_key_names_only(self):
        fake = make_positive_fake(self.tmp)
        settings = make_user_settings(self.tmp, env={"D7Y_EVAL_TEST_TOKEN": "super-secret-value"})
        output = self.tmp / "out"
        proc = run_cli(self.repo, "skills/starting-initiatives/evals/evals.json",
                       "start-new-initiative", output, claude=fake, user_settings=settings)
        # Exit may be nonzero (required rubric pending), but preflight must pass.
        self.assertNotEqual(proc.returncode, 2, proc.stderr)
        manifest = json.loads((output / "manifest.json").read_text())
        prov = manifest["env_provenance"]
        self.assertIn("D7Y_EVAL_TEST_TOKEN", prov["imported_keys"])
        blob = (output / "manifest.json").read_text() + "\n"
        blob += (output / "with-skill" / "artifacts" / "provenance.json").read_text()
        blob += (output / "with-skill" / "artifacts" / "telemetry.json").read_text()
        self.assertNotIn("super-secret-value", blob)

    def test_executable_version_probe_required(self):
        # Wrong-version fake -> live run fails; version probed at most once.
        wrong = self.tmp / "claude"
        wrong.write_text("#!/bin/sh\necho 'Claude Code 1.0.0'\n")
        wrong.chmod(0o755)
        output = self.tmp / "out"
        proc = run_cli(self.repo, "skills/starting-initiatives/evals/evals.json",
                       "start-new-initiative", output, claude=wrong,
                       user_settings=make_user_settings(self.tmp))
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("2.1.218", proc.stderr)

    def test_nonzero_run_still_writes_artifacts_and_exits_nonzero(self):
        fake = make_nonzero_fake(self.tmp)
        settings = make_user_settings(self.tmp)
        output = self.tmp / "out"
        proc = run_cli(self.repo, "skills/starting-initiatives/evals/evals.json",
                       "start-new-initiative", output, claude=fake, user_settings=settings)
        self.assertNotEqual(proc.returncode, 0)
        # Partial artifacts still present.
        for arm in ("with-skill", "baseline"):
            self.assertTrue((output / arm / "artifacts" / "process.json").exists())
        checks = json.loads((output / "checks.json").read_text())
        self.assertEqual(checks["pair_validity"]["status"], "fail")

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
        # Give the OS a moment, then assert no resistant child survived.
        time.sleep(1.0)
        after = set(self._child_pids())
        leftover = after - before
        self.assertFalse(leftover, f"child processes survived timeout: {leftover}")
        proc_json = json.loads((output / "with-skill" / "artifacts" / "process.json").read_text())
        self.assertTrue(proc_json["timed_out"])
        self.assertIsNotNone(proc_json["pid"])

    def test_canary_leak_in_run_fails_pair(self):
        # Fake that emits the canary skill in init -> pair validity fails.
        fake = self.tmp / "claude"
        body = (
            "import json, sys, os\n"
            "tools=['Skill','Read','Write','Edit','Bash']\n"
            "print(json.dumps({'type':'system','subtype':'init','session_id':'s','tools':tools,"
            "'model':'claude-sonnet-5','skills':['doctor', %r],"
            "'plugins':[{'name':'d7y-eval-session'}],'mcp_servers':[],'permissionMode':'dontAsk'}))\n"
            "print(json.dumps({'type':'result','subtype':'success','result':'x','is_error':False,"
            "'num_turns':1,'permission_denials':[],'modelUsage':{'claude-sonnet-5':{}}}))\n"
            "sys.exit(0)\n"
        ) % run_eval.FAKE_GLOBAL_SKILL_NAME
        _write_fake_claude(fake, body)
        settings = make_user_settings(self.tmp)
        output = self.tmp / "out"
        proc = run_cli(self.repo, "skills/starting-initiatives/evals/evals.json",
                       "start-new-initiative", output, claude=fake, user_settings=settings)
        self.assertNotEqual(proc.returncode, 0)
        checks = json.loads((output / "checks.json").read_text())
        self.assertEqual(checks["pair_validity"]["status"], "fail")

    @staticmethod
    def _child_pids() -> list[int]:
        out = subprocess.run(["pgrep", "-f", "resistant|sleep 300"], capture_output=True, text=True)
        return [int(x) for x in out.stdout.split() if x.strip().isdigit()]


class TestFixtureStagingSafety(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="d7y-eval-"))
        self.repo, self.commit = make_repo(self.tmp)

    def tearDown(self):
        if self.tmp.exists():
            shutil.rmtree(self.tmp)

    def test_duplicate_destination_detected(self):
        case = {"files": [{"source": "evals/files/customer-interview-analysis.md", "destination": "a/b.md"},
                          {"source": "evals/files/customer-interview-analysis.md", "destination": "a/b.md"}]}
        ws = self.tmp / "ws"
        ws.mkdir()
        with self.assertRaises(run_eval.PreflightError):
            run_eval.stage_workspace_seed(
                ws, case=case, repo=self.repo, commit=self.commit,
                skill_repo_dir="skills/starting-initiatives", seed_repo_paths=[])

    def test_control_destination_collision_detected(self):
        case = {"files": [{"source": "evals/files/customer-interview-analysis.md", "destination": "settings.json"}]}
        ws = self.tmp / "ws"
        ws.mkdir()
        with self.assertRaises(run_eval.PreflightError):
            run_eval.stage_workspace_seed(
                ws, case=case, repo=self.repo, commit=self.commit,
                skill_repo_dir="skills/starting-initiatives", seed_repo_paths=[])


if __name__ == "__main__":
    unittest.main()
