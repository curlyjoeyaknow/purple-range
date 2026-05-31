"""T-101 — adapter registry surface lock (FAIL-FIRST).

The registry enumerates all EIGHT adapter slots so the parallel streams S1/S2/S3
only ADD files under `adapters/<domain>/*` and NEVER edit the registry wiring.

LOCKED shape (proposed + pinned):
  adapters.REGISTRY : dict[str, list]  keyed by the 8 port names; each value is
  the list of registered adapters for that slot (placeholder entries OK at lock
  time). Registering an adapter is ADD-only (append to the slot's list / add a
  key under the slot) — never a rewrite of REGISTRY's keys.
"""

from __future__ import annotations

import pytest

# Plain import — RED at collection until T-101 lands the adapter registry.
import adapters

EIGHT_SLOTS = {
    "LabProvider",
    "ScenarioGenerator",
    "ThreatActor",
    "Telemetry",
    "IsolationProvider",
    "EventStore",
    "Clock",
    "Rng",
}


def test_registry_lists_all_eight_adapter_slots():
    """REGISTRY enumerates exactly the 8 port slots — no more, no fewer."""
    assert set(adapters.REGISTRY) == EIGHT_SLOTS, (
        "adapter registry must enumerate all 8 port slots (placeholders OK)"
    )


def test_registry_slots_are_add_only_containers():
    """Each slot is a container an adapter can be ADDED to without editing keys."""
    for slot, entries in adapters.REGISTRY.items():
        assert hasattr(entries, "__iter__"), f"slot {slot!r} must be an iterable of adapters"


@pytest.mark.parametrize("slot", sorted(EIGHT_SLOTS))
def test_each_slot_present(slot):
    assert slot in adapters.REGISTRY, f"missing registry slot {slot!r}"
