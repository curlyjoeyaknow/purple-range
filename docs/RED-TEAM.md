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

## 2026-05-31 — internal `reviewer` on T-110 (hash-chained SQLite EventStore)

> Target: `adapters/event_store.py`, `adapters/_chain.py`, `adapters/__init__.py` (diff `36ed1f2..204d074`)
> Invoked by: pm-orchestrator (post-implementer, pre-GATE-A). Full-context internal review.
> Verdict: **REQUEST CHANGES** — chain integrity is sound; one ADR §5 read-surface gap + hygiene to fix before GATE A.

**Verified SOUND under adversarial probes (the axes GATE-A reviewer-2 owns):**
- Atomicity — `chain_batch` raises before any `BEGIN`; a mid-`executemany` failure under explicit `BEGIN`/`isolation_level=""` rolls back the whole batch (probed `[1,2,5,3]` collision → only pre-existing row survives).
- Framing — `row_hash = sha256(prev_hash.encode("ascii") + b"\x00" + canonical_bytes)` computed once in `_chain.framed_row_hash`; genesis `"0"*64`; lone forged `seq=1` with wrong `prev_hash` fails verify.
- "Hash the bytes you persist" — `verify_rows` re-hashes the stored `payload` string bytes, never a reparsed object (kills the float/unicode round-trip class). NaN/Inf rejected recursively into nested `evidence` + `allow_nan=False` belt-and-braces.
- InMemory↔SQLite byte-identity is structural (both route through `_chain`); conformance fixtures + close-reopen pass.

**🔴 BLOCKER (resolve as T-111's FIRST move — it's a T-110↔T-111 contract decision; see [[Q-020]]):** `event_type` is written to the column but never read, never hashed, and absent from the `fold`/`replay_from` yielded dict — yet ADR §5 pins the Scorer reducer to dispatch on `(event_type, version)`. Two consequences: (1) T-111 cannot dispatch as specified; (2) the column is unverified denormalization — tampering it out-of-band to `'LIE'` keeps `verify_chain` `True`, so dispatching on the unhashed column is a latent scoring-integrity hole. Do NOT just surface the unhashed column. Decide (architect): discriminator inside the hashed payload (additive contract field → ADR/critic, ripples to committed `canonical_bytes_of`) vs re-derive shape from payload vs cross-check column against payload. `adapters/event_store.py:120-135`.

**🟠 MAJOR:** `SqliteEventStore` opens a connection in `__init__` that is never closed — no `close()`/`__del__`/`__enter__`/`__exit__`. Close-reopen "works" only by leaking the first handle; perf test opens 500 stores without cleanup. Add `close()` + context-manager. `adapters/event_store.py`.

**🟡 MINOR:** function-local `import json` in `_iter_rows` (`event_store.py:127`) — hoist to module top. · `append([])` opens/commits an empty transaction under `synchronous=FULL` — add an early-return no-op guard.

**Followups (not blockers):** `replay_from(seq<=0)` silently yields the whole log (ADR says 1-based — assert/document). · `test_scenario_aborted_is_idempotent_on_correlation_id` name implies store-level dedup; the store correctly appends 3 distinct position-bound rows (idempotency is a *reducer* property) — consider renaming. · the `@pytest.mark.perf` test RUNS in default `pytest -q` (not deselected) — confirm CI marker selection so it can't flake on a slow box.

**Cheap-fix shortlist for the next iteration:** close()/context-manager, hoist `json` import, empty-batch guard, `replay_from` guard, test rename. Then `external-reviewer` for a fresh-context read of the framing/verify code before GATE A.

---

## 2026-06-02 — external `external-reviewer` on T-110 (fresh-context, diff-only)

> Target: T-110 diff `e01bbbc..a572c88` (`adapters/`, `tests/`, `conftest.py`) handed as `/tmp/t110.diff` + ADR-0007 only — no project lore.
> Invoked by: pm-orchestrator (post internal-review cheap-fix pass `a572c88`, pre-GATE-A). Fresh-eyes read of framing/verify/transaction code + independent take on [[Q-020]].
> Verdict: chain math well-centralized and trusted; **two findings of substance** + readability nits. All independently re-verified against source before recording.

