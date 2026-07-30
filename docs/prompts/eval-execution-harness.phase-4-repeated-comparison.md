---
status: draft
plan: docs/plans/eval-execution-harness.md
execution: phase-4-repeated-comparison
executor: claude-code
branch: work/eval-harness-repeated-comparison
worktree: /home/noviadi/Developments/discovery/d7y-worktrees/eval-harness-repeated-comparison
permissionProfile: implementation-commit
commit: allowed
---

# Objective

Execute only Phase 4 of `docs/plans/eval-execution-harness.md`: run the accepted
three-case suite three times per arm, retain all eighteen trials, apply the
accepted deterministic and quality-review procedure, and produce a factual
paired comparison. This is an execution-and-evidence task, not an implementation
or repair task.

# Activation and predecessor gate

Execute only after Phase 3's implementation, six-trial evidence, and quality
review are accepted and integrated; the exact configuration is frozen; a human
approves eighteen Harbor rollouts, the USD 54 worst-case budget, and the API
profile; and this prompt is committed with `status: committed`.

The launcher-resolved starting `HEAD` is the exact clean `main` base containing
accepted Phases 0–3. Branch, worktree, Harbor version, images, Docker context,
API profile, credential key, case/task digests, and grading procedure must
match. Stop on any drift.

# Required context

Read `AGENTS.md`, `CLAUDE.md`, the governing plan and all phase feedback,
`docs/skill-evaluations.md`, the committed current suite, accepted
`evals/harbor/` runner/tests, retained Phase 3 evidence and quality disposition,
and the complete base diff.

# Writable paths

- `docs/plans/eval-execution-harness.md` for Phase 4 feedback only
- `/home/noviadi/Developments/discovery/d7y-eval-evidence/eval-execution-harness/phase-4-repeated-comparison`
  for retained review evidence

The evidence path must not exist before execution; no existing component may be
a symlink. Create it user-owned with mode `0700`. Do not modify implementation,
tests, skills, eval definitions, canon, `DEVELOPMENT.md`, this prompt, or another
plan. If code is defective, stop and report it for a separate correction
handoff.

# Permission, credentials, and cost envelope

- Profile: `implementation-commit`
- Extra tool grants: none
- Executor network: prohibited except for the Harbor trials' frozen
  agent-phase API allowlist.
- Credentials: frozen trial-scoped agent key only; never expose its value and
  never pass it to the verifier.
- Authorized Harbor rollouts: exactly eighteen—three cases by two arms by three
  repetitions.
- Per-rollout ceilings: `max_turns = 24`, `max_budget_usd = 3.00`, and the
  600-second agent timeout. Aggregate worst-case budget: USD 54.
- The rollout count is not a model-request count. Both ceilings must be enforced
  and recorded. No retry, replacement, judge call, exploratory probe, or
  additional rollout.
- MCP: strict-empty.
- Docker: resources prefixed `d7y-eval-phase4-`; no trial Docker socket mount.
- Commit/lifecycle: feedback commit on the assigned branch only; no rebase,
  merge, push, amend, force operation, branch lifecycle action, or modification
  of `main`.

# Required work

1. Preflight the frozen configuration and create a complete planned matrix of
   eighteen unique case/arm/repetition identities before the first call.
2. Alternate or deterministically balance arm order and record actual start
   order and timestamps.
3. Execute every planned trial once. Preserve failures and partial evidence;
   never substitute another trial.
4. Validate environment, pair, treatment, artifact, provenance, verifier, and
   credential controls for every trial.
5. Apply only the Phase 3 accepted deterministic checks. Create a new read-only
   quality-review packet for the eighteen fresh outputs and mark those
   assertions `ungradable` pending human review; do not self-adjudicate or call a
   judge. After executor return, Amp and the human record dispositions on the
   task branch before Phase 4 is accepted or integrated. The evidence-only
   normalized summaries remain unchanged; plan feedback links each disposition
   to stable trial and assertion identifiers.
6. Report raw counts and paired observations by case and assertion:
   pass/fail/error/ungradable, invocation false positives/negatives when
   observable, duration, tokens, tools, retries, pending quality assertions,
   and canonical infrastructure failures. Leave the quality fields pending
   until Amp and the human record their dispositions.
7. Produce no confidence claim, accepted `benchmark.json`, maturity
   recommendation, skill edit, or automated retry.

# Verification

Verify:

- exactly eighteen planned and eighteen uniquely identified trial records;
- zero unrecorded retry or replacement;
- three trials for every case/arm cell;
- configuration and task digest parity;
- required artifact-manifest disposition for every trial;
- summary regeneration solely from retained evidence;
- an inventory with hashes for every raw trial and normalized result;
- enforcement records for `max_turns` and `max_budget_usd` on every rollout;
- `python3 evals/validate_skill_evals.py`;
- `./d7y validate`;
- `git diff --check`;
- `git status --short`.

# Stop conditions

Stop before the first call on any configuration drift or missing predecessor
evidence, or if either per-rollout ceiling is not enforced. During execution,
stop only for a common unsafe boundary failure such as credential leakage, host
mount, or invalid network policy; retain the unexecuted matrix as explicit
missing trials. For ordinary agent, verifier, or assertion failures, preserve
the result and continue without retry.

# Completion

Append `### Phase 4 implementation feedback` with the frozen configuration,
planned and actual matrix, run order, trial IDs, aggregate observations,
evidence path/inventory hash, quality-review packet and pending dispositions,
spend/usage when available, deviations, and residual uncertainty. Commit only
plan feedback and return a clean worktree. Finalize the durable evidence
directory with its absolute path, owner, mode, file inventory, SHA-256 hashes,
and finalization time, and do not mutate it afterward. Amp and the human add
quality dispositions to plan feedback on the task branch before integration.
They do not rewrite the finalized evidence-only summaries. Do not mark the plan
done or interpret the result as maturity.
