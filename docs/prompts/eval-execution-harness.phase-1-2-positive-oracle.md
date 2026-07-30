---
status: committed
plan: eval-execution-harness
execution: phase-1-2-positive-oracle
executor: claude-code
branch: work/eval-harness-phase1
worktree: /home/noviadi/Developments/discovery/d7y-worktrees/eval-harness-phase1
permission_profile: implementation-commit
commit: allowed
lifecycle_authority: none
---

# Phase 1.2 — positive Harbor Oracle trial

Execute only Phase 1.2 in the existing persistent worktree, starting from
the reviewed clean Phase 1.1 tip. The governing plan and the Phase 1.1
fixture contract are authoritative. Do not modify the governing plan in this
subphase; record execution feedback in `evals/harbor/phase1-execution.md`.

## Required context and fixed inputs

Read before execution:

- `AGENTS.md`, `CLAUDE.md`, and `DEVELOPMENT.md`;
- `docs/plans/eval-execution-harness.md` Phase 0 and Phase 1 sections;
- `docs/prompts/README.md`;
- the accepted Phase 1.1 fixture and ledger;
- `evals/harbor/README.md`;
- `evals/harbor/profiles/claude-primary.json`;
- `evals/harbor/config/execution-posture.json`;
- `evals/harbor/payloads/starting-initiatives.json`;
- the installed Harbor 0.20.0 CLI/parser and Oracle trial implementation.

Use these exact Phase 0 inputs without rebuilding, weakening, or replacing
them:

- Harbor `0.20.0` through `uvx --from harbor==0.20.0`;
- agent image `d7y-eval-phase0-agent:2.1.218`;
- verifier base image `d7y-eval-phase0-verifier:phase0` through the accepted
  `tests/Dockerfile` build contract;
- execution posture: 2 CPU, 4096 MiB, 600-second agent timeout,
  120-second verifier timeout, no-network baseline, `api.z.ai` agent
  allowlist, separate no-network verifier;
- the intentional z.ai proxy/model mapping. Do not reinterpret or “correct”
  the requested Sonnet route or its expected `glm-4.7` provider result.

## Scope

Run exactly one positive Harbor Oracle trial using:

`evals/harbor/tasks/phase1-smoke/`

Use Harbor’s supported Oracle command (`harbor trial start -p <task-dir>
-a oracle`, after checking the installed `--help` if needed). Do not use
`harbor job start`, `harbor exec`, a Python simulation, or a Claude agent as
the Harbor agent.

Before the trial:

- verify the task parses with Harbor 0.20.0;
- verify the exact Phase 1.2 evidence directory is absent and no existing
  path component is a symlink;
- create it user-owned with mode `0700`:
  `/home/noviadi/Developments/discovery/d7y-eval-evidence/eval-execution-harness/phase-1-2-positive-oracle`;
- verify Docker access, the required images, the exact task fixture, and a
  clean worktree;
- record the pre-run source commit and resolved Harbor command before the
  first behavioral trial.

After the pre-run commit, do not change the task fixture, Dockerfile,
solution, verifier, or other executable trial inputs. Runtime evidence must
be attributable to that committed source. Do not rebase, merge, push, amend,
force, delete evidence, or perform worktree/branch lifecycle operations.

## Positive assertions

Retain the real Harbor trial directory and raw outputs in the Phase 1.2
evidence directory. Prove and record concrete observations for:

- container startup and fresh teardown;
- Oracle exit code `0` and successful input read;
- output creation and declared artifact collection;
- separate verifier startup and execution;
- verifier reward and artifact-transfer result;
- trial/job provenance, source commit, Harbor version, image identity, users,
  workdirs, resources, timeouts, and network policy;
- absence of host checkout, host home, host Claude settings, and Docker socket
  mounts in the agent environment;
- agent-side `/solution` staging and verifier-side `/tests/test.sh` staging.

Do not turn unsupported storage enforcement into a pass claim. Record it as
unsupported if the provider cannot enforce it. Do not run negative variants,
credential canaries, network probes beyond the configured positive smoke
behavior, or any Phase 1.3–1.6 work in this subphase.

## Evidence and completion

Keep the evidence directory outside Git and immutable after finalization.
Finalize it with its absolute path, owner, mode, complete file inventory,
SHA-256 hashes, and finalization time. Do not retain credentials or private
values. Preserve partial raw evidence if the trial fails; classify the result
as infrastructure, agent, evidence, verifier, or assertion failure according
to the governing plan rather than treating failure as success.

Append a Phase 1.2 section to `evals/harbor/phase1-execution.md` containing:

- exact command and trial/job identifiers;
- pre-run source commit and Harbor/image/provider identity;
- positive observations and raw evidence inventory;
- unsupported capabilities and deviations;
- cleanup state and the next subphase gate;
- explicit distinction between behavioral evidence and static validation.

Run and report, as applicable to the accepted fixture:

- Harbor 0.20.0 task parsing and the positive Oracle trial;
- focused fixture/evidence inventory checks;
- `python3 evals/harbor/scripts/posture.py`;
- `python3 evals/validate_skill_evals.py`;
- `./d7y validate`;
- `git diff --check` and `git status --short`.

Commit only the Phase 1.2 ledger/evidence bookkeeping on
`work/eval-harness-phase1`. Leave the worktree clean. Do not claim Phase 1
or Phase 1.2 acceptance; return the implementation report for review.
