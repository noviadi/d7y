# D7Y Skill Evaluation Contract

Skills are executable specifications for stochastic systems. They earn permanence through evidence that they invoke when intended, follow the intended process, improve outcomes over a baseline, and justify their cost.

An eval is:

```text
realistic case → Harbor trial pair → trace and artifacts → independent verification → evidence comparison
```

A successful example is not an eval. Neither is a static review of `SKILL.md`, a valid Harbor task, or a successful agent startup.

This contract describes the D7Y meaning of an eval. Harbor is the first execution substrate and provides the environment, agent lifecycle, resource and network policy, artifact transfer, and verifier isolation. D7Y retains ownership of cases, treatment comparisons, evidence semantics, D7Y-specific checks, and maturity decisions.

## Progressive maturity of the harness

Build and interpret evals in these stages:

1. **Environment foundation** — prove Harbor's container, network, resource, artifact, and separate-verifier boundaries with a disposable synthetic task.
2. **Treatment foundation** — run an identical baseline and treatment trial, with the target skill injected only into treatment, and record immutable provenance.
3. **One D7Y case** — verify one positive outcome case using an independent D7Y checker.
4. **Negative control** — verify that the skill remains available but does not invoke for a materially different prompt.
5. **Evidence-informed checks** — add only deterministic checks supported by observed Harbor traces and artifacts.
6. **Coverage and efficiency** — add structurally equivalent variants, observed failure cases, and descriptive cost/latency data.
7. **Regression, safety, and longitudinal evidence** — add previous versions, held-out cases, safety probes, repeated runs, and cross-revision comparison when skill evolution makes them necessary.

The first stages establish execution compatibility and evidence integrity. They do not establish stable improvement, portability, or skill maturity.

## Organization

Authored eval definitions live with the skill:

```text
skills/<skill>/
├── SKILL.md
├── scripts/                    # deterministic capability tools, when needed
└── evals/
    ├── evals.json              # committed cases and assertions
    ├── files/                  # committed input fixtures, when needed
    ├── graders/                # verifier-only checks, when needed
    └── benchmark.json          # accepted summary only after sufficient evidence
```

The shared schema lives at `evals/skill-evals.schema.json`.

Run `python3 evals/validate_skill_evals.py` to validate every suite, including fixture paths, unique IDs, and positive and negative invocation coverage. Schema validation proves only that the definition is well-formed; it is not behavioral evidence.

Raw Harbor trials and normalized D7Y results are generated outside skill source. The exact Harbor output layout is provider- and version-dependent, so D7Y should retain Harbor output and normalize only the following evidence kinds:

```text
evals/runs/<skill>/iteration-<N>/
├── manifest.json               # D7Y case, Harbor, provider, image, agent, and skill provenance
├── baseline/
│   ├── harbor-result.json
│   ├── agent/                  # raw agent logs or trajectory artifacts
│   ├── artifacts/              # declared outputs
│   └── verifier/               # separate verifier result and diagnostics
├── with-skill/
│   ├── harbor-result.json
│   ├── agent/
│   ├── artifacts/
│   └── verifier/
├── checks.json
└── summary.md
```

Keep raw trials and generated artifacts uncommitted by default. Retain or publish them separately when auditability requires it. Do not treat Harbor's numeric reward file as the D7Y canonical result; preserve the evidence needed to explain the reward.

## Case contract

Every skill must have `evals/evals.json`, but the first executable increment need not contain a full benchmark. Begin with the smallest discriminating set that exercises the current uncertainty:

- one clear positive invocation case;
- one materially different negative control;
- additional positive branches or difficult variants only when the first traces show that they reduce an important uncertainty.

Add cases from observed failures, false triggers, skipped steps, regressions, safety concerns, and user corrections. Prefer a small discriminating suite over a large collection of easy prompts.

Each case defines:

- a stable ID;
- a realistic user prompt;
- whether the skill should trigger;
- a human-readable expected outcome;
- optional files to stage into the agent environment;
- focused assertions.

Fixture `source` paths are relative to the skill directory. Fixture `destination` paths are relative to the task's declared agent workspace. Both must remain inside their intended roots. Eval definitions, expected outcomes, assertions, grader source, benchmark summaries, and harness control files must not be staged into the agent environment. Private expected outcomes, assertions, and grader/checker source belong in the separate verifier environment, not in the agent environment.

Do not require assertions to be complete before the first run. Initial Harbor traces and verifier artifacts reveal what is both important and observable. Tighten assertions only after inspecting those artifacts.

## Harbor execution contract

