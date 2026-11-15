# ruff: noqa: E501
"""The download manifest, the hash constants and the guard of the fetch-and-verify step (ADR-0022 sections 14.1, 14.2, 16, 18 and the lead's rulings on the implementation audits). Nothing here
touches the network (the one download function is injected into ``fetch_session``); every function is tested on synthetic files.

No download is made before the human lead's recorded approval and nothing is fetched without an explicit ``--i-have-recorded-human-approval`` flag and a manifest path (``fetch``). What is approved
(section 18): rows 1-4 of section 14.1 (the two teachers, the student, the Tatoeba exports), the two symmetry-check link files, the fallback teacher and fallback data only if the fallback rule of
section 4.2 is invoked, and the eight named packages of the data-generation step with their resolver dependencies, all within a running total below 30 GB kept in the download ledger
(``docs/reviews/p10-design-2026-11-15/DOWNLOAD_LEDGER.md``). Not approved: anything else.

Hash constants (audit A-B1). Every file the step downloads is checked against a constant in this reviewed file and never against a value the manifest supplies: the git-blob SHA-1 of every small file
(from the reviewer's saved Hub trees at the pinned revisions, ``adr-0022-review/web/*_tree.json``, read back in ``check_saved_trees.out.txt`` of the audit), the SHA-256 of every large file (section
14.1). A manifest whose digest is missing or differs from the constant is refused. Files are re-hashed from disk before each use (``verify_tree``, ``read_verified_bytes``). Tatoeba exports have no
revision: their SHA-256 values are recorded at the first download and frozen in a tracked record (``freeze_tatoeba_record``).
"""

import hashlib
import json
import os
import re
import shutil
import ssl
import subprocess
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import torch

from arborlm.io import atomic_write

from .core import ROOT

HF = "https://huggingface.co"
TATOEBA = "https://downloads.tatoeba.org/exports/per_language"
APPROVAL_FLAG = "--i-have-recorded-human-approval"
DOWNLOAD_CAP_BYTES = int(1.5e9)  # one session
DISK_CAP_BYTES = int(6e9)
LEDGER_CAP_BYTES = 30_000_000_000  # the human lead's standing permission: the running total of all downloads stays below this
DOWNLOAD_LEDGER = Path("docs/reviews/p10-design-2026-11-15/DOWNLOAD_LEDGER.md")
TATOEBA_RECORD = Path("studies/p10s2/records/tatoeba_session.json")  # tracked: the digests, sizes and session date frozen at the first download
STUDY = "P10-S2"


class FetchRefused(RuntimeError):
    """The fetch step refuses: no recorded approval, no manifest, an unapproved file, a missing or wrong digest, an overwrite or a cap."""


@dataclass(frozen=True)
class Source:
    name: str  # e.g. "teacher_a/pytorch_model.bin"
    url: str
    sha256: str | None  # a large file's SHA-256 constant; None for a small file and for a Tatoeba export
    git_sha1: str | None  # a small file's git-blob SHA-1 constant; None for a large file and for a Tatoeba export
    size: int | None
    row: int  # the row of section 14.1
    kind: str  # "model-large" | "model-small" | "tatoeba" | "fallback-model" | "fallback-data"
    license: str
    revision: str  # the pinned revision, or a note for a Tatoeba export


def _hf(repo: str, rev: str, f: str) -> str:
    return f"{HF}/{repo}/resolve/{rev}/{f}"


