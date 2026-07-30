---
plan: eval-execution-harness
execution: phase-1-1-fixture-contract-correction-2
status: committed
executor: claude-code
branch: work/eval-harness-phase1
worktree: /home/noviadi/Developments/discovery/d7y-worktrees/eval-harness-phase1
permission_profile: implementation-commit
---

Correct Phase 1.1 in the existing persistent worktree after review round 2.

Read the original Phase 1.1 prompt, the prior correction prompt, the current fixture, ledger, and Harbor 0.20.0 source for:

- `harbor.trial.trial.Trial._separate_verifier_env`
- `harbor.environments.docker.docker.DockerEnvironment.start`
- `harbor.environments.definition.should_use_prebuilt_docker_image`
- `harbor.verifier.verifier.Verifier._resolve_tests`

Review finding:

The current task still sets `[verifier.environment].docker_image = "d7y-eval-phase0-verifier:phase0"`. Harbor's separate verifier calls `start(force_build=False)`, and `should_use_prebuilt_docker_image(...)` therefore selects that prebuilt image and ignores `tests/Dockerfile`. The added Dockerfile does not actually stage `/tests/test.sh`.

Fix the fixture so the declared Harbor path really builds and uses `tests/Dockerfile` without a trial:

- Make the verifier environment use the local `tests/Dockerfile` as its environment definition by removing or otherwise correcting the verifier environment `docker_image` setting according to the Harbor 0.20.0 schema.
- Keep `tests/Dockerfile` based on the pinned Phase 0 verifier image and install `/tests/test.sh` there.
- Preserve separate verifier isolation and do not expose `tests/` to the agent environment.
- Update `evals/harbor/phase1-execution.md` so it says exactly why the Dockerfile is selected, what static source inspection proves, and what still requires Phase 1.2 runtime proof. Do not claim a trial result.
- Remove all trailing whitespace and ensure `git diff --check` passes.

Scope and safety:

- Phase 1.1 only: static fixture/configuration/build-contract work.
- Do not run `harbor trial start`, `harbor exec`, a Claude-agent trial, or any evidence-producing runtime.
- Do not modify the governing plan or prior prompts.
- Commit one correction commit on `work/eval-harness-phase1`.

Required checks before committing:

- Parse the task with Harbor 0.20.0.
- Use deterministic source/config inspection to prove that `start(force_build=False)` now selects the Dockerfile path (no trial).
- `python3 evals/harbor/scripts/posture.py`
- `python3 evals/validate_skill_evals.py`
- `./d7y validate`
- `git diff --check`
- clean `git status --short --branch` after commit.

Report the exact effective verifier build selection and resulting commit.
