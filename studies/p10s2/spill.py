# ruff: noqa: E501
"""The example bank of the data-generation step kept on disk instead of in memory (attempt 7 stopped on the memory guard at 9.38 GiB in the bank and bundle phases, not in the teacher loop).

At the registered size the bank holds 876,288 examples (the accepted pools and the gold pools, each with and without its target, and the panels). Held as Python objects they take 3.3 GB (about 3.8 KB each); the
list of their JSON records built for the bundle takes 1.6 GB more, and writing that list as one canonical JSON string a further 2.4 GB. ``SpillBank`` writes the canonical JSON text of each pool example to a
temporary file INSIDE the attempt's output folder as it is built and keeps only the key's offset; an example is read back (``example_from_json``, the same function ``read_bundle`` uses) when a check needs
it, and ``bank.json`` is written record by record. The bytes written are exactly those of ``arborlm.io.write_json`` on the sorted list of records (compact separators, sorted keys: the text of an element
inside a list is the text of the element alone), so every file hash of the bundle is unchanged. Nothing is reused across attempts: the file is created by the attempt and removed at its end.
Self-check only: not independent review, not Astra validation, not human approval."""

import json
import os
import tempfile
from collections.abc import Iterable, Iterator, Mapping, Sequence
from pathlib import Path
from typing import Any

from arborlm.io import fsync_dir

from .tokenization import Example, ReferenceTokenizer, Segment, build_example, example_from_json
from .world import ExampleBank, example_key


def canonical_text(obj: Any) -> str:
    """The text ``arborlm.io.canonical_json`` gives an element of a list: compact separators, sorted keys, ASCII."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), allow_nan=False)


def write_canonical_json_list(path: Path, texts: Iterable[str]) -> int:
    """Write ``[t1,t2,...]\\n`` (the bytes of ``write_json`` on the list of the records those texts encode) atomically: a temporary file in the same folder, flushed, fsynced, renamed, folder fsynced."""
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    n = 0
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(b"[")
            for t in texts:
                if n:
                    f.write(b",")
                f.write(t.encode())
                n += 1
            f.write(b"]\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(temporary, path)
        fsync_dir(path.parent)
    except BaseException:
        if os.path.exists(temporary):
            os.unlink(temporary)
        raise
    return n


class StreamedRecords:
    """The bank's records as a bundle field: written to ``bank.json`` one record at a time (``worldio.write_bundle`` calls ``write_canonical_json``); ``len`` is the number of records."""

    def __init__(self, bank: "SpillBank") -> None:
        self.bank = bank

    def __len__(self) -> int:
        return len(self.bank._loc)

    def texts(self) -> Iterator[str]:
        for k in sorted(self.bank._loc):
            yield self.bank.record_text(k)

    def write_canonical_json(self, path: Path) -> int:
        return write_canonical_json_list(path, self.texts())

    def materialize(self) -> list[dict[str, Any]]:
        return [json.loads(t) for t in self.texts()]


class SpillBank(ExampleBank):
    """An ``ExampleBank`` whose pool examples (those built while ``spilling`` is on) live in a temporary file. Insertion order of every key is kept (``iter_examples`` yields in the order the base class's
    ``examples.values()`` would), so index-based results of the checks are those of the in-memory bank."""

    def __init__(self, vocab_index: Mapping[str, int], path: Path) -> None:
        super().__init__()
        self.vocab_index = vocab_index
        self.path = path
        self._mem: dict[str, Example] = {}
        self._loc: dict[str, int | None] = {}  # every key, in insertion order: None = in memory, else the offset of its line in the spill file
        self._fh = open(path, "w+b")  # noqa: SIM115 (closed by ``close``)
        self.spilling = False

    # -- writing
    def build_from_tokenizer(self, tok: ReferenceTokenizer, vocab_index: Mapping[str, int], task: str, en: str, target: str | None) -> Example:
        k = example_key(task, en, target)
        if k in self._loc:
            return self._get(k)
        ex = build_example(tok, task, en, target, vocab_index, k)
        self._store(k, ex)
        return ex

    def add(self, task: str, en: str, target: str | None, ex: Example) -> None:
        k = example_key(task, en, target)
        self._mem.pop(k, None)
        self._store(k, ex)

    def _store(self, k: str, ex: Example) -> None:
        if self.spilling:
            self._fh.seek(0, os.SEEK_END)
            off = self._fh.tell()
            self._fh.write(canonical_text(ex.to_json()).encode() + b"\n")
            self._loc[k] = off
        else:
            self._mem[k] = ex
            self._loc[k] = None

    # -- reading
    def _get(self, k: str) -> Example:
        off = self._loc[k]
        if off is None:
            return self._mem[k]
        self._fh.flush()
        self._fh.seek(off)
        return example_from_json(json.loads(self._fh.readline()), self.vocab_index)

    def record_text(self, k: str) -> str:
        off = self._loc[k]
        if off is None:
            return canonical_text(self._mem[k].to_json())
        self._fh.flush()
        self._fh.seek(off)
        return self._fh.readline().decode().rstrip("\n")

    def prompt(self, task: str, en: str) -> Example:
        return self._get(example_key(task, en, None))

    def train(self, task: str, item: Any) -> Example:
        return self._get(example_key(task, item.en, item.target))

    def iter_examples(self) -> Iterator[Example]:
        for k in list(self._loc):
            yield self._get(k)

    def __len__(self) -> int:
        return len(self._loc)

    def to_records(self) -> list[dict[str, Any]]:  # the materialized list (small banks and tests); the bundle gets ``records_stream``
        return StreamedRecords(self).materialize()

    def records_stream(self) -> StreamedRecords:
        self._fh.flush()
        return StreamedRecords(self)

    def close(self, *, remove: bool = True) -> None:
        if not self._fh.closed:
            self._fh.close()
        if remove and self.path.exists():
            self.path.unlink()


def iter_examples(bank: ExampleBank) -> Iterator[Example]:
    """Every example of a bank in insertion order, for either kind of bank."""
    it = getattr(bank, "iter_examples", None)
    return it() if callable(it) else iter(bank.examples.values())


def check_segments_stream(inputs: Iterable[Sequence[Segment]], tok: ReferenceTokenizer) -> dict[str, Any]:
    """``tokenization.check_segments_vs_whole`` on an iterable consumed one input at a time (the same loop, the same result for the same inputs in the same order)."""
    bad: list[int] = []
    n = 0
    for n_i, segs in enumerate(inputs):
        n = n_i + 1
        text_segs = [s for s in segs if s.text != "<bos>"]
        whole = tok.encode("".join(s.text for s in text_segs))
        parts = [i for s in text_segs for i in s.ids]
        if whole != parts:
            bad.append(n_i)
    return {"n": n, "mismatches": bad, "mismatch_rate": len(bad) / n if n else 0.0}
