---
title: Minimal Skill Eval Runner
type: feat
status: todo
createdAt: 2026-07-26
updatedAt: 2026-07-26
---

# Minimal Skill Eval Runner

## Summary

Implement the smallest local runner that can produce inspectable comparative evidence for D7Y's current skills. For one selected case, it runs the same prompt in fresh isolated workspaces with and without the target skill, captures what happened, applies a few trusted deterministic checks, and records unresolved judgment honestly.

This is D7Y infrastructure, not a general eval framework. The first increment supports one verified agent executor, a no-skill baseline, sequential runs, and the assertions needed by the current suites. It does not automate qualitative judgment, benchmark acceptance, or skill maturity.

Start by probing Claude Code because it is the first intended D7Y product host binding—not because Claude Code implements the runner. Claude Code becomes the first executor only if a capability spike proves that it can isolate the target skill and expose trustworthy evidence. If Claude Code cannot meet the validity gates, record the failed gate and return the decision to Amp and the human before narrowing the binding, stopping, or probing another host strictly as internal eval infrastructure. Implement only the first runtime that passes. Do not build a multi-backend abstraction in this increment.

Passing the eval-runner gates establishes only compatibility with this bounded eval execution contract. It does not establish complete first-class D7Y runtime support on that host.

## Problem Framing

D7Y already has an evaluation contract, schema, validator, fixtures, and two provisional skill suites. It cannot yet execute them. Static validity therefore risks being mistaken for evidence that a skill invokes correctly or improves an outcome.

The next uncertainty is narrower than "how should D7Y run arbitrary evals?":

> Can D7Y produce one valid, reproducible with-skill versus no-skill comparison whose evidence is sufficient to inspect and mechanically check?

The comparison is invalid if the baseline can discover the target skill through the checkout, root instructions, user-global configuration, or another skill root. It is also invalid if the with-skill agent can see expected outputs, assertions, fixture source directories beyond the staged case inputs, graders, or benchmarks. Isolation and provenance are therefore required; generic execution and grading extensibility are not.

Current deterministic assertions are natural-language claims rather than executable declarations. Define only the structured checks supported by evidence observed in the first real traces. Do not design a broad grader protocol in advance.

## Success Criteria

1. A developer can validate a suite and run one selected case from a committed source revision through a short local command.
2. The case runs once with the target skill and once without it, in separate clean workspaces and fresh agent contexts.
3. A runtime capability record proves the target skill is available only in the with-skill configuration and records the effective instructions, skills, tools, settings, model, and permissions that the runtime can expose.
4. Eval definitions, expected outcomes, fixture source directories beyond the staged case inputs, graders, and benchmarks are not visible to either executing agent.
5. Prompt, declared fixtures, repository seed, model or mode, tools, permissions, and resource limits are equivalent across the pair except for the target skill treatment.
6. The source checkout is never modified. Fixture traversal, symlink escape, and overwrite of harness control files fail before agent execution.
7. Each run preserves the raw event stream, stderr, exit status, final response, elapsed duration, available usage telemetry, runtime metadata, and retained workspace changes.
8. A small fixed set of trusted deterministic checks reports `pass`, `fail`, `error`, or `ungradable` with concrete evidence. Missing telemetry is unavailable, not zero.
9. Rubric and human assertions remain `pending` until explicit review is recorded. A required pending, errored, failed, or ungradable assertion prevents an overall pass.
10. The generated summary reports observations and baseline deltas but makes no maturity recommendation and does not modify `SKILL.md` or an accepted `benchmark.json`.
11. At least one positive and one negative `starting-initiatives` case complete both configurations. Focused tests prove safe fixture handling, source immutability, target-skill isolation, and safe failure on malformed executor output.
12. The implemented command and known runtime limitations are documented, and canonical eval documentation is updated only where actual behavior refines its contract.

## Scope

### In scope

- A local Python 3 command under `evals/`, using the standard library where practical.
- A capability spike followed by exactly one implemented agent executor.
- Claude Code as the first runtime to probe because it is the first intended product host binding; Amp and Codex are fallbacks for internal eval infrastructure only, not production dependencies selected in advance.
- A committed Git revision as the source of the suite, fixtures, runtime skill payload, deterministic dependencies, and workspace seed.
- Separate with-skill and no-skill workspaces with neutral eval instructions.
- Sequential execution of one selected case or the cases in one current D7Y suite.
- Raw evidence capture and a factual per-case comparison summary.
- Only the trusted built-in deterministic checks required by current suites and supported by observed evidence.
- Visible pending states for rubric and human assertions.
- Focused deterministic tests and real runs using synthetic D7Y eval fixtures, not a real discovery initiative.

