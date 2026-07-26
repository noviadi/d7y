# D7Y Discovery Workbench

## Purpose

D7Y is an **agent-native environment for turning incomplete intent into evidence**.

It helps a human and agents move from a fuzzy opportunity through framing, brainstorming, research, experimentation, and—when useful—prototyping. Its purpose is not to maximize documents, ideas, or code, but to reduce the most consequential uncertainty and support better decisions.

Most initiatives should move toward a prototype because agentic implementation makes building an increasingly practical way to learn. However, a prototype is not always the right next step. An initiative may instead produce a clarified opportunity, reusable knowledge, a decision not to proceed, or a better question for future investigation.

## North Star

> Use agentic leverage to turn incomplete ideas into traceable evidence, concrete learning, and functional prototypes with radically less time and effort—without making uncertainty invisible or substituting generated confidence for judgment.

The intended loop is:

```text
Frame → Diverge → Select → Contract → Prototype → Verify
  ↑                                                    ↓
  └──────── Capture ← Commit, Stop, or Reframe ────────┘
```

This is not a mandatory document pipeline. The main uncertainty determines the next move, and the process uses the lightest workflow appropriate to the cost of being wrong.

## Agentic Premise

Traditional discovery is constrained by human attention, coordination, research effort, specialist availability, and the cost of producing testable artifacts. These constraints often produce sequential work, limited exploration, low-fidelity prototypes, and premature commitment.

Modern agents change those economics. Discovery activities can be:

- **augmented** through critique, recall, synthesis, and alternative framing;
- **delegated** when work is bounded and its output can be inspected;
- **parallelized** across independent questions, perspectives, and prototypes;
- **expanded** to consider more evidence and alternatives than would normally be economical;
- **compressed** into shorter learning cycles with earlier, fuller prototypes.

The ambition is an order-of-magnitude improvement—such as 5× or 10×—in the speed or effective capacity of discovery. This is an outcome to evaluate, not a benefit to assume.

Agentic leverage must be measured through:

- time from idea to useful evidence;
- consequential uncertainties resolved;
- credible alternatives considered;
- evidence coverage and quality;
- experiments completed per unit of human attention;
- prototype fidelity relative to its question;
- quality and reversibility of decisions.

More generated output is not itself evidence of improvement.

## Governing Rule

> Use the lightest workflow that makes intent, uncertainty, evidence, ownership, and risk visible enough for the cost of being wrong.

Before producing an artifact or prototype, ask:

> **If this initiative fails, what will probably have been wrong?**

The answer determines the smallest useful next move.

| Main uncertainty | Appropriate response |
|---|---|
| Intent — the desired outcome may be wrong | Clarify the opportunity and outcome |
| Context — relevant constraints may be missing | Retrieve and curate context and anti-goals |
| Semantics — key concepts or behavior are unclear | Develop scenarios, alternatives, or a mini-spec |
| Desirability — the problem may not matter enough | Conduct interviews, observation, or demand experiments |
| Architecture — feasibility or boundaries are unclear | Run a technical spike or architecture probe |
| Usability — users may not understand the interaction | Build a task-oriented interface prototype |
| Verification — success cannot yet be recognized | Define an evidence plan before building |

The workbench should not invoke a complete methodology merely because one is available. Under-mapping causes drift; over-mapping delays learning.

## Primary Unit: The Initiative

The system is organized around **initiatives**.

An initiative represents a problem, opportunity, or idea under investigation. It connects work performed across multiple sessions and may contain:

- provisional intent, users, outcomes, constraints, and anti-goals;
- the current problem or opportunity framing;
- evidence, sources, and residual uncertainty;
- assumptions and hypotheses;
- alternatives considered, including rejected alternatives;
- experiments and their results;
- decisions and their rationale;
- specifications where needed;
- prototypes;
- reusable conclusions.

A session is one episode of work. The initiative preserves enough meaning for future agents and sessions to continue without requiring the user to reconstruct its history.

Canonical initiative state lives under the repository-root `initiatives/` directory; reusable discovery capabilities live under `skills/`.

Intent is expected to begin incomplete. Agents may challenge, clarify, and propose interpretations of it, but they must not silently decide the destination.

