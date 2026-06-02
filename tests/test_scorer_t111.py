"""T-111 — the 3-pillar Scorer (pure core): FAIL-FIRST / RED.

These tests are the acceptance contract for T-111, pinned against ADR-0001
(``docs/ADR/0001-manifest-oracle-event-sourced-scoring.md`` §3, the 3-pillar
grading table + the event-sourcing invariants) and ARCHITECTURE.md ("The
3-pillar grading mechanics", "State model"). They are written BEFORE
``core/scorer`` exists: the module import is plain, so the whole file is RED at
collection until the implementer lands the surface — every behavioural assertion
below is a contract they must make GREEN, none weakened to pass today.

The Scorer has TWO responsibilities, and these tests lock BOTH:

  A. The PURE pillar graders — given the manifest oracle + the boundary-probed
     ground-truth (an attack outcome / a detection result / a re-attack +
     service-probe outcome), return a ``VerificationResult`` verdict. No I/O, no
     events; deterministic against the named fakes + FixedClock window math.

       grade_attack(manifest, *, submitted_ttp, attack_outcome)   -> VerificationResult
       grade_detect(manifest, *, detection_result, window)        -> VerificationResult
       grade_mitigate(manifest, *, mitigation_outcome)            -> VerificationResult

  B. The event-sourced REDUCER — folds the EventStore log into a scoreboard:
     applies the idempotency key ``(scenario_id, challenge_id, pillar,
     manifest_hash)``, gates ``score_awarded`` on a referenced PASSING
     ``verification_result``, and folds an un-terminated ``correlation_id`` to
     UNGRADEABLE (never a penalty, never a phantom pass).

       score_reducer(acc, row) -> Scoreboard           # a pure fold reducer
       derive_scoreboard(store) -> Scoreboard          # == store.fold(score_reducer, EMPTY)

     The ``Scoreboard`` read-model exposes:
       .points_for(pillar) -> int                      # total awarded points by pillar
       .status_of(correlation_id) -> str               # "graded" | "ungradeable" | "aborted"
       .awarded_keys() -> set[tuple]                    # the idempotency keys that scored

Boundary discipline (charter #5): the Scorer is the unit under test and is NEVER
mocked. The manifest / attack-outcome / detection-result / mitigation-outcome are
the DATA the named boundary fakes (FixedManifestGen / ScriptedActor /
ReplayLogBundle / FixedClock) hand it — built in ``conftest_t111``. Where a test
needs a port object, it wires a tiny scripted fake that conforms to the port and
returns that data, exactly as the production adapter will.

SPEC FORK flagged for ratification (see report) — the score_awarded→verification
BINDING semantics. ADR-0001 §4 says score_awarded is "bound to verification_ref
AND manifest_ref", but ``seq`` (the natural ref) is assigned by the store at
append time, so a pre-built fixture cannot pin ``verification_ref == seq``. These
reducer tests therefore gate on the BEHAVIOUR the ADR actually protects: an award
scores ONLY if a PASSING verification_result exists for the same correlation_id
(and the award's manifest_hash participates in the idempotency key). They do NOT
assert a specific ``verification_ref``-equals-``seq`` arithmetic — that is the
implementer's binding mechanism, left open here so the tests pin the contract
(no score without a passing verification; manifest_hash-keyed dedup) and not one
implementation of the ref linkage. If the owner ratifies STRICT ref binding, add
the seq-exact negative there; the current tests stay valid under both readings.
"""

from __future__ import annotations

import importlib

import conftest_t111 as fx
import pytest

import adapters

# RED discipline (honesty, charter #5): ``core/scorer`` does not exist yet, so a
# bare ``from core import scorer`` would raise at COLLECTION and take down every
# test in the file with one import error — masking which behaviours are unproven.
# Instead we resolve the module LAZILY behind a proxy: the file collects, and each
# test fails INDIVIDUALLY with a message naming the missing Scorer symbol it
# needed. The proxy is removed (replaced by ``from core import scorer``) the moment
# the implementer lands the module — at which point the tests fail/pass on
# BEHAVIOUR, which is the contract. No test is weakened: a missing symbol is a
# hard failure, never a skip.


class _MissingSurface:
    """Stands in for ``core.scorer`` until it exists; any access fails the test."""

    def __init__(self, exc: Exception) -> None:
        self._exc = exc

    def __getattr__(self, name: str):
        raise AssertionError(
            f"core.scorer.{name} is not implemented yet (T-111 RED): {self._exc!r}. "
            "The implementer must provide this Scorer surface."
        )


