---
name: phase-review
description: >-
  Comprehensive review at a milestone (end of an MVP phase, before a release,
  after a major architectural shift). Fans out reviewer, external-reviewer,
  and critic in parallel against the phase's aggregate diff and current state
  of the system. Consolidates findings, decides go/no-go, tags the milestone.
  Use whenever the project crosses a meaningful boundary.
---

# /phase-review — Milestone review

Run this when you've completed a build phase and are about to move on. The
goal is to *stop divergence*: catch where the project drifted from its
charter, its spec, or its design before you build the next thing on top.

## Step 1 — Define the phase

Be precise. The phase is bounded by two refs:

- `git tag phase-N-start` (or the previous phase tag, or a known commit)
- `HEAD` (or `git tag phase-N-end` once approved)

If those tags don't exist, create the `phase-N-start` tag pointing at the
phase's first commit before reviewing.

## Step 2 — Three reviews, in parallel

Spawn three subagents concurrently — they're independent and you want them
to disagree:

1. **`reviewer`** — full-context review of the aggregate diff. Does the
   phase deliver what the spec promised? Are all ADR commitments honoured?
   Are the docs current?
2. **`external-reviewer`** — fresh-context review of the aggregate diff.
   Would a new contributor be able to understand and extend this?
3. **`critic`** — red-team the *current state* of the system, not just the
   diff. What scaling assumptions are now load-bearing that weren't?
   What's the next failure mode? Where has the contract surface grown
   without anyone noticing?

## Step 3 — Cross-check the spec

Independent of the agent reviews, mechanically verify:

- [ ] `docs/PRD.md` claims match the phase's actual behaviour.
- [ ] `docs/ARCHITECTURE.md` reflects the system that was built (not the
      one we planned).
- [ ] Every ADR has been honoured; if any have been violated, an
      amendment ADR exists.
- [ ] `docs/CHANGELOG.md` covers every meaningful change in the phase.
- [ ] `docs/OPEN-QUESTIONS.md` is current — closed questions moved to
      ADRs, new ones logged.
- [ ] `docs/TODO.md` reflects what's actually done.

## Step 4 — Consolidate findings

`docs-keeper` writes a phase review entry into `docs/RED-TEAM.md`:

```
# Phase N review — YYYY-MM-DD

## What this phase delivered
<one paragraph against the spec>

## Reviewer findings
<reviewer's structured output>

## External-reviewer findings
<external-reviewer's structured output>

## Critic findings
<critic's structured output, with focus on state-of-system rather than diff>

## Spec/doc audit
<the checklist above, with notes on any drift found>

## Decision
GO | NO-GO | GO-WITH-FOLLOWUPS

## Followups (if go-with-followups)
- TODO T-NNN: <followup>
```

## Step 5 — Tag the milestone

If decision is GO:

```bash
git tag phase-N-end -m "Phase N complete: <one-line summary>"
git push origin phase-N-end
```

Update `docs/CHANGELOG.md` with the phase summary and version bump.

If NO-GO: stop forward work, address fatal findings, re-run phase review
when resolved.

If GO-WITH-FOLLOWUPS: tag and proceed, but the followups land in TODO with
real owners and dates — not "later".

## Cadence

- After every MVP phase.
- Before every release / deploy to a new environment.
- After any major architectural shift (new module, new external system,
  new tier transition).
- On a calendar cadence for long-running projects (e.g. every 4 weeks of
  active development).
