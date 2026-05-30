# RED-TEAM

Risk reviews from `/critique` and `/phase-review`. Maintained by the
`docs-keeper` agent. This is where the `critic`'s findings live so future-you
can see what was considered and how it was resolved.

Findings use the critic's severity scale:

- 🔴 **Fatal** — proposal cannot ship as-is.
- 🟠 **Serious** — likely to bite within 6 months.
- 🟡 **Smell** — might be fine, but worth a sentence in the ADR.

Related docs: [`docs/PRD.md`](PRD.md) · [`docs/ARCHITECTURE.md`](ARCHITECTURE.md) ·
[`docs/ADR/0001-manifest-oracle-event-sourced-scoring.md`](ADR/0001-manifest-oracle-event-sourced-scoring.md) ·
[`docs/BRAINSTORM.md`](BRAINSTORM.md) · [`docs/OPEN-QUESTIONS.md`](OPEN-QUESTIONS.md) ·
[`docs/TODO.md`](TODO.md) · [`docs/DELIVERY-PLAN.md`](DELIVERY-PLAN.md)
(the hostile-review gates A–D in DELIVERY-PLAN exist to keep the FATAL findings
F1/F2/F3 below closed).

---

## 2026-05-30 — `/critique` on the planning bootstrap (PRD + ARCHITECTURE + ADR-0001)

> Target: `docs/PRD.md`, `docs/ARCHITECTURE.md`, `docs/ADR/0001-manifest-oracle-event-sourced-scoring.md`
> Invoked by: pm-orchestrator (post-`/plan`, pre-sign-off)
> Critic: `claude-opus` (hostile design red-team) + a second confirming pass

### What the critic understood the proposal to be

A single-user, single-host purple-team training lab (clean rebuild of
`cyber-range`) whose spine is **manifest-as-oracle + event-sourced scoring**:
the scenario generator emits a versioned manifest that is the source of truth
for grading three pillars (ATTACK / DETECT / MITIGATE), and progress is derived
by folding an append-only event log. The whole project lives or dies on whether
DETECT and MITIGATE can be graded **honestly** against possibly-randomized
targets, and whether the lab stays **provably network-contained** while
automated attackers run.

### Verdict

**GO-WITH-FIXES** → fixes folded into ARCHITECTURE.md + ADR-0001 →
**confirming pass: FIXES CONFIRMED, ready for sign-off.** The one new SERIOUS
non-fatal raised by the confirming pass (benign provisioning traffic tripping
`panic()`) is closed by the provisioning-window invariant folded into the
containment model and the ADR-0006 reservation.

### Resolved — 🔴 Fatal (all CLOSED; confirmed by the second critic pass)

- 🔴 **F1 — DETECT grading is uncalibrated (a match-everything rule could pass the FP gate).**
  - Violated assumption: that "learner query returns ≥ expected hits" proves detection skill.
  - Failure mode: a rule matching all events trivially clears the TP threshold; grading rewards noise as signal.
  - Falsifiable test: feed a match-everything rule and a match-nothing rule to the grader; if either passes, grading is broken.
  - **Addressed by:** mandatory per-challenge **calibration fixture** `calibration{correct_ref, match_all_ref, match_none_ref}` on `DetectionRule` v2 + the manifest `detect` block; a **contracts-CI gate** asserts `correct_ref` PASSES, `match_all_ref` FAILS the FP half, and `match_none_ref` FAILS the TP half — proven, not assumed. ARCHITECTURE.md grading-discipline section, ADR-0001. 2026-05-30.
  - **Residual:** tracked as **Q-014** (sole-author fixtures + dependency on the Q-006 benign baseline) — accepted/documented, not blocking.

- 🔴 **F2 — `service_probe` is a fig-leaf (a deny-everything "mitigation" passes MITIGATE).**
  - Violated assumption: that a live-service probe proves the service still works *and* is hardened.
  - Failure mode: blocking the port entirely (breaking the service) reads as "attack prevented" and scores MITIGATE.
  - Falsifiable test: run the probe against a reference deny-everything config; if it PASSES, the gate is a liveness check, not a functional one.
  - **Addressed by:** mandatory `deny_all_ref`; the CI gate requires the probe to **PASS on the un-mitigated base** AND **FAIL on the reference deny-everything**, exercising the actual functional path (not liveness). ARCHITECTURE.md, ADR-0001. 2026-05-30.

