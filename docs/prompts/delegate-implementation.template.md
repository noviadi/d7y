---
plan: docs/plans/<plan-slug>.md
execution: <execution-slug>
executor: claude-code
branch: work/<branch-slug>
worktree: ../d7y-worktrees/<branch-slug>
permissionProfile: docs-commit | implementation-commit
commit: allowed
---

# Objective

<One paragraph stating the bounded change to implement, scoped to the governing plan. Name the plan and the user-selected deliverables.>

# Required context

Read before editing:

- the governing plan (`docs/plans/<plan-slug>.md`);
- `AGENTS.md`;
- `CLAUDE.md`;
- the relevant canonical sections this change touches;
- the complete committed diff from the launcher-resolved base.

# Writable paths

- `<explicit allow-list of paths the executor may modify>`

New files are authorized only at the paths listed above. Do not modify this concrete prompt.

# Permission envelope

- Profile: `docs-commit | implementation-commit`
- Extra tool grants: `<list repeatable --allow-tool matchers, or "none">`
- Network: prohibited.
- MCP servers: none (strict-empty).
- External services and credentials: none.
- Commit authority: allowed; make cohesive implementation commits on the assigned branch and stage only writable paths.
- Lifecycle authority: none. Do not rebase, merge, push, remove worktrees, create/rename/delete branches, amend existing commits, or force any Git operation.

# Verification

<List every check the governing plan requires. Invalid launcher cases must use disposable state and leave no artifacts. Do not invoke a nested live Claude run while testing the launcher; use `--dry-run`.>

# Completion

Append evidence-bearing implementation feedback to the governing plan (files changed, checks and results, a dry-run example, valid/invalid cases, deviations, residual risks, decisions returned), commit the implementation on the assigned branch, and return with a clean worktree. Stop and return consequential ambiguity or any required permission expansion.

<!--
Template: docs/prompts/delegate-implementation.template.md
Copy to docs/prompts/<plan-slug>.<execution-slug>.md and complete every field.
See docs/prompts/README.md for the artifact contract.
-->
