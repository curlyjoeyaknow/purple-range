"""T-110 — the shared hash-chain math for the EventStore adapters.

ADR-0007 pins ONE chain discipline that BOTH the SQLite production adapter and
the InMemory fake must compute byte-identically (§4a conformance). To make that
agreement structural rather than aspirational, the integrity primitives live
here, in one place, and both adapters call them. If the fake and the real
adapter ever diverge on a ``row_hash`` or a ``verify_chain`` verdict, it is
because one of them stopped going through this module — not because the math
drifted.

What this module owns (and nothing else):

  * ``GENESIS_SENTINEL`` — the chosen ``"0"*64`` "no predecessor" token (§1).
  * ``framed_row_hash`` — the §0 framed sha256
    ``sha256(prev_hash_bytes + b"\\x00" + canonical_bytes)``.
  * ``canonical_payload`` — the no-NaN canonical-JSON STRING the store persists
    in ``payload`` and hashes over (the §0 ``allow_nan=False`` precondition,
    enforced at the store's own call site without editing ``contracts``).
  * ``chain_batch`` — the authoritative §1a stamping: given the current tip and
    a batch of frozen events, assign ``seq``/``prev_hash``, reject non-finite /
    non-JSON-primitive evidence, and produce the persisted rows.
  * ``verify_rows`` — the §2 verdict over already-persisted rows, re-hashing the
    STORED ``payload`` bytes (never a re-parsed object).

stdlib only.
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

import contracts

# §1: genesis "no predecessor" sentinel — a chosen fixed 64-hex token, NOT the
# sha256 of empty input (that is e3b0c4…). Picked because it is fixed-width and
# never naturally produced, so an empty-store verify is trivially True and the
# first row chains off a constant rather than off "nothing".
GENESIS_SENTINEL = "0" * 64

_log = logging.getLogger("purple_range.event_store")


def framed_row_hash(prev_hash: str, event_type: str, canonical_bytes: bytes) -> str:
    """The §0 FRAMED row hash, now a 3-field frame (ADR-0007 Addendum 1 / Q-020).

    ``sha256(prev_hash_bytes + 0x00 + event_type_bytes + 0x00 + canonical_bytes)``.
    The one-byte NUL separators cannot occur in a hex token, in a snake_case
    ``event_type`` (derived from a Python identifier, NUL-free), or in
    ``separators=(",",":")`` canonical JSON, so the input is self-delimiting and
    a future hash-encoding change is loudly different bytes, not a silent
    chain corruption (ADR §0 rationale). ``event_type`` is encoded ``utf-8`` (not
    ``ascii``) so a future non-ASCII event class name cannot raise here (critic
    🟡-1).
    """
    return hashlib.sha256(
        prev_hash.encode("ascii") + b"\x00"
        + event_type.encode("utf-8") + b"\x00"
        + canonical_bytes
    ).hexdigest()


def _assert_json_primitive(value: Any) -> None:
    """Enforce the §0 evidence value-domain: JSON primitives, string keys, finite.

    Rejects non-finite floats (NaN/Inf/-Inf) and any non-JSON Python object
    (sets, bytes, datetimes, non-string dict keys) BEFORE it can enter the
    hashed bytes. Raises ``ValueError`` — a clean precondition violation the
    batch transaction rolls back on (§4 all-or-nothing).
    """
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            raise ValueError(
                "non-finite float (NaN/Inf) is not a valid chained value "
                "(ADR-0007 §0: the chain requires allow_nan=False semantics)"
            )
        return
    if isinstance(value, (str, int, bool)) or value is None:
        return
    if isinstance(value, (list, tuple)):
        for item in value:
            _assert_json_primitive(item)
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError(
                    f"non-string dict key {key!r} is out of the JSON value-domain "
                    "(ADR-0007 §0)"
                )
            _assert_json_primitive(item)
        return
    raise ValueError(
        f"value of type {type(value).__name__} is not a JSON primitive "
        "(ADR-0007 §0: evidence must be JSON-primitive-only)"
    )


def canonical_payload(row: dict) -> str:
    """The canonical-JSON STRING persisted in ``payload`` and hashed over.

    Layers the §0 no-NaN / JSON-primitive precondition on top of the locked
    ``contracts.canonical_json`` WITHOUT editing ``contracts``: we validate the
    value-domain first (raising on non-finite floats / non-JSON objects), then
    serialize through ``allow_nan=False``. For all finite, in-domain inputs this
    is byte-identical to ``contracts.canonical_json`` (the two differ only on the
    inputs §0 forbids), so the chain stays anchored to the one canonicalizer.
    """
    _assert_json_primitive(row)
    # allow_nan=False is belt-and-braces: _assert_json_primitive already rejected
    # non-finite floats, but this makes the no-NaN guarantee explicit at the
    # serializer call site (ADR §0 implementation note).
    return json.dumps(row, sort_keys=True, separators=(",", ":"), allow_nan=False)


def chain_batch(tip_seq: int, tip_hash: str, events: list) -> list[dict]:
    """Authoritatively stamp a batch onto the chain (§1a).

    ``tip_seq`` / ``tip_hash`` describe the current chain tip (0 / GENESIS_SENTINEL
    for an empty store). For each event in batch order this:

      1. ``dump``s the frozen event to an independent plain dict (frozen-safe),
      2. OVERWRITES the caller's ``seq``/``prev_hash`` with the assigned values
         (``seq = prev_seq + 1``; ``prev_hash`` = the prior row's ``row_hash``,
         or the tip's, or the genesis sentinel),
      3. canonicalizes (no-NaN, §0) and computes the framed ``row_hash`` over the
         3-field frame (``prev_hash``, ``event_type``, ``payload`` — Addendum 1),
      4. produces the persisted row: the patched dict + ``row_hash`` + the
         first-class ``event_type`` key + the canonical ``payload`` string.

    Returns the list of persisted rows in ``seq`` order. Raises (ValueError /
    SchemaError) on the FIRST invalid event WITHOUT having mutated any store —
    the caller commits the returned rows as one transaction, so a raise here is
    an all-or-nothing rollback (§4).

    ``event_type`` is a first-class (non-underscore) key — it survives
    ``public_row`` and lands on the yielded dict so reducers can dispatch on
    ``row["event_type"]`` (Addendum 1). The returned dicts also carry ONE private
    bookkeeping key the persistence layer strips before handing rows to callers:
    ``_payload`` (the internal canonical string the store persists).
    """
    rows: list[dict] = []
    prev_seq = tip_seq
    prev_hash = tip_hash
    for event in events:
        row = contracts.dump(event)  # independent deep-copied dict (frozen-safe)
        seq = prev_seq + 1
        row["seq"] = seq
        row["prev_hash"] = prev_hash
        # ``payload`` stays byte-for-byte ``canonical_json(dump(event)+seq+prev_hash)``:
        # ``event_type`` is hashed ADJACENT to it (the frame), NOT injected into it
        # (Addendum 1 rejects Option A — keeps the independent conformance oracle).
        payload = canonical_payload(row)  # raises on non-finite / non-JSON evidence
        event_type = _event_type_of(event)  # computed BEFORE hashing (Addendum 1)
        row_hash = framed_row_hash(prev_hash, event_type, payload.encode("utf-8"))
        row["event_type"] = event_type  # first-class key on the persisted/yielded row
        row["row_hash"] = row_hash
        rows.append({**row, "_payload": payload})
        prev_seq = seq
        prev_hash = row_hash
    return rows


def public_row(persisted: dict) -> dict:
    """Strip the private bookkeeping keys, returning the §1a caller-facing dict."""
    return {k: v for k, v in persisted.items() if not k.startswith("_")}


def verify_rows(rows: list[dict]) -> bool:
    """The §2 verdict over persisted rows, read BY NAME (Addendum 1, non-negotiable).

    Each ``row`` is a ``dict`` with keys ``seq``, ``prev_hash``, ``event_type``,
    ``payload``, ``row_hash`` — read by name so a future SELECT column reorder (or
    a divergence between this and ``_iter_rows``) cannot silently mis-hash a field.

    ``rows`` MUST already be ordered by ``seq`` ascending. Returns True iff the
    chain is intact, False (never raises for a tamper case) on any edit, reorder,
    deletion, or insertion. Re-hashes the STORED ``event_type`` + ``payload``
    bytes — never a re-parsed object, never a re-derived ``event_type`` (§0 /
    Addendum 1: "verify by re-reading the bytes you persist", for BOTH fields).
    On a False verdict, logs the FIRST bad ``seq`` (§2 / M3) while the public
    return stays a bare bool.

    An empty store ([]) is trivially True.
    """
    expected_seq = 1
    prev_hash = GENESIS_SENTINEL
    for row in rows:
        seq = row["seq"]
        row_prev_hash = row["prev_hash"]
        event_type = row["event_type"]
        payload = row["payload"]
        row_hash = row["row_hash"]
        if seq != expected_seq:
            _log.warning(
                "verify_chain: chain broken at seq=%s (expected gap-free seq=%s: "
                "deletion/insertion/reorder)",
                seq,
                expected_seq,
            )
            return False
        if row_prev_hash != prev_hash:
            _log.warning(
                "verify_chain: chain broken at seq=%s (prev_hash does not link to "
                "the prior row_hash: reorder or altered predecessor)",
                seq,
            )
            return False
        recomputed = framed_row_hash(row_prev_hash, event_type, payload.encode("utf-8"))
        if recomputed != row_hash:
            _log.warning(
                "verify_chain: chain broken at seq=%s (stored row_hash does not "
                "match the persisted payload bytes: edited row)",
                seq,
            )
            return False
        prev_hash = row_hash
        expected_seq += 1
    return True


def _event_type_of(event: Any) -> str:
    """Map a contract dataclass instance to its snake_case ``event_type`` token.

    ``ScenarioGenerated`` -> ``scenario_generated``, ``AttackExecuted`` ->
    ``attack_executed``, etc. ``event_type`` is NOT a dataclass attribute, so it
    is derived here from the class name and used both to populate the
    ``events.event_type`` column and to seed the §0/Addendum-1 framed row hash.
    """
    name = type(event).__name__
    out = []
    for i, ch in enumerate(name):
        if ch.isupper() and i > 0:
            out.append("_")
        out.append(ch.lower())
    return "".join(out)
