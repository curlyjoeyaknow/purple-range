"""T-101 — the persisted-shape catalogue: frozen dataclasses + JSON-Schemas.

Charter #2 (versioned contracts): every persisted shape carries ``version:int``
as its FIRST declared field; new fields are additive; removals need a migration
ADR. This module is the single source of truth for the 13 persisted shapes the
whole scoring spine folds over.

For each shape we keep TWO co-located artefacts:

  * a ``@dataclass(frozen=True)`` whose field order is the serialized key order
    (``version`` leads) — the typed value object ``load_<shape>`` returns;
  * a JSON-Schema dict (stdlib-validated, NO ``jsonschema`` dependency) used to
    reject malformed input on ingest.

``ValidationEvent`` is NOT redefined here — it already lives in ``lab.ledger``
(T-004). The catalogue REFERENCES that dataclass so the two never diverge.

stdlib only.
"""

from __future__ import annotations

import copy
import dataclasses
from dataclasses import dataclass, fields
from typing import Any

from lab.ledger import ValidationEvent as _LedgerValidationEvent


class SchemaError(ValueError):
    """Raised when a payload violates its shape's contract.

    A ``ValueError`` subclass (charter pins it as ValueError/TypeError-derived)
    so callers can ``except SchemaError`` narrowly or ``except ValueError`` broadly.
    """


# --------------------------------------------------------------------------
# A tiny stdlib JSON-Schema validator. We support exactly the keywords our
# catalogue uses: type, required, properties, enum, items, and a `nullable`
# convenience (a property whose declared type OR null is acceptable). This is
# deliberately minimal — full JSON-Schema is a dependency we refuse (charter
# #3 / stdlib-only). Each `properties` entry is {"type": <py-type-name>, ...}.
# --------------------------------------------------------------------------

# JSON-Schema type name -> Python type(s). bool is excluded from "integer"
# because in Python ``bool`` is an ``int`` subclass and we do not want True to
# satisfy an integer field (a recurring data-quality footgun).
_TYPE_MAP = {
    "string": str,
    "integer": int,
    "number": (int, float),
    "boolean": bool,
    "object": dict,
    "array": list,
}


def _type_ok(value: Any, type_name: str) -> bool:
    if type_name == "null":
        return value is None
    py = _TYPE_MAP[type_name]
    if type_name == "integer":
        # reject bool masquerading as int
        return isinstance(value, int) and not isinstance(value, bool)
    if type_name == "number":
        return isinstance(value, py) and not isinstance(value, bool)
    return isinstance(value, py)


def _validate(data: Any, schema: dict, path: str = "") -> None:
    """Validate ``data`` against ``schema``; raise SchemaError on first breach."""
    if not isinstance(data, dict):
        raise SchemaError(f"{path or '<root>'}: expected object, got {type(data).__name__}")

    required = schema.get("required", [])
    for key in required:
        if key not in data:
            raise SchemaError(f"{path}{key}: required field missing")

    props = schema.get("properties", {})
    for key, spec in props.items():
        if key not in data:
            continue  # presence is enforced by `required`; optional fields may be absent
        value = data[key]
        _validate_value(value, spec, f"{path}{key}")


def _validate_value(value: Any, spec: dict, path: str) -> None:
    # Accepted types: a single "type" or a list of types (for nullable unions).
    types = spec.get("type")
    if types is not None:
        type_list = types if isinstance(types, list) else [types]
        if not any(_type_ok(value, t) for t in type_list):
            raise SchemaError(
                f"{path}: expected type {types!r}, got {type(value).__name__}"
            )

    if "enum" in spec and value not in spec["enum"]:
        raise SchemaError(f"{path}: {value!r} not in enum {spec['enum']!r}")

    # Nested object.
    if spec.get("type") == "object" and "properties" in spec:
        _validate(value, spec, f"{path}.")

    # Array items.
    if spec.get("type") == "array" and "items" in spec and isinstance(value, list):
        item_spec = spec["items"]
        for i, item in enumerate(value):
            if item_spec.get("type") == "object":
                _validate(item, item_spec, f"{path}[{i}].")
            else:
                _validate_value(item, item_spec, f"{path}[{i}]")


