# OPEN-QUESTIONS

Unresolved decisions that block, slow, or shape the work. Maintained by the
`docs-keeper` agent. A question only leaves this file in two ways:

- **Resolved**: becomes an ADR (link both ways).
- **Withdrawn**: moot due to a change elsewhere — note the reason.

> Seeded 2026-05-30 from `docs/BRAINSTORM.md` (society-of-minds brainstorm for
> Purple Range). All `[owner]` defaults below are "confirmed-by-default unless
> vetoed" — they reflect locked-or-leaning decisions from convergence.

> **2026-05-30 — critic GO-WITH-FIXES folded in.** 3 FATAL (F1 DETECT
> grading-calibration fixture, F2 MITIGATE deny-everything fixture, F3
> containment-authority redesign → **ADR-0006 reserved**) and 5 MATERIAL
> (M1–M5) closed in ARCHITECTURE.md + ADR-0001. The few owner-facing residues
> surfaced by the fixes are tracked as Q-014/Q-015/Q-016 below. Full finding
> ledger with resolution status: [`docs/RED-TEAM.md`](RED-TEAM.md); milestone
> spine: [`docs/TODO.md`](TODO.md).

## Active questions

### Q-002 — Accept a semi-manual Security Onion install step, or build the unattended path?

- **Raised:** 2026-05-30 in BRAINSTORM.md (Risk #8)
- **Type:** technical
- **Blocks:** the "reproducible from one command" claim for any SO-bearing phase
- **What we know:**
  - SO `so-setup` is interactive by default → fights one-command reproducibility.
  - SO ships an unattended/airgap install path; Fleet tokens can be pre-minted.
- **What we don't:**
  - The effort cost of a fully-unattended SO install vs the documentation cost
    of a semi-manual step.
- **Options on the table:**
  - A. Document a semi-manual SO setup step — fast now, breaks one-command.
  - B. Invest in the unattended/airgap install path + pinned ISO — more build,
    preserves one-command reproducibility.
- **Who needs to weigh in:** owner
- **Decision deadline:** before the detection-data-plane phase is decomposed
- **Default if no decision by deadline:** Option B — pursue the unattended/airgap
  path with a pinned ISO and pre-minted Fleet tokens, since one-command
  reproducibility is a load-bearing project goal.

### Q-003 — Confirm Splunk is demoted to an optional Windows/Sysmon teaching lens?

- **Raised:** 2026-05-30 in BRAINSTORM.md (Detection data-plane)
- **Type:** technical
- **Blocks:** nothing — confirmation of a default
- **What we know:**
  - Splunk Free = 500 MB/day + NO scheduled alerting → cannot host
    detection-as-code.
  - Two SIEMs double RAM; Security Onion/Elastic is the chosen single grading
    pane and frees ~8 GB.
- **What we don't:** whether the owner wants Splunk kept first-class regardless.
- **Options on the table:**
  - A. Splunk OPTIONAL behind a flag, Security Onion/Elastic primary — chosen
    default.
  - B. Keep Splunk first-class — costs RAM and re-introduces the alerting ban.
- **Who needs to weigh in:** owner
- **Decision deadline:** before the detection-data-plane phase is decomposed
- **Default if no decision by deadline:** Option A — Splunk optional, Security
  Onion/Elastic primary.

### Q-004 — Confirm v1 threat-actor autonomy is a bounded allowlisted technique set (no autonomous exploit-selection)?

- **Raised:** 2026-05-30 in BRAINSTORM.md (Threat actors; Recorded dissent)
- **Type:** security 🔐
- **Blocks:** the ThreatActor runner design + containment risk model
- **What we know:**
  - Autonomous exploit-selection raises containment + ethics stakes
    (actor picks its own egress destination).
  - Bounded allowlisted set is deterministic and replayable.
- **What we don't:** whether the owner wants autonomous selection later, and
  under what additional containment.
- **Options on the table:**
  - A. Bounded allowlisted technique set for v1 — chosen default; lower
    containment/ethics risk.
  - B. Autonomous exploit-selection now — higher capability, much higher
    containment + ethics burden.
- **Who needs to weigh in:** owner
- **Decision deadline:** before the threat-actor phase is decomposed
- **Default if no decision by deadline:** Option A — bounded allowlisted set for
  v1; autonomous selection deferred to a future ADR.

### Q-005 — Approve a hash-chained SQLite scoring event store (vs the charter's small-tier JSONL default) at large tier?

- **Raised:** 2026-05-30 in BRAINSTORM.md (Scoring engine; Recorded dissent)
- **Type:** data
- **Blocks:** the scoring event-log implementation; deviates from charter
  non-negotiable #4's small-tier "one JSONL file" default
- **What we know (UPDATED 2026-05-30 per critic M3 — justification corrected):**
  - The "concurrent writers" reason is **DROPPED**: at sequential/single-user
    scope there is ONE logical scoring writer (the actor writes its own
    ground-truth JSONL; the orchestrator is the sole scoring-log writer).
  - The TRUE reasons SQLite is chosen: (1) **transactional multi-row append** so
    a multi-event step (verification_result + score_awarded) can never leave a
    broken hash chain; (2) **indexed `replay_from(seq)` / `verify_chain()`** over
    a real table with a monotonic `seq` column.
  - The hash chain is **tamper-EVIDENCE** (corruption / accidental-edit / reorder
    tripwire), NOT tamper-RESISTANCE — the sole owner can legitimately re-fold /
    re-chain. That is the honest property.
  - SQLite is stdlib (`sqlite3`); net add ~250–350 LOC, still stdlib-only.
- **What we don't:** whether the owner prefers to hold the JSONL default and
  accept full-file scans + no multi-row transaction.
- **Options on the table:**
  - A. SQLite append-only + hash-chained — transactional multi-row + indexed
    replay; deviates from default. **Recommended.**
  - B. One JSONL file — matches the charter default; no transaction boundary
    across rows, full-file scan for replay/verify.
- **Who needs to weigh in:** owner
- **Decision deadline:** before the scoring-engine phase is decomposed
- **Default if no decision by deadline:** Option A — SQLite append-only +
  hash-chained, justified (per M3) in ADR-0001 by transactional multi-row append
  + indexed replay, NOT concurrency.

### Q-006 — What is the benign baseline source for the false-positive gate?

- **Raised:** 2026-05-30 in BRAINSTORM.md (Detection grading oracle)
- **Type:** technical
- **Blocks:** the three-window TP+FP grading oracle (the FP half) AND the F1
  calibration fixture's FP-half references (match_all_ref must FAIL the FP gate
  against this baseline)
