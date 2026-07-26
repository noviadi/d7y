---
name: writing-great-skills
description: "Writes and reviews predictable agent skills. Use when creating, editing, splitting, routing, testing, or pruning skills in D7Y's skills directory."
license: MIT
compatibility: Markdown-based Agent Skills with YAML frontmatter; intended for later installation into agent-specific skill directories.
metadata:
  source: https://github.com/mattpocock/skills/tree/main/skills/productivity/writing-great-skills
  adapted-for: d7y
  maturity: provisional
---

# Writing Great Skills

Create skills that make an agent follow a predictable **process**, not produce identical output.

## 1. Establish the skill boundary

State the behavior the skill should make repeatable and the observed need it addresses. Identify:

- what the invocation supplies;
- what process the skill supplies;
- what successful behavior looks like;
- when the skill should not run;
- what belongs outside the skill.

Put adaptable interpretation, synthesis, and judgment in the skill. Put repeatable operations and checks in deterministic tools. Put context routing, permissions, and enforced gates in the harness.

**Complete when:** the skill has one coherent responsibility and every proposed instruction belongs to it rather than to a tool, the harness, or shared reference.

## 2. Choose invocation deliberately

Choose how the skill will be reached:

- **Model-invoked:** keep a narrow description when the agent or another skill must discover it autonomously.
- **User-invoked:** use the target agent's supported opt-out mechanism when invocation should require deliberate human choice.
- **Router-reached:** introduce a router when user-invoked skills become too numerous for a person to remember.

Model invocation spends persistent context load. User invocation spends human cognitive load. Pay only the cost the behavior justifies.

For a model-invoked description:

- begin with the skill's leading action;
- state what it does and the distinct conditions that trigger it;
- keep one trigger for each real branch;
- omit identity, explanation, and synonyms already covered by the body.

**Complete when:** the invocation mode is explicit, trigger branches are distinct, and the description contains no body summary disguised as routing information.

## 3. Design the information hierarchy

Arrange content by when the agent needs it:

1. ordered steps in `SKILL.md`;
2. rules and reference needed by every run in `SKILL.md`;
3. branch-specific or detailed reference behind explicit context pointers.

Keep definitions, rules, and caveats for one concept together. Inline anything every branch requires. Disclose material used only by some branches into clearly named sibling files, and state precisely when to read each one.

Split a skill only when the split earns its cost:

- split by invocation when a capability needs an independent trigger;
- split by sequence when visible later steps repeatedly cause the current step to finish prematurely;
- otherwise keep the process together.

**Complete when:** every instruction sits at the earliest level that needs it, every disclosed reference has a reliable retrieval condition, and no required meaning is scattered across files.

## 4. Write executable steps

Write actions in the order the agent should perform them. Each step must end with a checkable completion criterion.

Strong criteria describe observable coverage, for example:

- every invocation branch has a representative test;
- every external reference is reachable from a context pointer;
- every required artifact field is present;
- every changed behavior has one authoritative instruction.

Use compact, established leading words when they reliably recruit the intended behavior. Prefer positive target behavior over prohibitions. Keep hard prohibitions only for genuine guardrails, paired with the action the agent should take instead.

Do not add general advice the model already follows. Instructions earn space only when they alter invocation, process, judgment, verification, or failure handling.

**Complete when:** the agent can determine whether each step is finished without relying on a vague feeling of completeness.

## 5. Encode judgment and failure handling

Capture the parts that make the procedure valuable:

- decision branches and routing logic;
- evidence and provenance requirements;
- domain-specific judgment calls;
- integration points;
- autonomy and human-approval boundaries;
- known failure modes and recovery behavior;
- stop conditions and possible next skills.

Describe a decision's criteria rather than prescribing one output for every context. A skill should make the process predictable while leaving evidence-sensitive conclusions open.

**Complete when:** consequential branches, expected failures, and irreversible decisions have explicit handling rather than relying on improvisation.

## 6. Test behavior, not prose

Read `docs/skill-evaluations.md` and create `evals/evals.json` beside the skill using `evals/skill-evals.schema.json`. Begin with:

- a clear positive invocation;
- a materially different or difficult positive branch;
- a negative control that should not invoke the skill.

Add incomplete context and likely failures when they represent important branches. Define success before tuning the skill, then run each case in isolated contexts with and without the skill—or against the previous accepted version.

Observe whether the skill invokes correctly, performs sufficient legwork, respects checkpoints, retrieves disclosed references, and satisfies each completion criterion. Diagnose behavior from traces rather than debating wording in isolation.

Codify a new skill only after the process has been exercised manually enough to understand it. Promote repeated, strongly verifiable operations into deterministic tooling instead of expanding the skill indefinitely.

Run `python3 evals/validate_skill_evals.py` after authoring the suite.

**Complete when:** the validator passes and every invocation branch has comparative evidence of the intended process, or the skill remains explicitly provisional.

## 7. Prune before finishing

Apply these checks sentence by sentence:

- **Single source:** does this meaning exist in exactly one authoritative place?
- **Relevance:** does this sentence still affect the skill's behavior?
- **No-op:** would removing it change what the agent does?
- **Sediment:** is it stale material retained only because deletion feels risky?
- **Sprawl:** should branch-specific reference move behind a pointer?
- **Premature completion:** does a step need a sharper completion criterion?
- **Negation:** can a prohibition become a positive target behavior?

Delete failed sentences rather than cosmetically shortening them. Do not preserve explanatory prose merely because it sounds useful.

**Complete when:** every remaining sentence changes invocation, execution, judgment, verification, or recovery, and every meaning has one source of truth.

## 8. Validate the skill artifact

Before finishing, verify:

- the directory and frontmatter `name` match;
- the name uses lowercase gerund form with hyphens;
- the description states both behavior and invocation conditions;
- metadata and compatibility claims are accurate;
- `SKILL.md` remains focused and under 500 lines;
- `evals/evals.json` exists and conforms to the shared schema;
- referenced files and tools exist;
- source adaptations retain attribution and licensing;
- installation-specific links or symlinks are not assumed to exist.

Return the files created or changed, the invocation choice, the behavioral cases tested, and any provisional assumptions.

**Complete when:** all checks pass and another agent can use the skill without undisclosed context.
