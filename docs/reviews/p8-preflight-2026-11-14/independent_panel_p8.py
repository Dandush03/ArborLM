"""P8 pre-freeze panel proof (ADR-0015 section 6): are Panel A (validation ranks [3072, 3584)) and
Panel B ([3584, 4096)) eligible, unused and disjoint?

Auditor role (model claude-opus-5-5, from session metadata). Written from the registered recipe text
``arborlm-pilot-v1`` (pilot_data.RECIPE, read but not imported):
  - each row's exact UTF-8 bytes, cut into 65-byte chunks at stride 65 from offset 0; a trailing
    remainder shorter than 65 bytes is dropped;
  - rank key of a chunk = (sha256("arborlm-pilot-v1:{split}:{row}:{offset}") hex, row, offset);
  - within a split, among chunks with identical contents only the lowest rank key is kept;
  - a validation chunk whose contents equal ANY train chunk is excluded before deduplication;
  - "rank n" is the zero-based position in the ascending sort of the kept keys;
  - the training candidate pool is train ranks [0, 4096); calibration stream = train ranks [2048, 2560).
No ``arborlm`` import. Standard library only, plus ``pyarrow`` to read the parquet text column.
Run: uv run --locked --extra pilot python -I docs/reviews/p8-preflight-2026-11-14/independent_panel_p8.py
Reads raw text only; runs no model, evaluates nothing, writes only into this review folder.
Independent engineering evidence; not Astra validation; not human approval.
"""

from __future__ import annotations

import hashlib
import json
import platform
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
DATA = Path("/Users/daniellaloush/dandush03/ArborLM/data/wikitext2")  # main checkout, read only
OUT = HERE / "panel_confirmation.json"

CHUNK = 65
BLOCK = 512
TRAIN_POOL = 4096
PINNED = {  # fetch_wikitext.FILES at revision b08601e04326c79dfdd32d625aee71d232d685c3
    "train-00000-of-00001.parquet": ("e83889baabc497075506f91975be5fac0d45c5290b6b20582c8cd1e853d0c9f7", 6_357_543),
    "validation-00000-of-00001.parquet": ("204929b7ff9d6184953f867dedb860e40aa69c078fc1e54b3baaa8fb28511c4c", 657_209),
}
# Recorded panel byte hashes and where they are recorded.
EARLIER = {
    "P1": ((0, 512), "2e6b71b9472abf50f9c4705f2f8f13a69465a9f1b8360119ce5882872b772200", "src/arborlm/p2_data.py P1_VALIDATION_SHA256"),
    "P2": ((512, 1024), "8cd4ab927f9ff17f12bba56b011cf11a94d66e1b77f5f4eba97dd100fb455cd2", "src/arborlm/p3_data.py P2_VALIDATION_SHA256"),
    "P3": ((1024, 1536), "a2d63d4ed5300c74f49374c0e0c5bd6e70d4361bc0b2933a8d5ad33a08d724b0", "src/arborlm/p4_data.py P3_VALIDATION_SHA256"),
    "P4": ((1536, 2048), "4c6fb3f3a8f22d2e5b14c6703d3d8e02b40681482d5b93ba491e2df0583dc28f", "src/arborlm/p4_data.py P4_VALIDATION_SHA256"),
    "P5": ((2048, 2560), "d50cbe4c303791148c922bfe9201fe00b192c44deef855077860ffc98cc72b98", "src/arborlm/p5_data.py P5_VALIDATION_SHA256"),
    "P7B_streamB": ((2560, 3072), "4e2c9d971ee5a1e689cba50db79fd2de500f8098de239411e5b12b9ebd240731",
                    "results/p7b-2026-11-13/panel/P7BP-20261114T013656010347Z-9433b10446e5458885b6cb83f8d1a915/panel_record.json panel_sha256"),
}
P7B_RECORD = REPO / "results/p7b-2026-11-13/panel/P7BP-20261114T013656010347Z-9433b10446e5458885b6cb83f8d1a915/panel_record.json"
P5_MANIFEST = REPO / "results/p5-2026-11-13/b101-o301-baseline/dataset_manifest.json"
P1_TRAIN_BYTES_SHA256 = "1c3e7a3e02087392ae3db874935517c66e77f15d7a50c3285a8c5ba5d7fabd07"
NEW = {"panel_A": (3072, 3584), "panel_B": (3584, 4096)}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fsha(path: Path) -> str:
    d = hashlib.sha256()
    with open(path, "rb") as fh:
        while block := fh.read(1 << 20):
            d.update(block)
    return d.hexdigest()


