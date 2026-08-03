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

## Implementation feedback — B0/B1 (execution: b0-b1-characterize-and-relocate)

Executor: claude-code (Claude Code 2.1.218). Branch: `work/runtime-binding-b0-b1`.
Prompt: `docs/prompts/runtime-binding-claude-code.b0-b1-characterize-and-relocate.md`
@ dca9d1a. Base/starting HEAD: dca9d1a.

### B0 — Claude Code skill-loading contract (exit gate met)

Determined by inspecting the local Claude Code 2.1.218 installation (native ELF
binary at `~/.local/share/claude/versions/2.1.218`; GIT_SHA `bce61b43`, BUILD
`2026-07-22`) and reasoning from its embedded logic. No network used.

- **Discovery path.** Project skills are discovered at
  `.claude/skills/<name>/SKILL.md` (project scope) and
  `~/.claude/skills/<name>/SKILL.md` (user scope). Discovery walks upward from
  the workspace/cwd, adding every ancestor's `.claude/skills`
  ("dynamicSkillDirs"). Confirmed by binary strings ("Claude Code natively
  discovers skills from nested `.claude/skills/`") and resolution code
  `resolve(root, ".claude", "skills")`.
- **Symlink behavior — VIABLE.** The skills-directory loader iterates dirents
  (`withFileTypes`) and accepts any entry where `isDirectory() ||
  isSymbolicLink()`, then resolves `<skillsDir>/<name>/SKILL.md` via `realpath`
  (depth guard `++s>64`). So a symlinked skill **directory** is loaded, and
  `SKILL.md` is reached through symlinked directories (and through a symlinked
  `SKILL.md` itself). Nested chains (`.claude/skills/<name>` →
  `.d7y/skills/<name>` → repo `agents/skills/<name>`) resolve. Empirically
  corroborated on this host: `~/.claude/skills/omarchy` is itself a symlinked
  directory to an external path and loads. Caveats (not blockers):
  `settings.local.json` is explicitly rejected if symlinked; team-synced
  memory-store skills reject symlinked folders — neither affects project
  `.claude/skills/` discovery.
- **Command-access mechanism.** A skill's deterministic command is reached
  in-session via the host shell (Claude Code's Bash tool), so `d7y` must be on
  the session PATH. D7Y's `starting-initiatives` skill uses the runtime
  `d7y initiatives` CLI contract (not a skill-relative script), so the install
  must expose `d7y` on PATH (B2 concern). Skills may also use
  `${CLAUDE_SKILL_DIR}` (substituted with the skill's resolved directory) to
  reference colocated scripts; D7Y skills do not rely on it.
- **Observable load/trigger signal.** Load: project-scope skills appear in the
  plugin list as "Skills-directory plugins (`.claude/skills/*`)" — observable via
  `/plugins`, refreshed via `/reload-plugins`. Workspace **trust** gates
  project-scope loading: an untrusted workspace logs "…not loaded because this
  workspace was not trusted" and prompts "Accept the trust dialog for this
  workspace, then run /reload-plugins" (B2/B3 operational requirement: the
  installed directory must be trusted). Trigger: skills expose `name` +
  `description` frontmatter injected for model relevance; invocation is
  observable as a `Skill` tool-use event (consistent with the canon's recorded
  2.1.218 spike); a skill may also be user-invoked via `/<name>`.

**Conclusion: symlinks are viable. Proceeded to B1.** Static/binary inspection
only; behavioral confirmation (real session load + trigger) is B3.

### B1 — Relocate + author (exit gate met)

**Moved (`git mv`, history preserved — 7 files, pure renames):**

- `skills/` → `agents/skills/` (`starting-initiatives`, `writing-great-skills`,
  each with `SKILL.md`, `evals/evals.json`, fixtures, and `LICENSE`).
- `AGENTS.md` → `agents/AGENTS.md`; repo-root `AGENTS.md` → symlink to
  `agents/AGENTS.md`.
- `CLAUDE.md` → `agents/CLAUDE.md`; repo-root `CLAUDE.md` → symlink to
  `agents/CLAUDE.md`.

**Created:**

- `agents/runtime-AGENTS.md` — orientation-only runtime constitution: what the
  workbench is; initiatives as the key artifact + workspace layout
  (`initiatives/`, `.d7y/`, skills) + `d7y initiatives list/check`; and a
  skill-heavy guideline scoped to the currently available skills
  (`starting-initiatives`, `writing-great-skills`).

**Path references fixed:**

- `evals/validate_skill_evals.py`: skill discovery glob `Path("skills")` →
  `Path("agents/skills")` (it hardcoded `skills/`).
- `agents/skills/{starting-initiatives,writing-great-skills}/evals/evals.json`:
  `$schema` `../../../…` → `../../../../…` (now four levels to the repo root);
  both resolve to `evals/skill-evals.schema.json`.
- `agents/AGENTS.md` and `agents/CLAUDE.md`: skill pointers
  `skills/<name>/SKILL.md` → `agents/skills/<name>/SKILL.md` (three pointers).
  Mechanical path update only; constitutional intent unchanged.

**Symlink choice — `CLAUDE.md` (decision returned).** Preserved the two-companion
dev design rather than symlinking `CLAUDE.md` → `AGENTS.md`. Rationale: both
constitutions explicitly state they are separate companions ("not an inheritance
chain"; `CLAUDE.md`: "Do not load `AGENTS.md` automatically") with materially
different content (`AGENTS.md` = full dev constitution with Amp's role, mission,
architecture; `CLAUDE.md` = Claude execution companion with worktree/delegation
rules). Unifying would make Claude Code load the full `AGENTS.md` as its
always-loaded `CLAUDE.md`, contradicting the written design — a constitutional
change, not a relocation. So `CLAUDE.md` was relocated to `agents/CLAUDE.md` with
the root as a symlink to it: both dev constitutions under `agents/`, both root
files symlinks, two companions preserved. The runtime pattern (single
orientation `AGENTS.md` + `CLAUDE.md` → symlink) still applies to the runtime
root, which uses the separate `agents/runtime-AGENTS.md`.

### Checks and results

- `python3 evals/validate_skill_evals.py` → VALID for both suites under
  `agents/skills/`, rc 0.
- `./d7y validate` → evals VALID; "Initiatives: valid (0 found)", rc 0.
- Root `AGENTS.md`/`CLAUDE.md` symlinks resolve; `agents/AGENTS.md`,
  `agents/CLAUDE.md`, `agents/runtime-AGENTS.md` exist.
- `agents/runtime-AGENTS.md` is orientation-scoped: no Amp/Claude roles, worktree
  rules, auditable-delegation content, "build D7Y do not perform discovery", or
  eval contract.
- `git ls-files 'skills/*'` → 0 (no duplication); all seven files under
  `agents/skills/`.
- `git diff --check` → clean.
- `scripts/` grep for `skills/` → no matches (no stale source path in scripts).

### Deviations

- None from the writable scope. `git mv skills agents/skills` (whole directory)
  was used instead of per-entry `git mv skills/*` — equivalent result, history
  preserved (verified: seven pure renames).

### Residual risks / decisions returned

- **`DEVELOPMENT.md:8`** (root dev guide) still reads `[`skills/`](./skills/)` — a
  now-broken link. `DEVELOPMENT.md` is not in the prompt's writable-path list, so
  it was left unchanged. Recommend a one-line follow-up: `./skills/` →
  `./agents/skills/`.
- **Canon (prohibited, unchanged).** `docs/discovery-workbench.md:92`
  ("reusable discovery capabilities live under `skills/`") and
  `docs/skill-evaluations.md:34` (`skills/<skill>/`) are now stale as repo-source
  locations. Left unchanged per the no-canon-edit constraint; recommend Amp
  reconcile (they may also be read host-neutrally/conceptually, but the
  repo-source reading is now stale).
- **Harbor eval artifacts** (`evals/harbor/payloads/starting-initiatives.json`,
  `evals/harbor/scripts/posture.py`, `evals/harbor/scripts/test_posture.py`,
  `evals/harbor/README.md`) reference `skills/starting-initiatives/SKILL.md` as
  payload/posture source paths. Out of writable scope (eval logic); will need
  updating when the harbor harness is exercised — belongs to the eval-harness
  work. `./d7y validate` does not run the harbor harness, so it is unaffected.
- **Historical plans and immutable prompts** under `docs/` retain `skills/`
  references as historical evidence of pre-relocation state; intentionally not
  rewritten. The governing plan's own `skills/` references are runtime paths
  (`.d7y/skills/`, `.claude/skills/`) or describe the move itself — correct as-is.
- **Skill/eval content** (e.g., `agents/skills/writing-great-skills/SKILL.md`,
  eval prompt text saying "put it under `skills/`") left unchanged per the
  no-skill-content-change constraint; those `skills/` mentions describe target
  runtime/workspace locations, not the repo source.
- **Workspace trust** (B0 finding): a real runtime session in an installed
  directory requires the workspace to be trusted before project-scope skills
  load; B2/B3 must account for this.
- **Static validation only.** B0/B1 were verified by inspection plus deterministic
  validators. Behavioral binding (real session skill load + trigger + `d7y`
  in-session + a valid artifact) is B2/B3 and has not been run.
