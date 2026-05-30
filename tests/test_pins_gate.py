"""Contract tests for the dependency-pin enforcement gate (T-003).

``scripts/pins_gate.py`` is a Python-stdlib-only scanner CI runs (the ``pins``
stage) to fail any unpinned dependency before it lands. ARCHITECTURE.md (~L553)
defines the gate as: "regex gate: fail on ``:latest``, unpinned ``box_version``,
bare ``git clone`` without pinned ref". These tests pin the gate's behavioural
contract BEFORE the implementation exists (TDD; charter #5).

================================  LOCKED INTERFACE  ===========================

    find_pin_violations(root: Path) -> list[PinViolation]

        Pure function, injectable root, no git/network/subprocess dependency
        (tests drive it against tmp_path). Walks ``root`` and returns every
        pin violation found, empty list when clean.

    PinViolation  (frozen dataclass / attrs-equivalent)
        - .path : pathlib.Path | str   — the offending file
        - .line : int                  — 1-based line number of the offending line
        - .rule : str                  — one of the RULE STRINGS below
        - .text : str                  — the offending source line (rstripped)

    main(argv: list[str] | None = None) -> int
        Thin CLI: scan argv[0] (default "."), print findings, return/exit
        nonzero when ANY violation exists, zero when clean.

================================  RULE STRINGS  ===============================

    "docker-latest"        — a Docker image ref pinned to :latest OR with NO
                             tag/digest at all (bare `image: nginx`,
                             `image: nginx:latest`, `FROM ubuntu:latest`,
                             `FROM alpine`). A version tag (nginx:1.27.3) or a
                             @sha256 digest is OK.
    "unpinned-box-version" — a Vagrant `config.vm.box = "..."` (or yaml `box:`)
                             WITHOUT an accompanying box_version/version pin in
                             the SAME FILE. A box with a box_version pin is OK.
    "bare-git-clone"       — a `git clone <url>` with NO pinned ref: no inline
                             `--branch <tag>` and no `git checkout <40-hex sha>`
                             within the NEAR WINDOW (see below). A clone with a
                             pin is OK.

================================  PINNED DECISIONS  ===========================

These judgement calls are pinned here so the implementer cannot silently drift,
and so a future change that breaks them goes red with a named reason.

  * SCANNED FILE SET: ``*.yml``, ``*.yaml``, ``Dockerfile`` (and
    ``*.Dockerfile``), ``docker-compose*.yml``, ``Vagrantfile`` (and
    ``*.Vagrantfile``), ``*.sh``, and ``*.md``. A ``.txt`` / ``.py`` is NOT
    scanned. (ARCHITECTURE.md: the gate covers configs; we ADD .md because
    run-guides ship real, copy-pasteable commands.)

  * MARKDOWN: only FENCED code blocks (delimited by ``` ) are scanned in .md.
    PROSE mentions (inline backticks, running text) are NEVER flagged — the doc
    that *explains* the pin policy must not turn the build red. This is the
    deliberate false-positive guard for documentation.

  * BARE-CLONE "NEAR WINDOW": a `git clone` is considered pinned if a pinning
    ref appears EITHER inline on the clone line (`--branch <tag>`) OR on any of
    the NEXT 3 non-blank lines (a following `git checkout <sha>` /
    `git -C ... checkout <sha>`). 3 lines is chosen because the idiomatic
    pattern is `git clone` ; `cd <dir>` ; `git checkout <sha>` — the checkout
    is at most a couple of lines below. The window is conservative: too-far a
    checkout is treated as unpinned (better a false RED a human can fix by
    moving the checkout up than a false GREEN that ships an unpinned clone).
    A pinned checkout must reference a 40-hex commit SHA or a `--branch vX.Y.Z`
    tag — `git checkout main` does NOT pin.

  * BOUNDARY / FALSE-POSITIVE GUARDS: properly-pinned forms (nginx:1.27.3,
    @sha256 digest, box_version present, clone+checkout sha, --branch vTAG)
    MUST NOT be flagged. False positives here would block EVERY future PR, so
    each rule carries an explicit negative fixture.

These tests use the PURE function against tmp trees (copying data-driven
fixtures from tests/fixtures/pins/) — no git, no network, no subprocess —
except the single CLI exit-code test.
"""

from __future__ import annotations

import importlib
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Import the unit under test. Until scripts/pins_gate.py exists this is the
# expected first RED (collection/import error). Once the skeleton exists the
# behavioural assertions below drive the implementation.
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "pins"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

pins_gate = importlib.import_module("pins_gate")
find_pin_violations = pins_gate.find_pin_violations


# ---------------------------------------------------------------------------
# Helpers — keep the assertions about behaviour, not plumbing.
# ---------------------------------------------------------------------------

