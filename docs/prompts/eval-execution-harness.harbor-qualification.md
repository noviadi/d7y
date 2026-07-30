---
title: Harbor Qualification for Skill Eval Foundation
type: prompt
status: superseded
createdAt: 2026-07-30
updatedAt: 2026-07-30
---

# Harbor Qualification for Skill Eval Foundation

> Superseded without execution by the phase-specific prompt sequence recorded
> in `docs/plans/eval-execution-harness.md`. This prompt describes the rejected
> provider-certification posture and must not be delegated.

You are implementing the first Harbor qualification slice for D7Y's progressive skill-eval foundation.

## Handoff payload

- Governing plan: `docs/plans/eval-execution-harness.md`
- Execution slug: `harbor-qualification`
- Executor: Claude Code through `scripts/delegate-claude.sh`
- Assigned branch: `work/eval-execution-harness-harbor`
- Assigned worktree: `/home/noviadi/Developments/discovery/d7y-worktrees/eval-execution-harness-harbor`
- Permission profile: `implementation-commit`
- Extra tool grants: none
- Executor network posture: blocked pending a reviewed network-enabled launcher posture or pre-staged offline Harbor package/image bundle; the current launcher reports network `prohibited`
- Executor MCP posture: strict-empty; no MCP servers
- Executor persistence posture: disabled
- Writable paths: assigned worktree only, plus explicitly disposable `/tmp/d7y-harbor-*` and `/tmp/d7y-harbor-uv-cache` directories; no host checkout, host home, or credential paths. Host Docker daemon resources are external state, not trial-container mounts.
- Required context: `AGENTS.md`, `DEVELOPMENT.md`, `docs/discovery-workbench.md`, `docs/discovery-workbench-principles.md`, `docs/skill-evaluations.md`, `docs/plans/eval-execution-harness.md`, `docs/prompts/README.md`, and the Harbor `v0.20.0` task, agent, network, and artifact documentation
- Commit authority: explicitly granted on the assigned branch only
- Executor lifecycle authority: no rebase, merge, push, worktree removal, or branch deletion
- Frozen branch: `/home/noviadi/Developments/discovery/d7y-worktrees/eval-execution-harness` is historical and must not be reused

## First stop: prerequisites

Before editing implementation files, run and record:

```text
uvx --from harbor==0.20.0 harbor --version
docker --version
docker info
python3 --version
```

This prompt is not executable until the launcher network posture is resolved. `scripts/delegate-claude.sh` currently reports network `prohibited`, while Harbor package resolution and Docker image pulls require network access. Either add and review a network-enabled launcher posture or pre-stage exact Harbor packages and image digests for offline execution; do not silently override the launcher posture.

Use Harbor `0.20.0` and local Docker only. If Harbor cannot be resolved at exactly `0.20.0`, or `docker info` cannot access a daemon, stop and report `environment_error`; do not substitute the old wrapper, a shared latest installation, or another provider. Record Docker server version, storage driver, cgroup/runtime posture, kernel/network prerequisites, and Harbor image digests. Use `UV_CACHE_DIR=/tmp/d7y-harbor-uv-cache` or `--no-cache`; do not mutate shared user tooling with `uv tool install`.

The initial fixed task limits are environment build 600 seconds, agent setup 600 seconds, agent run 600 seconds, verifier 120 seconds, 2 CPUs, 4096 MiB memory, and 10240 MiB storage. Set CPU and memory enforcement modes explicitly to `limit` (not `auto`). Map network policy explicitly: `[environment].network_mode` is the startup/setup baseline, `[agent].network_mode` is the agent-run override, and `[verifier].network_mode` is the verifier override. Setup package hosts, if any, belong only to the environment baseline allowlist; Gate A has no live model endpoint. The host implementation executor remains Claude Code and may use its own invocation credentials; the launcher-imported host environment must never be copied into the Harbor trial.

