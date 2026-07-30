---
title: Delegation Prompt Artifacts
type: docs
status: accepted
createdAt: 2026-07-27
updatedAt: 2026-07-27
---

# Delegation Prompt Artifacts

This directory holds the preserved, reviewable prompts used when D7Y development work is delegated from Amp to an implementation executor such as Claude Code. It is governed by `AGENTS.md`, `CLAUDE.md`, and the plan `docs/plans/auditable-claude-delegation.md`.

## Why preserved prompts exist

A delegated handoff is auditable only when another operator can reconstruct exactly what was sent: the prompt text, the repository state, the permission posture, and the launcher revision. Preserving each concrete delegation prompt under `docs/prompts/` makes that reconstruction possible without trusting chat logs, screenshots, or memory.

Preservation is **evidence**, not proof. It does not make model output deterministic, does not sandbox the filesystem, and does not prove the executor behaved exactly as the prompt requested. It only guarantees the inputs are reproducible and reviewable.

## Naming

Two kinds of file live here, with distinct suffixes:

- **Concrete prompts** — `docs/prompts/<plan-slug>.<execution-slug>.md`
  - One per delegation instance, bound to a specific plan and execution.
  - `<plan-slug>` matches the plan filename in `docs/plans/`.
  - `<execution-slug>` distinguishes iterations of the same plan (for example `initial`, `rerun`, `fix-eval`).
  - Example: `docs/prompts/auditable-claude-delegation.initial.md`.
- **Reusable templates** — `docs/prompts/<prompt-template-slug>.template.md`
  - Copied and completed by Amp to start a new concrete prompt.
  - Example: `docs/prompts/delegate-implementation.template.md`.

Slugs are lowercase kebab-case. Filenames are stable identifiers; do not rename a prompt after execution.

## Immutability

A concrete prompt is immutable once execution begins.

- Amp commits the concrete prompt **before** creating the task worktree and invoking the executor, so the executor always starts from the reviewed, committed text.
- A concrete prompt must have frontmatter `status: committed` before delegation. Draft or ready prompts are review artifacts, not executable handoffs; the launcher rejects them. `status: superseded` marks an unexecuted prompt replaced by a newer handoff and is also non-executable.
- Do not edit an executed prompt to mark it superseded. Executed prompts remain immutable `committed` evidence; record their historical relationship in the governing plan or a later prompt.
- The executor must not modify the concrete prompt after execution begins. Implementation feedback goes into the governing plan, not back into the prompt.
- The launcher (`scripts/delegate-claude.sh`) rejects an untracked, uncommitted, or dirty prompt, and resolves the exact prompt commit to report.
- A concrete prompt never embeds its own Git commit SHA, because a tracked file cannot contain the ID of the commit that contains it. The launcher resolves the execution base from task `HEAD` and records it in the runtime envelope instead.

If a prompt needs to change, create a new concrete prompt with a new `<execution-slug>` rather than editing the executed one. Keep the prior instance so the history of what was sent remains reconstructable.

## Required content of a concrete prompt

A concrete prompt is a complete, self-contained handoff. It must record:

- the governing plan path;
- the execution slug and executor (for example `claude-code`);
- the assigned branch and worktree;
- the permission profile and any extra tool grants, network/MCP/credential posture, commit authority, and lifecycle authority;
- the writable paths (explicit allow-list);
- the required context to read before editing;
- the required verification;
- the completion contract, including appending implementation feedback to the governing plan and returning a clean worktree.

The launcher prepends a **runtime envelope** (repository root, prompt path, prompt commit, launcher commit, task base/starting `HEAD`, branch, worktree, Claude Code version, profile, model/effort, allowed matchers, and the network/MCP/persistence/settings posture) to the committed prompt text. The envelope is resolved at invocation time; the committed prompt carries only the durable handoff.

## Permission profiles

The launcher exposes two reviewed defaults:

- `docs-commit`: built-ins `Read,Edit,Write,Bash`, with `Read`, `Edit`, and `Write` plus narrowly matched Git status, diff, log, show, add, and commit commands.
- `implementation-commit`: built-ins `Read,Edit,Write,Bash,Glob,Grep`, with all six allowed. Generic `Bash` is a deliberate trust choice for build and test execution, not least privilege or an OS sandbox.

Repeatable `--allow-tool <matcher>` arguments add Claude Code permission matchers. They never execute prompt text and cannot expose a built-in omitted by the profile's `--tools` set. Preserve every required extra matcher in the concrete prompt so review can reconstruct the intended posture.

## User environment import

The launcher keeps Claude settings project-only so global `permissions`, `model`, `effortLevel`, and other behavior are not inherited. Before invocation it validates the top-level `env` object in `~/.claude/settings.json`, then a Python `execve` wrapper imports only those key/value pairs into the Claude subprocess. Bash never materializes the values, and they are never evaluated as shell, printed, persisted, or placed in process arguments. Inspection and execution each read and validate one file descriptor; execution also verifies the exact content hash observed during inspection. The runtime envelope reports the resolved source and imported key names with values redacted. Dry runs validate this source but do not start or version-probe Claude.

The settings file must be owned by the current user and must not be group/world writable. Mode `600` is recommended for defense in depth when the file contains credentials; a less restrictive read mode is allowed because parent-directory permissions may already prevent access. Imported values are available to Claude and its tool subprocesses, so this is settings isolation—not secret isolation or a substitute for sandboxing.

## Effective-instruction limitations

A prompt constrains an executor; it does not control it the way code controls a function.

- Model output is not deterministic. The same prompt and state can produce different results.
- A permission profile and prompt are not an OS or container sandbox. They narrow the tool surface and permission grants; they do not isolate filesystem paths, processes, ports, caches, credentials, or network egress. The launcher's reported network posture is not technical enforcement.
- Claude Code's effective tool set is whatever the host actually exposes. If a required flag is unsupported, the launcher stops and reports the mismatch rather than silently widening permissions.
- Treat the preserved prompt plus the postflight report (changed paths, commits created, worktree cleanliness) as the evidence trail. Promote claims only to the strength the evidence supports.

## Feedback linkage

Implementation feedback is appended to the **governing plan** (`docs/plans/<plan-slug>.md`), not to the prompt. The plan records files changed, checks and results, a dry-run example, valid/invalid launcher cases, deviations, residual risks, and decisions returned. This keeps the prompt immutable while still capturing what was learned. Accepted learning is later reconciled into canon by Amp; the plan is a handoff and feedback surface, not canonical truth.

## Bootstrap note

The first concrete prompt, `auditable-claude-delegation.initial.md`, bootstraps this very system: it establishes this directory, the template, and `scripts/delegate-claude.sh`. Per the governing plan, that initial delegation may invoke Claude Code directly because the launcher does not yet exist. From the next isolated handoff onward, the launcher is the default entry point.
