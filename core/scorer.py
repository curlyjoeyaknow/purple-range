"""T-111 — the 3-pillar Scorer: pure pillar graders + the event-sourced reducer.

This is PURE business logic (ports & adapters: the inside). It imports only
``contracts`` (the persisted-shape catalogue + invariants) and treats the store
/ telemetry / manifest it is handed as injected boundary objects — it never
imports a vendor SDK, ``sqlite3``, or a concrete adapter, and it reads nothing
from a wall-clock or RNG (time comes from the injected window). The scoreboard
is DERIVED by folding the append-only log, never cached as mutable state.

Two responsibilities, both pinned by ``tests/test_scorer_t111.py``:

  A. The PURE pillar graders — given the manifest oracle + boundary-probed
     ground truth, return a ``contracts.VerificationResult`` verdict bound to
     the manifest it graded (``manifest_ref == manifest.manifest_hash``) and
     tagged with the pillar it graded (``oracle``). No I/O, no events.

  B. The event-sourced reducer — ``score_reducer`` folds persisted rows into an
     immutable ``Scoreboard``, gating each ``score_awarded`` on a PASSING
     ``verification_result`` for the same correlation (ADR-0001 §4 / Q-022) and
     de-duplicating awards by the idempotency key
     ``(scenario_id, challenge_id, pillar, manifest_hash)`` (M5).

stdlib only.
"""

from __future__ import annotations

from typing import Any

import contracts

# Pillar tokens (mirror contracts._PILLAR_ENUM).
ATTACK, DETECT, MITIGATE = "attack", "detect", "mitigate"

# The "success" attack outcome that auto-scores ATTACK; the other AttackEvent
# outcomes ({blocked, partial}) never pass and never penalize DETECT.
_SUCCESS = "success"

# A generic verification ``oracle`` that pre-dates the per-pillar tagging the
# graders now emit. A ``verification_result`` whose oracle is this generic token
# satisfies the binding for ANY pillar; a pillar-specific oracle only satisfies
# its own pillar (Q-022 behavioral binding).
_GENERIC_ORACLE = "manifest"

# Placeholders the graders stamp on the pre-append VerificationResult. ``seq`` /
# ``prev_hash`` are authoritatively assigned by the EventStore at append time
# (ADR-0007 §1a); a freshly-graded verdict carries the genesis placeholders.
_PLACEHOLDER_SEQ = 0
_GENESIS_SENTINEL = "0" * 64
_GRADED_AT = "1970-01-01T00:00:00+00:00"


# ==========================================================================
# A. PURE PILLAR GRADERS
# ==========================================================================


def _verdict(manifest: contracts.VulnManifest, *, oracle: str, passed: bool,
             matched_ttp: str) -> contracts.VerificationResult:
    """Build the pillar verdict, bound to the manifest it graded against.

    ``manifest_ref`` carries the ``manifest_hash`` so the downstream
    ``score_awarded`` can reference the exact oracle this verdict graded; the
    ``seq`` / ``prev_hash`` are genesis placeholders the EventStore overwrites at
    append time (the verdict is graded before it is persisted).
    """
    return contracts.VerificationResult(
        version=2,
        seq=_PLACEHOLDER_SEQ,
        prev_hash=_GENESIS_SENTINEL,
        occurred_at=_GRADED_AT,
        oracle=oracle,
        passed=passed,
        matched_ttp=matched_ttp,
        manifest_ref=manifest.manifest_hash,
        correlation_id="",
        causation_id="",
    )


def _expected_ttps(manifest: contracts.VulnManifest) -> set[str]:
    """The union of ``attack.ttp`` across the manifest's vulns (the oracle)."""
    ttps: set[str] = set()
    for vuln in manifest.vulns:
        ttps.update(vuln.get("attack", {}).get("ttp", []))
    return ttps


