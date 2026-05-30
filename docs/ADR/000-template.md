# ADR-NNNN — <Short title in present tense, e.g. "Use append-only events for state">

> Status: proposed | accepted | superseded by ADR-MMMM | deprecated
> Date: YYYY-MM-DD
> Deciders: <names / handles>
> Supersedes: <ADR-XXXX, if any>

## Context

What are the forces in play? What constraints, requirements, or
observations led us here? What do we know — and crucially, what do we *not*
know? Include:

- The problem being solved (link to PRD / feature spec / issue).
- The constraints (NFR targets, compliance, deadlines, team skill, existing
  systems we must integrate with).
- The forces pulling in different directions (the genuine tradeoffs).
- The current state if changing it (what's there now and why it's not
  enough).

Be honest about uncertainty. "We don't yet know X" is valid context, not a
hole to paper over.

## Decision

State the decision in **one sentence first**, then describe the design.

> We will <verb> <object> <in this way>.

Follow with the design itself: data shapes, interfaces, components,
mechanism. Concrete enough that a sleep-deprived future-you can re-derive
the *why* from the artifact.

## Consequences

What becomes easy as a result? What becomes hard? What do we owe later?

- **Positive**: <what gets better, faster, safer>
- **Negative**: <what gets worse, slower, more constrained>
- **Neutral / deferred**: <work this decision creates that we'll do later>
- **Reversibility**: <how hard is this to undo if wrong? hours / days / months>

If this decision violates the engineering charter (`ENGINEERING.md`),
explain why and what mitigation is in place.

## Alternatives considered

At least two. "No alternative considered" is not acceptable — find one
even if it's obviously worse, to make the chosen path's reasoning
explicit. For each:

### Alternative 1 — <Name>

- **What it would look like:** <one paragraph>
- **Why not:** <the specific reason it was rejected, tied to the context>

### Alternative 2 — <Name>

- **What it would look like:** <one paragraph>
- **Why not:** <the specific reason>

## Accepted risks

🟡 Things the `critic` agent flagged that we're explicitly accepting (not
fixing now), with the conditions under which we'd revisit.

- <Risk> — accepted because <reason>. Revisit when <trigger>.

## Links

- PRD: <link>
- Related ADRs: <links>
- Related issues / PRs: <links>
- Architecture section affected: <doc link + section>