- **What we know:**
  - The oracle runs the learner's detection over a recorded BENIGN baseline
    window and requires `<= max_false_positives`.
  - The F1 calibration fixture is evaluated against this same baseline, so the
    baseline must be stable enough that a match-everything rule reliably trips
    the FP gate.
- **What we don't:** whether the baseline is canned/shipped or captured live.
- **Options on the table:**
  - A. Ship a canned baseline log/PCAP bundle — deterministic, portable; may not
    match a given victim's noise profile.
  - B. Capture a live idle window at range-up — matches the actual environment;
    adds a capture step and non-determinism.
- **Who needs to weigh in:** owner, with expert (detection-engineering) input
- **Decision deadline:** before the detection grading oracle is implemented
- **Default if no decision by deadline:** Option A — ship a canned baseline
  bundle for determinism (also makes the F1 fixture deterministic in CI); revisit
  live capture as a v2 hardening.

### Q-007 — DETECT grading: couple to a live SIEM at verify time, or to an offline-replayable log bundle?

- **Raised:** 2026-05-30 in BRAINSTORM.md (Detection grading oracle; Recorded dissent)
- **Type:** technical
- **Blocks:** the verify-time architecture of the DETECT pillar
- **What we know:**
  - Live-SIEM-at-verify is simpler to build but couples the scorer to a running
    Security Onion at grade time.
  - Offline-replayable log bundle is more honest/portable but more build.
  - Either way the scorer (not the adapter) owns the grading-window math incl.
    the M2 `skew_budget` (see Q-015).
- **What we don't:** whether portability/replay justifies the extra build now.
- **Options on the table:**
  - A. Live-SIEM-at-verify — least build; requires SO up during grading.
  - B. Offline-replayable log bundle — portable, honest, replayable; more build.
- **Who needs to weigh in:** owner
- **Decision deadline:** before the detection grading oracle is implemented
- **Default if no decision by deadline:** Option A for v1 (live-SIEM-at-verify),
  with the contract shaped so an offline-replay adapter can be added behind the
  same port later.

