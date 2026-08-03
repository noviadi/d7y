---
title: Iterative Skill Eval Harness (Blast-Radius-Matched)
type: feat
status: todo
createdAt: 2026-08-03
updatedAt: 2026-08-03
supersedes: docs/plans/eval-execution-harness.md
dependsOn: docs/plans/runtime-binding-claude-code.md
---

# Iterative Skill Eval Harness (Blast-Radius-Matched)

## Prerequisites

**Depends on [`docs/plans/runtime-binding-claude-code.md`](./runtime-binding-claude-code.md).**
D7Y's skills and CLI exist as artifacts, but no host binding realizes them yet
— the skills are not installed where a real Claude Code session loads them.
Stage 0 (real-use failure capture) and Stage 1a's "one real captured run" exit
gate both require D7Y to run for real. **Do not start this plan's stages until
the runtime-binding plan's completion boundary is met.** Until then, the only
permitted eval work is the pre-implementation scaffolding (failure-log format
and case-quality bar) that does not require a running binding.

## Summary

Build eval capability iteratively, matching every artifact to the evidence
that justifies it. The current skills write Markdown and run a dependency-free
Python checker; they do not execute untrusted code, touch the network, or
mutate shared state at scale. So the first useful eval work is **failure
capture** and a **thin deterministic workspace grader** for the deterministic
skill — not a benchmark runner, and not containerized isolation.

This plan **supersedes** `docs/plans/eval-execution-harness.md`, which fused
three distinct questions into one gate (can the substrate execute / is the
comparison valid / is the provider hardened). This plan separates them and
gates each behind the evidence that earns it.

The primary uncertainty is behavioral:

> Does each skill add value over a no-skill baseline, on realistic cases
> derived from observed use?

That is a question about skills, not about infrastructure. Spend complexity on
the comparison, not on controls the tasks do not require.

## Guiding eval principles (read before any judgment call)

These are the load-bearing lessons for this work. When a decision is unclear,
return here.

- **Grade the outcome, not the message or the path.** For `starting-initiatives`
  the outcome is the resulting initiative workspace state, checked
  deterministically — not what the agent said it did, and not the exact tool
  sequence it used.
- **Deterministic graders first; reuse, never reimplement.** The grader for
  `starting-initiatives` already exists (`scripts/check-initiatives.py`,
  `inventory(root)`). Import it. Do not rewrite parsing or validation.
- **Capture-grader ≠ benchmark runner.** A capture-grader grades whatever
  workspace you point it at and is useful from the first real use. A benchmark
  runner needs a case corpus and reports pass rates. Build the first now; the
  second is gated behind real cases. Confusing them is the Harbor mistake at a
  smaller scale.
- **Real-failure-derived cases beat authored scenarios.** Authored
  positive/negative controls are smoke tests, not the eval. The eval comes from
  observed failures encoded as synthetic fixtures (workbench-development mode
  forbids running real discovery in this repo).
- **Two-experts-agree is the case-quality bar.** A captured failure becomes a
  committed case only if two people would independently reach the same verdict:
  unambiguous, outcome-gradeable, severity-tagged, and discriminating.
- **Paired comparison is the power multiplier — but it is gated.** Running
  baseline and treatment on the same task is where real signal lives. It is
  Stage 1b, gated on having cases, because without cases it just re-runs smoke.
- **Read traces before tightening assertions.** Add deterministic assertions
  only after inspecting real traces/artifacts. Tightening before observing is
  guessing.
- **Report per-dimension, never a composite score.** Keep
  environment/pair/invocation/process/outcome/quality/efficiency separate. A
  single blended number is the most gameable map.
- **Claim-scoped validity; missing telemetry is `ungradable`, never an implicit
  pass.** A result is valid for the dimensions whose controls held. Unsupported
  capabilities are recorded limitations.
- **Match isolation to blast radius.** Pure-text and filesystem-Markdown tasks
  need only a fresh working directory. Containerization is per-skill, deferred
  until a skill actually executes untrusted code, touches the network, or
  mutates shared state at scale.
- **Sample-size humility.** Small sets show direction, not stability. No
  statistical-stability claim, no `benchmark.json`, no maturity promotion until
  the evidence supports it.

## What is carried over from the superseded plan and contract

The Harbor plan's *thinking* was mostly correct and is retained: paired
baseline/treatment; layered evidence with deterministic preference; canonical
failure classes (`environment_error`, `pair_error`, `agent_error`,
`evidence_error`, `verifier_error`, `assertion_fail`, `ungradable`);
claim-scoped validity; invocation as one dimension (availability ≠ invocation);
read-before-tighten; and "schema validation is not behavioral evidence."

## Per-skill mapping

