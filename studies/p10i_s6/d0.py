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
    count_overlaps,
    span_of,
    walk_panels,
)

from . import core, corpus
from .core import EngineeringStop


def rss_bytes() -> int:
    r = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(r)  # bytes on macOS (kilobytes on Linux: the platform of record is macOS)


def validation_candidates(train_rows: Sequence[str], val_rows: Sequence[str]) -> tuple[list[Any], list[Span], Mapping[str, Any]]:
    """WikiText-2 validation ranking as ``select`` gives it with every train candidate excluded (counts as ``select`` reports)."""
    _, full_train, _ = select(train_rows, "train", 0)
    n_val = select(val_rows, "validation", 0, excluded=full_train)[2]["eligible_unique_chunks"]
    val, _, counts = select(val_rows, "validation", n_val, excluded=full_train)
    return val, [span_of(c.row, c.offset) for c in val], counts


LEDGER_FORMAT = "p10i-panel-ledger-v1"
SOURCES = ("P10-I-S6 panel registered", "P10-I-S6 panel calibration")


def read_ledger(path: Path) -> tuple[bytes, dict[str, Any]]:
    """The shared panel ledger as it is on disk (ruling 17): ``{"format": "p10i-panel-ledger-v1", "p10is2": {...}, "windows": [{start, end, first_row, last_row, source, ...}]}``, byte offsets END-EXCLUSIVE in the concatenation of the rows of
    the WikiText-2 validation parquet, rows in file order, nothing between them. Nothing is assumed beyond that; anything else is an engineering stop."""
    raw = path.read_bytes()
    rec = json.loads(raw)
    if rec.get("format") != LEDGER_FORMAT or not isinstance(rec.get("windows"), list) or rec.get("p10is2", {}).get("end_exclusive") is not True:
        raise EngineeringStop(f"ENGINEERING STOP — {path} is not a {LEDGER_FORMAT} ledger with end-exclusive byte windows")
    for w in rec["windows"]:
        if not all(isinstance(w.get(k), int) for k in ("start", "end", "first_row", "last_row")) or not w["start"] < w["end"]:
            raise EngineeringStop("ENGINEERING STOP — a panel-ledger window lacks integer start/end/first_row/last_row")
    return raw, rec


def row_starts(row_lengths: Sequence[int]) -> list[int]:
    starts, t = [], 0
    for n in row_lengths:
        starts.append(t)
        t += int(n)
    return starts


def window_spans(start: int, end: int, starts: Sequence[int], lengths: Sequence[int]) -> list[Span]:
    """A byte window [start, end) of the concatenated rows as (row, start, end) spans in bytes of each row it touches."""
    import bisect

    out: list[Span] = []
    row = max(0, bisect.bisect_right(starts, start) - 1)
    while row < len(starts) and starts[row] < end:
        a_, b_ = max(start, starts[row]), min(end, starts[row] + lengths[row])
        if a_ < b_:
            out.append((row, a_ - starts[row], b_ - starts[row]))
        row += 1
    return out


def spans_in_ledger(ledger: Mapping[str, Any], row_lengths: Sequence[int]) -> list[Span]:
    """Every span the shared ledger excludes: each window of ``ledger["windows"]`` (P10-I-S3's two panels and P10-S2's generation windows) as row spans."""
    if not row_lengths:
        raise EngineeringStop("ENGINEERING STOP — the ledger's byte windows need the validation row lengths")
    starts, lengths = row_starts(row_lengths), list(row_lengths)
    out: list[Span] = []
    for w in ledger["windows"]:
        out += window_spans(int(w["start"]), int(w["end"]), starts, lengths)
    return out


def load_s3_excluded(path: Path, cfg: Mapping[str, Any]) -> tuple[list[Span], str]:
    """P10-I-S3's own excluded set (ruling 16): ``excluded_spans.json``, an object whose ``spans`` field holds [row, start, end] triples; a frozen input by SHA-256 (the config pins it)."""
    sha = file_sha256(path)
    if sha != str(cfg["data"]["s3_excluded_spans_sha256"]):
        raise EngineeringStop(f"ENGINEERING STOP — {path} does not hash to the pinned P10-I-S3 excluded set ({sha[:12]}...)")
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict) or obj.get("format") != "p10i-s3-excluded-spans-v1" or obj.get("end_offsets") != "exclusive" or not isinstance(obj.get("spans"), list):
        raise EngineeringStop("ENGINEERING STOP — the P10-I-S3 excluded-set file does not have the expected format")
    return [(int(r), int(a), int(b)) for r, a, b in obj["spans"]], sha


