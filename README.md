# d7y

**D7Y**—a numeronym for *discovery*—is an agent-native workbench for turning incomplete intent into traceable evidence, concrete learning, and, when useful, functional prototypes.

## Vision

D7Y explores how agentic capabilities can improve discovery by an order of magnitude: augmenting human judgment, delegating bounded work, parallelizing independent investigations, retrieving missing context, and making higher-fidelity experiments affordable earlier.

The goal is not to generate the most ideas, documents, or code. It is to reduce the most consequential uncertainty faster while keeping intent human-owned, evidence traceable, and residual uncertainty visible.

D7Y is designed around a thin harness, substantial Markdown skills, and deterministic tools for repeatable execution and verification.

## Repository

- [`docs/`](./docs/) contains the charter, principles, and evaluation contract.
- [`skills/`](./skills/) contains reusable discovery procedures and their eval suites.
- [`evals/`](./evals/) contains shared schemas and deterministic eval tooling.
- [`initiatives/`](./initiatives/) defines the durable unit and organization of discovery work.

Start with the [workbench charter](./docs/discovery-workbench.md) and [agent-native principles](./docs/discovery-workbench-principles.md).

## Repository CLI

`./d7y` is the canonical local command façade for repository development: a thin, dependency-free Bash dispatcher over the existing validators and the Claude delegation launcher. It owns command discovery and deterministic dispatch only.

```sh
./d7y validate                    # validate skill evals, then initiatives
./d7y dev delegate <prompt-path>  # delegate a Claude Code implementation handoff
```

The underlying scripts (`evals/validate_skill_evals.py`, `skills/starting-initiatives/scripts/check_initiatives.py`, and `scripts/delegate-claude.sh`) remain directly executable; `./d7y --help` lists the supported command groups. This is repository tooling, not a workflow engine, durable control plane, or first-class D7Y product-runtime binding.

## Runtime direction

D7Y's required behavior is **host-neutral**: skill behavior, initiative and artifact semantics, evidence standards, checkpoints, and deterministic capability contracts are owned by canon, independent of the agent host that runs them. A host **binding** provides the concrete realization—skill loading, instruction discovery, invocation routing, model/tool/permission mapping, command access, and trace capture.

Host-neutral means equivalent required behavior, not identical commands, paths, or configuration. **Claude Code is the first planned binding and the first binding to be evaluated.** No binding evaluation has occurred yet; it is not a fully supported end-user runtime, and a binding earns first-class status only when representative evidence covers installation, invocation, required tools and permissions, produced artifacts and provenance, and known limitations.

## Status

> **Work in progress:** D7Y is in its foundational development stage. Its skills remain provisional until comparative agent evals demonstrate value over a baseline, and its structure and interfaces may change as the workbench is exercised and refined.
