---
status: committed
plan: docs/plans/eval-execution-harness.md
execution: phase-1-harbor-smoke
executor: claude-code
branch: work/eval-harness-smoke
worktree: /home/noviadi/Developments/discovery/d7y-worktrees/eval-harness-smoke
permissionProfile: implementation-commit
commit: allowed
---

# Objective

Implement and run only Phase 1 of `docs/plans/eval-execution-harness.md`: one
Harbor-native Oracle smoke task plus the smallest negative variants needed to
verify container, network, resource, separate-verifier, artifact, timeout,
exit-state, and fake-secret handling. Do not invoke Claude Code as the Harbor
agent and do not build a D7Y case pair.

# Activation and predecessor gate

This prompt becomes executable only after Phase 0 is reviewed and integrated
into `main`, its exact versions, images, Docker context, network posture, and
provider limitations are recorded in the plan, and this prompt is committed
with `status: committed`.

The launcher-resolved starting `HEAD` is the exact base commit. It must equal
current `main`, contain the accepted Phase 0 inputs, and match the exact branch
and worktree above. Stop on mismatch, dirty state, or missing Phase 0 evidence.

# Required context

Read `AGENTS.md`, `CLAUDE.md`, `DEVELOPMENT.md`, the governing plan and its
Phase 0 feedback, `docs/skill-evaluations.md`, `docs/prompts/README.md`, the
implemented `evals/harbor/` inputs, the committed Phase 0 Harbor contract notes
and pinned installed Harbor source, and the complete base diff.

# Writable paths

- `evals/harbor/`
- `DEVELOPMENT.md`
- `docs/plans/eval-execution-harness.md` for Phase 1 feedback only
- `/home/noviadi/Developments/discovery/d7y-eval-evidence/eval-execution-harness/phase-1-harbor-smoke`
  for retained review evidence

The evidence path must not exist before execution; no existing component may be
a symlink. Create it user-owned with mode `0700`. Do not modify this prompt, a
skill, an eval definition, canon, or another plan.

# Permission and external-state envelope

- Profile: `implementation-commit`
- Extra tool grants: none
- Executor network: prohibited; all required packages and images must be
  available from Phase 0.
- Harbor trial network: only the explicit policies under test. No public default.
- Model/API calls and real credentials: prohibited.
- MCP: strict-empty.
- Docker: use resources prefixed `d7y-eval-phase1-`; no Docker socket mount in a
  trial. Clean disposable resources after collection.
- Commit and lifecycle authority: branch commits only; no rebase, merge, push,
  amend, force operation, branch lifecycle action, or modification of `main`.

# Required work

1. Create one synthetic Harbor task using Oracle and a solution script that
   actively reads declared input, writes a declared artifact, reports effective
   user/workdir, and exercises the configured network posture.
2. Use a separate verifier image with private checker material. Prove the
   agent cannot read verifier files and the verifier receives only declared
   outputs.
3. Verify absence of the source checkout, host home, host Claude settings, and
   Docker socket from the agent environment.
4. Verify CPU and memory limits, agent and verifier timeouts, fresh teardown,
   and explicit network behavior. Record storage enforcement as unsupported;
   do not run a quota probe.
5. Add only these deliberate failures: missing required artifact, non-zero
   Oracle exit, timeout, and denied network access. Preserve their diagnostics
   and map them to canonical failures.
6. Inject one fake sensitive-looking agent value and scan textual job config,
   logs, trajectory, and declared artifacts after finalization. Quarantine the
   evidence and report `evidence_error` if raw bytes remain.
7. Produce a provider capability record consumable by Phase 2. Do not implement
   skill treatment, Claude parsing, or a general provider interface.
8. Before the first Harbor smoke trial, commit every executable task, verifier,
   normalizer, and test input and require a clean worktree. Record that pre-run
   commit in every trial record. After the first trial, do not edit source; a
   defect returns for a separate correction handoff. Append feedback only in a
   later commit.

# Verification

Run and report:

- Harbor `0.20.0` task parsing;
- the positive Oracle smoke;
- the four deliberate negative variants;
- mount and verifier-boundary observations;
- environment, agent, and verifier network observations;
- CPU, memory, timeout, artifact-manifest, and cleanup observations;
- fake-value scan;
- focused deterministic tests for the smoke/result normalizer;
- `python3 evals/validate_skill_evals.py`;
- `./d7y validate`;
- `git diff --check`;
- `git status --short`.

Record exact trial identifiers and hash the retained evidence inventory. Static
task validation is not behavioral evidence. Finalize the evidence directory with
its absolute path, owner, mode, file inventory, SHA-256 hashes, and finalization
time; do not mutate it afterward.

# Stop conditions

Stop without weakening policy if a required Phase 0 image is unavailable,
Docker access changes, Harbor uses an implicit public network, verifier
separation fails, host material is mounted, or the fake value leaks. Do not
continue into Phase 2 or use model credentials.

# Completion

Append `### Phase 1 implementation feedback` to the plan with trials, results,
failure mappings, retained evidence path and inventory hash, cleanup state,
deviations, and provider limitations. Commit authorized source changes and
feedback, leaving the worktree clean. Preserve the finalized evidence directory
named under Writable paths for Amp review; do not claim acceptance or edit plan
status.
