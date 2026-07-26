---
title: Eval Execution Harness
type: feat
status: todo
createdAt: 2026-07-26
updatedAt: 2026-07-26
---

# Eval Execution Harness

## Summary

Implement the first executable D7Y eval harness so a skill suite can be run in isolated workspaces with and without the target skill, graded from captured evidence, and summarized against a baseline.

This document is the implementation handoff for a new agent session starting from the repository constitution.

The first backend should be Codex CLI because it is installed locally and documents non-interactive JSONL execution. Verify its live interface before implementation. Keep backend-specific command construction and event parsing isolated, but do not build a general plugin framework or support Amp and Claude in this increment.

The harness must turn the existing valid eval definitions into real comparative evidence. It must not promote skill maturity automatically or claim that a skill invoked when the backend cannot prove it.

## Problem Framing

D7Y currently has an evaluation contract, JSON Schema, definition validator, fixtures, and two provisional skill suites. It does not execute agent runs. Consequently:

- no skill has been compared with a no-skill or previous-version baseline;
- invocation, process, outcome, quality, and efficiency assertions have not been graded;
- valid eval definitions can be mistaken for evidence that a skill works;
- the repository cannot yet produce the benchmark required to promote a skill from `provisional` to `evaluated`.

A naive runner would produce invalid comparisons. D7Y's root `AGENTS.md` tells development agents to read the current skills, so using an ordinary checkout as the no-skill baseline would leak the target skill into that baseline. The harness therefore needs a neutral eval constitution and explicit target-skill isolation.

There is also a contract gap: current assertions label some natural-language statements `deterministic`, but most do not identify executable graders or structured parameters. The harness must make these assertions mechanically executable or reclassify them honestly; it must not interpret free-form prose and call the result deterministic.

## Requirements

1. **Validated input:** the CLI rejects a run before launching an agent when the selected `skills/<skill>/evals/evals.json` fails `evals/validate_skill_evals.py` or references missing fixtures.
2. **Explicit selection:** the CLI can select a skill, one or all cases, an iteration identifier, a source Git ref, and the Codex backend through documented arguments.
3. **Reproducible source:** each iteration records the source commit, target skill content hash, harness version, backend and model information, command configuration, date, and permission profile. The default run uses a committed Git ref and refuses an uncommitted source unless an explicit non-reproducible override is supplied and recorded.
4. **Fresh isolation:** every case/configuration pair starts in a separate clean workspace and fresh agent process with no state inherited from another case or configuration.
5. **Fixture safety:** fixture sources are read only from within the skill directory and destinations are staged only within the isolated workspace. Traversal, symlink escape, overwrite of harness control files, and undeclared fixture writes are rejected.
6. **Neutral constitution:** with-skill and baseline workspaces receive the same minimal eval-specific `AGENTS.md`; they do not inherit D7Y's development constitution, which references target skills and would contaminate the baseline.
7. **Skill isolation:** the with-skill workspace installs the complete target skill package into Codex's verified repository-scoped skill location. The no-skill baseline contains no installed or canonical copy of the target skill. Shared non-target repository contracts and deterministic dependencies remain equivalent.
8. **Baseline parity:** prompt, fixtures, source state, model, tools, permissions, environment policy, and resource limits are equivalent between with-skill and baseline runs except for the target skill. A previous-version baseline can substitute for no-skill when a snapshot is supplied.
9. **Least privilege:** Codex runs non-interactively with the minimum filesystem and network permissions required by the case. Commands may modify only the isolated workspace and run-artifact directory, never the source checkout.
10. **Evidence capture:** each run records raw JSONL events, stderr, exit status, final response, elapsed duration, available token usage, backend metadata, and a manifest of workspace changes. Produced files needed by graders are retained under the contract defined in `docs/skill-evaluations.md`.
11. **Honest invocation grading:** automatic invocation passes only from a backend signal proven by a capability test. If Codex does not expose skill loading, the result is `ungradable` or the assertion is reclassified; final-response wording alone is not accepted as deterministic proof.
12. **Executable deterministic assertions:** every assertion with kind `deterministic` resolves to a declared built-in or skill-local grader with structured inputs, returns pass/fail/error plus concrete evidence, and runs without model judgment.
13. **Structured qualitative grading:** rubric assertions are graded in a separate read-only agent context with schema-constrained output. Comparisons are blind to configuration labels where practical. Human assertions remain pending until explicit feedback is recorded.
14. **Required-result semantics:** a required assertion that fails, errors, is ungradable, or awaits human review prevents the case and accepted benchmark from passing. Optional assertions remain visible without determining the required result.
15. **Comparable aggregation:** the iteration benchmark reports per-case and per-configuration results, invocation false positives and negatives, dimension summaries, timing and token data when available, and deltas against baseline. Missing telemetry is represented as unavailable rather than zero.
16. **No automatic promotion:** the harness may recommend `evaluated`, `regressed`, or `retired`, but it does not modify `SKILL.md` maturity or overwrite an accepted `benchmark.json` without an explicit acceptance action.
17. **Failure preservation:** interrupted agent runs, grader failures, timeouts, and malformed traces leave inspectable artifacts and an explicit failed state; reruns use a new iteration or attempt directory rather than silently overwriting evidence.
18. **End-to-end proof:** at least one case from `starting-initiatives` completes both configurations and produces trace, grading, timing, outputs, and benchmark artifacts. Harness tests also prove that source files remain unchanged and that invalid fixture paths and malformed backend output fail safely.
19. **Documented operation:** a developer starting with `AGENTS.md` can follow a short command reference to validate suites, run one case, run a full iteration, inspect results, and understand which parts remain backend-dependent or provisional.

