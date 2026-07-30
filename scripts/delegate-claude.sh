#!/usr/bin/env bash
# scripts/delegate-claude.sh
#
# Thin deterministic launcher for isolated Amp -> Claude Code implementation
# delegation. See docs/prompts/README.md for the prompt artifact contract and
# docs/plans/auditable-claude-delegation.md for the governing plan.
#
# This script is a deterministic boundary, not a workflow engine. It resolves and
# reports handoff context, validates preconditions, and invokes Claude Code with a
# reviewed permission posture and a runtime envelope prepended to the committed
# prompt. It never rebase/merge/push, remove worktrees, delete branches, force
# operations, persist credentials, parse Markdown into commands, or reset state.

set -euo pipefail

readonly SCRIPT_PATH="$(readlink -f -- "${BASH_SOURCE[0]:-$0}")"
readonly PROMPTS_SUBDIR="docs/prompts"
readonly DEFAULT_PROFILE="docs-commit"
readonly NETWORK_POLICY="prohibited"
readonly MCP_POLICY="strict empty configuration"
readonly PERSISTENCE_POLICY="disabled"
readonly SETTINGS_NOTE="project settings plus env-only user import"

usage() {
  cat <<'EOF'
Usage: scripts/delegate-claude.sh [options] <concrete-prompt-path>

Thin deterministic launcher for isolated Claude Code implementation delegation.

Required:
  <concrete-prompt-path>   Path to a committed, unchanged concrete prompt that
                           lives inside docs/prompts/ of the repository.

Options:
  --profile <name>         Permission profile (default: docs-commit):
                             docs-commit           - doc edits + git commit only
                             implementation-commit - adds Glob/Grep and broader
                                                     Bash for build/test
  --model <model>          Claude Code model alias or full name (optional).
  --effort <level>         Claude Code effort level (optional).
  --allow-tool <matcher>   Repeatable. Extra Claude Code permission matcher to
                           add on top of the profile defaults, e.g.
                           "Bash(npm test:*)" or "Bash(python3 evals/*)". These
                           are permission matchers, never executed by the launcher.
  --dry-run                Resolve context, print the runtime envelope and the
                           Claude command posture, and exit without invoking
                           Claude Code.
  -h, --help               Show this help and exit.

Profile defaults (built-in tool set / allowed matchers):
  docs-commit
    tools   : Read,Edit,Write,Bash
    allowed : Read Edit Write
              Bash(git status:*) Bash(git diff:*) Bash(git log:*)
              Bash(git show:*) Bash(git add:*) Bash(git commit:*)
  implementation-commit
    tools   : Read,Edit,Write,Bash,Glob,Grep
    allowed : Read Edit Write Glob Grep Bash

Trust boundary:
  A profile narrows Claude Code's tool surface and permission grants only. It is
  NOT a filesystem or process sandbox. implementation-commit exposes broad shell
  capability (Bash) so build/test can run; that is a deliberate trust choice for
  isolated work, not least-privilege path isolation. Untrusted work still
  requires an OS/container sandbox.

Runtime posture:
  Network posture is reported as prohibited for Claude's built-in network tools;
  this is not an OS egress firewall. Bash remains subject to the selected profile
  and host policy. MCP is strict-empty
  (--mcp-config '{"mcpServers":{}}' --strict-mcp-config).
  Sessions are non-persistent (--no-session-persistence). Claude settings remain
  project-only (--setting-sources project); only the top-level env object from
  ~/.claude/settings.json is imported into the Claude subprocess. Environment
  values are never printed or passed as command arguments. Output is --verbose
  --output-format stream-json under --print.

Lifecycle authority: none. The launcher reports branch movement, changed paths,
commits created, and worktree cleanliness after a real run; it never mutates Git
state.
EOF
}

die() {
  printf 'delegate-claude.sh: error: %s\n' "$*" >&2
  exit 1
}

