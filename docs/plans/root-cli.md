---
title: Thin Root CLI
type: docs
status: done
createdAt: 2026-07-27
updatedAt: 2026-07-27
---

# Thin Root CLI

## Outcome

Add an executable `./d7y` at the repository root as the canonical local command façade for D7Y development. It gives developers one discoverable command vocabulary while retaining the existing Bash and Python scripts as independently executable implementation units.

This is a repository CLI, not a workflow engine, durable control plane, or supported end-user host binding. It owns command discovery and deterministic dispatch only.

## Accepted decisions

- `./d7y` is the canonical repository-level invocation surface.
- The first implementation is a dependency-free Bash dispatcher because the repository already requires Bash for delegation and Python 3 for validation; choosing Node or Bun only to alias those commands would add an unjustified package boundary.
- Existing scripts remain the source of their behavior. The CLI forwards to them rather than copying validation or delegation logic.
- The CLI resolves the repository root from its own location and works when invoked from another current directory.
- No `package.json` is added. A future package manifest may expose convenience aliases that call `./d7y`, but package-manager commands must not become a second source of command semantics.
- Development-only delegation remains visibly namespaced under `dev`; the CLI does not imply that Claude Code is a supported D7Y product runtime.

## Command contract

Implement these commands:

```text
./d7y [help|-h|--help]
./d7y validate
./d7y validate evals [evals.json ...]
./d7y validate initiatives [checker options ...]
./d7y dev delegate [launcher options ...] <concrete-prompt-path>
```

Behavior:

1. No arguments, `help`, `-h`, and `--help` print concise usage to stdout and exit `0`.
2. `validate` runs both existing validators from the repository root, in this order, and stops at the first failure:
   - `python3 evals/validate_skill_evals.py`
   - `python3 skills/starting-initiatives/scripts/check_initiatives.py --root .`
3. `validate evals` runs the eval validator from the repository root and forwards every remaining argument unchanged. This preserves its optional explicit `evals.json` paths.
4. `validate initiatives` runs the initiative checker from the repository root and forwards every remaining argument unchanged. Its existing `--root` and `--json` options remain available.
5. `dev delegate` executes `scripts/delegate-claude.sh` from the repository root and forwards every remaining argument unchanged, including `--help`, `--dry-run`, profile options, and the prompt path.
6. A missing subcommand or unknown command prints a short diagnostic and usage to stderr and exits `2` without invoking an underlying script.
7. For a recognized leaf command, preserve the underlying script's stdout, stderr, and exit status. Use `exec` when no aggregate sequencing remains.

The help text should describe the three useful command groups without reproducing every leaf script option. Users can obtain detailed leaf help with `./d7y dev delegate --help`, `./d7y validate initiatives --help`, or the underlying script where no help option currently exists.

## Scope

### Add the dispatcher

Create root-level executable `d7y` with:

- `#!/usr/bin/env bash` and fail-safe shell options;
- location-based repository-root resolution that handles spaces in paths;
- a small explicit `case`-based command tree;
- safe array/argument quoting and no `eval`;
- prerequisite failures left visible from the owning script or runtime;
- no temporary or persistent state.

Keep the dispatcher direct. Do not introduce helper libraries, command registries, plugin discovery, generated command definitions, or a second implementation of any validator or launcher precondition.

### Document the entrypoint

Update `README.md` with a short "Repository CLI" section that:

- identifies `./d7y` as the canonical local command façade;
- shows the aggregate validation and development delegation examples;
- states that the underlying scripts remain directly executable;
- characterizes the CLI as repository tooling rather than first-class product-runtime support;
- does not duplicate detailed launcher or validator documentation.

### Record implementation feedback

Append an `## Implementation Feedback` section to this plan containing:

- files changed;
- exact checks and results;
- any deviation from the command contract;
- residual risks or unsupported environments;
- decisions returned to Amp or the human.

## Verification

Run from the assigned task worktree:

```sh
bash -n d7y
./d7y --help
./d7y validate
./d7y validate evals
./d7y validate initiatives --json
./d7y dev delegate --help
(cd docs && ../d7y validate evals)
```

Also verify focused invalid dispatch without changing repository state:

```sh
./d7y unknown
./d7y validate unknown
./d7y dev unknown
```

Each invalid command must exit `2`, write a useful diagnostic to stderr, and not invoke an underlying tool. Finally run:

```sh
git diff --check
```

If `shellcheck` is installed, run it against `d7y`; otherwise record that it was unavailable rather than adding a dependency.

## Acceptance criteria

1. A developer can discover the supported command groups with `./d7y --help`.
2. All three existing deterministic entrypoints are reachable through the documented command tree.
3. Existing leaf arguments, output, and exit codes are preserved.
4. Validation works from the repository root and when `d7y` is invoked from another directory.
5. Unknown command paths fail before invoking another script and use exit status `2`.
6. `d7y` is executable in Git and introduces no Node, Bun, package-manager, or third-party runtime dependency.
7. README wording does not claim a durable control plane or supported product host binding.
8. The implementation remains a small dispatcher with no copied domain logic or premature extensibility.

