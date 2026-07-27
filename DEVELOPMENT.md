# Developing D7Y

This guide covers the repository surfaces and local commands used to develop D7Y. For product intent and architecture, start with the [workbench charter](./docs/discovery-workbench.md) and [agent-native principles](./docs/discovery-workbench-principles.md).

## Repository layout

- [`docs/`](./docs/) contains the charter, principles, plans, prompts, and evaluation contract.
- [`skills/`](./skills/) contains reusable discovery procedures and their eval suites.
- [`evals/`](./evals/) contains shared schemas and deterministic eval tooling.
- [`initiatives/`](./initiatives/) defines the durable unit and organization of discovery work.
- [`scripts/`](./scripts/) contains deterministic repository-development launchers.

Agent contributors must follow the role-specific repository guidance in [`AGENTS.md`](./AGENTS.md) and [`CLAUDE.md`](./CLAUDE.md).

## Repository CLI

`./d7y` is the canonical local command façade for repository development. It is a thin, dependency-free Bash dispatcher over the existing validators and Claude delegation launcher; it owns command discovery and deterministic dispatch only.

```sh
./d7y --help
./d7y validate                    # validate skill evals, then initiatives
./d7y dev plans                   # list plans that are not done
./d7y dev plans --all             # include completed plans
./d7y dev plans --done            # list only completed plans
./d7y dev delegate <prompt-path>  # delegate a Claude Code implementation handoff
```

The underlying scripts remain directly executable:

- `python3 evals/validate_skill_evals.py`
- `python3 skills/starting-initiatives/scripts/check_initiatives.py --root .`
- `scripts/delegate-claude.sh <prompt-path>`

Use `./d7y --help` to discover command groups and leaf help for detailed options. This CLI is repository tooling, not a workflow engine, durable control plane, or first-class D7Y product-runtime binding.

## Runtime development direction

D7Y's required behavior is **host-neutral**: skill behavior, initiative and artifact semantics, evidence standards, checkpoints, deterministic capability contracts, and canonical evaluation semantics belong to the core regardless of the agent host. A host **binding** provides the concrete realization—skill loading, instruction discovery, invocation and routing, model/tool/permission mapping, deterministic command access, trace and provenance capture, supported versions, and documented limitations.

Host-neutral means equivalent required behavior, not identical commands, paths, configuration, or event formats. **Claude Code is the first planned binding and the first binding to be evaluated.** No binding evaluation has occurred yet. A binding earns first-class status only when representative evidence covers installation, invocation, required tools and permissions, produced artifacts and provenance, and known limitations.