def read_text_column(path: Path) -> list[str]:
    import pyarrow.parquet as pq

    table = pq.read_table(path, columns=["text"], use_threads=False)
    return [str(x) if isinstance(x, str) else x for x in table.column("text").to_pylist()]


def rank_split(rows: list[str], split: str, exclude: set[str] | None):
    """Return (ranked list of dicts, set of kept content digests, set of ALL content digests seen
    before exclusion, counters)."""
    kept: dict[str, tuple[str, int, int, bytes]] = {}
    seen_all: set[str] = set()
    n_full = n_excl = n_dup = rem = 0
    for row, text in enumerate(rows):
        if not isinstance(text, str):
            raise SystemExit(f"STOP: non-string row {split}:{row}")
        b = text.encode("utf-8")
        rem += len(b) % CHUNK
        n = len(b) // CHUNK
        for k in range(n):
            off = k * CHUNK
            payload = b[off : off + CHUNK]
            dig = sha(payload)
            n_full += 1
            seen_all.add(dig)
            if exclude is not None and dig in exclude:
                n_excl += 1
                continue
            key = (sha(f"arborlm-pilot-v1:{split}:{row}:{off}".encode()), row, off)
            prev = kept.get(dig)
            if prev is not None:
                n_dup += 1
                if key < prev[:3]:
                    kept[dig] = (*key, payload)
            else:
                kept[dig] = (*key, payload)
    order = sorted(kept.items(), key=lambda kv: kv[1][:3])
    ranked = [{"rank": i, "rank_sha256": v[0], "row": v[1], "byte_offset": v[2], "payload": v[3], "chunk_sha256": d}
              for i, (d, v) in enumerate(order)]
    counts = {"rows": len(rows), "remainder_bytes": rem, "full_chunks": n_full, "excluded_cross_split": n_excl,
              "duplicates_after_cross_split": n_dup, "eligible_unique_chunks": len(ranked)}
    return ranked, set(kept), seen_all, counts


def block_bytes(ranked: list[dict], lo: int, hi: int) -> bytes:
    return b"".join(c["payload"] for c in ranked[lo:hi])


