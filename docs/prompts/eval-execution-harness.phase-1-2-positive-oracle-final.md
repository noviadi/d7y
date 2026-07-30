---
status: committed
plan: eval-execution-harness
execution: phase-1-2-positive-oracle-final
executor: claude-code
branch: work/eval-harness-phase1
worktree: /home/noviadi/Developments/discovery/d7y-worktrees/eval-harness-phase1
permission_profile: implementation-commit
commit: allowed
lifecycle_authority: none
---

# Phase 1.2 final corrected positive Oracle trial

Run exactly one fresh Harbor Oracle smoke trial against the reviewed Phase 1.2
runtime fixes. This is the acceptance execution for Phase 1.2. Work only in the
existing persistent task worktree and start from its clean launcher-recorded tip.

## Governing context and immutable inputs

Read `AGENTS.md`, `CLAUDE.md`, `DEVELOPMENT.md`, the Phase 0 and Phase 1
sections of `docs/plans/eval-execution-harness.md`, `docs/prompts/README.md`,
`evals/harbor/README.md`, `evals/harbor/phase1-execution.md`, and the installed
Harbor 0.20.0 Oracle and artifact-handling source as needed.

The reviewed task branch contains the durable fixes:

- the canonical agent image creates agent-owned `/workspace`, matching the
  task's configured `workdir`;
- the separate verifier checks the declared artifact at `/solution/output.txt`,
  matching Harbor's artifact rematerialization behavior.

The intentional Sonnet-to-`glm-4.7` z.ai proxy route is expected and is not a
failure. This Oracle trial does not require a model credential. Do not modify
the task, image recipe, solution, verifier, governing plan, prompts, or prior
evidence during this execution.

Preserve all prior evidence roots, including:

- `/home/noviadi/Developments/discovery/d7y-eval-evidence/eval-execution-harness/phase-1-2-positive-oracle`
- `/home/noviadi/Developments/discovery/d7y-eval-evidence/eval-execution-harness/phase-1-2-positive-oracle-rerun-1`
- `/home/noviadi/Developments/discovery/d7y-eval-evidence/eval-execution-harness/phase-1-2-positive-oracle-rerun-2`
- `/home/noviadi/Developments/discovery/d7y-eval-evidence/eval-execution-harness/phase-1-2-oracle-path-diagnostic-1`
- `/home/noviadi/Developments/discovery/d7y-eval-evidence/eval-execution-harness/phase-1-2-oracle-path-diagnostic-2`
- `/home/noviadi/Developments/discovery/d7y-eval-evidence/eval-execution-harness/phase-1-2-oracle-path-diagnostic-3`
- `/home/noviadi/Developments/discovery/d7y-eval-evidence/eval-execution-harness/phase-1-2-workspace-image-test-1`

## Exact execution contract

Use this new evidence directory:

`/home/noviadi/Developments/discovery/d7y-eval-evidence/eval-execution-harness/phase-1-2-positive-oracle-final`

Before execution, verify that the exact path is absent and has no symlink in
any existing component. Create it user-owned with mode `0700`. Record the
pre-run source commit and exact command before the first behavioral trial.

Use exactly the accepted fixture at `evals/harbor/tasks/phase1-smoke/`, Harbor
`0.20.0` via `uvx --from harbor==0.20.0`, agent image
`d7y-eval-phase0-agent:2.1.218`, verifier base image
`d7y-eval-phase0-verifier:phase0`, and the recorded Phase 0 posture. Rebuild the
canonical agent image from `evals/harbor/images/agent/Dockerfile` before the
trial if the current tag does not contain `/workspace`; record the resulting
image ID/digest in the evidence. Do not change the image tag or task inputs.

Run exactly this supported command once:

`uvx --from harbor==0.20.0 harbor trial start -p evals/harbor/tasks/phase1-smoke -a oracle --trials-dir /home/noviadi/Developments/discovery/d7y-eval-evidence/eval-execution-harness/phase-1-2-positive-oracle-final/trials`

Do not run negative variants, a Claude agent trial, `harbor job start`,
`harbor exec`, a Python simulation, unrelated network probes, credential
canaries, or later subphases. Do not retry in place. After the pre-run commit,
do not modify executable inputs, rebase, merge, push, amend, force, delete
evidence, or perform lifecycle operations.

## Required observations and completion

Capture and preserve the raw Harbor output and complete trial directory. Record
the exact trial identifier, result ID, pre-run commit, Harbor/image identity,
agent and verifier users, workdirs, resource limits, timeouts, network policy,
container startup and teardown, `/workspace` existence/ownership, `/solution`
staging, Oracle exit code, output artifact collection and hash, `/tests/test.sh`
staging, verifier execution and reward, absence of host checkout/home/Claude
settings/Docker socket mounts, unsupported storage enforcement, deviations,
residual risk, cleanup state, and a SHA-256 evidence inventory. Verify the
successful path includes Oracle exit `0`, output artifact transfer, verifier
reward `1.0`, and no agent `exit-code.txt` failure artifact.

Append a new Phase 1.2 final-corrected-trial section to
`evals/harbor/phase1-execution.md` after the trial. Preserve all historical
sections unchanged. Commit only that ledger/bookkeeping result on
`work/eval-harness-phase1`; leave the worktree clean. Do not claim completion
if any required runtime result is missing.

Run and report these validations with exact commands:

- supported Harbor task parser or equivalent installed Harbor validation;
- `python3 evals/harbor/scripts/posture.py`;
- `python3 evals/validate_skill_evals.py`;
- `./d7y validate`;
- focused evidence checks;
- `git diff --check`;
- `git status --short --branch`.

Return an evidence-backed implementation report for independent review,
including the final commit, evidence path, trial/result IDs, reward, image
identity, all verification results, deviations, and residual risk. Do not
integrate the branch into `main`.
