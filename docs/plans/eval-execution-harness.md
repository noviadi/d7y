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

## Phase 0 implementation feedback

Executor: Claude Code. Branch: `work/eval-harness-executable-posture`. Scope:
Phase 0 executable posture only. No Harbor trial, smoke task, case adapter,
grader, or comparison runner was run or built. The committed profile carries
only non-secret values and the credential key name; no credential value was
read, injected, tested, or printed.

### Files changed

New files under `evals/harbor/` only:

- `README.md`, `.gitignore`, `posture.json` (build record);
- `profiles/claude-primary.json` (approved non-secret API profile);
- `config/execution-posture.json` (Harbor resource/network/timeout envelope);
- `images/agent/Dockerfile` + `.dockerignore`, `images/verifier/Dockerfile` +
  `.dockerignore`;
- `payloads/starting-initiatives.json` (runtime payload manifest);
- `scripts/posture.py` (validator + digest logic), `scripts/test_posture.py`
  (26 focused tests, incl. duplicate-source rejection), `scripts/scan_image.py`
  (image canary scanner, fails closed), `scripts/test_scan_image.py` (14
  scanner fail-closed tests; no Docker daemon required).

> Reconciled by the `phase-0-review-corrections` handoff (see _Review
> corrections applied_ below): the scanner now fails closed, the recorded
> Claude Code binary SHA-256 is enforced as a build input and verified against
> the installed binary, installer-generated identity state is removed from the
> retained agent image, duplicate payload sources are rejected, reproducibility
> is stated precisely, and the original `hello-world` daemon probe is recorded
> as the sole execution deviation. Digests, layer count, test counts, retained
> resources, deviations, and limitations below reflect that rebuild.

### Exact versions and digests

- Harbor: `0.20.0` via `uvx --from harbor==0.20.0` (pinned, non-global).
- Python: `3.14.6`; `uv` `0.11.31`.
- Docker client/server: `29.6.2`; storage `overlay2` on `ext4` (`extfs`);
  cgroup v2 (systemd); kernel `7.1.4-arch1-1`; Arch Linux; host `archetude`.
- Claude Code: `2.1.218`, commit `bce61b433bc397ce68686368abd12f545b0a013a`,
  build date `2026-07-22T18:42:19Z`, linux-x64 binary checksum
  `e12071751a9336b8af1012c103358ff04ac18f9aaff4a738cff7ba5cdfaf63f2`
  (enforced as Dockerfile `ARG CLAUDE_CODE_BINARY_SHA256` and verified against
  the installed resolved binary via `sha256sum -c` during the build; the build
  step printed `<...>/2.1.218: OK`), installer bootstrap sha256
  `cde4f1702d3b1695f92b73d26888364e17bca476e17f0fd676484c951d36c125`.
  npm package `@anthropic-ai/claude-code@2.1.218` recorded for traceability
  (shasum `018479d04265ca1b03b87060ca459d14419fac1f`); the image installs via
  the native installer, matching Harbor's own path.
- Base image: `python:3.12-slim`, manifest-list digest
  `sha256:57cd7c3a7a273101a6485ba99423ee568157882804b1124b4dd04266317710de`,
  amd64 digest `sha256:cab2dbf575e971934a81e4622f5aba17aa7929719bd7e31033a3a83b97fd0464`
  (digest-pinned in both Dockerfiles), over `debian:trixie-slim`.
- Agent image `d7y-eval-phase0-agent:2.1.218`:
  `sha256:34b394a9bb9cd961dec70513bce375a5acb6203775a7b9567d26cdf75c01e5c1`
  (user `agent` uid 1000; 11 layers; 273 MB Claude layer; no `COPY`/`ADD`/secret
  mounts; env keys: PATH, LANG, GPG_KEY, PYTHON_VERSION, PYTHON_SHA256,
  DEBIAN_FRONTEND, PYTHONDONTWRITEBYTECODE, HOME; installer identity state
  `/home/agent/.claude` and `/home/agent/.claude.json` removed and asserted
  absent).
- Verifier image `d7y-eval-phase0-verifier:phase0`:
  `sha256:35b47fbb2fe1a4b01e9d10b6683a5e03e1e15aba4f5b9648d204186267023ca3`
  (user `verifier` uid 1001; no `COPY`/`ADD`/secret mounts). Recipe unchanged
  from the initial build; the different digest is the no-cache rebuild artifact
  (see _Reproducibility_).

### Docker context

`default` context, endpoint `unix:///var/run/docker.sock`. Daemon access
verified. Backing filesystem is ext4 on `/dev/mapper/home`; no XFS/project-quota
data root (recorded limitation, not a blocker). Linked-worktree port/cache
isolation does not apply.