### Out of scope

- Multiple production executors or a backend registry, plugin API, adapter hierarchy, or runtime discovery mechanism.
- Previous-version baselines.
- Arbitrary or skill-local executable graders.
- Automated rubric judging, judge calibration, blind pair scoring, or grader agents.
- Repeated-run statistics, claims of stable improvement, or run-order optimization.
- Benchmark acceptance commands, maturity recommendations, and automatic promotion, regression, or retirement.
- Parallel or distributed execution, CI integration, scheduling, a service, database, or web UI.
- Retry orchestration, resumable runs, or an attempt state machine; a rerun simply receives a new output directory.
- Network-dependent discovery tasks or real initiative creation.
- Indefinite retention of complete workspaces.

## Design

### Execution flow

```text
evals.json + committed source revision
                 │
                 ▼
validate suite and verified executor capability
                 │
                 ▼
build equivalent isolated workspace pair
                 │
        ┌────────┴────────┐
        ▼                 ▼
with-skill            no-skill
runtime payload       target instructions absent
        │                 │
        ▼                 ▼
fresh agent process   fresh agent process
        └────────┬────────┘
                 ▼
capture raw events, final response, timing, and changed files
                 │
                 ▼
trusted deterministic checks; rubric and human checks pending
                 │
                 ▼
factual comparison summary with no maturity decision
```

### Executor selection gate

Use a disposable synthetic skill and positive and negative prompts before implementing the runner. Probe Claude Code first. A runtime qualifies only if a recorded spike demonstrates:

1. fresh non-interactive contexts with no session reuse;
2. suppression or exact accounting of user and project instructions, skills, plugins, hooks, MCP servers, and mutable settings;
3. the target skill present exactly once with-skill and absent from every baseline skill root;
4. positive and negative invocation observable from a documented event or other runtime-owned signal rather than final-response wording;
5. machine-readable tool activity and final response capture;
6. workspace-scoped writes and a controlled tool and permission set;
7. runtime, model or mode, effective skill set, configuration, and usage metadata sufficient to scope the result.

For Claude Code, verify the live behavior of its non-interactive execution mode, structured event output, settings or permission scoping, and skill installation and listing; the presence of a flag in `--help` is not proof that isolation works. If Claude Code fails a core isolation or observability gate, record the failed gate and return the decision to Amp and the human before probing Amp or Codex strictly as internal eval infrastructure. Stop if no installed runtime can support an honest comparison.

The selected runtime's command construction and event parsing may live in one clearly named module or function. Do not introduce a common executor interface until a second runtime is actually required.

### Workspace and treatment boundary

Resolve the selected Git ref to a commit first and read all run inputs from that immutable object, not partly from the working tree.

Build both workspaces from the same declared repository seed. Replace source development instructions with identical neutral eval instructions and neutralize every additional instruction source discovered by the capability spike. Stage only declared fixtures.

Remove the target `SKILL.md` and its agent-readable references from both workspace seeds. Preserve required deterministic capability scripts in both configurations when the task needs them. Install a runtime payload only for the with-skill agent containing `SKILL.md` and execution-time references. Never include `evals/`, fixture sources, expected outcomes, assertions, graders, or benchmarks in the runtime payload.

This distinction matters for `starting-initiatives`: its checker path is repository-relative. Keep the checker available identically to both configurations while exposing the skill instructions only to the with-skill runtime. Verify this path behavior in the first vertical slice rather than assuming relocated package resources will resolve.

The run manifest records controllable inputs and the declared treatment delta. It does not claim that stochastic outputs, timestamps, service conditions, or generated identifiers are identical.

### Minimal checks and result semantics

Inspect the first captured traces before changing the eval schema. Then add only the declarations needed for observed, mechanically verifiable facts. Initial trusted checks may include:

- verified target-skill invocation event, if the runtime exposes one;
- command occurrence and exit result;
- path existence, absence, or count;
- JSON or schema validity;
- the existing initiative checker result.

Checks are harness-owned Python functions, not executable plugins. They inspect retained artifacts without repairing them and return a status plus concrete paths, events, command results, or diagnostics as evidence.

If invocation is not observable, invocation assertions are `ungradable`; they are not inferred from the answer or from a good outcome. Rubric and human assertions remain `pending`. The summary may say that the observed with-skill run outperformed the observed baseline on particular checks, but one pair is insufficient for a stable improvement or maturity claim.

### Artifacts

Follow the existing `evals/runs/<skill>/iteration-<N>/` shape where practical. Add only the files needed to inspect the run, likely:

