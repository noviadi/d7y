---
title: Progressive Harbor Skill Eval Foundation
type: feat
status: todo
createdAt: 2026-07-30
updatedAt: 2026-07-30
---

# Progressive Harbor Skill Eval Foundation

## Summary

Replace the brittle host-side Claude Code wrapper with a small Harbor-backed execution foundation for D7Y skill evals.

The first objective is not to build ideal evals, a benchmark service, or a complete agent-runtime abstraction. It is to establish one trustworthy, inspectable execution path in which:

- a synthetic D7Y case runs in a real isolated environment;
- the same case can run with and without a target skill;
- the agent cannot read the verifier's private grading material;
- failures use the canonical `environment_error`, `pair_error`, `agent_error`, `evidence_error`, `verifier_error`, `assertion_fail`, or `ungradable` identifiers;
- no result is called a skill improvement or maturity decision prematurely.

Harbor owns task environments, agent execution, resource and network policy, artifact transfer, and verifier isolation. D7Y owns the eval contract, case definitions, treatment comparison, D7Y-specific checks, provenance, and interpretation.

The current `work/eval-execution-harness` branch is frozen. This plan is the replacement implementation direction for `main`; its prior Claude Code wrapper and live-run evidence remain historical input, not the target architecture.

## Problem framing

D7Y has a useful skill-evaluation contract and provisional suites, but the attempted execution layer coupled isolation, Claude configuration, plugin discovery, permissions, process control, event parsing, workspace staging, and grading into one host-side wrapper. Runtime drift and setup errors can therefore produce structured-looking but dubious evals.

The first uncertainty is:

> Can D7Y run one honest skill comparison inside a controlled Harbor environment and explain every non-successful result?

The relevant paper insight is that skill contribution should be estimated through paired rollouts with and without the skill, while preserving execution feedback and distinguishing task performance from agent capability. A single pair is compatibility evidence, not stable improvement evidence. The paper also identifies repeated variants, cost and latency, safety, and longitudinal evaluation as important gaps; these belong in later increments rather than in the foundation.

## Governing decisions

### Harbor is the execution substrate, not the D7Y eval model

Use Harbor's task, environment, agent, trial, artifact, and verifier concepts where they reduce bespoke infrastructure. Do not make Harbor's numeric reward file, task layout, or agent adapter the canonical D7Y eval schema.

Harbor's local Docker environment is the first qualification target. A remote provider is a later explicitly qualified environment, not an implied portability claim.

### Containers replace host-side isolation claims

The agent must run inside a Harbor environment, not as a direct child process of the developer's host checkout. The selected environment must use an explicit non-public network policy, bounded resources, a non-root agent user where supported, and no host checkout or Docker socket mount.

This establishes isolation within the selected Harbor provider configuration. It does not prove that every Harbor provider, Docker daemon, or privileged host is adversarially secure. D7Y must state the provider and environment configuration with every result.

### Separate the verifier by default

Use Harbor's separate verifier environment. The agent receives only declared task inputs and treatment skill content. The verifier may contain private expected outcomes, assertions, grader/checker source, and harness controls; those materials must be built into or mounted only in the verifier environment. The verifier receives only allowlisted agent outputs and explicitly collected evidence from the agent environment.

Harbor documents shared verifier mode as able to see agent-mutated state and installed packages. Shared mode is therefore an explicit exception requiring a written reason.

### Treatment is skill injection, not prompt wrapping

Generate two trials from one immutable case:

```text
same task, image, prompt, model, tools, permissions, resources, and network
├── baseline: no target skill
└── treatment: target skill at an immutable content revision
```

Use Harbor's skill injection and require both the skill content digest and resolved source commit in the run manifest. Stop if either provenance value cannot be recorded. Do not inject D7Y expected outcomes, process instructions, grader details, or target-specific commands into the agent prompt merely to make grading easier.

### Invocation remains a separate evidence question

Harbor proving that a skill was copied into the sandbox proves availability, not invocation. The first implementation must determine whether the Harbor Claude Code integration exposes a trustworthy target-specific invocation signal. If it does not, the run may produce explicitly scoped outcome evidence only after human approval, but it cannot pass D7Y's invocation qualification gate.

