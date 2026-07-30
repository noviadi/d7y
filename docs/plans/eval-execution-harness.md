---
title: Harbor-Native Skill Eval Execution Foundation
type: feat
status: todo
createdAt: 2026-07-30
updatedAt: 2026-07-30
---

# Harbor-Native Skill Eval Execution Foundation

## Summary

Build the smallest Harbor-backed execution path that can produce honest,
repeatable D7Y skill comparisons on local Docker.

The foundation is successful when:

- a committed synthetic D7Y case runs in a fresh Harbor container;
- the same case runs without and with one immutable target skill;
- both arms use the same model, task, image, tools, resources, network, and API
  route;
- private assertions run in a separate verifier environment;
- required artifacts, trajectories, provenance, and failures remain
  inspectable;
- supported process, outcome, quality, and efficiency evidence can be compared
  even when invocation telemetry is unavailable;
- repeated positive and negative cases expose behavioral variation without
  implying premature maturity.

This plan does not certify local Docker as an adversarial sandbox. Hard storage
quotas, exact upstream route attestation, and broader provider-hardening probes
are separate claim-dependent work.

## Problem framing

D7Y has a canonical skill-evaluation contract and two provisional suites, but
no accepted behavioral execution path. The frozen host-side Claude wrapper
attempt reimplemented isolation, configuration, process management, event
parsing, staging, and grading. The replacement Harbor plan then made a dedicated
XFS/project-quota Docker daemon, an enforcing host firewall, external proxy
route evidence, and extensive canaries prerequisites for the first useful run.

That joined three different questions into one gate:

1. Can Harbor execute the task and preserve evidence?
2. Is the baseline/treatment comparison valid?
3. Is the provider hardened against hostile workloads and infrastructure abuse?

This plan answers the first two. The third is required only when a case or claim
depends on the additional control.

The primary uncertainty is:

> Can one committed D7Y suite run through Harbor on local Docker and produce a
> reproducible, explainable difference between no-skill and with-skill trials?

The harness should spend its complexity budget on that comparison, not on
certifying controls that bounded synthetic cases do not require.

## Governing decisions

### Eval validity is claim-scoped

Local Docker is the first execution provider. A result is valid for the evidence
dimensions whose required controls were enforced. Unsupported capabilities are
recorded as limitations, not silently treated as present and not promoted into
universal blockers.

For the bounded synthetic cases in this plan:

- CPU, memory, timeout, mount, network, pair, verifier, artifact, and provenance
  controls are required;
- Harbor-managed writable-layer storage enforcement is not required;
- `storage_mb` may be retained as declared task metadata, but the result must
  state that local Docker does not enforce it through Harbor;
- no hardened-provider, hostile-workload, or storage-isolation claim may be
  made.

If a later case can materially exhaust disk or execute adversarial payloads,
either qualify a storage-capable provider or provision and test an external
quota mechanism for that case.

### Harbor owns execution; D7Y owns meaning

Harbor owns container lifecycle, agent execution, network and supported resource
controls, skill injection, artifact transfer, trajectories, and verifier
isolation.

D7Y owns:

- conversion of committed eval cases into Harbor tasks;
- baseline/treatment parity checks;
- D7Y assertion and failure semantics;
- independent D7Y checkers;
- evidence normalization and comparison;
- quality review and maturity interpretation.

The adapter must not reimplement Harbor's process lifecycle, container
isolation, agent protocol, or result viewer.

### Pair the treatment, not the prompt

Each case produces matched trials:

```text
same case, prompt, fixtures, image, agent, model, tools, permissions,
API route, network, resources, timeout, and verifier
├── baseline: no target skill
└── treatment: target skill at an immutable content digest and source commit
```

Do not wrap the treatment prompt with skill instructions or grading hints.
Harbor skill injection is the only intended treatment difference.

### Separate the verifier

Use Harbor's separate verifier environment. The agent receives only its task
instruction, declared fixtures, public D7Y runtime capabilities, and the target
skill in the treatment arm.

Private expected outcomes, assertions, grader wrappers, and harness controls
belong in the verifier image. The verifier receives only declared outputs and
explicitly requested trace artifacts. Because Harbor artifact collection is
best-effort, the verifier or adapter must fail closed when a required artifact
is missing from the collection manifest.

