---
name: external-check
description: >-
  Run a fresh-context review on the current diff using the external-reviewer
  agent. The reviewer deliberately ignores most project context and reports
  what's confusing from the outside — naming, leaky abstractions, mismatched
  PR descriptions, onboarding friction. Use on non-trivial PRs after the
  internal reviewer has signed off.
---

# /external-check — Fresh-eyes review

Use this on non-trivial changes after `reviewer` has signed off. The internal
reviewer has full project context and will miss what's obvious to an
outsider. This skill catches that gap.

## Step 1 — Stage the diff

The external-reviewer agent reads **only**:

1. The diff (`git diff main...HEAD` or the PR diff).
2. The PR description.
3. At most one or two docs the PR description explicitly points at.

That's it. Do **not** pre-load CLAUDE.md, ENGINEERING.md, or the rest of
ARCHITECTURE for this agent — the point is to be the outsider.

If the PR doesn't have a description yet, write one now. A reviewer who
can't read the PR description hasn't been given a fair shot.

## Step 2 — Invoke external-reviewer

The agent produces the structured outsider report:

- What it thinks the change does (from the diff alone).
- What it had to guess to understand it.
- Naming / readability concerns.
- Leaky abstractions or hidden context.
- Mismatch between PR description and diff.
- "If I had to maintain this in 6 months…" — the onboarding-friction paragraph.

## Step 3 — Triage and act

Outsider findings tend to be one of three categories:

1. **Things only an outsider sees.** Confusing names, missing comments,
   implicit context. Almost always worth fixing — they're cheap to fix and
   the cost of not fixing compounds with every new contributor.
2. **Things the outsider got wrong because of missing context.** Don't
   dismiss these — they're a signal that *the docs* are missing context.
   Update the relevant doc, not the code.
3. **Project conventions the outsider questioned.** If the convention is
   load-bearing, link the outsider's report to the ADR that establishes it
   (and consider whether the ADR needs to be more discoverable).

## Step 4 — Append to PR

Paste the report into the PR thread (or attach as a review comment). It
helps future contributors and trains the team's eye for the same issues.

## When to skip

For trivial changes (docs-only, dependency bumps, single-line fixes) the
internal reviewer is sufficient. Anything that:

- introduces a new module
- changes a public contract
- adds a new external dependency
- changes a workflow or build step

…should run through external-check.

## CI integration

This skill is also automated in `.github/workflows/external-review.yml` — a
fresh Claude session runs it on every PR open/update. The CI version is a
safety net; this command is the in-session check during development.
