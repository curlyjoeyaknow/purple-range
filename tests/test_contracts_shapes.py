"""T-101 — versioned persisted-shape contract tests (FAIL-FIRST).

Pins the contract surface every downstream task consumes: each persisted shape
has a ``version:int`` FIRST, validates on ingest via ``contracts.load_<shape>()``,
rejects malformed input, and round-trips losslessly. The locked decisions:

LAYOUT (proposed + pinned here)
  contracts/schemas.py   -> frozen dataclasses, one per shape; `version` is the
                            first declared field on every persisted shape.
  contracts/__init__.py  -> re-exports the dataclasses + the `load_<shape>()`
                            validators + `canonical_json` + `manifest_hash` +
                            `idempotency_key` + the JSON-Schema dict per shape
                            (`SCHEMAS[<name>]`, stdlib-validated, no jsonschema dep).

CONTRACT of every `load_<shape>(data: dict)`:
  * returns a typed frozen dataclass instance on valid input;
  * raises (ValueError/TypeError subclass — pinned as `contracts.SchemaError`)
    if `version` is absent or any required field is missing / wrong-typed / a
    bad enum.

These tests FAIL at collection (no `contracts` package) until T-101 lands the
package, then assertion-level until the loaders are correct. They MUST NOT touch
the existing 133 tests.
"""

from __future__ import annotations

import dataclasses
import json

import pytest

import conftest_t101 as fx

# Plain import — NOT importorskip. T-101 must go RED (collection ImportError)
# until `contracts` lands; a skipped test would let CI's contracts stage pass
# green against a non-existent contract surface, defeating the lock.
import contracts


ALL_SHAPES = list(fx.PERSISTED_SHAPES)


def _loader(name):
    attr = fx.PERSISTED_SHAPES[name][1]
    return getattr(contracts, attr)


# --------------------------------------------------------------------------
# 1. version is mandatory on EVERY persisted shape.
# --------------------------------------------------------------------------

@pytest.mark.parametrize("name", ALL_SHAPES)
def test_every_persisted_shape_requires_version(name):
    """A shape ingested without `version` is rejected (charter #2)."""
    data = fx.fresh(name)
    data.pop("version", None)
    with pytest.raises(contracts.SchemaError):
        _loader(name)(data)


@pytest.mark.parametrize("name", ALL_SHAPES)
def test_valid_instance_loads(name):
    """The canonical valid instance loads without error (baseline sanity)."""
    obj = _loader(name)(fx.fresh(name))
    assert obj is not None, f"{name}: loader returned nothing for a valid instance"


# --------------------------------------------------------------------------
# 2. Malformed instances are rejected — one representative break per shape.
# --------------------------------------------------------------------------

@pytest.mark.parametrize("name", ALL_SHAPES)
def test_schema_rejects_malformed_shape(name):
    """A representative malformed instance (bad type / enum / missing) is rejected."""
    desc, mutate = fx.MALFORMED_CASES[name]
    bad = mutate(fx.fresh(name))
    with pytest.raises(contracts.SchemaError):
        _loader(name)(bad), f"{name}: loader accepted malformed input ({desc})"


# --------------------------------------------------------------------------
# 3. Round-trip: valid dict -> load -> dump -> equals the input.
#    Behaviour pinned: loading then serializing is lossless and stable.
# --------------------------------------------------------------------------

@pytest.mark.parametrize("name", ALL_SHAPES)
def test_round_trip_is_lossless(name):
    """load(dump(load(x))) preserves every field — no silent drop/rename."""
    data = fx.fresh(name)
    obj = _loader(name)(data)
    dumped = contracts.dump(obj)
    assert dumped == data, f"{name}: round-trip changed the payload"


# --------------------------------------------------------------------------
# 2b. NESTED malformed instances are rejected (B1). The schemas are NOT a
#     top-level-only gate: malformed nested containers (a bad Component, a
#     non-dict vuln, a missing F1 calibration ref) must be rejected too.
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    "name, desc, mutate",
    fx.NESTED_MALFORMED_CASES,
    ids=[f"{c[0]}::{c[1]}" for c in fx.NESTED_MALFORMED_CASES],
)
def test_schema_rejects_nested_malformed(name, desc, mutate):
    """A malformed NESTED container is rejected, not waved through."""
    bad = mutate(fx.fresh(name))
    with pytest.raises(contracts.SchemaError):
        _loader(name)(bad)


# --------------------------------------------------------------------------
# 3b. dump() returns an independent snapshot (B2). The "frozen" contract must
#     NOT be mutable through its dump: mutating a dumped nested container must
#     leave the source instance unchanged on a subsequent dump.
# --------------------------------------------------------------------------

