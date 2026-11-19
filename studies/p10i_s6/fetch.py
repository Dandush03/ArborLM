# ruff: noqa: E501
"""P10IS6 fetch stage (ADR-0031 section 6.3, ruling G20), against the project's ledger of record. The lead runs it; the implementer never does (no network here, the tests use a local fixture and a throw-away COPY of the ledger).

Source and pin practice (read from ``arborlm.fetch_wikitext``, which acquired WikiText-2): the publisher repository ``Salesforce/WikiText`` at the pinned revision; file URLs ``https://huggingface.co/datasets/<repo>/resolve/<revision>/<config>/<file>?download=true``;
size and SHA-256 are constants pinned BEFORE the download and verified AFTER it. This module does not assume the Hub's listing API. ``pin`` reads the Git-LFS POINTER FILE of each named train shard at the pinned revision
(``https://huggingface.co/datasets/<repo>/raw/<revision>/<config>/<file>``: a few hundred bytes, ``oid sha256:<hex>`` and ``size <bytes>``; the same ``raw/<revision>/`` form ``fetch_wikitext`` uses for the card) and writes
``studies/p10i_s6/freeze/wikitext103_pins.json`` (refuses to overwrite). The lead names the shards from the dataset's file view (the card's ``data_files`` glob is ``wikitext-103-raw-v1/train-*``). ``get`` refuses unless that pins file exists
(it is a frozen input once committed), then fetches each pinned file and verifies size and SHA-256.

The LEDGER OF RECORD is ``docs/reviews/p10-design-2026-11-15/DOWNLOAD_LEDGER.md``, the one document; no other ledger file is created. P10-S2's code (``studies/p10s2/fetch_guard.py``) appended to it like this and this study does the same through the SAME
functions (imported, frozen inputs): ``ledger_begin`` appends a row with status ``started`` and the DECLARED bytes BEFORE the fetch (columns ``Date (UTC) | Study | What | Source | Revision / hash | Licence | Bytes | Running total (bytes) | Status``,
refusing if the running total would reach the 30 GB standing permission); ``ledger_complete`` sets the bytes actually fetched and the status ``completed`` (or ``failed: <ExceptionType>``); every write recomputes the whole Running-total column and
replaces the file atomically. The Study cell is ``P10-I-S6``. Nothing is ever overwritten; a ``.part`` file is renamed by hard link.
"""

import hashlib
import json
import os
import re
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

from studies.p10s2.fetch_guard import (  # frozen imports (section 15): the ledger of record's own functions
    DOWNLOAD_LEDGER,
    FetchRefused,
    is_git_ignored,
    ledger_begin,
    ledger_complete,
    ledger_total_bytes,
    make_ssl_context,
)

from . import core
from .core import EngineeringStop

Opener = Callable[..., Any]
Downloader = Callable[[str, Path, int], int]  # (url, part file, byte limit) -> bytes written; raises past the limit
TIMEOUT = 60
BLOCK = 1 << 20
STUDY = "P10-I-S6"
PINS = core.FREEZE_DIR / "wikitext103_pins.json"
LICENCE = "CC-BY-SA-3.0/GFDL per card front matter; body CC BY-SA 4.0; discrepancy unresolved; local use only"
POINTER = re.compile(r"^version https://git-lfs\.github\.com/spec/v1\noid sha256:([0-9a-f]{64})\nsize (\d+)\n?$")


def base_url(cfg: Mapping[str, Any], kind: str) -> str:
    d = cfg["data"]
    return f"https://huggingface.co/datasets/{d['publisher_repo']}/{kind}/{d['revision']}/{d['configuration']}"


def parse_pointer(text: str) -> tuple[str, int]:
    m = POINTER.match(text.replace("\r\n", "\n"))
    if not m:
        raise EngineeringStop("ENGINEERING STOP — the file is not a Git-LFS pointer (oid sha256 and size)")
    return m[1], int(m[2])


def pin(names: Sequence[str], cfg: Mapping[str, Any], opener: Opener, out: Path) -> dict[str, Any]:
    """Pin names, sizes and SHA-256 values from the LFS pointer files at the pinned revision. Never overwrites."""
    if out.exists():
        raise EngineeringStop(f"ENGINEERING STOP — {out} exists: a pins file is written once")
    if not names or any(not re.fullmatch(r"train-\d{5}-of-\d{5}\.parquet", n) for n in names):
        raise EngineeringStop("ENGINEERING STOP — only train shards named train-NNNNN-of-NNNNN.parquet are pinned (the test and validation splits are never fetched)")
    files = []
    for n in sorted(names):
        with opener(f"{base_url(cfg, 'raw')}/{n}", timeout=TIMEOUT) as resp:
            sha, size = parse_pointer(resp.read().decode("utf-8"))
        files.append({"name": n, "bytes": size, "sha256": sha, "source": f"LFS pointer at raw/{cfg['data']['revision']}/{cfg['data']['configuration']}/{n}"})
    total = sum(f["bytes"] for f in files)
    if total > int(cfg["data"]["download_hard_stop_bytes"]):
        raise EngineeringStop(f"ENGINEERING STOP — the pinned files total {total} bytes, above the hard stop; not an extension")
    rec = {"repo": cfg["data"]["publisher_repo"], "revision": cfg["data"]["revision"], "configuration": cfg["data"]["configuration"], "expected_configuration_download_bytes": int(cfg["data"]["download_expected_bytes"]), "files": files}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rec, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return rec