Daemon-resource deviation (original Phase 0 execution; recorded here truthfully,
not repeated in the correction rebuild): a single disposable, unprefixed
`docker run --rm hello-world` probe was run once to confirm daemon access
before the prefixed image work. The `hello-world` container was removed by
`--rm`; the locally-cached `hello-world` image is a stock library image, not a
D7Y resource, and was left in place. Every other daemon resource D7Y created is
prefixed `d7y-eval-phase0-`.

### API-profile status

Committed and validated at `evals/harbor/profiles/claude-primary.json`. It
records requested model `claude-sonnet-5`, intentional z.ai proxy endpoint
`https://api.z.ai/api/anthropic`, exact allowed host `api.z.ai`, the five
allowlisted non-secret runtime values, the credential key name
`ANTHROPIC_AUTH_TOKEN` (value external), exclusion of the host Opus/Haiku
defaults, and the redacted configuration digest
`3088a1cae0ff9b0d1824c68f744b19402dfda1698cb9d096dcefe7e367ea0694`. Effective
model/provider remain `unavailable` until runtime evidence exists.

### Pre-build source commit and final build

Pre-build source commit: `39fab1b` (the corrected executable inputs: fail-closed
scanner, enforced binary checksum, identity-state removal, duplicate-source
rejection, and tests). Both images were rebuilt `--no-cache` from that commit:
agent `sha256:34b394a9…`, verifier `sha256:35b47fbb…`.

### Reproducibility

"Reproducible" here means **pinned content inputs plus a recorded, verifiable
retained image identity** — not byte-for-byte reproducibility across rebuilds.

What is pinned: the base image by amd64 manifest digest; the Claude Code version
by `ARG`; the installer bootstrap by SHA-256; and the installed linux-x64 binary
by the recorded SHA-256, enforced against the resolved binary during the build.

What is not pinned or not stable: Debian package resolution is **not**
snapshot-pinned (`apt-get update` resolves the current trixie set at build
time), and `docker build` image digests are **not** byte-for-byte reproducible
across independent no-cache rebuilds — each `RUN` layer is stamped with a
build-time creation timestamp. This correction demonstrates it directly: the
verifier recipe was unchanged and its base is digest-pinned, yet the no-cache
rebuild produced `sha256:35b47fbb…` versus the prior `sha256:ae7a327a…`.

The initial Phase 0 record's "digests identical across builds" observation held
only because that second build reused cached layers (same timestamps); a
cache-backed rebuild is not independent reproducibility and is no longer cited
as proof. Any future rebuild that yields a different digest must be rescanned
(real scanner + canary, both fail-closed) and re-recorded before use, and the
agent binary checksum gate must still pass.

### Verification results

- `uvx --from harbor==0.20.0 harbor --version` → `0.20.0` (pass).
- `docker --version` / `docker info` → client/server `29.6.2`, overlay2/ext4,
  default context (pass).
- No-cache image build → both images rebuilt `--no-cache` from `39fab1b`:
  agent `sha256:34b394a9…`, verifier `sha256:35b47fbb…` (pass).
- Binary checksum gate → build step `sha256sum -c` on the resolved installed
  binary printed `<...>/2.1.218: OK` against the recorded sha256 (pass).
- Container-side `claude --version` → `2.1.218 (Claude Code)` and installed
  binary sha256 `e12071751a…` verified in-container, no model call (pass).
- Image inspection → non-root users, no volumes/mounts, clean env key names,
  digest-pinned base; `/home/agent/.claude` and `/home/agent/.claude.json`
  absent (pass).
- Dockerfile inspection → no `COPY`/`ADD`/secret mounts; pinned base, pinned
  version, enforced binary checksum, identity state removed after version
  checks (pass).
- Image canary scan → agent and verifier `CLEAN` (`identity_state_present=false`,
  `scan_command_failed=false`); synthetic-secret rebuild canary (secret as
  build-arg + context file) `CLEAN`, did not leak; the scanner's fail-closed
  contract is covered by `test_scan_image.py` (pass).
- `evals/harbor/scripts/posture.py` → profile, envelope, and payload valid,
  digests verified (pass).
- `evals/harbor/scripts/test_posture.py` → 26 tests pass, incl. duplicate-source
  rejection (pass).
- `evals/harbor/scripts/test_scan_image.py` → 14 tests pass, incl. failed scan
  and failed canary build (pass).
- `python3 evals/validate_skill_evals.py` → 2 suites valid (pass).
- `./d7y validate` → evals + initiatives valid (pass).
- `git diff --check` and `git status --short` → clean (pass).

Static files and successful image construction are posture evidence only, not a
Harbor execution pass.

### External resources retained

