# HANDOFF — 2026-06-02 (T-101 MERGED #9; M1b spine T-100/T-110/T-111 ALL BUILT+GREEN [366 passed], branch tip 6f06416; NEXT: GATE A — the spine gate)

> Written by `docs-keeper`. Resume `/deliver` from "Next concrete step" with zero momentum lost.

## Current state in one paragraph

Purple Range is a clean rebuild of the messy `/home/memez/cyber-range` (READ-ONLY reference) into a purple-team CTF/lab platform with 3-pillar scoring (ATTACK → DETECT → MITIGATE), event-sourced with manifest-as-oracle. **M0 COMPLETE** (7 tasks merged to `main`); **M1a / T-101 = the CONTRACT LOCK is MERGED to `main`** via **PR #9** (squash `a76e3f7`, all 10 CI checks green) — `contracts/` (13 versioned shapes + loaders + `canonical_json`/`manifest_hash`/`idempotency_key`), `ports/` (8 Protocols), `adapters/` (8 fakes + `REGISTRY`). **M1b — the entire MVP scoring spine — is now BUILT + GREEN on branch `feat/t-100-t-110-eventstore` (tip `6f06416`), NOT yet merged, awaiting GATE A:** (1) **T-100** ADR-0007 + **Addendum 1** (the hash-chained SQLite EventStore design; tamper-EVIDENCE not -resistance; Addendum 1 = Q-020 resolution, Option D, frame `event_type` into the row hash); (2) **T-110** `SqliteEventStore` + `adapters/_chain.py` shared chain math + upgraded `InMemoryEventStore` (hash-chained, `verify_chain` re-reads persisted bytes, atomic batch append, `fold`/`replay_from` yield persisted dicts) — internal + external review chain complete; (3) **T-111** the event_type-framing change (`af74ea2`) AND **`core/scorer.py`** — the 3-pillar honest-scoring pure core: per-pillar graders (`grade_attack`/`grade_detect`/`grade_detect_via_telemetry`/`grade_mitigate`) + event-sourced `score_reducer`/`derive_scoreboard` + immutable `Scoreboard`, ports-clean (imports only `contracts` + stdlib). **Full suite 366 passed, 6 skipped** (pinned pytest 8.3.4) — there is NO project virtualenv; local runs use a throwaway venv (`/tmp/prvenv`) and **CI is the source of truth**. ⚠️ **GATE A is the immediate next step and is NOT yet run for the full spine:** per `docs/DELIVERY-PLAN.md` it spans **T-101 + T-110 + T-111**, adversarial, budget 4, MVP-BLOCKING, **TWO independent fresh clean-room reviewers, both must PASS** (R1 contracts/schema — the T-101 leg PASSed loop 1, re-confirm with T-110/T-111 layered on; R2 = chain integrity + fold/replay determinism + Scorer honesty/idempotency/seed-reroll). Two oracle-binding tightenings (**Q-022**) must be fed to the reviewers. On both-PASS → open the PR → green CI → squash-merge → **M2 (T-201 LabProvider)**.

## Workspace topology (KEEP STRAIGHT — do not cross-contaminate)

- `/home/memez/dev-bootstrap` — the FRAMEWORK + current session CWD. **Do NOT build the product here.**
- `/home/memez/cyber-range` — messy SOURCE. **READ-ONLY**; mine for good parts, never modify.
- `/home/memez/purple-range` — the CLEAN TARGET. **All artifacts/code go here.**
- `/home/memez/phalanx` — UNRELATED crypto project. **Hands off.**
- Lab artifacts live on `/mnt/data` (2TB NVMe, 1.7TB free), **NOT** the 244GB root.

### Session-CWD caveat (load-bearing for M2+)