The Harbor trial must not read or mount the host user's `~/.claude/settings.json`. The launcher may read the host settings for the implementation executor under its existing posture, but those values are not valid Harbor-trial configuration. Gate A reserves task `[environment].env` for a public non-secret interpolation sentinel and also uses a deliberately fake sensitive-looking value through TrialConfig's `agent.env`, with a key matching Harbor's sensitive-key recognition such as `D7Y_TEST_AUTH_TOKEN`. The raw fake canary must appear nowhere after finalization; only an approved redacted marker or digest may remain. Gate B later repeats this control with the approved credential posture. Do not implement Claude settings injection, API routing, or a Compose sidecar in this foundation handoff. A later human-approved Gate B prompt must supply the concrete external-proxy API profile; the executor must not invent one.

## Runtime payload boundary

For the first D7Y case, the agent payload is exactly:

- `SKILL.md` for the treatment arm only;
- `initiatives/README.md`;
- `d7y`;
- `scripts/check-initiatives.py`;
- declared case fixture files.

The agent image must not contain the source checkout, eval definitions, expected outcomes, assertions, benchmark summaries, private grading wrappers, or harness control files. `scripts/check-initiatives.py` is a public D7Y capability checker deliberately included in the payload; it is not the eval grader. Build private expected outcomes, assertions, and grader/checker wrappers into the separate verifier environment. Transfer only allowlisted agent outputs and evidence to that verifier.

Commit the exact skill/task inputs before behavioral execution. Verify their bytes match that D7Y source commit, then record the D7Y source commit separately from Harbor's skill content digest. Missing either invalidates treatment provenance.

## Scope

Implement only the first qualification slice:

1. A disposable Harbor isolation task using Harbor's built-in Oracle with a synthetic solution script for active read, write, environment, network, timeout, and artifact probes; use no-op only for absent-action or missing-artifact controls.
2. A disposable skill treatment pair with and without skill injection.
3. Harbor task/verifier/network/artifact qualification without Claude credentials.
4. Task/provenance normalization needed by D7Y; do not replace the D7Y schema or implement maturity scoring.

Do not implement Phases 2A–8 of the governing plan in this handoff. Do not reuse `evals/run_eval.py`, the frozen branch, its parser fixtures, or its host-side settings/plugin wrapper.

## Required verification

Run and report exact results for:

- Harbor installation and version check;
- Docker daemon access;
- namespaced Docker resource creation, inspection, and cleanup ownership; never mount the Docker socket into a trial container;
- effective UID and non-root verification;
- environment-build, agent-setup, agent-run, and verifier timeout behavior;
- CPU and memory enforcement modes plus an over-limit storage write test;
- Docker storage enforcement and network-controller capability;
- positive and negative isolation probes;
- separate verifier with private checker material;
- required-artifact absence and fail-closed behavior;
- baseline/treatment skill provenance and leakage checks;
- `environment.env` interpolation with a non-secret sentinel;
- deterministic public interpolation-canary scan across task files, manifests, logs, and artifacts;
- separate fake sensitive-looking trial-agent canary/redaction scan after Harbor finalization, including quarantine/deletion on raw bytes and fail-closed handling for unreadable files;
- `git diff --check`;
- `python3 evals/validate_skill_evals.py`;
- `./d7y validate` where the implementation touches repository validation surfaces.

Classify all failures with the canonical identifiers: `environment_error`, `pair_error`, `agent_error`, `evidence_error`, `verifier_error`, `assertion_fail`, or `ungradable`.

If prerequisites fail, make only the smallest safe documentation or capability-record adjustment needed to report the blocker, then stop. Do not weaken isolation, use Harbor's public network default, import unreviewed host state, use real Harbor-trial Claude credentials, or claim a qualified run. A storage over-limit failure or unsupported quota is `foundation-blocked`, not `foundation-qualified`.

## Completion

Return with a clean assigned worktree, cohesive commit(s), implementation feedback appended to the governing plan, exact verification results, deviations, and residual risks. This foundation handoff must not claim Claude/API qualification or update an accepted `benchmark.json`; keep skill maturity provisional.
