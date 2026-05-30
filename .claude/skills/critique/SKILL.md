---
name: critique
description: >-
  Run the critic agent on whatever's on the table — a concept, a doc, a design,
  an ADR, a diff, a contract. Mandatory before any non-obvious decision lands.
  Surfaces hidden coupling, scaling assumptions, ignored failure modes, missing
  abstractions, security holes, and ambiguous ownership. Output goes into
  docs/RED-TEAM.md.
---

# /critique — Hostile constructive review

Run this before any non-obvious decision lands. It is *not* optional —
`CLAUDE.md` rule #9.

## Step 1 — Name the target

Be explicit about what's being critiqued. The critic should not have to
guess. Acceptable targets:

- A doc: `docs/ARCHITECTURE.md`, `docs/PRD.md`, `docs/ADR/NNN-xxx.md`,
  `docs/features/<slug>.md`.
- A diff: `git diff main...HEAD` or a specific PR.
- A concept the user just described in chat — but in that case, write it
  down first as `docs/proposals/<slug>.md` so the critique has a stable
  artifact to attack.

If the target is verbal/fuzzy, the critique will be fuzzy. Capture it first.

## Step 2 — Invoke critic

Hand `critic` the target and any context it needs to understand the
surrounding system (relevant ADRs, the part of ARCHITECTURE this touches).
Critic produces the structured findings: 🔴 Fatal / 🟠 Serious / 🟡 Smell,
each with violated assumption + failure mode + falsifiable test, plus three
forcing questions.

## Step 3 — Triage the findings

For each finding:

- **🔴 Fatal**: must be addressed before this decision/code lands. Options
  are (a) change the design, (b) prove the concern wrong with the
  falsifiable test, or (c) document why the risk is accepted as an ADR
  amendment. "I'll deal with it later" is not an option.
- **🟠 Serious**: address now, or file as `docs/TODO.md` follow-up task with
  a real owner and date.
- **🟡 Smell**: at minimum, add a sentence in the relevant ADR acknowledging
  it so future-you knows it was considered.

## Step 4 — Answer the three forcing questions

The critic's three questions are not rhetorical. Write the answers — in the
ADR if there is one, in the spec if not. If you can't answer a forcing
question, that's the critic's strongest finding: you don't know enough yet
to decide.

## Step 5 — Log into RED-TEAM.md

`docs-keeper` appends the findings to `docs/RED-TEAM.md` with:

```
## YYYY-MM-DD — <target>

### Resolved
- 🔴 <finding> → <how addressed; commit/PR/ADR link>

### Open (followups)
- 🟠 <finding> → TODO T-NNN

### Accepted risks
- 🟡 <finding> → noted in ADR-NNN section "Accepted risks"
```

## Step 6 — Iterate if needed

If the critique forced a redesign, run `/critique` again on the new design.
It's normal for the first version of a non-trivial decision to take 2–3
critique rounds before it's defensible.

## When you can skip

Genuinely never. Even "obvious" decisions benefit from the questions. If a
decision really is trivial, `critic` will say so quickly and move on — that
costs you 60 seconds and saves you the one in twenty cases where "obvious"
turns out not to be.