### Build in evidence layers

The runner must not begin with a composite score. Each result keeps these layers separate:

1. **Environment validity** — task image, network, user, resources, and provider posture were as declared.
2. **Pair validity** — baseline and treatment were equivalent except for the skill treatment.
3. **Treatment evidence** — the skill was available only in the treatment and invocation evidence, if supported, is valid.
4. **Process evidence** — the agent's trace shows required actions or checkpoints.
5. **Outcome evidence** — the independent verifier confirms the produced artifact or state.
6. **Quality and human evidence** — judgment that deterministic checks cannot establish.
7. **Efficiency observations** — duration, tokens, tool calls, retries, and permission events when available.

Missing telemetry is `unavailable`, not zero. A failed baseline outcome does not invalidate a valid pair; an invalid environment or treatment does.

## Scope

### In scope for the foundation

- Harbor as the first execution substrate.
- Local Docker as the first qualified provider.
- One Harbor task template for synthetic D7Y skill cases.
- One positive and one negative `starting-initiatives` case, migrated only after the synthetic task works.
- Baseline and treatment trials generated from the same immutable case inputs.
- Explicit `no-network` or allowlisted network policy.
- Separate verifier environment.
- Declared artifact transfer and fail-closed required-artifact checks.
- Harbor task, image, agent, skill, and provider provenance, including skill content digest and resolved source commit.
- Raw agent logs or traces available to the verifier as declared artifacts.
- A thin D7Y adapter that translates D7Y cases into Harbor tasks and Harbor results into D7Y evidence layers.
- Dependency-light D7Y checks for paths, JSON/schema validity, command evidence, and the existing initiative checker.
- Synthetic fixtures and isolated eval workspaces only.

### Deferred until evidence justifies them

- A second executor or provider.
- A generalized executor interface.
- A top-level `d7y eval` product command.
- Arbitrary skill-local executable graders.
- Automated rubric or judge agents.
- Reward optimization or reinforcement learning.
- Parallel scheduling, a service, database, or web UI.
- Automatic maturity promotion, regression retirement, or benchmark acceptance.
- Full multi-run statistics and run-order optimization.
- Multimodal or long-horizon benchmark infrastructure.
- Skill retrieval, routing, compression, or library-level evaluation.

## Target architecture

```text
committed D7Y eval case and skill revision
                 │
                 ▼
       D7Y Harbor task builder
                 │
       ┌─────────┴─────────┐
       ▼                   ▼
 baseline task        treatment task
 no skill             immutable skill
       │                   │
       └─────────┬─────────┘
                 ▼
          Harbor environment
       container, network, limits
                 │
          Claude Code agent
                 │
        declared artifacts/traces
                 │
          separate verifier
                 │
          D7Y evidence report
```

The adapter should be deliberately small. It may construct Harbor task files, select the Harbor agent, collect trial metadata, and normalize evidence. It must not reimplement container isolation or duplicate Harbor's process lifecycle.

## Harbor qualification contract

Before migrating a real D7Y suite, prove these properties with a disposable synthetic task.

The first handoff uses Harbor `v0.6.5`, installed with `uv tool install harbor==0.6.5`, and local Docker. Re-qualify if the Harbor version, Docker context, agent integration, or provider changes. Use these initial fixed limits: setup 600 seconds, agent 600 seconds, verifier 120 seconds, 2 CPUs, 4096 MiB memory, and 10240 MiB storage. The task must declare an explicit non-public network policy for setup, agent, and verifier; the exact Claude authentication endpoint allowlist and imported credential key names must be recorded during preflight without recording values. If the selected Claude authentication mechanism cannot operate under an explicit allowlist, stop and return the network decision rather than using Harbor's public default.

The committed runtime payload for the first D7Y case is exactly: `SKILL.md`, `initiatives/README.md`, `d7y`, and `scripts/check-initiatives.py`, plus the case-declared fixture files. The agent image must not contain the source checkout, eval definitions, expected outcomes, assertions, grader source, benchmark summaries, or harness control files. The verifier image may contain the private checker and expected outcomes and receives only declared outputs and evidence.

### Environment

