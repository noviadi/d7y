#!/usr/bin/env bash
set -euo pipefail

source_root="$(git rev-parse --show-toplevel)"
fixture_root="$(mktemp -d "${TMPDIR:-/tmp}/d7y-delegate-frontmatter.XXXXXX")"
trap 'rm -rf -- "$fixture_root"' EXIT

git init -q -b work/frontmatter "$fixture_root"
git -C "$fixture_root" config user.email test@example.invalid
git -C "$fixture_root" config user.name "D7Y test"
mkdir -p "$fixture_root/scripts" "$fixture_root/docs/prompts" "$fixture_root/docs/plans"
cp "$source_root/scripts/delegate-claude.sh" "$fixture_root/scripts/delegate-claude.sh"
chmod +x "$fixture_root/scripts/delegate-claude.sh"
printf '# test plan\n' > "$fixture_root/docs/plans/test.md"

test_home="$fixture_root/home"
fake_bin="$fixture_root/bin"
mkdir -p "$test_home/.claude" "$fake_bin"
printf '{"env": {}}\n' > "$test_home/.claude/settings.json"
cat > "$fake_bin/claude" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF
chmod +x "$fake_bin/claude"

write_prompt() {
  local name="$1"
  shift
  {
    printf '%s\n' '---'
    printf '%s\n' "$@"
    printf '%s\n' '---' '# test prompt'
  } > "$fixture_root/docs/prompts/$name"
}

write_prompt test.valid.md 'status: committed'
write_prompt test.draft.md 'status: draft'
write_prompt test.missing.md 'plan: docs/plans/test.md'
write_prompt test.duplicate.md 'status: committed' 'status: draft'
{
  printf '%s\n' '---' 'status: committed'
  printf '%s\n' '# missing closing delimiter'
} > "$fixture_root/docs/prompts/test.malformed.md"

git -C "$fixture_root" add .
git -C "$fixture_root" commit -q -m 'frontmatter fixtures'

run_launcher() {
  local prompt="$1"
  (cd "$fixture_root" && env HOME="$test_home" PATH="$fake_bin:$PATH" \
    "$fixture_root/scripts/delegate-claude.sh" --dry-run \
    "docs/prompts/$prompt")
}

run_launcher test.valid.md >/dev/null 2>&1

for invalid_prompt in test.draft.md test.missing.md test.duplicate.md test.malformed.md; do
  if run_launcher "$invalid_prompt" >/dev/null 2>&1; then
    printf 'expected rejection for %s\n' "$invalid_prompt" >&2
    exit 1
  fi
done

printf 'delegate prompt frontmatter fixtures passed\n'
