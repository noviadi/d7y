---
status: committed
plan: docs/plans/eval-execution-harness.md
execution: phase-0-scanner-completeness
executor: claude-code
branch: work/eval-harness-executable-posture
worktree: /home/noviadi/Developments/discovery/d7y-worktrees/eval-harness-executable-posture
permissionProfile: implementation-commit
commit: allowed
---

# Objective

Correct the remaining Phase 0 acceptance blocker on the existing
`work/eval-harness-executable-posture` branch: make the retained-image
filesystem scan complete and genuinely fail closed. Requalify the unchanged
agent and verifier images with the corrected scanner, reconcile the evidence,
and return a clean branch for review. Do not rebuild the retained images,
implement Phase 1, or make a model/API call.

# Activation and handoff identity

This is a new immutable correction handoff. Do not edit either earlier Phase 0
prompt or this prompt.

The launcher-resolved starting `HEAD` must contain the complete Phase 0
implementation through `f3dc8a1`, rebased onto the `main` commit containing this
prompt. The launcher envelope must name the exact branch and worktree in this
prompt. Stop on a mismatch, dirty worktree, missing implementation, or missing
prompt.

# Required context

Read before editing:

- `AGENTS.md`, `CLAUDE.md`, and `DEVELOPMENT.md`;
- `docs/discovery-workbench.md`;
- `docs/skill-evaluations.md`;
- `docs/plans/eval-execution-harness.md`, including all Phase 0 feedback;
- `docs/prompts/README.md`;
- both earlier Phase 0 delegation prompts;
- the complete `main...HEAD` diff and all Phase 0 commits;
- every file currently under `evals/harbor/`.

# Acceptance-review finding

The current scanner detects a non-zero outer `docker run`, but the command
inside the container is incomplete:

- it runs as the image-configured non-root user;
- it discards `find` and `grep` diagnostics;
- its final `printf` returns zero even when those internal traversals fail;
- the content-search pipeline can mask the search command's status;
- missing or malformed output sections are interpreted as empty/absent.

Independent review reproduced this against the retained agent image:

```text
configured user: agent
find exit: 1 (unreadable image paths)
grep exit: 2 (unreadable image paths)
```

The existing wrapper nevertheless recorded `scan_command_failed=false` and
`CLEAN`. Therefore the previous live `CLEAN` evidence does not prove a complete
filesystem scan and must be superseded.

# Writable paths

- `evals/harbor/scripts/scan_image.py`
- `evals/harbor/scripts/test_scan_image.py`
- `evals/harbor/README.md`
- `evals/harbor/posture.json`
- `docs/plans/eval-execution-harness.md` for Phase 0 evidence reconciliation
  only

Do not modify image recipes, profiles, the execution envelope, payloads, either
earlier prompt, the eval schema, a skill, an initiative, another plan, or
canonical product behavior.

# Permission and external-state envelope

- Profile: `implementation-commit`
- Extra tool grants: none
- Executor network: no acquisition or model/API network is needed.
- Harbor model/API calls: prohibited.
- MCP: strict-empty.
- Credentials: no real model credential may be read, injected, tested, or
  printed. Synthetic canary values only.
- Docker: local daemon access is authorized for read-only inspection of the two
  retained images and disposable resources prefixed `d7y-eval-phase0-`. Do not
  create an unprefixed daemon probe, mount the Docker socket into a container,
  or rebuild/retag the retained agent or verifier images. Remove every
  disposable canary container/image.
- Commit authority: cohesive commits on the assigned branch only.
- Lifecycle authority: no rebase, merge, push, worktree removal, branch
  creation/deletion, amend, force operation, or modification of `main`.

# Required work

1. Run the qualification scan as an explicit root inspection process
   (`--user 0:0`) while preserving the image's configured non-root runtime user.
   This is scanner privilege only; do not change either image recipe or runtime
   posture.
2. Make the in-container traversal fail closed:
   - a failed `find` is a command failure;
   - content-search exit 1 means no match and is valid;
   - content-search exit greater than 1 is a command failure;
   - no pipeline may mask the status of the command supplying evidence;
   - do not silently discard the diagnostic needed to classify failure.
3. Require a complete, well-formed output protocol. A zero-exit response with a
   missing, duplicate, or invalid `FILES`, `CONTENT`, or `IDENTITY` section is a
   structured command/protocol failure, never an empty clean result.
4. Keep environment inspection fail closed, including malformed inspect JSON.
   Report structured, bounded diagnostics without a traceback-only failure.
5. Fully redact the generated synthetic canary token from diagnostics and
   reports. Do not leave its random suffix or partial value after replacing only
   the static prefix.
6. Extend deterministic tests to prove at least:
   - the scan invokes Docker with explicit root inspection;
   - outer Docker failure is non-clean;
   - malformed or incomplete zero-exit scan output is non-clean;
   - environment-inspect failure/malformed JSON is non-clean;
   - dirty and clean results remain distinguishable;
   - canary build/scan/cleanup failures remain non-clean;
   - the full synthetic token is absent from returned diagnostics.
   Tests must not require Docker and must clean their temporary directories.
7. Commit the corrected scanner and tests before live Docker verification.
8. Re-run the corrected scanner and synthetic canary against the unchanged
   retained images. Confirm their exact recorded digests remain:
   - agent:
     `sha256:34b394a9bb9cd961dec70513bce375a5acb6203775a7b9567d26cdf75c01e5c1`;
   - verifier:
     `sha256:35b47fbb2fe1a4b01e9d10b6683a5e03e1e15aba4f5b9648d204186267023ca3`.
9. Reconcile `README.md`, `posture.json`, and the plan feedback:
   - explicitly supersede the previous incomplete live scan;
   - record the independent reproduction and the corrected scanner source
     commit;
   - record the corrected live scan/canary result and test count;
   - do not change image-build provenance or imply an image rebuild;
   - retain the existing reproducibility limitations and Phase 0 boundary.

# Verification

Run and report:

- `python3 evals/harbor/scripts/test_scan_image.py`;
- `python3 evals/harbor/scripts/test_posture.py`;
- `python3 evals/harbor/scripts/posture.py`;
- exact Docker image digest/configured-user inspection;
- the corrected real image scanner and synthetic canary against both retained
  images;
- container-side confirmation that the agent identity paths remain absent,
  without a model call;
- cleanup inspection for disposable `d7y-eval-phase0-` canary resources;
- `python3 evals/validate_skill_evals.py`;
- `./d7y validate`;
- `git diff --check`;
- `git status --short`.

Static validation and image scanning remain posture evidence, not a Harbor
execution pass.

# Stop conditions

Stop and record `environment_error` without weakening a gate if the retained
image identities differ, a complete root filesystem scan cannot be performed,
internal traversal status cannot be distinguished from no matches, Docker
verification fails, disposable resources cannot be removed, or truthful
evidence cannot be reconciled. Do not substitute a partial scan, an image
rebuild, a live API probe, wider credentials, or pass-on-error behavior.

# Completion

Use one commit for the corrected scanner/tests and a later commit for
post-verification evidence reconciliation. Record changed files, tests,
corrected live results, unchanged image identities, superseded evidence,
external resources, deviations, and residual risk. Return a clean worktree.
Do not mark Phase 0 accepted; Amp reviews and integrates.