try:
    scorer = importlib.import_module("core.scorer")
except Exception as _exc:  # ModuleNotFoundError today; any import error -> per-test RED
    scorer = _MissingSurface(_exc)

# The pillar enum the verdicts carry (locked in contracts._PILLAR_ENUM).
ATTACK, DETECT, MITIGATE = "attack", "detect", "mitigate"


# ==========================================================================
# A. PURE PILLAR GRADERS
# ==========================================================================

# --------------------------------------------------------------------------
# ATTACK  [ADR §3 / ARCHITECTURE: pass iff learner TTP ∈ expected_ttps OR an auto
# attack_event with outcome:success; a flaky attack neither scores nor penalizes]
# --------------------------------------------------------------------------

def test_attack_passes_only_on_manifest_ttp_or_success_outcome():
    """ATTACK passes on a manifest-listed TTP; fails on an unlisted one.

    Two halves of one concept (the pass CONDITION), so two assertions with a
    shared arrange. The manifest lists T1190; a submitted T1190 with a probed
    ``success`` passes, an off-manifest T9999 does not.
    """
    manifest = fx.manifest()

    listed = scorer.grade_attack(
        manifest,
        submitted_ttp="T1190",
        attack_outcome=fx.attack_outcome(ttp="T1190", outcome="success"),
    )
    assert listed.passed is True, "a manifest-listed TTP with a success outcome must PASS ATTACK"

    unlisted = scorer.grade_attack(
        manifest,
        submitted_ttp="T9999",
        attack_outcome=fx.attack_outcome(ttp="T9999", outcome="success"),
    )
    assert unlisted.passed is False, "a TTP not in manifest.expected_ttps must FAIL ATTACK"


def test_attack_outcome_success_alone_passes_without_explicit_submission():
    """An auto ``attack_event`` with outcome:success matches even absent a typed
    submission — the OR-arm of the pass condition (ADR §3)."""
    manifest = fx.manifest()
    result = scorer.grade_attack(
        manifest,
        submitted_ttp=None,
        attack_outcome=fx.attack_outcome(ttp="T1190", outcome="success"),
    )
    assert result.passed is True, (
        "a probed attack_event{outcome:success} on a manifest TTP passes ATTACK "
        "even with no explicit learner submission"
    )


def test_attack_flaky_does_not_penalize_detect():
    """A flaky/failed ATTACK does not score ATTACK, and crucially does not
    penalize DETECT — the honesty rule (ADR §2 / §3).

    Arrange a partial (didn't-land) attack outcome but a clean DETECT signal.
    ATTACK must FAIL (no score), while DETECT graded over the SAME run still
    PASSES on its own ground-truth — the flaky attack is not held against blue.
    """
    manifest = fx.manifest()

    attack = scorer.grade_attack(
        manifest,
        submitted_ttp="T1190",
        attack_outcome=fx.attack_outcome(ttp="T1190", outcome="partial"),
    )
    assert attack.passed is False, "a flaky (partial/didn't-land) attack must NOT score ATTACK"

    # DETECT over a clean detection result is unaffected by the flaky attack.
    detect = scorer.grade_detect(
        manifest,
        detection_result=fx.detection_result(tp_hits=[1_050], fp_hits=[]),
        window=fx.detect_window(),
    )
    assert detect.passed is True, (
        "a flaky attack must NOT penalize DETECT — DETECT is graded on its own "
        "ground-truth, independent of the ATTACK verdict"
    )


@pytest.mark.parametrize("bad_outcome", ["blocked", "partial"])
def test_attack_non_success_outcome_does_not_score(bad_outcome):
    """Only outcome:success scores the auto-arm; blocked/partial do not (ADR §2)."""
    manifest = fx.manifest()
    result = scorer.grade_attack(
        manifest,
        submitted_ttp=None,
        attack_outcome=fx.attack_outcome(ttp="T1190", outcome=bad_outcome),
    )
    assert result.passed is False, f"outcome={bad_outcome!r} must not auto-score ATTACK"


# --------------------------------------------------------------------------
# DETECT  [ADR §3 / ARCHITECTURE: >= expected_min_hits over [t_start,t_end]±skew
# AND <= max_false_positives over the benign baseline; F1 discrimination]
# --------------------------------------------------------------------------