TEACHER_A = ("Helsinki-NLP/opus-mt-en-de", "6183067f769a302e3861815543b9f312c71b0ca4")
TEACHER_B = ("Helsinki-NLP/opus-mt-en-fr", "dd7f6540a7a48a7f4db59e5c0b9c42c8eea67f18")
STUDENT = ("HuggingFaceTB/SmolLM2-135M", "93efa2f097d58c2a74874c7e644dbc9b0cee75a2")
FALLBACK = ("Helsinki-NLP/opus-mt-en-es", "5bc4493d463cf000c1f0b50f8d56886a392ed4ab")
MARIAN_FILES = ("config.json", "generation_config.json", "source.spm", "target.spm", "vocab.json", "tokenizer_config.json")
STUDENT_FILES = ("config.json", "generation_config.json", "tokenizer.json", "tokenizer_config.json", "vocab.json", "merges.txt", "special_tokens_map.json")
LARGE: dict[str, tuple[str, int]] = {
    "teacher_a/pytorch_model.bin": ("da068344b1b0c20e6d4a8f77f48e06646b90d679029006b18579e68977206bdd", 297928209),
    "teacher_b/pytorch_model.bin": ("cc1de10b49342ad2f33e06bc4474ddd6eaca278474903c4a8636ce15680d64de", 300827685),
    "student/model.safetensors": ("80521b40281d6ce74e35c9282c22539e75aa0ac8578892b2a59955ef78d55da1", 269060552),
    "fallback/pytorch_model.bin": ("befce0f620e8e63f83bbb7f0818eb51d541cba28057a7cc14b00466d85c4994c", 312087523),
}
# git-blob SHA-1 and size of every small file at the pinned revisions: the values of the reviewer's saved Hub trees (audit A, check_saved_trees.out.txt). Constants in reviewed code.
SMALL: dict[str, tuple[str, int]] = {
    "teacher_a/config.json": ("0a49d3f4024d5ea51560d51f29d75722d794fb16", 1335),
    "teacher_a/generation_config.json": ("3d05a5bad924f2121cf5a006b36dfda02970289b", 293),
    "teacher_a/source.spm": ("e73d58f99c702eb1746e3dc55bc76255d7aa4a94", 768489),
    "teacher_a/target.spm": ("9dd0d88081be8d75fbc029762329cc11bfad07b9", 796845),
    "teacher_a/vocab.json": ("0da41bcf74fa9a6af4855c7350e27819796d9ca9", 1273232),
    "teacher_a/tokenizer_config.json": ("c1fe32f77a961c887ae8266fbd92f4f583fe309a", 42),
    "teacher_b/config.json": ("1ca77a4a9305ea071d96dd12dbe7c69c3a224f8e", 1416),
    "teacher_b/generation_config.json": ("a76623f9e228ce241586c6dc0ede54b9674940a6", 293),
    "teacher_b/source.spm": ("5b989d2ad3cc6596bef819b2ad755f3e06377476", 778395),
    "teacher_b/target.spm": ("e95b99a0e1a115d0f27eb051c7afc5a2859f1630", 802397),
    "teacher_b/vocab.json": ("f12d2f5f9cddfc4b05dee175269d98cab8274c12", 1339166),
    "teacher_b/tokenizer_config.json": ("599f1c74f7e68d1351c801ef3557a03fd846d171", 42),
    "student/config.json": ("ccf3dac2f33905d152adbdf3886b5e38a4eb7579", 704),
    "student/generation_config.json": ("0fce861c328ff24830f3037d91ce773254447bf7", 111),
    "student/tokenizer.json": ("f922b1797f0c88e71addc8393787831f2477a4bd", 2104556),
    "student/tokenizer_config.json": ("d45192775d58298087a1fedf5967fe5b63b091ab", 3658),
    "student/vocab.json": ("0ad5ecc2035b7031b88afb544ee95e2d49baa484", 800662),
    "student/merges.txt": ("69503b13f727ba3812b6803e97442a6de05ef5eb", 466391),
    "student/special_tokens_map.json": ("f6652f246cb895ca1edfb16d10b57917b266e335", 831),
    "fallback/config.json": ("c40dc3af1603bdbca3388970914022f4abb81f7f", 1473),
    "fallback/generation_config.json": ("f07859fcab98712b231d115475990a962eebc851", 293),
    "fallback/source.spm": ("6dc92ba66940f622779f82c376066c2c46bbad12", 801636),
    "fallback/target.spm": ("2dfb31564bc31c8fbc65c8bfa8cc201fbbf45e44", 825924),
    "fallback/vocab.json": ("d2c5a0f1ab2bb3a752894b854150c358f8c682f9", 1590040),
    "fallback/tokenizer_config.json": ("159d739c93118ec73b1a90a6045b636928fcce95", 44),
}
TATOEBA_FILES = {
    "eng_sentences": ("eng/eng_sentences.tsv.bz2", 24947715), "deu_sentences": ("deu/deu_sentences.tsv.bz2", 12144786), "fra_sentences": ("fra/fra_sentences.tsv.bz2", 9805546),
    "eng_deu_links": ("eng/eng-deu_links.tsv.bz2", 3557634), "eng_fra_links": ("eng/eng-fra_links.tsv.bz2", 2679128),
    "deu_eng_links": ("deu/deu-eng_links.tsv.bz2", 3552331), "fra_eng_links": ("fra/fra-eng_links.tsv.bz2", 2678076),
}  # the last two are the symmetry-check link files (6.2 MB, approved)
FALLBACK_DATA = {"spa_sentences": ("spa/spa_sentences.tsv.bz2", 6376323), "eng_spa_links": ("eng/eng-spa_links.tsv.bz2", 1762602)}
TATOEBA_NAMES = tuple(f"tatoeba/{n}.tsv.bz2" for n in TATOEBA_FILES)
FALLBACK_DATA_NAMES = tuple(f"tatoeba/{n}.tsv.bz2" for n in FALLBACK_DATA)
TATOEBA_NOTE = "no revision exists; SHA-256 recorded at the first download and frozen"


