# Initiative Organization

This directory is the canonical home for D7Y initiatives.

## What an initiative is

An **initiative** is a durable investigation of a problem, opportunity, or idea across one or more sessions. It exists to reduce consequential uncertainty and may lead to a prototype, a decision, reusable learning, or a deliberate stop.

An initiative is not:

- a fleeting idea that has not been accepted for investigation;
- a session or conversation;
- a required sequence of documents;
- a product repository after the work has graduated from experimentation.

Create an initiative when the intent is to investigate something beyond the current exchange and preserve continuity, evidence, or decisions.

## Canonical layout

```text
initiatives/
└── <stable-slug>/
    ├── initiative.md
    └── <artifacts added only as needed>
```

The slug is a stable identifier. Use lowercase words separated by hyphens. Do not rename it merely because the title or framing evolves.

`initiative.md` is the canonical current map. Supporting research, experiments, traces, and prototypes may be added beside it when the initiative needs them; no empty artifact structure is required.

## Lifecycle

Use one status:

- `active` — currently open for discovery;
- `paused` — intentionally deferred but resumable;
- `graduated` — moved into an independently maintained product or project;
- `archived` — stopped, superseded, merged, or retained only for learning.

Several initiatives may be active at once. Status does not identify the current initiative for a session.

## Current initiative

Resolve the current initiative from evidence in this order:

1. the user explicitly names or links an initiative;
2. the working path is inside an initiative directory;
3. the current conversation clearly continues one initiative;
4. an existing initiative is a strong semantic match for the stated outcome.

Do not use recency or `active` status alone. There is intentionally no repository-global `current` pointer because concurrent sessions may work on different initiatives.

## Similarity and identity

Two initiatives are the same when they pursue substantially the same intended outcome for the same problem or opportunity and can share one coherent uncertainty and decision history.

Shared keywords or domain are not enough. Classify candidates as:

- **same** — continue the existing initiative;
- **related** — create or use a distinct initiative and cross-link them;
- **superseding** — continue the chosen canonical initiative and archive or link the displaced one after human confirmation;
- **new** — no material match exists, so create a new initiative when the user intends to start one;
- **unclear** — present the comparison and ask before creating or merging.

Search existing `initiative.md` files before creating a new directory. Repository scanning is the initial index; add a generated or curated global index only when observed scale makes scanning inadequate.

## Minimum initiative artifact

Every `initiative.md` begins with this structure:

```markdown
---
title: <human-readable title>
status: active
created: YYYY-MM-DD
updated: YYYY-MM-DD
aliases: []
related: []
---

# <Title>

## Provisional intent

### Outcome

<What change or result is being pursued?>

### Subject

<For whom, or in what domain, does this matter?>

### Constraints and anti-goals

<Known boundaries; write "Unknown" when not established.>

## Primary uncertainty

<What is most likely to be wrong if this fails?>

## Current understanding

### Evidence

<Known observations and provenance; distinguish evidence from inference.>

### Assumptions

<Unverified beliefs currently shaping the initiative.>

## Current state

<What has been decided, what remains open, and the smallest useful next move.>
```

Store aliases as strings and related initiatives as stable slugs in their respective frontmatter lists.

Keep unknown fields explicit rather than inventing certainty. Extend the artifact only when a named uncertainty or continuity need requires it.
