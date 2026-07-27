---
title: Auditable Claude Code Delegation
type: docs
status: done
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

## Implementation feedback

### Result

Implemented the preserved-prompt contract and template, the executable launcher at `scripts/delegate-claude.sh`, and the Amp/Claude handoff bindings in `AGENTS.md` and `CLAUDE.md`.

The launcher validates a committed unchanged prompt, clean assigned `work/<slug>` checkout, and supported profile; resolves the execution envelope; streams the committed prompt bytes to Claude without evaluating Markdown; applies explicit tools, `dontAsk`, strict-empty MCP, project-only settings, and no persistence; then reports exit status, branch movement, commits, changed paths, and cleanliness without repairing state.

### Files changed

- `AGENTS.md`
- `CLAUDE.md`
- `docs/prompts/README.md`
- `docs/prompts/delegate-implementation.template.md`
- `scripts/delegate-claude.sh`
- this plan (feedback only)

The executed concrete prompt `docs/prompts/auditable-claude-delegation.initial.md` remained unchanged.

### Bootstrap execution evidence and deviations

The launcher did not exist at delegation time, so Amp used the plan's direct-bootstrap exception. Claude Code 2.1.218 was invoked on `work/auditable-claude-delegation` from base `38b059d23e954d7af7d82151dc789bf4b0f030cb`, with Sonnet, explicit `Read,Edit,Write,Bash`, `dontAsk`, no network tools, strict-empty MCP, no session persistence, and no lifecycle authority.

Project-only settings could not refresh the environment's OAuth credentials, while normal and safe-mode probes succeeded. Bootstrap therefore used `--safe-mode` and explicitly required Claude to read `CLAUDE.md`; this is a deviation from the launcher's intended `--setting-sources project` posture. One Opus/high run and two Sonnet retries stalled for prolonged reasoning without completing. The final low-effort retry produced the scoped files but was terminated before validation, feedback, or commit. Amp reviewed and retained those changes, corrected the strict-empty MCP JSON, preserved the prompt bytes through stdin, improved postflight changed-path reporting, ran verification, and committed the result. No permissions or lifecycle authority were widened after the handoff.

### Checks and results

- `bash -n scripts/delegate-claude.sh` — passed.
- `scripts/delegate-claude.sh --help` — passed.
- `git diff --check` — passed before the implementation commit.
- Focused terminology search across the changed constitutions, prompt artifacts, launcher, and plan — no contradictory script-location, lifecycle, prompt-immutability, deterministic-output, or sandbox claim found.
- `shellcheck scripts/delegate-claude.sh` — not run; `shellcheck` is unavailable in this environment.
- Clean-worktree dry run with `--profile implementation-commit --model sonnet --effort low` — passed without invoking Claude. It resolved prompt `docs/prompts/auditable-claude-delegation.initial.md` at `38b059d23e954d7af7d82151dc789bf4b0f030cb`, branch `work/auditable-claude-delegation`, the exact sibling worktree, starting HEAD, Claude Code 2.1.218, broad implementation profile, strict-empty MCP, project-only settings, and disabled persistence.
- Disposable-repository cases — valid dry run returned 0; untracked prompt, dirty prompt, invalid profile, and `main` execution each returned 1 with the intended reason. The fixture was removed afterward.

Representative dry-run command:

```sh
scripts/delegate-claude.sh \
  --dry-run \
  --profile implementation-commit \
  --model sonnet \
  --effort low \
  docs/prompts/auditable-claude-delegation.initial.md
```

### Residual risks

- `implementation-commit` deliberately grants generic Bash. It is suitable only for trusted scoped work in an isolated worktree and is not path, process, credential, or network isolation.
- Claude Code's project-only settings posture could not be exercised in a live delegated run with this OAuth environment. A future live launcher use must verify authentication succeeds without weakening settings isolation; failure should remain visible.
- Prompt and launcher preservation make inputs reconstructable, not model behavior reproducible.
- Claude Code may change flag behavior in later versions; the resolved version and dry-run posture remain review inputs.

### Decisions returned

No product-runtime or lifecycle decision was required. True OS/container isolation remains a separate design decision if untrusted implementation work is introduced.

## Amp review and acceptance

Amp reviewed the complete range `38b059d23e954d7af7d82151dc789bf4b0f030cb..800f533768b0cfac01730adc95008de7c02ff22f`. The first review rejected the initial implementation because Claude Code 2.1.218 requires `--verbose` with print-mode stream JSON, prompt bytes came from the mutable worktree, real-run evidence and postflight were incomplete, the template had contradictory commit authority, profile defaults were under-documented, and subdirectory invocation failed. Corrections in `51fe1c8` moved prompt input to the starting-HEAD Git blob, added the required flag and complete invocation report, made postflight preserve input and Claude statuses, aligned the template and profile contract, and normalized canonical launcher execution. A follow-up review found that Git inspection failures could still appear clean; `800f533` made cleanliness, changed-path, ancestry, and commit-count failures explicitly unresolved or partial without masking Claude's status.

Final acceptance evidence:

- `bash -n scripts/delegate-claude.sh` — passed.
- `scripts/delegate-claude.sh --help` — passed.
- Clean task-worktree dry runs from the repository root and `docs/` — passed; the final envelope reported prompt blob `c97b5ebeda91bb902daf6072f7f3a8a176ebc50f`, launcher/start tip `800f533768b0cfac01730adc95008de7c02ff22f`, exact branch/worktree, Claude Code 2.1.218, profile, strict-empty MCP, project-only settings, no persistence, and `--verbose --output-format stream-json` without invoking Claude.
- Disposable fake-Claude live path — passed. It exercised the real non-dry-run pipeline, asserted required CLI arguments, proved the bytes between prompt boundaries equal the committed Git blob byte-for-byte, preserved zero input/Claude/launcher statuses, and reported current branch, clean worktree, and complete changed-path inspection.
- Disposable invalid cases — template execution, untracked prompt with a committed matching plan, dirty prompt, invalid profile, and `main` execution each returned 1 with the intended rejection. Fixtures were removed.
- `git diff --check 38b059d...800f533` — passed.
- Final worktree — clean.
- `main` remained at the planned base `38b059d`; no rebase was required.

The accepted implementation retains all task commit boundaries. Residual risks remain as recorded above: no authenticated live Claude run succeeded in this OAuth environment, generic Bash is a trust grant rather than a sandbox, and future Claude CLI changes require renewed verification.
