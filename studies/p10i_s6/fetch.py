# ruff: noqa: E501
"""P10IS6 fetch stage (ADR-0031 section 6.3, ruling G20): the WikiText-103 raw TRAIN parquet files of the pinned publisher repository and revision. The lead runs it; the implementer never does (no network here, the tests use a local fixture).

Order: (1) the repository listing at the pinned revision gives the train file names with their LFS size and SHA-256; (2) one ledger row per file is written BEFORE the fetch (status PLANNED: URL at the pinned revision, expected bytes and
SHA-256); (3) each file is streamed to a staging name under a byte cap equal to its expected size; (4) size and SHA-256 are verified AFTER it, and a completion row is written (COMPLETE or FAILED); a mismatch is an engineering stop and
the staged file is kept as failure evidence; (5) the file is published without replacing anything. The test and validation splits are never listed for fetching. A total above the hard stop is an engineering stop, not an extension.

The ledger is written in two forms: ``DOWNLOAD_LEDGER_S6.jsonl`` (one JSON object per event) and ``DOWNLOAD_LEDGER_S6.md`` (one table row per event). The project's own ``DOWNLOAD_LEDGER.md`` lives in the git-ignored ``data/`` of
the lead's checkout and its exact column layout could not be read from this worktree (listed as an ambiguity): the rows carry the fields it is known to hold (date, URL at the pinned revision, file, expected and actual bytes, SHA-256).
"""

import hashlib
import json
import os
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from . import core
from .core import EngineeringStop

Opener = Callable[..., Any]
TIMEOUT = 60
BLOCK = 1 << 20
LICENCE = "publisher card front matter CC-BY-SA-3.0/GFDL, body CC BY-SA 4.0; discrepancy unresolved; local use only was approved (ADR-0004); no publication rights inferred"


def listing_url(cfg: Mapping[str, Any]) -> str:
    d = cfg["data"]
    return f"https://huggingface.co/api/datasets/{d['publisher_repo']}/tree/{d['revision']}/{d['configuration']}"


def file_url(cfg: Mapping[str, Any], path: str) -> str:
    d = cfg["data"]
    return f"https://huggingface.co/datasets/{d['publisher_repo']}/resolve/{d['revision']}/{path}?download=true"


def plan_from_listing(listing: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any]) -> list[dict[str, Any]]:
    """The train parquet files of the configuration, in lexicographic order of file name (the order the pools read them in), with LFS size and SHA-256. Anything that is not a train parquet file is ignored (the test and validation splits are never fetched)."""
    conf = str(cfg["data"]["configuration"])
    rows = []
    for e in listing:
        path = str(e.get("path", ""))
        name = path.split("/")[-1]
        if e.get("type") != "file" or not path.startswith(f"{conf}/") or not name.startswith("train-") or not name.endswith(".parquet"):
            continue
        lfs = e.get("lfs")
        if not isinstance(lfs, Mapping) or "oid" not in lfs or "size" not in lfs:
            raise EngineeringStop(f"ENGINEERING STOP — the listing gives no LFS size and SHA-256 for {path}")
        rows.append({"file": name, "path": path, "url": file_url(cfg, path), "expected_bytes": int(lfs["size"]), "expected_sha256": str(lfs["oid"])})
    rows.sort(key=lambda r: str(r["file"]))
    if not rows:
        raise EngineeringStop("ENGINEERING STOP — the listing at the pinned revision has no train parquet file")
    total = sum(int(r["expected_bytes"]) for r in rows)
    if total > int(cfg["data"]["download_hard_stop_bytes"]):
        raise EngineeringStop(f"ENGINEERING STOP — the train files total {total} bytes, above the hard stop of {int(cfg['data']['download_hard_stop_bytes'])}; a larger size is not an extension")
    return rows


def _row_md(row: Mapping[str, Any]) -> str:
    return "| {utc} | {status} | {file} | {url} | {expected_bytes} | {expected_sha256} | {actual_bytes} | {actual_sha256} | {running_total_bytes} | {note} |".format(**{k: row.get(k, "") for k in ("utc", "status", "file", "url", "expected_bytes", "expected_sha256", "actual_bytes", "actual_sha256", "running_total_bytes", "note")})


