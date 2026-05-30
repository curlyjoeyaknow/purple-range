"""ValidationEvent contract skeleton + append-only ledger (T-004).

Charter #2 (versioned contracts), #3 (ports & adapters), and #4 (append-only
events) all converge here. This module defines:

  * ``ValidationEvent`` — the versioned, immutable value object every
    validation check emits. ``version`` is first-class and serialized; the full
    event catalog + JSON-Schemas are locked later in T-101.
  * ``Ledger`` — the append-only port (no update/delete) with two adapters:
    ``JsonlLedger`` (production, one JSON line per event) and
    ``InMemoryLedger`` (test fake, an order-preserving list).
  * ``Clock`` — the time port, so business logic never calls ``datetime.now()``
    directly. ``FixedClock`` is the deterministic test fake; ``SystemClock`` is
    the production adapter.

stdlib only — no third-party imports anywhere in this package.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol, runtime_checkable

# The skeleton contract version. Charter #2: every persisted shape carries a
# `version:int`; new fields are additive, removals require a migration ADR.
SCHEMA_VERSION = 1


@dataclass(frozen=True, kw_only=True)
class ValidationEvent:
    """A single validation observation, append-only and immutable.

    Fields (and serialized key order) are pinned here so the JSONL ledger stays
    diffable/chainable. ``kw_only`` lets ``version`` lead the field list with a
    default while the remaining fields stay required, sidestepping the dataclass
    "default before non-default" ordering rule.

    ``phase`` and ``evidence_ref`` are nullable and serialize as JSON ``null``
    (present in the dict, never dropped, never stringified to ``"None"``).
    """

    version: int = field(default=SCHEMA_VERSION)
    run_id: str
    phase: str | None
    check: str
    status: str
    evidence_ref: str | None
    ts: str

    def to_dict(self) -> dict:
        """Return a deterministic, ordered dict with ``version`` first.

        ``dataclasses.asdict`` preserves field declaration order, so the key
        order is stable across serializations and ``version`` always leads.
        """
        return asdict(self)


@runtime_checkable
class Ledger(Protocol):
    """Append-only event sink. No update, no delete — state is a fold."""

    def append(self, event: ValidationEvent) -> None: ...


class JsonlLedger:
    """Production adapter: one ``json.dumps(event.to_dict())`` line per event.

    Opens the file in append mode for each write, so the file is created if
    absent and a second append never truncates the first. Each line is flushed
    as a complete record terminated by a newline — no partial lines on the
    happy path.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def append(self, event: ValidationEvent) -> None:
        line = json.dumps(event.to_dict())
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")


class InMemoryLedger:
    """Test fake: keeps appended events in an order-preserving list."""

    def __init__(self) -> None:
        self.events: list[ValidationEvent] = []

    def append(self, event: ValidationEvent) -> None:
        self.events.append(event)


@runtime_checkable
class Clock(Protocol):
    """Time port — business logic reads `now` through this, never wall-clock."""

    def now_iso(self) -> str: ...


class FixedClock:
    """Test fake: returns the injected timestamp on every call (deterministic)."""

    def __init__(self, ts: str) -> None:
        self._ts = ts

    def now_iso(self) -> str:
        return self._ts


class SystemClock:
    """Production adapter: current UTC time as an ISO-8601 string."""

    def now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()
