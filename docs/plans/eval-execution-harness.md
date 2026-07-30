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

Harbor's local Docker environment remains the first qualified-provider target. The assigned Docker daemon must be configured with an independently verified storage quota mechanism, such as overlay2 on XFS project quotas with a tested per-container `storage_mb` ceiling. No such mechanism is currently assigned in this repository; until one is supplied and verified, the daemon is only a capability-probe target and cannot qualify. A different provider is a separately scoped qualification, not an implied substitute.

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

Use Harbor's skill injection and require both the Harbor content digest and the D7Y source commit in the run manifest. Local skill paths do not receive Git provenance automatically, so commit the exact skill/task inputs before behavioral execution, verify their bytes match that commit, and record the D7Y commit separately from Harbor's digest. Stop if either provenance value cannot be recorded. Do not inject D7Y expected outcomes, process instructions, grader details, or target-specific commands into the agent prompt merely to make grading easier.

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
- Local Docker as the first qualified provider, conditional on an independently verified storage quota mechanism.
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

The first qualification targets Harbor `0.20.0` and the local Docker provider. Use a pinned, non-global invocation such as `uvx --from harbor==0.20.0 harbor`; do not silently use a shared latest Harbor installation. Re-qualify if the Harbor version, Docker context, agent integration, provider, or Docker network controller changes. Use these initial fixed limits: setup 600 seconds, agent 600 seconds, verifier 120 seconds, 2 CPUs, 4096 MiB memory, and 10240 MiB storage. Record the Harbor version, Docker client and server versions, storage driver, cgroup/runtime posture, kernel/network prerequisites, image digests, and the exact task schema accepted by the pinned release. The storage mechanism is part of the provider identity and must be named, configured, and behaviorally tested with an over-limit task before qualification.

Qualification is split into two gates. Gate A is a Harbor foundation probe and qualification: task loading, explicit network policy, environment injection with a public non-secret sentinel, agent/verifier isolation, artifact transfer, and storage enforcement. Gate A may return a blocker until the assigned Docker daemon has the named quota mechanism. Gate B is a separately human-approved Claude/API-profile qualification that may use credentials only after its concrete profile is supplied. No executor may invent a production endpoint, authentication key, upstream model mapping, or proxy evidence mechanism.

The committed runtime payload for the first D7Y case is exactly: `SKILL.md`, `initiatives/README.md`, `d7y`, and `scripts/check-initiatives.py`, plus the case-declared fixture files. `scripts/check-initiatives.py` is a public D7Y capability checker, not the private eval grader. The agent image must not contain the source checkout, eval definitions, expected outcomes, assertions, private grading wrappers, benchmark summaries, or harness control files. The verifier image may contain private assertions, checker/grader wrappers, and expected outcomes and receives only declared outputs and evidence.

### Environment

- The agent runs inside the intended container, not in the source checkout.
- The source checkout, host home, host Claude configuration, host skill roots, credentials, and Docker socket are not mounted into trial containers. The host implementation executor may use the Docker daemon to build, pull, run, inspect, and clean up Harbor resources, but that access is outside the trial and must be explicitly recorded.
- The agent user and effective working directory are recorded.
- CPU, memory, storage, timeout, and network policy are applied. A reported-but-unenforced limit is not qualification evidence.
- `network_mode` is explicit and never inherited from Harbor's public default.
- The verifier is a separate environment, contains its private checker, and receives only declared artifacts and evidence.
- The container is discarded or reset between baseline and treatment.

Gate A must run an over-limit storage test that attempts to exceed the declared
ceiling and observes a deterministic write failure or provider-enforced limit. A
stored `storage_mb` value, provider label, or successful task load is not evidence
of storage enforcement.

### Treatment

- The baseline has no target skill content.
- The treatment has exactly the target skill content with both a recorded content digest and resolved source commit.
- Eval definitions, expected outcomes, assertions, private grader source, and harness controls are absent from both agent environments, while private grading material is present only in the verifier environment.
- A suppression canary proves that an untrusted or unintended global skill/instruction is not silently influencing the trial, where the Harbor agent integration exposes such state.
- A failed treatment-boundary check invalidates the pair before outcome interpretation.

