"""Contract tests for the repo size-guard (T-001 forward guard).

The size-guard is the *forward* deliverable of T-001: a Python-stdlib script,
invoked by CI's ``size-guard`` stage, that prevents future bloat from ever
landing in the tracked tree. These tests pin its behavioural contract BEFORE
any implementation exists.

Locked interface (see module docstring of ``scripts/size_guard.py`` once
implemented):

    find_violations(
        root: Path,
        *,
        max_blob_bytes: int = 5 * 1024 * 1024,    # 5 MiB per-file cap
        max_total_bytes: int = 50 * 1024 * 1024,  # 50 MiB whole-tree cap
    ) -> list[Violation]

    Violation:
        - .path  : pathlib.Path or str naming the offending file (for the
                   total-exceeded rule, .path names the scanned root)
        - .size  : int bytes (the file's size, or the total for total-exceeded)
        - .rule  : str, one of {"oversized-blob", "total-exceeded"}

    main(argv: list[str] | None = None) -> int
        Thin CLI: prints violations, returns/exits nonzero when any exist,
        zero when clean. argv[0] is the root to scan.

Behavioural decisions locked here (so the implementer cannot drift):
  * BOUNDARY RULE is STRICTLY GREATER-THAN: a file of *exactly* max_blob_bytes
    is OK; only ``size > max_blob_bytes`` is an oversized-blob violation.
    Same for the total: ``total > max_total_bytes`` is a violation; a total
    equal to the cap passes. (Chosen so the documented cap is the largest
    *allowed* value, not the first *rejected* one.)
  * The walk SKIPS ignored / work dirs so the guard mirrors the *tracked*
    tree, not scratch space: .git, vendor/, __pycache__, .pytest_cache,
    node_modules. Files inside those never produce a violation and never
    count toward the total.
  * Symlinks are NOT followed (no descent through a symlinked dir), so a
    symlink loop cannot hang the walk.

These tests use the PURE function against a tmp tree (no real git repo, no
git binary, no subprocess) except for the single CLI exit-code test.

Sparse files: big files are created via seek+single-byte-write so the test
stays fast and cheap on disk while reporting a real logical size.
"""

from __future__ import annotations

import importlib
import subprocess
import sys
from pathlib import Path

import pytest

MB = 1024 * 1024

# Default caps the guard ships with (mirrored here so tests are explicit about
# the contract rather than depending on the import to read them).
DEFAULT_MAX_BLOB = 5 * MB
DEFAULT_MAX_TOTAL = 50 * MB


# ---------------------------------------------------------------------------
# Import the unit under test. Until scripts/size_guard.py exists this is the
# expected first RED (collection/import error). Once the skeleton exists the
# behavioural assertions below drive the implementation.
# ---------------------------------------------------------------------------

# Ensure scripts/ (sibling of tests/) is importable as `size_guard`.
REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

size_guard = importlib.import_module("size_guard")
find_violations = size_guard.find_violations


# ---------------------------------------------------------------------------
# Helpers — boundary plumbing, kept out of the assertions.
# ---------------------------------------------------------------------------