## Anti-goals

- A discovery workflow engine or encoded `Frame → Diverge → Select` sequence.
- Durable initiative, plan, task, or session state in the CLI.
- Automatic skill selection, agent routing, worktree lifecycle, review, merge, push, retry, scheduling, or resumability.
- A generic provider, command-plugin, or backend abstraction.
- Installing `d7y` globally or modifying `PATH`.
- Adding `package.json`, selecting Node versus Bun, or publishing a package.
- Changing any existing validator or delegation-launcher behavior.
- Claiming this repository façade establishes a first-class D7Y runtime binding.

## Stop conditions

- Stop if satisfying the command contract requires changing an underlying validator or delegation launcher rather than forwarding to it.
- Stop if an accepted command cannot preserve the owning script's arguments or exit status without inventing a new public option model.
- Stop and return any request to add workflow judgment, persistent state, automatic lifecycle actions, package infrastructure, or product-runtime support; those are separate architecture decisions.
- Preserve unrelated worktree changes and report any verification blocked by the environment.

## Implementation Feedback

Executor: Claude Code. Branch: `work/root-cli`. Executed from the assigned worktree at `/home/noviadi/Developments/discovery/d7y-worktrees/root-cli`.

### Files changed

- `d7y` (new executable, mode `0755`): dependency-free Bash dispatcher. Resolves the repository root from its own location via `readlink -f`, `cd`s there, and dispatches a small explicit `case` tree. Leaf commands (`validate evals`, `validate initiatives`, `dev delegate`) `exec` the underlying script; aggregate `validate` runs evals then initiatives under `set -e`. No `eval`, no temp/persistent state, no helper library.
- `README.md`: added a short "Repository CLI" section after the Repository section. Characterizes `./d7y` as repository tooling, shows aggregate validation and delegation examples, and states the underlying scripts remain directly executable. Does not duplicate leaf documentation.
- `docs/plans/root-cli.md`: this feedback section only.

No validator, launcher, prompt, or canonical document was modified.

### Exact checks and results

Required plan verification (run from the worktree root):

- `bash -n d7y` → rc `0`.
- `./d7y --help` → usage on stdout, exit `0`.
- `./d7y validate` → both validators pass, exit `0` (evals: 2 suites valid; initiatives: valid, 0 found).
- `./d7y validate evals` → 2 suites valid, exit `0`.
- `./d7y validate initiatives --json` → valid JSON, exit `0`.
- `./d7y dev delegate --help` → forwards to the launcher's usage, exit `0` (no live Claude run).
- `(cd docs && ../d7y validate evals)` → 2 suites valid, exit `0` (root resolution works from another current directory).

Invalid dispatch (each captured with stdout/stderr separated):

- `./d7y unknown` → exit `2`, empty stdout, diagnostic `d7y: unknown command: unknown` plus usage on stderr.
- `./d7y validate unknown` → exit `2`, empty stdout, diagnostic `d7y: unknown validate subcommand: unknown` plus usage on stderr.
- `./d7y dev unknown` → exit `2`, empty stdout, diagnostic `d7y: unknown dev subcommand: unknown` plus usage on stderr.

Empty stdout in all three confirms no underlying validator or launcher was invoked.

Additional contract checks:

- `./d7y`, `./d7y help`, `./d7y -h` → usage on stdout, exit `0`.
- `./d7y validate initiatives --help` → checker's argparse help forwarded, exit `0`.
- `./d7y validate evals /tmp/does-not-exist.json` → validator's own `INVALID:` output and exit `1` preserved through `exec` (leaf exit-status/output preservation without mutating repository state).
- `git diff --check` → clean, rc `0`.
- `shellcheck d7y` → not run; `shellcheck` is not installed in this environment.

### Deviations from the command contract

None. All six commands and the failure contract behave as specified.

### Residual risks and unsupported environments

- Root resolution uses `readlink -f`, already a repository dependency (`scripts/delegate-claude.sh` uses the same). Environments without GNU `readlink -f` are unsupported, consistent with the existing launcher.
- Aggregate `validate` stop-at-first-failure relies on `set -e`: the second validator's status is observable only when the first passes. Not exercised with a forced first-validator failure to avoid mutating repository state; the behavior is structural.
- `validate evals [paths...]` interprets relative path arguments against the repository root (the dispatcher `cd`s there before forwarding), matching the plan's "runs ... from the repository root" wording; callers should pass repo-relative paths.
- `shellcheck` static linting was unavailable; `bash -n` syntax validation was run instead.

### Decisions returned to Amp or the human

None. No scope expansion, workflow judgment, persistent state, package infrastructure, product-runtime support, or permission expansion was needed or requested.