## Scope

### In scope

- A local command-line harness under `evals/` using Python 3 and standard-library code where practical.
- One production execution backend: Codex CLI.
- Backend capability probing before finalizing invocation and telemetry parsing.
- Clean Git-ref workspaces for with-skill and baseline runs.
- Neutral eval-specific agent instructions.
- Safe fixture staging and complete target-skill installation.
- No-skill and previous-skill baselines.
- Trace, response, timing, token, workspace-change, grading, and benchmark artifacts.
- Built-in deterministic graders needed by current suites, plus skill-local grader execution.
- Read-only structured rubric grading and pending human assertions.
- Migration of the eval schema, validator, and current suites where executable grader declarations require it.
- Focused deterministic tests and one real end-to-end comparative case.
- Updates to `docs/skill-evaluations.md` when implementation decisions refine its artifact or grading contracts.

### Out of scope

- Amp or Claude execution backends.
- A generic plugin SDK for arbitrary agent runtimes.
- Cloud execution, distributed workers, scheduling, a web UI, or CI integration.
- Parallel case execution; begin sequentially for reproducibility and debuggability.
- Statistical claims from a single run or automatic repeated-run optimization.
- Automatic skill rewriting, benchmark acceptance, or maturity promotion.
- Executing a real discovery initiative or using personal knowledge as eval input.
- Supporting network-dependent evals in the first end-to-end suite.
- Retaining every full workspace indefinitely; raw artifacts follow the repository's ignored-run policy.

## High-Level Design

### Execution flow

```text
evals.json + source ref
        │
        ▼
validate suite and backend capabilities
        │
        ▼
create immutable iteration manifest
        │
        ├───────────────┐
        ▼               ▼
with-skill workspace    baseline workspace
install target skill    remove target skill
stage same fixtures     stage same fixtures
neutral AGENTS.md       neutral AGENTS.md
        │               │
        ▼               ▼
fresh Codex process     fresh Codex process
        │               │
        └───────┬───────┘
                ▼
capture traces, responses, telemetry, and workspace changes
                │
                ▼
deterministic graders → rubric grader → human pending state
                │
                ▼
case grading → iteration benchmark → promotion recommendation
```

### Components

Keep the implementation small and separate by responsibility rather than creating a framework:

- **CLI/orchestrator:** parses run selection, validates prerequisites, creates the iteration manifest, and coordinates sequential runs.
- **Workspace builder:** materializes a Git ref, replaces root instructions with a neutral eval constitution, excludes the target skill from the baseline, installs it for with-skill, and stages fixtures safely.
- **Codex executor:** owns only verified Codex command construction, process lifecycle, JSONL parsing, timeout handling, and telemetry extraction.
- **Artifact recorder:** writes the directory contract from `docs/skill-evaluations.md`, captures final responses and filesystem changes, and never mutates the source checkout.
- **Grading engine:** dispatches declared deterministic graders, invokes a separate structured rubric grader, preserves human-pending assertions, and records evidence for every result.
- **Aggregator:** builds case summaries and the iteration benchmark without changing accepted skill metadata.

Prefer plain data structures and subprocess boundaries. Introduce an adapter protocol only to isolate Codex-specific behavior that a future backend would necessarily replace; do not add runtime discovery, registration, or inheritance hierarchies.

### Workspace and baseline model

Use a committed source ref as the reproducible seed. The orchestrator reads the selected suite and fixtures from the source repository before creating workspaces.

Both configurations receive the same source material needed by the task, fixtures, neutral instructions, and policy. Remove the target skill's canonical directory from both workspaces after harvesting its suite and dependencies; install the complete package only in the with-skill runtime location. If a target skill depends on a script inside its package, that script travels with the installed package. Repository-level contracts such as `initiatives/README.md` remain available when the case needs them.

The neutral `AGENTS.md` should instruct the eval agent to execute only the supplied task inside the workspace, preserve evidence, avoid reading the external source checkout, and not infer access to undeclared skills. It should be identical across configurations.

### Grader contract

Evolve the schema deliberately so deterministic assertions identify executable graders and structured parameters. Prefer a small set of built-ins for repeated mechanical facts—skill invocation when observable, path existence or absence, command occurrence, exit status, JSON validity, and initiative checker result. Use skill-local scripts for domain-specific checks.

Every grader receives immutable run metadata, trace paths, output/workspace paths, assertion configuration, and configuration identity through a documented JSON input. It returns structured JSON with status, evidence, and optional diagnostics. Graders receive read-only access to captured artifacts and must not repair outputs.

Rubric grading receives only the prompt, expected outcome, assertion, and captured evidence required for judgment. For paired quality comparisons, hide with-skill/baseline labels. Validate grader responses against a JSON Schema before accepting them.

### Artifact compatibility

Start from the layout in `docs/skill-evaluations.md`. Add only files proven necessary by implementation, such as `manifest.json`, `final.md`, `stderr.log`, `workspace-diff.json`, or an attempt marker. Update that canonical document in the same change if the implemented layout differs.

## Implementation Units

### 1. Codex capability spike and contract decisions

Verify the installed Codex CLI's non-interactive flags, repository-scoped skill location, JSONL event shapes, skill-invocation observability, sandbox controls, final-response capture, token telemetry, and timeout behavior. Record fixture traces under ignored eval runs and document conclusions in the implementation notes or canonical eval contract.

**Acceptance criteria:** a disposable positive and negative skill run establishes which required signals are observable; unsupported signals are explicitly represented rather than inferred.

**Dependencies:** existing skill packages and eval contract.

### 2. Eval schema and grader declaration

Define the minimum structured grader declaration, update the schema and dependency-free validator, and migrate both current suites. Preserve the distinction among deterministic, rubric, and human assertions.

**Acceptance criteria:** all current suites pass validation; a deterministic assertion without an executable grader fails validation; unsafe grader and fixture paths are rejected.

**Dependencies:** Unit 1 for invocation capabilities and trace fields.

### 3. Reproducible workspace builder

Materialize isolated workspaces from a Git ref, apply neutral instructions, stage fixtures, remove target-skill leakage, and install the target package only for with-skill runs.

**Acceptance criteria:** paired workspace manifests differ only by declared configuration differences; traversal and symlink-escape tests fail safely; the source checkout remains byte-for-byte unchanged.

**Dependencies:** Unit 2 contracts.

### 4. Codex execution and evidence capture

Implement the sequential executor, timeout and interruption handling, trace parsing, final response capture, telemetry recording, and workspace-change manifest.

