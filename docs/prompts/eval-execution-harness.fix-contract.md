---
title: Minimal Skill Eval Runner contract correction handoff
type: prompt
status: committed
createdAt: 2026-07-27
updatedAt: 2026-07-27
---

# Correction handoff

Correct the implementation on `work/eval-execution-harness` so the offline runner and tests actually satisfy `docs/plans/eval-execution-harness.md`. Commit `8e4f933` is not accepted evidence: do not preserve its design merely because its helper-level tests pass. Replace or substantially rewrite it where necessary. Do not execute a live Claude eval; Amp retains the live qualification gate.

## Execution identity and lifecycle

- Governing plan: `docs/plans/eval-execution-harness.md`.
- Execution slug: `fix-contract`.
- Executor: Claude Code.
- Assigned branch: `work/eval-execution-harness`.
- Assigned worktree: `/home/noviadi/Developments/discovery/d7y-worktrees/eval-execution-harness`.
- Base: the launcher-resolved starting `HEAD`, which must contain the initial implementation commits rebased onto the committed correction prompt.
- Commit authority: explicitly granted on the assigned task branch only. Preserve existing commit boundaries and add cohesive correction commit(s); do not amend or squash.
- Lifecycle authority: none beyond task-branch commits. Do not create/rename/delete branches, rebase, merge, push, remove worktrees, amend, or force any Git operation.

## Permission and workspace posture

- Launcher profile: `implementation-commit`.
- Extra tool grants: none.
- Network: prohibited. Do not invoke nested live Claude runs or external services. Use fake executors and the immutable committed parser constructions.
- MCP: strict-empty. Persistence: disabled.
- Credentials: do not print, inspect, persist, forward, or test values. Tests must use synthetic settings and environments.
- Repository edits and lifecycle restrictions apply to D7Y. Tests may create disposable Git repositories, commits, refs, and process trees under OS temporary directories, must not modify shared D7Y Git state, and must clean temporary resources.

The requested model identifier is `claude-sonnet-5`. In this user's intentional z.ai routing, assistant events may identify `glm-4.7` while `system.init` and `result.modelUsage` identify the requested/canonical `claude-sonnet-5`. Record that distinction rather than rejecting it or claiming the assistant event used a literal Anthropic model.

## Required context

Before editing, read:

- `CLAUDE.md`, the launcher envelope, and this prompt;
- `docs/plans/eval-execution-harness.md` in full, including the initial implementation feedback as claims to correct;
- `docs/prompts/eval-execution-harness.initial.md` for the original contract;
- the complete `main...HEAD` diff and both existing task commits;
- `evals/run_eval.py`, `evals/test_run_eval.py`, all three committed parser constructions, the eval schema and validator;
- `skills/starting-initiatives/SKILL.md`, its eval suite and fixtures;
- `d7y`, `scripts/check-initiatives.py`, `initiatives/README.md`, `docs/skill-evaluations.md`, and `DEVELOPMENT.md`.

## Writable paths

Modify or create files only within:

- `evals/`, except the three committed `evals/fixtures/claude-code-2.1.218/*.jsonl` files are read-only;
- `skills/starting-initiatives/evals/`;
- `skills/writing-great-skills/evals/`;
- `docs/skill-evaluations.md`;
- `docs/plans/eval-execution-harness.md`;
- `DEVELOPMENT.md`.

Do not modify either concrete prompt, any `SKILL.md`, `d7y`, initiative canon/implementation, another skill, or another plan. New implementation/test files are authorized only under `evals/`; prefer replacing the current two files over adding layers.

## Blocking corrections

### 1. Immutable source and staging

- Resolve the selected ref once with `^{commit}` to a full SHA.
- Read the suite, case fixtures, authentic skill payload, allowlisted seed, D7Y façade, and shared initiative implementation only from that commit using Git objects—not `Path.read_*` against the worktree.
- Inspect committed tree modes and reject every symlink before content staging.
- Validate normalized source and destination paths for absolutes, traversal, containment, duplicates, existing-file overwrites, and control-path collisions before writing anything.
- Require a new output root outside the source checkout; reject pre-existing/stale output roots.
- Record selected object IDs and before/after source `git status --porcelain`; fail pair validity if the source changes.

### 2. Authentic treatment and distinct roots

- Materialize a valid session plugin from the committed target skill using `.claude-plugin/plugin.json` and `skills/starting-initiatives/SKILL.md` (plus only execution-time references actually used by that skill).
- Materialize an equivalent manifest-only control plugin for baseline.
- Keep workspace, plugin, `CLAUDE_CONFIG_DIR`, temporary directory, D7Y capability installation, and process starting directory distinct for each role required by the plan. No settings, plugin, canary, or harness control file may live in the target workspace.
- Complete all materialization before checking staged/runtime roots for leakage.

### 3. D7Y capability binding

- Materialize one shared read-only-in-practice capability installation from committed `d7y` and `scripts/check-initiatives.py`; fail if either required object is absent.
- Prepend that exact installation to both child `PATH`s after imported env values and record its executable path, object IDs, and commit.
- Run each agent from a process-start directory separate from its target workspace and pass the target workspace through the prompt/skill's explicit absolute `--root` command contract.
- Parse exact Bash tool events for `d7y initiatives list --root <workspace> --json` and `check --root <workspace> --json`; do not infer process compliance from the independent checker.
- Independently run the installed capability after each arm and preserve its JSON, exit status, and diagnostics as outcome evidence.

