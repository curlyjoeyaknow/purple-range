"""The `/mnt/data` storage layout + relocation config (T-005).

Purple Range keeps the git working tree on the 244 GB root under 50 MB; every
multi-gigabyte artifact (Vagrant boxes, VirtualBox machines, SecGen builds,
box caches, scoring state) lives on the 1.7 TB `/mnt/data` NVMe. This module is
the *pure, computed* source of truth for that on-disk layout and for the
relocation config that points Vagrant + VirtualBox at it.

It is stdlib only (pure `pathlib`, no vendor import). Computing `DEFAULT_BASE`
or a `StorageLayout` touches nothing on disk; only `ensure_layout(base)` with an
explicit base creates directories — and it does so idempotently. Actually
applying the relocation (`VBoxManage setproperty`, exporting `VAGRANT_HOME`) is
a host-tail side effect, out of scope here: we own the *data*, not the effect.

On-disk dir names are pinned by ARCHITECTURE.md (the `/mnt/data` storage
layout): `vendor boxes vbox secgen-builds box-cache work state`. Note the two
hyphenated directories (`secgen-builds`, `box-cache`) map to underscored
attributes (`secgen_builds`, `box_cache`) — Python attrs cannot be hyphenated.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

#: Pinned default base. This is a plain ``Path`` value — reading it creates
#: nothing. The real ``/mnt/data`` layout is only materialized by an explicit
#: ``ensure_layout(base)`` call (tests inject a ``tmp_path`` base).
DEFAULT_BASE: Path = Path("/mnt/data/purple-range")

#: (StorageLayout attribute name, exact on-disk directory name). The single
#: source of truth for the 7 canonical subdirs; the dataclass factory and
#: ``ensure_layout`` both derive from this so names cannot drift apart.
_SUBDIRS: tuple[tuple[str, str], ...] = (
    ("vendor", "vendor"),
    ("boxes", "boxes"),
    ("vbox", "vbox"),
    ("secgen_builds", "secgen-builds"),
    ("box_cache", "box-cache"),
    ("work", "work"),
    ("state", "state"),
)


@dataclass(frozen=True)
class StorageLayout:
    """The computed set of artifact paths under a base directory.

    Construct via :meth:`under` (or :func:`ensure_layout`) rather than passing
    every field by hand — the factory derives each subdir from ``base`` so the
    pinned names stay in lockstep with ``_SUBDIRS``.
    """

    base: Path
    vendor: Path
    boxes: Path
    vbox: Path
    secgen_builds: Path
    box_cache: Path
    work: Path
    state: Path

    @classmethod
    def under(cls, base: Path) -> StorageLayout:
        """Derive a layout whose subdir paths hang off ``base`` (no I/O)."""
        return cls(base=base, **{attr: base / disk_name for attr, disk_name in _SUBDIRS})


def ensure_layout(base: Path = DEFAULT_BASE) -> StorageLayout:
    """Create all 7 canonical subdirs under ``base`` idempotently.

    Uses ``mkdir(parents=True, exist_ok=True)`` per subdir, so missing parents
    are created and a re-run on an already-populated layout neither raises nor
    clobbers existing contents. Returns a :class:`StorageLayout` pointing at the
    created directories.
    """
    layout = StorageLayout.under(base)
    for attr, _disk_name in _SUBDIRS:
        getattr(layout, attr).mkdir(parents=True, exist_ok=True)
    return layout


def vagrant_home(layout: StorageLayout) -> Path:
    """The relocated ``VAGRANT_HOME`` — ARCHITECTURE maps it to ``<base>/boxes``."""
    return layout.boxes


def vbox_machine_folder(layout: StorageLayout) -> Path:
    """The VirtualBox default machine folder — mapped to ``<base>/vbox``.

    Applied on the host via ``VBoxManage setproperty machinefolder`` (host-tail);
    this returns the path that command should be given.
    """
    return layout.vbox


def relocation_env(layout: StorageLayout) -> dict[str, str]:
    """Process-env relocation mapping: ``{"VAGRANT_HOME": "<base>/boxes"}``.

    ``VAGRANT_HOME`` is the only true environment variable ARCHITECTURE names
    (the VBox machine folder is set via ``VBoxManage``, exposed through
    :func:`vbox_machine_folder`). Values are strings because env vars are.
    """
    return {"VAGRANT_HOME": str(layout.boxes)}
