# Developing D7Y

This guide covers the repository surfaces and local commands used to develop D7Y. For product intent and architecture, start with the [workbench charter](./docs/discovery-workbench.md) and [agent-native principles](./docs/discovery-workbench-principles.md).

## Repository layout

- [`docs/`](./docs/) contains the charter, principles, plans, prompts, and evaluation contract.
- [`agents/skills/`](./agents/skills/) contains reusable discovery procedures and their eval suites.
- [`evals/`](./evals/) contains shared schemas and deterministic eval tooling.
- [`initiatives/`](./initiatives/) defines the durable unit and organization of discovery work.
- [`scripts/`](./scripts/) contains deterministic repository-development launchers.

Agent contributors must follow the role-specific repository guidance in [`AGENTS.md`](./AGENTS.md) and [`CLAUDE.md`](./CLAUDE.md).

## Local CLI

`./d7y` is the canonical local command interface for D7Y. It is a thin, dependency-free façade over the deterministic initiative implementation and the Claude delegation launcher; it owns command discovery, target-workspace resolution, and deterministic dispatch only. User-facing capabilities live at the top level; contributor-only operations are isolated under `dev` or kept as compatibility commands.

```sh
./d7y --help
./d7y initiatives list                    # list initiatives in a workspace
./d7y initiatives check                   # validate initiative organization
./d7y validate                            # validate skill evals, then initiatives
./d7y dev plans                           # list plans that are not done
./d7y dev plans --all                     # include completed plans
./d7y dev plans --done                    # list only completed plans
./d7y dev delegate <prompt-path>          # delegate a Claude Code implementation handoff
./d7y dev install <directory>             # materialize a runnable D7Y runtime (dev facility)
```

`initiatives list` and `initiatives check` resolve the target workspace from an explicit `--root <path>` or, when omitted, from the nearest ancestor of the current directory containing `initiatives/README.md`. Run `./d7y initiatives list --help` or `./d7y initiatives check --help` for leaf options and exit statuses.

The underlying scripts remain directly executable:

- `python3 evals/validate_skill_evals.py`
- `python3 scripts/check-initiatives.py --root .` (shared initiative inventory and validation)
- `scripts/delegate-claude.sh <prompt-path>`

Use `./d7y --help` to discover command groups and leaf help for detailed options. The CLI is a thin deterministic command interface, not a workflow engine, durable control plane, or first-class D7Y product-runtime binding.

## Runtime development direction

D7Y's required behavior is **host-neutral**: skill behavior, initiative and artifact semantics, evidence standards, checkpoints, deterministic capability contracts, and canonical evaluation semantics belong to the core regardless of the agent host. A host **binding** provides the concrete realization—skill loading, instruction discovery, invocation and routing, model/tool/permission mapping, deterministic command access, trace and provenance capture, supported versions, and documented limitations.

Host-neutral means equivalent required behavior, not identical commands, paths, configuration, or event formats. **Claude Code is the first planned binding.** A historical host-side Claude Code 2.1.218 synthetic-plugin spike observed target availability and target-specific invocation evidence, but did not establish the Harbor binding or a safe API/model configuration boundary. Harbor-native comparative execution must prove task-scoped settings, explicit auth/endpoint injection, deterministic command access, required tools and permissions, produced artifacts and provenance, isolation, and known limitations. Requested model and API-route identity are required provenance; effective model/provider and target-specific invocation are recorded when trustworthy runtime-owned evidence exists and otherwise remain explicitly `unavailable` or `ungradable`. Missing telemetry limits the supported claim rather than invalidating process and outcome evidence whose required controls held.

## Dev-install runtime binding (Claude Code)

`./d7y dev install <directory>` materializes a **runnable D7Y runtime** in a target directory so the Claude Code binding can be exercised and real runs produced. It is a **contributor dev facility** for validating the binding — not a deliverable production installation, and not a claim that Claude Code is a supported end-user runtime.

```sh
./d7y dev install /tmp/my-d7y-run         # materialize the runtime (idempotent)
cd /tmp/my-d7y-run
export PATH="$PWD/.d7y:$PATH"             # optional: puts bare `d7y` on PATH (else invoke `.d7y/d7y`)
d7y initiatives list                      # verify the binding returns a valid inventory
```

What the install creates in `<directory>`:

- `.d7y/skills/<name>`, `.d7y/d7y`, `.d7y/scripts/check-initiatives.py` — **symlinked** into this repository (absolute targets), so source edits are live in the runtime.
- `.claude/skills/<name>` → `../../.d7y/skills/<name>` — Claude Code project-scope skill discovery.
- `AGENTS.md` — the runtime orientation constitution, **copied** from [`agents/runtime-AGENTS.md`](./agents/runtime-AGENTS.md) (not symlinked).
- `CLAUDE.md` → symlink to `AGENTS.md`.
- `initiatives/README.md` — the initiative contract (created if absent).

**Reachability.** The skills invoke the `d7y` CLI, which the runtime orientation (the copied `AGENTS.md`, auto-loaded by Claude Code) names at `.d7y/d7y`. An agent that reads its workspace orientation invokes `.d7y/d7y` directly on the first try; a session may also prepend `.d7y/` to `PATH` (shown above) to use the bare `d7y` form. The install prints this guidance.

**Workspace trust.** Project-scope skills (`.claude/skills/<name>`) load only from a trusted workspace:

- **Interactive (TUI) session:** accept the workspace trust dialog on first open, then run `/reload-plugins`.
- **Headless (`claude -p`):** the workspace is treated as trusted automatically — no dialog, no `/reload-plugins` (confirmed behaviorally in B3).

**Safety.** The install is idempotent: re-running re-links and refreshes the copied artifacts but **preserves** an existing `initiatives/` tree. It refuses (non-zero exit, nothing destroyed) to clobber an `initiatives/` holding data beyond the placed `README.md`, and refuses to install into the repository's own root.

### Supported version and limitations

- **Supported host version:** Claude Code **2.1.218** (skill-discovery/symlink mechanism characterized in B0; behavioral binding confirmed in B3). No cross-version support matrix is maintained.
- **Symlink requirement:** skills, the executable, and the checker are absolute symlinks into this repository, so the repo must remain at its current filesystem path for installed runtimes to resolve. A future production install would copy instead; that is out of scope.
- **What this does not establish:**
  - it is a **dev runtime only** — not a deliverable/production install (not copy-based, not versioned, not portable to other hosts or paths);
  - not hardened, and not a supported end-user product runtime, control plane, or UI;
  - B3's behavioral proof used a headless `--dangerously-skip-permissions` posture; behavior under a production permission profile is not separately verified.

See [`docs/plans/runtime-binding-claude-code.md`](./docs/plans/runtime-binding-claude-code.md) for the binding contract, stages, and implementation feedback (B0–B4).
