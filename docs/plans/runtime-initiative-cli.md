---
title: Runtime Initiative CLI
type: feat
status: ready
createdAt: 2026-07-27
updatedAt: 2026-07-27
---

# Runtime Initiative CLI

## Outcome

Make `d7y` the local deterministic capability interface for both people and agents, beginning with initiative inventory and validation:

```text
d7y initiatives list [--root <path>] [--status <status>] [--json]
d7y initiatives check [--root <path>] [--json]
```

The `starting-initiatives` skill must consume this stable command contract instead of naming a source-checkout-relative Python path. A transferred skill can then rely on the D7Y runtime binding to provide the capability without assuming that `skills/starting-initiatives/scripts/` exists under the process working directory.

This is a deliberate expansion of the current root CLI boundary. `d7y` remains a thin, local, deterministic façade, but it is no longer described only as repository-development tooling. User-facing capabilities live at top level; contributor-only operations remain visibly isolated under `d7y dev` or under existing compatibility commands.

## Problem

`skills/starting-initiatives/SKILL.md` currently instructs an agent to run:

```sh
python3 skills/starting-initiatives/scripts/check_initiatives.py --root . --json
```

That command conflates:

1. the **capability implementation root**, where the checker is installed; and
2. the **target workspace root**, where `initiatives/README.md` and initiative state live.

It works in the D7Y source checkout when invoked from the repository root. It is not a reliable runtime contract when a skill is installed into a host-specific skill directory, the process starts from another directory, or D7Y tooling is distributed separately from the target workspace.

The checker has also outgrown private ownership by `starting-initiatives`. It validates the repository-wide initiative contract, is called by contributor validation, and now has a direct human use case: listing and checking initiatives without invoking a discovery skill.

## Constitutional decision and consequences

This plan deliberately evolves the boundary described by `docs/discovery-workbench.md`, `DEVELOPMENT.md`, and `docs/plans/root-cli.md`:

- `d7y` becomes D7Y's local deterministic command and capability interface.
- The CLI is a control-plane **interface** for capability discovery, workspace resolution, deterministic execution, structured output, and host permission/provenance integration.
- Canonical initiative state remains ordinary versioned files under `initiatives/`; the CLI owns no hidden or duplicate durable state.
- Skills continue to own interpretation, matching, workflow judgment, human checkpoints, and selection of the next discovery move.
- The CLI does not encode the discovery loop, select an initiative semantically, route agents, or advance initiative lifecycle autonomously.
- Host bindings own installation, command availability, model/tool/permission mapping, and trace capture. Host-neutral core owns command behavior and structured result semantics, not identical installation paths.
- The existing `dev` namespace remains development-only. Existing top-level `validate` behavior remains compatible in this increment; reorganizing or removing it is out of scope.

This preserves the thin-harness, fat-skills, deterministic-foundation architecture: the capability surface becomes stable and end-user friendly without moving domain judgment into the CLI.

## Ownership boundary

```text
Human or agent
    |
    v
d7y initiatives ...
    |  command discovery, target-root resolution, output contract
    v
shared deterministic initiative implementation
    |  complete inventory and mechanical contract validation
    v
initiatives/README.md + initiatives/*/initiative.md

starting-initiatives skill
    owns when to inventory, semantic comparison, relationship classification,
    creation/resume judgment, checkpoints, and discovery handoff
```

The initiative organization contract remains authoritative for layout, fields, lifecycle states, and relationship invariants. The deterministic implementation realizes that contract mechanically. The CLI exposes the implementation. The skill interprets its result.

## Command contract

### Workspace selection

Every initiative command operates on one explicit target workspace:

1. If `--root <path>` is provided, resolve it to an absolute path and use it.
2. Otherwise, search from the caller's original working directory upward for the nearest directory containing `initiatives/README.md`.
3. If no workspace is found, fail with a concise diagnostic recommending `--root`, write no state, and exit `2`.

Do not infer the target workspace from the CLI installation directory. Preserve the caller's original working directory before the root script changes directory to locate its own implementation. An explicit target root is preferred for skills, host bindings, and automation; upward discovery is a human convenience.

### `d7y initiatives list`

Produce a complete deterministic inventory of canonical one-level `initiatives/<slug>/initiative.md` artifacts.

Options:

- `--root <path>` selects the workspace as described above.
- `--status <status>` filters returned records after validating the complete workspace. Accept only statuses defined by `initiatives/README.md`; repeated filters are not required in this increment.
- `--json` emits the versioned machine-readable result and no additional prose.
- `-h` and `--help` print leaf usage and exit `0`.

Human output must be concise and scan-friendly, with one initiative per line and at least slug, status, updated date, and title. It must also report workspace or record errors rather than silently omitting malformed artifacts.

JSON output retains the existing inventory meaning and includes at least:

```json
{
  "version": 1,
  "root": "/absolute/workspace",
  "valid": true,
  "count": 1,
  "errors": [],
  "warnings": [],
  "initiatives": [
    {
      "slug": "customer-interview-analysis",
      "path": "initiatives/customer-interview-analysis/initiative.md",
      "title": "Customer Interview Analysis",
      "status": "active",
      "created": "2026-07-27",
      "updated": "2026-07-27",
      "aliases": [],
      "related": [],
      "valid": true,
      "errors": [],
      "warnings": []
    }
  ]
}
```

Inventory always validates the complete workspace before applying an output filter. `count` is the number of returned records after filtering; malformed canonical records remain visible when they satisfy the filter or when no filter is supplied.

Exit status:

- `0` when the workspace and all inventoried records are valid, including an empty valid inventory;
- `1` when inventory completes but the workspace or any canonical record is invalid;
- `2` for command usage, an invalid filter, or inability to resolve a target workspace.

### `d7y initiatives check`

Validate the complete initiative organization without filtering.

- It accepts `--root`, `--json`, `-h`, and `--help` with the same meanings as `list`.
- Human output may retain the current checker summary and per-record diagnostics.
- JSON output uses the same versioned result shape as unfiltered `list --json` so agents do not need two parsers.
- Exit statuses follow the same `0` valid, `1` invalid, and `2` invocation contract.

`list` and `check` share one implementation of discovery and validation. They may present different human-readable views but must not implement initiative semantics twice.

## Skill contract

Update `starting-initiatives` to request the capability through:

```sh
d7y initiatives list --root <absolute-workspace-root> --json
```

The skill must:

- derive the target root from the repository whose `initiatives/README.md` it loaded, not from the process cwd or skill installation path;
- use the returned inventory as the complete deterministic candidate set;
- preserve and report invalid artifacts when their intent remains recoverable;
- invoke `d7y initiatives check --root <absolute-workspace-root> --json` after creating or changing an initiative;
- treat exit `1` plus valid JSON as a completed inventory containing contract errors, not as absence of inventory;
- stop and report an unavailable or incomplete D7Y runtime capability on exit `2`, missing command, malformed output, or execution denial rather than replacing deterministic validation with model reasoning.

Update the skill compatibility declaration to require a D7Y binding that exposes the initiative CLI capability, plus the runtime required by the selected binding. Do not mention an installation-specific skill resource path in the canonical runtime procedure.

## Implementation scope

### 1. Promote the deterministic implementation

Move `skills/starting-initiatives/scripts/check_initiatives.py` to a shared deterministic location outside a single skill. Prefer the smallest existing-compatible location, such as `scripts/check-initiatives.py`; do not add a Python package, command registry, or plugin mechanism merely for this move.

Preserve one source of validation and inventory semantics. Update contributor references, `d7y`, and skill references atomically. Do not leave a copied compatibility implementation under the skill.

The implementation may gain narrowly scoped formatting and filtering support needed by the command contract. Keep parsing, validation, relationship checks, and structured result construction independent from human presentation so both leaf commands consume the same result.

### 2. Extend the root CLI

Add the top-level `initiatives` command group to `d7y`. Retain the current explicit dispatch style, safe argument forwarding, dependency posture, and location-based implementation discovery.

Capture the caller's original working directory before changing directory to the D7Y installation root. Pass either the explicit root or the caller-relative discovered root to the deterministic implementation. Do not make user commands operate on the CLI source checkout by default.

Update root help so user-facing initiative commands are visually distinct from contributor-only `dev` commands. Do not duplicate all leaf options in root help.

Keep these existing commands compatible:

```text
d7y validate
d7y validate evals ...
d7y validate initiatives ...
d7y dev plans ...
d7y dev delegate ...
```

The existing `validate initiatives` command may forward to the relocated implementation or to `initiatives check`, but must preserve its accepted options, output, and exit status for this increment.

### 3. Update canonical and user documentation

Update at least:

- `docs/discovery-workbench.md` to describe the local CLI capability interface and its boundary from skill judgment and host bindings;
- `DEVELOPMENT.md` to distinguish user-facing top-level commands from `dev` commands and remove the claim that the entire CLI is development-only;
- `README.md` to show concise initiative listing and validation examples without claiming a fully evaluated host binding;
- `AGENTS.md` and `CLAUDE.md` deterministic validation instructions to use the canonical CLI where appropriate;
- `docs/plans/root-cli.md` only with a short supersession note linking this plan; preserve its historical accepted decisions and implementation feedback.

Do not claim that defining or implementing the command establishes first-class end-user runtime support. Installation and binding evidence remain required.

### 4. Update the skill and eval definition

Change `skills/starting-initiatives/SKILL.md` to consume the CLI contract before matching and after mutation. Update `skills/starting-initiatives/evals/evals.json` so its deterministic process assertion observes the canonical CLI capability rather than any internal script path.

Add a portability-focused positive case or binding fixture when the eval harness can express installation outside the target workspace and an unrelated starting cwd. Until that execution environment exists, record the missing behavioral evidence rather than representing static eval validation as a portability pass.

## Verification

### Static and existing validation

Run:

```sh
bash -n d7y
python3 evals/validate_skill_evals.py
./d7y validate
git diff --check
```

