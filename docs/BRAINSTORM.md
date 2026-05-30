# BRAINSTORM — Purple Range (codename "Phalanx cyber-range", restructured)

> Produced by `/society-of-minds`. This is the multi-perspective brainstorm
> that seeds `/plan`. It is a *recommendation*, not a spec.
> Date: 2026-05-30

**One-liner:** A purple-team CTF training platform where each challenge scores
THREE pillars — (1) execute an attack on a target, (2) detect it as blue-team,
(3) mitigate/harden so it's prevented (worth the most points) — run inside a
safe, network-isolated lab using modern attack methods with run-guides.
Personal/self-training use, reproducible from one command, full validated
platform.

> ⚠️ **Charter non-negotiable #9:** this brainstorm output MUST be red-teamed by
> the `critic` against the CHOSEN design during `/plan` — specifically the
> **manifest-drift**, **SecGen build-non-determinism**, **MITIGATE-honesty**,
> and **containment-pre-flight** claims.

## Scale read

**Assessed scale:** large
**Session shape run:** 7 perspectives (one model wearing seven hats — see
Recorded dissent caveat), full 4 rounds, one convergence pass.

Multi-domain platform (virtualization orchestration, vuln generation, automated
threat actors, detection data-plane, scoring engine, validation/reproducibility,
safety/containment), persisted scored state, automated adversarial actors that
choose their own egress, and a single-host resource ceiling — this is large by
surface area and by blast radius.

## The panel

| Perspective | Optimizes for | Suspicious of |
|---|---|---|
| Virtualization / Lab orchestration | Boots green, fits the host, reproducible | All-VMs RAM blowout; per-phase snapshot drift |
| Scenario generator | Scorable randomized targets; reuse SecGen value | Brittle legacy toolchain; manifest drift |
| Automated threat actors | MITRE-tagged ground-truth, replayability | Recording intent not outcome; autonomy → egress |
| Detection data-plane | Single grading store, detection-as-code | Two SIEMs (RAM); Splunk Free alerting ban |
| Scoring engine / CTF contracts | Honest grading, tamper-evidence, replay | Hardcoded answers; honor-system passes |
| Validation / reproducibility / DevEx | One-command rebuild, fast CI | Full-stack-in-CI (no nested virt); repo bloat |
| Safety / containment / ethics | Enforced invariant, fail-closed | Implicit trust; NAT-attached autonomous actor |

## Round 1 — Feasibility

