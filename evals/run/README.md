# evals/run — Stage 1a workspace capture-grader

A thin, dependency-free **capture-grader** for the `starting-initiatives` skill. It
is the first executable increment of the iterative skill eval harness
(`docs/plans/iterative-skill-eval-harness.md`, Stage 1a).

## What it is

A capture-grader grades **one pointed-at workspace** by reusing the existing
deterministic initiative checker (`scripts/check-initiatives.py` → `inventory`).
It is useful from the first real run, before any case corpus exists.

It is **not** a benchmark runner: it invokes no agent, runs no baseline/treatment
pair, and reports no pass-rate, statistical stability, or maturity. Those are
gated later stages (1b / Stage 0).

## What it grades

Only the **outcome** dimension — the workspace's deterministic initiative
inventory (valid records, count, per-record errors). Every other dimension
(process, invocation, quality, efficiency, environment, pair) is explicitly `N/A`;
evidence is never fabricated. This is claim-scoped validity: a result is valid for
the dimensions whose controls held.

## Usage

```sh
# Grade a workspace, retain the run under evals/runs/<skill>/iteration-<N>/
python3 evals/run/workspace_grader.py <workspace>

# Grade without writing files (prints checks.json to stdout)
python3 evals/run/workspace_grader.py <workspace> --no-emit

# Capture an optional transcript alongside the produced artifacts
python3 evals/run/workspace_grader.py <workspace> --transcript <path-to-jsonl>

# Choose a specific output dir or skill
python3 evals/run/workspace_grader.py <workspace> --out <dir> --skill starting-initiatives
```

Exit status: `0` on a clean pass (`failure_class=none`); `1` on any failure or
ungradable result; `2` if the checker cannot be loaded.

## Output

Into the output dir (default `evals/runs/<skill>/iteration-<N>/`, auto-incremented):

- `checks.json` — the layered result: `outcome` dimension (status, inventory_valid,
  count, workspace errors, per-record validity + errors), provenance, captured
  artifact list, and `failure_class` (`none` / `assertion_fail` / `evidence_error`
  / `ungradable`).
- `summary.md` — human-readable summary.
- `artifacts/initiatives/<slug>/initiative.md` — the produced initiative(s), copied.
- `artifacts/<transcript-name>` — the optional transcript, copied.

The `evals/runs/` tree is gitignored (`evals/.gitignore`): raw run artifacts are
kept outside the source tree by default, per `docs/skill-evaluations.md`.

## How it reuses the checker

The checker is `scripts/check-initiatives.py` — a hyphenated name that cannot be
`import`ed normally. The grader loads `inventory()` from its file path via
`importlib.util` (no copy, no shell-out, **no edit** to the checker). The grader
adds no parsing or validation of its own; it only layers and reports what the
deterministic checker already decides.

## Self-tests

```sh
python3 evals/run/test_workspace_grader.py
```

Deterministic fixture tests (no live agent): a valid workspace grades `pass`;
invalid variants (missing required heading, non-canonical slug, bad date,
template-placeholder remainders) grade `fail` with the right per-record errors; a
workspace with no `initiatives/` grades `ungradable`; `capture()` does not mutate
its input; `emit()` writes `checks.json` + `summary.md`; provenance is recorded.

## Scope limits

- **Stage 1a only.** No agent invocation, no paired comparison, no severity
  weighting, no `benchmark.json`, no maturity promotion, and no `d7y eval` façade
  command (all deferred by the governing plan).
- A clean grade reflects the workspace's deterministic initiative inventory only.
  It is not evidence about invocation, process, or prose quality — those need the
  gated later stages.