def load_pins(path: Path, cfg: Mapping[str, Any]) -> dict[str, Any]:
    if not path.is_file():
        raise EngineeringStop(f"ENGINEERING STOP — no pins file at {path}: pin the shards from their LFS pointers first (``pin``); nothing is fetched without constants fixed before the download")
    rec = json.loads(path.read_text(encoding="utf-8"))
    d = cfg["data"]
    if (rec["repo"], rec["revision"], rec["configuration"]) != (d["publisher_repo"], d["revision"], d["configuration"]) or not rec["files"]:
        raise EngineeringStop("ENGINEERING STOP — the pins file names another repository, revision or configuration than the config")
    if any(not f["name"].startswith("train-") for f in rec["files"]):
        raise EngineeringStop("ENGINEERING STOP — a pinned file is not a train shard")
    return dict(rec)


def urllib_downloader() -> Downloader:  # pragma: no cover - the lead's real download; never run by the implementer
    import urllib.request

    ctx = make_ssl_context()

    def go(url: str, part: Path, limit: int) -> int:
        got = 0
        with urllib.request.urlopen(url, timeout=TIMEOUT, context=ctx) as resp, part.open("xb") as f:  # noqa: S310
            while True:
                block = resp.read(min(BLOCK, limit - got + 1))
                if not block:
                    break
                got += len(block)
                if got > limit:
                    raise FetchRefused(f"refused: {url} sent more than {limit} bytes")
                f.write(block)
            f.flush()
            os.fsync(f.fileno())
        return got

    return go


def get(out_dir: Path, ledger_path: Path, cfg: Mapping[str, Any], pins: Mapping[str, Any], download: Downloader, *, root: Path | None = None) -> dict[str, Any]:
    """One session: for each pinned file, ledger row ``started`` FIRST, fetch to ``.part`` under a byte limit equal to the pin, verify size and SHA-256 after, hard-link into place, complete the row."""
    root = root or core.repo_root()
    if out_dir.exists() and any(out_dir.iterdir()):
        raise EngineeringStop(f"ENGINEERING STOP — {out_dir} is not a fresh folder")
    try:
        out_dir.resolve().relative_to(root.resolve())
        inside = True
    except ValueError:
        inside = False
    if inside and not is_git_ignored(out_dir, root):
        raise EngineeringStop(f"ENGINEERING STOP — {out_dir} is inside the repository and not git-ignored")
    declared = sum(int(f["bytes"]) for f in pins["files"])
    if declared > int(cfg["data"]["download_hard_stop_bytes"]):
        raise EngineeringStop("ENGINEERING STOP — the pinned files exceed the hard stop")
    make_ssl_context()
    out_dir.mkdir(parents=True, exist_ok=True)
    before = ledger_total_bytes(ledger_path)
    done = []
    for f in pins["files"]:
        target, part = out_dir / f["name"], out_dir / (f["name"] + ".part")
        if target.exists() or part.exists():
            raise EngineeringStop(f"ENGINEERING STOP — {target} or its .part exists; nothing is overwritten")
        url = f"{base_url(cfg, 'resolve')}/{f['name']}?download=true"
        idx = ledger_begin(ledger_path, what=f"wikitext103/{f['name']}", source=url, revision=f"{cfg['data']['revision']}; SHA-256 {f['sha256']}", licence=LICENCE, declared_bytes=int(f["bytes"]), study=STUDY)
        got = 0
        try:
            got = download(url, part, int(f["bytes"]))
            if got != int(f["bytes"]):
                raise FetchRefused(f"refused: {f['name']} has {got} bytes, pinned {f['bytes']}")
            with part.open("rb") as fh:
                sha = hashlib.file_digest(fh, "sha256").hexdigest()
            if sha != f["sha256"]:
                raise FetchRefused(f"refused: {f['name']} does not hash to its pinned SHA-256")
            os.link(part, target)
            part.unlink()
        except BaseException as e:
            part.unlink(missing_ok=True)
            ledger_complete(ledger_path, idx, actual_bytes=got, status=f"failed: {type(e).__name__}")
            raise
        ledger_complete(ledger_path, idx, actual_bytes=got, status="completed")
        done.append({"file": f["name"], "bytes": got, "sha256": f["sha256"]})
    return {"files": done, "total_bytes": sum(d["bytes"] for d in done), "ledger_total_before": before, "ledger_total_after": ledger_total_bytes(ledger_path), "ledger": str(DOWNLOAD_LEDGER)}


def main() -> int:  # pragma: no cover - the lead's command
    import argparse
    import urllib.request

    ap = argparse.ArgumentParser(prog="studies.p10i_s6.fetch")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("pin")
    p.add_argument("--files", required=True, help="comma-separated train shard names, e.g. train-00000-of-00002.parquet,...")
    g = sub.add_parser("get")
    g.add_argument("--out-dir", required=True)
    g.add_argument("--ledger", default=str(core.repo_root() / DOWNLOAD_LEDGER))
    a = ap.parse_args()
    cfg = core.load_config()
    if a.cmd == "pin":
        print(json.dumps(pin(a.files.split(","), cfg, urllib.request.urlopen, core.repo_root() / PINS), indent=1))
        return 0
    print(json.dumps(get(Path(a.out_dir), Path(a.ledger), cfg, load_pins(core.repo_root() / PINS, cfg), urllib_downloader()), indent=1))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
