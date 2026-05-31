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
    """Fake EventStore: list-backed; same fold/replay semantics as production."""

    def __init__(self) -> None:
        self._events: list = []

    def append(self, events: list) -> list:
        self._events.extend(events)
        return list(events)

    def fold(self, reducer: Any, init: Any) -> Any:
        acc = init
        for ev in self._events:
            acc = reducer(acc, ev)
        return acc

    def replay_from(self, seq: int) -> Iterator:
        return iter(self._events[seq:])

    def verify_chain(self) -> bool:
        return True


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
    "EventStore": [InMemoryEventStore],
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
    "FixedClock",
    "SeededRng",
    "REGISTRY",
]
