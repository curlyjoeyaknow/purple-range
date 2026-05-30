# TODO — Purple Range (codename Phalanx)

> Updated by the `docs-keeper` agent. Format matches `decomposer` output.
> This file holds **high-level milestones** derived from the architecture.
> `/decompose` produces the per-task graph (T-NNN); until then these are
> milestone-level (M-N) with rough dependency order, not over-decomposed.
>
> Spine: [`docs/PRD.md`](PRD.md) · [`docs/ARCHITECTURE.md`](ARCHITECTURE.md) ·
> [`docs/ADR/0001-manifest-oracle-event-sourced-scoring.md`](ADR/0001-manifest-oracle-event-sourced-scoring.md) ·
> [`docs/BRAINSTORM.md`](BRAINSTORM.md) · [`docs/OPEN-QUESTIONS.md`](OPEN-QUESTIONS.md) ·
> [`docs/RED-TEAM.md`](RED-TEAM.md)

## Status legend

- `ready` — no unmet dependencies; can be picked up.
- `in-progress` — being worked on; check the branch.
- `blocked-on-X` — waiting on another milestone/task ID.
- `review` — implementation done; in code review.
- `done` — merged.

## Milestone dependency order (rough)

```
M0 ──> M1 ──> M2 ──> M3 ──> M4
                 │           ▲
                 └──> M5 ────┘   (M5 containment gates M4 in practice)
M2 ──> M6
M2 ──> M7   (post-MVP randomization)
M1/M2 ──> M8
```

- **M0** must land first (hygiene + deps + CI + CLI scaffold).
- **M1** is the MVP backbone; everything scoring-related depends on it.
- **M2** proves the manifest-as-oracle pipeline end-to-end (the MVP).
- **M5** (containment hardening) **gates M4** in practice — no autonomous
  attacker runs until the host-side tripwire + `panic()` + pre-flight exist.
- **M6/M7/M8** are later/parallelizable once M2 is green.

## Milestones

### M0 — Repo hygiene + bootstrap

- [ ] **M0  De-bloat + fetch-deps + CI skeleton + lab CLI scaffold**  `[BLOCKER]`
  - Depends on: none
  - Scope: remove the three vendored clones + committed venv (6.2 GB → < 50 MB);
    `scripts/fetch-deps.sh` (pinned refs/commits, checksum-verified, into
    gitignored `vendor/` on `/mnt/data`); CI skeleton incl. `docs-discipline` +
    size-guard + contracts-CI placeholder; `lab` CLI scaffold
    (`up|down|reset|validate|status|panic`).
  - Refs: ARCHITECTURE.md "De-bloat + dependency pinning", "Repo layout", "lab CLI".
  - Status: ready

### M1 — Scoring spine (MVP backbone)

- [ ] **M1  Event store + contracts + scorer ports + fakes**  `[CRITICAL]`
  - Depends on: M0
  - Scope: append-only event store (SQLite hash-chained ledger, M3-corrected
    justification); versioned contracts (`version:<int>` on all persisted shapes);
    scorer + ports (Clock, Rng) with fakes; fold rules incl. UNGRADEABLE for
    un-terminated `correlation_id` (M4) + `scenario_aborted(v1)`; idempotent
    scoring key incl. `manifest_hash` (M5-scoring).
  - Refs: ARCHITECTURE.md event catalog, fold rules, scoring; ADR-0001.
  - Status: blocked-on-M0

### M2 — Vulhub/Docker web phase end-to-end (the MVP)

- [ ] **M2  generate → onboard → attack → 3-pillar grade (Docker/web)**  `[CRITICAL]`
  - Depends on: M1
  - Scope: prove the manifest-as-oracle pipeline on a Dockerized Vulhub web
    target across all three pillars (ATTACK, DETECT, MITIGATE); MITIGATE
    functional-path gate with `deny_all_ref` (F2). This is the MVP exit.
  - Refs: PRD goals; ARCHITECTURE.md orchestrator loop + grading discipline.
  - Status: blocked-on-M1

### M3 — Detection data-plane

- [ ] **M3  Detection data-plane (Security Onion primary)**  `[HIGH]`
  - Depends on: M2
  - Scope: Security Onion as the primary detection plane; onboarding;
    `DetectionRule` v2 + mandatory calibration fixture
    (`correct_ref`/`match_all_ref`/`match_none_ref`) + the contracts-CI
    calibration gate (F1).
  - Refs: ARCHITECTURE.md DETECT grading; RED-TEAM F1; Q-002, Q-006.
  - Status: blocked-on-M2

### M4 — Automated threat-actor runner