def copy_fixture(fixture_name: str, dest_dir: Path, dest_name: str | None = None) -> Path:
    """Copy a named fixture from tests/fixtures/pins into a tmp tree.

    Renaming on copy lets one fixture body be placed under the filename the
    scanner's extension matching expects (e.g. a compose body named
    docker-compose.yml).
    """
    src = FIXTURES / fixture_name
    dest_dir.mkdir(parents=True, exist_ok=True)
    dst = dest_dir / (dest_name or fixture_name)
    shutil.copyfile(src, dst)
    return dst


def rules(violations) -> list[str]:
    return [v.rule for v in violations]


def for_rule(violations, rule: str):
    return [v for v in violations if v.rule == rule]


# ===========================================================================
# 0. Clean tree — the most important false-positive guard.
# ===========================================================================

def test_clean_tree_has_zero_violations(tmp_path):
    """A properly pinned tree (every supported file type, all pinned) → []."""
    copy_fixture("clean_no_violations.yml", tmp_path)
    copy_fixture("good_docker_pinned.yml", tmp_path)
    copy_fixture("good_dockerfile_pinned.Dockerfile", tmp_path, "Dockerfile")
    copy_fixture("good_pinned_box.Vagrantfile", tmp_path, "Vagrantfile")
    copy_fixture("good_pinned_box.yml", tmp_path)
    copy_fixture("good_git_clone_checkout.sh", tmp_path)
    copy_fixture("good_git_clone_branch_tag.sh", tmp_path)
    copy_fixture("good_md_pinned_command.md", tmp_path)
    copy_fixture("good_md_prose_mention.md", tmp_path)
    copy_fixture("ignored_not_scanned.txt", tmp_path)

    violations = find_pin_violations(tmp_path)

    assert violations == [], (
        "a fully pinned tree must yield zero violations; a false positive here "
        f"would block every future PR. got: {rules(violations)} "
        f"-> {[(v.rule, str(v.path), v.line, v.text) for v in violations]}"
    )


# ===========================================================================
# 1. docker-latest — positive (must flag) and negative (must not).
# ===========================================================================

def test_docker_latest_flags_latest_and_untagged_in_compose(tmp_path):
    """`:latest` AND a bare/untagged image both trip docker-latest."""
    copy_fixture("bad_docker_latest.yml", tmp_path, "docker-compose.yml")

    hits = for_rule(find_pin_violations(tmp_path), "docker-latest")

    # nginx:latest, redis (bare), traefik:latest -> three offending lines.
    assert len(hits) == 3, (
        "expected three docker-latest hits (explicit :latest, bare untagged, "
        f"and a second :latest); got rules={rules(find_pin_violations(tmp_path))}"
    )
    flagged_text = " ".join(h.text for h in hits)
    assert "nginx:latest" in flagged_text
    assert "redis" in flagged_text, "a bare untagged image must be flagged too"


def test_docker_latest_reports_correct_line_number(tmp_path):
    """The violation .line is the 1-based line of the offending image ref."""
    copy_fixture("bad_docker_latest.yml", tmp_path, "docker-compose.yml")

    hits = for_rule(find_pin_violations(tmp_path), "docker-latest")
    nginx_hits = [h for h in hits if "nginx:latest" in h.text]

    assert len(nginx_hits) == 1
    # `image: nginx:latest` is line 6 in bad_docker_latest.yml (1-based).
    assert nginx_hits[0].line == 6, (
        f"nginx:latest is on line 6 of the fixture, got {nginx_hits[0].line}"
    )


def test_docker_latest_flags_dockerfile_from(tmp_path):
    """A Dockerfile `FROM ubuntu:latest` and bare `FROM alpine` are flagged."""
    copy_fixture("bad_dockerfile_latest.Dockerfile", tmp_path, "Dockerfile")

    hits = for_rule(find_pin_violations(tmp_path), "docker-latest")

    assert len(hits) == 2, (
        f"FROM ubuntu:latest and bare FROM alpine must both trip; got {rules(find_pin_violations(tmp_path))}"
    )


def test_docker_versioned_and_digest_pins_not_flagged(tmp_path):
    """nginx:1.27.3 and @sha256 digests must NOT be flagged (false-pos guard)."""
    copy_fixture("good_docker_pinned.yml", tmp_path, "docker-compose.yml")
    copy_fixture("good_dockerfile_pinned.Dockerfile", tmp_path, "Dockerfile")

    hits = for_rule(find_pin_violations(tmp_path), "docker-latest")

    assert hits == [], (
        "version-tagged and digest-pinned images must never be flagged; "
        f"got {[(str(h.path), h.line, h.text) for h in hits]}"
    )


# ===========================================================================
# 2. unpinned-box-version — positive and negative, Vagrantfile + yaml forms.
# ===========================================================================

