# HANDOFF — 2026-06-02 (T-101 MERGED #9; T-100/T-110 EventStore + T-111 Scorer ALL BUILT+GREEN [366 passed], tip c699e9a; NEXT: GATE A — the spine gate)

> Written by `docs-keeper`. Resume `/deliver` from "Next concrete step" with zero momentum lost.

## Current state in one paragraph

Purple Range is a clean rebuild of the messy `/home/memez/cyber-range` (READ-ONLY reference) into a purple-team CTF/lab platform with 3-pillar scoring (ATTACK → DETECT → MITIGATE). Pre-build pipeline COMPLETE, **M0 COMPLETE**, and **M1a / T-101 = the CONTRACT LOCK is now MERGED to `main`** via **PR #9** (squash commit `a76e3f7`) — **all 10 CI stages green** (incl. `lint` and `unit` = `pytest tests/ -q`). T-101 delivered, in one sequenced surface: **`contracts/`** — 13 versioned shapes with `load_<shape>`/`SchemaError` (nested validation), lossless `dump()` (version-first, deepcopy), stdlib-validated `SCHEMAS`, plus `canonical_json` / `manifest_hash` / `idempotency_key` / `mint_correlation_id`; **`ports/`** — 8 `@runtime_checkable` Protocols; **`adapters/`** — 8 fakes + `REGISTRY`; and `lab/cli.py` **F-006** (Rng-minted `run_id`, `uuid4` gone) + **F-007** (`HANDLERS` dispatch table). Quality trail: internal review fixed **B1** (nested validation) + **B2** (`dump` aliasing) + **S1** (schema/loader agreement); a fresh clean-room review of the **T-101 leg** PASSed on loop 1/4 with no blockers; CI also surfaced ruff debt (`I001`/`E702`) on the tester-locked test files that the review chain missed (no reviewer ran `ruff check .`) — fixed mechanically before merge. 3 NIT smells logged as **Q-017/18/19** (intentional / forward-compat). **294 passed, 6 skipped** (pinned pytest 8.3.4) — there is NO project virtualenv; local runs use a throwaway venv and **CI is the source of truth**. ⚠️ **GATE A is NOT fully closed:** per `docs/DELIVERY-PLAN.md` GATE A spans **T-101 + T-110 + T-111** and requires **TWO independent fresh clean-room reviewers, both must PASS** (reviewer 1 = contracts/fake-conformance ✓ done on the T-101 leg; reviewer 2 = hash-chain integrity + fold/replay determinism + idempotency/seed-reroll — fires AFTER T-111). Current branch: `feat/t-100-t-110-eventstore` (off merged `main`, no commits yet beyond this handoff).

## Workspace topology (KEEP STRAIGHT — do not cross-contaminate)

- `/home/memez/dev-bootstrap` — the FRAMEWORK + current session CWD. **Do NOT build the product here.**
- `/home/memez/cyber-range` — messy SOURCE. **READ-ONLY**; mine for good parts, never modify.
- `/home/memez/purple-range` — the CLEAN TARGET. **All artifacts/code go here.**
- `/home/memez/phalanx` — UNRELATED crypto project. **Hands off.**
- Lab artifacts live on `/mnt/data` (2TB NVMe, 1.7TB free), **NOT** the 244GB root.

### Session-CWD caveat (load-bearing for M2+)

This SESSION runs from `/home/memez/dev-bootstrap`, so the Task tool only resolves the GENERIC agent roster — the forged specialists in `purple-range/.claude/agents/` (lab-orchestration-engineer, detection-engineer, adversary-emulation-engineer) do NOT resolve as `subagent_type` from the framework dir. M0 + T-101 were repo/CI tooling, ADRs, and the contract/port spine with no domain depth, so generic `implementer`/`tester`/`architect` were correct. T-110 (EventStore) and T-111 (Scorer) are likewise generic-suitable. Before a task that needs real specialist depth — **M2 T-201 LabProvider (Vagrant/VBox), M3 detection, M4 threat-actor** — either run the session from inside `purple-range` OR pass the forged agent's `.md` as context to a generic agent.

## What I was doing when I stopped

- **Task:** Closed out T-101 end-to-end — tester RED (`78abe4b`) → implementer GREEN → internal review cleared B1/B2/S1 → fresh `clean-room-reviewer` GATE-A T-101 leg **PASS (loop 1/4)** → opened **PR #9** → CI surfaced ruff `I001`/`E702` debt on the test files → fixed mechanically → **all 10 CI stages green** → **squash-merged to `main` (`a76e3f7`)**, branch `feat/t-101-contracts` deleted.
- **Branch now:** `feat/t-100-t-110-eventstore` — created off the freshly-merged `main`, **no commits yet** (only this handoff is uncommitted). This branch will carry ADR-0007 (T-100) then the T-110 EventStore.
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

