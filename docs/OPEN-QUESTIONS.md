# OPEN-QUESTIONS

Unresolved decisions that block, slow, or shape the work. Maintained by the
`docs-keeper` agent. A question only leaves this file in two ways:

- **Resolved**: becomes an ADR (link both ways).
- **Withdrawn**: moot due to a change elsewhere — note the reason.

> Seeded 2026-05-30 from `docs/BRAINSTORM.md` (society-of-minds brainstorm for
> Purple Range). All `[owner]` defaults below are "confirmed-by-default unless
> vetoed" — they reflect locked-or-leaning decisions from convergence.

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
- **What we know:**
  - Large tier has concurrent threat-actor writers + replay queries +
    tamper-evidence needs.
  - SQLite is stdlib (`sqlite3`); net add ~250–350 LOC, still stdlib-only.
  - State remains a fold over append-only, hash-chained events either way.
- **What we don't:** whether the owner prefers to hold the JSONL default and
  serialize writers instead.
- **Options on the table:**
  - A. SQLite append-only + hash-chained — handles concurrency + replay well;
    deviates from default.
  - B. One JSONL file — matches the charter default; needs write serialization
    for concurrent actors.
- **Who needs to weigh in:** owner
- **Decision deadline:** before the scoring-engine phase is decomposed
- **Default if no decision by deadline:** Option A — SQLite append-only +
  hash-chained, recorded as an ADR justifying the tier deviation.

### Q-006 — What is the benign baseline source for the false-positive gate?

- **Raised:** 2026-05-30 in BRAINSTORM.md (Detection grading oracle)
- **Type:** technical
- **Blocks:** the three-window TP+FP grading oracle (the FP half)
- **What we know:**
  - The oracle runs the learner's detection over a recorded BENIGN baseline
    window and requires `<= max_false_positives`.
- **What we don't:** whether the baseline is canned/shipped or captured live.
- **Options on the table:**
  - A. Ship a canned baseline log/PCAP bundle — deterministic, portable; may not
    match a given victim's noise profile.
  - B. Capture a live idle window at range-up — matches the actual environment;
    adds a capture step and non-determinism.
- **Who needs to weigh in:** owner, with expert (detection-engineering) input
- **Decision deadline:** before the detection grading oracle is implemented
- **Default if no decision by deadline:** Option A — ship a canned baseline
  bundle for determinism; revisit live capture as a v2 hardening.

### Q-007 — DETECT grading: couple to a live SIEM at verify time, or to an offline-replayable log bundle?

- **Raised:** 2026-05-30 in BRAINSTORM.md (Detection grading oracle; Recorded dissent)
- **Type:** technical
- **Blocks:** the verify-time architecture of the DETECT pillar
- **What we know:**
  - Live-SIEM-at-verify is simpler to build but couples the scorer to a running
    Security Onion at grade time.
  - Offline-replayable log bundle is more honest/portable but more build.
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
    (detect + mitigate) oracles are MANUAL to author per vuln class.
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