### 4. Environment, executable, and exact argv

- Validate `~/.claude/settings.json` ownership/mode and import only its top-level string-to-string `env` map for a real run. Synthetic tests must inject an equivalent settings source without reading user credentials.
- Construct a minimal child environment, apply imported values first, then override harness-owned `CLAUDE_CONFIG_DIR`, `PWD`, capability `PATH`, `TMPDIR`, and controls. Reject canonical source/eval/skill path exposure without including values in errors or artifacts. Record only source provenance and sorted key names.
- Resolve one absolute Claude executable, parse and require exact version `2.1.218`, and reuse that provenance for both arms. Dry-run must neither start nor version-probe it.
- Use the exact selected argv, including one `--tools Skill,Read,Write,Edit,Bash` value—not nonexistent/repeated `--allow-tool` flags—and every fixed model/effort/settings/MCP/persistence/permission/plugin flag in the plan.

### 5. Strict parser and result semantics

- Treat malformed nonempty JSONL lines as executor errors; ignore only explicitly supported incidental event types, while rejecting malformed/unknown required event shapes.
- Require one valid `system.init` and terminal `result`, exact tools/model/MCP/permission, expected plugin, target namespaced skill only with-skill, only accounted built-in `doctor`, distinct sessions, successful terminal status, and available result fields.
- Match invocation only when `name == "Skill"` and `input.skill` exactly equals the expected namespaced target. The baseline fixture's `Skill(list)` must not count.
- Record requested/canonical model and the routed assistant-event model separately; permit the documented z.ai `glm-4.7` assistant routing.
- Compute parity from parsed evidence and declared controls, not absent metadata defaults. Keep pair validity, treatment checks, with-skill assertions, and baseline observations separate.
- For positive cases require exact target invocation; for negative controls require its absence while target availability remains proven. A required failed/error/ungradable/pending with-skill assertion prevents case pass; expected baseline failure does not invalidate a valid pair.

### 6. Canaries, timeout, and durable evidence

- Preflight/dry-run must fully materialize and validate immutable inputs, distinct roots, authentic treatment, control plugins/settings, capability, canaries, environment names/provenance, parity, and sanitized intended argv/manifests without starting or version-probing Claude.
- Build project-instruction and fake-global-skill suppression canaries in both arms and implement simulated pass/fail detection offline. The live pair must be invalid if canary instructions appear or the canary skill is discovered/invoked; offline tests must not claim actual runtime suppression is proven.
- On timeout, signal the complete process group with `SIGTERM`, drain/wait up to five seconds, then `SIGKILL` the group if necessary and drain/reap. Preserve partial stdout/stderr, elapsed duration, timeout state, and terminal status.
- Always preserve raw JSONL, raw stderr, final response, available usage/model/turn/permission telemetry, executable and command provenance, independent checker evidence, selected-object manifest, pair/check results, and retained workspace changes or an exact change manifest. Never record imported environment values.

### 7. End-to-end offline tests and honest feedback

Replace helper-only coverage with public-entry-point or full-arm tests in disposable Git repositories. At minimum prove:

- committed-object suite/fixture/skill/capability reads ignore dirty worktree replacements;
- committed symlink, absolute/traversing source/destination, duplicate destination, overwrite/control collision, stale output, and source-contained output rejection;
- authentic target/control plugin layouts and distinct roots;
- exact executable resolution/version behavior and exact argv;
- nested env-map validation, precedence, key-name-only evidence, path-leak rejection, and no-value diagnostics/artifacts;
- committed positive/baseline/negative fixture parsing, exact target versus `Skill(list)`, malformed required JSON/event rejection, session/parity/plugin/skill/result checks, and z.ai assistant routing;
- dry-run performs full preflight without invoking or version-probing the fake executable;
- successful and nonzero fake runs, timeout with a resistant forked child and PID evidence the complete process group died, partial-evidence retention, and required-assertion exit semantics;
- D7Y command-event evidence remains separate from independent installed-capability results;
- all required artifacts exist, contain no secrets/source leakage, and source status remains unchanged.

Revise the existing `## Implementation Feedback` in the plan rather than appending a contradictory second report. Remove unsupported claims and record exact offline evidence, deferred live gates, deviations, model routing, and residual risks. Do not mark the plan done or claim a live comparative eval.

## Required verification

Run and report:

```sh
python3 evals/validate_skill_evals.py
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s evals -p 'test_*.py'
./d7y validate
git diff --check
git status --short
```

Also run the corrected dry-run against the committed `start-new-initiative` case using a disposable output root, inspect its sanitized manifest/argv, then remove the output. Do not run without `--dry-run` against the real Claude executable.

## Completion

Commit cohesive corrections on the assigned branch, staging only writable paths. Return the tip with a clean worktree and no untracked files. Report any requirement you could not prove rather than weakening, simulating, or claiming it. The branch is not integration-ready until Amp independently reviews the complete base-to-tip diff and executes the live qualification gate.
