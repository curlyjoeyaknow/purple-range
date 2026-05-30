# HANDOFF — 2026-05-30 (post-/checkpoint, phase seam)

> Written by `docs-keeper`. Resume `/deliver` from "Next concrete step" with zero momentum lost.

## Current state in one paragraph

Purple Range is a clean rebuild of the messy `/home/memez/cyber-range` (READ-ONLY reference) into a purple-team CTF/lab platform with 3-pillar scoring (ATTACK → DETECT → MITIGATE). We are mid-`/deliver`: **society-of-minds brainstorm DONE, `/plan` DONE, architecture SIGNED OFF by owner (HARD STOP 3 cleared)**. Just ran `/checkpoint` at a clean phase seam. **No code has been written** — the repo holds spec docs only (2 commits). The next gates are `/forge-agents` (HARD STOP 4) then `/decompose` (HARD STOP 5). Critic returned GO-WITH-FIXES; all 3 fatal findings are CLOSED and confirmed by a 2nd pass.

## Workspace topology (KEEP STRAIGHT — do not cross-contaminate)

- `/home/memez/dev-bootstrap` — the FRAMEWORK + current session CWD. **Do NOT build the product here.**
- `/home/memez/cyber-range` — messy SOURCE. **READ-ONLY**; mine for good parts, never modify.
- `/home/memez/purple-range` — the CLEAN TARGET. **All artifacts/code go here.**
- `/home/memez/phalanx` — UNRELATED crypto project. **Hands off.**
- Lab artifacts live on `/mnt/data` (2TB NVMe, 1.7TB free), **NOT** the 244GB root.

## What I was doing when I stopped

- **Task:** Phase-seam checkpoint after architecture sign-off (HARD STOP 3 cleared).
- **Branch:** `main`
- **Repo:** `/home/memez/purple-range` (2 commits: `64038d9` scaffold+brainstorm; `3e8bfe4` spec). No git remote, no branch protection yet.
- **Worktree:** none.
- **File / line, mid-edit:** none — working tree clean.
- **Last command run:** `/checkpoint`.

## Next concrete step

Continue `/deliver`: run **`/forge-agents`** to generate Purple Range's domain specialists, then STOP at **HARD STOP 4** and present the forged roster to the owner for approve/trim — forge nothing a project this size doesn't need.

After HARD STOP 4 clears: run **`/decompose`** (critical path + real parallelism first, then agent assignment), then STOP at **HARD STOP 5** where `plan-critic` validates the plan, sets the hostile-review gates, and writes `docs/DELIVERY-PLAN.md`. **Build starts only after HARD STOP 5.**

## Locked decisions (do not relitigate)

- Tier: **Large**. Use: **personal / self-training**.
- Scope: **SEQUENTIAL / scenario-scoped** — not all phases hot at once (RAM-sequential is the only real ceiling).
- SecGen path: **Vulhub/Docker CVE targets FIRST**, then SecGen-containerized later (M7, post-MVP).
- Blue pane: **Security Onion / Elastic PRIMARY** (Splunk optional).
- Threat actors: bounded to an **allowlisted technique set v1**.
- **GOAD-full approved** (M6).

## Architecture spine (signed off — see `docs/ARCHITECTURE.md` + `docs/ADR/0001-...`)

- **Manifest-as-oracle** + **event-sourced hash-chained SQLite** scoring (state = fold of append-only events). This spine is what makes randomized targets scorable — preserve it.
- **Ports & adapters at EVERY boundary**, each with a prod adapter + a fake: LabProvider, ScenarioGenerator + VulnManifest, ThreatActor + attack_event ground-truth, Telemetry/OnboardSpec + DetectionRule, Scorer/EventStore, IsolationProvider, Clock, Rng.
- **3-pillar grading:** ATTACK = ttp ∈ manifest; DETECT = three-window TP+FP correlation with **mandatory** per-challenge calibration fixtures `{correct_ref, match_all_ref, match_none_ref}` + `skew_budget`; MITIGATE = re-attack blocked AND `service_probe` healthy with **mandatory** `deny_all_ref` negative fixture.
- **Two-tier validation:** thin push-blocking CI vs local `lab` harness (`--smoke/--e2e/--pair`), ValidationEvent ledger.
- **Host-side continuous egress containment:** `nft inet` PRIMARY + tripwire covering VM + Docker-bridge + IPv6 + DNS; in-guest probe is corroboration-only; tripwire DISARMED during the provisioning NAT-on window and RE-ARMED before first attack step; panic kill-switch; base-snapshot gate. **Containment authority MUST be host-side + continuous — the guest is untrusted.**
- **De-bloat 6.2GB → MBs** via `scripts/fetch-deps.sh` (pinned refs + checksums into gitignored `/mnt/data` vendor/). Pin `box_version` + image `@sha256` + Splunk version + SHA.