def grade_attack(manifest: contracts.VulnManifest, *, submitted_ttp: str | None,
                 attack_outcome: dict) -> contracts.VerificationResult:
    """ATTACK passes iff a ``success`` outcome landed on a manifest TTP.

    The pass condition (ADR-0001 §3) has one gate — an attack that actually
    LANDED (``outcome == success``) — keyed to a manifest TTP supplied either by
    the learner's ``submitted_ttp`` or by the auto ``attack_outcome.ttp``. A
    ``blocked`` / ``partial`` (flaky / didn't-land) outcome scores nothing, even
    for a manifest-listed TTP — and a flaky ATTACK is NOT held against DETECT,
    which is graded independently on its own ground truth.
    """
    expected = _expected_ttps(manifest)
    landed = attack_outcome.get("outcome") == _SUCCESS
    outcome_ttp = attack_outcome.get("ttp")

    candidate_ttp = submitted_ttp if submitted_ttp is not None else outcome_ttp
    passed = landed and candidate_ttp in expected

    matched = candidate_ttp if passed else ""
    return _verdict(manifest, oracle=ATTACK, passed=passed, matched_ttp=matched or "")


def _detect_thresholds(manifest: contracts.VulnManifest) -> tuple[int, int]:
    """The ``(expected_min_hits, max_false_positives)`` DETECT oracle thresholds.

    Read from the (single) vuln's ``detect`` block — the manifest's DETECT oracle.
    """
    detect = manifest.vulns[0]["detect"]
    return detect["expected_min_hits"], detect["max_false_positives"]


def _count_in_tp_window(detection_result: dict, window: dict) -> int:
    """Count TP hits inside ``[t_start, t_end] ± skew_budget`` after clock reconcile.

    SIEM timestamps are reconciled to actor-Clock time by adding
    ``clock_offset_s`` before the comparison; the skew edge is INCLUSIVE on both
    sides (``t_start - skew`` and ``t_end + skew`` both count).
    """
    offset = window["clock_offset_s"]
    skew = window["skew_budget_s"]
    lo = window["t_start"] - skew
    hi = window["t_end"] + skew
    return sum(1 for ts in detection_result.get("tp_hits", []) if lo <= ts + offset <= hi)


def _count_in_benign_window(detection_result: dict, window: dict) -> int:
    """Count FP hits inside the benign baseline window after clock reconcile."""
    offset = window["clock_offset_s"]
    lo = window["benign_start"]
    hi = window["benign_end"]
    return sum(1 for ts in detection_result.get("fp_hits", []) if lo <= ts + offset <= hi)


def grade_detect(manifest: contracts.VulnManifest, *, detection_result: dict,
                 window: dict) -> contracts.VerificationResult:
    """DETECT passes iff enough in-window TP AND few benign-window FP.

    Pass iff ``in_window_tp >= expected_min_hits`` AND
    ``fp_in_benign <= max_false_positives`` (ADR-0001 §3 / ARCHITECTURE F1).
    A match-everything rule fails the FP half; a match-nothing rule fails the TP
    half. The TP window is widened by the skew budget and reconciled by
    ``clock_offset_s`` (M2); the skew edge is inclusive.
    """
    min_hits, max_fp = _detect_thresholds(manifest)
    in_window_tp = _count_in_tp_window(detection_result, window)
    fp_in_benign = _count_in_benign_window(detection_result, window)
    passed = in_window_tp >= min_hits and fp_in_benign <= max_fp
    return _verdict(manifest, oracle=DETECT, passed=passed, matched_ttp="")


def grade_detect_via_telemetry(manifest: contracts.VulnManifest, *, telemetry: Any,
                               rule: Any, window: dict) -> contracts.VerificationResult:
    """DETECT, reading the detection result THROUGH the ``ports.Telemetry`` boundary.

    Runs the learner's query via ``telemetry.run_detection(rule, window)`` (the
    production ``ReplayLogBundle`` slots in unchanged), then grades the returned
    hits identically to ``grade_detect`` — proving the Scorer reads through the
    port rather than consuming a pre-counted integer.
    """
    detection_result = telemetry.run_detection(rule, window)
    return grade_detect(manifest, detection_result=detection_result, window=window)


