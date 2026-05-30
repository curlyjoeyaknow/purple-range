"""Pinned dependency fetcher — the logic behind ``scripts/fetch-deps.sh`` (T-002).

The named T-002 deliverable is ``scripts/fetch-deps.sh``, but a bash script that
clones over the network and checksums a tree is essentially untestable offline.
So, per charter #3 (ports & adapters), the *logic* lives here behind a
:class:`Fetcher` port:

  * production wires :class:`GitFetcher` (``git clone`` + ``git checkout`` via
    ``subprocess``);
  * tests wire a fake at the same port (no network, no git);
  * ``scripts/fetch-deps.sh`` is a thin shim that ``exec``s ``python3 -m
    lab.fetch_deps`` — its body holds no clone, so the pins-gate has nothing to
    flag there (the clone happens here, in Python, which the gate does not scan).

Integrity model
---------------
The gate is a DETERMINISTIC tree-content digest, NOT a tarball (see
:func:`tree_sha256`): a tarball's metadata varies across git/tar versions, but a
sorted ``"<relpath>\\0<sha256(bytes)>\\n"`` manifest depends only on path +
content, so the same commit checked out twice yields the same digest. The
resolved commit SHA is reported too, but the SHA256 tree digest is the gate the
spec requires ("verifies SHA256; refuses on mismatch").

The :class:`Fetcher` adapter only *populates* the tree and *reports* the
computed digest — it never verifies. Verification (and the collect-all-errors
fail policy, idempotency short-circuit, pending-pin refusal, and the
dest-under-vendor_base guarantee) is :func:`fetch_all`'s job: a single gate, not
duplicated in every adapter.

Upstream tree digests are not knowable offline, so a resolved dep ships with a
TOFU (trust-on-first-use) sentinel digest until its first verified fetch: the
first ``fetch`` mismatches the sentinel, prints the real sha256, and the
operator records that value into the manifest. A mismatch against a sentinel is
the expected first-run case; a mismatch against a real 64-hex pin is a tampering
signal (the two are worded differently — see :class:`ChecksumMismatch`).

Stdlib only (``subprocess``, ``hashlib``, ``pathlib``, ``dataclasses``,
``enum``) — no third-party import, no vendor SDK.
"""

from __future__ import annotations

import enum
import hashlib
import shutil
import subprocess
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

# =============================================================================
# Contracts (charter #2) — frozen, typed shapes the fetcher reads/produces.
# =============================================================================


class FetchStatus(enum.Enum):
    """Outcome of a single dep fetch."""

    FETCHED = "fetched"  # cloned/checked-out + verified now
    ALREADY_PRESENT = "already_present"  # valid dep already on disk; no-op


@dataclass(frozen=True)
class DepSpec:
    """A pinned dependency to fetch.

    ``pinned_commit`` is the integrity pin; ``None`` means the pin is not yet
    selected (SecGen / Q-011) and the dep must REFUSE rather than clone master.
    ``sha256`` is the expected tree-content digest (also ``None`` while pending).
    ``dest_subdir`` is the path UNDER the injected vendor base.
    """

    name: str
    repo_url: str
    pinned_commit: str | None
    sha256: str | None
    dest_subdir: str


@dataclass(frozen=True)
class FetchResult:
    """What actually happened for one dep: status, resolved commit, digest, dest."""

    name: str
    status: FetchStatus
    resolved_commit: str
    sha256: str
    dest: Path


# =============================================================================
# Exceptions — one base so callers catch a single type.
# =============================================================================


class FetchError(Exception):
    """Base for every fetch failure."""


