---
title: Minimal Skill Eval Runner
type: feat
status: todo
createdAt: 2026-07-26
updatedAt: 2026-07-27
---

# Minimal Skill Eval Runner

## Summary

Implement the smallest local runner that can produce inspectable comparative evidence for D7Y's current skills. For one selected case, it runs the same prompt in fresh isolated workspaces with and without the target skill, captures what happened, applies a few trusted deterministic checks, and records unresolved judgment honestly.

This is D7Y infrastructure, not a general eval framework. The first increment supports one verified agent executor, a no-skill baseline, sequential runs, and the assertions needed by the current suites. It does not automate qualitative judgment, benchmark acceptance, or skill maturity.

Claude Code 2.1.218 is the selected first executor because a recorded pre-delegation capability spike proved the bounded command and event contract below—not because Claude Code implements the runner. The spike established fresh non-interactive execution, controlled customization and target treatment, a target-specific `Skill` tool event, machine-readable tool and result evidence, and observed runtime metadata under `claude-sonnet-5`. Implement only this proven executor. Do not build a multi-backend abstraction in this increment.

Passing the eval-runner gates establishes only compatibility with this bounded eval execution contract. It does not establish complete first-class D7Y runtime support on that host.

## Problem Framing

D7Y already has an evaluation contract, schema, validator, fixtures, and two provisional skill suites. It cannot yet execute them. Static validity therefore risks being mistaken for evidence that a skill invokes correctly or improves an outcome.

The next uncertainty is narrower than "how should D7Y run arbitrary evals?":

> Can D7Y produce one valid, reproducible with-skill versus no-skill comparison whose evidence is sufficient to inspect and mechanically check?

The comparison is invalid if ordinary runtime discovery exposes the target skill to the baseline through the staged workspace, instructions, user-global configuration, plugins, or another skill root. It is also invalid if the harness stages or injects expected outputs, assertions, fixture source directories beyond the declared case inputs, graders, or benchmarks into agent-visible runtime roots. Controlled staging, runtime-state separation, and provenance are therefore required; generic execution and grading extensibility are not.

This first increment controls the agent context and staged inputs; it is not an OS, filesystem, process, network, or credential sandbox. It does not prove that an adversarial process could not inspect another path readable by the host user. If literal filesystem unreadability or process isolation is required to qualify the selected runtime, stop and make an OS sandbox a separate explicit prerequisite rather than implying that temporary workspaces or CLI permissions provide it.

Current deterministic assertions are natural-language claims rather than executable declarations. Define only the structured checks supported by evidence observed in the first real traces. Do not design a broad grader protocol in advance.

## Success Criteria

1. A developer can validate a suite and run one selected case from a committed source revision through a documented Python command under `evals/`.
2. The case runs once with the target skill and once without it, in separate clean workspaces and fresh agent contexts.
3. A committed runtime capability record and sanitized parser fixtures establish the selected runtime's declared command posture, prove target-skill availability only in the with-skill configuration, prove a target-specific invocation signal, and distinguish declared controls from runtime-observed skills, tools, model, plugins, MCP servers, permission mode, and unsupported telemetry.
4. Eval definitions, expected outcomes, assertions, fixture source directories beyond staged case inputs, graders, benchmarks, and harness control files are absent from every staged workspace, runtime skill payload, and runtime-discovered configuration root.
5. Prompt, declared fixtures, repository seed, model or mode, tools, permissions, and resource limits are equivalent across the pair except for the target skill treatment.
6. The harness reads run inputs from committed Git objects, never uses the source checkout as a run workspace, does not pass its path to the agent, and records before-and-after source status and selected-object hashes. Fixture traversal, committed symlink escape, and overwrite of harness control files fail before agent execution.
7. Each run preserves the raw event stream, stderr, exit status, final response, elapsed duration, available usage telemetry, runtime metadata, and retained workspace changes.
8. A small fixed set of trusted deterministic checks reports `pass`, `fail`, `error`, or `ungradable` with concrete evidence. Missing telemetry is unavailable, not zero.
9. Pair validity, treatment checks, with-skill assertion results, and baseline observations are reported separately. Rubric and human assertions remain `pending`; a required pending, errored, failed, or ungradable with-skill assertion prevents that case from being represented as passing, while an expected baseline failure does not invalidate an otherwise valid pair.
10. The generated summary reports observations and baseline deltas but makes no maturity recommendation and does not modify `SKILL.md` or an accepted `benchmark.json`.
11. At least one positive and one negative `starting-initiatives` case complete both configurations. The D7Y capability installation, target skill installation, target workspace, and process starting directory are distinct; both configurations receive the same recorded capability installation and explicit absolute target root.
12. Focused tests prove safe fixture handling, additive workspace construction, runtime-state separation, target-skill treatment isolation, source-checkout non-use, and safe failure on malformed executor output or unknown required events.
13. The implemented command and known runtime limitations are documented, and canonical eval documentation is updated only where actual behavior refines its contract.

