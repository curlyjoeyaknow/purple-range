# HANDOFF — YYYY-MM-DD HH:MM <timezone>

> Written by the `docs-keeper` agent when `/handoff` is invoked.
> Goal: a fresh Claude session (or human) resumes here in ten minutes flat.

## Current state in one paragraph

<What's done, what's in flight, what's blocked. Be specific.
"T-007 is in `implementer`; tests passing locally, lint clean, no PR yet"
beats "working on the event log thing".>

## What I was doing when I stopped

- **Task:** T-NNN — <short name>
- **Branch:** `<branch-name>`
- **Worktree:** `<path, if applicable>`
- **File / line, if mid-edit:** `<path>:NN`
- **Last command run:** `<the exact command>`

## Next concrete step

<One sentence. Not "continue the work" — something a fresh session can
literally execute. For example: "Run `pytest tests/test_event_log.py::test_replay`
and address the `AssertionError: expected version 2, got 1` on line 47.">

## Open decisions

- <Bulleted, link to `docs/OPEN-QUESTIONS.md` entries.>
- <Each item names the trigger that would unblock it.>

## Recent learnings (not yet in docs)

<One paragraph: things discovered this session — library quirks, correct
invocations, surprising behaviour — that aren't yet in ADRs or
ARCHITECTURE. Promote the load-bearing ones to docs before next session.>

## Risks / red flags

<Anything `critic` surfaced this session that hasn't been addressed.
Reference the `docs/RED-TEAM.md` entry.>

## Files modified this session

```
<paste `git status --short` output here>
```

## Suggested resume command

```bash
cd <repo>
git checkout <branch>
# If there's stashed work:
git stash list   # → 'stash@{0}: <task> in flight'
# git stash pop  # only after reading this HANDOFF in full

claude
> read docs/HANDOFF.md and resume from "Next concrete step"
```

## Session metadata

- **Started:** YYYY-MM-DD HH:MM
- **Ended:** YYYY-MM-DD HH:MM
- **Commits this session:** `<N>` (range: `<first-sha>..<last-sha>`)
- **PRs opened/closed:** <list>
- **ADRs added:** <list>
