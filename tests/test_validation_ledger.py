"""Contract tests for the ValidationEvent ledger skeleton (T-004).

T-004 introduces the *skeleton* of the ValidationEvent contract and its
append-only ledger. The full event catalog + JSON-Schemas are locked later in
T-101; here we lock only the minimal-but-versioned shape and the
append-only-writer behaviour, BEFORE any implementation exists.

These tests FAIL until `lab/ledger.py` exists. They fail for the right reason:
first an ImportError (no `lab` package), then assertion-level once the skeleton
question is resolved.

Locked interface (so the implementer cannot drift)
--------------------------------------------------
``lab/ledger.py`` defines:

    @dataclass(frozen=True)
    class ValidationEvent:
        # `version` is FIRST-CLASS and serialized; T-101 locks the full catalog.
        version: int = 1            # always present in the dict
        run_id: str = ...
        phase: str | None = ...
        check: str = ...
        status: str = ...
        evidence_ref: str | None = ...
        ts: str = ...

        def to_dict(self) -> dict:  # deterministic, ordered, one JSON line
            ...

    class Ledger(Protocol):         # the port; append-only — no update/delete
        def append(self, event: ValidationEvent) -> None: ...

    class JsonlLedger:              # prod adapter: one JSON line per event
        def __init__(self, path): ...
        def append(self, event): ...     # creates file if absent; APPENDS

    class InMemoryLedger:           # test fake: keeps a list
        events: list[ValidationEvent]
        def append(self, event): ...

    class Clock(Protocol):
        def now_iso(self) -> str: ...

    class FixedClock:               # test fake: deterministic ts
        def __init__(self, ts: str): ...
        def now_iso(self) -> str: ...   # returns the injected ts every call

Behavioural decisions locked here:
  * The serialized dict ALWAYS carries the `version` key (== 1 for the
    skeleton). A persisted shape without `version` is a charter #2 violation.
  * `evidence_ref=None` / `phase=None` serialize as JSON null — present in the
    dict, not dropped, not stringified to "None".
  * `JsonlLedger.append` is APPEND-ONLY: a second append never truncates the
    first; each line is independently valid JSON; no partial line on a normal
    append.
  * `FixedClock.now_iso()` is deterministic: two events stamped from the same
    injected clock share an identical `ts`.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Import the unit under test. Until lab/ledger.py exists this is the failure
# that makes these tests RED for the right reason (collection-time ImportError).
# The `lab` package lives at the repo root (sibling of tests/), mirroring how
# the existing scripts/ tests inject their import path.
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from lab.ledger import (  # noqa: E402
    Clock,
    FixedClock,
    InMemoryLedger,
    JsonlLedger,
    Ledger,
    ValidationEvent,
)

FIXED_TS = "2026-01-01T00:00:00Z"


def _make_event(**overrides) -> ValidationEvent:
    """A fully-populated skeleton event; overrides patch individual fields."""
    defaults = dict(
        run_id="run-1",
        phase="web",
        check="up",
        status="not-implemented",
        evidence_ref=None,
        ts=FIXED_TS,
    )
    defaults.update(overrides)
    return ValidationEvent(**defaults)


# ---------------------------------------------------------------------------
# 3. test_validation_ledger_appends — the spec-named test.
# ---------------------------------------------------------------------------
def test_validation_ledger_appends(tmp_path):
    """JsonlLedger appends one valid JSON line per event, append-only.

    Appending twice yields exactly two lines; each round-trips to a dict
    carrying every field; the file is created if absent.
    """
    path = tmp_path / "validation-events.jsonl"
    assert not path.exists(), "precondition: ledger file does not exist yet"

    ledger = JsonlLedger(path)
    ledger.append(_make_event(check="up"))

    assert path.exists(), "JsonlLedger.append must create the file if absent"

    ledger.append(_make_event(check="down"))

    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2, "two appends must yield exactly two JSONL lines"

    first = json.loads(lines[0])
    second = json.loads(lines[1])
    assert first["check"] == "up", "first line must be the first event appended"
    assert second["check"] == "down", (
        "second append must not truncate/overwrite the first line"
    )


def test_jsonl_lines_each_round_trip_to_a_dict(tmp_path):
    """Every appended line is independently valid JSON carrying all fields."""
    path = tmp_path / "validation-events.jsonl"
    ledger = JsonlLedger(path)
    ledger.append(_make_event(check="up", phase="web", evidence_ref="ev/1"))

    line = path.read_text(encoding="utf-8").splitlines()[0]
    record = json.loads(line)

    assert record["run_id"] == "run-1"
    assert record["phase"] == "web"
    assert record["check"] == "up"
    assert record["status"] == "not-implemented"
    assert record["evidence_ref"] == "ev/1"
    assert record["ts"] == FIXED_TS


def test_jsonl_append_is_append_only_not_truncating(tmp_path):
    """A second append preserves the first line verbatim (no truncation)."""
    path = tmp_path / "validation-events.jsonl"
    ledger = JsonlLedger(path)

    ledger.append(_make_event(check="up"))
    first_snapshot = path.read_text(encoding="utf-8")

    ledger.append(_make_event(check="status"))
    after = path.read_text(encoding="utf-8")

    assert after.startswith(first_snapshot), (
        "append-only: the bytes of the first event must remain a prefix "
        "after a second append"
    )


def test_jsonl_append_writes_no_partial_line(tmp_path):
    """On a normal append every line is complete, parseable JSON.

    Not over-engineering atomicity here — just proving the writer leaves no
    half-written / unparseable line behind on the happy path.
    """
    path = tmp_path / "validation-events.jsonl"
    ledger = JsonlLedger(path)
    for verb in ("up", "down", "reset"):
        ledger.append(_make_event(check=verb))

    raw = path.read_text(encoding="utf-8")
    lines = raw.splitlines()
    assert len(lines) == 3, "three appends → three lines, none merged/split"
    for line in lines:
        json.loads(line)  # raises if any line is a partial / malformed record


# ---------------------------------------------------------------------------
# 4. Edge cases — serialization stability, null handling, mandatory version.
# ---------------------------------------------------------------------------
def test_version_is_present_and_one_in_serialized_dict():
    """`version` is first-class and serialized == 1 (charter #2: every
    persisted shape carries `version:int`)."""
    record = _make_event().to_dict()
    assert "version" in record, "serialized ValidationEvent MUST carry `version`"
    assert record["version"] == 1, "skeleton ValidationEvent is version 1"
    assert isinstance(record["version"], int), "`version` is an int, not a str"


def test_none_fields_serialize_as_json_null():
    """evidence_ref=None and phase=None serialize as null — present, not
    dropped, not the string 'None'."""
    record = _make_event(phase=None, evidence_ref=None).to_dict()

    assert "phase" in record, "phase key must be present even when None"
    assert record["phase"] is None, "phase=None must serialize as JSON null"
    assert "evidence_ref" in record, "evidence_ref key must be present when None"
    assert record["evidence_ref"] is None, (
        "evidence_ref=None must serialize as JSON null, not 'None'"
    )

    # And it survives a JSON round-trip as null (not the string "None").
    reparsed = json.loads(json.dumps(record))
    assert reparsed["phase"] is None
    assert reparsed["evidence_ref"] is None


def test_serialization_is_stable_and_ordered():
    """to_dict() is deterministic: same event → byte-identical JSON, and key
    order is stable across two serializations (so the JSONL ledger is
    diffable / chainable later)."""
    event = _make_event()
    first = json.dumps(event.to_dict())
    second = json.dumps(_make_event().to_dict())

    assert first == second, "equal events must serialize to identical JSON"

    keys_a = list(event.to_dict().keys())
    keys_b = list(_make_event().to_dict().keys())
    assert keys_a == keys_b, "key ordering must be stable across serializations"


def test_validation_event_is_frozen():
    """ValidationEvent is immutable — an event, once made, is not mutated
    (append-only discipline starts at the value object)."""
    event = _make_event()
    with pytest.raises(Exception):
        event.status = "passed"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Clock port — ts comes from an injected clock (charter #3: clock behind a port).
# ---------------------------------------------------------------------------
def test_fixed_clock_returns_injected_ts_deterministically():
    """FixedClock.now_iso() returns the injected ts on every call, so two
    events stamped in one test share an identical ts."""
    clock = FixedClock(FIXED_TS)
    assert clock.now_iso() == FIXED_TS
    assert clock.now_iso() == FIXED_TS, "now_iso must be deterministic/repeatable"

    e1 = _make_event(ts=clock.now_iso(), check="up")
    e2 = _make_event(ts=clock.now_iso(), check="down")
    assert e1.ts == e2.ts == FIXED_TS, (
        "two events from the same FixedClock must share an identical ts"
    )


# ---------------------------------------------------------------------------
# Port conformance — the fakes satisfy the same contract as the prod adapters.
# (Structural conformance, not behaviour-mocking.)
# ---------------------------------------------------------------------------
def test_inmemory_ledger_conforms_to_ledger_port():
    """InMemoryLedger is a usable Ledger: append records the event in order."""
    ledger = InMemoryLedger()
    assert isinstance(ledger, Ledger), (
        "InMemoryLedger must structurally satisfy the Ledger port"
    )

    e1 = _make_event(check="up")
    e2 = _make_event(check="down")
    ledger.append(e1)
    ledger.append(e2)

    assert ledger.events == [e1, e2], (
        "InMemoryLedger.append is append-only and order-preserving"
    )


def test_jsonl_ledger_conforms_to_ledger_port(tmp_path):
    """JsonlLedger (prod adapter) satisfies the same Ledger port as the fake."""
    ledger = JsonlLedger(tmp_path / "validation-events.jsonl")
    assert isinstance(ledger, Ledger), (
        "JsonlLedger must structurally satisfy the Ledger port"
    )


def test_fixed_clock_conforms_to_clock_port():
    """FixedClock satisfies the Clock port (now_iso)."""
    assert isinstance(FixedClock(FIXED_TS), Clock), (
        "FixedClock must structurally satisfy the Clock port"
    )
