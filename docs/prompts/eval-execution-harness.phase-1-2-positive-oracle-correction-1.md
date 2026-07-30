---
status: committed
plan: eval-execution-harness
execution: phase-1-2-positive-oracle-correction-1
executor: claude-code
branch: work/eval-harness-phase1
worktree: /home/noviadi/Developments/discovery/d7y-worktrees/eval-harness-phase1
permission_profile: implementation-commit
commit: allowed
lifecycle_authority: none
---

# Phase 1.2 correction 1 — verifier image build permissions

Correct the Phase 1.2 fixture in the existing persistent worktree after the
first positive Oracle iteration failed during verifier image construction.

## Failure context

The first trial used pre-run source commit `900c1ed8d41b72f8360957763eb905d26cbfd062`.
Harbor 0.20.0 built `tests/Dockerfile`, but failed at:

`RUN chmod +x /tests/test.sh`

with `Operation not permitted`. The Phase 0 verifier base image runs as the
non-root `verifier` user, so the Dockerfile’s runtime permission commands are
not valid. The first delegation also made an out-of-scope post-trial commit
`164795f7fedb030ce0463fc41b726b2f558e0563`; preserve that history but do not
attribute any behavioral evidence to it. Do not delete existing partial
evidence.

## Required correction

- Read the governing plan, the accepted Phase 1.1 fixture contract, the
  Phase 1.2 prompt, and the Harbor/Docker build behavior.
- Fix the verifier Dockerfile with the smallest supported change: set the
  `/tests/test.sh` mode and ownership at copy time (for example using Docker
  `COPY --chmod` and `COPY --chown` semantics), avoiding privileged `RUN
  chmod` or `RUN chown` commands under the non-root base user. Keep the
  verifier runtime user as `verifier` and retain the Phase 0 image as `FROM`.
- Run a real Dockerfile build or equivalent deterministic build check to prove
  the image can be constructed and `/tests/test.sh` is executable/readable;
  this correction handoff must not run a Harbor trial.
- Do not modify the solution, task schema, verifier assertions, governing
  plan, original Phase 1.2 prompt, or prior evidence.
- Commit exactly one correction commit on `work/eval-harness-phase1` and leave
  the worktree clean.

## Evidence and safety

The failed iteration’s evidence root is:

`/home/noviadi/Developments/discovery/d7y-eval-evidence/eval-execution-harness/phase-1-2-positive-oracle`

Preserve it, including partial trial material. Do not delete or overwrite it.
The later positive rerun will use a new evidence directory supplied by a new
execution handoff. Do not run `harbor trial start`, `harbor exec`, negative
variants, or a Claude Harbor agent in this correction.

## Required checks

- deterministic Dockerfile/build check against the local
  `d7y-eval-phase0-verifier:phase0` image;
- Harbor 0.20.0 task parsing;
- `python3 evals/harbor/scripts/posture.py`;
- `python3 evals/validate_skill_evals.py`;
- `./d7y validate`;
- `git diff --check` and clean `git status --short --branch`.

Report the failed trial classification, exact Dockerfile correction, build
result, and resulting commit. Do not claim Phase 1.2 acceptance.
