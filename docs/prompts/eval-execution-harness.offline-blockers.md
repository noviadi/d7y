---
title: Minimal Skill Eval Runner offline-blocker correction
type: prompt
status: committed
createdAt: 2026-07-28
updatedAt: 2026-07-28
---

# Offline-blocker correction

Correct the rejected eval-runner rewrite on `work/eval-execution-harness` so its public CLI and complete-arm behavior satisfy `docs/plans/eval-execution-harness.md`. The current tip `4efffc5` passes its self-authored offline tests but is blocked from live qualification by independent review. Preserve sound ownership boundaries where useful, but do not preserve an implementation or test structure that masks the public runtime contract. Do not run a live Claude eval; Amp retains that gate.

## Execution identity and lifecycle

- Governing plan: `docs/plans/eval-execution-harness.md`.
- Execution slug: `offline-blockers`.
- Executor: Claude Code.
- Assigned branch: `work/eval-execution-harness`.
- Assigned worktree: `/home/noviadi/Developments/discovery/d7y-worktrees/eval-execution-harness`.
- Base: the launcher-resolved starting `HEAD`, rebased onto the commit containing this prompt.
- Commit authority: granted only on the assigned task branch. Add cohesive correction commit(s); do not amend or squash existing commits.
- Lifecycle authority: none beyond task-branch commits. Do not create, rename, or delete branches; rebase; merge; push; remove worktrees; amend; or force any Git operation.

## Permission and runtime posture

- Launcher profile: `implementation-commit`.
- Launcher model/effort: `opus --effort medium`. This deliberately avoids repeating the twice-stalled `opus --effort high` posture. The expected routed assistant model in this user environment is GLM-5.2; stop and report before editing if routing resolves differently.
- Extra tool grants: none.
- Network: prohibited. Never invoke a nested live Claude run or external service. Use strict behavioral fake executors and committed parser fixtures only.
- MCP: strict-empty. Persistence: disabled.
- Credentials: never print, inspect, persist, forward, or test real values. Tests must inject synthetic settings and environment values.
- Tests may create disposable Git repositories and process trees only under OS temporary directories and must clean them.

The implementation runner requests `claude-sonnet-5`. Its live execution may intentionally route assistant events to a permitted z.ai model; requested/canonical model and routed assistant model are separate evidence. Do not use this implementation handoff's launcher model as evidence for the eval runner's eventual live model contract.

## Required context

Before editing, read:

- `CLAUDE.md`, the launcher envelope, and this prompt;
- `docs/plans/eval-execution-harness.md` in full, treating its implementation-feedback claims as untrusted;
- `docs/prompts/eval-execution-harness.opus-alias-retry.md`, its incorporated `docs/prompts/eval-execution-harness.opus-rewrite.md`, and earlier correction prompts;
- the complete `f82c860...HEAD` diff and the rewrite delta `09c9571...HEAD`;
- `evals/run_eval.py`, `evals/test_run_eval.py`, all three immutable Claude fixtures, the eval schema, validator, and both current suites;
- `skills/starting-initiatives/SKILL.md` and required runtime references;
- `d7y`, `scripts/check-initiatives.py`, `initiatives/README.md`, `docs/skill-evaluations.md`, `DEVELOPMENT.md`, and the current installed `claude --help` output needed to construct a supported CLI contract.

## Writable paths

Modify or create files only within:

- `evals/`, except the existing `evals/fixtures/claude-code-2.1.218/*.jsonl` files are read-only;
- `skills/starting-initiatives/evals/`;
- `skills/writing-great-skills/evals/`;
- `docs/skill-evaluations.md`;
- `docs/plans/eval-execution-harness.md`;
- `DEVELOPMENT.md`.

Do not modify prompts, any `SKILL.md`, D7Y/initiative implementation or canon, another skill, or another plan. Prefer correcting `evals/run_eval.py` and `evals/test_run_eval.py` rather than adding layers or new abstractions.

## Blocking corrections

