#!/usr/bin/env python3
"""End-to-end tests for the minimal D7Y skill eval runner.

Most tests drive the public CLI (``evals/run_eval.py``) through ``subprocess``
against disposable committed Git repositories, so they exercise the real
ownership boundary. Behavioral fake executors are standalone scripts: they
independently recognize the concrete Claude 2.1.218 option surface, reject
unknown options (including an invented ``--root``), derive the workspace only
from the neutral prompt contract, and record their own invocation log that tests
inspect directly. They never import ``evals.run_eval`` or any production helper.
A few narrow unit tests import production parser/path primitives directly.
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
import run_eval  # noqa: E402  (narrow unit tests + authoritative inventory list)


# ---------------------------------------------------------------------------
# Disposable committed repositories and CLI driver.
# ---------------------------------------------------------------------------


def _write_canonical_repo(repo: Path, *, include_wgs: bool = False) -> None:
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
        sys.executable, str(RUNNER), "--source-repo", str(repo),
        "--suite", suite, "--case", case, "--output", str(output),
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
# Standalone (production-independent) fake Claude executors.
#
# Each fake answers the one-time --version probe, then parses its argv with an
# independent strict parser that recognizes the exact concrete Claude 2.1.218
# option surface in order, rejects any unknown option (including --root), and
# derives the workspace only from the neutral prompt contract. It records its
# own invocation to a log file that tests inspect directly.
# ---------------------------------------------------------------------------

_PRELUDE = '''#!/usr/bin/env python3
import sys, os, json, re, glob

if "--version" in sys.argv:
    print("Claude Code 2.1.218")
    sys.exit(0)

LOG = __LOG__
EXPECTED = [
    ("--print", "bool", None),
    ("--verbose", "bool", None),
    ("--output-format", "value", "stream-json"),
    ("--no-session-persistence", "bool", None),
    ("--strict-mcp-config", "bool", None),
    ("--mcp-config", "value", '{"mcpServers":{}}'),
    ("--permission-mode", "value", "dontAsk"),
    ("--model", "value", "claude-sonnet-5"),
    ("--effort", "value", "low"),
    ("--setting-sources", "value", "project"),
    ("--settings", "value", None),
    ("--plugin-dir", "value", None),
    ("--tools", "value", "Skill,Read,Write,Edit,Bash"),
]


def _record(d):
    try:
        with open(LOG, "a") as f:
            f.write(json.dumps(d) + "\\n")
    except Exception:
        pass


def _parse(argv):
    toks = list(argv)
    i = 0
    settings = None
    plugin = None
    for flag, kind, fixed in EXPECTED:
        if i >= len(toks) or toks[i] != flag:
            cur = toks[i] if i < len(toks) else "EOF"
            return None, "expected " + flag + " before " + str(cur), None, None, None
        i += 1
        if kind == "value":
            if i >= len(toks):
                return None, "missing value for " + flag, None, None, None
            val = toks[i]
            i += 1
            if fixed is not None and val != fixed:
                return None, "bad value for " + flag + ": " + str(val), None, None, None
            if flag == "--settings":
                settings = val
            elif flag == "--plugin-dir":
                plugin = val
    if i >= len(toks) or toks[i] != "--":
        cur = toks[i] if i < len(toks) else "EOF"
        return None, "expected -- separator before " + str(cur), None, None, None
    i += 1
    prompt = " ".join(toks[i:])
    m = re.search(r"Target workspace root: (\\S+)", prompt)
    root = m.group(1) if m else None
    return prompt, None, root, settings, plugin


_argv = sys.argv[1:]
_prompt, _err, _root, _settings, _plugin = _parse(_argv)
_record({"argv": _argv, "ok": _err is None, "error": _err, "workspace": _root,
         "settings": _settings, "plugin_dir": _plugin, "prompt": _prompt})
if _err is not None:
    sys.stderr.write("fake argv rejected: " + _err + "\\n")
    sys.exit(2)

# behavior appended below
'''


def _write_fake(tmp: Path, name: str, behavior: str) -> tuple[Path, Path]:
    log = tmp / (name + ".log")
    fake = tmp / (name + "-claude")
    fake.write_text(_PRELUDE.replace("__LOG__", repr(str(log))) + behavior)
    fake.chmod(0o755)
    return fake, log


_VALID_INITIATIVE_LINES = [
    "---", "title: Consultant proposals", "status: active", "created: 2026-07-27",
    "updated: 2026-07-27", "aliases: []", "related: []", "---", "",
    "# Consultant proposals", "", "## Provisional intent", "", "### Outcome", "",
    "Find need.", "", "### Subject", "", "Consultants.", "",
    "### Constraints and anti-goals", "", "Unknown.", "", "## Primary uncertainty",
    "", "Need.", "", "## Current understanding", "", "### Evidence", "", "None.",
    "", "### Assumptions", "", "Some.", "", "## Current state", "", "Next.", "",
]


def _valid_initiative_text():
    return "\n".join(_VALID_INITIATIVE_LINES)


def make_positive_fake(tmp: Path) -> tuple[Path, Path]:
    behavior = (
        "import glob as _glob\n"
        "_matches = _glob.glob(os.path.join(_plugin or '', 'skills', '*', 'SKILL.md')) if _plugin else []\n"
        "_has_skill = bool(_matches)\n"
        "_skill_name = os.path.basename(os.path.dirname(_matches[0])) if _matches else None\n"
        "_target = ('d7y-eval-session:' + _skill_name) if _has_skill else None\n"
        "_skills = [_target, 'doctor'] if _has_skill else ['doctor']\n"
        "_pname = 'd7y-eval-session' if _has_skill else 'd7y-eval-control'\n"
        "_sid = 'pos-' + str(os.getpid()) + '-' + str(_has_skill)\n"
        "print(json.dumps({'type': 'system', 'subtype': 'init', 'session_id': _sid, "
        "'tools': ['Skill', 'Read', 'Write', 'Edit', 'Bash'], 'model': 'claude-sonnet-5', "
        "'skills': _skills, 'plugins': [{'name': _pname, 'path': _plugin or '', 'version': '0.0.1'}], "
        "'mcp_servers': [], 'permissionMode': 'dontAsk'}))\n"
        "_events = []\n"
        "_final = 'Done.'\n"
        "_positive = ('start an initiative' in (_prompt or ''))\n"
        "if _has_skill and _positive:\n"
        "    _events.append({'type': 'assistant', 'message': {'role': 'assistant', 'model': 'glm-4.7',\n"
        "        'content': [{'type': 'tool_use', 'id': 'c1', 'name': 'Skill', 'input': {'skill': _target}}]}})\n"
        "    if _root:\n"
        "        _events.append({'type': 'assistant', 'message': {'role': 'assistant', 'model': 'glm-4.7',\n"
        "            'content': [{'type': 'tool_use', 'id': 'c2', 'name': 'Bash',\n"
        "            'input': {'command': 'd7y initiatives list --root ' + _root + ' --json'}}]}})\n"
        "        _events.append({'type': 'assistant', 'message': {'role': 'assistant', 'model': 'glm-4.7',\n"
        "            'content': [{'type': 'tool_use', 'id': 'c3', 'name': 'Bash',\n"
        "            'input': {'command': 'd7y initiatives check --root ' + _root + ' --json'}}]}})\n"
        "        _lj = json.dumps({'version': 1, 'root': _root, 'valid': True, 'count': 0, 'errors': [], 'warnings': [], 'initiatives': []})\n"
        "        _cj = json.dumps({'version': 1, 'root': _root, 'valid': True, 'count': 1, 'errors': [], 'warnings': [], 'initiatives': [{'slug': 'consultant-proposals', 'valid': True}]})\n"
        "        _events.append({'type': 'user', 'message': {'role': 'user', 'content': [{'type': 'tool_result', 'tool_use_id': 'c2', 'content': _lj, 'is_error': False}]}})\n"
        "        _events.append({'type': 'user', 'message': {'role': 'user', 'content': [{'type': 'tool_result', 'tool_use_id': 'c3', 'content': _cj, 'is_error': False}]}})\n"
        "        _idir = os.path.join(_root, 'initiatives', 'consultant-proposals')\n"
        "        os.makedirs(_idir, exist_ok=True)\n"
        "        open(os.path.join(_idir, 'initiative.md'), 'w').write(" + _VALID_INITIATIVE_PY + ")\n"
        "        _final = 'Created one initiative.'\n"
        "elif _has_skill and not _positive:\n"
        "    _events.append({'type': 'assistant', 'message': {'role': 'assistant', 'model': 'glm-4.7',\n"
        "        'content': [{'type': 'text', 'text': 'Just brainstorming names.'}]}})\n"
        "    _final = 'Ten names.'\n"
        "else:\n"
        "    _events.append({'type': 'assistant', 'message': {'role': 'assistant', 'model': 'glm-4.7',\n"
        "        'content': [{'type': 'tool_use', 'id': 'b1', 'name': 'Skill', 'input': {'skill': 'list'}}]}})\n"
        "    _final = 'No applicable skill.'\n"
        "for _e in _events:\n"
        "    print(json.dumps(_e))\n"
        "print(json.dumps({'type': 'result', 'subtype': 'success', 'result': _final, 'is_error': False,\n"
        "    'num_turns': len(_events) + 1, 'permission_denials': [],\n"
        "    'modelUsage': {'claude-sonnet-5': {'provider': 'firstParty', 'canonicalModel': 'claude-sonnet-5'}}}))\n"
        "sys.exit(0)\n"
    )
    return _write_fake(tmp, "positive", behavior)


# ---------------------------------------------------------------------------
# Simpler behavior builders for the remaining fakes.
# ---------------------------------------------------------------------------


def make_invocation_recording_fake(tmp: Path) -> Path:
    # Records argv via the shared prelude log; never emits a stream.
    return _write_fake(tmp, "rec", "sys.exit(0)\n")[0]


def make_nonzero_fake(tmp: Path) -> Path:
    return _write_fake(tmp, "nonzero", "print('boom')\nsys.exit(3)\n")[0]


def make_malformed_fake(tmp: Path) -> Path:
    return _write_fake(
        tmp, "malformed",
        'print(\'{"type": "system", "subtype": "init"}\')\n'
        "print('this is not json')\nsys.exit(0)\n",
    )[0]


def make_resistant_fake(tmp: Path) -> Path:
    return _write_fake(
        tmp, "resistant",
        "import signal, time\n"
        "child = os.fork()\n"
        "if child == 0:\n"
        "    signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
        "    signal.signal(signal.SIGINT, signal.SIG_IGN)\n"
        "    time.sleep(300)\n"
        "    sys.exit(0)\n"
        "print('{\"type\": \"system\", \"subtype\": \"init\", \"session_id\": \"r\"}')\n"
        "sys.stdout.flush()\n"
        "time.sleep(300)\n"
        "sys.exit(0)\n",
    )[0]


def make_redaction_fake(tmp: Path) -> Path:
    secret_ref = "os.environ.get('D7Y_EVAL_TEST_TOKEN', '')"
    behavior = (
        "import glob as _glob\n"
        "_matches = _glob.glob(os.path.join(_plugin or '', 'skills', '*', 'SKILL.md')) if _plugin else []\n"
        "_has_skill = bool(_matches)\n"
        "_skill_name = os.path.basename(os.path.dirname(_matches[0])) if _matches else None\n"
        "_target = ('d7y-eval-session:' + _skill_name) if _has_skill else None\n"
        "_skills = [_target, 'doctor'] if _has_skill else ['doctor']\n"
        "_pname = 'd7y-eval-session' if _has_skill else 'd7y-eval-control'\n"
        "_sid = 'red-' + str(os.getpid())\n"
        "_secret = " + secret_ref + "\n"
        "print(json.dumps({'type': 'system', 'subtype': 'init', 'session_id': _sid, "
        "'tools': ['Skill', 'Read', 'Write', 'Edit', 'Bash'], 'model': 'claude-sonnet-5', "
        "'skills': _skills, 'plugins': [{'name': _pname, 'path': _plugin or '', 'version': '0.0.1'}], "
        "'mcp_servers': [], 'permissionMode': 'dontAsk'}))\n"
        # secret in raw stdout (assistant text), a tool_result, and the final response.
        "print(json.dumps({'type': 'assistant', 'message': {'role': 'assistant', 'model': 'glm-4.7',\n"
        "    'content': [{'type': 'tool_use', 'id': 'x1', 'name': 'Bash', 'input': {'command': 'true'}}]}}))\n"
        "print(json.dumps({'type': 'user', 'message': {'role': 'user', 'content': [{'type': 'tool_result',\n"
        "    'tool_use_id': 'x1', 'content': 'saw ' + _secret, 'is_error': False}]}}))\n"
        "print(json.dumps({'type': 'assistant', 'message': {'role': 'assistant', 'model': 'glm-4.7',\n"
        "    'content': [{'type': 'text', 'text': 'echo ' + _secret}]}}))\n"
        # secret in raw stderr.
        "sys.stderr.write('stderr leak ' + _secret + '\\n')\n"
        # secret in checker-visible output: an initiative whose title carries it.
        "if _root and _has_skill:\n"
        "    _idir = os.path.join(_root, 'initiatives', 'leaked')\n"
        "    os.makedirs(_idir, exist_ok=True)\n"
        "    _lines = ['---', 'title: ' + _secret, 'status: active', 'created: 2026-07-27',\n"
        "        'updated: 2026-07-27', 'aliases: []', 'related: []', '---', '',\n"
        "        '# ' + _secret, '', '## Provisional intent', '', '### Outcome', '', 'X.', '',\n"
        "        '### Subject', '', 'X.', '', '### Constraints and anti-goals', '', 'Unknown.', '',\n"
        "        '## Primary uncertainty', '', 'X.', '', '## Current understanding', '',\n"
        "        '### Evidence', '', 'None.', '', '### Assumptions', '', 'X.', '',\n"
        "        '## Current state', '', 'X.', '']\n"
        "    open(os.path.join(_idir, 'initiative.md'), 'w').write('\\n'.join(_lines))\n"
        # secret in a retained filename and in a symlink target.
        "    if _root:\n"
        "        open(os.path.join(_root, _secret + '.md'), 'w').write('named after secret')\n"
        "        try:\n"
        "            os.symlink('/tmp/' + _secret + '-target', os.path.join(_root, _secret + '.link'))\n"
        "        except OSError:\n"
        "            pass\n"
        "print(json.dumps({'type': 'result', 'subtype': 'success', 'result': 'final ' + _secret,\n"
        "    'is_error': False, 'num_turns': 4, 'permission_denials': [],\n"
        "    'modelUsage': {'claude-sonnet-5': {'provider': 'firstParty', 'canonicalModel': 'claude-sonnet-5'}}}))\n"
        "sys.exit(0)\n"
    )
    return _write_fake(tmp, "redaction", behavior)[0]


def make_canary_leak_fake(tmp: Path, channel: str) -> Path:
    sig = CANARY_SIGNAL
    siglit = repr(sig)
    base = (
        "import glob as _glob\n"
        "_matches = _glob.glob(os.path.join(_plugin or '', 'skills', '*', 'SKILL.md')) if _plugin else []\n"
        "_has_skill = bool(_matches)\n"
        "_skill_name = os.path.basename(os.path.dirname(_matches[0])) if _matches else None\n"
        "_target = ('d7y-eval-session:' + _skill_name) if _has_skill else None\n"
        "_skills = [_target, 'doctor'] if _has_skill else ['doctor']\n"
        "_pname = 'd7y-eval-session' if _has_skill else 'd7y-eval-control'\n"
        "_sid = 'canary-' + str(os.getpid())\n"
        "print(json.dumps({'type': 'system', 'subtype': 'init', 'session_id': _sid, "
        "'tools': ['Skill', 'Read', 'Write', 'Edit', 'Bash'], 'model': 'claude-sonnet-5', "
        "'skills': _skills, 'plugins': [{'name': _pname, 'path': _plugin or '', 'version': '0.0.1'}], "
        "'mcp_servers': [], 'permissionMode': 'dontAsk'}))\n"
    )
    injected = {
        "text": (
            "print(json.dumps({'type': 'assistant', 'message': {'role': 'assistant', 'model': 'glm-4.7',\n"
            "    'content': [{'type': 'text', 'text': 'note: ' + " + siglit + "}]}}))\n"
        ),
        "bash": (
            "print(json.dumps({'type': 'assistant', 'message': {'role': 'assistant', 'model': 'glm-4.7',\n"
            "    'content': [{'type': 'tool_use', 'id': 'k1', 'name': 'Bash', 'input': {'command': 'echo ' + "
            + siglit + "}}]}}))\n"
        ),
        "tool_result": (
            "print(json.dumps({'type': 'assistant', 'message': {'role': 'assistant', 'model': 'glm-4.7',\n"
            "    'content': [{'type': 'tool_use', 'id': 'k1', 'name': 'Bash', 'input': {'command': 'true'}}]}}))\n"
            "print(json.dumps({'type': 'user', 'message': {'role': 'user', 'content': [{'type': 'tool_result',\n"
            "    'tool_use_id': 'k1', 'content': 'got ' + " + siglit + ", 'is_error': False}]}}))\n"
        ),
        "result": "",
        "nested": (
            "print(json.dumps({'type': 'assistant', 'message': {'role': 'assistant', 'model': 'glm-4.7',\n"
            "    'content': [{'type': 'text', 'text': 'ok'}], 'note': {'deep': " + siglit + "}}}))\n"
        ),
    }
    final_set = (
        "_final = ('ok ' + " + siglit + ") if " + repr(channel == "result") + " else 'ok'\n"
    )
    result_line = (
        "print(json.dumps({'type': 'result', 'subtype': 'success', 'result': _final, 'is_error': False, "
        "'num_turns': 3, 'permission_denials': [], "
        "'modelUsage': {'claude-sonnet-5': {'provider': 'firstParty', 'canonicalModel': 'claude-sonnet-5'}}}))\n"
        "sys.exit(0)\n"
    )
    behavior = base + final_set + injected.get(channel, "") + result_line
    return _write_fake(tmp, "canary-" + channel, behavior)[0]


def make_runtime_invalid_fake(tmp: Path, corruption: str) -> Path:
    base = (
        "import glob as _glob\n"
        "_matches = _glob.glob(os.path.join(_plugin or '', 'skills', '*', 'SKILL.md')) if _plugin else []\n"
        "_has_skill = bool(_matches)\n"
        "_skill_name = os.path.basename(os.path.dirname(_matches[0])) if _matches else None\n"
        "_target = ('d7y-eval-session:' + _skill_name) if _has_skill else None\n"
        "_skills = [_target, 'doctor']\n"
        "_plugins = [{'name': 'd7y-eval-session', 'path': _plugin or '', 'version': '0.0.1'}]\n"
        "_model_usage = {'claude-sonnet-5': {'provider': 'firstParty', 'canonicalModel': 'claude-sonnet-5'}}\n"
        "_assistant_model = 'glm-4.7'\n"
    )
    corrupt = {
        "extra-skill": "_skills = [_target, 'doctor', 'something-else']\n",
        "missing-doctor": "_skills = [_target]\n",
        "dup-plugin": "_plugins = [{'name': 'd7y-eval-session', 'path': _plugin or '', 'version': '0.0.1'}, {'name': 'd7y-eval-session', 'path': _plugin or '', 'version': '0.0.1'}]\n",
        "bad-modelusage": "_model_usage = {'claude-sonnet-5': {'provider': 'firstParty', 'canonicalModel': 'wrong'}}\n",
        "glm-4-6": "_assistant_model = 'glm-4.6'\n",
    }[corruption]
    tail = (
        "_sid = 'inv-' + str(os.getpid())\n"
        "print(json.dumps({'type': 'system', 'subtype': 'init', 'session_id': _sid, "
        "'tools': ['Skill', 'Read', 'Write', 'Edit', 'Bash'], 'model': 'claude-sonnet-5', "
        "'skills': _skills, 'plugins': _plugins, 'mcp_servers': [], 'permissionMode': 'dontAsk'}))\n"
        "print(json.dumps({'type': 'assistant', 'message': {'role': 'assistant', 'model': _assistant_model, "
        "'content': [{'type': 'tool_use', 'id': 's1', 'name': 'Skill', 'input': {'skill': _target}}]}}))\n"
        "print(json.dumps({'type': 'result', 'subtype': 'success', 'result': 'ok', 'is_error': False, "
        "'num_turns': 2, 'permission_denials': [], 'modelUsage': _model_usage}))\n"
        "sys.exit(0)\n"
    )
    return _write_fake(tmp, "invalid-" + corruption, base + corrupt + tail)[0]


_VALID_INITIATIVE_PY = repr(_valid_initiative_text())


def make_mutator_fake(tmp: Path, mutation: str) -> Path:
    behavior = (
        "import glob as _glob\n"
        "_matches = _glob.glob(os.path.join(_plugin or '', 'skills', '*', 'SKILL.md')) if _plugin else []\n"
        "_has_skill = bool(_matches)\n"
        "_skill_name = os.path.basename(os.path.dirname(_matches[0])) if _matches else None\n"
        "_target = ('d7y-eval-session:' + _skill_name) if _has_skill else None\n"
        "_skills = [_target, 'doctor'] if _has_skill else ['doctor']\n"
        "_pname = 'd7y-eval-session' if _has_skill else 'd7y-eval-control'\n"
        "_sid = 'mut-' + str(os.getpid())\n"
        "print(json.dumps({'type': 'system', 'subtype': 'init', 'session_id': _sid, "
        "'tools': ['Skill', 'Read', 'Write', 'Edit', 'Bash'], 'model': 'claude-sonnet-5', "
        "'skills': _skills, 'plugins': [{'name': _pname, 'path': _plugin or '', 'version': '0.0.1'}], "
        "'mcp_servers': [], 'permissionMode': 'dontAsk'}))\n"
        "if _has_skill and _root:\n"
        "    _readme = os.path.join(_root, 'initiatives', 'README.md')\n"
        "    _initmd = os.path.join(_root, 'initiatives', 'customer-interview-analysis', 'initiative.md')\n"
        + {
            "modify": "    if os.path.exists(_readme):\n        open(_readme, 'w').write('MUTATED CONTENT')\n",
            "delete": "    if os.path.exists(_readme):\n        os.unlink(_readme)\n",
            "symlink": "    if os.path.exists(_readme):\n        os.unlink(_readme)\n        os.symlink('/nonexistent-target-zz', _readme)\n",
            "add": (
                "    _d = os.path.join(_root, 'initiatives', 'extra')\n"
                "    os.makedirs(_d, exist_ok=True)\n"
                "    open(os.path.join(_d, 'initiative.md'), 'w').write(" + _VALID_INITIATIVE_PY + ")\n"
            ),
            "delete-initiative": "    if os.path.exists(_initmd):\n        os.unlink(_initmd)\n",
        }[mutation]
        + "if _has_skill:\n"
        "    print(json.dumps({'type': 'assistant', 'message': {'role': 'assistant', 'model': 'glm-4.7',\n"
        "        'content': [{'type': 'tool_use', 'id': 's1', 'name': 'Skill', 'input': {'skill': _target}}]}}))\n"
        "print(json.dumps({'type': 'result', 'subtype': 'success', 'result': 'ok', 'is_error': False,\n"
        "    'num_turns': 2, 'permission_denials': [],\n"
        "    'modelUsage': {'claude-sonnet-5': {'provider': 'firstParty', 'canonicalModel': 'claude-sonnet-5'}}}))\n"
        "sys.exit(0)\n"
    )
    return _write_fake(tmp, "mut-" + mutation, behavior)[0]


# ---------------------------------------------------------------------------
# Narrow unit tests: production parser, path, redaction primitives.
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
        self.assertFalse(run_eval.is_control_destination(Path("initiatives/README.md")))

    def test_tokenize_rejects_compound_and_quoted(self):
        self.assertIsNone(run_eval.tokenize_simple_command("d7y x && echo hi"))
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

    def test_fixtures_target_invocation_counts(self):
        pos = run_eval.parse_stream_json((self.fixtures / "positive.jsonl").read_text())
        self.assertEqual(run_eval.count_target_invocations(pos, "d7y-eval-probe:d7y-invocation-probe")[0], 1)
        base = run_eval.parse_stream_json((self.fixtures / "baseline.jsonl").read_text())
        self.assertEqual(run_eval.count_target_invocations(base, "d7y-eval-probe:d7y-invocation-probe")[0], 0)
        neg = run_eval.parse_stream_json((self.fixtures / "negative.jsonl").read_text())
        self.assertEqual(run_eval.count_target_invocations(neg, "d7y-eval-probe:d7y-invocation-probe")[0], 0)

    def test_prefix_does_not_count(self):
        events = [{"type": "assistant", "message": {"content": [
            {"type": "tool_use", "name": "Skill", "input": {"skill": "d7y-eval-session:starting-initiatives-extra"}}
        ]}}]
        self.assertEqual(run_eval.count_target_invocations(events, "d7y-eval-session:starting-initiatives")[0], 0)

    def test_malformed_line_raises(self):
        with self.assertRaises(ValueError):
            run_eval.parse_stream_json('{"type": "system"}\nnot json\n')

    def test_routed_model_extraction(self):
        events = [{"type": "assistant", "message": {"model": "glm-4.7", "content": []}}]
        self.assertEqual(run_eval.extract_routed_models(events), ["glm-4.7"])


def _bash_use(tid, command, index):
    return (index, {"type": "assistant", "message": {"content": [
        {"type": "tool_use", "id": tid, "name": "Bash", "input": {"command": command}}
    ]}})


def _tool_result(tid, content, *, is_error=False, index=99):
    return (index, {"type": "user", "message": {"content": [
        {"type": "tool_result", "tool_use_id": tid, "content": content, "is_error": is_error}
    ]}})


class TestD7YCommandAnalysis(unittest.TestCase):
    WS = "/ws"

    def _analyze(self, pairs):
        events = [ev for _, ev in sorted(pairs, key=lambda p: p[0])]
        return run_eval.analyze_d7y_commands(events, self.WS)

    def test_valid_list_then_check(self):
        out = self._analyze([
            _bash_use("a", "d7y initiatives list --root /ws --json", 1),
            _bash_use("b", "d7y initiatives check --root /ws --json", 2),
            _tool_result("a", '{"version":1,"root":"/ws","valid":true}', index=3),
            _tool_result("b", '{"version":1,"root":"/ws","valid":true}', index=4),
        ])
        self.assertTrue(out["shape_supported"])
        self.assertEqual(out["list"]["class"], "ok")
        self.assertEqual(out["check"]["class"], "ok")
        self.assertTrue(out["order_ok"])

    def test_wrong_root_not_valid(self):
        out = self._analyze([
            _bash_use("a", "d7y initiatives list --root /other --json", 1),
            _tool_result("a", "{}", index=2),
        ])
        self.assertEqual(out["list"]["class"], "wrong_shape")

    def test_quoted_echo_not_valid(self):
        out = self._analyze([
            _bash_use("a", 'echo "d7y initiatives list --root /ws --json"', 1),
            _tool_result("a", "ok", index=2),
        ])
        self.assertEqual(out["list"]["class"], "not_attempted")

    def test_unmatched_bash_use_unsupported_shape(self):
        # A Bash tool_use without exactly one later matching result is uncorrelated.
        out = self._analyze([
            _bash_use("a", "d7y initiatives list --root /ws --json", 1),
            _tool_result("other", "{}", index=2),
        ])
        self.assertFalse(out["shape_supported"])
        self.assertIn("a", out["uncorrelated_bash_ids"])

    def test_extra_bash_without_result_unsupported_shape(self):
        out = self._analyze([
            _bash_use("a", "d7y initiatives list --root /ws --json", 1),
            _bash_use("z", "ls", 2),
            _tool_result("a", '{"version":1,"valid":true}', index=3),
        ])
        self.assertFalse(out["shape_supported"])
        self.assertIn("z", out["uncorrelated_bash_ids"])

    def test_extra_bash_with_result_counted(self):
        out = self._analyze([
            _bash_use("a", "d7y initiatives list --root /ws --json", 1),
            _bash_use("b", "d7y initiatives check --root /ws --json", 2),
            _bash_use("z", "ls", 3),
            _tool_result("a", '{"version":1,"valid":true}', index=4),
            _tool_result("b", '{"version":1,"valid":true}', index=5),
            _tool_result("z", "out", index=6),
        ])
        self.assertTrue(out["shape_supported"])
        self.assertEqual(out["extra_bash_count"], 1)

    def test_error_result(self):
        out = self._analyze([
            _bash_use("a", "d7y initiatives check --root /ws --json", 1),
            _tool_result("a", "boom", is_error=True, index=2),
        ])
        self.assertEqual(out["check"]["class"], "error")

    def test_reversed_order(self):
        out = self._analyze([
            _bash_use("b", "d7y initiatives check --root /ws --json", 1),
            _bash_use("a", "d7y initiatives list --root /ws --json", 2),
            _tool_result("a", '{"version":1,"valid":true}', index=3),
            _tool_result("b", '{"version":1,"valid":true}', index=4),
        ])
        self.assertFalse(out["order_ok"])

    def test_result_before_use_unsupported(self):
        out = self._analyze([
            _tool_result("a", '{"version":1,"valid":true}', index=0),
            _bash_use("a", "d7y initiatives list --root /ws --json", 1),
        ])
        self.assertEqual(out["list"]["class"], "result_before_use")

    def test_duplicate_result_id_unsupported_shape(self):
        out = self._analyze([
            _bash_use("a", "d7y initiatives list --root /ws --json", 1),
            _tool_result("a", '{"version":1,"valid":true}', index=2),
            _tool_result("a", '{"version":1,"valid":true}', index=3),
        ])
        self.assertFalse(out["shape_supported"])

    def test_no_result_channel_unsupported_shape(self):
        out = self._analyze([_bash_use("a", "d7y initiatives list --root /ws --json", 1)])
        self.assertFalse(out["shape_supported"])

    def test_invalid_result_shape(self):
        out = self._analyze([
            _bash_use("a", "d7y initiatives check --root /ws --json", 1),
            _tool_result("a", '{"version":1,"valid":false}', index=2),
        ])
        self.assertEqual(out["check"]["class"], "invalid_result")


class TestRedactionUnit(unittest.TestCase):
    def test_recursive_redaction_keys_and_values(self):
        obj = {"secret-1": "secret-1 here", "b": ["secret-1", {"c": "secret-2"}], "n": 5}
        out = run_eval.redact_obj(obj, ["secret-1", "secret-2"])
        self.assertIn("<redacted>", out)
        self.assertEqual(out["<redacted>"], "<redacted> here")
        self.assertEqual(out["b"][1]["c"], "<redacted>")
        self.assertEqual(out["n"], 5)

    def test_collect_env_tokens_lenient(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "s.json"
            p.write_text('{"env": {"A": "tok-a", "B": "tok-b"}}')
            self.assertEqual(sorted(run_eval.collect_env_tokens(p)), ["tok-a", "tok-b"])
            bad = Path(d) / "bad.json"
            bad.write_text("not json")
            self.assertEqual(run_eval.collect_env_tokens(bad), [])


class TestCanaryScan(unittest.TestCase):
    def test_recursive_signal_detection_in_nested_metadata(self):
        events = [{"type": "assistant", "message": {"content": [
            {"type": "text", "text": "ok"}], "note": {"deep": run_eval.PROJECT_INSTRUCTION_SIGNAL}}}]
        clean, issues = run_eval.check_canary_leakage(events)
        self.assertFalse(clean)

    def test_global_skill_exact_identity_not_substring(self):
        decoy = "d7y-eval-session:not-the-canary-" + run_eval.FAKE_GLOBAL_SKILL_NAME
        clean, _ = run_eval.check_canary_leakage(
            [{"type": "system", "subtype": "init", "skills": ["doctor", decoy]}])
        self.assertTrue(clean)
        leak, issues = run_eval.check_canary_leakage(
            [{"type": "system", "subtype": "init", "skills": ["doctor", run_eval.FAKE_GLOBAL_SKILL_NAME]}])
        self.assertFalse(leak)


class TestValidateArmEvents(unittest.TestCase):
    def _events(self, **overrides):
        init = {
            "type": "system", "subtype": "init", "session_id": "s1",
            "tools": run_eval.EXPECTED_TOOLS, "model": run_eval.EXPECTED_MODEL,
            "skills": ["d7y-eval-session:starting-initiatives", "doctor"],
            "plugins": [{"name": "d7y-eval-session", "path": "/p", "version": "0.0.1"}],
            "mcp_servers": [], "permissionMode": "dontAsk",
        }
        init.update(overrides.get("init", {}))
        result = {
            "type": "result", "subtype": "success", "result": "ok", "is_error": False,
            "num_turns": 1, "permission_denials": [],
            "modelUsage": {"claude-sonnet-5": {"provider": "firstParty", "canonicalModel": "claude-sonnet-5"}},
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

    def test_valid_with_skill_exact_set(self):
        self.assertTrue(self._validate(self._events()).ok)

    def test_nonstring_skill_rejected(self):
        events = self._events(init={"skills": [
            "d7y-eval-session:starting-initiatives", "doctor", 5]})
        self.assertFalse(self._validate(events).ok)

    def test_extra_skill_rejected(self):
        self.assertFalse(self._validate(self._events(init={"skills": [
            "d7y-eval-session:starting-initiatives", "doctor", "extra"]})).ok)

    def test_missing_doctor_rejected(self):
        self.assertFalse(self._validate(self._events(init={"skills": [
            "d7y-eval-session:starting-initiatives"]})).ok)

    def test_duplicate_plugin_rejected(self):
        events = self._events(init={"plugins": [
            {"name": "d7y-eval-session", "path": "/p", "version": "0.0.1"},
            {"name": "d7y-eval-session", "path": "/p", "version": "0.0.1"}]})
        self.assertFalse(self._validate(events).ok)

    def test_malformed_plugin_missing_path_rejected(self):
        events = self._events(init={"plugins": [{"name": "d7y-eval-session", "version": "0.0.1"}]})
        self.assertFalse(self._validate(events).ok)

    def test_malformed_plugin_bad_version_type_rejected(self):
        events = self._events(init={"plugins": [
            {"name": "d7y-eval-session", "path": "/p", "version": 1}]})
        self.assertFalse(self._validate(events).ok)

    def test_num_turns_bool_rejected(self):
        # A bool must not satisfy the integer num_turns field.
        events = self._events(result={"num_turns": True})
        self.assertFalse(self._validate(events).ok)

    def test_nonzero_and_none_exit_invalid(self):
        self.assertFalse(self._validate(self._events(), exit_code=3).ok)
        self.assertFalse(self._validate(self._events(), exit_code=None).ok)

    def test_timeout_invalidates(self):
        self.assertFalse(self._validate(self._events(), timed_out=True).ok)

    def test_bad_modelusage_canonical_rejected(self):
        events = self._events(result={"modelUsage": {
            "claude-sonnet-5": {"provider": "firstParty", "canonicalModel": "wrong"}}})
        self.assertFalse(self._validate(events).ok)

    def test_glm_4_6_rejected(self):
        events = self._events(extra=[{"type": "assistant", "message": {"model": "glm-4.6", "content": []}}])
        self.assertFalse(self._validate(events).ok)

    def test_shared_session_rejected(self):
        v = self._validate(self._events(init={"session_id": "shared"}),
                           with_skill=False, expected_plugin="d7y-eval-control",
                           other_session_id="shared")
        self.assertFalse(v.ok)


class TestStagingSafety(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="d7y-eval-"))
        self.repo, self.commit = make_repo(self.tmp)

    def tearDown(self):
        if self.tmp.exists():
            shutil.rmtree(self.tmp)

    def test_ancestor_descendant_collision_detected(self):
        ws = self.tmp / "ws"
        ws.mkdir()
        with self.assertRaises(run_eval.PreflightError):
            run_eval.prevalidate_staging(
                [("evals/files/customer-interview-analysis.md", "a"),
                 ("evals/files/customer-interview-analysis.md", "a/b.md")], ws)

    def test_control_destination_collision_detected(self):
        ws = self.tmp / "ws"
        ws.mkdir()
        with self.assertRaises(run_eval.PreflightError):
            run_eval.prevalidate_staging(
                [("evals/files/customer-interview-analysis.md", "settings.json")], ws)


# Independent authoritative inventory lists (not imported from production), so
# behavioral tests compare against a self-contained contract.
EXPECTED_ARM_ARTIFACTS = (
    "trace.jsonl",
    "stderr.txt",
    "process.json",
    "provenance.json",
    "final-response.txt",
    "telemetry.json",
    "command-events.json",
    "checker.json",
    "workspace-changes.json",
    "workspace-snapshot.json",
    "selected-objects.json",
    "validation.json",
    "arm-summary.json",
)
EXPECTED_TOP_LEVEL_ARTIFACTS = (
    "manifest.json",
    "checks.json",
    "summary.md",
    "source-status.json",
)

# Project-instruction canary signal as an independent literal contract value
# (the production canary writes the same token; behavioral fakes must not import
# it from evals.run_eval).
CANARY_SIGNAL = "D7Y-EVAL-INSTRUCTION-CANARY-SIGNAL-7Q"


def _assert_complete_inventory(test: unittest.TestCase, output: Path) -> None:
    for arm in ("with-skill", "baseline"):
        for name in EXPECTED_ARM_ARTIFACTS:
            test.assertTrue((output / arm / "artifacts" / name).exists(),
                            f"missing {arm}/{name}")
    for name in EXPECTED_TOP_LEVEL_ARTIFACTS:
        test.assertTrue((output / name).exists(), f"missing top-level {name}")


# ---------------------------------------------------------------------------
# Public-CLI end-to-end tests.
# ---------------------------------------------------------------------------


class TestPublicCLI(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="d7y-eval-"))
        self.repo, self.commit = make_repo(self.tmp)

    def tearDown(self):
        if self.tmp.exists():
            shutil.rmtree(self.tmp)

    # -- correction 1 & 9: neutral prompt, independent argv records ----------

    def test_dry_run_complete_preflight_zero_invocations(self):
        fake = make_invocation_recording_fake(self.tmp)
        output = self.tmp / "out"
        proc = run_cli(self.repo, "skills/starting-initiatives/evals/evals.json",
                       "start-new-initiative", output, claude=fake, dry_run=True,
                       user_settings=make_user_settings(self.tmp))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.returncode, 0)
        self.assertFalse((self.tmp / "rec.log").exists(),
                         "dry-run must not invoke or version-probe the executable")
        manifest = json.loads((output / "manifest.json").read_text())
        self.assertEqual(manifest["commit"], self.commit)
        self.assertTrue(manifest["dry_run"])
        self.assertIsNone(manifest["executable"])
        plugin_skill = output / "with-skill" / "plugin" / "skills" / "starting-initiatives" / "SKILL.md"
        self.assertTrue(plugin_skill.exists())
        self.assertFalse((output / "baseline" / "plugin" / "skills").exists())
        self.assertNotEqual(manifest["roots"]["with_skill_workspace"], manifest["roots"]["baseline_workspace"])
        for ws in (output / "with-skill" / "workspace", output / "baseline" / "workspace"):
            for p in ws.rglob("*"):
                self.assertNotIn(p.name, {".claude-plugin", "settings.json", "CLAUDE.md"})
        self.assertIn("d7y", manifest["capability_object_ids"])
        self.assertEqual(_git(self.repo, "status", "--porcelain"), "")

    def test_neutral_prompt_and_independent_argv_records(self):
        fake, log = make_positive_fake(self.tmp)
        output = self.tmp / "out"
        proc = run_cli(self.repo, "skills/starting-initiatives/evals/evals.json",
                       "start-new-initiative", output, claude=fake,
                       user_settings=make_user_settings(self.tmp))
        self.assertNotEqual(proc.returncode, 2, proc.stderr)
        # The wrapper is behavior-neutral: it never names list/check/create.
        manifest = json.loads((output / "manifest.json").read_text())
        for key in ("with_skill_argv", "baseline_argv"):
            argv = manifest[key]
            self.assertNotIn("--root", argv[:-1])  # no top-level --root flag (prompt may mention it)
            self.assertEqual(argv.count("--tools"), 1)
            prompt_tail = argv[-1]
            self.assertNotIn("initiatives list", prompt_tail)
            self.assertNotIn("initiatives check", prompt_tail)
        # Independent fake records: parse the log directly (no production helper).
        records = [json.loads(line) for line in log.read_text().splitlines() if line.strip()]
        self.assertEqual(len(records), 2)
        roots = manifest["roots"]
        for rec in records:
            self.assertTrue(rec["ok"], rec)
            self.assertEqual(rec["error"], None)
            self.assertIsNotNone(rec["workspace"])
            self.assertIn(rec["workspace"], roots.values())

    # -- corrections 3 & 4: live positive run -------------------------------

    def test_live_positive_case_deterministic_passes_rubric_blocks(self):
        fake, _log = make_positive_fake(self.tmp)
        settings = make_user_settings(self.tmp)
        output = self.tmp / "out"
        proc = run_cli(self.repo, "skills/starting-initiatives/evals/evals.json",
                       "start-new-initiative", output, claude=fake, user_settings=settings)
        self.assertEqual(proc.returncode, 1, proc.stderr + "\n" + (output / "summary.md").read_text())
        checks = json.loads((output / "checks.json").read_text())
        self.assertEqual(checks["pair_validity"]["status"], "pass", checks["pair_validity"])
        self.assertEqual(checks["treatment_checks"]["status"], "pass")
        for a in checks["with_skill_assertions"]:
            if a["kind"] == "deterministic":
                self.assertEqual(a["status"], "pass", a)
        rubric = next(a for a in checks["with_skill_assertions"] if a["kind"] == "rubric")
        self.assertEqual(rubric["status"], "pending")
        _assert_complete_inventory(self, output)
        cmds = json.loads((output / "with-skill" / "artifacts" / "command-events.json").read_text())
        self.assertTrue(cmds["shape_supported"])
        self.assertEqual(cmds["list"]["class"], "ok")
        self.assertEqual(cmds["check"]["class"], "ok")
        self.assertTrue(cmds["order_ok"])
        checker = json.loads((output / "with-skill" / "artifacts" / "checker.json").read_text())
        self.assertTrue(checker["valid"])
        self.assertEqual(checker["state"], "ran")
        changes = json.loads((output / "with-skill" / "artifacts" / "workspace-changes.json").read_text())
        self.assertIn("initiatives/consultant-proposals/initiative.md", changes["added"])
        prov = json.loads((output / "with-skill" / "artifacts" / "provenance.json").read_text())
        self.assertEqual(prov["executable_version"], "Claude Code 2.1.218")
        self.assertTrue(prov["executable"].startswith("/"))
        self.assertEqual(_git(self.repo, "status", "--porcelain"), "")

    def test_live_negative_case_passes_on_absence(self):
        fake, _log = make_positive_fake(self.tmp)
        output = self.tmp / "out"
        proc = run_cli(self.repo, "skills/starting-initiatives/evals/evals.json",
                       "casual-brainstorm", output, claude=fake,
                       user_settings=make_user_settings(self.tmp))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        checks = json.loads((output / "checks.json").read_text())
        self.assertEqual(next(a for a in checks["with_skill_assertions"]
                              if a["id"] == "does-not-invoke")["status"], "pass")

    # -- correction 8: creates-no-duplicate, deletion fails ------------------

    def test_resume_creates_no_duplicate_pass(self):
        fake, _log = make_positive_fake(self.tmp)
        output = self.tmp / "out"
        proc = run_cli(self.repo, "skills/starting-initiatives/evals/evals.json",
                       "resume-same-initiative", output, claude=fake,
                       user_settings=make_user_settings(self.tmp))
        checks = json.loads((output / "checks.json").read_text())
        nodup = next(a for a in checks["with_skill_assertions"] if a["id"] == "creates-no-duplicate")
        self.assertEqual(nodup["status"], "pass", nodup)

    def test_creates_no_duplicate_fails_when_existing_deleted(self):
        fake = make_mutator_fake(self.tmp, "delete-initiative")
        output = self.tmp / "out"
        proc = run_cli(self.repo, "skills/starting-initiatives/evals/evals.json",
                       "resume-same-initiative", output, claude=fake,
                       user_settings=make_user_settings(self.tmp))
        checks = json.loads((output / "checks.json").read_text())
        nodup = next(a for a in checks["with_skill_assertions"] if a["id"] == "creates-no-duplicate")
        self.assertEqual(nodup["status"], "fail", nodup)

    # -- correction 8: preflight-reject unsupported skills ------------------

    def test_writing_great_skills_preflight_rejected(self):
        sub = self.tmp / "wgs-tmp"
        sub.mkdir()
        repo, _ = make_repo(sub, include_wgs=True)
        fake, _log = make_positive_fake(sub)
        output = sub / "out"
        proc = run_cli(repo, "skills/writing-great-skills/evals/evals.json",
                       "create-discovery-skill", output, claude=fake,
                       user_settings=make_user_settings(sub))
        self.assertEqual(proc.returncode, 2, proc.stderr)
        self.assertIn("unsupported skill", proc.stderr)
        self.assertFalse(output.exists(), "unsupported skill must not be executed")

    # -- correction 8: exact dispatch, unknown id ungradable ----------------

    def test_unknown_deterministic_id_is_ungradable(self):
        # Build a synthetic case via an in-memory assertion evaluation.
        arm = run_eval.ArmResult(
            config="with-skill", workspace=Path("/ws"), plugin_root=Path("/p"),
            argv=[], prompt="",
            validation=run_eval.ArmValidation(ok=True, errors=[], skills=["d7y-eval-session:starting-initiatives"]),
            outcome=run_eval.ProcessOutcome(stdout="", stderr="", exit_code=0, timed_out=False,
                                            duration_seconds=1.0, pid=1),
            workspace_changes={"added": [], "modified": [], "deleted": []},
        )
        status, _ = run_eval.evaluate_assertion(
            {"id": "invokes-unknown-skill", "kind": "deterministic", "required": True},
            with_skill=arm, skill_name="starting-initiatives")
        self.assertEqual(status, "ungradable")

    # -- correction 2: complete recursive redaction across all channels ------

    def test_imported_env_value_redacted_from_every_output_entry(self):
        fake = make_redaction_fake(self.tmp)
        secret = "super-secret-value-XYZ"
        settings = make_user_settings(self.tmp, env={"D7Y_EVAL_TEST_TOKEN": secret})
        output = self.tmp / "out"
        proc = run_cli(self.repo, "skills/starting-initiatives/evals/evals.json",
                       "start-new-initiative", output, claude=fake, user_settings=settings)
        self.assertNotEqual(proc.returncode, 2, proc.stderr)
        # Captured CLI stdout/stderr diagnostics never carry the value.
        self.assertNotIn(secret, proc.stdout)
        self.assertNotIn(secret, proc.stderr)
        # Every persisted output entry is clean: file contents, every path
        # component (filenames and directory names), and symlink targets.
        leaked = []
        for p in output.rglob("*"):
            rel = str(p)
            if secret in rel:
                leaked.append(("path", rel))
            if p.is_symlink() and secret in os.readlink(p):
                leaked.append(("symlink-target", rel))
            if p.is_file():
                try:
                    if secret in p.read_text(errors="ignore"):
                        leaked.append(("content", rel))
                except OSError:
                    continue
        self.assertEqual(leaked, [], f"secret leaked in: {leaked}")
        # Key-name provenance retained.
        manifest = json.loads((output / "manifest.json").read_text())
        self.assertIn("D7Y_EVAL_TEST_TOKEN", manifest["env_provenance"]["imported_keys"])
        # Redaction markers present where a value was scrubbed.
        self.assertIn("<redacted>", (output / "with-skill" / "artifacts" / "trace.jsonl").read_text())
        self.assertIn("<redacted>", (output / "with-skill" / "artifacts" / "checker.json").read_text())
        # The secret-named file was renamed and the secret symlink removed.
        self.assertFalse((output / "with-skill" / "workspace" / (secret + ".md")).exists())

    # -- correction 6: canary leakage across channels -----------------------

    def test_canary_leak_each_channel_fails_pair(self):
        for channel in ("text", "bash", "tool_result", "result", "nested"):
            fake = make_canary_leak_fake(self.tmp, channel)
            output = self.tmp / f"out-{channel}"
            proc = run_cli(self.repo, "skills/starting-initiatives/evals/evals.json",
                           "start-new-initiative", output, claude=fake,
                           user_settings=make_user_settings(self.tmp))
            checks = json.loads((output / "checks.json").read_text())
            self.assertEqual(checks["pair_validity"]["status"], "fail", f"{channel}: {checks}")
            self.assertTrue(any("canary" in e for e in checks["pair_validity"]["errors"]),
                            f"{channel}: {checks['pair_validity']['errors']}")

    # -- correction 4: runtime-invalid public-arm variants ------------------

    def test_runtime_invalid_variants_fail_pair(self):
        for corruption in ("extra-skill", "missing-doctor", "dup-plugin",
                           "bad-modelusage", "glm-4-6"):
            fake = make_runtime_invalid_fake(self.tmp, corruption)
            output = self.tmp / f"out-{corruption}"
            proc = run_cli(self.repo, "skills/starting-initiatives/evals/evals.json",
                           "start-new-initiative", output, claude=fake,
                           user_settings=make_user_settings(self.tmp))
            checks = json.loads((output / "checks.json").read_text())
            self.assertEqual(checks["pair_validity"]["status"], "fail",
                             f"{corruption}: {checks['pair_validity']}")
            _assert_complete_inventory(self, output)

    # -- correction 2: every Bash tool_use must correlate --------------------

    def test_extra_bash_use_lacking_result_blocks(self):
        behavior = (
            "import glob as _glob\n"
            "_matches = _glob.glob(os.path.join(_plugin or '', 'skills', '*', 'SKILL.md')) if _plugin else []\n"
            "_has_skill = bool(_matches)\n"
            "_skill_name = os.path.basename(os.path.dirname(_matches[0])) if _matches else None\n"
            "_target = ('d7y-eval-session:' + _skill_name) if _has_skill else None\n"
            "_skills = [_target, 'doctor'] if _has_skill else ['doctor']\n"
            "_pname = 'd7y-eval-session' if _has_skill else 'd7y-eval-control'\n"
            "_sid = 'extra-' + str(os.getpid())\n"
            "print(json.dumps({'type': 'system', 'subtype': 'init', 'session_id': _sid, "
            "'tools': ['Skill', 'Read', 'Write', 'Edit', 'Bash'], 'model': 'claude-sonnet-5', "
            "'skills': _skills, 'plugins': [{'name': _pname, 'path': _plugin or '', 'version': '0.0.1'}], "
            "'mcp_servers': [], 'permissionMode': 'dontAsk'}))\n"
            "if _has_skill and _root:\n"
            "    for _cmd, _id in [('d7y initiatives list --root ' + _root + ' --json', 'c2'), "
            "('d7y initiatives check --root ' + _root + ' --json', 'c3'), ('ls', 'c4')]:\n"
            "        print(json.dumps({'type': 'assistant', 'message': {'role': 'assistant', 'model': 'glm-4.7',\n"
            "            'content': [{'type': 'tool_use', 'id': _id, 'name': 'Bash', 'input': {'command': _cmd}}]}}))\n"
            "    print(json.dumps({'type': 'user', 'message': {'role': 'user', 'content': [{'type': 'tool_result',\n"
            "        'tool_use_id': 'c2', 'content': '{\"version\":1,\"root\":\"' + _root + '\",\"valid\":true}', 'is_error': False}]}}))\n"
            "    print(json.dumps({'type': 'user', 'message': {'role': 'user', 'content': [{'type': 'tool_result',\n"
            "        'tool_use_id': 'c3', 'content': '{\"version\":1,\"root\":\"' + _root + '\",\"valid\":true}', 'is_error': False}]}}))\n"
            "    # c4 (extra Bash) intentionally has NO tool_result.\n"
            "print(json.dumps({'type': 'result', 'subtype': 'success', 'result': 'ok', 'is_error': False, "
            "'num_turns': 5, 'permission_denials': [], "
            "'modelUsage': {'claude-sonnet-5': {'provider': 'firstParty', 'canonicalModel': 'claude-sonnet-5'}}}))\n"
            "sys.exit(0)\n"
        )
        fake = _write_fake(self.tmp, "extra-bash", behavior)[0]
        output = self.tmp / "out"
        proc = run_cli(self.repo, "skills/starting-initiatives/evals/evals.json",
                       "start-new-initiative", output, claude=fake,
                       user_settings=make_user_settings(self.tmp))
        checks = json.loads((output / "checks.json").read_text())
        proc_assertion = next(a for a in checks["with_skill_assertions"]
                              if a["id"] == "runs-checker-before-and-after")
        self.assertEqual(proc_assertion["status"], "ungradable", proc_assertion)

    # -- correction 5: independent-checker exceptions are contained ----------

    def test_checker_exception_contained(self):
        # Replace the committed d7y so `initiatives check` emits invalid UTF-8,
        # forcing a decode exception inside run_independent_checker.
        broken = self.repo / "d7y"
        broken.write_text(
            "#!/bin/sh\n"
            "if [ \"$1\" = \"initiatives\" ] && [ \"$2\" = \"check\" ]; then\n"
            "  printf '\\xff\\xfe'\n"
            "  exit 0\n"
            "fi\n"
            "exit 0\n"
        )
        broken.chmod(0o755)
        _git(self.repo, "add", "-A")
        _git(self.repo, "commit", "-m", "broken-d7y")
        fake, _log = make_positive_fake(self.tmp)
        output = self.tmp / "out"
        proc = run_cli(self.repo, "skills/starting-initiatives/evals/evals.json",
                       "start-new-initiative", output, claude=fake,
                       user_settings=make_user_settings(self.tmp))
        # The checker exception must be contained: full inventory still emitted.
        _assert_complete_inventory(self, output)
        checker = json.loads((output / "with-skill" / "artifacts" / "checker.json").read_text())
        self.assertEqual(checker["state"], "checker_error")
        self.assertFalse(checker["valid"])

    # -- correction 7: same complete inventory for every failure outcome ----

    def test_nonzero_exit_invalidates_and_emits_full_inventory(self):
        fake = make_nonzero_fake(self.tmp)
        output = self.tmp / "out"
        proc = run_cli(self.repo, "skills/starting-initiatives/evals/evals.json",
                       "start-new-initiative", output, claude=fake,
                       user_settings=make_user_settings(self.tmp))
        self.assertNotEqual(proc.returncode, 0)
        checks = json.loads((output / "checks.json").read_text())
        self.assertEqual(checks["pair_validity"]["status"], "fail")
        _assert_complete_inventory(self, output)

    def test_executable_resolution_failure_full_inventory(self):
        wrong = self.tmp / "claude"
        wrong.write_text("#!/bin/sh\necho 'Claude Code 1.0.0'\n")
        wrong.chmod(0o755)
        output = self.tmp / "out"
        proc = run_cli(self.repo, "skills/starting-initiatives/evals/evals.json",
                       "start-new-initiative", output, claude=wrong,
                       user_settings=make_user_settings(self.tmp))
        self.assertEqual(proc.returncode, 2)
        self.assertIn("2.1.218", proc.stderr)
        _assert_complete_inventory(self, output)
        prov = json.loads((output / "with-skill" / "artifacts" / "provenance.json").read_text())
        self.assertEqual(prov["state"], "unstarted")

    def test_malformed_stream_emits_full_inventory(self):
        fake = make_malformed_fake(self.tmp)
        output = self.tmp / "out"
        proc = run_cli(self.repo, "skills/starting-initiatives/evals/evals.json",
                       "start-new-initiative", output, claude=fake,
                       user_settings=make_user_settings(self.tmp))
        self.assertNotEqual(proc.returncode, 0)
        tel = json.loads((output / "with-skill" / "artifacts" / "telemetry.json").read_text())
        self.assertIsNotNone(tel["parse_error"])
        _assert_complete_inventory(self, output)

    def test_timeout_kills_process_group_reaps_full_inventory(self):
        fake = make_resistant_fake(self.tmp)
        output = self.tmp / "out"
        before = set(self._child_pids())
        proc = run_cli(self.repo, "skills/starting-initiatives/evals/evals.json",
                       "start-new-initiative", output, claude=fake,
                       user_settings=make_user_settings(self.tmp), timeout=2)
        self.assertNotEqual(proc.returncode, 0)
        time.sleep(1.0)
        after = set(self._child_pids())
        self.assertFalse(after - before, f"children survived: {after - before}")
        _assert_complete_inventory(self, output)
        pj = json.loads((output / "with-skill" / "artifacts" / "process.json").read_text())
        self.assertTrue(pj["timed_out"])

    def test_post_output_preflight_failure_emits_full_inventory(self):
        # Taint the staged seed with a canary marker so verify_workspace_isolation
        # fails AFTER output creation (a genuine post-output preflight failure).
        readme = self.repo / "initiatives" / "README.md"
        readme.write_text(readme.read_text() + "\n" + run_eval.PROJECT_INSTRUCTION_CANARY + "\n")
        _git(self.repo, "add", "-A")
        _git(self.repo, "commit", "-m", "tainted-seed")
        fake = make_invocation_recording_fake(self.tmp)
        output = self.tmp / "out"
        proc = run_cli(self.repo, "skills/starting-initiatives/evals/evals.json",
                       "start-new-initiative", output, claude=fake,
                       user_settings=make_user_settings(self.tmp))
        self.assertNotEqual(proc.returncode, 0)
        _assert_complete_inventory(self, output)

    def test_committed_symlink_in_skill_rejected_pre_output(self):
        link = self.repo / "skills" / "starting-initiatives" / "README.link"
        try:
            os.symlink("../../initiatives/README.md", link)
        except OSError:
            self.skipTest("cannot create symlink on this platform")
        _git(self.repo, "add", "-A")
        _git(self.repo, "commit", "-m", "symlink")
        fake = make_invocation_recording_fake(self.tmp)
        output = self.tmp / "out"
        proc = run_cli(self.repo, "skills/starting-initiatives/evals/evals.json",
                       "start-new-initiative", output, claude=fake,
                       user_settings=make_user_settings(self.tmp))
        self.assertNotEqual(proc.returncode, 0)
        # Atomic planning rejects before any output is created.
        self.assertFalse(output.exists())

    # -- correction 8: filesystem evidence: modify/delete/type-change/add ----

    def test_workspace_change_modified(self):
        fake = make_mutator_fake(self.tmp, "modify")
        output = self.tmp / "out"
        run_cli(self.repo, "skills/starting-initiatives/evals/evals.json",
                "start-new-initiative", output, claude=fake,
                user_settings=make_user_settings(self.tmp))
        ch = json.loads((output / "with-skill" / "artifacts" / "workspace-changes.json").read_text())
        self.assertIn("initiatives/README.md", ch["modified"])

    def test_workspace_change_deleted(self):
        fake = make_mutator_fake(self.tmp, "delete")
        output = self.tmp / "out"
        run_cli(self.repo, "skills/starting-initiatives/evals/evals.json",
                "start-new-initiative", output, claude=fake,
                user_settings=make_user_settings(self.tmp))
        ch = json.loads((output / "with-skill" / "artifacts" / "workspace-changes.json").read_text())
        self.assertIn("initiatives/README.md", ch["deleted"])

    def test_workspace_change_type_changed(self):
        fake = make_mutator_fake(self.tmp, "symlink")
        output = self.tmp / "out"
        run_cli(self.repo, "skills/starting-initiatives/evals/evals.json",
                "start-new-initiative", output, claude=fake,
                user_settings=make_user_settings(self.tmp))
        ch = json.loads((output / "with-skill" / "artifacts" / "workspace-changes.json").read_text())
        self.assertIn("initiatives/README.md", ch["type_changed"])
        snap = json.loads((output / "with-skill" / "artifacts" / "workspace-snapshot.json").read_text())
        self.assertEqual(snap["initiatives/README.md"]["type"], "symlink")

    def test_workspace_change_added(self):
        fake = make_mutator_fake(self.tmp, "add")
        output = self.tmp / "out"
        run_cli(self.repo, "skills/starting-initiatives/evals/evals.json",
                "start-new-initiative", output, claude=fake,
                user_settings=make_user_settings(self.tmp))
        ch = json.loads((output / "with-skill" / "artifacts" / "workspace-changes.json").read_text())
        self.assertIn("initiatives/extra/initiative.md", ch["added"])

    # -- corrections 5 & atomic preflight boundaries ------------------------

    def test_dirty_worktree_replacements_ignored(self):
        fake, _log = make_positive_fake(self.tmp)
        output = self.tmp / "out"
        run_cli(self.repo, "skills/starting-initiatives/evals/evals.json",
                "start-new-initiative", output, claude=fake,
                user_settings=make_user_settings(self.tmp))
        staged = json.loads((output / "manifest.json").read_text())["selected_objects"]["with_skill"]
        ids = {o["object_id"] for o in staged}
        (self.repo / "initiatives" / "README.md").write_text("DIRTY")
        out2 = self.tmp / "out2"
        run_cli(self.repo, "skills/starting-initiatives/evals/evals.json",
                "start-new-initiative", out2, claude=fake,
                user_settings=make_user_settings(self.tmp))
        staged2 = json.loads((out2 / "manifest.json").read_text())["selected_objects"]["with_skill"]
        self.assertEqual({o["object_id"] for o in staged2}, ids)
        self.assertNotIn("DIRTY", (out2 / "with-skill" / "workspace" / "initiatives" / "README.md").read_text())

    def test_output_inside_source_rejected(self):
        fake = make_invocation_recording_fake(self.tmp)
        proc = run_cli(self.repo, "skills/starting-initiatives/evals/evals.json",
                       "start-new-initiative", self.repo / "inside", claude=fake, dry_run=True,
                       user_settings=make_user_settings(self.tmp))
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("output root", proc.stderr)

    def test_empty_and_stale_and_symlink_output_rejected(self):
        fake = make_invocation_recording_fake(self.tmp)
        for setup in ("empty", "stale"):
            out = self.tmp / setup
            out.mkdir()
            if setup == "stale":
                (out / "x").write_text("x")
            proc = run_cli(self.repo, "skills/starting-initiatives/evals/evals.json",
                           "start-new-initiative", out, claude=fake, dry_run=True,
                           user_settings=make_user_settings(self.tmp))
            self.assertNotEqual(proc.returncode, 0)
        try:
            target = self.tmp / "real"; target.mkdir()
            link = self.tmp / "link"
            os.symlink(target, link)
        except OSError:
            self.skipTest("cannot create symlink")
        proc = run_cli(self.repo, "skills/starting-initiatives/evals/evals.json",
                       "start-new-initiative", link, claude=fake, dry_run=True,
                       user_settings=make_user_settings(self.tmp))
        self.assertNotEqual(proc.returncode, 0)

    def test_env_path_leak_rejected(self):
        fake, _log = make_positive_fake(self.tmp)
        settings = make_user_settings(self.tmp, env={"LEAK_VAR": str(self.repo)})
        output = self.tmp / "out"
        proc = run_cli(self.repo, "skills/starting-initiatives/evals/evals.json",
                       "start-new-initiative", output, claude=fake, user_settings=settings)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("forbidden path", proc.stderr)

    def test_source_status_evidence_recorded(self):
        fake = make_invocation_recording_fake(self.tmp)
        output = self.tmp / "out"
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
