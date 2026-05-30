---
name: plan
description: >-
  Spec-driven kickoff for a new project or feature. Asks for goal, tier, stack,
  and constraints; runs the architect to draft PRD + ARCHITECTURE + ADR-0001;
  runs the critic to red-team the design; runs docs-keeper to finalize. Use at
  the start of any new project or any non-trivial feature.
---

# /plan — Spec-driven planning

Run this at the start of any new project or any non-trivial feature —
ideally right after `/society-of-minds`, whose converged recommendation
(`docs/BRAINSTORM-*.md`) seeds the architect's work here.

Pipeline position:
`/society-of-minds` → **/plan** → `/forge-agents` → `/decompose` → execution.

## Step 1 — Elicit the inputs

If `/society-of-minds` ran, most of this is already captured in
`docs/BRAINSTORM-*.md` — read it first and only ask the user for gaps.
Otherwise, gather these from the user. Ask in one block, not one at a time:

1. **Goal in one sentence.** What does this project/feature *do* for *whom*?
2. **Success criteria.** How will we know it works? (Functional + NFRs.)
3. **Tier** — small / medium / large. Reference `ENGINEERING.md` for what
   each tier means in plumbing terms.
4. **Stack & deployment context.** Language, framework, runtime, where it
   runs (server, edge, device), what it must integrate with.
5. **Hard constraints.** Compliance, data residency, deadlines, team size,
   any "this must use X" mandates.
6. **What's deliberately out of scope.** Just as important as in-scope.

If the user can't answer one of these, that's an OPEN-QUESTION — log it and
proceed with the rest. Don't invent answers.

## Step 2 — Architect drafts the spine

Invoke the `architect` agent with the elicited inputs. They produce:

- `docs/PRD.md` from the template.
- `docs/ARCHITECTURE.md` from the template, sized to the tier.
- `docs/ADR/0001-initial-architecture.md`.
- `docs/OPEN-QUESTIONS.md` with anything the user couldn't answer.

## Step 3 — Critic red-teams the spine

Invoke the `critic` agent on the architect's output. They look for:

- Unstated assumptions about scale, security, failure modes.
- Premature optimization or premature generalization.
- Contracts that lack a `version` field or validation gate.
- Ports/adapter violations (vendor SDKs leaking into business logic).
- Missing observability story.

If critic returns 🔴 fatal findings, return to architect — do not paper over.

## Step 4 — Docs-keeper finalizes

Invoke the `docs-keeper` agent to:

- Ensure all doc cross-links are in place.
- Initialize `docs/TODO.md` with the high-level milestones.
- Initialize `docs/CHANGELOG.md` with the project bootstrap entry.
- Initialize `docs/RED-TEAM.md` with the critic's findings (resolved + open).
- Update `README.md` with status, quickstart, and links to the docs above.

## Step 5 — Commit the bootstrap

```bash
git add docs/ README.md CLAUDE.md ENGINEERING.md
git commit -m "spec: initial PRD, architecture, ADR-0001, charter"
```

## Step 6 — Hand off to /forge-agents, then /decompose

The plan is the spine. Next, forge the project-specific specialist subagents
the architecture calls for, *then* decompose into a build order assigned to
those specialists:

```
> /forge-agents      # create the project's domain specialists (skip if none needed)
> /decompose         # task graph → critical path → assignments → plan-critic gates
```

For a small project that needs no forged specialists, `/forge-agents` will
say so quickly and you go straight to `/decompose`.

## Notes

- This skill always produces docs, never code. Code starts at the first
  task `implementer` picks up.
- If the user is adding a *feature* to an existing project (not a new
  project), skip PRD/ARCHITECTURE creation; instead, update the relevant
  sections of the existing docs and write a feature spec at
  `docs/features/<slug>.md`. ADR is still mandatory if a non-obvious choice
  is made.
- The tier choice isn't permanent. Re-tier when complexity demands; the
  patterns don't change, only the plumbing.
