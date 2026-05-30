"""Contract tests for the `/mnt/data` storage layout + relocation config (T-005).

T-005 introduces the canonical on-disk layout under `/mnt/data/purple-range/`
and the config that relocates Vagrant + VirtualBox artifact directories onto the
1.7 TB `/mnt/data` NVMe — keeping the git working tree on the 244 GB root under
50 MB. These tests lock that contract BEFORE any implementation exists.

They FAIL until `lab/storage.py` exists. First failure is a collection-time
ImportError (no `lab.storage` module); once the module skeleton lands they fail
at assertion level on the pinned names/mappings/idempotency until the behaviour
is correct.

The unit under test is the *pure, computed* layout + config — never the real
filesystem. Every test injects a `tmp_path` base; NOTHING here ever touches the
real `/mnt/data`. Actually shelling out to `VBoxManage`/`vagrant` to apply the
relocation is a host-tail concern, out of scope for this unit: we test the
computed config (data), not the side effect.

Locked interface (so the implementer cannot drift)
--------------------------------------------------
`lab/storage.py` defines, stdlib only (pure `pathlib`, no vendor import):

    DEFAULT_BASE: Path = Path("/mnt/data/purple-range")   # the pinned default

    @dataclass(frozen=True)
    class StorageLayout:
        base: Path
        vendor: Path          # <base>/vendor
        boxes: Path           # <base>/boxes        (VAGRANT_HOME relocated here)
        vbox: Path            # <base>/vbox         (VBox default machine folder)
        secgen_builds: Path   # <base>/secgen-builds   (attr underscored, dir HYPHENATED)
        box_cache: Path       # <base>/box-cache       (attr underscored, dir HYPHENATED)
        work: Path            # <base>/work
        state: Path           # <base>/state

    def ensure_layout(base: Path = DEFAULT_BASE) -> StorageLayout:
        # creates all 7 subdirs idempotently (mkdir(parents=True, exist_ok=True))
        ...

    def vagrant_home(layout: StorageLayout) -> Path:        # == layout.boxes
        ...

    def vbox_machine_folder(layout: StorageLayout) -> Path:  # == layout.vbox
        ...

    def relocation_env(layout: StorageLayout) -> dict[str, str]:
        # at minimum {"VAGRANT_HOME": str(layout.boxes)} — VAGRANT_HOME is the
        # only true env var ARCHITECTURE names; the VBox machine folder is set
        # via VBoxManage (host-tail), exposed here through vbox_machine_folder().
        ...

PINNED FACTS (from ARCHITECTURE.md lines 668-683):
  * default base string ............ "/mnt/data/purple-range"
  * the 7 ON-DISK subdir names ..... vendor, boxes, vbox, secgen-builds,
                                     box-cache, work, state
  * VAGRANT_HOME ................... -> <base>/boxes
  * VBox default machine folder .... -> <base>/vbox
"""

from __future__ import annotations

from pathlib import Path

import pytest

# Hard import (NOT importorskip): until T-005 lands, this raises at collection
# time and the suite goes RED — which is the point of a test-first contract. A
# skip would hide the missing implementation behind a green run.
from lab import storage

# --- the pinned constants, asserted against the contract below ----------------

# (attribute name on StorageLayout, exact on-disk directory name)
SUBDIR_SPEC: list[tuple[str, str]] = [
    ("vendor", "vendor"),
    ("boxes", "boxes"),
    ("vbox", "vbox"),
    ("secgen_builds", "secgen-builds"),  # attr underscored, dir HYPHENATED
    ("box_cache", "box-cache"),          # attr underscored, dir HYPHENATED
    ("work", "work"),
    ("state", "state"),
]

EXPECTED_DIR_NAMES = [disk_name for _attr, disk_name in SUBDIR_SPEC]

DEFAULT_BASE_STR = "/mnt/data/purple-range"


# --- the two acceptance-named tests -------------------------------------------


