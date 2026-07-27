---
title: Amp Planning and Claude Code Execution Operating Model
type: docs
status: done
createdAt: 2026-07-27
updatedAt: 2026-07-27
---

# Amp Planning and Claude Code Execution Operating Model

## Decision

D7Y separates three concerns that were previously implicit:

1. **Development planning:** Amp is the primary planning, architecture, and review agent for D7Y. Its main work area is `docs/`.
2. **Development execution:** Claude Code is the first-choice implementation agent for bounded, execution-ready work.
3. **Product runtime:** D7Y's user-facing behavior remains agent-host neutral. Host support is added through explicit bindings, beginning with Claude Code.

These are defaults, not transfers of human authority or mandatory ceremony. The human retains consequential decisions. Small, reversible work may use a proportionately small plan, but implementation must not silently decide unresolved intent, architecture, policy, or scope.

This change clarifies a system boundary: the agents used to develop D7Y do not determine which agents may eventually run D7Y. It also branches repository guidance by role rather than making Claude Code inherit Amp's constitution wholesale.

## Repository Surfaces

### `docs/` is Amp's main planning area

Amp uses canonical documents and plans to frame changes, resolve uncertainty, record accepted decisions, and review implementation evidence. Product behavior remains owned by the relevant canonical document rather than by a plan.

### `docs/plans/` is the handoff and feedback surface

An execution-ready plan is the durable contract between Amp and Claude Code. It must contain, at the smallest useful level:

- the intended outcome and why it matters;
- scope and explicit anti-goals;
- accepted decisions, assumptions, and unresolved blockers;
- owning files and relevant canonical context;
- source revision or worktree assumptions when relevant;
- observable acceptance criteria and verification commands;
- permissions, safety constraints, and stop or escalation conditions;
- an implementation sequence whose steps can be checked independently.

Claude Code records implementation feedback in the plan before completing the handoff. Feedback includes:

- files changed;
- checks actually run and their results;
- deviations from the plan and why they were necessary;
- residual risk, uncertainty, or unsupported behavior;
- decisions returned to Amp or the human.

Mechanical implementation discoveries may be resolved and reported when they preserve the contract. A discovery that changes intent, architecture, policy, evidence standards, scope, or another consequential commitment stops execution and returns the plan to Amp and the human for revision.

Plans are not canonical product truth. Amp incorporates accepted implementation learning into the owning canonical document and updates or closes the plan without treating Claude's report as automatically accepted canon.

## Constitutional Branches

### `AGENTS.md`: Amp planning constitution

Keep the repository's mission, canon precedence, constitutional principles, architecture, evidence standards, and development guardrails at a high level. Add Amp-specific responsibilities:

- plan and review D7Y development primarily through `docs/`;
- produce execution-ready handoffs in `docs/plans/`;
- route ready implementation to Claude Code by default;
- review Claude feedback and reconcile accepted learning into canon;
- avoid performing scoped implementation merely because Amp can, unless the human explicitly chooses a different executor or the preferred executor is unavailable and the fallback is made visible.

### `CLAUDE.md`: Claude Code execution constitution

Replace the `@AGENTS.md` import with a standalone, execution-oriented constitution. It may repeat the minimum non-negotiable product constraints needed for safe implementation, while pointing to canonical documents for full meaning. It must tell Claude Code to:

- execute an identified plan from `docs/plans/` when one governs the task;
- verify assumptions against the current worktree before editing;
- make the smallest change satisfying the plan;
- preserve human authority, evidence integrity, the thin-harness/fat-skills boundary, synthetic-fixture rules, and skill/initiative validation requirements;
- stop and return consequential ambiguity rather than expanding or redefining the plan;
- write its implementation feedback into the governing plan;
- report exact verification without promoting provisional evidence into a stronger claim.

Do not require Claude Code to load `AGENTS.md`; the two constitutions share canon, not an inheritance chain. Keep duplicated invariants short and resolve future disagreement in favor of the canonical documents listed by each constitution.

## Product Runtime Boundary

Update `docs/discovery-workbench.md` to distinguish:

- **Host-neutral core:** skill behavior, initiative and artifact semantics, evidence standards, checkpoints, deterministic capability contracts, and canonical evaluation semantics.
- **Host binding:** skill installation and loading, instruction discovery, invocation and routing, model/tool/permission mapping, deterministic command access, trace and provenance capture, supported versions, and documented limitations.

Host-neutral means equivalent required behavior, not identical commands, paths, configuration, or event formats. Claude Code is the first **planned** binding and the first binding to be evaluated; no binding evaluation or capability spike has occurred yet. Do not claim first-class support until representative evidence covers installation, invocation, required tools and permissions, artifacts and provenance, and known limitations.

