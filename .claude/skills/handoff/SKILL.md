---
name: handoff
description: >-
  Write HANDOFF.md so the next Claude session (or human) can resume in ten
  minutes. Run when the user signals end-of-session, context is filling up, or
  Claude Code is about to be /compact'd. The handoff captures current state,
  what was in flight, the next concrete step, open decisions, and recent
  learnings not yet in docs.
---

# /handoff — Resume-ready snapshot

Run this:

- When the user signals end-of-session ("let's stop for the day", "I have to
  go", "save the state").
- When context is filling up and you're about to `/compact`.
- Before any planned long break (overnight, weekend, deployment window).

A good handoff means the next session resumes in ten minutes. A bad handoff
means a fresh session reads twenty files to figure out where you left off.

## Step 1 — Reconcile state

Before writing the handoff:

- `git status` — what's uncommitted?
- `git diff --stat` — what's been touched this session?
- `docs/TODO.md` — does the in-progress task status match reality?
- `docs/OPEN-QUESTIONS.md` — is anything new that should be logged?

If TODO is out of sync with reality, fix it first. Don't write a handoff
that lies.

## Step 2 — Invoke docs-keeper to write HANDOFF.md

The docs-keeper writes `docs/HANDOFF.md` using this skeleton:

```
# HANDOFF — YYYY-MM-DD HH:MM <timezone>

## Current state in one paragraph
<what's done, what's in flight, what's blocked. Be specific —
"T-007 is in implementer; tests passing locally, lint clean, no PR yet"
beats "working on the event log thing">

## What I was doing when I stopped
<the exact task ID, exact branch, exact file/line if applicable>

## Next concrete step
<one sentence. Not "continue the work" — something a fresh session can
literally execute: "Run `pytest tests/test_event_log.py::test_replay`
and address the failure on line 47">

## Open decisions
- <bulleted, link to OPEN-QUESTIONS.md entries>

## Recent learnings (not yet in docs)
<one paragraph: things discovered this session — gotchas, library quirks,
correct invocations — that aren't yet in ADRs or ARCHITECTURE>

## Risks / red flags
<anything critic surfaced this session that hasn't been addressed>

## Files modified this session
\`\`\`
<paste `git status --short` output>
\`\`\`

## Suggested resume command
\`\`\`
cd <repo> && git checkout <branch> && claude
> read docs/HANDOFF.md and resume from "Next concrete step"
\`\`\`
```

## Step 3 — Commit and push the handoff

Doc changes ride with code, but a handoff is its own commit since it
deliberately captures state:

```bash
git add docs/HANDOFF.md docs/TODO.md docs/OPEN-QUESTIONS.md
git commit -m "handoff: end of session YYYY-MM-DD"
git push
```

If the branch is in-flight (uncommitted work that's not ready), include
that in HANDOFF.md and either:

- WIP-commit it (`git commit -m "WIP: <task>"`) and note the WIP commit in
  HANDOFF, or
- Stash it (`git stash push -m "<task> in flight"`) and note the stash
  ref in HANDOFF.

Don't leave a session with uncommitted work and no mention of it.

## Step 4 — Resume protocol

On a fresh session, the user (or Claude) does:

```
> read docs/HANDOFF.md
> read docs/TODO.md
> resume from "Next concrete step"
```

The session should be productive within ten minutes. If it's not, the
handoff was too thin — and that's a HANDOFF.md quality issue to fix.
