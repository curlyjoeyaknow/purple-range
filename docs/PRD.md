# PRD — Purple Range (codename Phalanx)

> Status: draft
> Last updated: 2026-05-30
> Tier: large
> Spine: [`docs/BRAINSTORM.md`](BRAINSTORM.md) · Architecture: [`docs/ARCHITECTURE.md`](ARCHITECTURE.md) · ADR: [`docs/ADR/0001-manifest-oracle-event-sourced-scoring.md`](ADR/0001-manifest-oracle-event-sourced-scoring.md) · Open questions: [`docs/OPEN-QUESTIONS.md`](OPEN-QUESTIONS.md) · Red-team: [`docs/RED-TEAM.md`](RED-TEAM.md) · TODO: [`docs/TODO.md`](TODO.md)

## Problem

The owner self-trains in offensive **and** defensive security, but the existing
`cyber-range` repo (the "Phalanx" prototype) only honestly rewards the *attack*
half: its DETECT grading runs a hardcoded reference query the learner never
submits, and its MITIGATE grading can be cheated by simply breaking the service.
Progress is a single mutable JSON file with no audit or replay. Targets are
static, so a challenge is worthless after the first solve. Six gigabytes of
vendored clones bloat the tree, toolchain pins collide (host Vagrant 2.4.3 vs
SecGen's 2.2.9), and "all phases inter-communicate" was never physically
possible on one host. The result: a lab that *looks* like a purple-team trainer
but only scores red, can't be reproduced from one command, and can't be trusted
to stay network-isolated when automated attackers run. **Purple Range** is the
clean rebuild that makes all three pillars honestly scorable, reproducible, and
provably contained.

## Audience

A single user: **the owner**, training solo on their own bare-metal host
(Ryzen 7 9800X3D, 60 GiB RAM, `/dev/kvm` available, lab artifacts on a 1.7 TB
`/mnt/data` NVMe). Not a multi-tenant CTF platform, not a published product, not
a team trainer. Optimize for **reliability on this host and honest scoring**
over publish polish or contributor scaffolding.

## Goals (and non-goals)

### Goals

- **Three-pillar scoring, honestly graded against an oracle, never hardcoded.**
  Every challenge scores: (1) **ATTACK** a target, (2) **DETECT** it as
  blue-team, (3) **MITIGATE/harden** so the attack is prevented — MITIGATE worth
  the most points.
- **Manifest-as-oracle:** the scenario generator emits a versioned
  `vuln_manifest` (expected vulns + TTPs + detections + mitigations) that travels
  *with* the target, so even a **randomized** target stays scorable.
- **Modern attacks with run-guides**, MITRE ATT&CK-tagged, across the lab phases:
  Web/Linux → Splunk host-lens (p1) → Adversary emulation (p2) → Security Onion
  network-lens (p3) → GOAD Active Directory (p4) → SecGen randomized targets (p5).
- **Reproducible from one command** per phase: `lab up <phase>` provisions from
  pinned refs + checksums; `lab validate` proves the loop end-to-end.
- **Provably network-isolated:** containment is enforced code (fail-closed
  pre-flight + host firewall + kill-switch), not prose, *before* any automated
  attack runs.
- **Auditable, replayable, tamper-evident scoring:** state is a fold over an
  append-only, hash-chained event log.

### Non-goals (explicit out-of-scope)

- **Simultaneous all-phase boot.** Physically impossible on a 55-GiB-usable
  host. Scope is sequential / scenario-scoped (see Scope below). Cross-phase
  log-flow is proven for **one adjacent pair at a time**.
- **Autonomous exploit-selection.** v1 threat actors are bounded to an
  **allowlisted technique set**; no actor picks its own exploit or egress
  (→ Q-004).
- **Publishing / multi-tenant / shared scoreboard.** Single-user, single-host.
- **Enterprise compliance** (SOC2, audit-for-others, RBAC, retention SLAs). The
  hash-chain gives *personal* tamper-evidence, not a regulated audit trail.
- **Splunk as a first-class SIEM.** Security Onion / Elastic is the primary
  blue-team pane; Splunk is an optional Windows/Sysmon teaching lens behind a
  flag (→ Q-003).
- **A general scenario-authoring GUI.** Oracles are authored as versioned files
  for a small initial N of vuln classes (→ Q-008).

## Success criteria

How we know it works.

### Functional

- **F1 — Honest DETECT.** The learner *submits* a detection query; the scorer
  runs it over the attack's ground-truth window (must return `>= expected_min_hits`)
  AND over a benign baseline window (must return `<= max_false_positives`). PASS
  only if both hold. No hardcoded reference query anywhere in the grading path.
- **F2 — Cheat-proof MITIGATE.** A pillar passes only when the re-run attack
  reports `outcome:"blocked"` **and** a positive `service_probe` confirms the
  service is still healthy. Breaking the service fails the pillar.
- **F3 — Scorable randomized target.** A SecGen (or config-randomized) target
  with a fresh seed produces a fresh `vuln_manifest`, and all three pillars grade
  correctly against it with no per-challenge hardcoded answers.
- **F4 — One-command phase bring-up.** `lab up web` (and each phase) provisions
  green from pinned refs to a healthy, telemetry-enrolled state with no manual
  edits to version URLs.
- **F5 — Proven adjacent-pair log-flow.** `lab validate --pair p3 p4` boots two
  adjacent phases and asserts an attack on one shows up in the other's telemetry.
- **F6 — Enforced containment.** With NAT attached or a route-to-internet
  present, the fail-closed pre-flight ABORTS the attack and emits
  `IsolationFailed`. `lab panic` pauses all VMs and flushes host forwarding
  sub-second.
- **F7 — Replayable scoring.** Deleting the derived state and folding the event
  log reproduces the identical scoreboard; tampering with any event row breaks
  the hash chain and is detected.

### Performance / NFR

| Property | Target | Measured by |
|---|---|---|
| CI tier wall-clock | < 5 min, push-blocking, zero VMs | CI job duration |
| `lab validate --smoke <phase>` | boots → health → down within phase RAM budget | ValidationEvent ledger |
| `lab validate --e2e <phase>` | full attack→detect→mitigate→re-attack loop green | ValidationEvent ledger |
| Adjacent-pair RAM | ≤ ~55 GiB usable (GOAD-full + SO ≈ 48 GiB is the tightest pair) | host free-RAM probe pre-up |
| Containment pre-flight | runs before *every* attack step; fail-closed | `IsolationVerified`/`Failed` events |
| `lab panic` latency | sub-second host-side cut (does not trust guests) | wall-clock of nft flush |
| Tracked repo size | < ~50 MB (from 6.2 GB); no tracked blob > 5 MB | CI size-guard |
| Scoring store integrity | hash-chain verifies on every fold | replay self-check |

**Validation tiers** (two physical tiers — see ARCHITECTURE §Validation):

- **CI tier** (cloud, no VMs): lint, unit, contract-schema, syntax, pin-gate,
  docs, secrets, size-guard. Target < 5 min, push-blocking.
- **Local harness** (`lab validate`): `--smoke` (boot/health/down), `--e2e`
  (full loop), `--pair <a> <b>` (adjacent log-flow). Real VMs, owner's host only.

### Adoption / outcome

Single-user outcome measures: (a) the owner can author a new scorable challenge
(all three oracles) for a new vuln class without touching scorer code; (b) a
phase the owner hasn't touched in a month still boots green from pinned refs;
(c) the owner trusts the scoreboard enough to use rank as a real progress signal
(no honor-system inflation — unverifiable claims live in a separate UNVERIFIED
bucket that does not count toward rank).

## Constraints

### Hard

- **Single host, RAM-bound.** 60 GiB total, ~55 GiB usable for guests. Sequential
  scope is mandatory; only adjacent pairs co-resident, within budget.
- **Network isolation is non-negotiable.** Single host-only plane
  `192.168.56.0/24`; NAT off by default after provisioning; host firewall
  forward-drop; actors reject any target outside the CIDR. Fail-closed.
- **Charter minimum patterns** (`ENGINEERING.md`, `CLAUDE.md`): append-only
  events for persisted state; ports & adapters at *every* external boundary
  (hypervisor, SIEM, scenario generator, vendor attack tools, clock, randomness);
  `version: int` on everything persisted; spec & contracts before code.
- **Content line (legal/ethical, ⚖️ Q-009).** Repo holds run-guides + MITRE
  mappings + detections + *pinned references* only. Live payloads/droppers and
  generated victims are NEVER committed — pulled at provision time into gitignored
  work dirs, treated as untrusted, snapshot-bracketed, NAT-never.

### Soft

- **Stdlib-only scorer** (Python), evolving the existing `bluectf` validators.
- **Lab artifacts on `/mnt/data`** (1.7 TB NVMe), never the 244 GB root.
- **Reuse over rebuild:** wrap SecGen, evolve bluectf, adopt Security Onion's
  bundled stack rather than rebuild Elastic by hand.

## Tier

**Tier: large.** Justified, not defaulted: seven domains (virtualization
orchestration, scenario generation, automated threat actors, detection
data-plane, scoring engine, validation/reproducibility, safety/containment),
persisted scored state, automated adversarial actors with single-host blast
radius. Plumbing depth: hash-chained SQLite scoring store (→ Q-005), adapter
registry across many providers, materialized read-model for the scoreboard with
a rebuild path, two physical validation tiers. See ARCHITECTURE for the full
catalog.

## Scope (MVP)

The smallest thing that proves the value prop — **the Vulhub-CVE fast path**:

1. **Contracts first** (versioned): `Scenario`, `VulnManifest`, `OnboardSpec`,
   `DetectionRule`, `attack_event`, `ValidationEvent`, `IsolationReport`, and the
   five scoring event shapes. JSON-Schema fixtures in CI.
2. **Phase Web/Linux** (`lab up web`): Kali-in-container attacker + Vulhub/Docker
   CVE targets + Suricata/auditd signal, provisioned from pinned refs.
3. **One fully-oracled vuln class** (a curated Vulhub CVE) with all three pillars:
   ATTACK (TTP ∈ manifest), DETECT (three-window TP+FP), MITIGATE (re-attack
   blocked AND service healthy).
4. **Event-sourced scorer** over hash-chained SQLite; scoreboard = fold; replay
   self-check passes (F7).
5. **Enforced containment**: `IsolationProvider.verify_contained()` fail-closed
   pre-flight + `lab panic` kill-switch (F6).
6. **`lab validate --e2e web`** green end-to-end; CI tier < 5 min, push-blocking.

Then, **in priority order** (each a follow-up, not MVP):

- Phase 1 Splunk host-lens (optional flag) + Atomic Red Team adapter.
- Phase 3 Security Onion network-lens (primary SIEM) + Fleet enrollment.
- Phase 2 adversary emulation (native runner: DNS/MITM, reverse-shell→C2,
  AiTM-vs-mock-SSO).
- Phase 4 GOAD-full AD forest (→ Q-010, GOAD-full chosen).
- Phase 5 SecGen randomized targets, containerized behind the generator port
  (must-have, NOT critical-path-blocking).

"All phases boot & inter-communicate" is satisfied **sequentially**: each phase
boots green and runs a scripted attack→detect→mitigate loop; cross-phase
log-flow is proven for **one adjacent pair at a time** via `lab validate --pair`.

## Safety & defensible-educational framing

Purple Range is an **authorized self-training** lab for its single owner. Its
defensibility rests on four enforced properties, not on a disclaimer:

1. **Containment is code.** Single host-only plane; NAT-off default; host
   firewall forward-drop; in-code target allowlist; fail-closed pre-flight that
   ABORTS if a route to the internet or a bridged NIC is present; `lab panic`
   kill-switch that cuts forwarding host-side without trusting guests.
2. **The repo is not a weapons cache** (⚖️ Q-009). It holds run-guides, MITRE
   mappings, detection rules, and pinned *references*. Live payloads, droppers,
   and generated victims are pulled ephemerally at provision time into gitignored
   dirs, treated as untrusted, snapshot-bracketed, and NAT-never.
3. **Bounded autonomy** (Q-004). v1 actors run only an allowlisted technique set;
   no autonomous exploit- or egress-selection.
4. **`SAFETY.md`** documents the authorized-self-training scope, the containment
   invariants, the kill-switch, and the defensible-educational framing.

## Open questions

Tracked in [`docs/OPEN-QUESTIONS.md`](OPEN-QUESTIONS.md). Load-bearing for this
PRD: Q-002 (SO unattended install vs one-command), Q-003 (Splunk demotion),
Q-004 (bounded autonomy), Q-005 (SQLite scoring store), Q-006 (benign baseline
source), Q-007 (live-SIEM vs offline-replay grading), Q-008 (small initial N of
oracled vuln classes), Q-009 ⚖️ (content line), Q-010 (GOAD-full, chosen).
Q-001 (disk) is RESOLVED. New questions surfaced during drafting are appended
there (Q-011..Q-013).

## Related

- Brainstorm spine: [`docs/BRAINSTORM.md`](BRAINSTORM.md)
- Architecture: [`docs/ARCHITECTURE.md`](ARCHITECTURE.md)
- Initial ADR: [`docs/ADR/0001-manifest-oracle-event-sourced-scoring.md`](ADR/0001-manifest-oracle-event-sourced-scoring.md)
- Open questions: [`docs/OPEN-QUESTIONS.md`](OPEN-QUESTIONS.md)
- Build plan: `docs/TODO.md` (produced at `/decompose`)
</content>
</invoke>