def test_unpinned_box_flagged_in_vagrantfile(tmp_path):
    """A config.vm.box with no box_version in the file is flagged."""
    copy_fixture("bad_unpinned_box.Vagrantfile", tmp_path, "Vagrantfile")

    hits = for_rule(find_pin_violations(tmp_path), "unpinned-box-version")

    assert len(hits) == 1, (
        f"the unpinned box line must be flagged once; got {rules(find_pin_violations(tmp_path))}"
    )
    assert "config.vm.box" in hits[0].text
    # `config.vm.box = "..."` is line 4 in the fixture (1-based).
    assert hits[0].line == 4, f"box line is line 4, got {hits[0].line}"


def test_unpinned_box_flagged_in_yaml(tmp_path):
    """A yaml `box:` with no `box_version:`/`version:` in the file is flagged."""
    copy_fixture("bad_unpinned_box.yml", tmp_path)

    hits = for_rule(find_pin_violations(tmp_path), "unpinned-box-version")

    assert len(hits) == 1, (
        f"the unpinned yaml box must be flagged; got {rules(find_pin_violations(tmp_path))}"
    )


def test_pinned_box_version_not_flagged_vagrantfile(tmp_path):
    """A box WITH box_version in the same file must NOT be flagged."""
    copy_fixture("good_pinned_box.Vagrantfile", tmp_path, "Vagrantfile")

    hits = for_rule(find_pin_violations(tmp_path), "unpinned-box-version")

    assert hits == [], (
        "a box accompanied by box_version is pinned and must not be flagged; "
        f"got {[(str(h.path), h.line, h.text) for h in hits]}"
    )


def test_pinned_box_version_not_flagged_yaml(tmp_path):
    """A yaml box WITH box_version: in the same file must NOT be flagged."""
    copy_fixture("good_pinned_box.yml", tmp_path)

    hits = for_rule(find_pin_violations(tmp_path), "unpinned-box-version")

    assert hits == [], (
        f"yaml box+box_version must not be flagged; got {[h.text for h in hits]}"
    )


# ===========================================================================
# 3. bare-git-clone — positive, and the three negative pinned forms.
# ===========================================================================

def test_bare_git_clone_flagged(tmp_path):
    """A `git clone <url>` with no following checkout/branch is flagged."""
    copy_fixture("bad_bare_git_clone.sh", tmp_path)

    hits = for_rule(find_pin_violations(tmp_path), "bare-git-clone")

    assert len(hits) == 1, (
        f"the bare clone must be flagged once; got {rules(find_pin_violations(tmp_path))}"
    )
    assert "git clone" in hits[0].text
    # The clone is line 6 in bad_bare_git_clone.sh (1-based).
    assert hits[0].line == 6, f"clone is on line 6, got {hits[0].line}"


def test_clone_followed_by_checkout_sha_not_flagged(tmp_path):
    """clone + `git checkout <40-hex>` within the near window → not flagged."""
    copy_fixture("good_git_clone_checkout.sh", tmp_path)

    hits = for_rule(find_pin_violations(tmp_path), "bare-git-clone")

    assert hits == [], (
        "a clone pinned by a following checkout <sha> must not be flagged; "
        f"got {[(h.line, h.text) for h in hits]}"
    )


def test_clone_with_branch_tag_not_flagged(tmp_path):
    """clone --branch vX.Y.Z (inline pin) must NOT be flagged."""
    copy_fixture("good_git_clone_branch_tag.sh", tmp_path)

    hits = for_rule(find_pin_violations(tmp_path), "bare-git-clone")

    assert hits == [], (
        f"an inline --branch vTAG pins the clone; got {[h.text for h in hits]}"
    )


def test_clone_then_distant_checkout_is_still_flagged(tmp_path):
    """PINNED near-window: a checkout > 3 non-blank lines below does NOT pin.

    This pins the conservative window: better a false RED a human fixes by
    moving the checkout up than a false GREEN shipping an unpinned clone.
    """
    script = tmp_path / "distant.sh"
    script.write_text(
        "#!/usr/bin/env bash\n"
        "git clone https://github.com/vulhub/vulhub.git repo\n"  # line 2
        "cd repo\n"                                               # line 3
        "echo a\n"                                                # line 4
        "echo b\n"                                                # line 5
        "echo c\n"                                                # line 6
        "git checkout d277a8693e588684e951dddb0733809e53881a3c\n"  # line 7 (too far)
    )

    hits = for_rule(find_pin_violations(tmp_path), "bare-git-clone")

    assert len(hits) == 1, (
        "a checkout more than 3 non-blank lines below the clone is outside the "
        f"near window and must NOT count as a pin; got {rules(find_pin_violations(tmp_path))}"
    )
    assert hits[0].line == 2, f"the clone is on line 2, got {hits[0].line}"


