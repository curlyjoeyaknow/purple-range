# ADR-0005 — Sequential, scenario-scoped scope (not all phases booted simultaneously)

> Status: accepted
> Date: 2026-05-31
> Deciders: owner (memeworldorder2024), architect
> Supersedes: —

## Context

Purple Range runs on a **single bare-metal host** and the owner's original goal
was stated as "all lab phases boot and inter-communicate." Taken literally —
every phase hot at the same time — that is physically impossible on this host.
This ADR **records the already-settled scope decision** taken at brainstorm
convergence (a locked decision, BRAINSTORM §Locked decisions) and architecture
sign-off; it formalises *why* the redefined scope still satisfies the owner's
goal. See [`docs/ARCHITECTURE.md`](../ARCHITECTURE.md) (§High-level view,
§Validation, §Non-functional targets) and [`docs/BRAINSTORM.md`](../BRAINSTORM.md)
(§Scale read, Round 1 feasibility, §Locked decisions).

The forces in play:

- **RAM is the binding ceiling; disk is not.** Probed host (2026-05-30): 60 GiB
  RAM, ~55 GiB usable for guests. Disk was resolved as a *non*-ceiling on the
  same date — lab artifacts live on the 1.7 TB `/mnt/data` NVMe (Q-001 resolved),
  leaving RAM as the only real constraint.
- **The co-resident set blows the ceiling.** Booting Security Onion (~16 GiB) +
  Splunk + GOAD-full (a 5-VM AD forest, ~24–32 GiB) + SecGen victims *all at
  once* exceeds ~55 GiB and would additionally demand nested virtualisation. By
  contrast, **one adjacent pair** — e.g. GOAD-full + Security Onion ≈ 48 GiB — is
  *tight but feasible* within the usable budget.
- **The product loop is per-phase anyway.** Each phase's value is its own
  scripted ATTACK→DETECT→MITIGATE loop (ADR-0001). The three-pillar grading does
  not require other phases to be live; it requires *its* victim + *its* telemetry
  + *its* manifest oracle. Sequential scope therefore costs the product nothing
  on the core loop and gives a cleaner per-technique training signal (BRAINSTORM
  Round 4).
- **"Inter-communicate" still has to mean something.** The owner genuinely wants
  to prove cross-phase log/traffic flow, not just isolated phases. The question
  is *how much* must be hot to prove it.

What we know: the RAM arithmetic is decisive and was the Round-1 feasibility
showstopper-turned-cost. What we **don't** control: whether a future, larger host
appears — which is the explicit re-tier trigger below.

## Decision

> We will scope the lab as **sequential and scenario-scoped** — each phase boots
> green and runs its own attack→detect→mitigate loop independently, and
> cross-phase "inter-communication" is proven for **one adjacent pair at a time**
> (the `lab validate --pair <a> <b>` model) — **not** all phases hot
> simultaneously, because ~55 GiB usable RAM is the binding ceiling.

The design:

**1. One phase at a time for the core loop.** The orchestrator boots a single
phase, arms containment (ADR-0006), runs the scripted
attack→detect→mitigate→re-attack loop, grades all three pillars against the
manifest + ground-truth (ADR-0001), then tears down. A pre-up **free-RAM gate
aborts** if insufficient memory is available before a boot (ARCHITECTURE
§Non-functional targets: "Adjacent-pair RAM ≤ ~55 GiB usable; pre-up free-RAM
gate aborts if insufficient").

**2. Adjacent-pair, not all-hot, for inter-communication.** The single place
"phases inter-communicate" is proven is `lab validate --pair <a> <b>`: boot two
**adjacent** phases, assert inter-phase log flow within the RAM ceiling, then
rotate. Validation is therefore organised as: `lab validate --smoke <phase>`
(boot → health → down), `lab validate --e2e <phase>` (the full per-phase loop),
and `lab validate --pair <a> <b>` (the only cross-phase proof). `make
validate-all` runs the sequential per-phase e2e checks plus the adjacent-pair
checks into a green/red matrix.

**3. Why this still satisfies the owner's goal.** "Boot & inter-communicate" is
**redefined, not abandoned**: every phase *does* boot green and *does*
inter-communicate with its neighbour — just pairwise and in sequence rather than
all-at-once. The thing that is dropped (a single moment where *every* phase is
simultaneously live) was never required by the training value and was never
physically reachable on this host. The redefinition is recorded as a
load-bearing locked decision so it is not silently re-litigated later.

**4. Pair rotation must leave no residue.** Because phases are serial, rotation
correctness matters: the `--pair` validation asserts that after boot pair A →
teardown, the host `nft` ruleset, the VirtualBox registry, and Fleet enrollment
are back to baseline before boot pair B (ARCHITECTURE m5). A leaked nft rule, a
stale VM registration, or a lingering enrollment fails the check — this is the
guard that makes "sequential" trustworthy.

## Consequences

- **Positive:**
  - **The host can actually run the lab.** Sequential + adjacent-pair fits the
    ~55 GiB ceiling; GOAD-full is reachable solo and the GOAD+SO pair is feasible.
  - **Cleaner training signal.** One phase at a time isolates the
    technique-under-test from cross-phase noise (BRAINSTORM Round 4).
  - **Reproducibility preserved.** Each scenario is a self-contained, replayable
    run keyed by seed → manifest (ADR-0001); nothing depends on a fragile
    all-hot global state.
  - **Wide parallelism *off* the host.** Code, contract, and unit work
    (scorer, event-log fold, chain verify, contract loaders, all on fakes)
    parallelise freely in CI — they never touch a hypervisor (the `LabProvider`
    port + `InMemoryLab` fake, ADR-0002).

- **Negative:**
  - **Integration / validation is HOST-SERIAL.** Real boots cannot be
    parallelised — `lab validate --e2e` and `--pair` run one (or one pair) at a
    time on the single host, so end-to-end validation wall-clock is inherently
    serial. This constrains the delivery plan: real-boot validation tasks sit on
    a serial host lane, not a parallel one.
  - **No simultaneous all-phase demo.** If a future use case genuinely needs
    every phase hot at once (it does not today), this scope must be revisited.

- **Neutral / deferred:** the exact phase adjacency map (which pairs are
  "adjacent" and worth a `--pair` check) is decided per phase at decomposition,
  not here.

- **Reversibility:** **hours-to-days at the orchestration layer** — sequential
  vs co-resident is an orchestration policy, not a contract change, so the code
  cost to relax it is small. The true blocker to "all hot" is the **RAM ceiling**,
  which only a hardware change removes.

This decision **honours** the charter and introduces no deviation; it is a
scope/scale decision, not a pattern deviation.

## Alternatives considered

### Alternative 1 — All phases booted simultaneously

- **What it would look like:** boot Security Onion + Splunk + GOAD-full + SecGen
  victims concurrently so the whole range is live at once and any phase can talk
  to any other.
- **Why not:** **physically impossible on this host** — the co-resident set
  exceeds ~55 GiB usable RAM and would require nested virtualisation. It was the
  Round-1 feasibility showstopper. No software design removes a hardware ceiling.
  Rejected on physics.

### Alternative 2 — Cloud / multi-host (scale the range horizontally)

- **What it would look like:** spread phases across multiple machines or a cloud
  account so the aggregate RAM is unbounded and all phases can be hot.
- **Why not:** the project is **explicitly personal / single-owned-host**
  (BRAINSTORM §Locked decisions: audience is self-training, reliable on the
  owner's host over publish polish). Cloud/multi-host adds cost, an internet
  attack surface that fights the fail-closed containment invariant (ADR-0006),
  and operational overhead the charter's scope rejects. Rejected as out of scope.

### Alternative 3 — Pure-container range (drop full VMs to fit more phases in RAM)

- **What it would look like:** run every phase as containers so the per-phase RAM
  footprint shrinks enough to co-locate more (or all) phases.
- **Why not:** it **loses VM / Active-Directory fidelity** — GOAD's Windows
  forest, Security Onion's full sensor stack, and randomised SecGen victims are
  not container workloads (same reason ADR-0002 keeps containers as *an* adapter,
  not the only one). Shrinking RAM by discarding the exact fidelity the phases
  exist to teach is a false economy. Rejected — we keep containers for the
  Vulhub/web fast-path only.

## Accepted risks

🟡 Accepted, with the trigger to revisit:

- **Host-serial validation wall-clock** — accepted because real-boot validation
  is inherently single-host and the delivery plan already lanes it serially.
  Revisit only if validation time becomes the dominant delivery cost.
- **RAM ceiling as the re-tier trigger** — accepted as the explicit boundary:
  **if a larger host appears, revisit this scope** (more co-resident phases, or
  even all-hot, become possible). Until then sequential is mandatory, not
  preferred.

## Links

- PRD: [`docs/PRD.md`](../PRD.md)
- Spine ADR (reserved this one): [`0001-manifest-oracle-event-sourced-scoring.md`](0001-manifest-oracle-event-sourced-scoring.md)
- Related ADRs: ADR-0002 (`LabProvider` port — sequential boots run behind it), ADR-0006 (containment, armed per phase)
- Brainstorm: [`docs/BRAINSTORM.md`](../BRAINSTORM.md) §Scale read, Round 1, §Locked decisions
- Architecture sections affected: [`docs/ARCHITECTURE.md`](../ARCHITECTURE.md) §High-level view, §Validation (two tiers), §Non-functional targets (RAM ceiling)