## Discovery Behavior

### Diverge before committing

Exploration should encourage:

- independent problem framings;
- alternative customer or user segments;
- contradictory interpretations;
- unusual perspectives;
- competing solution directions;
- reasons the initial idea may be wrong.

Commitment requires stricter criteria:

- the uncertainty being addressed;
- assumptions being made;
- evidence required;
- scope and anti-goals;
- ownership of consequential decisions;
- stop or expiry conditions.

Rejected alternatives and the reasons they lost should be preserved without turning every possibility into a requirement.

### Match evidence to the claim

The system should define convincing evidence before building.

Different claims require different evidence:

- interviews and observations test problem understanding;
- behavioral or demand experiments test interest;
- task walkthroughs test usability;
- payload inspection tests data behavior;
- benchmarks test performance;
- technical spikes test feasibility;
- automated tests verify specified software behavior.

Tests cannot prove desirability, and an agent’s explanation cannot prove correctness. Where evidence is weak, the system should expose residual uncertainty rather than manufacture confidence.

### Prototype to answer a question

A prototype is an experiment, not an early product.

Every prototype should state:

- the hypothesis or decision it informs;
- the cheapest sufficient fidelity;
- what is intentionally fake or omitted;
- what evidence will be collected;
- its stop condition;
- its disposal or default-expiry rule.

Agentic implementation may make higher-fidelity prototypes affordable, but fuller prototypes should be built only when additional fidelity produces stronger evidence. Cheap code generation does not make structural complexity or accumulated debt cheap.

A prototype should graduate to its own product repository when it stops being primarily an experiment and begins becoming an independently maintained product.

## Agent Autonomy

Autonomy should be routed according to **verifiability, reversibility, and consequence**.

```text
Agent acts
→ Agent acts and reports
→ Agent proposes options
→ Human approves
→ Stop until human decision
```

Agents may act more independently when:

- the task is bounded;
- outcomes are reversible;
- evidence is observable;
- strong deterministic or repeatable checks exist;
- failure has limited consequences.

Agents should primarily produce options and evidence when:

- intent or semantics remain contested;
- trust, policy, ethics, or reputation are involved;
- architecture creates durable commitments;
- non-functional risks are significant;
- success depends on ambiguous human behavior;
- a decision is difficult to reverse.

Humans retain ownership of meaning, values, risk acceptance, and consequential commitment. Human attention should be concentrated at these decision points rather than inserted into every mechanical step.

## Skills, Harness, and Deterministic Foundation

The workbench is powered by a curated collection of composable agent skills. Relevant practices may be adapted from Matt Pocock’s skills, BMAD, GStack, GBrain, product discovery, customer research, design thinking, and other methods.

No framework should be adopted wholesale. Each skill must address a demonstrated discovery need.

The preferred architecture is **thin harness, fat skills, deterministic foundation**:

```text
┌──────────────────────────────────────────────────────┐
│ Fat skills                                           │
│ Judgment, process, domain knowledge, failure modes   │
└──────────────────────────┬───────────────────────────┘
                           │ routed and executed by
┌──────────────────────────▼───────────────────────────┐
│ Thin harness                                         │
│ Agent loop, context, state, tools, permissions       │
└──────────────────────────┬───────────────────────────┘
                           │ invokes
┌──────────────────────────▼───────────────────────────┐
│ Deterministic foundation                             │
│ Search, files, APIs, CLIs, schemas, checks, metrics  │
└──────────────────────────────────────────────────────┘
```

Push interpretation and adaptable process **up into skills**. Push repeatable execution and verification **down into deterministic tools**. Keep orchestration narrow enough that the system remains understandable and skills remain portable.

### The harness routes and constrains

The harness is the environment that runs the model. Thin does not mean trivial or unsafe; it means that the harness owns a small set of infrastructure responsibilities rather than embedding domain judgment into a large workflow engine.

It should:

- run the agent loop;
- maintain structured initiative and session state;
- read and write approved files;
- manage context and progressive retrieval;
- route requests to relevant skills and references;
- expose scoped, purpose-built tools;
- enforce permissions, checkpoints, and safety boundaries;
- record experiments, actions, and provenance;
- run deterministic gates and evaluations where possible.