def test_clone_then_checkout_branch_name_is_still_flagged(tmp_path):
    """`git checkout main` is a moving ref, not a pin — clone stays flagged."""
    script = tmp_path / "branchname.sh"
    script.write_text(
        "#!/usr/bin/env bash\n"
        "git clone https://github.com/vulhub/vulhub.git repo\n"  # line 2
        "cd repo\n"                                               # line 3
        "git checkout main\n"                                     # line 4 (not a sha/tag)
    )

    hits = for_rule(find_pin_violations(tmp_path), "bare-git-clone")

    assert len(hits) == 1, (
        "checkout of a branch name does not pin; the clone must still be flagged; "
        f"got {rules(find_pin_violations(tmp_path))}"
    )


# ===========================================================================
# 4. Markdown scanning decision — PINNED.
# ===========================================================================

def test_md_fenced_code_block_is_scanned(tmp_path):
    """A bare git clone inside a ``` fenced block in .md IS flagged.

    Run-guides ship real, copy-pasteable commands; an unpinned clone in a
    fenced block is a real anti-pattern, so .md fenced blocks are scanned.
    """
    copy_fixture("bad_md_real_command.md", tmp_path)

    hits = for_rule(find_pin_violations(tmp_path), "bare-git-clone")

    assert len(hits) == 1, (
        "a bare clone inside an .md fenced code block must be flagged; "
        f"got {rules(find_pin_violations(tmp_path))}"
    )


def test_md_prose_mentions_are_not_scanned(tmp_path):
    """Anti-patterns in PROSE (not fenced) must NOT be flagged.

    Otherwise the documentation explaining the pin policy turns the build red.
    """
    copy_fixture("good_md_prose_mention.md", tmp_path)

    violations = find_pin_violations(tmp_path)

    assert violations == [], (
        "prose mentions of :latest / bare clone (inline backticks, running "
        f"text) must never be flagged; got {[(v.rule, v.line, v.text) for v in violations]}"
    )


def test_md_fenced_block_with_pins_not_flagged(tmp_path):
    """A fenced block whose commands ARE pinned must not be flagged."""
    copy_fixture("good_md_pinned_command.md", tmp_path)

    violations = find_pin_violations(tmp_path)

    assert violations == [], (
        f"a fully pinned .md run-guide must not be flagged; got {rules(violations)}"
    )


# ===========================================================================
# 5. Scanned-file-set decision — non-scanned types are ignored.
# ===========================================================================

def test_unscanned_file_type_is_ignored(tmp_path):
    """A .txt carrying anti-patterns is NOT in the scanned set → no violation."""
    copy_fixture("ignored_not_scanned.txt", tmp_path)

    violations = find_pin_violations(tmp_path)

    assert violations == [], (
        ".txt is outside the scanned set (yml/yaml/Dockerfile/compose/"
        f"Vagrantfile/sh/md); must not be scanned. got {rules(violations)}"
    )


# ===========================================================================
# 6. Aggregation — a tree with one of each violation reports all three rules.
# ===========================================================================

def test_mixed_tree_reports_each_distinct_rule(tmp_path):
    """A tree with one of each anti-pattern surfaces all three rule strings."""
    copy_fixture("bad_docker_latest.yml", tmp_path, "docker-compose.yml")
    copy_fixture("bad_unpinned_box.Vagrantfile", tmp_path, "Vagrantfile")
    copy_fixture("bad_bare_git_clone.sh", tmp_path)

    found = set(rules(find_pin_violations(tmp_path)))

    assert {"docker-latest", "unpinned-box-version", "bare-git-clone"} <= found, (
        f"all three rule strings must appear; got {found}"
    )


# ===========================================================================
# 7. Thin CLI exit-code contract (the one subprocess test).
# ===========================================================================

def test_pins_gate_cli_exit_code(tmp_path):
    """CLI: nonzero exit on any violation, zero when the tree is clean."""
    script = SCRIPTS_DIR / "pins_gate.py"

    dirty = tmp_path / "dirty"
    copy_fixture("bad_docker_latest.yml", dirty, "docker-compose.yml")
    dirty_run = subprocess.run(
        [sys.executable, str(script), str(dirty)],
        capture_output=True,
        text=True,
    )
    assert dirty_run.returncode != 0, (
        f"dirty tree must exit nonzero; stdout={dirty_run.stdout!r} "
        f"stderr={dirty_run.stderr!r}"
    )

    clean = tmp_path / "clean"
    copy_fixture("clean_no_violations.yml", clean, "docker-compose.yml")
    clean_run = subprocess.run(
        [sys.executable, str(script), str(clean)],
        capture_output=True,
        text=True,
    )
    assert clean_run.returncode == 0, (
        f"clean tree must exit zero; stdout={clean_run.stdout!r} "
        f"stderr={clean_run.stderr!r}"
    )
