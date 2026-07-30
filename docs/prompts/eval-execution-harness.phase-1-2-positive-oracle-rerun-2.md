---
status: committed
plan: eval-execution-harness
execution: phase-1-2-positive-oracle-rerun-2
executor: claude-code
branch: work/eval-harness-phase1
worktree: /home/noviadi/Developments/discovery/d7y-worktrees/eval-harness-phase1
permission_profile: implementation-commit
commit: allowed
lifecycle_authority: none
---

# Phase 1.2 positive Oracle rerun 2

Run the single positive Harbor Oracle trial after the reviewed Oracle fixture
portability correction. This is a new, final bounded iteration of Phase 1.2,
not a continuation of either failed trial. Work only in the existing persistent
task worktree and start from its clean launcher-recorded tip.

## Governing context and accepted corrections

Read `AGENTS.md`, `CLAUDE.md`, `DEVELOPMENT.md`, the Phase 0 and Phase 1
sections of `docs/plans/eval-execution-harness.md`, `docs/prompts/README.md`,
the Phase 1.1 ledger, all committed Phase 1.2 prompts and correction prompts,
`evals/harbor/README.md`, and the installed Harbor 0.20.0 Oracle trial source.

The persistent branch already contains the reviewed Phase 1.1 fixture,
verifier-Dockerfile correction, and Oracle portability correction. The current
Oracle fixture is intentionally POSIX `/bin/sh` and uses shell built-ins for
the copy behavior. Do not modify any executable input in this handoff. The
intentional z.ai proxy and Sonnet-to-`glm-4.7` routing are expected and must
not be changed; this Oracle trial requires no model credential.

Preserve both prior Phase 1.2 evidence roots and do not attribute success to
either:

- `/home/noviadi/Developments/discovery/d7y-eval-evidence/eval-execution-harness/phase-1-2-positive-oracle`
- `/home/noviadi/Developments/discovery/d7y-eval-evidence/eval-execution-harness/phase-1-2-positive-oracle-rerun-1`

## Exact execution contract

The exact new evidence directory is:

`/home/noviadi/Developments/discovery/d7y-eval-evidence/eval-execution-harness/phase-1-2-positive-oracle-rerun-2`

Before execution, verify that this path is absent and has no symlink in any
existing component. Create it user-owned with mode `0700`. Keep raw Harbor
trial output and the real trial directory there. Record the pre-run source
commit and exact command before the first behavioral trial.

Use exactly the accepted fixture at `evals/harbor/tasks/phase1-smoke/`, Harbor
`0.20.0` via `uvx --from harbor==0.20.0`, agent image
`d7y-eval-phase0-agent:2.1.218`, verifier base image
`d7y-eval-phase0-verifier:phase0`, and the recorded Phase 0 posture. Run this
exact supported command, substituting only the evidence path:

`uvx --from harbor==0.20.0 harbor trial start -p evals/harbor/tasks/phase1-smoke -a oracle --trials-dir /home/noviadi/Developments/discovery/d7y-eval-evidence/eval-execution-harness/phase-1-2-positive-oracle-rerun-2/trials`

Run exactly one positive trial. Do not run negative variants, a Claude agent,
`harbor job start`, `harbor exec`, a Python simulation, unrelated network
probes, credential canaries, or later subphases. Do not retry in place.

After the pre-run commit, do not modify the task, Dockerfile, solution,
verifier, or other executable inputs. Do not rebase, merge, push, amend,
force, delete evidence, or perform lifecycle operations. If the trial fails,
retain all partial evidence and stop. Evidence directories are immutable after
finalization.

## Required observations and completion

Record concrete evidence for container startup and fresh teardown, Oracle exit
`0`, input read, declared output/artifact transfer, separate verifier
execution and reward, trial provenance, Harbor/image identity, users,
workdirs, resources, timeout, network policy, `/solution` staging,
`/tests/test.sh` staging, and absence of host checkout/home/Claude settings/
Docker socket mounts. Record unsupported storage enforcement as unsupported,
not as a pass. Preserve the exact trial identifier, result ID, pre-run commit,
evidence inventory, SHA-256 hashes, owner/mode/finalization time, cleanup
state, deviations, and the next subphase gate.

Append a Phase 1.2 final-rerun section to `evals/harbor/phase1-execution.md`.
Only append ledger/bookkeeping feedback after the trial; do not claim Phase
1.2 acceptance in the handoff. Commit only that ledger result on
`work/eval-harness-phase1` and leave the worktree clean.

Run the supported Harbor task parser or equivalent installed Harbor validation
(report the exact command; do not invent an unsupported CLI subcommand),
`python3 evals/harbor/scripts/posture.py`,
`python3 evals/validate_skill_evals.py`, `./d7y validate`, focused evidence
checks, `git diff --check`, and `git status --short --branch`. Return the
implementation report for independent review, including any deviation or
residual risk. Do not integrate the branch into `main`.
