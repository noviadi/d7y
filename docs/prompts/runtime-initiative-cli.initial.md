---
title: Runtime Initiative CLI implementation handoff
type: prompt
status: committed
createdAt: 2026-07-27
updatedAt: 2026-07-27
---

# Implementation handoff

Implement `docs/plans/runtime-initiative-cli.md` in the assigned isolated worktree.

## Execution identity and lifecycle

- Governing plan: `docs/plans/runtime-initiative-cli.md`.
- Execution slug: `initial`.
- Executor: Claude Code.
- Assigned branch: `work/runtime-initiative-cli`.
- Assigned worktree: `/home/noviadi/Developments/discovery/d7y-worktrees/runtime-initiative-cli`.
- Base commit: the `main` tip recorded by the launcher envelope; verify it matches the current task `HEAD` before editing.
- Commit authority: explicitly granted on the assigned `work/runtime-initiative-cli` branch only.
- Lifecycle authority: none beyond implementation commits. Do not create or rename branches, rebase, merge, push, remove worktrees, delete branches, force Git operations, or modify the concrete prompt.

## Permission and workspace posture

The launcher envelope is authoritative for the resolved repository, prompt commit, branch, worktree, Claude version, tools, permissions, network/MCP/persistence posture, and imported environment key names. Report any mismatch instead of inferring a replacement. Work only in the assigned worktree and preserve unrelated changes if encountered; return the worktree clean with no untracked files.

## Required context

Before editing, read:

- `AGENTS.md` and `CLAUDE.md`;
- `docs/plans/runtime-initiative-cli.md` in full;
- `docs/discovery-workbench.md`;
- `docs/skill-evaluations.md`;
- `initiatives/README.md`;
- `skills/writing-great-skills/SKILL.md`;
- `skills/starting-initiatives/SKILL.md` and its `evals/evals.json`;
- `d7y`, `DEVELOPMENT.md`, `README.md`, and `docs/plans/root-cli.md`;
- the current deterministic initiative checker and focused validation/eval tooling.

## Implementation requirements

Implement the plan’s complete command and compatibility contract, keeping one shared deterministic implementation for inventory and validation. Promote the checker to the smallest compatible shared location, add `d7y initiatives list/check` with explicit-root and caller-upward workspace resolution, stable human/JSON output, filtering, and exit statuses, and preserve existing `d7y validate`, `d7y validate initiatives`, `d7y validate evals`, `d7y dev plans`, and `d7y dev delegate` behavior. Update the starting skill and eval definition to use the runtime capability and preserve provisional maturity. Update all documentation named by the plan, including the short supersession note in `docs/plans/root-cli.md`. Do not add packaging, hidden state, a daemon, registry/plugin framework, workflow judgment, or initiative mutation commands.

Use `apply_patch` or equivalent repository-safe edits. Keep the CLI thin and explicit; keep semantic matching and human checkpoints in the skill; keep parsing/validation/result construction shared and independent from presentation. Do not create a real discovery initiative: use temporary synthetic workspaces outside the source checkout and clean them afterward.

## Required verification

Run and report the exact outcomes of:

```sh
bash -n d7y
python3 evals/validate_skill_evals.py
./d7y validate
git diff --check
```

Run `shellcheck d7y` if installed, otherwise report it unavailable. Exercise every focused command case in the plan, including valid empty/multi-record/filter/check output, malformed artifacts, missing reciprocal relationships, invalid options/root resolution, nested upward discovery, unrelated-cwd explicit-root operation, compatibility of `d7y validate initiatives --json`, and concise root/leaf help. Confirm synthetic workspaces are removed. Distinguish static validation from behavioral exercise; do not claim a transferred-host eval unless the harness actually supports and runs it.

## Completion contract

Before finishing, append an `## Implementation Feedback` section to `docs/plans/runtime-initiative-cli.md` covering files moved/changed, exact checks and useful result summaries/exit statuses, synthetic cases, compatibility, deviations, runtime/platform assumptions, static versus behavioral evidence, and residual installation/host-binding risk. Commit the implementation and feedback in cohesive commit(s) on `work/runtime-initiative-cli` without squashing unrelated boundaries. Then verify and report the resulting tip and a clean worktree. Do not modify this prompt artifact.