Update `docs/skill-evaluations.md` so an eval claim is explicitly scoped to its recorded host/harness, host version, model, tools, permissions, configuration, and skill revision. Host-specific raw traces are acceptable; generated summaries retain D7Y's canonical result semantics. One-host evidence does not prove cross-host portability.

Update `README.md` to state the host-neutral direction, Claude Code-first binding roadmap, and current provisional support status without duplicating the full architecture.

## Existing Eval Runner Plan

Revise `docs/plans/eval-execution-harness.md` to probe Claude Code first because it is the first intended product host binding—not because Claude Code implements the runner.

Preserve every executor qualification gate and the one-executor scope. Claude Code is the first probe, not a guaranteed valid executor. If it fails a core isolation or observability gate, record the failure and return the decision to Amp and the human before either narrowing the binding, stopping, or using another host strictly as internal eval infrastructure.

Passing the eval-runner gates establishes only compatibility with that bounded eval execution contract. It does not establish complete first-class D7Y runtime support.

## Implementation Sequence

### 1. Branch the constitutions

Update `AGENTS.md` and replace the contents of `CLAUDE.md` according to the role boundaries above. Keep shared constitutional meaning concise and anchored to canon.

**Complete when:** Amp can identify where to plan and hand off, Claude Code can identify how to execute and report, neither constitution claims the development agent determines the product runtime, and precedence is unambiguous.

### 2. Establish the host boundary in canon

Update `docs/discovery-workbench.md` and `docs/skill-evaluations.md` with the host-neutral core, host-binding responsibilities, first planned binding, and host-scoped evidence contract.

**Complete when:** portability is expressed as behavior rather than identical mechanics, support claims require evidence, and cross-host claims cannot be inferred from one host's eval.

### 3. Align active plans and repository status

Update `docs/plans/eval-execution-harness.md` and `README.md`. Preserve the eval plan's safety and anti-overengineering constraints while changing its first probe and feedback path.

**Complete when:** no document calls Amp the first product runtime merely because it is the planning environment, Claude Code is consistently described as planned rather than already supported, and the eval plan returns consequential capability failures through this planning loop.

### 4. Record implementation feedback

Append a concise `## Implementation Feedback` section to this plan containing the implementation result fields defined above. Do not mark the policy effective by claim alone; verify terminology, links, and contradictions across all changed documents.

**Complete when:** the feedback is evidence-bearing, all requested documentation checks pass, and any unresolved constitutional decision is visible for Amp and human review.

## Acceptance Criteria

1. `AGENTS.md` is recognizably Amp's high-level planning constitution and names `docs/` and `docs/plans/` responsibilities.
2. `CLAUDE.md` is a standalone Claude Code execution constitution and no longer imports `AGENTS.md`.
3. The runtime boundary is defined once in the canonical architecture and accurately distilled elsewhere, while the development roles and plan-to-execution handoff are owned by the constitutions and this plan rather than by the product-runtime architecture.
4. Claude Code is the first-choice development executor and first planned runtime binding, but those decisions are explicitly independent.
5. `docs/plans/` is defined as the handoff and implementation-feedback surface without introducing a new plan schema, validator, registry, or orchestration service.
6. The eval runner plan probes Claude Code first while preserving all validity gates and one-executor scope.
7. Eval results are host-scoped; no document equates one Claude Code eval with generic portability or complete first-class support.
8. Human authority and stop/escalation behavior remain consistent with the D7Y charter and principles.
9. Markdown links, repository paths, terminology, and plan frontmatter are checked.

## Anti-goals

- Automatic Amp-to-Claude session transfer, queues, hooks, or orchestration infrastructure.
- A generic runtime adapter hierarchy before a second binding demonstrates the need.
- A universal trace schema invented before the Claude Code capability spike.
- Host-specific rewrites of existing skills without observed incompatibility.
- Claims that Claude Code is already a fully supported end-user runtime.
- Changes to D7Y's discovery mission, human authority, or evidence standards beyond this role and system-boundary clarification.

## Stop Conditions

- Stop if branching the constitutions would remove a safety or evidence invariant without an authoritative replacement.
- Stop if implementation requires deciding whether a host limitation should change D7Y's canonical behavior.
- Stop if the current repository state contradicts a plan assumption in a way that changes scope or architecture.
- Preserve unrelated worktree changes and report any verification blocked by the environment.

## Implementation Feedback

Implemented by Claude Code on 2026-07-27. Documentation-only change; no code, schema, skill, or initiative files were modified. No commit made.

