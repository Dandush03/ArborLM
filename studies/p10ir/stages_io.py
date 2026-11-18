# ruff: noqa: E501
"""P10IR file layout of a run directory (no torch): one folder per item, one file per read, so that a PAUSED stage resumes without recomputing a finished read.

``<run>/<stage>/items/<item>/item.json`` (the gates and the completion mark, written last) and ``<run>/<stage>/items/<item>/read.<read>.json`` (one per finished read).
"""

from collections.abc import Iterator
from pathlib import Path


def safe_name(text: str) -> str:
    """A file-system safe form of an item id or a read name (``|`` -> ``__``, ``/`` -> ``~``)."""
    return text.replace("|", "__").replace("/", "~")


def items_dir(run_dir: Path, stage: str) -> Path:
    return run_dir / stage / "items"


def item_dir(run_dir: Path, stage: str, item: str) -> Path:
    return items_dir(run_dir, stage) / safe_name(item)


def read_path(run_dir: Path, stage: str, item: str, read: str) -> Path:
    return item_dir(run_dir, stage, item) / f"read.{safe_name(read)}.json"


def item_path(run_dir: Path, stage: str, item: str) -> Path:
    return item_dir(run_dir, stage, item) / "item.json"


def iter_item_dirs(run_dir: Path, stage: str) -> Iterator[Path]:
    root = items_dir(run_dir, stage)
    if root.is_dir():
        yield from sorted(p for p in root.iterdir() if p.is_dir())
