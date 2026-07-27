---
plan: docs/plans/root-cli.md
execution: initial
executor: claude-code
branch: work/root-cli
worktree: ../d7y-worktrees/root-cli
permissionProfile: implementation-commit
commit: allowed
---

# Objective

Implement the bounded thin root CLI defined by `docs/plans/root-cli.md`: add executable `./d7y` as a dependency-free Bash command façade over the existing validators and Claude delegation launcher, document it briefly in `README.md`, verify the exact command and failure contract, append implementation feedback to the governing plan, and commit the result on the assigned branch.

# Required context

Read before editing:

- the governing plan (`docs/plans/root-cli.md`);
- `AGENTS.md`;
- `CLAUDE.md`;
- `docs/discovery-workbench.md`, especially "Skills, Harness, and Deterministic Foundation" and "Host-Neutral Core and Host Bindings";
- `README.md`;
- the command interfaces of `evals/validate_skill_evals.py`, `skills/starting-initiatives/scripts/check_initiatives.py`, and `scripts/delegate-claude.sh`;
- the complete committed diff from the launcher-resolved base.

# Writable paths

- `d7y` (new executable file)
- `README.md`
- `docs/plans/root-cli.md` (implementation feedback only)

New files are authorized only at the paths listed above. Do not modify this concrete prompt or any underlying validator or launcher.

# Permission envelope

- Profile: `implementation-commit`
- Extra tool grants: none.
- Network: prohibited.
- MCP servers: none (strict-empty).
- External services and credentials: none beyond the launcher's existing environment import needed to invoke Claude Code; do not access or report their values.
- Commit authority: allowed; make cohesive implementation commits on the assigned branch and stage only writable paths.
- Lifecycle authority: none. Do not rebase, merge, push, remove worktrees, create/rename/delete branches, amend existing commits, or force any Git operation.

# Verification

Run every command required by the governing plan:

```sh
bash -n d7y
./d7y --help
./d7y validate
./d7y validate evals
./d7y validate initiatives --json
./d7y dev delegate --help
(cd docs && ../d7y validate evals)
```

Run the three invalid dispatch cases from the plan and explicitly verify that each exits `2`, writes its diagnostic to stderr, and does not invoke an underlying tool. Use shell status capture without suppressing or rewriting the result. Run `git diff --check`. Run `shellcheck d7y` only if `shellcheck` is installed; otherwise record it as unavailable.

Do not invoke a live nested Claude run while checking delegation. `./d7y dev delegate --help` is the required non-executing check.

# Completion

Append evidence-bearing implementation feedback to the governing plan (files changed, exact checks and results, deviations, residual risks, and decisions returned), commit the implementation on the assigned branch, and return with a clean worktree. Stop and return consequential ambiguity or any required permission expansion.
