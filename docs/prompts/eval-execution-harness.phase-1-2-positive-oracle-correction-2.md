---
status: committed
plan: eval-execution-harness
execution: phase-1-2-positive-oracle-correction-2
executor: claude-code
branch: work/eval-harness-phase1
worktree: /home/noviadi/Developments/discovery/d7y-worktrees/eval-harness-phase1
permission_profile: implementation-commit
commit: allowed
lifecycle_authority: none
---

# Phase 1.2 correction 2 — make the Oracle fixture shell-portable

Correct the Phase 1.2 Oracle fixture in the existing persistent worktree after
the first successful verifier-image build and the subsequent positive rerun
failed during Oracle execution.

## Failure context

The fresh positive trial used source commit `2941e4e36a1809e964705a16560f6ca513fdf9d9`
and Harbor `0.20.0`. Verifier image construction completed, but the Oracle
agent recorded exit code `127`; Harbor then could not collect the declared
`/solution/output.txt`, and the verifier reward was `0`. Preserve both prior
evidence roots and do not attribute success to either:

- `/home/noviadi/Developments/discovery/d7y-eval-evidence/eval-execution-harness/phase-1-2-positive-oracle`
- `/home/noviadi/Developments/discovery/d7y-eval-evidence/eval-execution-harness/phase-1-2-positive-oracle-rerun-1`

Installed Harbor source inspection shows Oracle executes Linux `solve.sh`
through its supported direct-script path, wrapped in `bash -c`, and stages the
solution directory at `/solution`. A disposable upload-and-exec probe against
`d7y-eval-phase0-agent:2.1.218` succeeds with the current script, so do not
claim that the exact Harbor root cause is proven. The correction must reduce
the fixture's interpreter and command dependencies while preserving the
behavioral contract.

## Required correction

- Read the governing plan, the accepted Phase 1.1 fixture contract, the Phase
  1.2 prompts and prior correction prompts, the Harbor Oracle implementation,
  and the Phase 0 image posture.
- Update only `evals/harbor/tasks/phase1-smoke/solution/solve.sh` so it uses
  POSIX `/bin/sh` and shell built-ins for the copy behavior. It must still read
  `/solution/input.txt`, write exactly `/solution/output.txt`, preserve the
  expected content byte-for-byte, fail clearly if the input is absent, and
  remain executable. Do not change the task schema, artifacts, verifier,
  Dockerfile, instruction, governing plan, or any evidence directory.
- Run a deterministic disposable-container check using the exact Phase 0
  agent image and staged `/solution` directory. Prove the script exits `0`,
  creates the output, and preserves the expected content. This correction
  handoff must not run a Harbor trial.
- Commit exactly one correction commit on `work/eval-harness-phase1` and leave
  the worktree clean.

## Evidence and safety

Do not delete, overwrite, or mutate either prior Phase 1.2 evidence root. Do
not run `harbor trial start`, `harbor exec`, negative variants, network probes
beyond the deterministic disposable-container check, or a Claude Harbor
agent. The next positive trial must use a new evidence directory and a new
execution handoff.

## Required checks

- exact-file inspection and disposable-container execution against
  `d7y-eval-phase0-agent:2.1.218`;
- Harbor 0.20.0 task parsing;
- `python3 evals/harbor/scripts/posture.py`;
- `python3 evals/validate_skill_evals.py`;
- `./d7y validate`;
- `git diff --check` and clean `git status --short --branch`.

Report the failure classification, exact solution-script correction,
deterministic execution result, and resulting commit. Do not claim Phase 1.2
acceptance.
