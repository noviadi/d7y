# D7Y Skill Evaluation Contract

Skills are executable specifications for stochastic systems. They earn permanence through evidence that they invoke when intended, follow the intended process, improve outcomes over a baseline, and justify their cost.

An eval is:

```text
realistic prompt → isolated run → trace and artifacts → evidence-backed checks → comparison
```

A successful example is not an eval. Neither is a static review of `SKILL.md`.

## Organization

Authored eval definitions live with the skill:

```text
skills/<skill>/
├── SKILL.md
├── scripts/                    # deterministic capability tools, when needed
└── evals/
    ├── evals.json              # committed cases and assertions
    ├── files/                  # committed input fixtures, when needed
    ├── graders/                # committed skill-specific graders, when needed
    └── benchmark.json          # latest accepted summary, once evaluated
```

The shared schema lives at `evals/skill-evals.schema.json`.

Run `python3 evals/validate_skill_evals.py` to validate every suite, including fixture paths, unique IDs, and positive and negative invocation coverage.

Raw runs are generated outside skill source:

```text
evals/runs/<skill>/iteration-<N>/
├── skill-snapshot/             # version under comparison when needed
├── <case-id>/
│   ├── with-skill/
│   │   ├── trace.jsonl
│   │   ├── outputs/
│   │   ├── timing.json
│   │   └── grading.json
│   └── baseline/
│       ├── trace.jsonl
│       ├── outputs/
│       ├── timing.json
│       └── grading.json
├── benchmark.json
└── feedback.json
```

Commit eval definitions, fixtures, graders, and an accepted benchmark summary. Keep raw traces and generated artifacts uncommitted by default; retain or publish them separately when auditability requires it.

The minimal contributor runner (`python3 evals/run_eval.py`) writes one output directory per invocation rather than the long-lived `evals/runs/...` tree above. Each output contains a sanitized `manifest.json` of selected Git object IDs and roots, a `checks.json` of pair/treatment/assertion results, a factual `summary.md`, and a per-configuration `<arm>/artifacts/` set (raw `trace.jsonl`, `stderr.txt`, `final-response.txt`, `telemetry.json`, executable+argv `provenance.json`, parsed `command-events.json`, independent `checker.json`, `workspace-changes.json`, `validation.json`, and `process.json`). The directory shape is an implementation detail of the runner; the canonical artifact kinds (raw trace, timing/usage, deterministic checks, comparison summary) are unchanged.

## Minimum suite

Every skill must have `evals/evals.json`. Begin with three realistic cases:

1. a clear positive invocation;
2. a materially different or difficult positive branch;
3. a negative control that should not invoke the skill.

Add cases from observed failures, false triggers, skipped steps, regressions, and user corrections. Prefer a small discriminating suite over a large collection of easy prompts.

Each case defines:

- a stable ID;
- a realistic user prompt;
- whether the skill should trigger;
- a human-readable expected outcome;
- optional files to stage into the clean workspace;
- focused assertions.

Fixture `source` paths are relative to the skill directory. Fixture `destination` paths are relative to the isolated workspace root. Both must remain inside those roots.

Do not require assertions to be complete before the first run. Initial outputs often reveal what is both important and observable. Tighten assertions after inspecting the first traces and artifacts.

## What to evaluate

Use a small set of must-pass checks across five dimensions:

| Dimension | Question |
|---|---|
| Invocation | Did the skill trigger for positive cases and stay out of negative controls? |
| Process | Did the agent retrieve required context, respect checkpoints, and perform the intended steps? |
| Outcome | Did it produce the required decision, artifact, or working state? |
| Quality | Is the result coherent, useful, evidence-aware, and appropriate to the task? |
| Efficiency | Did the skill avoid unnecessary turns, commands, tokens, time, and permission escalation? |

An assertion declares its dimension and grading kind:

- `deterministic` for mechanically observable facts in traces, files, schemas, or command results;
- `rubric` for structured model judgment over qualities that code cannot adequately recognize;
- `human` for consequential or taste-dependent review that should not be delegated.

Prefer deterministic graders wherever the claim is mechanical. Require concrete evidence for every pass. A heading, claim, or confident explanation is not evidence that the underlying work occurred.

## Running an iteration

For each case:

1. Start from a clean workspace and fresh agent context.
2. Stage only the declared files and repository context.
3. Run once with the skill version under evaluation.
4. Run the same prompt and environment against a baseline.
5. Capture the trace, final response, produced artifacts, duration, token usage, tool calls, and permission level.
6. Run deterministic graders first.
7. Apply structured rubric grading only where deterministic evidence is insufficient.
8. Record specific human feedback where judgment remains necessary.

The baseline is:

- **without skill** when establishing whether a new skill adds value;
- **previous accepted skill version** when checking an improvement or regression.

Keep model, tools, permissions, input files, and starting repository state equivalent across configurations. For stochastic behavior, repeat cases enough to distinguish a stable improvement from a lucky run. Early suites may use one run per case, but should report raw counts rather than misleading statistical precision.

Use blind comparison for qualitative judgments when practical so the grader does not know which output came from which configuration.

## Host and harness scoping

An eval result is a claim about behavior under a specific execution context. Scope every eval claim to the recorded host and harness that produced it:

- host and harness;
- host and harness versions;
- model (and mode if relevant);
- tools and permissions;
- configuration and effective instructions;
- skill revision;
- date.

Host-specific raw traces are acceptable as evidence. Generated summaries and benchmarks retain D7Y's canonical result semantics, but a summary's portability claim cannot exceed what the underlying host evidence supports. One-host evidence does not prove cross-host portability, and a passing eval on one host does not establish first-class D7Y runtime support on that host. State the host and harness with each reported result; never generalize a one-host eval into a host-neutral or multi-host claim.

## Benchmark and maturity

Aggregate results by configuration and dimension. At minimum, record:

- required assertions passed and failed;
- false-negative and false-positive invocation counts;
- per-case failures with evidence;
- duration and token usage when available;
- the delta against baseline;
- unresolved human feedback;
- model, host and harness with versions, tools and permissions, configuration and effective instructions, date, and skill revision.

Skill maturity means:

- `provisional` — cases exist, but comparative runs are incomplete or required checks fail;
- `evaluated` — all required checks pass and evidence shows material value over the baseline;
- `regressed` — a previously accepted required check now fails;
- `retired` — the skill no longer adds enough value to justify invocation and maintenance cost.

Maturity is an evidence claim, not an author judgment. A skill remains provisional until its accepted benchmark supports promotion.

## Improving a skill from evals

Use failed assertions, execution traces, and specific human feedback to identify the underlying process failure. Improve the general behavior rather than adding a prompt-specific patch.

Remove assertions that pass equally without the skill; they do not demonstrate value. Investigate checks that fail in both configurations before changing the skill. Treat inconsistent results as evidence of a flaky eval, ambiguous instruction, uncontrolled environment, or stochastic behavior requiring repeated runs.

Keep skills lean as coverage grows. Move repeated mechanical work into scripts and deterministic graders rather than expanding prose. Periodically evaluate whether removing instructions preserves or improves results.

## Sources

This contract adapts:

- [Agent Skills — Evaluating skill output quality](https://agentskills.io/skill-creation/evaluating-skills)
- [OpenAI — Testing Agent Skills Systematically with Evals](https://developers.openai.com/blog/eval-skills)
