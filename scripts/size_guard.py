"""Repo size-guard — the forward deliverable of T-001.

A Python-stdlib-only script (invoked by CI's ``size-guard`` stage) that
prevents future bloat from landing in the tracked tree. It walks the files
under a root and reports two kinds of violation:

  * ``oversized-blob``  — a single file larger than ``max_blob_bytes``.
  * ``total-exceeded``  — the summed size of all scanned files larger than
    ``max_total_bytes``.

Behavioural contract (pinned by ``tests/test_size_guard.py`` — the test wins):

  * BOUNDARY is STRICTLY GREATER-THAN. A file of *exactly* ``max_blob_bytes``
    passes; only ``size > max_blob_bytes`` trips ``oversized-blob``. Same for
    the total: ``total > max_total_bytes`` is a violation, ``total ==`` cap
    passes. The documented cap is the largest *allowed* value.
  * The walk SKIPS ignored / work dirs so the guard mirrors the *tracked*
    tree, not scratch space: ``.git``, ``vendor``, ``__pycache__``,
    ``.pytest_cache``, ``node_modules``. Files inside those never produce a
    violation and never count toward the total.
  * Symlinked directories are NOT followed, so a symlink loop cannot hang the
    walk (``os.walk(..., followlinks=False)``).

Pure ``find_violations`` does the work; ``main`` is a thin CLI over it.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

# 5 MiB per-file cap; 50 MiB whole-tree cap. These are the shipped defaults.
DEFAULT_MAX_BLOB_BYTES = 5 * 1024 * 1024
DEFAULT_MAX_TOTAL_BYTES = 50 * 1024 * 1024

# Directories that mirror gitignored / work space — never scanned, never
# counted. Mirrors the .gitignore'd dirs + the /mnt/data storage layout's
# in-repo equivalents (vendor/) so the guard reflects the tracked tree.
SKIP_DIRS = frozenset(
    {".git", "vendor", "__pycache__", ".pytest_cache", "node_modules"}
)

RULE_OVERSIZED_BLOB = "oversized-blob"
RULE_TOTAL_EXCEEDED = "total-exceeded"


@dataclass(frozen=True)
class Violation:
    """A single size-guard finding.

    ``path`` is the offending file, except for ``total-exceeded`` where it is
    the scanned root. ``size`` is the file's real byte size, or the summed
    tree total for ``total-exceeded``. ``rule`` is one of the RULE_* constants.
    """

    path: Path
    size: int
    rule: str


def find_violations(
    root: Path,
    *,
    max_blob_bytes: int = DEFAULT_MAX_BLOB_BYTES,
    max_total_bytes: int = DEFAULT_MAX_TOTAL_BYTES,
) -> list[Violation]:
    """Walk ``root`` and return size-guard violations (empty when clean).

    Skips :data:`SKIP_DIRS` entirely (their bytes do not count toward the
    total) and does not follow symlinked directories.
    """
    root = Path(root)
    violations: list[Violation] = []
    total = 0

    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        # Prune skipped dirs in place so os.walk does not descend into them.
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]

        for filename in filenames:
            file_path = Path(dirpath) / filename
            # A symlinked file (or a broken link) reports its own logical
            # size via lstat; we never follow it to a target.
            size = file_path.lstat().st_size
            total += size
            if size > max_blob_bytes:
                violations.append(
                    Violation(path=file_path, size=size, rule=RULE_OVERSIZED_BLOB)
                )

    if total > max_total_bytes:
        violations.append(
            Violation(path=root, size=total, rule=RULE_TOTAL_EXCEEDED)
        )

    return violations


def main(argv: list[str] | None = None) -> int:
    """Thin CLI: scan ``argv[0]`` (default "."), print findings, return code.

    Returns nonzero when any violation exists, zero when the tree is clean.
    """
    if argv is None:
        argv = sys.argv[1:]
    root = Path(argv[0]) if argv else Path(".")

    violations = find_violations(root)

    if not violations:
        print(f"size-guard: OK — no violations under {root}")
        return 0

    print(f"size-guard: {len(violations)} violation(s) under {root}:")
    for v in violations:
        print(f"  [{v.rule}] {v.path} ({v.size} bytes)")
    return 1


if __name__ == "__main__":
    sys.exit(main())