def _model_sources(label: str, repo_rev: tuple[str, str], files: Sequence[str], large: str, row: int, lic: str, large_kind: str, small_kind: str) -> list[Source]:
    repo, rev = repo_rev
    out: list[Source] = []
    for f in (large, *files):
        name = f"{label}/{f}"
        if name in LARGE:
            out.append(Source(name, _hf(repo, rev, f), LARGE[name][0], None, LARGE[name][1], row, large_kind, lic, rev))
        else:
            out.append(Source(name, _hf(repo, rev, f), None, SMALL[name][0], SMALL[name][1], row, small_kind, lic, rev))
    return out


def primary_sources() -> list[Source]:
    out = _model_sources("teacher_a", TEACHER_A, MARIAN_FILES, "pytorch_model.bin", 1, "CC-BY-4.0", "model-large", "model-small")
    out += _model_sources("teacher_b", TEACHER_B, MARIAN_FILES, "pytorch_model.bin", 2, "Apache-2.0", "model-large", "model-small")
    out += _model_sources("student", STUDENT, STUDENT_FILES, "model.safetensors", 3, "Apache-2.0", "model-large", "model-small")
    for name, (rel, size) in TATOEBA_FILES.items():
        out.append(Source(f"tatoeba/{name}.tsv.bz2", f"{TATOEBA}/{rel}", None, None, size, 4, "tatoeba", "CC BY 2.0 FR", TATOEBA_NOTE))
    return out


def fallback_sources() -> list[Source]:
    """Rows 5 and 6 only: the fallback teacher and the fallback data (a later weekly export)."""
    out = _model_sources("fallback", FALLBACK, MARIAN_FILES, "pytorch_model.bin", 5, "Apache-2.0", "fallback-model", "fallback-model")
    for name, (rel, size) in FALLBACK_DATA.items():
        out.append(Source(f"tatoeba/{name}.tsv.bz2", f"{TATOEBA}/{rel}", None, None, size, 6, "fallback-data", "CC BY 2.0 FR", "from a later weekly export; recorded at its first download"))
    return out


def sources(*, fallback: bool = False) -> list[Source]:
    """The approved sources: rows 1-4, and with ``fallback`` also rows 5 and 6 (used to know every approved name; a manifest never mixes the two sets)."""
    return primary_sources() + (fallback_sources() if fallback else [])


# --- hash constants and verification ----------------------------------------------------------------------------------------------------------
def expected_digest(name: str) -> tuple[str, str]:
    """``("sha256", hex)`` or ``("git-sha1", hex)`` for a file with a constant in this module; a Tatoeba export or an unknown name has none (``FetchRefused``)."""
    if name in LARGE:
        return "sha256", LARGE[name][0]
    if name in SMALL:
        return "git-sha1", SMALL[name][0]
    raise FetchRefused(f"refused: {name!r} has no hash constant in reviewed code")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git_blob_sha1_bytes(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data, usedforsecurity=False).hexdigest()  # noqa: S324 - the git object id, compared with a constant; not used for security of secrets


def git_blob_sha1_file(path: Path) -> str:
    h = hashlib.sha1(f"blob {path.stat().st_size}\0".encode(), usedforsecurity=False)  # noqa: S324
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def digest_matches_constant(path: Path, name: str) -> tuple[bool, str, str]:
    """(matches, algorithm, got): the file's digest by the algorithm of its constant."""
    algo, want = expected_digest(name)
    got = sha256_file(path) if algo == "sha256" else git_blob_sha1_file(path)
    return got == want, algo, got


