"""T-101 — the 8 ports + their fakes: structural conformance (FAIL-FIRST).

Each port is a `@runtime_checkable` Protocol in `ports/` with NO vendor imports.
Each fake is the boundary double (registered in `adapters/`). This module pins:

  * the 8 Protocol names exist on `ports`;
  * each fake structurally conforms (`isinstance(fake, Port)` against the
    runtime-checkable Protocol) — i.e. the fake exposes the required methods;
  * a behavioral smoke per fake (it actually does the boundary thing).

LOCKED port surfaces (method names pinned; signatures per ARCHITECTURE.md):
  LabProvider        : bring_up, tear_down, snapshot, restore, status
  ScenarioGenerator  : generate
  ThreatActor        : run, techniques
  Telemetry          : onboard, run_detection, capture_baseline
  IsolationProvider  : arm_tripwire, verify_contained, disarm_tripwire, panic
  EventStore         : append, fold, replay_from, verify_chain
  Clock              : now, offset_to            (lab.ledger.Clock re-exports/ wraps)
  Rng                : seed, next

LOCKED fakes (importable from `adapters`):
  InMemoryLab, FixedManifestGen, ScriptedActor, ReplayLogBundle,
  CannedReport, InMemoryEventStore, FixedClock, SeededRng

The charter rule: "if a fake is hard to write, the interface is wrong." These
conformance tests double as the pressure test — a fake that can't be a few lines
means the port is overweight.
"""

from __future__ import annotations

import pytest

import adapters

# Plain imports — RED at collection until T-101 lands ports + fakes.
import ports

# port-name -> (Protocol attr on `ports`, required method names, fake attr on `adapters`)
PORT_SPECS = {
    "LabProvider": ("LabProvider", ["bring_up", "tear_down", "snapshot", "restore", "status"], "InMemoryLab"),
    "ScenarioGenerator": ("ScenarioGenerator", ["generate"], "FixedManifestGen"),
    "ThreatActor": ("ThreatActor", ["run", "techniques"], "ScriptedActor"),
    "Telemetry": ("Telemetry", ["onboard", "run_detection", "capture_baseline"], "ReplayLogBundle"),
    "IsolationProvider": ("IsolationProvider", ["arm_tripwire", "verify_contained", "disarm_tripwire", "panic"], "CannedReport"),
    "EventStore": ("EventStore", ["append", "fold", "replay_from", "verify_chain"], "InMemoryEventStore"),
    "Clock": ("Clock", ["now", "offset_to"], "FixedClock"),
    "Rng": ("Rng", ["seed", "next"], "SeededRng"),
}

PORT_NAMES = list(PORT_SPECS)


# --------------------------------------------------------------------------
# Ports exist, are runtime-checkable, declare the right methods, no vendor imports.
# --------------------------------------------------------------------------

@pytest.mark.parametrize("name", PORT_NAMES)
def test_port_protocol_exists_and_declares_methods(name):
    proto_attr, methods, _ = PORT_SPECS[name]
    proto = getattr(ports, proto_attr)
    for m in methods:
        assert hasattr(proto, m), f"{name} port missing method {m!r}"


@pytest.mark.parametrize("name", PORT_NAMES)
def test_port_is_runtime_checkable(name):
    """isinstance() must work against the Protocol (so conformance is testable)."""
    proto_attr, _, fake_attr = PORT_SPECS[name]
    proto = getattr(ports, proto_attr)
    fake_cls = getattr(adapters, fake_attr)
    # runtime_checkable Protocols allow isinstance; a plain class would TypeError.
    assert isinstance(_make_fake(fake_cls, name), proto), (
        f"{fake_attr} does not structurally conform to the {name} port"
    )


def test_ports_module_imports_no_vendor_sdk():
    """Charter #3: ports define interfaces only — no subprocess/socket/vendor."""
    import ports as ports_mod

    src = _module_source(ports_mod)
    for forbidden in ("import subprocess", "import socket", "VBoxManage", "import docker"):
        assert forbidden not in src, f"ports/ must not import {forbidden!r}"


# --------------------------------------------------------------------------
# Per-fake structural conformance + behavioral smoke.
# --------------------------------------------------------------------------

@pytest.mark.parametrize("name", PORT_NAMES)
def test_fake_conforms_to_port(name):
    proto_attr, methods, fake_attr = PORT_SPECS[name]
    proto = getattr(ports, proto_attr)
    fake = _make_fake(getattr(adapters, fake_attr), name)
    assert isinstance(fake, proto), f"{fake_attr} not structurally a {name}"
    for m in methods:
        assert callable(getattr(fake, m, None)), f"{fake_attr}.{m} not callable"


def test_inmemory_event_store_round_trips_events():
    """InMemoryEventStore behavioral smoke: append then fold reproduces state."""
    store = adapters.InMemoryEventStore()
    store.append([{"version": 1, "kind": "a"}, {"version": 1, "kind": "b"}])
    count = store.fold(lambda acc, ev: acc + 1, 0)
    assert count == 2, "fold over appended events must see every event"


def test_seeded_rng_is_deterministic():
    """SeededRng behavioral smoke: same seed -> same stream."""
    a = adapters.SeededRng(seed=99)
    b = adapters.SeededRng(seed=99)
    assert [a.next() for _ in range(4)] == [b.next() for _ in range(4)]


def test_fixed_clock_returns_injected_time():
    """FixedClock behavioral smoke: now() is the injected, deterministic value."""
    clk = adapters.FixedClock(now="2026-05-31T00:00:00+00:00")
    assert clk.now() == clk.now(), "FixedClock must be stable across calls"


def test_canned_report_returns_parametrized_branch():
    """CannedReport behavioral smoke: returns the report it was constructed with
    (so all isolation branches — contained / breached — are testable)."""
    breached = adapters.CannedReport(route_to_internet=True)
    report = breached.verify_contained()
    assert report["route_to_internet"] is True


# --------------------------------------------------------------------------
# Helpers — construct each fake with the minimum its constructor needs. Kept in
# the test so an over-heavy constructor (charter: "hard to write -> wrong port")
# shows up here as friction.
# --------------------------------------------------------------------------

def _make_fake(cls, name):
    """Construct the fake for port `name` with the minimum its constructor needs."""
    if name == "Clock":  # FixedClock(now=...)
        return cls(now="2026-05-31T00:00:00+00:00")
    if name == "Rng":  # SeededRng(seed=...)
        return cls(seed=1)
    return cls()


def _module_source(mod):
    import inspect

    try:
        return inspect.getsource(mod)
    except OSError:
        from pathlib import Path

        return Path(mod.__file__).read_text(encoding="utf-8")
