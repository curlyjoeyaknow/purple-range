"""T-101 — boundary fakes + the adapter registry.

Eight fakes, one per port, each the minimal double that structurally conforms to
its ``ports`` Protocol and does the boundary thing deterministically (charter #5:
fakes only at boundaries; "if a fake is hard to write, the port is wrong" — these
are all a few lines). Production adapters (VirtualBox, Elastic, nftables, sqlite,
…) land in later streams under ``adapters/<domain>/`` and register into
``REGISTRY`` by ADD only.

``REGISTRY`` enumerates all eight port slots up front so the parallel streams
S1/S2/S3 append adapters without ever editing the registry's keys.

stdlib only — no vendor SDK imported here at lock time.
"""

from __future__ import annotations

import random
from typing import Any, Iterator

from adapters import _chain
from adapters.event_store import SqliteEventStore


# --------------------------------------------------------------------------
# LabProvider fake
# --------------------------------------------------------------------------
class InMemoryLab:
    """Fake LabProvider: returns canned handles/statuses, no real provisioning."""

    def bring_up(self, scenario: Any) -> Any:
        return {"handle": "lab-1", "scenario": scenario}

    def tear_down(self, handle: Any) -> None:
        return None

    def snapshot(self, handle: Any, name: str) -> Any:
        return {"handle": handle, "snapshot": name}

    def restore(self, handle: Any, ref: Any) -> None:
        return None

    def status(self, handle: Any) -> list:
        return []


# --------------------------------------------------------------------------
# ScenarioGenerator fake
# --------------------------------------------------------------------------
class FixedManifestGen:
    """Fake ScenarioGenerator: returns a frozen manifest + stub victim."""

    def generate(self, scenario_spec: Any, seed: int) -> Any:
        return {"victim": None, "manifest": None, "seed": seed}


# --------------------------------------------------------------------------
# ThreatActor fake
# --------------------------------------------------------------------------
class ScriptedActor:
    """Fake ThreatActor: replays a fixed AttackEventLog for scorer tests."""

    def run(self, playbook: Any, target: Any, seed: int) -> Any:
        return []

    def techniques(self) -> list:
        return []


# --------------------------------------------------------------------------
# Telemetry fake
# --------------------------------------------------------------------------
class ReplayLogBundle:
    """Fake Telemetry: runs detection against a shipped offline log bundle."""

    def onboard(self, victim: Any, spec: Any) -> Any:
        return {"enrolled": True}

    def run_detection(self, rule: Any, window: Any) -> Any:
        return {"hits": 0}

    def capture_baseline(self, window: Any) -> Any:
        return {"baseline_ref": "baseline-1"}


# --------------------------------------------------------------------------
# IsolationProvider fake
# --------------------------------------------------------------------------
class CannedReport:
    """Fake IsolationProvider: returns a parametrized report so every isolation
    branch (contained / breached / tripwire-fired) is testable.

    The report verify_contained() returns is built from the constructor kwargs,
    defaulting to a fully-contained report; pass ``route_to_internet=True`` (or
    any other field) to exercise the breached branch.
    """

    def __init__(self, **report: Any) -> None:
        base = {
            "route_to_internet": False,
            "bridged_present": False,
            "tripwire_egress_count": 0,
        }
        base.update(report)
        self._report = base

    def arm_tripwire(self, planes: Any) -> Any:
        return {"handle": "tripwire-1", "planes": planes}

    def verify_contained(self) -> Any:
        return dict(self._report)

    def disarm_tripwire(self, handle: Any) -> Any:
        return {"egress_count": 0}

    def panic(self) -> None:
        return None


