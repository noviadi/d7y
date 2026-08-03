# D7Y Runtime Orientation

D7Y is an agent-native discovery workbench. It turns incomplete intent into
traceable evidence, concrete learning, and — when useful — functional
prototypes, while keeping intent human-owned, evidence traceable, and
uncertainty visible. It is built as a thin harness over substantial Markdown
skills and a deterministic foundation: judgment lives in inspectable skills,
repeatable work in deterministic tools, and orchestration stays narrow.

This is the runtime orientation for a workspace where D7Y has been installed.
It tells you what the key artifact is, where things live, and which skill to
reach for. It is intentionally lean.

## The initiative is the key artifact

An **initiative** is a durable investigation of a problem, opportunity, or idea
across sessions. It holds provisional intent, framing, evidence, alternatives,
experiments, decisions, and residual uncertainty — enough for future sessions
to continue without reconstructing its history.

Canonical initiative state lives at `initiatives/<stable-slug>/initiative.md`.
Read `initiatives/README.md` for the organization contract: statuses, layout,
identity criteria, and the minimum artifact. Several initiatives may be active;
there is no global current pointer, so identify the current one from explicit
reference, working path, and context.

### Workspace layout

- `initiatives/` — durable initiative state and its organization contract.
- `.d7y/` — the runtime: the `d7y` executable, deterministic scripts, and the
  installed skills.
- skills — surfaced through your host binding so the agent can discover and
  invoke them in-session.

### Deterministic initiative commands

Use the `d7y` command for deterministic initiative inventory and validation:

```sh
d7y initiatives list                # list initiatives in this workspace
d7y initiatives check               # validate initiative organization
d7y initiatives list --json         # machine-readable inventory
```

`d7y` owns command dispatch, target-workspace resolution, deterministic
execution, and the output contract only. It does not select an initiative
semantically or advance the discovery loop — that is the agent's job, guided by
skills.

## Reach for the right skill

D7Y's capability lives in its skills: reusable Markdown procedures that teach
the agent how to perform a kind of discovery work. The skills available in this
runtime are:

- **starting-initiatives** — start or resume a discovery initiative; check the
  session and existing initiatives for the same or related intent before
  creating anything.
- **writing-great-skills** — author or repair a D7Y skill with a narrow trigger,
  one coherent process, checkable completion, and a colocated eval suite.

Invoke the skill that matches the discovery move you are making. Skills carry
their own context, conditions, and completion criteria; read the relevant skill
before acting on it, and let the primary uncertainty choose the next move.