### Execution and evidence

- The Harbor Claude Code integration can run non-interactively with a bounded timeout.
- Agent stdout, stderr, exit status, tool activity, final response, and available usage data are retained.
- A timeout or malformed agent result produces an explicit infrastructure error and preserves partial evidence.
- Required artifact collection is verified by the separate verifier; Harbor's best-effort collection behavior must not turn missing evidence into success.
- Invocation is either observed from a runtime-owned signal or explicitly marked unavailable.

### Qualification outcome

Gate A outcomes are:

- `foundation-qualified` — Harbor task, network, storage, verifier, artifact, and secret-canary controls passed;
- `foundation-blocked` — the assigned provider lacks the named storage quota or another required capability and must be configured before qualification;
- `foundation-not-qualified` — the environment, treatment boundary, or evidence contract cannot be trusted.

Gate B outcomes are:

- `claude-qualified` — the approved Claude/API profile, execution, route evidence, and required observability passed;
- `claude-outcome-only` — scoped execution and outcome evidence work, but invocation evidence is unavailable; this is explicitly unqualified for invocation evaluation;
- `claude-not-qualified` — Claude execution, route, treatment, or evidence cannot be trusted.

Gate B requires `foundation-qualified` from the same provider, image digests, resource controls, mounts, and effective network posture. Any change to those conditions requires the affected foundation probes to run again. Only `claude-qualified` supports the full D7Y invocation contract. No qualification outcome promotes a skill or establishes stable improvement. These gate outcomes are plan-local provisional statuses, not canonical product result values.

## Claude configuration and API boundary

The frozen runner demonstrated a configuration failure that must not be reproduced in Harbor. It read only the top-level `env` object from the host user's `~/.claude/settings.json`, imported every key/value into the Claude process, and overrode only `CLAUDE_CONFIG_DIR`, `PWD`, `TMPDIR`, and `PATH`. Model, provider, endpoint, and authentication variables therefore remained able to override the requested CLI model. A requested `claude-sonnet-5` and an observed routed model such as `glm-4.7` are different facts and must never be collapsed into one setting.

The Harbor implementation must not read or mount the host `~/.claude/settings.json`. It must generate or materialize a task-scoped Claude configuration bundle inside the agent image or runtime workspace. More importantly, API routing must be a first-class Harbor run input, not an incidental Claude setting:

1. **Harness settings** — use Harbor's native Claude controls first: pinned agent version, model, permission mode, allowed/disallowed tools, MCP configuration, skills, and environment inputs. A committed settings file is allowed only for controls the native adapter cannot express; a custom adapter that installs it must be separately justified and qualified. It must not inherit user settings.
2. **Runtime environment** — an explicit allowlist of configuration keys injected by Harbor. Values are supplied through approved runtime secret/configuration inputs, never committed to task files or printed in artifacts. This includes the endpoint/proxy URL and authentication inputs required by the selected API profile.
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

Reserve Harbor task `[environment].env` for Gate A's public interpolation sentinel and other non-secret values. Never place a real credential or credential reference there: task environment values persist in the container environment and are not the Gate B secret boundary. For Gate B, pass credentials only through Harbor trial-scoped `[agent].env` using a D7Y allowlist of key names, and ensure verifier configuration has no agent credentials. The task must set explicit setup, agent, and verifier network policies. Setup may use a separately allowlisted package-install host; runtime may reach only the approved API endpoint or proxy. The verifier must not receive agent credentials or API configuration unless a specific check requires a redacted configuration identity.

Represent the route as a named, versioned API profile resolved when the Harbor task is built. At minimum it contains:

- route kind: direct custom endpoint or proxy;
- agent-visible endpoint value or internal proxy service name;
- the allowlisted agent environment keys and runtime secret names;
- upstream provider and model mapping, when a proxy performs translation;
- exact Harbor allowed hosts and network mode;
- redacted configuration digest and proxy image/configuration digest.