require_git_clean() {
  # $1 = optional path filter
  local out
  if [[ $# -eq 1 ]]; then
    out="$(git status --porcelain -- "$1")" || return 2
  else
    out="$(git status --porcelain)" || return 2
  fi
  [[ -z "$out" ]]
}

inspect_claude_user_env() {
  local settings_path inspection mode mode_oct

  command -v python3 >/dev/null 2>&1 \
    || die "python3 is required to import Claude user environment"

  settings_path="$(readlink -f -- "$HOME/.claude/settings.json" 2>/dev/null || true)"
  [[ -n "$settings_path" && -f "$settings_path" ]] \
    || die "Claude user settings not found: $HOME/.claude/settings.json"

  if ! inspection="$(python3 - "$settings_path" <<'PY'
import hashlib
import json
import os
import re
import stat
import sys

path = sys.argv[1]
fd = os.open(path, os.O_RDONLY | os.O_CLOEXEC)
try:
    metadata = os.fstat(fd)
    if not stat.S_ISREG(metadata.st_mode):
        raise SystemExit("Claude user settings must be a regular file")
    if metadata.st_uid != os.getuid():
        raise SystemExit("Claude user settings are not owned by the current user")
    if stat.S_IMODE(metadata.st_mode) & 0o022:
        raise SystemExit("Claude user settings must not be group/world writable")
    chunks = []
    while chunk := os.read(fd, 65536):
        chunks.append(chunk)
finally:
    os.close(fd)

raw = b"".join(chunks)
settings = json.loads(raw.decode("utf-8"))

env = settings.get("env", {})
if not isinstance(env, dict):
    raise SystemExit("Claude settings field 'env' must be an object")

name_pattern = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
for key in sorted(env):
    value = env[key]
    if not isinstance(key, str) or not name_pattern.fullmatch(key):
        raise SystemExit(f"Invalid environment variable name: {key!r}")
    if not isinstance(value, str):
        raise SystemExit(f"Environment variable {key!r} must have a string value")
    if "\0" in value:
        raise SystemExit(f"Environment variable {key!r} contains a NUL byte")
print(hashlib.sha256(raw).hexdigest())
print(f"{stat.S_IMODE(metadata.st_mode):03o}")
for key in sorted(env):
    print(key)
PY
)"; then
    die "failed to validate env in $settings_path"
  fi

  CLAUDE_USER_SETTINGS_PATH="$settings_path"
  CLAUDE_USER_SETTINGS_HASH="${inspection%%$'\n'*}"
  inspection="${inspection#*$'\n'}"
  mode="${inspection%%$'\n'*}"
  inspection="${inspection#*$'\n'}"
  if [[ "$inspection" == "$mode" ]]; then
    inspection=""
  fi
  mode_oct=$((8#$mode))
  if (( (mode_oct & 077) != 0 )); then
    printf 'delegate-claude.sh: warning: %s has mode %s; 600 is recommended for secret-bearing settings\n' \
      "$settings_path" "$mode" >&2
  fi
  CLAUDE_IMPORTED_ENV_KEYS="${inspection//$'\n'/ }"
  [[ -n "$CLAUDE_IMPORTED_ENV_KEYS" ]] || CLAUDE_IMPORTED_ENV_KEYS="none"
}

run_claude_with_user_env() {
  python3 -c '
import hashlib
import json
import os
import re
import stat
import sys

path, expected_hash, claude_bin, *claude_args = sys.argv[1:]
fd = os.open(path, os.O_RDONLY | os.O_CLOEXEC)
try:
    metadata = os.fstat(fd)
    if not stat.S_ISREG(metadata.st_mode):
        raise SystemExit("Claude user settings must be a regular file")
    if metadata.st_uid != os.getuid():
        raise SystemExit("Claude user settings are not owned by the current user")
    if stat.S_IMODE(metadata.st_mode) & 0o022:
        raise SystemExit("Claude user settings must not be group/world writable")
    chunks = []
    while chunk := os.read(fd, 65536):
        chunks.append(chunk)
finally:
    os.close(fd)

raw = b"".join(chunks)
if hashlib.sha256(raw).hexdigest() != expected_hash:
    raise SystemExit("Claude user settings changed after validation; retry the delegation")

settings = json.loads(raw.decode("utf-8"))
env = settings.get("env", {})
if not isinstance(env, dict):
    raise SystemExit("Claude settings field env must be an object")

name_pattern = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
for key, value in env.items():
    if not isinstance(key, str) or not name_pattern.fullmatch(key):
        raise SystemExit(f"Invalid environment variable name: {key!r}")
    if not isinstance(value, str) or "\0" in value:
        raise SystemExit(f"Invalid string value for environment variable {key!r}")

child_env = os.environ.copy()
child_env.update(env)
os.execve(claude_bin, [claude_bin, *claude_args], child_env)
' "$CLAUDE_USER_SETTINGS_PATH" "$CLAUDE_USER_SETTINGS_HASH" "$@"
}

# ---- argument parsing -------------------------------------------------------

profile="$DEFAULT_PROFILE"
model=""
effort=""
dry_run=0
prompt_arg=""
extra_tools=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    --dry-run)
      dry_run=1
      shift
      ;;
    --profile)
      [[ $# -ge 2 ]] || die "--profile requires a value"
      profile="$2"
      shift 2
      ;;
    --profile=*)
      profile="${1#--profile=}"
      shift
      ;;
    --model)
      [[ $# -ge 2 ]] || die "--model requires a value"
      model="$2"
      shift 2
      ;;
    --model=*)
      model="${1#--model=}"
      shift
      ;;
    --effort)
      [[ $# -ge 2 ]] || die "--effort requires a value"
      effort="$2"
      shift 2
      ;;
    --effort=*)
      effort="${1#--effort=}"
      shift
      ;;
    --allow-tool)
      [[ $# -ge 2 ]] || die "--allow-tool requires a value"
      extra_tools+=("$2")
      shift 2
      ;;
    --allow-tool=*)
      extra_tools+=("${1#--allow-tool=}")
      shift
      ;;
    --)
      shift
      break
      ;;
    -*)
      die "unknown argument: $1"
      ;;
    *)
      if [[ -n "$prompt_arg" ]]; then
        die "only one concrete prompt path may be given (got '$prompt_arg' and '$1')"
      fi
      prompt_arg="$1"
      shift
      ;;
  esac