## Milestones (`docs/TODO.md`)

- **M0** hygiene / de-bloat / fetch-deps / CI skeleton / `lab` CLI scaffold
- **M1** scoring spine (event store, contracts, scorer ports, fakes) — **MVP backbone**
- **M2** Vulhub web phase e2e (generate → onboard → attack → 3-pillar grade)
- **M3** detection data-plane (Security Onion primary + onboarding + DetectionRule + calibration gate)
- **M4** threat-actor runner (native adapter + ground-truth, allowlist)
- **M5** containment hardening (gates M4)
- **M6** GOAD-AD phase
- **M7** SecGen containerized generator (post-MVP)
- **M8** validation harness tiers

Reserved **ADRs 0002–0006** to be written during `/decompose`.

## Open decisions

See `docs/OPEN-QUESTIONS.md` (Q-001..Q-015). **Non-blocking for M0/M1** — those run no live attacks / SecGen / SIEM.

- **Q-002** SO unattended install — unblock trigger: M3.
- **Q-006** benign baseline source — trigger: M3.
- **Q-007** DETECT live-SIEM coupling — trigger: M3.
- **Q-008** oracle small-N behaviour — trigger: M2.
- **Q-009** ⚖️ content/ethics line — **MUST resolve before M4/M5** (expert/legal checkpoint).
- **Q-011 / Q-012 / Q-013** SecGen + GOAD pins — trigger: M6/M7.
- **Q-014** sole-author calibration fixtures — trigger: M3.
- **Q-015** — see file.
- **Infra:** set up GitHub remote + branch protection + decide team-vs-solo merge mode **BEFORE** opening any EXECUTE-phase PRs.

## Recent learnings (not yet in docs)

The manifest-as-oracle spine is the load-bearing trick that makes randomized targets scorable — guard it through decomposition. The DETECT/MITIGATE pillars are only as honest as their calibration/negative fixtures, so those CI gates (`{correct_ref, match_all_ref, match_none_ref}` + `skew_budget`, and `deny_all_ref`) are load-bearing, not optional — do not let `/decompose` quietly defer them. Containment authority must be host-side and continuous because the guest is untrusted. Disk is no longer a constraint (1.7TB on `/mnt/data`); **RAM-sequential is the only real ceiling** (60GiB total, ~55 usable for guests), which is why scope is sequential/scenario-scoped.

## Risks / red flags

`critic` returned **GO-WITH-FIXES**; **3 fatal findings CLOSED and confirmed by a 2nd pass** (F1 DETECT calibration fixtures, F2 MITIGATE deny-everything fixture, F3 host-side continuous containment). M1–M5 + m1–m5 follow-ups folded into `docs/TODO.md`. See `docs/RED-TEAM.md`. Remaining live risk surface (egress containment, content/ethics line) is gated to M4/M5 and tracked by Q-009; do not start live-attack milestones until those gates are armed and Q-009 is resolved.

## Host facts

Ryzen 9800X3D 8C/16T, 60GiB RAM (~55 usable for guests), bare metal, AMD-V + `/dev/kvm`. VirtualBox 7.1.18 AND libvirt available. Vagrant 2.4.3, Docker 29.5.2, podman 4.9.3, rbenv Ruby 3.2.3, Ubuntu 24.04, kernel 6.17.

## Files modified this session

```
(working tree clean — /checkpoint committed at the seam; 2 commits total on main)
```

## Suggested resume command

```bash
cd /home/memez/purple-range
git checkout main
git log --oneline -2   # expect 3e8bfe4 spec ; 64038d9 scaffold

claude
> read docs/HANDOFF.md and resume /deliver from "Next concrete step":
> run /forge-agents, then HARD STOP 4 (present roster for approve/trim).
```

## Session metadata

- **Ended:** 2026-05-30 (clean phase seam, post-`/checkpoint`)
- **Commits on main:** 2 (`64038d9`..`3e8bfe4`)
- **PRs opened/closed:** none (no remote yet)
- **ADRs added:** ADR-0001 (manifest-oracle + event-sourced scoring); 0002–0006 reserved for `/decompose`
- **`/deliver` position:** brainstorm ✔ · `/plan` ✔ · architecture sign-off (HARD STOP 3) ✔ · **next: `/forge-agents` → HARD STOP 4**