- The agent runs inside the intended container, not in the source checkout.
- The source checkout, host home, host Claude configuration, host skill roots, credentials, and Docker socket are not mounted.
- The agent user and effective working directory are recorded.
- CPU, memory, storage, timeout, and network policy are applied or reported as unsupported.
- `network_mode` is explicit and never inherited from Harbor's public default.
- The verifier is a separate environment, contains its private checker, and receives only declared artifacts and evidence.
- The container is discarded or reset between baseline and treatment.

### Treatment

- The baseline has no target skill content.
- The treatment has exactly the target skill content with both a recorded content digest and resolved source commit.
- Eval definitions, expected outcomes, assertions, grader source, and harness controls are absent from both agent environments, while private grading material is present only in the verifier environment.
- A suppression canary proves that an untrusted or unintended global skill/instruction is not silently influencing the trial, where the Harbor agent integration exposes such state.
- A failed treatment-boundary check invalidates the pair before outcome interpretation.

### Execution and evidence

- The Harbor Claude Code integration can run non-interactively with a bounded timeout.
- Agent stdout, stderr, exit status, tool activity, final response, and available usage data are retained.
- A timeout or malformed agent result produces an explicit infrastructure error and preserves partial evidence.
- Required artifact collection is verified by the separate verifier; Harbor's best-effort collection behavior must not turn missing evidence into success.
- Invocation is either observed from a runtime-owned signal or explicitly marked unavailable.

### Qualification outcome

The qualification result is one of:

- `qualified` — all required foundation gates passed;
- `qualified-with-bounded-evidence` — execution and outcome evidence work, but invocation or another non-required signal is unavailable;
- `not-qualified` — the environment, treatment boundary, or evidence contract cannot be trusted.

Only `qualified` supports the full D7Y invocation contract. No qualification outcome promotes a skill or establishes stable improvement.

## Claude configuration and API boundary

The frozen runner demonstrated a configuration failure that must not be reproduced in Harbor. It read only the top-level `env` object from the host user's `~/.claude/settings.json`, imported every key/value into the Claude process, and overrode only `CLAUDE_CONFIG_DIR`, `PWD`, `TMPDIR`, and `PATH`. Model, provider, endpoint, and authentication variables therefore remained able to override the requested CLI model. A requested `claude-sonnet-5` and an observed routed model such as `glm-4.7` are different facts and must never be collapsed into one setting.

The Harbor implementation must not read or mount the host `~/.claude/settings.json`. It must generate or materialize a task-scoped Claude configuration bundle inside the agent image or runtime workspace:

1. **Harness settings** — a committed, reviewable settings file containing only D7Y-approved behavior controls such as project instruction policy, tool permissions, MCP policy, and persistence settings. It must not inherit user settings.
2. **Runtime environment** — an explicit allowlist of configuration keys injected by Harbor. Values are supplied through approved runtime secret/configuration inputs, never committed to task files or printed in artifacts.
3. **Model contract** — a requested model, provider, and effective model identity recorded separately. Any model/provider environment key not explicitly declared for the run is rejected before agent startup.
4. **API endpoint contract** — the endpoint or proxy identity, configuration digest, upstream provider, and allowed hostnames are recorded. A credential value is never recorded.

The allowed runtime configuration must distinguish:

- authentication inputs, such as an approved API key or token name;
- endpoint/proxy inputs, such as an approved `ANTHROPIC_BASE_URL` or equivalent Claude endpoint setting;
- model/provider routing inputs, which must be explicitly pinned or explicitly prohibited;
- unrelated inherited settings, which must be absent rather than silently accepted.

Configuration precedence must be explicit and testable: the task-scoped bundle and
allowlisted runtime environment are the only configuration inputs; the selected
agent integration's documented command-line request is recorded as the requested
value; and the observed provider response or runtime metadata establishes the
effective value. No host environment or host settings file participates. At
minimum, the adapter must classify routing and credential variables such as
`ANTHROPIC_BASE_URL`, `ANTHROPIC_MODEL`, `ANTHROPIC_SMALL_FAST_MODEL`,
`ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN`, `CLAUDE_CODE_USE_BEDROCK`, and
`CLAUDE_CODE_USE_VERTEX` (where supported by the selected Claude Code version),
then either pin them explicitly or reject them before startup. This classification
must be version-tested rather than inferred from a successful final response.

