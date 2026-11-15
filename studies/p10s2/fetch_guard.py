# ruff: noqa: E501
"""The download manifest and the guard of the fetch-and-verify step (ADR-0022 sections 14.1, 14.2, 16, 18). Pure functions: nothing here touches the network and every function is tested.

No download is made before the human lead's recorded approval and nothing is fetched without an explicit ``--i-have-recorded-human-approval`` flag and a manifest path (``fetch``). What is approved
(section 18): rows 1-4 of section 14.1 (the two teachers, the student, the Tatoeba exports), the two symmetry-check link files, the fallback teacher and fallback data only if the fallback rule of section 4.2 is
invoked (the invocation first returns to the human lead), and the eight named packages of the data-generation step once the human lead's confirmation with sizes is recorded. Not approved: anything else.

Pinned identities are quoted from the ADR. Where the ADR gives no digest (the git-blob SHA-1 of the small configuration files at the pinned revisions; the Tatoeba SHA-256 values, which are recorded at first
download and frozen), the manifest says so: the fetch step refuses a model file whose digest is not given, and records a Tatoeba file's digest at first download.
"""

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import torch

HF = "https://huggingface.co"
TATOEBA = "https://downloads.tatoeba.org/exports/per_language"
APPROVAL_FLAG = "--i-have-recorded-human-approval"
DOWNLOAD_CAP_BYTES = int(1.5e9)
DISK_CAP_BYTES = int(6e9)


class FetchRefused(RuntimeError):
    """The fetch step refuses: no recorded approval, no manifest, an unapproved file, a missing digest or a cap."""


@dataclass(frozen=True)
class Source:
    name: str  # e.g. "teacher_a/pytorch_model.bin"
    url: str
    sha256: str | None  # None: model files need one; Tatoeba files are recorded at first download
    size: int | None
    row: int  # the row of section 14.1
    kind: str  # "model-large" | "model-small" | "tatoeba" | "fallback-model" | "fallback-data"
    license: str


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
TATOEBA_FILES = {
    "eng_sentences": ("eng/eng_sentences.tsv.bz2", 24947715), "deu_sentences": ("deu/deu_sentences.tsv.bz2", 12144786), "fra_sentences": ("fra/fra_sentences.tsv.bz2", 9805546),
    "eng_deu_links": ("eng/eng-deu_links.tsv.bz2", 3557634), "eng_fra_links": ("eng/eng-fra_links.tsv.bz2", 2679128),
    "deu_eng_links": ("deu/deu-eng_links.tsv.bz2", 3552331), "fra_eng_links": ("fra/fra-eng_links.tsv.bz2", 2678076),
}  # the last two are the symmetry-check link files (6.2 MB, approved)
FALLBACK_DATA = {"spa_sentences": ("spa/spa_sentences.tsv.bz2", 6376323), "eng_spa_links": ("eng/eng-spa_links.tsv.bz2", 1762602)}


def sources(*, fallback: bool = False) -> list[Source]:
    out: list[Source] = []
    for label, (repo, rev), lic in (("teacher_a", TEACHER_A, "CC-BY-4.0"), ("teacher_b", TEACHER_B, "Apache-2.0")):
        for f in ("pytorch_model.bin", *MARIAN_FILES):
            big = LARGE.get(f"{label}/{f}")
            out.append(Source(f"{label}/{f}", _hf(repo, rev, f), big[0] if big else None, big[1] if big else None, 1 if label == "teacher_a" else 2, "model-large" if big else "model-small", lic))
    for f in ("model.safetensors", *STUDENT_FILES):
        big = LARGE.get(f"student/{f}")
        out.append(Source(f"student/{f}", _hf(*STUDENT, f), big[0] if big else None, big[1] if big else None, 3, "model-large" if big else "model-small", "Apache-2.0"))
    for name, (rel, size) in TATOEBA_FILES.items():
        out.append(Source(f"tatoeba/{name}.tsv.bz2", f"{TATOEBA}/{rel}", None, size, 4, "tatoeba", "CC BY 2.0 FR"))
    if fallback:
        for f in ("pytorch_model.bin", *MARIAN_FILES):
            big = LARGE.get(f"fallback/{f}")
            out.append(Source(f"fallback/{f}", _hf(*FALLBACK, f), big[0] if big else None, big[1] if big else None, 5, "fallback-model", "Apache-2.0"))
        for name, (rel, size) in FALLBACK_DATA.items():
            out.append(Source(f"tatoeba/{name}.tsv.bz2", f"{TATOEBA}/{rel}", None, size, 6, "fallback-data", "CC BY 2.0 FR"))
    return out


