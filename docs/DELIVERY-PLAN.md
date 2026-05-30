# DELIVERY-PLAN — Purple Range (codename Phalanx)

> Produced by `/decompose` → validated and gated by the `plan-critic` agent.
> The `pm-orchestrator` is **bound** by this document. If reality diverges,
> re-run `/decompose` to re-validate — don't improvise around it.
> Last validated: 2026-05-30
>
> Spine: [`docs/TODO.md`](TODO.md) (task graph) ·
> [`docs/ARCHITECTURE.md`](ARCHITECTURE.md) (design + contract catalog) ·
> [`docs/RED-TEAM.md`](RED-TEAM.md) (the FATAL findings these gates exist to
> close) · [`docs/PRD.md`](PRD.md) · [`docs/OPEN-QUESTIONS.md`](OPEN-QUESTIONS.md).

## Validated critical path

### MVP critical path (→ MVP exit at T-203)

```
T-001 → T-003 → T-101 → T-110 → T-111 → T-201 → T-202 → T-203  (MVP EXIT)
```

**Bottleneck tasks** (a day of slip here = a day of project slip):
- **T-101** — the M1a contract-lock blocker; **max fan-out**. Every parallel
  stream and every downstream task consumes its shapes/ports/fakes. Nothing real
  fans out until it lands.
- **T-111** — the **honest-scoring core** (3-pillar grading: ATTACK / DETECT
  F1-three-window / MITIGATE F2-functional-path). The central product claim lives
  here; it is pure-core but logic-dense.
- **T-203** — the **host-serial convergence**: three specialists + the scorer +
  real adapters meet on one 60 GB host to prove manifest-as-oracle end-to-end.

### Full-project critical path (post-MVP — NOT slack)

```
T-101 → T-501 → T-502 (502a core ∥ M2 / 502b host-tail)
      → T-503 (503a core ∥ M2 / 503b host-tail → IsolationVerified)
      → T-403 (web LIVE attack) → T-602 (AD LIVE attack — FULL-PROJECT FINISH)
```

- **Containment (S3) is critical path, not slack.** The full-project finish line
  is **T-602**, and it runs through **T-503 → T-403**. The orchestrator must NOT
  treat "MVP exit at T-203" as "project done" and demote containment.
- **Added post-MVP bottleneck: T-503** — its host-verified tail **T-503b** emits
  the `IsolationVerified` event that **gates ALL live attack** (T-203 via the
  T-502 edge, T-403, T-602). It is the single most safety-load-bearing task.

### What makes the parallelism real

