---
status: committed
plan: docs/plans/eval-execution-harness.md
execution: phase-1-harbor-smoke-fix
executor: claude-code
branch: work/eval-harness-smoke-fix
worktree: /home/noviadi/Developments/discovery/d7y-worktrees/eval-harness-smoke-fix
permissionProfile: implementation-commit
commit: allowed
---

# Objective

Correct and complete Phase 1 of `docs/plans/eval-execution-harness.md` in a
fresh worktree. The previous draft is rejected: it used `harbor job start`, ran
only two variants, used non-Harbor `/harmon/*` paths, and claimed completion
without behavioral evidence. Implement one real Harbor 0.20.0 Oracle trial,
the four required negative trials, retained evidence, and the provider
capability record. Do not implement Phase 2 or a generic provider interface.

# Non-negotiable Harbor contract

Use Harbor's supported `trial start` workflow with `-p <task-dir>` and
`-a oracle`; do not use the experimental `harbor exec` or a nonexistent
`harbor job start` interface. First run `harbor trial start --help` and inspect
only the relevant installed Harbor 0.20.0 source if needed. The task must use
the standard layout and paths: `instruction.md`, `task.toml`, optional
`environment/`, `solution/solve.sh`, `tests/test.sh`, agent `/solution`,
verifier `/tests`, and runtime `/logs/{agent,verifier,artifacts}`. Never use
`/harmon` or invent CLI flags.

The task must parse with Harbor before any trial. Use the exact recorded Phase 0
inputs: `evals/harbor/profiles/claude-primary.json`,
`evals/harbor/config/execution-posture.json`,
`d7y-eval-phase0-agent:2.1.218`, and `d7y-eval-phase0-verifier:phase0` with
their recorded digests. Configure the environment baseline, agent allowlist,
separate no-network verifier, users, CPU/memory, and timeouts from the Phase 0
envelope using the actual Harbor 0.20.0 schema. Do not pass credentials or
real API calls.

The Oracle solution must read a synthetic declared input, write declared
artifacts below `/logs/artifacts`, record user and workdir, and exercise the
configured network policy. The verifier must run in the separate verifier
environment, receive only declared outputs, and write reward diagnostics under
`/logs/verifier`. Keep private checker material in the task's verifier test
payload, never in the agent environment or image. Prove no source checkout,
host home, host Claude settings, or Docker socket is available.

# Required variants and evidence

Run exactly five trials: positive, missing required artifact, nonzero Oracle
exit, timeout, and denied network. Do not report a Python simulation or a
wrapper's guessed status as Harbor evidence; retain the real Harbor trial
directories/logs and exact trial identifiers. Map diagnostics to the canonical
failure classes. Record resource and timeout observations and mark local
Docker storage-quota enforcement unsupported without probing quota.

Inject one synthetic fake sensitive-looking value only where the approved
Phase 1 contract requires it. Scan task inputs, logs, trajectory, verifier
output, and declared artifacts after finalization. If raw bytes occur, stop,
quarantine the evidence, and record `evidence_error`; never claim success.

Before the first trial, commit all executable task/verifier inputs and require a
clean worktree. Record that commit in every trial. Do not create a second
untracked helper or edit source after the first trial. If the first real trial
reveals a source defect, stop and report it rather than silently rerunning with
edited source.

# Scope, posture, and completion

Only modify `evals/harbor/`, `DEVELOPMENT.md`, and the Phase 1 feedback section
of `docs/plans/eval-execution-harness.md`, plus the required evidence directory
`/home/noviadi/Developments/discovery/d7y-eval-evidence/eval-execution-harness/phase-1-harbor-smoke`.
The evidence path must be absent before execution, user-owned mode `0700`,
finalized with inventory SHA-256 hashes, and absent from Git. Use disposable
Docker resource names prefixed `d7y-eval-phase1-` and clean them. Do not edit
prompts, skills, eval definitions, canon, other plans, or `main`; do not rebase,
merge, push, amend, force, or perform lifecycle operations.

Run Harbor parsing and the positive plus all four negative trials, then focused
tests for any normalizer, `python3 evals/validate_skill_evals.py`, `./d7y
validate`, `git diff --check`, and `git status --short`. Append
`### Phase 1 implementation feedback` with exact commands, trial IDs, results,
failure mappings, evidence inventory hash, cleanup, deviations, and provider
limitations. Commit only the reviewed implementation and feedback on this
branch, leaving it clean. Do not claim acceptance or change plan status.
