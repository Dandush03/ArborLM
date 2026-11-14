# ruff: noqa: E501
"""P9 version store (package I5): copy-on-write snapshots and atomic manifest publication in a local
directory; an engineering test only.

Specification: ADR-0017 section 8.5 ("Version store (engineering test only)"): a reader pinned to V1
while V2 is prepared; no mixed versions, replay equivalence, rollback. Nothing here is storage I/O
evidence (ADR 13) and nothing here is a learning claim: it is a consistency test of a local directory.
Self-check only: not independent review, not Astra validation, not human approval.

Layout under ``<root>``:

* ``objects/<sha256>`` immutable, content-addressed blobs; never rewritten, never deleted. A blob is
  either a *chunk* (the raw bytes of up to ``chunk_rows`` consecutive rows of a tensor), a tensor
  *index* (canonical JSON: dtype, shape, row count per chunk, chunk hashes) or an *update record*.
  A new version writes only the chunks whose bytes differ from blobs already present, so unchanged rows
  are shared (copy-on-write at row-chunk granularity).
* ``versions/<name>.json`` the manifest of a version: ``entries`` (logical tensor name -> index blob
  hash), ``parent``, ``update`` (hash of the update record against the parent: for every changed
  tensor the changed rows and their new bytes), ``state_digest`` (SHA-256 over the content of all
  tensors, independent of how they are chunked or shared) and ``chunk_rows``.
* ``CURRENT`` the pointer to the published version, one JSON object replaced atomically (temporary
  file in the same directory, ``fsync``, ``os.replace``, directory ``fsync``). It also holds every
  published version with the SHA-256 of its manifest file and the publication history, so the single
  atomic replace is the only commit point.

Rules and definitions fixed here:

* One writer, many readers. Readers never take a lock: blobs are immutable and a pinned reader reads
  its manifest once.
* ``publish`` verifies the staged version completely (every blob exists and hashes to its name, the
  state digest matches the content) and refuses a version whose parent is not the current version
  (``StaleParent``), so a published chain always replays.
* *No mixed versions*: every ``PinnedReader.read_all`` recomputes the state digest from the bytes it
  read and compares it with the manifest's; a manifest that combines the index of one version with the
  values of another (or any edited entry) fails that comparison.
* *Replay equivalence*: ``replay`` re-applies the recorded update of a version to its parent's
  tensors and ``replay_check`` compares the result byte for byte with the stored version.
* A crash before the pointer replace leaves the previous version current; the temporary file it leaves
  is reported by ``verify`` and removed only by an explicit ``recover``.
"""

import argparse
import ctypes
import hashlib
import json
import os
import shutil
import sys
import threading
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import torch

from arborlm.io import canonical_json, fsync_dir, sha256, write_json

STORE_SCHEMA = 1
DEFAULT_CHUNK_ROWS = 64
STATEMENT = (
    "Engineering consistency test of a local directory version store (ADR-0017 section 8.5). It "
    "makes no learning claim, is not storage I/O evidence (ADR-0013), and is not independent review, "
    "Astra validation or human approval."
)

_DTYPES: dict[str, torch.dtype] = {
    "float32": torch.float32,
    "float64": torch.float64,
    "int64": torch.int64,
    "int32": torch.int32,
    "uint8": torch.uint8,
    "bool": torch.bool,
}
_DTYPE_NAME = {v: k for k, v in _DTYPES.items()}


class StoreError(Exception):
    """Base class of version store errors."""


class StoreCorruption(StoreError):
    """A blob, manifest or pointer does not hash or parse as recorded."""


class MixedVersionError(StoreCorruption):
    """A manifest's entries do not form the state its digest names (mixed index/value versions)."""


class StaleParent(StoreError):
    """The version to publish was not derived from the current version."""


class SimulatedCrash(StoreError):
    """Raised by test hooks to stop a publication before the pointer is replaced."""


@dataclass(frozen=True)
class VersionManifest:
    """``name``; ``entries`` maps a logical file name (``keys``, ``values``, ``wq``, ...) to the SHA-256
    of its tensor index blob; ``parent`` names the version it was derived from (None for the first).
    ``state_digest``, ``update`` and ``chunk_rows`` are additions to the stub (defaults keep the stub's
    three-field construction valid)."""

    name: str
    entries: dict[str, str]
    parent: str | None
    state_digest: str = ""
    update: str | None = None
    chunk_rows: int = DEFAULT_CHUNK_ROWS

    def to_json(self) -> dict[str, Any]:
        return {
            "schema": STORE_SCHEMA,
            "name": self.name,
            "parent": self.parent,
            "entries": dict(sorted(self.entries.items())),
            "update": self.update,
            "state_digest": self.state_digest,
            "chunk_rows": self.chunk_rows,
        }

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "VersionManifest":
        try:
            return cls(
                name=str(data["name"]),
                entries={str(k): str(v) for k, v in data["entries"].items()},
                parent=None if data["parent"] is None else str(data["parent"]),
                state_digest=str(data["state_digest"]),
                update=None if data["update"] is None else str(data["update"]),
                chunk_rows=int(data["chunk_rows"]),
            )
        except (KeyError, TypeError, AttributeError, ValueError) as exc:
            raise StoreCorruption(f"unparsable manifest: {exc!r}") from exc


