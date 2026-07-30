---
status: committed
plan: eval-execution-harness
execution: phase-1-2-positive-oracle-rerun-1
executor: claude-code
branch: work/eval-harness-phase1
worktree: /home/noviadi/Developments/discovery/d7y-worktrees/eval-harness-phase1
permission_profile: implementation-commit
commit: allowed
lifecycle_authority: none
---

# Phase 1.2 positive Oracle rerun 1

Run the single positive Harbor Oracle trial again after the reviewed
verifier-Dockerfile correction. This is a new iteration of Phase 1.2, not a
continuation of the failed iteration. Start from the launcher-recorded clean
tip in the same persistent worktree.

## Fixed correction and predecessor evidence

The prior iteration failed during verifier image construction at
`RUN chmod +x /tests/test.sh` with `Operation not permitted`. The reviewed
correction now uses:

`COPY --chown=verifier:verifier --chmod=755 test.sh /tests/test.sh`

based on `d7y-eval-phase0-verifier:phase0`. An independent Docker build proved
the resulting file is executable and owned by `verifier:verifier`, with the
default runtime user still `verifier`. Do not change this correction or any
other executable fixture input before the trial.

Preserve the prior failed-iteration evidence at:

`/home/noviadi/Developments/discovery/d7y-eval-evidence/eval-execution-harness/phase-1-2-positive-oracle`

Do not delete, overwrite, or attribute success to it.

## Required context and exact inputs

Read `AGENTS.md`, `CLAUDE.md`, `DEVELOPMENT.md`, the governing plan Phase 0
and Phase 1 sections, `docs/prompts/README.md`, the Phase 1.1 ledger, the
Phase 1.2 prompt, the correction prompt, `evals/harbor/README.md`, and the
installed Harbor 0.20.0 Oracle trial implementation.

Use exactly the accepted fixture at `evals/harbor/tasks/phase1-smoke/`, Harbor
`0.20.0` via `uvx --from harbor==0.20.0`, agent image
`d7y-eval-phase0-agent:2.1.218`, verifier base image
`d7y-eval-phase0-verifier:phase0`, and the recorded Phase 0 posture. The
intentional z.ai proxy and Sonnet-to-`glm-4.7` routing are expected and must
not be changed. This Oracle trial requires no model credential.

## Evidence and execution contract

The exact new evidence directory is:

`/home/noviadi/Developments/discovery/d7y-eval-evidence/eval-execution-harness/phase-1-2-positive-oracle-rerun-1`

It must be absent before execution, have no symlink in any existing component,
and be created user-owned with mode `0700`. Keep raw Harbor trial output and
the real trial directory there. Record the pre-run source commit and exact
command before the first behavioral trial. Use Harbor’s supported command:

`uvx --from harbor==0.20.0 harbor trial start -p evals/harbor/tasks/phase1-smoke -a oracle --trials-dir <new-evidence-dir>/trials`

Do not use `harbor job start`, `harbor exec`, a Python simulation, or a Claude
agent. Run exactly one positive trial. Do not run negative variants, network
probes beyond the configured trial, credential canaries, or later subphases.

After the pre-run commit, do not modify the task, Dockerfile, solution,
verifier, or other executable inputs. Do not rebase, merge, push, amend,
force, delete evidence, or perform lifecycle operations. If the trial fails,
retain all partial evidence and stop; do not repair and rerun inside this
handoff.

## Required observations and completion

Record concrete evidence for startup/teardown, Oracle exit `0`, input read,
declared output/artifact transfer, separate verifier execution and reward,
trial provenance, Harbor/image identity, users, workdirs, resources,
timeouts, network policy, `/solution` staging, `/tests/test.sh` staging, and
absence of host checkout/home/Claude settings/Docker socket mounts. Record
unsupported storage enforcement as unsupported, not as a pass.

Append a Phase 1.2 rerun section to `evals/harbor/phase1-execution.md` with
the exact trial identifier, pre-run commit, evidence inventory and SHA-256
hashes, owner/mode/finalization time, observations, cleanup state, deviations,
and the next subphase gate. Keep the evidence directory immutable after
finalization and leave the worktree clean.

Run the applicable Harbor parser, posture validator, skill-eval validator,
`./d7y validate`, focused evidence checks, `git diff --check`, and
`git status --short`. Commit only the ledger/bookkeeping result on
`work/eval-harness-phase1`. Do not claim Phase 1.2 acceptance; return the
implementation report for review.