| Skill | Spectrum | Outcome grader | Hard-to-grade slice | Blast radius | First eval work |
|---|---|---|---|---|---|
| `starting-initiatives` | coding-ish (deterministic checker) | `check-initiatives.inventory()` | selection correctness (intent-match); invocation telemetry | filesystem Markdown + no-state checker | Stage 1a capture-grader (justified now) |
| `writing-great-skills` | anchor-anchored generative | `validate_skill_evals.py` + schema + structural | prose quality; true quality measured downstream via produced skills' evals | pure text | deferred (Stage 2) |

`starting-initiatives` earns a thin grader now because deterministic grading
gives objective signal per run — the runner is glue around an existing grader,
not new infrastructure. `writing-great-skills` is generative: per-run signal is
not cheap, so its eval waits for a real-failure corpus and defined judgment
dimensions.

## Stages and gates

### Stage 0 — Failure capture (the starting line; no harness)

- **Entry gate:** the runtime-binding plan is complete — D7Y runs as a real
  binding and at least one real session has produced a real run. Stage 0 is
  real-use observation; it is impossible until D7Y actually runs. (Before that,
  only the failure-log format and case-quality bar may be drafted.)
- **Work:** use both skills in real D7Y discovery work elsewhere. Log failures
  to `evals/failures.md` (uncommitted by default) with a structured entry:
  skill, prompt/intent summary, observed behavior, expected behavior, failure
  class (over-trigger / under-trigger / wrong selection / missed step / invalid
  artifact / ambiguous instruction / flaky), severity, and whether it is
  outcome-checkable.
- **Exit gate:** enough observed failures to encode a *discriminating* derived
  case set for `starting-initiatives` — coverage of the distinct failure modes,
  not a fixed count (~15–25 is a guide, not a target). Each candidate case must
  clear the two-experts-agree bar.
- **Hard rule:** no runner, no grader code, no benchmark work in this stage.

### Stage 1a — Thin deterministic workspace grader (`starting-initiatives`)

- **Entry gate:** Stage 0 has begun (the failure log exists and is being
  populated). A full corpus is **not** required, because the grader is useful on
  any single workspace from the first real use.
- **Work:** a dependency-free Python tool that takes a workspace path, runs
  `check-initiatives.inventory()` against it, captures the produced
  `initiatives/` artifacts and any pointed-at transcript, and emits a layered
  outcome result with provenance. It grades **one workspace** — no agent
  invocation, no baseline/treatment pair, no pass rate.
- **Exit gate:** grades any pointed-at workspace; focused self-tests pass
  (valid/invalid fixture workspaces); one real captured run graded and retained
  in the runs layout. No benchmark, no pass-rate, no maturity.
- **Hard rules:** do not invoke an agent; do not build pair logic; do not edit
  the skills, the schema, the existing graders, or canon.

### Stage 1b — Paired baseline/treatment runner (deferred)

- **Entry gate:** Stage 0 has produced a discriminating derived case set for the
  target skill. This is the hard gate — do not start without it.
- **Work:** extend to paired baseline/treatment, headless agent invocation,
  pair-validity checks, repeated comparison, per-dimension reporting, and
  severity weighting (report equal- and severity-weighted views separately).
- **Exit gate:** repeated paired evidence with per-dimension counts and a
  factual summary distinguishing behavior from infrastructure failure. Still no
  `benchmark.json`, no maturity.
- **Known unknowns resolved here, not in 1a:** the exact headless Claude Code
  invocation contract, and whether a runtime-owned skill-load signal exists for
  invocation grading (fallback `ungradable` is acceptable). Treat each as a
  short discovery step; document findings; do not invent a parser.

### Stage 2 — `writing-great-skills` eval (deferred; generative)

- **Entry gate:** the judgment dimensions for this skill are defined **and** a
  real-failure corpus exists for it. The deterministic-signal-per-run
  justification does not hold, so nothing is built for it until then.
- **Work:** deterministic structural/schema gates (reuse
  `validate_skill_evals.py`), a calibrated rubric for prose quality, and nested
  evaluation through the skills it produces.

### Stage 3 — Escalate isolation per skill (Harbor, deferred)

- **Entry gate:** a skill exists that executes untrusted code, touches the
  network, or mutates shared state at scale.
- **Work:** re-introduce Harbor **for that skill's suite only**, qualified once
  per materially distinct configuration, scoped to the claims that depend on it.

## Stage 1a grader sketch

Location: `evals/run/workspace_grader.py` (dependency-free Python 3; new).

