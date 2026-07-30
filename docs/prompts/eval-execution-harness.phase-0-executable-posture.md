---
status: draft
plan: docs/plans/eval-execution-harness.md
execution: phase-0-executable-posture
executor: claude-code
branch: work/eval-harness-executable-posture
worktree: /home/noviadi/Developments/discovery/d7y-worktrees/eval-harness-executable-posture
permissionProfile: implementation-commit
commit: allowed
---

# Objective

Implement only Phase 0 of `docs/plans/eval-execution-harness.md`: establish
reproducible Harbor, Docker, agent-image, verifier-image, API-profile, network,
resource, and runtime-payload inputs for later phases. Do not run a Harbor model
trial or implement the smoke task, case adapter, grader, or comparison runner.

# Activation and handoff identity

This prompt is executable only after it is committed with `status: committed`
on `main`. The launcher-resolved starting `HEAD` is the exact base commit and
must contain this prompt, the revised plan, and the revised evaluation canon.
The launcher envelope must name the exact branch and worktree in this prompt.
Stop on any mismatch, dirty worktree, or missing input.

There is no predecessor phase. The frozen `work/eval-execution-harness` branch
and superseded `harbor-qualification` prompt are historical inputs only.
A human must supply the exact non-secret direct-endpoint or proxy identity,
requested model, allowed hosts, runtime key names, and credential key name
before execution. The credential value is not a Phase 0 input.

# Required context

Read before editing:

- `AGENTS.md`, `CLAUDE.md`, and `DEVELOPMENT.md`;
- `docs/discovery-workbench.md`;
- `docs/discovery-workbench-principles.md`;
- `docs/skill-evaluations.md`;
- `docs/plans/eval-execution-harness.md`;
- `docs/prompts/README.md`;
- Harbor `v0.20.0` task, Docker, agent, skill, resource, network, artifact, and
  separate-verifier documentation;
- the complete committed diff from the launcher-resolved base.

# Writable paths

- `evals/harbor/`
- `DEVELOPMENT.md`
- `docs/plans/eval-execution-harness.md` for Phase 0 feedback only

New files are authorized only under `evals/harbor/`. Do not modify this prompt,
the eval schema, a skill, an initiative, or another plan.

# Permission and external-state envelope

- Profile: `implementation-commit`
- Extra tool grants: none
- Executor network: bootstrap acquisition only.
- Reviewed bootstrap destinations:
  `pypi.org`, `files.pythonhosted.org`, `registry-1.docker.io`,
  `auth.docker.io`, `production.cloudflare.docker.com`,
  `registry.npmjs.org`, `downloads.claude.ai`,
  `www.harborframework.com`, `github.com`, and
  `raw.githubusercontent.com`.
- Harbor model/API calls: prohibited.
- MCP: strict-empty.
- Credentials: no real model credential may be read, injected, tested, or
  printed. Record only the human-supplied non-secret profile values and
  credential key name.
- Docker: local daemon access is authorized for resources prefixed
  `d7y-eval-phase0-`. Do not mount the Docker socket into a container. Remove
  disposable containers and networks; retain an image only when its exact
  identity and rebuild recipe are recorded.
- Commit authority: cohesive commits on the assigned branch only.
- Lifecycle authority: no rebase, merge, push, worktree removal, branch
  creation/deletion, amend, force operation, or modification of `main`.

# Required work

1. Run and record the exact Harbor, Docker client/server, Docker context, and
   Python versions. Use Harbor `0.20.0` through a pinned non-global invocation.
2. Establish the smallest reproducible agent image containing the exact Claude
   Code version and required shell/process tools. Prefer a pinned base and
   deterministic build inputs. Prove the installed version without a model call.
3. Establish the separate verifier image posture and its no-network baseline.
   Do not add case-specific private graders yet.
4. Validate the human-supplied API-profile values and commit the resolved
   non-secret artifact at `evals/harbor/profiles/claude-primary.json`. It records
   requested model, endpoint identity, exact allowed hosts, runtime key names,
   credential key name, and redacted digest semantics. Do not invent or default
   endpoint, provider, model, or credential values.
5. Record CPU limit, memory limit, agent timeout, verifier timeout, users,
   network baselines/overrides, declared storage, and effective local-Docker
   storage support. Storage enforcement must be `unsupported`, not simulated.
6. Define the exact `starting-initiatives` runtime payload and prove the image
   does not bake in the source checkout, host settings, eval definitions,
   expected outcomes, graders, credentials, or benchmark material.
7. Commit the image recipe, profile, and other executable Phase 0 inputs, return
   to a clean source state, then perform the final image build and inspection
   from that commit. Record the pre-build commit. Any later feedback is a
   separate commit.
8. Document exact inputs Phase 1 may consume. Do not build Phase 1 behavior.

# Verification

Run and report:

- `uvx --from harbor==0.20.0 harbor --version`;
- `docker --version` and `docker info`;
- reproducible image build or digest resolution;
- container-side `claude --version`;
- image inspection for configured user, mounts, environment, and digest;
- deterministic inspection of Dockerfiles, build arguments, secret mounts,
  configured environment key names, image history, and image file paths;
- a synthetic canary scan over the image and retained build evidence;
- confirmation that no forbidden host settings path or settings file is
  present, while explicitly recording that unknown secret bytes cannot be
  exhaustively disproved without reading them;
- focused tests for any configuration parser or digest logic added;
- `python3 evals/validate_skill_evals.py`;
- `./d7y validate`;
- `git diff --check`;
- `git status --short`.

Static files or successful image construction are posture evidence only, not a
Harbor execution pass.

# Stop conditions

Stop and record `environment_error` without broadening scope if Docker is
unavailable, Harbor `0.20.0` cannot be acquired, an image cannot be pinned, or
the required network posture or concrete non-secret API profile cannot be
represented. A missing XFS quota or host firewall is a limitation, not a
blocker. Do not substitute another provider, the historical host wrapper, an
unpinned latest version, or a live API probe.

# Completion

Append `### Phase 0 implementation feedback` to the governing plan with files
changed, exact versions and digests, Docker context, API-profile status,
profile path/digest, pre-build source commit, verification results, external
resources retained, deviations, limitations, and the inputs required by Phase
1. Commit only authorized paths and return a clean worktree. Do not mark the
plan or Phase 0 accepted; Amp reviews and integrates.
