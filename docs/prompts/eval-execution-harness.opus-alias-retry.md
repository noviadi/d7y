---
title: Minimal Skill Eval Runner Opus alias retry
type: prompt
status: committed
createdAt: 2026-07-27
updatedAt: 2026-07-27
---

# Opus alias retry

Replace the rejected eval-runner implementation on `work/eval-execution-harness` with a coherent implementation whose public CLI and complete-arm behavior satisfy `docs/plans/eval-execution-harness.md`. This retries the aborted `opus-rewrite` execution using Claude Code's built-in `opus` alias. The previous `claude-opus` argument unexpectedly routed assistant events to GLM-4.7 and was stopped before edits. The user environment maps `opus` to GLM-5.2. Record the launcher model alias and routed assistant model separately. Do not treat intentional GLM-5.2 routing as a mismatch, and do not run a live eval.

## Execution contract

- Governing plan: `docs/plans/eval-execution-harness.md`.
- Execution slug: `opus-alias-retry`; executor: Claude Code via launcher `--model opus --effort high`.
- Branch: `work/eval-execution-harness`; worktree: `/home/noviadi/Developments/discovery/d7y-worktrees/eval-execution-harness`.
- Base: launcher-resolved starting `HEAD`, rebased onto this prompt commit.
- Commit on the task branch only. Do not amend/squash, create/delete/rename branches, rebase, merge, push, remove worktrees, or force operations.
- Profile `implementation-commit`; no extra grants; network prohibited; strict-empty MCP; persistence disabled.
- Never inspect, print, persist, forward, or test credential values. Synthetic tests inject synthetic settings. Temporary repositories/processes must be isolated and cleaned.

## Required context and writable paths

Read `CLAUDE.md`, this prompt, `docs/prompts/eval-execution-harness.opus-rewrite.md`, every earlier prompt for this plan, the complete task-branch diff, the governing plan, runner/tests, immutable parser fixtures, schema/validator/suites, target skill and references, `d7y`, initiative checker/contract, canonical eval documentation, and contributor documentation. The detailed definition of done and test matrix in `docs/prompts/eval-execution-harness.opus-rewrite.md` is incorporated into this retry in full; follow it as the implementation specification. Existing feedback and passing helper tests are untrusted.

Write only under `evals/` (existing Claude JSONL fixtures read-only), both current skills' `evals/` directories, `docs/skill-evaluations.md`, `docs/plans/eval-execution-harness.md`, and `DEVELOPMENT.md`. Do not modify prompts, skills, D7Y/initiative implementation or canon, other plans, or other skills. Prefer replacing the existing runner and tests rather than adding layers.

## Blocking acceptance gates

1. Resolve commit before reading a repository-relative suite; every suite/case/fixture/skill/reference/seed/capability input comes from immutable Git objects. Reject symlinks, unsafe paths, duplicate/overwrite/control collisions, stale or source-overlapping output, and source mutation on every exit path.
2. One shared dry/live preflight materializes distinct workspace/plugin/config/temp/artifact roots per arm plus separate process-start/shared capability roots. Plugin roots use `.claude-plugin/plugin.json` and `skills/starting-initiatives/SKILL.md`; baseline is manifest-only. Controls and canaries never live in target workspaces.
3. Canaries test suppression and are never positively exposed through prompt, env, `--skill-dir`, workspace, or plugin. Dry-run performs complete preflight but neither resolves, probes, nor invokes Claude.
4. Validate and import the full top-level string-to-string user `env` map securely, then apply harness overrides. Artifacts/errors contain provenance and key names only. Resolve/version-check one absolute Claude 2.1.218 executable once and reuse it.
5. Exact argv uses one `--tools Skill,Read,Write,Edit,Bash` value and every fixed model/effort/settings/MCP/session/permission/plugin flag. Agents start outside targets; prompts bind the correct absolute `--root`.
6. Require both committed D7Y capability objects. Keep exact agent Bash list/check command evidence distinct from independent post-arm installed-checker evidence.
7. Require exact target `d7y-eval-session:starting-initiatives`, one init/result, exact accounted runtime state, distinct sessions, successful terminal evidence, and routed model provenance. Required pending/ungradable/error/fail assertions prevent pass and zero exit.
8. Timeout kills and reaps the complete process group while retaining partial evidence. Every outcome writes raw streams, response/telemetry, argv/executable, checker, workspace/object/check/summary artifacts without secret or source leakage.
9. Most tests invoke the public CLI in disposable committed repositories; full-arm tests cover process behavior. Prove immutable dirty-worktree reads, all safety rejection paths, authentic roots, env behavior, dry-run zero invocation, one version probe/two exact arm argv, strict traces, nonzero/malformed/timeout evidence, checker separation, assertion exit semantics, artifact inventory, and unchanged source. A test that never invokes its claimed boundary is invalid.

## Verification and completion

Run `python3 evals/validate_skill_evals.py`, `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s evals -p 'test_*.py'`, `./d7y validate`, `git diff --check`, and `git status --short`. Run and inspect only the public dry-run with a nonexistent/invocation-recording executable and disposable output; never run live Claude.

Replace the plan's implementation feedback with concise factual evidence—no duplicate sections, emoji claims, stale commits, or unsupported “end-to-end” language. Keep the plan todo and live gates deferred. Commit only authorized paths and finish clean; report anything unproven.