Harbor task configuration may reference runtime environment values, but must not contain secret values. The task must set explicit network policy for setup, agent, and verifier. The agent may reach only the declared API endpoint or proxy. The verifier must not receive agent credentials or API configuration unless a specific check requires a redacted configuration identity.

Support two qualified API topologies, selecting one per run:

- **External proxy:** the agent reaches an approved HTTPS proxy or custom API endpoint through an exact Harbor allowlist; the proxy handles upstream authentication and any model translation.
- **Harbor sidecar proxy:** a Docker Compose sidecar receives agent requests on an internal service name; only the sidecar reaches the upstream API. Sidecar configuration and upstream identity are hashed and recorded, while credentials remain runtime-only.

The first qualification must prove the selected topology with a harmless request and a known response. It must record requested model, effective model/provider, endpoint identity, proxy identity/configuration digest, and authentication key names. It must fail with `evidence_error` or `agent_error` when the effective model/provider or endpoint cannot be established, and with `pair_error` when baseline and treatment receive different configuration. Do not infer model or API identity from the final response.

## Progressive implementation sequence

### Phase 0 — Freeze and reset the implementation direction

Treat the current Claude wrapper branch as a frozen historical attempt. Do not repair or extend its host-side isolation model in this plan.

Record the pinned Harbor version and installation command, Python version, Docker client and daemon versions, selected image digests, selected agent integration, provider configuration, network policies, resource limits, Claude authentication mechanism and imported key names, and the exact runtime payload. Keep secrets out of plans, task files, and artifacts. The current environment has Docker client `29.6.2` but no permitted Docker daemon access; this is a preflight blocker until daemon access is granted or another explicitly qualified provider is selected.

**Exit evidence:** a committed implementation prompt can point at this plan, the main branch is the source base, and the chosen Harbor/Docker posture is reproducible by a developer.

### Phase 1 — Prove Harbor isolation with a disposable task

Create one synthetic task that has no D7Y semantics. The agent attempts to read canary files, write an artifact, inspect its environment, and finish. The verifier checks:

- host/source paths are not available;
- only declared task files are present;
- network behavior matches the explicit policy;
- agent and verifier filesystems are distinct;
- declared artifacts arrive at the verifier;
- missing required artifacts fail verification;
- timeout and non-zero agent exits retain evidence.

Do not add Claude skill invocation assertions yet. This phase tests Harbor and the task boundary, not skill quality.

**Exit evidence:** a report with positive and negative isolation observations, provider-scoped limitations, and a clear failure classification for each deliberately broken variant.

### Phase 2 — Prove paired skill treatment

Extend the synthetic task with a disposable skill that emits a unique, harmless runtime marker when used. Generate baseline and treatment trials from identical task inputs.

Check that:

- the treatment can access the skill;
- the baseline cannot access the skill;
- the marker is absent from the baseline;
- the skill digest and task/image digests are recorded;
- no task or verifier material leaks into either arm;
- treatment differences are limited to the declared skill injection.

The marker is a qualification probe, not an outcome score.

**Exit evidence:** a valid paired trial whose treatment boundary can be inspected independently of the agent's final response.

### Phase 3 — Qualify Claude Code through Harbor

Run the synthetic positive and negative prompts with Harbor's Claude Code integration. Determine which evidence is genuinely available from Harbor and the integration rather than assumed from the old wrapper:

- target skill availability;
- target-specific invocation;
- tool calls and command results;
- final response;
- requested model and effective model/provider;
- API endpoint/proxy identity and configuration digest;
- authentication mechanism and imported key names, never values;
- model and usage telemetry;
- timeout and error state.

Do not recreate the old host settings/plugin wrapper inside the Harbor task. Implement the explicit task-scoped configuration bundle and API topology above. If the Harbor Claude integration does not expose a supported way to inject those settings or environment values, stop and record the integration gap rather than importing host `settings.json` or weakening the model/provider checks.