def build_manifest(*, fallback_human_decision: str | None = None) -> dict[str, Any]:
    """The manifest of exactly the approved downloads. Fallback files are included only with a recorded human decision invoking the fallback (the invocation returns to the human lead first)."""
    srcs = sources(fallback=bool(fallback_human_decision))
    return {
        "schema": 1, "spec": "docs/decisions/ADR-0022-p10-s2-two-teacher-transfer.md revision 5, section 14.1", "fallback_human_decision": fallback_human_decision,
        "files": [{"name": s.name, "url": s.url, "sha256": s.sha256, "size": s.size, "row": s.row, "kind": s.kind, "license": s.license} for s in srcs],
        "note": "git-blob SHA-1 values of the small configuration files at the pinned revisions are not in the ADR: they must be supplied (from the Hub tree at the pinned revision) before the fetch; a Tatoeba file's SHA-256 is recorded at first download and frozen",
    }  # fmt: skip


def check_authorization(approved_flag: bool, manifest_path: Path | None) -> None:
    """Refuse unless the explicit approval flag and a manifest path are both given."""
    if not approved_flag:
        raise FetchRefused(f"refused: {APPROVAL_FLAG} is required; a download needs the human lead's recorded approval (ADR-0022 section 16)")
    if manifest_path is None:
        raise FetchRefused("refused: a manifest path is required")
    if not manifest_path.is_file():
        raise FetchRefused(f"refused: manifest {manifest_path} does not exist")


def validate_manifest(manifest: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Check a manifest against the approved set: every file must be an approved source with the approved URL; fallback files need a recorded human decision; every model file needs a digest
    (a file with no digest and not a Tatoeba export is refused); the declared sizes must fit the download cap. Returns the file entries."""
    approved = {s.name: s for s in sources(fallback=True)}
    fb_ok = bool(manifest.get("fallback_human_decision"))
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
        if src.kind in ("fallback-model", "fallback-data") and not fb_ok:
            raise FetchRefused(f"refused: {name!r} is a fallback file and no human decision invoking the fallback is recorded")
        digest = f.get("sha256") or f.get("git_sha1")
        if src.kind != "tatoeba" and src.kind != "fallback-data" and not digest:
            raise FetchRefused(f"refused: {name!r} has no recorded digest (a model file is fetched only against a pinned SHA-256 or git-blob SHA-1)")
        if src.sha256 is not None and f.get("sha256") not in (None, src.sha256):
            raise FetchRefused(f"refused: {name!r} names a SHA-256 other than the pinned one")
        total += int(f.get("size") or 0)
    if total > DOWNLOAD_CAP_BYTES:
        raise FetchRefused(f"refused: the declared sizes total {total} bytes, over the download cap of {DOWNLOAD_CAP_BYTES}")
    return files


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_file(path: Path, expected_sha256: str) -> None:
    got = sha256_file(path)
    if got != expected_sha256:
        raise FetchRefused(f"refused: {path} has SHA-256 {got}, not the pinned {expected_sha256}")


def load_pickle_weights(path: Path, expected_sha256: str) -> Any:
    """Teacher weights are pickle files: SHA-256 checked, then loaded once with ``torch.load(weights_only=True)`` (offline, on CPU). A file that holds anything but tensors and plain containers is refused by
    torch's restricted unpickler. A test on a synthetic file enforces this; a source test enforces that every ``torch.load`` in the package passes ``weights_only=True``."""
    verify_file(path, expected_sha256)
    return torch.load(path, weights_only=True, map_location="cpu")


def record_tatoeba_digests(paths: Sequence[Path]) -> dict[str, str]:
    """SHA-256 recorded at first download and frozen from then on (the downloaded bytes are kept and verified at every load)."""
    return {p.name: sha256_file(p) for p in paths}


def manifest_json(manifest: Mapping[str, Any]) -> str:
    return json.dumps(manifest, indent=1, sort_keys=True)