Avoid a large collection of overlapping tools, always-loaded instructions, and framework abstractions that consume attention without improving outcomes. The harness should provide the right context and capability at the right time without drowning the agent in either.

### Skills are executable recipes for judgment

A skill is a reusable Markdown procedure that teaches the agent **how** to perform a kind of work. The initiative supplies the subject, constraints, and question; the skill supplies the process.

In that sense, a skill behaves like a method call:

```text
skill(process) + invocation(context and parameters) → situated capability
```

Markdown skills are simultaneously human-readable documentation, agent instructions, and portable specifications. Their value lies not in generic exhortations, but in encoding domain judgment, routing logic, evidence standards, integration points, and known failure modes.

The root virtue of a skill is **predictability**: it should cause the agent to follow the same intended process across runs, while still allowing outputs to vary with context and evidence.

A skill should define only what its behavior requires, including as appropriate:

- purpose, parameters, and invocation conditions;
- when not to use it;
- required inputs and context to retrieve;
- ordered steps with checkable completion criteria;
- decision branches and routing logic;
- evidence and citation requirements;
- expected artifacts and integration points;
- human checkpoints and autonomy limits;
- stop conditions and failure handling;
- possible next skills.

Put immediately required steps in the skill. Keep supporting rules near the steps that use them, and progressively disclose branch-specific or detailed reference material through explicit context pointers. Each meaning should have one authoritative home.

### Invocation has a cost

Skills may be:

- **model-invoked**, when the agent must recognize and apply them autonomously;
- **user-invoked**, when deliberate manual activation is preferable;
- reached through a **router**, when user-invoked skills become too numerous to remember.

Model-invoked descriptions consume context on every turn, while user-invoked skills consume human memory and attention. A model-facing description should therefore contain compact, distinct triggers rather than a summary of the entire skill. Resolvers and routers should load detailed context only when it becomes relevant.

The system should prefer a small, legible capability surface over an always-visible catalog of every possible method.

### Put work on the correct side

Use skills where the agent must interpret, adapt, synthesize, ask questions, or exercise judgment. Use deterministic code where the same input should reliably produce the same output.

| Work | Appropriate layer |
|---|---|
| Interpret an ambiguous opportunity | Skill |
| Select an experiment from context | Skill |
| Synthesize contradictory evidence | Skill |
| Search files or retrieve records | Deterministic tool |
| Calculate metrics or validate a schema | Deterministic tool |
| Enforce permissions or an approval gate | Harness |

Do not force deterministic work into latent reasoning, and do not freeze context-sensitive judgment into brittle workflow code.

### Skills must earn permanence

New behavior should normally be performed manually on representative cases before being codified. Once the process is understood and expected to recur, it can become a skill; once its actions are strongly verifiable, parts may become deterministic tooling or automation.

Skills should improve from observed traces, failures, and user corrections, but changes to canonical behavior remain reviewable. Periodically prune:

- duplicated meanings;
- instructions that do not change behavior;
- stale rules and accumulated sediment;
- oversized skills that should disclose references progressively;
- ambiguous completion criteria that encourage premature completion;
- negative instructions that can be replaced with a clear positive behavior.

The goal is not a large skill library. It is a compounding set of trusted discovery capabilities whose process becomes more reliable through use.

Every skill must carry a small colocated eval suite and earn maturity through isolated comparative runs. Evals cover invocation, process, outcome, quality, and efficiency; they use deterministic evidence where possible and structured judgment where necessary. The organization and maturity contract lives in [Skill Evaluations](./skill-evaluations.md).

## Context and Retrieval

The user should not need to supply all relevant context in every prompt.

The system should progressively retrieve from:

1. the current conversation;
2. the current initiative;
3. the discovery repository;
4. connected knowledge sources;
5. external research.

The order may change according to the question. Market research may begin externally, while a continuity question should begin with the initiative.

Retrieved material must preserve provenance and distinguish:

- user-provided information;
- canonical knowledge;
- prior discovery trace;
- external evidence;
- agent interpretation;
- unverified hypothesis.