def test_storage_layout_idempotent(tmp_path: Path) -> None:
    """Re-running ensure_layout is a no-op: all 7 dirs exist, nothing clobbered.

    Plants a sentinel file inside one subdir between the two calls and asserts it
    survives — proving the second call neither errors, recreates, nor clobbers.
    """
    base = tmp_path / "mnt-data" / "purple-range"

    first = storage.ensure_layout(base)
    for _attr, disk_name in SUBDIR_SPEC:
        created = base / disk_name
        assert created.is_dir(), f"first ensure_layout did not create {disk_name}/"

    # Plant a sentinel inside one subdir; the second run must not touch it.
    sentinel = first.state / "validation-events.jsonl"
    sentinel.write_text("sentinel-line\n", encoding="utf-8")

    second = storage.ensure_layout(base)  # must NOT raise

    assert sentinel.read_text(encoding="utf-8") == "sentinel-line\n", (
        "second ensure_layout clobbered existing data — not idempotent"
    )
    for _attr, disk_name in SUBDIR_SPEC:
        assert (base / disk_name).is_dir(), (
            f"second ensure_layout lost {disk_name}/ — not idempotent"
        )
    assert second.base == first.base, "re-run returned a layout with a different base"


def test_no_artifact_path_under_root(tmp_path: Path) -> None:
    """Every artifact path resolves UNDER the injected base, NEVER under the repo.

    This is the guard that keeps multi-GB artifacts off the 244 GB root. We check
    all 7 subdirs PLUS VAGRANT_HOME PLUS the VBox machine folder: each is relative
    to the base, and none is relative to the repo working-tree root.
    """
    base = tmp_path / "mnt-data" / "purple-range"
    layout = storage.ensure_layout(base)
    repo_root = Path(__file__).resolve().parent.parent  # the purple-range working tree

    base_resolved = base.resolve()
    artifact_paths = {
        **{attr: getattr(layout, attr) for attr, _ in SUBDIR_SPEC},
        "VAGRANT_HOME": storage.vagrant_home(layout),
        "vbox_machine_folder": storage.vbox_machine_folder(layout),
    }

    for label, path in artifact_paths.items():
        resolved = Path(path).resolve()
        assert resolved.is_relative_to(base_resolved), (
            f"{label} ({resolved}) escapes the injected base {base_resolved}"
        )
        assert not resolved.is_relative_to(repo_root), (
            f"{label} ({resolved}) resolves under the repo working tree "
            f"{repo_root} — multi-GB artifacts would land on the 244 GB root"
        )


# --- edge cases: pinned names, mappings, default, parents ---------------------


@pytest.mark.parametrize("attr,disk_name", SUBDIR_SPEC, ids=EXPECTED_DIR_NAMES)
def test_subdir_attr_maps_to_exact_architecture_dir_name(
    tmp_path: Path, attr: str, disk_name: str
) -> None:
    """Each layout attribute points at exactly the ARCHITECTURE on-disk dir name.

    Pins the hyphenated names (`secgen-builds`, `box-cache`) so the implementer
    cannot quietly underscore the directories to match the attributes.
    """
    base = tmp_path / "purple-range"
    layout = storage.ensure_layout(base)

    path = getattr(layout, attr)
    assert path.name == disk_name, (
        f"layout.{attr} on-disk dir is {path.name!r}, expected {disk_name!r}"
    )
    assert path.parent == base, f"layout.{attr} is not a direct child of base"


def test_layout_exposes_exactly_the_seven_canonical_subdirs(tmp_path: Path) -> None:
    """The layout exposes all 7 canonical subdir names and no foreign extras.

    Asserted by reading the on-disk dir names off the layout's path attributes,
    so it locks the *set* of artifact directories, not just individual presence.
    """
    base = tmp_path / "purple-range"
    layout = storage.ensure_layout(base)

    on_disk_names = sorted(getattr(layout, attr).name for attr, _ in SUBDIR_SPEC)
    assert on_disk_names == sorted(EXPECTED_DIR_NAMES), (
        "layout does not expose exactly the 7 ARCHITECTURE subdir names"
    )


