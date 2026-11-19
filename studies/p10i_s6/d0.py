# ruff: noqa: E501
"""P10IS6 stage D0, data preparation (ADR-0031 sections 6.4, 6.5, 16): article exclusion, pools, the uint8 chunk table, the pool-size decision, the panels, the gates, the manifest. Single process; RSS measured, guard 8 GiB.

``prepare`` takes the ROWS (iterables of strings) so that it is tested on small fixtures; ``main`` reads the pinned parquet files (WikiText-103 train shards by the pins file, WikiText-2 train and validation by ``fetch_wikitext.FILES``) and is run with ``python -I`` by
``launch/prepare-data.sh`` from a directory that is not the data directory. No network. The panel ledger is appended through this module's own code (refuses keys that exist).

Panels (section 6.4 rule 6): the registered panel, then the calibration panel, 512 chunks each, by ADR-0026 section 4's walk (``studies.p10i_s3.data.walk_panels``) over the WikiText-2 validation ranking (``pilot_data.select`` with the train candidates excluded), skipping every span already in
the shared ledger and in the extra span files named (P10-I-S3's two panels); the walk starts at ``[data] panel_walk_start`` (8192, ADR-0026 section 4's start, ruling E in the departures list); two new panels are appended to the ledger.
"""

import hashlib
import json
import resource
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

from arborlm.io import atomic_write, canonical_json, file_sha256
from arborlm.pilot_data import CHUNK_BYTES, select
from studies.p10i_s3.data import (  # frozen imports: pure functions, no P10-I-S3 config read
    Span,
    span_of,
    walk_panels,
)

from . import core, corpus
from .core import EngineeringStop

LEDGER_KEYS = ("p10i-s6-registered", "p10i-s6-calibration")


def rss_bytes() -> int:
    r = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(r)  # bytes on macOS (kilobytes on Linux: the platform of record is macOS)


def validation_candidates(train_rows: Sequence[str], val_rows: Sequence[str]) -> tuple[list[Any], list[Span], Mapping[str, Any]]:
    """WikiText-2 validation ranking as ``select`` gives it with every train candidate excluded (counts as ``select`` reports)."""
    _, full_train, _ = select(train_rows, "train", 0)
    n_val = select(val_rows, "validation", 0, excluded=full_train)[2]["eligible_unique_chunks"]
    val, _, counts = select(val_rows, "validation", n_val, excluded=full_train)
    return val, [span_of(c.row, c.offset) for c in val], counts


def spans_in_ledger(ledger: Mapping[str, Any]) -> list[Span]:
    body = ledger["ledger"]
    out: list[Span] = []
    for spans in body.get("panels", {}).values():
        out += [(int(a), int(b), int(c)) for a, b, c in spans]
    out += [(int(a), int(b), int(c)) for a, b, c in body.get("excluded_windows", [])]
    return out


def append_ledger(path: Path, panels: Mapping[str, Sequence[int]], val_spans: Sequence[Span]) -> dict[str, Any]:
    """Append the two new panels to the shared panel ledger (atomic replace; the sha is recomputed the way ``studies.p10i_s3.data.ledger`` does). Refuses a key that exists."""
    rec = json.loads(path.read_text(encoding="utf-8"))
    body = rec["ledger"]
    for k, ranks in panels.items():
        if k in body["panels"] or k in body.get("panel_ranks", {}):
            raise EngineeringStop(f"ENGINEERING STOP — the panel ledger already holds {k}")
        body["panels"][k] = [list(val_spans[r]) for r in ranks]
        body.setdefault("panel_ranks", {})[k] = list(ranks)
    sha = hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    new = {"ledger": body, "sha256": sha}
    atomic_write(path, (json.dumps(new, sort_keys=True) + "\n").encode())
    return {"sha256": sha, "keys": list(panels)}


