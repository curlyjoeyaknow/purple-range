# ENGINEERING.md — Spec-Driven Delivery Charter

The bet: a small set of patterns, adopted from commit one, removes the
compounding tax of rework, drift, vendor lock-in, and "what does this even do
now" — so each change is cheaper than the last.

The expensive part of these patterns is **retrofitting** them — event-sourcing
a mutable app, adding a `version` field after data is live, extracting a port
after a vendor SDK is wired through everything. Adopt them day one and the
incremental cost is small while the payoff compounds.

## The principle: patterns are the default; only the plumbing scales

What scales with project size is **how much plumbing** sits under the patterns,
not **whether** you use them.

- **Adopt the patterns by default** on anything that persists state or crosses a
  boundary.
- **Dial the plumbing** to the project's depth (see Tiers, below).

### Narrow exceptions where it's fine to skip a pattern

- **No persisted state** — a pure input→output transform: nothing to event-source.
- **No external boundary** — no API/DB/vendor: no port worth abstracting.
- **Truly throwaway** — deleted tomorrow: version control + real tests, move on.

Outside these, default to the patterns. "Almost every project" is the bar.

## The default patterns

1. **Append-only events, derived state.** Treat persisted change as an
   append-only log of facts; compute state by folding the log. You get audit,
   rebuild ("replay the log"), undo, and debugging nearly for free. Scales
   down to a JSONL file or one `events` table — barely more than CRUD.

2. **Contracts first, versioned.** Define data/event/API shapes — names,
   types, required/optional, a **version field**, one **validation gate** —
   *before* building on them. The version field is free now and unbuyable
   later. Systems add **lineage** (correlation/causation IDs).

3. **Ports & adapters at every boundary.** Depend on an interface; put the
   vendor SDK / DB / API behind an adapter; test with a fake at the boundary.
   It just *names a seam you were going to create anyway*.

4. **Decisions → ADRs.** Every non-obvious choice gets a short record:
   context, decision, consequences, alternatives. Future-you needs the *why*.
   Template in `docs/ADR/000-template.md`.

5. **TDD with honest tests.** Test first; never mock the unit under test;
   fakes only at boundaries. A test that asserts implementation rather than
   behaviour is a design smell — redesign, don't extend the mock.

6. **Git discipline.** Branch per feature, small commits with *why* in the
   message, version major changes, push often. Worktrees for genuinely
   parallel tracks (`git worktree add ../proj-feature-x feature-x`).

7. **Spec before code & a derived build order.** Goals → PRD → MVP →
   feature specs; decompose, draw the dependency graph, walk the
   **critical path** (re-derive it when the architecture changes).

8. **Changelog + open-questions log; current docs.** Log every change in
   `docs/CHANGELOG.md`. Track unresolved decisions and expert/legal
   checkpoints in `docs/OPEN-QUESTIONS.md`. Look up live dependency docs
   rather than trusting stale memory.

## Scale the plumbing, not the posture

Same patterns, more or less machinery as depth grows:

| Pattern | Small | Medium | Large |
|---|---|---|---|
| Event log | JSONL / one append table | partitioned files + projections module | partitioned Parquet lake + compaction + rebuild jobs |
| Contracts | typed model + `version` field | catalog of types + validation gate | full catalog + upcasters + registry + lineage |
| Ports/adapters | 1 interface + a fake | a few adapters | adapter registry + many providers |
| Rebuildable state | re-run the fold | projection module | materialized read-models + scheduled rebuild |

Pick the tier at `/plan` time. Re-tier when complexity demands; the patterns
don't change, only their plumbing.

## The artifact set a project accumulates

```
docs/
  PRD.md                    PRD + MVP scope
  ARCHITECTURE.md           system design + event/contract catalog
  ADR/                      ADR-001 … ADR-N
  TODO.md                   live task graph + status
  CHANGELOG.md              what changed and when
  OPEN-QUESTIONS.md         unresolved decisions; expert checkpoints
  RED-TEAM.md               risk reviews from /critique and /phase-review
  HANDOFF.md                snapshot for the next session
README.md                   repo map + quickstart + status
```

## Posture

- **Honest advisor.** Push back with substance. Flag risk. Prefer a foundation
  pass over a band-aid when a late requirement breaks an assumption. Validate
  what's right before correcting what isn't.
- **Substance over form.** A relabel that doesn't change real behaviour
  isn't a fix.

## How to use this doc

1. Confirm the work persists state or crosses a boundary → apply the
   patterns (only skip via the narrow exceptions above).
2. Set the **plumbing depth** at `/plan` time.
3. **Lock the contracts** before building on them.
4. Choose architecture by criteria; record the ADR.
5. Decompose → critical path → build with TDD.
6. Log decisions and open questions as you go.
