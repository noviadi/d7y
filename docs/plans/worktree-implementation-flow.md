---
title: Worktree-Isolated Implementation Flow
type: docs
status: todo
createdAt: 2026-07-27
updatedAt: 2026-07-27
---

# Worktree-Isolated Implementation Flow

## Outcome

Make isolated Git worktrees the executable default for non-trivial Amp-to-Claude implementation handoffs while preserving a lighter same-worktree path for changes where isolation would be ceremony rather than protection.

This is a constitutional workflow rule, not automation. Update only `AGENTS.md` and `CLAUDE.md`. Do not add scripts, hooks, aliases, templates, schemas, or `.gitignore` entries.

## Accepted Decisions

- Amp continues to plan and review from the main checkout.
- An execution-ready plan and every required task input must be committed to `main` before creating the implementation worktree.
- Each task uses a private branch named `work/<slug>` and a sibling worktree at `../d7y-worktrees/<slug>`.
- The handoff records the base commit, exact branch, exact worktree path, governing plan, verification, and explicit permission for Claude Code to commit on the task branch.
- Claude Code implements, verifies, writes feedback into the governing plan, creates cohesive commits on the task branch, and returns a clean worktree.
- Amp reviews committed branch history, the complete `main...branch` diff, verification evidence, and plan feedback. Corrections and review feedback remain on the task branch.
- If `main` advances, rebase the private task branch onto current `main`, rerun affected verification, and review the rebased result again.
- Integrate only with `git merge --ff-only <branch>`. Do not squash. Preserve every accepted task-branch commit and its authorship; rebase may rewrite commit IDs but not collapse commit boundaries.
- If fast-forward integration fails, do not create an incidental merge commit. Rebase and repeat final verification and review.
- Worktree and branch cleanup is a separate, deliberate action after integration. Never remove a dirty worktree, use forced removal, or delete an unmerged branch by default.

## Constitutional Changes

### `AGENTS.md`

Add a concise section near Amp's repository role or development discipline that makes Amp responsible for the lifecycle:

1. Decide whether isolation is proportionate.
2. Commit the ready plan and required inputs to `main`.
3. Create or direct creation of `work/<slug>` at `../d7y-worktrees/<slug>` from the recorded base.
4. Invoke Claude in the exact worktree and authorize commits only on that branch.
5. Require a clean worktree before review.
6. Review branch commits, full diff, feedback, checks, deviations, and residual risk.
7. Keep correction loops on the task branch.
8. Rebase when necessary, then rerun affected checks and review the final result.
9. Integrate with `--ff-only` and without squashing.
10. Treat cleanup as separate and safe: confirm integration and cleanliness before non-forced worktree removal and normal merged-branch deletion.

State explicitly that linked worktrees isolate files and indexes but still share Git objects, refs, repository configuration, hooks, remotes, and external resources. Integrations into `main` are serialized.

Allow same-worktree execution when the work is trivial and reversible, intentionally depends on uncommitted state, directly corrects an uncommitted change, uses linked-worktree-incompatible tooling, requires a serialized live handoff edit, or the human chooses the lighter path. Same-worktree execution remains serialized and must account for untracked files.

### `CLAUDE.md`

Add execution rules that require Claude Code to:

- use the exact assigned worktree and task branch rather than the main checkout;
- verify current path, branch, HEAD/base, governing plan, and task scope before editing;
- commit only when the handoff explicitly authorizes it and only on the assigned task branch;
- stage explicit intended paths, make cohesive commits, preserve attribution, and never squash merely to simplify review;
- include implementation feedback in the governing plan and commit it with the implementation;
- return with no uncommitted or untracked files;
- not rebase, merge into `main`, remove the worktree, delete branches, force operations, or push unless the handoff explicitly assigns that action;
- remember that linked worktrees share Git metadata and external resources, so avoid repository-global configuration or shared-resource changes outside scope;
- follow the explicitly selected same-worktree path when Amp or the human chooses it instead of creating an unsolicited worktree.

## Verification

- `git diff --check` passes.
- `AGENTS.md` and `CLAUDE.md` agree on path, branch, commit, review, rebase, fast-forward, no-squash, and cleanup semantics.
- Searches find no instruction that authorizes Claude to commit directly to `main` or implies branch review includes uncommitted files.
- Existing planning/execution/runtime responsibilities and human authority remain unchanged.
- Claude records files changed, checks run, deviations, residual risk, and decisions returned in this plan.

## Stop Conditions

- Stop if the existing branch or target worktree path already exists with unrelated state.
- Stop if the plan or a required task input is not committed at the recorded base.
- Stop if a rebase conflict would change intent, architecture, policy, scope, or evidence standards; return it to Amp and the human.
- Stop integration if the task worktree is dirty, required verification is incomplete, or `--ff-only` cannot advance `main` to the reviewed tip.
- Do not delete or force-clean worktree data as part of this implementation.

## Anti-goals

- Automated worktree lifecycle management.
- Nested worktrees under the main checkout.
- Squash merges or incidental merge commits.
- A requirement to use a worktree for every typo or tiny correction.
- Treating linked worktrees as process, Git-metadata, network, port, cache, or external-service isolation.