**Independent confirmation of [[Q-020]] (🔴, agrees with internal review) — AND a cleaner fix shape.** Traced from the outside: `chain_batch` hashes `payload = canonical_payload(contracts.dump(event) + seq + prev_hash)` (`_chain.py:243`); `event_type` is derived *separately* via `_event_type_of(event)` (`:245`) and never enters `row`/`payload`; `verify_rows`/`verify_chain` re-read only `(seq, prev_hash, payload, row_hash)` (`event_store.py:107-110`). So `UPDATE events SET event_type=… ` leaves `verify_chain()` `True` — a tamper blind-spot in the exact field ADR §5 says reducers dispatch on. Blast radius is live *because* of this architecture.
  - **Argues AGAINST the ADR default (inject `event_type` as a key into the hashed payload):** that changes the canonical bytes of every event and forces editing the *independent* conformance oracle `conftest_t110.canonical_bytes_of` (so the test no longer checks the store against a contracts-level definition), and it makes `payload` no longer a faithful `canonical_json(dump(event))` — a stray key for any future `contracts.load_<shape>` re-hydration (ADR §1a).
  - **Proposes instead — frame `event_type` into the hash alongside `payload`, the way `prev_hash` already is:** `row_hash = sha256(prev_hash_bytes + \x00 + event_type_bytes + \x00 + canonical_bytes)`. Keeps `payload == canonical_json(dump(event))` (oracle survives intact), keeps "hash the bytes you persist" honest, and localizes the change to `framed_row_hash` + `chain_batch` (pass `event_type`) + `verify_rows`/`verify_chain` (must also SELECT + frame `event_type`). Same chain-breaking migration cost as the inject option, but cleaner. **→ This becomes a third candidate (Option C) for the Q-020 decision; carry into the T-111-opening architect+critic.** **pm verified all premises against source 2026-06-02** (event_type genuinely outside payload; oracle would indeed have to change under the inject option).
  - **Also flags the missing negative test:** the suite covers edit/reorder/delete/insert of `payload` but has **no test that tampers a non-`payload` column** — precisely how this slipped through. The Q-020 fix MUST land `test_verify_chain_detects_tampered_event_type`.

**🟠 NEW — `append`'s tip-read sits OUTSIDE its transaction (unguarded single-writer assumption).** `_tip()` reads the chain tip (`event_store.py:71`), `chain_batch` computes off it (`:74`), THEN `BEGIN`/`executemany`/`commit` (`:76-85`) — nothing holds a write lock across the read→write gap. Safe *today* only because of the ADR-0005 single-writer scope, which is **lore invisible at the `append` call site**; the tests themselves open second connections to the same file. **pm re-verified + corrected the severity:** the reviewer's "silently forked chain" worst-case is NOT reachable — `seq` is `PRIMARY KEY`, so a concurrent duplicate-`seq` insert raises `IntegrityError` → rollback (no silent corruption). Real exposure = **spurious failures under concurrent writers**, not integrity loss. Clean hardening: `BEGIN IMMEDIATE` + read the tip *inside* the transaction. **Logged as [[Q-021]]; non-blocking for the single-writer MVP, decide at/after T-111.**

**🟡 Readability nits (fold into the Q-020 rewrite — it touches these exact lines):**
- `_event_type_of` docstring (`_chain.py:201-207`) is garbled mid-sentence ("the persisted row's `event_type` would-be field is NOT a dataclass attribute…") — rewrite when the framing fix edits this function.
- `public_row` strips keys by `startswith("_")` (`_chain.py:152`) — a string-prefix convention doing load-bearing work; an event field named with a leading underscore would be silently dropped. Add a guard/comment.
- `fold(..., "WHERE 1=1")` (`event_store.py:94`) — SQL fragment as arg; a `where=""` default reads cleaner.
- `verify_rows` positional unpack couples to the SELECT column ORDER in a different module (`event_store.py:107-110` ↔ `_chain.py:155`) — reorder the SELECT and verification silently hashes the wrong field. Comment or named-tuple.
- `close()` docstring claims "Idempotent" but asserts a property of stdlib `sqlite3`, not of this code; post-`close()` method calls raise opaque `ProgrammingError`. Soften the doc.
- Test tamper at `test_event_store_t110.py` grabs `seq=1` (`scenario_generated`, whose payload has no `"attack"` substring) so the `replace("attack",…)` branch is dead and falls through to the whitespace branch — still asserts correctly, but misleading. (low)

**Disposition:** No code touched now — the cheap nits fold into the imminent Q-020 rewrite of `_chain.py`/`event_store.py` (avoids double-touching the same lines pre-GATE-A). Q-020 gains **Option C (frame-it)** as the now-preferred shape; **Q-021** opened for the tip-read race.

