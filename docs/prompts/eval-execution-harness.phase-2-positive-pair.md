---
status: draft
plan: docs/plans/eval-execution-harness.md
execution: phase-2-positive-pair
executor: claude-code
branch: work/eval-harness-positive-pair
worktree: /home/noviadi/Developments/discovery/d7y-worktrees/eval-harness-positive-pair
permissionProfile: implementation-commit
commit: allowed
---

# Objective

Implement and run only Phase 2 of `docs/plans/eval-execution-harness.md`: the
thin D7Y-to-Harbor adapter and one matched baseline/treatment pair for
`start-new-initiative`. Preserve raw Harbor evidence, verify parity and private
grading, and discover the actual Claude trajectory contract. Do not add the
other cases, repetitions, a model judge, or maturity scoring.

# Activation and predecessor gate

Execute only after Phase 1 is reviewed and integrated, its provider capability
record is accepted, a human has approved the exact API profile, credential key
name, two-rollout USD 6 worst-case budget, and allowed hosts, and this prompt is
committed with `status: committed`.

The launcher-resolved starting `HEAD` is the exact base commit and must be clean
current `main` containing accepted Phases 0–1. The branch, worktree, images,
Docker context, Harbor version, and API-profile digest must match recorded
inputs. Stop on any mismatch.

# Required context

Read `AGENTS.md`, `CLAUDE.md`, `DEVELOPMENT.md`, the governing plan and Phase
0–1 feedback, `docs/skill-evaluations.md`, `initiatives/README.md`,
`skills/starting-initiatives/SKILL.md` and its required references,
`skills/starting-initiatives/evals/evals.json`,
`scripts/check-initiatives.py`, `d7y`, all `evals/harbor/` inputs, relevant
committed Phase 0 Harbor contract notes and pinned installed Harbor source,
and the complete base diff.

# Writable paths

- `evals/harbor/`
- `skills/starting-initiatives/evals/graders/`
- `DEVELOPMENT.md`
- `docs/plans/eval-execution-harness.md` for Phase 2 feedback only
- `/home/noviadi/Developments/discovery/d7y-eval-evidence/eval-execution-harness/phase-2-positive-pair`
  for retained review evidence

The evidence path must not exist before execution; no existing component may be
a symlink. Create it user-owned with mode `0700`. Do not modify the skill,
`evals.json`, canon, this prompt, or another plan.

# Permission, credentials, and cost envelope

- Profile: `implementation-commit`
- Extra tool grants: none
- Executor network: prohibited except for the Harbor trial's recorded
  agent-phase API allowlist.
- Harbor credential: use only the approved trial-scoped agent environment key.
  The runner may pass its opaque value from the executor environment into the
  trial agent environment without exposing it to the model or logs. Never
  inspect, print, persist, hash, or forward it outside that trial agent process.
  The verifier and every other process receive no agent credential or API
  configuration.
- Authorized Harbor rollouts: exactly two, one baseline and one treatment.
- Per-rollout ceilings: `max_turns = 24`, `max_budget_usd = 3.00`, and the
  plan's 600-second agent timeout. Aggregate worst-case budget: USD 6.
- The rollout count is not a model-request count. The selected integration must
  enforce and record both ceilings before the first live rollout.
- No retry, replacement, model judge, or unrelated probe.
- MCP: strict-empty.
- Docker: resources prefixed `d7y-eval-phase2-`; no trial Docker socket mount.
- Commit and lifecycle authority: branch commits only; no rebase, merge, push,
  amend, force operation, branch lifecycle action, or modification of `main`.

# Required work

1. Convert only `start-new-initiative` from the immutable committed suite into
   a Harbor task with its declared prompt, synthetic workspace, public runtime
   payload, and private separate verifier.
2. Run baseline without the target skill and treatment with Harbor skill
   injection. Do not alter or wrap the prompt.
3. Verify parity for task, fixture, image, agent, model, API profile, tools,
   permissions, network, resources, timeout, verifier, and run configuration.
4. Record Harbor skill digest, D7Y source commit, and a byte match to that
   commit. Prove the baseline agent environment lacks the target skill; prove
   both agent environments lack private grader material; and prove both
   separate verifier environments contain the same private grader.
5. Validate Harbor's artifact manifest; independently run the verifier copy of
   the initiative checker without repairing output.
6. Retain raw result, trajectory, final response, artifacts, verifier output,
   timing, usage when available, and partial failure evidence.
7. Inspect the actual trajectory and document candidate runtime-owned
   invocation, command, model, and usage signals in feedback. Do not add a new
   trajectory-derived source check after observing these trials. Mark
   unsupported or not-yet-accepted invocation checks `ungradable`; Amp decides
   whether Phase 3 may implement a candidate before its pre-run commit.
8. Regenerate `manifest.json`, `checks.json`, and `summary.md` solely from
   retained evidence.
9. Before the first live rollout, commit the adapter, generated-task logic,
   private grader, tests, and every other executable input and require a clean
   worktree. Record that pre-run commit in both manifests. After the first live
   rollout, do not edit source; return defects for a separate correction
   handoff. Append runtime feedback only in a later commit.

Complete both arms unless the first exposes a common unsafe boundary failure
such as credential leakage, host mount, or invalid network policy. Do not hide
an ordinary failed arm by stopping or rerunning.

# Verification

Run focused adapter, parity, provenance, manifest, failure-mapping, and summary
regeneration tests; the two live Harbor trials; the independent initiative
checker; `python3 evals/validate_skill_evals.py`; `./d7y validate`;
`git diff --check`; and `git status --short`.

Repeat the accepted fake sensitive-value canary and scan retained textual
evidence for that canary. Never read the real credential value or use it as a
scan token. Record exact trial IDs. Finalize the evidence directory with its
absolute path, owner, mode, file inventory, SHA-256 hashes, and finalization
time; do not mutate it afterward.

# Stop conditions

Stop on predecessor drift, credential leakage, host-state leakage, implicit
public network, verifier exposure, pair mismatch, missing required provenance,
failure to enforce the per-rollout ceilings, or more than two planned rollouts.
Do not implement Phase 3 or infer invocation from outcomes.

# Completion

Append `### Phase 2 implementation feedback` with exact configuration, trial
IDs, pair checks, stable and unavailable telemetry, assertion results, retained
evidence inventory, pre-run source commit, actual spend/usage when available,
deviations, and residual risks.
Commit authorized source and feedback, return a clean worktree, and preserve the
external evidence for Amp review. Do not mark the phase accepted or the plan
done.