def selection_bytes(ranked: list[dict], lo: int, hi: int, *, local_rank: bool) -> bytes:
    """Canonical JSON (sorted keys, compact separators, trailing newline) of the selection list
    [{rank, row, byte_offset, rank_sha256, chunk_sha256}]. P2/P5 '*.selected.json' numbered ranks
    from 0 within the list; for the new panels the global rank is used (as in the P7-B record's
    rows_detail). Both forms are reported for the new panels."""
    items = [{"rank": (i if local_rank else lo + i), "row": c["row"], "byte_offset": c["byte_offset"],
              "rank_sha256": c["rank_sha256"], "chunk_sha256": c["chunk_sha256"]}
             for i, c in enumerate(ranked[lo:hi])]
    return (json.dumps(items, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def article_index(rows: list[str]) -> list[int]:
    """Descriptive only: article id per row, where a WikiText top-level heading row looks like
    ' = Title = ' (and not ' = = Sub = = '). Rows before the first heading get -1."""
    out, cur = [], -1
    for t in rows:
        s = t.strip()
        if t.startswith(" = ") and not t.startswith(" = = ") and s.startswith("= ") and s.endswith(" =") and not s.startswith("= ="):
            cur += 1
        out.append(cur)
    return out


def main() -> int:
    inputs = {}
    rows = {}
    for name, split in (("train-00000-of-00001.parquet", "train"), ("validation-00000-of-00001.parquet", "validation")):
        p = DATA / name
        digest, size = PINNED[name]
        got = fsha(p)
        inputs[name] = {"path": str(p), "sha256": got, "bytes": p.stat().st_size,
                        "matches_pinned": got == digest and p.stat().st_size == size}
        if not inputs[name]["matches_pinned"]:
            raise SystemExit(f"STOP: pinned file mismatch {name}")
        rows[split] = read_text_column(p)
    inputs["manifest.json"] = {"path": str(DATA / "manifest.json"), "sha256": fsha(DATA / "manifest.json")}

    train, train_kept, train_all, tcounts = rank_split(rows["train"], "train", None)
    val, _, _, vcounts = rank_split(rows["validation"], "validation", train_all)
    eligible = len(val)
    result: dict = {
        "schema": "p8-panel-confirmation-v1",
        "tool": "independent_panel_p8.py (auditor role, claude-opus-5-5) v1",
        "tool_sha256": fsha(Path(__file__)),
        "label": "independent engineering evidence; not Astra validation; not human approval",
        "inputs": inputs,
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "counts": {"train": tcounts, "validation": vcounts},
        "validation_eligible_candidates": eligible,
        "at_least_4096_eligible": eligible >= 4096,
    }
    if eligible < 4096:
        result["verdict"] = f"STOP: only {eligible} eligible validation candidates (< 4096)"
        OUT.write_text(json.dumps(result, indent=1, sort_keys=True) + "\n")
        print(result["verdict"])
        return 2

    # sanity: ordering strictly increasing and unique content in the ranked list
    keys = [(c["rank_sha256"], c["row"], c["byte_offset"]) for c in val]
    result["ranking_sanity"] = {
        "strictly_increasing_keys": all(a < b for a, b in zip(keys, keys[1:])),
        "unique_contents": len({c["chunk_sha256"] for c in val}) == len(val),
        "no_validation_candidate_equals_any_train_chunk": not ({c["chunk_sha256"] for c in val} & train_all),
        "all_payloads_65_bytes": all(len(c["payload"]) == CHUNK for c in val[:4096]),
    }

    # 2. earlier panels
    earlier = {}
    for name, ((lo, hi), recorded, source) in EARLIER.items():
        got = sha(block_bytes(val, lo, hi))
        earlier[name] = {"ranks": [lo, hi], "sha256": got, "recorded_sha256": recorded, "recorded_in": source,
                         "reproduced": got == recorded}
    result["earlier_panels"] = earlier
    result["all_six_earlier_reproduced"] = all(v["reproduced"] for v in earlier.values())

    # extra identity cross-checks against recorded artifacts (read only)
    p5 = json.loads(P5_MANIFEST.read_text())
    p7b = json.loads(P7B_RECORD.read_text())
    pool = train[:TRAIN_POOL]
    result["identity_crosschecks"] = {
        "train_pool_bytes_equals_P1_train_bytes": sha(block_bytes(train, 0, TRAIN_POOL)) == P1_TRAIN_BYTES_SHA256,
        "train_selection_equals_P5_train.selected.json": sha(selection_bytes(train, 0, TRAIN_POOL, local_rank=True))
        == p5["checksums_sha256"]["train.selected.json"],
        "validation_first_2560_selection_equals_P5": sha(selection_bytes(val, 0, 2560, local_rank=True))
        == p5["checksums_sha256"]["validation_first_2560.selected.json"],
        "validation_counts_equal_P5_manifest": all(vcounts[k] == p5["counts"]["validation"][k] for k in vcounts),
        "train_counts_equal_P5_manifest": all(tcounts[k] == p5["counts"]["train"][k] for k in tcounts),
        "P7B_streamB_row_sha256_list_equal": [c["chunk_sha256"] for c in val[2560:3072]] == p7b["row_sha256"],
        "P7B_streamB_rows_detail_equal": [(c["rank"], c["row"], c["byte_offset"], c["rank_sha256"]) for c in val[2560:3072]]
        == [(d["rank"], d["row"], d["byte_offset"], d["rank_sha256"]) for d in p7b["rows_detail"]],
        "P5_manifest_sha256": fsha(P5_MANIFEST),
        "P7B_panel_record_sha256": fsha(P7B_RECORD),
    }

    # 3. new panels
    cal = train[2048:2560]
    sets = {
        "earlier_validation_ranks_0_3071": {c["chunk_sha256"] for c in val[:3072]},
        "calibration_stream_train_ranks_2048_2559": {c["chunk_sha256"] for c in cal},
        "training_candidate_pool_train_ranks_0_4095": {c["chunk_sha256"] for c in pool},
        "every_train_chunk_in_file": train_all,
    }
    for name, ((lo, hi), _, _) in EARLIER.items():
        sets[f"earlier_{name}_ranks_{lo}_{hi - 1}"] = {c["chunk_sha256"] for c in val[lo:hi]}

    panels = {}
    digs = {}
    for name, (lo, hi) in NEW.items():
        block = val[lo:hi]
        d = [c["chunk_sha256"] for c in block]
        digs[name] = set(d)
        panels[name] = {
            "ranks": [lo, hi],
            "ranks_inclusive": [lo, hi - 1],
            "rows": len(block),
            "bytes": len(block_bytes(val, lo, hi)),
            "panel_sha256": sha(block_bytes(val, lo, hi)),
            "row_sha256_list_sha256": sha(("\n".join(d) + "\n").encode()),
            "selection_sha256_global_rank": sha(selection_bytes(val, lo, hi, local_rank=False)),
            "selection_sha256_local_rank": sha(selection_bytes(val, lo, hi, local_rank=True)),
            "duplicates_within_panel": len(d) - len(set(d)),
            "overlap": {k: len(set(d) & s) for k, s in sets.items()},
            "first_rows_detail": [{"rank": c["rank"], "row": c["row"], "byte_offset": c["byte_offset"],
                                   "rank_sha256": c["rank_sha256"], "chunk_sha256": c["chunk_sha256"]} for c in block[:3]],
        }
    panels["panel_A"]["overlap"]["other_new_panel"] = len(digs["panel_A"] & digs["panel_B"])
    panels["panel_B"]["overlap"]["other_new_panel"] = len(digs["panel_A"] & digs["panel_B"])
    result["new_panels"] = panels
    result["zero_exact_overlap"] = all(
        p["duplicates_within_panel"] == 0 and not any(p["overlap"].values()) and p["rows"] == BLOCK for p in panels.values())

    # 4b. descriptive near-duplicate / shared-article caveats (not a gate)
    vart = article_index(rows["validation"])
    train_titles = set()
    for t in rows["train"]:
        s = t.strip()
        if t.startswith(" = ") and not t.startswith(" = = ") and s.endswith(" =") and not s.startswith("= ="):
            train_titles.add(s)
    val_title_of_article = {}
    for i, t in enumerate(rows["validation"]):
        if vart[i] >= 0 and vart[i] not in val_title_of_article:
            val_title_of_article[vart[i]] = t.strip()
    train_blob = b"\x00".join(t.encode("utf-8") for t in rows["train"])
    val_blob = b"\x00".join(t.encode("utf-8") for t in rows["validation"])
    caveats = {}
    for name, (lo, hi) in NEW.items():
        block = val[lo:hi]
        p_rows = {c["row"] for c in block}
        p_arts = {vart[c["row"]] for c in block}
        def rows_of(a: int, b: int) -> set[int]:
            return {c["row"] for c in val[a:b]}
        def arts_of(a: int, b: int) -> set[int]:
            return {vart[c["row"]] for c in val[a:b]}
        other = (3584, 4096) if name == "panel_A" else (3072, 3584)
        caveats[name] = {
            "distinct_source_rows": len(p_rows),
            "distinct_source_articles": len(p_arts),
            "source_rows_shared_with_earlier_ranks_0_3071": len(p_rows & rows_of(0, 3072)),
            "source_articles_shared_with_earlier_ranks_0_3071": len(p_arts & arts_of(0, 3072)),
            "source_rows_shared_with_other_new_panel": len(p_rows & rows_of(*other)),
            "source_articles_shared_with_other_new_panel": len(p_arts & arts_of(*other)),
            "chunks_whose_65_bytes_occur_anywhere_in_train_text_any_offset": sum(1 for c in block if c["payload"] in train_blob),
            "chunks_whose_65_bytes_occur_more_than_once_in_validation_text": sum(1 for c in block if val_blob.count(c["payload"]) > 1),
            "panel_article_titles_also_train_article_titles": len({val_title_of_article.get(a) for a in p_arts} & train_titles),
        }
    result["descriptive_caveats_not_gates"] = {
        "note": ("Rows are WikiText lines; articles inferred from ' = Title = ' heading rows (heuristic). Shared rows "
                 "or articles mean the same source text contributes different 65-byte chunks to different panels; "
                 "the recipe deduplicates exact chunk contents only (pilot_data limitation text)."),
        **caveats,
    }

    ok = (result["at_least_4096_eligible"] and result["all_six_earlier_reproduced"] and result["zero_exact_overlap"]
          and all(result["ranking_sanity"].values())
          and all(v for v in result["identity_crosschecks"].values() if isinstance(v, bool)))
    result["computational_checks_pass"] = ok
    result["verdict_scope"] = ("ELIGIBLE and DISJOINT are decided here; UNUSED additionally depends on the repository "
                               "search recorded in outputs/repo_search.log and PANEL_PROOF.md")
    OUT.write_text(json.dumps(result, indent=1, sort_keys=True) + "\n")
    print(json.dumps({k: result[k] for k in ("validation_eligible_candidates", "all_six_earlier_reproduced",
                                             "zero_exact_overlap", "computational_checks_pass")}))
    for name, p in panels.items():
        print(name, p["ranks"], p["panel_sha256"], p["overlap"], p["duplicates_within_panel"])
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