Retrieval is itself a source of risk. Several agents using the same incomplete brief or flawed retrieved context do not provide independent validation; they amplify a shared error. Where independence matters, agents should frame or investigate a question separately before seeing each other’s conclusions.

The workbench must therefore audit not only individual outputs, but also shared inputs, evaluation criteria, and workflow topology.

## Trace and Canon

The system should keep **discovery trace** separate from **canonical knowledge**.

The trace may be append-only and include:

- questions;
- alternatives;
- sources;
- experiments;
- observations;
- decisions;
- session history.

Canon represents the current curated understanding:

- durable intent;
- accepted definitions;
- validated findings;
- product or organizational knowledge;
- reusable workflows and principles.

Agents may propose canonical updates, but agent-generated summaries should not become durable truth automatically. A comprehending human decides what enters canon, and canon should remain versioned and revisable as evidence changes.

The existing personal knowledge base may remain the canonical home for broader personal and professional knowledge. The Discovery Workbench should initially integrate with it through controlled, read-only retrieval. Write-back, semantic indexing, graph traversal, and automated enrichment should be added only after demonstrated needs justify them.

## Artifacts as Contracts

Artifacts exist to reduce a named uncertainty or preserve meaning across agents and sessions. They are contracts and maps, not ceremony or truth.

Prefer the smallest sufficient artifact:

- question;
- hypothesis;
- scenario;
- source note;
- decision record;
- experiment card;
- prototype brief;
- evaluation result.

Artifacts should expose assumptions, confidence, provenance, ownership, and expiry conditions. Important conclusions should not remain trapped in conversation, but neither should every conversational detail become permanent documentation.

## Boundaries

The Discovery Workbench is not:

- a replacement for all personal knowledge management;
- a rigid waterfall from brainstorming to implementation;
- an autonomous startup generator;
- a collection of every available skill or agent persona;
- a system that treats process completion as validation;
- a system that treats code, tests, or plausible explanations as proof of market value;
- a knowledge graph designed before genuine retrieval needs emerge;
- a permanent home for products that have graduated from experimentation.

## Sources and Influences

This charter synthesizes internal learning with external methods. Relevant source material includes:

- Garry Tan, [“Thin Harness, Fat Skills”](https://raw.githubusercontent.com/garrytan/gbrain/refs/heads/master/docs/ethos/THIN_HARNESS_FAT_SKILLS.md);
- Garry Tan, [“Homebrew for Personal AI” (Markdown Skills as Recipes)](https://raw.githubusercontent.com/garrytan/gbrain/refs/heads/master/docs/ethos/MARKDOWN_SKILLS_AS_RECIPES.md);
- Matt Pocock, [“Writing Great Skills”](https://raw.githubusercontent.com/mattpocock/skills/refs/heads/main/skills/productivity/writing-great-skills/SKILL.md);
- the supporting [Principles for an Agent-Native Discovery Workbench](./discovery-workbench-principles.md).

These sources inform the workbench but do not govern it wholesale. Their practices should be tested against real discovery initiatives, adapted to local needs, and retained only when they improve learning, reliability, or leverage.

## Definition of Success

The workbench succeeds when:

- a vague idea becomes a clearly framed, revisable initiative;
- the most consequential uncertainty determines the next action;
- relevant context is found without being repeatedly restated;
- evidence, inference, and hypothesis remain distinguishable;
- multiple credible alternatives can be explored efficiently;
- agents perform bounded work with appropriate autonomy;
- skills invoke reliably, follow predictable processes, and load only the context they need;
- skill changes demonstrate value against a baseline through evidence-backed evals;
- judgment remains in inspectable skills while repeatable execution is deterministically verified;
- research, critique, and prototyping can proceed in parallel without merely reproducing shared assumptions;
- prototypes are functional enough to answer their intended question;
- future sessions can reconstruct the initiative and its decisions;
- abandoned initiatives still produce reusable learning;
- the user spends more attention on judgment and less on mechanical work;
- faster execution improves learning rather than hiding uncertainty;
- promising discoveries can graduate cleanly into independent products.

> **The Discovery Workbench uses agentic leverage not simply to automate discovery, but to change the depth, breadth, speed, and prototype fidelity that are economically possible—while keeping intent human-owned, evidence traceable, and uncertainty visible.**
