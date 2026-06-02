"""T-110 — the append-only, hash-chained EventStore (FAIL-FIRST / RED).

These tests are the acceptance contract for T-110, pinned against ADR-0007
(``docs/ADR/0007-event-store-hash-chained-sqlite.md``). They are written BEFORE
``SqliteEventStore`` exists: SQLite-specific tests skip cleanly when the adapter
is absent (so the file collects), but every behavioural assertion below is a
contract the implementer must make GREEN — none is weakened to pass today.

What is being pinned (one sentence per group, ADR section in brackets):

  * Chain integrity is tamper-EVIDENCE [§0/§1/§2]: ``verify_chain()`` is True on
    an intact chain and an empty store, False (never raises) on any row edit,
    reorder, deletion, or insertion; genesis ``prev_hash`` is the ``"0"*64``
    sentinel; ``row_hash`` is the FRAMED sha256
    ``sha256(prev_hash_bytes + b"\\x00" + canonical_bytes)``.
  * ``append`` is AUTHORITATIVE over ``seq``/``prev_hash`` [§1a]: it overwrites
    caller placeholders / wrong values, returns ``list[dict]`` of the populated
    persisted rows (incl. ``row_hash``), and is atomic per multi-row batch.
  * Hashed-input stability [§0]: non-finite floats in ``evidence`` are rejected
    at append; non-ASCII evidence round-trips; verification re-reads the
    PERSISTED bytes, not a re-parsed object.
  * fold / replay are deterministic and ``seq``-ordered [§5].
  * Idempotency / abort honesty [M4]: a re-appended ``scenario_aborted`` for a
    correlation_id does not double-count; an unterminated correlation_id folds
    to "ungradeable", not a pass.
  * InMemory and SQLite agree byte-for-byte on ``row_hash`` and the
    ``verify_chain`` verdict over the §4a pinned fixtures.

Boundary discipline: the EventStore is the unit under test and is NEVER mocked.
``FixedClock`` / ``SeededRng`` are the only fakes, used solely at the clock/rng
boundaries (correlation_id minting). Tampering a SQLite row is done out-of-band
via stdlib ``sqlite3`` against the DB FILE (a boundary), which is exactly the
out-of-band-edit tamper signal the chain must catch.
"""

from __future__ import annotations

import dataclasses
import sqlite3
import time

import conftest_t110 as fx
import pytest

import adapters
import contracts

# Plain imports — RED at collection until the packages exist (they do, post-T-101).
import ports  # noqa: F401  (imported to assert the package surface exists)

# The production adapter T-110 lands (ADD-only into adapters). Absent today:
# SQLite-only tests skip on it; the InMemory leg still exercises the contract.
SqliteEventStore = getattr(adapters, "SqliteEventStore", None)
_SQLITE_REASON = "SqliteEventStore not implemented yet (T-110 RED phase)"


# --------------------------------------------------------------------------
# Store construction helpers. Each returns a FRESH store of the named adapter.
# The SQLite factory takes a tmp_path file so close/reopen tests can target it.
# --------------------------------------------------------------------------

def make_inmemory():
    return adapters.InMemoryEventStore()


def make_sqlite(path):
    if SqliteEventStore is None:
        pytest.skip(_SQLITE_REASON)
    return SqliteEventStore(str(path))


@pytest.fixture
def sqlite_path(tmp_path):
    return tmp_path / "events.db"


# Every "behaviour holds on both adapters" test parametrizes over this. The
# SQLite branch is constructed lazily inside the test (it needs tmp_path), so we
# parametrize a STRING key and dispatch.
ADAPTER_KEYS = ["inmemory", "sqlite"]


def make_store(key, path):
    return make_inmemory() if key == "inmemory" else make_sqlite(path)


def read_row(path, seq):
    """Read one persisted SQLite row BY NAME, returning (seq, event_type, payload, row_hash).

    Reads columns by explicit name (not positional ``*``) so a future column
    reorder cannot silently mis-map the fields under test. This is the out-of-band
    boundary read the Addendum-1 positive-discrimination test re-frames against.
    """
    conn = sqlite3.connect(str(path))
    try:
        row = conn.execute(
            "SELECT seq, event_type, payload, row_hash FROM events WHERE seq = ?",
            (seq,),
        ).fetchone()
    finally:
        conn.close()
    return row


