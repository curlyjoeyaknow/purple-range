# FRAMEWORK.md — How the whole thing runs end to end

This kit is a *framework*, not just a pile of skills. One command — `/deliver`
— drives a project from a one-line idea to a shipped, reviewed build, running
autonomously between a small set of human-decision checkpoints and managing
its own context so it never stalls on a force-compact.

Read `CLAUDE.md` for the standing rules and `ENGINEERING.md` for the
engineering charter. This file is about how the parts move together.

## The end-to-end flow

```
/deliver
   │
   ├─[STOP] /society-of-minds   scale-calibrated panel: feasibility, ideal
   │                            architecture, red-team, cost/benefit.
   │                            → you give goal/scope/tier, then pick a direction
   │
   ├─       /plan               PRD + ARCHITECTURE + ADR-0001 (critic red-teams)
   ├─[STOP]                     architecture sign-off — wait for approval
   │
   ├─       /forge-agents       project-specific specialist subagents
   ├─[STOP]                     quick roster approve/trim (skip if none)
   │
   ├─       /decompose          task graph → critical-path & parallelism analysis
   │                            → agent assignment → plan-critic validates &
   │                            sets hostile-review gates → DELIVERY-PLAN.md
   ├─[STOP]                     light confirm of plan + gates
   │
   ├─       EXECUTE (pm-orchestrator, bound by DELIVERY-PLAN.md) — AUTONOMOUS
   │            critical path first; parallel streams to assigned agents in
   │            worktrees; per task: tester → implementer → reviewer → docs-keeper;
   │            /ship through CI; clean-room hostile gates at milestones;
   │            /phase-review at boundaries; /checkpoint to stay under 60%.
   │
   ├─[STOP]  only on: gate escalation past loop budget · expert/legal question ·
   │                  destructive op · plan deviation
   │
   └─       final /phase-review → tag → CHANGELOG → closing /handoff → report
```

`[STOP]` = a human-decision checkpoint. Everything between is autonomous.

## The autonomy policy (pause for decisions, not for permission)

The framework's defining behaviour. A **decision** changes *what* gets built or
*whether it's safe*; **progress** is building the already-decided thing.

**Stops (human judgement):** brainstorm inputs · brainstorm convergence ·
architecture sign-off · forged roster · delivery-plan confirm · gate
escalation past loop budget · expert/legal (⚖️) open questions · anything
destructive or charter-bending.

**Autonomous (no permission asked):** the per-task build loop · CI · opening
and merging green PRs within branch protection · hostile gates within budget ·
moving between tasks · parallel streams · all doc maintenance · feature-branch
commits/pushes · checkpointing.

This is enforced two ways: the `/deliver` skill instructs the orchestrator on
where to stop, and `.claude/settings.json` `permissions.allow` lists the
routine commands so the tool itself doesn't prompt for them. Destructive
commands sit in `permissions.deny` and escalate regardless.

## The context-management architecture

The orchestrator runs longest, so it's most at risk of an abrupt auto-compact
mid-build. Four hooks plus one discipline keep it under ~60% and make any
compaction lossless.

| Mechanism | Type | What it does |
|---|---|---|
| `statusline.sh` | `statusLine` | Estimates context %, renders it, and trips `.claude/state/checkpoint-needed` at the threshold (default 60%). |
| `checkpoint-nudge.sh` | `UserPromptSubmit` hook | When the flag is set, injects a directive: run `/checkpoint` (handoff → commit → compact) before continuing. |
| `precompact-handoff.sh` | `PreCompact` hook | **Backstop.** Before any compaction (auto or manual), writes a mechanical state snapshot and backs up the transcript — so even a surprise compaction loses nothing. |
| `session-restore.sh` | `SessionStart(compact\|resume)` hook | After a compaction/resume, re-injects `docs/HANDOFF.md` + the snapshot + delivery-plan position, so the session wakes up grounded. |
| **Delegation discipline** | orchestrator behaviour | Heavy/noisy work goes to short-lived subagents whose context is discarded on return. The conductor holds decisions and state, not raw output. *This is what actually keeps usage low.* |

Flow of a checkpoint:

```
context climbs → statusline trips flag at 60%
   → next turn, checkpoint-nudge injects "run /checkpoint"
   → /checkpoint: reconcile TODO/DELIVERY-PLAN → /handoff → commit → /compact
   → PreCompact snapshots + backs up transcript
   → SessionStart(compact) re-injects handoff
   → orchestrator resumes from "Next concrete step", still bound by the plan
```

