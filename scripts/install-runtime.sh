#!/usr/bin/env bash
# scripts/install-runtime.sh
#
# Deterministic D7Y runtime installer for the dev-install binding. Materializes
# a runnable D7Y runtime in a target directory:
#
#   .d7y/skills/<name>                -> this repo's agents/skills/<name>  (absolute)
#   .d7y/d7y                          -> this repo's d7y                   (absolute)
#   .d7y/scripts/check-initiatives.py -> this repo's scripts/check-initiatives.py
#   .claude/skills/<name>             -> ../../.d7y/skills/<name>          (relative)
#   AGENTS.md                         -> copied from agents/runtime-AGENTS.md
#   CLAUDE.md                         -> AGENTS.md                        (relative)
#   initiatives/README.md             -> copied from initiatives/README.md
#
# Skills, the executable, and the checker are symlinked (not copied) so source
# edits stay live in every installed runtime — the same live-edit intent for
# which the skills are symlinked. The d7y facade resolves its own root via
# `readlink -f`, so a symlinked .d7y/d7y resolves ROOT to this repository and
# finds scripts/check-initiatives.py there; the placed .d7y/scripts symlink is
# layout-consistent and points at the same source.
#
# Idempotent: re-running re-links and refreshes the copied artifacts but
# preserves an existing target initiatives/ tree. It refuses (non-zero exit,
# clear message) to clobber an initiatives/ that holds data beyond the placed
# README.md, and exits before writing anything in that case.
#
# This is a deterministic local install helper, not a workflow engine, durable
# control plane, or production installer. It performs local symlink/copy
# operations only: no network, no persistent state, no Git lifecycle actions.
# See docs/plans/runtime-binding-claude-code.md (Stage B2).

set -euo pipefail

readonly SELF_PATH="$(readlink -f -- "${BASH_SOURCE[0]:-$0}")"
readonly SOURCE_ROOT="$(dirname -- "$(dirname -- "$SELF_PATH")")"
readonly SOURCE_D7Y="$SOURCE_ROOT/d7y"
readonly SOURCE_CHECKER="$SOURCE_ROOT/scripts/check-initiatives.py"
readonly SOURCE_RUNTIME_AGENTS="$SOURCE_ROOT/agents/runtime-AGENTS.md"
readonly SOURCE_INITIATIVES_README="$SOURCE_ROOT/initiatives/README.md"
readonly SOURCE_SKILLS="$SOURCE_ROOT/agents/skills"

die() {
  printf 'd7y dev install: %s\n' "$*" >&2
  exit 2
}

usage() {
  cat <<'EOF'
Usage: d7y dev install <directory>

Materialize a runnable D7Y runtime in <directory> (the dev-install binding):
symlinked skills, executable, and checker (live-edit from this repository); a
copied runtime constitution (AGENTS.md); a CLAUDE.md symlink; the Claude Code
project-scope skill-discovery symlinks; and the placed initiative contract.

The target directory and its parents are created if they do not exist. As with
other `d7y dev` commands, a relative <directory> resolves from the repository
root.

Idempotent: re-running re-links and refreshes artifacts but preserves an
existing initiatives/ tree. Refuses (non-zero exit) to clobber an initiatives/
that holds data beyond the placed README.md; nothing is destroyed.

After install, `d7y` is reachable in-session by prepending the target's .d7y/
to PATH, e.g. from <directory>:

  export PATH="$PWD/.d7y:$PATH"

The target workspace must be trusted in Claude Code for project-scope skills
(.claude/skills/<name>) to load.

Options:
  -h, --help   Show this help and exit.
EOF
}

# ---- argument parsing -------------------------------------------------------

target_arg=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    --)
      shift
      [[ $# -eq 1 ]] || die "exactly one <directory> is required"
      target_arg="$1"
      shift
      ;;
    -*)
      die "unknown option: $1"
      ;;
    *)
      [[ -z "$target_arg" ]] || die "only one <directory> may be given (got '$target_arg' and '$1')"
      target_arg="$1"
      shift
      ;;
  esac
done

if [[ -z "$target_arg" ]]; then
  usage >&2
  exit 2
fi

# ---- target resolution ------------------------------------------------------

# Resolve to an absolute path, creating the directory (and parents) if needed.
# A target that already exists must be a directory.
if [[ -e "$target_arg" ]]; then
  [[ -d "$target_arg" ]] || die "target exists and is not a directory: $target_arg"
  target="$(readlink -f -- "$target_arg")" || die "cannot resolve target: $target_arg"
else
  mkdir -p -- "$target_arg" || die "cannot create target directory: $target_arg"
  target="$(readlink -f -- "$target_arg")" || die "cannot resolve target: $target_arg"
fi
[[ -n "$target" && -d "$target" ]] || die "resolved target is not a directory: $target_arg"

