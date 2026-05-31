# CHANGELOG

All notable changes to this project are recorded here.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning: [Semantic Versioning](https://semver.org/).

Updated by the `docs-keeper` agent on every PR. Code changes that don't
touch this file are blocked by CI (`.github/workflows/ci.yml` →
`docs-discipline` job).

## [Unreleased]

### Added
- T-101: **M1a contract lock (GATE A passed, clean-room PASS loop 1)** — the
  contract spine, all stdlib-only / additive / version-first. NEW `contracts/`
  package: 13 versioned persisted shapes as frozen dataclasses (`scenario`,
  `vuln_manifest(v2)`, `onboard_spec`, `detection_rule(v2)`, `attack_event`,
  `isolation_report(v2)`, `validation_event` [references `lab.ledger.ValidationEvent`,
  not redefined], `scenario_generated(v2)`, `attack_executed`, `scenario_aborted`,
  `submission`, `verification_result(v2)`, `score_awarded(v2)`), each loadable via
  `load_<shape>()` returning a frozen instance or raising `contracts.SchemaError`
  (incl. nested-field validation). `contracts.SCHEMAS` holds stdlib-validated
  JSON-Schemas (no `jsonschema` dep). Invariants implemented: `canonical_json`,
  `manifest_hash = sha256(canonical_json(victim, vulns, seed))`, `idempotency_key =
  (scenario_id, challenge_id, pillar, manifest_hash)`, and `mint_correlation_id(rng)`
  (Rng-port-minted, **F-006**). `dump()` is lossless, version-first, and deep-copies
  nested containers (no aliasing into frozen instances). NEW `ports/` package: 8
  `@runtime_checkable` Protocols (LabProvider, ScenarioGenerator, ThreatActor,
  Telemetry, IsolationProvider, EventStore, Clock, Rng), no vendor SDK. NEW
  `adapters/` package: 8 conforming fakes (InMemoryLab, FixedManifestGen,
  ScriptedActor, ReplayLogBundle, CannedReport, InMemoryEventStore, FixedClock,
  SeededRng) + `REGISTRY` (8 ADD-only slots). 294 passed / 6 skipped (the 6 skips
  are event shapes with no container field to test aliasing on). See
  [`docs/TODO.md`](TODO.md) T-101.
- **M0 milestone complete (2026-05-31)** — repo hygiene, push-blocking CI gate,
  `lab` CLI + ValidationEvent(v1) ledger, `/mnt/data` storage layout, and the
  pinned dependency fetcher all merged to `main`; 133 tests green; CI live and
  branch protection requires all 10 stage checks. Next: T-101 (M1a contract
  lock = GATE A). See [`docs/TODO.md`](TODO.md) M0 section.
- T-006: ADR-0002 — hypervisor/provisioner behind a `LabProvider` port
  (VirtualBox-now / libvirt-deferred / DockerCompose); documents the port methods
  (`bring_up/tear_down/snapshot/restore/status`) + base-snapshot rule —
  [`docs/ADR/0002-hypervisor-behind-labprovider.md`](ADR/0002-hypervisor-behind-labprovider.md).
- T-007: ADR-0005 — sequential / scenario-scoped scope; records why simultaneous
  all-phase boot is out of scope and how the adjacent-pair co-residency model
  satisfies inter-phase communication under the RAM ceiling —
  [`docs/ADR/0005-sequential-scenario-scoped-scope.md`](ADR/0005-sequential-scenario-scoped-scope.md).
- T-002: pinned dependency fetcher — `lab/fetch_deps.py` (stdlib-only) behind a
  `Fetcher` port (charter #3): `GitFetcher` clone+checkout adapter, a
  deterministic `tree_sha256` integrity digest (sorted `path\0sha256(bytes)`,
  `.git` excluded — clone-layout-independent), and a `fetch_all` orchestrator
  enforcing the SHA256 checksum gate (refuses + cleans up on mismatch),
  idempotent no-op re-runs (ALREADY_PRESENT, fetcher not re-invoked), pending-pin
  refusal (SecGen / Q-011 — never clones master), dest-under-vendor_base, and a
  collect-all-errors fail policy (`AggregateFetchError`). `load_manifest()` holds
  the ARCHITECTURE.md pins (Vulhub, ART, GOAD = v3.0.0 commit-resolved; SecGen
  pending); resolved-dep digests are TOFU (trust-on-first-use) sentinels
  recorded on first verified fetch. Thin `scripts/fetch-deps.sh` shim execs
  `python3 -m lab.fetch_deps`. `main()` is an injectable argparse CLI with two
  actions: `list` (default, offline-safe, creates nothing) prints the manifest;
  `fetch` actually runs `fetch_all` (PROD defaults `GitFetcher` + the
  StorageLayout `vendor` dir under `DEFAULT_BASE`, wired lazily inside the
  `fetch` branch only — never at import or on `list`), printing a per-dep result
  line (fetched / already-present / pending / first-fetch / FAILED) and exiting
  nonzero if any dep failed. Operator-legible errors: a TOFU-sentinel mismatch
  reads as a first-fetch "verify the upstream, then record the printed sha256"
  prompt, while a real 64-hex mismatch reads as an alarming possible-tampering
  signal (the two are deliberately distinct for a security tool); a pending pin
  (SecGen) points the operator at `docs/OPEN-QUESTIONS.md` (Q-011) in plain
  language rather than a bare lore token.
- T-005: `/mnt/data` storage-layout bootstrap + relocation config — `lab/storage.py`
  (stdlib-only, pure `pathlib`). Computes the 7 canonical artifact subdirs
  (`vendor boxes vbox secgen-builds box-cache work state`) under a base,
  `ensure_layout()` creates them idempotently, and `relocation_env()` points
  `VAGRANT_HOME`/VBox machine folder at `/mnt/data` to keep the root tree < 50 MB.
- Project bootstrap for **Purple Range** (codename Phalanx) — a single-user,
  single-host purple-team training lab; clean rebuild of `cyber-range`.
- Framework scaffold (CLAUDE.md operating manual, `.claude/` agents + skills,
  ENGINEERING.md charter, doc templates).
- Society-of-minds brainstorm — [`docs/BRAINSTORM.md`](BRAINSTORM.md).
- Product requirements — [`docs/PRD.md`](PRD.md).
- System design + contract catalog — [`docs/ARCHITECTURE.md`](ARCHITECTURE.md).
- ADR-0001 (manifest-as-oracle + event-sourced scoring) —
  [`docs/ADR/0001-manifest-oracle-event-sourced-scoring.md`](ADR/0001-manifest-oracle-event-sourced-scoring.md).
- Open questions register — [`docs/OPEN-QUESTIONS.md`](OPEN-QUESTIONS.md).
- Red-team review record — [`docs/RED-TEAM.md`](RED-TEAM.md): critic GO-WITH-FIXES,
  3 FATAL (F1 DETECT calibration, F2 MITIGATE functional-path, F3
  containment-authority redesign → ADR-0006 reserved) + 5 MATERIAL folded;
  confirming pass FIXES CONFIRMED.
- Milestone TODO spine (M0–M8 + open ADRs) — [`docs/TODO.md`](TODO.md).
- plan: decomposed + validated + gated (2026-05-30) — `/decompose` task graph
  (T-001..T-803) validated by `plan-critic` and recorded as the binding
  [`docs/DELIVERY-PLAN.md`](DELIVERY-PLAN.md): MVP critical path
  T-001→T-003→T-101→T-110→T-111→T-201→T-202→T-203; post-MVP critical path
  through T-501→T-502→T-503→T-403→T-602 (containment is critical, not slack);
  three true parallel streams after the M1a contract-lock blocker (S1 detection,
  S2 threat-actor skeleton, S3 containment core); four clean-room hostile-review
  gates A–D. Cross-linked TODO ↔ DELIVERY-PLAN ↔ ARCHITECTURE ↔ RED-TEAM.
- infra: published repo (public) + solo branch protection; refreshed handoff for
  execution phase (2026-05-31).
- T-001: `scripts/size_guard.py` — stdlib-only repo size-guard (the T-001 forward
  guard, wired to CI's `size-guard` stage). Pure `find_violations()` walks the
  tracked tree (skipping `.git`/`vendor`/`__pycache__`/`.pytest_cache`/
  `node_modules`, never following symlinked dirs), flags `oversized-blob`
  (> 5 MiB/file) and `total-exceeded` (> 50 MiB/tree) on a strict greater-than
  boundary; thin `main()` CLI exits nonzero on any violation. 17 contract tests.
- T-001: expanded `.gitignore` — `vendor/`, the in-repo equivalents of the
  `/mnt/data` storage-layout dirs (`work/`, `state/`, `boxes/`, `vbox/`,
  `secgen-builds/`, `box-cache/`), Python noise, and Vagrant/VirtualBox local
  dirs. (`/mnt/data` itself is an absolute host path outside the repo — no
  ignore entry needed; noted inline.)
- T-003: thin push-blocking CI skeleton — `.github/workflows/ci.yml` declares
  all ten stages up front, each carrying a collision-free `stage:<token>` marker
  so later tasks only add fixtures inside an already-declared stage and never
  edit the layout (plan-critic C1). Stages: lint (ruff/yamllint/ansible-lint +
  shellcheck scoped to our `scripts/*.sh` only, so tester-owned
  `tests/fixtures/**` and framework `.claude/**` shell scripts cannot redden
  this PR's CI on SC2164), unit (pinned `pytest==8.3.4` over `tests/`),
  contracts / f1-calibration / f2-mitigate (**declared placeholders** — green
  no-op stubs wired later in T-101 / T-304 / T-402), syntax
  (vagrant/ansible/compose/packer validate, each guarded to skip cleanly until
  its inputs exist), pins, docs (`mkdocs build --strict`, guarded until
  `mkdocs.yml` lands), secrets (`gitleaks/gitleaks-action@v2`), and size-guard.
  Triggers on `pull_request`; python 3.12; all action + pip versions pinned.
- T-003: `scripts/pins_gate.py` — stdlib-only dependency-pin gate (CI `pins`
  stage). Pure `find_pin_violations()` walks an injectable root (no
  git/network/subprocess) and flags `docker-latest` (`:latest`/untagged image
  refs; version tag or `@sha256` digest is OK), `unpinned-box-version` (a
  Vagrant/yaml box with no `box_version`/`version` in the same file), and
  `bare-git-clone` (a `git clone` not pinned inline by `--branch vX.Y.Z` or by a
  `git checkout <40-hex sha>`/`vTAG` within the next 3 non-blank lines). Scans
  yml/yaml/Dockerfile/compose/Vagrantfile/sh and `.md` fenced code blocks only
  (prose is never flagged); skips ONLY the root-relative path `tests/fixtures`
  (the deliberately-bad negative-test corpus) — matched by relative path, not
  bare dirname, so a real violation under any *other* future `fixtures` dir
  (e.g. planned DETECT calibration fixtures) is still caught. size-guard does
  NOT skip it (byte accounting must reflect the whole tracked tree).
  Thin `main()` CLI exits nonzero on any violation. 20 contract tests.
- T-003: `ruff.toml` — lint config for our tooling (py312; F/I/E/W, E501 off;
  `F401` ignored under `tests/**` for pytest mark/fixture imports).
- T-003: size-guard CI stage invokes `size_guard.py .` with an explicit root,
  closing the T-001 missing-root false-pass (`os.walk` silently yields nothing
  for a nonexistent path).
- T-003: CI tool-version pins are single-sourced — `ruff`/`pytest`/`yamllint`
  `pip install` steps now reference the top-level `env:` vars
  (`${{ env.RUFF_VERSION }}` etc.) instead of re-hardcoding the strings, so a
  bump edits one place and cannot drift. Placeholder vs skip-when-absent stages
  now carry self-documenting inline markers (`# PLACEHOLDER (wired in T-xxx)` vs
  `# SKIP-WHEN-ABSENT`) so a contributor copying a stage won't leave a stray
  `exit 0` in a real check.
- T-004: `lab/` package — the locked CLI dispatch scaffold + ValidationEvent(v1)
  ledger skeleton. `lab/cli.py` registers the FULL argparse dispatch table up
  front (plan-critic C1) — six top-level verbs (`up down reset validate status
  panic`, each with an optional `<phase>`; `validate` also takes `--smoke`/
  `--e2e`/`--pair`) and three stream sub-command groups (`detection onboard`,
  `threat-actor run`, `isolation arm`/`disarm`) — so streams S1/S2/S3 register
  against a fixed argparse surface. (The per-command handler-dispatch *body* seam
  is NOT built yet — `main()` builds the event inline; T-101 adds the
  `check -> handler` seam before fan-out, followup F-007.) Each recognized command appends
  exactly one `not-implemented` ValidationEvent with its pinned `check` string
  and exits 0; an unknown command is an argparse error (nonzero, no event).
  `lab/ledger.py` defines the versioned, frozen `ValidationEvent` (charter #2 —
  `version:int` first and serialized; `phase`/`evidence_ref=None` → JSON null),
  the append-only `Ledger` port (charter #4) with `JsonlLedger` (prod, one JSON
  line/event, append-mode, never truncates) + `InMemoryLedger` fake, and the
  `Clock` port with `FixedClock` (test) + `SystemClock` (prod). cli.py stamps
  `ts` from the injected clock — never `datetime.now()` — and imports NO vendor
  SDK/concrete provider, sitting over the T-101 `LabProvider` seam. `python -m
  lab` works via `lab/__main__.py`. 43 contract tests (20 CLI + 23 ledger).

### Changed
- T-101: `lab/cli.py` — **F-006** closed: `main()` now takes an injected `rng=`
  and mints `run_id` from the Rng port (`uuid4` removed) — no unported randomness
  survives M1a. **F-007** closed: a `HANDLERS` `check -> handler` dispatch table
  added so a registered handler replaces the default not-implemented event-append
  path; S1/S2/S3 fill command bodies by ADD, never editing `main()`.
- Containment model hardened (critic F3): host-side nftables forward-drop as the
  primary enforcement + continuous host-side egress tripwire (v4/v6/DNS, vboxnet
  and Docker bridge planes) as the real gate; in-guest probe demoted to
  corroboration only. Added the **provisioning-window invariant** — tripwire is
  disarmed during the sanctioned provisioning window (NAT-on, Q-012) and re-armed
  before the first attack step so benign provisioning traffic never fires
  `panic()`.
- plan-critic corrections C1–C5 folded into [`docs/TODO.md`](TODO.md): shared-infra
  files (lab dispatch table, adapter registry, CI workflow, dependency manifest
  T-103) carved into the M1a blocker so streams stay file-disjoint (C1); T-502/T-503
  split into fake-driven cores (implementer) + host-serial verification tails (C2);
  T-203 gated behind containment (`blocked-on: T-502`) with a single-point
  fail-closed live-attack refusal in the orchestrator loop (C3); the store ADR
  renumbered **ADR-0005-store → ADR-0007** to clear the sequential-scope clash —
  ARCHITECTURE.md ADR list updated (C4); S3 + T-403 + T-602 re-labelled POST-MVP
  CRITICAL PATH (not slack), full-project finish line T-602 (C5).

---

## [0.1.0] — 2026-05-30

### Added
- Initial planning bootstrap: framework scaffold, society-of-minds brainstorm,
  PRD + ARCHITECTURE + ADR-0001, critic red-team + folded fixes. Planning
  complete; awaiting architecture sign-off before build.

[Unreleased]: https://github.com/curlyjoeyaknow/purple-range/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/curlyjoeyaknow/purple-range/releases/tag/v0.1.0
