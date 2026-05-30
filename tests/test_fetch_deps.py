"""Contract tests for the pinned dependency fetcher (T-002).

T-002's deliverable is named `scripts/fetch-deps.sh` in the spec, but a bash
script that does `git clone` + sha256 over the network is essentially
untestable offline. We resolve that with PORTS & ADAPTERS (charter #3): the
*logic* lives in a stdlib Python module behind a `Fetcher` port; the real
adapter does `git clone`/`git checkout` via subprocess; a FAKE adapter
"fetches" from a local fixture dir with NO network. The `scripts/fetch-deps.sh`
wrapper is a thin shim that calls `python -m lab.fetch_deps` — its body is not
tested here (only that the entrypoint exists, asserted via the module API).

These tests lock that contract BEFORE any implementation exists. They FAIL
until `lab/fetch_deps.py` exists — the first failure is a collection-time
ImportError (deliberately a hard import, not `importorskip`: a skip would hide
the missing implementation behind a green run).

NO NETWORK in any test. The real git/subprocess adapter is exercised only via
the fake at the port boundary, EXCEPT the one optional integration test which
builds a *local bare git repo in tmp_path* (still fully offline) to prove the
real adapter satisfies the same `Fetcher` contract as the fake — guarding
against fake/real drift.

================================================================================
LOCKED INTERFACE (so the implementer cannot drift)
================================================================================
`lab/fetch_deps.py` defines, stdlib only (no vendor import):

    class FetchStatus(enum.Enum):
        FETCHED = "fetched"                 # cloned/checked-out + verified now
        ALREADY_PRESENT = "already_present" # valid dep already on disk; no-op

    @dataclass(frozen=True)
    class DepSpec:
        name: str               # e.g. "vulhub"
        repo_url: str           # clone source (a path for the fake/local repo)
        pinned_commit: str | None   # the integrity pin; None => pending (Q-011)
        sha256: str | None      # expected tree-content digest; None => pending
        dest_subdir: str        # path UNDER the injected vendor base, e.g. "vulhub"

    @dataclass(frozen=True)
    class FetchResult:
        name: str
        status: FetchStatus
        resolved_commit: str    # the commit actually present after the fetch
        sha256: str             # the tree-content digest actually computed
        dest: Path              # absolute path under the vendor base

    @runtime_checkable
    class Fetcher(Protocol):
        def fetch(self, dep: DepSpec, dest: Path) -> FetchResult: ...
        # Populates `dest` with the dep tree at `dep.pinned_commit`, returns the
        # resolved commit + computed tree digest. MUST NOT verify the checksum
        # itself — verification is the orchestrator's gate (see below).

    def tree_sha256(root: Path) -> str:
        # Deterministic content digest of a directory tree (see "WHAT gets
        # checksummed" below). The single source of truth for the integrity
        # gate; used by both the fetcher and the verifier.

    def fetch_all(
        specs: Iterable[DepSpec],
        fetcher: Fetcher,
        vendor_base: Path,
    ) -> list[FetchResult]:
        # Orchestrates: for each spec, fetch into vendor_base/<dest_subdir>,
        # verify the digest, short-circuit if already valid (idempotent),
        # quarantine/refuse on mismatch. COLLECT-ALL-ERRORS then raise.

    def load_manifest() -> list[DepSpec]:
        # The REAL pins, read from ARCHITECTURE.md "Pinned versions" (held as a
        # module const / small data file). Vulhub/ART/GOAD have pinned_commit;
        # SecGen is pending (pinned_commit=None, Q-011).

Exceptions (all subclasses of a common `FetchError` so callers catch one type):
    class FetchError(Exception): ...                 # base
    class ChecksumMismatch(FetchError): ...          # has .name/.expected/.actual
    class PendingPinError(FetchError): ...           # pin not selected (Q-011)
    class WrongCommitError(FetchError): ...          # on-disk dep at wrong commit
    class AggregateFetchError(FetchError): ...       # .errors: list[FetchError]

================================================================================
PINNED DESIGN DECISIONS (rationale lives with the test that exercises each)
================================================================================
* MODULE PATH ............ lab/fetch_deps.py (sibling of storage.py/ledger.py).
* WHAT IS CHECKSUMMED ..... a DETERMINISTIC tree-content digest, NOT a tarball:
    tree_sha256(root) = sha256 over sorted lines, one per regular file:
        "<relpath>\0<sha256(file_bytes)>\n"
    with the ".git" directory excluded. This is deterministic because it depends
    ONLY on path + content (sorted), never on mtime/inode/clone time/git pack
    layout — so the same commit checked out twice yields the same digest. (A raw
    `git archive` tar can vary by tar metadata across git versions; a sorted
    content manifest cannot.) The resolved commit SHA is ALSO pinned and checked
    (WrongCommitError), but the spec explicitly requires a SHA256 gate that
    "refuses on mismatch", so the tree digest is that gate.
* FAIL POLICY ............ COLLECT-ALL-ERRORS. fetch_all attempts every spec; a
    bad checksum on one dep does NOT silently skip the rest, and a good dep is
    still fetched. All failures are raised together as AggregateFetchError so the
    operator sees every problem in one run, not one-at-a-time.
* PENDING-PIN RULE ....... a DepSpec with pinned_commit is None (SecGen, Q-011)
    REFUSES with PendingPinError naming the dep + Q-011 — it NEVER clones master.
    An unset pin must not be able to masquerade as a fetched dep.
* VENDOR-DEST GUARANTEE ... every dep lands under the injected vendor_base
    (StorageLayout.vendor on /mnt/data), NEVER under the repo working tree.
* IDEMPOTENCY ............ a dep already present at the pinned commit with a
    matching digest is a NO-OP: the Fetcher.fetch is NOT invoked the second time,
    and the tree is byte-identical across the re-run.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

# Hard import (NOT importorskip): until T-002 lands, this raises at collection
# time and the suite goes RED — the point of a test-first contract.
from lab import fetch_deps

# =============================================================================
# Test doubles: a FAKE Fetcher at the port boundary (NO network, NO real git).
# =============================================================================


def _write_tree(root: Path, files: dict[str, bytes]) -> None:
    """Materialize a {relpath: bytes} mapping as a directory tree under root."""
    for rel, data in files.items():
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)


class FakeFetcher:
    """In-memory boundary fake: "fetches" a scripted tree, NO network/git.

    Maps `dep.pinned_commit` -> a {relpath: bytes} tree. On `fetch`, it records
    the call (so idempotency can assert non-invocation), copies the scripted tree
    into `dest`, and reports the resolved commit + the SAME deterministic digest
    the production code computes via `fetch_deps.tree_sha256`. It satisfies the
    `Fetcher` Protocol structurally — exercised, never mocked.
    """

    def __init__(self, trees_by_commit: dict[str, dict[str, bytes]]) -> None:
        self._trees = trees_by_commit
        self.fetch_calls: list[str] = []  # dep.name per invocation, in order

    def fetch(self, dep: fetch_deps.DepSpec, dest: Path) -> fetch_deps.FetchResult:
        self.fetch_calls.append(dep.name)
        if dep.pinned_commit not in self._trees:
            raise AssertionError(
                f"fake has no scripted tree for commit {dep.pinned_commit!r}"
            )
        dest.mkdir(parents=True, exist_ok=True)
        _write_tree(dest, self._trees[dep.pinned_commit])
        digest = fetch_deps.tree_sha256(dest)
        return fetch_deps.FetchResult(
            name=dep.name,
            status=fetch_deps.FetchStatus.FETCHED,
            resolved_commit=dep.pinned_commit,
            sha256=digest,
            dest=dest,
        )


def _digest_of(files: dict[str, bytes]) -> str:
    """Compute the expected tree digest for a {relpath: bytes} tree, in-test.

    Independent re-derivation of the pinned tree_sha256 algorithm, so the digest
    a DepSpec pins is computed WITHOUT calling the unit under test. If the
    implementation's tree_sha256 disagrees with this, that is a real contract
    break, not a tautology.
    """
    lines = []
    for rel in sorted(files):
        body_hash = hashlib.sha256(files[rel]).hexdigest()
        lines.append(f"{rel}\0{body_hash}\n")
    return hashlib.sha256("".join(lines).encode("utf-8")).hexdigest()


# A canonical good tree + its pinned commit/digest, reused across tests.
_GOOD_COMMIT = "d277a8693e588684e951dddb0733809e53881a3c"
_GOOD_TREE: dict[str, bytes] = {
    "README.md": b"vulhub pinned\n",
    "cve/poc.yml": b"id: CVE-EXAMPLE\n",
}


def _good_spec(digest: str, *, name: str = "vulhub", subdir: str = "vulhub") -> "fetch_deps.DepSpec":
    return fetch_deps.DepSpec(
        name=name,
        repo_url="file:///offline/fake.git",
        pinned_commit=_GOOD_COMMIT,
        sha256=digest,
        dest_subdir=subdir,
    )


# =============================================================================
# 1. The integrity gate — rejects a checksum mismatch, loudly, no garbage left.
# =============================================================================


def test_fetch_deps_rejects_checksum_mismatch(tmp_path: Path) -> None:
    """A dep whose fetched tree digest != the pinned sha256 FAILS loudly.

    The fetch must raise (surfaced as AggregateFetchError naming the dep +
    expected-vs-actual), and must NOT leave a populated/garbage dep tree in the
    vendor dest — a half-written dep that later reads as "present" would silently
    poison every downstream consumer. This is THE integrity gate.
    """
    vendor = tmp_path / "vendor"
    fetcher = FakeFetcher({_GOOD_COMMIT: _GOOD_TREE})
    # Pin a digest that does NOT match the tree the fetcher will produce.
    wrong_digest = "0" * 64
    spec = _good_spec(wrong_digest)

    with pytest.raises(fetch_deps.FetchError) as excinfo:
        fetch_deps.fetch_all([spec], fetcher, vendor)

    msg = str(excinfo.value)
    assert "vulhub" in msg, "mismatch error must name which dep failed"
    assert wrong_digest in msg, "mismatch error must surface the EXPECTED digest"
    actual = _digest_of(_GOOD_TREE)
    assert actual in msg, "mismatch error must surface the ACTUAL digest"

    # No garbage left behind: the dest must not survive as a valid-looking dep.
    dest = vendor / "vulhub"
    leftover = list(dest.rglob("*")) if dest.exists() else []
    assert leftover == [], (
        "checksum mismatch left a partial/garbage dep at the dest — a later run "
        "could mistake it for a valid present dep"
    )


def test_checksum_mismatch_error_is_typed_and_carries_fields(tmp_path: Path) -> None:
    """The mismatch raises ChecksumMismatch (under the aggregate) with fields.

    Callers should branch on a typed error carrying .name/.expected/.actual, not
    parse a string. The aggregate wraps the per-dep typed errors.
    """
    vendor = tmp_path / "vendor"
    fetcher = FakeFetcher({_GOOD_COMMIT: _GOOD_TREE})
    spec = _good_spec("0" * 64)

    with pytest.raises(fetch_deps.AggregateFetchError) as excinfo:
        fetch_deps.fetch_all([spec], fetcher, vendor)

    errors = excinfo.value.errors
    assert len(errors) == 1, "exactly one dep failed; aggregate should hold one error"
    err = errors[0]
    assert isinstance(err, fetch_deps.ChecksumMismatch)
    assert err.name == "vulhub"
    assert err.expected == "0" * 64
    assert err.actual == _digest_of(_GOOD_TREE)


# =============================================================================
# 2. Idempotency — a valid present dep is a NO-OP (fetcher NOT re-invoked).
# =============================================================================


def test_fetch_deps_idempotent(tmp_path: Path) -> None:
    """Re-fetching an already-present, correctly-pinned, matching dep is a no-op.

    First run fetches once (one Fetcher.fetch call). Second run must short-circuit
    on the existing valid dep: the Fetcher is NOT invoked again (no re-clone / no
    network via the fake), the result reports ALREADY_PRESENT, and the tree is
    byte-identical to the first run.
    """
    vendor = tmp_path / "vendor"
    digest = _digest_of(_GOOD_TREE)
    spec = _good_spec(digest)
    fetcher = FakeFetcher({_GOOD_COMMIT: _GOOD_TREE})

    first = fetch_deps.fetch_all([spec], fetcher, vendor)
    assert fetcher.fetch_calls == ["vulhub"], "first run should fetch exactly once"
    assert first[0].status is fetch_deps.FetchStatus.FETCHED

    dest = vendor / "vulhub"
    snapshot = {p.relative_to(dest).as_posix(): p.read_bytes()
                for p in sorted(dest.rglob("*")) if p.is_file()}

    second = fetch_deps.fetch_all([spec], fetcher, vendor)
    assert fetcher.fetch_calls == ["vulhub"], (
        "second run re-invoked the Fetcher — not idempotent (re-clone/network)"
    )
    assert second[0].status is fetch_deps.FetchStatus.ALREADY_PRESENT, (
        "an already-valid dep must report ALREADY_PRESENT, not FETCHED"
    )

    after = {p.relative_to(dest).as_posix(): p.read_bytes()
             for p in sorted(dest.rglob("*")) if p.is_file()}
    assert after == snapshot, "idempotent re-run changed the dep tree on disk"


# =============================================================================
# 3a. Wrong-commit dep on disk is detected & corrected — not silently accepted.
# =============================================================================


def test_present_dep_at_wrong_commit_is_refetched_to_pinned_commit(tmp_path: Path) -> None:
    """A dep already on disk but at the WRONG commit is re-fetched to the pin.

    Pre-seed the dest with a tree whose content does NOT match the pinned digest
    (simulating a stale/wrong checkout). fetch_all must NOT accept it as present;
    it must re-fetch to the pinned commit so the resulting tree matches the pin.
    """
    vendor = tmp_path / "vendor"
    dest = vendor / "vulhub"
    # Stale tree on disk (wrong content => wrong digest vs the pin).
    _write_tree(dest, {"README.md": b"STALE wrong-commit checkout\n"})

    digest = _digest_of(_GOOD_TREE)
    spec = _good_spec(digest)
    fetcher = FakeFetcher({_GOOD_COMMIT: _GOOD_TREE})

    results = fetch_deps.fetch_all([spec], fetcher, vendor)

    assert fetcher.fetch_calls == ["vulhub"], (
        "a wrong-commit present dep must be re-fetched, not silently accepted"
    )
    assert results[0].status is fetch_deps.FetchStatus.FETCHED
    assert fetch_deps.tree_sha256(dest) == digest, (
        "after correcting a wrong-commit dep the tree must match the pinned digest"
    )


# =============================================================================
# 3b. Dest is ALWAYS under the injected vendor base, never the repo root.
# =============================================================================


def test_dest_lives_under_injected_vendor_base_never_repo_root(tmp_path: Path) -> None:
    """Every fetched dep resolves UNDER the injected vendor base, not the repo.

    Guards the /mnt/data invariant: multi-GB vendored clones must never land on
    the 244 GB root / inside the git working tree.
    """
    vendor = tmp_path / "mnt-data" / "purple-range" / "vendor"
    digest = _digest_of(_GOOD_TREE)
    spec = _good_spec(digest)
    fetcher = FakeFetcher({_GOOD_COMMIT: _GOOD_TREE})

    results = fetch_deps.fetch_all([spec], fetcher, vendor)

    repo_root = Path(__file__).resolve().parent.parent
    resolved = results[0].dest.resolve()
    assert resolved.is_relative_to(vendor.resolve()), (
        f"dest {resolved} escaped the injected vendor base {vendor.resolve()}"
    )
    assert not resolved.is_relative_to(repo_root), (
        f"dest {resolved} resolves under the repo working tree {repo_root}"
    )
    assert resolved == (vendor / "vulhub").resolve(), (
        "dest must be vendor_base/<dest_subdir>"
    )


# =============================================================================
# 3c. A successful fetch is reported: status + resolved commit + digest + dest.
# =============================================================================


def test_successful_fetch_reports_status_commit_and_checksum(tmp_path: Path) -> None:
    """A FetchResult records what actually happened: status, commit, digest, dest."""
    vendor = tmp_path / "vendor"
    digest = _digest_of(_GOOD_TREE)
    spec = _good_spec(digest)
    fetcher = FakeFetcher({_GOOD_COMMIT: _GOOD_TREE})

    result = fetch_deps.fetch_all([spec], fetcher, vendor)[0]

    assert result.name == "vulhub"
    assert result.status is fetch_deps.FetchStatus.FETCHED
    assert result.resolved_commit == _GOOD_COMMIT, "must report the resolved commit"
    assert result.sha256 == digest, "must report the verified tree digest"
    assert result.dest == vendor / "vulhub"


# =============================================================================
# 3d. Multiple deps fetch independently — one bad checksum doesn't skip the rest.
# =============================================================================


def test_multiple_deps_one_bad_checksum_does_not_skip_the_rest(tmp_path: Path) -> None:
    """COLLECT-ALL-ERRORS: a good dep still fetches; the bad one is reported.

    Pins the fail policy: fetch_all attempts EVERY spec, fetches the good ones,
    and raises an AggregateFetchError naming only the failures — it does not
    fail-fast and silently skip the remaining (good) deps.
    """
    vendor = tmp_path / "vendor"
    good_commit = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    good_tree = {"ok.txt": b"good dep\n"}
    bad_commit = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
    bad_tree = {"x.txt": b"bad dep\n"}

    good = fetch_deps.DepSpec(
        name="art", repo_url="file:///offline/art.git",
        pinned_commit=good_commit, sha256=_digest_of(good_tree), dest_subdir="art",
    )
    bad = fetch_deps.DepSpec(
        name="goad", repo_url="file:///offline/goad.git",
        pinned_commit=bad_commit, sha256="f" * 64, dest_subdir="goad",
    )
    fetcher = FakeFetcher({good_commit: good_tree, bad_commit: bad_tree})

    with pytest.raises(fetch_deps.AggregateFetchError) as excinfo:
        fetch_deps.fetch_all([good, bad], fetcher, vendor)

    # The good dep was attempted AND landed correctly despite the bad sibling.
    assert "art" in fetcher.fetch_calls and "goad" in fetcher.fetch_calls, (
        "fail policy must attempt every dep, not stop at the first failure"
    )
    good_dest = vendor / "art"
    assert fetch_deps.tree_sha256(good_dest) == _digest_of(good_tree), (
        "the good dep should be fully fetched even though a sibling failed"
    )
    # Only the bad dep is reported as an error.
    failed_names = {e.name for e in excinfo.value.errors}
    assert failed_names == {"goad"}, f"only goad should be reported, got {failed_names}"


# =============================================================================
# 3e. Pending-pin (SecGen / Q-011) refuses — never clones master.
# =============================================================================


def test_pending_pin_refuses_and_never_fetches(tmp_path: Path) -> None:
    """A DepSpec with pinned_commit=None REFUSES with a Q-011 PendingPinError.

    An unset pin must not be able to masquerade as a fetched dep by quietly
    cloning master. The Fetcher must NOT be invoked for a pending-pin dep, and
    the error must name the dep + Q-011 so the operator knows why.
    """
    vendor = tmp_path / "vendor"
    secgen = fetch_deps.DepSpec(
        name="secgen", repo_url="file:///offline/secgen.git",
        pinned_commit=None, sha256=None, dest_subdir="secgen",
    )
    fetcher = FakeFetcher({})  # no trees scripted — must never be called

    with pytest.raises(fetch_deps.FetchError) as excinfo:
        fetch_deps.fetch_all([secgen], fetcher, vendor)

    errors = getattr(excinfo.value, "errors", [excinfo.value])
    assert any(isinstance(e, fetch_deps.PendingPinError) for e in errors), (
        "a pending pin must raise PendingPinError, not a generic failure"
    )
    msg = str(excinfo.value)
    assert "secgen" in msg.lower(), "pending-pin error must name the dep"
    assert "Q-011" in msg, "pending-pin error must reference the open question Q-011"
    assert fetcher.fetch_calls == [], (
        "the Fetcher must NOT be invoked for a pending-pin dep (no clone of master)"
    )
    assert not (vendor / "secgen").exists() or list((vendor / "secgen").rglob("*")) == [], (
        "a pending-pin dep must leave no dep tree on disk"
    )


# =============================================================================
# 3f. The REAL manifest of pins is well-formed and honest about SecGen.
# =============================================================================


def test_manifest_has_pinned_commits_for_vulhub_art_goad_and_secgen_pending() -> None:
    """The loaded manifest pins Vulhub/ART/GOAD and marks SecGen pending (None).

    Cheap guard that the pins read from ARCHITECTURE.md "Pinned versions" are
    present and non-empty for the three resolved deps, and that SecGen is
    EXPLICITLY pending (pinned_commit is None) so an unset pin cannot masquerade
    as a fetched dep. Asserts the two ARCHITECTURE-authoritative commit hashes.
    """
    manifest = {d.name.lower(): d for d in fetch_deps.load_manifest()}

    for resolved in ("vulhub", "atomic-red-team", "goad"):
        assert resolved in manifest, f"manifest is missing {resolved!r}"
        assert manifest[resolved].pinned_commit, (
            f"{resolved} must have a non-empty pinned_commit"
        )

    # The two ARCHITECTURE.md-authoritative commit pins, verbatim.
    assert manifest["vulhub"].pinned_commit == (
        "d277a8693e588684e951dddb0733809e53881a3c"
    )
    assert manifest["atomic-red-team"].pinned_commit == (
        "daee1d5098b5a03c260835f87c33c3814c4695fa"
    )

    # SecGen is explicitly pending per Q-011 — pin NOT yet selected.
    assert "secgen" in manifest, "manifest must list SecGen (as pending)"
    assert manifest["secgen"].pinned_commit is None, (
        "SecGen pin is not selected yet (Q-011) — it must be None, not a guess"
    )


def test_every_resolved_manifest_dep_carries_a_sha256_gate() -> None:
    """Each non-pending dep pins a sha256 so the integrity gate has something to check.

    A resolved dep (pinned_commit set) with sha256=None would make the checksum
    gate a no-op — the spec requires "verifies SHA256; refuses on mismatch".
    SecGen (pending) is exempt: it has neither a commit nor a checksum yet.
    """
    for dep in fetch_deps.load_manifest():
        if dep.pinned_commit is None:
            assert dep.sha256 is None, (
                f"{dep.name}: a pending pin must not carry a checksum (nothing to pin yet)"
            )
        else:
            assert dep.sha256, (
                f"{dep.name}: a resolved pin must carry a non-empty sha256 integrity gate"
            )


# =============================================================================
# tree_sha256 determinism — the gate is only honest if the digest is stable.
# =============================================================================


def test_tree_sha256_is_deterministic_and_content_addressed(tmp_path: Path) -> None:
    """Same content+paths => same digest; different content => different digest.

    Pins WHY the tree digest is a valid integrity gate: it depends only on path +
    file content (sorted), so the same commit checked out twice yields the same
    value, while any content change flips it.
    """
    a = tmp_path / "a"
    b = tmp_path / "b"
    _write_tree(a, _GOOD_TREE)
    _write_tree(b, _GOOD_TREE)

    assert fetch_deps.tree_sha256(a) == fetch_deps.tree_sha256(b), (
        "identical trees must hash identically (determinism)"
    )
    assert fetch_deps.tree_sha256(a) == _digest_of(_GOOD_TREE), (
        "tree_sha256 must match the independently-derived path\\0sha256 manifest"
    )

    # A single byte changed flips the digest.
    (b / "README.md").write_bytes(b"tampered\n")
    assert fetch_deps.tree_sha256(b) != fetch_deps.tree_sha256(a), (
        "a content change must change the tree digest (it is the integrity gate)"
    )


def test_tree_sha256_ignores_git_internals(tmp_path: Path) -> None:
    """The digest excludes the .git directory so it is clone-layout-independent.

    A real `git clone` writes a .git dir whose pack layout varies by git version
    and clone time; including it would make the digest non-deterministic and the
    gate worthless. The pinned algorithm excludes .git.
    """
    root = tmp_path / "repo"
    _write_tree(root, _GOOD_TREE)
    baseline = fetch_deps.tree_sha256(root)

    # Simulate git internals; the digest must be unaffected.
    _write_tree(root, {".git/HEAD": b"ref: refs/heads/main\n",
                       ".git/objects/pack/whatever.pack": b"\x00\x01\x02"})
    assert fetch_deps.tree_sha256(root) == baseline, (
        "tree_sha256 must ignore the .git directory (clone-layout-dependent)"
    )


# =============================================================================
# Conformance: the FAKE satisfies the Fetcher port (no mock of the unit).
# =============================================================================


def test_fake_fetcher_conforms_to_fetcher_port() -> None:
    """The FakeFetcher we test through structurally IS a Fetcher.

    If the fake cannot satisfy the port, the port is wrong (charter #5). This
    keeps the boundary fake honest against the same contract the real adapter
    must meet.
    """
    fetcher = FakeFetcher({})
    assert isinstance(fetcher, fetch_deps.Fetcher), (
        "FakeFetcher must satisfy the Fetcher Protocol"
    )


# =============================================================================
# CLI `fetch` action — main() must actually FETCH, not just list (PR fix 1).
# These stay fully OFFLINE: a FakeFetcher + an injected vendor_base + injected
# specs at the same `main(argv, *, fetcher, vendor_base, specs)` seam cli.py uses.
# =============================================================================


def test_main_fetch_invokes_fetch_all_via_injected_fetcher(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`main(["fetch"], fetcher=fake, vendor_base=tmp, specs=[...])` runs fetch_all.

    The bug this guards: `main()` used to only LIST the manifest; fetch_all and
    GitFetcher were reachable only from tests. The `fetch` action must drive
    fetch_all through the injected fetcher and report success per dep.
    """
    digest = _digest_of(_GOOD_TREE)
    spec = _good_spec(digest)
    fetcher = FakeFetcher({_GOOD_COMMIT: _GOOD_TREE})

    rc = fetch_deps.main(
        ["fetch"], fetcher=fetcher, vendor_base=tmp_path, specs=[spec]
    )

    assert rc == 0, "a fully-successful fetch must return 0"
    assert fetcher.fetch_calls == ["vulhub"], (
        "the fetch action must actually invoke the (injected) fetcher"
    )
    out = capsys.readouterr().out
    assert "vulhub" in out, "the fetch action must report a per-dep result line"


def test_main_fetch_reports_failure_nonzero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A ChecksumMismatch makes `fetch` return nonzero and name the failing dep.

    A real (non-TOFU) mismatch is a possible tampering signal — the operator
    must see the dep name and the alarming guidance, and the process must exit
    nonzero so CI/automation does not treat a poisoned fetch as success.
    """
    # Pin a REAL 64-hex digest that does not match the tree => alarming mismatch.
    spec = _good_spec("0" * 64)
    fetcher = FakeFetcher({_GOOD_COMMIT: _GOOD_TREE})

    rc = fetch_deps.main(
        ["fetch"], fetcher=fetcher, vendor_base=tmp_path, specs=[spec]
    )

    assert rc != 0, "any failed dep must make the fetch action return nonzero"
    out = capsys.readouterr().out
    assert "vulhub" in out, "the failure report must name the failing dep"


def test_main_fetch_tofu_first_fetch_message_is_legible(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A TOFU-sentinel mismatch reads as 'first fetch, record the sha256', not alarm.

    Distinguishing the TOFU first-run case from a real mismatch matters for a
    security tool: the first fetch should tell the operator to verify + record
    the printed sha256, and must print the actual digest to record.
    """
    spec = _good_spec(fetch_deps.TOFU_PENDING_SHA256)
    fetcher = FakeFetcher({_GOOD_COMMIT: _GOOD_TREE})

    rc = fetch_deps.main(
        ["fetch"], fetcher=fetcher, vendor_base=tmp_path, specs=[spec]
    )

    assert rc != 0, "an unpinned (TOFU) dep has not yet passed the gate => nonzero"
    out = capsys.readouterr().out.lower()
    assert "tofu" in out or "first fetch" in out, (
        "the TOFU first-fetch case must explain itself as trust-on-first-use"
    )
    assert _digest_of(_GOOD_TREE) in out, (
        "the TOFU first-fetch case must print the actual sha256 to record"
    )


# =============================================================================
# OPTIONAL offline integration: the REAL git adapter vs the SAME contract.
# Still NO network — builds a local repo in tmp_path. Guards fake/real drift.
# =============================================================================


def _git(repo: Path, *args: str) -> None:
    import subprocess

    subprocess.run(
        ["git", "-c", "user.email=t@offline", "-c", "user.name=offline",
         "-c", "commit.gpgsign=false", *args],
        cwd=repo, check=True, capture_output=True,
    )


@pytest.mark.skipif(
    __import__("shutil").which("git") is None, reason="git not installed"
)
def test_real_git_fetcher_satisfies_same_contract_offline(tmp_path: Path) -> None:
    """The production GitFetcher checks out the pinned commit from a LOCAL repo.

    Builds a real git repo in tmp_path (no network), commits a known tree, and
    drives the real adapter through `fetch_all`. Proves the real adapter computes
    the SAME tree digest and resolves the SAME commit as the fake — the anti-drift
    guard. If the real adapter is named differently, this locks GitFetcher.
    """
    src = tmp_path / "src-repo"
    src.mkdir()
    _git(src, "init", "-q")
    _write_tree(src, {"README.md": b"real git tree\n", "sub/poc.yml": b"id: X\n"})
    _git(src, "add", "-A")
    _git(src, "commit", "-q", "-m", "pinned tree")

    import subprocess
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=src, check=True, capture_output=True, text=True
    ).stdout.strip()

    # Expected digest computed by checking out into a scratch dir? No — compute
    # over the working tree minus .git, matching the pinned algorithm.
    expected_digest = _digest_of({"README.md": b"real git tree\n", "sub/poc.yml": b"id: X\n"})

    vendor = tmp_path / "vendor"
    spec = fetch_deps.DepSpec(
        name="localdep", repo_url=str(src), pinned_commit=commit,
        sha256=expected_digest, dest_subdir="localdep",
    )

    fetcher = fetch_deps.GitFetcher()
    assert isinstance(fetcher, fetch_deps.Fetcher), "GitFetcher must satisfy the port"

    results = fetch_deps.fetch_all([spec], fetcher, vendor)
    assert results[0].resolved_commit == commit, "real adapter must resolve the pinned commit"
    assert results[0].sha256 == expected_digest, (
        "real adapter's tree digest must match the pinned algorithm (no drift vs fake)"
    )
    assert fetch_deps.tree_sha256(vendor / "localdep") == expected_digest