def _as_row(ev) -> dict:
    """Pin the persisted shape: append returns, and fold/replay_from yield, dicts.

    ADR §1a pins ``append -> list[dict]`` (the persisted superset rows incl.
    ``row_hash``). The SQLite adapter reconstructs each row from the stored
    ``payload`` dict, not the caller's frozen dataclass — so the returned and
    yielded items are that dict shape. This helper names the contract: a non-dict
    item is the broken concept, surfaced here rather than as a downstream
    ``TypeError: not subscriptable`` / ``AttributeError``.
    """
    assert isinstance(ev, dict), (
        "append/fold/replay_from must produce persisted dicts (the §1a row shape), "
        f"got {type(ev).__name__}"
    )
    return ev


# ==========================================================================
# Chain integrity — tamper-EVIDENCE  [ADR §0 / §1 / §2]
# ==========================================================================

@pytest.mark.parametrize("adapter", ADAPTER_KEYS)
def test_verify_chain_passes_on_intact_chain(adapter, sqlite_path):
    """A freshly appended, untouched chain verifies True."""
    store = make_store(adapter, sqlite_path)
    store.append(fx.a_few_events())
    assert store.verify_chain() is True, "an intact chain must verify"


@pytest.mark.parametrize("adapter", ADAPTER_KEYS)
def test_verify_chain_empty_store_is_true(adapter, sqlite_path):
    """An empty store has a trivially valid (empty) chain — True, not False."""
    store = make_store(adapter, sqlite_path)
    assert store.verify_chain() is True, "an empty store's chain is trivially valid"


def test_verify_chain_detects_tampered_row(sqlite_path):
    """Editing a persisted row's bytes out-of-band makes verify_chain False.

    SQLite-specific: we mutate the stored ``payload`` directly via stdlib sqlite3
    against the DB FILE (an out-of-band edit a chain-unaware process would make).
    The store re-hashes the STORED bytes, so its row_hash no longer matches.
    """
    store = make_sqlite(sqlite_path)
    store.append(fx.a_few_events())
    assert store.verify_chain() is True

    # Out-of-band edit: flip a byte of one row's persisted payload.
    conn = sqlite3.connect(str(sqlite_path))
    try:
        row = conn.execute(
            "SELECT seq, payload FROM events ORDER BY seq LIMIT 1"
        ).fetchone()
        tampered = row[1].replace("attack", "DETECT", 1) if "attack" in row[1] else row[1] + " "
        conn.execute("UPDATE events SET payload = ? WHERE seq = ?", (tampered, row[0]))
        conn.commit()
    finally:
        conn.close()

    assert store.verify_chain() is False, "a row whose persisted bytes changed must fail verify"


def test_verify_chain_detects_tampered_event_type(sqlite_path):
    """Tampering ONLY the event_type column out-of-band -> verify_chain() False.

    Addendum 1 / Q-020 regression guard. This is the test whose ABSENCE let the
    blind-spot slip: it tampers a NON-``payload`` column (``event_type``, the very
    field the T-111 reducer dispatches on) and asserts the chain catches it. Under
    the pre-Addendum 2-field frame, ``event_type`` is unhashed and unread by
    ``verify_chain``, so this stays True (RED). Option D folds ``event_type`` into
    the framed hash and re-reads the stored column, making it trip.
    """
    store = make_sqlite(sqlite_path)
    store.append(fx.a_few_events())
    assert store.verify_chain() is True

    conn = sqlite3.connect(str(sqlite_path))
    try:
        seq = conn.execute("SELECT seq FROM events ORDER BY seq LIMIT 1").fetchone()[0]
        # Change ONLY event_type; leave payload / prev_hash / row_hash untouched.
        conn.execute("UPDATE events SET event_type = 'LIE' WHERE seq = ?", (seq,))
        conn.commit()
    finally:
        conn.close()

    assert store.verify_chain() is False, (
        "tampering event_type alone must now break the chain (Q-020)"
    )


