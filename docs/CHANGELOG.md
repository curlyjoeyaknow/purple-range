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

### Changed
- Containment model hardened (critic F3): host-side nftables forward-drop as the
  primary enforcement + continuous host-side egress tripwire (v4/v6/DNS, vboxnet
  and Docker bridge planes) as the real gate; in-guest probe demoted to
  corroboration only. Added the **provisioning-window invariant** — tripwire is
  disarmed during the sanctioned provisioning window (NAT-on, Q-012) and re-armed
  before the first attack step so benign provisioning traffic never fires
  `panic()`.

---

## [0.1.0] — 2026-05-30

### Added
- Initial planning bootstrap: framework scaffold, society-of-minds brainstorm,
  PRD + ARCHITECTURE + ADR-0001, critic red-team + folded fixes. Planning
  complete; awaiting architecture sign-off before build.

[Unreleased]: https://github.com/memeworldorder2024/purple-range/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/memeworldorder2024/purple-range/releases/tag/v0.1.0
