# TODO — Purple Range (codename Phalanx)

> Updated by the `docs-keeper` agent. Format matches `decomposer` output.
> `/decompose` (2026-05-30) refined the milestone spine (M0–M8) into a
> dependency-ordered task graph (T-NNN). Milestone headings are preserved as
> the organizing spine; tasks below carry the real edges, contract surfaces,
> acceptance criteria, test plans, and agent assignments.
>
> Spine: [`docs/PRD.md`](PRD.md) · [`docs/ARCHITECTURE.md`](ARCHITECTURE.md) ·
> [`docs/ADR/0001-manifest-oracle-event-sourced-scoring.md`](ADR/0001-manifest-oracle-event-sourced-scoring.md) ·
> [`docs/BRAINSTORM.md`](BRAINSTORM.md) · [`docs/OPEN-QUESTIONS.md`](OPEN-QUESTIONS.md) ·
> [`docs/RED-TEAM.md`](RED-TEAM.md)
>
> **Validated + gated:** `plan-critic` validated the critical path + parallelism
> and set the hostile-review gates; the binding plan is
> [`docs/DELIVERY-PLAN.md`](DELIVERY-PLAN.md). The 5 plan-critic corrections
> (C1–C5) are folded into the task graph below.

## Goal

Build an honest, reproducible, provably-contained single-host purple-team lab
whose three pillars (ATTACK / DETECT / MITIGATE) grade against a versioned
manifest-oracle, with progress derived by folding an append-only hash-chained
event log.

## Constraints

- **Single host, RAM-bound** (~55 GiB usable). Any task that boots real VMs/SO
  is **HOST-SERIAL** (resource ceiling); pure code/contract/unit tasks
  parallelize freely. Tagged `[HOST-SERIAL]` where it bites.
- **Safety non-negotiable:** no LIVE automated attack task runs before
  containment is COMPLETE+host-verified. Hard edges: **T-503b → T-403** (web live)
  and **T-502 → T-203** (the MVP e2e fires a live attack too — C3). The refusal
  is enforced at ONE point — the orchestrator loop's
  `test_live_attack_refused_without_containment` (`IsolationVerified` required) —
  so every attack path (T-203/T-403/T-602) inherits it.
- **Contracts before implementations; ports & adapters at every boundary;
  `version:int` on every persisted shape; spec/contracts before code** (charter
  #2/#3). The shared contracts **AND the shared-infra files** (the full `lab`
  dispatch table T-004, the adapter registry T-101, the CI workflow structure
  T-003, and the unified dependency manifest T-103) are locked **first** as the
  M1a blocker so S1/S2/S3 stay file-disjoint and become additive-only.
- **CI tier < 5 min, zero VMs, push-blocking.** Pins gate; size-guard < 50 MB.
- Pinned versions are authoritative in ARCHITECTURE.md "Pinned versions".

## Status legend

- `ready` — no unmet dependencies; can be picked up.
- `in-progress` — being worked on; check the branch.
- `blocked-on-X` — waiting on another task ID.
- `review` — implementation done; in code review.
- `done` — merged.

## Task-graph overview

```
M0 hygiene/bootstrap ─────────────────────────────────────────────┐
  T-001 de-bloat ─ T-002 fetch-deps ─ T-003 CI skel ─ T-004 lab CLI ─ T-005 /mnt/data
                                                  │ ADR-0002, ADR-0005 (T-006, T-007)
                                                  ▼
M1a CONTRACT LOCK (BLOCKER) ── T-101 contracts+schemas+fakes ── ADR-0005-store (T-102)
                                                  │  unblocks ALL fan-out
        ┌─────────────────────────────────────────┼───────────────────────────┐
        ▼ (critical path)                          ▼ parallel after M1a          ▼
M1b  T-110 EventStore ─ T-111 Scorer 3-pillar      S1 detection (M3)            S3 containment (M5)
        │                                          S2 threat-actor skeleton(M4) ADR-0006 (T-501)
        ▼
M2  T-201 LabProvider ─ T-202 Vulhub gen ─ T-203 e2e 3-pillar  ◀── MVP EXIT
        │  ADR-0002-finalize (T-006 lands here) · T-203 blocked-on T-502 (C3 safety)
        ▼
M3  T-301 ADR-0004 ─ T-302 SO provision ─ T-303 onboard/fleet ─ T-304 F1 gate ─ T-305 live-SIEM grade
M4  T-401 actor skeleton(fakes) ─ T-402 F2 mitigate ──[T-503b done]──▶ T-403 LIVE attack
M5  T-501 ADR-0006 ─ T-502a/502b nft (core∥ / host-tail) ─ T-503a/503b tripwire+panic+preflight (core∥ / host-tail → IsolationVerified)
        │  POST-MVP CRITICAL PATH (NOT slack) ─ gates ALL live attack
M6  T-601 GOAD provision ─ T-602 AD attacks/detections  (FULL-PROJECT FINISH; needs M2,M5)
M7  T-701 ADR-0003 ─ T-702 SecGen container generator   (needs M2)
M8  T-801 harness tiers ─ T-802 pair-rotation/no-residue ─ T-803 reproducibility
```

---

## M0 — Repo hygiene + bootstrap

### T-001  De-bloat the tracked tree (6.2 GB → < 50 MB)            [BLOCKER]
- Depends on: none
- Contract surface: none (repo hygiene). Touches `.gitignore`, removes vendored
  clones (SecGen / hacktricks / PayloadsAllTheThings) + committed `handbook/.venv`.
- Acceptance:
  - Tracked repo < ~50 MB; no tracked blob > 5 MB (history rewrite if needed).
  - `.gitignore` excludes `vendor/`, `/mnt/data` artifacts, work dirs.
- Test plan: tester writes `test_size_guard_passes` against the size-guard script
  (assert fail on a planted 6 MB blob, pass on clean tree) **before** the purge.
