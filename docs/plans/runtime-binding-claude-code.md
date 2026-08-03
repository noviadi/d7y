---
title: Real Runtime Binding (Claude Code) — Dev Install
type: feat
status: todo
createdAt: 2026-08-03
updatedAt: 2026-08-03
blocks: docs/plans/iterative-skill-eval-harness.md
---

# Real Runtime Binding (Claude Code) — Dev Install

## Summary

D7Y's skills and deterministic CLI exist as repository artifacts, but no host
binding realizes them. This plan establishes the first real binding — Claude
Code — as a **dev runtime environment setup**, not a deliverable production
installation. It adds `d7y dev install <directory>`, which materializes a
runnable D7Y runtime in a target directory so the binding can be exercised and
real runs produced.

It **blocks** `docs/plans/iterative-skill-eval-harness.md`. Stage 0 (real-use
failure capture) and Stage 1a's "one real captured run" exit gate both require
D7Y to run for real. Do not start the eval plan until this plan's completion
boundary is met.

This is explicitly **not** a supported end-user product install. It is a
contributor facility for setting up a runtime environment in which to validate
the binding and generate the first real runs.

## Primary uncertainty

> Can a real Claude Code session, opened in a `d7y dev install`-prepared
> directory, load D7Y's skills, trigger the right one on a real prompt, reach
> `d7y initiatives` in-session, and produce a valid artifact — with the
> load/trigger observable?

## Binding/install model

Two folders, two roles:

- **Dev source — `agents/`** (in this repo): the canonical home for the skills
  and the constitution source. Root `AGENTS.md` and `CLAUDE.md` become symlinks
  into `agents/` so a dev session still discovers them at the repo root.
- **Runtime instance — `.d7y/`** (in an installed target directory): the
  materialized runtime artifacts — skills, the `d7y` executable,
  `scripts/check-initiatives.py`, and configs.

`d7y dev install <directory>` prepares a target directory as follows:

```text
<directory>/
├── .d7y/
│   ├── skills/<name>/          # symlinked from this repo's agents/skills/<name>
│   ├── d7y                     # the executable (reachable in-session)
│   └── scripts/check-initiatives.py
├── .claude/
│   └── skills/<name> -> ../../.d7y/skills/<name>   # Claude Code discovery (symlink)
├── AGENTS.md                   # runtime constitution (orientation), copied from agents/runtime-AGENTS.md
├── CLAUDE.md -> AGENTS.md      # symlink
└── initiatives/
    └── README.md               # the initiative contract the skill requires
```

### Decisions locked

- **Skills are symlinked**, not copied. `.claude/skills/<name>` →
  `.d7y/skills/<name>`; and in this dev install, `.d7y/skills/<name>` → the
  repo's `agents/skills/<name>`, so source edits are live in the runtime. (A
  future production install would copy; that is out of scope here.)
- **The runtime `AGENTS.md` is a separate, authored orientation constitution**
  (`agents/runtime-AGENTS.md`), copied to the runtime root by install — not the
  dev constitution and not a generated projection. See _Runtime constitution_.
- **Install is a dev facility** under the existing `d7y dev` group: `d7y dev
  install <directory>`. Idempotent; re-running re-links and refreshes artifacts
  but preserves the target's `initiatives/` data.

## Runtime constitution

The runtime `AGENTS.md` is a **separate, authored constitution** — not the dev
constitution, and not a generated projection. The dev constitution is kept as-is
(relocated under `agents/`); a new runtime constitution is authored under
`agents/` and **copied** to the runtime root as `AGENTS.md` by
`d7y dev install`.

It is a lean orientation document for someone *using* D7Y. It contains only:

1. **What the workbench is** — high-level context: D7Y turns incomplete intent
   into traceable evidence, learning, and prototypes; thin harness, fat skills,
   deterministic foundation. A paragraph or two.
2. **Initiatives as the key artifact, and the folder structure** — what an
   initiative is; that canonical state lives at
   `initiatives/<slug>/initiative.md`; the workspace layout (`initiatives/`,
   `.d7y/`, skills); and how to use `d7y initiatives list/check`.
3. **A skill-heavy workbench, scoped to current skills** — D7Y's capability
   lives in its skills; the guideline is to invoke the right skill for the
   discovery move; list/point to the skills currently available (today:
   `starting-initiatives`, `writing-great-skills`).

Excluded (they live elsewhere): the dev operating model; the full discovery
principles (those stay in `docs/discovery-workbench-principles.md` and inside
the skills); Amp/Claude roles; worktree handoffs; the eval contract.

Source artifact: `agents/runtime-AGENTS.md`. The dev constitution lives at
`agents/AGENTS.md` (the repo root `AGENTS.md` symlinks to it).

## Stages

### Stage B0 — Characterize the host skill-loading contract (discovery)

