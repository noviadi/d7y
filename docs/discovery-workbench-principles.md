# Principles for the D7Y Agent-Native Discovery Workbench

> **Purpose:** help a human and agents move from a fuzzy opportunity through brainstorming and into an evidence-producing prototype—without mistaking plausible output, process, or code for discovery.

## The foundation

Discovery is an **intent-to-evidence learning loop**, not a document pipeline. Human intent begins incomplete and tacit; it becomes clearer through alternatives, probes, observed outcomes, and correction. The workbench should therefore optimize for **reducing the most consequential uncertainty**, not for generating the most ideas, artifacts, or code.

Its governing rule is:

> Use the lightest workflow that makes intent, uncertainty, evidence, ownership, and risk visible enough for the cost of being wrong.

## Core principles

### 1. Converge on intent; do not pretend it arrives complete

Humans own the destination, but discovery helps them find it. Begin with a provisional outcome, users, constraints, anti-goals, and the cost of being wrong. Treat these as a revisable setpoint, then repeatedly compare evidence against them. Agents may challenge, clarify, and propose intent; they must not silently choose it.

### 2. Let the main uncertainty choose the next move

Before producing anything, ask: **“If this fails, what will probably be wrong?”** Classify the answer:

| Main uncertainty | Smallest useful response |
|---|---|
| Intent — wrong outcome | Opportunity or outcome brief |
| Context — known constraints may be missed | Curated context and anti-goals |
| Semantics — key terms or behavior are undecided | Scenarios and a mini-spec |
| Architecture — feasibility or boundaries are unclear | Technical spike or architecture note |
| Verification — success cannot yet be recognized | Evidence plan before prototyping |

Do not use a full process by habit. Under-mapping causes drift; over-mapping delays learning.

### 3. Separate divergence from commitment

Brainstorming benefits from permissive exploration: varied roles, independent alternatives, contradiction, and unusual frames. Decision and delivery require stricter contracts: explicit criteria, assumptions, scope, evidence, and ownership. Preserve rejected options and why they lost, but do not let every idea become a requirement.

### 4. Use artifacts as contracts, not ceremony

Each artifact must reduce a named uncertainty or preserve meaning across agents and sessions. Prefer the smallest sufficient object: question, hypothesis, scenario, decision record, experiment card, prototype brief. An artifact is a **map**, never the territory; show assumptions, confidence, provenance, and expiry conditions rather than presenting it as truth.

### 5. Prototype to answer a question

A prototype is an experiment, not an early product. Every prototype should state:

- the hypothesis or decision it informs;
- the cheapest fidelity needed;
- what is intentionally fake or omitted;
- the evidence to collect;
- a stop condition and disposal/default-expiry rule.

Prefer reversible probes. Production rigor belongs only where code will accumulate or risk requires it. Cheap generation does not make structural debt cheap.

### 6. Match evidence to the claim

Define convincing evidence before building. Interviews test problem understanding; task walkthroughs test usability; payload inspection tests analytics; benchmarks test performance; technical spikes test feasibility. Tests cannot prove desirability, and an agent’s explanation cannot prove correctness. When proof is weak, expose residual uncertainty rather than manufacturing confidence.

### 7. Route autonomy by verifiability and consequence

Agents can act more independently where outcomes are reversible and strong checks exist. Where semantics, policy, architecture, trust, or non-functional risk dominate, agents should produce options and evidence for human judgment. Use a spectrum: **agent acts → agent proposes → human approves → stop**.

### 8. Build the harness, not just the prompt

An agent is a model plus its harness. Reliable discovery needs structured state, scoped tools, schemas, permissions, checkpoints, experiment logs, and deterministic gates—not only instructions. Prompts guide; enforced boundaries constrain. Automate repeated, well-verified moves, while periodically auditing the automation itself.

### 9. Challenge shared maps and correlated agents

Many agents reading one flawed brief do not create independent validation; they scale the same error. Treat shared context, retrieval, evaluation criteria, and orchestration as common-mode risks. Encourage genuinely independent framing before sharing conclusions, diversify reviewers where useful, and audit the **graph**—shared inputs and workflow topology—not only individual outputs.

### 10. Keep trace separate from canon

Retain an append-only discovery trace—questions, alternatives, experiments, evidence, and decisions—but curate canonical knowledge separately. Agent-generated summaries and rationales may be incomplete or unfaithful. Agents may propose updates; a comprehending human decides what becomes durable intent, policy, product knowledge, or reusable workflow. Version and revisit canon as the territory changes.

## The operating loop

**Frame → Diverge → Select → Contract → Prototype → Verify → Commit or Reframe → Capture**

At every transition, require three things: the uncertainty being reduced, the evidence sought, and the owner of the next irreversible decision. The workbench succeeds when it makes learning faster **without making uncertainty invisible**.
