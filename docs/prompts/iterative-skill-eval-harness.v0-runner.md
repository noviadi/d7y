---
status: draft
plan: docs/plans/iterative-skill-eval-harness.md
execution: stage-1a-workspace-grader
executor: claude-code
branch: work/iterative-skill-eval-stage-1a
worktree: ../d7y-worktrees/iterative-skill-eval-stage-1a
permissionProfile: implementation-commit
commit: allowed
---

# Objective

Implement Stage 1a of `docs/plans/iterative-skill-eval-harness.md`: a thin,
dependency-free **deterministic workspace grader** for the `starting-initiatives`
skill. The grader takes a workspace path, runs the existing deterministic
checker against it by import, captures the produced artifacts without mutation,
and emits a layered outcome result with provenance. It is a capture-grader, not
a benchmark runner.

Scope is the grader and its self-tests only. No agent invocation, no
baseline/treatment pairing, no benchmark, no maturity, no canon edits, no new
eval cases.

# Required context

Read before editing:

- the governing plan (`docs/plans/iterative-skill-eval-harness.md`), especially
  _Guiding eval principles_, _Stage 1a_, _Stage 1a grader sketch_, and _Output
  shape_;
- `AGENTS.md` and `CLAUDE.md`;
- `docs/skill-evaluations.md` (dimension table, layered results, canonical
  failure classes) — preserve these semantics; omit dimensions that lack
  evidence rather than fabricating them;
- `scripts/check-initiatives.py` — the grader to reuse by import
  (`inventory(root: Path) -> dict`; `valid`, `count`, per-record `errors`;
  exit 0 valid / 1 invalid);
- `initiatives/README.md` — the workspace shape the grader will encounter
  (`initiatives/<slug>/initiative.md` plus the organization contract);
- `evals/skill-evals.schema.json` and `evals/validate_skill_evals.py`;
- `skills/starting-initiatives/evals/evals.json` and its `evals/files/`
  fixtures — the source of fixture workspaces for self-tests;
- the complete committed diff from the launcher-resolved base.

# Writable paths

- `evals/run/workspace_grader.py`
- `evals/run/test_workspace_grader.py`
- `evals/run/README.md`

New files are authorized only at the paths listed above. Do not modify this
concrete prompt. Do not edit `docs/skill-evaluations.md`, the skills, the
existing graders (`scripts/check-initiatives.py`, `evals/validate_skill_evals.py`),
the schema, or any canon in this execution.

# Permission envelope

- Profile: `implementation-commit`
- Extra tool grants: none.
- Network: prohibited.
- MCP servers: none (strict-empty).
- External services and credentials: none.
- Commit authority: allowed; make cohesive implementation commits on the
  assigned branch and stage only writable paths.
- Lifecycle authority: none. Do not rebase, merge, push, remove worktrees,
  create/rename/delete branches, amend existing commits, or force any Git
  operation.

# Implementation requirements

- Dependency-free Python 3 (stdlib only), consistent with `check-initiatives.py`.
- Reuse `check-initiatives.inventory()` by import. Do not reimplement initiative
  parsing, validation, or relationship checking.
- `grade(workspace)` runs the checker against the workspace and records validity,
  count, per-record validity and errors, and the artifact inventory
  (`initiatives/<slug>/initiative.md`).
- `capture(workspace, transcript_path | None)` copies produced artifacts (and an
  optional pointed-at transcript) into the runs layout. It must never mutate the
  input workspace.
- `emit_layered(...)` writes `checks.json` and `summary.md` in the shape the plan
  specifies. Emit the `outcome` dimension from the inventory; omit or mark `N/A`
  every dimension with no evidence (process, invocation, quality, efficiency,
  environment, pair). Do not fabricate layers. Use the canonical failure classes.
- Provenance records the d7y source commit, the skill source commit, the checker
  identity, and the date.
- The grader grades one workspace. Do not add agent invocation, baseline/
  treatment pairing, pass rates, repeated comparison, or any containerization.
  If the implementation starts to need those, stop and return the ambiguity —
  that is Stage 1b, gated, and out of scope here.

# Verification

1. `python3 evals/validate_skill_evals.py` — suites still valid.
2. `./d7y validate` — evals + initiatives valid.
3. `python3 evals/run/test_workspace_grader.py` — focused self-tests with
   fixture workspaces: a valid workspace grades `pass`; invalid workspaces
   (missing required heading, bad slug, malformed date, leftover placeholder,
   duplicate identity) grade `fail` with the correct errors; capture does not
   mutate the input; provenance is recorded. No live agent anywhere.
4. A dry-run grading a fixture workspace materialized from an existing
   `starting-initiatives` case, with the layered result retained.
5. `git diff --check` and a clean task worktree.

Report static validation, deterministic tests, and the dry-run as distinct
facts. A clean dry-run is not a behavioral run.

# Completion

Append evidence-bearing implementation feedback to
`docs/plans/iterative-skill-eval-harness.md` (files changed, module shape,
checks and results, a dry-run example with the emitted `checks.json`,
deviations, residual risks, and decisions returned). Commit the implementation
on the assigned branch and return with a clean worktree. Stop and return
consequential ambiguity or any required permission expansion — in particular if
reuse-by-import of `check-initiatives.inventory()` is blocked by anything not
named here.