### Honest limits (and how they're handled)

- The 60% trigger is a **heuristic** (transcript-size estimate, deliberately
  conservative so it fires early). If your Claude Code version exposes a native
  context-usage field to the statusline, wire it into `statusline.sh` for
  precision. The `PreCompact` backstop is the hard guarantee regardless.
- **The orchestrator runs as the main session, not as a subagent.** This is the
  fix for the obvious gap (session-level hooks can't see a subagent's context):
  the conductor is the main session so the guard protects it, and it spawns
  short-lived *worker* subagents whose noisy context is discarded on return.
- **The agent may not be able to self-`/compact`.** So the guard does not
  depend on it. What it guarantees: the handoff is always fresh at ~60%, and
  `PreCompact`+`SessionStart(compact)` make any compaction (manual, or auto at
  the real cliff) lossless. Proactive checkpointing chooses a clean seam; it
  does not assume self-compaction.
- **"Multiple reviewers" are the same model in separate contexts** — correlated,
  not statistically independent. They catch what habituation hid, which is
  real, but N model passes ≠ N independent checks. For genuinely irreversible
  gates, route to a human (plan-critic can mark a gate `human`).
- **Clean-room isolation is a convention, not a sandbox.** The reviewer has
  read/exec tools and is instructed not to wander; if it must read neighbouring
  code it has to declare it. Enforcement is behavioural, not mechanical.

## The merge gate (resolving the solo-dev deadlock)

Opening a PR and getting CI green is autonomous. **Merging is not, by default** —
because branch protection requires a review and an agent can't approve its own
PR. Two supported modes:

- **Team mode** (`setup-branch-protection.sh`): 1 required approval. The agent
  stops at "PR open, CI green, awaiting merge"; a human merges. `gh pr merge`
  stays in `permissions.ask`.
- **Solo mode** (`setup-branch-protection.sh --solo`): 0 required approvals,
  but CI + linear history + conversation resolution still enforced. The agent
  may merge its own green PR; move `gh pr merge` to `permissions.allow`. The
  gate is "green CI + review discipline", not "a second human".

Until `ci.yml` is wired to your stack its `test` job fails by design and will
block merges — start with `setup-branch-protection.sh --solo --checks ""` and
add required checks once CI is real.

## Right-size the framework itself (don't let the scaffolding become the work)

The full pipeline — 11 agents, 11 skills, 4 hooks, gates, worktrees — is sized
for medium-to-large projects. For small work it is *itself* over-engineering,
the exact thing it warns against. Use the minimal subset instead:

| Project | Use | Skip |
|---|---|---|
| **Trivial / spike** | `critic` once on the idea, then build with honest tests. | Everything else. |
| **Small** (one service, a weekend) | `/plan` (PRD + 1 ADR) · TDD loop · `/ship` · one gate at the end. No forged agents, no worktrees, solo-mode branch protection. | society-of-minds panel, forge-agents, parallel streams, multi-gate plan. |
| **Medium** | The full pipeline, modest gates. | Adversarial gates unless a milestone is truly irreversible. |
| **Large** | Everything, gates dialled up. | — |

`/society-of-minds` Step 0 and `/deliver`'s closing note already calibrate to
scale; this table is the explicit "less is more" contract. If reading and
maintaining the scaffolding for a project would cost more than the project,
you picked the wrong tier — drop down.

## Running it

```bash
# One-time per machine
./install/00-system-tools.sh && ./install/01-vscode-setup.sh

# Per project (from an empty repo)
/path/to/dev-bootstrap/install/02-init-project.sh
gh repo create && git push -u origin main
./scripts/setup-branch-protection.sh

# Then, in Claude Code:
/deliver
```

## Resuming

```
> read docs/HANDOFF.md and docs/DELIVERY-PLAN.md
> /deliver
```

The orchestrator re-grounds and continues the autonomous loop from the
handoff's "Next concrete step", still bound by the delivery plan and still
stopping only at the human-decision checkpoints.

## Tuning

- Checkpoint threshold: `CLAUDE_CHECKPOINT_PCT` (default 60),
  `CLAUDE_CONTEXT_TOKENS` (default 200000) — env vars read by `statusline.sh`.
- Where it stops: edit the autonomy policy in `.claude/skills/deliver/SKILL.md`.
- What runs without prompting: edit `permissions` in `.claude/settings.json`.
- Gate strictness: `.claude/agents/plan-critic.md` decides difficulty/loops;
  the spec lands in `docs/DELIVERY-PLAN.md`.
