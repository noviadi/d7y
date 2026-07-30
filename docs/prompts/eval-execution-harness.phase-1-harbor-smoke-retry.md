---
status: committed
plan: docs/plans/eval-execution-harness.md
execution: phase-1-harbor-smoke-retry
executor: claude-code
branch: work/eval-harness-smoke-retry
worktree: /home/noviadi/Developments/discovery/d7y-worktrees/eval-harness-smoke-retry
permissionProfile: implementation-commit
commit: allowed
---

# Objective

Implement and execute only Phase 1 of `docs/plans/eval-execution-harness.md`:
one Harbor 0.20.0 Oracle smoke task and the four required deliberately broken
variants. Produce the provider capability record and append Phase 1 feedback to
the governing plan. Do not implement Phase 2, a general provider interface,
skill treatment, Claude parsing, or a D7Y case pair.

# Execution posture

Phase 0 is already reviewed and integrated at the launcher-resolved base.
Use the recorded Phase 0 inputs exactly: profile
`evals/harbor/profiles/claude-primary.json`, envelope
`evals/harbor/config/execution-posture.json`, agent image
`d7y-eval-phase0-agent:2.1.218`, verifier image
`d7y-eval-phase0-verifier:phase0`, the payload manifest, and the posture
validator. Do not weaken a network, mount, resource, timeout, verifier, or
credential policy to make a trial pass. If a prerequisite is missing or a
policy cannot be proven, stop and record the blocker.

Read the governing plan and Phase 0 feedback, `AGENTS.md`, `CLAUDE.md`,
`DEVELOPMENT.md`, `docs/prompts/README.md`, `docs/skill-evaluations.md`, and
the implemented `evals/harbor/` inputs. Read enough Harbor source to use the
documented task schema, then implement promptly; do not spend the execution
on exhaustive Harbor source archaeology or speculative framework changes.

# Scope and writable paths

Only modify:

- `evals/harbor/`
- `DEVELOPMENT.md`
- `docs/plans/eval-execution-harness.md` for the required Phase 1 feedback
- `/home/noviadi/Developments/discovery/d7y-eval-evidence/eval-execution-harness/phase-1-harbor-smoke`

Do not modify this prompt, the earlier Phase 1 prompt, skills, eval
definitions, canon, another plan, or `main`. Use only synthetic values and do
not invoke Claude Code as the Harbor agent or use real credentials.

The evidence directory must be absent before execution, user-owned, mode
`0700`, finalized with an absolute-path record, file inventory, SHA-256 hashes,
and finalization time, and absent from Git. Use Docker resources prefixed
`d7y-eval-phase1-`; clean disposable resources after collection.

# Required implementation and observations

Create a synthetic Oracle task and solution that reads declared input, writes a
declared artifact, records effective user/workdir, and exercises explicit
network policy. Use the separate verifier image with private checker material;
prove the agent cannot read verifier files and the verifier receives only
declared outputs. Prove no source checkout, host home, host Claude settings, or
Docker socket is visible. Record CPU/memory, agent/verifier timeouts, teardown,
artifact manifests, and the planned unsupported local storage-quota
capability; do not run a quota probe.

Run exactly these negative variants: missing required artifact, non-zero Oracle
exit, timeout, and denied network. Preserve diagnostics and map them to the
canonical failures. Inject one synthetic fake sensitive-looking value and scan
task config, logs, trajectory, and declared artifacts after finalization;
quarantine and report `evidence_error` if it leaks.

Before the first trial, commit all executable task, verifier, normalizer, and
test inputs and require a clean worktree. Record that pre-run commit in every
trial record. After the first trial, source edits require a separate correction
handoff; do not silently edit-and-rerun within this handoff.

# Verification and completion

Run Harbor 0.20.0 parsing, the positive smoke, all four negative variants,
mount/verifier-boundary checks, environment/agent/verifier network checks,
resource/timeout/artifact/cleanup checks, fake-value scanning, focused
deterministic smoke/normalizer tests, `python3 evals/validate_skill_evals.py`,
`./d7y validate`, `git diff --check`, and `git status --short`. Distinguish
static validation from behavioral evidence. Append
`### Phase 1 implementation feedback` to the governing plan with exact trial
IDs, results, mappings, evidence inventory hash, cleanup, deviations, and
provider limitations. Commit authorized changes on this branch only and leave
the worktree clean. Do not claim plan acceptance or change plan status. Do not
rebase, merge, push, amend, force, or perform branch/worktree lifecycle
operations.