## Scope

### In scope

- A local Python 3 command under `evals/`, using the standard library where practical.
- A pre-delegation capability spike followed by exactly one implemented agent executor whose command and event contract are already recorded.
- Claude Code as the first runtime to probe because it is the first intended product host binding; Amp and Codex are fallbacks for internal eval infrastructure only, not production dependencies selected in advance.
- A committed Git revision as the source of the suite, fixtures, runtime skill payload, deterministic capability installation, and an allowlisted workspace seed.
- Separate with-skill and no-skill workspaces with neutral eval instructions.
- Separate per-run runtime state, plugin or skill roots, and process contexts.
- One recorded D7Y CLI capability installation exposed identically to both configurations and separately from the target workspace and target skill installation.
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
- Claims of adversarial filesystem, process, network, credential, or host-user isolation without a separately approved OS sandbox.
- A top-level `d7y eval` product capability; this runner is contributor infrastructure.

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

Before creating a concrete implementation prompt or task worktree, Amp and the human used a disposable synthetic skill and positive and negative prompts to probe Claude Code. The spike demonstrated:

1. fresh non-interactive contexts with no session reuse;
2. declared project-only settings, separate runtime state, empty MCP configuration, and runtime-observed skills, plugins, tools, model, and permission mode;
3. the target skill present exactly once with-skill and absent from every baseline skill root;
4. positive and negative invocation observable from a documented event or other runtime-owned signal rather than final-response wording;
5. machine-readable tool activity and final response capture;
6. a controlled synthetic-probe tool and permission set and honest documentation of any host-readable paths that are not technically sandboxed;
7. runtime-observed model, effective skill set, plugins, MCP servers, tools, permission mode, result, and available usage metadata sufficient to scope the synthetic result.

The spike did not directly observe effective instructions, hooks, auto-memory, session-persistence behavior, effort, hidden cache provenance, or all mutable host state. Treat the corresponding flags, settings, configuration-root paths, and file hashes as declared invocation inputs rather than runtime-reported facts. The first vertical slice must use suppression canaries to test instruction and global-skill leakage and must stop on a failed canary.

The selected Claude Code 2.1.218 executor contract is:

- launch each arm as a new process with a distinct temporary `CLAUDE_CONFIG_DIR` and `--no-session-persistence`;
- use `--setting-sources project` plus a harness-owned `--settings` file that sets `disableBundledSkills: true` and `includeGitInstructions: false`;
- construct a scrubbed child environment from a minimal platform base and the top-level string-to-string `env` object in the current user's `~/.claude/settings.json`, recording the source and retained key names but never values; apply imported values first and then override harness-owned `CLAUDE_CONFIG_DIR`, `PWD`, capability `PATH`, temporary-directory, and related control variables; do not load user permissions, hooks, model, effort, plugins, skills, or other settings; fail before launch if any retained value exposes the source checkout, skill source, or eval source path;
- use a session-only `--plugin-dir` payload containing the target skill with-skill and an equivalent empty plugin baseline;
- invoke `--print --verbose --output-format stream-json --no-session-persistence`, `--strict-mcp-config --mcp-config '{"mcpServers":{}}'`, `--permission-mode dontAsk`, `--model claude-sonnet-5`, and `--effort low`; use exactly `Skill` for the synthetic parser contract and exactly `Skill,Read,Write,Edit,Bash` in both arms of the first real slice, stopping rather than broadening the set if that slice cannot run;
- resolve the executable once, require `claude --version` from that executable to report `2.1.218`, and record its path and version separately from the event stream;
- accept an arm only when `system.init` reports the exact requested model, empty MCP servers, the exact tool set, the expected session plugin, the target skill present only with-skill, and no unexpected skill beyond the built-in `doctor` observed in both arms;
- prove automatic invocation only from an assistant `tool_use` content block whose `name` is `Skill` and whose `input.skill` equals the namespaced target; use the absence of that event for the with-skill negative control and baseline treatment evidence;
- take final response, available usage, actual model/provider, turn count, permission denials, and terminal status from the `result` event, failing safely when required fields or event shapes differ; measure elapsed duration around the child process with a monotonic clock because the observed result event did not expose it;
- enforce a ten-minute timeout per arm by terminating the child process group, waiting five seconds, then killing the group if needed; retain an explicit timeout result and partial stdout and stderr.

`--bare` was rejected for the runner contract: it suppressed project and user customization and exposed session-plugin availability, but only guaranteed explicit `/plugin:skill` expansion and did not expose the `Skill` tool needed for automatic invocation. `--safe-mode` disables skills and cannot be the with-skill posture. `--disable-slash-commands` remains unsuitable as an asymmetric baseline treatment. The `sonnet` alias resolved to `glm-4.7` in this environment, so the selected contract uses the full `claude-sonnet-5` identifier and verifies the actual model in both init and result evidence.

A skill listing or initialization record proves availability, not invocation. Qualification requires a runtime-owned event that uniquely identifies use of the target skill for the positive prompt and its absence for the negative prompt; final-response wording and a good outcome prove neither. If Claude Code fails a core isolation or observability gate, record the failed gate and return the decision to Amp and the human before probing Amp or Codex strictly as internal eval infrastructure. Stop if no installed runtime can support an honest comparison.

The selected runtime's command construction and event parsing may live in one clearly named module or function. Do not introduce a common executor interface until a second runtime is actually required.

### Workspace and treatment boundary

Resolve the selected Git ref to a commit first and read all run inputs from that immutable object, not partly from the working tree. Record the source checkout status and relevant object hashes before and after execution, but never use that checkout as an agent workspace or capability installation.

Build both workspaces additively from the same allowlisted repository seed. For the first `starting-initiatives` slice, begin with the committed initiative organization contract, identical neutral eval instructions, and declared fixtures; do not copy a broad checkout and attempt to subtract agent-readable material. Add the smallest structured repository-context declaration needed to make that seed explicit and validate every source and destination before staging.

Create separate per-configuration plugin or skill roots and runtime-state directories. Install a runtime payload only for the with-skill agent containing `SKILL.md` and execution-time references; give the baseline an equivalent empty treatment location. Never include `evals/`, fixture sources, expected outcomes, assertions, graders, benchmarks, or harness control files in either runtime payload or runtime-discovered root.

Materialize one minimal D7Y capability installation from the selected source commit, containing the `d7y` façade and shared initiative implementation. Expose that exact installation on `PATH` identically to both configurations while keeping it separate from the target workspace, target skill installation, process starting directory, and source checkout. For `starting-initiatives`, record the resolved executable and source revision, run from a third directory, pass the target workspace as an explicit absolute `--root`, and capture arguments, exit status, and JSON result. Do not expose the source checkout's `./d7y` directly.

The run manifest records controllable inputs and the declared treatment delta. It does not claim that stochastic outputs, timestamps, service conditions, or generated identifiers are identical.

