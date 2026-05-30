# BRAINSTORM — <Project / Feature Name>

> Produced by `/society-of-minds`. This is the multi-perspective brainstorm
> that seeds `/plan`. It is a *recommendation*, not a spec.
> Date: YYYY-MM-DD

## Scale read

**Assessed scale:** trivial | small | medium | large
**Session shape run:** <panel size, rounds, depth — e.g. "4 perspectives,
full 4 rounds, one convergence pass">

<One line justifying the scale read — what about the project put it here.>

## The panel

| Perspective | Optimizes for | Suspicious of |
|---|---|---|
| <e.g. Data/state> | <correctness, rebuildability> | <premature denormalization> |
| <e.g. API/contract> | <stable, versioned interfaces> | <leaky coupling> |
| <e.g. Security> | <least privilege, trust boundaries> | <implicit trust> |
| <e.g. Cost/ops> | <run cost, operability> | <infra we can't afford to run> |
| … | … | … |

## Round 1 — Feasibility

| Perspective | Biggest feasibility risk | Showstopper / Cost / Non-issue |
|---|---|---|
| … | … | … |

**Verdict:** go | go-with-conditions | reconsider
**Conditions (if any):** …

## Round 2 — Ideal architecture (per domain)

<Each perspective's proposed design for its slice, with the contract/port
that connects it to the rest. Every piece of complexity justified against
the scale.>

## Round 3 — Red-team (perspectives attacking each other's proposals)

| Risk raised | Against | Severity | Candidate mitigation |
|---|---|---|---|
| 🔴 … | <proposal> | … | … |
| 🟠 … | <proposal> | … | … |

## Round 4 — Cost/benefit of competing approaches

| Approach | Build cost | Run cost | Complexity carried | Reversibility | Verdict |
|---|---|---|---|---|---|
| A — … | … | … | … | … | recommended / rejected |
| B — … | … | … | … | … | … |

## Recommended architecture sketch

**Tier:** small | medium | large (justified above — not defaulted)

<The converged design. Confirm the minimum patterns are present even at the
smallest scale:>

- [ ] **Append-only event logging** — at minimum <JSONL file / one `events`
      table>.
- [ ] **Ports & adapters** at each domain boundary — at minimum one interface
      + one fake per boundary.
- [ ] **Versioned contracts** — `version` field on persisted shapes.

<Anything above the minimum is listed here WITH the scale pressure that
justifies it. If there's no such pressure, it's not in the design.>

## Top risks + mitigations (ranked)

1. 🔴 <risk> → <mitigation, owner-able>
2. 🟠 <risk> → <mitigation>
3. 🟡 <risk> → <mitigation>

## Recorded dissent

<Where panellists still disagree after convergence. Don't paper over — these
often become the first ADRs.>

- <Perspective X> still favours <approach> over the recommendation because
  <reason>. To revisit if <trigger>.

## Open questions → OPEN-QUESTIONS.md

- Q-NNN: <unresolved decision that needs more info or a human>

## Hand-off

Next: `/plan` — the architect turns this recommendation into PRD +
ARCHITECTURE + ADR-0001, and `critic` red-teams the *chosen* design.
