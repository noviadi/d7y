---
status: committed
plan: eval-execution-harness
execution: phase-1-2-runtime-fixes
executor: claude-code
branch: work/eval-harness-phase1
worktree: /home/noviadi/Developments/discovery/d7y-worktrees/eval-harness-phase1
permission_profile: implementation-commit
commit: allowed
lifecycle_authority: none
---

# Phase 1.2 runtime fixes

Implement the two confirmed runtime fixes in the existing persistent Phase 1
worktree. Do not run a Harbor trial in this handoff; the corrected smoke trial
will use a new immutable execution prompt and evidence directory after review.

## Confirmed failures

Harbor 0.20.0's Docker execution applies the task's configured
`workdir = "/workspace"` to every `environment.exec()` call. The Phase 0
agent image did not contain `/workspace`, so Docker failed before `chmod` and
before Oracle could start, returning `127`.

An isolated derived image containing agent-owned `/workspace` allowed Oracle to
run successfully and produced `/solution/output.txt` with the expected SHA-256.
The separate verifier then failed because the fixture verifier looked for
`/logs/artifacts/solution/output.txt`, while Harbor 0.20.0 re-materializes
declared artifacts at their original source path, `/solution/output.txt`.

Do not attribute either failure to the expected Sonnet-to-`glm-4.7` proxy route.

## Required changes

Change only these durable files:

- `evals/harbor/images/agent/Dockerfile`
- `evals/harbor/tasks/phase1-smoke/tests/test.sh`
- `evals/harbor/README.md`
- `evals/harbor/phase1-execution.md`

In the agent Dockerfile, add only an agent-owned `/workspace` directory after
the `agent` user exists. Preserve the image's users, entrypoint/default
command, environment, installed packages, network posture, Claude version,
and all existing image checks. Do not add `WORKDIR`; Harbor supplies the task
working directory. Use the existing `agent` user and group.

In the Phase 1 verifier script, change the expected artifact path to the
declared artifact's actual verifier-side path `/solution/output.txt`. Keep
the content assertion, reward behavior, and verifier isolation unchanged.

Update the Harbor README to document that the Phase 0 agent image provides an
agent-owned `/workspace` working directory and that declared artifacts are
re-materialized at their original source paths in the separate verifier.
Append implementation feedback to `evals/harbor/phase1-execution.md`, clearly
separating the two root causes, the temporary derived-image experiment, and
the corrected durable inputs. Do not rewrite historical failed evidence.

Do not modify `docs/plans/eval-execution-harness.md`, existing concrete
prompts, `task.toml`, the solution script, the verifier Dockerfile, the Phase
0 verifier image, posture policy values, or any evidence directory.

## Required verification

Run and report:

- `docker build -t d7y-eval-phase0-agent:2.1.218 -f evals/harbor/images/agent/Dockerfile evals/harbor/images/agent`;
- a disposable container check proving `/workspace` exists and is owned by
  `agent`, while the configured runtime user remains `agent`;
- `python3 evals/harbor/scripts/posture.py`;
- `python3 evals/validate_skill_evals.py`;
- `./d7y validate`;
- focused task inspection confirming the verifier checks `/solution/output.txt`;
- `git diff --check` and `git status --short --branch`.

Commit exactly one implementation commit on `work/eval-harness-phase1`, leave
the worktree clean, and return the changed-path list, build/image identity,
verification results, deviations, and residual risks. Do not claim Phase 1.2
acceptance; that requires the subsequent fresh Harbor trial review.