For the external proxy topology, the generated task keeps the proxy endpoint and
non-secret profile metadata in task configuration, and passes the credential only
through trial-scoped `agent.env` at execution time. Harbor's `${HOST_VAR}`
interpolation in `environment.env` is tested only with Gate A's public sentinel.
Gate B's sensitive-looking canary is agent-scoped and must be checked after
finalization. The proxy must emit a redacted request record (route, requested model,
upstream status, and correlation ID) through an independently controlled endpoint
log or declared artifact. This proves routing without exposing the API credential or
relying on Claude's final response.

Harbor's Docker Compose support can add a proxy service, and the `main` agent
container can reach it by service name. However, Compose services share the task
network and Harbor's documented network policy is applied to the environment/agent
phase, not automatically as a distinct egress firewall per service. A sidecar is
therefore not evidence that the agent cannot also reach the upstream. Treat sidecar
routing as a Docker-specific follow-on until a direct-egress negative test or an
additional provider-enforced network boundary proves otherwise. Sidecar request logs
may be collected with Harbor's `service` artifact entries, but they must be captured
before separate-verifier teardown.

Support API topologies progressively:

- **Foundation — external proxy:** the agent reaches an approved HTTPS proxy through an exact Harbor runtime allowlist; the proxy handles upstream authentication and any model translation. This is the first Gate B topology. Direct official Anthropic routing is deferred until an independent route-evidence mechanism is defined and qualified.
- **Follow-on — Docker Compose sidecar:** a Compose sidecar receives agent requests on an internal service name. Sidecar configuration and upstream identity are hashed and recorded, credentials remain runtime-only, and direct agent-to-upstream access must be tested separately. This topology is Docker-specific; Harbor documents that many cloud providers do not support Compose environments.

The first Gate B credentialed qualification must prove the external proxy/custom endpoint topology with a harmless request and a known response. It must record the API profile, route identity, proxy request record, requested model, effective model/provider when available, and authentication key names. It must fail with `evidence_error` or `agent_error` when the route cannot be established, and with `pair_error` when baseline and treatment receive different API profiles. Effective model/provider is useful provenance, but route evidence comes from the proxy or endpoint boundary, not from the final response.

## Progressive implementation sequence

### Phase 0 — Freeze and reset the implementation direction

Treat the current Claude wrapper branch as a frozen historical attempt. Do not repair or extend its host-side isolation model in this plan.

Record the pinned Harbor version and invocation, Python version, Docker client and daemon versions, storage driver and quota mechanism, cgroup/runtime and kernel/network prerequisites, selected image digests, selected agent integration, API-profile status, injection mechanism, network policies, resource limits, and the exact runtime payload. Probe Docker access under the exact assigned executor/launcher posture rather than relying on a sandbox-specific observation. Keep secrets out of plans, task files, and artifacts. Do not install Harbor into shared user tooling as an unrecorded side effect.

**Exit evidence:** a committed implementation prompt can point at this plan, the main branch is the source base, and the chosen Harbor/Docker posture is reproducible by a developer.

### Phase 0A — Probe Harbor without Claude credentials

Build and run a disposable task using Harbor `0.20.0` and local Docker only. Use Harbor's built-in Oracle with a synthetic solution script for active read, write, environment, network, timeout, and artifact probes; use a no-op only for deliberately absent-action or missing-artifact controls. Do not require Harbor-trial Claude authentication. Prove the exact `task.toml` fields used by this plan: environment and phase network policies, `environment.env` interpolation with a public non-secret sentinel, separate verifier configuration, declared artifacts, and the selected resource controls. Test storage enforcement explicitly with an over-limit write. If Docker reports storage without enforcing it, record `environment_error` as a foundation blocker; do not call the probe qualified. Run positive and deliberately broken variants and classify each failure.