| Perspective | Biggest feasibility risk | Showstopper / Cost / Non-issue |
|---|---|---|
| Virtualization | All phases hot simultaneously is physically impossible on host | Cost — fixed by sequential/scenario-scoped scope |
| Scenario generator | SecGen's Vagrant 2.2.9 pin collides with host 2.4.3 | Cost — containerize the legacy toolchain |
| Threat actors | Ground-truth records intent, not observed outcome → poisons grading | Cost — outcome-probe each step |
| Detection | Splunk Free = 500MB/day + NO scheduled alerting (can't host detection-as-code) | Cost — consolidate on Security Onion/Elastic |
| Scoring | DETECT pillar is **fake today** (hardcoded ref query; learner submits nothing) | Showstopper for the value prop — must rebuild grading |
| Validation | Full-stack-in-CI impossible (no nested virt on runners; OOM; multi-hour flaky) | Cost — split CI tier from local VM harness |
| Safety | Autonomous actor picks its own egress destination + NAT attached → implant escape | Showstopper unless containment is an enforced invariant |

**Verdict:** go-with-conditions

**Conditions:**
1. Accept sequential / scenario-scoped scope. ✅ DONE (locked).
2. Disk RESOLVED (2026-05-30): lab artifacts live on the 1.7 TB `/mnt/data` NVMe; image-cleanup discipline is still good practice but no longer a ceiling. → **Q-001** (resolved)
3. SecGen runs containerized on a pinned legacy toolchain, deferred behind the Vulhub-CVE fast path.
4. Detection grading must be rebuilt (current grading is fake — see Risk #1).
5. Containment enforced as an invariant (fail-closed pre-flight) before any automated attack runs.

### Host profile (probed 2026-05-30)

| Property | Value |
|---|---|
| CPU | AMD Ryzen 7 9800X3D, 8C/16T |
| RAM | 60 GiB (~55 usable for guests) — **the only real ceiling now** |
| Disk (root) | 913 GB volume, 244 GB free (72% used) |
| Disk (lab) | **/mnt/data — 1.9 TB NVMe SSD (TEAM TM8FFD002T, /dev/nvme1n1), LUKS+ext4, 1.7 TB free (4% used)** — fast NVMe, good for VM disk I/O |
| Platform | Bare metal; AMD-V + `/dev/kvm` usable (VirtualBox AND libvirt/KVM available) |
| Installed | VirtualBox 7.1.18, Vagrant 2.4.3, Docker 29.5.2, podman 4.9.3, rbenv Ruby 3.2.3 + Bundler 2.4.20 |
| OS / kernel | Ubuntu 24.04.4, kernel 6.17 |

**Lab-storage decision (2026-05-30):** ALL lab artifacts live on the 1.7 TB
`/mnt/data` NVMe, NOT the 244 GB root volume — VirtualBox default machine
folder, Vagrant boxes dir, SecGen builds, the gitignored `vendor/` deps, and
the box image cache all relocate under `/mnt/data`.

**Implications:** sequential-scoped is mandatory (confirmed); disk is no longer
a ceiling (1.7 TB free on `/mnt/data`) — RAM-sequential is the only real
constraint; GOAD-full (~24–32 GB) reachable solo; SO (16 GB) + GOAD as an
adjacent pair is tight but possible within ~55 GB usable; SecGen's Vagrant
2.2.9 pin conflicts with host 2.4.3 → containerize SecGen's toolchain.

## Round 2 — Ideal architecture (per domain)

> The strongest signal of the brainstorm: four independent panel lenses
> converged on the same spine. See **The unifying architecture** below before
> the per-domain sketches.

### The unifying architecture: MANIFEST-AS-ORACLE

- The **SCENARIO GENERATOR** emits a seedable, VERSIONED `vuln_manifest` per
  run: the vulns present + expected attack TTPs + expected detections +
  expected mitigations. The oracle travels WITH the target — this is what makes
  a RANDOMIZED target scorable.
- **AUTOMATED THREAT ACTORS** emit MITRE-tagged attack ground-truth: which TTP,
  when, against which host, with OBSERVED OUTCOME (success/blocked/partial) —
  not mere intent.
- The **SCORER** grades all three pillars against manifest + ground-truth,
  NEVER hardcoded answers.

### Virtualization / Lab orchestration

Hybrid, scenario-scoped, one-phase-at-a-time, behind a `LabProvider` port. Full
VMs for Security Onion / GOAD / SecGen victims; containers (Docker) for web
targets (DVWA / JuiceShop / WebGoat / Vulhub) + the attacker box
(Kali-in-container). Vagrant+VirtualBox as the first adapter (lowest migration
cost); libvirt/KVM as a deferred second adapter behind the same port; Fake
adapter for tests.

Snapshot per **TARGET VM** (not per-phase, to avoid drift): snapshot
"clean"/"base" after provision & before first attack; restore to re-run an
attack after mitigation (the core training loop).

```
Port (LabProvider):
  bring_up(scenario) -> LabHandle
  tear_down(handle)
  snapshot(handle, name) -> SnapshotRef
  restore(handle, ref)
  status(handle) -> [ComponentStatus]

Scenario{ version:int, id, components:[Component], net:"192.168.56.0/24" }
Component{ name, kind:VM|CONTAINER, image, ram_mb, cpus, ip, promisc:bool }

Events: lab.brought_up | snapshotted | restored | torn_down
        (idempotency_key = scenario.id + attempt)
```

### Scenario generator (vulnerable targets)

WRAP SecGen, don't replace (its ~1000 Puppet vuln modules + ready CTF scenarios
are irreplaceable). Run SecGen inside a PINNED OCI container (Ruby 3.2 + bundle +
imagemagick + Packer + Vagrant 2.2.9 + libvirt) so its legacy toolchain never
collides with host 2.4.3; output is a box image + manifest, not a live host.
Transform SecGen's existing `marker.xml` (flags/hints/CyBOK/msf_module) INTO our
manifest and EXTEND with detect/mitigate oracles (SecGen has none).

FAST PATH first: curated Vulhub/Docker CVE targets — deterministic,
already-CVE-labelled — to author manifests cheaply and prove
scorer+detect+mitigate wiring this week. SecGen randomization is the phase-2
"mystery-box" capability (NOT critical-path-blocking).

```
Port (ScenarioGenerator):
  generate(scenario_spec, seed) -> { victim:VMHandle|container, manifest:VulnManifest }
  Fake returns fixed manifest + stub.

VulnManifest (version:1):
  scenario_id, seed, generated_at
  victim{ ip, hostname, platform, services[] }
  vulns[]{
    id, cve|flaw_class, access(remote|local), planted_value/flag,
    attack{ ttp:[ATT&CK], proof_signal },
    detect{ expected_log_source, expected_signal/sigma_ref },
    mitigate{ control, verify_check },
    secgen_hint, secgen_solution, cybok_ref
  }
  scoring_oracle_ref
```

**CRITICAL:** schema-validate `marker.xml` on ingest; manifest carries
`version`; CI golden-file test on one frozen scenario (guards manifest-drift —
see Risk #5).

### Automated threat actors

Custom scripted playbook RUNNER that orchestrates existing tools (no single
framework adopted wholesale). Adapters:

- **NATIVE** (existing bettercap caplet / reverse shell / docker.sock escape /
  Evilginx-vs-mock-SSO — the bulk).
- **ATOMIC RED TEAM** adapter (Windows/AD atomics on GOAD, ATT&CK-tagged, free).
- **CALDERA** adapter DEFERRED/optional (autonomous AD chains only; heavy C2
  infra).

GROUND-TRUTH records **OBSERVED OUTCOME, not intent** (a flaky attack that
didn't land must not score the learner as "missed a detection"). seed-driven for
replayability. Runner REFUSES targets outside `192.168.56.0/24`.

```
Port (ThreatActor):
  run(playbook_id|chain, target, seed) -> AttackEventLog   # append-only JSONL, one event per TTP step

attack_event{
  schema_version, run_id, seed, playbook_id, step,
  attack_technique(ATT&CK), tactic, target_ip, actor_ip,
  ts_start, ts_end, outcome:success|failed|partial,
  evidence{...}, expected_signal:[...], correlation_id
}
```

For v1 the autonomy ceiling is a **bounded allowlisted technique set** (no
autonomous exploit-selection). → **Q-004**

### Detection data-plane (blue-team telemetry)

Consolidate on **SECURITY ONION 2.4** (bundles Suricata + Zeek + Elastic + Fleet
+ Kibana) as the single pane and grading store. DEMOTE Splunk to optional
(Splunk Free = 500MB/day + NO scheduled alerting → cannot host
detection-as-code; two SIEMs double RAM). Keep Splunk only as an optional
Windows/Sysmon teaching lens behind a flag. → **Q-003**

```
OnboardSpec (version:1):
  every freshly-generated victim enrolls Elastic Agent against SO Fleet
  via a pre-minted enrollment token
  required_streams[ process, network, auth, file ]
  network_visibility span_port
  heartbeat_deadline_s:120
  # NO victim is "ready" until Fleet shows its heartbeat (gate range-up on this).

DetectionRule (version:1){
  id, mitre, store, language(eql|lucene|suricata|spl),
  query, expected_min_hits, max_false_positives, ground_truth_ref
}
# Convert existing prose starter-searches into versioned rule files.
```

**GRADING ORACLE (three-window TP+FP test):** run the LEARNER'S submitted
detection over the attack's `[t_start, t_end]` window from ground-truth → must
return `>= expected_min_hits` (true positive); run the SAME query over a recorded
BENIGN baseline window → must return `<= max_false_positives` (low false
positive); PASS only if both hold. → benign-baseline source is **Q-006**;
live-SIEM-vs-offline-replay coupling is **Q-007**.

### Scoring engine & CTF contracts

EVOLVE `bluectf` (keep the 4 validators http_header / http_contains /
splunk_search→elastic_search / cmd as adapters behind a port; keep ranks,
blue-vs-red split, CLI ergonomics, stdlib-only). REPLACE
`~/.bluectf-progress.json` with an APPEND-ONLY, HASH-CHAINED event log (SQLite via
stdlib `sqlite3` at this tier — concurrent threat-actor writers + replay
queries). State = fold over events. Net add ~250–350 LOC, still stdlib.
SQLite-vs-JSONL at this tier is **Q-005** (deviates from charter's small-tier
JSONL default).

```
Event shapes (versioned):
  scenario_generated{ ..., seed, manifest_ref }
  attack_executed{ ..., actor:auto|learner, ttp, target, outcome, correlation_id }
  submission{ ..., pillar:attack|detect|mitigate, evidence }
  verification_result{ ..., oracle:manifest|ground_truth|reattack, passed:bool, matched_ttp }
  score_awarded{ ..., pillar, points, verification_ref }

Invariants:
  - score_awarded only emittable with a referenced PASSING verification_result
  - idempotency_key = (scenario_id, challenge_id, pillar)
  - prev_hash per row (tamper-evidence)
```

**3-pillar scoring vs a randomized target:**

| Pillar | Pass condition |
|---|---|
| ATTACK | learner's TTP ∈ `manifest.expected_ttps` OR matches an auto `attack_event` |
| DETECT | learner's detection fires on real ground-truth within window AND not on benign control (temporal + TTP correlation — generalizes `payload-sweep.py` into the scoring primitive) |
| MITIGATE | re-run attack → `outcome:"blocked"` AND a positive `service_probe` still healthy (defeats the "deny-everything" cheat) |

Honor-system "done" kept ONLY for un-automatable evidence, scored in a separate
**UNVERIFIED bucket** that does not count toward rank.

### Validation / reproducibility / DevEx (split physically into two tiers)

**CI TIER** (cloud, zero VMs, target <5 min, push-blocking):

| Stage | Tooling |
|---|---|
| lint | shellcheck / ansible-lint / yamllint / ruff |
| unit | pytest on scorer + event-log fold + contract loaders |
| contracts | JSON-Schema validate every event/manifest/scenario fixture; assert `version` field present |
| syntax | `vagrant validate`, `ansible-playbook --syntax-check`, `docker compose config -q`, `packer validate` |
| pins | regex gate: fail on floating `:latest` / unpinned `box_version` / bare `git clone` without pinned ref |
| docs | `mkdocs build --strict` + link-check |
| secrets | gitleaks |
| size-guard | fail if any tracked blob >5 MB or repo >~50 MB |

Matrix axis: python:3.12 only.

**LOCAL VALIDATION HARNESS** (on host, real VMs) — a `lab` CLI (thin over
Makefile/justfile) with three depths:

- `lab validate --smoke <phase>` — boot → service health → down.
- `lab validate --e2e <phase>` — boot → scripted attack → assert detection fires
  → apply mitigation → re-attack → assert blocked → teardown.
- `lab validate --pair <a> <b>` — boot two ADJACENT phases → assert inter-phase
  log flow → the ONLY place "phases inter-communicate" is proven, within RAM
  ceiling.

Each step emits a versioned `ValidationEvent{ version, run_id, phase, check,
status, evidence_ref, ts }` to append-only `validation-events.jsonl`; report =
fold. VM control behind `LabProvider` port (Fake adapter makes harness logic
itself CI-testable).

**ENTRYPOINT:** `lab up|down|reset|validate|status <phase>` + Makefile
`make validate-all` (sequential per-phase e2e + adjacent-pair checks →
green/red matrix).

**PINNING + DE-BLOAT (6.2 GB → <50 MB tracked):** pin every `box_version`,
Docker image by `@sha256` digest, Splunk/SUF version + verified SHA256; remove
the 3 vendored clones (SecGen 4.8 GB / hacktricks 930 MB / PayloadsAllTheThings
38 MB) from the working tree → `scripts/fetch-deps.sh` clones each at a PINNED
ref/commit into a gitignored `vendor/` with checksum verification (prefer
fetch-script over submodules for the 4.8 GB SecGen); purge committed venv
(cyber-range had `handbook/.venv` committed); CI size-guard prevents regression.

### Safety / containment / ethics (enforced invariant, not a doc)

> REQUIRED because automated actors pick their own egress destination.

**Containment invariants:**
1. **default-deny egress** — NAT detached by default after provisioning;
   internet is a temporary, explicit, logged provision/update state.
2. **single network plane** — only `192.168.56.0/24` host-only, never bridged;
   host nftables/ufw drops `vboxnet→eth0/wlan` forwarding as a second layer.
3. **target allowlist enforced IN CODE** — actors reject any target outside the
   CIDR.

```
Port (IsolationProvider):
  verify_contained() -> IsolationReport{
    version, nat_detached, bridged_present, route_to_internet,
    host_fw_egress_blocked, target_cidr, checked_at
  }
  # Prod adapter shells VBoxManage NIC check + in-VM probe:
  #   curl https://1.1.1.1 MUST fail; ping 192.168.56.x MUST succeed.
  # Fake returns canned report.
```

**FAIL-CLOSED pre-flight:** lab provider runs `verify_contained()` BEFORE any
attack/threat-actor step; if `route_to_internet` or `bridged_present` → ABORT.
Emit `IsolationVerified` / `IsolationFailed` events every time.

**Kill-switch `phalanx panic`:** pause all actor/victim VMs + host nft flush of
the vboxnet-forward chain (sub-second, host-side, doesn't trust guests). Safety
net: mandatory base snapshot per VM before first attack; no attack permitted
against a VM lacking a base snapshot (assert in pre-flight).

**Content handling (the weapons-cache line):** repo holds run-guides + MITRE
mappings + pinned REFERENCES to offensive content, NEVER committed live
malware/droppers/generated victims; pull at provision time from pinned commits
into gitignored work dirs; treat generated SecGen victims as untrusted,
snapshot-bracketed, NAT-never. One-page `SAFETY.md` (authorized-self-training
scope, containment invariants, kill-switch, defensible educational framing).
Secrets hygiene: a single LAB-ONLY gitignored `lab-credentials` namespace +
gitleaks pre-commit gate. → content line confirmation is **Q-009** ⚖️.

## Round 3 — Red-team (perspectives attacking each other's proposals)

| Risk raised | Against | Severity | Candidate mitigation |
|---|---|---|---|
| 🔴 DETECT grading is FAKE — `splunk_search` runs a hardcoded reference query; learner never submits a detection | Scoring (current bluectf) | Critical | Rebuild as three-window TP+FP oracle; learner submits, we run it |
| 🔴 MITIGATE "deny-everything" cheat — breaking the service makes re-attack "fail" → false pass | Scoring (mitigate pillar) | Critical | Two-sided assertion: attack blocked AND positive `service_probe` healthy |
| 🔴 SecGen build NON-DETERMINISM — fixed seed still reaches apt/Packer/forge; same seed can yield a non-booting box months later | Scenario generator | High | Containerized pinned toolchain + frozen/cached base box + offline apt mirror snapshot; Vulhub-CVE fast path deterministic by construction |
| 🔴 Threat-actor GROUND-TRUTH drift — recording intent not observed outcome poisons grading | Threat actors | High | Outcome-probe each step; partial/failed excluded from "missed detection" penalties |
| 🟠 Manifest drift — SecGen module change → marker.xml shape change → parser silently mis-maps → wrong oracle | Scenario generator / scorer | High | Schema-validate on ingest; versioned manifest; CI golden-file test |
| 🔴 Containment failure with autonomous actor + NAT attached → implant egress to internet/LAN | Safety / threat actors | Critical | Fail-closed pre-flight + NAT-off-default + host firewall forward-drop |
| 🟠 Single-host RAM ceiling — OOM if phases co-resident (disk RESOLVED 2026-05-30: 1.7 TB free on `/mnt/data` NVMe; was 244 GB on root) | Virtualization | Med (was High) | Sequential scope; adjacent-pair only; lab artifacts on `/mnt/data`; image-cleanup now good-practice not blocker |
| 🟠 SO `so-setup` is interactive → fights one-command reproducibility | Validation / detection | Medium | SO unattended/airgap install path + pinned ISO; pre-mint Fleet tokens (→ **Q-002**) |

## Round 4 — Cost/benefit of competing approaches

| Domain | Approach | Verdict | Why |
|---|---|---|---|
| Orchestration | Hybrid VMs+containers behind a port | **recommended** | Beats all-VirtualBox (RAM) and full-libvirt-now (rewrite delay); sequential gives cleaner per-technique training signal |
| Orchestration | All-VirtualBox / full-libvirt-now | rejected | RAM blowout / rewrite delay |
| Generator | Wrap-SecGen + Vulhub fast-path | **recommended** | Scored challenges this week, randomization later, one new abstraction |
| Generator | Fix-as-is-uncontained / full-replace | rejected | Toolchain collision / weeks rebuilding + still need the manifest |
| Threat actors | Native runner + Atomic adapter | **recommended** | Beats Caldera-wholesale (C2 infra to babysit, non-deterministic autonomy) and Atomic-only (no MITM/escape coverage) |
| Detection | Security-Onion / Elastic single-pane | **recommended** | Beats Splunk-centric (Free-tier alerting ban + 500MB cap) and Elastic-DIY (rebuilds what SO ships); frees ~8 GB RAM |
| Scoring | Evolve-bluectf over SQLite event log | **recommended** | Beats rebuild (throws away good validators/ranks) and per-challenge hardcoded verify (worthless after first SecGen reroll) |
| Validation | Thin-CI + local-harness | **recommended** | Beats full-stack-in-CI (no nested virt on runners; OOM; multi-hour flaky jobs) |

## Recommended architecture sketch

**Tier:** large (justified above — not defaulted: 7 domains, persisted scored
state, automated adversarial actors, single-host blast radius).

Minimum patterns confirmed present even at the smallest scale:

- [x] **Append-only event logging** — attack `AttackEventLog` JSONL,
      `validation-events.jsonl`, and the scoring event log (SQLite, hash-chained
      — tier-justified, see **Q-005**).
- [x] **Ports & adapters** at each domain boundary — `LabProvider`,
      `ScenarioGenerator`, `ThreatActor`, `IsolationProvider`, plus the scorer's
      validator port — each with a Fake adapter.
- [x] **Versioned contracts** — `version` field on `Scenario`, `VulnManifest`,
      `OnboardSpec`, `DetectionRule`, `attack_event`, `ValidationEvent`,
      `IsolationReport`, and every scoring event shape.

**Above-minimum complexity, with its scale pressure:**

- *Hash-chained SQLite scoring store* (vs one JSONL) — concurrent threat-actor
  writers + replay queries + tamper-evidence at large tier. → **Q-005**.
- *Two physical validation tiers* (CI vs local VM harness) — no nested virt on
  cloud runners; real e2e needs the host.
- *Containerized legacy SecGen toolchain* — host Vagrant 2.4.3 vs SecGen's
  2.2.9 pin is irreconcilable in-process.
- *IsolationProvider + fail-closed pre-flight + kill-switch* — automated actors
  choose their own egress; containment must be enforced code, not prose.

### Locked decisions (owner-confirmed at convergence)

- **TIER:** Large. **AUDIENCE:** personal/self-training (reliable on owner's
  host > publish polish; keep reproducibility, skip contribution scaffolding).
- **WORKSPACE:** fresh clean repo `/home/memez/purple-range`
  (framework-scaffolded). Mine good parts from `/home/memez/cyber-range`
  (read-only — DO NOT touch).
- **SCOPE SHAPE (load-bearing):** "all phases boot & inter-communicate" is
  REDEFINED as sequential, scenario-scoped — each phase boots green & runs a
  scripted attack→detect→mitigate; cross-phase log-flow is proven for ONE
  adjacent pair at a time. NOT all phases hot simultaneously (physically
  impossible on the host).
- **SECGEN PATH:** Vulhub/Docker CVE targets FIRST (deterministic,
  CVE-labelled) to prove the scorer+manifest contracts; SecGen random-VM
  generation layered AFTER, containerized, behind the generator port. SecGen is
  a must-have but NOT critical-path-blocking.
- **DEFAULTS owner did not veto:** Splunk demoted to OPTIONAL (Security
  Onion/Elastic is the primary blue-team pane); automated threat actors bounded
  to an ALLOWLISTED technique set for v1 (no autonomous exploit-selection).

## Top risks + mitigations (ranked)

1. 🔴 **DETECT grading is fake today** (hardcoded ref query; learner submits
   nothing) → rebuild as three-window TP+FP oracle; learner submits the
   detection, we run it.
2. 🔴 **MITIGATE "deny-everything" cheat** → two-sided assertion (attack blocked
   AND positive `service_probe` healthy).
3. 🔴 **SecGen build non-determinism** → containerized pinned toolchain +
   frozen/cached base box + offline apt mirror snapshot; Vulhub-CVE fast path is
   deterministic by construction.
4. 🔴 **Threat-actor ground-truth drift** (intent vs observed outcome) →
   outcome-probe each step; partial/failed excluded from "missed detection"
   penalties.
5. 🟠 **Manifest drift** (SecGen marker.xml shape change → silent mis-map) →
   schema-validate on ingest; versioned manifest; CI golden-file test.
6. 🔴 **Containment failure** (autonomous actor + NAT attached → implant egress)
   → fail-closed pre-flight + NAT-off-default + host firewall forward-drop.
7. 🟠 **Single-host RAM ceiling** (OOM if phases co-resident) → sequential
   scope; adjacent-pair only. **Disk RESOLVED (2026-05-30):** 1.7 TB free on
   the `/mnt/data` NVMe (lab artifacts relocated there); RAM-sequential is now
   the only real ceiling; image-cleanup remains good practice, not a blocker.
8. 🟠 **SO `so-setup` interactive** fights one-command reproducibility → SO
   unattended/airgap install path + pinned ISO; pre-mint Fleet tokens
   (→ **Q-002**).

## Recorded dissent

> **Caveat:** this was one model wearing seven hats, NOT independent experts.
> High-stakes items below are routed to OPEN-QUESTIONS for a human.

- **Scoring lens** recommends **SQLite over JSONL** for the scoring event store
  at large tier (concurrent auto-actor writers + replay) — deviates from the
  charter's "one JSONL file" small-tier default. Needs confirm. → **Q-005**.
- **Generator lens:** do we actually need VM-level randomization (SecGen), or is
  a config/CVE-randomized CONTAINER ("different every run") enough for
  detect/mitigate scoring? Owner chose Vulhub-first / SecGen-later, which keeps
  both alive; revisit whether SecGen earns its brittleness after the fast path
  proves out.
- **Detection lens:** DETECT correlation couples the scorer to a LIVE SIEM at
  verify time vs an offline-replayable log bundle (more honest/portable but more
  build). Undecided. → **Q-007**.
- **Threat-actor lens:** ground-truth source — self-probe-with-outcome (couples
  less) vs trusted third-observer tcpdump/auditd tap (more honest, couples actor
  to detection plane). Lean self-probe for v1, third-observer as v2 hardening.
- **Safety lens:** threat-actor autonomy ceiling — bounded allowlisted technique
  set (v1, chosen) vs autonomous exploit-selection (raises containment + ethics
  stakes). → **Q-004**.

## Open questions → OPEN-QUESTIONS.md

- Q-001 [owner] Disk budget + image-cleanup policy (244 GB free vs 100–200 GB).
- Q-002 [owner] Security Onion interactive installer vs one-command reproducibility.
- Q-003 [owner] Splunk demotion to optional Windows/Sysmon lens.
- Q-004 [owner] Threat-actor autonomy — bounded allowlisted set vs autonomous selection.
- Q-005 [owner] Scoring store SQLite vs JSONL at large tier.
- Q-006 [owner/expert] Benign baseline source for the false-positive gate.
- Q-007 [owner] DETECT grading coupling — live-SIEM-at-verify vs offline-replay.
- Q-008 [owner] Who authors the detect/mitigate oracle per vuln class; start with small N?
- Q-009 [owner/legal-ethics ⚖️] Content line — guides+MITRE+detections in repo, live payloads ephemeral only.
- Q-010 [owner] GOAD-full (~24–32 GB) vs GOAD-Light (3 VMs). **GOAD-full now UNBLOCKED (2026-05-30):** disk cleared by `/mnt/data`; ~24–32 GB RAM fits the 60 GB host solo; the GOAD + Security Onion adjacent pair ≈48 GB is tight but within ~55 GB usable. Recommend GOAD-full.

## Hand-off

Next: `/plan` — the architect turns this recommendation into PRD +
ARCHITECTURE + ADR-0001, and `critic` red-teams the *chosen* design. Per charter
non-negotiable #9, the critic must specifically attack the **manifest-drift**,
**SecGen build-non-determinism**, **MITIGATE-honesty**, and
**containment-pre-flight** claims.
