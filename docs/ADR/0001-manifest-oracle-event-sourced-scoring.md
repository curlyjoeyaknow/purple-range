# ADR-0001 — Manifest-as-oracle + event-sourced scoring as the platform spine

> Status: proposed (GO-WITH-FIXES from critic; 3 FATAL findings folded in 2026-05-30)
> Date: 2026-05-30
> Deciders: owner (memeworldorder2024), architect
> Supersedes: —

## Context

Purple Range (codename Phalanx) is a single-user, single-host purple-team
training lab — a clean rebuild of `cyber-range`. See [`docs/PRD.md`](../PRD.md),
the brainstorm spine [`docs/BRAINSTORM.md`](../BRAINSTORM.md), the architecture
[`docs/ARCHITECTURE.md`](../ARCHITECTURE.md), and the critic red-team
[`docs/RED-TEAM.md`](../RED-TEAM.md) (the 3 FATAL findings folded into this ADR).
The product
promise is that **every challenge scores three pillars** — ATTACK, DETECT,
MITIGATE — with MITIGATE worth the most. The whole project lives or dies on one
question: **how do we grade DETECT and MITIGATE honestly, against targets that
may be randomized, without hardcoding answers?**

The forces in play:

- **The current grading is fake.** `cyber-range`'s `bluectf` `splunk_search`
  validator runs a *hardcoded reference query* and the learner submits nothing —
  the DETECT pillar tests the lab author, not the learner. MITIGATE is
  honor-system. This is the top-ranked risk (BRAINSTORM Risk #1).
- **Targets must be randomizable to stay valuable.** A static target is solved
  once and worthless. SecGen produces randomized victims; a Vulhub CVE is
  deterministic but still must be graded without per-challenge hardcoding. A
  scoring approach that bakes in answers dies at the first re-roll.
- **State must be auditable, replayable, tamper-evident.** Automated threat
  actors write a per-run ground-truth JSONL; the owner wants to trust rank as a
  real progress signal. `~/.bluectf-progress.json` (a single mutable file) gives
  none of audit, replay, undo, or tamper-evidence.
- **Charter non-negotiables** (`ENGINEERING.md`, `CLAUDE.md`): append-only events
  with derived state; `version:int` on everything persisted; ports & adapters at
  every boundary; contracts before implementations. These are minimum patterns,
  not options.
- **Cheats are adversarial.** A learner (even one who is also the author) can
  game a naive grader: a "match-everything" detection rule trivially fires;
  "deny-everything"/break-the-service makes a re-attack "fail" and falsely passes
  MITIGATE (BRAINSTORM Risk #2). **The critic showed these cheats also defeat the
  *graders' own fixtures* if the oracles are authored blind** — see the FATAL
  fixes below.

What we know: the four panel lenses (generator, threat-actor, detection, scoring)
independently converged on the same spine — a manifest oracle plus an
event-sourced store. What we **don't** know yet, and route to OPEN-QUESTIONS:
the benign-baseline source for the FP gate (Q-006), whether DETECT grading
couples to a live SIEM or an offline-replay bundle (Q-007), and whether SQLite or
JSONL backs the store (Q-005). This ADR fixes the *shape* so those choices slot
in behind ports without disturbing the spine.

## Decision

> We will make a **versioned `vuln_manifest` (the oracle) the single source of
> grading truth, and persist all scoring as an append-only, hash-chained event
> log whose fold is the scoreboard** — so that randomized targets stay scorable,
> all three pillars are graded against the manifest and observed-outcome
> ground-truth (never hardcoded answers), and state is auditable, replayable, and
> tamper-evident.

The design:

**1. Manifest-as-oracle.** The `ScenarioGenerator` port emits a
`VulnManifest(version:2)` per run that travels *with* the target: the vulns
present and, per vuln, the expected `attack` TTPs, the `detect` oracle, and the
`mitigate` oracle. A fresh seed yields a fresh manifest with a `manifest_hash`.
The scorer reads the manifest; it never embeds answers.

**1a. Oracles must prove they discriminate (FATAL F1/F2 — folded in).** An
authored-blind threshold is worthless: a `max_false_positives` set too loosely
lets a "match-everything" rule pass the FP gate, and a single liveness
`service_probe` lets a "deny-everything" mitigation pass MITIGATE. So an oracle
is **AUTHORED only when it passes a mandatory, CI-gated calibration fixture:**

- **DETECT (F1):** the `detect` block carries a versioned
  `calibration{ correct_ref, match_all_ref, match_none_ref }`. Against its own
  ground-truth + benign windows the contracts CI stage asserts: (a) the
  reference-correct rule PASSES, (b) match-everything (`*`/`true`) FAILS the FP
  half, (c) match-nothing FAILS the TP half. The existing `marker.xml` golden
  test validates manifest *parsing*; this fixture validates *grading
  discrimination* — both required, neither substitutes.
- **MITIGATE (F2):** the `mitigate` block carries a `deny_all_ref`. CI asserts
  the `service_probe` (a) PASSES against the un-mitigated base snapshot (it is a
  real positive control, not always-red) and (b) FAILS against a reference
  deny-everything mitigation, exercising the **actual functional path** the
  mitigation could break — not just a `/` 200.

**2. Observed-outcome ground-truth.** The `ThreatActor` port emits an
`AttackEvent(version:1)` per TTP step recording `outcome:success|failed|partial`
(probed, not assumed) with `ts_start`/`ts_end` and a `correlation_id`. A flaky
attack that didn't land neither scores ATTACK nor penalizes DETECT. A
mid-playbook crash emits `scenario_aborted` (M4) so a truncated window is folded
UNGRADEABLE rather than penalizing the learner.

**3. Three-pillar grading** (full mechanics in
[ARCHITECTURE §grading](../ARCHITECTURE.md#the-3-pillar-grading-mechanics)):

| Pillar | Oracle | Pass condition |
|---|---|---|
| ATTACK | manifest | learner TTP ∈ `expected_ttps` OR matches an auto `attack_event` with `outcome:success` |
| DETECT | ground-truth (three-window TP+FP) | learner query returns `>= expected_min_hits` over `[t_start,t_end]±skew_budget` **AND** `<= max_false_positives` over a benign baseline window; calibration-fixture-proven (F1) |
| MITIGATE | re-attack | re-run from `base` snapshot → `outcome:"blocked"` **AND** `service_probe` healthy on the functional path; deny-everything-fixture-proven (F2) |

The **Clock port governs the grading-window math** (M2): victim↔host skew is
measured at onboard and stored on the manifest; the DETECT correlation
reconciles SIEM ingest timestamps to actor Clock time using that offset plus a
versioned `skew_budget` — otherwise NTP-blocked clock skew makes the three-window
correlation non-replayable and the Clock port decorative.

**4. Event-sourced, hash-chained store.** Six versioned event types —
`scenario_generated`, `attack_executed`, `scenario_aborted` (M4), `submission`,
`verification_result`, `score_awarded` — appended through an `EventStore` port.
Each row carries `seq`, `prev_hash`, `row_hash = H(prev_hash ||
canonical_json(event))`, plus `correlation_id`/`causation_id` lineage.
Invariants: `score_awarded` is emittable only against a referenced **passing**
`verification_result` and is **bound to that `verification_ref` AND
`manifest_ref`**; idempotency key **`(scenario_id, challenge_id, pillar,
manifest_hash)`** (M5 — `manifest_hash`/`seed` included so a pillar passed under
seed A is *not* reused after a re-roll to seed B); an un-terminated
correlation_id folds INCOMPLETE/UNGRADEABLE (M4); the scoreboard is a **fold**
over the log; `verify_chain()` detects tampering/reordering. Backed by
`SqliteEventStore` in production (→ Q-005), `InMemoryEventStore` in tests.

**4a. Containment authority is host-side and continuous (FATAL F3 — folded in;
ADR-0006 reserved).** The original point-in-time `verify_contained()` pre-flight
was TOCTOU (containment can break *during* an attack), trusted the guest, and was
vboxnet-shaped while the MVP runs in Docker. Redesigned: the **PRIMARY gate** is
the host-side `nft` forward-drop; the **real gate** is a **host-side continuous
egress tripwire** armed for the *whole* attack window that fires `IsolationFailed`
+ `panic()` on ANY egress packet; the in-guest probe is **corroboration only,
never the pass condition**. The model and `IsolationReport(version:2)` explicitly
cover **IPv6** (nft `inet`/`ip6tables`), **DNS egress**, and the **Docker bridge**
(compose networks have their own egress not governed by the vboxnet chain). This
is a redesign of the *locus of authority*, not a tweak; it is reserved as
**ADR-0006 (containment-authority: host-side-continuous)**.

**5. Honor-system quarantine.** Un-automatable evidence is scored in a separate
**UNVERIFIED** bucket that does not count toward rank.

This ADR fixes the spine. Adapter- and phase-specific choices are reserved to
follow-on ADRs (see Links).

## Consequences

- **Positive:**
  - Randomized targets become scorable — the manifest makes "different every run"
    gradeable with zero scorer changes. This is the capability the whole product
    rests on.
  - DETECT is honest **and proven so**: the learner submits, we run it, and the
    F1 calibration fixture proves the threshold actually discriminates (match-all
    fails FP, match-none fails TP) — closing the "authored-blind threshold" hole.
  - MITIGATE is cheat-resistant **and proven so**: the F2 deny-everything fixture
    proves the `service_probe` detects a broken service on the functional path,
    not just liveness.
  - Containment is enforced by a host-side **continuous** tripwire, closing the
    TOCTOU + guest-trust + Docker-blind holes (F3).
  - Audit, replay, undo, and tamper-EVIDENCE come nearly free from the event log
    (charter #1, #4) — rank is trustworthy.
  - Q-005/Q-006/Q-007 slot in behind the `EventStore` and `Telemetry` ports
    without disturbing the spine.

- **Negative:**
  - The detect/mitigate oracles are **manual to author per vuln class** AND now
    **must each ship a calibration/negative fixture** (F1/F2) — more author cost,
    but it is the cost of honest grading and it is CI-enforced so it cannot be
    skipped. Mitigated by starting with a small N via the Vulhub fast path (Q-008).
  - **Manifest drift** becomes a first-class risk: a SecGen `marker.xml` shape
    change can silently mis-map the oracle (Risk #5). Mitigated by schema-validation
    on ingest, a versioned manifest, and a CI golden-file test.
  - Hash-chaining adds ~250–350 LOC and a canonical-JSON discipline (stable key
    order) over a plain JSON file — still stdlib-only. It buys tamper-EVIDENCE,
    not tamper-RESISTANCE (M3).
  - The continuous tripwire adds a host-side sensor process running for the whole
    attack window (m3 owner-tailable as a structured-log + JSONL ledger).

- **Neutral / deferred:** the live-SIEM-vs-offline-replay grading coupling
  (Q-007) is deferred behind the `Telemetry` port; the benign-baseline source
  (Q-006) is deferred behind `capture_baseline`. SQLite-vs-JSONL (Q-005) is
  deferred but defaulted to SQLite, justified below.

- **Reversibility:** **months** to undo the spine choice once challenges and the
  event log exist — this is the load-bearing decision, deliberately settled
  first. But the *plumbing* behind the ports (store backend, SIEM, baseline
  source, containment adapter) is **hours-to-days** reversible by design, because
  each is an adapter.

This decision **honors** the charter (it implements #1/#2/#3/#4 directly). The
one deviation — SQLite over the small-tier JSONL default — is justified below
(M3) and recorded as Q-005 for explicit owner sign-off rather than papered over.

## Risks (corrected wording)

🟡 Flagged in the brainstorm, accepted here after the `critic` pass and folded
fixes:

- **Risk #2 — break-the-service MITIGATE cheat:** closed by the two-sided
  re-attack assertion **and proven** by the F2 deny-everything negative fixture.
- **Risk #3 — SecGen build non-determinism (M1, corrected claim):** SecGen boxes
  are **PINNED-BY-CACHED-OUTPUT-BOX** — built once on `/mnt/data`, the output box
  cached, **never rebuilt from seed in normal operation**. We do **not** claim
  "reproducible-by-rebuild": the default path uses live apt (Q-012 Option B), so
  a months-later rebuild can drift/fail. Rebuild-reproducibility is claimable
  **only** if Q-012 Option A (frozen apt snapshot) is adopted. Vulhub CVE images
  remain deterministic by `@sha256` pin regardless. (Acceptable post-MVP; the
  claim is corrected now.)
- **Risk #5 — manifest drift:** accepted with schema-validation + versioning +
  CI golden-file as the falsifiable guard.

## Charter-deviation justification — SQLite over the small-tier JSONL default (Q-005, M3)

Restated to the **true** reasons (the prior "concurrent writers" rationale is
**dropped** — at sequential/single-user scope there is exactly ONE logical
scoring writer: the actor writes its own ground-truth JSONL, and the orchestrator
is the sole scoring-log writer):

1. **Transactional multi-row append for the hash-chain invariant.** A single
   logical step can emit several chained rows (e.g. `verification_result` +
   `score_awarded`); SQLite gives an atomic multi-row transaction so a partial
   write can never leave a broken chain. A bare JSONL append has no transaction
   boundary across rows.
2. **Indexed `replay_from(seq)` / `verify_chain()` over a real table.** A
   monotonic indexed `seq` column makes seek-replay and chain-verification
   O(log n) over a table rather than a full-file scan.

The hash chain is **tamper-EVIDENCE, not tamper-RESISTANCE** (M3): it is a
corruption / accidental-edit / reorder tripwire. The sole owner of the file can
legitimately re-fold and re-chain at will, so it does not *resist* a determined
owner — and it does not need to, for a solo lab. That is the honest property.

## Alternatives considered

### Alternative 1 — Hardcoded per-challenge verify (the status quo)

- **What it would look like:** keep `bluectf`'s model — each challenge embeds a
  reference detection query and a fixed mitigation check; the scorer runs the
  author's answer and marks the learner complete.
- **Why not:** it is **the fake grading we are rebuilding away from**. It tests
  the author, not the learner (DETECT submits nothing); it cannot grade a
  randomized target (the embedded answer is wrong the moment SecGen re-rolls);
  and it offers no defense against the match-everything / deny-everything cheats.
  It directly contradicts the product promise.

### Alternative 2 — Honor-system "done" for all blue pillars

- **What it would look like:** the learner self-attests DETECT and MITIGATE
  ("I saw it fire", "I hardened it"); the scorer trusts the claim. Trivial to
  build (it's most of today's `bluectf done`).
- **Why not:** it makes rank meaningless — there is no falsifiable test that the
  detection actually fired on real ground-truth or that the mitigation actually
  blocked the re-attack. The owner explicitly wants rank to be a *real* progress
  signal. We keep honor-system only for genuinely un-automatable evidence, and
  quarantine it in a non-ranking UNVERIFIED bucket.

### Alternative 3 — Manifest oracle, but non-event-sourced mutable state

- **What it would look like:** adopt the manifest oracle and honest three-pillar
  grading, but persist results to a mutable `progress.json` / a CRUD `scores`
  table updated in place (no append-only log).
- **Why not:** it throws away audit, replay, undo, and tamper-evidence — the
  exact properties that make a solo scoreboard trustworthy and that the charter
  mandates (#1, #4). A corrupted write is unrecoverable with no log to re-fold,
  and a partial multi-row update (verification + award) can leave the scoreboard
  inconsistent with no transactional boundary. The incremental cost of
  append-only-with-fold over CRUD is small now and unbuyable after the data is
  live (charter rationale).

## Accepted risks

🟡 Accepted after the `critic` pass and OPEN-QUESTIONS resolution:

- **Oracle-authoring burden (now incl. F1/F2 fixtures)** — accepted because the
  Vulhub fast path lets us prove the spine with a small N (Q-008), and the
  fixtures are the minimum proof that grading is honest. Revisit if authoring an
  oracle + fixtures per vuln class proves slower than ~one evening each.
- **Manifest drift** (Risk #5) — accepted with schema-validation + versioning +
  CI golden-file as the falsifiable guard.
- **SQLite over JSONL** (Q-005) — accepted as justified above (transactional
  multi-row append + indexed replay; NOT concurrency); **owner sign-off
  required** before the scoring-engine phase is decomposed.
- **DETECT live-SIEM coupling** (Q-007) — accepted for v1 with the `Telemetry`
  port + `ReplayLogBundle` fake shaped to admit an offline-replay adapter later.
- **SecGen pinned-by-cached-output-box, not reproducible-by-rebuild** (M1) —
  accepted for MVP; rebuild-reproducibility deferred to Q-012 Option A.

> Per CLAUDE.md non-negotiable #9, this ADR was red-teamed by the `critic`
> (GO-WITH-FIXES; 3 FATAL findings F1/F2/F3 folded in here and in ARCHITECTURE,
> 5 MATERIAL M1–M5 addressed, 5 MINOR m1–m5 recorded). Fatal findings triggered
> redesign (containment authority, F3), not a paper-over.

## Links

- PRD: [`docs/PRD.md`](../PRD.md)
- Architecture: [`docs/ARCHITECTURE.md`](../ARCHITECTURE.md) (§manifest-as-oracle data flow, §contracts, §grading, §state model, §containment model)
- Brainstorm spine: [`docs/BRAINSTORM.md`](../BRAINSTORM.md)
- Open questions: [`docs/OPEN-QUESTIONS.md`](../OPEN-QUESTIONS.md) — Q-005, Q-006, Q-007, Q-008, Q-012
- **Reserved follow-on ADRs** (split out at `/decompose`, NOT written here):
  - ADR-0002 — Hypervisor behind `LabProvider` (VirtualBox-now / libvirt-deferred)
  - ADR-0003 — SecGen containerized toolchain
  - ADR-0004 — Security Onion as primary SIEM (Splunk optional)
  - ADR-0005 — Sequential / scenario-scoped scope
  - **ADR-0006 — Containment authority: host-side-continuous egress tripwire (F3)**
</content>