# --------------------------------------------------------------------------
# Frozen dataclasses — one per shape. Field order == serialized key order, and
# ``version`` is ALWAYS first. We use ``kw_only=True`` so a defaulted ``version``
# can lead while the rest stay required (same trick as lab.ledger.ValidationEvent).
# --------------------------------------------------------------------------


@dataclass(frozen=True, kw_only=True)
class Scenario:
    version: int
    id: str
    components: list
    net: str


@dataclass(frozen=True, kw_only=True)
class VulnManifest:
    version: int
    scenario_id: str
    seed: int
    manifest_hash: str
    generated_at: str
    clock_offset_s: int
    skew_budget_s: int
    victim: dict
    vulns: list
    scoring_oracle_ref: str


@dataclass(frozen=True, kw_only=True)
class OnboardSpec:
    version: int
    enroll: str
    enrollment_token_ref: str
    required_streams: list
    network_visibility: str
    heartbeat_deadline_s: int


@dataclass(frozen=True, kw_only=True)
class DetectionRule:
    version: int
    id: str
    mitre: str
    store: str
    language: str
    query: str
    expected_min_hits: int
    max_false_positives: int
    skew_budget_s: int
    ground_truth_ref: str
    calibration: dict


@dataclass(frozen=True, kw_only=True)
class AttackEvent:
    version: int
    run_id: str
    seed: int
    playbook_id: str
    step: int
    attack_technique: str
    tactic: str
    target_ip: str
    actor_ip: str
    ts_start: str
    ts_end: str
    outcome: str
    evidence: dict
    expected_signal: list
    correlation_id: str


@dataclass(frozen=True, kw_only=True)
class IsolationReport:
    version: int
    host_fw_egress_blocked_v4: bool
    host_fw_egress_blocked_v6: bool
    docker_bridge_egress_blocked: bool
    dns_egress_blocked: bool
    tripwire_armed: bool
    tripwire_egress_count: int
    planes_covered: list
    guest_probe_internet_unreachable: bool | None
    guest_probe_labnet_reachable: bool | None
    nat_detached: bool
    bridged_present: bool
    route_to_internet: bool
    target_cidr: str
    checked_at: str


@dataclass(frozen=True, kw_only=True)
class ScenarioGenerated:
    version: int
    seq: int
    prev_hash: str
    occurred_at: str
    seed: int
    manifest_ref: str
    manifest_hash: str
    clock_offset_s: int
    correlation_id: str


@dataclass(frozen=True, kw_only=True)
class AttackExecuted:
    version: int
    seq: int
    prev_hash: str
    occurred_at: str
    actor: str
    ttp: str
    target: str
    outcome: str
    correlation_id: str
    causation_id: str


@dataclass(frozen=True, kw_only=True)
class ScenarioAborted:
    version: int
    seq: int
    prev_hash: str
    occurred_at: str
    reason: str
    last_good_seq: int
    correlation_id: str
    causation_id: str


@dataclass(frozen=True, kw_only=True)
class Submission:
    version: int
    seq: int
    prev_hash: str
    occurred_at: str
    pillar: str
    evidence: dict
    manifest_hash: str
    correlation_id: str
    causation_id: str


@dataclass(frozen=True, kw_only=True)
class VerificationResult:
    version: int
    seq: int
    prev_hash: str
    occurred_at: str
    oracle: str
    passed: bool
    matched_ttp: str
    manifest_ref: str
    correlation_id: str
    causation_id: str


@dataclass(frozen=True, kw_only=True)
class ScoreAwarded:
    version: int
    seq: int
    prev_hash: str
    occurred_at: str
    pillar: str
    points: int
    verification_ref: str
    manifest_ref: str
    manifest_hash: str
    correlation_id: str
    causation_id: str


# --------------------------------------------------------------------------
# JSON-Schemas. Required == every field on the canonical valid instance, so a
# dropped required field is rejected. Enums + nullable unions are encoded where
# the malformed cases (conftest_t101.MALFORMED_CASES) exercise them.
# --------------------------------------------------------------------------

_PILLAR_ENUM = ["attack", "detect", "mitigate"]
_OUTCOME_ENUM = ["success", "blocked", "partial"]
_COMPONENT_KIND_ENUM = ["VM", "CONTAINER"]

