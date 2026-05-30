# TODO — <Project Name>

> Updated by the `docs-keeper` agent. Format matches `decomposer` output.

## Status legend

- `ready` — no unmet dependencies; can be picked up.
- `in-progress` — being worked on; check the branch.
- `blocked-on-X` — waiting on another task ID.
- `review` — implementation done; in code review.
- `done` — merged.

## Critical path

```
T-001 → T-003 → T-007 → T-011 → done
```

Re-derive this whenever the architecture shifts or a task is reordered.

## Parallel streams (worktree fan-out candidates)

- **Stream A**: T-002, T-004, T-006 — contract surface: `<foo, bar>`
- **Stream B**: T-005, T-008 — contract surface: `<baz>`
- **Serial**: T-009 depends on Stream A landing

## Tasks

### Phase 1 — <name>

- [ ] **T-001  <short name>**  `[BLOCKER]`
  - Depends on: none
  - Contract surface: <types/ports touched; new ones introduced>
  - Acceptance:
    - <testable condition>
    - <testable condition>
  - Test plan: <which tests are written first, against what fake>
  - Effort: XS | S | M | L
  - Worktree-safe with: <list of other task IDs>
  - Status: ready
  - Owner: <if assigned>

- [ ] **T-002  <short name>**  `[CRITICAL]`
  - Depends on: T-001
  - …

- [ ] **T-003  <short name>**  `[PARALLEL]`
  - Depends on: T-001
  - …

### Phase 2 — <name>

…

## Followups (not blockers; from `/critique` and `/phase-review`)

- [ ] **F-001** — <one-line>
  - Source: RED-TEAM.md entry YYYY-MM-DD
  - Severity: 🟠 | 🟡
  - Trigger: <when this becomes blocking>

## Done

Move tasks here when merged, keep the ID for traceability.

- [x] **T-000  Bootstrap** — merged YYYY-MM-DD in <PR link>
