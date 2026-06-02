"""T-110 — ``SqliteEventStore``: the hash-chained SQLite production adapter.

Implements the locked ``ports.EventStore`` Protocol over one stdlib-``sqlite3``
``events`` table (ADR-0007 §3). All chain math is shared with the InMemory fake
via ``adapters._chain`` so the two are byte-identical by construction (§4a).

``sqlite3`` is stdlib — allowed by the charter's stdlib-only posture — and it is
contained HERE: nothing else in business logic imports it.

The ``events`` table (column names matched exactly to the ADR §3 / T-110 tests,
which tamper the file out-of-band by these names):

    events(seq INTEGER PRIMARY KEY, event_type TEXT, payload TEXT,
           prev_hash TEXT, row_hash TEXT)

``payload`` holds the canonical-JSON event STRING — the exact bytes hashed —
and ``verify_chain`` re-reads THOSE bytes (§0 "hash the bytes you persist").
"""

from __future__ import annotations

import json
import sqlite3
from typing import Any, Iterator

from adapters import _chain  # sibling submodule; safe even mid-package-init

_DDL = """
CREATE TABLE IF NOT EXISTS events (
    seq        INTEGER PRIMARY KEY,
    event_type TEXT NOT NULL,
    payload    TEXT NOT NULL,
    prev_hash  TEXT NOT NULL,
    row_hash   TEXT NOT NULL
)
"""


class SqliteEventStore:
    """Append-only, hash-chained EventStore over stdlib ``sqlite3`` (ADR-0007).

    One connection per store; the same file can be reopened by a fresh instance
    (the durability/round-trip property the list-fake cannot model). Durability
    PRAGMA floor pinned by ADR §3a: ``synchronous=FULL`` (the default durable
    rollback-journal mode) — the strongest of the two permitted variants, chosen
    over NORMAL+WAL so a power loss cannot even drop the committed tail. At
    personal volume the latency cost is comfortably inside the <5 ms/event NFR.
    """

    def __init__(self, path: str) -> None:
        self._path = path
        self._conn = sqlite3.connect(path)
        # ADR §3a durable floor: FULL is the strongest permitted variant.
        self._conn.execute("PRAGMA synchronous = FULL")
        self._conn.execute(_DDL)
        self._conn.commit()

    # -- EventStore port -------------------------------------------------

    def append(self, events: list) -> list:
        """Authoritatively stamp + persist a batch in ONE transaction (§1a/§4).

        Reads the current chain tip, chains the whole batch off it, and commits
        all rows atomically. If any event is invalid (non-finite / non-JSON
        evidence, §0), ``chain_batch`` raises BEFORE any write and the
        transaction rolls back — none of the batch persists, the chain is
        unbroken. Returns ``list[dict]`` of the populated persisted rows.
        """
        if not events:  # no-op: don't open a transaction under synchronous=FULL
            return []
        tip_seq, tip_hash = self._tip()
        # May raise (ValueError / SchemaError) — nothing written yet, so the
        # store is untouched and the chain stays intact (§4 all-or-nothing).
        persisted = _chain.chain_batch(tip_seq, tip_hash, events)
        try:
            self._conn.execute("BEGIN")
            self._conn.executemany(
                "INSERT INTO events (seq, event_type, payload, prev_hash, row_hash) "
                "VALUES (?, ?, ?, ?, ?)",
                [
                    (r["seq"], r["event_type"], r["_payload"], r["prev_hash"], r["row_hash"])
                    for r in persisted
                ],
            )
            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise
        return [_chain.public_row(r) for r in persisted]

    def fold(self, reducer: Any, init: Any) -> Any:
        """Reduce the whole log from genesis, in ``seq`` order, deterministically."""
        acc = init
        for row in self._iter_rows(""):
            acc = reducer(acc, row)
        return acc

    def replay_from(self, seq: int) -> Iterator:
        """Yield the persisted-dict suffix from ``seq`` onward, ``seq``-ordered.

        Indexed seek (``WHERE seq >= ?``) on the ``seq`` PRIMARY KEY (§3).
        """
        return iter(list(self._iter_rows("WHERE seq >= ?", (seq,))))

    def verify_chain(self) -> bool:
        """§2 verdict: True on an intact (or empty) chain, False on any tamper."""
        cur = self._conn.execute(
            "SELECT seq, prev_hash, event_type, payload, row_hash FROM events ORDER BY seq"
        )
        # Key-based hand-off to verify_rows (Addendum 1, non-negotiable): build a
        # list[dict] column->value so a future SELECT reorder cannot mis-hash.
        rows = [
            {
                "seq": seq,
                "prev_hash": prev_hash,
                "event_type": event_type,
                "payload": payload,
                "row_hash": row_hash,
            }
            for seq, prev_hash, event_type, payload, row_hash in cur
        ]
        return _chain.verify_rows(rows)

    # -- lifecycle -------------------------------------------------------

    def close(self) -> None:
        """Close the underlying connection (sqlite3 tolerates a redundant close)."""
        self._conn.close()

    def __enter__(self) -> SqliteEventStore:
        return self

    def __exit__(self, *exc) -> bool:
        self.close()
        return False  # never suppress exceptions

    # -- internals -------------------------------------------------------

    def _tip(self) -> tuple[int, str]:
        """The current chain tip ``(seq, row_hash)`` — (0, sentinel) when empty."""
        row = self._conn.execute(
            "SELECT seq, row_hash FROM events ORDER BY seq DESC LIMIT 1"
        ).fetchone()
        if row is None:
            return 0, _chain.GENESIS_SENTINEL
        return row[0], row[1]

    def _iter_rows(self, where: str, params: tuple = ()) -> Iterator[dict]:
        """Yield persisted dicts (the §1a row shape) reconstructed from ``payload``.

        Per the committed judgment call, fold/replay_from yield the SAME dict
        shape ``append`` returns — reconstructed from the stored ``payload`` plus
        the stored ``row_hash``, never the caller's frozen dataclass.
        """
        cur = self._conn.execute(
            f"SELECT payload, row_hash, event_type FROM events {where} ORDER BY seq",
            params,
        )
        for payload, row_hash, event_type in cur:
            row = json.loads(payload)
            row["row_hash"] = row_hash
            row["event_type"] = event_type  # first-class discriminator (Addendum 1)
            yield row
