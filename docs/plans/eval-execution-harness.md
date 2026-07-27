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

### Files changed

- `evals/run_eval.py` — rewritten from the ownership boundary outward.
- `evals/test_run_eval.py` — rewritten; helper-only tests replaced with subprocess public-CLI tests plus narrow parser/path unit tests.

This is the `opus-alias-retry` execution. The launcher model alias was `opus`; the routed assistant model is GLM-5.2. The requested runner contract model is `claude-sonnet-5`; permitted routed assistant events include `glm-4.7`/`glm-4.6` and are recorded separately, not rejected as a mismatch.

### Implemented command

```sh
python3 evals/run_eval.py --source-repo <repo> --suite <repo-relative-evals.json> \
  --case <case-id> --output <dir> [--commit <ref>] [--claude <path>] [--dry-run]
```

### What the public CLI actually does (proven by tests)

- `--commit` is resolved to one SHA before the suite is read. Suite, case, fixtures, target skill, repository seed (`initiatives/README.md`), the `d7y` façade, and `scripts/check-initiatives.py` are read exclusively via Git objects; dirty worktree replacements have no effect (`test_dirty_worktree_replacements_ignored`). Real blob object IDs are recorded, not `commit:path` strings.
- Committed symlinks anywhere in the staged skill tree are rejected (`test_committed_symlink_in_skill_rejected`); absolute/traversal paths, duplicate destinations, control-destination collisions, output-inside-source, and stale output are rejected (unit + CLI tests).
- One shared preflight is used by dry and live modes. Distinct roots are materialized per arm for workspace, plugin, `CLAUDE_CONFIG_DIR`, temp, and artifacts, plus separate shared process-start and capability roots. Plugins, harness settings, config, temp, and canaries live outside target workspaces (`test_dry_run_complete_preflight_zero_invocations`).
- Authentic plugin layout: `<arm>/plugin/.claude-plugin/plugin.json` and `<arm>/plugin/skills/starting-initiatives/SKILL.md` (with-skill only); a separate manifest-only `d7y-eval-control` baseline plugin. `--plugin-dir` receives the plugin root.
- Suppression canaries (project-instruction and fake-global-skill) are written only into suppressed config-root locations and are never passed via `--skill-dir`, environment, prompt, workspace, or plugin. Canary discovery/invocation/text invalidates pair validity (`test_canary_leak_in_run_fails_pair`, unit test).
- The top-level user `env` map is validated (regular file, current-user owned, not group/world-writable, string-to-string) and imported first; harness-owned `CLAUDE_CONFIG_DIR`, `PWD`, `TMPDIR`, and capability `PATH` override afterward. Canonical source/eval/skill path exposure in child values is rejected (`test_env_path_leak_rejected`). Artifacts carry provenance and key names only — never values (`test_env_provenance_key_names_only`).
- One absolute executable is resolved once and requires parsed `claude --version` == `2.1.218` for both arms; dry-run neither resolves nor probes it (`test_executable_version_probe_required`, provenance artifact). Exact argv uses one `--tools Skill,Read,Write,Edit,Bash` value plus every fixed flag and `--root <absolute workspace>` (`test_dry_run_argv_uses_one_tools_value_and_root`).
- Both committed D7Y capability objects are required and materialized into one shared installation. Agents start in the process-start root with their own absolute `--root`. Bash command events for `d7y initiatives list/check --root <workspace> --json` are parsed and kept distinct from the independent installed-checker run captured after each arm (`test_live_positive_case_passes_end_to_end`).
- Strict event semantics: exactly one `system.init` and one successful terminal `result`; exact tools, requested `claude-sonnet-5`, empty MCP, `dontAsk`, expected plugin, accounted skills (`doctor` plus target with-skill), distinct sessions, and required result fields. Target invocation counts only for `name=="Skill"` with `input.skill == "d7y-eval-session:starting-initiatives"`; prefixes and `Skill(list)` never count (unit tests + fixtures).
- Timeout sends `SIGTERM` to the process group, drains for up to five seconds, then `SIGKILL`s the group even if the parent exited; partial stdout/stderr, duration, timeout/terminal state, and child PID are retained. A forked `SIGTERM`-resistant child is reaped (`test_timeout_kills_process_group_and_reaps`).
- Always writes the complete per-arm artifact tree (raw JSONL, stderr, final response, telemetry with canonical+routed model, executable+argv provenance, command events, independent checker evidence, workspace changes, validation, process) plus `manifest.json`, `checks.json`, and `summary.md` — for nonzero, malformed, and timeout runs as well (`test_nonzero_run_still_writes_artifacts_and_exits_nonzero`, `test_malformed_stream_marks_arm_error`).

### Result semantics

Pair validity, treatment, with-skill assertions, and baseline observations are separate. Deterministic assertions resolve from evidence (invocation, process `d7y` list/check commands, outcome via workspace change + independent checker). Rubric and human assertions stay `pending`; unsupported deterministic assertions are `ungradable`. Any required `pending`/`ungradable`/`error`/`fail` assertion blocks case pass and a zero exit. The positive `start-new-initiative` case therefore exits nonzero because its required rubric assertion is `pending` while every required deterministic assertion passes; the negative `casual-brainstorm` case (deterministic assertions only) passes when the target is available but not invoked.

### Offline verification run

- `python3 evals/validate_skill_evals.py` — both suites VALID.
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s evals -p 'test_*.py'` — 31 tests, OK.
- `./d7y validate` — evals and initiatives valid.
- `git diff --check` — clean.
- Public dry-run against committed `start-new-initiative` with a nonexistent executable and synthetic settings: authentic plugin trees, distinct roots, no control files in workspaces, sanitized manifest (no source path or env values), and one `--tools` value with `--root`/`--plugin-dir`. Output disposed of.

### Deferred / unproven

- No live Claude run was executed (network prohibited). The first real `starting-initiatives` qualification pair, real skill-resource portability, production timeout behavior, suppression-canary effectiveness against the live CLI, and model-routing observations remain Amp's live gates.
- Schema, validator, suites, `SKILL.md`, `d7y`, initiative canon, other skills/plans, and prompts were not modified. Plan status remains `todo`.