### Keep Claude configuration task-scoped

Do not read or mount the host user's `~/.claude/settings.json`. Use a prebuilt,
digest-recorded agent image containing the pinned Claude Code version so normal
trials do not install the agent at runtime.

Resolve a named API profile for the job. It may describe a direct official
endpoint or an approved proxy and must contain:

- the agent-visible endpoint identity;
- requested model;
- allowlisted runtime environment key names;
- credential source by key name, never value;
- exact Harbor runtime allowed hosts;
- a redacted configuration digest.

Before Phase 0 can be accepted, a human supplies the exact non-secret values and
the executor commits the resolved profile at
`evals/harbor/profiles/claude-primary.json`. The credential value remains
external; the profile records only its environment key name. Amp reviews and
integrates that artifact before a credentialed phase may begin.

Pass credentials opaquely through trial-scoped agent environment inputs. The
runner may deliver the value to the trial agent process without displaying or
persisting it; the executor must not inspect it, and no verifier or other
process may receive it. Record effective model/provider evidence when the
endpoint exposes it; otherwise mark it unavailable. Independent proxy logs or
exact upstream attestation are required only for claims that depend on upstream
identity.

Credentialed trials use three independent bounds:

- the exact number of Harbor rollouts authorized by the phase;
- `max_turns = 24` for each Claude Code rollout;
- `max_budget_usd = 3.00` for each rollout, in addition to the 600-second agent
  timeout.

The aggregate worst-case budgets are USD 6 for Phase 2, USD 18 for Phase 3, and
USD 54 for Phase 4. Human approval is required before each phase. If the selected
Harbor/Claude integration cannot enforce and record the per-rollout turn and
budget ceilings, stop before a live trial and revise the approved profile or
plan explicitly. A rollout limit is not represented as a model-request count.

### Invocation is one evidence dimension

Skill availability in the treatment does not prove invocation. Inspect the
actual Harbor Claude trajectory before defining an invocation parser.

If a stable runtime-owned target-specific event exists, grade invocation from
that event. If it does not, mark invocation assertions `ungradable` and continue
grading supported process, outcome, quality, and efficiency dimensions. Do not
infer invocation from the final response or a successful artifact. Missing
invocation evidence blocks invocation-dependent maturity claims, not the
execution foundation.

### Prefer evidence over a composite score

Keep these result layers separate:

1. environment validity;
2. baseline/treatment pair validity;
3. treatment availability and invocation evidence;
4. process checks;
5. outcome checks;
6. quality or human review;
7. efficiency observations;
8. provider limitations.

Harbor's reward file may summarize verifier success, but it is not D7Y's
canonical result. Every D7Y pass cites concrete retained evidence.

## Scope

### In scope

- Harbor `0.20.0`, invoked from a pinned non-global installation.
- Local Docker as the first execution provider.
- One digest-recorded Docker agent image with a pinned Claude Code version.
- One disposable Harbor Oracle smoke task.
- A thin case-to-task and result-normalization adapter.
- The three current `starting-initiatives` cases.
- Matched baseline and treatment jobs.
- Separate verifier images with private deterministic grading material.
- Explicit environment, agent, and verifier network policies.
- Trial-scoped credential injection with key-name provenance.
- Skill digest and D7Y source-commit provenance.
- Required artifact and trajectory retention.
- Canonical D7Y failure identifiers.
- One initial pass of every case followed by three trials per arm and case for
  the first comparative evidence set.
- Structured rubric or human review for declared quality assertions.
- Synthetic fixtures and isolated eval workspaces only.

### Deferred

- Hard local-Docker writable-layer quotas or a dedicated XFS Docker daemon.
- Adversarial provider or sandbox certification.
- Mandatory external proxy topology and independent route logs.
- A second Harbor provider.
- A generalized executor interface.
- A top-level `d7y eval` product command.
- Arbitrary skill-local executable graders.
- Automated judge selection or reward optimization.
- A service, database, scheduler, or web UI.
- Automatic retries, maturity promotion, or benchmark acceptance.
- Cross-model, cross-provider, multimodal, or long-horizon evaluation.
- Automated skill evolution.

