---
status: committed
plan: docs/plans/eval-execution-harness.md
execution: phase-1.1-fixture-contract
executor: claude-code
branch: work/eval-harness-phase1
worktree: /home/noviadi/Developments/discovery/d7y-worktrees/eval-harness-phase1
permissionProfile: implementation-commit
commit: allowed
---

# Objective

Execute only Phase 1.1: establish and validate the canonical Harbor Phase 1
fixture contract. Do not run an agent trial, verifier trial, negative variant,
or evidence finalization. Do not edit the governing plan.

This is the first subphase in a persistent worktree. Later subphases will use
the same branch and worktree, but may start only from this subphase's clean
commit after review. The only accepted result here is a fixture that Harbor can
parse and whose input and separate-verifier staging paths are mechanically
understood before behavioral execution begins.

# Required context and fixed inputs

Read `AGENTS.md`, `CLAUDE.md`, `DEVELOPMENT.md`, the governing plan's Phase 0
and Phase 1 sections, `evals/harbor/README.md`, the Phase 0 profile/envelope/
payload, and the installed Harbor 0.20.0 source for `Task`, `OracleAgent`,
`Verifier`, and separate-verifier environment construction. Treat Harbor's
installed source as authoritative. The z.ai proxy/model mapping is intentional
and must not be changed.

Use these exact recorded inputs without rebuilding or weakening them:

- agent image `d7y-eval-phase0-agent:2.1.218`;
- verifier base image `d7y-eval-phase0-verifier:phase0`;
- `evals/harbor/config/execution-posture.json`;
- `evals/harbor/profiles/claude-primary.json`;
- `evals/harbor/payloads/starting-initiatives.json`.

# Work allowed

Only modify `evals/harbor/`. Create the standard Harbor task fixture under a
single stable path such as `evals/harbor/tasks/phase1-smoke/`, plus an
execution ledger at `evals/harbor/phase1-execution.md`. The ledger is
execution-level feedback and is not a replacement for or edit to the governing
plan.

The fixture must define, using Harbor 0.20.0's actual schema:

- `task.toml` with the exact environment, agent, verifier, user, network,
  resource, timeout, and artifact posture;
- `instruction.md` with no credentials or private checker material;
- a deterministic Oracle `solution/solve.sh` and synthetic declared input;
- a separate-verifier `tests/test.sh` that always writes
  `/logs/verifier/reward.txt` and does not trust agent-written reward files;
- the actual staging mechanism that makes `/task/input.txt` (or an explicitly
  documented equivalent) available to the agent without a host checkout;
- the actual staging mechanism that makes `/tests/test.sh` available inside the
  separate verifier while retaining the pinned Phase 0 verifier base posture.

Do not guess Harbor behavior. Prove the staging mechanism by reading the
installed 0.20.0 code and a no-trial fixture/build probe. If a derived verifier
build context is required, record why it still consumes the pinned Phase 0
verifier image and contains only the test payload. Do not use `/harmon`,
`harbor job start`, `harbor exec`, a Python simulation, or invented schema
fields.

# Verification and completion

Run the Harbor 0.20.0 parser/fixture validation, the posture validator, focused
fixture checks, `python3 evals/validate_skill_evals.py`, `./d7y validate`,
`git diff --check`, and `git status --short`. Do not start a Harbor trial; this
subphase is static/build-contract validation only. Record exact commands and
results, the resolved staging paths, unsupported capabilities, and the next
subphase gate in `evals/harbor/phase1-execution.md`.

Before committing, confirm no evidence directory was created, no Docker trial
resource remains, no prompt or governing plan changed, and the worktree is
clean. Commit the fixture and ledger on `work/eval-harness-phase1`. Do not
rebase, merge, push, amend, force, or perform worktree/branch lifecycle
operations. Do not claim Phase 1 or Phase 1.1 behavioral acceptance.