def grade_mitigate(manifest: contracts.VulnManifest, *,
                   mitigation_outcome: dict) -> contracts.VerificationResult:
    """MITIGATE passes iff the re-attack is BLOCKED AND the service stays healthy.

    Both halves are required (ADR-0001 §3 / ARCHITECTURE F2): a re-attack that
    still lands fails the re-attack half; a deny-everything mitigation that blocks
    the re-attack but breaks the service fails the service-probe half (the probe
    is not a liveness rubber-stamp).
    """
    blocked = mitigation_outcome.get("reattack_outcome") == "blocked"
    healthy = mitigation_outcome.get("service_healthy") is True
    return _verdict(manifest, oracle=MITIGATE, passed=blocked and healthy, matched_ttp="")


# ==========================================================================
# B. EVENT-SOURCED REDUCER
# ==========================================================================


class Scoreboard:
    """Immutable read-model derived by folding the append-only event log.

    Value-like (``__eq__`` compares the derived state) so re-folding the same log
    reproduces an equal scoreboard — the replayability invariant. Every reducer
    step returns a NEW Scoreboard; the accumulator is never mutated, keeping the
    fold pure.

    Internal state:
      * ``_points``       — pillar -> total awarded points.
      * ``_awarded_keys`` — the idempotency keys that have scored (the dedup set).
      * ``_status``       — correlation_id -> "graded" | "ungradeable" | "aborted".
      * ``_passing``      — correlation_id -> frozenset of pillars a PASSING
                            verification has proven for that correlation.
    """

    __slots__ = ("_points", "_awarded_keys", "_status", "_passing")

    def __init__(self, points: dict[str, int] | None = None,
                 awarded_keys: frozenset[tuple] = frozenset(),
                 status: dict[str, str] | None = None,
                 passing: dict[str, frozenset[str]] | None = None) -> None:
        self._points: dict[str, int] = dict(points or {})
        self._awarded_keys: frozenset[tuple] = awarded_keys
        self._status: dict[str, str] = dict(status or {})
        self._passing: dict[str, frozenset[str]] = dict(passing or {})

    # -- read API ----------------------------------------------------------

    def points_for(self, pillar: str) -> int:
        """Total awarded points for ``pillar`` (0 if nothing scored)."""
        return self._points.get(pillar, 0)

    def status_of(self, correlation_id: str) -> str:
        """The fold status of ``correlation_id``.

        ``"aborted"`` if a ``scenario_aborted`` terminated it; ``"graded"`` if a
        terminating ``verification_result`` was folded; ``"ungradeable"`` for a
        seen-but-unterminated correlation (and as the default for any unseen id —
        never an implicit pass).
        """
        return self._status.get(correlation_id, "ungradeable")

    def awarded_keys(self) -> set[tuple]:
        """The set of idempotency keys that have scored."""
        return set(self._awarded_keys)

    # -- value semantics ---------------------------------------------------

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Scoreboard):
            return NotImplemented
        return (
            self._points == other._points
            and self._awarded_keys == other._awarded_keys
            and self._status == other._status
            and self._passing == other._passing
        )

    def __hash__(self) -> int:  # pragma: no cover - value object, equality-driven
        return hash((tuple(sorted(self._points.items())), self._awarded_keys,
                     tuple(sorted(self._status.items()))))

    def __repr__(self) -> str:  # pragma: no cover - debugging aid only
        return (f"Scoreboard(points={self._points!r}, "
                f"awarded_keys={set(self._awarded_keys)!r}, status={self._status!r})")

    # -- internal copy-with helpers (return NEW instances; never mutate self)

    def _with_status(self, correlation_id: str, status: str) -> "Scoreboard":
        new_status = dict(self._status)
        new_status[correlation_id] = status
        return Scoreboard(self._points, self._awarded_keys, new_status, self._passing)

    def _with_passing_pillar(self, correlation_id: str, pillar: str) -> "Scoreboard":
        new_passing = dict(self._passing)
        new_passing[correlation_id] = self._passing.get(correlation_id, frozenset()) | {pillar}
        # A terminating verdict marks the correlation graded (unless already aborted).
        new_status = dict(self._status)
        if new_status.get(correlation_id) != "aborted":
            new_status[correlation_id] = "graded"
        return Scoreboard(self._points, self._awarded_keys, new_status, new_passing)

    def _with_award(self, pillar: str, points: int, key: tuple) -> "Scoreboard":
        new_points = dict(self._points)
        new_points[pillar] = new_points.get(pillar, 0) + points
        new_keys = self._awarded_keys | {key}
        return Scoreboard(new_points, new_keys, self._status, self._passing)


