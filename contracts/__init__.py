"""T-101 — the contract spine: persisted shapes + core invariants.

Re-exports the per-shape frozen dataclasses, their ``load_<shape>`` validators,
the ``SCHEMAS`` catalogue, and the cross-cutting invariants every downstream
task folds over:

  * ``canonical_json``  — the exact serialization the hash-chain hashes over;
  * ``manifest_hash``   — sha256 over canonical (victim, vulns, seed);
  * ``idempotency_key`` — the scoring de-dup key (M5);
  * ``mint_correlation_id`` — Rng-port-minted, deterministic-yet-distinct (F-006).

stdlib only — no third-party imports.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from contracts.schemas import (
    SCHEMAS,
    AttackEvent,
    AttackExecuted,
    DetectionRule,
    IsolationReport,
    OnboardSpec,
    Scenario,
    ScenarioAborted,
    ScenarioGenerated,
    SchemaError,
    ScoreAwarded,
    Submission,
    VerificationResult,
    VulnManifest,
    dump,
    load_attack_event,
    load_attack_executed,
    load_detection_rule,
    load_isolation_report,
    load_onboard_spec,
    load_scenario,
    load_scenario_aborted,
    load_scenario_generated,
    load_score_awarded,
    load_submission,
    load_validation_event,
    load_verification_result,
    load_vuln_manifest,
)


def canonical_json(obj: Any) -> str:
    """The canonical JSON serialization the hash-chain hashes over.

    Sorted keys + no whitespace => stable across dict-ordering and re-encoding,
    so the same logical content always produces the same bytes (and thus the
    same hash).
    """
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def manifest_hash(victim: dict, vulns: list, seed: int) -> str:
    """sha256 hexdigest over canonical (victim, vulns, seed).

    Order-insensitive (canonical_json sorts keys) and 64 hex chars; any change
    to victim, vulns, or seed yields a different digest (the M5 re-roll signal).
    """
    payload = {"victim": victim, "vulns": vulns, "seed": seed}
    return hashlib.sha256(canonical_json(payload).encode()).hexdigest()


def idempotency_key(
    scenario_id: str, challenge_id: str, pillar: str, manifest_hash: str
) -> tuple[str, str, str, str]:
    """The scoring de-dup key: a 4-tuple in this exact order (M5).

    A pass earned under one ``manifest_hash`` is NOT reused after a seed re-roll
    (which changes the hash), so re-rolled scenarios are graded afresh.
    """
    return (scenario_id, challenge_id, pillar, manifest_hash)


def mint_correlation_id(rng) -> str:
    """Mint a correlation_id by drawing from the injected ``Rng`` port (F-006).

    NOT ``uuid.uuid4()``: the id is a hex digest of one ``rng.next()`` draw, so a
    fresh ``SeededRng(same seed)`` reproduces the identical sequence (replayable)
    while successive draws on one instance stay distinct (the rng stream
    advances). This is what lets concurrent/repeated same-seed runs never collide
    in the log yet remain deterministically replayable.
    """
    draw = rng.next()
    return hashlib.sha256(str(draw).encode()).hexdigest()


__all__ = [
    "SCHEMAS",
    "SchemaError",
    "dump",
    "canonical_json",
    "manifest_hash",
    "idempotency_key",
    "mint_correlation_id",
    # dataclasses
    "Scenario",
    "VulnManifest",
    "OnboardSpec",
    "DetectionRule",
    "AttackEvent",
    "IsolationReport",
    "ScenarioGenerated",
    "AttackExecuted",
    "ScenarioAborted",
    "Submission",
    "VerificationResult",
    "ScoreAwarded",
    # loaders
    "load_scenario",
    "load_vuln_manifest",
    "load_onboard_spec",
    "load_detection_rule",
    "load_attack_event",
    "load_isolation_report",
    "load_validation_event",
    "load_scenario_generated",
    "load_attack_executed",
    "load_scenario_aborted",
    "load_submission",
    "load_verification_result",
    "load_score_awarded",
]