### Minimal checks and result semantics

Inspect the first captured traces before changing the eval schema. Then add only the declarations needed for observed, mechanically verifiable facts. Initial trusted checks may include:

- verified target-skill invocation event, if the runtime exposes one;
- command occurrence and exit result;
- path existence, absence, or count;
- JSON or schema validity;
- the existing initiative checker result.

Checks are harness-owned Python functions, not executable plugins. They inspect retained artifacts without repairing them and return a status plus concrete paths, events, command results, or diagnostics as evidence.

Keep four result layers distinct:

1. **Pair validity** fails on treatment leakage, parity failure, uncontrolled runtime state, a missing configuration, or malformed required executor evidence.
2. **Treatment checks** prove target availability with-skill and absence in the baseline; they are harness-owned rather than authored baseline outcome assertions.
3. **With-skill assertions** apply the case's invocation, process, outcome, quality, and efficiency requirements. Positive invocation checks require the target event; negative controls require its absence even though the target is available.
4. **Baseline observations** report comparable process and outcome facts. A baseline failure may demonstrate skill value and does not by itself invalidate the pair.

The trace-backed assertion that the agent ran `d7y initiatives list` before matching and `check` after creation is separate from an independent harness-run post-execution initiative check. The latter proves outcome validity, not that the agent followed the skill process.

An executor without observable invocation does not pass qualification. Only if the human explicitly approves an outcome-only run may invocation assertions be `ungradable`; such a run cannot satisfy this plan's invocation success criteria. Rubric and human assertions remain `pending`. The summary may say that the observed with-skill run outperformed the observed baseline on particular checks, but one pair is insufficient for a stable improvement or maturity claim.

### Command ownership

Expose the first increment through one documented Python entry point under `evals/` and document it in `DEVELOPMENT.md`. Do not add a top-level `d7y eval` command: skill evaluation is contributor infrastructure, while top-level `d7y` commands are user-facing deterministic capabilities. If later use justifies a façade, add it under `d7y dev` in a separate change rather than duplicating runner behavior.

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

Commit the capability record and small sanitized event fixtures needed to test the selected runtime parser. Do not commit raw model traces or credentials merely to preserve the spike.

## Implementation Sequence

### 0. Pre-delegation Claude Code capability spike — complete

Amp ran a disposable positive and negative synthetic skill case through Claude Code with controlled settings, separate runtime state, and session-only skill installation. The spike did not run through `scripts/delegate-claude.sh`; that launcher governs implementation handoffs and is not the eval executor. The selected contract is recorded above and sanitized parser constructions live under `evals/fixtures/claude-code-2.1.218/`.

Observed evidence: the positive arm emitted a target-specific `Skill` tool event and `D7Y-PROBE:THETA-2`; the equivalent empty-plugin arm exposed no target skill or target event; the with-skill negative prompt exposed the target but emitted no target event. Runtime events reported `claude-sonnet-5`, empty MCP, fresh session IDs, `dontAsk`, and the configured tools. No persistence and low effort were supplied command controls, not runtime-reported facts. Project-only execution required importing the reviewed top-level user environment because isolated configuration otherwise failed authentication. The unavoidable `doctor` skill remained visible identically in both arms. Claude's native `plugin eval` command was present but unavailable behind an early-access gate and is not part of the implementation contract.

The committed JSONL files are sanitized parser constructions based on the observed event shapes, not verbatim raw traces or independent capability evidence. They preserve behavior-critical target, non-target, model, plugin, tool, permission, MCP, session, result, and usage structure while replacing volatile identifiers and paths and omitting sensitive values. The capability claim rests on the live spike summarized here; parser fixtures only make that selected shape testable.

Unsupported or bounded claims: no adversarial filesystem/process isolation was established; no timeout or malformed-stream behavior was exercised against the live CLI; instruction, global-skill, and hidden-state suppression still require vertical-slice canaries; the negative prompt was not run under the final restricted synthetic tool list; and the real `starting-initiatives` tool set and D7Y capability binding remain implementation qualification work. The first real pair must stop if its fixed tools, permissions, D7Y command binding, canaries, or process-tree timeout do not work. One positive and one negative synthetic run establish compatibility, not stochastic reliability or first-class binding status.