### Q-008 — Accept starting with a SMALL N of fully-oracled vuln classes rather than all ~1000 SecGen modules?

- **Raised:** 2026-05-30 in BRAINSTORM.md (Open questions)
- **Type:** product
- **Blocks:** scope of the first scorable challenge set
- **What we know:**
  - SecGen gives the attack side free; the two high-value pillars
    (detect + mitigate) oracles are MANUAL to author per vuln class — and each
    now also ships a CI-gated calibration/negative fixture (F1/F2), adding to the
    per-class authoring cost.
  - Authoring all ~1000 modules' detect/mitigate oracles up front is infeasible.
- **What we don't:** who authors the oracles, and how large the initial N is.
- **Options on the table:**
  - A. Start with a small N of fully-oracled vuln classes (Vulhub-CVE fast path
    first) — proves the wiring this week; grows incrementally.
  - B. Attempt broad coverage up front — slow, blocks first scored challenge.
- **Who needs to weigh in:** owner (and whoever authors the oracles)
- **Decision deadline:** before the scenario-generator/oracle authoring phase is decomposed
- **Default if no decision by deadline:** Option A — start with a small N of
  fully-oracled vuln classes via the Vulhub-CVE fast path; grow the catalog
  incrementally.

### Q-010 — GOAD-full (~24–32 GB, 5 Windows VMs) or GOAD-Light (3 VMs)?

- **Raised:** 2026-05-30 in BRAINSTORM.md (Host profile / Open questions)
- **Type:** technical
- **Blocks:** the AD/GOAD phase scenario spec
- **What we know:**
  - Host has 60 GB RAM (~55 usable). Disk is no longer a constraint — Q-001
    RESOLVED (1.7 TB free on `/mnt/data` NVMe; lab artifacts stored there).
  - GOAD-full (~24–32 GB) is reachable solo; SO (16 GB) + GOAD as an adjacent
    pair ≈48 GB is tight but within ~55 GB usable; GOAD-Light is 3 VMs.
  - `panic()` VM-pause is serial/best-effort and exceeds 1 s with GOAD-full's 5
    VMs (m4) — containment never waits on the pause; the host nft egress-cut
    (sub-second) is the guarantee.
- **What we don't:** whether the owner wants the leaner footprint regardless.
- **Options on the table:**
  - A. GOAD-full — richer AD attack surface; fits the host solo; pair is tight
    but feasible. **Recommended (disk no longer a constraint).**
  - B. GOAD-Light (3 VMs) — leaner RAM footprint; less coverage.
- **Who needs to weigh in:** owner (owner-confirmable)
- **Decision deadline:** before the AD/GOAD phase is decomposed
- **Default if no decision by deadline:** Option A — **GOAD-full**. With Q-001
  resolved, disk is no longer a constraint and RAM is sufficient solo;
  GOAD-Light only if the owner prefers the leaner footprint.

### Q-011 — Which exact SecGen commit + known-good frozen base box do we pin?