def prepare(rows103: Iterable[str], wt2_train: Sequence[str], wt2_val: Sequence[str], ledger_path: Path, out_dir: Path, cfg: Mapping[str, Any], *, extra_excluded: Sequence[Span] = (), expect_p1_train_sha: str | None = None) -> dict[str, Any]:
    d = cfg["data"]
    out_dir.mkdir(parents=True, exist_ok=True)
    if (out_dir / "d0_manifest.json").exists():
        raise EngineeringStop("ENGINEERING STOP — a D0 manifest exists in the output folder; D0 is written once")
    label = str(d["rank_label"])
    gates: dict[str, Any] = {}
    # E and the equality gate on WikiText-2 (rule 3)
    e = corpus.excluded_digests([*wt2_train, *wt2_val])
    eq = corpus.reproduces_select(list(wt2_train), "train")
    first = corpus.scan_rows(list(wt2_train))
    sel2 = corpus.select_compact(first, "arborlm-pilot-v1:train", remove_hit_articles=False)
    h = hashlib.sha256(b"".join(corpus.payload_of(first, i) for i in sel2.kept[:4096])).hexdigest()
    gates["select_equal"] = {"passed": bool(eq["passed"]), **eq}
    gates["reproduction"] = {"passed": (expect_p1_train_sha is None) or h == expect_p1_train_sha, "first_4096_train_ranks_sha256": h, "recorded": expect_p1_train_sha}
    # WikiText-103
    sc = corpus.scan_rows(rows103, e)
    sel = corpus.select_compact(sc, label)
    pools, k_max, decision = corpus.decide_pools(sc, sel, cfg)
    table = corpus.write_chunk_table(sc, pools, out_dir, cfg)
    gates["overlap_with_E"] = {"passed": corpus.overlap_with_excluded(sc, pools, e) == 0}
    gates["pools_disjoint"] = {"passed": corpus.pools_disjoint(sc, pools)}
    # panels
    val, val_spans, vcounts = validation_candidates(list(wt2_train), list(wt2_val))
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    excluded = [*spans_in_ledger(ledger), *extra_excluded]
    n = int(cfg["setting"]["panel_chunks"])
    reg_ranks, cal_ranks = walk_panels(val_spans, excluded, int(d["panel_walk_start"]), n, 2)
    panel_bytes = b"".join(val[r].payload for r in [*reg_ranks, *cal_ranks])
    atomic_write(out_dir / "panels.bytes", panel_bytes)
    left = len(val_spans) - int(d["panel_walk_start"]) - 2 * n
    appended = append_ledger(ledger_path, {LEDGER_KEYS[0]: reg_ranks, LEDGER_KEYS[1]: cal_ranks}, val_spans)
    reg_pool_payloads = (corpus.payload_of(sc, i) for i in pools.registered)
    near = corpus.shares_32_byte_substring([val[r].payload for r in reg_ranks], reg_pool_payloads)
    rss = rss_bytes()
    gates["rss"] = {"passed": rss <= int(d["d0_rss_bytes"]), "peak_rss_bytes": rss, "guard": int(d["d0_rss_bytes"])}
    files = {table["name"]: table["sha256"], "panels.bytes": hashlib.sha256(panel_bytes).hexdigest()}
    manifest = {**core.envelope("d0"), "counts": sel.counts, "decision": decision, "table": table, "panels_file": "panels.bytes", "panels": {"registered": reg_ranks, "calibration": cal_ranks, "ledger_append": appended}, "eligible_validation_spans_left_for_panels": left, "validation_counts": dict(vcounts), "near_duplicate_share_registered_panel": near, "gates": gates, "files": files, "k_max": k_max, "rank_label": label}
    atomic_write(out_dir / "d0_manifest.json", canonical_json(core.jsonable(manifest)))
    if not all(g["passed"] for g in gates.values()):
        raise EngineeringStop(f"ENGINEERING STOP — a D0 gate failed: {[k for k, g in gates.items() if not g['passed']]}")
    return manifest


def main() -> int:  # pragma: no cover - the lead's command, run through launch/prepare-data.sh with python -I
    import argparse

    from arborlm.fetch_wikitext import DOWNLOAD_FILES, FILES
    from arborlm.p2_data import P1_TRAIN_SHA256
    from arborlm.pilot_data import _rows

    from . import fetch

    ap = argparse.ArgumentParser(prog="studies.p10i_s6.d0")
    ap.add_argument("--wikitext103-dir", required=True)
    ap.add_argument("--wikitext2-dir", required=True)
    ap.add_argument("--panel-ledger", required=True)
    ap.add_argument("--extra-excluded", action="append", default=[], help="JSON files of [row, start, end] spans (P10-I-S3's two panels if the ledger does not hold them)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    cfg = core.load_config()
    pins = fetch.load_pins(core.repo_root() / fetch.PINS, cfg)
    d103 = Path(a.wikitext103_dir)
    for f in pins["files"]:
        if (d103 / f["name"]).stat().st_size != f["bytes"] or file_sha256(d103 / f["name"]) != f["sha256"]:
            raise EngineeringStop(f"ENGINEERING STOP — {f['name']} does not match its pin")
    d2 = Path(a.wikitext2_dir)
    for n in DOWNLOAD_FILES:
        if (d2 / n).stat().st_size != FILES[n]["bytes"] or file_sha256(d2 / n) != FILES[n]["sha256"]:
            raise EngineeringStop(f"ENGINEERING STOP — pinned WikiText-2 file mismatch: {n}")

    def rows103() -> Iterable[str]:
        for f in sorted(pins["files"], key=lambda x: x["name"]):  # lexicographic order of file name, rows numbered across files
            yield from _rows(d103 / f["name"])

    extra: list[Span] = []
    for p in a.extra_excluded:
        extra += [(int(x), int(y), int(z)) for x, y, z in json.loads(Path(p).read_text())]
    m = prepare(rows103(), list(_rows(d2 / DOWNLOAD_FILES[0])), list(_rows(d2 / DOWNLOAD_FILES[1])), Path(a.panel_ledger), Path(a.out), cfg, extra_excluded=extra, expect_p1_train_sha=P1_TRAIN_SHA256)
    print(json.dumps({"d0_manifest": str(Path(a.out) / "d0_manifest.json"), "k_max": m["k_max"], "pools": [m["table"]["registered_rows"], m["table"]["calibration_rows"]], "gates": {k: g["passed"] for k, g in m["gates"].items()}}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())


__all__ = ["prepare", "CHUNK_BYTES"]