### 1. Paired capture vertical slice

Implement committed-ref resolution, additive workspace construction, neutral instructions, separate runtime state, the proven runtime payload contract, the recorded D7Y capability installation, sequential execution, and raw artifact capture. Run the positive `starting-initiatives` creation case in both configurations. Ensure eval material is absent from staged and runtime-discovered roots and the capability installation is available identically to both configurations.

**Complete when:** both runs are inspectable, the target treatment is proven, changed files are retained, malformed stream and timeout states fail explicitly, and the source checkout is unchanged.

### 2. Evidence-informed deterministic checks

Inspect the captured events and outputs, define the smallest structured check declarations they support, and update the schema, validator, and current suites consistently. Implement only trusted built-ins required by the current cases. Keep unsupported deterministic assertions `ungradable` and rubric or human assertions `pending`.

**Complete when:** every executed deterministic declaration resolves to a known built-in, every result cites evidence, unsafe declaration parameters fail validation, and the summary can be regenerated from captured artifacts.

### 3. Current-suite proof and documentation

Run at least the positive creation case and negative naming control through both configurations. Document validation, one-case execution, suite execution if implemented, artifact inspection, and known runtime limitations. Align `docs/skill-evaluations.md` with proven behavior without accepting a benchmark or changing maturity.

**Complete when:** focused tests pass, the two comparative cases produce factual summaries, source safety is demonstrated, and the documentation distinguishes schema validation, an observed run, and evidence sufficient for a maturity decision.

Focused acceptance cases must include suppression canaries for user or project instructions and a fake global skill; target availability only with-skill; positive target invocation only with-skill; no target invocation for the negative control; an allowlisted seed manifest; absence of eval and control material from staged and runtime roots; the recorded `d7y` capability path and absolute target root; separate agent-command and independent post-run checker evidence; safe rejection of traversal, committed symlinks, control-path collisions, malformed streams, and unknown required events; and timeout termination of the complete child process tree with an explicit retained timeout result.

## Risks and Stop Conditions

- **Claude Code cannot isolate global state:** do not weaken the baseline; record the failed gate and return the decision to Amp and the human before probing the next runtime strictly as internal eval infrastructure.
- **Invocation is not observable:** do not accept self-report as evidence. An invocation-observability failure is a failed qualification gate: record it and return the decision to Amp and the human before probing another host strictly as internal eval infrastructure. If the human explicitly approves an outcome-only run, it may produce scoped outcome evidence, but it remains unqualified for invocation evaluation and must not be represented as passing the executor qualification gate.
- **Eval leakage:** fail before execution if a staged workspace, runtime payload, or runtime-discovered root contains eval definitions, assertions, graders, expected outcomes, benchmarks, fixture source directories, or harness control files.
- **Instruction leakage:** fail the comparison when effective instruction or skill sources cannot be enumerated or suppressed sufficiently to prove the treatment.
- **D7Y capability binding is unavailable:** do not substitute a repository-relative checker or the source checkout's executable. Stop if an equivalent recorded capability installation cannot be exposed to both configurations independently of the target workspace.
- **Skill resource paths break after installation:** make the runtime payload portable before continuing; do not repair it by exposing skill-source or eval directories.
- **Isolation requirement expands:** if trusted controlled staging is insufficient and literal host-path unreadability is required, stop and return an explicit OS-sandbox decision rather than extending the runner implicitly.
- **Model or CLI drift:** capture versions and keep small parser fixtures from the capability spike; fail safely on unknown required event shapes.
- **Stochastic overclaim:** report raw observations from a single pair, never stable improvement or maturity.
- **Scope growth:** defer any second executor, arbitrary grader, rubric agent, lifecycle manager, or service until observed D7Y eval failures demonstrate the need.

