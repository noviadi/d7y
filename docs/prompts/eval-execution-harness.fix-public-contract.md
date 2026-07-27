---
title: Minimal Skill Eval Runner public-contract correction handoff
type: prompt
status: committed
createdAt: 2026-07-27
updatedAt: 2026-07-27
---

# Public-contract correction handoff

Rewrite the implementation on `work/eval-execution-harness` so its public entry point and complete-arm behavior actually satisfy `docs/plans/eval-execution-harness.md`. The implementations in `0299808` and `457e094` are rejected, even though their helper tests pass. Do not preserve their structure or compatibility when replacement is simpler and safer. Do not execute a live Claude eval; Amp retains that gate.

## Execution identity and lifecycle

- Governing plan: `docs/plans/eval-execution-harness.md`.
- Execution slug: `fix-public-contract`.
- Executor: Claude Code.
- Assigned branch: `work/eval-execution-harness`.
- Assigned worktree: `/home/noviadi/Developments/discovery/d7y-worktrees/eval-execution-harness`.
- Base: the launcher-resolved starting `HEAD`, rebased onto the commit containing this prompt.
- Commit authority: granted only on the assigned task branch. Add cohesive correction commit(s); do not amend or squash existing commits.
- Lifecycle authority: none beyond task-branch commits. Do not create, rename, or delete branches; rebase; merge; push; remove worktrees; amend; or force any Git operation.

## Permission and workspace posture

- Launcher profile: `implementation-commit`.
- Extra tool grants: none.
- Network: prohibited. Never invoke a nested live Claude run or external service. Use fake executors and committed parser fixtures only.
- MCP: strict-empty. Persistence: disabled.
- Credentials: never print, inspect, persist, forward, or test values. Tests must inject synthetic settings and environments.
- Tests may create disposable Git repositories and process trees only under OS temporary directories and must clean them.

The requested executor model is `claude-sonnet-5`. This user's intentional z.ai routing may emit assistant events identifying `glm-4.7` while init/result evidence identifies requested/canonical `claude-sonnet-5`. Preserve and test that distinction; do not reject it as a model mismatch.

## Required context

Before editing, read:

- `CLAUDE.md`, the launcher envelope, and this prompt;
- `docs/plans/eval-execution-harness.md` in full; treat its current implementation-feedback section as untrusted claims to replace;
- `docs/prompts/eval-execution-harness.initial.md` and `docs/prompts/eval-execution-harness.fix-contract.md`;
- the complete `449fe4d...HEAD` diff and task-branch commits;
- `evals/run_eval.py`, `evals/test_run_eval.py`, all three committed Claude fixtures, the eval schema, validator, and both current suites;
- `skills/starting-initiatives/SKILL.md` and its runtime references;
- `d7y`, `scripts/check-initiatives.py`, `initiatives/README.md`, `docs/skill-evaluations.md`, and `DEVELOPMENT.md`.

## Writable paths

Modify or create files only within:

- `evals/`, except the three `evals/fixtures/claude-code-2.1.218/*.jsonl` files are read-only;
- `skills/starting-initiatives/evals/`;
- `skills/writing-great-skills/evals/`;
- `docs/skill-evaluations.md`;
- `docs/plans/eval-execution-harness.md`;
- `DEVELOPMENT.md`.

Do not modify prompts, any `SKILL.md`, `d7y`, initiative canon/implementation, another skill, or another plan. Prefer replacing `evals/run_eval.py` and `evals/test_run_eval.py` over adding files or abstractions.

## Non-negotiable corrections

### 1. One immutable input boundary

- Resolve `--commit` first. Interpret `--suite` as a repository-relative path and read the suite, selected case, fixture declarations/content, target skill and required references, allowlisted seed, `d7y`, and initiative checker exclusively from that commit via Git objects. Dirty worktree replacements must have no effect.
- Reject absolute/traversing paths and every committed symlink. Prevalidate the complete staging map before writes: normalized containment, duplicate destinations, existing-file overwrites, and control collisions.
- Require a new output root disjoint from the source checkout. Record actual object IDs, not descriptive `commit:path` strings.
- Record source status before preflight and in a `finally` path after all work, including failures/timeouts; source mutation invalidates the pair.

### 2. Shared preflight used by dry and live modes

- Materialize all immutable inputs and separate target workspace, plugin, config, temp, process-start, capability, and artifact roots before either mode diverges.
- Use authentic Claude plugin layouts: `.claude-plugin/plugin.json` and `skills/starting-initiatives/SKILL.md` plus only required committed runtime references. Baseline gets a separate equivalent manifest-only control plugin.
- Keep plugin, settings, config, temp, canaries, and harness controls outside target workspaces. Run leakage checks only after complete materialization.
- Add project-instruction and fake-global-skill suppression canaries to both configurations. A live observation/discovery/invocation invalidates the pair; offline tests may prove detection only, not real suppression.
- `--dry-run` must execute this complete preflight and write sanitized intended argv/manifests without starting or version-probing the supplied executable.

### 3. Exact environment, executable, and Claude command