def test_row_hash_frames_event_type(sqlite_path):
    """The stored event_type is provably an INPUT to the row hash (causation).

    Paired with the verdict-only negative above (critic 🟠): ``is False`` alone
    could trip for an unrelated reason (a tuple-arity bug, the seq/prev_hash check
    firing first). This pins that ``event_type`` is THE byte that matters by
    reproducing the stored row_hash with the stored event_type, and showing a
    DIFFERENT event_type yields a DIFFERENT hash. seq=1 chains off the sentinel.
    """
    store = make_sqlite(sqlite_path)
    store.append(fx.a_few_events())

    seq, etype, payload, rh = read_row(sqlite_path, seq=1)

    # Re-framing with the STORED event_type reproduces the STORED row_hash...
    assert fx.framed_row_hash(fx.GENESIS_SENTINEL, etype, payload.encode("utf-8")) == rh, (
        "the stored event_type must reproduce the stored row_hash when framed in"
    )
    # ...and a DIFFERENT event_type yields a DIFFERENT hash (control: event_type
    # is genuinely load-bearing in the frame, not incidental).
    assert fx.framed_row_hash(fx.GENESIS_SENTINEL, "other_type", payload.encode("utf-8")) != rh, (
        "a different event_type must change the row_hash (it is a framed input)"
    )


def test_verify_chain_detects_reorder(sqlite_path):
    """Swapping two rows' seq (reorder) breaks the prev_hash links -> False."""
    store = make_sqlite(sqlite_path)
    store.append(fx.a_few_events())
    assert store.verify_chain() is True

    conn = sqlite3.connect(str(sqlite_path))
    try:
        rows = conn.execute("SELECT seq FROM events ORDER BY seq").fetchall()
        s1, s2 = rows[1][0], rows[2][0]
        # Swap two adjacent seqs via a temporary out-of-range value.
        conn.execute("UPDATE events SET seq = -1 WHERE seq = ?", (s1,))
        conn.execute("UPDATE events SET seq = ? WHERE seq = ?", (s1, s2))
        conn.execute("UPDATE events SET seq = ? WHERE seq = -1", (s2,))
        conn.commit()
    finally:
        conn.close()

    assert store.verify_chain() is False, "reordered rows must fail verify"


def test_verify_chain_detects_deletion(sqlite_path):
    """Deleting a row leaves a seq gap and a broken link -> False."""
    store = make_sqlite(sqlite_path)
    store.append(fx.a_few_events())
    assert store.verify_chain() is True

    conn = sqlite3.connect(str(sqlite_path))
    try:
        mid = conn.execute(
            "SELECT seq FROM events ORDER BY seq LIMIT 1 OFFSET 2"
        ).fetchone()[0]
        conn.execute("DELETE FROM events WHERE seq = ?", (mid,))
        conn.commit()
    finally:
        conn.close()

    assert store.verify_chain() is False, "a deleted row (seq gap) must fail verify"


def test_verify_chain_detects_insertion(sqlite_path):
    """Inserting a forged row that does not chain -> False."""
    store = make_sqlite(sqlite_path)
    store.append(fx.a_few_events())
    assert store.verify_chain() is True

    conn = sqlite3.connect(str(sqlite_path))
    try:
        maxseq = conn.execute("SELECT MAX(seq) FROM events").fetchone()[0]
        # A forged row appended past the tip whose prev_hash/row_hash are bogus.
        cols = [r[1] for r in conn.execute("PRAGMA table_info(events)").fetchall()]
        forged = {c: "x" for c in cols}
        forged["seq"] = maxseq + 1
        forged["event_type"] = "submission"
        forged["payload"] = "{}"
        forged["prev_hash"] = "f" * 64
        forged["row_hash"] = "e" * 64
        placeholders = ",".join("?" for _ in cols)
        conn.execute(
            f"INSERT INTO events ({','.join(cols)}) VALUES ({placeholders})",
            [forged[c] for c in cols],
        )
        conn.commit()
    finally:
        conn.close()

    assert store.verify_chain() is False, "an inserted forged row must fail verify"


def test_genesis_prev_hash_is_zero_sentinel(sqlite_path):
    """The first row's prev_hash is the chosen "0"*64 sentinel, not e3b0c4…."""
    store = make_sqlite(sqlite_path)
    rows = store.append([fx.scenario_generated()])
    first = rows[0]
    assert first["prev_hash"] == "0" * 64, "genesis prev_hash must be the 64-zero sentinel"


