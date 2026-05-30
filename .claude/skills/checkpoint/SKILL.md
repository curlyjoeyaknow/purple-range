---
name: checkpoint
description: >-
  Context hygiene in one step: reconcile state, write/refresh the handoff,
  commit it, and compact — proactively, before a force-compact. Triggered by
  the context guard when usage crosses the threshold (default 60%), and run
  manually at any natural pause. Keeps the pm-orchestrator and any long-running
  session well below the compaction cliff so nothing is ever lost. Use whenever
  context is getting full, before a long autonomous run, or at phase boundaries.
---

# /checkpoint — Proactive context hygiene

The framework's defense against losing state to a force-compact. Run it
proactively — the goal is to checkpoint *on your terms* at ~60% context, never
to be surprised by an auto-compact at 95%.

The context guard (`.claude/hooks/statusline.sh` + `checkpoint-nudge.sh`)
fires this automatically when usage crosses the threshold. You can also run it
by hand anytime.

## Steps

1. **Reconcile state.** Make `docs/TODO.md` and `docs/DELIVERY-PLAN.md` match
   reality — mark done what's done, note what's in flight. A handoff built on
   stale state is worse than none.

2. **Account for in-flight subagent work.** If you're the `pm-orchestrator`
   and have parallel streams running in worktrees, confirm each is either
   merged, WIP-committed (`git commit -m "WIP: <task>"`), or explicitly
   captured in the handoff. Nothing uncommitted-and-unmentioned.

3. **Write the handoff.** Invoke `docs-keeper` to write `docs/HANDOFF.md` per
   the `/handoff` skill — current state, what you were doing, the *next
   concrete step*, open decisions, recent learnings, risks, files touched.

4. **Commit and push.**
   ```bash
   git add docs/HANDOFF.md docs/TODO.md docs/DELIVERY-PLAN.md docs/OPEN-QUESTIONS.md
   git commit -m "checkpoint: handoff at ~<pct>% context"
   git push
   ```

5. **Compact (on a clean seam).** Run `/compact` if your Claude Code build
   lets the agent trigger it; otherwise say "ready to /compact" and let the
   user run it. Either way the seam is now clean: the `PreCompact` hook backs
   up the transcript and writes a mechanical snapshot, and the
   `SessionStart(compact)` hook re-injects the handoff afterward. The value of
   checkpointing at ~60% is that *you* chose the seam (a task boundary, fresh
   handoff) — not that the agent necessarily self-compacts. Even an auto-compact
   from here is lossless because the handoff is current.

6. **Resume** from the handoff's "Next concrete step" — no momentum lost.

## Why 60% and not 95%

Auto-compaction near the limit is abrupt and lossy: it can land mid-reasoning,
mid-task, mid-tool-call. Checkpointing at ~60% means you choose the seam — at
a task boundary, with a clean handoff — and keep ~40% headroom for the
re-grounding context the restore hook injects. For the `pm-orchestrator`,
which runs longest, this is the difference between a smooth multi-session build
and a project that periodically forgets what it was doing.

## Note on subagents and where the orchestrator runs

These hooks operate at the **session** level, and a subagent runs in its own
context window the hooks can't see. The resolution (see FRAMEWORK.md): **run
the `pm-orchestrator` as the main session**, and have *it* spawn short-lived
worker subagents (tester, implementer, reviewers). That way the session-level
context guard protects the long-lived conductor — the thing actually at risk —
while the workers' noisy context is discarded when they return. The 60% target
is enforced for the orchestrator precisely because it is the main session.