```text
workspace_grader.py
├── grade(workspace: Path) -> result
│     imports check-initiatives.inventory(workspace)
│     records: valid (bool), count, per-record validity + errors,
│     workspace identity, artifact inventory (initiatives/<slug>/initiative.md)
├── capture(workspace, transcript_path | None) -> evidence
│     copies the produced initiatives/ artifacts (and optional pointed-at
│     transcript) into the runs layout; never mutates the input workspace
├── emit_layered(result, evidence, provenance) -> checks.json + summary.md
│     outcome dimension from inventory(); other dimensions marked N/A where no
│     evidence exists (do not fabricate layers); canonical failure classes
└── provenance: d7y source commit, skill source commit, checker version, date
```

The grader takes a workspace, grades it, captures evidence without mutation,
and emits only the dimensions that have evidence. It is a capture-grader: useful
on the first real run, before any case corpus exists.

## Output shape (checks.json, Stage 1a)

```json
{
  "schema_version": 1,
  "skill": "starting-initiatives",
  "workspace": "<abs path>",
  "provenance": { "d7y_commit": "...", "skill_commit": "...", "checker": "check-initiatives.py", "date": "..." },
  "dimensions": {
    "outcome": {
      "status": "pass | fail | ungradable",
      "inventory_valid": false,
      "count": 0,
      "records": [ { "slug": "...", "valid": false, "errors": ["..."] } ]
    }
  },
  "captured": [ "initiatives/<slug>/initiative.md" ],
  "failure_class": "assertion_fail | evidence_error | ungradable | none"
}
```

Dimensions without evidence (process, invocation, quality, efficiency,
environment, pair) are omitted or explicitly `N/A` in 1a — never fabricated.

Runs layout reuses the contract's `evals/runs/<skill>/iteration-<N>/`
(`manifest.json`, `checks.json`, `summary.md`, `artifacts/`), with raw run
artifacts kept outside the source tree by default.

## Canon updates required (separate reviewed step, not part of 1a)

`docs/skill-evaluations.md` states Harbor is "the first execution substrate."
Superseding this plan requires revising that canon so it does not contradict
the blast-radius-matched path. Proposed edits, integrated by Amp after review:

- Reframe the execution-substrate sentence: Harbor is the substrate for skills
  whose blast radius requires containerized isolation; the default path is the
  thin blast-radius-matched grader/runner.
- Move the detailed Harbor execution contract under a scoped "containerized
  execution (when required)" heading, retaining its content for when it applies.
- Keep the case contract, dimension table, failure semantics, and maturity model
  unchanged (substrate-neutral, already correct).

These canon edits are **not** in scope for Stage 1a execution.

## Scope

### In scope for Stage 1a (the executable-now part)

- `evals/run/workspace_grader.py`, `evals/run/test_workspace_grader.py`, and a
  short `evals/run/README.md`.
- Reuse of `check-initiatives.inventory()` by import.
- Layered outcome result + capture, no agent invocation, no pairing.
- Self-tests using fixture workspaces (materialized from the existing
  `skills/starting-initiatives/evals/evals.json` fixtures).

### Deferred (gated)

- Stage 1b paired runner, headless agent invocation, pair validity, repeated
  comparison, severity weighting (gated on the Stage 0 case set).
- `writing-great-skills` eval (Stage 2).
- Harbor, Docker, quotas, firewall, proxy attestation, adversarial probes,
  image scanning (Stage 3, per-skill).
- A top-level `d7y eval` product command; automated judge selection; automated
  skill evolution; cross-model/provider evaluation; service/database/UI.
- The canon edits above (separate reviewed step).

## Verification (Stage 1a)

1. `python3 evals/validate_skill_evals.py` — suites still valid.
2. `./d7y validate` — evals + initiatives valid.
3. `python3 evals/run/test_workspace_grader.py` — focused self-tests: a valid
   fixture workspace grades `pass`; an invalid one (missing heading, bad slug,
   bad date, placeholder remainders) grades `fail` with the right errors;
   capture does not mutate the input; provenance is recorded. No live agent.
4. A dry-run grading a fixture workspace materialized from an existing case.
5. `git diff --check` and a clean task worktree.

Report static validation, deterministic tests, and the dry-run as distinct
facts. A clean dry-run is not a behavioral run.

## Completion boundary

Stage 1a is complete when:

- a thin, dependency-free workspace grader reuses `check-initiatives.inventory()`;
- it grades any pointed-at workspace and emits the layered outcome result with
  provenance, without fabricating dimensions that lack evidence;
- one real captured run is retained in the runs layout;
- no benchmark, pass-rate, maturity, or canon change has been made.

Stages 1b, 2, and 3 remain gated and are not complete. The foundation proves a
bounded blast-radius-matched grading path for the deterministic skill. It does
not prove containerized isolation, paired comparison, statistical stability,
or that any skill is `evaluated`.