# --------------------------------------------------------------------------
# EventStore fake
# --------------------------------------------------------------------------
class InMemoryEventStore:
    """Fake EventStore: list-backed, with the SAME chain math as ``SqliteEventStore``.

    T-110 upgraded this from a pass-through stub to a true boundary double: it
    holds the persisted rows in memory but runs every chain operation through the
    shared ``adapters._chain`` primitives, so its ``row_hash`` is BYTE-IDENTICAL
    to the SQLite adapter's (ADR-0007 §4a conformance) and its ``verify_chain``
    re-reads the persisted canonical bytes exactly as the real adapter does. The
    only thing it cannot model is on-disk durability across a close/reopen — that
    is the SQLite-only test (§4a round-trip).
    """

    def __init__(self) -> None:
        # Each item is a persisted row: the §1a public dict (now incl. the
        # first-class ``event_type`` key, Addendum 1) plus the private
        # ``_payload`` bookkeeping the chain math carries.
        self._rows: list[dict] = []

    def append(self, events: list) -> list:
        """Authoritatively stamp + chain a batch (§1a/§4), all-or-nothing.

        ``chain_batch`` raises on the first invalid event BEFORE ``self._rows`` is
        touched, so a poisoned batch leaves the in-memory chain unbroken — the
        same atomicity the SQLite transaction gives.
        """
        tip_seq, tip_hash = self._tip()
        persisted = _chain.chain_batch(tip_seq, tip_hash, events)
        self._rows.extend(persisted)
        return [_chain.public_row(r) for r in persisted]

    def fold(self, reducer: Any, init: Any) -> Any:
        acc = init
        for row in self._rows:
            acc = reducer(acc, _chain.public_row(row))
        return acc

    def replay_from(self, seq: int) -> Iterator:
        # seq is 1-based and gap-free; yield the suffix from `seq` onward.
        return iter([_chain.public_row(r) for r in self._rows if r["seq"] >= seq])

    def verify_chain(self) -> bool:
        # Key-based hand-off (Addendum 1): same dict shape the SQLite adapter
        # builds, sourcing event_type from the first-class key and payload from
        # the private canonical-string carry.
        rows = [
            {
                "seq": r["seq"],
                "prev_hash": r["prev_hash"],
                "event_type": r["event_type"],
                "payload": r["_payload"],
                "row_hash": r["row_hash"],
            }
            for r in self._rows
        ]
        return _chain.verify_rows(rows)

    def _tip(self) -> tuple[int, str]:
        if not self._rows:
            return 0, _chain.GENESIS_SENTINEL
        tip = self._rows[-1]
        return tip["seq"], tip["row_hash"]


# --------------------------------------------------------------------------
# Clock fake (T-101 ports.Clock — now()/offset_to(), distinct from
# lab.ledger.FixedClock which keeps the now_iso() Ledger surface).
# --------------------------------------------------------------------------
class FixedClock:
    """Fake Clock: returns the injected timestamp on every call (deterministic).

    Distinct from ``lab.ledger.FixedClock`` (which exposes ``now_iso()`` for the
    Ledger surface): this one implements the T-101 ``ports.Clock`` port
    (``now`` / ``offset_to``) used by the grading-window math.
    """

    def __init__(self, now: str) -> None:
        self._now = now

    def now(self) -> str:
        return self._now

    def offset_to(self, host_ts: Any) -> int:
        return 0


# --------------------------------------------------------------------------
# Rng fake
# --------------------------------------------------------------------------
class SeededRng:
    """Fake Rng: a seeded stdlib PRNG. Same seed -> same stream (deterministic).

    All randomization flows through ``next()``; ``seed()`` re-seeds the stream.
    Built on ``random.Random`` so the sequence is reproducible across runs and
    across processes for a given seed.
    """

    def __init__(self, seed: int = 0) -> None:
        self._seed = seed
        self._rng = random.Random(seed)

    def seed(self, s: int) -> None:
        self._seed = s
        self._rng = random.Random(s)

    def next(self) -> int:
        return self._rng.getrandbits(64)


# --------------------------------------------------------------------------
# Registry — all 8 slots enumerated up front; ADD-only. Placeholder entries are
# the fakes so the slots are non-empty and structurally exercised at lock time;
# production adapters append here from later streams.
# --------------------------------------------------------------------------
REGISTRY: dict[str, list] = {
    "LabProvider": [InMemoryLab],
    "ScenarioGenerator": [FixedManifestGen],
    "ThreatActor": [ScriptedActor],
    "Telemetry": [ReplayLogBundle],
    "IsolationProvider": [CannedReport],
    "EventStore": [InMemoryEventStore, SqliteEventStore],
    "Clock": [FixedClock],
    "Rng": [SeededRng],
}


__all__ = [
    "InMemoryLab",
    "FixedManifestGen",
    "ScriptedActor",
    "ReplayLogBundle",
    "CannedReport",
    "InMemoryEventStore",
    "SqliteEventStore",
    "FixedClock",
    "SeededRng",
    "REGISTRY",
]