## Sources and Current Inputs

- `AGENTS.md` — workbench-development constitution.
- `docs/discovery-workbench.md` — thin-harness, fat-skills, deterministic-foundation architecture.
- `docs/discovery-workbench-principles.md` — evidence and autonomy principles.
- `docs/skill-evaluations.md` — canonical skill evaluation and maturity contract.
- `docs/plans/runtime-initiative-cli.md` — completed initiative capability contract and deferred binding evidence.
- `docs/plans/auditable-claude-delegation.md` — development launcher evidence and its explicit non-sandbox boundary.
- `evals/skill-evals.schema.json` — current suite schema.
- `evals/validate_skill_evals.py` — current dependency-free validator.
- `skills/starting-initiatives/evals/evals.json` — first vertical-slice suite.
- `skills/writing-great-skills/evals/evals.json` — second current suite to migrate after the check declaration is proven.
- `scripts/check-initiatives.py` — shared deterministic initiative capability used by the first case (exposed via `d7y initiatives list`/`check`).
- [Agent Skills — Evaluating skill output quality](https://agentskills.io/skill-creation/evaluating-skills)
- [OpenAI — Testing Agent Skills Systematically with Evals](https://developers.openai.com/blog/eval-skills)

## Implementation Feedback

### Execution posture

Eighth incremental correction (preflight redaction gate over-rejection), on
branch `work/eval-execution-harness`, base `935a869`. The seventh correction's
preflight redaction gate rejected every token shorter than 8 characters and
every all-digit token. That rule was wrong: the real qualification environment
imports exactly those shapes — 7-character model ids (`glm-4.7`), all-digit
timeouts (`API_TIMEOUT_MS`, `CLAUDE_CODE_AUTO_COMPACT_WINDOW`), and the
one-digit flag `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1` — so the corrected
runner rejected the valid proxy environment before it could execute Claude and
no live qualification artifact could be produced. The gate is now permissive:
structural redaction (`redact_obj` preserves non-string scalars; `redact_jsonl`
parses and re-serializes each event line) is what keeps retained JSON valid for
arbitrary token values, so short/numeric/literal values are permitted and fully
scrubbed from every string position. `validate_redaction_tokens` now only
rejects non-string/empty tokens (a defensive invariant that never fires for
real collected values). The source-mutation correction (blocker 2) is unchanged
and its public test is retained. Verified offline that the real
`~/.claude/settings.json` imported values now pass the gate.

Seventh incremental correction (final-review blockers), on branch
`work/eval-execution-harness`, base `7f4e91d`. Two final-review blockers in the
retained-evidence and check-semantics contracts, both reproduced against the
authoritative live artifacts at
`/tmp/d7y-live-positive-20260729-model-full/` (`jq empty` failed on both
`trace.jsonl` files with `Invalid numeric literal`, because numeric fields such
as `estimated_tokens` became bare `<redacted>` tokens). No runner or plan
redesign; no scope expansion; no change to the `--model claude-sonnet-5`
contract, plugin, permission, prompt, D7Y command, assertion, or baseline
semantics.

Sixth incremental correction (process-evidence contract), on branch
`work/eval-execution-harness`, base `9d9a33b`. The process assertion requires
every Bash tool use to have exactly one later result and requires exactly one
supported, complete `d7y initiatives list` and one `d7y initiatives check`
command for the arm, with the list before the check. Correlated non-D7Y setup
commands such as `pwd` and `mkdir` are retained in evidence and are allowed;
duplicate, malformed, wrapped, or wrong-root D7Y attempts remain ungradable.
This keeps the skill test about the required D7Y behavior while preserving
strict evidence correlation and command-shape validation.

Fifth incremental correction (live-binding defect pass), on branch `work/eval-execution-harness`, base `7cea204`. Launcher model alias `opus`; routed assistant model in this environment is GLM-5.2. The runner's requested contract model is `claude-sonnet-5`; the only routed assistant event supported by committed capability evidence is `glm-4.7`. No runner or plan redesign; no scope expansion. This correction responds to three runtime-binding defects exposed by the retained live qualification artifacts at `/tmp/d7y-live-positive-20260728-live/` and `/tmp/d7y-live-negative-20260728-live/`.

### Files changed (this correction)

- `evals/run_eval.py` —
  - `redact_jsonl` (new) parses each complete JSON event line, recursively
    redacts only string keys and string values via `redact_obj`, and re-serializes
    it as valid JSON, preserving numbers, booleans, nulls, arrays, and object
    structure. Non-JSON/blank lines are redacted safely as raw text. `write_jsonl`
    (new) applies it; `finalize_arm` writes `trace.jsonl` through `write_jsonl`
    instead of raw `write_text`, so retained stream-json stays parseable.
  - `_unsafe_redaction_token` and `validate_redaction_tokens` (new) atomically
    reject imported environment values that are unsafe to apply to arbitrary raw
    text (too short, a JSON literal, all-digit, or devoid of alphanumeric
    characters) without echoing the value. `run_preflight` calls it after
    collecting imported tokens and before `output_dir.mkdir`, so no output root
    or partial staging is created on rejection. *(Revised in the eighth
    correction: this content-based rule rejected the real qualification
    environment — short model ids, numeric timeouts, the flag `1` — and was
    replaced by a permissive defensive invariant, since structural redaction
    makes content rejection unnecessary. See the eighth correction above.)*
  - `compute_checks` gains a `source_mutated` parameter; when true it records a
    `"source checkout mutated during the run"` pair-validity error, so a mutated
    source is represented in `checks.json` (`pair_validity: fail`,
    `case_pass: false`) and not only in the exit status. `main` computes
    `source_status_after` before each `compute_checks` call and passes
    `source_mutated`; `finalize_run` reuses an already-computed after-status.
- `evals/test_run_eval.py` — 96 tests (was 89). Added `make_jsonl_redaction_fake`
  (secret in stdout/stderr/JSONL values, keys, nested metadata, workspace
  contents, filenames, symlink targets, alongside numeric/boolean/null/array
  fields) and `make_source_mutator_fake` (valid pair that mutates the source
  checkout). New public-CLI tests prove the JSONL trace stays line-parseable with
  typed fields preserved and no leak; unsafe imported values are rejected
  pre-output with no leak; and source mutation flips `pair_validity` to fail and
  `case_pass` to false with full finalization. New unit tests cover
  `redact_jsonl` (type preservation + malformed-line handling) and
  `validate_redaction_tokens` (safe accepted; unsafe rejected without leaking).
- `docs/plans/eval-execution-harness.md` — this section.

### Implemented command

```sh
python3 evals/run_eval.py --source-repo <repo> --suite <repo-relative-evals.json> \
  --case <case-id> --output <dir> [--commit <ref>] [--claude <path>] [--dry-run]
```

### Defects corrected (proven by tests)

1. **Redaction corrupted retained JSONL.** Raw substring redaction turned
   numeric fields (e.g. `estimated_tokens`) into bare `<redacted>` tokens,
   invalidating `trace.jsonl` (`jq empty` parse error). `redact_jsonl` now
   redacts structurally — only string keys/values — so numbers, booleans, nulls,
   arrays, and structure survive and every retained line stays valid JSON.
   `test_jsonl_trace_stays_parseable_and_types_preserved_under_redaction`
   independently scans the whole output tree and captured stdout/stderr for a
   synthetic secret, then proves every retained JSONL line parses and that
   numeric/boolean/null/array fields keep exact types while the secret is gone;
   `test_redact_jsonl_preserves_types_and_redacts_strings` and
   `test_redact_jsonl_malformed_line_redacted_safely` prove the unit behavior
   including malformed-line raw redaction.
2. **Unsafe imported values were silently applied.** A low-entropy imported env
   value (short, numeric, a JSON literal, or punctuation-only) used as a raw-text
   redaction token would broadly collide and corrupt output.
   `validate_redaction_tokens` rejects such values atomically before any write,
   without leaking them. *(Revised in the eighth correction: the content-based
   rejection was removed because it rejected the real environment; structural
   redaction now guarantees safety for all string values. Replaced by
   `test_real_shaped_imported_values_permitted_and_fully_redacted`, which proves
   real-shaped values are permitted and fully scrubbed while JSONL stays
   parseable and typed.)*
3. **Source mutation did not invalidate machine-readable checks.** `compute_checks`
   previously ran before post-run source integrity was incorporated, so
   finalization could record a mutation warning and nonzero exit while
   `checks.json` still said `pair_validity: pass` and `case_pass: true`. A
   detected source mutation is now a pair-validity failure that blocks
   `case_pass`, with summary and checks agreeing with the exit status; source
   evidence and full finalization are preserved. `test_source_mutation_invalidates_checks`
   drives a controlled executor that mutates the source checkout and asserts
   nonzero exit, `pair_validity: fail`, `case_pass: false`, the exact
   source-integrity pair error with no secret, summary agreement, distinct
   before/after source hashes, and a complete artifact inventory (both arms,
   checker evidence, manifest, summary). The existing `test_source_status_evidence_recorded`
   is retained but recording alone is no longer treated as sufficient.

### Preserve (no regression)

Neutral prompts and exact argv (including `--tools Skill,Read,Write,Edit,Bash`
and `--permission-mode dontAsk`); metadata-only plugin manifest; harness
permission allow list; complete recursive redaction of contents, filenames,
directory names, and symlink targets (now structural for JSONL); every-Bash
correlation; strict runtime metadata; canary detection; atomic preflight;
complete inventories for every outcome; timeout/process-group reaping;
source-before/after evidence; independent-checker exception containment; exact
assertion dispatch; the complete D7Y result-shape gate; unsupported-trace
`ungradable` semantics — all retained and still covered by the prior public tests.

### Exact verification results

- `python3 evals/validate_skill_evals.py` — both suites VALID.
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s evals -p 'test_*.py' -v` — 96 tests, OK.
- `./d7y validate` — evals and initiatives valid (rc=0).
- `git diff --check` — clean (rc=0).
- `git diff --check main...HEAD` — clean (rc=0).

### Deferred live gates / residual risk

- The existing live artifacts are NOT claimed repaired; a new authoritative live
  run is required after this correction. Offline fakes prove contract mechanics
  only — structural JSONL redaction, preflight rejection of unsafe tokens, and
  source-mutation check invalidation — not that the live Claude 2.1.218 runtime
  emits a now-clean trace. The actual Claude runtime remains a live gate.
- **Structural redaction boundary:** `redact_jsonl` only preserves types for
  lines that parse as JSON. A genuine non-JSON line (rare for stream-json) is
  scrubbed as raw text and need not remain parseable; this is intentional and is
  covered by the malformed-line unit test. Raw `stderr.txt` remains raw-text
  redacted (stderr is not structured JSON).
- **Token-safety rule:** *(eighth correction)* the preflight no longer rejects
  values by length or digit content; structural redaction makes any string value
  safe and the real environment imports short/numeric values that must be
  permitted. Only non-string/empty tokens are rejected. Accepted residual, by
  design: a value that also appears as a JSON number/boolean/null field is
  preserved there so typed fields stay typed (this is why a bare flag like `1`
  is checked at its emitted string positions in tests, not globally).
- The first real `starting-initiatives` qualification pair, real skill-resource
  portability, production timeout behavior, suppression-canary effectiveness
  against the live CLI, the live `d7y` command/tool_result stream contract,
  model-routing observations, manifest loading, and `permissions.allow` honor
  under `dontAsk` remain Amp's independent live gates.
- Schema, suites, `SKILL.md`, `d7y`, initiative canon, other skills/plans,
  prompts, and `DEVELOPMENT.md` were not modified. Plan status remains `todo`.