def test_detect_passes_on_enough_tp_and_few_fp():
    """The positive control: enough true positives in-window AND few false
    positives in the benign window PASSES both halves."""
    manifest = fx.manifest()  # expected_min_hits=1, max_false_positives=2
    result = scorer.grade_detect(
        manifest,
        detection_result=fx.detection_result(tp_hits=[1_050], fp_hits=[]),
        window=fx.detect_window(),
    )
    assert result.passed is True, "enough TP in-window + few FP must PASS DETECT (both halves)"


def test_detect_match_everything_fails_FP_half():
    """A "match-everything" rule fires on the benign baseline too — it EXCEEDS
    max_false_positives and must FAIL the FP half (F1 discrimination, scorer side).

    manifest max_false_positives=2; a match-all rule returns 3 benign-window hits.
    It has plenty of TP, so the ONLY reason to fail is the FP gate — which proves
    the threshold discriminates (ADR §1a / ARCHITECTURE F1 (b))."""
    manifest = fx.manifest()
    result = scorer.grade_detect(
        manifest,
        detection_result=fx.detection_result(
            tp_hits=[1_010, 1_050, 1_090],          # abundant true positives
            fp_hits=[5_010, 5_050, 5_090],          # 3 > max_false_positives=2
        ),
        window=fx.detect_window(),
    )
    assert result.passed is False, (
        "a match-everything rule firing on the benign baseline must FAIL the FP "
        "half — it cannot pass DETECT by matching everything"
    )


def test_detect_match_nothing_fails_TP_half():
    """A "match-nothing" rule returns zero in-window hits — it falls below
    expected_min_hits and must FAIL the TP half (F1 (c), scorer side).

    Zero FP (it matches nothing, so the FP gate is trivially satisfied); the ONLY
    reason to fail is the TP gate — proving a match-none rule cannot pass."""
    manifest = fx.manifest()
    result = scorer.grade_detect(
        manifest,
        detection_result=fx.detection_result(tp_hits=[], fp_hits=[]),
        window=fx.detect_window(),
    )
    assert result.passed is False, (
        "a match-nothing rule (0 in-window hits) must FAIL the TP half — it cannot "
        "pass DETECT by matching nothing"
    )


def test_detect_window_respects_skew_budget_and_clock_offset():
    """A TP hit OUTSIDE [t_start,t_end] but WITHIN the skew budget still counts,
    after reconciling SIEM ts to actor Clock via clock_offset_s (ADR §3 / M2).

    Window is [1000,1100], skew_budget=30. A hit at actor-time 1125 is 25 s past
    t_end — inside the +30 budget — so it counts. The SIEM reported it at 1075,
    50 s skewed; clock_offset_s=+50 reconciles 1075 -> 1125. Without the offset OR
    without the skew budget this hit would be dropped and DETECT would (wrongly)
    fail the TP half."""
    manifest = fx.manifest()
    result = scorer.grade_detect(
        manifest,
        # SIEM-reported ts = 1075; +clock_offset_s(50) -> actor-time 1125.
        detection_result=fx.detection_result(tp_hits=[1_075], fp_hits=[]),
        window=fx.detect_window(clock_offset_s=50, skew_budget_s=30),
    )
    assert result.passed is True, (
        "a TP hit reconciled by clock_offset_s into the ±skew_budget window must "
        "count — the Clock port governs the grading window, not decoration"
    )


def test_detect_hit_just_inside_skew_boundary_counts():
    """Boundary (off-by-one), inclusive edge: a hit EXACTLY at t_end+skew_budget
    counts (the window is inclusive of its skew edge)."""
    manifest = fx.manifest()
    result = scorer.grade_detect(
        manifest,
        detection_result=fx.detection_result(tp_hits=[1_130], fp_hits=[]),  # 1100+30
        window=fx.detect_window(clock_offset_s=0, skew_budget_s=30),
    )
    assert result.passed is True, "a hit at exactly t_end + skew_budget is in-window (inclusive edge)"


def test_detect_hit_just_outside_skew_boundary_is_dropped():
    """Boundary (off-by-one), exclusive side: a hit ONE second past t_end+skew is
    NOT a true positive, so with no other TP, DETECT fails the TP half.

    Paired with the inclusive-edge test above so the boundary is pinned on BOTH
    sides — the classic skew off-by-one. 1131 = 1100+30+1."""
    manifest = fx.manifest()
    result = scorer.grade_detect(
        manifest,
        detection_result=fx.detection_result(tp_hits=[1_131], fp_hits=[]),
        window=fx.detect_window(clock_offset_s=0, skew_budget_s=30),
    )
    assert result.passed is False, (
        "a hit one second past t_end + skew_budget is out-of-window; with no other "
        "TP, DETECT must fail the TP half (off-by-one guard)"
    )