## Files modified this session (T-101 — contract spine, GATE A PASS)

```
T-101 (PR #9, branch feat/t-101-contracts):
  78abe4b  WIP T-101 (tester RED): lock the contract spine — failing tests for all shapes/ports/adapters
  6a8dba3  T-101 (implementer GREEN): land the contract spine — make the RED surface pass

  contracts/   13 versioned shapes + load_<shape>/SchemaError (nested) + dump() (lossless, version-first, deepcopy)
               + SCHEMAS (stdlib-validated) + canonical_json/manifest_hash/idempotency_key/mint_correlation_id
  ports/       8 @runtime_checkable Protocols
  adapters/    8 fakes + REGISTRY
  lab/cli.py   F-006 (Rng-minted run_id; uuid4 removed) + F-007 (HANDLERS dispatch table)
  docs/OPEN-QUESTIONS.md  Q-017/Q-018/Q-019 (GATE A NITs, deferred-intentional)
  docs/TODO.md / docs/CHANGELOG.md / docs/HANDOFF.md  reconciled to T-101-DONE / GATE A-PASS seam

Working tree: CLEAN on feat/t-101-contracts. Local: 294 passed, 6 skipped (pytest 8.3.4, throwaway venv).
CI: PR #9 — contracts/f1-calibration/f2-mitigate GREEN; lint/unit/docs/pins/secrets/size-guard/syntax pending.
```

## Suggested resume command

```bash
cd /home/memez/purple-range
git checkout feat/t-100-t-110-eventstore   # already off merged main; this handoff is its first commit
git log --oneline -3 main                  # expect a76e3f7 #9 (T-101 spine) · 06cb93a #8 (M0 ADRs)

claude
> read docs/HANDOFF.md + docs/DELIVERY-PLAN.md + docs/TODO.md, then CONTINUE the GATE-A remainder:
> (1) T-100: architect writes docs/ADR/0007 — EventStore hash-chain = tamper-EVIDENCE,
>     row_hash = H(prev_hash || canonical_json(event)), SQLite-over-JSONL (ADR before code, charter #6).
> (2) T-110: tester locks the chain RED (verify_chain tamper-detect, fold/replay determinism,
>     unterminated-correlation_id ungradeable, scenario_aborted idempotent, append-latency budget),
>     then implementer builds SqliteEventStore behind the EXISTING EventStore port + InMemoryEventStore fake.
> (3) T-111 Scorer (3-pillar, idempotency_key-keyed, per ADR-0001).
> (4) GATE A = TWO fresh clean-room reviewers over T-101+T-110+T-111, BOTH must PASS. Then M2 → T-203 = GATE B.
> Before every push: ruff check . AND pytest tests/ -q (throwaway venv: python3 -m venv /tmp/x &&
>   /tmp/x/bin/pip install pytest==8.3.4 ruff). Each task = branch → PR → GREEN CI → squash-merge → docs note.
> NOTE: for specialist depth (M2 T-201 onward) run from inside purple-range or pass the forged .md as context.
```

## Session metadata

- **Updated:** 2026-05-31 (T-101 MERGED seam — contract spine on `main` via PR #9, all CI green; checkpoint at M1a→M1b, context guard ~74%).
- **Branch:** `feat/t-100-t-110-eventstore` (off merged `main`; only this handoff committed). `feat/t-101-contracts` deleted post-merge.
- **Commits on `main`:** through `a76e3f7` (#9, T-101 contract spine); `06cb93a` (#8, M0 closeout ADRs).
- **Remote:** `origin` → PUBLIC `github.com/curlyjoeyaknow/purple-range`; `main` solo-protected, **10 required status checks enforced**.
- **PRs:** #1–#9 merged; none open.
- **ADRs:** ADR-0001 (manifest-oracle) + ADR-0002 (hypervisor/LabProvider) + ADR-0005 (sequential-scope) landed; **ADR-0007 (store) = the NEXT task (T-100), precedes T-110**; ADR-0003/0004/0006 reserved/in-flight.
- **`/deliver` position:** pipeline ✔ · M0 ✔ · **M1a T-101 MERGED** (GATE A reviewer-1/T-101 leg PASS) · next **T-100 ADR-0007 → T-110 EventStore → T-111 Scorer**, then **GATE A (2 clean-room reviewers, both must PASS)** → **M2** (T-201/T-202/T-203 = GATE B = MVP exit).
```