# --------------------------------------------------------------------------
# Nested sub-schemas for the compound shapes. Declared here so the (already
# nested-aware) validator engine actually validates nested containers instead
# of waving through a bare {"type": "array"} / {"type": "object"}. Each is the
# canonical shape (Component / victim / vuln / the
# calibration + detect + mitigate sub-objects).
# --------------------------------------------------------------------------

# Scenario.components[] — a Component (ARCHITECTURE: name, kind:VM|CONTAINER,
# image, ram_mb, cpus, ip, promisc:bool).
_COMPONENT_SCHEMA: dict = {
    "type": "object",
    "required": ["name", "kind", "image", "ram_mb", "cpus", "ip", "promisc"],
    "properties": {
        "name": {"type": "string"},
        "kind": {"type": "string", "enum": _COMPONENT_KIND_ENUM},
        "image": {"type": "string"},
        "ram_mb": {"type": "integer"},
        "cpus": {"type": "integer"},
        "ip": {"type": "string"},
        "promisc": {"type": "boolean"},
    },
}

# VulnManifest.victim — { ip, hostname, platform, services[] }.
_VICTIM_SCHEMA: dict = {
    "type": "object",
    "required": ["ip", "hostname", "platform", "services"],
    "properties": {
        "ip": {"type": "string"},
        "hostname": {"type": "string"},
        "platform": {"type": "string"},
        "services": {"type": "array", "items": {"type": "string"}},
    },
}

# The F1 calibration block — { correct_ref, match_all_ref, match_none_ref }.
# Shared verbatim by vuln.detect and DetectionRule (both ship calibration).
_CALIBRATION_SCHEMA: dict = {
    "type": "object",
    "required": ["correct_ref", "match_all_ref", "match_none_ref"],
    "properties": {
        "correct_ref": {"type": "string"},
        "match_all_ref": {"type": "string"},
        "match_none_ref": {"type": "string"},
    },
}

# vuln.detect — the DETECT oracle block (incl. the mandatory calibration F1).
_VULN_DETECT_SCHEMA: dict = {
    "type": "object",
    "required": [
        "expected_log_source", "expected_signal", "expected_min_hits",
        "max_false_positives", "skew_budget_s", "calibration",
    ],
    "properties": {
        "expected_log_source": {"type": "string"},
        "expected_signal": {"type": "string"},
        "expected_min_hits": {"type": "integer"},
        "max_false_positives": {"type": "integer"},
        "skew_budget_s": {"type": "integer"},
        "calibration": _CALIBRATION_SCHEMA,
    },
}

# vuln.mitigate — the MITIGATE block (incl. the mandatory deny_all_ref F2).
_VULN_MITIGATE_SCHEMA: dict = {
    "type": "object",
    "required": ["control", "verify_check", "service_probe", "deny_all_ref"],
    "properties": {
        "control": {"type": "string"},
        "verify_check": {"type": "string"},
        "service_probe": {"type": "string"},
        "deny_all_ref": {"type": "string"},
    },
}

# vuln.attack — { ttp:[ATT&CK], proof_signal }.
_VULN_ATTACK_SCHEMA: dict = {
    "type": "object",
    "required": ["ttp", "proof_signal"],
    "properties": {
        "ttp": {"type": "array", "items": {"type": "string"}},
        "proof_signal": {"type": "string"},
    },
}

# VulnManifest.vulns[] — one vuln/oracle entry. secgen_hint/secgen_solution/
# cybok_ref are optional nullable hints (present on the canonical instance but
# not load-bearing), so they are typed-when-present, not required.
_VULN_SCHEMA: dict = {
    "type": "object",
    "required": ["id", "cve", "access", "attack", "detect", "mitigate"],
    "properties": {
        "id": {"type": "string"},
        "cve": {"type": "string"},
        "access": {"type": "string", "enum": ["remote", "local"]},
        "planted_value": {"type": "string"},
        "attack": _VULN_ATTACK_SCHEMA,
        "detect": _VULN_DETECT_SCHEMA,
        "mitigate": _VULN_MITIGATE_SCHEMA,
        "secgen_hint": {"type": ["string", "null"]},
        "secgen_solution": {"type": ["string", "null"]},
        "cybok_ref": {"type": ["string", "null"]},
    },
}