**Acceptance criteria:** synthetic success, agent failure, malformed JSONL, and timeout cases produce complete explicit run states and preserve inspectable artifacts.

**Dependencies:** Units 1 and 3.

### 5. Grading and aggregation

Implement built-in and skill-local deterministic graders, structured read-only rubric grading, human-pending states, required-result semantics, and iteration aggregation.

**Acceptance criteria:** graders require evidence, invalid grader output fails closed, missing telemetry remains unavailable, blind pair labels are enforced where configured, and benchmark deltas reproduce from grading artifacts.

**Dependencies:** Units 2 and 4.

### 6. End-to-end CLI and documentation

Connect selection, validation, execution, grading, and aggregation behind the documented CLI. Run one `starting-initiatives` case with and without the skill, then document actual commands and limitations.

**Acceptance criteria:** Requirement 18's end-to-end artifacts exist under an ignored iteration directory; focused tests pass; `docs/skill-evaluations.md` matches implemented behavior; no skill is promoted automatically.

**Dependencies:** Units 1–5.

## Risks & Dependencies

- **Invocation observability:** Codex may inject skills without emitting an explicit event. This blocks deterministic invocation grading unless another backend-supported signal exists. Do not use self-reported final text as proof; reclassify or mark ungradable.
- **Baseline contamination:** root `AGENTS.md`, canonical target skill files, user-global skills, or agent-global configuration may leak capability into the baseline. Neutral instructions, target removal, environment isolation, and manifesting loaded configuration are required.
- **Global agent state:** Codex may load user-level instructions or skills outside the workspace. The capability spike must identify suppression or isolation controls; otherwise record this as an unresolved validity limitation.
- **Permission safety:** agent CLI automation can mutate files or use network credentials. Restrict execution to disposable workspaces with least privilege and avoid forwarding unrelated secrets.
- **Free-form deterministic assertions:** current descriptions are not executable specifications. Schema migration is required before honest automated grading.
- **Rubric bias and leakage:** a judge can prefer the labeled skill output or share context with the executing agent. Use separate read-only contexts, structured output, and blind labels.
- **Model and CLI drift:** event formats, skill-loading behavior, and token telemetry can change. Capture versions, fail on unknown required event shapes, and keep parser fixtures.
- **Cost and latency:** paired agent runs plus rubric grading multiply usage. Begin sequentially, expose case selection, record costs, and avoid retries that conceal failures.
- **Reproducibility:** uncommitted source, external network responses, nondeterministic model behavior, and mutable global configuration reduce comparability. Default to committed refs and record every known variable.
- **Repository contract coupling:** implementation may reveal that `docs/skill-evaluations.md` or schema v1 is insufficient. Update canonical contracts deliberately and migrate both suites in the same unit.
- **Dependencies:** Python 3, Git, Codex CLI, an authenticated model backend, and local filesystem isolation. Avoid new Python packages unless they remove more complexity than they introduce.

## Sources/References

### D7Y canon and current implementation

- `AGENTS.md` — always-loaded workbench development constitution.
- `docs/discovery-workbench.md` — architecture, boundaries, and evidence principles.
- `docs/discovery-workbench-principles.md` — intent-to-evidence and autonomy principles.
- `docs/skill-evaluations.md` — canonical eval organization, lifecycle, and maturity contract.
- `evals/skill-evals.schema.json` — current suite schema.
- `evals/validate_skill_evals.py` — current dependency-free definition validator.
- `skills/starting-initiatives/evals/evals.json` — first end-to-end target suite.
- `skills/writing-great-skills/evals/evals.json` — meta-skill suite and second migration target.
- `skills/starting-initiatives/scripts/check_initiatives.py` — deterministic domain check available to graders.

### External references

- [Agent Skills — Evaluating skill output quality](https://agentskills.io/skill-creation/evaluating-skills)
- [OpenAI — Testing Agent Skills Systematically with Evals](https://developers.openai.com/blog/eval-skills)
- Verify current Codex CLI behavior from its installed `--help` output and authoritative documentation before relying on command flags or event fields.