- **Raised:** 2026-05-30 during `/plan` (ARCHITECTURE pinned-versions table; ADR-0001 SecGen build non-determinism)
- **Type:** technical
- **Blocks:** the `SecGenContainer` adapter pin (ADR-0003); reproducibility of phase-5
- **What we know:**
  - SecGen is a rolling repo with **no releases**; its README pins Vagrant 2.2.9
    (Ubuntu 20.04), Ruby 3.2, Packer, ImageMagick, libvirt — to be run inside the
    pinned OCI image so it never collides with host Vagrant 2.4.3.
  - Build non-determinism (Risk #3): even a fixed seed reaches apt/Packer/forge,
    so the same seed can yield a non-booting box months later unless the base box
    and apt state are frozen/cached. Per M1 the box is **pinned-by-cached-output-
    box** (built once, output cached, never rebuilt in normal operation), NOT
    reproducible-by-rebuild.
- **What we don't:** which SecGen commit builds cleanly on the pinned toolchain,
  and which frozen base box + (optional) offline apt mirror snapshot to cache.
- **Options on the table:**
  - A. Pin a specific SecGen commit verified to build, plus a cached frozen base
    box on `/mnt/data` — deterministic-by-cache, more setup.
  - B. Track SecGen master and accept occasional rebuild breakage — less setup,
    fails the reproducibility goal for phase-5.
- **Who needs to weigh in:** owner
- **Decision deadline:** before the SecGen/phase-5 generator phase is decomposed
- **Default if no decision by deadline:** Option A — pin a verified commit + cache
  a frozen base box; SecGen is must-have but NOT critical-path-blocking, so this
  resolves after the Vulhub fast path proves the spine.

### Q-012 — Offline apt-mirror snapshot for SecGen/victim builds, or accept live apt at provision?

- **Raised:** 2026-05-30 during `/plan` (Risk #3 mitigation depth)
- **Type:** technical
- **Blocks:** the determinism guarantee of generated-victim builds; how "NAT-on
  only during provision" interacts with reproducibility; **which reproducibility
  CLAIM the SecGen section may make (M1)**
- **What we know:**
  - Risk #3's full mitigation calls for an "offline apt mirror snapshot" so a
    rebuild months later resolves the same packages.
  - Provisioning is the only sanctioned NAT-on window; a frozen mirror would let
    even that be cut.
  - **M1 (critic):** with the default (Option B, live apt), "reproducible-by-
    rebuild" is FALSE and must NOT be claimed — only "pinned-by-cached-output-
    box". Claiming rebuild-reproducibility REQUIRES Option A.
- **What we don't:** whether the determinism payoff justifies hosting and storing
  an apt mirror snapshot on `/mnt/data`.
- **Options on the table:**
  - A. Host a frozen apt mirror snapshot on `/mnt/data` — fully reproducible
    (rebuild-reproducibility claimable), NAT-never even at provision; storage +
    maintenance cost.
  - B. Accept live apt during the provision NAT-on window — simpler; rebuilds may
    drift; only the cached-output-box claim is honest.
- **Who needs to weigh in:** owner
- **Decision deadline:** before phase-5 (SecGen) is decomposed; lower priority for
  the Vulhub fast path (CVE images are `@sha256`-pinned, deterministic by
  construction)
- **Default if no decision by deadline:** Option B for the fast path (images are
  digest-pinned anyway), with the SecGen section claiming only "pinned-by-cached-
  output-box" (M1); revisit Option A only if SecGen rebuild drift bites or
  rebuild-reproducibility is ever required.

### Q-013 — GOAD has no clean semver release: which commit do we pin off `v3.0.0`?

- **Raised:** 2026-05-30 during `/plan` (pinned-versions lookup, charter rule 10)
- **Type:** technical
- **Blocks:** the GOAD/phase-4 pin; reproducibility of the AD forest
- **What we know:**
  - GOAD's latest "release" tag is `v3.0.0` (2024-11-29), described as a "V3 beta
    merge into main" — development continues on `main` past the tag, so the
    floating tag/branch is not a stable pin.
  - Charter rule 10 requires a pinned ref, not a floating branch.
- **What we don't:** which specific commit builds the chosen GOAD-full forest
  cleanly on the host (VirtualBox 7.1.18 / Vagrant 2.4.3).
- **Options on the table:**
  - A. Pin a specific verified commit at/after `v3.0.0` — reproducible.
  - B. Track `main` — risks drift/breakage on rebuild.
- **Who needs to weigh in:** owner
- **Decision deadline:** before the GOAD/phase-4 phase is decomposed
- **Default if no decision by deadline:** Option A — pin a verified commit;
  GOAD-full chosen (Q-010), so the pin is selected during phase-4 build-out.

### Q-014 — Who authors the F1/F2 oracle fixtures, and is the calibration suite a per-challenge gate or a sampled gate?

- **Raised:** 2026-05-30 (critic F1/F2 — folded into ARCHITECTURE + ADR-0001)
- **Type:** product / process
- **Blocks:** the contracts CI stage definition and the oracle-authoring workflow
- **What we know:**
  - F1 requires each DETECT oracle to ship
    `calibration{correct_ref, match_all_ref, match_none_ref}` proving the
    threshold discriminates (correct PASSES, match-all FAILS FP, match-none FAILS
    TP). F2 requires each MITIGATE oracle to ship a `deny_all_ref` proving the
    `service_probe` PASSES un-mitigated and FAILS deny-everything on the
    functional path.
  - These are CI-gated in the contracts stage; a challenge without passing
    fixtures is rejected (build red).
- **What we don't:** whether every challenge must carry its own fixtures from day
  one, or whether a shared/templated reference set is acceptable for a family of
  similar CVEs to reduce authoring cost.
- **Options on the table:**
  - A. Per-challenge mandatory fixtures — strongest honesty guarantee; highest
    authoring cost. **Recommended (matches F1/F2 as written).**
  - B. Templated/shared reference fixtures per vuln-family — cheaper; risks a
    family template that does not actually discriminate for an outlier member.
- **Who needs to weigh in:** owner (and whoever authors the oracles)
- **Decision deadline:** before the scoring-engine / oracle-authoring phase is decomposed
- **Default if no decision by deadline:** Option A — per-challenge mandatory
  fixtures, consistent with F1/F2; revisit templating only if authoring cost
  proves prohibitive after the small-N fast path.

### Q-015 — Default `skew_budget_s` and the victim↔host clock-offset measurement method?

- **Raised:** 2026-05-30 (critic M2 — folded into ARCHITECTURE + ADR-0001)
- **Type:** technical
- **Blocks:** the DETECT three-window correlation math; replayability of DETECT grading
- **What we know:**
  - NTP egress is blocked by containment, so victim/SIEM/actor clocks WILL skew.
  - Fix is twofold: a versioned `skew_budget_s` pad on the correlation window AND
    measuring victim↔host offset at onboard, stored on the manifest
    (`clock_offset_s`) for window correction; prefer correlating on
    `correlation_id` / host+technique where the log format allows.
  - The Clock port governs this grading-window math (reconciling SIEM ingest
    timestamps to actor Clock), not just event emission.
- **What we don't:** the numeric default for `skew_budget_s`, and whether offset
  is measured once at onboard or re-sampled (clocks drift over a long window).
- **Options on the table:**
  - A. Single offset measured at onboard + a conservative `skew_budget_s` pad
    (e.g. 30 s) — simple; may under-correct on long windows.
  - B. Periodic re-measurement of offset during the attack window — tighter; more
    machinery.
- **Who needs to weigh in:** owner, with detection-engineering input
- **Decision deadline:** before the detection grading oracle is implemented
- **Default if no decision by deadline:** Option A — measure offset once at
  onboard, store `clock_offset_s` on the manifest, default `skew_budget_s` to a
  conservative pad; prefer `correlation_id`-based correlation where the log
  format carries it; revisit Option B only if long-window drift bites.

### Q-017 — Should the JSON-Schemas reject unknown keys (`additionalProperties: false`), or keep dropping them (forward-compat)?

- **Raised:** 2026-05-31 (T-101 GATE A clean-room — NIT, left intentional)
- **Type:** technical
- **Blocks:** nothing today; shapes the strictness contract a downstream
  strict-validation owner would change
- **What we know:**
  - The T-101 `contracts.SCHEMAS` deliberately do NOT set
    `additionalProperties: false`, so an unknown key on a persisted shape is
    **dropped, not rejected** on load.
  - This is consistent with the additive/forward-compat charter (#2: new fields
    are additive) — an older reader tolerates a newer writer's extra field.
- **What we don't:** whether a future consumer needs typo-detection strictness
  (a misspelled field silently vanishing) more than forward-compat tolerance.
- **Options on the table:**
  - A. Keep the current behaviour — unknown keys dropped; forward-compatible.
    **Chosen default (intentional at T-101).**
  - B. Set `additionalProperties: false` per schema — rejects unknown keys;
    catches typos but breaks an older reader against a newer writer.
- **Who needs to weigh in:** owner / downstream contract consumer
- **Decision deadline:** before any shape needs strict cross-version validation
- **Default if no decision by deadline:** Option A — forward-compat drop;
  add `additionalProperties: false` only where a specific shape needs strictness.

### Q-018 — Do `components` / `vulns` / `services` need a `minItems` cardinality floor?

- **Raised:** 2026-05-31 (T-101 GATE A clean-room — NIT, left intentional)
- **Type:** technical
- **Blocks:** nothing today; an empty-list shape currently validates
- **What we know:**
  - The T-101 schemas put **no `minItems` floor** on `components` / `vulns` /
    `services`, so a Scenario with zero components or a VulnManifest with zero
    vulns is schema-valid.
  - Consistent with the additive posture (a contract change to add a floor is a
    tightening, deferrable until a concrete consumer relies on non-emptiness).
- **What we don't:** which consumer first depends on a non-empty list (likely the
  Scorer T-111 / generator T-202) — that consumer should set the floor it needs.
- **Options on the table:**
  - A. No floor at the contract layer; consumers assert their own non-emptiness.
    **Chosen default (intentional at T-101).**
  - B. Add `minItems: 1` floors now — rejects degenerate shapes at the boundary.
- **Who needs to weigh in:** owner / Scorer (T-111) + generator (T-202) owner
- **Decision deadline:** when T-111/T-202 land (they are the first real consumers)
- **Default if no decision by deadline:** Option A — no contract-layer floor;
  the first consumer that requires non-emptiness adds the `minItems` it needs.

### Q-019 — Should port conformance verify method SIGNATURES, not just method presence?

- **Raised:** 2026-05-31 (T-101 GATE A clean-room — NIT, left intentional)
- **Type:** technical
- **Blocks:** nothing today; tightens fake↔port conformance guarantees
- **What we know:**
  - The 8 ports are `@runtime_checkable` Protocols, so `isinstance(fake, Port)`
    verifies **method presence, not signature** — a fake with a method of the
    right name but wrong arity/params still passes the structural check.
  - This is a known `typing.runtime_checkable` limitation, not a T-101 bug; the
    static type-checker (when wired) catches signature drift.
- **What we don't:** whether to add a signature-asserting conformance test (e.g.
  `inspect.signature` comparison) or rely on a future static-type gate in CI.