done

# Allow a trailing positional after `--`.
if [[ -z "$prompt_arg" && $# -eq 1 ]]; then
  prompt_arg="$1"
  shift
elif [[ $# -gt 0 ]]; then
  die "unexpected trailing arguments: $*"
fi

[[ -n "$prompt_arg" ]] || die "missing required <concrete-prompt-path> (see --help)"

# ---- profile resolution -----------------------------------------------------

case "$profile" in
  docs-commit)
    profile_tools="Read,Edit,Write,Bash"
    profile_allowed=(Read Edit Write \
      "Bash(git status:*)" "Bash(git diff:*)" "Bash(git log:*)" \
      "Bash(git show:*)" "Bash(git add:*)" "Bash(git commit:*)")
    ;;
  implementation-commit)
    profile_tools="Read,Edit,Write,Bash,Glob,Grep"
    profile_allowed=(Read Edit Write Glob Grep Bash)
    ;;
  *)
    die "invalid profile '$profile' (expected: docs-commit | implementation-commit)"
    ;;
esac

# ---- repository context -----------------------------------------------------

command -v git >/dev/null 2>&1 || die "git is required but not on PATH"
claude_bin="$(command -v claude 2>/dev/null)" \
  || die "claude (Claude Code) is required but not on PATH"
claude_bin="$(readlink -f -- "$claude_bin")"

root="$(git rev-parse --show-toplevel 2>/dev/null)" \
  || die "must run inside a git worktree"

# Normalize the prompt path to an absolute path, then to a repo-relative path.
prompt_abs="$(readlink -f -- "$prompt_arg" 2>/dev/null || true)"
[[ -n "$prompt_abs" && -f "$prompt_abs" ]] \
  || die "prompt path does not exist or is not a regular file: $prompt_arg"

[[ "$prompt_abs" == "$root"/* ]] \
  || die "prompt must live inside the repository root ($root); got $prompt_abs"
rel="${prompt_abs#"$root"/}"

[[ "$rel" == "$PROMPTS_SUBDIR"/* ]] \
  || die "prompt must live inside $PROMPTS_SUBDIR/ (got $rel)"

cd -- "$root"

[[ "$SCRIPT_PATH" == "$root/scripts/delegate-claude.sh" ]] \
  || die "invoke the canonical launcher at $root/scripts/delegate-claude.sh"

task_head="$(git rev-parse HEAD)"

prompt_name="${rel#"$PROMPTS_SUBDIR"/}"
if [[ "$prompt_name" == *.template.md ]]; then
  die "template prompts cannot be executed; copy it to a concrete <plan-slug>.<execution-slug>.md path"
fi
if [[ ! "$prompt_name" =~ ^([a-z0-9]+(-[a-z0-9]+)*)\.([a-z0-9]+(-[a-z0-9]+)*)\.md$ ]]; then
  die "invalid concrete prompt name '$prompt_name' (expected <plan-slug>.<execution-slug>.md)"
fi
plan_slug="${BASH_REMATCH[1]}"
plan_rel="docs/plans/$plan_slug.md"
git cat-file -e "$task_head:$plan_rel" 2>/dev/null \
  || die "concrete prompt has no committed governing plan at $plan_rel"

# Prompt must be tracked, committed, and unchanged.
git ls-files --error-unmatch -- "$rel" >/dev/null 2>&1 \
  || die "prompt is not tracked by git: $rel (commit it before delegating)"
require_git_clean "$rel" \
  || die "prompt has uncommitted changes or status could not be inspected: $rel"
prompt_commit="$(git log -1 --format=%H -- "$rel" 2>/dev/null)" \
  || die "could not resolve the commit that introduced the prompt"
[[ -n "$prompt_commit" ]] \
  || die "prompt has no commit history: $rel"
prompt_blob="$(git rev-parse "$task_head:$rel" 2>/dev/null)" \
  || die "prompt is not committed at starting HEAD $task_head: $rel"
[[ "$(git cat-file -t "$prompt_blob" 2>/dev/null)" == "blob" ]] \
  || die "committed prompt object is not a blob: $rel"

if ! prompt_status="$(git cat-file blob "$prompt_blob" | python3 -c '
import re
import sys

lines = sys.stdin.read().splitlines()
if not lines or lines[0] != "---":
    raise SystemExit("malformed frontmatter: missing opening delimiter")

closing = [index for index, line in enumerate(lines[1:], start=1) if line == "---"]
if len(closing) != 1:
    raise SystemExit("malformed frontmatter: expected exactly one closing delimiter")

fields = {}
for number, line in enumerate(lines[1:closing[0]], start=2):
    if not line.strip():
        continue
    match = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_-]*):[ \t]*(.*)", line)
    if not match:
        raise SystemExit(f"malformed frontmatter: invalid field at line {number}")
    key, value = match.groups()
    if key in fields:
        raise SystemExit(f"malformed frontmatter: duplicate field {key!r}")
    fields[key] = value

status = fields.get("status")
if status is None:
    raise SystemExit("malformed frontmatter: missing status")
print(status)
')"; then
  die "prompt frontmatter could not be parsed"
fi
[[ "$prompt_status" == "committed" ]] \
  || die "prompt status must be 'committed' before delegation (got '$prompt_status')"

# Branch must be a non-main work/<slug> branch in a clean worktree.
branch="$(git rev-parse --abbrev-ref HEAD)"
[[ "$branch" != "main" && "$branch" != "master" ]] \
  || die "refusing to delegate from '$branch'; use an assigned work/<slug> branch"
[[ "$branch" =~ ^work/[^/]+$ ]] \
  || die "branch '$branch' is not a work/<slug> branch"

require_git_clean \
  || die "worktree is not clean or status could not be inspected"

worktree_path="$(git rev-parse --show-toplevel)"

launcher_rel="scripts/delegate-claude.sh"
git ls-files --error-unmatch -- "$launcher_rel" >/dev/null 2>&1 \
  || die "canonical launcher is not tracked: $launcher_rel"
require_git_clean "$launcher_rel" \
  || die "canonical launcher has uncommitted changes or status could not be inspected: $launcher_rel"
launcher_commit="$(git log -1 --format=%H -- "$launcher_rel")"
launcher_id="committed $launcher_commit"

inspect_claude_user_env
if [[ "$dry_run" -eq 1 ]]; then
  claude_version="not probed (dry run)"
else
  if ! claude_version="$(run_claude_with_user_env "$claude_bin" --version | head -n1)"; then
    die "failed to run Claude Code with the imported user environment"
  fi
  [[ -n "$claude_version" ]] || claude_version="unknown"
fi

# ---- allowed matchers (profile defaults + extras) ---------------------------

allowed_list=("${profile_allowed[@]}")
if [[ ${#extra_tools[@]} -gt 0 ]]; then
  allowed_list+=("${extra_tools[@]}")
fi
# Join with single spaces into one matcher string (Claude Code accepts a
# space-separated --allowed-tools value).
allowed_joined=""
for m in "${allowed_list[@]}"; do
  if [[ -z "$allowed_joined" ]]; then
    allowed_joined="$m"
  else
    allowed_joined="$allowed_joined $m"
  fi
done
extra_grants="${extra_tools[*]:-none}"

# ---- runtime envelope -------------------------------------------------------

prompt_bytes="$(git cat-file -s "$prompt_blob")"

read -r -d '' envelope_header <<EOF || true
Launcher-resolved execution envelope:
- repository root: $root
- prompt path: $rel
- prompt commit: $prompt_commit
- prompt blob: $prompt_blob
- launcher commit: $launcher_id
- task base / starting HEAD: $task_head
- branch: $branch
- worktree: $worktree_path
- Claude Code version: $claude_version
- permission profile: $profile
- built-in tools: $profile_tools
- allowed matchers: $allowed_joined
- extra tool grants: $extra_grants
- network: $NETWORK_POLICY
- MCP: $MCP_POLICY
- persistence: $PERSISTENCE_POLICY
- settings: $SETTINGS_NOTE
- user env source: $CLAUDE_USER_SETTINGS_PATH
- user env keys: $CLAUDE_IMPORTED_ENV_KEYS
- user env values: redacted
- lifecycle authority: none

The committed concrete prompt at $rel (commit $prompt_commit) follows verbatim.
Do not modify the concrete prompt. Treat this envelope plus the committed prompt
and the governing plan as the complete handoff; report any mismatch instead of
overriding the resolved context.

---BEGIN CONCRETE PROMPT---
EOF

readonly envelope_footer='---END CONCRETE PROMPT---'

# ---- command construction ---------------------------------------------------

cmd=("$claude_bin" --print --permission-mode dontAsk --tools "$profile_tools"
    --allowed-tools "$allowed_joined" --mcp-config '{"mcpServers":{}}' --strict-mcp-config
    --setting-sources project --no-session-persistence --verbose --output-format stream-json)
[[ -n "$model" ]] && cmd+=(--model "$model")
[[ -n "$effort" ]] && cmd+=(--effort "$effort")

# ---- dry run ----------------------------------------------------------------

if [[ "$dry_run" -eq 1 ]]; then
  printf '# delegate-claude.sh dry run\n'
  printf '# No Claude Code process was started.\n\n'
  printf '## Resolved envelope\n'
  printf '%s\n' "$envelope_header"
  git cat-file blob "$prompt_blob"
  printf '\n%s\n\n' "$envelope_footer"
  printf '## Claude invocation posture\n'
  printf '  claude --print --permission-mode dontAsk \\\n'
  printf '    --tools %s \\\n' "$profile_tools"
  printf '    --allowed-tools %s \\\n' "$allowed_joined"
  printf '    --mcp-config {"mcpServers":{}} --strict-mcp-config \\\n'
  printf '    --setting-sources project --no-session-persistence \\\n'
  printf '    --verbose --output-format stream-json'
  [[ -n "$model" ]]  && printf ' \\\n    --model %s' "$model"
  [[ -n "$effort" ]] && printf ' \\\n    --effort %s' "$effort"
  printf ' \\\n    <stdin: envelope + %s verbatim bytes from %s>\n' "$prompt_bytes" "$rel"
  printf '\n## Prompt identity\n'
  printf '  path: %s\n' "$rel"
  printf '  commit: %s\n' "$prompt_commit"
  printf '  size: %s bytes\n' "$prompt_bytes"
  printf '\nDry run OK.\n'
  exit 0
fi

# ---- invocation + non-destructive postflight --------------------------------

printf 'delegate-claude.sh: starting Claude Code (profile=%s branch=%s base=%s)\n' \
  "$profile" "$branch" "$task_head" >&2
printf '  prompt            : %s\n' "$rel" >&2
printf '  prompt commit     : %s\n' "$prompt_commit" >&2
printf '  prompt blob       : %s\n' "$prompt_blob" >&2
printf '  launcher commit   : %s\n' "$launcher_commit" >&2
printf '  worktree          : %s\n' "$worktree_path" >&2
printf '  Claude Code       : %s\n' "$claude_version" >&2
printf '  model / effort    : %s / %s\n' "${model:-default}" "${effort:-default}" >&2
printf '  built-in tools    : %s\n' "$profile_tools" >&2
printf '  allowed matchers  : %s\n' "$allowed_joined" >&2
printf '  extra grants      : %s\n' "$extra_grants" >&2
printf '  runtime posture   : network %s; MCP %s; persistence %s; %s\n' \
  "$NETWORK_POLICY" "$MCP_POLICY" "$PERSISTENCE_POLICY" "$SETTINGS_NOTE" >&2
printf '  user env source   : %s\n' "$CLAUDE_USER_SETTINGS_PATH" >&2
printf '  user env keys     : %s\n' "$CLAUDE_IMPORTED_ENV_KEYS" >&2
printf '  user env values   : redacted\n' >&2

stream_handoff() {
  printf '%s\n' "$envelope_header" || return
  git cat-file blob "$prompt_blob" || return
  printf '\n%s\n' "$envelope_footer"
}

set +e
stream_handoff | run_claude_with_user_env "${cmd[@]}"
pipeline_status=("${PIPESTATUS[@]}")
producer_rc="${pipeline_status[0]}"
claude_rc="${pipeline_status[1]}"
rc="$claude_rc"
if [[ "$rc" -eq 0 && "$producer_rc" -ne 0 ]]; then
  rc="$producer_rc"
fi

new_head="$(git rev-parse HEAD 2>/dev/null || printf 'unresolved')"
current_branch="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || printf 'unresolved')"
commits_created=0
if [[ "$new_head" != "unresolved" && "$new_head" != "$task_head" ]]; then
  git merge-base --is-ancestor "$task_head" "$new_head" 2>/dev/null
  ancestor_rc=$?
  if [[ "$ancestor_rc" -eq 0 ]]; then
    commits_created="$(git rev-list --count "${task_head}..${new_head}" 2>/dev/null)"
    [[ $? -eq 0 ]] || commits_created="unresolved"
  elif [[ "$ancestor_rc" -eq 1 ]]; then
    commits_created="unknown (current HEAD is not a descendant of starting HEAD)"
  else
    commits_created="unresolved"
  fi
fi
diff_paths="$(git diff --name-only "$task_head" 2>/dev/null)"
diff_rc=$?
untracked_paths="$(git ls-files --others --exclude-standard 2>/dev/null)"
untracked_rc=$?
if [[ "$diff_rc" -eq 0 && "$untracked_rc" -eq 0 ]]; then
  changed_paths_state="complete"
elif [[ "$diff_rc" -eq 0 || "$untracked_rc" -eq 0 ]]; then
  changed_paths_state="partial"
else
  changed_paths_state="unresolved"
fi
changed_paths="$(printf '%s\n%s\n' "$diff_paths" "$untracked_paths" | awk 'NF' | sort -u)"

status_output="$(git status --porcelain 2>/dev/null)"
status_rc=$?
if [[ "$status_rc" -ne 0 ]]; then
  worktree_clean="unresolved"
elif [[ -z "$status_output" ]]; then
  worktree_clean="yes"
else
  worktree_clean="no"
fi

printf '\n' >&2
printf 'delegate-claude.sh: postflight (non-destructive)\n' >&2
printf '  input exit status  : %s\n' "$producer_rc" >&2
printf '  claude exit status : %s\n' "$claude_rc" >&2
printf '  launcher status    : %s\n' "$rc" >&2
printf '  starting HEAD      : %s\n' "$task_head" >&2
printf '  current HEAD       : %s\n' "$new_head" >&2
printf '  starting branch    : %s\n' "$branch" >&2
printf '  current branch     : %s\n' "$current_branch" >&2
printf '  commits created    : %s\n' "$commits_created" >&2
printf '  worktree clean     : %s\n' "$worktree_clean" >&2
printf '  changed-path scan  : %s\n' "$changed_paths_state" >&2
if [[ -n "$changed_paths" ]]; then
  printf '  changed paths      :\n' >&2
  while IFS= read -r line; do
    printf '    - %s\n' "$line" >&2
  done <<< "$changed_paths"
  printf '  (review the main...%s diff before integrating)\n' "$branch" >&2
fi

exit "$rc"