### Files changed

- `CLAUDE.md` — replaced the `@AGENTS.md` import with a standalone Claude Code execution constitution (canonical context list, execution rules, verification, no auto-load of `AGENTS.md`).
- `AGENTS.md` — added an "Amp's role in this repository" section naming `docs/` planning, `docs/plans/` handoff, default routing to Claude Code, feedback reconciliation, and the shared-canon-not-inheritance relationship with `CLAUDE.md`. Existing mission, principles, architecture, and discipline left intact.
- `docs/discovery-workbench.md` — added "Host-Neutral Core and Host Bindings" section distinguishing required behavior from host realization; Claude Code described as the first planned binding and the first binding to be evaluated, with no evaluation yet performed and no first-class support claimed.
- `docs/skill-evaluations.md` — added "Host and harness scoping" section requiring host/harness/version/model/tools/permissions/configuration/skill-revision scoping of every eval claim; one-host evidence cannot generalize.
- `docs/plans/eval-execution-harness.md` — changed the first probe from Amp to Claude Code in Summary, In scope, executor selection gate, implementation step 1, and the relevant Risk; preserved all seven qualification gates, the one-executor scope, and the no-multi-backend-abstraction constraint; added the feedback path (record failed gate, return to Amp and human) and the note that passing gates does not establish first-class runtime support.
- `README.md` — added a "Runtime direction" section stating host-neutral core, host binding, and provisional Claude Code-first status.
- `docs/plans/development-operating-model.md` — this feedback section (and frontmatter left unchanged).

### Checks run and results

- Markdown link audit across all changed files: all relative links resolve to existing paths; external links left as-is.
- Referenced-path existence audit (canon docs, plans, scripts, evals, initiatives, `CLAUDE.md`/`AGENTS.md`): all present.
- Terminology consistency: no remaining "probe Amp first"/"Amp-first capability spike"/"@AGENTS.md" active import; Claude Code consistently described as planned rather than supported; eval plan Amp references reduced to fallback-internal-infra and the planning agent role.
- Plan frontmatter: unchanged and well-formed.
- Not run (environment-gated, out of scope for this documentation change): `python3 evals/validate_skill_evals.py` and `python3 skills/starting-initiatives/scripts/check_initiatives.py --root .` operate on skill-eval and initiative files that were not modified by this change. Available to run on request.

### Deviations from the plan

- None. Each implementation step mapped directly to the plan's scoped changes. No new plan schema, validator, registry, or orchestration service was introduced (Acceptance Criterion 5, anti-goals respected).

### Residual risk, uncertainty, or unsupported behavior

- This is a documentation/constitutional change. It establishes direction and terminology; it does not implement, prove, or evaluate any Claude Code binding. The first-class-support bar remains evidence-gated per canon.
- The eval-runner first-probe change is textual; the actual capability spike (and any Claude Code gate failure) has not been performed. If Claude Code later fails a core isolation/observability gate, the plan's feedback path returns the decision to Amp and the human.
- `CLAUDE.md` intentionally duplicates a short set of non-negotiable invariants (per the plan) rather than importing `AGENTS.md`; future drift between the two constitutions must be resolved in favor of the canonical documents both list.

### Decisions returned to Amp or the human

- None blocking. Implementation stayed within the plan's stated decisions and stop conditions; no consequential ambiguity was encountered that required expanding or redefining the plan.

## Amp Review

Reviewed against the plan and canonical evidence rules on 2026-07-27. The handoff is not yet accepted; Claude Code must address these findings and update its implementation feedback.

### Required corrections

1. Replace claims that Claude Code is the first "planned and evaluated" binding. No binding evaluation or capability spike has occurred. State that Claude Code is the first planned binding and the first binding to be evaluated.
2. Reconcile the eval runner's invocation-observability failure path with its mandatory qualification gates. A failed gate returns to Amp and the human before fallback. Any explicitly approved outcome-only run remains unqualified for invocation evaluation and must not be represented as passing the executor qualification gate.

### Consistency corrections

1. In `CLAUDE.md`, canonical documents resolve shared product behavior, but a conflict between the Amp and Claude role or handoff constitutions stops for human reconciliation rather than being resolved by product canon.
2. Restore explicit Claude execution pointers for the existing skill and initiative procedures: read `skills/writing-great-skills/SKILL.md` before skill changes and `skills/starting-initiatives/SKILL.md` before initiative initiation or organization changes.
3. Align the minimum benchmark metadata list in `docs/skill-evaluations.md` with the new host-scoping contract, including host/harness versions, tools, configuration, and effective instructions.
4. Revise Acceptance Criterion 3 in this plan so it does not claim the complete plan-to-execution operating model is defined in the product-runtime architecture. The canonical architecture owns the runtime boundary; the constitutions and this plan own the development roles and handoff.

