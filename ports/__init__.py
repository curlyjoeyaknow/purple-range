"""Port interfaces (T-101) — the boundary Protocols every adapter implements.

Charter #3: every external dependency (DB, vendor SDK, HTTP API, filesystem,
clock, randomness) sits behind an interface defined in OUR code. Production
wires the real adapter; tests wire a fake. This module holds the eight ports;
it imports NO vendor SDK and no concrete adapter — interfaces only. The method
names and signatures are pinned by ARCHITECTURE.md ("Port catalogue").

Every Protocol is ``@runtime_checkable`` so a fake's structural conformance is
asserted with ``isinstance(fake, Port)`` (T-101 conformance tests). Bodies are
``...`` — a Protocol describes the surface, never an implementation.

stdlib only.
"""

from __future__ import annotations

from typing import Any, Iterator, Protocol, runtime_checkable


@runtime_checkable
class LabProvider(Protocol):
    """Provisions and controls the lab targets (VMs / containers)."""

    def bring_up(self, scenario: Any) -> Any: ...

    def tear_down(self, handle: Any) -> None: ...

    def snapshot(self, handle: Any, name: str) -> Any: ...

    def restore(self, handle: Any, ref: Any) -> None: ...

    def status(self, handle: Any) -> list: ...


@runtime_checkable
class ScenarioGenerator(Protocol):
    """Produces a vulnerable victim + its scoring manifest from a spec + seed."""

    def generate(self, scenario_spec: Any, seed: int) -> Any: ...


@runtime_checkable
class ThreatActor(Protocol):
    """Runs bounded, allowlisted automated attacks against a target."""

    def run(self, playbook: Any, target: Any, seed: int) -> Any: ...

    def techniques(self) -> list: ...


@runtime_checkable
class Telemetry(Protocol):
    """Blue-team data-plane onboarding + detection execution."""

    def onboard(self, victim: Any, spec: Any) -> Any: ...

    def run_detection(self, rule: Any, window: Any) -> Any: ...

    def capture_baseline(self, window: Any) -> Any: ...


@runtime_checkable
class IsolationProvider(Protocol):
    """Enforced containment: host-side tripwire + corroborating report."""

    def arm_tripwire(self, planes: Any) -> Any: ...

    def verify_contained(self) -> Any: ...

    def disarm_tripwire(self, handle: Any) -> Any: ...

    def panic(self) -> None: ...


@runtime_checkable
class EventStore(Protocol):
    """Append-only, hash-chained persistence; state is derived by ``fold``."""

    def append(self, events: list) -> list: ...

    def fold(self, reducer: Any, init: Any) -> Any: ...

    def replay_from(self, seq: int) -> Iterator: ...

    def verify_chain(self) -> bool: ...


@runtime_checkable
class Clock(Protocol):
    """Time port: governs grading-window math, not merely event emission."""

    def now(self) -> Any: ...

    def offset_to(self, host_ts: Any) -> Any: ...


@runtime_checkable
class Rng(Protocol):
    """Randomness port: all randomization (correlation_ids, seeds) flows here."""

    def seed(self, s: int) -> None: ...

    def next(self) -> int: ...


__all__ = [
    "LabProvider",
    "ScenarioGenerator",
    "ThreatActor",
    "Telemetry",
    "IsolationProvider",
    "EventStore",
    "Clock",
    "Rng",
]