- [ ] **M4  Native ThreatActor adapter + ground-truth, bounded allowlist**  `[HIGH]`
  - Depends on: M2; **gated by M5 in practice** (no autonomous attacker before containment hardening)
  - Scope: native runner adapter (bettercap caplet / revshell / AiTM-vs-mock);
    ground-truth emission for DETECT windows; in-code CIDR allowlist; v1 =
    allowlisted technique set only, no autonomous exploit/egress selection.
  - Refs: ARCHITECTURE.md ThreatActor port; OPEN-QUESTIONS Q-007/Q-008; RED-TEAM F3.
  - Status: blocked-on-M2, blocked-on-M5

### M5 — Containment hardening (gates M4)

- [ ] **M5  IsolationProvider + host-side tripwire + panic + pre-flight**  `[CRITICAL]`
  - Depends on: M1 (events/ports); **gates M4**
  - Scope: `IsolationProvider` port + `HostNftablesTripwire` adapter;
    host nft forward-drop (PRIMARY) on vboxnet + Docker bridge, v4/v6/DNS;
    continuous egress tripwire (arm/disarm whole-window, re-armed per step) as
    the REAL gate firing `IsolationFailed` + `panic()`; in-guest probe =
    corroboration only; `IsolationReport` v2; `lab panic` (nft egress-cut
    sub-second + best-effort VM-pause). **Provisioning-window invariant:** tripwire
    DISARMED during sanctioned provisioning (NAT-on, Q-012), RE-ARMED before
    first attack — provisioning must never fire `panic()`.
  - Refs: ARCHITECTURE.md containment model + IsolationProvider; ADR-0006; RED-TEAM F3.
  - Status: blocked-on-M1

### M6 — GOAD-AD phase

- [ ] **M6  GOAD / Active Directory phase**  `[MEDIUM]`
  - Depends on: M2 (pipeline proven); M5 (containment for multi-VM)
  - Scope: GOAD-based AD scenario through the manifest-as-oracle pipeline;
    VM plane (vboxnet) first-class; `panic()` VM-pause caveat with GOAD-full's 5 VMs.
  - Refs: ARCHITECTURE.md phases; m4 panic caveat.
  - Status: blocked-on-M2, blocked-on-M5

### M7 — SecGen containerized generator (post-MVP randomization)

- [ ] **M7  SecGen containerized generator**  `[MEDIUM]`
  - Depends on: M2
  - Scope: containerize SecGen (Ruby 3.2 / Vagrant 2.2.9 / Packer / libvirt in OCI
    image, ADR-0003) to deliver post-MVP target randomization; "pinned-by-cached-
    output-box" claim (M1-corrected). Select exact SecGen commit + frozen base box.
  - Refs: ARCHITECTURE.md pinned versions; ADR-0003 (reserved); Q-011, Q-012.
  - Status: blocked-on-M2

### M8 — Validation harness + reproducibility

- [ ] **M8  Validation harness tiers + reproducibility**  `[MEDIUM]`
  - Depends on: M1, M2 (and each phase as it lands)
  - Scope: `lab validate --e2e <phase>` tiers (boot → arm tripwire → scripted
    attack → assert `tripwire_egress_count==0` → teardown); pair-rotation +
    teardown-leaves-no-residue assertion (m5); reproducibility claims gated on Q-012.
  - Refs: ARCHITECTURE.md validation; RED-TEAM m5.
  - Status: blocked-on-M2

## Open ADRs (to be written at the relevant `/decompose` / phase)

- [ ] **ADR-0002** — (reserved) — see OPEN-QUESTIONS.md "Reserved ADR" / Q-002.
  - Status: ready (write before the SO unattended-install path lands)
- [ ] **ADR-0003** — SecGen containerization (Ruby/Vagrant/Packer/libvirt in OCI; toolchain-pin collision). `[for M7]`
  - Status: ready (write before M7)
- [ ] **ADR-0004** — (reserved) — see OPEN-QUESTIONS.md.
  - Status: ready
- [ ] **ADR-0005** — Hash-chaining as tamper-EVIDENCE not tamper-resistance (Q-005). `[for M1]`
  - Status: ready (write before M1 ledger lands)
- [ ] **ADR-0006** — Containment authority: host-side-continuous (RESERVED, critic F3). Must record the **provisioning-window arm/disarm invariant**. `[for M5]`
  - Status: ready (write at `/decompose` of M5 / the containment phase)

## Followups (not blockers; from `/critique` and `/phase-review`)

- [ ] **F-001 (Q-014)** — DETECT calibration fixtures are sole-authored + depend on the Q-006 benign baseline.
  - Source: RED-TEAM.md 2026-05-30, F1 residual
  - Severity: 🟠 — accepted/documented
  - Trigger: when a calibration fixture is found to pass a bad rule, or Q-006 baseline is finalized.

## Done

Move milestones/tasks here when merged, keep the ID for traceability.

- (none yet — planning complete, awaiting architecture sign-off before build)