- 🔴 **F3 — Containment is TOCTOU + guest-trusting + vboxnet-shaped while the MVP is Docker.**
  - Violated assumption: that a point-in-time, in-guest pre-flight probe proves isolation for the whole attack window.
  - Failure mode: containment can break *during* an attack; an in-guest probe trusts a host the lab declares hostile; the vboxnet-only model ignores the Docker bridge plane and IPv6/DNS egress.
  - Falsifiable test: break egress mid-attack (or send an IPv6/DNS packet, or egress via the Docker bridge); if grading still reports "contained", the gate is fictional.
  - **Addressed by:** **host-side nftables forward-drop as the PRIMARY enforcement**; a **continuous host-side egress tripwire** (armed pre-flight, runs the whole window, re-armed per step) as the **real gate**, firing `IsolationFailed` + `panic()` on any egress; the in-guest probe **demoted to corroboration only**; `IsolationReport` v2 covers **IPv6** (nft `inet`), **DNS egress**, and the **Docker bridge** — both VM and container planes. **ADR-0006 reserved** (containment-authority: host-side-continuous). ARCHITECTURE.md containment model + IsolationProvider port, OPEN-QUESTIONS.md. 2026-05-30.
  - **Residual (confirming pass, 🟠 SERIOUS, now CLOSED):** benign provisioning traffic could trip `panic()` and DoS the lab. Closed by the **provisioning-window invariant**: the tripwire is **DISARMED** during the sanctioned provisioning window (NAT-on, for apt/Packer/box-build per Q-012) and **RE-ARMED** before the first attack step; provisioning traffic must never fire `panic()`. Arm window = **[post-onboard/post-provision, pre-first-attack]** through **[end of attack/teardown]**. Folded into ARCHITECTURE.md containment model + ADR-0006 reservation note (ARCHITECTURE.md + OPEN-QUESTIONS.md). 2026-05-30.

### Resolved — 🟠 Material (closed / folded)

- 🟠 **M1 — SecGen "reproducible" claim overstated.**
  - **Addressed by:** claim corrected to **"pinned-by-cached-output-box"** (rebuild-reproducibility requires Q-012 Option A frozen apt). **ACCEPTED-as-is for MVP**, claim corrected in ARCHITECTURE.md. 2026-05-30.
- 🟠 **M2 — Clock skew breaks the DETECT time window.**
  - **Addressed by:** versioned `skew_budget_s` + `clock_offset_s` measured at onboard; the **Clock port** governs grading-window math. ARCHITECTURE.md, ADR-0001. 2026-05-30.
- 🟠 **M3 — SQLite-over-JSONL justified on wrong grounds.**
  - **Addressed by:** justification rewritten to the true reasons (**transactional multi-row hash-chain append + indexed replay**); the concurrency reason was dropped; hash-chaining restated as **tamper-EVIDENCE, not tamper-resistance** (→ **Q-005**). ARCHITECTURE.md, ADR-0001. 2026-05-30.
- 🟠 **M4 — Partial failure leaves un-gradeable orphan runs.**
  - **Addressed by:** new `scenario_aborted(v1)` event + an **UNGRADEABLE fold rule** for any un-terminated `correlation_id` + **idempotent resume**. ARCHITECTURE.md event catalog + fold rules. 2026-05-30.
- 🟠 **M5 — Scoring idempotency key omitted the seed.**
  - **Addressed by:** `manifest_hash` added to the idempotency key + `score_awarded` bound to `verification_ref` + `manifest_ref`. ARCHITECTURE.md, ADR-0001. 2026-05-30.

### Resolved — 🟡 Minor / smell (placed)

- 🟡 **m1** — `correlation_id` generated via the **Rng port**, distinct per run yet replayable.
- 🟡 **m2** — the scorer treats `DetectionRule.query` as an **opaque blob** (no per-language branching in the scorer).
- 🟡 **m3** — observability sink = **structured JSON to stderr + JSONL ledgers** (stdlib only, no OTel).
- 🟡 **m4** — the `panic()` claim **split**: nft egress-cut is **sub-second**; VM-pause is **best-effort** (serial, >1 s with GOAD-full's 5 VMs).
- 🟡 **m5** — **teardown-leaves-no-residue** assertion added to the pair-rotation validation.

### Three forcing questions — and our answers

1. **Q:** What single failure makes the whole "honest scoring" promise a lie?
   **A:** Grading that rewards a non-skill (match-everything DETECT or deny-everything MITIGATE). Closed by F1/F2 calibration + functional-path CI gates.
2. **Q:** Can the lab leak to the internet while an automated attacker runs, and would you know?
   **A:** No undetected leak: a host-side continuous egress tripwire (v4/v6/DNS, both planes) is the gate and fires `panic()` on any egress; the only sanctioned egress window is provisioning, during which the tripwire is explicitly disarmed and re-armed before the first attack (F3 + provisioning-window invariant).
3. **Q:** If you rebuild from one command in six months, do you get the same lab?
   **A:** Not bit-for-bit until Q-012 Option A (frozen apt); the MVP claim is corrected to "pinned-by-cached-output-box" (M1). Tracked, accepted for MVP.
