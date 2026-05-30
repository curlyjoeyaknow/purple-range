# HANDOFF — 2026-05-31 (M0 in progress — 2 of 5 blockers merged)

> Written by `docs-keeper`. Resume `/deliver` from "Next concrete step" with zero momentum lost.

## Current state in one paragraph

Purple Range is a clean rebuild of the messy `/home/memez/cyber-range` (READ-ONLY reference) into a purple-team CTF/lab platform with 3-pillar scoring (ATTACK → DETECT → MITIGATE). Pre-build pipeline COMPLETE (brainstorm/plan/arch-signoff/forge/decompose). **EXECUTE phase is UNDERWAY — M0 is 2 of 5 blockers done and MERGED to `main`:** **T-001** (PR #2, `b072ad6`) — `scripts/size_guard.py` + bloat-prevention `.gitignore`; **T-003** (PR #3, `1da6a06`) — thin push-blocking CI skeleton (`.github/workflows/ci.yml`, 10 stages) + `scripts/pins_gate.py`. **CI is now REAL and self-green** (all 10 stages passed on PR #3's own run), and `main` branch protection has been **re-wired to REQUIRE all 10 checks** (solo mode, 0 approvals). Account `curlyjoeyaknow`; repo PUBLIC. Test suite: 56 tests (17 size-guard + 20 pins + 19 CI-structure), all green; run via a throwaway venv (`python3 -m venv /tmp/x && /tmp/x/bin/pip install pytest ruff`) — pytest/ruff are NOT yet installed on the host (pinned in CI; host dep manifest is T-103).

## Workspace topology (KEEP STRAIGHT — do not cross-contaminate)

- `/home/memez/dev-bootstrap` — the FRAMEWORK + current session CWD. **Do NOT build the product here.**
- `/home/memez/cyber-range` — messy SOURCE. **READ-ONLY**; mine for good parts, never modify.
- `/home/memez/purple-range` — the CLEAN TARGET. **All artifacts/code go here.**
- `/home/memez/phalanx` — UNRELATED crypto project. **Hands off.**
- Lab artifacts live on `/mnt/data` (2TB NVMe, 1.7TB free), **NOT** the 244GB root.

## What I was doing when I stopped

- **Task:** Completed T-001 + T-003 (both merged), wired branch protection to require the 10 CI checks, refreshed this handoff at the M0 mid-phase seam.
- **Branch:** `main` (protected — PR-per-task, NO direct pushes; even admin is blocked, `enforce_admins: true`).
- **Repo:** `/home/memez/purple-range`, remote `origin` → `https://github.com/curlyjoeyaknow/purple-range.git` (PUBLIC). Working tree CLEAN, `main` synced.
- **Worktree:** none.
- **In flight:** nothing — no uncommitted product code, no running subagents.
- **Note:** this SESSION runs from `/home/memez/dev-bootstrap`, so the Task tool only resolves the GENERIC agent roster — the forged specialists in `purple-range/.claude/agents/` (lab-orchestration-engineer, detection-engineer, adversary-emulation-engineer) are NOT available as `subagent_type` here. T-001/T-003 were repo/CI tooling with no domain depth, so generic `implementer` was correct. Before a task that needs real specialist depth (e.g. M2 T-201 LabProvider Vagrant/VBox, M3 detection, M4 threat-actor), either run the session from inside `purple-range` or pass the forged agent's `.md` as context to a generic agent.

## Next concrete step

**CONTINUE M0, then M1a (GATE A), BOUND BY `docs/DELIVERY-PLAN.md`.** Critical path: ~~T-001~~ → ~~T-003~~ → **T-101** → T-110 → T-111 → T-201 → T-202 → T-203 (MVP exit).

Remaining M0 blockers (all now unblocked by T-001/T-003; file-disjoint, worktree-safe with each other):
- **T-002** `scripts/fetch-deps.sh` — clone each dep at its PINNED ref + verify SHA256 into gitignored `/mnt/data/.../vendor/`; idempotent. Tester writes `test_fetch_deps_rejects_checksum_mismatch` + `test_fetch_deps_idempotent` vs a fake fetch target first. Pins live in ARCHITECTURE.md "Pinned versions" (Vulhub `d277a86…`, ART `daee1d5…`, GOAD `v3.0.0` commit-pin, SecGen TBD Q-011).
- **T-004** `lab` CLI scaffold — FULL argparse dispatch table locked up front (6 top-level: `up|down|reset|validate|status|panic` + stream sub-verbs `detection onboard`, `threat-actor run`, `isolation arm|disarm`) so S1/S2/S3 only fill bodies later; `ValidationEvent(version:1)` skeleton + JSONL ledger writer. Sits over `LabProvider` (no vendor import). Tester: `test_lab_cli_parses_all_commands` + `test_validation_ledger_appends`.
- **T-005** `/mnt/data` storage layout + config — idempotent bootstrap creating `vendor/ boxes/ vbox/ secgen-builds/ box-cache/ work/ state/`; relocate `VAGRANT_HOME` + VBox machine folder; root stays < 50 MB. Tester: `test_storage_layout_idempotent` + `test_no_artifact_path_under_root`.
- **T-006 / T-007** ADR-0002 (hypervisor behind LabProvider) + ADR-0005 (sequential-scope) — docs-only, PARALLEL, worktree-safe with everything.

Then **T-101 = M1a CONTRACT LOCK (the big blocker that unblocks all fan-out) = GATE A** (adversarial clean-room, budget 4, MVP-blocking): the versioned contracts (VulnManifest, attack_event, DetectionRule v2, challenge_spec, event shapes incl. `scenario_aborted`) + ADR-0007 store, all ports + their FAKES. Generic implementer/tester own this.

**Per-task loop:** `tester` (failing test) → implementer (generic, or forged specialist when domain depth is needed) → `reviewer` → (`external-reviewer` if non-trivial) → docs note. **Each task** = feature branch → PR → green CI → squash-merge. **DONE:** branch protection already requires the 10 checks (`lint/unit/contracts/f1-calibration/f2-mitigate/syntax/pins/docs/secrets/size-guard`), so every future PR must be green.

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

## Open followups (logged in TODO.md "Followups")

- **F-002** 🟠 — duplicate `env:` key in `.github/workflows/external-review.yml` (pre-existing framework scaffold; invalid YAML; lint stage path-ignores it for now). Fix: merge the two `env:` blocks.
- **F-003** 🟡 — pins-gate `unpinned-box-version` is file- not block-granular (any bare `version` token disarms it in-file); harden before M2 lands real Vagrantfiles.
- **F-004** 🟡 — pins-gate has no rule for unpinned Actions `uses:` refs; `ci.yml` floats `@v4/@v5/@v2`. Add `unpinned-action-ref` + SHA-pin in a reproducibility hardening pass.
- **F-005** 🟢 — `PYTHON_VERSION` env declared-but-unused in ci.yml (structure test asserts literal `3.12`).

## Files modified this session (EXECUTE — M0 T-001 + T-003)

```
T-001 (PR #2, b072ad6): scripts/size_guard.py, tests/test_size_guard.py, .gitignore (+ CHANGELOG/TODO)
T-003 (PR #3, 1da6a06): scripts/pins_gate.py, ruff.toml, .github/workflows/ci.yml,
        tests/test_pins_gate.py, tests/test_ci_workflow_structure.py, tests/fixtures/pins/* (+ CHANGELOG/TODO)
infra: branch protection re-wired to require the 10 CI checks (solo mode)
docs: this handoff refresh
Working tree: CLEAN (this handoff lands via its own docs PR).
```

## Suggested resume command

```bash
cd /home/memez/purple-range
git checkout main && git pull
git log --oneline -4   # expect 1da6a06 T-003 (#3) ; b072ad6 T-001 (#2) ; 168482a chore (#1) ; 748139e plan

claude
> read docs/HANDOFF.md and docs/DELIVERY-PLAN.md, then CONTINUE M0:
> next tasks T-002 (fetch-deps) / T-004 (lab CLI) / T-005 (/mnt/data) — file-disjoint, then T-101 = GATE A.
> Per-task: tester → implementer → reviewer → docs note. Each task = branch → PR → GREEN CI (now required) → squash-merge.
```

## Session metadata

- **Updated:** 2026-05-31 (M0 mid-phase seam — T-001 + T-003 merged, CI live, protection requires 10 checks).
- **Commits on main:** 7 (`64038d9`..`1da6a06`).
- **Remote:** `origin` → PUBLIC `github.com/curlyjoeyaknow/purple-range`; `main` solo-protected, **10 required status checks now enforced**.
- **PRs:** #1 (handoff), #2 (T-001), #3 (T-003) merged; handoff-refresh PR pending.
- **ADRs:** ADR-0001 landed; 0002–0007 reserved/in-flight (store ADR renumbered 0005→0007); T-006/T-007 write 0002/0005 in M0.
- **`/deliver` position:** pipeline ✔ · EXECUTE underway — **M0 2/5 blockers merged; next T-002/T-004/T-005 → T-101 (GATE A) → M1b → M2 (MVP exit T-203).**
