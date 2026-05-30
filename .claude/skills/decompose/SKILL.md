---
name: decompose
description: >-
  Convert a spec (PRD or feature doc) into a task graph, then analyze the
  critical path and parallel-development opportunities FIRST, assign the
  best-suited agents (generic or project-forged) to each task, and finish by
  having plan-critic validate the whole plan and designate the hostile-review
  gates. Run after /plan and /forge-agents, after any architecture change, or
  whenever scope shifts. The output (docs/TODO.md + docs/DELIVERY-PLAN.md) is
  what binds the pm-orchestrator.
---

# /decompose — Spec → validated, assigned, gated build plan

Run after `/plan` and `/forge-agents`. Turns the plan into a buildable order
that the `pm-orchestrator` can execute with maximum safe parallelism.

This skill produces two artifacts:
- `docs/TODO.md` — the task graph (the *what*).
- `docs/DELIVERY-PLAN.md` — the validated critical path, parallel streams,
  agent assignments, and hostile-review gates (the *how fast and how safe*).

## Step 1 — Confirm the spec is current

Glance at `docs/PRD.md`, `docs/ARCHITECTURE.md`, `docs/BRAINSTORM-*.md`, and
any existing `docs/TODO.md`. If the spec is stale, stop and run `/plan` to
refresh it — decomposing on a stale spec just spreads the staleness.

## Step 2 — Decomposer builds the raw task graph

Invoke the `decomposer` agent. It produces tasks with: dependencies, contract
surface, testable acceptance criteria, test plan, effort tier — blockers
first, with `[BLOCKER | CRITICAL | PARALLEL]` tags.

## Step 3 — Critic checks for hidden coupling

Invoke `critic` specifically to find **false parallelism**: tasks marked
parallel that actually share a contract surface, file set, or migration. If
found, either resequence to serial or add a blocker task that locks the shared
contract first (prefer the latter — it *creates* real parallelism).

## Step 4 — Analyze critical path and parallel opportunities FIRST

Before assigning anyone to anything, work out the shape of the build:

1. **Derive the critical path.** The longest dependency chain. Re-derive it
   from the graph; don't trust labels. Note the bottleneck tasks — where a
   day of slip is a day of project slip.
2. **Find the real parallel streams.** Sets of tasks that are genuinely
   independent (disjoint contract surfaces *and* file sets). These are your
   speed multipliers — they run alongside the critical path, soaking up
   slack.
3. **Front-load the blockers.** Shared contracts and ports go first so the
   streams can fan out as early as possible.
4. **Identify near-critical streams.** Streams with little slack that would
   *become* the critical path if they slipped — these need monitoring.

The goal: **maximize parallel throughput without ever lengthening the
critical path.** Parallel work fills the gaps; it never pulls an agent off a
critical-path task.

## Step 5 — Assign the best-suited agent to each task

Map every task to the agent best suited to it — generic roster or the
specialists `/forge-agents` created:

- Match by specialization: the `react-frontend-implementer` gets UI tasks,
  the `postgres-schema-architect` gets schema tasks, etc.
- Match by phase: `tester` writes failing tests first on every task;
  `implementer`/specialist makes them pass; `reviewer` reviews.
- Watch for over-subscription: if one specialist is assigned three
  consecutive critical-path tasks, that's a hidden serialization — flag it
  for a second specialist (forge one) or resequence.
- Assign parallel streams to *different* agents so they can actually run at
  once.

Record assignments against each task.

## Step 6 — Plan-critic validates and sets the gates (MANDATORY, before execution)

Invoke the `plan-critic` agent. This is the gate before the orchestrator
runs. It:

- Re-derives and validates the critical path; confirms parallelism is real;
  corrects false concurrency.
- Sanity-checks agent assignments (suitability + over-subscription).
- **Designates the hostile-review gates**: which milestones get a clean-room
  hostile review, each gate's difficulty (`light`/`standard`/`hard`/
  `adversarial`), and the loop budget — scaled to each milestone's blast
  radius and irreversibility. High-stakes/irreversible/high-fan-out
  milestones get hard gates; cheap reversible work gets none.
- Enforces that every gate runs via the `clean-room-reviewer` in a **fresh
  subagent context** — unbiased, uncontaminated by build context.

`plan-critic` writes `docs/DELIVERY-PLAN.md` (via `docs-keeper`) using
`docs/DELIVERY-PLAN.template.md`. If it finds the plan unsound, it returns to
the decomposer — do not start execution on an unvalidated plan.

## Step 7 — Docs-keeper files TODO.md and DELIVERY-PLAN.md

`docs-keeper` writes the task graph to `docs/TODO.md` and the validated
delivery plan to `docs/DELIVERY-PLAN.md`. Existing in-flight tasks keep their
status.

## Step 8 — Commit

```bash
git add docs/TODO.md docs/DELIVERY-PLAN.md
git commit -m "plan: decompose, validate critical path, assign agents, set review gates"
```

## Step 9 — Create worktrees for the validated parallel streams

For each genuinely independent stream in DELIVERY-PLAN.md:

```bash
git worktree add ../this-repo-stream-a stream-a
git worktree add ../this-repo-stream-b stream-b
```

## Step 10 — Hand off to the pm-orchestrator

The orchestrator is now *bound* by `docs/DELIVERY-PLAN.md`: it executes the
critical path first, fans parallel streams out to their assigned agents in
worktrees, never sacrifices the critical path for parallel work, and runs the
designated clean-room hostile reviews at each gate with the specified
difficulty and loop budget.

```
> use the pm-orchestrator to begin execution per docs/DELIVERY-PLAN.md
```
