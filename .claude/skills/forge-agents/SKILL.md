---
name: forge-agents
description: >-
  Generate project-specific specialized subagents tailored to THIS project's
  architecture and task domains, writing them into .claude/agents/. Run AFTER
  /plan (so the architecture and stack are known) and BEFORE /decompose (so the
  task graph can be assigned to real specialists). Derives the needed
  specializations from the architecture's modules and contract surfaces, writes
  one focused agent per genuine specialization, scoped to the stack — and
  deliberately forges nothing the project doesn't need. Use whenever a new
  project or major feature has a settled architecture and is about to be
  decomposed and built.
---

# /forge-agents — Create the project's specialist subagents

The generic roster (`critic`, `architect`, `decomposer`, `implementer`,
`tester`, `reviewer`, `external-reviewer`, `clean-room-reviewer`,
`docs-keeper`, `plan-critic`, `pm-orchestrator`) is project-agnostic. This
skill adds the *domain* specialists that this specific project needs — the
`react-frontend-implementer`, the `postgres-schema-architect`, the
`stripe-adapter-implementer`, the `etl-pipeline-tester`, whatever the
architecture actually calls for.

Run it after `/plan` (architecture is settled) and before `/decompose` (so
the task graph assigns work to specialists that exist).

## Step 1 — Derive the needed specializations

Read `docs/ARCHITECTURE.md`, the ADRs, and `docs/BRAINSTORM-*.md`. The
specializations fall out of:

- **Modules** — each major module with non-trivial domain logic may warrant a
  specialist (the API layer, the data layer, the processing core, the UI).
- **Adapters** — each external boundary (a specific DB, a specific vendor SDK,
  a specific protocol) often warrants an adapter specialist who knows that
  vendor's quirks and current docs.
- **Cross-cutting concerns** — if the project has heavy security, perf, or
  accessibility demands, a dedicated specialist for that concern.

Write the list down and confirm it with the user before generating. This is
also where you decide what NOT to forge.

## Step 2 — The anti-proliferation rule

**Do not manufacture agents for their own sake.** Each forged agent must earn
its place by either (a) encapsulating real domain knowledge the generic
`implementer`/`tester` lack, or (b) enabling parallelism (a distinct
specialist lets two streams run at once where one generalist would serialize
them).

Calibrate to scale:
- **Small project**: often zero or one forged agent. The generic roster is
  usually enough. Forging five specialists for a CLI tool is the exact
  over-engineering this kit exists to prevent.
- **Medium**: a handful — typically one per major module/adapter that carries
  real domain weight.
- **Large**: a richer roster, but still only where specialization buys
  knowledge or parallelism.

If you're tempted to forge an agent that would just be "the implementer but
it says React a lot", don't — note the React context in CLAUDE.md instead.

## Step 3 — Write each agent

Each forged agent is a Markdown file in `.claude/agents/<name>.md` with YAML
frontmatter, following the same shape as the existing roster. Requirements:

- **`name`**: `kebab-case`, specific (`postgres-schema-architect`, not
  `db-guy`).
- **`description`**: the routing hint — pushy and context-rich, so the
  orchestrator auto-delegates correctly. Include both what it does and when
  to use it. (See skill-creator's guidance: descriptions are the primary
  routing mechanism; make them a little pushy.)
- **`tools`**: scope to what the agent needs. Implementers need
  Read/Write/Edit/Bash; reviewers usually just Read/Grep/Glob.
- **`model`** (optional): heavier reasoning agents can inherit the session
  model; cheap exploratory ones can be pinned to a faster model.
- **Body (the system prompt)** must:
  1. Inherit the charter — reference `ENGINEERING.md` and `CLAUDE.md`; the
     specialist is bound by the same non-negotiables (ports/adapters,
     append-only events, versioned contracts, honest TDD, docs-as-you-go).
  2. State the specialization crisply — what this agent knows that the
     generic implementer doesn't.
  3. Name the current dependency docs it should consult (don't trust stale
     memory of a library version — look it up).
  4. Define its handoffs — to `tester` before it, `reviewer` after it, and
     `clean-room-reviewer` at gates.

Template skeleton for a forged implementer:

```markdown
---
name: <domain>-implementer
description: >-
  <Pushy, specific routing hint: what domain it implements and when to
  delegate to it.>
tools: Read, Write, Edit, Grep, Glob, Bash
---

# <Domain> Implementer

You implement the <domain> slice of this project. You are bound by
`ENGINEERING.md` and `CLAUDE.md` — same non-negotiables as every agent.

## Your specialization
<What you know that the generic implementer doesn't: the framework's
idioms, the vendor's gotchas, the protocol's edge cases.>

## Current docs to consult
<Which live docs to look up before coding — pin versions, don't guess.>

## Boundaries
- You go through the <domain> port; you never leak the vendor SDK upward.
- Tests use the <domain> fake; contract tests run against the real adapter in CI.

## Handoffs
- `tester` writes failing tests before you touch code.
- `reviewer` reviews your output; `clean-room-reviewer` gates at milestones.
```

## Step 4 — Register and announce

- Save each agent to `.claude/agents/`.
- Update `CLAUDE.md`'s agent roster table with the new specialists and their
  one-line "when to use".
- Have `docs-keeper` note the forged roster in `docs/ARCHITECTURE.md` (a
  short "Build roster" section) so the team knows who builds what.

## Step 5 — Hand off to /decompose

Now the task graph can assign real specialists:

```
> /decompose
```

The decomposer will map each task to the best-suited agent (generic or
forged), and `plan-critic` will sanity-check that no specialization is
missing and no single specialist is over-subscribed on the critical path.

## Note on the skill-creator skill

If you want to go further and create *project-specific skills* (not just
agents) — e.g. a `/deploy` skill wired to this project's exact pipeline — use
the `skill-creator` skill, which has tooling for drafting, testing, and
optimizing skill trigger descriptions. `forge-agents` is the lightweight,
agent-only path for the common case.