def write_file(path: Path, n_bytes: int) -> Path:
    """Create a file of logical size ``n_bytes`` cheaply (sparse).

    seek(n-1)+write one byte yields a file whose stat().st_size == n without
    physically writing n bytes. For n == 0 we just touch.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as fh:
        if n_bytes > 0:
            fh.seek(n_bytes - 1)
            fh.write(b"\0")
    assert path.stat().st_size == n_bytes, "test fixture must have the size it claims"
    return path


def rules(violations) -> list[str]:
    return [v.rule for v in violations]


def paths(violations) -> list[str]:
    return [str(v.path) for v in violations]


# ---------------------------------------------------------------------------
# 1. Acceptance test named in the spec.
# ---------------------------------------------------------------------------

def test_size_guard_passes(tmp_path):
    """A clean tree of small files yields ZERO violations."""
    write_file(tmp_path / "README.md", 200)
    write_file(tmp_path / "src" / "main.py", 4 * 1024)
    write_file(tmp_path / "docs" / "spec.md", 12 * 1024)

    violations = find_violations(tmp_path)

    assert violations == [], (
        f"clean small tree must produce no violations, got {rules(violations)}"
    )


# ---------------------------------------------------------------------------
# 2. Oversized single blob.
# ---------------------------------------------------------------------------

def test_size_guard_fails_on_oversized_blob(tmp_path):
    """A 6 MiB file → exactly one oversized-blob violation naming that file."""
    write_file(tmp_path / "tiny.txt", 100)
    big = write_file(tmp_path / "assets" / "huge.bin", 6 * MB)

    violations = find_violations(tmp_path)

    oversized = [v for v in violations if v.rule == "oversized-blob"]
    assert len(oversized) == 1, (
        f"exactly one oversized-blob expected, got rules={rules(violations)}"
    )
    assert Path(oversized[0].path) == big, (
        "the violation must name the offending file"
    )


def test_oversized_blob_reports_actual_size(tmp_path):
    """The oversized-blob violation carries the file's real byte size."""
    big = write_file(tmp_path / "huge.bin", 6 * MB)

    [v] = [v for v in find_violations(tmp_path) if v.rule == "oversized-blob"]

    assert v.size == 6 * MB, "violation.size must be the file's actual size in bytes"
    assert Path(v.path) == big


# ---------------------------------------------------------------------------
# 3. Total cap exceeded (injected small cap keeps the test fast).
# ---------------------------------------------------------------------------

def test_size_guard_fails_when_total_exceeds_cap(tmp_path):
    """Many small files summing over an injected total cap → total-exceeded."""
    # 10 files of 100 KiB = ~1 MiB total; cap it at 500 KiB so we trip total
    # WITHOUT any single file tripping the per-blob cap.
    for i in range(10):
        write_file(tmp_path / f"f{i}.dat", 100 * 1024)

    violations = find_violations(
        tmp_path,
        max_blob_bytes=1 * MB,        # no single file is oversized
        max_total_bytes=500 * 1024,   # but the sum is
    )

    total_v = [v for v in violations if v.rule == "total-exceeded"]
    assert len(total_v) == 1, (
        f"expected one total-exceeded violation, got rules={rules(violations)}"
    )
    assert total_v[0].size >= 10 * 100 * 1024, (
        "total-exceeded.size must report the summed tree size"
    )
    assert not any(v.rule == "oversized-blob" for v in violations), (
        "no single file should trip the per-blob cap in this scenario"
    )


# ---------------------------------------------------------------------------
# 4. Ignored / work dirs are skipped.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("ignored_dir", ["vendor", "__pycache__", ".git", ".pytest_cache", "node_modules"])
def test_size_guard_skips_ignored_dirs(tmp_path, ignored_dir):
    """A 6 MiB blob inside an ignored/work dir produces NO violation."""
    write_file(tmp_path / "kept.txt", 100)
    write_file(tmp_path / ignored_dir / "huge.bin", 6 * MB)

    violations = find_violations(tmp_path)

    assert violations == [], (
        f"blob under {ignored_dir}/ must be ignored (gitignored/work dir), "
        f"got {rules(violations)} for {paths(violations)}"
    )


def test_ignored_dir_blob_does_not_count_toward_total(tmp_path):
    """Bytes under an ignored dir do not count toward the total cap either."""
    write_file(tmp_path / "kept.bin", 100 * 1024)          # 100 KiB tracked
    write_file(tmp_path / "vendor" / "blob.bin", 40 * MB)  # huge, ignored

    violations = find_violations(
        tmp_path,
        max_blob_bytes=1 * MB,
        max_total_bytes=1 * MB,  # tracked total (100 KiB) is well under
    )

    assert violations == [], (
        "vendor/ bytes must not count toward the total; "
        f"got {rules(violations)}"
    )