- **Options on the table:**
  - A. Accept presence-only runtime checks; rely on a static type-check CI stage
    for signature conformance. **Chosen default (intentional at T-101).**
  - B. Add an `inspect.signature`-based conformance test per port/fake — catches
    arity drift at runtime; more test machinery to maintain.
- **Who needs to weigh in:** owner / whoever wires the static-type CI stage
- **Decision deadline:** before the first parallel stream adds a real adapter
  whose signature could drift from its port (S1/S2/S3 fan-out)
- **Default if no decision by deadline:** Option A — presence-only runtime check
  now; add a signature gate (or the static-type CI stage) before stream fan-out
  if drift bites.

### Q-020 — How does the Scorer reducer get each event's type discriminator, tamper-evidently? [✅ RESOLVED 2026-06-02 → ADR-0007 Addendum 1, Option D]

- **✅ RESOLVED 2026-06-02 (Option D — frame `event_type` into the row hash):** decided
  via the mandatory `architect` → `critic` loop at the top of T-111 and recorded in
  **[ADR-0007 Addendum 1](ADR/0007-event-store-hash-chained-sqlite.md)**. `event_type` is
  folded into the framed row hash alongside `payload`
  (`sha256(prev_hash \x00 event_type \x00 canonical_bytes)`, utf-8) and promoted to a
  first-class yielded key — tamper-evident, on the read surface, and `payload` stays
  byte-for-byte `canonical_json(dump(event))` so the independent conformance oracle
  survives. Critic verdict: core sound (3 objections failed on evidence); 8 fixable
  findings all addressed before binding (see [`docs/RED-TEAM.md`](RED-TEAM.md) 2026-06-02).
  **Residual:** D authenticates `event_type` *immutability*, not its *correspondence to
  the payload it labels* (Option-C territory if T-111 dispatch needs it). **Next:**
  `tester` writes the mandated tests (negative + positive-discrimination + key-set) RED-first.