### 1. Bind the workspace through a supported Claude command

- Remove the unsupported top-level Claude `--root` flag. Claude Code 2.1.218 `--help` does not declare it.
- Start both agents in the distinct process-start directory as planned. Wrap the unchanged case prompt in identical neutral harness instructions that identify that arm's absolute target workspace and require D7Y commands to use `--root <absolute workspace>`. The treatment delta remains only the target plugin.
- Keep exactly one `--tools Skill,Read,Write,Edit,Bash` value and all supported fixed print, verbose, stream JSON, no-persistence, strict-empty MCP, permission, model, effort, setting-source, settings, and plugin flags.
- Replace fakes that invent `--root` semantics with strict parsers that reject every unknown option, record the actual argv, and obtain the target workspace only from the prompt contract. Assert the two actual arm argv records and prompt bindings, not a second call to the production argv helper.

### 2. Redact every imported environment value from every output

- Keep imported environment values in memory only as child-process inputs and redaction tokens. Preserve provenance by source and sorted key names only.
- Recursively sanitize every persisted or user-visible text/JSON field: raw stdout and stderr, parsed events, final response, telemetry, argv/provenance, checker stdout/stderr/parsed data, checks, summaries, manifests, diagnostics, and failure artifacts. Do not include a secret value in an exception.
- Add a public-CLI fake that echoes a synthetic imported value through raw stdout, raw stderr, a tool result, final response, and checker-visible output. Recursively scan every generated file and captured CLI output to prove the value is absent while its key-name provenance remains.

### 3. Prove exact successful D7Y command execution

- Replace substring detection with a deliberately narrow parser for the supported simple Bash command shape. Require exact tokenized commands `d7y initiatives list --root <this-arm-workspace> --json` and `d7y initiatives check --root <this-arm-workspace> --json`; reject wrappers, prefixes, compound commands, wrong roots, missing/duplicate flags, and quoted evidence inside `echo` or similar commands.
- Correlate each Bash `tool_use` ID with a later non-error `tool_result`, preserve its result evidence, and require list before check. Require successful, parseable JSON evidence where the observed stream contract supports it. Unsupported or incomplete trace shapes are `ungradable`, never `pass`.
- Keep this agent-command evidence separate from the independently executed installed checker. Tests must include wrong-root, quoted-substring, absent-result, error-result, reversed-order, and valid traces.

### 4. Require exact runtime state and successful process outcome

- Require exact accounted skills: `{d7y-eval-session:starting-initiatives, doctor}` with-skill and `{doctor}` baseline. Require the one expected plugin and no extras, exact tools, empty MCP, permission mode, requested model, distinct nonempty sessions, and clean canaries.
- Require exactly one init and one result; an explicitly successful terminal subtype, `is_error == false`, correctly typed required result fields, no permission denials, zero subprocess exit, and no timeout. A valid-looking stream followed by nonzero exit must invalidate the arm and pair.
- Require `modelUsage` to contain the canonical `claude-sonnet-5` entry and preserve provider/canonical metadata available in the selected event contract. Permit only routed assistant models supported by committed capability evidence or explicitly returned for live qualification; do not silently widen the allowlist.
- Add complete-arm public tests for every invalid terminal/process/runtime-state variant rather than relying only on parser helper tests.

### 5. Make preflight atomic and source-safe on every exit

- Capture source status before creating or writing any output or staging material.
- Require a genuinely new output path: reject every existing entry, including an empty directory, and reject a symlink at the output path or in any existing parent component. Keep output and source mutually disjoint.
- Prevalidate the complete materialization/staging map before writes. Reject equality and ancestor/descendant destination collisions such as `a` versus `a/b`, symlinks, unsafe paths, control collisions, and overwrites.
- Route dry-run, preflight errors after the snapshot, executable-resolution errors, arm errors, and normal completion through one final source comparison that controls the CLI status. Record before and after status without leaking the source path. Source mutation invalidates dry and live outcomes.
- Prove these through the public CLI. Direct helper tests may supplement but cannot replace boundary tests.

