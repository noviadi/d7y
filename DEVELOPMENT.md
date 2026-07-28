# Developing D7Y

This guide covers the repository surfaces and local commands used to develop D7Y. For product intent and architecture, start with the [workbench charter](./docs/discovery-workbench.md) and [agent-native principles](./docs/discovery-workbench-principles.md).

## Repository layout

- [`docs/`](./docs/) contains the charter, principles, plans, prompts, and evaluation contract.
- [`skills/`](./skills/) contains reusable discovery procedures and their eval suites.
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
```

`initiatives list` and `initiatives check` resolve the target workspace from an explicit `--root <path>` or, when omitted, from the nearest ancestor of the current directory containing `initiatives/README.md`. Run `./d7y initiatives list --help` or `./d7y initiatives check --help` for leaf options and exit statuses.

The underlying scripts remain directly executable:

- `python3 evals/validate_skill_evals.py`
- `python3 evals/run_eval.py --source-repo <repo> --suite <suite> --case <id> --output <dir> [--commit <ref>] [--claude <path>] [--dry-run]` (minimal skill eval runner; reads every input from immutable Git objects, binds the target workspace through the supported Claude command surface, and writes a complete redacted artifact tree)
- `python3 scripts/check-initiatives.py --root .` (shared initiative inventory and validation)
- `scripts/delegate-claude.sh <prompt-path>`

Use `./d7y --help` to discover command groups and leaf help for detailed options. The CLI is a thin deterministic command interface, not a workflow engine, durable control plane, or first-class D7Y product-runtime binding.

## Runtime development direction

D7Y's required behavior is **host-neutral**: skill behavior, initiative and artifact semantics, evidence standards, checkpoints, deterministic capability contracts, and canonical evaluation semantics belong to the core regardless of the agent host. A host **binding** provides the concrete realization—skill loading, instruction discovery, invocation and routing, model/tool/permission mapping, deterministic command access, trace and provenance capture, supported versions, and documented limitations.

Host-neutral means equivalent required behavior, not identical commands, paths, configuration, or event formats. **Claude Code is the first planned binding and the first binding being evaluated.** A bounded Claude Code 2.1.218 synthetic-plugin spike established target availability and target-specific invocation evidence under a controlled eval posture; the first real D7Y skill run and several isolation canaries remain implementation gates. A binding earns first-class status only when representative evidence covers installation, invocation, deterministic command access, required tools and permissions, produced artifacts and provenance, and known limitations.