- **Raised:** 2026-05-31 (T-110 internal `reviewer`, 🔴 — see [`docs/RED-TEAM.md`](RED-TEAM.md) 2026-05-31)
- **Type:** technical / contract
- **Blocks:** **T-111 (Scorer) — must resolve as its FIRST move, before any reducer code.** Also inside GATE A scope. *(Now unblocked.)*
- **What we know:**
  - ADR-0007 §5 pins the reducer to dispatch on `(event_type, version)`.
  - T-110 stores `event_type` as a `events` column derived from the dataclass name,
    but it is **not** in the hashed `payload` and **not** in the `fold`/`replay_from`
    yielded dict. So the chain does NOT protect it: tampering the column to `'LIE'`
    keeps `verify_chain() == True`.
  - The event dataclasses carry no explicit discriminator field — shapes are
    distinguished structurally (field sets), which the reviewer flagged as fragile
    for a reducer to rely on.
- **What we don't:** which mechanism gives the reducer a discriminator that is BOTH
  available on the read surface AND tamper-evident.
- **Options on the table:**
  - A. **Additive discriminator field** on every event dataclass (`event_type: str`),
    so it's in `dump()` → hashed → yielded. Tamper-evident and clean, BUT a contract
    change → needs an ADR note + critic, and ripples to committed tests
    (`canonical_bytes_of` auto-includes it via `dump`; T-101 field-set assertions may
    need updating). Likely the right answer.
  - B. **Re-derive shape from payload** at read time (attempt `contracts.load_<shape>()`
    / structural match). No contract change; fragile and O(shapes) per row.
  - C. **Cross-check the column against the payload** in the reducer (dispatch on the
    column but assert it matches a payload-derived shape; mismatch → ungradeable).
    Cheapest; keeps the denormalized column but closes the tamper hole.
  - D. **Frame `event_type` into the hash alongside `payload`** (NOT into the payload
    dict), the way `prev_hash` already is:
    `row_hash = sha256(prev_hash_bytes + \x00 + event_type_bytes + \x00 + canonical_bytes)`.
    Raised by the 2026-06-02 `external-reviewer`. Makes `event_type` tamper-evident
    **without** changing the canonical payload bytes — so `payload` stays exactly
    `canonical_json(dump(event))` and the **independent** conformance oracle
    `conftest_t110.canonical_bytes_of` survives intact (Option A, by contrast, forces
    editing that oracle and makes `payload` no longer a faithful serialization).
    Localized to `framed_row_hash` + `chain_batch` (pass `event_type`) +
    `verify_rows`/`verify_chain` (also SELECT + frame `event_type`). Same chain-breaking
    migration cost as A, but cleaner; keeps `event_type` a real separately-stored column
    that happens to be authenticated rather than smuggled into the event.