SCHEMAS: dict[str, dict] = {
    "scenario": {
        "type": "object",
        "required": ["version", "id", "components", "net"],
        "properties": {
            "version": {"type": "integer"},
            "id": {"type": "string"},
            "components": {"type": "array", "items": _COMPONENT_SCHEMA},
            "net": {"type": "string"},
        },
    },
    "vuln_manifest": {
        "type": "object",
        "required": [
            "version", "scenario_id", "seed", "manifest_hash", "generated_at",
            "clock_offset_s", "skew_budget_s", "victim", "vulns", "scoring_oracle_ref",
        ],
        "properties": {
            "version": {"type": "integer"},
            "scenario_id": {"type": "string"},
            "seed": {"type": "integer"},
            "manifest_hash": {"type": "string"},
            "generated_at": {"type": "string"},
            "clock_offset_s": {"type": "integer"},
            "skew_budget_s": {"type": "integer"},
            "victim": _VICTIM_SCHEMA,
            "vulns": {"type": "array", "items": _VULN_SCHEMA},
            "scoring_oracle_ref": {"type": "string"},
        },
    },
    "onboard_spec": {
        "type": "object",
        "required": [
            "version", "enroll", "enrollment_token_ref", "required_streams",
            "network_visibility", "heartbeat_deadline_s",
        ],
        "properties": {
            "version": {"type": "integer"},
            "enroll": {"type": "string"},
            "enrollment_token_ref": {"type": "string"},
            "required_streams": {"type": "array"},
            "network_visibility": {"type": "string"},
            "heartbeat_deadline_s": {"type": "integer"},
        },
    },
    "detection_rule": {
        "type": "object",
        "required": [
            "version", "id", "mitre", "store", "language", "query",
            "expected_min_hits", "max_false_positives", "skew_budget_s",
            "ground_truth_ref", "calibration",
        ],
        "properties": {
            "version": {"type": "integer"},
            "id": {"type": "string"},
            "mitre": {"type": "string"},
            "store": {"type": "string"},
            "language": {"type": "string", "enum": ["eql", "lucene", "suricata", "spl"]},
            "query": {"type": "string"},
            "expected_min_hits": {"type": "integer"},
            "max_false_positives": {"type": "integer"},
            "skew_budget_s": {"type": "integer"},
            "ground_truth_ref": {"type": "string"},
            "calibration": _CALIBRATION_SCHEMA,
        },
    },
    "attack_event": {
        "type": "object",
        "required": [
            "version", "run_id", "seed", "playbook_id", "step", "attack_technique",
            "tactic", "target_ip", "actor_ip", "ts_start", "ts_end", "outcome",
            "evidence", "expected_signal", "correlation_id",
        ],
        "properties": {
            "version": {"type": "integer"},
            "run_id": {"type": "string"},
            "seed": {"type": "integer"},
            "playbook_id": {"type": "string"},
            "step": {"type": "integer"},
            "attack_technique": {"type": "string"},
            "tactic": {"type": "string"},
            "target_ip": {"type": "string"},
            "actor_ip": {"type": "string"},
            "ts_start": {"type": "string"},
            "ts_end": {"type": "string"},
            "outcome": {"type": "string", "enum": _OUTCOME_ENUM},
            "evidence": {"type": "object"},
            "expected_signal": {"type": "array"},
            "correlation_id": {"type": "string"},
        },
    },
    "isolation_report": {
        "type": "object",
        "required": [
            "version", "host_fw_egress_blocked_v4", "host_fw_egress_blocked_v6",
            "docker_bridge_egress_blocked", "dns_egress_blocked", "tripwire_armed",
            "tripwire_egress_count", "planes_covered", "guest_probe_internet_unreachable",
            "guest_probe_labnet_reachable", "nat_detached", "bridged_present",
            "route_to_internet", "target_cidr", "checked_at",
        ],
        "properties": {
            "version": {"type": "integer"},
            "host_fw_egress_blocked_v4": {"type": "boolean"},
            "host_fw_egress_blocked_v6": {"type": "boolean"},
            "docker_bridge_egress_blocked": {"type": "boolean"},
            "dns_egress_blocked": {"type": "boolean"},
            "tripwire_armed": {"type": "boolean"},
            "tripwire_egress_count": {"type": "integer"},
            "planes_covered": {"type": "array"},
            "guest_probe_internet_unreachable": {"type": ["boolean", "null"]},
            "guest_probe_labnet_reachable": {"type": ["boolean", "null"]},
            "nat_detached": {"type": "boolean"},
            "bridged_present": {"type": "boolean"},
            "route_to_internet": {"type": "boolean"},
            "target_cidr": {"type": "string"},
            "checked_at": {"type": "string"},
        },
    },
    "validation_event": {
        "type": "object",
        "required": ["version", "run_id", "phase", "check", "status", "evidence_ref", "ts"],
        "properties": {
            "version": {"type": "integer"},
            "run_id": {"type": "string"},
            "phase": {"type": ["string", "null"]},
            "check": {"type": "string"},
            "status": {"type": "string"},
            "evidence_ref": {"type": ["string", "null"]},
            "ts": {"type": "string"},
        },
    },
    "scenario_generated": {
        "type": "object",
        "required": [
            "version", "seq", "prev_hash", "occurred_at", "seed", "manifest_ref",
            "manifest_hash", "clock_offset_s", "correlation_id",
        ],
        "properties": {
            "version": {"type": "integer"},
            "seq": {"type": "integer"},
            "prev_hash": {"type": "string"},
            "occurred_at": {"type": "string"},
            "seed": {"type": "integer"},
            "manifest_ref": {"type": "string"},
            "manifest_hash": {"type": "string"},
            "clock_offset_s": {"type": "integer"},
            "correlation_id": {"type": "string"},
        },
    },
    "attack_executed": {
        "type": "object",
        "required": [
            "version", "seq", "prev_hash", "occurred_at", "actor", "ttp",
            "target", "outcome", "correlation_id", "causation_id",
        ],
        "properties": {
            "version": {"type": "integer"},
            "seq": {"type": "integer"},
            "prev_hash": {"type": "string"},
            "occurred_at": {"type": "string"},
            "actor": {"type": "string"},
            "ttp": {"type": "string"},
            "target": {"type": "string"},
            "outcome": {"type": "string", "enum": _OUTCOME_ENUM},
            "correlation_id": {"type": "string"},
            "causation_id": {"type": "string"},
        },
    },
    "scenario_aborted": {
        "type": "object",
        "required": [
            "version", "seq", "prev_hash", "occurred_at", "reason",
            "last_good_seq", "correlation_id", "causation_id",
        ],
        "properties": {
            "version": {"type": "integer"},
            "seq": {"type": "integer"},
            "prev_hash": {"type": "string"},
            "occurred_at": {"type": "string"},
            "reason": {"type": "string"},
            "last_good_seq": {"type": "integer"},
            "correlation_id": {"type": "string"},
            "causation_id": {"type": "string"},
        },
    },
    "submission": {
        "type": "object",
        "required": [
            "version", "seq", "prev_hash", "occurred_at", "pillar", "evidence",
            "manifest_hash", "correlation_id", "causation_id",
        ],
        "properties": {
            "version": {"type": "integer"},
            "seq": {"type": "integer"},
            "prev_hash": {"type": "string"},
            "occurred_at": {"type": "string"},
            "pillar": {"type": "string", "enum": _PILLAR_ENUM},
            "evidence": {"type": "object"},
            "manifest_hash": {"type": "string"},
            "correlation_id": {"type": "string"},
            "causation_id": {"type": "string"},
        },
    },
    "verification_result": {
        "type": "object",
        "required": [
            "version", "seq", "prev_hash", "occurred_at", "oracle", "passed",
            "matched_ttp", "manifest_ref", "correlation_id", "causation_id",
        ],
        "properties": {
            "version": {"type": "integer"},
            "seq": {"type": "integer"},
            "prev_hash": {"type": "string"},
            "occurred_at": {"type": "string"},
            "oracle": {"type": "string"},
            "passed": {"type": "boolean"},
            "matched_ttp": {"type": "string"},
            "manifest_ref": {"type": "string"},
            "correlation_id": {"type": "string"},
            "causation_id": {"type": "string"},
        },
    },
    "score_awarded": {
        "type": "object",
        "required": [
            "version", "seq", "prev_hash", "occurred_at", "pillar", "points",
            "verification_ref", "manifest_ref", "manifest_hash",
            "correlation_id", "causation_id",
        ],
        "properties": {
            "version": {"type": "integer"},
            "seq": {"type": "integer"},
            "prev_hash": {"type": "string"},
            "occurred_at": {"type": "string"},
            "pillar": {"type": "string", "enum": _PILLAR_ENUM},
            "points": {"type": "integer"},
            "verification_ref": {"type": "string"},
            "manifest_ref": {"type": "string"},
            "manifest_hash": {"type": "string"},
            "correlation_id": {"type": "string"},
            "causation_id": {"type": "string"},
        },
    },
}


