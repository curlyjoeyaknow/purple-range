"""The `lab` CLI dispatch table (T-004) — argparse surface LOCKED here.

T-004 locks the FULL `lab` argparse surface up front (plan-critic C1) so the
parallel streams S1/S2/S3 register against a fixed command set and never touch
the parser wiring.

NOTE (followup F-007): the per-command *body* seam does not exist yet — `main()`
builds the not-implemented `ValidationEvent` inline for every command, with no
``check -> handler`` dispatch table. Until T-101 introduces that handler seam
(alongside the Rng-minted run-scoped id, F-006), a stream filling a real command
body will edit `main()`. The argparse table is locked; the handler seam is not.

Dispatch table (locked)
------------------------
Six top-level verbs, each taking an OPTIONAL ``<phase>`` positional where
applicable::

    up | down | reset | validate | status | panic

``validate`` additionally accepts tier flags ``--smoke`` / ``--e2e`` /
``--pair`` (ARCHITECTURE.md 565-569).

Four stream sub-commands::

    detection onboard
    threat-actor run
    isolation arm
    isolation disarm

Each recognized command appends EXACTLY ONE ``ValidationEvent`` with
``status="not-implemented"`` and the pinned ``check`` string, then returns 0.
An unknown command/sub-command is an argparse error (nonzero ``SystemExit``)
and appends NO event.

Boundary rule (charter #3): this module imports NO vendor SDK and no concrete
``LabProvider`` — it sits over the (T-101) provider port seam. The timestamp is
stamped from the injected ``Clock``, never ``datetime.now()``.
"""

from __future__ import annotations

import argparse
import sys

import adapters
import contracts
from lab.ledger import (
    Clock,
    JsonlLedger,
    Ledger,
    SystemClock,
    ValidationEvent,
)
from ports import Rng

# Production location of the append-only validation ledger
# (ARCHITECTURE.md ~L689). Only used when no ledger is injected.
DEFAULT_LEDGER_PATH = "/mnt/data/purple-range/state/validation-events.jsonl"

NOT_IMPLEMENTED = "not-implemented"

# Top-level verbs that take an optional <phase> positional. Each maps 1:1 to
# its pinned `check` string (the bare verb name).
TOP_LEVEL_VERBS = ("up", "down", "reset", "validate", "status", "panic")

# F-007 — the check->handler dispatch seam. A stream fills a command BODY by
# registering ``HANDLERS[<check>] = fn`` (ADD only) without editing the parser
# or ``main()``. A registered handler is invoked as ``fn(ctx) -> int`` (the rc
# main returns). Empty at lock time: every recognized command still falls back
# to the T-004 default (append one not-implemented ValidationEvent, return 0).
HANDLERS: dict = {}


def _build_parser() -> argparse.ArgumentParser:
    """Build the locked dispatch parser. Streams fill command bodies, not this."""
    parser = argparse.ArgumentParser(
        prog="lab",
        description=(
            "Purple Range lab control: up, down, reset, validate, status, "
            "panic; plus stream groups detection, threat-actor, isolation."
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # Top-level verbs, each with an optional <phase> positional.
    for verb in TOP_LEVEL_VERBS:
        p = sub.add_parser(verb, help=f"{verb} a lab phase (stub)")
        p.add_argument("phase", nargs="?", default=None, help="target phase (optional)")
        if verb == "validate":
            # NOTE: these tier flags are PARSED-BUT-NOT-YET-CONSUMED in the T-004
            # skeleton — main() emits a not-implemented event regardless of tier.
            # T-801 (the `lab validate` tier owner) wires them onto the event and
            # tightens `--pair` arity (currently loose nargs="*"; should be exactly
            # two phases). Until then they are inert: present on the locked surface
            # so streams need not edit the parser, but they drive no behaviour.
            p.add_argument("--smoke", action="store_true", help="smoke tier")
            p.add_argument("--e2e", action="store_true", help="end-to-end tier")
            # --pair takes the (web, ad) phase pair to cross-validate.
            p.add_argument("--pair", nargs="*", default=None, help="validate a phase pair")

    # Stream sub-command groups: parent verb + a nested sub-command.
    detection = sub.add_parser("detection", help="detection stream (S1)")
    det_sub = detection.add_subparsers(dest="subcommand", required=True)
    det_sub.add_parser("onboard", help="onboard a detection source (stub)")

    threat_actor = sub.add_parser("threat-actor", help="threat-actor stream (S2)")
    ta_sub = threat_actor.add_subparsers(dest="subcommand", required=True)
    ta_sub.add_parser("run", help="run a threat-actor scenario (stub)")

    isolation = sub.add_parser("isolation", help="isolation stream (S3)")
    iso_sub = isolation.add_subparsers(dest="subcommand", required=True)
    iso_sub.add_parser("arm", help="arm isolation (stub)")
    iso_sub.add_parser("disarm", help="disarm isolation (stub)")

    return parser


def _check_for(args: argparse.Namespace) -> str:
    """Resolve the pinned `check` string for a parsed command.

    Top-level verbs use the bare verb name; sub-commands use ``parent.sub``.
    """
    subcommand = getattr(args, "subcommand", None)
    if subcommand is not None:
        return f"{args.command}.{subcommand}"
    return args.command


def main(
    argv: list[str] | None = None,
    *,
    ledger: Ledger | None = None,
    clock: Clock | None = None,
    rng: Rng | None = None,
) -> int:
    """Parse ``argv``, dispatch the matched command, return its exit code.

    Tests inject fake ``ledger``/``clock``/``rng``; production wires a
    ``JsonlLedger`` at :data:`DEFAULT_LEDGER_PATH`, a ``SystemClock``, and a
    system ``SeededRng``. The timestamp is read from the clock port — never
    ``datetime.now()`` here.

    F-006: the ``run_id`` is minted from the injected ``Rng`` port (not a random
    UUID), so a SeededRng makes the run_id replayable.

    F-007: if a handler is registered in :data:`HANDLERS` for the resolved
    ``check`` string it is invoked (``handler(ctx) -> int``) and its return code
    is returned; otherwise the T-004 default runs — append exactly one
    not-implemented ``ValidationEvent`` and return 0.

    An unparseable command raises ``SystemExit`` (argparse) before any dispatch.
    """
    if argv is None:
        argv = sys.argv[1:]
    if ledger is None:
        ledger = JsonlLedger(DEFAULT_LEDGER_PATH)
    if clock is None:
        clock = SystemClock()
    if rng is None:
        rng = adapters.SeededRng()

    parser = _build_parser()
    args = parser.parse_args(argv)  # SystemExit on unknown command/sub-command

    check = _check_for(args)
    run_id = contracts.mint_correlation_id(rng)

    handler = HANDLERS.get(check)
    if handler is not None:
        ctx = {
            "args": args,
            "check": check,
            "run_id": run_id,
            "ledger": ledger,
            "clock": clock,
            "rng": rng,
        }
        return handler(ctx)

    event = ValidationEvent(
        run_id=run_id,
        phase=getattr(args, "phase", None),
        check=check,
        status=NOT_IMPLEMENTED,
        evidence_ref=None,
        ts=clock.now_iso(),
    )
    ledger.append(event)
    return 0


if __name__ == "__main__":
    sys.exit(main())
