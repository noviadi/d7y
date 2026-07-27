---
title: Minimal Skill Eval Runner implementation handoff
type: prompt
status: committed
createdAt: 2026-07-27
updatedAt: 2026-07-27
---

# Implementation handoff

Implement the deterministic runner and offline verification portion of `docs/plans/eval-execution-harness.md` in the assigned isolated worktree. The live positive and negative Claude Code evaluation pairs are deliberately reserved for Amp's post-implementation review because this implementation handoff prohibits network use and nested live Claude invocations.

## Execution identity and lifecycle

- Governing plan: `docs/plans/eval-execution-harness.md`.
- Execution slug: `initial`.
- Executor: Claude Code.
- Assigned branch: `work/eval-execution-harness`.
- Assigned worktree: `/home/noviadi/Developments/discovery/d7y-worktrees/eval-execution-harness`.
- Base commit: the `main` tip recorded by the launcher envelope; verify it matches the current task `HEAD` before editing.
- Commit authority: explicitly granted on the assigned `work/eval-execution-harness` branch only.
- Lifecycle authority: none beyond implementation commits. Do not create or rename branches, rebase, merge, push, remove worktrees, delete branches, amend existing commits, force Git operations, or modify this concrete prompt.

## Permission and workspace posture

- Launcher profile: `implementation-commit`.
- Extra tool grants: none.
- Network: prohibited. Do not invoke a nested live Claude Code run, access another external service, or add a network dependency. Use the committed JSONL parser constructions and local fake-executor processes for verification.
- MCP servers: none, strict-empty.
- Persistence: disabled by the launcher.
- Credentials: the launcher may import reviewed environment values for its own Claude process; do not print, inspect, persist, forward, or test them. The implemented runner must preserve the plan's env-only authentication boundary without recording values.
- Work only in the assigned worktree. Preserve unrelated changes if encountered and stop on any handoff mismatch.
- Repository edits and lifecycle restrictions apply to the assigned D7Y worktree and shared D7Y Git metadata. Focused tests may create disposable Git repositories, fixture commits, and refs under OS temporary directories, but must not modify D7Y refs, configuration, or worktrees and must remove all temporary state afterward.

## Required context

Before editing, read:

- `CLAUDE.md` and the launcher-provided handoff envelope;
- `docs/plans/eval-execution-harness.md` in full;
- `docs/discovery-workbench.md` and `docs/discovery-workbench-principles.md`;
- `docs/skill-evaluations.md`;
- `initiatives/README.md`;
- `skills/writing-great-skills/SKILL.md`;
- `skills/starting-initiatives/SKILL.md` and `skills/starting-initiatives/evals/evals.json`;
- `skills/writing-great-skills/evals/evals.json`;
- `docs/plans/runtime-initiative-cli.md` and `docs/plans/auditable-claude-delegation.md`;
- `d7y`, `scripts/check-initiatives.py`, `evals/skill-evals.schema.json`, `evals/validate_skill_evals.py`, `evals/.gitignore`, and the committed Claude Code parser fixtures.

## Writable paths

Modify or create files only within this allow-list:

- `evals/`
- `skills/starting-initiatives/evals/`
- `skills/writing-great-skills/evals/`
- `docs/skill-evaluations.md`
- `docs/plans/eval-execution-harness.md`
- `DEVELOPMENT.md`

Do not modify this prompt or the three committed `evals/fixtures/claude-code-2.1.218/*.jsonl` parser constructions. Do not modify `d7y`, initiative canon, the shared initiative implementation, any `SKILL.md`, another skill, or another plan. New files are authorized only under `evals/`; prefer the fewest cohesive standard-library modules and tests needed by the plan.

## Implementation requirements

Implement one documented Python entry point under `evals/` for one selected case and, if it remains small, one selected suite. Do not add a top-level `d7y eval` command or a multi-executor abstraction.

The implementation must honor the complete selected Claude Code 2.1.218 contract in the plan, including:

- committed-ref resolution and all repository-derived run inputs read from immutable Git objects;
- additive allowlisted workspace seeds rather than broad checkout copies;
- safe source/destination validation before staging, including traversal, symlink, and control-path rejection;
- equivalent paired workspaces with separate runtime/config/plugin/process roots and only the target plugin as treatment delta;
- a separately materialized, recorded D7Y capability installation exposed identically to both arms without using the source checkout as workspace or executable source at runtime;
- a scrubbed child environment with imported user env values applied before harness-owned overrides, source/eval/skill path-leak rejection, and no value recording;
- the exact model, effort, tools, MCP, settings, persistence, permission, plugin, and built-in `doctor` expectations recorded by the plan;
- executable/version provenance outside the event stream, monotonic duration, ten-minute process-group timeout with five-second escalation, and retained partial evidence;
- strict parsing of required `system.init`, target-specific `Skill` events, and `result` evidence, with safe failure on malformed or unknown required shapes;
- separate pair validity, treatment checks, with-skill assertions, and baseline observations;
- trusted built-in checks only, with rubric and human checks left `pending` and unavailable telemetry never represented as zero;
- raw evidence, retained workspace changes, factual summaries, and no benchmark acceptance or maturity recommendation.

Provide a dry-run/preflight mode that resolves the committed ref, validates and materializes the seed, capability, plugin, and config layout, performs leak and parity checks, and emits sanitized manifests and intended command posture without invoking or version-probing Claude and without recording environment values.

Inspect the committed parser constructions and existing deterministic D7Y contracts before changing the eval schema. Add only declarations directly supported by that committed evidence. Leave declarations whose evidence shape depends on the first real `starting-initiatives` traces unchanged and `ungradable`, and report them for post-live refinement. Fake-executor output verifies harness mechanics and must not be represented as observed behavioral evidence. Update the schema, dependency-free validator, and affected current suites consistently only for evidence-backed refinements, and preserve provisional maturity.

Treat the first real `starting-initiatives` pair as a post-implementation qualification gate, not as something to fake. The command must make that run possible, but this handoff must not execute it. Do not weaken the fixed `Skill,Read,Write,Edit,Bash` posture, skip suppression canaries, expose source/eval paths, or silently broaden permissions to make offline tests pass. Return a consequential ambiguity instead.

## Required offline verification

Run and report:

```sh
python3 evals/validate_skill_evals.py
python3 -m unittest discover -s evals -p 'test_*.py'
./d7y validate
git diff --check
```

Exercise focused valid and invalid cases with temporary synthetic workspaces and local fake Claude executables or committed parser fixtures. Coverage must include:

- positive target invocation, exact non-target `Skill` calls, and negative no-invocation parsing;
- distinct pair state, exact parity of tools/model/MCP/permission/control settings, and the exact declared plugin treatment delta;
- suppression-canary construction and simulated pass/fail detection, without representing actual instruction or global-skill suppression as proven before the live pair;
- allowlisted seed construction and absence of eval/control material;
- source checkout non-use and environment path-leak rejection;
- traversal, committed symlink, overwrite/control-path collision, malformed required-event, and unknown required-event-shape rejection;
- external version capture and monotonic timing;
- successful child execution, nonzero exit, malformed stream, timeout, and complete child-process-group termination;
- dry-run behavior that does not start or version-probe the fake executor;
- separate trace-backed D7Y command evidence and independent post-run initiative checking;
- factual result layering, pending rubric/human assertions, and expected baseline failures not invalidating a pair.

Use disposable directories outside the source checkout for behavioral tests and remove them. Tests may create temporary Git repositories and commits there solely to exercise committed-object behavior; they must not mutate D7Y Git state. Do not run a live Claude eval, create a real initiative, accept a benchmark, or claim comparative behavioral evidence.

## Completion contract

Append an `## Implementation Feedback` section to `docs/plans/eval-execution-harness.md` with:

- files changed and the implemented command;
- exact offline checks and results;
- representative fake-executor valid and invalid cases;
- the dry-run command Amp should use before the first live pair;
- any schema refinement, the committed evidence supporting it, and declarations deferred pending the first live traces;
- deviations, unsupported telemetry, platform/runtime assumptions, residual risks, and decisions returned;
- an explicit statement that no live comparative eval ran during this network-prohibited handoff.

Commit the implementation and feedback in cohesive commit(s) on `work/eval-execution-harness`, staging only writable paths. Return the resulting tip with a clean worktree and no untracked files. Do not mark the plan done: Amp must review the implementation and execute the live qualification cases first.
