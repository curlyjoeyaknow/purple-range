# Purple Range (codename Phalanx)

A single-user, single-host **purple-team CTF/lab** that scores every challenge
across three pillars — **attack → detect → mitigate** — honestly graded against
a generated manifest-as-oracle, never hardcoded answers. Clean rebuild of
[`/home/memez/cyber-range`](../cyber-range), which only ever scored the attack
half and couldn't be trusted to stay network-isolated.

## Status

**Planning complete; awaiting architecture sign-off before build.**

PRD, ARCHITECTURE, and ADR-0001 are written; the critic red-team is folded in
and confirmed (GO-WITH-FIXES → fixes confirmed). See
[`docs/RED-TEAM.md`](docs/RED-TEAM.md). No application code yet.

## Quickstart

> TBD — the `lab` CLI is not built yet. Once M0/M1 land, expect roughly:
>
> ```
> lab up <phase>       # provision + onboard a scenario
> lab validate <phase> # boot → arm containment tripwire → e2e → teardown
> lab status           # scoring state (folded from the event log)
> lab panic            # kill-switch: cut egress + pause VMs
> ```
>
> Until then, start with the docs below.

## Documentation

| Doc | Purpose |
|---|---|
| [`docs/PRD.md`](docs/PRD.md) | Product requirements — what it is, for whom, goals/non-goals |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | System design, contract catalog, containment model |
| [`docs/ADR/0001-manifest-oracle-event-sourced-scoring.md`](docs/ADR/0001-manifest-oracle-event-sourced-scoring.md) | The platform spine decision |
| [`docs/BRAINSTORM.md`](docs/BRAINSTORM.md) | Society-of-minds brainstorm (feasibility, ideal design, red-team) |
| [`docs/OPEN-QUESTIONS.md`](docs/OPEN-QUESTIONS.md) | Unresolved decisions + reserved ADRs + expert checkpoints |
| [`docs/RED-TEAM.md`](docs/RED-TEAM.md) | Critic findings with resolution status |
| [`docs/TODO.md`](docs/TODO.md) | Milestone spine (M0–M8) and open ADRs |
| [`docs/CHANGELOG.md`](docs/CHANGELOG.md) | What changed and when |

See [`CLAUDE.md`](CLAUDE.md) for the project operating manual and
[`ENGINEERING.md`](ENGINEERING.md) for the full engineering charter.
