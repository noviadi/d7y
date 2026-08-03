---
status: committed
plan: docs/plans/runtime-binding-claude-code.md
execution: b2-dev-install
executor: claude-code
branch: work/runtime-binding-b2
worktree: ../d7y-worktrees/runtime-binding-b2
permissionProfile: implementation-commit
commit: allowed
---

# Objective

Execute Stage B2 of `docs/plans/runtime-binding-claude-code.md`: add
`d7y dev install <directory>` to the `d7y` façade (the existing contributor-only
`dev` group). It materializes a runnable D7Y runtime in a target directory per
the install model, idempotently, without clobbering existing initiative data.

B2 delivers the **install mechanics** only. The behavioral binding — a live
Claude Code session loading skills, triggering, and producing an artifact — is
**Stage B3** and is explicitly out of scope here. Do not run a nested live
Claude session; verify with fixture/dry checks.

# Required context

Read before editing:

- the governing plan (`docs/plans/runtime-binding-claude-code.md`), especially
  _Binding/install model_, _Decisions locked_, _Stage B2_, and the
  _Implementation feedback — B0/B1_ section (the characterized binding contract:
  symlinks are viable; workspace-trust gates project-scope loading; `d7y` must
  be reachable in-session via PATH);
- `AGENTS.md` and `CLAUDE.md`;
- the `d7y` executable at the repo root — understand its dispatch pattern from
  the existing `dev plans` and `dev delegate` subcommands; match it;
- `scripts/check-initiatives.py` (the deterministic capability the runtime
  exposes via `d7y initiatives`) and `scripts/delegate-claude.sh` (an existing
  script the façade dispatches to, as a pattern reference);
- `agents/skills/` (the source skills to link from), `agents/runtime-AGENTS.md`
  (the runtime constitution to copy), and `initiatives/README.md` (the contract
  to place);
- `docs/prompts/README.md` and `docs/prompts/delegate-implementation.template.md`
  (prompt contract);
- the complete committed diff from the launcher-resolved base.

# Writable paths

- `d7y` (the façade — add the `dev install` subcommand)
- `scripts/` (a new deterministic install helper + its tests, if consistent with
  the thin-façade architecture; otherwise inline in `d7y`)
- `docs/plans/runtime-binding-claude-code.md` (implementation feedback only)

New files are authorized only at the paths above. Do not modify this prompt. Do
not edit the skills, the runtime constitution (`agents/runtime-AGENTS.md`), the
dev constitution, canon (`docs/discovery-workbench*`, `docs/skill-evaluations.md`),
the schema, or `evals/validate_skill_evals.py`. Stage B3 (live session) is out of
scope.

# Permission envelope

- Profile: `implementation-commit`
- Extra tool grants: none.
- Network: prohibited. (The install is local symlinks/copies; no fetch.)
- MCP servers: none (strict-empty).
- External services and credentials: none.
- Commit authority: allowed; make cohesive implementation commits on the
  assigned branch and stage only writable paths.
- Lifecycle authority: none. Do not rebase, merge, push, remove worktrees,
  create/rename/delete branches, amend existing commits, or force any Git
  operation.

# Implementation requirements

- Add `d7y dev install <directory>` following the façade's existing dispatch
  pattern (mirror how `dev plans` / `dev delegate` are wired). Keep the façade
  thin; put install logic in a deterministic helper under `scripts/` if that
  matches the architecture.
- Materialize the target per the plan's install model:
  - `.d7y/skills/<name>` → symlink to this repo's `agents/skills/<name>`
    (absolute target, so source edits are live in the runtime);
  - `.d7y/d7y` — the executable, reachable in-session (see PATH decision below);
  - `.d7y/scripts/check-initiatives.py`;
  - `.claude/skills/<name>` → symlink to `../../.d7y/skills/<name>`;
  - `AGENTS.md` — **copied** from `agents/runtime-AGENTS.md` (not symlinked);
  - `CLAUDE.md` → symlink to `AGENTS.md`;
  - `initiatives/README.md` placed (create `initiatives/` if absent).
- **Idempotent:** re-running re-links and refreshes artifacts but **preserves**
  an existing target `initiatives/` tree. Refuse (non-zero exit, clear message)
  to clobber an `initiatives/` that contains data beyond the placed `README.md`.
- **PATH decision (required, from the B0 finding):** `d7y` must be reachable
  in-session. Decide and implement one of: (a) print the exact access method
  the user/agent must use (e.g., invoke `.d7y/d7y` or prepend `.d7y/` to PATH),
  or (b) link `d7y` into an explicitly PATH-provided directory. Record the
  choice and the rationale. Do not leave reachability silent.
- **Workspace-trust guidance (from the B0 finding):** the install cannot force
  Claude Code workspace trust, so emit a clear note that the target workspace
  must be trusted for project-scope skills to load (B3 confirms this behaviorally).
- Copy-vs-symlink for `.d7y/d7y` and `.d7y/scripts/check-initiatives.py`: choose
  consistently with the dev-install live-edit intent, and ensure
  `d7y initiatives list` / `d7y initiatives check` resolve correctly when invoked
  from the target workspace (the façade's path resolution must still find its
  dispatch targets). Record the choice.

# Verification

1. `d7y dev install <tmp-target>` produces the exact layout above; symlinks
   resolve (`.claude/skills/<name>/SKILL.md` → this repo's
   `agents/skills/<name>/SKILL.md`).
2. `AGENTS.md` in the target equals `agents/runtime-AGENTS.md` (copy, not link);
   `CLAUDE.md` → symlink to it.
3. From the target workspace, `d7y initiatives list` and `d7y initiatives check`
   run and return valid JSON / correct exit codes against the placed
   `initiatives/README.md` (empty initiative set is valid).
4. Idempotent: a second `d7y dev install <same-target>` succeeds and changes
   nothing material.
5. Clobber refusal: a target whose `initiatives/` holds data beyond `README.md`
   is rejected with a non-zero exit and a clear message; nothing is destroyed.
6. PATH access method and workspace-trust guidance are emitted on install.
7. `python3 evals/validate_skill_evals.py` and `./d7y validate` still pass (no
   regressions to existing artifacts).
8. Focused tests for the install helper (layout, idempotency, clobber refusal)
   pass using a disposable temp target; no live nested Claude session is run.
9. `git diff --check` and a clean task worktree.

Report mechanics evidence only. A correct install layout is not a behavioral
binding — that is B3.

# Completion

Append evidence-bearing implementation feedback to
`docs/plans/runtime-binding-claude-code.md`: files changed; the façade dispatch
approach; the **PATH decision** and its rationale; the copy-vs-symlink choices
for `d7y` and the checker; the workspace-trust guidance emitted; idempotency and
clobber-refusal evidence; a dry-run example showing the produced layout; checks
and results; deviations; residual risks; and decisions returned. Commit the
implementation on the assigned branch and return with a clean worktree. Stop and
return consequential ambiguity — in particular if the façade's path resolution
prevents `d7y initiatives` from working in the target workspace, or if no
sensible PATH strategy exists without a decision you are not authorized to make.