def append_ledger(ledger_dir: Path, row: Mapping[str, Any]) -> None:
    ledger_dir.mkdir(parents=True, exist_ok=True)
    row = {"utc": datetime.now(UTC).isoformat(), **row}
    with (ledger_dir / "DOWNLOAD_LEDGER_S6.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, sort_keys=True) + "\n")
        f.flush()
        os.fsync(f.fileno())
    md = ledger_dir / "DOWNLOAD_LEDGER_S6.md"
    if not md.exists():
        md.write_text("| utc | status | file | URL at the pinned revision | expected bytes | expected SHA-256 (LFS) | actual bytes | actual SHA-256 | running total (this study) | note |\n|---|---|---|---|---|---|---|---|---|---|\n", encoding="utf-8")
    with md.open("a", encoding="utf-8") as f:
        f.write(_row_md(row) + "\n")


def _stream(opener: Opener, url: str, dest: Path, cap: int) -> tuple[int, str]:
    digest, got = hashlib.sha256(), 0
    with opener(url, timeout=TIMEOUT) as resp, dest.open("xb") as out:
        length = resp.headers.get("Content-Length")
        if length is not None and int(length) > cap:
            raise EngineeringStop(f"ENGINEERING STOP — declared size {length} of {url} exceeds the expected {cap}")
        while True:
            block = resp.read(min(BLOCK, cap - got + 1))
            if not block:
                break
            got += len(block)
            if got > cap:
                raise EngineeringStop(f"ENGINEERING STOP — {url} sent more than the expected {cap} bytes")
            out.write(block)
            digest.update(block)
        out.flush()
        os.fsync(out.fileno())
    return got, digest.hexdigest()


def fetch(out_dir: Path, ledger_dir: Path, cfg: Mapping[str, Any], opener: Opener, *, running_total_before: int = 0) -> dict[str, Any]:
    """The whole stage. ``opener(url, timeout=...)`` is ``urllib.request.urlopen`` in the real run and a local fixture in tests. Existing files that verify are kept; an existing file that does not verify is preserved and is an engineering stop."""
    with opener(listing_url(cfg), timeout=TIMEOUT) as resp:
        listing = json.loads(resp.read())
    plan = plan_from_listing(listing, cfg)
    for r in plan:  # (2) every row is on the ledger before any fetch
        append_ledger(ledger_dir, {"status": "PLANNED", "file": r["file"], "url": r["url"], "expected_bytes": r["expected_bytes"], "expected_sha256": r["expected_sha256"], "note": f"revision {cfg['data']['revision']}; {LICENCE}"})
    out_dir.mkdir(parents=True, exist_ok=True)
    total = running_total_before
    done: list[dict[str, Any]] = []
    for r in plan:
        target = out_dir / str(r["file"])
        if target.exists():
            ok = target.stat().st_size == r["expected_bytes"] and hashlib.file_digest(target.open("rb"), "sha256").hexdigest() == r["expected_sha256"]
            if not ok:
                append_ledger(ledger_dir, {"status": "FAILED", "file": r["file"], "note": "an existing file does not match the LFS size or SHA-256; preserved"})
                raise EngineeringStop(f"ENGINEERING STOP — existing {target} does not match the pinned LFS size and SHA-256; preserved as evidence")
            total += int(r["expected_bytes"])
            append_ledger(ledger_dir, {"status": "COMPLETE", "file": r["file"], "actual_bytes": r["expected_bytes"], "actual_sha256": r["expected_sha256"], "running_total_bytes": total, "note": "already present and verified"})
            done.append(r)
            continue
        staged = out_dir / f".staging-{r['file']}"
        if staged.exists():
            raise EngineeringStop(f"ENGINEERING STOP — a staged file already exists: {staged} (kept; remove it by hand after looking)")
        try:
            got, sha = _stream(opener, str(r["url"]), staged, int(r["expected_bytes"]))
        except EngineeringStop as e:
            append_ledger(ledger_dir, {"status": "FAILED", "file": r["file"], "note": str(e)[:200]})
            raise
        if got != r["expected_bytes"] or sha != r["expected_sha256"]:
            append_ledger(ledger_dir, {"status": "FAILED", "file": r["file"], "actual_bytes": got, "actual_sha256": sha, "note": "size or SHA-256 differs from the LFS metadata; the staged file is kept"})
            raise EngineeringStop(f"ENGINEERING STOP — {r['file']}: {got} bytes / {sha} differ from the LFS {r['expected_bytes']} / {r['expected_sha256']} (staged file kept)")
        try:
            os.link(staged, target)
        except FileExistsError as e:
            raise EngineeringStop(f"ENGINEERING STOP — {target} appeared during the fetch; kept") from e
        staged.unlink()
        total += got
        append_ledger(ledger_dir, {"status": "COMPLETE", "file": r["file"], "actual_bytes": got, "actual_sha256": sha, "running_total_bytes": total})
        done.append(r)
    return {"files": [{k: r[k] for k in ("file", "expected_bytes", "expected_sha256")} for r in done], "total_bytes": total - running_total_before, "revision": cfg["data"]["revision"], "configuration": cfg["data"]["configuration"], "listing_url": listing_url(cfg)}


def main() -> int:  # pragma: no cover - the lead's command; it is never run by the implementer
    import argparse
    import urllib.request

    ap = argparse.ArgumentParser(prog="studies.p10i_s6.fetch")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--ledger-dir", required=True)
    ap.add_argument("--running-total-bytes", type=int, default=0)
    a = ap.parse_args()
    cfg = core.load_config()
    res = fetch(Path(a.out_dir), Path(a.ledger_dir), cfg, urllib.request.urlopen, running_total_before=a.running_total_bytes)
    print(json.dumps(res, indent=1))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
