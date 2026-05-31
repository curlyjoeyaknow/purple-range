"""Shared T-101 fixtures: the canonical VALID instance per persisted shape.

Imported by the T-101 contract test modules. Kept out of the root ``conftest.py``
so it does not perturb the existing 133 tests; each T-101 module imports the
builders it needs directly.

Every builder returns a *minimally-valid* dict for one shape — the smallest
payload ``contracts.load_<shape>()`` must accept. Tests mutate copies of these
(drop ``version``, corrupt a field) to drive the rejection paths. The builders
live here, not inline, so the "valid baseline" is single-sourced: if a required
field changes, it changes in exactly one place and every rejection test that
derived from it stays honest.
"""

from __future__ import annotations

import copy


# --------------------------------------------------------------------------
# Valid-instance builders, one per persisted shape. version is ALWAYS present
# and is the contract's first declared field.
# --------------------------------------------------------------------------

def scenario() -> dict:
    return {
        "version": 1,
        "id": "scn-001",
        "components": [
            {
                "name": "victim-web",
                "kind": "CONTAINER",
                "image": "vulhub/cve@sha256:" + "a" * 64,
                "ram_mb": 512,
                "cpus": 1,
                "ip": "192.168.56.10",
                "promisc": False,
            }
        ],
        "net": "192.168.56.0/24",
    }


def victim() -> dict:
    return {
        "ip": "192.168.56.10",
        "hostname": "victim-web",
        "platform": "linux",
        "services": ["http"],
    }


def vuln() -> dict:
    return {
        "id": "v1",
        "cve": "CVE-2024-0001",
        "access": "remote",
        "planted_value": "FLAG{x}",
        "attack": {"ttp": ["T1190"], "proof_signal": "shell"},
        "detect": {
            "expected_log_source": "suricata",
            "expected_signal": "alert",
            "expected_min_hits": 1,
            "max_false_positives": 0,
            "skew_budget_s": 5,
            "calibration": {
                "correct_ref": "rule-correct",
                "match_all_ref": "rule-all",
                "match_none_ref": "rule-none",
            },
        },
        "mitigate": {
            "control": "patch",
            "verify_check": "reattack",
            "service_probe": "GET /app",
            "deny_all_ref": "deny-all-mitigation",
        },
        "secgen_hint": None,
        "secgen_solution": None,
        "cybok_ref": None,
    }


def vuln_manifest() -> dict:
    return {
        "version": 2,
        "scenario_id": "scn-001",
        "seed": 1234,
        "manifest_hash": "0" * 64,
        "generated_at": "2026-05-31T00:00:00+00:00",
        "clock_offset_s": 0,
        "skew_budget_s": 5,
        "victim": victim(),
        "vulns": [vuln()],
        "scoring_oracle_ref": "oracle-1",
    }


def onboard_spec() -> dict:
    return {
        "version": 1,
        "enroll": "elastic-agent-vs-fleet",
        "enrollment_token_ref": "tok-1",
        "required_streams": ["process", "network", "auth", "file"],
        "network_visibility": "span_port",
        "heartbeat_deadline_s": 120,
    }


def detection_rule() -> dict:
    return {
        "version": 2,
        "id": "rule-1",
        "mitre": "T1190",
        "store": "elastic",
        "language": "eql",
        "query": "process where true",
        "expected_min_hits": 1,
        "max_false_positives": 0,
        "skew_budget_s": 5,
        "ground_truth_ref": "gt-1",
        "calibration": {
            "correct_ref": "rule-correct",
            "match_all_ref": "rule-all",
            "match_none_ref": "rule-none",
        },
    }


def attack_event() -> dict:
    return {
        "version": 1,
        "run_id": "run-1",
        "seed": 1234,
        "playbook_id": "pb-1",
        "step": 0,
        "attack_technique": "T1190",
        "tactic": "initial-access",
        "target_ip": "192.168.56.10",
        "actor_ip": "192.168.56.5",
        "ts_start": "2026-05-31T00:00:00+00:00",
        "ts_end": "2026-05-31T00:00:01+00:00",
        "outcome": "success",
        "evidence": {"stdout": "..."},
        "expected_signal": ["alert"],
        "correlation_id": "corr-1",
    }