@pytest.mark.parametrize("name", ALL_SHAPES)
def test_dump_does_not_alias_nested_mutables(name):
    """Mutating a dumped list/dict must not reach back into the instance."""
    obj = _loader(name)(fx.fresh(name))
    first = contracts.dump(obj)
    mutated_any = False
    for key, value in first.items():
        if isinstance(value, list):
            value.append("__intruder__")
            mutated_any = True
        elif isinstance(value, dict):
            value["__intruder__"] = "x"
            mutated_any = True
    second = contracts.dump(obj)
    assert second == fx.fresh(name), (
        f"{name}: mutating dump() output bled back into the frozen instance"
    )
    if not mutated_any:
        pytest.skip(f"{name}: no container fields to test aliasing on")


def test_dump_components_append_does_not_mutate_source():
    """Direct repro: dump(obj)['components'].append(...) leaves a 2nd dump intact."""
    obj = contracts.load_scenario(fx.scenario())
    contracts.dump(obj)["components"].append({"name": "intruder"})
    assert len(contracts.dump(obj)["components"]) == 1


# --------------------------------------------------------------------------
# 3c. Schema/loader agreement (S1). For every persisted shape the set of
#     non-version required fields the SCHEMA enforces must equal the set the
#     LOADER (dataclass, no-default fields) enforces — so they cannot drift.
#     `version` is excluded: it is schema-required everywhere, but the
#     lab.ledger ValidationEvent dataclass carries a default for it, so it is
#     "version-optional" at the constructor and must not count as a mismatch.
# --------------------------------------------------------------------------

@pytest.mark.parametrize("name", ALL_SHAPES)
def test_schema_required_matches_loader_required(name):
    cls = contracts.schemas._DATACLASS_FOR[name]
    loader_required = {
        f.name
        for f in dataclasses.fields(cls)
        if f.default is dataclasses.MISSING
        and f.default_factory is dataclasses.MISSING
    } - {"version"}
    schema_required = set(contracts.SCHEMAS[name]["required"]) - {"version"}
    assert schema_required == loader_required, (
        f"{name}: schema/loader required-field sets disagree "
        f"(schema-only={schema_required - loader_required}, "
        f"loader-only={loader_required - schema_required})"
    )


# --------------------------------------------------------------------------
# 4. version is the FIRST serialized key where hash-chain diffability needs it
#    (all event shapes + the manifest). Pins ordering, not just presence.
# --------------------------------------------------------------------------

VERSION_FIRST_SHAPES = [
    "vuln_manifest",
    "scenario_generated",
    "attack_executed",
    "scenario_aborted",
    "submission",
    "verification_result",
    "score_awarded",
    "attack_event",
    "isolation_report",
    "validation_event",
]


@pytest.mark.parametrize("name", VERSION_FIRST_SHAPES)
def test_version_is_first_serialized_key(name):
    """`version` leads the serialized dict so chained rows stay diffable."""
    obj = _loader(name)(fx.fresh(name))
    dumped = contracts.dump(obj)
    first_key = next(iter(dumped))
    assert first_key == "version", (
        f"{name}: first serialized key is {first_key!r}, expected 'version'"
    )


# --------------------------------------------------------------------------
# 5. The catalog is COMPLETE — every shape the spec names is exposed, and the
#    pre-existing ValidationEvent is referenced (not redefined) in the catalog.
# --------------------------------------------------------------------------

def test_catalog_exposes_all_thirteen_shapes():
    """contracts.SCHEMAS enumerates exactly the spec's persisted shapes."""
    assert set(contracts.SCHEMAS) == set(ALL_SHAPES), (
        "contracts.SCHEMAS must enumerate every persisted shape in the catalog"
    )


def test_validation_event_is_the_lab_ledger_shape_not_a_duplicate():
    """ValidationEvent(v1) already lives in lab/ledger.py — the catalog references
    it, it does not define a second incompatible shape (the fields must match)."""
    from lab.ledger import ValidationEvent as LedgerVE

    ledger_fields = {f for f in LedgerVE.__dataclass_fields__}
    catalog_fields = set(fx.validation_event())
    assert catalog_fields == ledger_fields, (
        "catalog ValidationEvent diverged from lab/ledger.py ValidationEvent"
    )
    # And the catalog loader accepts what the ledger dataclass emits.
    ve = LedgerVE(
        run_id="r", phase="web", check="up",
        status="not-implemented", evidence_ref=None, ts="2026-05-31T00:00:00+00:00",
    )
    obj = contracts.load_validation_event(ve.to_dict())
    assert obj is not None


# --------------------------------------------------------------------------
# 6. Every shape ships a JSON-Schema (stdlib-validated), and the canonical valid
#    instance is JSON-serializable (CI's contracts stage validates fixtures).
# --------------------------------------------------------------------------

@pytest.mark.parametrize("name", ALL_SHAPES)
def test_shape_json_schema_present_and_instance_serializable(name):
    schema = contracts.SCHEMAS[name]
    assert isinstance(schema, dict) and schema, f"{name}: missing JSON-Schema"
    # Round-trips through JSON without error (no non-serializable defaults).
    json.loads(json.dumps(fx.fresh(name)))
