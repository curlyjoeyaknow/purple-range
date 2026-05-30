# HANDOFF — 2026-05-31 (M0 COMPLETE — M1a / GATE A next)

> Written by `docs-keeper`. Resume `/deliver` from "Next concrete step" with zero momentum lost.

## Current state in one paragraph

Purple Range is a clean rebuild of the messy `/home/memez/cyber-range` (READ-ONLY reference) into a purple-team CTF/lab platform with 3-pillar scoring (ATTACK → DETECT → MITIGATE). Pre-build pipeline COMPLETE (brainstorm/plan/arch-signoff/forge/decompose). **M0 IS COMPLETE — all 7 M0 tasks merged to `main`:** the **5 code blockers** — **T-001** (PR #2, `b072ad6`) size-guard + bloat-prevention `.gitignore`; **T-003** (PR #3, `1da6a06`) 10-stage push-blocking CI + `scripts/pins_gate.py`; **T-004** (PR #5, `e992c2d`) `lab/` package (CLI dispatch table + ValidationEvent(v1) ledger + `__main__`); **T-005** (PR #6, `a88e8bd`) `lab/storage.py` `/mnt/data` storage layout + relocation; **T-002** (PR #7, `38cebb8`) `lab/fetch_deps.py` (Fetcher port + GitFetcher + tree_sha256 + fetch_all + load_manifest + injectable list/fetch main) + `scripts/fetch-deps.sh` + repo-root `conftest.py` — plus the **2 ADRs** **T-006/T-007** (PR #8, THIS branch) ADR-0002 (hypervisor behind `LabProvider`) + ADR-0005 (sequential / scenario-scoped scope), both status accepted (2026-05-31). **133 tests green on `main`, all CI stages green, every PR squash-merged.** CI is live and `main` branch protection REQUIRES all 10 stage checks (solo mode, 0 approvals). Account `curlyjoeyaknow`; repo PUBLIC. Working tree CLEAN, `main` synced (this handoff lands on PR #8). Run tests via a throwaway venv (`python3 -m venv /tmp/x && /tmp/x/bin/pip install pytest ruff`) — pytest/ruff are still NOT installed on the host (pinned in CI; host dep manifest is T-103). NOTE: the new repo-root `conftest.py` (T-002) makes `import lab` robust under bare `pytest` (fixes a sys.path CI gap).

## Workspace topology (KEEP STRAIGHT — do not cross-contaminate)

- `/home/memez/dev-bootstrap` — the FRAMEWORK + current session CWD. **Do NOT build the product here.**
- `/home/memez/cyber-range` — messy SOURCE. **READ-ONLY**; mine for good parts, never modify.
- `/home/memez/purple-range` — the CLEAN TARGET. **All artifacts/code go here.**
- `/home/memez/phalanx` — UNRELATED crypto project. **Hands off.**
- Lab artifacts live on `/mnt/data` (2TB NVMe, 1.7TB free), **NOT** the 244GB root.

### Session-CWD caveat (load-bearing for M2+)

This SESSION runs from `/home/memez/dev-bootstrap`, so the Task tool only resolves the GENERIC agent roster — the forged specialists in `purple-range/.claude/agents/` (lab-orchestration-engineer, detection-engineer, adversary-emulation-engineer) do NOT resolve as `subagent_type` from the framework dir. M0 was repo/CI tooling + ADRs with no domain depth, so generic `implementer`/`tester`/`architect` were correct. Before a task that needs real specialist depth — **M2 T-201 LabProvider (Vagrant/VBox), M3 detection, M4 threat-actor** — either run the session from inside `purple-range` OR pass the forged agent's `.md` as context to a generic agent.

## What I was doing when I stopped

- **Task:** Closed out M0 — wrote ADR-0002 + ADR-0005 (architect), then reconciled `docs/TODO.md` / `docs/CHANGELOG.md` / `docs/HANDOFF.md` to the M0-COMPLETE seam (this docs PR #8). No code/tests touched.
- **Branch:** `chore/m0-closeout-adrs` (the M0-closeout/ADR docs PR #8, about to merge to `main`).
- **Repo:** `/home/memez/purple-range`, remote `origin` → `https://github.com/curlyjoeyaknow/purple-range.git` (PUBLIC). `main` is protected — PR-per-task, NO direct pushes (`enforce_admins: true`).
- **Worktree:** none.
- **In flight:** PR #8 (ADRs + doc reconciliation) pending merge; no uncommitted product code, no running subagents.

## Next concrete step

**T-101 = M1a CONTRACT LOCK = GATE A** (adversarial clean-room review, budget 4, **MVP-blocking**) — the big blocker that unblocks ALL fan-out. It locks, in one sequenced surface:

- The **versioned contracts**: `Scenario(v1)`, `VulnManifest(v2)` (incl. F1 `detect.calibration{correct_ref, match_all_ref, match_none_ref}` + F2 `mitigate{service_probe, deny_all_ref}` + `skew_budget_s`/`clock_offset_s`/`manifest_hash`), `OnboardSpec(v1)`, `DetectionRule(v2)` (calibration block + opaque `query` + `language`), `AttackEvent(v1)`, `IsolationReport(v2)`, `ValidationEvent(v1)`, the `challenge_spec`, and the **6 event shapes**: `scenario_generated(v2)`, `attack_executed(v1)`, `scenario_aborted(v1)`, `submission(v1)`, `verification_result(v2)`, `score_awarded(v2)`.
- **ALL 8 ports + their FAKES**: LabProvider/InMemoryLab, ScenarioGenerator/FixedManifestGen, ThreatActor/ScriptedActor, Telemetry/ReplayLogBundle, IsolationProvider/CannedReport, EventStore/InMemoryEventStore, Clock/FixedClock, Rng/SeededRng.
- The **adapter registry** (`adapters/__init__`) with placeholder registrations for all 8 slots — streams ADD `adapters/<domain>/*`, never edit the registry.
- `manifest_hash = H(canonical_json(victim, vulns, seed))` + `correlation_id` **Rng-minted** (distinct-per-run, replayable) — **closes F-006** (replaces `lab/cli.py`'s inline `uuid.uuid4().hex` run_id with an injected Rng-minted correlation_id).
- The **`lab` per-command handler-dispatch seam** (`check -> handler` table or `lab/handlers/`) so S1/S2/S3 fill command bodies by ADD, never editing `main()` — **closes F-007**.

The store ADR **ADR-0007** (T-100, hash-chain = tamper-EVIDENCE-not-resistance + SQLite-over-JSONL) is a doc dependency that precedes the chain impl.

**Loop:** `tester` locks the shapes first (failing tests) → generic `implementer` builds → `reviewer` → then **GATE A via a FRESH `clean-room-reviewer` subagent** (clean context, no lore). After T-101: **T-110 EventStore** → **T-111 Scorer** (rest of GATE A), then **M2** — T-201 LabProvider → T-202 Vulhub gen → **T-203 e2e 3-pillar grade = GATE B = MVP EXIT**.

**Per-task discipline:** feature branch → PR per task → **GREEN CI required to merge** (all 10 checks now enforced) → squash-merge → docs note.

## Workflow (main is protected)

All work on feature branches, PR per task, solo auto-merge on green. **NOTE:** `Bash(gh pr merge:*)` may be in the framework's "ask" list, so the first merge in a session may prompt the human — accept it or move it to allow for full autonomy.

## Clean-room gates (from `docs/DELIVERY-PLAN.md`, run via `clean-room-reviewer` in a FRESH subagent)

- **GATE A** @ T-101 / T-110 / T-111 — contract+scoring spine; **adversarial; budget 4; MVP-blocking**.
- **GATE B** @ T-203 — e2e oracle / MVP exit; **hard; budget 3; MVP release**.
- **GATE C** @ T-304 — F1 calibration; **hard; budget 2**.
- **GATE D** @ T-403 + M5 — containment + F2 safety; **adversarial; budget 4 + human final sign-off**.

**SAFETY EDGE:** no live automated attack runs without containment COMPLETE+host-verified — the fail-closed orchestrator pre-flight refuses any live attack without an `IsolationVerified` event (single enforcement point; T-203 gated behind T-502; inherited by T-403, T-602). **M5 containment lands before M4 live attack** (hard edges T-502→T-203, T-503b→T-403).

## Public-repo content policy (load-bearing)

Repo holds **run-guides + MITRE mappings + PINNED REFERENCES only** — **NEVER** committed live malware / exploits / payloads (pulled at provision time into gitignored dirs). This is what keeps a public purple-team repo defensible; **enforced at GATE D**. Hold all offensive-content work to it.

## Open decisions (see `docs/OPEN-QUESTIONS.md`)

- **Q-002 / Q-006 / Q-007 / Q-008** — resolve as phases approach (M2/M3 triggers).
- **Q-009** ⚖️ ethics / content line — **MUST resolve before M4/M5** (expert/legal checkpoint).
- **Q-011** — SecGen pin TBD (fetcher refuses; `pinned_commit=None`) — resolve before **M7**.
- **Q-012** — SecGen rebuild-reproducibility (Option A) — before M7.
- **Q-013** — GOAD pin: **RESOLVED** (v3.0.0 commit-resolved to `8c18acc…`, backfilled into ARCHITECTURE.md by T-002).

## Recent learnings (not yet fully in docs)

T-002 added a repo-root `conftest.py` that makes `import lab` robust under bare `pytest` — closes a sys.path gap that would have bitten CI as the package grew. The fetcher records resolved-dep `sha256` as a TOFU (trust-on-first-use) sentinel: a real 64-hex mismatch reads as possible tampering, a first-fetch reads as "record this" — deliberately distinct messaging for a security tool. The manifest-as-oracle spine remains the load-bearing trick that makes randomized targets scorable — guard it through execution; the DETECT/MITIGATE pillars are only as honest as their calibration/negative fixtures (`{correct_ref, match_all_ref, match_none_ref}` + `skew_budget`, and `deny_all_ref`). Containment authority must be host-side and continuous because the guest is untrusted. Disk is no longer a constraint (1.7TB on `/mnt/data`); **RAM-sequential is the only real ceiling** (~55 GiB usable for guests).

## Risks / red flags

`critic` returned **GO-WITH-FIXES**; **3 fatal findings CLOSED and confirmed by a 2nd pass** (F1 DETECT calibration fixtures, F2 MITIGATE deny-everything fixture, F3 host-side continuous containment). See `docs/RED-TEAM.md`. Live risk surface (egress containment, content/ethics line) is gated to M4/M5 and tracked by Q-009; the fail-closed orchestrator pre-flight (no live attack without `IsolationVerified`) is the runtime backstop. Do not start live-attack milestones until those gates are armed and Q-009 is resolved. Open M0 followups still logged in `docs/TODO.md` "Followups" (not yet addressed): **F-002** (dup `env:` in `external-review.yml`), **F-003** (pins-gate box-version file-granularity — harden before M2), **F-004** (no unpinned-Actions-`uses:` rule), **F-005** (unused `PYTHON_VERSION` env), **F-006** (Rng-minted correlation_id — closed by T-101), **F-007** (handler-dispatch seam — closed by T-101).

## Host facts

Ryzen 9800X3D 8C/16T, 60GiB RAM (~55 usable for guests), bare metal, AMD-V + `/dev/kvm`. VirtualBox 7.1.18 AND libvirt available. Vagrant 2.4.3, Docker 29.5.2, podman 4.9.3, rbenv Ruby 3.2.3, Ubuntu 24.04, kernel 6.17. `/mnt/data` 2TB NVMe, 1.7TB free.

## Files modified this session (M0 closeout — T-006 + T-007 + doc reconciliation)

```
T-006 + T-007 (PR #8, branch chore/m0-closeout-adrs):
  docs/ADR/0002-hypervisor-behind-labprovider.md   (new, status accepted)
  docs/ADR/0005-sequential-scenario-scoped-scope.md (new, status accepted)
  docs/TODO.md      (T-006/T-007 → DONE; M0 COMPLETE header note)
  docs/CHANGELOG.md (ADR-0002 + ADR-0005 + M0-complete summary under [Unreleased]/Added)
  docs/HANDOFF.md   (this rewrite — M0-COMPLETE seam)
Working tree: clean prior to this docs PR; gates pass (pins_gate ., size_guard .).
```

## Suggested resume command

```bash
cd /home/memez/purple-range
git checkout main && git pull
git log --oneline -5   # expect ...#8 (M0 closeout ADRs); 38cebb8 T-002 (#7); a88e8bd T-005 (#6); e992c2d T-004 (#5)

claude
> read docs/HANDOFF.md + docs/DELIVERY-PLAN.md + docs/TODO.md, then START M1a:
> T-101 = CONTRACT LOCK = GATE A. tester locks ALL shapes + 8 port fakes + adapter registry
> + manifest_hash + Rng-minted correlation_id (F-006) + lab handler-dispatch seam (F-007) FIRST;
> then implementer; then GATE A via a FRESH clean-room-reviewer subagent (budget 4, MVP-blocking).
> Doc dependency: ADR-0007 (store). Each task = branch → PR → GREEN CI (required) → squash-merge.
> NOTE: for specialist depth (M2 T-201 onward) run from inside purple-range or pass the forged .md as context.
```

## Session metadata

- **Updated:** 2026-05-31 (M0 COMPLETE seam — 5 code blockers + 2 ADRs merged; CI live; 10 required checks; 133 tests green).
- **Commits on `main`:** 9 (`3caf450`/`6ed5d10`/`748139e` planning → `168482a` #1 → `b072ad6` #2 → `1da6a06` #3 → `e342e45` #4 → `e992c2d` #5 → `a88e8bd` #6 → `38cebb8` #7) + this PR #8 pending.
- **Remote:** `origin` → PUBLIC `github.com/curlyjoeyaknow/purple-range`; `main` solo-protected, **10 required status checks enforced**.
- **PRs:** #1–#7 merged; **#8 (M0 closeout ADRs + docs) pending**.
- **ADRs:** ADR-0001 (manifest-oracle) + ADR-0002 (hypervisor/LabProvider) + ADR-0005 (sequential-scope) landed; ADR-0003/0004/0006/0007 reserved/in-flight (store ADR renumbered 0005→0007).
- **`/deliver` position:** pipeline ✔ · **M0 COMPLETE** · next M1a **T-101 = GATE A** → M1b (T-110 EventStore, T-111 Scorer) → M2 (T-201/T-202/T-203 = GATE B = MVP exit).