def isolation_report() -> dict:
    return {
        "version": 2,
        "host_fw_egress_blocked_v4": True,
        "host_fw_egress_blocked_v6": True,
        "docker_bridge_egress_blocked": True,
        "dns_egress_blocked": True,
        "tripwire_armed": True,
        "tripwire_egress_count": 0,
        "planes_covered": ["vboxnet", "docker_bridge"],
        "guest_probe_internet_unreachable": None,
        "guest_probe_labnet_reachable": None,
        "nat_detached": True,
        "bridged_present": False,
        "route_to_internet": False,
        "target_cidr": "192.168.56.0/24",
        "checked_at": "2026-05-31T00:00:00+00:00",
    }


def validation_event() -> dict:
    return {
        "version": 1,
        "run_id": "run-1",
        "phase": "web",
        "check": "up",
        "status": "not-implemented",
        "evidence_ref": None,
        "ts": "2026-05-31T00:00:00+00:00",
    }


# --------------------------------------------------------------------------
# Event shapes (the spine of the spine). Each carries seq/prev_hash/occurred_at.
# --------------------------------------------------------------------------

def scenario_generated() -> dict:
    return {
        "version": 2,
        "seq": 0,
        "prev_hash": "0" * 64,
        "occurred_at": "2026-05-31T00:00:00+00:00",
        "seed": 1234,
        "manifest_ref": "manifest-1",
        "manifest_hash": "0" * 64,
        "clock_offset_s": 0,
        "correlation_id": "corr-1",
    }


def attack_executed() -> dict:
    return {
        "version": 1,
        "seq": 1,
        "prev_hash": "a" * 64,
        "occurred_at": "2026-05-31T00:00:01+00:00",
        "actor": "auto",
        "ttp": "T1190",
        "target": "192.168.56.10",
        "outcome": "success",
        "correlation_id": "corr-1",
        "causation_id": "corr-1",
    }


def scenario_aborted() -> dict:
    return {
        "version": 1,
        "seq": 2,
        "prev_hash": "b" * 64,
        "occurred_at": "2026-05-31T00:00:02+00:00",
        "reason": "orchestrator_restart",
        "last_good_seq": 1,
        "correlation_id": "corr-1",
        "causation_id": "corr-1",
    }


def submission() -> dict:
    return {
        "version": 1,
        "seq": 3,
        "prev_hash": "c" * 64,
        "occurred_at": "2026-05-31T00:00:03+00:00",
        "pillar": "attack",
        "evidence": {"ttp": "T1190"},
        "manifest_hash": "0" * 64,
        "correlation_id": "corr-1",
        "causation_id": "corr-1",
    }


def verification_result() -> dict:
    return {
        "version": 2,
        "seq": 4,
        "prev_hash": "d" * 64,
        "occurred_at": "2026-05-31T00:00:04+00:00",
        "oracle": "manifest",
        "passed": True,
        "matched_ttp": "T1190",
        "manifest_ref": "manifest-1",
        "correlation_id": "corr-1",
        "causation_id": "corr-1",
    }


def score_awarded() -> dict:
    return {
        "version": 2,
        "seq": 5,
        "prev_hash": "e" * 64,
        "occurred_at": "2026-05-31T00:00:05+00:00",
        "pillar": "attack",
        "points": 10,
        "verification_ref": "4",
        "manifest_ref": "manifest-1",
        "manifest_hash": "0" * 64,
        "correlation_id": "corr-1",
        "causation_id": "corr-1",
    }


# --------------------------------------------------------------------------
# Registry: shape-name -> (valid builder, loader attribute name on `contracts`).
# Drives the parametrized version / round-trip / malformed tests so a new shape
# is added in ONE place.
# --------------------------------------------------------------------------

PERSISTED_SHAPES = {
    "scenario": (scenario, "load_scenario"),
    "vuln_manifest": (vuln_manifest, "load_vuln_manifest"),
    "onboard_spec": (onboard_spec, "load_onboard_spec"),
    "detection_rule": (detection_rule, "load_detection_rule"),
    "attack_event": (attack_event, "load_attack_event"),
    "isolation_report": (isolation_report, "load_isolation_report"),
    "validation_event": (validation_event, "load_validation_event"),
    "scenario_generated": (scenario_generated, "load_scenario_generated"),
    "attack_executed": (attack_executed, "load_attack_executed"),
    "scenario_aborted": (scenario_aborted, "load_scenario_aborted"),
    "submission": (submission, "load_submission"),
    "verification_result": (verification_result, "load_verification_result"),
    "score_awarded": (score_awarded, "load_score_awarded"),
}

