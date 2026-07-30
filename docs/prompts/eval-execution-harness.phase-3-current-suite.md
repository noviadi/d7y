---
status: draft
plan: docs/plans/eval-execution-harness.md
execution: phase-3-current-suite
executor: claude-code
branch: work/eval-harness-current-suite
worktree: /home/noviadi/Developments/discovery/d7y-worktrees/eval-harness-current-suite
permissionProfile: implementation-commit
commit: allowed
---

# Objective

Implement and run only Phase 3 of `docs/plans/eval-execution-harness.md`: extend
the accepted Phase 2 path to all three current `starting-initiatives` cases and
run each once in both arms. Grade supported deterministic assertions and prepare
an evidence-only quality-review packet. Do not run repetitions, add a model
judge, change the skill, or promote maturity.

# Activation and predecessor gate

Execute only after Phase 2 implementation and pair evidence are reviewed and
integrated, the accepted trajectory contract and unsupported telemetry are
recorded, the same API profile and six-rollout USD 18 worst-case budget are
human-approved, and this prompt is committed with `status: committed`.

The launcher-resolved starting `HEAD` is the exact clean `main` base containing
accepted Phases 0–2. Branch, worktree, Harbor version, images, Docker context,
API-profile digest, and credential key name must match. Stop on drift.

# Required context

Read `AGENTS.md`, `CLAUDE.md`, `DEVELOPMENT.md`, the plan and all prior phase
feedback, `docs/skill-evaluations.md`, the complete
`skills/starting-initiatives/evals/` suite and fixtures, the target skill and
required references, `initiatives/README.md`, `d7y`,
`scripts/check-initiatives.py`, all accepted `evals/harbor/` code and tests,
retained Phase 2 evidence, relevant Harbor documentation, and the complete base
diff.

# Writable paths

- `evals/harbor/`
- `skills/starting-initiatives/evals/graders/`
- `DEVELOPMENT.md`
- `docs/plans/eval-execution-harness.md` for Phase 3 feedback only
- `/home/noviadi/Developments/discovery/d7y-eval-evidence/eval-execution-harness/phase-3-current-suite`
  for retained review evidence

The evidence path must not exist before execution; no existing component may be
a symlink. Create it user-owned with mode `0700`. Do not modify `SKILL.md`,
`evals.json`, canon, this prompt, or another plan.

# Permission, credentials, and cost envelope

- Profile: `implementation-commit`
- Extra tool grants: none
- Executor network: prohibited except for the Harbor trials' recorded
  agent-phase API allowlist.
- Credentials: approved trial-scoped agent key only; never expose its value and
  never pass it to the verifier.
- Authorized Harbor rollouts: exactly six—three cases by two arms.
- Per-rollout ceilings: `max_turns = 24`, `max_budget_usd = 3.00`, and the
  600-second agent timeout. Aggregate worst-case budget: USD 18.
- The rollout count is not a model-request count. The integration must enforce
  and record both ceilings. No retry, replacement, rubric model, or unrelated
  rollout.
- MCP: strict-empty.
- Docker: resources prefixed `d7y-eval-phase3-`; no trial Docker socket mount.
- Commit/lifecycle: branch commits only; no rebase, merge, push, amend, force
  operation, branch lifecycle action, or modification of `main`.

# Required work

1. Reuse the Phase 2 builder and adapter; add only the case-specific fixture and
   verifier behavior required for `resume-same-initiative` and
   `casual-brainstorm`.
2. Before the pre-run commit, implement a trajectory-derived invocation or
   command check only when Phase 2 feedback identifies the exact stable signal
   and Amp explicitly accepted it. Otherwise leave the assertion `ungradable`.
3. Run every committed case once as baseline and treatment with matched
   configuration and recorded arm order.
4. Verify creation, resume/no-duplicate, and negative/no-creation outcomes
   independently. Do not apply creation grading to the resume or negative case.
5. Grade invocation only from the accepted trajectory signal. Otherwise mark it
   `ungradable` consistently.
6. Preserve per-arm raw evidence and apply the same required-artifact,
   provenance, parity, failure, and credential controls as Phase 2.
7. Create a read-only quality-review packet for every declared rubric
   assertion, containing only the relevant artifact, assertion, provenance, and
   structured response fields. Do not self-adjudicate human judgment or call a
   model judge.
8. Produce factual per-case summaries and one six-trial inventory. Do not
   aggregate into a maturity or benchmark decision.
9. Before the first live rollout, commit all new case, fixture, grader, adapter,
   and test inputs and require a clean worktree. Record that pre-run commit in
   all six manifests. After the first rollout, do not edit source; return defects
   for a separate correction handoff. Append feedback only in a later commit.

# Verification

Run focused tests for all three case semantics, supported/unsupported assertion
dispatch, fixture isolation, pair parity, artifact failure, and summary
regeneration; exactly six live trials; independent initiative checks;
`python3 evals/validate_skill_evals.py`; `./d7y validate`;
`git diff --check`; and `git status --short`.

Confirm six unique trial IDs, no silent retry, the expected case/arm matrix, and
the enforced per-rollout ceilings. Finalize the evidence directory with its
absolute path, owner, mode, file inventory, SHA-256 hashes, and finalization
time; do not mutate it afterward.

# Stop conditions

Stop rather than widening the adapter if a case requires a new general
abstraction, the Phase 2 trace contract drifts, configuration parity fails,
private material leaks, the turn/budget ceilings cannot be enforced, or the
six-rollout cap would be exceeded. Record the specific failure and do not
continue to Phase 4.

# Completion

Append `### Phase 3 implementation feedback` with files, trial matrix, checks,
ungradable assertions, quality-review packet path, evidence path/hash,
pre-run source commit, actual usage/cost observations, deviations, and residual
risks. Commit authorized source and feedback, return a clean worktree, and
preserve evidence for Amp and human review. After executor return, Amp and the
human record the packet dispositions on the task branch before integration.
Phase 3 is not accepted until that review is complete.