def test_row_hash_is_framed_input(sqlite_path):
    """row_hash is the FRAMED sha256, NOT bare prev_hash||payload concatenation.

    We recompute the framed hash independently (conftest helper) over the
    store-assigned prev_hash and the persisted canonical bytes, and assert the
    store's returned row_hash equals it. A bare-concat implementation fails here.
    """
    store = make_sqlite(sqlite_path)
    rows = store.append([fx.scenario_generated(), fx.attack_executed()])

    conn = sqlite3.connect(str(sqlite_path))
    try:
        persisted = conn.execute(
            "SELECT seq, prev_hash, event_type, payload, row_hash FROM events ORDER BY seq"
        ).fetchall()
    finally:
        conn.close()

    for seq, prev_hash, event_type, payload, row_hash in persisted:
        expected = fx.framed_row_hash(prev_hash, event_type, payload.encode("utf-8"))
        assert row_hash == expected, (
            f"row {seq}: row_hash must be the framed sha256 of "
            "prev_hash_bytes + 0x00 + event_type_bytes + 0x00 + persisted canonical bytes"
        )
    # And the returned dicts agree with the persisted row_hashes (no divergence).
    assert [r["row_hash"] for r in rows] == [p[3] for p in persisted]


# ==========================================================================
# append authority  [ADR §1a — the B2 resolution]
# ==========================================================================

@pytest.mark.parametrize("adapter", ADAPTER_KEYS)
def test_append_assigns_seq_and_prev_hash_overwriting_placeholders(adapter, sqlite_path):
    """Caller passes seq=0 / prev_hash="0"*64 placeholders; store assigns the
    real seq=tip+1 and prev_hash=tip.row_hash."""
    store = make_store(adapter, sqlite_path)
    rows = [_as_row(r) for r in store.append(fx.a_few_events())]

    seqs = [r["seq"] for r in rows]
    assert seqs == [1, 2, 3, 4, 5], "append must assign a gap-free 1-based seq run"

    # genesis chains off the sentinel; each subsequent prev_hash is the prior row_hash.
    assert rows[0]["prev_hash"] == "0" * 64
    for prev, cur in zip(rows, rows[1:]):
        assert cur["prev_hash"] == prev["row_hash"], "each prev_hash links to the prior row_hash"


@pytest.mark.parametrize("adapter", ADAPTER_KEYS)
def test_append_ignores_wrong_caller_prev_hash(adapter, sqlite_path):
    """A caller-supplied WRONG prev_hash is overwritten, not trusted; the chain
    still verifies. This is the integrity boundary: callers cannot forge linkage."""
    store = make_store(adapter, sqlite_path)
    # Construct events whose placeholder prev_hash is a deliberately bogus value.
    bad = contracts.ScenarioGenerated(
        version=2,
        seq=999,
        prev_hash="b" * 64,  # a lie the store must overwrite
        occurred_at="2026-05-31T00:00:00+00:00",
        seed=1,
        manifest_ref="m",
        manifest_hash="0" * 64,
        clock_offset_s=0,
        correlation_id="corr-1",
    )
    rows = [_as_row(r) for r in store.append([bad, fx.attack_executed()])]

    assert rows[0]["seq"] == 1, "wrong caller seq must be overwritten with tip+1"
    assert rows[0]["prev_hash"] == "0" * 64, "wrong caller prev_hash must be overwritten with the sentinel"
    assert store.verify_chain() is True, "chain must verify despite the caller's bogus prev_hash"


@pytest.mark.parametrize("adapter", ADAPTER_KEYS)
def test_append_returns_list_of_populated_dicts_with_row_hash(adapter, sqlite_path):
    """append returns list[dict]; each dict is the persisted superset (the event
    fields + assigned seq/prev_hash + the computed row_hash)."""
    store = make_store(adapter, sqlite_path)
    rows = store.append(fx.a_few_events())

    assert isinstance(rows, list)
    assert len(rows) == 5
    for r in rows:
        assert isinstance(r, dict), "each returned row must be a plain dict"
        for key in ("version", "seq", "prev_hash", "row_hash"):
            assert key in r, f"returned row must include {key!r}"
        assert isinstance(r["row_hash"], str) and len(r["row_hash"]) == 64


@pytest.mark.parametrize("adapter", ADAPTER_KEYS)
def test_multi_row_append_is_atomic(adapter, sqlite_path):
    """A multi-row append is ONE transaction: if any row in the batch is invalid
    (here, a non-finite float in evidence — §0), NONE persist and the chain stays
    unbroken. All-or-nothing."""
    store = make_store(adapter, sqlite_path)
    store.append([fx.scenario_generated()])  # a valid genesis already present
    chain_len_before = len(list(store.replay_from(1)))

    poisoned_batch = [
        fx.attack_executed(),
        fx.submission(evidence={"x": float("inf")}),  # invalid — must abort the batch
        fx.score_awarded(),
    ]
    with pytest.raises((ValueError, contracts.SchemaError)):
        store.append(poisoned_batch)

    chain_len_after = len(list(store.replay_from(1)))
    assert chain_len_after == chain_len_before, "a failed batch must persist NONE of its rows"
    assert store.verify_chain() is True, "the chain must stay intact after a rolled-back batch"