**Exit evidence:** a Harbor-specific capability record and parser or adapter tests, with unsupported telemetry explicitly listed.

### Phase 4 — Migrate one D7Y outcome case

Migrate only the positive `starting-initiatives` creation case. Keep the case small and use the independent D7Y initiative checker in the separate verifier.

The agent environment receives only:

- the case instruction;
- the declared synthetic repository seed;
- declared fixture inputs;
- the D7Y capability needed by the case;
- the treatment skill in the treatment arm.

The verifier image contains the private initiative checker and expected outcome rules. It receives only the declared initiative output and required trace or command artifacts, then independently runs the checker and reports outcome evidence separately from process evidence.

**Exit evidence:** one inspectable baseline/treatment pair, with source checkout unchanged and every non-success classified.

### Phase 5 — Add the negative invocation control

Migrate a materially different prompt that should not invoke `starting-initiatives`. Run it in both arms. The treatment may have the skill available, but must not invoke it for the negative control.

**Exit evidence:** positive and negative invocation behavior is reported separately from outcome behavior. If invocation is unavailable through Harbor, stop the full invocation qualification and record the bounded outcome-only capability instead of inferring invocation.

### Phase 6 — Add evidence-informed deterministic checks

Only after inspecting real Harbor traces, add the smallest D7Y check declarations supported by stable evidence. Initial checks may include:

- target invocation event, if available;
- command occurrence and exit result;
- required output path existence or absence;
- JSON/schema validity;
- independent `d7y initiatives check` result;
- required artifact presence;
- environment and treatment provenance.

Checks are harness-owned and inspect artifacts without repairing them. Each result cites concrete evidence. Rubric and human assertions remain visibly pending.

**Exit evidence:** summaries can be regenerated from retained artifacts and cannot call a run passing when required evidence is missing.

### Phase 7 — Follow-on roadmap: expand coverage conservatively

After the foundation is reliable, add the second current suite and then small structurally equivalent variants. Vary inputs and irrelevant context rather than merely duplicating prompts. Report raw per-case results and aggregate counts; do not manufacture statistical precision from a tiny suite.

At this phase, begin recording efficiency observations—duration, available tokens, tool calls, permission events, and recovery attempts—without making fragile hard thresholds the primary acceptance rule.

**Exit evidence:** the suite demonstrates reuse across multiple cases and exposes false triggers, skipped steps, and common failure modes.

### Phase 8 — Follow-on roadmap: add regression, safety, and longitudinal evidence

Only when skill revisions are being made from eval feedback, add:

- a previous accepted skill snapshot;
- held-out cases for regression;
- explicit safety and prompt-injection controls;
- repeated runs sufficient to distinguish a stable pattern from a lucky run;
- longitudinal reports across skill revisions.

Safety failures remain separate hard gates. A skill must not gain utility credit by weakening permission, data-protection, or instruction-boundary behavior.

This phase is where the paper's recommendations about multi-run trajectory comparison, held-out evaluation, cost/latency, safety, and evolution tracking become operational. It is intentionally outside this plan's completion boundary. Before adding `safety` assertions, migrate `evals/skill-evals.schema.json` and its validator to accept the canonical safety dimension; the current schema supports only invocation, process, outcome, quality, and efficiency.

## Artifact and result contract

Each paired iteration should retain or reference:

- D7Y case and suite commit IDs;
- skill commit and content digest;
- Harbor version and task/job configuration;
- environment/provider and image digest;
- agent integration and model configuration;
- requested and effective model/provider;
- API endpoint/proxy identity and configuration digest;
- authentication mechanism and imported key names, never values;
- baseline/treatment distinction;
- network, user, resource, and timeout posture;
- task and verifier manifests;
- raw agent stdout/stderr or trajectory artifact;
- final response and available usage telemetry;
- declared workspace/output artifacts;
- verifier result and independent D7Y checker result;
- environment, pair, treatment, process, outcome, quality, and efficiency evidence;
- failure class and diagnostic;
- unresolved limitations.

Suggested output shape:

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

The exact Harbor output layout may differ. D7Y should normalize only the canonical evidence kinds above and should not duplicate all Harbor internals.

## Failure taxonomy and stop conditions