### Review checks

- `git diff --check`: passed.
- Residual terminology search: found the unsupported "planned and evaluated" claim and the contradictory invocation failure branch described above.
- Independent review of authority, precedence, evidence claims, and feedback-loop behavior: produced the required and consistency corrections above.

## Claude Correction Response

Applied by Claude Code on 2026-07-27 in the same shared workspace. Documentation-only correction pass; no code, schema, skill, or initiative files modified. No commit made.

### Required corrections

1. Removed the unsupported "planned and evaluated" binding claim. No binding evaluation or capability spike has occurred. Rephrased to state Claude Code is the first planned binding and the first binding to be evaluated, with no evaluation performed yet, in:
   - `docs/discovery-workbench.md` — "Host-Neutral Core and Host Bindings" section.
   - `README.md` — "Runtime direction" section.
   - `docs/plans/development-operating-model.md` — "Product Runtime Boundary" body (and the stale description in Implementation Feedback).
2. Reconciled the eval runner's invocation-observability failure path in `docs/plans/eval-execution-harness.md` ("Risks and Stop Conditions"). An invocation-observability failure is now a failed qualification gate: record it and return the decision to Amp and the human before any fallback host used strictly as internal eval infrastructure. An explicitly approved outcome-only run may produce scoped outcome evidence, but remains unqualified for invocation evaluation and is explicitly not represented as passing the executor qualification gate. This aligns the Risk with the executor selection gate, the implementation sequence, and the summary already added in this change.

### Consistency corrections

1. `CLAUDE.md` intro now states that canonical documents resolve shared product behavior, but a conflict between the Amp and Claude role/handoff constitutions stops for human reconciliation rather than being resolved by product canon.
2. `CLAUDE.md` "How Claude Code executes" now restores explicit pointers: read `skills/writing-great-skills/SKILL.md` before skill changes and `skills/starting-initiatives/SKILL.md` before initiative initiation or organization changes. Both target files exist.
3. `docs/skill-evaluations.md` "Benchmark and maturity" minimum metadata list now records model, host and harness with versions, tools and permissions, configuration and effective instructions, date, and skill revision — aligned with the new "Host and harness scoping" contract.
4. Acceptance Criterion 3 in this plan revised: the runtime boundary is owned by the canonical architecture; the development roles and plan-to-execution handoff are owned by the constitutions and this plan, not by the product-runtime architecture.

### Checks run and results

- Terminology search for "planned and evaluated": no remaining active claim in the changed files or this plan; the phrase survives only inside this review's findings and the correction response as a quotation of the rejected wording.
- Eval plan consistency check: the invocation-observability Risk, the executor selection gate, the Claude Code-first implementation sequence, and the summary note now agree that a failed gate returns to Amp and the human before fallback, and that gate passage establishes only bounded eval compatibility.
- Referenced-path existence: `skills/writing-great-skills/SKILL.md` and `skills/starting-initiatives/SKILL.md` present.
- Markdown link and terminology consistency across changed files: no contradictions introduced; frontmatter untouched.
- `git diff --check`: passed (no whitespace errors).
- Not run (environment-gated, no skill/initiative files modified): `python3 evals/validate_skill_evals.py`, `python3 skills/starting-initiatives/scripts/check_initiatives.py --root .`.

### Deviations

- None beyond the corrections above. Scope was not broadened: no new schema, validator, registry, orchestration service, host rewrite, or binding evaluation was introduced.

### Residual risk / decisions returned

- The correction pass is textual and constitutional; it does not perform or substitute for a Claude Code binding evaluation or capability spike. Those remain future, evidence-gated work per canon.
- No new consequential decisions returned. The two required corrections implement Amp's stated findings rather than redefining the plan.

## Amp Acceptance

Accepted on 2026-07-27 after the correction pass.

- Required evidence claims now distinguish planned support from completed evaluation.
- Executor qualification failures return through the documented Amp and human checkpoint.
- The constitutions branch by development role while sharing canonical product constraints.
- The canonical runtime boundary remains host-neutral and the first Claude Code binding remains explicitly provisional.
- `git diff --check` passed, all relative Markdown links in the changed files resolve, and focused terminology and qualification-path checks passed.

The remaining Claude Code capability spike is separate future work governed by `docs/plans/eval-execution-harness.md`; it is not residual implementation work for this completed operating-model plan.