# A representative malformed mutation per shape: (description, mutator). Each
# mutator takes a fresh valid dict and breaks ONE thing (wrong type / bad enum /
# missing required field). load_* MUST reject every one of these.
def _drop(key):
    def m(d):
        d.pop(key, None)
        return d
    return m


def _set(key, value):
    def m(d):
        d[key] = value
        return d
    return m


MALFORMED_CASES = {
    "scenario": ("net wrong type", _set("net", 123)),
    "vuln_manifest": ("seed wrong type", _set("seed", "not-an-int")),
    "onboard_spec": ("heartbeat_deadline_s missing", _drop("heartbeat_deadline_s")),
    "detection_rule": ("language bad enum", _set("language", "klingon")),
    "attack_event": ("outcome bad enum", _set("outcome", "exploded")),
    "isolation_report": ("tripwire_egress_count wrong type", _set("tripwire_egress_count", "zero")),
    "validation_event": ("check missing", _drop("check")),
    "scenario_generated": ("manifest_hash missing", _drop("manifest_hash")),
    "attack_executed": ("outcome bad enum", _set("outcome", "nope")),
    "scenario_aborted": ("last_good_seq wrong type", _set("last_good_seq", "x")),
    "submission": ("pillar bad enum", _set("pillar", "purple")),
    "verification_result": ("passed wrong type", _set("passed", "yes")),
    "score_awarded": ("points wrong type", _set("points", "ten")),
}


# NESTED malformed cases — at least one per COMPOUND shape, exercising the
# nested-container validation that bare {"type":"array"}/{"type":"object"}
# schemas used to wave through. Each entry is (shape, description, mutator) and
# load_<shape> MUST reject it. These are ADDITIVE to MALFORMED_CASES (which
# stays one-per-shape and is NOT weakened).
NESTED_MALFORMED_CASES = [
    # scenario.components[] — a Component with wrong-typed name, bad kind enum,
    # and a non-bool promisc (the exact repro from the internal review).
    (
        "scenario",
        "component name/kind/promisc all malformed",
        _set("components", [{"name": 123, "kind": "NONSENSE", "promisc": "not-a-bool"}]),
    ),
    # scenario.components[] — a single nested field wrong-typed (ram_mb str).
    (
        "scenario",
        "component ram_mb wrong type",
        lambda d: (d["components"][0].__setitem__("ram_mb", "lots"), d)[1],
    ),
    # vuln_manifest.victim — victim.ip wrong type (the repro: {"ip": 999}).
    (
        "vuln_manifest",
        "victim ip wrong type",
        _set("victim", {"ip": 999, "hostname": "h", "platform": "linux", "services": ["http"]}),
    ),
    # vuln_manifest.vulns[] — an array element that is not even an object.
    (
        "vuln_manifest",
        "vulns element not a dict",
        _set("vulns", ["not-a-dict"]),
    ),
    # vuln_manifest.vulns[].detect.calibration — a missing F1 calibration ref.
    (
        "vuln_manifest",
        "vuln detect.calibration missing a ref",
        lambda d: (d["vulns"][0]["detect"]["calibration"].pop("correct_ref"), d)[1],
    ),
    # vuln_manifest.vulns[].mitigate.deny_all_ref — missing F2 negative fixture.
    (
        "vuln_manifest",
        "vuln mitigate.deny_all_ref missing",
        lambda d: (d["vulns"][0]["mitigate"].pop("deny_all_ref"), d)[1],
    ),
    # detection_rule.calibration — wrong-typed nested ref.
    (
        "detection_rule",
        "calibration.correct_ref wrong type",
        lambda d: (d["calibration"].__setitem__("correct_ref", 7), d)[1],
    ),
]


def fresh(name: str) -> dict:
    """A deep copy of the canonical valid instance for ``name``."""
    return copy.deepcopy(PERSISTED_SHAPES[name][0]())
