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
  (--setting-sources project). Output is --verbose --output-format stream-json
  under --print.

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
  || die "prompt has uncommitted changes: $rel (commit it before delegating)"
prompt_commit="$(git log -1 --format=%H -- "$rel" 2>/dev/null)" \
  || die "could not resolve the commit that introduced the prompt"
[[ -n "$prompt_commit" ]] \
  || die "prompt has no commit history: $rel"
prompt_blob="$(git rev-parse "$task_head:$rel" 2>/dev/null)" \
  || die "prompt is not committed at starting HEAD $task_head: $rel"
[[ "$(git cat-file -t "$prompt_blob" 2>/dev/null)" == "blob" ]] \
  || die "committed prompt object is not a blob: $rel"

# Branch must be a non-main work/<slug> branch in a clean worktree.
branch="$(git rev-parse --abbrev-ref HEAD)"
[[ "$branch" != "main" && "$branch" != "master" ]] \
  || die "refusing to delegate from '$branch'; use an assigned work/<slug> branch"
[[ "$branch" =~ ^work/[^/]+$ ]] \
  || die "branch '$branch' is not a work/<slug> branch"

require_git_clean \
  || die "worktree is not clean; commit or discard changes before delegating"

worktree_path="$(git rev-parse --show-toplevel)"
claude_version="$(claude --version 2>/dev/null | head -n1 || echo "unknown")"

launcher_rel="scripts/delegate-claude.sh"
git ls-files --error-unmatch -- "$launcher_rel" >/dev/null 2>&1 \
  || die "canonical launcher is not tracked: $launcher_rel"
require_git_clean "$launcher_rel" \
  || die "canonical launcher has uncommitted changes: $launcher_rel"
launcher_commit="$(git log -1 --format=%H -- "$launcher_rel")"
launcher_id="committed $launcher_commit"

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

stream_handoff() {
  printf '%s\n' "$envelope_header" || return
  git cat-file blob "$prompt_blob" || return
  printf '\n%s\n' "$envelope_footer"
}

set +e
stream_handoff | "${cmd[@]}"
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
  if git merge-base --is-ancestor "$task_head" "$new_head"; then
    commits_created="$(git rev-list --count "${task_head}..${new_head}")"
  else
    commits_created="unknown (current HEAD is not a descendant of starting HEAD)"
  fi
fi
changed_paths="$({ git diff --name-only "$task_head" 2>/dev/null || true; git ls-files --others --exclude-standard 2>/dev/null || true; } | awk 'NF' | sort -u)"
worktree_clean="no"
if require_git_clean; then
  worktree_clean="yes"
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
if [[ -n "$changed_paths" ]]; then
  printf '  changed paths      :\n' >&2
  while IFS= read -r line; do
    printf '    - %s\n' "$line" >&2
  done <<< "$changed_paths"
  printf '  (review the main...%s diff before integrating)\n' "$branch" >&2
fi

exit "$rc"
