# DELIVERY-PLAN — <Project Name>

> Produced by `/decompose` → validated and gated by the `plan-critic` agent.
> The `pm-orchestrator` is **bound** by this document. If reality diverges,
> re-run `/decompose` to re-validate — don't improvise around it.
> Last validated: YYYY-MM-DD

## Validated critical path

```
T-001 → T-003 → T-007 → T-011 → done
```

**Bottleneck tasks** (a day of slip here = a day of project slip):
- T-003 — <why: e.g. shared event contract everything depends on>
- T-007 — <why>

## Near-critical streams (monitor — would become the critical path if slipped)

- Stream B (T-005, T-008): ~1.5 days slack. Rebalance toward it if it slips.

## Validated parallel streams + agent assignments

> Each stream runs concurrently in its own worktree. Assignments are to the
> agent best-suited to the task (generic roster or `/forge-agents` specialist).

| Stream | Tasks → Agent | Parallel-safe because | Worktree |
|---|---|---|---|
| A | T-002 → `frontend-implementer`, T-004 → `api-implementer` | disjoint contract surfaces (foo / bar), disjoint files | `../proj-stream-a` |
| B | T-005, T-008 → `pipeline-implementer` | disjoint from A; serial within B | `../proj-stream-b` |
| Serial | T-009 → `integration-implementer` | depends on Stream A landing | main |

## Corrections plan-critic made to the decomposer's draft

- Downgraded T-006 ↔ T-008 from parallel to serial (shared `events` table
  migration — false concurrency).
- Added blocker **T-000b**: lock the `EventEnvelope` contract before Stream A
  fans out, so A's tasks become genuinely parallel.
- Flagged `api-implementer` over-subscribed on the critical path (T-003,
  T-007, T-011) → recommend forging a second API specialist OR resequencing
  T-011 off the critical path.

## Hostile-review gates

> Every gate runs via the `clean-room-reviewer` agent in a **fresh subagent
> context** — given only the artifact + its acceptance spec, no project lore.
> Difficulty and loop budget are scaled to blast radius and irreversibility.

| Milestone | After task(s) | Why gated | Difficulty | Loop budget | Reviewers |
|---|---|---|---|---|---|
| M1 — contract spine locked | T-000b, T-003 | high fan-out, hard to change later | `hard` | 3 | 1× clean-room |
| M2 — auth boundary | T-007 | security blast radius, irreversible | `adversarial` | 4 | 2× clean-room (independent) |
| M3 — MVP integration | T-011 | release gate | `standard` | 2 | 1× clean-room |

Difficulty legend: `light` (advisory) · `standard` (address 🔴/🟠) ·
`hard` (address all + re-review) · `adversarial` (multiple independent
reviewers must all PASS).

## Escalation rule

If any gate exceeds its loop budget without a PASS, **stop forward work on
that milestone's dependents** and escalate to a human decision with the open
findings attached. Looping past budget is its own failure mode.

## Scale note

Project tier: **<small | medium | large>**. This plan's machinery (number of
gates, parallel streams, worktrees) is sized to that tier. Re-validate if the
tier changes.