def test_detect_reads_through_telemetry_port():
    """The DETECT grader consumes a Telemetry PORT result, not a hardcoded count.

    A scripted Telemetry fake (conforms to ``ports.Telemetry``) returns the hits;
    the Scorer calls ``run_detection`` and grades the result. This pins that the
    Scorer reads through the boundary (the production ReplayLogBundle slots in
    unchanged), rather than the test pre-counting. The Scorer is NOT faked — only
    the Telemetry boundary is."""
    manifest = fx.manifest()
    telemetry = fx.ScriptedDetectionTelemetry(fx.detection_result(tp_hits=[1_050], fp_hits=[]))

    result = scorer.grade_detect_via_telemetry(
        manifest,
        telemetry=telemetry,
        rule={"id": "rule-1"},
        window=fx.detect_window(),
    )
    assert result.passed is True, (
        "grade_detect_via_telemetry must run the learner's query through the "
        "Telemetry port and grade the returned hits"
    )


# --------------------------------------------------------------------------
# MITIGATE  [ADR §3 / ARCHITECTURE: re-attack -> blocked AND service_probe healthy
# on the functional path; F2 deny-everything discrimination]
# --------------------------------------------------------------------------

def test_mitigate_passes_on_blocked_reattack_and_healthy_service():
    """The positive control: a re-attack that is BLOCKED with the service still
    healthy on the functional path PASSES MITIGATE (both halves)."""
    result = scorer.grade_mitigate(
        fx.manifest(),
        mitigation_outcome=fx.mitigation_outcome(reattack_outcome="blocked", service_healthy=True),
    )
    assert result.passed is True, "blocked re-attack + healthy service must PASS MITIGATE"


def test_mitigate_deny_everything_fails_service_probe():
    """A "deny-everything" mitigation BLOCKS the re-attack but BREAKS the service —
    the service_probe must FAIL it (F2 discrimination, scorer side, ADR §1a/§3).

    The re-attack IS blocked (the cheat's one true thing), so the ONLY reason to
    fail is the service-probe half. This proves the probe detects a broken
    service, not just liveness — a deny-everything cannot buy MITIGATE."""
    result = scorer.grade_mitigate(
        fx.manifest(),
        mitigation_outcome=fx.mitigation_outcome(reattack_outcome="blocked", service_healthy=False),
    )
    assert result.passed is False, (
        "deny-everything blocks the re-attack but breaks the service — the "
        "service_probe must FAIL MITIGATE (it is not a liveness rubber-stamp)"
    )


def test_mitigate_fails_when_reattack_not_blocked():
    """If the re-attack still SUCCEEDS, the mitigation didn't work — FAIL MITIGATE
    even with a healthy service (the re-attack half)."""
    result = scorer.grade_mitigate(
        fx.manifest(),
        mitigation_outcome=fx.mitigation_outcome(reattack_outcome="success", service_healthy=True),
    )
    assert result.passed is False, "a re-attack that still lands means MITIGATE fails"


# --------------------------------------------------------------------------
# Cross-pillar: a passing grader emits a VerificationResult BOUND to the manifest
# (verification_ref + manifest_ref), and the verdict carries the right oracle.
# --------------------------------------------------------------------------

def test_grader_emits_verification_result_bound_to_manifest_ref():
    """Every pillar verdict is a VerificationResult bound to the manifest it
    graded against (manifest_ref), not a bare bool — so the downstream
    score_awarded can reference it (ADR §4)."""
    manifest = fx.manifest()
    result = scorer.grade_attack(
        manifest,
        submitted_ttp="T1190",
        attack_outcome=fx.attack_outcome(ttp="T1190", outcome="success"),
    )
    assert isinstance(result, type(fx.verification_result())), (
        "a grader must return a VerificationResult contract instance"
    )
    assert result.manifest_ref == manifest.manifest_hash, (
        "the verdict must be bound to the manifest it was graded against "
        "(manifest_ref carries the manifest_hash)"
    )


# ==========================================================================
# B. EVENT-SOURCED REDUCER  [ADR §4 / ARCHITECTURE State model]
# ==========================================================================

# Each reducer test assembles a correlation chain in the EventStore (the real
# InMemoryEventStore fake — a boundary, never mocked) and folds it with the
# Scorer's reducer. The Scorer reducer is the unit under test.

def _store_with(events: list):
    """A fresh InMemoryEventStore with ``events`` appended (one batch)."""
    store = adapters.InMemoryEventStore()
    store.append(events)
    return store