class ChecksumMismatch(FetchError):
    """The fetched tree digest did not match the pinned sha256.

    Two operator-facing cases, deliberately worded differently (this is a
    security tool — the distinction matters):

      * the expected value is the TOFU sentinel (:data:`TOFU_PENDING_SHA256`),
        i.e. the integrity of this dep has never been pinned yet. This is the
        EXPECTED first-fetch outcome: verify the upstream, then record the
        printed ``actual`` sha256 into the manifest. Not alarming.
      * the expected value is a real 64-hex digest. The tree on the wire does
        NOT match what we pinned — a possible tampering / wrong-source signal.
        Alarming: do NOT just record the new digest.

    The string ``str(exc)`` reads correctly for whichever case applies; the
    typed fields (``.name``/``.expected``/``.actual``/``.is_tofu``) let callers
    branch without parsing prose.
    """

    def __init__(self, name: str, expected: str, actual: str) -> None:
        self.name = name
        self.expected = expected
        self.actual = actual
        self.is_tofu = expected == TOFU_PENDING_SHA256
        if self.is_tofu:
            message = (
                f"{name}: first fetch — integrity not yet pinned (TOFU, "
                f"trust-on-first-use). Verify this is the upstream you expect, "
                f"then record the printed sha256 {actual} into the {name} "
                f"DepSpec in lab/fetch_deps.py (replacing the TOFU sentinel)."
            )
        else:
            message = (
                f"{name}: SHA256 INTEGRITY MISMATCH — expected {expected}, got "
                f"{actual}. The fetched tree does NOT match the pinned digest; "
                f"this can indicate tampering or a wrong/moved upstream. Do NOT "
                f"blindly record the new digest — investigate before trusting it."
            )
        super().__init__(message)


class PendingPinError(FetchError):
    """The dep's pin has not been selected yet (Q-011): refuse, never clone master."""

    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(
            f"{name}: dependency pin not yet selected — refusing to fetch (an "
            f"unset pin must never masquerade as a fetched dep). See "
            f"docs/OPEN-QUESTIONS.md (Q-011) for which commit + base box to pin."
        )


class WrongCommitError(FetchError):
    """A dep on disk resolved to a commit other than the pin.

    Reserved for an explicit-commit-assertion path. Currently a wrong-commit
    checkout is already handled by digest re-fetch: :func:`_is_valid_present`
    sees the mismatched tree digest, declares the dep not-present, and
    :func:`fetch_all` re-fetches to the pinned commit (see
    ``test_present_dep_at_wrong_commit_is_refetched_to_pinned_commit``). This
    class is kept (it is part of the locked exception hierarchy) for a future
    path that asserts the resolved commit SHA directly rather than via digest.
    """

    def __init__(self, name: str, expected: str, actual: str) -> None:
        self.name = name
        self.expected = expected
        self.actual = actual
        super().__init__(
            f"{name}: on-disk commit {actual} != pinned {expected}"
        )


class AggregateFetchError(FetchError):
    """Collected per-dep failures from one ``fetch_all`` run (fail policy)."""

    def __init__(self, errors: list[FetchError]) -> None:
        self.errors = errors
        joined = "; ".join(str(e) for e in errors)
        super().__init__(f"{len(errors)} dependency fetch error(s): {joined}")


# =============================================================================
# The Fetcher port (charter #3). Production = GitFetcher; tests = a fake.
# =============================================================================


@runtime_checkable
class Fetcher(Protocol):
    """Populates ``dest`` with ``dep``'s tree at the pin; reports commit + digest.

    MUST NOT verify the checksum itself — verification is :func:`fetch_all`'s
    gate. A structural Protocol so the boundary fake and :class:`GitFetcher`
    satisfy the same contract without inheritance.
    """

    def fetch(self, dep: DepSpec, dest: Path) -> FetchResult: ...


# =============================================================================
# tree_sha256 — the single source of truth for the integrity gate.
# =============================================================================


def tree_sha256(root: Path) -> str:
    """Deterministic content digest of the directory tree under ``root``.

    Hashes ``sha256`` over the sorted concatenation of one line per regular
    file::

        "<relpath>\\0<sha256(file_bytes)>\\n"

    with the ``.git`` directory excluded. Depends ONLY on path + content
    (sorted) — never on mtime, inode, clone time, or git pack layout — so the
    same commit checked out twice yields the same digest, while any content
    change flips it. Relative paths are POSIX-normalized so the digest is
    platform-stable.
    """
    root = Path(root)
    lines: list[str] = []
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        rel = path.relative_to(root)
        parts = rel.parts
        if parts and parts[0] == ".git":
            continue  # clone-layout-dependent; excluded so the gate is honest
        rel_posix = rel.as_posix()
        body_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        lines.append(f"{rel_posix}\0{body_hash}\n")
    return hashlib.sha256("".join(sorted(lines)).encode("utf-8")).hexdigest()