# Refuse to install D7Y into its own source tree: that would overwrite the
# repository's own root AGENTS.md/CLAUDE.md symlinks and scatter runtime
# artifacts into the source checkout.
[[ "$target" != "$SOURCE_ROOT" ]] \
  || die "refusing to install into the D7Y source tree itself ($SOURCE_ROOT); choose a separate target"

# ---- source validation ------------------------------------------------------

for f in "$SOURCE_D7Y" "$SOURCE_CHECKER" "$SOURCE_RUNTIME_AGENTS" "$SOURCE_INITIATIVES_README"; do
  [[ -f "$f" ]] || die "source artifact missing: $f (run from a D7Y repository checkout)"
done
[[ -d "$SOURCE_SKILLS" ]] || die "source skills directory missing: $SOURCE_SKILLS"

# ---- clobber guard ----------------------------------------------------------

# Protect any existing initiative data. initiatives/README.md is a D7Y-owned
# contract artifact (refreshed on re-run); anything else under initiatives/ is
# treated as irreplaceable workspace data. Check before writing anything.
if [[ -d "$target/initiatives" ]]; then
  shopt -s nullglob dotglob
  extra=()
  for entry in "$target/initiatives"/*; do
    [[ "$(basename -- "$entry")" == "README.md" ]] && continue
    extra+=("$entry")
  done
  shopt -u dotglob nullglob
  if [[ ${#extra[@]} -gt 0 ]]; then
    die "refusing to clobber existing initiative data under $target/initiatives/ (found ${extra[0]}); move it aside or choose a fresh target"
  fi
fi

# ---- materialize the runtime ------------------------------------------------

mkdir -p -- "$target/.d7y/skills" "$target/.d7y/scripts" \
          "$target/.claude/skills" "$target/initiatives"

# Skills: .d7y/skills/<name> -> repo source (absolute), and
# .claude/skills/<name> -> ../../.d7y/skills/<name> (relative) for Claude Code
# project-scope discovery. Discover every skill directory so new skills are
# surfaced automatically.
shopt -s nullglob
skill_names=()
for d in "$SOURCE_SKILLS"/*/; do
  name="$(basename -- "$d")"
  skill_names+=("$name")
  ln -sfn -- "$SOURCE_SKILLS/$name" "$target/.d7y/skills/$name"
  ln -sfn -- "../../.d7y/skills/$name" "$target/.claude/skills/$name"
done
shopt -u nullglob
[[ ${#skill_names[@]} -gt 0 ]] || die "no source skills found under $SOURCE_SKILLS"

# Executable + checker: symlinked for live-edit consistency with the skills.
ln -sfn -- "$SOURCE_D7Y" "$target/.d7y/d7y"
ln -sfn -- "$SOURCE_CHECKER" "$target/.d7y/scripts/check-initiatives.py"

# Runtime constitution: copied (not symlinked) per the install model.
cp -f -- "$SOURCE_RUNTIME_AGENTS" "$target/AGENTS.md"
ln -sfn -- "AGENTS.md" "$target/CLAUDE.md"

# Initiative contract: placed / refreshed.
cp -f -- "$SOURCE_INITIATIVES_README" "$target/initiatives/README.md"

# ---- guidance ---------------------------------------------------------------

printf 'Installed D7Y runtime at %s\n' "$target"
printf '\n'
printf 'Layout (symlinks are live-edit from this repository):\n'
for name in "${skill_names[@]}"; do
  printf '  .d7y/skills/%-22s -> %s/agents/skills/%s\n' "$name" "$SOURCE_ROOT" "$name"
  printf '  .claude/skills/%-19s -> ../../.d7y/skills/%s\n' "$name" "$name"
done
printf '  .d7y/d7y                          -> %s/d7y\n' "$SOURCE_ROOT"
printf '  .d7y/scripts/check-initiatives.py -> %s/scripts/check-initiatives.py\n' "$SOURCE_ROOT"
printf '  AGENTS.md                         (copied from agents/runtime-AGENTS.md)\n'
printf '  CLAUDE.md                         -> AGENTS.md\n'
printf '  initiatives/README.md             (placed)\n'
printf '\n'
printf 'Reach d7y in-session: the runtime orientation (AGENTS.md, auto-loaded)\n'
printf 'names the executable at .d7y/d7y. Invoke it directly, or prepend .d7y/ to\n'
printf 'PATH for the bare `d7y` form:\n'
printf '  cd %s\n' "$target"
printf '  export PATH="$PWD/.d7y:$PATH"\n'
printf '  d7y initiatives list\n'
printf '\n'
printf 'Workspace trust: this directory must be trusted in Claude Code for\n'
printf 'project-scope skills (.claude/skills/<name>) to load. In an untrusted\n'
printf 'workspace the skills are logged as "not loaded" until you accept the trust\n'
printf 'dialog and run /reload-plugins.\n'
