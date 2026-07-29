---
title: Harbor Qualification for Skill Eval Foundation
type: prompt
status: ready
createdAt: 2026-07-30
updatedAt: 2026-07-30
---

# Harbor Qualification for Skill Eval Foundation

You are implementing the first Harbor qualification slice for D7Y's progressive skill-eval foundation.

## Handoff payload

- Governing plan: `docs/plans/eval-execution-harness.md`
- Base commit: `c9f371a`
- Assigned branch: `work/eval-execution-harness-harbor`
- Assigned worktree: `/home/noviadi/Developments/discovery/d7y-worktrees/eval-execution-harness-harbor`
- Commit authority: explicitly granted on the assigned branch only
- Executor lifecycle authority: no rebase, merge, push, worktree removal, or branch deletion
- Frozen branch: `/home/noviadi/Developments/discovery/d7y-worktrees/eval-execution-harness` is historical and must not be reused

## First stop: prerequisites

Before editing implementation files, run and record:

```text
uv tool install harbor==0.6.5
harbor --version
docker --version
docker info
python3 --version
```

Use Harbor `0.6.5` and local Docker only. If Harbor cannot be installed, `harbor --version` is not `0.6.5`, or `docker info` cannot access a daemon, stop and report `environment_error`; do not substitute the old wrapper or another provider.

The initial fixed task limits are setup 600 seconds, agent 600 seconds, verifier 120 seconds, 2 CPUs, 4096 MiB memory, and 10240 MiB storage. Configure explicit non-public network policies for setup, agent, and verifier. Record the exact Claude authentication mechanism and imported key names, never values. If Claude cannot operate under an explicit allowlist, stop and return the network decision.

Do not read or mount the host user's `~/.claude/settings.json`. Build a task-scoped Claude settings bundle with only approved tool, MCP, instruction, and persistence controls. For this qualification, use one named external HTTPS proxy/custom-endpoint API profile. The profile must specify the agent-visible endpoint, Harbor host allowlist, runtime secret/key names, upstream mapping, and redacted configuration digests. Inject endpoint/proxy and authentication values through an explicit Harbor runtime environment allowlist; Harbor's `${HOST_VAR}` task interpolation must be verified at runtime, and secret values must not appear in `task.toml`, Dockerfiles, prompts, logs, or artifacts. Record route evidence from the endpoint/proxy boundary and record requested model separately from effective model/provider. Do not claim a Compose sidecar provides per-service egress isolation; that is follow-on work.

Qualify the external allowlisted HTTPS proxy/custom endpoint first. Record endpoint/proxy identity and configuration digest, upstream provider/model mapping, and imported key names without values. A requested `claude-sonnet-5` does not establish that model was used; fail closed if route evidence cannot be observed. Do not implement the Docker Compose sidecar topology in this handoff.

## Runtime payload boundary

For the first D7Y case, the agent payload is exactly:

- `SKILL.md` for the treatment arm only;
- `initiatives/README.md`;
- `d7y`;
- `scripts/check-initiatives.py`;
- declared case fixture files.

The agent image must not contain the source checkout, eval definitions, expected outcomes, assertions, grader/checker source, benchmark summaries, or harness controls. Build private expected outcomes, assertions, and checker code into the separate verifier environment. Transfer only allowlisted agent outputs and evidence to that verifier.

Record both the target skill content digest and resolved source commit. Missing either invalidates treatment provenance.

## Scope

Implement only the first qualification slice:

1. A disposable Harbor isolation task with positive and deliberately broken probes.
2. A disposable skill treatment pair with and without skill injection.
3. Harbor Claude Code integration qualification for task-scoped settings, API-profile injection, route evidence, requested versus effective model/provider, availability, invocation evidence, final response, tool activity, timeout, and failure capture.
4. Task/provenance normalization needed by D7Y; do not replace the D7Y schema or implement maturity scoring.

Do not implement Phases 4–8 of the governing plan in this handoff. Do not reuse `evals/run_eval.py`, the frozen branch, its parser fixtures, or its host-side settings/plugin wrapper.

## Required verification

Run and report exact results for:

- Harbor installation and version check;
- Docker daemon access;
- positive and negative isolation probes;
- separate verifier with private checker material;
- required-artifact absence and fail-closed behavior;
- baseline/treatment skill provenance and leakage checks;
- task-scoped Claude settings, explicit API-profile injection, route/proxy evidence, and requested/effective model checks;
- Claude Code non-interactive execution and timeout/error capture;
- `git diff --check`;
- `python3 evals/validate_skill_evals.py`;
- `./d7y validate` where the implementation touches repository validation surfaces.

Classify all failures with the canonical identifiers: `environment_error`, `pair_error`, `agent_error`, `evidence_error`, `verifier_error`, `assertion_fail`, or `ungradable`.

If prerequisites fail, make only the smallest safe documentation or capability-record adjustment needed to report the blocker, then stop. Do not weaken isolation, use Harbor's public network default, import unreviewed host state, or claim a qualified run.

## Completion

Return with a clean assigned worktree, cohesive commit(s), implementation feedback appended to the governing plan, exact verification results, deviations, and residual risks. Keep skill maturity provisional. Do not update an accepted `benchmark.json`.