def test_scoreboard_is_a_fold_of_the_log():
    """The scoreboard is a pure FOLD over the log: re-folding the SAME log
    reproduces an identical scoreboard (replayability — ADR §4 / charter #1).

    A passing verification + its bound score_awarded; two independent folds of the
    same store must be equal, and the awarded points must be present."""
    store = _store_with([
        fx.scenario_generated(correlation_id="c1"),
        fx.attack_executed(correlation_id="c1"),
        fx.submission(correlation_id="c1"),
        fx.verification_result(correlation_id="c1", passed=True),
        fx.score_awarded(correlation_id="c1", pillar="attack", points=10),
    ])

    first = scorer.derive_scoreboard(store)
    second = scorer.derive_scoreboard(store)

    assert first == second, "two folds of the same log must produce an identical scoreboard"
    assert first.points_for("attack") == 10, "the fold must reduce awarded points by pillar"


def test_score_awarded_requires_passing_verification():
    """A ``score_awarded`` whose referenced ``verification_result`` did NOT pass
    must NOT add points — no score without a passing verification (ADR §4).

    The chain carries a FAILING verification_result; even though a score_awarded
    row follows it, the reducer must refuse to count it (the honesty gate)."""
    store = _store_with([
        fx.scenario_generated(correlation_id="c1"),
        fx.attack_executed(correlation_id="c1"),
        fx.submission(correlation_id="c1"),
        fx.verification_result(correlation_id="c1", passed=False),
        fx.score_awarded(correlation_id="c1", pillar="attack", points=10),
    ])
    board = scorer.derive_scoreboard(store)
    assert board.points_for("attack") == 0, (
        "score_awarded gated on a FAILING verification_result must contribute 0 "
        "points — there is no score without a passing verification"
    )


def test_unterminated_correlation_id_folds_ungradeable():
    """A correlation chain with no terminating verdict folds to UNGRADEABLE — not
    a pass, not a penalty (ADR §2/§4 / ARCHITECTURE State model)."""
    store = _store_with([
        fx.scenario_generated(correlation_id="c-open"),
        fx.attack_executed(correlation_id="c-open"),
        fx.submission(correlation_id="c-open"),
        # No verification_result / score_awarded — the run never terminates.
    ])
    board = scorer.derive_scoreboard(store)
    assert board.status_of("c-open") == "ungradeable", (
        "an un-terminated correlation_id must fold to UNGRADEABLE, never an "
        "implicit pass"
    )
    assert board.points_for("attack") == 0, "an un-terminated run scores nothing"


def test_aborted_correlation_id_folds_aborted_not_penalized():
    """A scenario_aborted terminates the run as ABORTED (UNGRADEABLE family) —
    a mid-playbook crash never appears as a penalty or a phantom pass (M4)."""
    store = _store_with([
        fx.scenario_generated(correlation_id="c-crash"),
        fx.attack_executed(correlation_id="c-crash"),
        fx.scenario_aborted(correlation_id="c-crash"),
    ])
    board = scorer.derive_scoreboard(store)
    assert board.status_of("c-crash") == "aborted", "an aborted run folds to ABORTED"
    assert board.points_for("attack") == 0, "an aborted run scores nothing"


def test_reducer_idempotent_on_correlation_id():
    """Re-applying the SAME (scenario, challenge, pillar, manifest_hash) award
    does not double-count — the idempotency key dedups (ADR §4 / M5).

    Two score_awarded rows for the same pillar under the same manifest_hash (both
    backed by the same passing verification) must award the points ONCE."""
    mh = fx.manifest().manifest_hash
    store = _store_with([
        fx.scenario_generated(correlation_id="c1"),
        fx.verification_result(correlation_id="c1", passed=True),
        fx.score_awarded(correlation_id="c1", pillar="attack", points=10, manifest_hash=mh),
        # A duplicate award for the same pillar+manifest_hash — must be a no-op.
        fx.score_awarded(correlation_id="c1", pillar="attack", points=10, manifest_hash=mh),
    ])
    board = scorer.derive_scoreboard(store)
    assert board.points_for("attack") == 10, (
        "a duplicate award under the same idempotency key must NOT double-count"
    )