def verify_against_constant(path: Path, name: str) -> None:
    """The file at ``path`` against the constant of ``name`` in this module. A missing file, a name without a constant or a different digest is refused."""
    if not path.is_file():
        raise FetchRefused(f"refused: {path} does not exist")
    ok, algo, got = digest_matches_constant(path, name)
    if not ok:
        raise FetchRefused(f"refused: {name} has {algo} {got}, not the constant {expected_digest(name)[1]} in reviewed code")


def verify_tree(directory: Path, names: Iterable[str]) -> dict[str, str]:
    """Re-hash every named file from disk against its constant (before its use). Returns name -> digest. Any difference refuses."""
    out: dict[str, str] = {}
    for n in names:
        verify_against_constant(directory / n, n)
        out[n] = digest_matches_constant(directory / n, n)[2]
    return out


def read_verified_bytes(directory: Path, name: str) -> bytes:
    """Read a small file once and check the very bytes returned against its constant, so what is parsed is what was verified."""
    p = directory / name
    if not p.is_file():
        raise FetchRefused(f"refused: {p} does not exist")
    data = p.read_bytes()
    algo, want = expected_digest(name)
    got = hashlib.sha256(data).hexdigest() if algo == "sha256" else git_blob_sha1_bytes(data)
    if got != want:
        raise FetchRefused(f"refused: {name} has {algo} {got}, not the constant {want} in reviewed code")
    return data


def verify_file(path: Path, expected_sha256: str) -> None:
    got = sha256_file(path)
    if got != expected_sha256:
        raise FetchRefused(f"refused: {path} has SHA-256 {got}, not the pinned {expected_sha256}")


def load_pickle_weights(path: Path, expected_sha256: str) -> Any:
    """Teacher weights are pickle files: SHA-256 checked, then loaded once with ``torch.load(weights_only=True)`` (offline, on CPU). A file that holds anything but tensors and plain containers is refused by
    torch's restricted unpickler. A test on a synthetic file enforces this; a source test enforces that every ``torch.load`` in the package passes ``weights_only=True``."""
    verify_file(path, expected_sha256)
    return torch.load(path, weights_only=True, map_location="cpu")


# --- the manifest ------------------------------------------------------------------------------------------------------------------------------
def build_manifest(*, fallback_human_decision: Any = None) -> dict[str, Any]:
    """The manifest of exactly the approved downloads, with the digest constants of this module filled in. With a ``fallback_human_decision`` (naming a committed record: ``{"path": ..., "commit": ...}``)
    the manifest lists the fallback rows (5 and 6) only; the primary files stay frozen and are never listed again."""
    srcs = fallback_sources() if fallback_human_decision else primary_sources()
    return {
        "schema": 2, "spec": "docs/decisions/ADR-0022-p10-s2-two-teacher-transfer.md revision 5, section 14.1", "fallback_human_decision": fallback_human_decision if fallback_human_decision else None,
        "files": [{"name": s.name, "url": s.url, "sha256": s.sha256, "git_sha1": s.git_sha1, "size": s.size, "row": s.row, "kind": s.kind, "license": s.license} for s in srcs],
        "note": "digests are the constants of studies/p10s2/fetch_guard.py (git-blob SHA-1 of the small files from the reviewer's saved Hub trees, SHA-256 of the large files from section 14.1); a Tatoeba file's SHA-256 is recorded at first download and frozen",
    }  # fmt: skip


def check_authorization(approved_flag: bool, manifest_path: Path | None) -> None:
    """Refuse unless the explicit approval flag and a manifest path are both given."""
    if not approved_flag:
        raise FetchRefused(f"refused: {APPROVAL_FLAG} is required; a download needs the human lead's recorded approval (ADR-0022 section 16)")
    if manifest_path is None:
        raise FetchRefused("refused: a manifest path is required")
    if not manifest_path.is_file():
        raise FetchRefused(f"refused: manifest {manifest_path} does not exist")


_COMMIT = re.compile(r"^[0-9a-f]{40}$")


