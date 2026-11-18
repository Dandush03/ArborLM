# ruff: noqa: E501
"""P10IR registry of records (ADR-0029 section 13, 'Analysis tests'): read records and item records keyed so that two reads of one cell can never share a key.

The key of a read record is ``core.read_key(stage, cell label, update, read name)``: the read's name is part of it. ``studies/p10s1/analysis.py`` lines 167-169 keyed by cell and snapshot
only, so that two reads of one cell would have collided; ``Registry.put_read`` refuses a key that is already held. The key is computed from the record's own fields, so a record cannot be stored under
another key; ``load`` does not compare the file name with the key (the file name is ``read.<read name>.json`` by construction, ``stages_io.read_path``; a duplicate read is still refused by the key). Pure: no torch, no I/O besides ``load``.
"""

from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from . import core

SCOPES = ("tree", "f0", "index")


class KeyCollision(ValueError):
    """Two records claim one key."""


class Registry:
    def __init__(self) -> None:
        self.reads: dict[str, dict[str, Any]] = {}
        self.items: dict[str, dict[str, Any]] = {}

    # -- writing ----------------------------------------------------------------------------------------------------------------------
    def put_read(self, record: Mapping[str, Any]) -> str:
        key = core.read_key(str(record["stage"]), str(record["cell"]), int(record["update"]), str(record["read"]))
        if key in self.reads:
            raise KeyCollision(f"a read record is already held under {key}")
        self.reads[key] = dict(record)
        return key

    def put_item(self, record: Mapping[str, Any]) -> str:
        key = core.item_id(str(record["stage"]), str(record["cell"]), int(record["update"]))
        if key in self.items:
            raise KeyCollision(f"an item record is already held under {key}")
        self.items[key] = dict(record)
        return key

    # -- reading ----------------------------------------------------------------------------------------------------------------------
    def read(self, stage: str, cell: str, update: int, read: str) -> dict[str, Any] | None:
        return self.reads.get(core.read_key(stage, cell, update, read))

    def item(self, stage: str, cell: str, update: int) -> dict[str, Any] | None:
        return self.items.get(core.item_id(stage, cell, update))

    def reads_of(self, stage: str, cell: str, update: int) -> dict[str, dict[str, Any]]:
        prefix = f"{stage}|{cell}|u{update:07d}|"
        return {k[len(prefix) :]: v for k, v in self.reads.items() if k.startswith(prefix)}

    def keys(self) -> Iterable[str]:
        return sorted(self.reads)


def scope_ok(item: Mapping[str, Any] | None, scope: str) -> tuple[bool, str]:
    """Whether every gate of ``scope`` passed in an item record (an absent or incomplete item is not ok). Returns (ok, reason)."""
    if scope not in SCOPES:
        raise ValueError(f"unknown gate scope {scope!r}")
    if item is None:
        return False, "no item record"
    if not item.get("complete"):
        return False, "item incomplete"
    failed = sorted(n for n, g in item.get("gates", {}).items() if g.get("scope") == scope and (g.get("passed") is False or (g.get("passed") is None and g.get("status") != "skipped")))  # only a gate recorded as skipped (not the platform of record) is not a failure
    return (not failed), ("gate(s) failed: " + ", ".join(failed) if failed else "")


def load(run_dir: Path, stage: str) -> Registry:
    """Load every read and item record of ``<run_dir>/<stage>/items`` (written by the workers: ``items/<item id with '|' as '__'>/item.json`` and ``<read name>.json`` beside it)."""
    from .stages_io import iter_item_dirs  # local import: file layout lives with the stage code

    reg = Registry()
    for folder in iter_item_dirs(run_dir, stage):
        item_path = folder / "item.json"
        if item_path.is_file():
            reg.put_item(core.read_record(item_path, "item"))
        for p in sorted(folder.glob("read.*.json")):
            reg.put_read(core.read_record(p, "read"))
    return reg