- Docker image `d7y-eval-phase0-agent:2.1.218`
  (`sha256:34b394a9…`; identity and rebuild recipe recorded above).
- Docker image `d7y-eval-phase0-verifier:phase0`
  (`sha256:35b47fbb…`; identity and rebuild recipe recorded above).

The disposable `d7y-eval-phase0-canary:scratch` synthetic-secret image was
rebuilt and removed during the correction scan. No eval-evidence directory is
created for Phase 0: no Harbor trial ran and no raw run artifacts exist to
retain; run evidence directories begin with Phase 1.

### Deviations

- Daemon-resource deviation (original Phase 0 execution): a single disposable,
  unprefixed `docker run --rm hello-world` probe was run once to confirm daemon
  access before the prefixed image work. The `hello-world` container was
  removed by `--rm`; the cached `hello-world` library image was left in place.
  Every other D7Y-created daemon resource is prefixed `d7y-eval-phase0-`. This
  was not repeated in the correction rebuild.
- The agent image uses the native Claude Code installer (not npm) because that
  is the exact path Harbor's v0.20.0 claude-code adapter uses, so the adapter
  detects the pinned version and skips runtime install; the npm package
  metadata is recorded for traceability. No scope was expanded into Phase 1
  behavior.

### Limitations

- No XFS/project-quota data root; Harbor-managed writable-layer storage is
  `unsupported`. The declared `storage_mb` is retained as task metadata only,
  not simulated or treated as enforced.
- No host firewall certifies the launcher bootstrap declaration (not a Phase 0
  blocker).
- Independent upstream route attestation is unavailable; effective
  model/provider remain runtime evidence.
- Debian package resolution is not snapshot-pinned; `apt-get update` resolves
  the current trixie set at build time.
- Image digests are not byte-for-byte reproducible across independent no-cache
  rebuilds (see _Reproducibility_); reproducibility means pinned content inputs
  plus a recorded, verifiable retained image identity, not identical digests.
- The image scan proves the searched-for forbidden material and named secret
  bytes are absent (including the installer identity state, now removed); it
  cannot exhaustively disprove unknown secret bytes without reading every byte.

### Review corrections applied

This `phase-0-review-corrections` handoff corrected the bounded Phase 0 review
findings and rebuilt the images `--no-cache` from `39fab1b`:

1. `scan_image.py` fails closed — a failed scan, canary build, canary scan, or
   cleanup is a distinct command failure with redacted diagnostics and a
   non-zero exit, never `CLEAN`. Covered by `test_scan_image.py` (14 tests).
2. The recorded linux-x64 Claude Code binary SHA-256 is an explicit build input
   (`ARG CLAUDE_CODE_BINARY_SHA256`) and is verified against the installed
   binary during the build; the gate printed `<...>/2.1.218: OK`.
3. Installer-generated identity state (`/home/agent/.claude` and
   `/home/agent/.claude.json`, carrying generated machine/user IDs) is removed
   from the retained agent image after all version checks and asserted absent;
   the scanner confirms `identity_state_present=false`.
4. Duplicate fixed payload sources are now rejected by `posture.py` rather than
   silently skipped; covered by a focused invalid-case test.
5. Reproducibility is stated precisely (pinned inputs + recorded retained
   identity, not byte-for-byte; Debian not snapshot-pinned; no cache-backed
   proof) — see _Reproducibility_.
6. The original `hello-world` daemon probe is recorded as the sole execution
   deviation — see _Deviations_ and _Docker context_.

Residual risk: the binary checksum gate and scanner are strong but cannot
exhaustively disprove unknown secret bytes, and a future rebuild with a
different digest requires rescanning before use. Static validation and image
construction remain posture evidence, not a Harbor execution pass.

### Inputs required by Phase 1

- Profile: `evals/harbor/profiles/claude-primary.json` (`claude-primary`).
- Execution envelope: `evals/harbor/config/execution-posture.json`
  (2 CPU/4096 MiB limit, 600 s agent, 120 s verifier, `no-network` baseline,
  `api.z.ai` agent allowlist, separate no-network verifier).
- Agent image: `d7y-eval-phase0-agent:2.1.218`
  (`sha256:34b394a9…`).
- Verifier image: `d7y-eval-phase0-verifier:phase0`
  (`sha256:35b47fbb…`).
- Payload contract: `evals/harbor/payloads/starting-initiatives.json`.
- Validator: `evals/harbor/scripts/posture.py`.

Phase 1 builds the Harbor Oracle smoke task consuming this profile, envelope,
and these images; it stages the runtime payload and adds the verifier test
script plus the public initiative checker to the separate verifier `tests/`
directory. It must not bake any of those into the images or infer missing
Phase 0 evidence.