def new_windows(panels: Mapping[str, Sequence[int]], val_spans: Sequence[Span], starts: Sequence[int]) -> list[dict[str, Any]]:
    """The entries this study adds, in the ledger's own window format (one per panel chunk)."""
    out = []
    for source, ranks in panels.items():
        for r in ranks:
            row, a, b = val_spans[r]
            out.append({"start": starts[row] + a, "end": starts[row] + b, "first_row": row, "last_row": row, "source": source})
    return out


def plan_append(path: Path, add: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Everything about the append EXCEPT writing it: the new bytes and the record (hash before and after, entries added). Refuses a non-canonical ledger (the old entries must keep their bytes), a ledger that already holds this study's windows, and any change
    to an existing key or entry."""
    raw, rec = read_ledger(path)
    canon = (json.dumps(rec, sort_keys=True, separators=(",", ":")) + "\n").encode()
    if canon != raw:
        raise EngineeringStop("ENGINEERING STOP — the panel ledger is not in canonical form; appending would rewrite it")
    if any(w.get("source") in SOURCES for w in rec["windows"]):
        raise EngineeringStop("ENGINEERING STOP — the panel ledger already holds P10-I-S6 windows")
    before = hashlib.sha256(raw).hexdigest()
    old_windows = json.loads(raw)["windows"]
    rec["windows"] = [*rec["windows"], *add]
    new = (json.dumps(rec, sort_keys=True, separators=(",", ":")) + "\n").encode()
    check = json.loads(new)
    if check["windows"][: len(old_windows)] != old_windows or {k: v for k, v in check.items() if k != "windows"} != {k: v for k, v in json.loads(raw).items() if k != "windows"}:
        raise EngineeringStop("ENGINEERING STOP — appending would change an existing key or entry")
    return {"new_bytes": new, "before_bytes_sha256": before, "info": {"sha256_before": before, "sha256_after": hashlib.sha256(new).hexdigest(), "entries_added": len(add), "windows_before": len(old_windows), "windows_after": len(check["windows"])}}


def commit_append(path: Path, plan: Mapping[str, Any]) -> dict[str, Any]:
    """The append, the LAST act of D0: it writes only if the file still has the hash the plan was made on."""
    if hashlib.sha256(path.read_bytes()).hexdigest() != plan["before_bytes_sha256"]:
        raise EngineeringStop("ENGINEERING STOP — the panel ledger changed since D0 planned its append")
    atomic_write(path, plan["new_bytes"])
    return dict(plan["info"])


def append_panels(path: Path, add: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Append entries to ``windows`` without rewriting any existing key or entry (ruling 17): plan, then commit."""
    return commit_append(path, plan_append(path, add))


def ledger_state(path: Path, add: Sequence[Mapping[str, Any]]) -> str:
    """``absent``: the ledger holds none of this study's windows. ``present``: it holds EXACTLY ``add`` (by value, in order) as its last entries. Anything else (some of them, other content, other places) is an engineering stop."""
    _, rec = read_ledger(path)
    mine = [i for i, w in enumerate(rec["windows"]) if w.get("source") in SOURCES]
    if not mine:
        return "absent"
    n = len(add)
    if mine != list(range(len(rec["windows"]) - n, len(rec["windows"]))) or rec["windows"][-n:] != json.loads(json.dumps(list(add))):
        raise EngineeringStop("ENGINEERING STOP — the panel ledger holds P10-I-S6 windows that are not exactly this D0's panels (or not at its end): it is not accepted")
    return "present"


def verify_output(out_dir: Path) -> dict[str, Any]:
    """The output is complete and verified: the manifest exists, every file it lists is there and hashes to what it says, the table has its recorded size."""
    mf = out_dir / "d0_manifest.json"
    if not mf.is_file():
        raise EngineeringStop("ENGINEERING STOP — the D0 output has no manifest")
    m = json.loads(mf.read_text(encoding="utf-8"))
    for name, digest in m["files"].items():
        f = out_dir / name
        if not f.is_file() or file_sha256(f) != digest:
            raise EngineeringStop(f"ENGINEERING STOP — the D0 output file {name} is missing or does not hash to the manifest")
    if (out_dir / m["table"]["name"]).stat().st_size != int(m["table"]["rows"]) * 65:
        raise EngineeringStop("ENGINEERING STOP — the chunk table has the wrong size")
    return m  # type: ignore[no-any-return]


def prepare(rows103: Iterable[str], wt2_train: Sequence[str], wt2_val: Sequence[str], ledger_path: Path, out_dir: Path, cfg: Mapping[str, Any], *, s3_excluded: Sequence[Span] = (), s3_excluded_sha256: str | None = None, expect_p1_train_sha: str | None = None) -> dict[str, Any]:
    """Order of acts (audit N1, ruling 17): everything this study writes for itself, the manifest in its final form included, is built in ``out_dir/_work``, moved into place and VERIFIED; only then is the shared ledger appended, as the very last act.
    A failure before the append leaves the ledger untouched and the partial work kept aside as ``_failed-N``. A rerun that finds a complete verified output accepts it: if the ledger does not yet hold the windows it performs only the append; if it already holds exactly
    these windows (by value) it changes nothing. Any other state is refused."""
    out_dir.mkdir(parents=True, exist_ok=True)
    if (out_dir / "d0_manifest.json").exists():
        return _resume(wt2_train, wt2_val, ledger_path, out_dir)
    work = out_dir / "_work"
    if work.exists():
        work.rename(out_dir / f"_failed-{len(list(out_dir.glob('_failed-*')))}")
    work.mkdir()
    try:
        manifest, plan = _prepare(rows103, wt2_train, wt2_val, ledger_path, work, cfg, s3_excluded, s3_excluded_sha256, expect_p1_train_sha)
    except BaseException:
        work.rename(out_dir / f"_failed-{len(list(out_dir.glob('_failed-*')))}")
        raise
    for f in sorted(work.iterdir(), key=lambda p: p.name == "d0_manifest.json"):  # the manifest is moved last: its presence means the output is complete
        f.rename(out_dir / f.name)
    work.rmdir()
    verify_output(out_dir)
    commit_append(ledger_path, plan)  # the last act
    return manifest


def _resume(wt2_train: Sequence[str], wt2_val: Sequence[str], ledger_path: Path, out_dir: Path) -> dict[str, Any]:
    m = verify_output(out_dir)
    lengths = [len(r.encode("utf-8")) for r in wt2_val]
    _, vspans, _ = validation_candidates(list(wt2_train), list(wt2_val))
    adds = new_windows({SOURCES[0]: m["panels"]["registered"], SOURCES[1]: m["panels"]["calibration"]}, vspans, row_starts(lengths))
    info = m["panels"]["ledger_append"]
    if ledger_state(ledger_path, adds) == "present":
        if hashlib.sha256(ledger_path.read_bytes()).hexdigest() != info["sha256_after"]:
            raise EngineeringStop("ENGINEERING STOP — the ledger holds this D0's windows but its hash is not the one the manifest recorded")
        return m
    plan = plan_append(ledger_path, adds)
    if plan["info"] != info:
        raise EngineeringStop("ENGINEERING STOP — the ledger is not the file this D0 was prepared against (its hash before differs from the manifest's)")
    commit_append(ledger_path, plan)
    return m


def _prepare(rows103: Iterable[str], wt2_train: Sequence[str], wt2_val: Sequence[str], ledger_path: Path, out_dir: Path, cfg: Mapping[str, Any], s3_excluded: Sequence[Span], s3_sha: str | None, expect_p1_train_sha: str | None) -> tuple[dict[str, Any], dict[str, Any]]:
    d = cfg["data"]
    label = str(d["rank_label"])
    gates: dict[str, Any] = {}
    e = corpus.excluded_digests([*wt2_train, *wt2_val])
    eq = corpus.reproduces_select(list(wt2_train), "train")
    first = corpus.scan_rows(list(wt2_train))
    sel2 = corpus.select_compact(first, "arborlm-pilot-v1:train", remove_hit_articles=False)
    h = hashlib.sha256(b"".join(corpus.payload_of(first, i) for i in sel2.kept[:4096])).hexdigest()
    gates["select_equal"] = {"passed": bool(eq["passed"]), **eq}
    gates["reproduction"] = {"passed": (expect_p1_train_sha is None) or h == expect_p1_train_sha, "first_4096_train_ranks_sha256": h, "recorded": expect_p1_train_sha}
    sc = corpus.scan_rows(rows103, e)
    sel = corpus.select_compact(sc, label)
    pools, k_max, decision = corpus.decide_pools(sc, sel, cfg)
    table = corpus.write_chunk_table(sc, pools, out_dir, cfg)
    gates["overlap_with_E"] = {"passed": corpus.overlap_with_excluded(sc, pools, e) == 0}
    gates["pools_disjoint"] = {"passed": corpus.pools_disjoint(sc, pools)}
    # panels: the excluded set is every span of the shared ledger + P10-I-S3's own excluded set (ruling 16; its two panels are windows of the ledger)
    val, val_spans, vcounts = validation_candidates(list(wt2_train), list(wt2_val))
    lengths = [len(r.encode("utf-8")) for r in wt2_val]
    _, ledger = read_ledger(ledger_path)
    excluded = [*spans_in_ledger(ledger, lengths), *s3_excluded]
    n = int(cfg["setting"]["panel_chunks"])
    reg_ranks, cal_ranks = walk_panels(val_spans, excluded, int(d["panel_walk_start"]), n, 2)
    new_spans = [val_spans[r] for r in [*reg_ranks, *cal_ranks]]
    gates["panels_disjoint_from_excluded"] = {"passed": count_overlaps(new_spans, excluded) == 0, "excluded_spans": len(excluded), "s3_excluded_spans": len(s3_excluded)}
    panel_bytes = b"".join(val[r].payload for r in [*reg_ranks, *cal_ranks])
    atomic_write(out_dir / "panels.bytes", panel_bytes)
    left = len(val_spans) - int(d["panel_walk_start"]) - 2 * n
    near = corpus.shares_32_byte_substring([val[r].payload for r in reg_ranks], (corpus.payload_of(sc, i) for i in pools.registered))
    rss = rss_bytes()
    gates["rss"] = {"passed": rss <= int(d["d0_rss_bytes"]), "peak_rss_bytes": rss, "guard": int(d["d0_rss_bytes"])}
    if not all(g["passed"] for g in gates.values()):
        raise EngineeringStop(f"ENGINEERING STOP — a D0 gate failed: {[k for k, g in gates.items() if not g['passed']]}")
    adds = new_windows({SOURCES[0]: reg_ranks, SOURCES[1]: cal_ranks}, val_spans, row_starts(lengths))
    plan = plan_append(ledger_path, adds)  # planned here, WRITTEN last (by ``prepare``, after the output is in place and verified)
    appended = plan["info"]
    files = {table["name"]: table["sha256"], "panels.bytes": hashlib.sha256(panel_bytes).hexdigest()}
    manifest = {**core.envelope("d0"), "counts": sel.counts, "decision": decision, "table": table, "panels_file": "panels.bytes", "panels": {"registered": reg_ranks, "calibration": cal_ranks, "ledger_append": appended}, "eligible_validation_spans_left_for_panels": left, "validation_counts": dict(vcounts), "near_duplicate_share_registered_panel": near, "gates": gates, "files": files, "k_max": k_max, "rank_label": label, "s3_excluded_spans_sha256": s3_sha}
    atomic_write(out_dir / "d0_manifest.json", canonical_json(core.jsonable(manifest)))
    return manifest, plan


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
    ap.add_argument("--s3-excluded-spans", required=True, help="P10-I-S3's excluded_spans.json (an object with a `spans` field; pinned by SHA-256 in the config)")
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

    s3_spans, s3_sha = load_s3_excluded(Path(a.s3_excluded_spans), cfg)
    m = prepare(rows103(), list(_rows(d2 / DOWNLOAD_FILES[0])), list(_rows(d2 / DOWNLOAD_FILES[1])), Path(a.panel_ledger), Path(a.out), cfg, s3_excluded=s3_spans, s3_excluded_sha256=s3_sha, expect_p1_train_sha=P1_TRAIN_SHA256)
    print(json.dumps({"d0_manifest": str(Path(a.out) / "d0_manifest.json"), "k_max": m["k_max"], "pools": [m["table"]["registered_rows"], m["table"]["calibration_rows"]], "gates": {k: g["passed"] for k, g in m["gates"].items()}}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())


__all__ = ["prepare", "CHUNK_BYTES"]