def test_ensure_layout_returns_layout_pointing_at_created_dirs(tmp_path: Path) -> None:
    """The returned StorageLayout's paths point at the directories just created."""
    base = tmp_path / "purple-range"
    layout = storage.ensure_layout(base)

    assert layout.base == base, "layout.base does not equal the injected base"
    for attr, _disk_name in SUBDIR_SPEC:
        path = getattr(layout, attr)
        assert path.is_dir(), f"layout.{attr} does not point at a created directory"


def test_default_base_is_pinned_without_creating_it() -> None:
    """The default base is exactly `/mnt/data/purple-range` — checked, NOT created.

    Reads the configured default value only; never calls ensure_layout on it, so
    the real /mnt/data is never touched by the suite.
    """
    assert str(storage.DEFAULT_BASE) == DEFAULT_BASE_STR, (
        f"DEFAULT_BASE is {storage.DEFAULT_BASE!r}, expected {DEFAULT_BASE_STR!r}"
    )
    # Sanity: we did not accidentally materialize the real layout.
    assert not (storage.DEFAULT_BASE / "state").exists(), (
        "reading DEFAULT_BASE must not create the real /mnt/data layout"
    )


def test_vagrant_home_maps_to_boxes(tmp_path: Path) -> None:
    """VAGRANT_HOME relocation resolves to <base>/boxes (ARCHITECTURE mapping)."""
    base = tmp_path / "purple-range"
    layout = storage.ensure_layout(base)

    assert storage.vagrant_home(layout) == layout.boxes
    assert layout.boxes == base / "boxes"


def test_vbox_machine_folder_maps_to_vbox(tmp_path: Path) -> None:
    """VBox default machine folder resolves to <base>/vbox (ARCHITECTURE mapping)."""
    base = tmp_path / "purple-range"
    layout = storage.ensure_layout(base)

    assert storage.vbox_machine_folder(layout) == layout.vbox
    assert layout.vbox == base / "vbox"


def test_relocation_env_points_vagrant_home_at_boxes(tmp_path: Path) -> None:
    """relocation_env carries VAGRANT_HOME=<base>/boxes as a plain str mapping.

    VAGRANT_HOME is the only true env var ARCHITECTURE names; values must be
    strings (env vars are strings), pointing at the relocated boxes dir.
    """
    base = tmp_path / "purple-range"
    layout = storage.ensure_layout(base)

    env = storage.relocation_env(layout)
    assert env["VAGRANT_HOME"] == str(layout.boxes), (
        "relocation_env must point VAGRANT_HOME at the relocated boxes dir"
    )
    assert all(isinstance(v, str) for v in env.values()), (
        "relocation_env values must be strings (they become process env vars)"
    )


def test_ensure_layout_idempotent_when_base_already_fully_exists(tmp_path: Path) -> None:
    """A base whose 7 subdirs already exist is fine — second call is a clean no-op."""
    base = tmp_path / "purple-range"
    for _attr, disk_name in SUBDIR_SPEC:
        (base / disk_name).mkdir(parents=True, exist_ok=True)

    layout = storage.ensure_layout(base)  # must NOT raise on pre-existing dirs

    for attr, _disk_name in SUBDIR_SPEC:
        assert getattr(layout, attr).is_dir()


def test_ensure_layout_creates_missing_parent_dirs(tmp_path: Path) -> None:
    """A base nested under not-yet-existing parents is created (parents=True)."""
    base = tmp_path / "deep" / "missing" / "parents" / "purple-range"
    assert not base.exists(), "precondition: nested base does not exist yet"

    layout = storage.ensure_layout(base)

    assert base.is_dir(), "ensure_layout did not create the nested base"
    for attr, _disk_name in SUBDIR_SPEC:
        assert getattr(layout, attr).is_dir(), (
            f"ensure_layout did not create {attr}/ under a nested base"
        )
