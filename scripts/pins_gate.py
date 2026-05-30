"""Dependency-pin enforcement gate — the forward deliverable of T-003.

A Python-stdlib-only scanner (invoked by CI's ``pins`` stage) that fails any
unpinned dependency before it lands. ARCHITECTURE.md (~L553) defines the gate
as: "regex gate: fail on ``:latest``, unpinned ``box_version``, bare
``git clone`` without pinned ref". We add ``.md`` fenced-block scanning because
run-guides ship real, copy-pasteable commands.

Behavioural contract (pinned by ``tests/test_pins_gate.py`` — the test wins):

  * ``docker-latest``        — a Docker image ref pinned to ``:latest`` OR with
                               no tag/digest at all. A version tag
                               (``nginx:1.27.3``) or an ``@sha256`` digest is OK.
  * ``unpinned-box-version`` — a Vagrant ``config.vm.box`` (or yaml ``box:``)
                               with no accompanying ``box_version``/``version``
                               pin in the SAME FILE.
  * ``bare-git-clone``       — a ``git clone <url>`` with no pinned ref: no
                               inline ``--branch vX.Y.Z`` and no
                               ``git checkout <40-hex sha>`` (or ``--branch
                               vTAG``) within the next 3 non-blank lines.

  * SCANNED FILE SET: ``*.yml``, ``*.yaml``, ``Dockerfile`` (and
    ``*.Dockerfile``), ``docker-compose*.yml``, ``Vagrantfile`` (and
    ``*.Vagrantfile``), ``*.sh``, and ``*.md``. Other types are ignored.
  * MARKDOWN: only FENCED code blocks (delimited by lines beginning with
    ``` ``` ```) are scanned; prose is never flagged.

Pure ``find_pin_violations`` does the work; ``main`` is a thin CLI over it.
No git, network, or subprocess dependency — the root is injectable.
"""

from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

RULE_DOCKER_LATEST = "docker-latest"
RULE_UNPINNED_BOX = "unpinned-box-version"
RULE_BARE_GIT_CLONE = "bare-git-clone"

# Suffix / name patterns the scanner inspects. Everything else is ignored.
SCANNED_SUFFIXES = frozenset({".yml", ".yaml", ".sh", ".md", ".dockerfile", ".vagrantfile"})
SCANNED_NAMES = frozenset({"dockerfile", "vagrantfile"})

# Directories that mirror gitignored / work space — never scanned, matched by
# bare name anywhere in the tree.
SKIP_DIRS = frozenset(
    {".git", "vendor", "__pycache__", ".pytest_cache", "node_modules"}
)

# Path skipped by its ROOT-RELATIVE path (NOT bare name): the deliberately-bad
# pins corpus. Its fixtures intentionally carry the anti-patterns the gate
# detects, so scanning them would flag our own negative-test data. We match the
# relative path (not the bare dirname ``fixtures``) so that a real violation
# under any *other* future ``fixtures`` dir — e.g. the planned DETECT
# calibration-fixture dirs (PRD L171) — is still caught. (size_guard.py
# deliberately does NOT skip this: byte-size accounting must reflect the whole
# tracked tree, and large fixtures are exactly what it should still weigh.)
SKIP_RELATIVE_DIRS = frozenset({os.path.join("tests", "fixtures")})

# How many non-blank lines below a `git clone` may host the pinning checkout.
CLONE_NEAR_WINDOW = 3

# A 40-hex git commit SHA.
_SHA_RE = re.compile(r"\b[0-9a-fA-F]{40}\b")
# A version tag `--branch vX.Y.Z` (semver-ish) inline on a clone or a checkout.
_BRANCH_TAG_RE = re.compile(r"--branch[=\s]+v\d+(?:\.\d+)*\b")
# `git checkout <40-hex sha>` (allowing `git -C <dir> checkout <sha>`).
_CHECKOUT_SHA_RE = re.compile(r"\bgit\b.*\bcheckout\b.*[0-9a-fA-F]{40}\b")
# `git checkout` that pins via a version tag.
_CHECKOUT_TAG_RE = re.compile(r"\bgit\b.*\bcheckout\b.*\bv\d+(?:\.\d+)*\b")
# A `git clone <url>` invocation.
_GIT_CLONE_RE = re.compile(r"\bgit\s+clone\b")

# A docker image reference on a compose `image:` line.
_IMAGE_LINE_RE = re.compile(r"^\s*image:\s*(\S+)")
# A Dockerfile `FROM <ref> [AS alias]` line.
_FROM_LINE_RE = re.compile(r"^\s*FROM\s+(\S+)", re.IGNORECASE)

# A Vagrant `config.vm.box = "..."` assignment.
_VM_BOX_RE = re.compile(r"config\.vm\.box\s*=")
# A yaml `box:` key (but not `box_version:`).
_YAML_BOX_RE = re.compile(r"^\s*box:\s*\S")
# Any box-version pin present in the file (Vagrant or yaml form).
_BOX_VERSION_RE = re.compile(r"(box_version|version)\b")


@dataclass(frozen=True)
class PinViolation:
    """A single dependency-pin finding.

    ``path`` is the offending file, ``line`` the 1-based line number, ``rule``
    one of the RULE_* constants, and ``text`` the offending source line
    (rstripped).
    """

    path: Path
    line: int
    rule: str
    text: str


def _is_scanned(path: Path) -> bool:
    name = path.name.lower()
    if name in SCANNED_NAMES:
        return True
    return path.suffix.lower() in SCANNED_SUFFIXES


