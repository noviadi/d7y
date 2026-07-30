---
status: draft
plan: docs/plans/eval-execution-harness.md
execution: phase-1.5-negative-variants
executor: claude-code
branch: work/eval-harness-phase1
worktree: /home/noviadi/Developments/discovery/d7y-worktrees/eval-harness-phase1
permissionProfile: implementation-commit
commit: allowed
---

# Phase 1.5 — deliberate negative variants

Starting from the reviewed Phase 1.4 tip, run exactly four real Harbor
variants: missing required artifact, non-zero Oracle exit, timeout, and denied
network. Preserve diagnostics and map each to the canonical failure class.
Do not edit the accepted positive fixture after the first variant; use isolated
variant inputs/tasks and retain exact trial identifiers.