- **Harbor unavailable or version incompatible:** stop with `environment_error`; do not silently fall back to the old wrapper.
- **Container boundary cannot be demonstrated:** stop with `environment_error` and record the provider limitation.
- **Network policy is implicit or public:** stop with `environment_error` until explicitly configured.
- **Host checkout or credentials are mounted:** stop with `environment_error` before agent execution.
- **Shared verifier is used accidentally:** stop with `pair_error`; do not interpret its result.
- **Skill treatment leaks into baseline:** fail pair validity.
- **Required artifact is absent:** report `evidence_error` or `ungradable`, never success.
- **Claude invocation is not observable:** report `ungradable` for invocation and do not claim invocation success.
- **Harbor agent integration changes its trace contract:** preserve raw evidence, report `evidence_error`, and update the bounded adapter only after a new capability check.
- **Agent timeout or crash:** retain partial logs and report `agent_error`.
- **Verifier failure:** report `verifier_error` and distinguish it from an agent-produced invalid outcome.
- **Stochastic variation:** report observations; do not promote maturity from one pair.
- **Scope growth:** add no abstraction, provider, grader, or orchestration layer without a demonstrated current failure requiring it.

## Verification requirements

Documentation and plan work must verify paths, terminology, Harbor links, and consistency with D7Y canon.

The implementation must, in progressive order, verify:

1. Harbor task parsing, pinned installation, and local Docker startup.
2. Positive and negative isolation probes.
3. Separate verifier and required artifact behavior.
4. Baseline/treatment skill provenance and leakage controls.
5. Claude Code execution and error capture through Harbor.
6. One positive D7Y case and one negative control.
7. Regeneration of summaries from retained artifacts.

Static task validation is not behavioral evidence. A successful Harbor startup is not skill evidence. A successful single run is not stable improvement evidence. A valid benchmark summary is not a maturity decision without comparative and human-appropriate evidence.

## Sources and current inputs

- `AGENTS.md` — workbench-development constitution and implementation boundaries.
- `docs/discovery-workbench.md` — thin-harness, fat-skills, deterministic-foundation architecture.
- `docs/discovery-workbench-principles.md` — evidence, uncertainty, autonomy, and trace/canon principles.
- `docs/skill-evaluations.md` — D7Y skill-evaluation contract and maturity semantics.
- `evals/skill-evals.schema.json` — current suite schema.
- `evals/validate_skill_evals.py` — current dependency-free validator.
- `skills/starting-initiatives/evals/evals.json` — first synthetic D7Y suite.
- `skills/writing-great-skills/evals/evals.json` — later current suite.
- `scripts/check-initiatives.py` — independent initiative checker capability.
- [Harbor motivation](https://www.harborframework.com/docs) — task, environment, agent, and provider model.
- [Harbor core concepts](https://www.harborframework.com/docs/core-concepts) — task, trial, job, agent, and container concepts.
- [Harbor task structure](https://www.harborframework.com/docs/tasks) — resources, network policy, environments, artifacts, and verifier isolation.
- [Harbor agents](https://www.harborframework.com/docs/agents) — Claude Code integration and custom agent boundaries.
- [Harbor skills](https://www.harborframework.com/docs/run-jobs/skills) — skill injection and content provenance.
- [Harbor artifact collection](https://www.harborframework.com/docs/run-jobs/results-and-artifacts) — artifact and sidecar evidence behavior.
- [Agent Skill Evaluation and Evolution: Frameworks and Benchmarks](https://arxiv.org/html/2606.11435v1) — paired rollout comparison, execution feedback, multi-run trajectories, safety, cost/latency, and longitudinal gaps.

## Completion boundary

This plan is complete at the end of Phases 0–6: the Harbor foundation, paired treatment qualification, Claude integration qualification, one positive D7Y case, one negative control, and evidence-informed deterministic checks are inspectable and their limitations are explicit. Phases 7–8 are follow-on roadmap work outside this plan's completion boundary.

The plan must not declare a skill `evaluated`, update an accepted `benchmark.json`, or recommend maturity until the canonical skill-evaluation contract has sufficient comparative evidence and the appropriate human review.