## Target architecture

```text
committed evals.json, fixtures, and source revision
                         │
                         ▼
                D7Y Harbor task builder
                         │
              one immutable case definition
                         │
              ┌──────────┴──────────┐
              ▼                     ▼
        baseline Harbor job   treatment Harbor job
        no target skill       --skill <target>
              │                     │
              └──────────┬──────────┘
                         ▼
              separate Harbor verifier
                         │
                         ▼
           raw Harbor evidence + D7Y checks
                         │
                         ▼
               factual paired comparison
```

The baseline and treatment may be separate Harbor jobs because skill injection
is job configuration. The adapter must compare their resolved task and job
configuration and reject a pair when anything other than the declared treatment
and run identity differs.

## Minimal execution contract

### Prerequisites

Before implementation or behavioral execution, prove:

```text
uvx --from harbor==0.20.0 harbor --version
docker --version
docker info
python3 --version
```

Harbor package and Docker image acquisition may use a reviewed bootstrap network
posture. That implementation-executor posture is not a Harbor trial control and
must not be copied into task evidence.

The only current host blocker for local execution is failure to access a working
Docker daemon or to acquire the pinned Harbor package and required images. A
missing XFS quota data root or host firewall does not block this bounded
foundation.

### Provider and image posture

Record:

- Harbor version;
- Docker client and server versions;
- Docker context and provider type;
- agent and verifier image digests;
- Claude Code version;
- CPU and memory enforcement modes;
- declared storage and effective storage support;
- agent and verifier users;
- environment, agent, and verifier network policies;
- timeouts.

Use initial limits of 2 CPUs, 4096 MiB memory, 600 seconds for the agent, and 120
seconds for the verifier unless observed behavior justifies a smaller value.
Use explicit CPU and memory limit enforcement. Record local Docker storage
enforcement as unsupported rather than probing a limit the provider does not
claim to enforce.

### Network and secrets

Prefer a prebuilt image so environment startup does not need package network
access. Use:

- `no-network` for the environment baseline where the selected Harbor Docker
  network controller supports the required agent-phase override;
- an agent-phase allowlist containing only the resolved API-profile hosts;
- `no-network` for the verifier;
- trial-scoped agent environment values for credentials;
- no credentials in task files, images, prompts, manifests, or verifier inputs.

Run one synthetic sensitive-value canary when qualifying a materially new
Harbor/Claude/image configuration. Scan the textual job configuration, logs,
trajectory, and declared artifacts for the canary after finalization. This is an
integration qualification, not a per-case grading step. Real credential values
must never be used as scan tokens or retained as evidence.

### Runtime payload

For `starting-initiatives`, the agent receives only:

- the case instruction;
- its declared synthetic workspace and fixtures;
- `initiatives/README.md`;
- `d7y`;
- `scripts/check-initiatives.py`;
- `SKILL.md` and its required public references in the treatment arm.

Do not stage eval definitions, expected outcomes, assertions, grader source,
benchmark summaries, plan files, or the source checkout.

The verifier contains the private wrapper and its own staged copy of the public
initiative checker. It independently validates the declared output without
repairing it.

### Provenance and parity

Commit the exact case, fixture, skill, and task-builder inputs before behavioral
execution. For a local Harbor skill, record:

- Harbor's content digest;
- the D7Y source commit;
- a check that the injected skill bytes match that commit.

Every phase that creates or changes executable inputs must make a clean pre-run
commit before its first Harbor behavioral trial and record that commit in every
trial manifest. Runtime execution may append feedback in a later commit, but it
must not change source after the first trial. A discovered implementation defect
returns for a separate correction handoff and a new iteration; evidence is never
attributed to code committed only after the run.

The adapter compares the resolved baseline and treatment configurations. A
difference in image, task, prompt, fixture, agent, model, API profile, tools,
permissions, network, resources, timeout, or verifier is `pair_error`.

### Evidence retention

Retain Harbor's raw job and trial outputs. Normalize only:

```text
evals/runs/<skill>/iteration-<N>/
├── manifest.json
├── baseline/
│   ├── harbor-result.json
│   ├── agent/
│   ├── artifacts/
│   └── verifier/
├── with-skill/
│   ├── harbor-result.json
│   ├── agent/
│   ├── artifacts/
│   └── verifier/
├── checks.json
└── summary.md
```

Raw and normalized evidence required by a later phase lives outside Git
worktrees at:

```text
/home/noviadi/Developments/discovery/d7y-eval-evidence/
└── eval-execution-harness/
    └── <phase-execution-slug>/
```

Each phase receives one exact evidence directory. It must be absent before the
phase starts, have no symlink in an existing path component, be created
user-owned with mode `0700`, and remain immutable after its inventory is
finalized. The phase records its absolute path, file inventory, SHA-256 hashes,
owner, mode, and finalization time in plan feedback. A successor verifies that
inventory before use. Do not delete evidence until the plan is integrated,
closed, and the human explicitly authorizes cleanup. The evidence store must
contain no credential values.

The manifest records case and source revisions, Harbor/provider/image/agent
identity, requested model and route profile, effective model/provider when
available, tools, permissions, network, resources, users, timeouts, run order,
skill digest, and provider limitations.

Missing telemetry is `unavailable`, not zero. Missing required artifacts are
`evidence_error` or `ungradable`, never an implicit pass. Preserve partial
evidence for timeouts and crashes.

Human quality dispositions are a separate acceptance layer. Raw and normalized
run evidence retains the corresponding assertions as `ungradable` with stable
trial and assertion identifiers. Amp and the human record accepted dispositions
against those identifiers in plan feedback after reviewing the immutable
quality packet. Regeneration reproduces the evidence-only summaries and verifies
the disposition references separately; it does not silently fold manual
judgment into machine-derived output.

## Phase prompt map

Each phase has its own concrete draft prompt:

| Phase | Prompt | Activation gate |
|---|---|---|
| 0 | `docs/prompts/eval-execution-harness.phase-0-executable-posture.md` | This plan, canon, and all six prompts are committed on `main`; a human supplies the exact non-secret API-profile inputs. |
| 1 | `docs/prompts/eval-execution-harness.phase-1-harbor-smoke.md` | Phase 0 is reviewed, integrated, and its exact inputs are recorded. |
| 2 | `docs/prompts/eval-execution-harness.phase-2-positive-pair.md` | Phase 1 smoke evidence is accepted and a human approves the API profile and bounded spend. |
| 3 | `docs/prompts/eval-execution-harness.phase-3-current-suite.md` | Phase 2 pair and trajectory contract are reviewed and integrated. |
| 4 | `docs/prompts/eval-execution-harness.phase-4-repeated-comparison.md` | Phase 3 six-trial case set and human quality dispositions are accepted. |
| 5 | `docs/prompts/eval-execution-harness.phase-5-reconcile-foundation.md` | Phase 4 evidence inventory and human quality dispositions are accepted and available without rerunning model trials. |

Prompts remain `status: draft` until their activation gate is satisfied. Before
each handoff, commit that prompt as `status: committed` on `main`, create its
exact branch and sibling worktree from the launcher-recorded base, and execute
only that phase. Integrate phases serially. A later phase must not infer missing
predecessor evidence or repair an earlier phase silently.

## Implementation sequence

### Phase 0 — Establish the executable posture

Freeze the historical `work/eval-execution-harness` host-wrapper branch. Do not
reuse its process runner or configuration parser.

The existing `docs/prompts/eval-execution-harness.harbor-qualification.md` is
`status: superseded` and remains non-executable historical evidence for the
rejected qualification posture. Do not edit or execute it.

Resolve the pinned Harbor invocation, Docker daemon access, agent and verifier
images, Claude Code version, API profile, resource limits, network policies, and
runtime payload. Keep secrets external to Git.

**Exit evidence:** the implementation handoff names a working Docker context,
obtainable pinned dependencies and images, and a non-secret API profile. Docker
unavailability is `environment_error`; missing hard storage quota is a recorded
limitation.

### Phase 1 — Run one Harbor-native smoke task

Use Harbor's Oracle and a synthetic solution script to prove:

- container startup and fresh teardown;
- absence of host checkout, home, and Docker socket mounts;
- explicit environment and verifier network behavior;
- CPU, memory, and timeout behavior;
- separate verifier isolation;
- declared artifact transfer;
- required-artifact failure;
- retention of non-zero exit and timeout diagnostics;
- one fake credential-canary scan.

Include deliberately broken variants only for the controls whose failure
classification the adapter must understand.

**Exit evidence:** one provider capability record with positive observations,
negative controls, and explicit unsupported capabilities.

### Phase 2 — Build the thin adapter and one positive pair

Generate a Harbor task from `start-new-initiative`. Run baseline and treatment
with the same resolved configuration, adding only the target skill to treatment.

The adapter must:

- verify task and job parity;
- verify skill digest and source provenance;
- validate the artifact collection manifest;
- preserve raw Harbor outputs;
- run the private verifier and public D7Y checker;
- emit canonical D7Y failure classes;
- regenerate `checks.json` and `summary.md` from retained evidence.

Inspect the actual Claude trajectory and document which invocation, command,
model, and usage fields may be stable enough to grade. Do not add a new
trajectory-derived source check after the Phase 2 trials. Amp reviews the
candidate contract; Phase 3 may implement an accepted check before its own
pre-run source commit.

**Exit evidence:** one inspectable positive pair. Unsupported invocation remains
`ungradable`; supported outcome and process checks still run.

### Phase 3 — Run the complete current case set

Add `resume-same-initiative` and `casual-brainstorm` without changing the runner
architecture. Before the pre-run commit, implement only a trajectory check that
Amp accepted from Phase 2 evidence; otherwise keep invocation `ungradable`. Run
every case once in both arms.

Verify:

- creation and resume semantics independently;
- no duplicate initiative for the resume case;
- no initiative creation for the negative control;
- target invocation or explicit `ungradable` status;
- rubric or human disposition for required quality assertions;
- no assertion is inferred from a composite reward.

**Exit evidence:** six trials with per-case, per-arm evidence and no silent
unsupported assertions.

### Phase 4 — Produce the first repeated comparison

Run three trials per arm and case using the same configuration, for eighteen
trials total. Alternate or otherwise record arm order so temporal drift is
visible. Do not silently retry or replace failed trials.

Report:

- required assertion pass, fail, error, and ungradable counts;
- per-case baseline/treatment outcomes;
- invocation false positives and false negatives when observable;
- duration, token, tool, and retry observations when available;
- rubric or human quality results;
- environment, pair, agent, evidence, and verifier failures;
- provider and telemetry limitations.

Use descriptive counts and paired observations. Do not claim statistical
stability, create an accepted `benchmark.json`, or recommend maturity from this
small set.

**Exit evidence:** the first repeatable comparative evidence set and a factual
summary that distinguishes behavior from infrastructure failures.

### Phase 5 — Reconcile evidence and close the foundation

Update only checks justified by observed stable traces and artifacts. Remove
checks that pass equally in both arms and do not demonstrate value. Regenerate
machine-derived outputs into Phase 5's own evidence directory; keep accepted
human dispositions in plan feedback as a separately verified review layer.
Document unsupported telemetry and any provider-specific limitation in canon or
the binding record that owns it.

**Exit evidence:** the task builder, Harbor tasks, checks, and summaries can be
reproduced from committed inputs; the source checkout remains unchanged by eval
runs; and all required verification passes.

## Failure semantics

Use the canonical identifiers:

- `environment_error` — a capability required by this case or execution failed;
- `pair_error` — arm configurations differ beyond the declared treatment or
  treatment material leaked;
- `agent_error` — timeout, crash, malformed result, or agent execution failure;
- `evidence_error` — required trace, artifact, provenance, or telemetry is
  absent or malformed;
- `verifier_error` — the separate verifier could not execute or interpret its
  inputs;
- `assertion_fail` — valid evidence shows a required behavior did not occur;
- `ungradable` — the assertion requires unavailable telemetry or unresolved
  judgment.

An unsupported provider capability is an `environment_error` only when the case
or claim requires it. Otherwise record it as a limitation. A rerun is a new
trial with new provenance.