# --- tensor bytes ------------------------------------------------------------------------------------
def _raw(t: torch.Tensor) -> bytes:
    """The exact bytes of a CPU tensor in C order."""
    flat = t.detach().cpu().contiguous()
    size = flat.numel() * flat.element_size()
    return b"" if size == 0 else ctypes.string_at(flat.data_ptr(), size)


def _from_raw(data: bytes, dtype: str, shape: list[int]) -> torch.Tensor:
    if dtype not in _DTYPES:
        raise StoreCorruption(f"unsupported dtype {dtype!r}")
    count = 1
    for n in shape:
        count *= n
    if count == 0:
        return torch.empty(shape, dtype=_DTYPES[dtype])
    return torch.frombuffer(bytearray(data), dtype=_DTYPES[dtype]).reshape(shape).clone()


def _rows(shape: list[int]) -> int:
    return shape[0] if shape else 1


def _u8_rows(t: torch.Tensor) -> torch.Tensor:
    """``[rows, row_bytes]`` uint8 view sharing memory with a contiguous tensor."""
    rows = _rows(list(t.shape))
    return t.reshape(-1).view(torch.uint8).reshape(rows, -1)


def _check_tensor(name: str, t: Any) -> torch.Tensor:
    if not isinstance(t, torch.Tensor) or t.dtype not in _DTYPE_NAME:
        raise ValueError(f"entry {name!r} must be a tensor of dtype {sorted(_DTYPES)}")
    return t.detach().cpu().contiguous()


def tensors_identical(a: dict[str, Any], b: dict[str, Any]) -> bool:
    """Same names, dtypes, shapes and bytes."""
    if a.keys() != b.keys():
        return False
    return all(
        a[k].dtype == b[k].dtype
        and list(a[k].shape) == list(b[k].shape)
        and _raw(a[k]) == _raw(b[k])
        for k in a
    )


def state_digest_of(tensors: dict[str, Any]) -> str:
    """SHA-256 over names, dtypes, shapes and bytes of every tensor (sorted by name); independent of
    chunking, sharing and version names."""
    h = hashlib.sha256()
    for name in sorted(tensors):
        t = _check_tensor(name, tensors[name])
        h.update(_tensor_header(name, _DTYPE_NAME[t.dtype], list(t.shape)))
        h.update(hashlib.sha256(_raw(t)).digest())
    return h.hexdigest()


def _tensor_header(name: str, dtype: str, shape: list[int]) -> bytes:
    return json.dumps([name, dtype, shape], separators=(",", ":")).encode() + b"\0"


