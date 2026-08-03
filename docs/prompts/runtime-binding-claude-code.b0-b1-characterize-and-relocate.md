---
status: draft
plan: docs/plans/runtime-binding-claude-code.md
execution: b0-b1-characterize-and-relocate
executor: claude-code
branch: work/runtime-binding-b0-b1
worktree: ../d7y-worktrees/runtime-binding-b0-b1
permissionProfile: implementation-commit
commit: allowed
---

# Objective

Execute Stage B0 and Stage B1 of `docs/plans/runtime-binding-claude-code.md`.

- **B0 — characterize:** determine how the target Claude Code version discovers
  project skills and whether it follows symlinks, and record the finding.
- **B1 — relocate + author:** move the canonical source under `agents/`
  (`skills/` → `agents/skills/`; dev constitution → `agents/AGENTS.md` with root
  symlinks), author the runtime constitution at `agents/runtime-AGENTS.md`, and
  fix resulting path references.

This is a **pure relocation + symlink + authoring + path-ref** task. It does
**not** build `d7y dev install` (that is Stage B2, separate), does not change
skill content or behavior, does not change eval logic, and does not edit canon.

# Required context

Read before editing:

- the governing plan (`docs/plans/runtime-binding-claude-code.md`), especially
  _Binding/install model_, _Runtime constitution_, _Stage B0_, and _Stage B1_;
- `AGENTS.md` and `CLAUDE.md`;
- `docs/prompts/README.md` (prompt artifact contract) and
  `docs/prompts/delegate-implementation.template.md`;
- `evals/validate_skill_evals.py` and `evals/skill-evals.schema.json` — note
  whether skill discovery hardcodes `skills/`;
- `skills/*/SKILL.md` and `skills/*/evals/evals.json` (note each `evals.json`
  `$schema` relative reference);
- `docs/discovery-workbench.md` and `docs/discovery-workbench-principles.md` —
  the source material for the runtime constitution's orientation content;
- the complete committed diff from the launcher-resolved base.

# Writable paths

- `agents/` (new — `agents/skills/`, `agents/AGENTS.md`, `agents/runtime-AGENTS.md`)
- `skills/` (contents moved out via `git mv`)
- `AGENTS.md`, `CLAUDE.md` (root — converted to symlinks)
- `evals/validate_skill_evals.py` (path references only, if discovery hardcodes `skills/`)
- `skills/*/evals/evals.json` (moved with `skills/`; fix `$schema` relative refs)
- `docs/` (path-reference fixes only, where text cites `skills/` locations)

New files are authorized only at the paths above. Do not modify this prompt. Do
not edit skill content, eval logic, the schema, or canon
(`docs/discovery-workbench*`, `docs/skill-evaluations.md`). `d7y dev install` is
out of scope (B2).

# Permission envelope

- Profile: `implementation-commit`
- Extra tool grants: none.
- Network: prohibited. (B0 works from local inspection of the Claude Code
  installation and known mechanics; do not fetch docs over the network.)
- MCP servers: none (strict-empty).
- External services and credentials: none.
- Commit authority: allowed; make cohesive implementation commits on the
  assigned branch and stage only writable paths.
- Lifecycle authority: none. Do not rebase, merge, push, remove worktrees,
  create/rename/delete branches, amend existing commits, or force any Git
  operation.

# Implementation requirements

## B0 first

Determine, by inspecting the local Claude Code installation and reasoning from
its known mechanics: how project skills are discovered
(`.claude/skills/<name>/SKILL.md`); whether symlinks are followed at the skill
directory and at `SKILL.md`; how a skill's deterministic command is reached
in-session; and what load/trigger signal is observable. Record this as a
**Claude Code binding contract** note appended to the plan feedback. **If
symlinks are not viable, stop and return — do not proceed to B1.** The install
model depends on symlinked skills.

## B1 (only if B0 confirms symlinks are viable)

- `git mv skills/*` → `agents/skills/*` (preserve history; do not copy).
- `git mv AGENTS.md` → `agents/AGENTS.md`; make the repo-root `AGENTS.md` a
  symlink to `agents/AGENTS.md`. Make `CLAUDE.md` a symlink to `AGENTS.md`
  (unifying with the runtime pattern); if the prior two-companion dev design
  must be preserved, keep `CLAUDE.md` as a thin separate companion instead —
  record the choice either way.
- Author `agents/runtime-AGENTS.md` per the plan's _Runtime constitution_ spec:
  orientation only — (1) what the workbench is; (2) initiatives as the key
  artifact plus the folder structure and `d7y initiatives list/check`; (3) a
  skill-heavy guideline scoped to the currently available skills
  (`starting-initiatives`, `writing-great-skills`). Exclude all dev operating
  model.
- Fix path references caused by the move: `evals/validate_skill_evals.py`
  skill discovery (`skills/` → `agents/skills/`) if hardcoded; each
  `evals.json` `$schema` relative reference; and any `docs/` text citing
  `skills/` locations.
- No skill content changes; no eval logic changes; no CLI changes.

# Verification

1. `python3 evals/validate_skill_evals.py` — discovers and validates suites
   under `agents/skills/`.
2. `./d7y validate` — evals + initiatives valid.
3. Root `AGENTS.md` and `CLAUDE.md` symlinks resolve; `agents/AGENTS.md` and
   `agents/runtime-AGENTS.md` exist.
4. `agents/runtime-AGENTS.md` is orientation-scoped: contains no Amp/Claude
   roles, worktree rules, auditable-delegation content, "build D7Y do not
   perform discovery", or eval contract.
5. No broken references: a grep confirms no stale `skills/` path remains where
   `agents/skills/` is now meant (in scripts and docs); `git ls-files` shows
   `skills/` contents moved to `agents/skills/`, not duplicated.
6. The B0 binding-contract note is recorded (discovery path, symlink behavior,
   command-access mechanism, observable load/trigger signal).
7. `git diff --check` and a clean task worktree.

Report B0 findings and B1 changes as distinct facts. Static validation passing
is not a behavioral binding test (that is B2/B3).

# Completion

Append evidence-bearing implementation feedback to
`docs/plans/runtime-binding-claude-code.md`: the B0 binding-contract note; B1
files moved and created; the symlink choices made; path references fixed; checks
and results; deviations; residual risks; and decisions returned (especially the
`CLAUDE.md` symlink-vs-companion choice and the confirmed skill-discovery
mechanism). Commit the implementation on the assigned branch and return with a
clean worktree. Stop and return consequential ambiguity — in particular if B0
cannot confirm symlink viability, or if any path-ref change would alter
behavior rather than merely relocate.