# Shape-name -> dataclass. ValidationEvent maps to the lab.ledger class (NOT a
# duplicate), so the catalogue references the single existing definition.
_DATACLASS_FOR: dict[str, type] = {
    "scenario": Scenario,
    "vuln_manifest": VulnManifest,
    "onboard_spec": OnboardSpec,
    "detection_rule": DetectionRule,
    "attack_event": AttackEvent,
    "isolation_report": IsolationReport,
    "validation_event": _LedgerValidationEvent,
    "scenario_generated": ScenarioGenerated,
    "attack_executed": AttackExecuted,
    "scenario_aborted": ScenarioAborted,
    "submission": Submission,
    "verification_result": VerificationResult,
    "score_awarded": ScoreAwarded,
}


def _load(name: str, data: Any) -> Any:
    """Validate ``data`` against the ``name`` schema, return the frozen instance."""
    if not isinstance(data, dict):
        raise SchemaError(f"{name}: expected a dict, got {type(data).__name__}")
    _validate(data, SCHEMAS[name])
    cls = _DATACLASS_FOR[name]
    # Build kwargs only from the dataclass's own fields so an unexpected extra
    # key can't reach the constructor (it was already schema-checked; this is
    # belt-and-braces against a TypeError leaking out as a non-SchemaError).
    field_names = {f.name for f in fields(cls)}
    kwargs = {k: v for k, v in data.items() if k in field_names}
    try:
        return cls(**kwargs)
    except TypeError as exc:  # missing/extra constructor arg
        raise SchemaError(f"{name}: {exc}") from exc