# ==========================================================================
# Yielded read-contract key-set  [Addendum 1 §1a — the widened read surface]
# ==========================================================================

def _dataclass_field_names(event) -> set:
    """The declared field names of a contract event dataclass."""
    return {f.name for f in dataclasses.fields(event)}


@pytest.mark.parametrize("adapter", ADAPTER_KEYS)
def test_yielded_row_keyset(adapter, sqlite_path):
    """fold/replay yield EXACTLY {dataclass fields} ∪ {row_hash, event_type}.

    Addendum 1 promotes ``event_type`` from the stripped private ``_event_type``
    to a first-class yielded key (the reducer reads ``row["event_type"]``), so the
    §1a yielded key-set is now a real contract. Pinning it (both adapters) guards
    the load-bearing ``public_row`` ``startswith("_")`` strip: a real event field
    must never be silently dropped, and the new ``event_type`` key must be present.
    Pre-Addendum the yielded dict has NO ``event_type`` key -> RED (KeyError-style
    set mismatch). seq=1 is a ScenarioGenerated; we pin its exact shape.
    """
    store = make_store(adapter, sqlite_path)
    store.append(fx.a_few_events())

    row = _as_row(next(iter(store.replay_from(1))))
    expected = _dataclass_field_names(fx.scenario_generated()) | {"row_hash", "event_type"}
    assert set(row.keys()) == expected, (
        "yielded row key-set must be exactly the dataclass fields plus "
        f"{{row_hash, event_type}}; got {sorted(row.keys())}"
    )
    assert row["event_type"] == "scenario_generated", (
        "the yielded event_type must be the snake_case discriminator the reducer dispatches on"
    )


# ==========================================================================
# Hashed-input stability  [ADR §0 — the B1 resolution]
# ==========================================================================

@pytest.mark.parametrize("adapter", ADAPTER_KEYS)
@pytest.mark.parametrize("bad_value", [float("nan"), float("inf"), float("-inf")])
def test_append_rejects_nan_or_inf_evidence(adapter, sqlite_path, bad_value):
    """A non-finite float anywhere in evidence is rejected at append (clean
    error) and never enters the chain (allow_nan=False semantics, §0)."""
    store = make_store(adapter, sqlite_path)
    with pytest.raises((ValueError, contracts.SchemaError)):
        store.append([fx.submission(evidence={"metric": bad_value})])
    assert store.verify_chain() is True, "a rejected non-finite event must not corrupt the chain"


def test_row_hash_stable_under_unicode_evidence(sqlite_path):
    """Non-ASCII evidence appends and survives a store->reopen with verify True."""
    store = make_sqlite(sqlite_path)
    store.append([fx.scenario_generated(), fx.submission(evidence={"note": "café — δ"})])
    assert store.verify_chain() is True

    reopened = make_sqlite(sqlite_path)
    assert reopened.verify_chain() is True, "unicode evidence must verify after reopen"


def test_hash_over_persisted_bytes_not_reparsed_object(sqlite_path):
    """Verification re-reads the stored bytes (the "hash the bytes you persist"
    rule): the chain is stable across a store->reopen cycle with no re-derivation
    divergence."""
    store = make_sqlite(sqlite_path)
    original = store.append(fx.a_few_events())
    assert store.verify_chain() is True

    reopened = make_sqlite(sqlite_path)
    assert reopened.verify_chain() is True

    # The persisted row_hashes are byte-identical to what append originally returned.
    conn = sqlite3.connect(str(sqlite_path))
    try:
        persisted = [r[0] for r in conn.execute("SELECT row_hash FROM events ORDER BY seq")]
    finally:
        conn.close()
    assert persisted == [r["row_hash"] for r in original], (
        "stored row_hash must equal the append-time row_hash (no read-time re-encode drift)"
    )


# ==========================================================================
# fold / replay determinism  [ADR §5]
# ==========================================================================