def _seen(board: Scoreboard, correlation_id: str) -> Scoreboard:
    """Record a correlation as at-least seen (defaults its status to ungradeable)."""
    if correlation_id in board._status:
        return board
    return board._with_status(correlation_id, "ungradeable")


def _oracle_matches(oracle: str, pillar: str) -> bool:
    """Whether a verification ``oracle`` satisfies the binding for ``pillar``.

    The generic ``"manifest"`` oracle satisfies any pillar; a pillar-specific
    oracle satisfies only its own pillar (Q-022 behavioral binding).
    """
    return oracle == pillar or oracle == _GENERIC_ORACLE


def _award_key(row: dict) -> tuple:
    """The idempotency key for a ``score_awarded`` row (M5).

    ``(scenario_id, challenge_id, pillar, manifest_hash)`` — built via
    ``contracts.idempotency_key``. The persisted ``score_awarded`` carries no
    distinct scenario/challenge id at T-111, so the correlation_id stands in for
    both axes; ``manifest_hash`` is the load-bearing axis (a seed re-roll changes
    it, keeping re-rolled passes as distinct keys).
    """
    scenario_id = row["correlation_id"]
    challenge_id = row["correlation_id"]
    return contracts.idempotency_key(
        scenario_id, challenge_id, row["pillar"], row["manifest_hash"]
    )


def score_reducer(acc: Scoreboard, row: dict) -> Scoreboard:
    """Pure fold step over one persisted row, dispatching on ``event_type``.

    * ``scenario_aborted`` -> status ABORTED (never a penalty / phantom pass).
    * ``verification_result`` (passed) -> records the proven pillar + marks the
      correlation GRADED so a bound ``score_awarded`` can score; a FAILED
      verification proves nothing (the honesty gate).
    * ``score_awarded`` -> contributes points IFF a passing verification has
      proven its pillar for the same correlation AND its idempotency key is new.
    * any other chained row -> marks the correlation seen (default ungradeable).
    """
    event_type = row.get("event_type")
    correlation_id = row.get("correlation_id", "")

    if event_type == "scenario_aborted":
        return acc._with_status(correlation_id, "aborted")

    if event_type == "verification_result":
        acc = _seen(acc, correlation_id)
        if row.get("passed"):
            return acc._with_passing_pillar(correlation_id, row["oracle"])
        return acc

    if event_type == "score_awarded":
        acc = _seen(acc, correlation_id)
        pillar = row["pillar"]
        # Q-022 honesty gate: no points without a passing verification that
        # proves THIS pillar for THIS correlation.
        if not _has_matching_pass(acc, correlation_id, pillar):
            return acc
        key = _award_key(row)
        if key in acc._awarded_keys:  # idempotency: count once (M5).
            return acc
        return acc._with_award(pillar, row["points"], key)

    # Any other chained event (scenario_generated, attack_executed, submission, …)
    # just marks the correlation seen so an unterminated chain folds ungradeable.
    if correlation_id:
        return _seen(acc, correlation_id)
    return acc


def _has_matching_pass(board: Scoreboard, correlation_id: str, pillar: str) -> bool:
    """Whether a PASSING verification on ``correlation_id`` binds to ``pillar``.

    True iff the correlation has a proven oracle that matches the award's pillar:
    the award's own pillar, or the generic ``"manifest"`` oracle that satisfies
    any pillar (Q-022).
    """
    proven = board._passing.get(correlation_id, frozenset())
    return any(_oracle_matches(oracle, pillar) for oracle in proven)


def derive_scoreboard(store: Any) -> Scoreboard:
    """Fold the EventStore's log into a Scoreboard (== ``store.fold(reducer, EMPTY)``).

    Pure derivation: the scoreboard is recomputed from the log every call, so two
    folds of the same store are equal (replayability) and never read cached state.
    """
    return store.fold(score_reducer, Scoreboard())
