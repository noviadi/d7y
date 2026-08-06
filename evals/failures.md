# D7Y skill failure log (Stage 0 capture)

Real-use failures observed while running the skills against a real runtime
binding. This is the Stage 0 capture mechanism for
`docs/plans/iterative-skill-eval-harness.md`: it feeds the discriminating
derived case set that Stage 1b will run as paired baseline/treatment.

This file is **uncommitted by default** (per canon, raw capture is not source).
Entries are appended as failures are observed; each must clear a
two-experts-agree bar before it is promoted into a derived eval case.

Entry fields: `skill`, `intent`, `observed`, `expected`, `failure_class`
(one of `environment_error`, `pair_error`, `agent_error`, `evidence_error`,
`verifier_error`, `assertion_fail`, `ungradable`), `severity`, and
`outcome_checkable`. `source` links the evidence.

---

## 0001 — bare `d7y` not reachable; first invocation failed

- **skill:** starting-initiatives
- **intent:** Start an initiative from a name-only prompt ("Fuzzy Finance
  Tracker") in a dev-install workspace.
- **observed:** The agent's first CLI call was the bare `d7y initiatives list
  --root <workspace> --json`. It failed with `d7y: command not found` (shell
  exit `127`) because the dev-install binding places the executable at
  `.d7y/d7y` and does not add `.d7y/` to `PATH`. The agent then searched
  `.d7y/`, located the symlink, and re-ran via the absolute path (exit `0`).
- **expected:** The runtime orientation names the executable path, so the agent
  invokes the correct `d7y` on the first try with no failed bare-command
  attempt and no filesystem search.
- **failure_class:** environment_error (the runtime did not expose the CLI the
  way the skill assumed; the skill's behavior was correct for its contract)
- **severity:** low — recovered within the same run; final artifact valid
- **outcome_checkable:** yes — the `127` / command-not-found and the subsequent
  successful invocation are both deterministic and visible in the trace
- **source:** `../d7y-workspaces/workspace-1` run, transcript
  `e1bc9a2a-2745-42e1-9bdc-7372b737fb9e.jsonl`, produced
  `initiatives/fuzzy-finance-tracker/initiative.md`
- **status:** addressed — `agents/runtime-AGENTS.md` now names `.d7y/d7y`;
  `agents/skills/starting-initiatives/SKILL.md` now resolves the CLI from the
  workspace orientation before invoking and treats `127`/`126` as
  command-not-found. Derived case: `locates-cli-first-try`.

## 0002 — did not stop-and-report on a missing command

- **skill:** starting-initiatives
- **intent:** Same run as 0001.
- **observed:** On the failed bare-`d7y` call, the skill's failure contract
  required stopping and reporting an unavailable runtime rather than
  substituting model reasoning. The agent instead improvised: searched the
  filesystem, found `.d7y/d7y`, and completed the task by absolute path. It did
  not stop and report.
- **expected:** The agent follows the skill's stop-and-report contract when the
  runtime appears unavailable — locating the executable per the orientation
  first, then stopping and reporting only if no reachable executable exists.
- **failure_class:** agent_error (deviation from the skill's stated process)
- **severity:** low here — the outcome was correct; but the same deviation
  against a genuinely unavailable runtime would lead to fabricating an
  initiative from model reasoning, a high-severity failure mode
- **outcome_checkable:** yes — the trace shows whether the agent stopped and
  reported or improvised past the contract
- **source:** same run as 0001
- **status:** addressed in contract — the skill now requires resolving the
  executable from the orientation before treating the capability as
  unavailable. Derived case: `stops-when-runtime-unavailable`.

## 0003 — name-only prompt elaborated with untraceable content

- **skill:** starting-initiatives
- **intent:** "create initiative called fuzzy finance tracker" (a name only).
- **observed:** The artifact is format-valid and marks several sections
  `Unknown` (Subject, Constraints; Evidence = "started from a name only"), but
  Outcome and Primary uncertainty assert specifics the request did not supply:
  "fuzzy" resolved to *input* imprecision; invented sub-activities
  ("free-form / approximate transactions", "categorizing noisy data", "estimates
  over exact figures"); and an invented user segment ("Personal or small-team
  money tracking"). One inference is labeled in Assumptions, but the rest is
  asserted as content.
- **expected:** A name-only request yields a thin artifact: sections the request
  does not support read `Unknown`; all inference is confined to Assumptions and
  labeled; no invented user segments, sub-activities, mechanisms, or examples.
- **failure_class:** agent_error (over-elaboration beyond the supplied context),
  rooted in the skill under-specifying the lightness/traceability rule
- **severity:** medium — the artifact is usable, but untraceable content in a
  discovery artifact can mislead downstream decisions by reading as established
  understanding
- **outcome_checkable:** yes — traceability is rubric-gradeable against the prompt
- **source:** `../d7y-workspaces/workspace-1` run;
  `initiatives/fuzzy-finance-tracker/initiative.md`
- **status:** draft — skill-hardening + derived cases in
  `work/skill-lightness-hardening`. The discriminating Stage 1b comparison is
  `lighter-than-baseline-on-terse-prompt`: the skill must produce a thinner,
  more honest artifact than a no-skill baseline on a name-only prompt.

## 0004 — invented user segment from a rich prompt

- **skill:** starting-initiatives
- **intent:** Rich prompt describing a fuzzy, green/yellow/red, signal-based
  inventory with precision-on-request and a non-discrete underlying value.
- **observed:** The artifact is dense and mostly traceable — Evidence correctly
  attributes to "the user's framing" and assumptions are labeled. One leak:
  Subject posits "**Operators and managers** who need to make replenishment
  decisions…" — the prompt said only a generic "user" and never named a user
  segment.
- **expected:** When the intended user is not stated, Subject reads `Unknown`
  rather than positing a segment.
- **failure_class:** agent_error (invented user segment), narrow instance of the
  0003 root cause
- **severity:** low — single unflagged inference in an otherwise traceable
  artifact
- **outcome_checkable:** yes
- **source:** `../d7y-workspaces/workspace-2` run;
  `initiatives/fuzzy-inventory-management/initiative.md`
- **status:** draft — same hardening as 0003 covers this; derived case
  `no-invented-user-segment`.
