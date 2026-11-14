# ruff: noqa: E501
"""P9 version store (package I5): copy-on-write snapshots and atomic manifest publication in a local
directory; an engineering test only.

Specification: ADR-0017 section 8.5 ("Version store (engineering test only)"): a reader pinned to V1
while V2 is prepared; no mixed versions, replay equivalence, rollback. STUB: signatures only. Nothing
here is storage I/O evidence (ADR 13); it is a consistency test of a local directory.

Layout: ``<root>/objects/<sha256>`` immutable content-addressed blobs (a version only adds blobs for
rows or files that changed, sharing the rest), ``<root>/versions/<name>.json`` manifests (key ->
blob hash), ``<root>/CURRENT`` the atomically replaced pointer to the published version.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class VersionManifest:
    """``name``; ``entries`` maps a logical file name (``keys``, ``values``, ``wq``, ...) to a blob
    SHA-256; ``parent`` names the version it was derived from (None for the first)."""

    name: str
    entries: dict[str, str]
    parent: str | None


class VersionStore:
    def __init__(self, root: Path) -> None:
        raise NotImplementedError

    def stage(self, name: str, tensors: dict[str, Any], parent: str | None) -> VersionManifest:
        """Write blobs (copy-on-write: unchanged tensors reuse their blob) and the manifest of version
        ``name`` without publishing it."""
        raise NotImplementedError

    def publish(self, name: str) -> None:
        """Atomically make ``name`` current (``os.replace`` of ``CURRENT``, then directory fsync)."""
        raise NotImplementedError

    def rollback(self, name: str) -> None:
        """Atomically make a previously published version current again."""
        raise NotImplementedError

    def current(self) -> str | None:
        raise NotImplementedError

    def pin(self, name: str | None = None) -> "PinnedReader":
        """A reader of version ``name`` (default: current) that never sees another version."""
        raise NotImplementedError

    def verify(self) -> dict[str, Any]:
        """Check every manifest's blobs exist and hash correctly; no orphan manifest."""
        raise NotImplementedError


class PinnedReader:
    """Reads one version's tensors; the version is fixed at construction."""

    name: str

    def read(self, entry: str) -> Any:
        raise NotImplementedError

    def read_all(self) -> dict[str, Any]:
        raise NotImplementedError


def consistency_test(root: Path, v1: dict[str, Any], v2: dict[str, Any]) -> dict[str, Any]:
    """The engineering test of ADR 8.5: publish V1, pin a reader, stage and publish V2 while the
    reader keeps reading V1 (no mixed versions), check replay equivalence (restoring V1 or V2 from the
    store equals the originals bit for bit) and rollback. Returns a record with ``passed``."""
    raise NotImplementedError


def main(argv: list[str] | None = None) -> int:
    raise NotImplementedError