---

## 2026-06-02 — `/critique` on ADR-0007 Addendum 1 (Option D resolves Q-020)

> Target: the just-written ADR-0007 "Addendum 1" (authenticate `event_type` by framing it into the row hash). Mandatory pre-decision critique loop (charter #9), run by `architect` → `critic` at the top of T-111 before any reducer code.
> Verdict: **core decision (D over A/C) SOUND** — the three nominated objections all FAILED on the evidence; **8 fixable findings (🟠×3, 🟡×5), none fatal**, all addressed in the addendum before it became binding. pm independently re-verified the two linchpin claims against source (`schemas.py` loader drops extras; `framed_row_hash` current signature).

**Objections tried that FAILED (why D is sound):**
- **Framing/collision — sound.** NUL-delimited 3-field frame `prev_hash \x00 event_type \x00 canonical_bytes` is self-delimiting and *strictly stronger* than the old 2-field frame; `event_type` (identifier-derived) and `canonical_bytes` (`json.dumps` escapes NUL) are provably NUL-free. No length-extension angle (hash compared for equality, never used as a suffix-MAC).
- **"D re-introduces A's stray-key defect on the read path" (the nominated sharpest) — FAILED.** Verified in `contracts/schemas.py`: `_validate` iterates only the schema's `properties`/`required` (no `additionalProperties:false`, per Q-017) and `_load` filters `kwargs` to dataclass `field_names` — extras silently dropped. The yielded dict already carries the non-field key `row_hash` through this exact path. So promoting `event_type` to a yielded key is safe. **Bonus finding:** the addendum's *original* A-rejection prose over-claimed (it blamed stray-key re-hydration); the real discriminator is **oracle-independence** (A changes `canonical_bytes`, forcing edits to the independent `conftest_t110.canonical_bytes_of` and collapsing `test_row_hash_is_framed_input` into a tautology). Rationale corrected.

**Findings, each addressed in the addendum:**
- 🟡-1 `event_type.encode("ascii")` can raise `UnicodeEncodeError` on a future non-ASCII class name (Python 3 permits Unicode identifiers) → **changed pinned signature to `utf-8`** (same encoding as `canonical_bytes`, still NUL-free).
- 🟡-2 A-rejection rationale mis-argued → **corrected to oracle-independence** (stray keys are dropped by design).
- 🟡-3 §1a yielded-dict read-contract widens (gains `event_type` key) with no version handle → **mandated `test_yielded_row_keyset`** pinning `{fields} ∪ {row_hash, event_type}` (the charter-#2 "version surface" for a non-dataclass persisted shape).
- 🟠-4 the lone negative test asserts the *verdict* not the *cause* (can pass for the wrong reason) → **paired with positive-discrimination `test_row_hash_frames_event_type`** (stored `event_type` reproduces stored `row_hash`; a different `event_type` does not).
- 🟠-5 `event_type` authenticated as *bytes* (immutability) but NOT for *correspondence to the payload it labels* → **Consequences corrected** to scope the guarantee precisely; correspondence recorded as an explicit **residual** (Option-C territory if T-111 dispatch needs it). Within the declared tamper-evidence (not -resistance) threat model.
- 🟠-6 §4a conformance compares only `row_hash`+verdict, not the yielded `event_type` (SQLite re-sources it from the column, InMemory from the dict) → **widened §4a to compare full yielded dicts** + **promoted the distinct-`event_type` fixture from recommended to mandated** (else every fixture shares `event_type="submission"` and the suite passes even if `event_type` were dropped from the frame).
- 🟡-7 the 5-tuple SELECT↔`verify_rows` positional coupling "add a comment" mitigation is hand-waving → **mandated key-based** (`list[dict]` by name, preferred) — a comment doesn't fail a test on reorder.
- 🟡-8 `public_row` `startswith("_")` strip is load-bearing (it's exactly the drop-a-real-field bug-class this change fixes) → **elevated from nit**, pinned by `test_yielded_row_keyset`.
- 🟡-9 Q-021 ride-along couples a non-blocking concurrency fix to the blocking integrity fix → **flipped default to split**; Q-021 is a separate follow-up.

**Disposition:** Addendum revised in place; it is now the **binding T-111 spec**. Q-020 RESOLVED (Option D). Next: `tester` writes the mandated tests RED-first, then `implementer`.

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
