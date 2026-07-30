---
status: draft
plan: docs/plans/eval-execution-harness.md
execution: phase-5-reconcile-foundation
executor: claude-code
branch: work/eval-harness-reconcile
worktree: /home/noviadi/Developments/discovery/d7y-worktrees/eval-harness-reconcile
permissionProfile: implementation-commit
commit: allowed
---

# Objective

Implement only Phase 5 of `docs/plans/eval-execution-harness.md`: reconcile the
accepted Phase 4 evidence into the smallest stable task builder, checks, result
normalization, contributor instructions, and plan feedback. Reproduce summaries
from retained evidence without any new model trial. Do not change a skill,
promote maturity, accept a benchmark, or make provider-hardening claims.

# Activation and predecessor gate

Execute only after Phase 4's eighteen-trial evidence and quality dispositions
are reviewed, retained at
`/home/noviadi/Developments/discovery/d7y-eval-evidence/eval-execution-harness/phase-4-repeated-comparison`,
inventory-verified, and accepted as the input to reconciliation; any required
correction handoff is already integrated; and this prompt is committed with
`status: committed`.

The launcher-resolved starting `HEAD` is the exact clean `main` base containing
accepted Phases 0–4. The branch, worktree, source revision, evidence inventory
hash, and frozen configuration must match the plan. Stop on mismatch or missing
raw evidence.

# Required context

Read `AGENTS.md`, `CLAUDE.md`, `DEVELOPMENT.md`, the governing plan and all phase
feedback, `docs/discovery-workbench.md`, `docs/discovery-workbench-principles.md`,
`docs/skill-evaluations.md`, current suites and schema, all accepted
`evals/harbor/` implementation and tests, the complete retained Phase 4 raw and
normalized evidence, the accepted quality dispositions, and the complete base
diff.

# Writable paths

- `evals/harbor/`
- `DEVELOPMENT.md`
- `docs/plans/eval-execution-harness.md` for Phase 5 feedback only
- `/home/noviadi/Developments/discovery/d7y-eval-evidence/eval-execution-harness/phase-5-reconcile-foundation`
  for retained regeneration evidence

Do not modify a skill, eval definition, eval schema, canonical document, this
prompt, or another plan. Canonical changes discovered here must be proposed in
feedback for Amp and human review, not applied by the executor.

The Phase 5 evidence path must not exist before execution; no existing component
may be a symlink. Create it user-owned with mode `0700`. Treat the Phase 4
evidence directory as read-only.

# Permission envelope

- Profile: `implementation-commit`
- Extra tool grants: none
- Network: prohibited.
- Model/API calls and credentials: prohibited.
- MCP: strict-empty.
- Docker: no new Harbor trial. A local deterministic container command is
  allowed only when an accepted test requires it and must use prefix
  `d7y-eval-phase5-`.
- Commit/lifecycle: cohesive branch commits only; no rebase, merge, push,
  amend, force operation, branch lifecycle action, or modification of `main`.

# Required work

1. Verify the retained Phase 4 evidence inventory against its recorded hashes
   before using it.
2. Regenerate every normalized check and evidence-only summary from raw evidence
   into the Phase 5 evidence directory without repair, model calls, or hidden
   manual inputs. Quality assertions remain `ungradable` in these generated
   outputs.
3. Keep checks only when their required signal was stable and they distinguish
   meaningful behavior. Remove or narrow checks that passed equally in both
   arms, depended on unstable event shapes, or inferred unsupported facts.
4. Preserve `unavailable`, `ungradable`, and canonical failure semantics. Do not
   turn absent telemetry into zero or success.
5. Keep the adapter Harbor-specific and small. Do not introduce a generic
   executor, service, database, scheduler, plugin system, or top-level product
   command.
6. Update contributor instructions only for commands and limitations that the
   accepted evidence actually proves.
7. List proposed canonical or binding-record updates, if any, with exact
   evidence and consequences. Leave their acceptance to Amp and the human.
8. Verify accepted human dispositions separately against stable trial and
   assertion identifiers in the Phase 4 quality packet and plan feedback. Do
   not merge them into regenerated machine-derived results.

# Verification

Run and report:

- evidence-inventory hash verification;
- deterministic regeneration of all Phase 4 normalized outputs;
- a clean comparison between regenerated and accepted evidence-only summaries;
- referential validation of plan-level human dispositions against the immutable
  quality packet;
- focused valid, invalid, missing-artifact, malformed-trajectory, and
  unsupported-telemetry tests;
- `python3 evals/validate_skill_evals.py`;
- `./d7y validate`;
- `git diff --check`;
- `git status --short`.

No verification step may contact a model endpoint or silently rerun Harbor.
Finalize the Phase 5 evidence directory with its absolute path, owner, mode,
file inventory, SHA-256 hashes, and finalization time; do not mutate it
afterward.

# Stop conditions

Stop if retained evidence is missing or hash-mismatched, regeneration requires
manual repair, a proposed check lacks stable evidence, or completion requires a
constitutional change. Record the blocker and return it rather than inventing
evidence, weakening a check, or expanding scope.

# Completion

Append `### Phase 5 implementation feedback` with files, evidence inventory,
regeneration evidence path and inventory, results, disposition-reference
validation, checks kept/removed and why, tests, deviations, provider and
telemetry limitations, proposed canonical updates, and residual risks. Commit
authorized changes and return a clean worktree. Do not set plan status to
`done`; Amp reviews the complete phase history, reconciles accepted canon, and
owns final plan closure.
