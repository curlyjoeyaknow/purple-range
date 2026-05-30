# HANDOFF — 2026-05-31 (pre-build seam, execution about to start)

> Written by `docs-keeper`. Resume `/deliver` from "Next concrete step" with zero momentum lost.

## Current state in one paragraph

Purple Range is a clean rebuild of the messy `/home/memez/cyber-range` (READ-ONLY reference) into a purple-team CTF/lab platform with 3-pillar scoring (ATTACK → DETECT → MITIGATE). **The ENTIRE pre-build pipeline is COMPLETE:** society-of-minds ✔, `/plan` + architecture sign-off ✔, `/forge-agents` (3 specialists) ✔ + owner-approved, `/decompose` ✔ (30-task graph + `docs/DELIVERY-PLAN.md`, `plan-critic` validated, 4 clean-room gates designated) ✔ + owner-confirmed. **GitHub infra is DONE:** public repo `github.com/curlyjoeyaknow/purple-range`, `main` branch-protected in **SOLO mode** (0 approvals, linear history, conversation resolution, no force-push, **NO required status checks yet** — add real check names after the CI workflow exists at T-003). Account: `curlyjoeyaknow`. The repo was made **PUBLIC at the owner's explicit choice** (was private; branch protection needs Pro for private repos). **No product code has been written yet** — next action is autonomous EXECUTE-phase build.

## Workspace topology (KEEP STRAIGHT — do not cross-contaminate)

- `/home/memez/dev-bootstrap` — the FRAMEWORK + current session CWD. **Do NOT build the product here.**
- `/home/memez/cyber-range` — messy SOURCE. **READ-ONLY**; mine for good parts, never modify.
- `/home/memez/purple-range` — the CLEAN TARGET. **All artifacts/code go here.**
- `/home/memez/phalanx` — UNRELATED crypto project. **Hands off.**
- Lab artifacts live on `/mnt/data` (2TB NVMe, 1.7TB free), **NOT** the 244GB root.

## What I was doing when I stopped

- **Task:** Pre-build seam — pipeline complete, GitHub infra stood up, refreshing handoff before EXECUTE begins.
- **Branch:** `main` (protected — no further direct pushes).
- **Repo:** `/home/memez/purple-range`, remote `origin` → `https://github.com/curlyjoeyaknow/purple-range.git` (PUBLIC).
- **Worktree:** none.
- **File / line, mid-edit:** none — only `docs/RED-TEAM.md` shows uncommitted local edits at handoff write time.
- **Last actions:** `/forge-agents`, `/decompose`, GitHub publish + branch protection (solo mode).

## Next concrete step

**BEGIN AUTONOMOUS EXECUTION of M0 then M1 on the critical path, BOUND BY `docs/DELIVERY-PLAN.md`.**

Critical path: **T-001 → T-003 → T-101 → T-110 → T-111 → T-201 → T-202 → T-203 (MVP exit).**

M0 first tasks:
- repo hygiene / de-bloat
- `scripts/fetch-deps.sh` — pinned refs + checksums into gitignored `/mnt/data` `vendor/`
- thin **CI skeleton (T-003)**: lint / unit / contracts / syntax / pins / docs / secrets / size-guard — **all stages STUBBED** so streams only fill fixtures
- **lab CLI scaffold (T-004)**: FULL dispatch table incl. stream sub-commands
- `/mnt/data` storage layout

**Per-task loop:** `tester` (failing test) → `implementer`/specialist → `reviewer` → `docs-keeper`.
**Each task** = feature branch → PR → green CI → squash-merge (main is protected; **NO direct pushes**).
After **T-003** lands real CI, **re-run `scripts/setup-branch-protection.sh --solo --checks "<real job names>"`** to require green CI.

## Workflow now (CHANGED — main is protected)

All work on feature branches, PR per task, solo auto-merge on green. **NOTE:** `Bash(gh pr merge:*)` is in the framework's "ask" list, so the FIRST merge in a session may prompt the human — consider moving it to allow in the active settings for full autonomy, or accept the prompt.

## Clean-room gates (from `docs/DELIVERY-PLAN.md`, run via `clean-room-reviewer` in a FRESH subagent)

- **GATE A** @ T-101/110/111 — spine; adversarial; budget 4; **MVP-blocking**.
- **GATE B** @ T-203 — e2e oracle; hard; budget 3; **MVP release**.
- **GATE C** @ T-304 — F1 calibration; hard; budget 2.
- **GATE D** @ T-403 + M5 — containment + F2 safety; adversarial; budget 4 + **human final sign-off**.

**SAFETY EDGE:** fail-closed orchestrator pre-flight refuses any live attack without an `IsolationVerified` event (T-203 gated behind T-502; inherited by T-403, T-602).

## Public-repo content policy (now load-bearing)

Repo holds **run-guides + MITRE mappings + PINNED REFERENCES only** — **NEVER** committed live malware / exploits / payloads (pulled at provision time into gitignored dirs). This is what keeps a public purple-team repo defensible; **enforced at GATE D**. Hold all offensive-content work to it.