# =============================================================================
# GitFetcher — the production adapter (clone + checkout via subprocess).
# =============================================================================


class GitFetcher:
    """Production :class:`Fetcher`: ``git clone`` + ``git checkout <pin>``.

    Works against any ``repo_url`` git accepts, including a plain local
    filesystem path (used by the offline integration test against a bare/local
    repo in ``tmp_path``). Clones into ``dest``, checks out the pinned commit,
    then computes the tree digest via :func:`tree_sha256`. Does NOT verify the
    checksum — that is :func:`fetch_all`'s gate.
    """

    def fetch(self, dep: DepSpec, dest: Path) -> FetchResult:
        if dep.pinned_commit is None:  # defensive; fetch_all refuses earlier
            raise PendingPinError(dep.name)

        dest = Path(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        # Clean any prior contents so the checkout is exactly the pinned tree.
        if dest.exists():
            shutil.rmtree(dest)

        self._git("clone", "--quiet", dep.repo_url, str(dest))
        self._git("-C", str(dest), "checkout", "--quiet", dep.pinned_commit)
        resolved = self._git(
            "-C", str(dest), "rev-parse", "HEAD"
        ).strip()

        return FetchResult(
            name=dep.name,
            status=FetchStatus.FETCHED,
            resolved_commit=resolved,
            sha256=tree_sha256(dest),
            dest=dest,
        )

    @staticmethod
    def _git(*args: str) -> str:
        """Run a git subprocess, return stdout; raise on nonzero exit."""
        completed = subprocess.run(
            ["git", *args],
            check=True,
            capture_output=True,
            text=True,
        )
        return completed.stdout


# =============================================================================
# fetch_all — the orchestrator: gate, idempotency, refusal, collect-all-errors.
# =============================================================================


def _is_valid_present(dest: Path, dep: DepSpec) -> bool:
    """True iff a dep already on disk matches its pinned digest (idempotency).

    A non-existent/empty dest, or one whose tree digest differs from the pin
    (e.g. a stale/wrong-commit checkout), is NOT valid — the orchestrator must
    re-fetch it.
    """
    if not dest.exists() or not any(dest.iterdir()):
        return False
    return tree_sha256(dest) == dep.sha256


def fetch_all(
    specs: Iterable[DepSpec],
    fetcher: Fetcher,
    vendor_base: Path,
) -> list[FetchResult]:
    """Fetch every spec under ``vendor_base``; verify, dedupe, collect errors.

    For each spec:

      * a pending pin (``pinned_commit is None``) REFUSES with
        :class:`PendingPinError` — the fetcher is never invoked, no tree lands;
      * an already-present dep whose digest matches the pin is a NO-OP
        (``ALREADY_PRESENT``); the fetcher is NOT re-invoked (idempotency);
      * otherwise the fetcher populates ``vendor_base/<dest_subdir>`` and the
        computed digest is verified against the pin — a mismatch raises
        :class:`ChecksumMismatch` and the garbage tree is removed so a later run
        cannot mistake it for a valid present dep.

    Fail policy is COLLECT-ALL-ERRORS: every spec is attempted; good deps still
    land; all failures are raised together as :class:`AggregateFetchError`.
    """
    vendor_base = Path(vendor_base)
    results: list[FetchResult] = []
    errors: list[FetchError] = []

    for dep in specs:
        dest = vendor_base / dep.dest_subdir
        try:
            results.append(_fetch_one(dep, fetcher, dest))
        except FetchError as exc:
            errors.append(exc)

    if errors:
        raise AggregateFetchError(errors)
    return results


def _fetch_one(dep: DepSpec, fetcher: Fetcher, dest: Path) -> FetchResult:
    """Fetch+verify a single dep (raises a typed FetchError on refusal/mismatch)."""
    if dep.pinned_commit is None:
        raise PendingPinError(dep.name)

    # Idempotency: a valid present dep is a no-op; the fetcher is NOT invoked.
    if _is_valid_present(dest, dep):
        return FetchResult(
            name=dep.name,
            status=FetchStatus.ALREADY_PRESENT,
            resolved_commit=dep.pinned_commit,
            sha256=dep.sha256,
            dest=dest,
        )

    result = fetcher.fetch(dep, dest)

    if result.sha256 != dep.sha256:
        # Refuse on mismatch: leave no partial/garbage tree behind.
        if dest.exists():
            shutil.rmtree(dest)
        raise ChecksumMismatch(dep.name, expected=dep.sha256, actual=result.sha256)

    return result


# =============================================================================
# load_manifest — the REAL pins from ARCHITECTURE.md "Pinned versions".
# =============================================================================
#
# sha256 honesty (read this before "fixing" the digests below)
# ------------------------------------------------------------
# The upstream tree digests are NOT knowable offline — they are recorded on the
# first verified fetch (trust-on-first-use). The contract (see
# tests/test_fetch_deps.py::test_every_resolved_manifest_dep_carries_a_sha256_gate)
# requires every RESOLVED dep to carry a NON-EMPTY sha256 (a None there would
# make the integrity gate a silent no-op) and every PENDING dep to carry None.
# So the resolved deps below carry an explicit TOFU SENTINEL — non-empty, and
# deliberately NOT a 64-hex digest so it can never be mistaken for a verified
# pin: the first offline `fetch_all` against the real repos will mismatch and
# print the actual digest, which then replaces the sentinel here. Inventing a
# plausible-looking fake 64-hex value would be WORSE — it could silently pass a
# tampered tree. The sentinel fails loudly and honestly.

#: Trust-on-first-use placeholder for an upstream digest not yet recorded.
#: Non-empty (satisfies the resolved-dep gate) and intentionally not 64-hex.
TOFU_PENDING_SHA256 = "TOFU-pending-first-fetch"

# Pins copied verbatim from docs/ARCHITECTURE.md "Pinned versions" (charter #10,
# checked 2026-05-30). GOAD pins the v3.0.0 *commit* (ls-remote-resolved), never
# the floating tag (→ Q-013). SecGen's commit is not selected yet (→ Q-011).
_MANIFEST: tuple[DepSpec, ...] = (
    DepSpec(
        name="vulhub",
        repo_url="https://github.com/vulhub/vulhub.git",
        pinned_commit="d277a8693e588684e951dddb0733809e53881a3c",
        sha256=TOFU_PENDING_SHA256,
        dest_subdir="vulhub",
    ),
    DepSpec(
        name="atomic-red-team",
        repo_url="https://github.com/redcanaryco/atomic-red-team.git",
        pinned_commit="daee1d5098b5a03c260835f87c33c3814c4695fa",
        sha256=TOFU_PENDING_SHA256,
        dest_subdir="atomic-red-team",
    ),
    DepSpec(
        name="goad",
        repo_url="https://github.com/Orange-Cyberdefense/GOAD.git",
        # v3.0.0 tag resolved to its commit (charter #10): the gate pins commits,
        # not floating tags. Re-verify at fetch time.
        pinned_commit="8c18acc1bd857efda07a15297466fae114bb484b",
        sha256=TOFU_PENDING_SHA256,
        dest_subdir="goad",
    ),
    DepSpec(
        name="secgen",
        repo_url="https://github.com/cliffe/SecGen.git",
        pinned_commit=None,  # Q-011: commit not selected yet — must refuse, not guess
        sha256=None,  # pending: nothing to pin until the commit is chosen
        dest_subdir="secgen",
    ),
)


def load_manifest() -> list[DepSpec]:
    """Return the real pinned-dependency manifest from ARCHITECTURE.md."""
    return list(_MANIFEST)


# =============================================================================
# CLI entry — `python -m lab.fetch_deps`; the .sh wrapper execs this.
# =============================================================================


def _print_manifest(specs: Iterable[DepSpec]) -> None:
    """Print one line per dep: name, pin (or pending marker), dest subdir."""
    for dep in specs:
        pin = dep.pinned_commit or "(pending — Q-011)"
        print(f"{dep.name:18} {pin}  -> {dep.dest_subdir}")


def _run_fetch(
    specs: list[DepSpec], fetcher: Fetcher, vendor_base: Path
) -> int:
    """Run :func:`fetch_all` and print a per-dep result; return process exit code.

    Prints one ``fetched`` / ``already-present`` line per successful dep, then
    (on :class:`AggregateFetchError`) one explanatory line per failure —
    ``pending`` for an unselected pin, the legible TOFU first-fetch guidance for
    a sentinel mismatch, and the alarming tampering wording for a real mismatch.
    Returns 0 only when every dep succeeded; nonzero if any dep failed.
    """
    try:
        results = fetch_all(specs, fetcher, vendor_base)
    except AggregateFetchError as agg:
        # Good deps still landed; report each failure on its own line so the
        # operator sees every problem in one run (collect-all-errors policy).
        for err in agg.errors:
            if isinstance(err, PendingPinError):
                print(f"{err.name:18} pending  -> {err}")
            elif isinstance(err, ChecksumMismatch):
                label = "first-fetch" if err.is_tofu else "FAILED"
                print(f"{err.name:18} {label}  -> {err}")
            else:
                name = getattr(err, "name", "?")
                print(f"{name:18} FAILED  -> {err}")
        return 1

    for result in results:
        label = (
            "already-present"
            if result.status is FetchStatus.ALREADY_PRESENT
            else "fetched"
        )
        print(
            f"{result.name:18} {label}  -> {result.dest} "
            f"@ {result.resolved_commit} (sha256 {result.sha256})"
        )
    return 0


def main(
    argv: list[str] | None = None,
    *,
    fetcher: Fetcher | None = None,
    vendor_base: Path | None = None,
    specs: list[DepSpec] | None = None,
) -> int:
    """`python -m lab.fetch_deps {list|fetch}` — show the manifest, or fetch it.

    Two actions, ``list`` is the default (offline-safe, creates nothing):

      * ``list`` prints the pinned-dependency manifest.
      * ``fetch`` actually runs :func:`fetch_all` and prints a per-dep result.

    Injectable like :mod:`lab.cli`'s ``main``: tests pass ``fetcher`` (a fake),
    ``vendor_base`` (a tmp dir) and ``specs`` to drive ``fetch`` fully offline.
    When NOT injected, the ``fetch`` action constructs the PROD defaults —
    :class:`GitFetcher` and the StorageLayout ``vendor`` dir under
    :data:`lab.storage.DEFAULT_BASE`. Those defaults (and the ``ensure_layout``
    that creates ``/mnt/data``) are built ONLY inside the ``fetch`` branch, never
    at import time and never on the ``list`` path. Returns 0 on full success,
    nonzero if any dep failed.
    """
    import argparse

    parser = argparse.ArgumentParser(
        prog="lab.fetch_deps",
        description="Pinned dependency fetcher (T-002): list pins, or fetch them.",
    )
    parser.add_argument(
        "action",
        nargs="?",
        choices=("list", "fetch"),
        default="list",
        help="list the pin manifest (default) or fetch every pinned dep",
    )
    args = parser.parse_args(argv)

    if specs is None:
        specs = load_manifest()

    if args.action == "list":
        _print_manifest(specs)
        return 0

    # action == "fetch": wire PROD defaults lazily (never on the list path / at
    # import). The real fetch legitimately needs the vendor dir on disk, so
    # ensure_layout(DEFAULT_BASE) here is intentional.
    if fetcher is None:
        fetcher = GitFetcher()
    if vendor_base is None:
        from lab.storage import DEFAULT_BASE, ensure_layout

        vendor_base = ensure_layout(DEFAULT_BASE).vendor

    return _run_fetch(specs, fetcher, vendor_base)


if __name__ == "__main__":
    import sys

    sys.exit(main())
