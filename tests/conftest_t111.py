"""Shared T-111 fixtures: oracle/ground-truth/boundary-result builders for the
3-pillar Scorer.

Imported by ``test_scorer_t111.py``. Kept out of the root ``conftest.py`` (same
convention as ``conftest_t101`` / ``conftest_t110``) so it does not perturb the
existing 340-green suite; the T-111 module imports the builders it needs directly.

What lives here:

  * ``manifest(...)`` — a frozen ``VulnManifest`` (the ATTACK/DETECT/MITIGATE
    oracle) whose ``manifest_hash`` is computed from ``contracts.manifest_hash``
    so re-seeding the fixture re-rolls the hash (the M5 idempotency signal).
  * Per-pillar boundary-RESULT builders — the small plain-data shapes the Scorer's
    pure pillar graders consume: an ``attack_outcome`` (what the ScriptedActor
    probed), a ``detection_result`` (what ReplayLogBundle.run_detection returned:
    TP-window hits + benign-baseline hits, each carrying actor-Clock-reconciled
    timestamps), and a ``mitigation_outcome`` (the re-attack verdict + the
    service-probe health the ScriptedActor + functional-path probe produced).
  * ``chained event-row builders`` for the reducer leg — thin re-exports of the
    T-110 builders plus ``verification_result(passed=...)`` / ``score_awarded``
    so a correlation chain can be assembled and folded.

Boundary discipline (charter #5): these builders produce the DATA that the named
boundary fakes (FixedManifestGen / ScriptedActor / ReplayLogBundle / FixedClock)
hand to the Scorer. They are NOT the Scorer; the Scorer (the unit under test) is
never faked. Where a test needs a port object rather than a value, it wires a
tiny scripted fake here that structurally conforms to the ``ports`` Protocol and
returns this scripted data — the same shape the production adapter will return.

These builders reuse the T-101 contract dataclasses + ``contracts.manifest_hash``
(the single sources of truth); they do not redefine shapes.
"""

from __future__ import annotations

from typing import Any

# Re-export the T-110 chained-event builders so the reducer tests assemble
# correlation chains from the same source of truth (no shape drift).
from conftest_t110 import (  # noqa: F401
    GENESIS_SENTINEL,
    attack_executed,
    scenario_aborted,
    scenario_generated,
    submission,
)

import contracts

# --------------------------------------------------------------------------
# The manifest oracle. A canonical victim + one vuln carrying all three oracle
# blocks (attack/detect/mitigate). ``manifest_hash`` is DERIVED from the locked
# ``contracts.manifest_hash(victim, vulns, seed)`` so two fixtures with different
# seeds get different hashes (the re-roll signal the idempotency key keys on).
# --------------------------------------------------------------------------

VICTIM: dict = {
    "ip": "192.168.56.10",
    "hostname": "victim-01",
    "platform": "linux",
    "services": ["http"],
}

# The vuln/oracle block. expected_ttps lives under attack.ttp; the DETECT
# thresholds (expected_min_hits / max_false_positives / skew_budget_s) under
# detect; the MITIGATE service_probe + deny_all_ref under mitigate.
VULN: dict = {
    "id": "vuln-1",
    "cve": "CVE-2021-0000",
    "access": "remote",
    "attack": {"ttp": ["T1190"], "proof_signal": "shell"},
    "detect": {
        "expected_log_source": "http",
        "expected_signal": "exploit",
        "expected_min_hits": 1,
        "max_false_positives": 2,
        "skew_budget_s": 30,
        "calibration": {
            "correct_ref": "rule-correct",
            "match_all_ref": "rule-all",
            "match_none_ref": "rule-none",
        },
    },
    "mitigate": {
        "control": "patch",
        "verify_check": "version >= 1.2.3",
        "service_probe": "authed-transaction",
        "deny_all_ref": "mit-deny-all",
    },
}


def manifest(*, seed: int = 1234, vulns: list | None = None,
            clock_offset_s: int = 0, skew_budget_s: int = 30) -> contracts.VulnManifest:
    """A frozen VulnManifest oracle whose manifest_hash is content-derived.

    Re-call with a different ``seed`` (or mutated ``vulns``) to get a DIFFERENT
    ``manifest_hash`` — the seed-reroll signal the scoring idempotency key keys on.
    """
    vulns = [dict(VULN)] if vulns is None else vulns
    mh = contracts.manifest_hash(VICTIM, vulns, seed)
    return contracts.VulnManifest(
        version=2,
        scenario_id="scn-1",
        seed=seed,
        manifest_hash=mh,
        generated_at="2026-06-02T00:00:00+00:00",
        clock_offset_s=clock_offset_s,
        skew_budget_s=skew_budget_s,
        victim=dict(VICTIM),
        vulns=vulns,
        scoring_oracle_ref="oracle-1",
    )


# --------------------------------------------------------------------------
# ATTACK boundary-result: what the ScriptedActor PROBED for one TTP step. The
# Scorer's ATTACK grader reads (ttp, outcome) and decides pass/fail against the
# manifest's expected_ttps. outcome ∈ {success, blocked, partial} (the locked
# AttackEvent outcome enum) plus the honest "failed/flaky" case (an attack that
# did not land), modeled as outcome="partial" or a missing/None outcome.
# --------------------------------------------------------------------------

def attack_outcome(*, ttp: str = "T1190", outcome: str = "success") -> dict:
    """One probed attack step: the TTP the learner ran + its probed outcome."""
    return {"ttp": ttp, "outcome": outcome}


