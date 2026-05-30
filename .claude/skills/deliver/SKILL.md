---
name: deliver
description: >-
  The end-to-end driver. Runs the whole framework from a one-line project idea
  through to a shipped, reviewed build — autonomously between a small set of
  human-decision checkpoints (brainstorm input, architecture sign-off, gate
  escalations). Pauses for genuine decisions and blockers, NOT for routine
  progress approval. Manages its own context with /checkpoint so it never hits
  a force-compact. Use this to kick off or resume a full project/feature build
  when you want the framework to run itself with you steering at the decision
  points.
---

# /deliver — End-to-end autonomous delivery

This is the conductor's score. It runs the full pipeline
(`society-of-minds → plan → forge-agents → decompose → execute → ship →
phase-review`) as one continuous flow, driven by the `pm-orchestrator`,
**stopping only at the human-decision checkpoints and true blockers below.**

The governing principle: **pause for decisions, not for permission.** Between
checkpoints, execute and report — do not ask "shall I continue?" after every
step. The user is steering at the forks, not approving every mile of road.

## The autonomy policy

### HARD STOP — wait for the user (these need human judgement)

1. **Brainstorm inputs** — at `/society-of-minds`: project goal, scope,
   constraints, and the scale/tier read. Ask, then run the panel.
2. **Brainstorm convergence** — present the recommendation + recorded dissent.
   The user picks the direction (or asks for another round).
3. **Architecture sign-off** — present PRD + ARCHITECTURE + ADR-0001. **Do not
   start building until the user approves the design.** This is the most
   important gate — everything downstream assumes it.
4. **Forged roster** — present the proposed specialist subagents from
   `/forge-agents` for a quick approve/trim (skip if none needed).
5. **Delivery plan** — present the validated critical path, parallel streams,
   and the hostile-review gate spec. A light confirm; proceed unless the user
   objects.
6. **Gate escalation** — any hostile clean-room gate that exceeds its loop
   budget. Stop, surface the open findings, let the user decide.
7. **Open question needing a human** — anything in `docs/OPEN-QUESTIONS.md`
   marked ⚖️ (expert/legal) or that genuinely needs a product/judgement call.
8. **Anything destructive or charter-bending** — force-push, history rewrite,
   data deletion, dropping a migration, or deviating from the validated plan.

9. **PR merge into the protected branch.** Opening the PR and getting CI green
   is autonomous; the *merge* is a checkpoint by default, because in a normal
   (team-mode) repo an agent cannot approve its own PR and branch protection
   requires a review. Two ways to run it:
   - **Team mode (default):** a human reviews and merges. The agent stops at
     "PR open, CI green, awaiting merge."
   - **Solo mode:** run `./scripts/setup-branch-protection.sh --solo` once —
     0 required approvals but CI/linear-history/conversation-resolution still
     enforced. Then the agent may merge its own green PR autonomously, and you
     can move `Bash(gh pr merge:*)` from `ask` to `allow` in settings. The gate
     becomes "green CI + review discipline" rather than "a second human".

### PROCEED AUTONOMOUSLY — do not ask permission

- The per-task loop: `tester` → assigned implementer/specialist → `reviewer`
  → `docs-keeper`, for every task on the plan.
- Running CI and opening PRs within branch protection. (Merging is checkpoint #9
  in team mode; autonomous only in solo mode.)
- Running the clean-room hostile gates **within** their loop budget.
- Moving between tasks; starting validated parallel streams in worktrees.
- All doc maintenance (CHANGELOG, TODO, DELIVERY-PLAN, ADRs).
- Routine commits/pushes on feature branches.
- `/checkpoint` (handoff + compact) — in fact, do this proactively; never ask.

**Where the orchestrator runs:** as the **main session**, not as a subagent.
It spawns short-lived worker subagents (tester, implementer, reviewers) whose
noisy context is discarded on return. This is deliberate — the session-level
context guard (statusline + nudge + PreCompact) only protects the main session,
and the orchestrator is the long-lived thing that needs protecting.

When in doubt between "this is a decision" and "this is progress", a decision
changes *what* gets built or *whether it's safe*; progress is just building the
already-decided thing. Stop for the former, fly through the latter.

## The run

```
1. HARD STOP 1–2  ── /society-of-minds
     Elicit goal/scope/constraints/tier → run the scale-calibrated panel →
     present convergence → user picks direction.

2. /plan
     architect drafts PRD + ARCHITECTURE + ADR-0001 from the brainstorm;
     critic red-teams the chosen design.
   HARD STOP 3 ── architecture sign-off. Wait for explicit approval.

3. /forge-agents
     Generate project specialists (or determine none are needed).
   HARD STOP 4 ── quick roster approve/trim.

4. /decompose
     task graph → critic (coupling) → critical-path & parallelism analysis →
     agent assignment → plan-critic validates & sets the gates →
     docs/DELIVERY-PLAN.md.
   HARD STOP 5 ── light confirm of the plan + gates.

5. EXECUTE (pm-orchestrator, bound by DELIVERY-PLAN.md) — AUTONOMOUS
     Loop over the critical path first, fan parallel streams to their assigned
     agents in worktrees, run per-task tester→implementer→reviewer→docs-keeper,
     /ship each through CI, and run the hostile clean-room gates at the
     designated milestones (within loop budget).
     • At every phase boundary: /phase-review, then continue.
     • Continuously: keep context under the threshold via /checkpoint.
     • Only surface to the user on HARD STOP 6–8.

6. On completion: final /phase-review (release gate), tag, update CHANGELOG,
   write a closing /handoff. Report what shipped.
```

## Context discipline during the run (so it never stalls)

The orchestrator must stay well below the compaction cliff — target under 60%:

- **Delegate aggressively.** Push heavy/noisy work (repo exploration, doc
  lookup, test runs, reviews) into short-lived subagents. The conductor's own
  context holds decisions and state, not raw output.
- **Checkpoint at seams.** Run `/checkpoint` at each phase boundary and
  whenever the context guard nudges (~60%). Checkpoint on your terms; never
  ride into a force-compact.
- **Trust the hooks.** `PreCompact` snapshots state and backs up the
  transcript; `SessionStart(compact)` re-injects the handoff. Even a surprise
  compaction is recoverable — but proactive checkpointing means you rarely
  test that backstop.

## Resuming a run

If a previous session ended (or compacted) mid-build:

```
> read docs/HANDOFF.md and docs/DELIVERY-PLAN.md
> /deliver   # resumes from the handoff's "Next concrete step"
```

The orchestrator re-grounds from the handoff + delivery plan and continues the
autonomous loop from where it left off, still bound by the plan and still
stopping only at the checkpoints above.

## Calibrate to scale

For a small project, the front-half collapses: the brainstorm is a short panel
(or skipped), there may be no forged agents, and the plan has one gate at the
end. The autonomy policy is unchanged — fewer stops, because there are fewer
genuine decisions. Don't manufacture checkpoints a small project doesn't have.