# --- the store ---------------------------------------------------------------------------------------
class VersionStore:
    """Copy-on-write versions of named tensors in a local directory, one writer and many readers."""

    def __init__(self, root: Path, chunk_rows: int = DEFAULT_CHUNK_ROWS) -> None:
        if chunk_rows < 1:
            raise ValueError("chunk_rows must be positive")
        self.root = Path(root)
        self.chunk_rows = chunk_rows
        self.objects = self.root / "objects"
        self.versions = self.root / "versions"
        self.pointer = self.root / "CURRENT"
        self.objects.mkdir(parents=True, exist_ok=True)
        self.versions.mkdir(parents=True, exist_ok=True)
        self._write_lock = threading.Lock()
        self.last_stage: dict[str, int] = {}

    # -- hooks (tests override these to simulate a crash) ------------------------------------------
    def _before_rename(self) -> None:
        """Called after the new pointer is durable in a temporary file and before it replaces CURRENT."""

    # -- blobs --------------------------------------------------------------------------------------
    def _blob_path(self, digest: str) -> Path:
        return self.objects / digest

    def _temp_name(self) -> str:
        return f".tmp-{os.getpid()}-{uuid.uuid4().hex}"

    def _write_durable(self, directory: Path, data: bytes) -> Path:
        temporary = directory / self._temp_name()
        with temporary.open("wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        return temporary

    def _put_blob(self, data: bytes) -> str:
        digest = sha256(data)
        path = self._blob_path(digest)
        if path.exists():
            self.last_stage["reused_blobs"] = self.last_stage.get("reused_blobs", 0) + 1
            return digest
        temporary = self._write_durable(self.objects, data)
        os.replace(temporary, path)
        self.last_stage["new_blobs"] = self.last_stage.get("new_blobs", 0) + 1
        self.last_stage["new_bytes"] = self.last_stage.get("new_bytes", 0) + len(data)
        return digest

    def _get_blob(self, digest: str) -> bytes:
        try:
            data = self._blob_path(digest).read_bytes()
        except FileNotFoundError as exc:
            raise StoreCorruption(f"missing blob {digest}") from exc
        if sha256(data) != digest:
            raise StoreCorruption(f"blob {digest} does not hash to its name")
        return data

    def _get_json_blob(self, digest: str) -> dict[str, Any]:
        value = json.loads(self._get_blob(digest))
        if not isinstance(value, dict):
            raise StoreCorruption(f"blob {digest} is not a JSON object")
        return value

    # -- tensors <-> blobs ----------------------------------------------------------------------------
    def _put_tensor(self, name: str, t: torch.Tensor) -> str:
        dtype = _DTYPE_NAME[t.dtype]
        shape = list(t.shape)
        rows = _rows(shape)
        chunks: list[str] = []
        if t.numel():
            u8 = _u8_rows(t)
            for lo in range(0, rows, self.chunk_rows):
                chunks.append(self._put_blob(_raw(u8[lo : lo + self.chunk_rows])))
        index = {"dtype": dtype, "shape": shape, "chunk_rows": self.chunk_rows, "chunks": chunks}
        return self._put_blob(canonical_json(index))

    def read_tensor(self, index_digest: str) -> torch.Tensor:
        """A tensor from its index blob, every blob verified."""
        index = self._get_json_blob(index_digest)
        try:
            dtype, shape, chunks = (
                str(index["dtype"]),
                [int(n) for n in index["shape"]],
                list(index["chunks"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise StoreCorruption(f"unparsable tensor index {index_digest}") from exc
        data = b"".join(self._get_blob(str(c)) for c in chunks)
        return _from_raw(data, dtype, shape)

    # -- manifests ------------------------------------------------------------------------------------
    def _manifest_path(self, name: str) -> Path:
        if (
            not name
            or "/" in name
            or name.startswith(".")
            or not all(c.isalnum() or c in "-_." for c in name)
        ):
            raise ValueError(f"bad version name {name!r}")
        return self.versions / f"{name}.json"

    def manifest(self, name: str) -> VersionManifest:
        path = self._manifest_path(name)
        try:
            data = json.loads(path.read_bytes())
        except FileNotFoundError as exc:
            raise StoreError(f"no such version {name!r}") from exc
        except json.JSONDecodeError as exc:
            raise StoreCorruption(f"manifest {name!r} is not JSON") from exc
        manifest = VersionManifest.from_json(data)
        if manifest.name != name:
            raise StoreCorruption(f"manifest file {name!r} names version {manifest.name!r}")
        return manifest

    def manifest_sha256(self, name: str) -> str:
        self._manifest_path(name)
        return sha256(self._manifest_path(name).read_bytes())

    def versions_staged(self) -> list[str]:
        return sorted(p.stem for p in self.versions.glob("*.json"))

    # -- staging --------------------------------------------------------------------------------------
    def stage(self, name: str, tensors: dict[str, Any], parent: str | None) -> VersionManifest:
        """Write blobs (copy-on-write: chunks already present are reused) and the manifest of version
        ``name`` without publishing it. With a ``parent``, the update against the parent (changed rows
        and their new bytes) is recorded in the manifest. ``last_stage`` counts new and reused blobs."""
        path = self._manifest_path(name)
        with self._write_lock:
            if path.exists():
                raise FileExistsError(f"version {name!r} already staged")
            if not tensors:
                raise ValueError("a version needs at least one tensor")
            checked = {k: _check_tensor(k, v) for k, v in tensors.items()}
            parent_tensors: dict[str, torch.Tensor] | None = None
            if parent is not None:
                if not self._manifest_path(parent).exists():
                    raise StoreError(f"parent version {parent!r} is not staged")
                parent_tensors = self._read_version(parent)
            self.last_stage = {"new_blobs": 0, "reused_blobs": 0, "new_bytes": 0}
            entries = {k: self._put_tensor(k, t) for k, t in sorted(checked.items())}
            update = (
                None
                if parent_tensors is None
                else self._put_update(str(parent), parent_tensors, checked)
            )
            manifest = VersionManifest(
                name, entries, parent, state_digest_of(checked), update, self.chunk_rows
            )
            body = canonical_json(manifest.to_json())
            temporary = self._write_durable(self.versions, body)
            try:
                os.link(temporary, path)
            finally:
                Path(temporary).unlink(missing_ok=True)
            fsync_dir(self.objects)
            fsync_dir(self.versions)
            return manifest

    def _read_version(self, name: str) -> dict[str, torch.Tensor]:
        manifest = self.manifest(name)
        return {k: self.read_tensor(h) for k, h in manifest.entries.items()}

    def _put_update(
        self, parent: str, before: dict[str, torch.Tensor], after: dict[str, torch.Tensor]
    ) -> str:
        changes: dict[str, Any] = {}
        for name in sorted(after):
            new = after[name]
            old = before.get(name)
            dtype, shape = _DTYPE_NAME[new.dtype], list(new.shape)
            if (
                old is None
                or old.dtype != new.dtype
                or list(old.shape) != shape
                or new.numel() == 0
            ):
                changes[name] = {"kind": "full", "index": self._put_tensor(name, new)}
                continue
            differ = (_u8_rows(old) != _u8_rows(new)).any(dim=1)
            changed = [int(i) for i in torch.nonzero(differ).reshape(-1).tolist()]
            if changed:
                payload = _raw(_u8_rows(new)[changed])
                changes[name] = {
                    "kind": "rows",
                    "dtype": dtype,
                    "shape": shape,
                    "rows": changed,
                    "data": self._put_blob(payload),
                }
        record = {
            "parent": parent,
            "changes": changes,
            "removed": sorted(set(before) - set(after)),
        }
        return self._put_blob(canonical_json(record))

    # -- verification ---------------------------------------------------------------------------------
    def verify_version(self, name: str) -> dict[str, Any]:
        """Check one staged version: every blob exists and hashes to its name, the state digest matches
        the content, the parent exists. Never raises for a corrupt version; returns ``ok`` and ``problems``."""
        problems: list[str] = []
        try:
            manifest = self.manifest(name)
        except StoreError as exc:
            return {"name": name, "ok": False, "problems": [f"manifest: {exc}"]}
        tensors: dict[str, torch.Tensor] = {}
        for entry, digest in manifest.entries.items():
            try:
                tensors[entry] = self.read_tensor(digest)
            except StoreError as exc:
                problems.append(f"entry {entry}: {exc}")
        if not problems and state_digest_of(tensors) != manifest.state_digest:
            problems.append(
                "mixed or edited entries: content does not match the manifest's state digest"
            )
        if manifest.parent is not None and not self._manifest_path(manifest.parent).exists():
            problems.append(f"orphan manifest: parent {manifest.parent!r} does not exist")
        if manifest.update is not None:
            try:
                self._get_json_blob(manifest.update)
            except StoreError as exc:
                problems.append(f"update record: {exc}")
        return {"name": name, "ok": not problems, "problems": problems}

    def verify(self) -> dict[str, Any]:
        """Check every manifest's blobs, digests and parents, the pointer and the published records.
        Staged but unpublished versions are listed, not counted as problems; leftover temporary files
        (a crash) are listed."""
        problems: list[str] = []
        state = self._read_pointer()
        published = dict(state["published"]) if state else {}
        reports = []
        for name in self.versions_staged():
            report = self.verify_version(name)
            reports.append(report)
            problems.extend(f"{name}: {p}" for p in report["problems"])
            if name in published and report["ok"] and self.manifest_sha256(name) != published[name]:
                problems.append(f"{name}: manifest file changed after publication")
        if state is not None and state["name"] not in self.versions_staged():
            problems.append(f"CURRENT names missing version {state['name']!r}")
        for name in published:
            if name not in self.versions_staged():
                problems.append(f"published version {name!r} has no manifest")
        blobs = [p for p in self.objects.iterdir() if not p.name.startswith(".")]
        leftovers = sorted(
            str(p.relative_to(self.root))
            for d in (self.objects, self.versions, self.root)
            for p in d.iterdir()
            if p.name.startswith(".tmp-")
        )
        return {
            "ok": not problems,
            "problems": problems,
            "current": None if state is None else state["name"],
            "versions": reports,
            "staged_unpublished": [n for n in self.versions_staged() if n not in published],
            "leftover_temp": leftovers,
            "blob_count": len(blobs),
            "blob_bytes": sum(p.stat().st_size for p in blobs),
        }

    def recover(self) -> list[str]:
        """Remove the temporary files a crashed writer left (explicit; never automatic)."""
        removed = []
        for directory in (self.objects, self.versions, self.root):
            for path in directory.iterdir():
                if path.name.startswith(".tmp-") and path.is_file():
                    removed.append(str(path.relative_to(self.root)))
                    path.unlink()
        return sorted(removed)

    # -- pointer --------------------------------------------------------------------------------------
    def _read_pointer(self) -> dict[str, Any] | None:
        try:
            raw = self.pointer.read_bytes()
        except FileNotFoundError:
            return None
        try:
            state = json.loads(raw)
            if (
                not isinstance(state["name"], str)
                or not isinstance(state["published"], dict)
                or not isinstance(state["history"], list)
                or not isinstance(state["sequence"], int)
            ):
                raise TypeError("pointer fields")
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            raise StoreCorruption(f"CURRENT is unreadable: {exc!r}") from exc
        return dict(state)

    def current(self) -> str | None:
        state = self._read_pointer()
        return None if state is None else str(state["name"])

    def published(self) -> list[str]:
        state = self._read_pointer()
        return [] if state is None else list(state["published"])

    def history(self) -> list[dict[str, Any]]:
        state = self._read_pointer()
        return [] if state is None else [dict(e) for e in state["history"]]

    def _commit_pointer(self, state: dict[str, Any]) -> None:
        temporary = self._write_durable(self.root, canonical_json(state))
        self._before_rename()
        os.replace(temporary, self.pointer)
        fsync_dir(self.root)

    def _require_sound(self, name: str) -> None:
        report = self.verify_version(name)
        if not report["ok"]:
            problems = "; ".join(report["problems"])
            cls = MixedVersionError if "mixed or edited" in problems else StoreCorruption
            raise cls(f"version {name!r} failed verification: {problems}")

    def publish(self, name: str) -> None:
        """Atomically make ``name`` current (``os.replace`` of ``CURRENT``, then directory fsync). The
        version is verified first, and must have been derived from the current version (or be the
        first)."""
        with self._write_lock:
            manifest = self.manifest(name)
            self._require_sound(name)
            state = self._read_pointer()
            if state is None:
                if manifest.parent is not None:
                    raise StaleParent(
                        f"{name!r} has parent {manifest.parent!r} but nothing is published"
                    )
                new: dict[str, Any] = {
                    "schema": STORE_SCHEMA,
                    "name": name,
                    "sequence": 1,
                    "published": {name: self.manifest_sha256(name)},
                    "history": [{"sequence": 1, "action": "publish", "name": name}],
                }
            else:
                if manifest.parent != state["name"]:
                    raise StaleParent(
                        f"{name!r} was derived from {manifest.parent!r}, current is {state['name']!r}"
                    )
                sequence = int(state["sequence"]) + 1
                published = dict(state["published"])
                published[name] = self.manifest_sha256(name)
                new = {
                    "schema": STORE_SCHEMA,
                    "name": name,
                    "sequence": sequence,
                    "published": published,
                    "history": [
                        *state["history"],
                        {"sequence": sequence, "action": "publish", "name": name},
                    ],
                }
            self._commit_pointer(new)

    def rollback(self, name: str) -> None:
        """Atomically make a previously published version current again."""
        with self._write_lock:
            state = self._read_pointer()
            if state is None or name not in state["published"]:
                raise StoreError(f"{name!r} was never published")
            if self.manifest_sha256(name) != state["published"][name]:
                raise StoreCorruption(f"manifest of {name!r} changed after publication")
            self._require_sound(name)
            sequence = int(state["sequence"]) + 1
            new = {
                "schema": STORE_SCHEMA,
                "name": name,
                "sequence": sequence,
                "published": dict(state["published"]),
                "history": [
                    *state["history"],
                    {"sequence": sequence, "action": "rollback", "name": name},
                ],
            }
            self._commit_pointer(new)

    # -- readers ---------------------------------------------------------------------------------------
    def pin(self, name: str | None = None) -> "PinnedReader":
        """A reader of version ``name`` (default: current) that never sees another version: it reads
        the manifest once, now, and blobs are immutable."""
        state = self._read_pointer()
        if name is None:
            if state is None:
                raise StoreError("nothing is published")
            name = str(state["name"])
        manifest = self.manifest(name)
        recorded = None if state is None else state["published"].get(name)
        if recorded is not None and self.manifest_sha256(name) != recorded:
            raise StoreCorruption(f"manifest of {name!r} changed after publication")
        return PinnedReader(self, manifest, published=recorded is not None)

    def verify_published(self) -> dict[str, Any]:
        return self.verify()

    # -- replay -------------------------------------------------------------------------------------------
    def replay(self, name: str) -> dict[str, torch.Tensor]:
        """Re-apply the recorded update of ``name`` to its parent's tensors (read from the store)."""
        manifest = self.manifest(name)
        if manifest.parent is None or manifest.update is None:
            raise StoreError(f"version {name!r} has no recorded update")
        tensors = self._read_version(manifest.parent)
        record = self._get_json_blob(manifest.update)
        if record.get("parent") != manifest.parent:
            raise StoreCorruption("update record names a different parent")
        for entry in record["removed"]:
            tensors.pop(entry)
        for entry, change in record["changes"].items():
            if change["kind"] == "full":
                tensors[entry] = self.read_tensor(change["index"])
                continue
            base = tensors[entry].clone().contiguous()
            if str(change["dtype"]) != _DTYPE_NAME[base.dtype] or list(change["shape"]) != list(
                base.shape
            ):
                raise StoreCorruption(f"update of {entry!r} does not match the parent's shape")
            rows = [int(i) for i in change["rows"]]
            data = self._get_blob(change["data"])
            view = _u8_rows(base)
            payload = torch.frombuffer(bytearray(data), dtype=torch.uint8).reshape(len(rows), -1)
            view[rows] = payload
            tensors[entry] = base
        return tensors

    def replay_check(self, name: str) -> dict[str, Any]:
        """Replay equivalence: re-applying the recorded update from the parent reproduces the stored
        version byte for byte. Never raises for corrupt content; returns ``passed`` and ``problems``."""
        problems: list[str] = []
        try:
            replayed = self.replay(name)
            stored = self._read_version(name)
        except (StoreError, KeyError, ValueError, RuntimeError) as exc:
            return {
                "name": name,
                "passed": False,
                "problems": [f"{type(exc).__name__}: {exc}"],
                "changed_rows": {},
            }
        if replayed.keys() != stored.keys():
            problems.append("entry sets differ")
        for entry in sorted(replayed.keys() & stored.keys()):
            if not tensors_identical({entry: replayed[entry]}, {entry: stored[entry]}):
                problems.append(f"entry {entry} differs from the replayed bytes")
        changed: dict[str, int] = {}
        try:
            record = self._get_json_blob(self.manifest(name).update or "")
            changed = {
                e: len(c["rows"]) for e, c in record["changes"].items() if c["kind"] == "rows"
            }
        except StoreError:
            pass
        return {"name": name, "passed": not problems, "problems": problems, "changed_rows": changed}


class PinnedReader:
    """Reads one version's tensors; the version is fixed at construction."""

    name: str

    def __init__(
        self, store: VersionStore, manifest: VersionManifest, published: bool = True
    ) -> None:
        self._store = store
        self.manifest = manifest
        self.name = manifest.name
        self.published = published

    def read(self, entry: str) -> Any:
        """One tensor of the pinned version (every blob verified)."""
        try:
            digest = self.manifest.entries[entry]
        except KeyError as exc:
            raise KeyError(f"version {self.name!r} has no entry {entry!r}") from exc
        return self._store.read_tensor(digest)

    def read_all(self) -> dict[str, Any]:
        """All tensors of the pinned version; raises ``MixedVersionError`` unless their content digests to
        the manifest's state digest."""
        tensors = {k: self._store.read_tensor(h) for k, h in self.manifest.entries.items()}
        if state_digest_of(tensors) != self.manifest.state_digest:
            raise MixedVersionError(f"entries of {self.name!r} do not form its recorded state")
        return tensors


# --- the engineering test -----------------------------------------------------------------------------
class _CrashingStore(VersionStore):
    def _before_rename(self) -> None:
        raise SimulatedCrash("crash before the pointer rename")


def _copy_store(root: Path, target: Path) -> None:
    shutil.copytree(root, target)


def consistency_test(root: Path, v1: dict[str, Any], v2: dict[str, Any]) -> dict[str, Any]:
    """The engineering test of ADR 8.5: publish V1, pin a reader, stage and publish V2 while the
    reader keeps reading V1 (no mixed versions), check replay equivalence (re-applying the recorded
    update from V1 reproduces V2 bit for bit) and rollback, then run the negative controls (crash before
    the rename, a deliberately mixed manifest, a tampered blob, a tampered update record) on a copy.
    Returns a record with ``passed``. It is not a learning claim."""
    root = Path(root)
    main_root = root / "store"
    if main_root.exists() and any(main_root.iterdir()):
        raise FileExistsError(f"{main_root} is not empty")
    checks: dict[str, bool] = {}
    errors: list[str] = []

    def check(name: str, fn: Any) -> Any:
        try:
            value = fn()
        except Exception as exc:  # a failed check is a result, not a crash of the test
            checks[name] = False
            errors.append(f"{name}: {type(exc).__name__}: {exc}")
            return None
        checks[name] = bool(value)
        return value

    a = {k: _check_tensor(k, t) for k, t in v1.items()}
    b = {k: _check_tensor(k, t) for k, t in v2.items()}
    store = VersionStore(main_root)

    store.stage("V1", a, None)
    store.publish("V1")
    reader = store.pin()
    check("first_publish_is_current", lambda: store.current() == "V1" and reader.name == "V1")
    check("reader_reads_v1_exactly", lambda: tensors_identical(reader.read_all(), a))

    store.stage("V2", b, "V1")
    stats_v2 = dict(store.last_stage)
    check("staged_v2_is_not_current", lambda: store.current() == "V1")
    check("pin_during_staging_is_v1", lambda: store.pin().name == "V1")
    check("reader_still_v1_while_v2_staged", lambda: tensors_identical(reader.read_all(), a))

    # concurrent reads while V2 publishes
    stop = threading.Event()
    counts = {"before": 0, "after": 0, "pinned_bad": 0, "fresh_bad": 0, "fresh_reads": 0}
    published_flag = threading.Event()
    started = threading.Event()
    digest_a, digest_b = state_digest_of(a), state_digest_of(b)

    def pinned_loop() -> None:
        while not stop.is_set():
            ok = True
            try:
                ok = tensors_identical(reader.read_all(), a)
            except StoreError:
                ok = False
            counts["pinned_bad"] += 0 if ok else 1
            counts["after" if published_flag.is_set() else "before"] += 1
            started.set()

    def fresh_loop() -> None:
        while not stop.is_set():
            try:
                got = store.pin().read_all()
                ok = state_digest_of(got) in (digest_a, digest_b)
            except StoreError:
                ok = False
            counts["fresh_bad"] += 0 if ok else 1
            counts["fresh_reads"] += 1

    threads = [threading.Thread(target=pinned_loop), threading.Thread(target=fresh_loop)]
    for t in threads:
        t.start()
    started.wait(timeout=30)
    store.publish("V2")
    published_flag.set()
    limit = time.monotonic() + 30.0
    while counts["after"] < 3 and time.monotonic() < limit and all(t.is_alive() for t in threads):
        time.sleep(0.01)
    stop.set()
    for t in threads:
        t.join(timeout=60)
    check(
        "concurrent_reader_saw_only_v1",
        lambda: counts["pinned_bad"] == 0 and counts["before"] >= 1 and counts["after"] >= 1,
    )
    check(
        "fresh_pins_always_a_whole_version",
        lambda: counts["fresh_bad"] == 0 and counts["fresh_reads"] >= 1,
    )
    check("v2_is_current_after_publish", lambda: store.current() == "V2")
    check(
        "old_reader_still_v1",
        lambda: reader.name == "V1" and tensors_identical(reader.read_all(), a),
    )
    check(
        "new_pin_reads_v2_exactly",
        lambda: store.pin().name == "V2" and tensors_identical(store.pin().read_all(), b),
    )

    replay = store.replay_check("V2")
    check("replay_equivalence_v1_to_v2", lambda: replay["passed"])
    check("replay_bytes_equal_v2", lambda: tensors_identical(store.replay("V2"), b))

    store.rollback("V1")
    check("rollback_makes_v1_current", lambda: store.current() == "V1")
    check(
        "rollback_restores_v1_byte_identically",
        lambda: tensors_identical(store.pin().read_all(), a),
    )
    check(
        "v2_still_published_and_readable_after_rollback",
        lambda: "V2" in store.published() and tensors_identical(store.pin("V2").read_all(), b),
    )
    report = store.verify()
    check("store_verifies_clean", lambda: report["ok"] and not report["leftover_temp"])

    # negative controls on a copy: each failure must be detected, V1 must survive the crash
    negative: dict[str, bool] = {}
    neg_root = root / "negative"
    _copy_store(main_root, neg_root / "crash")
    _copy_store(main_root, neg_root / "mixed")
    _copy_store(main_root, neg_root / "tamper_blob")
    _copy_store(main_root, neg_root / "tamper_update")

    def crash_case() -> bool:
        crash = _CrashingStore(neg_root / "crash")
        crash.stage("V3", {k: t.clone() for k, t in b.items()}, "V1")
        try:
            crash.publish("V3")
        except SimulatedCrash:
            pass
        else:
            return False
        reopened = VersionStore(neg_root / "crash")
        leftovers = reopened.verify()["leftover_temp"]
        ok = (
            reopened.current() == "V1"
            and tensors_identical(reopened.pin().read_all(), a)
            and bool(leftovers)
        )
        reopened.recover()
        return ok and not reopened.verify()["leftover_temp"] and reopened.verify()["ok"]

    def mixed_case() -> bool:
        mixed = VersionStore(neg_root / "mixed")
        manifest = mixed.manifest("V2")
        victim = sorted(
            k for k in manifest.entries if manifest.entries[k] != mixed.manifest("V1").entries[k]
        )
        if not victim:
            return False
        entries = dict(manifest.entries)
        entries[victim[0]] = mixed.manifest("V1").entries[victim[0]]
        forged = VersionManifest(
            "Vmixed", entries, "V2", manifest.state_digest, None, manifest.chunk_rows
        )
        mixed._manifest_path("Vmixed").write_bytes(canonical_json(forged.to_json()))
        detected_verify = not mixed.verify_version("Vmixed")["ok"]
        try:
            mixed.publish("Vmixed")
            refused = False
        except StoreError:
            refused = True
        try:
            mixed.pin("Vmixed").read_all()
            reader_refused = False
        except MixedVersionError:
            reader_refused = True
        return detected_verify and refused and reader_refused and mixed.current() == "V1"

    def tamper_blob_case() -> bool:
        tampered = VersionStore(neg_root / "tamper_blob")
        m1, m2 = tampered.manifest("V1"), tampered.manifest("V2")
        index = tampered._get_json_blob(
            next(m2.entries[k] for k in sorted(m2.entries) if m2.entries[k] != m1.entries[k])
        )
        v1_chunks = {c for h in m1.entries.values() for c in tampered._get_json_blob(h)["chunks"]}
        fresh_chunks = [c for c in index["chunks"] if c not in v1_chunks]
        if not fresh_chunks:
            return False
        path = tampered._blob_path(fresh_chunks[0])
        data = bytearray(path.read_bytes())
        data[0] ^= 0xFF
        path.write_bytes(bytes(data))
        replay_check = tampered.replay_check("V2")
        return (not replay_check["passed"]) and (not tampered.verify()["ok"])

    def tamper_update_case() -> bool:
        tampered = VersionStore(neg_root / "tamper_update")
        manifest = tampered.manifest("V2")
        assert manifest.update is not None
        record = tampered._get_json_blob(manifest.update)
        rows_entries = [e for e, c in record["changes"].items() if c["kind"] == "rows"]
        if not rows_entries:
            return False
        change = record["changes"][rows_entries[0]]
        original = tampered._get_blob(change["data"])
        altered = bytearray(original)
        altered[0] ^= 0xFF
        change["data"] = tampered._put_blob(bytes(altered))
        record_digest = tampered._put_blob(canonical_json(record))
        # the V2 content is untouched and self-consistent; only the recorded update no longer reproduces it
        forged = VersionManifest(
            "V2", manifest.entries, "V1", manifest.state_digest, record_digest, manifest.chunk_rows
        )
        tampered._manifest_path("V2").write_bytes(canonical_json(forged.to_json()))
        return not tampered.replay_check("V2")["passed"]

    for name, fn in (
        ("crash_before_rename_keeps_v1_current", crash_case),
        ("mixed_manifest_detected_and_refused", mixed_case),
        ("tampered_v2_blob_fails", tamper_blob_case),
        ("tampered_update_record_fails_replay", tamper_update_case),
    ):
        try:
            negative[name] = bool(fn())
        except Exception as exc:
            negative[name] = False
            errors.append(f"{name}: {type(exc).__name__}: {exc}")

    full_bytes = sum(t.numel() * t.element_size() for t in b.values())
    passed = all(checks.values()) and all(negative.values())
    return {
        "kind": "p9_version_store_consistency",
        "schema": STORE_SCHEMA,
        "engineering_test_only": True,
        "statement": STATEMENT,
        "passed": passed,
        "checks": checks,
        "negative_controls": negative,
        "errors": errors,
        "inputs": {
            "v1_state_digest": digest_a,
            "v2_state_digest": digest_b,
            "entries": {
                k: {"dtype": _DTYPE_NAME[t.dtype], "shape": list(t.shape)}
                for k, t in sorted(b.items())
            },
            "chunk_rows": store.chunk_rows,
        },
        "copy_on_write": {
            "v2_new_blobs": stats_v2.get("new_blobs", 0),
            "v2_reused_blobs": stats_v2.get("reused_blobs", 0),
            "v2_new_bytes": stats_v2.get("new_bytes", 0),
            "v2_full_tensor_bytes": full_bytes,
            "v2_changed_rows": replay["changed_rows"],
        },
        "concurrency": {
            "pinned_reader_ran_before_publish": counts["before"] >= 1,
            "pinned_reader_ran_after_publish": counts["after"] >= 1,
            "pinned_reader_mismatches": counts["pinned_bad"],
            "fresh_pin_mismatches": counts["fresh_bad"],
        },
        "history": store.history(),
    }


# --- command line ---------------------------------------------------------------------------------------
SYNTHETIC_SEED = 179001  # rehearsal namespace; a synthetic tensor draw, never a registered seed


def synthetic_versions(
    seed: int = SYNTHETIC_SEED, slots: int = 4096
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Deterministic V1 and V2 with the shapes of a flat memory addition (keys, values, wq, wo, gate); V2
    changes 64 key rows, 64 value rows, the query projection and the gate, as a partial update would."""
    g = torch.Generator().manual_seed(seed)
    v1 = {
        "keys": torch.randn(slots, 16, generator=g),
        "values": torch.randn(slots, 32, generator=g),
        "wq": torch.randn(16, 32, generator=g),
        "wo": torch.randn(32, 32, generator=g),
        "gate": torch.tensor(-2.0),
    }
    v2 = {k: t.clone() for k, t in v1.items()}
    rows = torch.randperm(slots, generator=g)[:64]
    v2["keys"][rows] += torch.randn(64, 16, generator=g)
    v2["values"][rows] += torch.randn(64, 32, generator=g)
    v2["wq"] += 0.01
    v2["gate"] = torch.tensor(-1.9)
    return v1, v2


def _addition_tensors(snapshot: Path) -> dict[str, Any]:
    payload = torch.load(snapshot / "model.pt", weights_only=True, map_location="cpu")
    prefix = "addition."
    return {k[len(prefix) :]: v for k, v in payload["model"].items() if k.startswith(prefix)}


def main(argv: list[str] | None = None) -> int:
    """``python -m studies.p9.store consistency --out <dir> [--v1 <snapshot> --v2 <snapshot>]`` runs the
    engineering test and writes ``<dir>/consistency.json`` (also printed). Without snapshots it uses
    ``synthetic_versions``; with two snapshot directories it stores their ``addition.*`` tensors."""
    parser = argparse.ArgumentParser(prog="python -m studies.p9.store", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("consistency")
    p.add_argument("--out", required=True)
    p.add_argument("--v1", default=None)
    p.add_argument("--v2", default=None)
    args = parser.parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    if (args.v1 is None) != (args.v2 is None):
        print("--v1 and --v2 go together", file=sys.stderr)
        return 2
    if args.v1 is None:
        v1, v2 = synthetic_versions()
        source: dict[str, Any] = {"kind": "synthetic", "seed": SYNTHETIC_SEED}
    else:
        v1, v2 = _addition_tensors(Path(args.v1)), _addition_tensors(Path(args.v2))
        source = {"kind": "snapshots", "v1": str(args.v1), "v2": str(args.v2)}
    result = consistency_test(out, v1, v2)
    result["source"] = source
    write_json(out / "consistency.json", result)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

__all__ = [
    "PinnedReader",
    "SimulatedCrash",
    "StaleParent",
    "StoreCorruption",
    "StoreError",
    "VersionManifest",
    "VersionStore",
    "MixedVersionError",
    "consistency_test",
    "main",
    "state_digest_of",
    "synthetic_versions",
    "tensors_identical",
]
