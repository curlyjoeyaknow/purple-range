"""Contract tests for the `lab` CLI dispatch table (T-004).

T-004 locks the FULL `lab` dispatch table up front (plan-critic C1) so the
parallel streams S1/S2/S3 only fill in the body of an already-registered
command and never edit the argparse/dispatch wiring. These tests pin that
table + each stub's behaviour BEFORE any implementation exists.

These tests FAIL until `lab/cli.py` exists (collection-time ImportError), then
assertion-level once the skeleton resolves.

Locked interface (so the implementer cannot drift)
--------------------------------------------------
``lab/cli.py`` defines:

    def main(
        argv: list[str] | None = None,
        *,
        ledger: Ledger | None = None,   # injected fake in tests; JsonlLedger in prod
        clock: Clock | None = None,     # injected FixedClock in tests
    ) -> int:
        ...

DISPATCH TABLE — LOCKED HERE
----------------------------
Six top-level verbs, each taking an OPTIONAL `<phase>` positional where
applicable:

    up | down | reset | validate | status | panic

`validate` additionally accepts the tier flags  --smoke / --e2e / --pair
(ARCHITECTURE.md 565-569).

Four stream sub-commands (S1/S2/S3 verbs stubbed up front):

    detection onboard
    threat-actor run
    isolation arm
    isolation disarm

PINNED `check` strings per command (the value written on the stub's
ValidationEvent). Top-level verbs use the bare verb name; sub-commands use a
dotted `parent.sub` form:

    up            -> "up"
    down          -> "down"
    reset         -> "reset"
    validate      -> "validate"
    status        -> "status"
    panic         -> "panic"
    detection onboard   -> "detection.onboard"
    threat-actor run    -> "threat-actor.run"
    isolation arm       -> "isolation.arm"
    isolation disarm    -> "isolation.disarm"

PINNED stub behaviour:
  * status string for every stub is exactly "not-implemented".
  * a recognized stub exits 0 and appends EXACTLY ONE ValidationEvent.
  * an UNKNOWN command exits NONZERO (argparse error; SystemExit != 0).
  * `lab --help` exits 0 and its text lists all six top-level verbs AND the
    stream sub-commands.

Boundary rule: cli.py imports NO vendor SDK and no concrete LabProvider — it
sits over the (T-101) port seam. Stamps `ts` from the injected Clock, never
datetime.now().
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Import the units under test. RED for the right reason until lab/ exists.
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from lab.cli import main  # noqa: E402
from lab.ledger import FixedClock, InMemoryLedger  # noqa: E402

FIXED_TS = "2026-01-01T00:00:00Z"

# (argv, pinned check string) for every recognized stub command.
TOP_LEVEL_COMMANDS = [
    (["up"], "up"),
    (["down"], "down"),
    (["reset"], "reset"),
    (["validate"], "validate"),
    (["status"], "status"),
    (["panic"], "panic"),
]

STREAM_SUBCOMMANDS = [
    (["detection", "onboard"], "detection.onboard"),
    (["threat-actor", "run"], "threat-actor.run"),
    (["isolation", "arm"], "isolation.arm"),
    (["isolation", "disarm"], "isolation.disarm"),
]

ALL_COMMANDS = TOP_LEVEL_COMMANDS + STREAM_SUBCOMMANDS

VALIDATE_FLAGS = [
    (["validate", "--smoke", "web"], "validate"),
    (["validate", "--e2e", "web"], "validate"),
    (["validate", "--pair", "web", "ad"], "validate"),
]


# ---------------------------------------------------------------------------
# 1. test_lab_cli_parses_all_commands — argparse accepts every command.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "argv,check",
    ALL_COMMANDS,
    ids=[c for _, c in ALL_COMMANDS],
)
def test_lab_cli_parses_all_commands(argv, check):
    """argparse accepts EVERY top-level verb and stream sub-command; each
    recognized command exits 0 (parse succeeds, stub runs)."""
    rc = main(argv, ledger=InMemoryLedger(), clock=FixedClock(FIXED_TS))
    assert rc == 0, f"recognized command {argv!r} must parse and exit 0"


@pytest.mark.parametrize(
    "argv,check",
    VALIDATE_FLAGS,
    ids=["validate-smoke", "validate-e2e", "validate-pair"],
)
def test_validate_accepts_tier_flags(argv, check):
    """`validate` accepts --smoke / --e2e / --pair (ARCHITECTURE 565-569)."""
    rc = main(argv, ledger=InMemoryLedger(), clock=FixedClock(FIXED_TS))
    assert rc == 0, f"validate tier {argv!r} must parse and exit 0"


def test_help_exits_zero():
    """`lab --help` exits 0 (argparse raises SystemExit(0) on --help)."""
    with pytest.raises(SystemExit) as exc:
        main(["--help"], ledger=InMemoryLedger(), clock=FixedClock(FIXED_TS))
    assert exc.value.code == 0, "`lab --help` must exit 0"


def test_help_text_lists_all_commands(capsys):
    """`lab --help` text names all six top-level verbs AND the stream
    sub-command parents (so the dispatch surface is discoverable)."""
    with pytest.raises(SystemExit):
        main(["--help"], ledger=InMemoryLedger(), clock=FixedClock(FIXED_TS))
    help_text = capsys.readouterr().out

    for verb in ("up", "down", "reset", "validate", "status", "panic"):
        assert verb in help_text, f"--help must list top-level verb {verb!r}"
    for parent in ("detection", "threat-actor", "isolation"):
        assert parent in help_text, (
            f"--help must list stream sub-command group {parent!r}"
        )


def test_unknown_command_exits_nonzero():
    """An UNKNOWN command is an argparse error → nonzero exit (SystemExit !=0)."""
    with pytest.raises(SystemExit) as exc:
        main(
            ["frobnicate"],
            ledger=InMemoryLedger(),
            clock=FixedClock(FIXED_TS),
        )
    assert exc.value.code != 0, "unknown command must exit nonzero"


def test_unknown_subcommand_exits_nonzero():
    """An unknown sub-command under a known group is also an argparse error."""
    with pytest.raises(SystemExit) as exc:
        main(
            ["isolation", "explode"],
            ledger=InMemoryLedger(),
            clock=FixedClock(FIXED_TS),
        )
    assert exc.value.code != 0, "unknown sub-command must exit nonzero"


# ---------------------------------------------------------------------------
# 2. Each stub appends EXACTLY ONE not-implemented ValidationEvent and exits 0.
#    Ledger + clock are INJECTED — no real filesystem write in dispatch tests.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "argv,check",
    ALL_COMMANDS,
    ids=[c for _, c in ALL_COMMANDS],
)
def test_stub_appends_single_not_implemented_event(argv, check):
    """Running any stub via main() appends exactly one ValidationEvent with
    status='not-implemented' and check=<the pinned verb name>, and exits 0."""
    ledger = InMemoryLedger()
    clock = FixedClock(FIXED_TS)

    rc = main(argv, ledger=ledger, clock=clock)

    assert rc == 0, f"{argv!r} stub must exit 0"
    assert len(ledger.events) == 1, (
        f"{argv!r} must append EXACTLY ONE ValidationEvent, "
        f"got {len(ledger.events)}"
    )
    event = ledger.events[0]
    assert event.status == "not-implemented", (
        "stub status must be exactly 'not-implemented'"
    )
    assert event.check == check, (
        f"stub for {argv!r} must record check={check!r}, got {event.check!r}"
    )


def test_stub_event_ts_comes_from_injected_clock():
    """The stub stamps `ts` from the injected Clock — never datetime.now()."""
    ledger = InMemoryLedger()
    main(["up"], ledger=ledger, clock=FixedClock(FIXED_TS))
    assert ledger.events[0].ts == FIXED_TS, (
        "stub event ts must come from the injected clock, not wall-clock time"
    )


def test_stub_event_carries_version():
    """The appended event is the versioned skeleton shape (charter #2)."""
    ledger = InMemoryLedger()
    main(["status"], ledger=ledger, clock=FixedClock(FIXED_TS))
    assert ledger.events[0].to_dict()["version"] == 1, (
        "the stub's ValidationEvent must serialize with version 1"
    )


def test_unknown_command_appends_no_event():
    """A rejected (unknown) command must NOT append a ValidationEvent —
    only recognized stubs emit a ledger record."""
    ledger = InMemoryLedger()
    with pytest.raises(SystemExit):
        main(["frobnicate"], ledger=ledger, clock=FixedClock(FIXED_TS))
    assert ledger.events == [], (
        "an unparseable command must not append any ValidationEvent"
    )


def test_cli_core_imports_no_vendor_sdk():
    """Boundary rule (charter #3): lab.cli imports no concrete provider /
    vendor SDK. The CLI core sits over the (T-101) LabProvider port seam.

    Guards against a stream later leaking `import vboxapi` / `import docker` /
    `subprocess` / `socket` into the dispatch core.
    """
    import lab.cli as cli_module

    source = Path(cli_module.__file__).read_text(encoding="utf-8")
    forbidden = ("vboxapi", "import docker", "VBoxManage")
    for token in forbidden:
        assert token not in source, (
            f"lab/cli.py must not import a vendor SDK; found {token!r}"
        )
