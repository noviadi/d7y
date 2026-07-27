---
title: Minimal Skill Eval Runner Opus rewrite handoff
type: prompt
status: committed
createdAt: 2026-07-27
updatedAt: 2026-07-27
---

# Opus rewrite handoff

Replace the rejected eval-runner implementation on `work/eval-execution-harness` with a small, coherent implementation whose public CLI and complete arms satisfy `docs/plans/eval-execution-harness.md`. Three previous implementations superficially changed helpers while leaving the public contract broken. Do not patch around them. Rewrite `evals/run_eval.py` and `evals/test_run_eval.py` from the ownership boundary outward, retaining code only after proving it belongs in the corrected design. Do not run live Claude; Amp owns live qualification.

## Identity, routing, and lifecycle

- Governing plan: `docs/plans/eval-execution-harness.md`.
- Execution slug: `opus-rewrite`.
- Executor: Claude Code, requested through launcher model identifier `claude-opus` at high effort.
- User routing: `claude-opus` intentionally resolves to GLM-5.2 in this environment. Record requested contract and routed assistant model separately; this is not a mismatch.
- Branch: `work/eval-execution-harness`.
- Worktree: `/home/noviadi/Developments/discovery/d7y-worktrees/eval-execution-harness`.
- Base: launcher-resolved starting `HEAD`, rebased onto this committed prompt.
- Commit authority: task branch only. Add correction commit(s); never amend or squash.
- No branch creation/deletion/rename, rebase, merge, push, worktree removal, force operation, or shared lifecycle action.

## Execution posture

- Profile: `implementation-commit`; no extra grants.
- Network prohibited; strict-empty MCP; no persistence. Do not invoke nested Claude or any external service.
- Never inspect, print, persist, or test credential values. Synthetic tests inject synthetic settings.
- Disposable test repositories/processes belong under OS temporary directories and must be cleaned.

## Required reading before editing

Read `CLAUDE.md`, this prompt, `docs/plans/eval-execution-harness.md`, all earlier prompts for this plan, and the complete `9bd2c60...HEAD` diff. Treat every existing implementation-feedback claim and passing helper test as untrusted. Read the existing runner/tests, three immutable parser fixtures, schema/validator, both suites, `skills/starting-initiatives/SKILL.md` and references, `d7y`, `scripts/check-initiatives.py`, `initiatives/README.md`, `docs/skill-evaluations.md`, and `DEVELOPMENT.md`.

## Writable paths

Only: `evals/` (except existing Claude JSONL fixtures are read-only), both current skills' `evals/` directories, `docs/skill-evaluations.md`, `docs/plans/eval-execution-harness.md`, and `DEVELOPMENT.md`. Do not modify prompts, `SKILL.md`, D7Y/initiative implementation or canon, other plans, or other skills. Prefer only the existing runner and test files.

## Definition of done: actual public behavior

### Immutable preflight

1. Resolve the selected ref to one commit before reading the suite. `--suite` is repository-relative. Read suite/case, fixtures, skill/references, seed, façade, and checker only through Git objects from that commit. Dirty worktree replacements cannot affect execution.
2. Reject every committed symlink and all absolute/traversing paths. Prevalidate all normalized source/destination entries, duplicates, overwrite/control collisions, and containment before writing.
3. Require a new output root disjoint from source. Record actual object IDs. Snapshot source status before work and in `finally` after every success/failure/timeout; mutation invalidates the result.
4. Build one shared preflight used identically by dry/live modes. Materialize before checking leakage. Dry-run performs every preflight except executable resolution/version/invocation.

### Authentic isolated treatment

5. Create distinct arm roots for target workspace, plugin, `CLAUDE_CONFIG_DIR`, temp, and artifacts, plus separate process-start and shared capability roots. No plugin/settings/config/canary/harness control file may live in target workspaces.
6. A plugin root contains `.claude-plugin/plugin.json` and `skills/starting-initiatives/SKILL.md` plus only required committed runtime references. Baseline has a separate equivalent manifest-only plugin. The path passed to `--plugin-dir` is the plugin root, not `.claude-plugin` itself.
7. Suppression canaries test absence: put project-instruction and fake-global-skill canaries only in locations that should be suppressed by the selected posture. Never pass a canary through `--skill-dir`, environment, prompt, workspace, plugin, or other agent-visible positive input. Detection invalidates live parity; offline tests prove detection mechanics only.