- Effort: S
- Worktree-safe with: T-006, T-007 (docs/ADR only).
- Agent: lab-orchestration-engineer
- Status: DONE (PR #2) — forward guard `scripts/size_guard.py` + `.gitignore`
  landed; 17 contract tests green; reviewer APPROVE (no blockers).

### T-002  `scripts/fetch-deps.sh` — pinned refs + checksums         [BLOCKER]
- Depends on: T-001
- Contract surface: none (build tooling). Reads pins from ARCHITECTURE.md
  "Pinned versions"; writes into gitignored `/mnt/data/.../vendor/`.
- Acceptance:
  - Clones each dep at its **pinned commit/box_version** (Vulhub
    `d277a86…`, ART `daee1d5…`, GOAD `v3.0.0` commit-pin, SecGen TBD per Q-011);
    verifies SHA256; refuses on mismatch.
  - Idempotent re-run is a no-op; no network write to the tracked tree.
- Test plan: tester writes `test_fetch_deps_rejects_checksum_mismatch` and
  `test_fetch_deps_idempotent` against a fake fetch target first.
- Effort: M
- Worktree-safe with: T-003, T-004, T-005.
- Agent: lab-orchestration-engineer
- Status: blocked-on-T-001

### T-003  Thin push-blocking CI skeleton                            [BLOCKER]
- Depends on: T-001
- Contract surface: none yet (contracts gate is a **placeholder** here; wired to
  real schemas in T-101 and to F1/F2 fixtures in T-304/T-402).
- Acceptance (**ALL stages present and stubbed up front**, < 5 min, zero VMs,
  python:3.12): lint (shellcheck/ansible-lint/yamllint/ruff), unit (pytest),
  **contracts gate** (placeholder → wired in T-101), **F1 calibration stage**
  (placeholder → fixtures filled by T-304), **F2 mitigate stage** (placeholder
  → fixtures filled by T-402), syntax (vagrant/ansible/compose/packer validate),
  pins (regex gate: fail `:latest`/unpinned `box_version`/bare `git clone`),
  docs (`mkdocs build --strict` + link-check), secrets (gitleaks), size-guard.
  - The workflow STRUCTURE is locked here — T-304/T-402 only fill in fixtures
    inside their already-declared stage and never edit the workflow layout.
  - **size-guard hardening (from T-001 review):** the `size-guard` stage must
    invoke `size_guard.py` with a known-good root (`.`) OR harden `main()` to
    exit nonzero on a nonexistent root — `os.walk` silently yields nothing for a
    missing path, so a typo'd path is currently a quiet false-pass (green). Add
    a test for the nonexistent-root case when wiring this stage.
- Test plan: tester adds fixtures that each stage must reject (a `:latest` pin,
  a >5 MB blob, a leaked secret, a broken doc link) — gate must go red on each.
- Rationale: shared-infra file locked in M1a so S1/S2/S3 stay file-disjoint (plan-critic §2).
- Effort: M
- Worktree-safe with: T-002, T-004, T-005.
- Agent: implementer
- Status: blocked-on-T-001

### T-004  `lab` CLI scaffold + ValidationEvent ledger skeleton      [BLOCKER]
- Depends on: T-001
- Contract surface: introduces `ValidationEvent(version:1)` **skeleton only**
  (full shape locked in T-101); the **FULL `lab` CLI dispatch table** — the six
  top-level verbs (`lab up|down|reset|validate|status|panic`) **AND every
  stream-specific sub-command** so no parallel stream edits the dispatch later:
  `lab detection onboard`, `lab threat-actor run`, `lab panic`, `lab isolation
  arm|disarm` (S1/S2/S3 sub-verbs stubbed up front); JSONL ledger writer skeleton.
- Acceptance:
  - `lab --help` lists all six top-level commands **and** the stream sub-commands
    (detection/onboard, threat-actor run, isolation arm/disarm); each stub exits
    cleanly with a "not-implemented" ValidationEvent appended to
    `validation-events.jsonl`.
  - The dispatch table is LOCKED here — S1/S2/S3 only fill in the body of their
    already-registered sub-command, never edit argparse/dispatch wiring.
  - Harness logic sits over `LabProvider` so it is CI-testable via the fake
    later (no vendor import in the CLI core).
- Test plan: tester writes `test_lab_cli_parses_all_commands` (incl. the
  stream sub-commands) and `test_validation_ledger_appends` against an in-memory
  ledger first.
- Rationale: shared-infra file locked in M1a so S1/S2/S3 stay file-disjoint (plan-critic §2).
- Effort: M
- Worktree-safe with: T-002, T-003, T-005.
- Agent: lab-orchestration-engineer
- Status: blocked-on-T-001

### T-005  `/mnt/data` storage layout + config                       [BLOCKER]
- Depends on: T-001
- Contract surface: none (filesystem layout + config). Creates `vendor/`,
  `boxes/`, `vbox/`, `secgen-builds/`, `box-cache/`, `work/`, `state/`;
  relocates `VAGRANT_HOME` + VBox machine folder to `/mnt/data`.
- Acceptance:
  - A bootstrap step creates the layout idempotently; config points all
    multi-GB artifact paths at `/mnt/data`; root tree stays < 50 MB.
- Test plan: tester writes `test_storage_layout_idempotent` (re-run = no-op) and
  `test_no_artifact_path_under_root` against a temp root first.
- Effort: S
- Worktree-safe with: T-002, T-003, T-004.
- Agent: lab-orchestration-engineer
- Status: blocked-on-T-001

### T-006  ADR-0002 — Hypervisor behind LabProvider                  [PARALLEL]
- Depends on: none (write at M0; **finalize/confirm at M2** when the real
  VagrantVirtualBox adapter lands in T-201).
- Contract surface: documents the `LabProvider` port boundary (VirtualBox-now /
  libvirt-deferred / DockerCompose).
- Acceptance: ADR with context/decision/consequences/alternatives; names the
  port methods (`bring_up/tear_down/snapshot/restore/status`) and the base-snapshot rule.
- Test plan: n/a (doc). docs gate (`mkdocs build --strict`) must pass.
- Effort: S
- Worktree-safe with: all M0 code tasks, T-007.
- Agent: architect
- Status: ready

### T-007  ADR-0005 — Sequential / scenario-scoped scope             [PARALLEL]
- Depends on: none (write at M0)
- Contract surface: none (scope decision); justifies single-host sequential
  scope + adjacent-pair-only co-residency + RAM ceiling.
- Acceptance: ADR records why simultaneous all-phase boot is out of scope and
  how the adjacent-pair model satisfies "phases inter-communicate".
- Test plan: n/a (doc). docs gate passes.
- Effort: S
- Worktree-safe with: all M0 code tasks, T-006.
- Agent: architect
- Status: ready

---

## M1 — Scoring spine (MVP backbone)

> **Decomposed into M1a (CONTRACT-LOCK BLOCKER) and M1b (EventStore+Scorer,
> critical path).** M1a must land before M3/M4/M5 code can fan out — they all
> consume these contracts. Locking them first is what makes the parallel
> streams real instead of falsely concurrent.

### M1a — Contract lock (the blocker that unblocks fan-out)

### T-100  ADR-0007 — Hash-chain = tamper-EVIDENCE not -resistance (store)  [BLOCKER]
- Depends on: T-003 (CI exists to host the contracts gate)
- Contract surface: writes **ADR-0007** (renumbered from the clashing "ADR-0005-
  store" — 0005 is reserved for sequential-scope). Documents the EventStore
  hash-chain property + SQLite-over-JSONL justification (transactional multi-row
  append + indexed replay; M3-fix).
- Acceptance: ADR-0007 records `row_hash = H(prev_hash || canonical_json(event))`,
  the re-fold/re-chain owner property, and why it is evidence not resistance.
- Test plan: n/a (doc). docs gate passes.
- Effort: S
- Worktree-safe with: T-101 (doc vs code, but precedes the chain impl).
- Agent: architect
- Status: blocked-on-T-003

### T-101  Versioned contracts + JSON-Schemas + ALL port FAKES        [BLOCKER]
- Depends on: T-003 (contracts CI stage), T-004 (ValidationEvent skeleton)
- Contract surface (THE shared surface — everything downstream consumes this):
  - **Dataclasses + JSON-Schema** for every persisted shape:
    `Scenario(v1)`, `VulnManifest(v2)` (incl. `detect.calibration{correct_ref,
    match_all_ref, match_none_ref}` F1, `mitigate{service_probe, deny_all_ref}`
    F2, `skew_budget_s`, `clock_offset_s`, `manifest_hash`),
    `OnboardSpec(v1)`, `DetectionRule(v2)` (incl. `calibration` block + opaque
    `query` + `language`), `AttackEvent(v1)`, `IsolationReport(v2)` (v4/v6/DNS/
    docker-bridge/tripwire fields), `ValidationEvent(v1)`, and the **6 event
    shapes**: `scenario_generated(v2)`, `attack_executed(v1)`,
    `scenario_aborted(v1)`, `submission(v1)`, `verification_result(v2)`,
    `score_awarded(v2)`.
  - **All port interfaces defined** (no vendor imports): LabProvider,
    ScenarioGenerator, ThreatActor, Telemetry, IsolationProvider, EventStore,
    Clock, Rng — each with its **FAKE** (InMemoryLab, FixedManifestGen,
    ScriptedActor, ReplayLogBundle, CannedReport, InMemoryEventStore, FixedClock,
    SeededRng).
  - `manifest_hash = H(canonical_json(victim, vulns, seed))` defined;
    scoring idempotency key `(scenario_id, challenge_id, pillar, manifest_hash)`
    defined; `correlation_id` minted from Rng (distinct-per-run, replayable).
  - **Adapter-registry / `adapters/__init__` import surface LOCKED** with
    placeholder registrations for ALL EIGHT adapters (LabProvider,
    ScenarioGenerator, ThreatActor, Telemetry, IsolationProvider, EventStore,
    Clock, Rng) so the parallel streams only ADD files under `adapters/<domain>/*`
    and NEVER edit the registry.
- Acceptance:
  - `contracts.load_*()` validates every shape on ingest; rejects a shape
    missing `version`.
  - CI **contracts** stage validates every shipped fixture against its schema.
  - Every fake satisfies its port interface (structural conformance test).
  - The adapter registry enumerates all eight adapter slots (placeholder entries
    OK); a stream adding `adapters/<domain>/<name>.py` registers by ADD only —
    `test_registry_lists_all_eight_adapter_slots` guards the surface.
  - If a fake is hard to write, the interface is wrong — redesign the interface.
- Test plan: tester writes, first and failing:
  `test_every_persisted_shape_requires_version`,
  `test_schema_rejects_malformed_<shape>` per shape,
  `test_fake_conforms_to_port_<port>` per port,
  `test_manifest_hash_is_canonical_and_stable`,
  `test_correlation_id_distinct_same_seed_yet_replayable`,
  `test_registry_lists_all_eight_adapter_slots`.
- Rationale: shared-infra file locked in M1a so S1/S2/S3 stay file-disjoint (plan-critic §2).
- Effort: L
- Worktree-safe with: T-100 (doc). **Blocks** T-110, T-201, S1, S2, S3.
- Agent: tester (locks shapes) + implementer
- Status: blocked-on-T-003, blocked-on-T-004

### T-103  Unified dependency manifest — all-stream pins added ONCE  [BLOCKER]
- Depends on: T-101 (so the contract surface that names the deps exists)
- Contract surface: `pyproject.toml` + lockfile — adds ALL THREE streams'
  pinned deps (S1 detection, S2 threat-actor, S3 containment) in ONE sequenced
  change, drawn from ARCHITECTURE.md "Pinned versions".
- Acceptance:
  - Every dep any stream will import is pinned here in a single commit; lockfile
    regenerated and committed; CI pins gate stays green.
  - After this lands, NO stream touches `pyproject.toml` — streams only IMPORT
    already-pinned deps. This is part of the M1a contract-lock blocker.
- Test plan: tester asserts `test_lockfile_in_sync_with_pyproject` and the pins
  gate rejects an unpinned add; streams adding an unlisted import fail CI.
- Rationale: shared-infra file locked in M1a so S1/S2/S3 stay file-disjoint (plan-critic §2).
- Effort: S
- Worktree-safe with: T-100 (doc); precedes all stream fan-out.
- Agent: implementer
- Status: blocked-on-T-101

### M1b — EventStore + Scorer (critical path)

### T-110  Append-only hash-chained SQLite EventStore                 [CRITICAL]
- Depends on: T-101 (event shapes locked), T-100 (chain ADR)
- Contract surface: implements `EventStore` port — `SqliteEventStore` (prod) +
  exercises `InMemoryEventStore` (fake from T-101): `append` (multi-row TXN,
  `seq`/`prev_hash`/`row_hash`), `fold`, `replay_from`, `verify_chain`.
- Acceptance:
  - Multi-row append is one transaction; `row_hash` chains per row.
  - `verify_chain()` PASSES on a clean log, FAILS on any row edit/reorder/delete.
  - `replay_from(seq)` seeks on indexed `seq`; fold reproduces identical state.
  - Fold treats an un-terminated `correlation_id` as INCOMPLETE/UNGRADEABLE (M4);
    `scenario_aborted` closes it idempotently.
  - NFR micro-bench: append < 5 ms/event; full rebuild < 1 s (personal volume).
- Test plan: tester writes first:
  `test_verify_chain_detects_tampered_row`,
  `test_fold_replay_reproduces_scoreboard`,
  `test_unterminated_correlation_id_is_ungradeable`,
  `test_scenario_aborted_is_idempotent_on_correlation_id`,
  `test_append_latency_under_budget`.
- Effort: L
- Worktree-safe with: nothing on the critical path (it IS the path); S1/S2/S3
  run in parallel against the **fakes**, not this.
- Agent: implementer
- Status: blocked-on-T-101

### T-111  Scorer — 3-pillar grading logic (pure core)                [CRITICAL]
- Depends on: T-110 (EventStore), T-101 (manifest/rule/event shapes + fakes)
- Contract surface: `core/scorer` (pure) — consumes `VulnManifest`,
  ground-truth, `submission`; emits `verification_result(v2)` + `score_awarded(v2)`;
  uses Clock for grading-window math, Telemetry/ThreatActor **ports** (fakes here).
  Treats `DetectionRule.query` as an **opaque blob**; never branches on `language`.
- Acceptance (the honest-scoring core):
  - **ATTACK:** passes iff learner TTP ∈ `manifest.expected_ttps` OR matches an
    auto `attack_executed{outcome:success}`; a flaky/failed attack does not score
    and does not penalize DETECT.
  - **DETECT:** three-window TP+FP — `>= expected_min_hits` over
    `[t_start,t_end] ± skew_budget` AND `<= max_false_positives` over the benign
    baseline window. Reconciles SIEM ts to actor Clock via `clock_offset_s`.
  - **MITIGATE:** re-attack from `base` snapshot → `outcome:"blocked"` AND
    `service_probe` healthy over the **functional path**.
  - `score_awarded` emittable ONLY with a referenced PASSING `verification_result`,
    bound to `verification_ref` + `manifest_ref`; idempotency key includes
    `manifest_hash` (a pass under seed A is NOT reused after a re-roll to seed B).
- Test plan: tester writes first, all against the fakes (ScriptedActor /
  ReplayLogBundle / FixedManifestGen / FixedClock):
  `test_attack_passes_only_on_manifest_ttp_or_success_outcome`,
  `test_attack_flaky_does_not_penalize_detect`,
  `test_detect_match_everything_fails_FP_half`,
  `test_detect_match_nothing_fails_TP_half`,
  `test_detect_window_respects_skew_budget_and_clock_offset`,
  `test_mitigate_deny_everything_fails_service_probe`,
  `test_score_not_reused_after_seed_reroll`,
  `test_score_bound_to_verification_and_manifest_ref`.
- Effort: L
- Worktree-safe with: nothing (critical path).
- Agent: implementer
- Status: blocked-on-T-110

---

## M2 — Vulhub/Docker web phase end-to-end (the MVP)

### T-201  LabProvider — VagrantVirtualBox + DockerCompose adapters   [CRITICAL]
- Depends on: T-101 (LabProvider port + InMemoryLab fake), T-005 (/mnt/data),
  T-002 (deps)
- Contract surface: implements `LabProvider` (prod adapters); per-VM `base`
  snapshot rule; finalizes ADR-0002 (T-006).
- Acceptance:
  - `bring_up/tear_down/snapshot/restore/status` work against a real Docker
    compose target and a real VBox VM; no attack allowed without a `base` snapshot.
  - Harness logic unchanged (still drives the fake in CI).
- Test plan: harness logic tested via InMemoryLab in CI; adapter conformance
  proven in the `lab validate --smoke web` HOST-SERIAL step (T-203).
- Effort: L
- Worktree-safe with: T-202 only if files are disjoint (see false-concurrency
  note: both touch the generate→up glue — sequence T-201 before T-202).
- Agent: lab-orchestration-engineer
- Status: blocked-on-T-101, blocked-on-T-005
- HOST-SERIAL (real VM/Docker boot)

### T-202  ScenarioGenerator — VulhubCVE adapter (emits VulnManifest) [CRITICAL]
- Depends on: T-201 (LabProvider), T-101 (ScenarioGenerator port + manifest schema)
- Contract surface: implements `ScenarioGenerator` (VulhubCVE prod adapter);
  authors ONE curated CVE manifest (all three oracle blocks incl. F1 calibration
  refs + F2 deny_all_ref + service_probe).
- Acceptance:
  - `@sha256`-pinned CVE container stands up deterministically; emits a
    schema-valid `VulnManifest(v2)` with stable `manifest_hash`.
  - The authored manifest passes the contracts schema gate.
- Test plan: tester writes `test_vulhub_manifest_is_schema_valid` and
  `test_manifest_hash_stable_across_runs` (manifest-only, no VM) first.
- Effort: L
- Worktree-safe with: none (sequenced after T-201).
- Agent: lab-orchestration-engineer + detection-engineer (detect block) +
  adversary-emulation-engineer (attack/mitigate blocks)
- Status: blocked-on-T-201
- HOST-SERIAL (container boot for authoring/verification)

### T-203  Wire full pipeline generate→onboard→attack→3-pillar grade [CRITICAL]
- Depends on: T-202, T-111 (Scorer), T-110 (EventStore),
  **T-502 (nft PRIMARY containment incl. Docker-bridge plane — host-verified
  via T-502b)**
- **blocked-on: T-502** — T-203's MVP e2e runs a LIVE attack on a Vulhub CVE,
  which MUST NOT run before the nftables PRIMARY containment (incl. the Docker-
  bridge plane) exists and is host-verified. The full safety chain therefore
  requires T-502 (core+host) to land before T-203's host run. *(See C3: this
  closes the back door where the MVP e2e could fire a live attack ahead of
  containment.)*
- Contract surface: orchestrator loop wiring (pure core driving real adapters);
  proves manifest-as-oracle end-to-end on ONE real Vulhub CVE. **MVP EXIT.**
- Acceptance:
  - `lab validate --e2e web` green: generate → onboard → attack → ATTACK+DETECT+
    MITIGATE all grade correctly against the manifest; replay self-check passes
    (delete derived state, re-fold → identical scoreboard); chain verifies.
  - MITIGATE functional-path gate active (F2) on the real target.
  - **Fail-closed pre-flight guards T-203's attack too:** the orchestrator loop's
    `test_live_attack_refused_without_containment` (requires an `IsolationVerified`
    event) gates THIS e2e attack. The refusal is routed through the orchestrator
    loop as the SINGLE enforcement point so EVERY attack path (T-203, T-403,
    T-602) inherits it from one place.
- Test plan: tester writes the orchestrator-loop test against fakes first
  (`test_full_loop_emits_expected_event_sequence`) AND the shared
  `test_live_attack_refused_without_containment` (no `IsolationVerified` → refuse),
  then the HOST-SERIAL `lab validate --e2e web` green run is the acceptance gate.
- Effort: L
- Worktree-safe with: none (MVP convergence point).
- Agent: lab-orchestration-engineer + adversary-emulation-engineer +
  detection-engineer converge; implementer for glue
- Status: blocked-on-T-202, blocked-on-T-111, blocked-on-T-502
- HOST-SERIAL · SAFETY-GATED

---

## M3 — Detection data-plane (Security Onion primary) — STREAM S1

### T-301  ADR-0004 — Security Onion as primary SIEM                  [PARALLEL]
- Depends on: T-101 (Telemetry port locked)
- Contract surface: documents Telemetry port + SO-primary / Splunk-optional decision.
- Acceptance: ADR with context/decision/consequences/alternatives; notes Q-002
  SO unattended-install risk.
- Test plan: n/a (doc). docs gate passes.
- Effort: S
- Worktree-safe with: all S2/S3 tasks.
- Agent: architect
- Status: blocked-on-T-101

### T-302  Security Onion 2.4 provisioning                            [PARALLEL]
- Depends on: T-301, T-201 (LabProvider for VM boot)
- Contract surface: SO 2.4.211-20260407 provisioning behind LabProvider/Docker;
  note Q-002 interactive-installer risk.
- Acceptance: `lab up` brings SO to a healthy Suricata+Zeek+Elastic+Fleet+Kibana
  state from pinned artifact; no `:latest`.
- Test plan: provisioning logic CI-tested via fakes; HOST-SERIAL smoke boot is
  the real gate (folds into T-803/T-801 e2e).
- Effort: L
- Worktree-safe with: S2/S3 (disjoint contract surface: Telemetry vs ThreatActor/
  Isolation). Real-boot step HOST-SERIAL.
- Agent: detection-engineer
- Status: blocked-on-T-301
- HOST-SERIAL (SO boot)

### T-303  OnboardSpec / Fleet enrollment of dynamic victims          [PARALLEL]
- Depends on: T-302, T-101 (OnboardSpec)
- Contract surface: `Telemetry.onboard()` SO/Fleet adapter; heartbeat gate.
- Acceptance: no victim is "ready" until Fleet shows heartbeat within
  `heartbeat_deadline_s`; range-up gated on it.
- Test plan: tester writes `test_onboard_gates_on_heartbeat` against
  ReplayLogBundle/CannedReport first.
- Effort: M
- Worktree-safe with: S2/S3.
- Agent: detection-engineer
- Status: blocked-on-T-302

### T-304  DetectionRule authoring + F1 calibration CI gate           [PARALLEL]
- Depends on: T-101 (DetectionRule v2 + calibration schema), T-303 (live SIEM
  to run rules) for the live half; the **fixture gate** half needs only T-101.
- Contract surface: converts prose starter-searches to versioned `DetectionRule(v2)`;
  wires the **F1 contracts-CI calibration gate**.
- Acceptance (F1):
  - Per challenge: `correct_ref` PASSES both halves; `match_all_ref` FAILS the FP
    half; `match_none_ref` FAILS the TP half. Any violation → build red.
  - CI contracts stage runs the calibration fixture for every challenge.
- Test plan: tester writes the gate test first against recorded log bundles
  (ReplayLogBundle): `test_calibration_correct_passes`,
  `test_calibration_match_all_fails_fp`, `test_calibration_match_none_fails_tp`.
- Effort: M
- Worktree-safe with: S2/S3 (DetectionRule surface already locked in T-101).
- Agent: detection-engineer
- Status: blocked-on-T-101 (fixture gate) / blocked-on-T-303 (live half)

### T-305  Three-window TP+FP grading oracle wired to live SIEM       [PARALLEL]
- Depends on: T-304, T-303, T-111 (Scorer DETECT logic)
- Contract surface: `Telemetry.run_detection(rule, window)` over live SO;
  `capture_baseline(window)` benign window (Q-006); feeds Scorer DETECT.
- Acceptance: DETECT grades correctly against live SIEM with skew_budget +
  clock_offset reconciliation; benign-window FP half enforced.
- Test plan: tester writes `test_detect_grade_against_recorded_bundle` first
  (offline), then the live-SIEM path validated in T-203/T-801 e2e (HOST-SERIAL).
- Effort: M
- Worktree-safe with: S2/S3.
- Agent: detection-engineer
- Status: blocked-on-T-304
- HOST-SERIAL (live SIEM)

---

## M4 — Automated threat-actor runner — STREAM S2 (skeleton) + LIVE-gated

### T-401  ThreatActor skeleton against FAKES (no live exec)          [PARALLEL]
- Depends on: T-101 (ThreatActor port + ScriptedActor fake + AttackEvent shape)
- Contract surface: NativeRunner + AtomicRedTeam **adapter skeletons**;
  in-code lab-CIDR allowlist (`192.168.56.0/24` refusal); ground-truth
  observed-outcome emission shape; `scenario_aborted` on actor crash. **No live
  exploit execution** — exercised only against ScriptedActor/InMemoryLab.
- Acceptance:
  - Runner refuses any target outside the CIDR (in-code, unit-tested).
  - Emits append-only `AttackEvent(v1)` per step with observed outcome; an actor
    crash mid-playbook yields `scenario_aborted` (no phantom gradeable run).
  - Allowlisted technique set only; no autonomous exploit/egress selection.
- Test plan: tester writes first:
  `test_actor_refuses_target_outside_cidr`,
  `test_attack_event_records_observed_outcome_not_intent`,
  `test_actor_crash_emits_scenario_aborted`.
- Effort: M
- Worktree-safe with: S1 (Telemetry) + S3 (Isolation) — disjoint contract
  surfaces; ThreatActor shape locked in T-101.
- Agent: adversary-emulation-engineer
- Status: blocked-on-T-101

### T-402  F2 MITIGATE verification + deny_all_ref negative fixture   [PARALLEL]
- Depends on: T-401, T-101 (mitigate block + deny_all_ref), T-111 (Scorer MITIGATE)
- Contract surface: re-attack-from-base + `service_probe` functional-path check;
  the **F2 contracts-CI deny-everything fixture gate**.
- Acceptance (F2):
  - `service_probe` PASSES against un-mitigated base AND FAILS against the
    reference deny-everything mitigation; exercises the actual functional path,
    not liveness. Any violation → build red.
  - MITIGATE passes only on `outcome:"blocked"` AND healthy `service_probe`.
- Test plan: tester writes first:
  `test_service_probe_passes_unmitigated_base`,
  `test_service_probe_fails_deny_everything`,
  `test_mitigate_requires_blocked_and_healthy`.
- Effort: M
- Worktree-safe with: S1/S3 (uses fakes; no live boot).
- Agent: adversary-emulation-engineer
- Status: blocked-on-T-401

### T-403  LIVE attack execution (NativeRunner + ART, real targets)   [CRITICAL]
- Depends on: T-402, T-203 (web pipeline),
  **T-503b (containment COMPLETE+host-verified, emits `IsolationVerified`)**
- Contract surface: wires the real exploit execution path of NativeRunner/ART
  against live lab targets; ATTACK-pillar reproduction check on a real CVE.
- Acceptance:
  - Live attack runs ONLY with the host tripwire armed (T-503b); any egress →
    `IsolationFailed` + `panic()`; ATTACK pillar reproduces against the manifest.
  - `tripwire_egress_count == 0` asserted across the whole live window.
  - Inherits the SINGLE-enforcement-point refusal from the orchestrator loop
    (defined at T-203): no `IsolationVerified` → live attack refused.
- Test plan: reuses the shared orchestrator-loop pre-flight
  `test_live_attack_refused_without_containment` (refused unless `IsolationVerified`
  present); then HOST-SERIAL live e2e.
- Effort: L
- Worktree-safe with: NONE — **hard safety edge T-503b → T-403** (no live attack
  before containment lands+host-verifies). HOST-SERIAL.
- Agent: adversary-emulation-engineer
- Status: blocked-on-T-402, blocked-on-T-503b
- HOST-SERIAL · SAFETY-GATED

---

## M5 — Containment hardening (gates M4-live) — STREAM S3

### T-501  ADR-0006 — Containment authority + provisioning-window invariant  [PARALLEL]
- Depends on: T-101 (IsolationProvider port + IsolationReport v2 locked)
- Contract surface: documents host-side-continuous authority; `verify_contained()`
  + in-guest probe demoted to corroboration; v4/v6/DNS/docker-bridge planes;
  the **arm/disarm provisioning-window invariant** (DISARMED during sanctioned
  provisioning, RE-ARMED before first attack).
- Acceptance: ADR records the locus-of-authority redesign + the arm window
  `[post-provision, pre-first-attack] → [end-of-attack/teardown]`.
- Test plan: n/a (doc). docs gate passes.
- Effort: S
- Worktree-safe with: all S1/S2 tasks.
- Agent: architect
- Status: blocked-on-T-101

### T-502  IsolationProvider port + nftables egress enforcement (PRIMARY)  [CRITICAL]

> **Split (plan-critic §2 — hidden serialization fix):** the fake-driven CORE
> (`T-502a`) carries no host dependency and lands in parallel with the M2
> critical path; only the host-serial nft-verification TAIL (`T-502b`)
> serializes on the single host. Reassigned the core to a generic `implementer`
> so S3 logic is not bottlenecked behind the single host-bound specialist.

#### T-502a  IsolationProvider core + nft program/assert logic (fake-driven)  [CRITICAL]
- Depends on: T-501, T-101 (IsolationProvider + IsolationReport v2 + CannedReport)
- Contract surface: `HostNftablesTripwire` adapter LOGIC — builds the host `nft`
  `inet` forward-drop ruleset (v4+v6) for BOTH `vboxnet` and the Docker compose
  bridge; DNS-egress-block ruleset (resolver host-only→host→upstream only);
  `verify_contained()` fail-closed pre-flight decision logic (in-guest probe
  corroboration-only); base-snapshot gate. CI-testable entirely via `CannedReport`
  + fake clock/sensor — emits the ruleset/decision, does not apply it to the host.
- Acceptance:
  - Both-plane ruleset generated AND the assert logic verified against CannedReport;
    `route_to_internet`/`bridged_present`/any egress in the report → ABORT +
    `IsolationFailed`.
  - In-guest probe recorded on `IsolationReport` but NEVER the pass condition.
- Test plan: tester writes the CannedReport branch tests FIRST
  (`test_breach_branch_aborts`, `test_guest_probe_never_grants_pass`,
  `test_docker_bridge_plane_asserted`).
- Effort: M
- Worktree-safe with: S1/S2 (Isolation surface locked in T-101); runs parallel to M2.
- Agent: implementer (+ tester writes CannedReport branch tests first)
- Status: blocked-on-T-501

#### T-502b  nft host-verification TAIL (HOST-SERIAL)                  [CRITICAL]
- Depends on: T-502a
- Contract surface: applies the T-502a ruleset to the real host `nft` and proves
  the live forward-drop on both planes.
- Acceptance: real `nft` programmed on the host; both planes asserted live; any
  live egress → ABORT + `IsolationFailed`.
- Test plan: HOST-SERIAL nft verification on the real host.
- Effort: S
- Worktree-safe with: NONE (single-host serial).
- Agent: lab-orchestration-engineer
- Status: blocked-on-T-502a
- HOST-SERIAL (real nft on host)

### T-503  Continuous egress tripwire + panic + arm/disarm window     [CRITICAL]

> **Split (plan-critic §2 — hidden serialization fix):** fake-driven CORE
> (`T-503a`, implementer) lands in parallel; the host-serial verification TAIL
> (`T-503b`, lab-orchestration-engineer) serializes on the single host.
> **`T-503b` (host-verified) is the edge that unblocks T-403.**

#### T-503a  Tripwire + panic + arm/disarm CORE (fake-driven)         [CRITICAL]
- Depends on: T-502a
- Contract surface: continuous host-sensor LOGIC (nft counter / tcpdump
  abstraction behind the sensor port) over each lab-net→uplink path for the WHOLE
  window; `arm_tripwire`/`disarm_tripwire`/`panic`; the provisioning-window
  arm/disarm invariant; `lab panic` decision path (nft-flush egress-cut +
  best-effort serial VM-pause). CI-testable via CannedReport + fake clock/sensor.
- Acceptance:
  - Tripwire armed before + throughout every attack; ANY egress packet (v4/v6/DNS,
    either plane) → `IsolationFailed` + `panic()`.
  - DISARMED during provisioning (benign apt/Packer/box-build must NOT fire
    `panic()`); RE-ARMED before first attack step.
  - `disarm_tripwire()` asserts `tripwire_egress_count == 0` at teardown.
  - `panic` egress-cut decision is sub-second (nft flush); VM-pause best-effort/serial.
- Test plan: tester writes FIRST (CannedReport + fake clock/sensor):
  `test_tripwire_fires_panic_on_any_egress`,
  `test_tripwire_disarmed_during_provisioning_window`,
  `test_tripwire_rearmed_before_first_attack`,
  `test_disarm_asserts_zero_egress_count`,
  `test_panic_egress_cut_sub_second`.
- Effort: M
- Worktree-safe with: S1/S2; runs parallel to M2.
- Agent: implementer (+ tester writes CannedReport branch tests first)
- Status: blocked-on-T-502a

#### T-503b  Tripwire host-verification TAIL + IsolationVerified gate (HOST-SERIAL)  [CRITICAL]
- Depends on: T-503a, T-502b
- Contract surface: arms the real continuous sensor on the host; proves live
  egress → `panic()`; emits the `IsolationVerified` event that gates every live
  attack path.
- Acceptance:
  - Real tripwire fires `panic()` on a live test egress packet (v4/v6/DNS, either
    plane); `tripwire_egress_count == 0` asserted across the verification window;
    `IsolationVerified` event emitted on a clean pass.
- Test plan: HOST-SERIAL verification on the real host.
- Effort: S
- Worktree-safe with: NONE on the safety edge — **completing+verifying T-503b
  unblocks T-403** (the live-attack gate).
- Agent: lab-orchestration-engineer
- Status: blocked-on-T-503a, blocked-on-T-502b
- HOST-SERIAL · SAFETY-CRITICAL

---

## M6 — GOAD / Active Directory phase

### T-601  GOAD-full provisioning (5-VM AD forest)                    [MEDIUM]
- Depends on: T-203 (pipeline proven), T-503b (containment host-verified for
  multi-VM), T-201 (LabProvider VBox)
- Contract surface: GOAD `v3.0.0` commit-pin behind LabProvider (vboxnet plane);
  free-RAM pre-up gate (GOAD-full + SO is the tightest pair, ~48 GiB).
- Acceptance: `lab up goad` brings the forest healthy within the RAM ceiling;
  pre-up free-RAM gate aborts if insufficient; `panic` VM-pause caveat (>1 s, 5 VMs).
- Test plan: provisioning logic CI-tested via fakes; HOST-SERIAL smoke boot gate.
- Effort: L
- Worktree-safe with: M7 (different generator/provider paths) but HOST-SERIAL
  (cannot co-boot with other heavy phases).
- Agent: lab-orchestration-engineer
- Status: blocked-on-T-203, blocked-on-T-503b
- HOST-SERIAL

### T-602  AD attacks (ART atomics) + AD detections + 3-pillar grade [MEDIUM]
- Depends on: T-601, T-403 (live attack path), T-305 (DETECT oracle)
- Contract surface: AtomicRedTeam adapter atomics on GOAD; AD-phase manifest
  oracle (attack/detect/mitigate); grades through the same Scorer (no scorer change).
- Acceptance: ATT&CK-tagged atomics run contained; DETECT/MITIGATE grade against
  the GOAD manifest; replay self-check passes.
- Test plan: tester writes AD-manifest schema + scorer tests against fakes first;
  HOST-SERIAL live e2e gate.
- Effort: L
- Worktree-safe with: M7. HOST-SERIAL · SAFETY-GATED — inherits the single
  orchestrator-loop refusal (`IsolationVerified` required, defined at T-203) via
  T-403; safety edge T-503b → T-403 → T-602.
- Agent: adversary-emulation-engineer + detection-engineer
- Status: blocked-on-T-601, blocked-on-T-403
- HOST-SERIAL

---

## M7 — SecGen containerized generator (post-MVP randomization)

### T-701  ADR-0003 — SecGen containerized toolchain                 [PARALLEL]
- Depends on: T-101 (ScenarioGenerator port locked)
- Contract surface: documents the OCI-containerized SecGen (Ruby 3.2 / Vagrant
  2.2.9 / Packer / libvirt) behind the generator port; toolchain-pin collision
  resolution; "pinned-by-cached-output-box" (not rebuild-reproducible) caveat.
- Acceptance: ADR records the containerization decision + Q-011/Q-012 residuals.
- Test plan: n/a (doc). docs gate passes.
- Effort: S
- Worktree-safe with: M6, M8.
- Agent: architect
- Status: blocked-on-T-101

### T-702  SecGenContainer generator adapter (randomized targets)     [MEDIUM]
- Depends on: T-701, T-203 (pipeline proven), T-002 (pinned SecGen fetch)
- Contract surface: `SecGenContainer` adapter — transforms `marker.xml` →
  `VulnManifest`; extends with detect/mitigate oracles; cached-output-box on
  `/mnt/data/secgen-builds/` (NAT-never, snapshot-bracketed, untrusted).
- Acceptance:
  - A fresh seed → fresh manifest → all three pillars grade with **zero scorer
    changes** (proves manifest-as-oracle on a randomized target, PRD F3).
  - Box built once + cached; never rebuilt-from-seed in normal operation.
- Test plan: tester writes `test_secgen_marker_to_manifest_schema_valid` and
  `test_fresh_seed_yields_distinct_scorable_manifest` first (manifest-only),
  then HOST-SERIAL build/boot gate.
- Effort: L
- Worktree-safe with: M6. HOST-SERIAL (box build/boot).
- Agent: lab-orchestration-engineer
- Status: blocked-on-T-701, blocked-on-T-203
- HOST-SERIAL

---

## M8 — Validation harness tiers + reproducibility

### T-801  `lab validate` tiers + ValidationEvent ledger fold        [MEDIUM]
- Depends on: T-203 (e2e web exists), T-110 (fold), T-004 (ledger skeleton)
- Contract surface: `lab validate --smoke|--e2e|--pair`; ValidationEvent fold →
  green/red matrix (`lab report`); the e2e tier asserts arm-tripwire →
  attack → detect → mitigate → re-attack → `tripwire_egress_count==0` → teardown.
- Acceptance:
  - `--smoke` boot/health/down; `--e2e` full loop green; report = fold of the
    JSONL ledger. Harness logic CI-tested via InMemoryLab.
- Test plan: tester writes `test_validation_ledger_folds_to_matrix` and
  `test_e2e_tier_asserts_zero_egress_count` against fakes first.
- Effort: M
- Worktree-safe with: T-803 (different assertions).
- Agent: lab-orchestration-engineer + implementer
- Status: blocked-on-T-203
- HOST-SERIAL (e2e real-boot tier)

### T-802  `--pair` rotation + teardown-leaves-no-residue assertion   [MEDIUM]
- Depends on: T-801, T-503b (nft ruleset baseline, host-verified), T-303 (Fleet enrollment)
- Contract surface: `lab validate --pair <a> <b>` adjacent log-flow + the m5
  rotation residue assertion (nft ruleset + VBox registry + Fleet enrollment
  back to baseline after teardown).
- Acceptance:
  - Boot pair A → teardown → assert nft/VBox/Fleet at baseline → boot pair B; a
    leaked nft rule / stale VM registration / lingering enrollment FAILS the check.
  - Inter-phase log-flow proven for one adjacent pair within the RAM ceiling.
- Test plan: tester writes `test_teardown_restores_baseline_state` against fakes
  first; HOST-SERIAL pair-rotation gate.
- Effort: M
- Worktree-safe with: T-803.
- Agent: lab-orchestration-engineer
- Status: blocked-on-T-801
- HOST-SERIAL

### T-803  Reproducibility assertions                                 [MEDIUM]
- Depends on: T-801, T-002 (pinned fetch)
- Contract surface: reproducibility checks — pinned-from-one-command bring-up;
  Vulhub determinism (`@sha256`); SecGen "pinned-by-cached-output-box" claim
  (rebuild-reproducibility gated on Q-012 Option A, NOT claimed for MVP).
- Acceptance: a phase boots green from pinned refs with no manual version edits
  (PRD F4); reproducibility claims are honest (no rebuild-repro claim absent Q-012-A).
- Test plan: tester writes `test_bring_up_from_pins_no_manual_edit` first;
  HOST-SERIAL boot gate.
- Effort: M
- Worktree-safe with: T-802.
- Agent: lab-orchestration-engineer
- Status: blocked-on-T-801
- HOST-SERIAL

---

## Critical path

```
T-001 → T-003 → T-101 (M1a contract lock, BLOCKER) → T-110 (EventStore)
      → T-111 (Scorer 3-pillar) → T-201 (LabProvider) → T-202 (Vulhub gen)
      → T-203 (e2e 3-pillar grade — MVP EXIT)
```

- **Bottleneck tasks:** **T-101** (all fan-out blocks on it), **T-111**
  (the honest-scoring core — F1/F2 grading logic), **T-203** (the HOST-SERIAL
  MVP convergence where three specialists + the scorer + real adapters meet).

### POST-MVP CRITICAL PATH (NOT slack — plan-critic C5)

```
T-101 → T-501 → T-502 (T-502a core ∥ M2; T-502b host-tail) → T-503
      (T-503a core ∥ M2; T-503b host-tail, emits IsolationVerified)
      → T-403 (LIVE attack) → T-602 (AD live attack — FULL-PROJECT FINISH LINE)
```

- **S3 (containment: T-501 / T-502 / T-503) and T-403, T-602 are the POST-MVP
  CRITICAL PATH — they are NOT a slack stream.** The full-project finish line is
  **T-602**, and it runs THROUGH **T-503 → T-403**. Containment GATES every live
  attack (T-203 too, via the T-502 edge), so it cannot be deprioritized.
- **The orchestrator MUST NOT treat "MVP exit at T-203" as "project done"** and
  drop containment to a slack stream. MVP exit ≠ project finish; the project is
  not done until T-602 lands behind verified containment.
- **Added post-MVP bottleneck: T-503** (its host-verified tail T-503b emits
  `IsolationVerified` and therefore gates ALL live attack — T-203 / T-403 / T-602).

## Parallel streams (worktree fan-out candidates)

After **T-101 (contracts/fakes locked)** lands, and once **T-201 (LabProvider)**
exists for the boot-dependent halves, three streams run in parallel against the
**fakes** — each touching a disjoint port/contract surface:

- **Stream S1 — Detection plane (M3):** T-301, T-302, T-303, T-304, T-305.
  Independence: touches ONLY the `Telemetry` port + `DetectionRule`/`OnboardSpec`
  contracts (locked in T-101); develops against `ReplayLogBundle`/recorded logs.
- **Stream S2 — Threat-actor skeleton (M4):** T-401, T-402. Independence: touches
  ONLY the `ThreatActor` port + `AttackEvent`/mitigate contracts; develops
  against `ScriptedActor`/`InMemoryLab`. **NO live execution in this stream.**
- **Stream S3 — Containment CORE (M5):** T-501 (ADR), **T-502a, T-503a** (the
  fake-driven cores, now `implementer`-owned + `tester`-first). Independence:
  touches ONLY the `IsolationProvider` port + `IsolationReport v2`; develops
  against `CannedReport`. **This stream is POST-MVP CRITICAL PATH, not slack.**
  The host-serial verification TAILS (**T-502b, T-503b**) serialize on the single
  host with the M2 critical path regardless of agent — only `lab-orchestration-
  engineer` runs them. T-503b emits `IsolationVerified` and gates ALL live attack.

- **Serial after streams land:** T-403 (live attack) depends on **both** S2
  (T-402) **and** S3's host-verified tail (**T-503b**). T-602 (AD) depends on
  T-403 + T-601 + T-305.
  All real-boot / live-SIEM / nft / box-build steps are **HOST-SERIAL** (single
  host, RAM ceiling) — they cannot run concurrently on the host even when their
  code is independent.

## False concurrency caught (and how resolved)

1. **S1/S2/S3 sharing event/manifest/report shapes.** If the detect, attack,
   isolation, and scoring shapes were each authored inside their own milestone,
   the three streams would all be mutating the same contract surface — classic
   false concurrency. **Resolved by the M1a contract-lock blocker (T-101):**
   every shape + every port + every fake is defined ONCE, up front; the streams
   then consume frozen contracts and only ADD adapter code. New fields are
   additive only (charter #2). Streams are genuinely disjoint *because* T-101
   exists. **Extended (plan-critic C1):** the shared-infra FILES are also carved
   into M1a so streams never collide on them — the FULL `lab` dispatch table
   (T-004, incl. stream sub-commands), the adapter registry (T-101, all eight
   slots stubbed), the CI workflow structure (T-003, all stages incl. contracts/
   F1/F2 stubbed), and the unified dependency manifest (T-103, all three streams'
   pins added once). After M1a, S1/S2/S3 are ADDITIVE-ONLY — they add files under
   `adapters/<domain>/*` and fill in already-registered stubs, never editing the
   dispatch, registry, workflow, or `pyproject.toml`.
2. **F1 / F2 CI gates appearing in M3/M4 only.** The calibration/deny-all schema
   blocks (`calibration{}`, `deny_all_ref`, `service_probe`) are part of the
   `VulnManifest`/`DetectionRule` shapes — if they were authored in T-304/T-402
   they would change the contract surface S2/S1 share. **Resolved:** the *shapes*
   are in T-101; T-304/T-402 only wire the *gate behavior* against those locked
   shapes.
3. **T-201 vs T-202 claimed parallel.** Both touch the generate→bring-up glue and
   both are HOST-SERIAL. **Resolved by resequencing:** T-202 depends on T-201
   (not parallel); LabProvider lands before the Vulhub generator wires onto it.
4. **T-304 split dependency.** The F1 *fixture* gate needs only T-101 (offline,
   recorded bundles) and can start early; the *live* half needs T-303 (live SIEM).
   **Resolved:** marked as a split dependency so the offline gate is not falsely
   blocked behind the live-SIEM boot.

## M5 → M4-live safety edge (visible, non-negotiable)

```
   T-502 (nft PRIMARY containment, host-verified via T-502b)
        │  guards T-203's MVP e2e attack too (C3)
        ▼
   T-503b (tripwire + panic + arm/disarm, host-verified — emits IsolationVerified)
        │  HARD EDGE
        ▼
   T-403 (LIVE attack execution)   ── refused unless IsolationVerified present
        │
        ▼
   T-602 (AD LIVE attack — inherits the same single-point refusal)
```

The M4 **skeleton** (T-401/T-402) runs in parallel against fakes with no live
execution. The fail-closed pre-flight `test_live_attack_refused_without_containment`
(requires an `IsolationVerified` event) lives in the **orchestrator loop as the
SINGLE enforcement point** — so EVERY attack path inherits it from one place:
T-203 (MVP e2e), T-403 (web live), T-602 (AD live). The live-attack tasks carry
explicit edges on the host-verified containment (T-502 → T-203; **T-503b →
T-403**); T-602 inherits via T-403.

## Open ADRs (now mapped to tasks)

> Numbering clash RESOLVED (plan-critic C4): the store/tamper-evidence ADR is
> **ADR-0007**, freeing ADR-0005 for sequential-scope only.

- **ADR-0002 (hypervisor)** → **T-006** (write at M0, finalize at T-201/M2).
- **ADR-0003 (SecGen-containerized)** → **T-701** (write before M7/T-702).
- **ADR-0004 (SO-primary-SIEM)** → **T-301** (write at M3 head).
- **ADR-0005 (sequential-scope)** → **T-007** (write at M0).
- **ADR-0006 (containment-authority + provisioning-window)** → **T-501** (write
  before M5 code; must record the provisioning-window arm/disarm invariant).
- **ADR-0007 (store / hash-chain tamper-evidence)** → **T-100** (write before
  T-110 ledger). *(Renumbered from the clashing "ADR-0005-store".)*

## Followups (not blockers; from `/critique` and `/phase-review`)

- [ ] **F-001 (Q-014)** — DETECT calibration fixtures are sole-authored + depend
  on the Q-006 benign baseline.
  - Source: RED-TEAM.md 2026-05-30, F1 residual. Severity: 🟠 — accepted.
  - Trigger: a calibration fixture is found to pass a bad rule, or Q-006 finalized.

## Open questions (decisions still needed before/within the graph)

- **O-1 (ADR numbering clash) — RESOLVED (plan-critic C4).** The store/tamper-
  evidence ADR collided with the reserved ADR-0005 (sequential-scope).
  **Renumbered to ADR-0007**; T-100 writes under ADR-0007. Authoritative map:
  0002 hypervisor · 0003 SecGen-containerized · 0004 SO-primary-SIEM ·
  0005 sequential-scope · 0006 containment-authority+provisioning-window ·
  0007 store/tamper-evidence. (ARCHITECTURE.md ADR list updated to add 0007.)
- **O-2 (SecGen pin, Q-011/Q-012).** Exact SecGen commit + known-good frozen
  base box are still unselected; T-002 and T-702 cannot fully pin until resolved.
  Rebuild-reproducibility (T-803) stays unclaimed unless Q-012 Option A is adopted.
- **O-3 (SO unattended install, Q-002).** T-302 assumes an unattended/airgap SO
  2.4.211 path exists; if only the interactive installer is viable, T-302 effort
  rises and the e2e SO smoke gate needs a manual-step carve-out.
- **O-4 (benign baseline source, Q-006).** The DETECT FP half (T-305) and F1
  calibration (T-304) depend on a defined benign baseline window source; finalize
  before T-305 grades live.
- **O-5 (Q-007 live-SIEM vs offline-replay grading).** If offline-replay grading
  is chosen, T-305 grades via `ReplayLogBundle` and the live-SIEM HOST-SERIAL
  dependency on T-302/T-303 relaxes — decide before S1 wires its live half.

## Done

Move tasks here when merged, keep the ID for traceability.

- (none yet — planning complete, awaiting plan-critic validation + gates.)