def dump(obj: Any) -> dict:
    """Serialize a frozen contract instance back to a plain dict.

    Lossless and order-stable: ``dataclasses.fields`` preserves declaration
    order, so ``version`` leads and ``load(dump(x)) == load(x)``.

    Container-typed values (lists/dicts) are DEEP-COPIED. ``@dataclass(frozen=
    True)`` freezes attribute *rebinding* but NOT the contents of a mutable a
    field already points at — so returning the instance's own list/dict by
    reference would let a caller mutate the "frozen" contract through its dump
    (``dump(x)["components"].append(...)`` reaching back into ``x``). Copying
    severs that alias so a dumped instance is an independent snapshot.
    """
    if not dataclasses.is_dataclass(obj):
        raise TypeError(f"dump() expects a contract dataclass, got {type(obj).__name__}")
    out = {}
    for f in fields(obj):
        value = getattr(obj, f.name)
        if isinstance(value, (list, dict)):
            value = copy.deepcopy(value)
        out[f.name] = value
    return out


# Public loaders, one per shape (``load_<shape>``), generated from the registry
# so a new shape is wired in exactly one place.
def _make_loader(name: str):
    def loader(data: dict):
        return _load(name, data)

    loader.__name__ = f"load_{name}"
    loader.__qualname__ = f"load_{name}"
    loader.__doc__ = f"Validate and load a `{name}` payload into its frozen dataclass."
    return loader


load_scenario = _make_loader("scenario")
load_vuln_manifest = _make_loader("vuln_manifest")
load_onboard_spec = _make_loader("onboard_spec")
load_detection_rule = _make_loader("detection_rule")
load_attack_event = _make_loader("attack_event")
load_isolation_report = _make_loader("isolation_report")
load_validation_event = _make_loader("validation_event")
load_scenario_generated = _make_loader("scenario_generated")
load_attack_executed = _make_loader("attack_executed")
load_scenario_aborted = _make_loader("scenario_aborted")
load_submission = _make_loader("submission")
load_verification_result = _make_loader("verification_result")
load_score_awarded = _make_loader("score_awarded")
