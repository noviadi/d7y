---
status: draft
plan: docs/plans/eval-execution-harness.md
execution: phase-1.2-positive-oracle
executor: claude-code
branch: work/eval-harness-phase1
worktree: /home/noviadi/Developments/discovery/d7y-worktrees/eval-harness-phase1
permissionProfile: implementation-commit
commit: allowed
---

# Phase 1.2 — positive Harbor Oracle trial

Starting from the reviewed clean Phase 1.1 tip in the same worktree, run only
one positive Harbor 0.20.0 Oracle trial using the accepted fixture. Prove
startup/teardown, input read, declared artifact transfer, Oracle exit state,
trial provenance, and the agent-side mount/host-material boundaries. Retain
the real Harbor trial directory and record results in the execution ledger.
Do not run negative variants or change fixture source after the trial begins.
Use the exact Phase 0 posture and leave the worktree clean with a committed
subphase result.