- **Entry gate:** none.
- **Work:** confirm how the target Claude Code version discovers project skills
  (`.claude/skills/<name>/SKILL.md`), whether it follows symlinks, how a skill's
  deterministic command is reached in-session, and what load/trigger signal is
  observable. Use the `claude-code-guide` reference and Claude Code docs; record
  the exact version and mechanism.
- **Exit gate:** a written "Claude Code binding contract" note naming the
  discovery path, symlink behavior, command-access mechanism, and observable
  load/trigger signal — or an explicit statement that a needed signal is
  unavailable.

### Stage B1 — Relocate canonical source under `agents/` and author the runtime constitution

- **Entry gate:** B0's contract note exists (confirms symlinks are viable, or
  selects the fallback).
- **Work:** move `skills/` → `agents/skills/`; relocate the dev constitution to
  `agents/AGENTS.md` with the repo root `AGENTS.md` (and `CLAUDE.md`) as
  symlinks into it, so dev discovery is unchanged. **Author the runtime
  constitution** at `agents/runtime-AGENTS.md` per the _Runtime constitution_
  spec (what the workbench is; initiatives + folder structure; skill-heavy
  guideline scoped to currently available skills). Update the few paths that
  reference `skills/` (`validate_skill_evals.py`, docs, the `$schema` relative
  refs in each `evals.json`).
- **Exit gate:** `python3 evals/validate_skill_evals.py` and `./d7y validate`
  pass with skills under `agents/skills/`; root symlinks resolve;
  `agents/runtime-AGENTS.md` exists and is scoped to orientation only (no dev
  operating model).

### Stage B2 — Build `d7y dev install <directory>`

- **Entry gate:** B1 complete.
- **Work:** add `d7y dev install <directory>` to the `d7y` façade (the existing
  contributor-only `dev` group). It materializes the target per the install
  model: `.d7y/` (skills symlinked from `agents/skills/`, `d7y`, checker),
  `.claude/skills/*` → `.d7y/skills/*`, the runtime `AGENTS.md` **copied** from
  `agents/runtime-AGENTS.md`, `CLAUDE.md` → symlink, and `initiatives/README.md`.
  Idempotent;
  refuse to clobber an existing target's `initiatives/` data.
- **Exit gate:** `d7y dev install <dir>` produces the layout above; re-running is
  safe; a fresh Claude Code session in `<dir>` sees the skills available and can
  run `d7y initiatives list/check`.

### Stage B3 — End-to-end real-run smoke

- **Entry gate:** B2 complete.
- **Work:** `d7y dev install` a temp directory; open a real Claude Code session
  there; run one positive `starting-initiatives` invocation and one negative
  control on synthetic fixtures (workbench-development mode). Confirm the skill
  loads; triggers on the positive and not the negative; reaches
  `d7y initiatives list/check`; and produces a valid initiative passing
  `check-initiatives.inventory()`.
- **Exit gate:** one real captured run exists (the artifact Stage 1a of the eval
  plan will grade), with load/trigger observed or explicitly marked
  unobservable.

### Stage B4 — Document the dev-install path and limitations

- **Entry gate:** B3 complete.
- **Work:** record the `d7y dev install` procedure, the supported Claude Code
  version, symlink requirements, and what this binding does and does not
  establish (dev runtime only; not a production install; not hardened; not
  portable to other hosts).
- **Exit gate:** another contributor can `d7y dev install` and run D7Y from the
  repository, knowing the scope limits.

## Scope

### In scope

- Characterize Claude Code skill loading; relocate canonical source under
  `agents/`; build `d7y dev install`; one real end-to-end run; documented
  dev-install path and limitations; the minimal runtime constitution artifact.

### Deferred

- A deliverable/production install (copy-based, versioned, portable).
- Other hosts; Harbor/containerization; hardening and adversarial controls; a
  product runtime, control plane, or UI; cross-version support matrices; and the
  iterative skill eval harness (gated on this plan).

## Verification

1. The target Claude Code version and skill-discovery/symlink mechanism are
   recorded.
2. Skills under `agents/skills/`; root `AGENTS.md`/`CLAUDE.md` symlinks resolve;
   `validate_skill_evals.py` and `./d7y validate` pass.
3. `d7y dev install <dir>` produces the specified layout and is idempotent.
4. A real session in an installed directory lists/loads the skills and reaches
   `d7y initiatives list/check`.
5. One positive real run produces an initiative passing
   `check-initiatives.inventory()`; the negative control does not trigger.
6. Load/trigger is observed or explicitly marked unobservable.
7. The dev-install procedure and limitations are documented.

## Completion boundary

Complete when D7Y runs as a real Claude Code binding via `d7y dev install`:
skills load and trigger correctly in a real session in an installed directory,
`d7y` is reachable in-session, one real captured run exists and passes the
deterministic checker, and the dev-install path and limitations are documented.
This **unblocks** — but does not perform — the iterative skill eval harness.