# --------------------------------------------------------------------------
# DETECT boundary-result: what ReplayLogBundle.run_detection returned when the
# learner's (opaque) query was run over (a) the TP window [t_start,t_end]±skew and
# (b) the benign baseline window. Each hit carries a timestamp already reconciled
# to actor-Clock via clock_offset_s; the Scorer counts hits inside the window.
#
# We model the result as the two hit-lists the grader thresholds against:
#   tp_hits     — hits over the ground-truth (true-positive) window
#   fp_hits     — hits over the benign baseline window (false positives)
# Each hit is an actor-Clock-reconciled epoch-seconds timestamp (int) so the
# skew-budget window math is exercised against real timestamps, not a pre-counted
# integer (that would make the window/skew/offset logic untestable).
# --------------------------------------------------------------------------

def detection_result(*, tp_hits: list[int] | None = None,
                     fp_hits: list[int] | None = None) -> dict:
    """A run_detection result: TP-window hit timestamps + benign-window hit ts.

    Timestamps are actor-Clock epoch seconds; the Scorer applies the manifest's
    clock_offset_s + skew_budget_s window before counting them.
    """
    return {
        "tp_hits": [] if tp_hits is None else list(tp_hits),
        "fp_hits": [] if fp_hits is None else list(fp_hits),
    }


# The ground-truth TP window for the DETECT tests, in actor-Clock epoch seconds.
# t_start..t_end is the attack window; the skew budget widens it on both sides.
GT_T_START = 1_000
GT_T_END = 1_100

# A benign baseline window (disjoint from the TP window) the FP gate counts over.
BENIGN_T_START = 5_000
BENIGN_T_END = 5_100


def detect_window(*, t_start: int = GT_T_START, t_end: int = GT_T_END,
                  benign_start: int = BENIGN_T_START, benign_end: int = BENIGN_T_END,
                  clock_offset_s: int = 0, skew_budget_s: int = 30) -> dict:
    """The DETECT grading window the Scorer derives from the manifest + ground-truth.

    The TP window is [t_start, t_end] widened by ±skew_budget_s; SIEM timestamps
    are reconciled to actor Clock by adding clock_offset_s before the comparison.
    """
    return {
        "t_start": t_start,
        "t_end": t_end,
        "benign_start": benign_start,
        "benign_end": benign_end,
        "clock_offset_s": clock_offset_s,
        "skew_budget_s": skew_budget_s,
    }


# --------------------------------------------------------------------------
# MITIGATE boundary-result: the re-attack verdict (from ScriptedActor re-running
# the playbook from the ``base`` snapshot) + the service-probe health (the
# functional-path probe). MITIGATE passes iff re-attack is BLOCKED *and* the
# service is healthy. A deny-everything cheat blocks the re-attack but breaks the
# service, so the probe must fail it.
# --------------------------------------------------------------------------

def mitigation_outcome(*, reattack_outcome: str = "blocked",
                       service_healthy: bool = True) -> dict:
    """A MITIGATE boundary result: the re-attack outcome + service-probe health."""
    return {"reattack_outcome": reattack_outcome, "service_healthy": service_healthy}


# --------------------------------------------------------------------------
# Chained-event builders for the REDUCER leg. verification_result / score_awarded
# carry a manifest_hash so the idempotency-key + seed-reroll tests can vary it.
# (conftest_t110's verification_result has no manifest_hash arg, and its
# score_awarded defaults a fixed hash — we wrap to thread an explicit hash.)
# --------------------------------------------------------------------------

def verification_result(*, correlation_id: str = "corr-1", causation_id: str = "corr-1",
                        passed: bool = True, oracle: str = "manifest",
                        matched_ttp: str = "T1190",
                        manifest_ref: str = "manifest-1") -> contracts.VerificationResult:
    """A verification_result row (the gate score_awarded references)."""
    return contracts.VerificationResult(
        version=2,
        seq=0,
        prev_hash=GENESIS_SENTINEL,
        occurred_at="2026-06-02T00:00:04+00:00",
        oracle=oracle,
        passed=passed,
        matched_ttp=matched_ttp,
        manifest_ref=manifest_ref,
        correlation_id=correlation_id,
        causation_id=causation_id,
    )


def score_awarded(*, correlation_id: str = "corr-1", causation_id: str = "corr-1",
                  pillar: str = "attack", points: int = 10,
                  verification_ref: str = "4", manifest_ref: str = "manifest-1",
                  manifest_hash: str = "0" * 64) -> contracts.ScoreAwarded:
    """A score_awarded row carrying its bound verification_ref/manifest_ref/hash."""
    return contracts.ScoreAwarded(
        version=2,
        seq=0,
        prev_hash=GENESIS_SENTINEL,
        occurred_at="2026-06-02T00:00:05+00:00",
        pillar=pillar,
        points=points,
        verification_ref=verification_ref,
        manifest_ref=manifest_ref,
        manifest_hash=manifest_hash,
        correlation_id=correlation_id,
        causation_id=causation_id,
    )


# --------------------------------------------------------------------------
# Tiny scripted boundary fakes — used ONLY where a test must hand the Scorer a
# PORT object (not a value). Each conforms structurally to its ``ports`` Protocol
# and returns the scripted data above, exactly as the production adapter will.
# The Scorer is never among these — it is the unit under test.
# --------------------------------------------------------------------------

class ScriptedDetectionTelemetry:
    """A Telemetry fake that returns a scripted run_detection result.

    Mirrors ``adapters.ReplayLogBundle``'s surface; constructed with the TP/FP hit
    timestamps a test wants the learner's query to "return", so the Scorer's
    DETECT grader exercises real window math over real timestamps.
    """

    def __init__(self, result: dict) -> None:
        self._result = result

    def onboard(self, victim: Any, spec: Any) -> Any:
        return {"enrolled": True}

    def run_detection(self, rule: Any, window: Any) -> Any:
        return dict(self._result)

    def capture_baseline(self, window: Any) -> Any:
        return {"baseline_ref": "baseline-1"}
