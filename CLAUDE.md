# CLAUDE.md — Project Operating Manual

This file is loaded into every Claude Code session for this repo. Read it.
The full engineering charter is in `ENGINEERING.md`; this is the short list
of *non-negotiables*.

## Non-negotiables

1. **Spec before code.** If there is no PRD, ARCHITECTURE doc, or feature spec
   for what you're about to build, write it first. If one exists but is stale,
   update it first. No code lands without a spec it implements.

2. **Contracts before implementations.** Data shapes, event shapes, API shapes
   — defined, typed, and versioned (a `version: <int>` field on everything
   persisted) *before* anything depends on them. New fields are additive;
   removals require a migration ADR.

3. **Ports & adapters at every boundary.** Every external dependency (DB,
   vendor SDK, HTTP API, filesystem, clock, randomness) sits behind an
   interface defined in our code. Production wires the real adapter; tests
   wire a fake. Never `import` a vendor SDK directly from business logic.

4. **Append-only events for persisted state change.** State is derived by
   folding the event log. Even at small scale (one JSONL file or one
   `events` table) — adopt the pattern from commit 1. Retrofitting later is
   the expensive path.

5. **TDD, honestly.** Failing test first. Never mock the unit under test.
   Fakes only at boundaries. If you find yourself writing a test that
   asserts the implementation rather than the behaviour, stop and redesign.

6. **Decisions become ADRs.** Anything non-obvious — pick a database, pick a
   framework, pick a contract shape, pick a folder layout — gets an ADR in
   `docs/ADR/` *before* the code lands. Context, decision, consequences,
   alternatives considered. Future-you needs the *why*.

7. **Docs are part of the change.** Every PR touches the relevant doc:
   README (if user-visible), ARCHITECTURE (if structural), CHANGELOG
   (always), TODO (mark items done/added), HANDOFF (refresh at session end).

8. **Branch per feature, PRs only, small commits.** Direct pushes to `main`
   are blocked by branch protection. Use worktrees for genuinely parallel
   work. Commit messages explain *why*, not *what* — the diff shows *what*.

9. **The critique loop is mandatory for non-obvious decisions.** Before any
   architecture, contract, or interface choice lands, invoke `/critique` and
   address every concern raised — either by changing the design or by
   documenting why the concern is acceptable. Comfort is not consensus.

10. **Look up live docs.** For every dependency, look up current
    documentation rather than relying on memory of older versions. Pin
    versions; record them in the architecture doc.

11. **Pause for decisions, not for permission.** Under `/deliver`, stop only
    at the defined human-decision checkpoints (brainstorm, architecture
    sign-off, gate escalations, expert/legal questions, destructive ops) and
    true blockers. Between them, execute and report — don't ask approval to
    keep building the already-decided thing.

12. **Checkpoint before the cliff.** Keep long-running context under ~60%.
    Run `/checkpoint` proactively at phase seams and when the context guard
    nudges. The orchestrator delegates noisy work to subagents to stay lean.
    Never ride into a force-compact with unsaved state.

## What I expect you to do, by default

- When asked to "build X", first check whether the spec exists. If not, and
  the design isn't obvious, run `/society-of-minds` to pressure-test the
  approach, then `/plan`. If a spec exists, go to `/forge-agents` (if
  specialists are needed) then `/decompose`.
- Before decomposition, run `/forge-agents` to create the project's domain
  specialists — but forge nothing a small project doesn't need.
- `/decompose` must analyze the critical path and real parallel opportunities
  *first*, then assign best-suited agents, then have `plan-critic` validate
  the plan and set the hostile-review gates before any execution starts.
- When proposing a design, invoke the `critic` agent on it before defending it.
- When implementing, run the `tester` agent first to lock the contract via a
  failing test, then the assigned implementer/specialist.
- At plan-critic's designated milestones, run the hostile gate via a
  `clean-room-reviewer` spawned as a fresh subagent — clean context, no lore.
- After any non-trivial change, the `docs-keeper` updates CHANGELOG and TODO.
- When the user signals "let's stop for the day" or context is filling up,
  run `/handoff` to write a resumable HANDOFF.md.
- Between phases, run `/phase-review` — it fans out reviewer +
  external-reviewer + critic in parallel.

## Agent roster (see `.claude/agents/`)

| Agent | When to use |
|---|---|
| `pm-orchestrator` | Default conductor — routes work, manages parallel streams, enforces the delivery plan and its gates. |
| `critic` | Red-teaming concepts, designs, and decisions. Hostile, constructive. |
| `architect` | System/component design; produces ADRs and architecture docs. |
| `decomposer` | Turns a goal into a task graph with a critical path. |
| `plan-critic` | Validates critical path + parallelism; designates the hostile-review gates. Runs before execution. |
| `implementer` | TDD-disciplined code writer. |
| `tester` | Test-first specialist; honest tests only. |
| `reviewer` | Internal code review with full project context. |
| `external-reviewer` | Fresh-context readability review; sees only the diff + minimal context. |
| `clean-room-reviewer` | Hostile, zero-context milestone gate review. Always spawned as a fresh subagent. |
| `docs-keeper` | README, CHANGELOG, TODO, DELIVERY-PLAN, HANDOFF maintainer. |
| `detection-engineer` *(forged)* | DETECT pillar: Elastic EQL/Lucene/Suricata/Zeek detections on Security Onion 2.4, Fleet onboarding (OnboardSpec), the three-window TP+FP grading oracle, and the F1 calibration fixtures. M3/M2/M6. |
| `adversary-emulation-engineer` *(forged)* | ATTACK pillar: safe, bounded threat-actor runner (native + Atomic Red Team), MITRE-tagged observed-outcome ground-truth, the ttp∈manifest check, and the F2 MITIGATE re-attack/deny-everything verification. M2/M4/M6, gated by M5. |
| `lab-orchestration-engineer` *(forged)* | Provisioning + virtualization + CONTAINMENT: LabProvider/IsolationProvider/ScenarioGenerator ports, Vagrant/VirtualBox/Docker, snapshots, /mnt/data layout, GOAD/SecGen, host nftables tripwire + panic. M0/M2/M5/M6/M7. |

## Skills (slash commands in `.claude/skills/`)

| Command | Effect |
|---|---|
| `/deliver` | End-to-end driver: runs the whole pipeline autonomously between human-decision checkpoints. |
| `/society-of-minds` | Multi-domain brainstorm: feasibility, ideal architecture, red-team, cost/benefit — scaled to project size. Run first. |
| `/plan` | New project/feature: PRD → ARCHITECTURE → ADR-0001 → TODO. |
| `/forge-agents` | Generate this project's domain-specialist subagents into `.claude/agents/`. |
| `/decompose` | Goal → task graph → critical path → agent assignment → plan-critic gates. |
| `/critique` | Run the critic on whatever's on the table. |
| `/external-check` | Run external-reviewer on the current diff. |
| `/phase-review` | Comprehensive review at a milestone. |
| `/checkpoint` | Reconcile state, write handoff, commit, compact — proactively, before a force-compact. |
| `/handoff` | Write HANDOFF.md for the next session. |
| `/ship` | Pre-PR checklist + open PR + wait for CI. |

## Posture

Push back with substance. Disagreement is the job, not impertinence. When you
think I'm wrong, say so — and bring the falsifiable test that would prove it.
