# ruff: noqa: E501
"""Reuse of the completed stages of an earlier registered attempt (ADR-0025 addendum, attempt 3, section 4).

The six stages of attempt 2 that completed (inputs, partition, qfit, qcheck, generation, regeneration) are carried into attempt 3 without being recomputed, on conditions this module checks by code:

1. every file those stages wrote is listed with its SHA-256 in the plan (``inputs["reuse"]``), read from the earlier attempt's run directory as it stands, as BYTES: nothing is parsed, no sealed value is opened, the
   directory is never written; a difference is PAUSED — IDENTITY, at the freeze and at the start (and the end) of every stage of attempt 3 (``pkgmanifest.verify_inputs`` calls ``verify_block``);
2. the attempt-3 run directory holds symbolic links to the reused directories (inputs, partition, qfit, qcheck, generation) and the file ``partition_counts.json``, so that the later stages read exactly those files
   through the paths they always use; the reused stages get completion records of this run (mode registered, naming their source); the regeneration check is NOT linked: attempt 3 runs it again
   (``regeneration.json`` of attempt 2 stays in the hashed set, as the thing the new check is compared with by the stage's own token-identity test).

The stages of attempt 3 are ``reuse``, ``regeneration``, ``outputs``, ``analysis`` (``ORDER``)."""

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from arborlm.io import file_sha256, write_json

from ..common import core
from ..common.core import StageRefused

SOURCE_STAGES = ("inputs", "partition", "qfit", "qcheck", "generation", "regeneration")
HASHED_TOP = ("inputs", "partition", "partition_counts.json", "qfit", "qcheck", "generation", "regeneration", "regeneration.json")  # every file the six stages wrote
LINKED = ("inputs", "partition", "partition_counts.json", "qfit", "qcheck", "generation")  # read by the later stages through the paths they always use
RECORDED = ("inputs", "partition", "qfit", "qcheck", "generation")  # the stages whose completion record this run writes (regeneration runs again)
ORDER = ("reuse", "regeneration", "outputs", "analysis")
KEY = "reuse"


def tree_sha256(files: dict[str, str]) -> str:
    h = hashlib.sha256()
    for k in sorted(files):
        h.update(f"{k}\0{files[k]}\n".encode())
    return h.hexdigest()


def hash_files(source: Path) -> dict[str, str]:
    """SHA-256 of every file of the six stages in ``source`` (relative path -> digest), by bytes. Symbolic links are refused. The directory is only read."""
    out: dict[str, str] = {}
    for top in HASHED_TOP:
        base = source / top
        if base.is_symlink():
            raise StageRefused(f"refused: {base} is a symbolic link")
        paths = [base] if base.is_file() else sorted(p for p in base.rglob("*")) if base.is_dir() else []
        if not paths:
            raise StageRefused(f"refused: {base} does not exist: a stage of the earlier attempt did not write it")
        for p in paths:
            if p.is_symlink():
                raise StageRefused(f"refused: {p} is a symbolic link")
            if p.is_file():
                out[str(p.relative_to(source))] = file_sha256(p)
    for s in SOURCE_STAGES:
        rec = source / "stages" / f"{s}.complete.json"
        if not rec.is_file():
            raise StageRefused(f"refused: {rec} does not exist: stage {s!r} of the earlier attempt has no completion record")
        out[str(rec.relative_to(source))] = file_sha256(rec)
    return out


def build_block(source: Path, freeze_commit: str, mode: str = "registered") -> dict[str, Any]:
    """The ``inputs["reuse"]`` block of a plan: where the files are, under which freeze they were computed, every file with its digest, and the tree digest."""
    files = hash_files(source)
    return {"source_run_dir": str(source), "freeze_commit": freeze_commit, "mode": mode, "stages": list(SOURCE_STAGES), "file_count": len(files), "tree_sha256": tree_sha256(files), "files": files}


def verify_block(block: dict[str, Any]) -> None:
    """The earlier attempt's files are, byte for byte, the files the plan recorded (and no file was added to the hashed set). A difference is PAUSED — IDENTITY."""
    now = hash_files(Path(block["source_run_dir"]))
    want: dict[str, str] = block["files"]
    differ = sorted(k for k in set(now) | set(want) if now.get(k) != want.get(k))
    if differ or tree_sha256(now) != block["tree_sha256"] or len(now) != block["file_count"]:
        raise StageRefused(f"refused: {len(differ)} file(s) of the reused stages in {block['source_run_dir']} differ from the plan's list (PAUSED — IDENTITY): " + ", ".join(differ[:8]))


def link_and_record(block: dict[str, Any], run_dir: Path, mode: str) -> dict[str, Any]:
    """The ``reuse`` stage's work: verify, link the reused directories and ``partition_counts.json`` into ``run_dir`` (only ``run_dir`` is written), and write the completion records of the reused stages."""
    if block["mode"] != mode:
        raise StageRefused(f"refused: the reuse block is of mode {block['mode']!r} and this stage runs in mode {mode!r}")
    verify_block(block)
    source = Path(block["source_run_dir"])
    if source.resolve() == run_dir.resolve():
        raise StageRefused("refused: the reused run directory is this run directory")
    run_dir.mkdir(parents=True, exist_ok=True)
    for top in LINKED:
        dest = run_dir / top
        if dest.is_symlink() and Path(os.readlink(dest)) == source / top:
            continue
        if dest.exists() or dest.is_symlink():
            raise StageRefused(f"refused: {dest} exists and is not the link to the reused {top}")
        os.symlink(source / top, dest)
    (run_dir / "stages").mkdir(exist_ok=True)
    for s in RECORDED:
        original = json.loads((source / "stages" / f"{s}.complete.json").read_text())
        write_json(run_dir / "stages" / f"{s}.complete.json", {**original, "mode": mode, "reused_from": str(source), "reused_freeze_commit": block["freeze_commit"], "reused_utc": core.utc_stamp()})
    return {"reused_stages": list(RECORDED), "linked": list(LINKED), "file_count": block["file_count"], "tree_sha256": block["tree_sha256"], "freeze_commit": block["freeze_commit"]}