Each comparison is generated from one immutable case and produces two trials:

```text
same task, image, prompt, model, tools, permissions, resources, and network
├── baseline: no target skill
└── treatment: target skill at an immutable content digest or commit
```

The first qualified provider is local Docker through Harbor. Every result records the Harbor version, provider, task configuration, image digest, agent integration, model, skill revision, and date. A result scoped to one provider does not prove portability to other Harbor providers or hosts.

Claude configuration is task-scoped, not inherited from the host. Do not read or mount the host user's `~/.claude/settings.json`. Each trial resolves a named API-routing profile describing direct-endpoint or proxy routing, the agent-visible endpoint, allowlisted runtime keys, credential sources, network allowlist, and redacted configuration digests. Inject only explicitly allowlisted runtime configuration values; never commit or persist credential values. Record route evidence separately from requested and effective model/provider evidence. A requested model is not evidence of the effective routed model.

The agent environment must use:

- an explicit `no-network` or allowlisted network policy;
- bounded CPU, memory, storage, and timeout settings;
- a non-root agent user where supported;
- no source-checkout, host-home, credential, or Docker-socket mount;
- a fresh or reset environment for each arm;
- only declared task inputs and the treatment skill, when applicable.

Use Harbor's separate verifier environment by default. It contains private expected outcomes, assertions, grader/checker source, and harness controls, and receives only allowlisted agent outputs and explicitly collected evidence. The agent environment must not receive those private verifier materials or the skill source repository. Shared verifier mode is an exception requiring a recorded reason because it can observe agent-mutated state and installed packages.

Harbor skill injection proves that skill content was made available to the treatment. Record both the content digest and resolved source commit; missing either is an evidence error. Availability does not prove invocation. Invocation requires a trustworthy runtime-owned signal from the selected agent integration. Final-response wording, skill availability, or a successful outcome alone is insufficient.

If the selected Harbor agent integration cannot expose invocation, the run may produce explicitly scoped outcome evidence only with human approval. It remains unqualified for invocation evaluation and must not be represented as satisfying the full skill contract.

## What to evaluate

Keep these evidence dimensions distinct:

| Dimension | Question | Preferred evidence |
|---|---|---|
| Environment | Did the declared Harbor boundary actually hold? | Harbor/provider metadata, isolation probes, manifests |
| Pair validity | Were baseline and treatment equivalent except for the skill? | Task/image/config/skill provenance and leakage checks |
| Invocation | Did the skill trigger when intended and stay out of negative controls? | Runtime-owned invocation event |
| Process | Did the agent retrieve required context and perform intended steps? | Trace, tool calls, command results, checkpoints |
| Outcome | Did it produce the required decision, artifact, or state? | Separate verifier and independent D7Y checker |
| Quality | Is the result coherent, useful, evidence-aware, and appropriate? | Structured rubric or human review |
| Efficiency | What did the skill cost? | Duration, tokens, tools, retries, permissions when available |
| Safety (later schema migration) | Did it preserve permission and data boundaries under misuse? | Explicit safety and injection probes |

An assertion declares its dimension and grading kind:

- `deterministic` for mechanically observable facts in traces, files, schemas, verifier results, or command results;
- `rubric` for structured judgment over qualities that code cannot adequately recognize;
- `human` for consequential or taste-dependent review that should not be delegated.

Prefer deterministic checks wherever the claim is mechanical. Require concrete evidence for every pass. A heading, claim, confident explanation, or Harbor reward value is not evidence that the underlying work occurred.

Keep the result layers separate:

1. **Environment validity** — the Harbor task and provider posture were as declared.
2. **Pair validity** — baseline and treatment were comparable and leakage-free.
3. **Treatment evidence** — the skill was available only in treatment and invocation evidence is valid or explicitly unavailable.
4. **With-skill assertions** — process, outcome, quality, efficiency, and safety requirements for treatment.
5. **Baseline observations** — comparable facts from the no-skill trial. A baseline failure may demonstrate value and does not by itself invalidate the pair.

An invalid environment or treatment invalidates the comparison. Missing telemetry is `unavailable`, not zero. Missing required artifacts are an evidence error or `ungradable`, never an implicit pass.

## Running an iteration

For each initial case:

1. Resolve the D7Y case, fixtures, skill, and task inputs from an immutable source revision.
2. Build or select one Harbor task and record its image, provider, agent, model, tools, permissions, network, resources, and timeout posture.
3. Run the baseline and treatment as fresh Harbor trials with only the declared skill treatment differing.
4. Capture Harbor results, raw agent logs or traces, final response, produced artifacts, timing, available usage data, and failure state.
5. Verify required artifacts in a separate Harbor verifier environment.
6. Run D7Y deterministic checks without repairing agent output.
7. Apply rubric or human review only where deterministic evidence is insufficient.
8. Produce a factual comparison summary with unresolved limitations and failure classes.

The baseline is:

- **without skill** when establishing whether a new skill adds value;
- **previous accepted skill version** only when checking an improvement or regression in a later stage.

The first foundation may run one pair per case. Report raw observations and do not imply statistical stability. Once repeated variants or repeated runs are added, compare patterns across cases and curate successful and failed traces rather than treating every raw trajectory as reusable knowledge.

## Failure semantics

Use explicit failure classes so infrastructure problems cannot masquerade as skill failures:

- `environment_error` — Harbor task, image, provider, network, resource, user, or container boundary failed;
- `pair_error` — baseline and treatment were not equivalent or treatment material leaked;
- `agent_error` — timeout, crash, malformed result, or agent execution failure;
- `evidence_error` — required trace, artifact, provenance, or telemetry was unavailable or malformed;
- `verifier_error` — the separate verifier could not execute or interpret its inputs;
- `assertion_fail` — the environment and evidence were valid, but a required skill assertion failed;
- `ungradable` — the claim requires unavailable telemetry, rubric judgment, or human review.

Preserve partial evidence for timeouts, crashes, and collection failures. Do not retry silently or replace a failed trial with a successful one. A rerun is a new iteration with new provenance.

## Benchmark and maturity

Do not create or accept `benchmark.json` during the environment, treatment, or first-case foundation stages. A factual `summary.md` may report observations and baseline deltas, but it must not recommend maturity.

When sufficient comparative evidence exists, aggregate by configuration and dimension. At minimum, record:

- required assertions passed and failed;
- false-negative and false-positive invocation counts;
- environment, pair, evidence, and verifier failures;
- per-case failures with concrete evidence;
- duration and token usage when available;
- the delta against baseline;
- unresolved rubric and human feedback;
- Harbor/provider, image, agent, requested and effective model/provider, API endpoint or proxy identity/configuration digest, authentication mechanism/key names, model, tools, permissions, configuration, date, and skill revision.

Skill maturity means:

- `provisional` — cases exist, but the Harbor foundation, comparative runs, or required checks are incomplete;
- `evaluated` — the accepted evidence supports material value over baseline across an appropriate case set and required checks pass;
- `regressed` — a previously accepted required check now fails under a comparable configuration;
- `retired` — the skill no longer adds enough value to justify invocation and maintenance cost.

One successful pair is never enough for `evaluated`. Maturity is an evidence claim, not an author judgment, and remains subject to appropriate human review.

## Improving a skill from evals

Use failed assertions, execution traces, verifier evidence, and specific human feedback to identify the underlying process failure. Improve general behavior rather than adding a prompt-specific patch.

Remove assertions that pass equally without the skill; they do not demonstrate value. Investigate checks that fail in both configurations before changing the skill. Treat inconsistent results as evidence of a flaky case, ambiguous instruction, uncontrolled environment, agent integration drift, or stochastic behavior requiring repeated variants or runs.

When skill revisions begin, preserve the prior accepted skill snapshot and add held-out cases before claiming regression safety. Before authoring safety assertions, migrate `evals/skill-evals.schema.json` and `evals/validate_skill_evals.py` to accept a `safety` dimension. Curate trajectories by quality, diversity, and difficulty before using them to revise a skill. Do not allow automated skill evolution to silently remove safety constraints or convert unverified traces into canon.

Keep skills lean as coverage grows. Move repeated mechanical work into deterministic capability scripts or verifier checks rather than expanding prose. Periodically evaluate whether removing instructions preserves or improves results.

## Sources

This contract adapts:

- [Agent Skills — Evaluating skill output quality](https://agentskills.io/skill-creation/evaluating-skills)
- [OpenAI — Testing Agent Skills Systematically with Evals](https://developers.openai.com/blog/eval-skills)
- [Harbor task structure](https://www.harborframework.com/docs/tasks)
- [Harbor agents](https://www.harborframework.com/docs/agents)
- [Harbor skills and provenance](https://www.harborframework.com/docs/run-jobs/skills)
- [Harbor artifact collection](https://www.harborframework.com/docs/run-jobs/results-and-artifacts)
- [Agent Skill Evaluation and Evolution: Frameworks and Benchmarks](https://arxiv.org/html/2606.11435v1)
