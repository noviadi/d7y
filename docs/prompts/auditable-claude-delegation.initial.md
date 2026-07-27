---
plan: docs/plans/auditable-claude-delegation.md
execution: initial
executor: claude-code
branch: work/auditable-claude-delegation
worktree: ../d7y-worktrees/auditable-claude-delegation
permissionProfile: implementation-commit
commit: allowed
---

# Objective

Implement the execution-ready plan in `docs/plans/auditable-claude-delegation.md`. Establish preserved delegation prompts and the deterministic Claude Code launcher at the user-selected location `scripts/delegate-claude.sh`.

# Required context

Read before editing:

- the governing plan;
- `AGENTS.md`;
- `CLAUDE.md`;
- the relevant deterministic-foundation and harness sections of `docs/discovery-workbench.md`;
- the complete committed diff from the launcher-resolved base.

# Writable paths

- `AGENTS.md`
- `CLAUDE.md`
- `docs/prompts/README.md`
- `docs/prompts/delegate-implementation.template.md`
- `docs/plans/auditable-claude-delegation.md` for implementation feedback only
- `scripts/delegate-claude.sh`

Do not modify this concrete prompt. New files are authorized only at the three new paths listed above.

# Permission envelope

- Profile: `implementation-commit`
- Extra tool grants required for this execution must be visible in the launcher invocation and this prompt or returned to Amp before use.
- Network: prohibited.
- MCP servers: none.
- External services and credentials: none.
- Commit authority: cohesive implementation commits on the assigned branch; stage only writable paths.
- Lifecycle authority: none. Do not rebase, merge, push, remove worktrees, create/rename/delete branches, amend existing commits, or force any Git operation.

# Verification

Run every check in the governing plan. Invalid cases must use disposable state and leave no artifacts. Do not invoke a nested live Claude run while testing the launcher; use `--dry-run`.

# Completion

Append evidence-bearing implementation feedback to the governing plan, commit the implementation on the assigned branch, and return with a clean worktree. Stop and return consequential ambiguity or any required permission expansion.