## Separate provider-hardening roadmap

Do not add these controls to the foundation unless a concrete threat model
requires them:

- hard writable-layer storage quotas and over-limit probes;
- a dedicated Docker daemon or alternate storage-capable provider;
- adversarial network bypass tests;
- exhaustive secret scanning across arbitrary binary artifacts;
- enforced non-root execution for hostile payloads;
- proxy sidecars and independently controlled route logs;
- host kernel, firewall, cgroup, and daemon certification;
- cross-provider portability claims.

When needed, qualify them once per materially distinct
Harbor/provider/image/network configuration and state which eval claims depend
on them.

## Verification

Implementation verification must include:

1. `python3 evals/validate_skill_evals.py`;
2. `./d7y validate`;
3. focused adapter and task-builder tests;
4. Harbor task parsing with the pinned release;
5. the Phase 1 smoke task and negative controls;
6. one positive matched pair;
7. all current positive and negative cases;
8. the repeated comparison;
9. summary regeneration from retained artifacts;
10. `git diff --check` and a clean task worktree.

Report static validation, deterministic tests, Harbor smoke evidence,
single-pair evidence, repeated comparative evidence, and human or rubric review
as distinct facts.

## Current prerequisite evidence

The 2026-07-30 attempt on `work/harbor-execution-prerequisites` stopped before
Harbor execution:

- Docker client access existed, but the executor could not access
  `/var/run/docker.sock`;
- the visible Docker data path was ext4 rather than a dedicated XFS/project-quota
  data root;
- no reviewed host firewall enforced the launcher's bootstrap declaration;
- Harbor packages and images were not acquired;
- no Harbor smoke task or Claude trial ran.

Under this revised plan, Docker daemon access remains a real prerequisite.
Dedicated XFS quotas and host-firewall certification are not prerequisites for
the bounded foundation. The launcher network-posture work is implementation
handoff infrastructure and must remain separate from Harbor trial policy.

## Sources

- `AGENTS.md` — development constitution and evidence boundaries.
- `docs/discovery-workbench.md` — thin-harness, fat-skills architecture.
- `docs/discovery-workbench-principles.md` — uncertainty and evidence
  principles.
- `docs/skill-evaluations.md` — canonical evaluation and claim semantics.
- `evals/skill-evals.schema.json` — authored suite schema.
- `skills/starting-initiatives/evals/evals.json` — first executable suite.
- `scripts/check-initiatives.py` — public independent checker capability.
- [Harbor tasks](https://www.harborframework.com/docs/tasks) — task,
  network, resource, artifact, and separate-verifier configuration.
- [Harbor evals](https://www.harborframework.com/docs/run-jobs/run-evals) —
  jobs, trials, trajectories, and result layout.
- [Harbor skills](https://www.harborframework.com/docs/run-jobs/skills) —
  skill injection and provenance.
- [Harbor `v0.20.0` Claude Code adapter](https://github.com/harbor-framework/harbor/blob/v0.20.0/src/harbor/agents/installed/claude_code.py)
  — pinned `max_turns` and `max_budget_usd` CLI mappings and trajectory support.
- [Harbor artifact collection](https://www.harborframework.com/docs/run-jobs/results-and-artifacts)
  — collection manifest and best-effort behavior.
- [Harbor resource management](https://www.harborframework.com/docs/tasks/managing-resources)
  — provider-specific enforcement support.
- [OpenAI — Testing Agent Skills Systematically with Evals](https://developers.openai.com/blog/eval-skills)
  — small targeted cases, trace-based checks, and progressive grading.

## Completion boundary

This plan is complete when Phases 0–5 have produced:

- one accepted Harbor capability smoke record;
- a reproducible builder and thin adapter;
- all three `starting-initiatives` cases in both arms;
- three retained trials per arm and case;
- deterministic, rubric, and human dispositions where declared;
- explicit unsupported invocation or provider limitations;
- regenerable factual summaries;
- no maturity promotion or accepted benchmark claim.

The foundation proves a bounded Harbor-on-Docker evaluation path. It does not
prove hardened sandboxing, cross-provider portability, statistical stability,
or that a skill is `evaluated`.