### Exact runtime contract

8. Validate a regular, user-owned, non-group/world-writable settings file and its complete top-level string-to-string `env` map. Tests inject a synthetic path. Import env first; then override config/PWD/PATH/TMPDIR/control values. Diagnostics/artifacts contain key names and provenance only, never values. Check only child values for canonical source/eval/skill path leaks.
9. Resolve one absolute executable and exact version `2.1.218` once per live pair. Use that path for both arms. Dry-run neither resolves nor probes it.
10. Exact argv includes one `--tools Skill,Read,Write,Edit,Bash` value plus fixed print, verbose, stream-json, no-persistence, strict-empty MCP, dontAsk, `claude-sonnet-5`, low effort, project settings, explicit settings, and arm plugin flags. Preserve an argv array, not shell-joined authority.
11. Require both committed D7Y objects in a shared capability installation. Start agents outside target workspaces. Bind each arm prompt to its own absolute `--root`. Parse exact Bash command events for list/check with that root and JSON flags. Independently run the installed checker after each arm and preserve this as separate outcome evidence.

### Trace and result semantics

12. Exact expected target is `d7y-eval-session:starting-initiatives`. Only `Skill` with `input.skill` exactly equal counts. Prefixes and `Skill(list)` do not.
13. Require exactly one init and one successful terminal result, exact tools/requested model/MCP/permission/plugin/accounted skills, distinct pair sessions, required result fields, and no malformed or duplicate required events. Record canonical/requested `claude-sonnet-5` separately from allowed z.ai assistant routing (`glm-4.7` in fixtures/live Sonnet routing).
14. Positive case requires target invocation; negative case requires absence while availability remains proven. Pair validity, treatment, with-skill assertions, and baseline observations remain distinct. Rubric/human assertions are pending; unsupported deterministic assertions ungradable. Any required pending/ungradable/error/fail prevents case pass and zero exit. Baseline outcome failure alone does not invalidate structurally valid parity.
15. Timeout: SIGTERM process group, drain/wait up to five seconds, then SIGKILL any surviving group even if parent exited; drain/reap. Preserve partial stdout/stderr, duration, timeout/terminal state, and child PID evidence.
16. Always write per-arm raw JSONL/stderr/final response/telemetry, executable+argv provenance, independent checker evidence, exact workspace changes, object manifest, checks, and factual summary—even for nonzero, malformed, or timeout runs. No imported values or source-path leakage.

## Tests are acceptance evidence, not helper demonstrations

Delete misleading tests and unused fakes. Most tests must invoke the public script through subprocess in disposable committed repositories; complete-`run_arm` tests may cover process behavior. Helper unit tests are limited to parsers/path primitives.

Public/full-arm tests must prove dirty committed-input replacement immunity; symlink/path/duplicate/overwrite/control/output rejection; real plugin trees and root separation; synthetic env validation/precedence/key-only/no-value behavior; complete dry preflight and zero fake invocations; exactly one version probe plus two exact arm argv records; strict positive/baseline/negative parsing and routed model evidence; nonzero/malformed runs; resistant fork timeout and dead PID/process group with partial evidence; separate command-event/checker evidence; required-assertion exit behavior; complete artifacts without secrets/source leakage; and unchanged source status after success and failure.

An assertion such as “invocation log stayed empty” without running the CLI is forbidden. A test named end-to-end must cross the public boundary it claims.

## Verification

Run:

```sh
python3 evals/validate_skill_evals.py
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s evals -p 'test_*.py'
./d7y validate
git diff --check
git status --short
```

Also run the public dry-run against committed `start-new-initiative` using a nonexistent or invocation-recording fake executable and fresh temporary output. Inspect plugin trees, root separation, sanitized manifest, and intended argv; remove output. Never run live Claude.

Replace—not append to—the plan's implementation-feedback section with concise facts tied to actual tests. Remove duplicates, unsupported claims, emoji checklists, stale commit-specific dry-run commands, and trailing whitespace. Keep plan status todo and report live gates as deferred.

Commit only writable paths and finish clean. Report unproven requirements honestly. Amp will review complete base-to-tip behavior before any live pair.
