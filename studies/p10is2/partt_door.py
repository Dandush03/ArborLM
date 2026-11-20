# ruff: noqa: E501
"""The one checked door through which Part T reads Part Q (ADR-0025 addendum, Part T rulings 6 and 10; audit R1, R2).

The plan names the Part Q run directory of record and its manifest by path and SHA-256 (and, for the files of reused stages that the manifest does not list, Part Q's plan whose reuse block lists them). Every Part Q
file Part T reads is looked up in the manifest's ``files`` (or the reuse list), and its bytes are re-hashed before use; a difference, or a file the lists do not name, is PAUSED — IDENTITY. Nothing sealed and no
per-item score of Part Q's qualification is ever read through it: only the bundle, the gloss bank and the draws record."""

from pathlib import Path
from typing import Any

from arborlm.io import file_sha256, read_json

from .common.core import StageRefused


class PartQDoor:
    def __init__(self, qdir: Path, files: dict[str, str]) -> None:
        self.qdir, self.files = qdir, files

    @classmethod
    def from_plan(cls, part_q: dict[str, Any]) -> "PartQDoor":
        """The door of a registered run: the manifest and (if named) Part Q's plan are checked against the hashes the Part T plan recorded, then their file lists are the door's lists."""
        qdir = Path(part_q["run_dir"])
        man = Path(part_q["manifest"]["path"])
        if not man.is_file() or file_sha256(man) != part_q["manifest"]["sha256"]:
            raise StageRefused(f"refused: Part Q's manifest {man} differs from the hash in the plan (PAUSED — IDENTITY)")
        files = dict(read_json(man)["files"])
        qp = part_q.get("plan")
        if qp:
            pp = Path(qp["path"])
            if not pp.is_file() or file_sha256(pp) != qp["sha256"]:
                raise StageRefused(f"refused: Part Q's plan {pp} differs from the hash in the plan (PAUSED — IDENTITY)")
            for rel, h in (read_json(pp).get("inputs", {}).get("reuse", {}).get("files", {})).items():
                files.setdefault(rel, h)  # the files of the reused stages that the manifest does not list: by the reuse hashes
        return cls(qdir, files)

    @classmethod
    def from_dir(cls, qdir: Path) -> "PartQDoor":
        """A door over a Part Q directory's own manifest (calibration, before a plan exists): the files are still re-hashed against it."""
        man = qdir / "manifest.json"
        if not man.is_file():
            raise StageRefused(f"refused: {man} does not exist")
        return cls(qdir, dict(read_json(man)["files"]))

    def verify(self, rel: str) -> Path:
        want = self.files.get(rel)
        if want is None:
            raise StageRefused(f"refused: {rel} is not listed in Part Q's manifest or reuse hashes: Part T reads listed files only (ruling L12)")
        p = self.qdir / rel
        if not p.is_file() or file_sha256(p) != want:
            raise StageRefused(f"refused: {p} differs from the hash Part Q's manifest lists (PAUSED — IDENTITY)")
        return p

    def verify_prefix(self, prefix: str) -> int:
        names = sorted(r for r in self.files if r.startswith(prefix))
        if not names:
            raise StageRefused(f"refused: Part Q's manifest lists no file under {prefix}")
        for r in names:
            self.verify(r)
        return len(names)

    def read_json(self, rel: str) -> Any:
        return read_json(self.verify(rel))


__all__ = ["PartQDoor"]