Add two deterministic canaries. Gate A injects a public interpolation sentinel through `environment.env`. Gate B, only after human approval, injects a sensitive-looking canary through trial-scoped `agent.env` using the D7Y key allowlist. After Harbor finalization, scan task files, manifests, logs, and collected artifacts byte-for-byte; permit only an approved redacted marker or digest representation. If raw sensitive bytes appear, quarantine the result, delete the raw-secret-bearing artifacts, and report `evidence_error`; never publish or grade the trial. Account for binary/unreadable files by failing closed when they cannot be scanned.

**Exit evidence:** a Harbor `0.20.0` capability record, valid task fixtures, positive and negative results, separate-verifier evidence, a behavioral storage-boundary result, and a clean canary report. The result is `foundation-qualified` only when storage and network boundaries are enforced. Otherwise return `foundation-blocked` with the missing quota mechanism named; never report a successful foundation qualification.

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

### Phase 2A — Supply and approve the Claude/API profile

Before any credentialed run, a human supplies and approves a concrete external-proxy API profile containing the non-secret proxy hostname, exact Harbor setup/runtime allowlists, authentication key name, upstream provider/model mapping, proxy configuration digest, route-evidence source, exact Claude Code version, exact digest-pinned agent image, and trial-scoped secret injection mechanism. The profile is committed as non-secret configuration or recorded in the execution envelope; its values are never invented by the executor. Direct official Anthropic routing is outside the first Gate B until independent route evidence is defined and qualified.

**Exit evidence:** an approved profile and a credential injection procedure that does not write secrets to the repository, task files, logs, or artifacts.

### Phase 3 — Qualify Claude Code through Harbor

Run the synthetic positive and negative prompts with Harbor's Claude Code integration and the approved external-proxy profile. Pin and record the exact Claude Code agent version and use a digest-pinned agent image containing that version; do not accept Harbor's default installer result as reproducible. If installation is required, give setup its own explicit package/download allowlist distinct from the runtime API allowlist. Use Harbor's native Claude controls for permission mode, tools, MCP, skills, model, and environment inputs. If a settings file is necessary, implement a small custom adapter only after recording the native-control gap and qualifying that adapter separately. Determine which evidence is genuinely available from Harbor and the integration rather than assumed from the old wrapper:

- target skill availability;
- target-specific invocation;
- tool calls and command results;
- final response;
- API profile, route identity, and proxy request evidence when applicable;
- requested model and effective model/provider when available;
- authentication mechanism and imported key names, never values;
- model and usage telemetry;
- timeout and error state.

Do not recreate the old host settings/plugin wrapper inside the Harbor task. Use the Harbor Claude adapter's native controls and the approved API profile. If a required control cannot be expressed natively, stop and record the gap before authorizing a small custom adapter; never import host `settings.json` or weaken route checks.

**Exit evidence:** a Harbor-specific capability record and parser or adapter tests, with unsupported telemetry explicitly listed.

### Phase 4 — Migrate one D7Y outcome case

Migrate only the positive `starting-initiatives` creation case. Keep the case small. The public `scripts/check-initiatives.py` capability checker is staged separately into the verifier, where a private grading wrapper supplies expected rules and records the checker commit/digest; the agent's public copy is not the private grader.

The agent environment receives only:

- the case instruction;
- the declared synthetic repository seed;
- declared fixture inputs;
- the D7Y capability needed by the case;
- the treatment skill in the treatment arm.

The verifier image contains the private grading wrapper, a separately staged copy of the public capability checker, and expected outcome rules. It receives only the declared initiative output and required trace or command artifacts, then independently runs the checker and reports outcome evidence separately from process evidence.

**Exit evidence:** one inspectable baseline/treatment pair, with source checkout unchanged and every non-success classified.

### Phase 5 — Add the negative invocation control

Migrate a materially different prompt that should not invoke `starting-initiatives`. Run it in both arms. The treatment may have the skill available, but must not invoke it for the negative control.

**Exit evidence:** positive and negative invocation behavior is reported separately from outcome behavior. If invocation is unavailable through Harbor, stop the full invocation qualification and record `claude-outcome-only`, explicitly unqualified for invocation, instead of inferring invocation.

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
