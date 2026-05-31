"""T-101 — core contract invariants (FAIL-FIRST).

Pins three load-bearing contracts the whole scoring spine relies on:

  manifest_hash = sha256(canonical_json(victim, vulns, seed))
    * canonical_json = json.dumps(obj, sort_keys=True, separators=(",", ":"))
      — sorted keys, no whitespace; stable across dict-ordering and
      re-serialization.
    * same (victim, vulns, seed) -> same hash; any change -> different hash.

  correlation_id is minted from the Rng PORT (not uuid.uuid4()):
    * a fixed seed yields a DETERMINISTIC, REPLAYABLE sequence;
    * yet each draw is DISTINCT (two runs of the same seed never collide).
      This is the F-006 anchor.

  scoring idempotency key = (scenario_id, challenge_id, pillar, manifest_hash)
    * a 4-tuple in that order; a pass under seed A is not reused after a re-roll
      to seed B (different manifest_hash -> different key).

Locked API (proposed + pinned):
  contracts.canonical_json(obj) -> str
  contracts.manifest_hash(victim: dict, vulns: list, seed: int) -> str  (64 hex)
  contracts.idempotency_key(scenario_id, challenge_id, pillar, manifest_hash)
      -> tuple[str, str, str, str]
  contracts.mint_correlation_id(rng) -> str   (draws from the Rng port)
"""

from __future__ import annotations

import hashlib
import json

import conftest_t101 as fx

import adapters

# Plain imports — must go RED at collection until T-101 lands the packages.
import contracts
import ports  # noqa: F401  (imported to assert the package exists)

# --------------------------------------------------------------------------
# manifest_hash — canonical + stable
# --------------------------------------------------------------------------

def test_manifest_hash_matches_sha256_of_canonical_json():
    """The hash is exactly sha256 over canonical JSON of (victim, vulns, seed)."""
    victim = fx.victim()
    vulns = [fx.vuln()]
    seed = 1234
    expected = hashlib.sha256(
        contracts.canonical_json({"victim": victim, "vulns": vulns, "seed": seed}).encode()
    ).hexdigest()
    assert contracts.manifest_hash(victim, vulns, seed) == expected


def test_manifest_hash_stable_across_dict_ordering():
    """Re-ordering the keys of victim/vulns does NOT change the hash."""
    victim = fx.victim()
    vulns = [fx.vuln()]
    reordered_victim = dict(reversed(list(victim.items())))
    h1 = contracts.manifest_hash(victim, vulns, 1234)
    h2 = contracts.manifest_hash(reordered_victim, vulns, 1234)
    assert h1 == h2, "manifest_hash must be insensitive to dict key ordering"


def test_canonical_json_is_sorted_and_whitespace_free():
    """canonical_json pins the exact serialization the chain hashes over."""
    s = contracts.canonical_json({"b": 1, "a": 2})
    assert s == json.dumps({"a": 2, "b": 1}, sort_keys=True, separators=(",", ":"))
    assert " " not in s and "\n" not in s


def test_manifest_hash_changes_when_any_input_changes():
    """Any change to victim, vulns, or seed yields a different hash."""
    base = contracts.manifest_hash(fx.victim(), [fx.vuln()], 1234)
    assert contracts.manifest_hash(fx.victim(), [fx.vuln()], 9999) != base, "seed change"
    v = fx.victim()
    v["hostname"] = "other"
    assert contracts.manifest_hash(v, [fx.vuln()], 1234) != base, "victim change"
    vu = fx.vuln()
    vu["id"] = "v2"
    assert contracts.manifest_hash(fx.victim(), [vu], 1234) != base, "vulns change"


def test_manifest_hash_is_64_hex_chars():
    h = contracts.manifest_hash(fx.victim(), [fx.vuln()], 1234)
    assert len(h) == 64 and all(c in "0123456789abcdef" for c in h)


# --------------------------------------------------------------------------
# correlation_id — from the Rng port; deterministic-yet-distinct (F-006)
# --------------------------------------------------------------------------

def test_correlation_id_distinct_same_seed_yet_replayable():
    """Same seed -> identical, replayable sequence; each draw is distinct."""
    rng_a = adapters.SeededRng(seed=42)
    rng_b = adapters.SeededRng(seed=42)

    seq_a = [contracts.mint_correlation_id(rng_a) for _ in range(3)]
    seq_b = [contracts.mint_correlation_id(rng_b) for _ in range(3)]

    assert seq_a == seq_b, "same seed must replay an identical correlation_id sequence"
    assert len(set(seq_a)) == 3, "each draw within a run must be DISTINCT"


def test_correlation_id_differs_across_seeds():
    a = contracts.mint_correlation_id(adapters.SeededRng(seed=1))
    b = contracts.mint_correlation_id(adapters.SeededRng(seed=2))
    assert a != b, "different seeds should mint different correlation_ids"


def test_correlation_id_source_is_the_rng_port_not_uuid4():
    """mint_correlation_id draws from the injected Rng port — proven by the fact
    that a SeededRng makes it deterministic (uuid4() could never be)."""
    rng = adapters.SeededRng(seed=7)
    first = contracts.mint_correlation_id(rng)
    again = contracts.mint_correlation_id(adapters.SeededRng(seed=7))
    assert first == again, "id must be reproducible from the Rng seed (not uuid4)"


# --------------------------------------------------------------------------
# scoring idempotency key — (scenario_id, challenge_id, pillar, manifest_hash)
# --------------------------------------------------------------------------

def test_idempotency_key_tuple_shape_and_order():
    key = contracts.idempotency_key("scn-1", "ch-1", "attack", "deadbeef")
    assert key == ("scn-1", "ch-1", "attack", "deadbeef")
    assert len(key) == 4


def test_idempotency_key_distinguishes_seed_reroll():
    """A pass under manifest_hash A is NOT the same key after a re-roll to B."""
    key_a = contracts.idempotency_key("scn-1", "ch-1", "detect", "hashA")
    key_b = contracts.idempotency_key("scn-1", "ch-1", "detect", "hashB")
    assert key_a != key_b, "different manifest_hash must yield a different key (M5)"


def test_idempotency_key_same_inputs_same_key():
    """Same operation twice -> same key (idempotency)."""
    a = contracts.idempotency_key("scn-1", "ch-1", "mitigate", "h")
    b = contracts.idempotency_key("scn-1", "ch-1", "mitigate", "h")
    assert a == b