def test_score_not_reused_after_seed_reroll():
    """A pass earned under seed A's manifest_hash is NOT reused after a re-roll to
    seed B — the idempotency key INCLUDES manifest_hash (ADR §4 / M5).

    Seed A and seed B produce DIFFERENT manifest_hashes (content-derived). An
    award under hash A and a separate award under hash B are DISTINCT idempotency
    keys, so the seed-B run is graded afresh and BOTH score — the seed-A pass was
    not silently reused to cover seed B (and conversely a single hash-A award is
    not credited to a hash-B run)."""
    hash_a = fx.manifest(seed=111).manifest_hash
    hash_b = fx.manifest(seed=222).manifest_hash
    assert hash_a != hash_b, "fixture sanity: different seeds must yield different manifest_hash"

    store = _store_with([
        fx.scenario_generated(correlation_id="cA"),
        fx.verification_result(correlation_id="cA", passed=True),
        fx.score_awarded(correlation_id="cA", pillar="attack", points=10, manifest_hash=hash_a),
        fx.scenario_generated(correlation_id="cB"),
        fx.verification_result(correlation_id="cB", passed=True),
        fx.score_awarded(correlation_id="cB", pillar="attack", points=10, manifest_hash=hash_b),
    ])
    board = scorer.derive_scoreboard(store)

    keys = board.awarded_keys()
    # The two awards are DISTINCT idempotency keys (manifest_hash differs)...
    assert len({k for k in keys}) == 2, (
        "a seed re-roll changes manifest_hash, so the two awards are distinct "
        "idempotency keys — the seed-A pass is not reused for seed B"
    )
    # ...and both score (the seed-B run was graded fresh, not deduped against A).
    assert board.points_for("attack") == 20, (
        "two genuinely distinct (re-rolled) passes must both score — the "
        "manifest_hash in the key keeps them separate"
    )


def test_score_bound_to_verification_and_manifest_ref():
    """A ``score_awarded`` is counted ONLY when bound to its referenced verification
    AND manifest (ADR §4): a score_awarded whose verification_ref points at NO
    passing verification_result in the log contributes nothing.

    Here the award references a verification that is absent/unpassed — the binding
    is dangling, so the gate refuses it. Pins that the reducer enforces the
    binding, not merely the presence of a score_awarded row."""
    store = _store_with([
        fx.scenario_generated(correlation_id="c1"),
        # NO verification_result at all — the award's verification_ref dangles.
        fx.score_awarded(correlation_id="c1", pillar="attack", points=10),
    ])
    board = scorer.derive_scoreboard(store)
    assert board.points_for("attack") == 0, (
        "a score_awarded with no passing verification_result to bind to must "
        "contribute 0 — the binding is enforced, not assumed"
    )


# --------------------------------------------------------------------------
# Reducer edge cases a strong tester catches.
# --------------------------------------------------------------------------

def test_empty_log_folds_to_empty_scoreboard():
    """An empty log folds to an empty scoreboard: zero points, no crash."""
    store = adapters.InMemoryEventStore()
    board = scorer.derive_scoreboard(store)
    for pillar in (ATTACK, DETECT, MITIGATE):
        assert board.points_for(pillar) == 0, f"empty log must score 0 for {pillar}"


def test_reducer_is_order_stable_across_append_batches():
    """The fold is by seq, independent of append batching — the scoreboard is the
    same whether the chain is appended in one batch or several."""
    one_batch = _store_with([
        fx.scenario_generated(correlation_id="c1"),
        fx.verification_result(correlation_id="c1", passed=True),
        fx.score_awarded(correlation_id="c1", pillar="attack", points=10),
    ])

    split = adapters.InMemoryEventStore()
    split.append([fx.scenario_generated(correlation_id="c1")])
    split.append([fx.verification_result(correlation_id="c1", passed=True)])
    split.append([fx.score_awarded(correlation_id="c1", pillar="attack", points=10)])

    assert scorer.derive_scoreboard(one_batch) == scorer.derive_scoreboard(split), (
        "the scoreboard must be a pure fold by seq, independent of how rows were "
        "batched into the store"
    )


def test_reducer_keeps_pillars_separate():
    """Awards under different pillars accumulate independently — no cross-pillar
    bleed (a per-pillar idempotency key)."""
    store = _store_with([
        fx.scenario_generated(correlation_id="c1"),
        fx.verification_result(correlation_id="c1", passed=True),
        fx.score_awarded(correlation_id="c1", pillar="attack", points=10),
        fx.verification_result(correlation_id="c1", passed=True),
        fx.score_awarded(correlation_id="c1", pillar="mitigate", points=30),
    ])
    board = scorer.derive_scoreboard(store)
    assert board.points_for("attack") == 10
    assert board.points_for("mitigate") == 30
    assert board.points_for("detect") == 0, "an ungraded pillar stays at 0"
