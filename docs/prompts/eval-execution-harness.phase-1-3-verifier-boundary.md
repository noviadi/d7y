---
status: draft
plan: docs/plans/eval-execution-harness.md
execution: phase-1-3-verifier-boundary
executor: claude-code
branch: work/eval-harness-phase1
worktree: /home/noviadi/Developments/discovery/d7y-worktrees/eval-harness-phase1
permissionProfile: implementation-commit
commit: allowed
---

# Phase 1.3 — separate verifier and canary

Starting from the reviewed Phase 1.2 tip, run the positive trial's separate
verifier boundary checks only. Prove `/tests/test.sh` staging, verifier user
and no-network posture, agent inability to read verifier material, declared
outputs as the only transfer, reward-file fail-closed behavior, and the fake
credential canary scan across finalized textual evidence. Do not add negative
variants or broaden the provider scope. Record evidence in the execution ledger
and commit a clean subphase result.