def check_fallback_decision(decision: Any, root: Path | None = None) -> None:
    """The fallback is invoked only by a recorded decision that names a committed record: ``{"path": <repository-relative path>, "commit": <40-hex commit>}``, and that file must exist at that
    commit. Any other value (a non-empty string, a path with no commit, a commit without the file) is refused."""
    if not isinstance(decision, Mapping) or set(decision) != {"path", "commit"}:
        raise FetchRefused("refused: no human decision invoking the fallback is recorded (it must be an object with exactly the keys 'path' and 'commit' naming a committed record)")
    path, commit = decision["path"], decision["commit"]
    if not isinstance(path, str) or not path or Path(path).is_absolute() or ".." in Path(path).parts or not isinstance(commit, str) or not _COMMIT.match(commit):
        raise FetchRefused("refused: the fallback decision must give a repository-relative path and a full 40-character commit hash")
    r = subprocess.run(["git", "-C", str(root or ROOT), "cat-file", "-e", f"{commit}:{path}"], capture_output=True, check=False)  # noqa: S603, S607
    if r.returncode != 0:
        raise FetchRefused(f"refused: {path} does not exist at commit {commit}: the fallback decision does not name a committed record")


def validate_manifest(manifest: Mapping[str, Any], *, root: Path | None = None) -> list[dict[str, Any]]:
    """Check a manifest against the approved set. Every file must be an approved source with the approved URL; every file with a hash constant (every model file, small or large) must carry exactly that
    digest in the manifest: a missing digest or a different one is refused (the manifest never supplies the value it is checked against); a manifest is either the primary set (all seven Tatoeba files
    together, because they must come from one session) or the fallback rows only, which need a decision naming a committed record; the declared sizes must fit the download cap. Returns the entries."""
    primary = {s.name: s for s in primary_sources()}
    fallback = {s.name: s for s in fallback_sources()}
    approved = {**primary, **fallback}
    files = list(manifest.get("files", []))
    if not files:
        raise FetchRefused("refused: the manifest lists no file")
    total = 0
    seen: set[str] = set()
    for f in files:
        name = f.get("name")
        if name not in approved:
            raise FetchRefused(f"refused: {name!r} is not an approved download (ADR-0022 section 14.1, 18)")
        if name in seen:
            raise FetchRefused(f"refused: {name!r} is listed twice")
        seen.add(name)
        src = approved[name]
        if f.get("url") != src.url:
            raise FetchRefused(f"refused: {name!r} has a URL other than the approved one")
        if src.sha256 is not None and f.get("sha256") != src.sha256:
            raise FetchRefused(f"refused: {name!r} has a SHA-256 other than the pinned one (or none): the digest is checked against the constant in reviewed code")
        if src.git_sha1 is not None and f.get("git_sha1") != src.git_sha1:
            raise FetchRefused(f"refused: {name!r} has a git-blob SHA-1 other than the pinned one (or none): the digest is checked against the constant in reviewed code")
        if f.get("size") != src.size:
            raise FetchRefused(f"refused: {name!r} declares a size other than the approved {src.size}")
        total += int(src.size or 0)  # the declared size is the constant's
    fb_names = {n for n in seen if n in fallback}
    if fb_names:
        check_fallback_decision(manifest.get("fallback_human_decision"), root)
        if seen - set(fallback):
            raise FetchRefused("refused: a fallback manifest lists the fallback rows only; the primary files are frozen and are not listed again")
        if seen != set(fallback):
            raise FetchRefused("refused: a fallback manifest lists every fallback row (the teacher, its small files and both data files) together")
    else:
        got_tat = seen & set(TATOEBA_NAMES)
        if got_tat and got_tat != set(TATOEBA_NAMES):
            raise FetchRefused(f"refused: the seven Tatoeba files are fetched in one session; missing {sorted(set(TATOEBA_NAMES) - got_tat)}")
    if total > DOWNLOAD_CAP_BYTES:
        raise FetchRefused(f"refused: the declared sizes total {total} bytes, over the download cap of {DOWNLOAD_CAP_BYTES}")
    if total > DISK_CAP_BYTES:
        raise FetchRefused(f"refused: the declared sizes total {total} bytes, over the disk cap of {DISK_CAP_BYTES}")
    return files


# --- the download ledger (docs/reviews/p10-design-2026-11-15/DOWNLOAD_LEDGER.md) ---------------------------------------------------------------
LEDGER_COLUMNS = ("Date (UTC)", "Study", "What", "Source", "Revision / hash", "Licence", "Bytes", "Running total (bytes)", "Status")