- an iteration manifest;
- per-configuration raw event stream and stderr;
- final response;
- timing and available usage data;
- retained changed files or a workspace-change manifest;
- deterministic check results;
- one factual case or iteration summary.

Raw runs remain ignored. Update `docs/skill-evaluations.md` in the implementation change if the proven artifact layout differs from its current example. Do not create an acceptance workflow around `benchmark.json`.

## Implementation Sequence

### 1. Claude Code-first capability spike

Run a disposable positive and negative synthetic skill case through Claude Code with isolated settings and skill locations, probing it first because it is the first intended product host binding. Record the exact commands, effective skill listings, representative event shapes, permission behavior, and whether invocation is trustworthy. Probe Amp or Codex strictly as internal eval infrastructure only if Claude Code fails a core gate and Amp and the human direct it.

**Complete when:** one runtime passes every core gate and its unsupported telemetry is explicit, or implementation stops because no available runtime can produce a valid comparison.

### 2. Paired capture vertical slice

Implement committed-ref resolution, safe workspace construction, neutral instructions, runtime-payload installation, one executor, sequential execution, and raw artifact capture. Run the positive `starting-initiatives` creation case in both configurations. Ensure eval material is absent from agent-visible files and the checker remains available identically to both configurations.

**Complete when:** both runs are inspectable, the target treatment is proven, changed files are retained, malformed stream and timeout states fail explicitly, and the source checkout is unchanged.

### 3. Evidence-informed deterministic checks

Inspect the captured events and outputs, define the smallest structured check declarations they support, and update the schema, validator, and current suites consistently. Implement only trusted built-ins required by the current cases. Keep unsupported deterministic assertions `ungradable` and rubric or human assertions `pending`.

**Complete when:** every executed deterministic declaration resolves to a known built-in, every result cites evidence, unsafe declaration parameters fail validation, and the summary can be regenerated from captured artifacts.

### 4. Current-suite proof and documentation

Run at least the positive creation case and negative naming control through both configurations. Document validation, one-case execution, suite execution if implemented, artifact inspection, and known runtime limitations. Align `docs/skill-evaluations.md` with proven behavior without accepting a benchmark or changing maturity.

**Complete when:** focused tests pass, the two comparative cases produce factual summaries, source safety is demonstrated, and the documentation distinguishes schema validation, an observed run, and evidence sufficient for a maturity decision.

## Risks and Stop Conditions

- **Claude Code cannot isolate global state:** do not weaken the baseline; record the failed gate and return the decision to Amp and the human before probing the next runtime strictly as internal eval infrastructure.
- **Invocation is not observable:** do not accept self-report as evidence. An invocation-observability failure is a failed qualification gate: record it and return the decision to Amp and the human before probing another host strictly as internal eval infrastructure. If the human explicitly approves an outcome-only run, it may produce scoped outcome evidence, but it remains unqualified for invocation evaluation and must not be represented as passing the executor qualification gate.
- **Eval leakage:** fail before execution if the runtime payload or agent workspace contains eval definitions, graders, expected outcomes, or benchmarks.
- **Instruction leakage:** fail the comparison when effective instruction or skill sources cannot be enumerated or suppressed sufficiently to prove the treatment.
- **Skill resource paths break after installation:** preserve shared deterministic dependencies in both workspaces or make the skill reference portable before continuing.
- **Model or CLI drift:** capture versions and keep small parser fixtures from the capability spike; fail safely on unknown required event shapes.
- **Stochastic overclaim:** report raw observations from a single pair, never stable improvement or maturity.
- **Scope growth:** defer any second executor, arbitrary grader, rubric agent, lifecycle manager, or service until observed D7Y eval failures demonstrate the need.

## Sources and Current Inputs

- `AGENTS.md` — workbench-development constitution.
- `docs/discovery-workbench.md` — thin-harness, fat-skills, deterministic-foundation architecture.
- `docs/discovery-workbench-principles.md` — evidence and autonomy principles.
- `docs/skill-evaluations.md` — canonical skill evaluation and maturity contract.
- `evals/skill-evals.schema.json` — current suite schema.
- `evals/validate_skill_evals.py` — current dependency-free validator.
- `skills/starting-initiatives/evals/evals.json` — first vertical-slice suite.
- `skills/writing-great-skills/evals/evals.json` — second current suite to migrate after the check declaration is proven.
- `scripts/check-initiatives.py` — shared deterministic initiative capability used by the first case (exposed via `d7y initiatives list`/`check`).
- [Agent Skills — Evaluating skill output quality](https://agentskills.io/skill-creation/evaluating-skills)
- [OpenAI — Testing Agent Skills Systematically with Evals](https://developers.openai.com/blog/eval-skills)
