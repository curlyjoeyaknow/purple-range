"""Shared T-110 fixtures: event-row builders + chain helpers for the EventStore.

Imported by ``test_event_store_t110.py``. Kept out of the root ``conftest.py``
(same convention as ``conftest_t101``) so it does not perturb the existing
suite; the T-110 module imports the builders it needs directly.

What lives here:

  * ``placeholder_event(...)`` builders for the six CHAINED event shapes, each
    constructed with the ADR-0007 §1a placeholder ``seq=0`` / ``prev_hash="0"*64``
    a caller must pass purely to satisfy the (required, non-defaulted) dataclass
    fields — values ``append`` then overwrites. They return frozen contract
    dataclass instances (what ``EventStore.append`` consumes), not raw dicts.
  * ``GENESIS_SENTINEL`` — the chosen 64-hex "no predecessor" token (ADR §1).
  * ``framed_row_hash(prev_hash, event_type, canonical_bytes)`` — the ADR §0
    FRAMED hash (3-field frame post-Addendum-1), recomputed independently here so
    tests assert the store's bytes against a definition that does NOT live in the
    store. ``event_type`` is framed in (utf-8) between ``prev_hash`` and
    ``canonical_bytes`` (Addendum 1 / Q-020).
  * ``CONFORMANCE_FIXTURES`` — the §4a pinned evidence/value shapes (finite float,
    non-ASCII string, nested dict) the InMemory-vs-SQLite conformance suite runs
    through BOTH adapters.

These builders reuse the T-101 contract dataclasses (the single source of truth);
they do not redefine shapes.
"""

from __future__ import annotations

import hashlib

import contracts

# ADR-0007 §1: genesis "no predecessor" sentinel — a chosen fixed 64-hex token,
# NOT the sha256 of empty input. Used both as the placeholder prev_hash a caller
# passes and as the value append stamps onto the first row.
GENESIS_SENTINEL = "0" * 64

# The placeholder seq a caller passes (discarded + overwritten by append, §1a).
PLACEHOLDER_SEQ = 0


def framed_row_hash(prev_hash: str, event_type: str, canonical_bytes: bytes) -> str:
    """The ADR-0007 §0 FRAMED row hash (3-field frame), independent of the store.

        row_hash = sha256(
            prev_hash.encode("ascii") + b"\\x00"
            + event_type.encode("utf-8") + b"\\x00"   # utf-8, NOT ascii (critic 🟡-1)
            + canonical_bytes
        )

    This is the *pinned* framing (not bare ``prev_hash + payload``) — one-byte NUL
    separators that cannot occur in a hex token, a snake_case ``event_type``
    identifier, or ``separators=(",",":")`` canonical JSON, so the input stays
    self-delimiting. Addendum 1 (Q-020) folded ``event_type`` into the frame so
    the denormalized ``events.event_type`` column is authenticated, not smuggled.
    Tests use this to assert the store frames its input exactly so — mirroring the
    production ``_chain.framed_row_hash`` signature — independently of the store.
    """
    return hashlib.sha256(
        prev_hash.encode("ascii") + b"\x00"
        + event_type.encode("utf-8") + b"\x00"
        + canonical_bytes
    ).hexdigest()


def canonical_bytes_of(event) -> bytes:
    """The exact UTF-8 canonical bytes the chain hashes over for ``event``.

    ``dump`` -> plain dict -> ``canonical_json`` -> utf-8, i.e. the bytes the
    store persists in ``payload`` and frames into ``row_hash``. Tests pass the
    store-ASSIGNED seq/prev_hash in via ``seq``/``prev_hash`` to reconstruct the
    persisted dict for an independent hash check.
    """
    d = contracts.dump(event)
    return contracts.canonical_json(d).encode("utf-8")


# --------------------------------------------------------------------------
# Placeholder-event builders for the six chained shapes. Each carries the §1a
# placeholders (seq=0, prev_hash=GENESIS_SENTINEL); append assigns the real
# values. correlation_id defaults to a caller-supplied value so idempotency /
# termination tests can pin a known correlation chain.
# --------------------------------------------------------------------------

