# PRD — <Project Name>

> Status: draft | in-progress | shipped
> Last updated: YYYY-MM-DD

## Problem

<One paragraph. Who has the problem, what is it, why does it matter, what
happens if it's not solved.>

## Audience

<Who this is for. Be specific — "developers" is not specific; "Python
backend developers integrating webhooks at small SaaS companies" is.>

## Goals (and non-goals)

### Goals
- <Functional outcome 1>
- <Functional outcome 2>

### Non-goals (explicit out-of-scope)
- <Thing we are deliberately not doing>
- <Adjacent capability that's tempting but out of scope>

## Success criteria

How will we know this works?

- **Functional:** <observable behaviour that proves the goal is met>
- **Performance / NFR:** <p95 latency, throughput, durability, etc.>
- **Adoption / outcome:** <measure that ties to the audience's problem>

## Constraints

- **Hard:** <compliance, deadline, integration mandate>
- **Soft:** <team size, budget, preferred stack>

## Tier

**Tier:** small | medium | large

See `ENGINEERING.md` for what tier means in plumbing terms. Tiering at this
stage sets the depth of the event log, contract catalog, and adapter layer.

## Scope (MVP)

<The smallest thing that delivers the success criteria. Anything beyond
this is a follow-up. If "MVP" looks like "everything", split it.>

## Open questions

Track these in `docs/OPEN-QUESTIONS.md` and link from here. Don't make
silent assumptions.

## Related

- Architecture: `docs/ARCHITECTURE.md`
- Initial ADR: `docs/ADR/0001-initial-architecture.md`
- Build plan: `docs/TODO.md`