### 6. Use canaries that can detect instruction loading

- Keep both canaries only in runtime locations the selected posture claims to suppress; never positively expose their content through prompt, environment, workspace, plugin, settings argument, or another skill root.
- Give the project-instruction canary a unique required observable response or tool signal if loaded, and detect that signal throughout relevant event and result content. Keep fake-global-skill discovery and invocation checks exact.
- Add a structurally valid complete-arm fake where canary leakage is the only invalidating fact. Offline tests prove only placement and detection mechanics; real suppression remains a live gate.

### 7. Always emit the complete evidence inventory

- Create explicit result records for both arms before executable resolution and route every outcome through one finalization path.
- Always emit every named per-arm artifact, even when unavailable or empty: raw stream, raw stderr, process/unstarted state, final response, telemetry, executable/argv provenance, command events/results, independent checker record, workspace changes or retained snapshot, selected-object evidence, validation, and arm summary. Emit pair checks, manifest, source before/after evidence, and factual summary for every post-output failure.
- Spawn errors, executable-resolution errors, malformed streams, nonzero exits, and timeouts must retain explicit states and complete partial evidence. Snapshot each workspace even when parsing or execution fails.
- Apply the redaction contract from correction 2 to the entire inventory. Tests must assert the full inventory for each failure class, not a representative subset.

### 8. Grade only supported declarations and detect all workspace changes

- Validate the selected immutable suite with the committed schema/validator contract before materialization; do not accept only a hand-written minimal shape.
- Dispatch deterministic assertions by explicit supported assertion ID and semantics, not broad dimension or `should_trigger` heuristics. Unknown deterministic declarations are `ungradable` and required ungradable checks block pass.
- Correctly distinguish the first-slice positive creation case, negative control, and resume/no-duplicate semantics if that case is exposed. Do not apply initiative-creation grading to `writing-great-skills`; either support a declaration honestly or constrain the CLI to the approved first-slice cases with a clear preflight error.
- Hash the complete staged workspace baseline and report added, modified, and deleted paths after every arm. Staged-file edits or removals must not disappear from evidence.
- Add public cases for unknown deterministic IDs, resume/no-duplicate semantics or explicit unsupported-case rejection, writing-great-skills rejection/support, and added/modified/deleted workspace evidence.

## Preserve already-sound behavior

Retain or replace without regression the parts independently substantiated at `4efffc5`: immutable Git-object reads for selected inputs and real blob IDs; authentic distinct plugin/workspace/config/temp/artifact roots; both committed D7Y capability objects in one shared installation; dry-run zero executable resolution/probe/invocation; one executable version probe reused by two live arms; exact target `Skill` invocation counting; process-group timeout escalation and partial stream capture; and required pending/ungradable/error/fail assertions blocking pass. Passing old tests is not evidence if the test boundary is misleading.

## Required verification

Run and report:

```sh
python3 evals/validate_skill_evals.py
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s evals -p 'test_*.py'
./d7y validate
git diff --check
git status --short
```

Also run the public dry-run for committed `start-new-initiative` with a nonexistent or invocation-recording executable, synthetic user settings, and a disposable new output path. Inspect authentic plugin trees, root separation, no control files in workspaces, sanitized manifests/artifacts, supported intended argv, and prompt workspace binding; then remove only that disposable output. Never run the public runner against real Claude.

## Feedback and completion

Replace the plan's current `## Implementation Feedback` section with one concise factual record. Include exact public tests run, accepted offline evidence, the supported Claude argv correction, deferred live gates, routing distinction, deviations, and residual risks. Do not mark the plan done, claim a live comparison, or claim suppression/runtime portability from fakes.

Commit cohesive corrections on the assigned task branch, staging only authorized paths. Return a clean worktree with no untracked files. Explicitly report anything unproven rather than weakening or simulating it. The branch remains blocked until Amp independently reviews the complete base-to-tip diff and only then performs the retained live qualification gates.
