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

readonly SCRIPT_PATH="${BASH_SOURCE[0]:-$0}"
readonly PROMPTS_SUBDIR="docs/prompts"
readonly DEFAULT_PROFILE="docs-commit"
readonly NETWORK_POLICY="prohibited"
readonly MCP_POLICY="strict empty configuration"
readonly PERSISTENCE_POLICY="disabled"
readonly SETTINGS_NOTE="project-only via --setting-sources project"

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
  Network is prohibited. MCP is strict-empty
  (--mcp-config '{"mcpServers":{}}' --strict-mcp-config).
  Sessions are non-persistent (--no-session-persistence). Settings are project-only
  (--setting-sources project). Output is --output-format stream-json under --print.

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
    out="$(git status --porcelain -- "$1")"
  else
    out="$(git status --porcelain)"
  fi
  [[ -z "$out" ]]
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
command -v claude >/dev/null 2>&1 || die "claude (Claude Code) is required but not on PATH"

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

# Prompt must be tracked, committed, and unchanged.
git ls-files --error-unmatch -- "$rel" >/dev/null 2>&1 \
  || die "prompt is not tracked by git: $rel (commit it before delegating)"
require_git_clean "$rel" \
  || die "prompt has uncommitted changes: $rel (commit it before delegating)"
prompt_commit="$(git log -1 --format=%H -- "$rel" 2>/dev/null)" \
  || die "could not resolve the commit that introduced the prompt"
[[ -n "$prompt_commit" ]] \
  || die "prompt has no commit history: $rel"

# Branch must be a non-main work/<slug> branch in a clean worktree.
branch="$(git rev-parse --abbrev-ref HEAD)"
[[ "$branch" != "main" && "$branch" != "master" ]] \
  || die "refusing to delegate from '$branch'; use an assigned work/<slug> branch"
[[ "$branch" =~ ^work/[^/]+$ ]] \
  || die "branch '$branch' is not a work/<slug> branch"

require_git_clean \
  || die "worktree is not clean; commit or discard changes before delegating"

task_head="$(git rev-parse HEAD)"
worktree_path="$(git rev-parse --show-toplevel)"
claude_version="$(claude --version 2>/dev/null | head -n1 || echo "unknown")"

# Launcher commit: the commit that last touched this script. During the initial
# bootstrap the launcher is brand new and may not yet be committed; report that
# honestly rather than fabricating an ID.
launcher_rel="${SCRIPT_PATH#"$root"/}"
if git ls-files --error-unmatch -- "$launcher_rel" >/dev/null 2>&1 \
   && require_git_clean "$launcher_rel"; then
  launcher_commit="$(git log -1 --format=%H -- "$launcher_rel")"
  launcher_id="committed $launcher_commit"
else
  launcher_id="bootstrap exception; $launcher_rel is untracked or uncommitted"
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

prompt_bytes="$(wc -c < "$prompt_abs" | tr -d ' ')"

read -r -d '' envelope_header <<EOF || true
Launcher-resolved execution envelope:
- repository root: $root
- prompt path: $rel
- prompt commit: $prompt_commit
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
- lifecycle authority: none

The committed concrete prompt at $rel (commit $prompt_commit) follows verbatim.
Do not modify the concrete prompt. Treat this envelope plus the committed prompt
and the governing plan as the complete handoff; report any mismatch instead of
overriding the resolved context.

---BEGIN CONCRETE PROMPT---
EOF

readonly envelope_footer='---END CONCRETE PROMPT---'

# ---- command construction ---------------------------------------------------

cmd=(claude --print --permission-mode dontAsk --tools "$profile_tools"
    --allowed-tools "$allowed_joined" --mcp-config '{"mcpServers":{}}' --strict-mcp-config
    --setting-sources project --no-session-persistence --output-format stream-json)
[[ -n "$model" ]] && cmd+=(--model "$model")
[[ -n "$effort" ]] && cmd+=(--effort "$effort")

# ---- dry run ----------------------------------------------------------------

if [[ "$dry_run" -eq 1 ]]; then
  printf '# delegate-claude.sh dry run\n'
  printf '# No Claude Code process was started.\n\n'
  printf '## Resolved envelope\n'
  printf '%s\n' "$envelope_header"
  cat -- "$prompt_abs"
  printf '\n%s\n\n' "$envelope_footer"
  printf '## Claude invocation posture\n'
  printf '  claude --print --permission-mode dontAsk \\\n'
  printf '    --tools %s \\\n' "$profile_tools"
  printf '    --allowed-tools %s \\\n' "$allowed_joined"
  printf '    --mcp-config {"mcpServers":{}} --strict-mcp-config \\\n'
  printf '    --setting-sources project --no-session-persistence \\\n'
  printf '    --output-format stream-json'
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

set +e
{
  printf '%s\n' "$envelope_header"
  cat -- "$prompt_abs"
  printf '\n%s\n' "$envelope_footer"
} | "${cmd[@]}"
rc="${PIPESTATUS[1]}"
set -e

new_head="$(git rev-parse HEAD)"
commits_created=0
if [[ "$new_head" != "$task_head" ]]; then
  if git merge-base --is-ancestor "$task_head" "$new_head"; then
    commits_created="$(git rev-list --count "${task_head}..${new_head}")"
  else
    commits_created="unknown (current HEAD is not a descendant of starting HEAD)"
  fi
fi
changed_paths="$({
  git diff --name-only "$task_head" 2>/dev/null
  git ls-files --others --exclude-standard
} | awk 'NF' | sort -u)"
worktree_clean="no"
if require_git_clean; then
  worktree_clean="yes"
fi

printf '\n' >&2
printf 'delegate-claude.sh: postflight (non-destructive)\n' >&2
printf '  claude exit status : %s\n' "$rc" >&2
printf '  starting HEAD      : %s\n' "$task_head" >&2
printf '  current HEAD       : %s\n' "$new_head" >&2
printf '  branch             : %s\n' "$branch" >&2
printf '  commits created    : %s\n' "$commits_created" >&2
printf '  worktree clean     : %s\n' "$worktree_clean" >&2
if [[ -n "$changed_paths" ]]; then
  printf '  changed paths      :\n' >&2
  while IFS= read -r line; do
    printf '    - %s\n' "$line" >&2
  done <<< "$changed_paths"
  printf '  (review the main...%s diff before integrating)\n' "$branch" >&2
  fi

exit "$rc"
