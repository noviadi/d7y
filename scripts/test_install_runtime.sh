#!/usr/bin/env bash
# Focused fixtures for scripts/install-runtime.sh (d7y dev install): layout,
# in-target command resolution, idempotency, clobber refusal, and guidance.
# Mirrors the style of scripts/test_delegate_prompt_frontmatter.sh.
set -euo pipefail

source_root="$(git rev-parse --show-toplevel)"
fixture_root="$(mktemp -d "${TMPDIR:-/tmp}/d7y-install-runtime.XXXXXX")"
trap 'rm -rf -- "$fixture_root"' EXIT

target="$fixture_root/runtime"
d7y_bin="$source_root/d7y"

fail() {
  printf 'test_install_runtime: assertion failed: %s\n' "$*" >&2
  exit 1
}

assert_resolves() {
  [[ -e "$1" ]] || fail "$1 does not resolve"
}
assert_link_target() {
  local got
  got="$(readlink -- "$1")"
  [[ "$got" == "$2" ]] || fail "$1 readlink -> '$got' (want '$2')"
}
assert_file_equals() {
  cmp -s -- "$1" "$2" || fail "$1 != $2"
}
assert_regular_file() {
  [[ -f "$1" && ! -L "$1" ]] || fail "$1 is not a regular file"
}

# 1. Fresh install produces the exact layout and emits guidance.
out="$("$d7y_bin" dev install "$target")"
[[ "$out" == *'export PATH="$PWD/.d7y:$PATH"'* ]] || fail "PATH access guidance not emitted"
[[ "$out" == *'must be trusted'* ]] || fail "workspace-trust guidance not emitted"

for name in starting-initiatives writing-great-skills; do
  assert_link_target "$target/.d7y/skills/$name" "$source_root/agents/skills/$name"
  assert_resolves "$target/.d7y/skills/$name/SKILL.md"
  assert_link_target "$target/.claude/skills/$name" "../../.d7y/skills/$name"
  assert_resolves "$target/.claude/skills/$name/SKILL.md"
  assert_file_equals "$target/.claude/skills/$name/SKILL.md" "$source_root/agents/skills/$name/SKILL.md"
done
assert_link_target "$target/.d7y/d7y" "$source_root/d7y"
assert_resolves "$target/.d7y/d7y"
assert_link_target "$target/.d7y/scripts/check-initiatives.py" "$source_root/scripts/check-initiatives.py"
assert_regular_file "$target/AGENTS.md"
assert_file_equals "$target/AGENTS.md" "$source_root/agents/runtime-AGENTS.md"
assert_link_target "$target/CLAUDE.md" "AGENTS.md"
assert_resolves "$target/CLAUDE.md"
assert_regular_file "$target/initiatives/README.md"
assert_file_equals "$target/initiatives/README.md" "$source_root/initiatives/README.md"

# 2. From the target workspace, d7y initiatives list/check resolve and work.
list_json="$("$target/.d7y/d7y" initiatives list --root "$target" --json)"
printf '%s' "$list_json" | python3 -c \
  'import json,sys; d=json.load(sys.stdin); assert d["valid"] is True and d["count"] == 0, d'
"$target/.d7y/d7y" initiatives check --root "$target" >/dev/null
# Discovery path (no --root), run from inside the target workspace:
( cd "$target" && "$target/.d7y/d7y" initiatives list --json >/dev/null )

# 3. Idempotent: re-running changes nothing material.
snapshot() {
  readlink -- "$target/.d7y/d7y"
  readlink -- "$target/.d7y/scripts/check-initiatives.py"
  readlink -- "$target/.d7y/skills/starting-initiatives"
  readlink -- "$target/.claude/skills/starting-initiatives"
  readlink -- "$target/CLAUDE.md"
  cksum -- "$target/AGENTS.md" "$target/initiatives/README.md"
}
before="$(snapshot)"
"$d7y_bin" dev install "$target" >/dev/null
after="$(snapshot)"
[[ "$before" == "$after" ]] || fail "idempotent re-run changed material state"

# 4. Clobber refusal: existing initiative data is rejected; nothing is destroyed.
mkdir -p "$target/initiatives/alpha"
cat > "$target/initiatives/alpha/initiative.md" <<'EOF'
---
title: Alpha
status: active
created: 2026-08-03
updated: 2026-08-03
aliases: []
related: []
---

# Alpha
EOF
if "$d7y_bin" dev install "$target" >/dev/null 2>&1; then
  fail "install succeeded over existing initiative data (should have refused)"
fi
[[ -f "$target/initiatives/alpha/initiative.md" ]] || fail "clobber refusal destroyed initiative data"
assert_file_equals "$target/AGENTS.md" "$source_root/agents/runtime-AGENTS.md"

# 5. Self-install into the source tree is refused.
if "$d7y_bin" dev install "$source_root" >/dev/null 2>&1; then
  fail "install into the source tree succeeded (should have refused)"
fi

printf 'install-runtime fixtures passed\n'
