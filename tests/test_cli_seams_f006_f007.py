"""T-101 — F-006 (Rng-minted correlation_id) + F-007 (handler-dispatch seam).

These pin the two seams T-004 deferred to T-101, as CONTRACTS the implementer
rewires `lab/cli.py` against. We do NOT mock the unit under test (`main`); we
drive it with the boundary fakes (an injected Rng + an in-memory ledger).

F-006 — `main()` mints the run/correlation id from an INJECTED `Rng` port, NOT
  `uuid.uuid4()`. Proven behaviorally: under a SeededRng the id on the emitted
  ValidationEvent is REPLAYABLE (two same-seed runs produce the same id) — which
  uuid4() could never be. `main`'s signature must accept `rng=` like it accepts
  `clock=`/`ledger=`.

F-007 — the `lab` CLI exposes a `check -> handler` dispatch seam (a HANDLERS
  table or `lab/handlers/` package) so a command body is filled by ADD without
  editing `main()`'s parser. Proven: a handler registered for a `check` string is
  looked up and invoked by `main()`.
"""

from __future__ import annotations

import pytest

from lab import cli  # already exists (T-004)
from lab.ledger import InMemoryLedger, FixedClock  # already exists (T-004)

# Plain import — RED at collection until T-101 lands the SeededRng adapter and
# rewires cli.main() to accept it (F-006).
import adapters


def _run(argv, *, rng, ledger=None, clock=None):
    ledger = ledger or InMemoryLedger()
    clock = clock or FixedClock("2026-05-31T00:00:00+00:00")
    rc = cli.main(argv, ledger=ledger, clock=clock, rng=rng)
    return rc, ledger


# --------------------------------------------------------------------------
# F-006 — correlation/run id is Rng-minted and replayable.
# --------------------------------------------------------------------------

def test_main_accepts_injected_rng():
    """main() takes an `rng=` keyword (the Rng port), like clock/ledger."""
    import inspect

    params = inspect.signature(cli.main).parameters
    assert "rng" in params, "main() must accept an injected `rng` (F-006)"


def test_run_id_is_replayable_under_seeded_rng():
    """Same seed -> same run_id on the emitted event (so it is NOT uuid4)."""
    _, ledger_a = _run(["status"], rng=adapters.SeededRng(seed=5))
    _, ledger_b = _run(["status"], rng=adapters.SeededRng(seed=5))
    id_a = ledger_a.events[0].run_id
    id_b = ledger_b.events[0].run_id
    assert id_a == id_b, "run_id must be replayable from the Rng seed (F-006: not uuid4)"


def test_run_id_differs_across_seeds():
    _, ledger_a = _run(["status"], rng=adapters.SeededRng(seed=1))
    _, ledger_b = _run(["status"], rng=adapters.SeededRng(seed=2))
    assert ledger_a.events[0].run_id != ledger_b.events[0].run_id


def test_no_uuid4_in_cli_source():
    """The inline `uuid.uuid4().hex` run_id must be gone (F-006 close-out)."""
    import inspect

    src = inspect.getsource(cli)
    assert "uuid4" not in src, "F-006: cli.py must not mint ids from uuid.uuid4()"


# --------------------------------------------------------------------------
# F-007 — handler-dispatch seam: check -> handler, filled by ADD.
# --------------------------------------------------------------------------

def test_handler_dispatch_seam_exists():
    """A `check -> handler` table (HANDLERS) or `lab/handlers/` package exists."""
    has_table = hasattr(cli, "HANDLERS")
    has_pkg = False
    try:
        import lab.handlers  # noqa: F401

        has_pkg = True
    except ImportError:
        pass
    assert has_table or has_pkg, (
        "F-007: a check->handler dispatch seam must exist (HANDLERS table or lab/handlers/)"
    )


def test_registered_handler_is_invoked_by_main():
    """A handler registered for a `check` is looked up and called by main() —
    so a stream fills a command body by ADD, never editing the parser."""
    if not hasattr(cli, "HANDLERS"):
        pytest.skip("seam is the lab/handlers/ package variant; table variant not used")

    called = {}

    def fake_handler(ctx):
        called["hit"] = True
        return 0

    # ADD-only registration: install a handler for the `status` check.
    cli.HANDLERS["status"] = fake_handler
    try:
        rc, _ = _run(["status"], rng=adapters.SeededRng(seed=1))
    finally:
        cli.HANDLERS.pop("status", None)
    assert called.get("hit"), "main() must dispatch a `check` to its registered handler"
    assert rc == 0
