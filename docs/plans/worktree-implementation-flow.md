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

## Implementation feedback

Implemented by Claude Code on `work/constitution-worktree-flow` from base `944ae7310c991da3f4a4023421bf34c8bff7125f`. Documentation-only change; no scripts, hooks, aliases, templates, schemas, or `.gitignore` entries added.

### Files changed

- `AGENTS.md`: added a `## Worktree-isolated implementation handoffs` section after Amp's repository role. It states the default, enumerates Amp's ten-step lifecycle, records the `--ff-only` no-squash integration rule and the rebase-instead-of-incidental-merge rule, states that linked worktrees share Git objects/refs/config/hooks/remotes/external resources and that `main` integrations are serialized, and lists the same-worktree exceptions (serialized, accounts for untracked files).
- `CLAUDE.md`: added a `## Worktree-isolated execution` section after `## How Claude Code executes`. It requires using the assigned worktree and branch, pre-edit verification, branch-only commits on explicit authorization, staging explicit paths / cohesive commits / preserved attribution / no squash, feedback committed with the implementation, a clean worktree on return, prohibition of rebase/merge-to-main/worktree-removal/branch-deletion/force/push unless explicitly assigned, awareness of shared Git metadata and external resources, and following the same-worktree path when chosen.
- `docs/plans/worktree-implementation-flow.md`: set `status: done` and added this feedback section.

### Checks run

- `git diff --check` — passes (no whitespace/conflict errors, no output).
- Agreement check (path, branch, commit, review, rebase, fast-forward, no-squash, cleanup semantics): the AGENTS.md lifecycle and CLAUDE.md execution rules were written to match the accepted decisions verbatim in semantics; both reference `work/<slug>`, `../d7y-worktrees/<slug>`, `--ff-only` integration without squash, rebase-then-rerun, clean-worktree-before-review, and separate deliberate cleanup.
- `grep` for instructions authorizing Claude to commit directly to `main`: none found.
- `grep` for review text implying branch review includes uncommitted/untracked files: none found; CLAUDE.md requires a clean worktree and AGENTS.md step 5 requires a clean worktree before review.

### Verification classification

Static documentation validation only. No deterministic tests, isolated agent runs, comparative evals, or human acceptance performed (none applicable to this constitutional documentation change). No new evals, scripts, or skills touched.

### Deviations

None. Scope was held to `AGENTS.md`, `CLAUDE.md`, and this plan's feedback as the handoff instructed.

### Residual risk / uncertainty

- These are unenforced workflow rules by design (anti-goal: automation). Conformance depends on Amp and Claude Code following them; nothing in-tree verifies a handoff used a worktree.
- The plan's status field is Amp-owned metadata; set to `done` here to reflect a complete implementation pending Amp review. Amp may reset or supersede it during reconciliation.

### Decisions returned

None requiring Amp/human reconciliation. No consequential ambiguity encountered; no stop condition triggered (base commit present, plan committed at base, assigned branch/worktree used, clean start).

## Amp review

Reviewed the committed implementation range `944ae7310c991da3f4a4023421bf34c8bff7125f...f4c6d0bd94e88c0bb39129e35de97a505a775330` on 2026-07-27. The task worktree was clean and `git diff --check` passed. Integration is blocked pending these corrections:

1. Make the prohibition on Claude Code committing to `main` unconditional. Even when Amp or the human selects same-worktree execution, an authorized Claude commit requires an explicitly assigned non-main `work/<slug>` branch. Amp's own direct planning commits are unaffected.
2. Mirror integration and cleanup invariants in `CLAUDE.md` because it does not inherit `AGENTS.md`. If a handoff explicitly delegates lifecycle actions, Claude must still preserve commit boundaries, never squash, rebase only as directed, rerun affected verification, return the rebased result for review before integration, use only `git merge --ff-only`, confirm the reviewed tip and clean relevant worktrees, and use non-forced removal plus normal deletion of an integrated branch. An ordinary handoff cannot authorize forced cleanup or deletion of unmerged work.
3. Constitutionalize the required handoff payload in both roles: base commit, exact non-main branch, exact worktree path, governing plan, required verification, and explicit commit permission. Claude stops before editing when a required field is missing or does not match the current checkout.
4. Correct the implementation feedback's agreement claim after making these changes. It currently overstates what `CLAUDE.md` says about the sibling path, `--ff-only`, rebase, and cleanup.
5. State external-resource isolation accurately: linked worktrees do not isolate ports, caches, services, credentials, or other external resources; namespace them separately when the task requires it.
6. Add immediate integration checks to Amp's lifecycle: `main` is the destination, the task tip is the reviewed tip, required verification is complete, and both relevant worktrees are clean.

No change to the accepted sibling path, private branch convention, no-squash history, or manual workflow is requested.
