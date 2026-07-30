---
plan: eval-execution-harness
execution: phase-1-1-fixture-contract-correction-1
status: committed
executor: claude-code
branch: work/eval-harness-phase1
worktree: /home/noviadi/Developments/discovery/d7y-worktrees/eval-harness-phase1
permission_profile: implementation-commit
---

You are correcting the Phase 1.1 fixture-contract implementation in the existing persistent worktree.

Read first:

- `docs/plans/eval-execution-harness.md`
- `docs/prompts/eval-execution-harness.phase-1-1-fixture-contract.md`
- the Phase 1.1 changes and `evals/harbor/phase1-execution.md`
- the installed Harbor 0.20.0 source relevant to `Trial._separate_verifier_env`, `Verifier._resolve_tests`, and environment construction

Review findings to fix:

1. `git diff --check` fails because `evals/harbor/phase1-execution.md` contains trailing whitespace. Remove it.
2. The current fixture documents `/tests/test.sh` but does not prove that Harbor 0.20.0 will make that script available in the separate verifier environment when `skip_tests_upload=True`. Establish an actual, supported staging contract for the declared environment/runtime. Do not claim that a host-side `tests/test.sh` is sufficient unless the Harbor source path proves it. Keep verifier tests hidden from the agent environment and preserve the separate-verifier boundary.

Requirements:

- Stay within Phase 1.1: fixture/configuration and static construction validation only.
- Do not run `harbor trial start`, `harbor exec`, a Claude-agent trial, or any runtime/evidence-producing smoke test.
- Do not modify `docs/plans/eval-execution-harness.md` or the original Phase 1.1 prompt.
- Preserve the persistent branch/worktree and commit the correction as one new commit on `work/eval-harness-phase1`.
- Use the real Harbor 0.20.0 code path to validate the contract. If the current pinned prebuilt verifier image makes the requested staging impossible without a prebuilt image change, record that explicitly and implement the smallest local fixture/image contract needed for the later runtime phase; do not invent a mechanism.
- Update the execution ledger to distinguish static validation from runtime proof and to record any limitation or changed fixture files.

Required checks before committing:

- Harbor 0.20.0 task parsing and any deterministic Dockerfile/build-context or environment-construction validation that does not start a trial.
- `python3 evals/harbor/scripts/posture.py`
- `python3 evals/validate_skill_evals.py`
- `./d7y validate`
- `git diff --check`
- `git status --short --branch` must be clean after commit.

Report the exact staging mechanism, what was statically proven, what remains runtime-only, and the resulting commit.
