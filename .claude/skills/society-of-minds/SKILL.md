---
name: society-of-minds
description: >-
  Multi-perspective architecture brainstorm. Run this FIRST when discussing a
  new project or a major feature, before /plan. Convenes a scale-appropriate
  panel of specialized domain-architect perspectives to debate the project
  from several angles: feasibility, ideal architecture per domain, red-teaming
  for risks + mitigations, and cost/benefit of competing approaches. Calibrates
  the size of the panel and the depth of debate to the project's actual scale —
  a small tool gets a short, cheap session; a large system gets a deep one.
  Anti-over-engineering by design. Converges to a recommendation that seeds the
  PRD and architecture. Use whenever a project plan, system design, or "how
  should we build this" question is on the table.
---

# /society-of-minds — Multi-domain brainstorm

The first move on any non-trivial project. Before committing to a design, put
the idea in front of a panel of specialists who each see a different part of
the elephant, let them argue, and converge on a recommendation.

The output seeds `/plan`. It is *discussion and recommendation*, not code and
not a final spec.

## Step 0 — Calibrate to scale (do this before convening anyone)

The single most important input. Read the project intent and place it:

| Scale read | Panel size | Rounds | Depth |
|---|---|---|---|
| **Trivial / throwaway** | Skip the panel. One architect + one critic pass. | — | Minutes. |
| **Small** (one service, one data store, modest load) | 2–3 perspectives | Feasibility + a single combined arch/risk round | Short. |
| **Medium** (several modules, real users, integrations) | 3–5 perspectives | Feasibility → architecture → red-team → cost/benefit | Moderate. |
| **Large** (distributed, high scale, compliance, multi-team) | 5–7+ perspectives | All rounds, multiple convergence passes, explicit dissent capture | Deep. |

State your scale read and the resulting session shape to the user before
running it. If they disagree, re-calibrate. **Do not run a large-system
brainstorm for a small-system problem** — it wastes time and tends to
manufacture complexity the project doesn't need.

## Step 1 — Compose the panel (domains chosen to fit the project)

The perspectives are *not* a fixed list — pick the domains that actually
matter for this project. Heuristics for choosing:

- Always consider: **data/state modelling**, **the primary runtime/execution
  domain**, **security & trust**, **cost & operability**.
- Add domain experts the project actually implicates, e.g.:
  - Web app → frontend/UX, API/contract design, auth, data, infra/cost.
  - Data pipeline → ingestion, storage/modelling, processing, reliability, cost.
  - Embedded/realtime → timing/concurrency, power/resource, safety, OTA update.
  - ML system → data/labelling, training/eval, serving/latency, drift/monitoring.
  - CLI/library → API ergonomics, packaging/distribution, backward-compat.

Compose each panellist as a short expert brief (name, domain, what they
optimize for, what they're suspicious of). Spawn each as a **parallel
subagent** so their reasoning runs in a separate context and doesn't
groupthink within one transcript. (On Claude.ai with no subagents, role-play
them in sequence instead.)

**Be honest about what this is:** these are one model wearing different hats,
not a panel of independent experts. The value is that diverse prompts force
*considerations* that a single pass would skip — the security frame catches
what the cost frame misses — not that you're getting genuinely uncorrelated
judgement. Treat "recorded dissent" as "angles worth keeping visible", and
when a decision is high-stakes enough to need real independence, route it to a
human expert via an OPEN-QUESTION rather than trusting the panel's consensus.

You may persist especially useful panellist briefs, but they're usually
ephemeral — the *implementation* specialists get forged later by
`/forge-agents`.

## Step 2 — Run the rounds

Each round, every panellist contributes from their domain; then you (the
facilitator) synthesize and surface the disagreements.

1. **Feasibility.** Can this be built as imagined, with the stated
   constraints (time, team, stack, budget)? Each panellist names the single
   biggest feasibility risk in their domain and whether it's a showstopper,
   a cost, or a non-issue.
2. **Ideal architecture (per domain).** Each panellist proposes the *right*
   design for their slice — and must justify every piece of complexity
   against the project scale (see the guardrail below). They sketch the
   contract/port that connects their slice to the rest.
3. **Red-team.** Panellists attack *each other's* proposals — failure modes,
   coupling, scaling cliffs, security holes, operational pain. Every risk
   raised must come with a candidate mitigation (or an explicit "no good
   mitigation — avoid this approach").
4. **Cost/benefit of competing approaches.** Where panellists proposed
   different paths, lay them side by side: build cost, run cost, complexity
   carried, optionality preserved, reversibility. Recommend per axis.

For small projects, collapse rounds 2–4 into one combined pass. For large
ones, run a second convergence pass after red-team to re-cost the survivors.

## Step 3 — The anti-over-engineering guardrail (binding on every panellist)

Complexity must be *earned by the project's scale*. The facilitator rejects
any proposal that adds infrastructure the project doesn't need yet. Defaults:

- **Bare minimum, always present, even at the smallest scale:**
  - **Append-only event logging** — even if that's a single JSONL file or one
    `events` table. It's nearly free and it's the expensive thing to retrofit.
  - **Ports & adapters at each domain boundary** — even if that's one
    interface and one fake. It just names a seam you'd create anyway.
  - **Versioned contracts** — a `version` field on persisted shapes.
- **Everything above the minimum must justify itself.** Kafka, CQRS read
  models, service meshes, multi-region, event upcasters, registries — these
  are *large-tier* plumbing. If someone proposes them for a small/medium
  project, they must show the specific scale pressure that demands it. Absent
  that, the recommendation is the simplest thing that satisfies the patterns.
- When in doubt, recommend the **lower tier** and note the trigger that would
  justify moving up. Re-tiering later is cheap *because* the patterns were
  there from day one.

## Step 4 — Converge and record

Synthesize into a recommendation and hand to `docs-keeper` to file at
`docs/BRAINSTORM-<slug>.md` using `docs/BRAINSTORM.template.md`:

- **Feasibility verdict** — go / go-with-conditions / reconsider, with the
  conditions.
- **Recommended architecture sketch** — the converged design, at the tier the
  panel justified (small/medium/large), with the minimum patterns present.
- **Top risks + mitigations** — ranked, each with an owner-able mitigation.
- **Cost/benefit summary** — the competing approaches and why the recommended
  one won.
- **Recorded dissent** — where panellists still disagree, capture it (don't
  paper over). These often become the first ADRs.
- **Open questions** — anything unresolved → `docs/OPEN-QUESTIONS.md`.

## Step 5 — Hand off to /plan

The brainstorm is the input to planning, not a substitute for it:

```
> /plan
```

`/plan`'s architect reads `docs/BRAINSTORM-<slug>.md`, turns the converged
recommendation into the PRD + ARCHITECTURE + ADR-0001, and the `critic` then
red-teams *that* (a different job from the panel's red-team round — the panel
attacked options; the critic attacks the chosen design).

## When to skip

- Trivial/throwaway work — go straight to `/plan` (or just build it).
- A feature whose design is already settled by an existing ADR — no new
  decision to brainstorm.

For everything with a genuine "how should we build this?" question, run it.
The session is scaled to the stakes, so for a small project it costs minutes.