def _image_ref_is_pinned(ref: str) -> bool:
    """A docker image ref is pinned by an ``@sha256`` digest or a non-latest tag.

    The tag colon is the one after the final ``/`` (so a registry-with-port
    like ``host:5000/img`` is not mistaken for a tag), and ``:latest`` never
    pins.
    """
    if "@sha256:" in ref:
        return True
    last_segment = ref.rsplit("/", 1)[-1]
    if ":" not in last_segment:
        return False  # bare/untagged image
    tag = last_segment.rsplit(":", 1)[-1]
    return tag != "" and tag != "latest"


def _scan_docker(lines: list[str], path: Path) -> list[PinViolation]:
    """Flag compose ``image:`` and Dockerfile ``FROM`` refs that are unpinned."""
    found: list[PinViolation] = []
    for idx, raw in enumerate(lines, start=1):
        ref = None
        m = _IMAGE_LINE_RE.match(raw)
        if m:
            ref = m.group(1)
        else:
            m = _FROM_LINE_RE.match(raw)
            if m:
                ref = m.group(1)
        if ref is None:
            continue
        if not _image_ref_is_pinned(ref):
            found.append(
                PinViolation(path=path, line=idx, rule=RULE_DOCKER_LATEST, text=raw.rstrip())
            )
    return found


def _scan_box(lines: list[str], path: Path) -> list[PinViolation]:
    """Flag a Vagrant/yaml box reference with no box-version pin in the file."""
    has_version = any(_BOX_VERSION_RE.search(line) for line in lines)
    if has_version:
        return []
    found: list[PinViolation] = []
    for idx, raw in enumerate(lines, start=1):
        if _VM_BOX_RE.search(raw) or _YAML_BOX_RE.match(raw):
            found.append(
                PinViolation(path=path, line=idx, rule=RULE_UNPINNED_BOX, text=raw.rstrip())
            )
    return found


def _scan_git_clone(lines: list[str], path: Path) -> list[PinViolation]:
    """Flag a ``git clone`` not pinned inline or by a near-window checkout."""
    found: list[PinViolation] = []
    for idx, raw in enumerate(lines, start=1):
        if not _GIT_CLONE_RE.search(raw):
            continue
        if _BRANCH_TAG_RE.search(raw):
            continue  # inline `--branch vX.Y.Z` pins the clone
        if _clone_pinned_by_near_window(lines, idx):
            continue
        found.append(
            PinViolation(path=path, line=idx, rule=RULE_BARE_GIT_CLONE, text=raw.rstrip())
        )
    return found


def _clone_pinned_by_near_window(lines: list[str], clone_line: int) -> bool:
    """True if a pinning checkout appears in the next CLONE_NEAR_WINDOW non-blank lines."""
    seen = 0
    for raw in lines[clone_line:]:  # lines after the clone (clone_line is 1-based)
        if not raw.strip():
            continue  # blank lines do not count against the window
        seen += 1
        if seen > CLONE_NEAR_WINDOW:
            break
        if _CHECKOUT_SHA_RE.search(raw) or _CHECKOUT_TAG_RE.search(raw):
            return True
    return False


def _fenced_code_lines(lines: list[str]) -> list[str]:
    """Return the lines that fall INSIDE ``` fenced blocks, blanking the rest.

    Line positions are preserved (non-fenced lines become ""), so downstream
    line numbers stay 1-based against the original file. A fence toggles only
    when a line *begins* with ``` (CommonMark), so an inline triple-backtick in
    prose does not open a block.
    """
    out: list[str] = []
    in_fence = False
    for raw in lines:
        is_fence = raw.lstrip().startswith("```")
        if is_fence:
            in_fence = not in_fence
            out.append("")  # the fence delimiter itself is never scanned
            continue
        out.append(raw if in_fence else "")
    return out


def _scan_file(path: Path) -> list[PinViolation]:
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return []
    lines = text.splitlines()

    if path.suffix.lower() == ".md":
        lines = _fenced_code_lines(lines)

    found: list[PinViolation] = []
    found.extend(_scan_docker(lines, path))
    found.extend(_scan_box(lines, path))
    found.extend(_scan_git_clone(lines, path))
    return found


def find_pin_violations(root: Path) -> list[PinViolation]:
    """Walk ``root`` and return every dependency-pin violation (empty when clean).

    Pure: no git, network, or subprocess. Skips :data:`SKIP_DIRS` and does not
    follow symlinked directories.
    """
    root = Path(root)
    violations: list[PinViolation] = []
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames[:] = [
            d
            for d in dirnames
            if d not in SKIP_DIRS
            and os.path.relpath(os.path.join(dirpath, d), root) not in SKIP_RELATIVE_DIRS
        ]
        for filename in sorted(filenames):
            path = Path(dirpath) / filename
            if _is_scanned(path):
                violations.extend(_scan_file(path))
    return violations


def main(argv: list[str] | None = None) -> int:
    """Thin CLI: scan ``argv[0]`` (default "."), print findings, return code.

    Returns nonzero when any violation exists, zero when the tree is clean.
    """
    if argv is None:
        argv = sys.argv[1:]
    root = Path(argv[0]) if argv else Path(".")

    violations = find_pin_violations(root)

    if not violations:
        print(f"pins-gate: OK — no unpinned dependencies under {root}")
        return 0

    print(f"pins-gate: {len(violations)} violation(s) under {root}:")
    for v in violations:
        print(f"  [{v.rule}] {v.path}:{v.line}: {v.text}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