- **Whichever option wins, the fix MUST land a negative test** —
  `test_verify_chain_detects_tampered_event_type` — the current suite has NO test that
  tampers a non-`payload` column, which is exactly how this slipped through.
- **Who needs to weigh in:** `architect` (contract impact) + `critic` (tamper-evidence) at the top of T-111.
- **Decision deadline:** start of T-111.
- **Default if no decision by deadline:** **Option D (frame-it)** — preferred over A on
  oracle-preservation grounds (keeps `payload == canonical_json(dump(event))` and leaves
  the independent test oracle unedited); confirm with `architect` + `critic` via a short
  ADR-0007 addendum. (Updated 2026-06-02 from A → D after the external review; A remains
  the fallback if framing proves to interact badly with re-hydration.)

### Q-021 — Should `append` harden the tip-read into its transaction, or rely on the single-writer scope? [non-blocking]

- **Raised:** 2026-06-02 (T-110 `external-reviewer`, 🟠 — see [`docs/RED-TEAM.md`](RED-TEAM.md) 2026-06-02)
- **Type:** technical / concurrency
- **Blocks:** nothing for the MVP (single-writer). Revisit if a second writer is ever introduced.
- **What we know:**
  - `SqliteEventStore.append` reads the chain tip via `_tip()` **outside** the
    transaction (`event_store.py:71`), then `chain_batch` computes off it (`:74`),
    then `BEGIN`/`executemany`/`commit` (`:76-85`). Nothing holds a write lock across
    the read→write gap.
  - Safe today **only** because of the ADR-0005 single-writer scope — lore that is
    invisible at the `append` call site. The T-110 tests themselves open second
    connections to the same file.
  - **Integrity is NOT at risk** under a concurrent writer: `seq` is `PRIMARY KEY`, so a
    duplicate-`seq` insert raises `IntegrityError` → rollback. No silent fork/corruption.
    The only exposure is **spurious append failures** under concurrency.
- **What we don't:** whether the project will ever want more than one writer (the current
  architecture says no).
- **Options:**
  - A. **Leave it** — document the single-writer precondition at the `append` call site
    (a comment + an ADR-0005 pointer). Zero code change; honest about the assumption.
  - B. **Harden now** — `BEGIN IMMEDIATE` and read the tip *inside* the transaction, so the
    read→write window is atomic and a second writer blocks rather than spuriously failing.
    Cheap, localized, makes the code correct without leaning on lore.