def _scoreboard_reducer(acc, ev):
    """A small, pure fold reducer for the determinism tests.

    The exact Scorer reducer signature is deferred to T-111 (ADR §5); these
    tests only need a DETERMINISTIC reduction over the persisted rows, so we
    fold ``score_awarded`` points by pillar. ``ev`` is a persisted dict (the
    shape ``fold`` yields). Unknown shapes are ignored.
    """
    ev = _as_row(ev)
    acc = dict(acc)
    if "points" in ev and ev.get("pillar") is not None:
        acc[ev["pillar"]] = acc.get(ev["pillar"], 0) + ev["points"]
    return acc


@pytest.mark.parametrize("adapter", ADAPTER_KEYS)
def test_fold_replay_reproduces_scoreboard(adapter, sqlite_path):
    """fold() reduces the log to a deterministic state; two folds of the same
    log are identical."""
    store = make_store(adapter, sqlite_path)
    store.append(fx.a_few_events())

    first = store.fold(_scoreboard_reducer, {})
    second = store.fold(_scoreboard_reducer, {})
    assert first == second, "two folds of the same log must be byte-identical"
    assert first.get("attack") == 10, "fold must reduce the score_awarded points deterministically"


@pytest.mark.parametrize("adapter", ADAPTER_KEYS)
def test_replay_from_seeks_by_seq(adapter, sqlite_path):
    """replay_from(seq) yields exactly the suffix from `seq` onward, seq-ordered."""
    store = make_store(adapter, sqlite_path)
    store.append(fx.a_few_events())  # seqs 1..5

    suffix = list(store.replay_from(3))
    seqs = [_as_row(ev)["seq"] for ev in suffix]
    assert seqs == [3, 4, 5], "replay_from(3) must yield seqs 3,4,5 in order"


@pytest.mark.parametrize("adapter", ADAPTER_KEYS)
def test_fold_is_order_stable_by_seq(adapter, sqlite_path):
    """fold is ordered strictly by seq, independent of append batching/timing."""
    store = make_store(adapter, sqlite_path)
    # Append in two batches; the seq order is what fold must honour, not batch order.
    store.append([fx.scenario_generated(), fx.attack_executed()])
    store.append([fx.submission(), fx.verification_result(), fx.score_awarded()])

    seqs = [_as_row(ev)["seq"] for ev in store.replay_from(1)]
    assert seqs == sorted(seqs) == [1, 2, 3, 4, 5], "fold/replay order is strictly by seq"


# ==========================================================================
# Idempotency / abort honesty  [M4 grading honesty]
# ==========================================================================

def _termination_reducer(acc, ev):
    """Fold a per-correlation_id grading state: a correlation chain is gradeable
    only once a terminating verdict (verification_result / score_awarded) lands;
    a scenario_aborted marks it aborted (idempotent — re-marking is a no-op).
    """
    ev = _as_row(ev)
    acc = dict(acc)
    cid = ev.get("correlation_id")
    if cid is None:
        return acc
    state = dict(acc.get(cid, {"status": "ungradeable", "points": 0}))
    if "points" in ev and ev.get("pillar") is not None:
        state["status"] = "graded"
        state["points"] += ev.get("points", 0)
    elif ev.get("reason") is not None:
        # Idempotent: aborting an already-aborted correlation does not stack.
        state["status"] = "aborted"
    acc[cid] = state
    return acc


@pytest.mark.parametrize("adapter", ADAPTER_KEYS)
def test_scenario_aborted_is_idempotent_on_correlation_id(adapter, sqlite_path):
    """Re-appending a scenario_aborted for the same correlation_id does not
    double-count — the folded state is the same as a single abort."""
    store = make_store(adapter, sqlite_path)
    store.append([
        fx.scenario_generated(correlation_id="corr-A"),
        fx.scenario_aborted(correlation_id="corr-A"),
    ])
    once = store.fold(_termination_reducer, {})

    store.append([fx.scenario_aborted(correlation_id="corr-A")])
    twice = store.fold(_termination_reducer, {})

    assert twice["corr-A"]["status"] == "aborted"
    assert twice["corr-A"] == once["corr-A"], "a repeated abort must not change the folded state"


