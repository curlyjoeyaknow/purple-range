# CHANGELOG

All notable changes to this project are recorded here.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning: [Semantic Versioning](https://semver.org/).

Updated by the `docs-keeper` agent on every PR. Code changes that don't
touch this file are blocked by CI (`.github/workflows/ci.yml` →
`docs-discipline` job).

## [Unreleased]

### Added
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

### Changed
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