- **Who needs to weigh in:** `architect` (is single-writer a permanent invariant?).
- **Decision deadline:** at or after T-111 (not a GATE-A blocker).
- **Default if no decision by deadline:** Option B (harden) **if** it lands for free during
  the Q-020 rewrite of `append`/`_chain` (the rewrite already touches this path); otherwise
  Option A (document the precondition at the call site).

## Reserved ADR

- **ADR-0006 — Containment authority: host-side-continuous (RESERVED 2026-05-30,
  critic F3).** The TOCTOU + guest-trust + vboxnet-shaped pre-flight is redesigned
  so the **host-side nftables forward-drop is the primary enforcement** and a
  **host-side continuous egress tripwire (whole-window) is the real gate** that
  fires `IsolationFailed` + `panic()` on ANY egress packet; `verify_contained()`
  and the in-guest probe are demoted to corroboration only. The model + the new
  `IsolationReport(version:2)` explicitly cover **IPv6** (nft `inet`/`ip6tables`),
  **DNS egress**, and the **Docker bridge** plane (the Vulhub/web MVP runs in
  Docker, whose compose-network egress is NOT governed by the vboxnet nft chain).
  **Provisioning-window invariant (INVARIANT — closes the one SERIOUS
  non-fatal from the confirming critic pass):** the host-side egress tripwire
  is **DISARMED** during the sanctioned provisioning window (NAT-on, for
  `apt`/Packer/box-build per Q-012) and **RE-ARMED** before the first attack
  step. Provisioning traffic must never fire `panic()` (else benign apt/box
  egress would DoS the lab). Arm window is **[post-onboard/post-provision,
  pre-first-attack]** through **[end of attack/teardown]**; ADR-0006 must
  record this arm/disarm contract.
  Written out at `/decompose` of the containment/isolation phase.

## Expert / legal checkpoints ⚖️

Questions that genuinely need a human expert (lawyer, security pro, domain
specialist, regulator) — Claude does not make these calls.

- ⚖️ **Q-009** — Confirm comfort that the repo itself holds ONLY guides + MITRE
  mappings + detections, with live payloads ONLY in ephemeral gitignored
  pull-at-provision dirs (keeps it a training lab, not a weapons cache).
  - **Raised:** 2026-05-30 in BRAINSTORM.md (Safety / containment / ethics)
  - **Type:** legal ⚖️ / security 🔐
  - **Why it needs an expert:** the content line is a legal/ethical framing
    decision (defensible educational scope vs distributing offensive tooling),
    not a purely technical one.
  - **What we know:** plan is repo = run-guides + MITRE + detections + pinned
    REFERENCES; live malware/droppers/generated victims NEVER committed, pulled
    at provision time from pinned commits into gitignored work dirs; generated
    SecGen victims treated as untrusted, snapshot-bracketed, NAT-never; a
    one-page `SAFETY.md` documents authorized-self-training scope.
  - **Decision deadline:** before any offensive content reference or provisioning
    fetch is committed
  - **Default if no decision by deadline:** enforce the strict line (guides +
    MITRE + detections + pinned references only; no live payloads in-tree) and
    ship `SAFETY.md`; do not commit anything weapons-cache-adjacent until
    confirmed.
  - **Status:** pending

- ⚖️ **Q-006** *(also routed to expert)* — see Active questions above; benign
  baseline source benefits from detection-engineering input.
  - **Status:** pending

## Resolved (recent — older items live in ADRs)

| ID | Question | Resolution | ADR |
|---|---|---|---|
| Q-001 | Disk budget + image-cleanup policy (was 244 GB free) | **RESOLVED 2026-05-30** — second NVMe SSD (`/dev/nvme1n1`, 1.9 TB, LUKS+ext4, mounted `/mnt/data`, 1.7 TB free) found; ALL lab artifacts (VBox machine folder, Vagrant boxes, SecGen builds, gitignored `vendor/`, box cache) stored under `/mnt/data`, not root. Image-cleanup remains good practice but is no longer a blocker. RAM-sequential is now the only real ceiling. | _(no ADR yet — hardware fact, not a design choice)_ |

## Withdrawn

| ID | Question | Why withdrawn |
|---|---|---|
| — | (none yet) | — |
</content>