If `shellcheck` is installed, run it against `d7y`; otherwise report it unavailable.

### Focused command behavior

Use temporary synthetic workspaces outside the source checkout. Do not create a real discovery initiative. Verify:

1. `d7y initiatives list --root <valid-empty-workspace>` returns an empty valid inventory and exit `0`.
2. `d7y initiatives list --root <valid-workspace>` returns all records in stable order and exit `0`.
3. `d7y initiatives list --root <valid-workspace> --status active --json` returns only active records with valid JSON.
4. `d7y initiatives check --root <valid-workspace> --json` returns the complete unfiltered inventory.
5. A malformed initiative remains in JSON with errors and causes exit `1`.
6. A missing reciprocal relationship causes exit `1` and identifies both the source record and missing invariant clearly enough to repair.
7. Unknown status, missing option value, unknown option, and unresolved root each exit `2` without modifying files.
8. From a nested directory in a synthetic workspace, root discovery finds the nearest ancestor containing `initiatives/README.md`.
9. From an unrelated cwd with `--root <absolute-workspace>`, the command operates on the target workspace rather than the D7Y installation checkout.
10. Existing `d7y validate initiatives --json` remains compatible.
11. Root and leaf help are concise, accurate, and separate user-facing and development command groups.

Clean every synthetic workspace after verification.

### Skill-level evidence

Run the existing skill eval-definition validator and, when the execution harness is available, an isolated `starting-initiatives` comparison in which:

- the skill installation directory differs from the target workspace;
- execution begins from a third directory;
- the CLI receives an explicit absolute root;
- the trace shows list before matching and check after creation;
- command revision or binding version, target root, arguments, exit status, and result are observable;
- no network access is required.

Report this separately from static validation. The skill remains provisional until comparative behavior evidence supports promotion.

## Acceptance criteria

1. A human can list initiatives with one discoverable `d7y initiatives list` command.
2. A human can validate initiative organization with `d7y initiatives check`.
3. Human output is readable and JSON output is stable, complete, and versioned.
4. Skills and automation can select an explicit target root without depending on cwd or internal source paths.
5. The same deterministic implementation serves list, check, contributor validation, and the starting skill.
6. Malformed artifacts remain visible and produce a distinct invalid-state exit status.
7. CLI installation location and target workspace location are independent.
8. Existing development commands remain compatible.
9. Canon clearly assigns judgment to skills, deterministic operations to the CLI/tooling foundation, and installation/permissions/provenance to host bindings.
10. No workflow engine, hidden state, capability registry, package manager, daemon, or plugin framework is introduced.

## Anti-goals

- Automatically selecting which initiative is current based on keywords, recency, or status.
- Encoding `same`, `related`, `superseding`, `new`, or `unclear` judgment in deterministic code.
- Creating, linking, archiving, graduating, or otherwise mutating initiatives through the CLI in this increment.
- Running the full discovery loop or routing the next skill from the CLI.
- Adding a durable service, daemon, database, global registry, or background process.
- Defining a generic provider/plugin abstraction before a second implementation requires one.
- Installing `d7y` globally, modifying `PATH`, or declaring a first-class host binding complete.
- Adding a package manifest solely to expose command aliases.
- Duplicating initiative validation logic across the skill, CLI, and checker.
- Treating valid JSON or static eval definitions as evidence that transferred runtime execution works.

## Deferred decisions

Defer until observed use provides evidence:

- `d7y initiatives show <slug>` and richer query/search commands;
- mechanical mutation commands such as `create`, `link`, or `set-status`;
- a workspace manifest beyond `initiatives/README.md` as the root marker;
- global installation and distribution packaging;
- a host-native tool API equivalent to the CLI;
- a formal capability registry, version negotiation, or plugin discovery;
- moving from a shared script to a Python package;
- reorganizing the existing top-level `validate` compatibility group;
- cross-host provenance schemas beyond evidence available from the first binding.

Add a deferred capability only when it has a concrete consumer, permission need, or observed usability failure.

## Stop conditions

- Stop if implementation requires choosing a global installation or package-distribution strategy; return that as a separate host-binding plan.
- Stop if initiative listing cannot preserve malformed canonical artifacts and structured errors without breaking the existing checker contract.
- Stop if a proposed CLI behavior requires semantic matching or an irreversible initiative decision; keep that behavior in the skill.
- Stop if preserving `validate initiatives` compatibility would require a second validation implementation; route both surfaces to the shared implementation instead.
- Stop and seek review before adding hidden state, a daemon, automatic lifecycle mutation, or a generic control-plane framework.

## Required implementation feedback

Before review, append an `## Implementation Feedback` section containing:

- files changed and any moved paths;
- exact command checks, outputs at a useful summary level, and exit statuses;
- synthetic workspace cases exercised;
- compatibility results for existing commands;
- deviations from this contract and why;
- runtime and platform assumptions;
- what was statically validated versus behaviorally exercised;
- residual risk, especially installation and host-binding evidence not yet established.
