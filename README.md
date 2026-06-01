# Purple Range (codename Phalanx)

A single-user, single-host **purple-team CTF/lab** that scores every challenge
across three pillars — **attack → detect → mitigate** — honestly graded against
a generated manifest-as-oracle, never hardcoded answers. Clean rebuild of
[`/home/memez/cyber-range`](../cyber-range), which only ever scored the attack
half and couldn't be trusted to stay network-isolated.

## Status

**Planning complete; awaiting architecture sign-off before build.**

Planning and architecture are complete; the red-team review is folded in and
confirmed (GO-WITH-FIXES → fixes confirmed). No application code yet.

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

## Layout

- `lab/` — the `lab` CLI (provision, validate, score, panic) and event ledger.
- `contracts/` — event/contract schemas (the platform spine).
- `adapters/` · `ports/` — ports & adapters around the lab provider.
- `scripts/` — dependency pinning and repository guards.
- `tests/` — the test suite over the contracts, ports, and fakes.