## Locked decisions (do not relitigate)

- Tier: **Large**. Use: **personal / self-training**.
- Scope: **SEQUENTIAL / scenario-scoped** — not all phases hot at once (RAM-sequential is the only real ceiling).
- SecGen path: **Vulhub/Docker CVE targets FIRST**, then SecGen-containerized later (M7, post-MVP).
- Blue pane: **Security Onion / Elastic PRIMARY** (Splunk optional).
- Threat actors: bounded to an **allowlisted technique set v1**.
- **GOAD-full approved** (M6).
- **Repo is PUBLIC** (owner's explicit choice); `main` branch-protected in **solo mode**.

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

ADRs 0002–0007 reserved/in-flight per `/decompose` (store ADR renumbered 0005→0007; see ARCHITECTURE.md ADR list).

## Open decisions

**GitHub infra: now DONE** (public repo + solo branch protection up). Remaining (see `docs/OPEN-QUESTIONS.md`):

- **Q-002 / Q-006 / Q-007 / Q-008** — resolve as phases approach (M2/M3 triggers).
- **Q-009** ⚖️ ethics / content line — **MUST resolve before M4/M5** (expert/legal checkpoint).
- **Q-011 / Q-012 / Q-013** — SecGen + GOAD pins — resolve before **M7 / M6**.

## Recent learnings (not yet in docs)

The manifest-as-oracle spine is the load-bearing trick that makes randomized targets scorable — guard it through execution. The DETECT/MITIGATE pillars are only as honest as their calibration/negative fixtures, so those CI gates (`{correct_ref, match_all_ref, match_none_ref}` + `skew_budget`, and `deny_all_ref`) are load-bearing, not optional. Containment authority must be host-side and continuous because the guest is untrusted. Disk is no longer a constraint (1.7TB on `/mnt/data`); **RAM-sequential is the only real ceiling** (60GiB total, ~55 usable for guests). The CI skeleton ships STUBBED first (T-003) so parallel streams only fill fixtures — required status checks get wired into branch protection only after real job names exist.

## Risks / red flags

`critic` returned **GO-WITH-FIXES**; **3 fatal findings CLOSED and confirmed by a 2nd pass** (F1 DETECT calibration fixtures, F2 MITIGATE deny-everything fixture, F3 host-side continuous containment). See `docs/RED-TEAM.md`. Live risk surface (egress containment, content/ethics line) is gated to M4/M5 and tracked by Q-009; the fail-closed orchestrator pre-flight (no live attack without `IsolationVerified`) is the runtime backstop. Do not start live-attack milestones until those gates are armed and Q-009 is resolved. Public-repo content policy (run-guides + mappings + pins only, never live payloads) is enforced at GATE D.

## Host facts

Ryzen 9800X3D 8C/16T, 60GiB RAM (~55 usable for guests), bare metal, AMD-V + `/dev/kvm`. VirtualBox 7.1.18 AND libvirt available. Vagrant 2.4.3, Docker 29.5.2, podman 4.9.3, rbenv Ruby 3.2.3, Ubuntu 24.04, kernel 6.17. `/mnt/data` 2TB NVMe, 1.7TB free.

## Files modified this session

```
Pipeline + infra session (no product code):
  forge: project specialists (detection, adversary-emulation, lab-orchestration)
  plan: /decompose task graph + DELIVERY-PLAN.md, plan-critic gates A–D
  infra: published PUBLIC repo origin → curlyjoeyaknow/purple-range; solo branch protection on main
  docs: this handoff refresh + CHANGELOG entry
Working tree at write time: docs/RED-TEAM.md modified (uncommitted).
```

## Suggested resume command

```bash
cd /home/memez/purple-range
git checkout main
git log --oneline -5   # expect 748139e plan ; 6ed5d10 forge ; 3caf450 checkpoint ; 3e8bfe4 spec ; 64038d9 scaffold

claude
> read docs/HANDOFF.md and docs/DELIVERY-PLAN.md, then BEGIN EXECUTE:
> start M0 critical path at T-001 → T-003. Per-task: tester → implementer → reviewer → docs-keeper.
> Each task = feature branch → PR → green CI → squash-merge (main is protected).
```

## Session metadata

- **Ended:** 2026-05-31 (pre-build seam — pipeline complete, infra up, execution next).
- **Commits on main:** 5 (`64038d9`..`748139e`).
- **Remote:** `origin` → PUBLIC `github.com/curlyjoeyaknow/purple-range`; `main` solo-protected (no required checks yet).
- **PRs opened/closed:** none yet (execution about to start; PR-per-task from here).
- **ADRs:** ADR-0001 landed; 0002–0007 reserved/in-flight (store ADR renumbered 0005→0007).
- **`/deliver` position:** brainstorm ✔ · `/plan` ✔ · arch sign-off ✔ · `/forge-agents` ✔ · `/decompose` ✔ · GitHub infra ✔ · **next: EXECUTE M0→M1 (T-001→T-003→…→T-203).**