# ---------------------------------------------------------------------------
# 5. Edge cases.
# ---------------------------------------------------------------------------

def test_empty_tree_passes(tmp_path):
    """An empty directory tree is clean."""
    assert find_violations(tmp_path) == []


def test_file_exactly_at_blob_cap_is_allowed(tmp_path):
    """BOUNDARY: a file of EXACTLY max_blob_bytes passes (strict > only)."""
    write_file(tmp_path / "edge.bin", DEFAULT_MAX_BLOB)

    violations = find_violations(tmp_path)

    assert violations == [], (
        "a file exactly at the cap must be allowed; the rule is strictly >"
    )


def test_file_one_byte_over_blob_cap_is_a_violation(tmp_path):
    """BOUNDARY: max_blob_bytes + 1 is the first rejected size."""
    write_file(tmp_path / "edge.bin", DEFAULT_MAX_BLOB + 1)

    violations = find_violations(tmp_path)

    assert rules(violations) == ["oversized-blob"], (
        "one byte over the cap must trip oversized-blob"
    )


def test_total_exactly_at_cap_is_allowed(tmp_path):
    """BOUNDARY: total == max_total_bytes passes (strict > only)."""
    write_file(tmp_path / "a.bin", 300 * 1024)
    write_file(tmp_path / "b.bin", 200 * 1024)  # sum == 500 KiB exactly

    violations = find_violations(
        tmp_path,
        max_blob_bytes=1 * MB,
        max_total_bytes=500 * 1024,
    )

    assert violations == [], "total exactly at the cap must be allowed"


def test_symlink_dir_is_not_followed(tmp_path):
    """A symlinked directory is not descended into, so loops cannot hang."""
    real = tmp_path / "real"
    write_file(real / "small.txt", 100)
    # A self-referential symlink loop: link -> real, and real/back -> tmp_path.
    link = tmp_path / "link"
    link.symlink_to(real, target_is_directory=True)
    (real / "back").symlink_to(tmp_path, target_is_directory=True)

    # If the walk followed symlinks, this would recurse forever / raise.
    violations = find_violations(tmp_path)

    assert violations == [], (
        "symlinked dirs must not be followed; the walk must terminate cleanly"
    )


def test_nested_real_dirs_are_walked(tmp_path):
    """Real (non-ignored) nested dirs ARE scanned — guard sees deep blobs."""
    write_file(tmp_path / "a" / "b" / "c" / "deep.bin", 6 * MB)

    violations = find_violations(tmp_path)

    assert rules(violations) == ["oversized-blob"], (
        "a deep blob in a normal nested dir must still be caught"
    )


# ---------------------------------------------------------------------------
# 6. Thin CLI exit-code contract (the one subprocess test).
# ---------------------------------------------------------------------------

def test_size_guard_cli_exit_code(tmp_path):
    """CLI: nonzero exit on a dirty tree, zero on a clean tree."""
    script = SCRIPTS_DIR / "size_guard.py"

    # Dirty tree.
    dirty = tmp_path / "dirty"
    write_file(dirty / "ok.txt", 100)
    write_file(dirty / "huge.bin", 6 * MB)
    dirty_run = subprocess.run(
        [sys.executable, str(script), str(dirty)],
        capture_output=True,
        text=True,
    )
    assert dirty_run.returncode != 0, (
        f"dirty tree must exit nonzero; stdout={dirty_run.stdout!r} "
        f"stderr={dirty_run.stderr!r}"
    )

    # Clean tree.
    clean = tmp_path / "clean"
    write_file(clean / "ok.txt", 100)
    clean_run = subprocess.run(
        [sys.executable, str(script), str(clean)],
        capture_output=True,
        text=True,
    )
    assert clean_run.returncode == 0, (
        f"clean tree must exit zero; stdout={clean_run.stdout!r} "
        f"stderr={clean_run.stderr!r}"
    )
