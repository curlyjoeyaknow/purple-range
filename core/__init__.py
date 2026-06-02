"""T-111 — pure business-logic core (ports & adapters: the inside).

Modules here import ``contracts`` and ``ports`` (types / Protocols only) and
receive every boundary (store, telemetry, manifest, clock) as an injected
object. They import NO vendor SDK, NO concrete adapter, and NO ``sqlite3`` —
the charter's port discipline keeps the core deterministic and replayable.

stdlib only.
"""

from __future__ import annotations