@pytest.mark.parametrize("adapter", ADAPTER_KEYS)
def test_unterminated_correlation_id_is_ungradeable(adapter, sqlite_path):
    """A correlation chain with no terminating verdict folds to "ungradeable",
    NOT a pass — grading honesty (M4)."""
    store = make_store(adapter, sqlite_path)
    store.append([
        fx.scenario_generated(correlation_id="corr-open"),
        fx.attack_executed(correlation_id="corr-open"),
        fx.submission(correlation_id="corr-open"),
        # NO verification_result / score_awarded — the correlation never terminates.
    ])
    state = store.fold(_termination_reducer, {})
    assert state["corr-open"]["status"] == "ungradeable", (
        "an unterminated correlation must be ungradeable, never an implicit pass"
    )
    assert state["corr-open"]["points"] == 0


# ==========================================================================
# Conformance — fake vs SQLite MUST agree  [ADR §4a — the M2 resolution]
# ==========================================================================

@pytest.mark.parametrize("fixture_id,builder", fx.CONFORMANCE_FIXTURES, ids=[f[0] for f in fx.CONFORMANCE_FIXTURES])
def test_inmemory_and_sqlite_agree_on_row_hash(fixture_id, builder, sqlite_path):
    """For a float / non-ASCII / nested-dict evidence fixture, InMemory and
    SQLite produce BYTE-IDENTICAL row_hash and the SAME verify_chain verdict."""
    if SqliteEventStore is None:
        pytest.skip(_SQLITE_REASON)

    batch = [fx.scenario_generated(), builder()]

    mem = make_inmemory()
    mem_rows = mem.append([e for e in batch])

    sql = make_sqlite(sqlite_path)
    sql_rows = sql.append([e for e in batch])

    assert [r["row_hash"] for r in mem_rows] == [r["row_hash"] for r in sql_rows], (
        f"{fixture_id}: row_hash must be byte-identical across InMemory and SQLite"
    )
    assert mem.verify_chain() == sql.verify_chain() is True, (
        f"{fixture_id}: both adapters must report the same (passing) verify_chain verdict"
    )

    # WIDENED (Addendum 1, critic 🟠): row_hash byte-identity holds "by
    # construction" (one shared _chain.framed_row_hash) but does NOT pin that the
    # YIELDED event_type values agree — SQLite re-sources event_type from its
    # column, InMemory from the in-dict value. Compare the FULL yielded dict so
    # the convergence (including event_type) is pinned, not merely asserted.
    mem_yielded = [dict(r) for r in mem.replay_from(1)]
    sql_yielded = [dict(r) for r in sql.replay_from(1)]
    assert mem_yielded == sql_yielded, (
        f"{fixture_id}: the full yielded dict (incl. event_type) must agree across "
        "InMemory and SQLite, not just row_hash"
    )


def test_sqlite_survives_close_reopen(sqlite_path):
    """Append, close, reopen a NEW SqliteEventStore on the same file: verify_chain
    is still True and fold is unchanged — durability the list-fake cannot model."""
    store = make_sqlite(sqlite_path)
    store.append(fx.a_few_events())
    before = store.fold(_scoreboard_reducer, {})
    del store  # drop the original handle

    reopened = make_sqlite(sqlite_path)
    assert reopened.verify_chain() is True, "chain must survive a close/reopen cycle"
    assert reopened.fold(_scoreboard_reducer, {}) == before, "fold must be unchanged after reopen"


# ==========================================================================
# Performance  [NFR — kept non-flaky via a generous-but-meaningful bound]
# ==========================================================================

@pytest.mark.perf
def test_append_latency_and_rebuild_budget(sqlite_path):
    """append < 5 ms/event and a full rebuild (fold from genesis) < 1 s at a
    modest N. The bounds are generous (mark `perf`, single events to surface
    per-append cost) so a slow CI box does not flake, while a regression to an
    O(N) full-file rewrite-per-append would still blow them."""
    store = make_sqlite(sqlite_path)
    n = 500

    t0 = time.perf_counter()
    for i in range(n):
        # Append one event at a time so the measured cost is per-append, not amortized.
        store.append([fx.attack_executed(correlation_id=f"corr-{i}")])
    append_elapsed = time.perf_counter() - t0
    per_event_ms = (append_elapsed / n) * 1000.0
    assert per_event_ms < 5.0, f"append must be < 5 ms/event; got {per_event_ms:.2f} ms"

    t1 = time.perf_counter()
    store.fold(_scoreboard_reducer, {})
    rebuild_elapsed = time.perf_counter() - t1
    assert rebuild_elapsed < 1.0, f"full rebuild must be < 1 s; got {rebuild_elapsed:.3f} s"