The **M1a contract-lock blocker** is the enabler: **T-101** (all shapes + all
eight ports + all eight fakes + the adapter registry surface) *plus the carved
shared-infra files* — the full `lab` dispatch table (**T-004**), the CI workflow
structure with contracts/F1/F2 stages stubbed (**T-003**), and the unified
dependency manifest (**T-103**). Once these land, the three streams are
**file-disjoint and additive-only**: they add files under `adapters/<domain>/*`
and fill in already-registered stubs, never editing the dispatch, registry,
workflow, or `pyproject.toml`. Without this carve the streams are false
concurrency (they'd collide-merge on shared infra).

## Near-critical / true parallel streams (monitor)

> Each stream runs concurrently in its own worktree **after M1a**, against the
> fakes — additive-only. **The host-serial tails serialize on the single 60 GB
> host regardless of agent** (resource ceiling, not a logical dependency).

| Stream | Tasks → Agent | Parallel-safe because | Worktree |
|---|---|---|---|
| **S1 — Detection** | T-301 (ADR) → `architect`; T-302, T-303, T-304, T-305 → `detection-engineer` | touches ONLY `Telemetry` port + `DetectionRule`/`OnboardSpec`; develops vs `ReplayLogBundle` / recorded logs | `../phalanx-s1-detection` |
| **S2 — Threat-actor skeleton** | T-401, T-402 → `adversary-emulation-engineer` | touches ONLY `ThreatActor` port + `AttackEvent`/mitigate; develops vs `ScriptedActor`; **NO live execution** | `../phalanx-s2-actor` |
| **S3 — Containment CORE** | T-501 (ADR) → `architect`; **T-502a, T-503a** → `implementer` (+ `tester` writes CannedReport branch tests first) | touches ONLY `IsolationProvider` port + `IsolationReport v2`; develops vs `CannedReport`; **post-MVP critical, not slack** | `../phalanx-s3-containment` |
| **Host-serial tails** | T-201/T-202/T-203 (M2), **T-502b/T-503b** (S3 nft-verify), **T-403** (web live), T-302/T-305 (live SIEM), T-601/T-602 (GOAD) → `lab-orchestration-engineer` (+ converging specialists) | serialize on the single 60 GB host (RAM ceiling) — cannot co-boot even when code is independent | main |

Agent-assignment summary: **detection-engineer → S1**;
**adversary-emulation-engineer → S2**; **implementer + tester → S3 cores**
(T-502a/T-503a); **lab-orchestration-engineer → the host-serial tails + the M2
critical path**.

## Corrections plan-critic made to the decomposer's draft

1. **C1 — Carve shared-infra files into the M1a blocker.** T-004 stubs the FULL
   `lab` dispatch table incl. stream sub-commands; T-101 locks the adapter
   registry with all eight placeholder registrations; T-003 stubs all CI stages
   incl. contracts + F1 + F2; **new T-103** adds all three streams' pinned deps
   to `pyproject.toml`/lockfile ONCE. Result: S1/S2/S3 become additive-only and
   file-disjoint, preventing stream merge collisions.
2. **C2 — Fix hidden serialization on S3.** Split **T-502 → T-502a** (fake-driven
   core, `implementer` + `tester`-first) **+ T-502b** (host-serial nft tail,
   `lab-orchestration-engineer`); same split for **T-503 → T-503a + T-503b**. The
   S3 logic now lands in parallel with the M2 critical path; only the host-serial
   tails serialize.
3. **C3 — Close the T-203 safety back door.** Added hard `blocked-on: T-502` to
   T-203 (its MVP e2e fires a live attack and must not precede the nftables
   PRIMARY containment incl. the Docker-bridge plane). Routed the fail-closed
   pre-flight refusal (`test_live_attack_refused_without_containment`, requires
   `IsolationVerified`) through the **orchestrator loop as the single enforcement
   point** so T-203 / T-403 / T-602 all inherit it.
4. **C4 — Renumber the ADR clash.** The store / hash-chain tamper-evidence ADR
   (T-100) collided with reserved ADR-0005 (sequential-scope). Renumbered to
   **ADR-0007**; T-100 writes under ADR-0007; the Open-ADR map and ARCHITECTURE.md
   updated (0002 hypervisor · 0003 SecGen-containerized · 0004 SO-primary-SIEM ·
   0005 sequential-scope · 0006 containment-authority+provisioning-window ·
   0007 store/tamper-evidence). T-110 stays blocked on T-100.
5. **C5 — Re-label the post-MVP critical path.** S3 (T-501/T-502/T-503) and
   T-403, T-602 are marked **POST-MVP CRITICAL PATH**, not slack. The full-project
   finish line is T-602 through T-503 → T-403; the orchestrator must not treat
   MVP exit at T-203 as project-done and drop containment to a slack stream.

## Safety edge (non-negotiable)

```
   T-502 (nft PRIMARY containment, host-verified via T-502b) ── guards T-203's MVP e2e
        ▼
   T-503b (tripwire + panic + arm/disarm, host-verified — emits IsolationVerified)
        │  HARD EDGE
        ▼
   T-403 (web LIVE attack) ── refused unless IsolationVerified present
        ▼
   T-602 (AD LIVE attack) ── inherits the same single-point refusal
```

A fail-closed orchestrator pre-flight refuses ANY live attack without an
`IsolationVerified` event. Enforced at **ONE point** (the orchestrator loop) so
**every** attack path inherits it: **T-502 → T-203** (MVP e2e), **T-503b →
T-403** (web live), T-403 → T-602 (AD live). No live attack runs before
containment is COMPLETE+host-verified.

## Hostile-review gates

> Every gate runs via the `clean-room-reviewer` agent in a **fresh subagent
> context** — given only the artifact + its acceptance spec, no project lore.
> **Inline / internal review does NOT satisfy a gate.** Difficulty and loop
> budget are scaled to blast radius and irreversibility. On budget exhaustion,
> **stop the milestone's dependents and escalate to a human** (HARD STOP 6).

| Gate | After task(s) | Why gated | Difficulty | Loop budget | Reviewers |
|---|---|---|---|---|---|
| **A — Scoring spine** | T-101 + T-110 + T-111 | max fan-out + tamper/replay correctness; hardest to change later | `adversarial` | 4 | **2× fresh clean-room (both must PASS)** |
| **B — Manifest-as-oracle e2e** | T-203 | the central product claim, on a real target | `hard` | 3 | 1× fresh clean-room |
| **C — F1 DETECT calibration** | T-304 | honesty of the DETECT pillar | `hard` | 2 | 1× fresh clean-room |
| **D — Containment + F2 + live-attack edge** | T-403 + M5 (T-502/T-503) | irreversible egress-escape blast radius | `adversarial` | 4 | **2× fresh clean-room (both must PASS) + RECOMMEND human final sign-off** |

### GATE A @ T-101 + T-110 + T-111 — the spine — ADVERSARIAL — budget 4 — MVP-BLOCKING

Two **independent fresh** reviewers, both must PASS:
- **Reviewer 1:** contracts / schema completeness / `version:int` on every
  persisted shape / fake-conformance (every fake satisfies its port; the
  adapter registry enumerates all eight slots).
- **Reviewer 2:** hash-chain integrity + fold/replay determinism +
  idempotency / seed-reroll (a pass under seed A is NOT reused after re-roll to
  seed B; `verify_chain` detects any tamper; replay reproduces the scoreboard).

### GATE B @ T-203 — manifest-as-oracle e2e — HARD — budget 3 — MVP RELEASE GATE

Verify: the full event sequence emits as specified; **replay reproduces the
scoreboard** (delete derived state → re-fold → identical); the **F2
functional-path** holds on the real target; and the **pre-flight refusal guards
the e2e attack** (no `IsolationVerified` → refused).

### GATE C @ T-304 — F1 DETECT calibration — HARD — budget 2 — post-MVP

Verify: `correct_ref` PASSES; `match_all_ref` FAILS the FP half;
`match_none_ref` FAILS the TP half; and the scorer **never branches on
`language`** (treats `DetectionRule.query` as an opaque blob).

### GATE D @ T-403 + M5 (T-502 / T-503) — containment invariant + F2 honesty + live-attack edge — ADVERSARIAL — budget 4 — post-MVP, gates ALL live attack

Two **independent fresh** reviewers, both must PASS:
- **Reviewer 1 (containment):** both planes enforced incl. **IPv6 / DNS**
  (vboxnet AND Docker bridge); tripwire fires `panic()` on ANY egress; the
  in-guest probe is corroboration-only and NEVER grants a pass; the arm/disarm
  provisioning-window invariant holds; `tripwire_egress_count == 0` asserted
  across the window.
- **Reviewer 2 (live-attack edge):** a live attack is **structurally refused**
  without `IsolationVerified`, verified across **T-203 / T-403 / T-602**, with no
  bypass of the single enforcement point.
- **RECOMMEND a human final sign-off as the last loop** — egress-escape is
  irreversible.

## Escalation rule

If any gate exceeds its loop budget without a PASS, **stop forward work on that
milestone's dependents** and escalate to a human decision with the open findings
attached. Looping past budget is its own failure mode.

- **GATE A and GATE D budget-exhaustion are HARD STOPS** (per HARD STOP 6):
  escalate to a human; do NOT proceed on an unsound scoring spine (A) or
  unverified containment (D). An unsound spine corrupts every score; unverified
  containment risks irreversible egress.

## Scale / anti-over-engineering note

Project tier: **large** — an automated-adversary purple-team lab with a
single-host blast radius and an irreversible egress-escape failure mode. Four
clean-room gates is **proportionate** to that tier: two adversarial
(spine + containment) where correctness is load-bearing and hard to change, two
hard (e2e release + DETECT honesty).

Deliberately **ungated** (to avoid over-engineering): M0 repo hygiene
(T-001..T-007), the doc-only ADR tasks (T-006/T-007/T-100/T-301/T-501/T-701),
and the S1/S2 fake-skeleton work that touches no real target. Re-validate the
machinery if the tier changes.