- For real runs, securely validate the user settings regular file, ownership, mode, and top-level `env` string map. Tests inject a synthetic settings path. Import all valid env entries first, then override harness-owned `CLAUDE_CONFIG_DIR`, `PWD`, capability `PATH`, `TMPDIR`, and controls.
- Reject canonical source/eval/skill path exposure among child values, but never put values in diagnostics or artifacts. Record source provenance and sorted key names only. Do not reject unused parent-process variables.
- Resolve one absolute executable and require an exact parsed Claude Code version `2.1.218` once before both live arms. Dry-run performs neither action.
- Build the exact planned command, including one `--tools Skill,Read,Write,Edit,Bash` argument—not `--allow-tool`—and the fixed print/verbose/stream-json/session/MCP/permission/model/effort/settings/plugin flags.

### 4. Real D7Y binding and evidence separation

- Require and materialize both committed capability objects into one shared installation exposed identically to both arms; record commit, object IDs, and executable path.
- Start each agent outside its target workspace and bind the prompt to that arm's explicit absolute `--root` contract.
- Parse exact Bash events for `d7y initiatives list --root <workspace> --json` and `d7y initiatives check --root <workspace> --json`. Keep command-event evidence distinct from independent installed-capability checks run after each arm.
- Preserve independent checker argv, stdout JSON, stderr, and exit status for each arm.

### 5. Strict trace, parity, and success semantics

- Derive one exact expected namespaced target, `d7y-eval-session:starting-initiatives`. Invocation counts only for `name == "Skill"` with `input.skill` exactly equal to it; `Skill(list)` and prefix matches never count.
- Require exactly one valid init and one successful terminal result; exact tools, requested model, empty MCP, permission mode, expected plugin and accounted skills; distinct sessions; required result fields; and no malformed or duplicate required event.
- Preserve requested/canonical `claude-sonnet-5` separately from permitted routed assistant model `glm-4.7`.
- Compute control parity and pair validity from evidence. Positive cases require target invocation; negative cases require absence while target availability remains proven.
- Keep pair validity, treatment, with-skill assertions, and baseline observations separate. Rubric/human checks remain `pending`; unsupported deterministic checks are `ungradable`. Any required failed/error/ungradable/pending with-skill assertion prevents case pass and a zero CLI exit. Expected baseline outcome failure alone does not invalidate a structurally valid pair.

### 6. Complete timeout and durable evidence

- On timeout send `SIGTERM` to the process group, drain/wait up to five seconds, then send `SIGKILL` to the group if any member remains even if the parent exited; drain and reap. Retain partial stdout/stderr, elapsed duration, timeout status, terminal status, and child-PID evidence.
- Always write per-arm raw JSONL, raw stderr, final response, usage/model/turn/permission telemetry, executable and argv provenance, checker evidence, workspace-change manifest or retained changes, selected-object manifest, checks, and factual summary. Never persist imported values.
- Nonzero, malformed, and timed-out fake runs must still leave complete partial artifacts.

### 7. Tests must execute public behavior

Replace the helper-assertion suite with subprocess tests of the public CLI or complete `run_arm` tests inside disposable committed repositories. Importing helpers is acceptable only for narrow parser unit cases; it cannot be the evidence for runner behavior.

At minimum prove end to end:

- dirty suite/fixture/skill/capability worktree replacements are ignored;
- committed symlink, source/destination absolute/traversal, duplicate destination, overwrite/control collision, stale output, and source/output containment rejection;
- authentic plugins and all distinct roots;
- injected nested env validation, precedence, key-only evidence, no-value errors/artifacts, and path-leak rejection;
- dry-run complete preflight with a fake executable that would record any version/run invocation, proving zero invocations;
- exact one-time version resolution and exact argv for both successful fake arms;
- committed fixture parsing, exact target versus `Skill(list)`, malformed/duplicate/missing required events, session/parity/plugin/skill/result failures, and z.ai assistant routing;
- successful, nonzero, and malformed fake executions; resistant forked-child timeout with PID evidence the whole group died and partial evidence survived;
- command-event evidence separate from independent capability evidence;
- required assertion exit semantics, complete artifact inventory, no secret/source leakage, and unchanged source status after success and failure.

Delete misleading tests, unused fakes, duplicate code, and unsupported feedback claims. Test names and documentation must describe only what actually ran.

## Required verification

Run and report:

```sh
python3 evals/validate_skill_evals.py
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s evals -p 'test_*.py'
./d7y validate
git diff --check
git status --short
```

Also run the corrected public dry-run for the committed `start-new-initiative` case with a nonexistent/invocation-recording fake executable and a disposable output root. Inspect its plugin tree, root separation, sanitized manifests, and intended exact argv, then clean the output. Do not execute the public runner without `--dry-run` against real Claude.

## Feedback and completion

Replace the plan's current `## Implementation Feedback` section with one concise factual record; do not append another report. Include exact tests actually run, offline evidence, deferred live gates, z.ai routing distinction, deviations, and residual risks. Do not mark the plan done or claim a live comparison.

Commit cohesive corrections on the assigned branch, staging only writable paths. Return a clean worktree with no untracked files. Explicitly report anything unproven rather than weakening or simulating the requirement. The branch remains unqualified until Amp reviews the complete base-to-tip diff and runs the live gates.