This SESSION runs from `/home/memez/dev-bootstrap`, so the Task tool only resolves the GENERIC agent roster — the forged specialists in `purple-range/.claude/agents/` (lab-orchestration-engineer, detection-engineer, adversary-emulation-engineer) do NOT resolve as `subagent_type` from the framework dir. M0 + T-101 were repo/CI tooling, ADRs, and the contract/port spine with no domain depth, so generic `implementer`/`tester`/`architect` were correct. T-110 (EventStore) and T-111 (Scorer) are likewise generic-suitable. Before a task that needs real specialist depth — **M2 T-201 LabProvider (Vagrant/VBox), M3 detection, M4 threat-actor** — either run the session from inside `purple-range` OR pass the forged agent's `.md` as context to a generic agent.

## What I was doing when I stopped

- **Task:** Built the entire M1b scoring spine on `feat/t-100-t-110-eventstore`. Sequence this session: T-100 ADR-0007 (critic loop closed) → T-110 EventStore RED→GREEN → internal + external review chain → Q-020 surfaced (event_type unhashed) → **ADR-0007 Addendum 1** decision (architect→critic, Option D) → event_type-framing RED→GREEN (`af74ea2`) → **T-111 Scorer** RED (`66ca3c0`, 26 tests) → GREEN (`c699e9a`, `core/scorer.py`) → docs reconciled (`6f06416`). Every step verified independently (re-ran suite + ruff, read the diffs). Suite **366 passed / 6 skipped**.
- **Branch now:** `feat/t-100-t-110-eventstore`, tip `6f06416`, **all pushed, clean tree**. Carries T-100 + T-110 + T-111 (they share one PR, opened after GATE A passes). `main` is at `a76e3f7` (#9).
- **Repo:** `/home/memez/purple-range`, remote `origin` → `https://github.com/curlyjoeyaknow/purple-range.git` (PUBLIC). `main` is protected — PR-per-task, NO direct pushes (`enforce_admins: true`), 10 required status checks.
- **Worktree:** none. **In flight (2026-06-02):** NOTHING running; clean tree; tip `c699e9a`, all pushed. **The whole MVP scoring spine is now BUILT + GREEN on `feat/t-100-t-110-eventstore`:** T-100 ADR-0007 + Addendum 1, T-110 EventStore (reviewed internal+external), T-111 Q-020 event_type framing (`af74ea2`), and **T-111 Scorer pure core** (`core/scorer.py`: RED `66ca3c0` → GREEN `c699e9a`). Full suite **366 passed / 6 skipped**, ruff clean. **NEXT IS GATE A** — see step 2.

## Next concrete step

> ✅ **T-100 DONE** (`e01bbbc`, critic loop closed) and ✅ **T-110 DONE — GREEN** (`204d074` on `feat/t-100-t-110-eventstore`): `adapters/event_store.py` `SqliteEventStore` + `adapters/_chain.py` shared chain math + `InMemoryEventStore` upgraded to ADR-0007 semantics. Full suite **335 passed / 6 skipped**, `ruff check .` clean, both pushed. RED→GREEN committed separately (`1327162`→`204d074`). **Resume HERE:**

> ✅ **T-110 internal `reviewer` DONE** (2026-05-31, full findings in [`docs/RED-TEAM.md`](RED-TEAM.md)). Verdict REQUEST CHANGES, but the **chain-integrity axes GATE-A reviewer-2 owns are verified SOUND under adversarial probes** (rollback atomicity, framing, genesis, recursive NaN rejection, re-read-bytes verify, structural byte-identity). Findings are a read-surface gap + hygiene, NOT integrity defects. ✅ `external-reviewer` now also DONE (`020dffb`) — see step 1 below; the full T-110 review chain (internal + external) is complete.

1. ✅ **T-110 cheap-fix pass DONE** (`a572c88`): `SqliteEventStore.close()` + `__enter__`/`__exit__`, hoisted `import json`, `append([])` no-op guard — ruff clean, 335 passed. Two NITs deliberately deferred (tracked in RED-TEAM.md): `replay_from(seq<=0)` doc, and renaming `test_scenario_aborted_is_idempotent_on_correlation_id` → `..._reducer_idempotent...`.
   - ✅ **T-110 `external-reviewer` DONE** (2026-06-02, `020dffb`; findings in [`docs/RED-TEAM.md`](RED-TEAM.md) 2026-06-02). Fresh-context, diff-only. Chain math trusted. Two outputs of substance, both re-verified against source: **(a)** [[Q-020]] confirmed a 3rd time AND given a cleaner fix shape → **Option D (frame `event_type` INTO the hash alongside `payload`, NOT into the payload dict)** — preserves `payload == canonical_json(dump(event))` so the independent conformance oracle survives unedited; now the Q-020 default. **(b)** **[[Q-021]]** opened (non-blocking): `append` reads the chain tip OUTSIDE its transaction — safe only by the ADR-0005 single-writer scope; PK protects integrity (dup-seq → IntegrityError → rollback), so exposure is spurious failures, not corruption. Harden with `BEGIN IMMEDIATE` + tip-read-inside-txn, or document the precondition. Readability nits folded into the Q-020 rewrite (it touches the same lines). **The T-110 review chain is now COMPLETE — no code touched since `a572c88`; the only post-review change is docs (`020dffb`).**
2. ✅ **T-111 — Scorer DONE/GREEN** (`66ca3c0` RED → `c699e9a` GREEN). `core/scorer.py` is the 3-pillar honest-scoring core: per-pillar graders + event-sourced reducer + immutable `Scoreboard`, ports-clean, 26 tests green (366 suite). **NEXT = GATE A — the spine gate** (`docs/DELIVERY-PLAN.md` §GATE A): the whole MVP spine **T-101 + T-110 + T-111** is now built and green on this branch. **Adversarial, budget 4, MVP-BLOCKING; TWO independent fresh `clean-room-reviewer` subagents, BOTH must PASS** (each spawned in a clean context with ONLY the artifact + acceptance spec, no project lore):
   - **Reviewer 1 — contracts/schema:** every persisted shape has `version:int`; loaders reject malformed; canonical_json/manifest_hash/idempotency_key sound. (The T-101 leg already PASSed loop 1; re-confirm it still holds with T-110/T-111 layered on.)
   - **Reviewer 2 — chain integrity + scoring:** EventStore hash-chain (framing incl. the Addendum-1 `event_type`, fold/replay determinism, atomic batch, NaN reject) **and** Scorer honesty (3-pillar discrimination, idempotency/seed-reroll, UNGRADEABLE/aborted fold, the honesty gate).
   - **FEED BOTH REVIEWERS [[Q-022]]'s two tightenings** (oracle vocabulary vs ADR-0001; per-pillar binding not yet *proven* by fixtures) — let the hostile gate rule on whether they block. Budget-exhaustion on GATE A = **HARD STOP → escalate** (an unsound spine corrupts every score).
   - **On both-PASS:** open the PR (T-100+T-110+T-111 share `feat/t-100-t-110-eventstore`) → green CI (10 checks; run `ruff check .` + `pytest tests/ -q` locally first) → squash-merge → **M1b CLOSED → M2** (T-201 LabProvider).
   - **Pre-existing residual (not GATE-A-blocking unless a reviewer says so):** ADR-0007 Addendum 1 Option D authenticates `event_type` *immutability*, not *payload correspondence* — Option-C cross-check available if needed (recorded in [[Q-020]]).
   - T-110 acceptance already locked & green: `test_verify_chain_detects_tampered_row`, `test_fold_replay_reproduces_scoreboard`, `test_*_idempotent_on_correlation_id`, `test_unterminated_correlation_id_is_ungradeable`, the §4a conformance fixtures, and the <5 ms append / <1 s rebuild budget — see `tests/test_event_store_t110.py`.
4. **Then GATE A (the binding one):** TWO fresh `clean-room-reviewer` subagents over T-101+T-110+T-111, **both must PASS** (reviewer 1 contracts ✓ already; reviewer 2 = chain integrity + fold/replay determinism + idempotency/seed-reroll). adversarial, budget 4, MVP-blocking. THEN **M2** → T-203 = GATE B = MVP exit.
5. **Per-task discipline (unchanged):** `tester` RED → `implementer` → `reviewer` → GATE per `docs/DELIVERY-PLAN.md` via FRESH `clean-room-reviewer`. Each task = feature branch → PR → **GREEN CI required** (all 10 checks; **run `ruff check .` AND `pytest tests/ -q` locally before pushing** — the review chain doesn't catch lint) → squash-merge → docs note.

## Workflow (main is protected)

All work on feature branches, PR per task, solo auto-merge on green. **NOTE:** `Bash(gh pr merge:*)` may be in the framework's "ask" list, so the first merge in a session may prompt the human — accept it or move it to allow for full autonomy.

## Clean-room gates (from `docs/DELIVERY-PLAN.md`, run via `clean-room-reviewer` in a FRESH subagent)

- **GATE A** @ T-101 / T-110 / T-111 — contract+scoring spine; **adversarial; budget 4; MVP-blocking**. **T-101 leg PASSED (loop 1/4); T-110 + T-111 legs remain.**
- **GATE B** @ T-203 — e2e oracle / MVP exit; **hard; budget 3; MVP release**.
- **GATE C** @ T-304 — F1 calibration; **hard; budget 2**.
- **GATE D** @ T-403 + M5 — containment + F2 safety; **adversarial; budget 4 + human final sign-off**.

**SAFETY EDGE:** no live automated attack runs without containment COMPLETE+host-verified — the fail-closed orchestrator pre-flight refuses any live attack without an `IsolationVerified` event (single enforcement point; T-203 gated behind T-502; inherited by T-403, T-602). **M5 containment lands before M4 live attack** (hard edges T-502→T-203, T-503b→T-403).

## Public-repo content policy (load-bearing)

Repo holds **run-guides + MITRE mappings + PINNED REFERENCES only** — **NEVER** committed live malware / exploits / payloads (pulled at provision time into gitignored dirs). This is what keeps a public purple-team repo defensible; **enforced at GATE D**. Hold all offensive-content work to it.

## Open decisions (see `docs/OPEN-QUESTIONS.md`)

- **Q-017 / Q-018 / Q-019** (NEW, from GATE A NITs) — **DEFERRED-INTENTIONAL**: additionalProperties strictness, `minItems` cardinality floor, and Protocol-signature conformance. A downstream owner needing strictness adds it at their own boundary; don't pre-tighten the spine.
- **Q-002 / Q-006 / Q-007 / Q-008** — resolve as phases approach (M2/M3 triggers).
- **Q-009** ⚖️ ethics / content line — **MUST resolve before M4/M5** (expert/legal checkpoint).
- **Q-011** — SecGen pin TBD (fetcher refuses; `pinned_commit=None`) — resolve before **M7**.
- **Q-012** — SecGen rebuild-reproducibility (Option A) — before M7.
- **Q-013** — GOAD pin: **RESOLVED** (v3.0.0 commit-resolved to `8c18acc…`, backfilled into ARCHITECTURE.md by T-002).

## Recent learnings (not yet fully in docs)

T-101's manifest-as-oracle spine is now concrete: `manifest_hash = H(canonical_json(...))` plus `idempotency_key` give a deterministic, replayable grading key — guard `canonical_json`'s stability (sort + separators) through execution, because every downstream score keys off it. `dump()` is deliberately lossless, version-first, and deepcopy'd (B2 fix) so persisted events never alias caller state. Loader validation is **nested** (B1 fix) — a malformed inner shape fails at load, not silently downstream. Two implementer choices were left UNPINNED but ratified through GATE A and worth re-examining if a cross-process replay requirement ever tightens: `mint_correlation_id` uses `sha256(str(rng.next()))`, and `SeededRng` draws from `random.Random.getrandbits(64)`. There is **no project virtualenv** — pytest/ruff are pinned in CI only; local runs use a throwaway venv (`python3 -m venv /tmp/x && /tmp/x/bin/pip install pytest==8.3.4 ruff`) and CI remains the source of truth. The DETECT/MITIGATE pillars are only as honest as their calibration/negative fixtures (`{correct_ref, match_all_ref, match_none_ref}` + `skew_budget`, and `deny_all_ref`); containment authority must be host-side and continuous because the guest is untrusted. Disk is no longer a constraint (1.7TB on `/mnt/data`); **RAM-sequential is the only real ceiling** (~55 GiB usable for guests).

## Risks / red flags

`critic` returned **GO-WITH-FIXES**; **3 fatal findings CLOSED and confirmed by a 2nd pass** (F1 DETECT calibration fixtures, F2 MITIGATE deny-everything fixture, F3 host-side continuous containment). See `docs/RED-TEAM.md`. GATE A's T-101 leg returned **PASS with no blockers** (3 NITs → Q-017/18/19, all deferred-intentional). Live risk surface (egress containment, content/ethics line) is gated to M4/M5 and tracked by Q-009; the fail-closed orchestrator pre-flight (no live attack without `IsolationVerified`) is the runtime backstop. Do not start live-attack milestones until those gates are armed and Q-009 is resolved. Open M0 followups still logged in `docs/TODO.md` "Followups" (not yet addressed): **F-002** (dup `env:` in `external-review.yml`), **F-003** (pins-gate box-version file-granularity — harden before M2), **F-004** (no unpinned-Actions-`uses:` rule), **F-005** (unused `PYTHON_VERSION` env). **F-006** (Rng-minted correlation_id) and **F-007** (handler-dispatch seam) are now **CLOSED by T-101**.

## Host facts

Ryzen 9800X3D 8C/16T, 60GiB RAM (~55 usable for guests), bare metal, AMD-V + `/dev/kvm`. VirtualBox 7.1.18 AND libvirt available. Vagrant 2.4.3, Docker 29.5.2, podman 4.9.3, rbenv Ruby 3.2.3, Ubuntu 24.04, kernel 6.17. `/mnt/data` 2TB NVMe, 1.7TB free.

## Files modified this session (M1b spine — T-100/T-110/T-111, branch `feat/t-100-t-110-eventstore`)

```
Commit chain (newest first), all pushed:
  6f06416  docs: T-111 Scorer GREEN — reconcile TODO/CHANGELOG/HANDOFF; next = GATE A
  c699e9a  T-111(green): 3-pillar Scorer pure core (core/scorer.py)        <-- 366 green
  66ca3c0  T-111(red): lock the 3-pillar Scorer contract (26 failing tests)
  48d6f53  T-111(decision): resolve Q-020 — ADR-0007 Addendum 1 (Option D)
  af74ea2  T-111(green): authenticate event_type by framing (Addendum 1)
  bfa7ecf  T-111(red): lock event_type-framing contract
  020dffb  docs: record T-110 external review (Q-020 Option D, opens Q-021)
  a572c88  T-110: address internal review — connection lifecycle + read hygiene
  204d074  T-110(green): hash-chained SQLite EventStore + upgraded InMemory fake
  1327162  T-110(red): lock the hash-chained EventStore contract
  e01bbbc  T-100: ADR-0007 — hash-chained SQLite EventStore
  (+ interleaved handoff/checkpoint commits 31236fb, b3fdd57, 636e85a, b9969f1, 36ed1f2)

Code:
  core/scorer.py, core/__init__.py   NEW — 3-pillar Scorer pure core (ports-clean)
  adapters/_chain.py                 NEW — shared chain math (framed_row_hash incl. event_type, chain_batch, verify_rows)
  adapters/event_store.py            NEW — SqliteEventStore (stdlib sqlite3, contained)
  adapters/__init__.py               InMemoryEventStore upgraded to ADR-0007 + Addendum-1 semantics; SqliteEventStore registered
  tests/test_event_store_t110.py, tests/conftest_t110.py   T-110 + event_type-framing tests
  tests/test_scorer_t111.py, tests/conftest_t111.py        T-111 Scorer tests (26)
  conftest.py                        registered the `perf` marker
Docs:
  docs/ADR/0007-...md (+ Addendum 1) · docs/RED-TEAM.md (T-110 internal+external, Q-020 critic) ·
  docs/OPEN-QUESTIONS.md (Q-020 RESOLVED, Q-021 opened, Q-022 opened) · docs/TODO.md/CHANGELOG.md/HANDOFF.md reconciled

Working tree: CLEAN, all pushed. Local: 366 passed, 6 skipped (pytest 8.3.4, /tmp/prvenv). PR not yet opened (after GATE A).
```

## Suggested resume command

```bash
cd /home/memez/purple-range
git checkout feat/t-100-t-110-eventstore   # tip 6f06416, all pushed, clean tree
git log --oneline -3                        # expect 6f06416 · c699e9a (T-111 green) · 66ca3c0 (T-111 red)
# sanity: rebuild the throwaway venv if gone, confirm green before doing anything
python3 -m venv /tmp/prvenv && /tmp/prvenv/bin/pip install -q pytest==8.3.4 ruff==0.8.6
/tmp/prvenv/bin/pytest tests/ -q            # expect 366 passed, 6 skipped
/tmp/prvenv/bin/ruff check .                # expect clean

claude
> read docs/HANDOFF.md + docs/DELIVERY-PLAN.md (§GATE A) + docs/OPEN-QUESTIONS.md (Q-022), then run GATE A:
> The MVP spine T-101 + T-110 + T-111 is BUILT + GREEN on this branch. GATE A = TWO independent FRESH
> clean-room-reviewer subagents (each spawned in a CLEAN context — give ONLY the artifact diff + the
> acceptance spec, NO project lore/CLAUDE.md), BOTH must PASS:
>   R1 (contracts/schema): version:int on every persisted shape; loaders reject malformed; canonical_json/
>      manifest_hash/idempotency_key sound. (T-101 leg PASSed loop 1 — re-confirm with T-110/T-111 layered on.)
>   R2 (chain integrity + scoring): EventStore framing (incl. Addendum-1 event_type), fold/replay determinism,
>      atomic batch, NaN reject; AND Scorer honesty (3-pillar discrimination, idempotency/seed-reroll,
>      UNGRADEABLE/aborted fold, the no-score-without-passing-verification gate).
>   FEED BOTH the two Q-022 tightenings (oracle vocabulary vs ADR-0001; per-pillar binding not yet PROVEN by
>      fixtures) and let the gate rule on whether they block. Budget 4; budget-exhaustion = HARD STOP, escalate.
> On both-PASS: open ONE PR (T-100+T-110+T-111) → green CI (10 checks; ruff check . + pytest tests/ -q FIRST)
>   → squash-merge → M1b CLOSED → M2 (T-201 LabProvider).
> NOTE: for specialist depth (M2 T-201 onward) run from inside purple-range or pass the forged agent .md as context.
```

## Session metadata

- **Updated:** 2026-06-02 (M1b spine BUILT+GREEN seam — T-100/T-110/T-111 on `feat/t-100-t-110-eventstore`, 366 green; checkpoint before GATE A. Refreshed for a full-context-clear: every section reconciled to tip `6f06416`).
- **Branch:** `feat/t-100-t-110-eventstore`, tip `6f06416`, all pushed, clean tree. Carries T-100+T-110+T-111 (one PR, after GATE A). `feat/t-101-contracts` deleted post-merge.
- **Commits on `main`:** through `a76e3f7` (#9, T-101 contract spine); `06cb93a` (#8, M0 closeout ADRs). The M1b branch is NOT yet merged (awaiting GATE A).
- **Remote:** `origin` → PUBLIC `github.com/curlyjoeyaknow/purple-range`; `main` solo-protected, **10 required status checks enforced**.
- **PRs:** #1–#9 merged; none open.
- **ADRs:** ADR-0001 (manifest-oracle) + ADR-0002 (hypervisor/LabProvider) + ADR-0005 (sequential-scope) landed; **ADR-0007 (store) = the NEXT task (T-100), precedes T-110**; ADR-0003/0004/0006 reserved/in-flight.
- **`/deliver` position:** pipeline ✔ · M0 ✔ · **M1a T-101 MERGED** (GATE A reviewer-1/T-101 leg PASS) · next **T-100 ADR-0007 → T-110 EventStore → T-111 Scorer**, then **GATE A (2 clean-room reviewers, both must PASS)** → **M2** (T-201/T-202/T-203 = GATE B = MVP exit).
```