def _split_row(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _read_ledger(path: Path) -> tuple[list[str], list[list[str]], list[str]]:
    """(lines before the data rows incl. header and separator, data rows as cells, lines after the table)."""
    lines = path.read_text().split("\n")
    idx = [i for i, ln in enumerate(lines) if ln.startswith("|")]
    if len(idx) < 2 or idx != list(range(idx[0], idx[0] + len(idx))):
        raise FetchRefused(f"refused: {path} has no contiguous markdown table")
    head = lines[idx[0] : idx[0] + 2]
    if _split_row(head[0]) != list(LEDGER_COLUMNS):
        raise FetchRefused(f"refused: the columns of {path} are not {list(LEDGER_COLUMNS)}")
    rows = [_split_row(lines[i]) for i in idx[2:]]
    rows = [r for r in rows if not (len(r) > 2 and r[2].startswith("nothing has been downloaded"))]  # the placeholder row of an empty ledger
    if any(len(r) != len(LEDGER_COLUMNS) for r in rows):
        raise FetchRefused(f"refused: a row of {path} does not have {len(LEDGER_COLUMNS)} columns")
    return lines[: idx[0] + 2], rows, lines[idx[-1] + 1 :]


def _int(cell: str) -> int:
    c = cell.replace(",", "").replace("_", "").strip()
    return int(c) if c.isdigit() else 0


def ledger_total_bytes(path: Path) -> int:
    """The running total of the ledger: the sum of the Bytes column over every row (a started row counts at its declared size until it is completed, a failed one at the bytes it fetched)."""
    return sum(_int(r[6]) for r in _read_ledger(path)[1])


def _write_ledger(path: Path, head: list[str], rows: list[list[str]], tail: list[str]) -> None:
    running = 0
    out_rows: list[str] = []
    for r in rows:
        running += _int(r[6])
        r = [*r[:7], str(running), r[8]]
        out_rows.append("| " + " | ".join(c.replace("|", "/") for c in r) + " |")
    atomic_write(path, ("\n".join([*head, *out_rows, *tail])).encode())


def ledger_begin(path: Path, *, what: str, source: str, revision: str, licence: str, declared_bytes: int, date: str | None = None, study: str = STUDY, cap: int = LEDGER_CAP_BYTES) -> int:
    """Append a "started" row BEFORE a fetch begins. The declared bytes count towards the running total at once; a fetch that would take the total to the cap or above is refused (it returns to the
    human lead). Returns the row index."""
    head, rows, tail = _read_ledger(path)
    total = sum(_int(r[6]) for r in rows)
    if total + declared_bytes >= cap:
        raise FetchRefused(f"refused: {declared_bytes} bytes on a running total of {total} would reach the 30 GB limit of the standing permission ({cap}); a fetch that would take the total there returns to the human lead")
    rows.append([date or datetime.now(UTC).date().isoformat(), study, what, source, revision, licence, str(declared_bytes), "0", "started"])
    _write_ledger(path, head, rows, tail)
    return len(rows) - 1


def ledger_complete(path: Path, index: int, *, actual_bytes: int, status: str) -> None:
    """Complete the row after the fetch: the bytes actually fetched and the status ("completed", or "failed: ..." with the bytes fetched so far)."""
    head, rows, tail = _read_ledger(path)
    if not 0 <= index < len(rows):
        raise FetchRefused(f"refused: ledger row {index} does not exist")
    rows[index][6] = str(actual_bytes)
    rows[index][8] = status
    _write_ledger(path, head, rows, tail)


# --- the session ----------------------------------------------------------------------------------------------------------------------------
Downloader = Callable[[str, Path, int], int]  # (url, part file, byte limit) -> bytes written; raises FetchRefused past the limit


def make_ssl_context() -> ssl.SSLContext:
    """The default context: certificate and host name verification on. It is asserted, not assumed."""
    ctx = ssl.create_default_context()
    if ctx.verify_mode != ssl.CERT_REQUIRED or not ctx.check_hostname:
        raise FetchRefused("refused: TLS verification is not enabled")
    return ctx


def under_data_dir(dest: Path, data_root: Path) -> bool:
    try:
        dest.resolve().relative_to(data_root.resolve())
    except ValueError:
        return False
    return True


def is_git_ignored(path: Path, root: Path | None = None) -> bool:
    r = subprocess.run(["git", "-C", str(root or ROOT), "check-ignore", "-q", str(path)], capture_output=True, check=False)  # noqa: S603, S607
    return r.returncode == 0


def _ledger_revision(src: Source) -> str:
    if src.sha256:
        return f"{src.revision}; SHA-256 {src.sha256}"
    if src.git_sha1:
        return f"{src.revision}; git-blob SHA-1 {src.git_sha1}"
    return src.revision


def fetch_session(
    manifest: Mapping[str, Any], dest_dir: Path, *, download: Downloader, ledger_path: Path, data_root: Path | None = None, root: Path | None = None, free_bytes: int | None = None,
) -> dict[str, Any]:  # fmt: skip
    """One fetch session over a validated manifest (``download`` is injected: the real one is in ``fetch``, tests pass a function that writes synthetic bytes).

    Refusals before anything is fetched: an invalid manifest; a destination outside the git-ignored ``data/`` or not a fresh folder; free disk space below the declared sizes; a ledger that would
    reach 30 GB. For each file: refuse if it exists (nothing is ever overwritten); write the ledger row ("started") first; fetch to a ``.part`` file; check the size (every file but a Tatoeba export,
    whose size changes weekly) and the digest against the constant in reviewed code (a mismatch deletes the file); rename into place; complete the ledger row. The session total is capped, not
    only each file. A failure completes the ledger row as failed and re-raises."""
    files = validate_manifest(manifest, root=root)
    by = {s.name: s for s in sources(fallback=True)}
    droot = data_root if data_root is not None else (root or ROOT) / "data"
    if not under_data_dir(dest_dir, droot):
        raise FetchRefused(f"refused: {dest_dir} is not under the git-ignored {droot}")
    if dest_dir.exists() and any(dest_dir.iterdir()):
        raise FetchRefused(f"refused: {dest_dir} is not a fresh folder")
    declared = sum(int(by[f["name"]].size or 0) for f in files)
    free = free_bytes if free_bytes is not None else shutil.disk_usage(dest_dir.parent if dest_dir.parent.exists() else droot.parent).free
    if free < declared:
        raise FetchRefused(f"refused: {free} free bytes, fewer than the declared {declared}")
    if ledger_total_bytes(ledger_path) + declared >= LEDGER_CAP_BYTES:
        raise FetchRefused(f"refused: the declared {declared} bytes would take the ledger to 30 GB or more")
    make_ssl_context()
    dest_dir.mkdir(parents=True, exist_ok=True)
    started = datetime.now(UTC)
    record: dict[str, Any] = {"started": started.isoformat(timespec="seconds"), "session_date": started.date().isoformat(), "files": {}, "fallback": any(by[f["name"]].kind.startswith("fallback") for f in files)}
    session_bytes = 0
    tatoeba: list[Path] = []
    for f in files:
        src = by[f["name"]]
        out = dest_dir / src.name
        if out.exists():
            raise FetchRefused(f"refused: {out} exists; a fetched file is never overwritten")
        out.parent.mkdir(parents=True, exist_ok=True)
        part = out.with_name(out.name + ".part")
        if part.exists():
            raise FetchRefused(f"refused: {part} exists from an earlier session")
        idx = ledger_begin(ledger_path, what=src.name, source=src.url, revision=_ledger_revision(src), licence=src.license, declared_bytes=int(src.size or 0))
        limit = min(DOWNLOAD_CAP_BYTES - session_bytes, LEDGER_CAP_BYTES - 1 - ledger_total_bytes(ledger_path) + int(src.size or 0))
        got = 0
        try:
            got = download(src.url, part, limit)
            if src.kind != "tatoeba" and src.kind != "fallback-data" and got != src.size:
                raise FetchRefused(f"refused: {src.name} has {got} bytes, expected {src.size}")
            if src.kind not in ("tatoeba", "fallback-data"):
                verify_against_constant(part, src.name)
            try:
                os.link(part, out)  # atomic and never replaces an existing file (a rename would)
            except FileExistsError as exc:
                raise FetchRefused(f"refused: {out} appeared during the fetch; a fetched file is never overwritten") from exc
            part.unlink()
        except BaseException as e:
            part.unlink(missing_ok=True)
            ledger_complete(ledger_path, idx, actual_bytes=got, status=f"failed: {type(e).__name__}")
            raise
        ledger_complete(ledger_path, idx, actual_bytes=got, status="completed")
        session_bytes += got
        if src.kind in ("tatoeba", "fallback-data"):
            tatoeba.append(out)
        record["files"][src.name] = {"sha256": sha256_file(out), "bytes": out.stat().st_size}
    record["tatoeba_recorded_at_first_download"] = record_tatoeba_digests(tatoeba)
    record["finished"] = datetime.now(UTC).isoformat(timespec="seconds")
    rec_path = dest_dir / "fetch_record.json"
    if rec_path.exists():
        raise FetchRefused(f"refused: {rec_path} exists")
    rec_path.write_text(json.dumps(record, indent=1, sort_keys=True) + "\n")
    return record


def record_tatoeba_digests(paths: Sequence[Path]) -> dict[str, str]:
    """SHA-256 recorded at first download and frozen from then on (the downloaded bytes are kept and verified at every load)."""
    return {p.name: sha256_file(p) for p in paths}


# --- the frozen Tatoeba record (tracked) ---------------------------------------------------------------------------------------------------
def tracked_and_clean(path: Path, root: Path | None = None) -> bool:
    """True if ``path`` is tracked by git and has no uncommitted change (so what it freezes is what was reviewed)."""
    r = root or ROOT
    a = subprocess.run(["git", "-C", str(r), "ls-files", "--error-unmatch", str(path)], capture_output=True, check=False)  # noqa: S603, S607
    b = subprocess.run(["git", "-C", str(r), "diff", "--quiet", "HEAD", "--", str(path)], capture_output=True, check=False)  # noqa: S603, S607
    return a.returncode == 0 and b.returncode == 0


def freeze_tatoeba_record(downloads: Path, record_path: Path, *, root: Path | None = None, require_committed: bool = True) -> dict[str, Any]:
    """The Tatoeba digests, sizes and session date, frozen in a tracked record (audit A-B2 and the pre-download checklist).

    If ``record_path`` exists it must be tracked and unmodified (``require_committed``) and every Tatoeba file in ``downloads`` is re-hashed against it (a changed file is refused). If it does not
    exist, this is the first use after the session: the files are re-hashed from disk, compared with the digests ``fetch_record.json`` took at fetch time (a difference is refused), and the record
    is written (a new file; it is never overwritten) with ``status`` "written: commit it before the freeze"."""
    names = [n for n in TATOEBA_NAMES if (downloads / n).exists()]
    if not names:
        raise FetchRefused(f"refused: no Tatoeba file in {downloads}")
    disk = {n: {"sha256": sha256_file(downloads / n), "bytes": (downloads / n).stat().st_size} for n in names}
    if record_path.exists():
        if require_committed and not tracked_and_clean(record_path, root):
            raise FetchRefused(f"refused: {record_path} is not committed and unmodified")
        rec = json.loads(record_path.read_text())
        for n, spec in rec["files"].items():
            if n not in disk or disk[n] != spec:
                raise FetchRefused(f"refused: {n} differs from the frozen Tatoeba record {record_path} (re-hashed from disk)")
        if set(rec["files"]) != set(disk):
            raise FetchRefused(f"refused: the Tatoeba files on disk {sorted(disk)} differ from the frozen record's {sorted(rec['files'])}")
        return {**rec, "status": "verified against the committed record"}
    fr = json.loads((downloads / "fetch_record.json").read_text())
    at_fetch = fr["tatoeba_recorded_at_first_download"]
    for n, spec in disk.items():
        if at_fetch.get(Path(n).name) != spec["sha256"]:
            raise FetchRefused(f"refused: {n} no longer hashes to the digest recorded at fetch time")
    rec = {"schema": 1, "what": "Tatoeba exports: SHA-256 and sizes recorded at the first download and frozen (ADR-0022 section 14.1)", "session_date": fr["session_date"], "started": fr["started"], "finished": fr["finished"], "files": disk}
    record_path.parent.mkdir(parents=True, exist_ok=True)
    record_path.write_text(json.dumps(rec, indent=1, sort_keys=True) + "\n")
    return {**rec, "status": "written: commit it before the freeze"}


def manifest_json(manifest: Mapping[str, Any]) -> str:
    return json.dumps(manifest, indent=1, sort_keys=True)
