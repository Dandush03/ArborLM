"""Descriptive follow-up (not a gate): locate the panel chunks flagged by independent_panel_p8.py's
substring caveats. Uses the tool's own functions (same review folder); no arborlm import.
Run: uv run --locked --extra pilot python -I docs/reviews/p8-preflight-2026-11-14/neardup_detail.py"""
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("ip", Path(__file__).with_name("independent_panel_p8.py"))
ip = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ip)
tr = ip.read_text_column(ip.DATA / "train-00000-of-00001.parquet")
va = ip.read_text_column(ip.DATA / "validation-00000-of-00001.parquet")
train, _, train_all, _ = ip.rank_split(tr, "train", None)
val, _, _, _ = ip.rank_split(va, "validation", train_all)
art = ip.article_index(va)
print("validation articles (heuristic):", max(art) + 1)
for lo, hi, name in ((3072, 3584, "A"), (3584, 4096, "B")):
    for c in val[lo:hi]:
        p = c["payload"]
        t_hits = [(r, t.encode().find(p)) for r, t in enumerate(tr) if p in t.encode()]
        v_hits = [(r, b.find(p)) for r, t in enumerate(va) for b in [t.encode()] if p in b]
        v_all = [(r, i) for r, t in enumerate(va) for b in [t.encode()] for i in range(len(b)) if b.startswith(p, i)]
        if t_hits or len(v_all) > 1:
            locs = []
            for r, i in v_all:
                k = next((x["rank"] for x in val if x["row"] == r and x["byte_offset"] <= i < x["byte_offset"] + 65), None)
                locs.append({"row": r, "byte": i, "aligned": i % 65 == 0, "in_validation_rank": k})
            print(f"panel {name} rank {c['rank']} row {c['row']} off {c['byte_offset']} payload {p!r}")
            print("   train occurrences (row, byte):", t_hits[:5], "aligned:", [i % 65 == 0 for _, i in t_hits[:5]])
            print("   validation occurrences:", locs)
            for r, i in t_hits:
                cov = [x["rank"] for x in train if x["row"] == r and x["byte_offset"] < i + 65 and i < x["byte_offset"] + 65]
                print(f"   train row {r}: overlapping train chunk ranks {cov}; any in pool [0,4096): {any(k < 4096 for k in cov)};"
                      f" any in calibration [2048,2560): {any(2048 <= k < 2560 for k in cov)}")
