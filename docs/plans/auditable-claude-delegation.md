---
title: Auditable Claude Code Delegation
type: docs
status: todo
createdAt: 2026-07-27
updatedAt: 2026-07-27
---

# Auditable Claude Code Delegation

## Outcome

Make Amp-to-Claude Code implementation delegation auditable and repeatable by preserving each concrete delegation prompt under `docs/prompts/` and invoking it through a thin deterministic launcher at `scripts/delegate-claude.sh`.

Repeatable means another operator can reconstruct the committed prompt, repository state, launcher revision, permission profile, and invocation inputs. It does not mean model output is deterministic or that Claude Code becomes an OS-level sandbox.

## Accepted decisions

- Concrete prompts use `docs/prompts/<plan-slug>.<execution-slug>.md` and remain unchanged after execution.
- Reusable prompts use `docs/prompts/<prompt-template-slug>.template.md`.
- `docs/prompts/README.md` owns the prompt artifact contract and naming rules.
- The launcher lives at `scripts/delegate-claude.sh`, takes a concrete prompt path, applies reviewed permission defaults, validates the handoff context, and invokes Claude Code with the prompt content verbatim inside a deterministic runtime envelope.
- The launcher is a thin deterministic boundary, not a workflow engine. Amp still plans, creates the branch/worktree, reviews, rebases when necessary, integrates, and performs deliberate cleanup.
- Concrete prompts do not embed their own Git commit SHA because a tracked file cannot contain the ID of the commit that contains it. The launcher resolves the exact execution base from task `HEAD`, adds it to the runtime envelope sent to Claude, and reports it for plan feedback.
- Default execution is non-interactive and least-privilege oriented: `dontAsk`, no web tools, no inherited MCP servers, no session persistence, and only the selected profile's built-in tools and command grants.
- The first profiles are `docs-commit` and `implementation-commit`. Shared defaults stay narrow; task-specific extra tool grants must be explicit launcher arguments and preserved in the concrete prompt.
- This initial bootstrap delegation may invoke Claude Code directly because the launcher does not exist yet. Amp must preserve the concrete prompt, constrain the direct invocation equivalently, and record its exact permission posture in review. Subsequent isolated handoffs use the launcher by default.
- A permission profile and prompt constrain Claude Code but do not create filesystem or process isolation. High-risk or untrusted execution still requires an OS/container sandbox.
- The launcher may detect and report a failed precondition or postcondition, but never resets, restores, rebases, merges, pushes, removes worktrees, deletes branches, or force-cleans state.

## Scope

### Add prompt artifacts

Create:

- `docs/prompts/README.md` with the artifact contract, naming, immutability, required content, effective-instruction limitations, and feedback linkage;
- `docs/prompts/delegate-implementation.template.md` as the smallest reusable implementation delegation template.

Keep this concrete prompt, `docs/prompts/auditable-claude-delegation.initial.md`, unchanged as the first auditable delegation instance.

### Add the launcher

Create executable `scripts/delegate-claude.sh` with:

- `--help` and `--dry-run`;
- one required concrete prompt path;
- `--profile docs-commit|implementation-commit` with a conservative default;
- optional explicit `--model`, `--effort`, and repeatable `--allow-tool` arguments;
- checks that the prompt is inside `docs/prompts/`, tracked, committed, and unchanged;
- checks that execution is on a non-`main` `work/<slug>` branch in a clean worktree;
- resolution and reporting of repository root, prompt commit, task base/starting `HEAD`, current branch, current worktree, Claude Code version, profile, model/effort when provided, and extra tool grants;
- a runtime envelope containing those exact values before the committed prompt content;
- Claude invocation using `--permission-mode dontAsk`, an explicit built-in tool set, strict empty MCP configuration, project-only settings, no session persistence, and structured stream output;
- exit-status preservation and non-destructive postflight reporting of branch movement, changed paths, commits created, and worktree cleanliness.

The script must quote paths and arguments safely, reject unknown arguments and invalid profiles, use no `eval`, create no persistent temporary files, and never interpret Markdown as shell commands. Task-specific `--allow-tool` values are passed as Claude Code permission matchers, not executed by the launcher.

Profile defaults must be documented in the script and prompt README. Do not claim path-level write sandboxing. `implementation-commit` may expose broader build/test capability only when unavoidable; explain the trust boundary rather than disguising generic shell access as least privilege.

### Update constitutions

Update `AGENTS.md` so Amp must:

- preserve and commit the concrete prompt before creating the task worktree;
- use the launcher by default for isolated Claude Code handoffs;
- record the prompt path, prompt commit, launcher commit, resolved base, Claude Code version, model/effort, permission profile, extra grants, and resulting tip during review;
- treat prompt preservation as evidence, not proof of deterministic output or sandboxing;
- retain lifecycle authority: normal Claude implementation handoffs never delegate rebase, merge, push, worktree removal, or branch deletion.

Update `CLAUDE.md` so Claude Code:

- treats the launcher-provided runtime envelope plus committed prompt and governing plan as the handoff;
- reports a mismatch rather than overriding resolved context;
- does not modify the concrete prompt after execution begins;
- never performs lifecycle actions during a normal implementation handoff.

Keep both constitutions concise and consistent. Do not modify product-runtime canon; this is the repository development handoff binding, not first-class runtime support.

### Record feedback

Append implementation feedback to this plan with:

- files changed;
- exact checks and results;
- a dry-run example showing the resolved envelope and permission posture without invoking Claude;
- valid and invalid script cases;
- deviations;
- residual risks;
- decisions returned.

## Verification

- `bash -n scripts/delegate-claude.sh`
- `scripts/delegate-claude.sh --help`
- A dry run from the assigned clean task worktree succeeds and reports the exact prompt, branch, worktree, starting HEAD, profile, and command posture without invoking Claude.
- Focused invalid cases reject an untracked prompt, a dirty prompt, an invalid profile, and execution from `main`; use disposable files or isolated temporary repositories and clean them afterward.
- `git diff --check`
- Search changed files for contradictory permission, lifecycle, prompt immutability, script-location, and path claims.

## Stop conditions

- Stop if Claude Code 2.1.218 does not support a required flag as observed from live `--help`; report the mismatch rather than silently weakening permissions.
- Stop if the launcher would need to parse arbitrary Markdown into commands, persist credentials, or automate Amp's review/integration authority.
- Stop if safe focused invalid-case testing would require destructive operations in the main checkout or another agent's worktree.
- Stop and return any requirement for true filesystem isolation as a separate sandbox design decision.

## Anti-goals

- Deterministic model output.
- A general orchestration framework or prompt registry.
- Automatic plan generation, prompt acceptance, worktree creation, rebase, integration, push, or cleanup.
- Treating `--allowedTools`, the committed prompt, or a linked worktree as an OS security sandbox.
- Storing secrets, credentials, or raw sensitive traces in prompts or plans.
- A templating engine in this increment; the template is copied and completed by Amp.