def scenario_generated(*, correlation_id: str = "corr-1", seed: int = 1234) -> contracts.ScenarioGenerated:
    return contracts.ScenarioGenerated(
        version=2,
        seq=PLACEHOLDER_SEQ,
        prev_hash=GENESIS_SENTINEL,
        occurred_at="2026-05-31T00:00:00+00:00",
        seed=seed,
        manifest_ref="manifest-1",
        manifest_hash="0" * 64,
        clock_offset_s=0,
        correlation_id=correlation_id,
    )


def attack_executed(*, correlation_id: str = "corr-1", causation_id: str = "corr-1") -> contracts.AttackExecuted:
    return contracts.AttackExecuted(
        version=1,
        seq=PLACEHOLDER_SEQ,
        prev_hash=GENESIS_SENTINEL,
        occurred_at="2026-05-31T00:00:01+00:00",
        actor="auto",
        ttp="T1190",
        target="192.168.56.10",
        outcome="success",
        correlation_id=correlation_id,
        causation_id=causation_id,
    )


def scenario_aborted(
    *, correlation_id: str = "corr-1", causation_id: str = "corr-1", last_good_seq: int = 1
) -> contracts.ScenarioAborted:
    return contracts.ScenarioAborted(
        version=1,
        seq=PLACEHOLDER_SEQ,
        prev_hash=GENESIS_SENTINEL,
        occurred_at="2026-05-31T00:00:02+00:00",
        reason="orchestrator_restart",
        last_good_seq=last_good_seq,
        correlation_id=correlation_id,
        causation_id=causation_id,
    )


def submission(
    *, correlation_id: str = "corr-1", causation_id: str = "corr-1", evidence: dict | None = None
) -> contracts.Submission:
    return contracts.Submission(
        version=1,
        seq=PLACEHOLDER_SEQ,
        prev_hash=GENESIS_SENTINEL,
        occurred_at="2026-05-31T00:00:03+00:00",
        pillar="attack",
        evidence={"ttp": "T1190"} if evidence is None else evidence,
        manifest_hash="0" * 64,
        correlation_id=correlation_id,
        causation_id=causation_id,
    )


def verification_result(
    *, correlation_id: str = "corr-1", causation_id: str = "corr-1", passed: bool = True
) -> contracts.VerificationResult:
    return contracts.VerificationResult(
        version=2,
        seq=PLACEHOLDER_SEQ,
        prev_hash=GENESIS_SENTINEL,
        occurred_at="2026-05-31T00:00:04+00:00",
        oracle="manifest",
        passed=passed,
        matched_ttp="T1190",
        manifest_ref="manifest-1",
        correlation_id=correlation_id,
        causation_id=causation_id,
    )


def score_awarded(
    *, correlation_id: str = "corr-1", causation_id: str = "corr-1", points: int = 10
) -> contracts.ScoreAwarded:
    return contracts.ScoreAwarded(
        version=2,
        seq=PLACEHOLDER_SEQ,
        prev_hash=GENESIS_SENTINEL,
        occurred_at="2026-05-31T00:00:05+00:00",
        pillar="attack",
        points=points,
        verification_ref="4",
        manifest_ref="manifest-1",
        manifest_hash="0" * 64,
        correlation_id=correlation_id,
        causation_id=causation_id,
    )


def a_few_events() -> list:
    """A short, valid, chainable batch spanning several shapes (happy path)."""
    return [
        scenario_generated(),
        attack_executed(),
        submission(),
        verification_result(),
        score_awarded(),
    ]


# --------------------------------------------------------------------------
# §4a conformance fixture set — PINNED evidence/value shapes that MUST produce
# byte-identical row_hash across InMemory and SQLite. Each entry is
# (id, event-builder-callable) yielding a single chained event whose evidence
# exercises one stability property.
# --------------------------------------------------------------------------

CONFORMANCE_FIXTURES = [
    ("finite_float_evidence", lambda: submission(evidence={"score": 0.5})),
    ("non_ascii_evidence", lambda: submission(evidence={"note": "café — δ"})),
    ("nested_dict_evidence", lambda: submission(evidence={"a": {"b": [1, 2, {"c": True}]}})),
    # MANDATED (Addendum 1, promoted per critic 🟠): a fixture whose event_type
    # DIFFERS from the submission-rooted three above, so the conformance suite
    # actually proves the event_type frame moves the row_hash across adapters.
    # Without a distinct event_type every fixture shares event_type="submission"
    # and the suite would pass even if event_type were dropped from the frame.
    ("distinct_event_type", lambda: attack_executed()),
]
