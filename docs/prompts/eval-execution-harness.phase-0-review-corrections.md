---
status: committed
plan: docs/plans/eval-execution-harness.md
execution: phase-0-review-corrections
executor: claude-code
branch: work/eval-harness-executable-posture
worktree: /home/noviadi/Developments/discovery/d7y-worktrees/eval-harness-executable-posture
permissionProfile: implementation-commit
commit: allowed
---

# Objective

Correct the bounded Phase 0 review findings on the existing
`work/eval-harness-executable-posture` branch. Make image scanning fail closed,
enforce the recorded Claude Code binary checksum in the image recipe, remove
installer-generated identity state from the final image, reject duplicate
payload sources, and reconcile the evidence to the strength actually proven.
Do not implement or run Phase 1 behavior or make a model/API call.

# Activation and handoff identity

This is a new concrete correction handoff. The original committed Phase 0
prompt is immutable execution evidence and must not be edited.

The launcher-resolved starting `HEAD` must contain the two original Phase 0
implementation commits rebased onto the `main` commit containing this prompt.
The launcher envelope must name the exact branch and worktree in this prompt.
Stop on a mismatch, dirty worktree, missing original implementation, or missing
prompt.

# Required context

Read before editing:

- `AGENTS.md`, `CLAUDE.md`, and `DEVELOPMENT.md`;
- `docs/discovery-workbench.md`;
- `docs/skill-evaluations.md`;
- `docs/plans/eval-execution-harness.md`, including Phase 0 feedback;
- `docs/prompts/README.md`;
- `docs/prompts/eval-execution-harness.phase-0-executable-posture.md`;
- the complete `main...HEAD` diff and both original Phase 0 commits;
- every file currently under `evals/harbor/`.

# Review findings to correct

1. `evals/harbor/scripts/scan_image.py` decides cleanliness from empty hit
   lists without requiring the image scan process to succeed. A Docker run exit
   code such as 125 can therefore be reported `CLEAN`.
2. The synthetic canary records `leaked: false` when its Docker build fails,
   and `main()` treats that as a passing canary. Build, scan, and cleanup
   failures must not become absence evidence.
3. The agent recipe records the installed Claude Code binary checksum but does
   not independently enforce it. The retained image also contains
   installer-generated `.claude` backup state with generated machine/user IDs.
4. The payload validator silently skips validation after the first occurrence
   of a source rather than rejecting duplicate sources.
5. The feedback describes a cached same-digest rebuild as proof that the recipe
   is reproducible. The base, installer bootstrap, version, and retained image
   identity are pinned, but Debian package resolution is not snapshot-pinned
   and a cached rebuild is not an independent clean rebuild.
6. The feedback says only prefixed Docker resources were created and records no
   deviation, although a disposable `hello-world` daemon probe was run. Record
   that bounded exception and its cleanup truthfully.

# Writable paths

- `evals/harbor/`
- `docs/plans/eval-execution-harness.md` for reconciliation of the existing
  Phase 0 implementation feedback only

Do not modify either delegation prompt, the eval schema, a skill, an
initiative, another plan, or canonical product behavior outside this Phase 0
posture.

# Permission and external-state envelope

- Profile: `implementation-commit`
- Extra tool grants: none
- Executor network: bootstrap acquisition and the bounded clean Docker rebuild
  only.
- Reviewed bootstrap destinations remain those in the original Phase 0 prompt.
- Harbor model/API calls: prohibited.
- MCP: strict-empty.
- Credentials: no real model credential may be read, injected, tested, or
  printed. Synthetic canary values only.
- Docker: local daemon access is authorized for resources prefixed
  `d7y-eval-phase0-`. Do not create another unprefixed daemon probe and do not
  mount the Docker socket into a container. Remove disposable containers,
  networks, and canary images. Retain only the two recorded Phase 0 images.
- Commit authority: cohesive commits on the assigned branch only.
- Lifecycle authority: no rebase, merge, push, worktree removal, branch
  creation/deletion, amend, force operation, or modification of `main`.

# Required work

1. Make every image-scan and synthetic-canary execution failure fail closed.
   Reports must distinguish command failure from detected forbidden material,
   include useful redacted diagnostics, and return non-zero for either.
   A failed canary build, failed scan, or failed cleanup is not `CLEAN`.
2. Add deterministic unit tests that exercise at least a failed image scan and
   a failed canary build without requiring a live Docker daemon. Preserve tests
   for successful clean and detected-dirty decisions where useful.
3. Add the recorded linux-x64 Claude Code binary SHA-256 as an explicit build
   input and verify the installed versioned binary against it during the build.
   Keep the version check without making a model call.
4. Remove installer-generated `.claude` state from the final image after all
   build-time version checks. Verify the retained image contains no
   `.claude` directory, settings, generated machine/user IDs, or credentials.
5. Reject duplicate fixed payload sources and add a focused invalid-case test.
6. Commit the corrected executable inputs, then perform a no-cache final build
   from that commit. Re-run image inspection and canary verification, update
   the exact image digests and evidence, and place feedback-only recording in a
   later commit.
7. Describe reproducibility precisely:
   - distinguish pinned inputs and exact retained image identity from
     from-scratch byte-for-byte reproducibility;
   - state that Debian package resolution is not snapshot-pinned;
   - do not use a cache-backed rebuild as proof of independent reproducibility;
   - require any future rebuild with a different digest to be rescanned and
     recorded before use.
8. Reconcile the Phase 0 feedback, `evals/harbor/README.md`, and
   `evals/harbor/posture.json` so version/digest/test counts, retained resources,
   deviations, limitations, and claims agree. Record the disposable
   `hello-world` probe as the original execution deviation; do not repeat it.

# Verification

Run and report:

- focused scanner tests, including simulated command/build failure;
- `python3 evals/harbor/scripts/posture.py`;
- all Phase 0 unit tests;
- a no-cache build of both final Phase 0 images from the committed corrected
  inputs;
- container-side `claude --version` and checksum verification without a model
  call;
- image inspection for configured user, mounts, environment, digest, forbidden
  material, and absence of `/home/agent/.claude`;
- the real image scanner and synthetic canary against the final images;
- `python3 evals/validate_skill_evals.py`;
- `./d7y validate`;
- `git diff --check`;
- `git status --short`.

Static validation and image construction remain posture evidence, not a Harbor
execution pass.

# Stop conditions

Stop and record `environment_error` without weakening a gate if a clean rebuild
cannot acquire its reviewed inputs, the installed binary does not match the
explicit checksum, Docker verification fails, disposable resources cannot be
removed, or truthful evidence cannot be reconciled. Do not substitute a live
API probe, a different agent version, a wider credential posture, or a
pass-on-error scanner.

# Completion

Commit corrected executable inputs before the final no-cache build. Append or
reconcile the existing `### Phase 0 implementation feedback` only after that
build and inspection, in a later commit. Record files changed, exact image
digests, verification results, the original daemon-probe deviation, corrected
limitations, external resources retained, and any residual risk. Return a
clean worktree. Do not mark Phase 0 accepted; Amp reviews and integrates.
