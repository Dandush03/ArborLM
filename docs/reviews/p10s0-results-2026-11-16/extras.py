"""Things in the records the report does not show (descriptive; enters no rule). Reads mine.json and the raw diagnostics.

Usage: python3 -I extras.py <mine.json> <run dir>
"""
import json, sys, statistics, collections
from pathlib import Path

m = json.loads(Path(sys.argv[1]).read_text())
run = Path(sys.argv[2])
cells = m["cells"]
dyn = m["dynamics"]
CU = {"2K/4K": "u8192", "8K/16K": "u32768", "8K/4K": "u32768", "32K/64K": "u131072"}


def key(block, arm, ct, d, j):
    return f"{block}|{arm}|{ct}|{d}|{j}"


print("== failure reasons per arm and cell type (S0 criteria, class readout): count of cells failing each condition")
for ak in sorted(m["arms"]):
    arm, ct = ak.split("|")
    cnt = collections.Counter()
    only = collections.Counter()
    for k, v in cells.items():
        b, a, c, d, j, u = k.split("|")
        if b == "Q1" and a == arm and c == ct and u == CU[ct] and v["failed"]:
            cnt.update(v["failed"])
            only[tuple(v["failed"])] += 1
    print(f"  {ak:14s} {dict(sorted(cnt.items()))}  patterns {dict(only)}")

print("\n== near-threshold SUCCESSFUL cells (S0 criteria): smallest margins per condition, per arm/celltype at the class readout")
for ak in sorted(m["arms"]):
    arm, ct = ak.split("|")
    succ = [(k, v) for k, v in cells.items() if k.startswith(f"Q1|{arm}|{ct}|") and k.endswith(CU[ct]) and v["s0"]]
    if not succ:
        continue
    out = []
    for f in ("c1", "c3_distinct", "c3_largest", "c4", "c6"):
        vals = [(v["margins"].get(f), k) for k, v in succ if v["margins"].get(f) is not None]
        if vals:
            mn = min(vals)
            out.append(f"{f}={mn[0]:.4f}({mn[1].split('|')[3]}/{mn[1].split('|')[4]})")
    print(f"  {ak:14s} n={len(succ):2d} " + " ".join(out))
for blk, arm, ct in (("WX", "WX-A5-D", "2K/4K"), ("WX", "WX-A5-D", "8K/16K"), ("PR", "A5-D", "32K/64K")):
    succ = [(k, v) for k, v in cells.items() if k.startswith(f"{blk}|{arm}|{ct}|") and k.endswith(CU[ct]) and v["s0"]]
    out = []
    for f in ("c1", "c3_distinct", "c3_largest", "c4", "c6"):
        vals = [(v["margins"].get(f), k) for k, v in succ if v["margins"].get(f) is not None]
        if vals:
            mn = min(vals)
            out.append(f"{f}={mn[0]:.4f}({mn[1].split('|')[3]})")
    print(f"  {blk} {arm} {ct}: n={len(succ)} " + " ".join(out))

print("\n== condition-4 margin of every A5-D success at 2K/4K and 8K/16K (H1/H2 over Panel A and B, minus 0.90), sorted, first 6")
for ct in ("2K/4K", "8K/16K"):
    vals = []
    for k, v in cells.items():
        if k.startswith(f"Q1|A5-D|{ct}|") and k.endswith(CU[ct]):
            run_name = k
            vals.append((round(v["margins"]["c4"], 4), k.split("|")[3] + "/" + k.split("|")[4]))
    print(f"  {ct}: {sorted(vals)[:6]}")

print("\n== success at U (8,192) and at 4U (32,768) for 8K cell types (S0 criteria): lost = success at U, failure at 4U")
for ak in sorted(m["arms"]):
    arm, ct = ak.split("|")
    if ct not in ("8K/16K", "8K/4K"):
        continue
    tab = collections.Counter()
    lost = []
    for d in range(1, 11):
        for j in (0, 1):
            ku = key("Q1", arm, ct, d, j) + "|u8192"
            k4 = key("Q1", arm, ct, d, j) + "|u32768"
            if ku not in cells:
                continue
            su, s4 = cells[ku]["s0"], cells[k4]["s0"]
            tab[(su, s4)] += 1
            if su and not s4:
                lost.append(f"d{d}j{j}:{cells[k4]['failed']}")
    print(f"  {ak:14s} (U,4U) counts {{(T,T):{tab[(True, True)]}, (T,F):{tab[(True, False)]}, (F,T):{tab[(False, True)]}, (F,F):{tab[(False, False)]}}} lost: {lost}")

print("\n== collapse onset and escape (slot-based, ADR-0019 8.1) per arm/celltype")
for ak in sorted(m["arms"]):
    arm, ct = ak.split("|")
    ks = [k for k in dyn if k.startswith(f"Q1|{arm}|{ct}|")]
    on = [dyn[k]["onset"] for k in ks if dyn[k]["onset"] is not None]
    es = [dyn[k]["escape"] for k in ks if dyn[k]["escape"] is not None]
    print(f"  {ak:14s} onsets {len(on)}/{len(ks)} median onset {statistics.median(on) if on else None} max onset {max(on) if on else None}; escapes {len(es)} median escape {statistics.median(es) if es else None} max {max(es) if es else None}")

print("\n== probe-accuracy trajectory: cells whose probe accuracy reached >= 0.90 and later fell below 0.85 (descriptive)")
for cdir in sorted((run / "cells").iterdir()):
    if "A6" in cdir.name or "A7" in cdir.name:
        continue
    pa = []
    with (cdir / "diagnostics.jsonl").open() as fh:
        for line in fh:
            r = json.loads(line)
            pa.append((r["update"], r["probe_accuracy"]))
    first = next((i for i, (u, a) in enumerate(pa) if a >= 0.90), None)
    if first is not None:
        low = min(pa[first:], key=lambda x: x[1])
        if low[1] < 0.85:
            print(f"  {cdir.name}: first >=0.90 at {pa[first][0]}, min after {low[1]:.3f} at {low[0]}, final {pa[-1][1]:.3f}")

print("\n== A5-D minimum distinct top-1 on the probe over training (how far from the collapse threshold of 32)")
for ct in ("2K/4K", "8K/16K", "8K/4K"):
    mins = []
    for cdir in sorted((run / "cells").glob(f"Q1-A5-D-{ct.replace('/', '')}-*")):
        with (cdir / "diagnostics.jsonl").open() as fh:
            mins.append(min(json.loads(l)["distinct_top1"] for l in fh))
    print(f"  {ct}: min over cells {min(mins)}, median of per-cell minima {statistics.median(mins)}")
for ct in ("2K/4K", "8K/16K"):
    mins = []
    for cdir in sorted((run / "cells").glob(f"Q1-A0-{ct.replace('/', '')}-*")):
        with (cdir / "diagnostics.jsonl").open() as fh:
            mins.append(min(json.loads(l)["distinct_top1"] for l in fh))
    print(f"  A0 {ct}: per-cell minimum distinct top-1: {sorted(mins)}")

print("\n== LM relative rise r and margin to the flag (r_A6 + 0.05 - r), minimum per arm/celltype")
for ak in sorted(m["arms"]):
    arm, ct = ak.split("|")
    vals = [(v["lm_r_a6"] + 0.05 - v["lm_r"], k) for k, v in cells.items() if k.startswith(f"Q1|{arm}|{ct}|") and k.endswith(CU[ct])]
    mn = min(vals)
    print(f"  {ak:14s} min margin {mn[0]:.4f} ({mn[1].split('|')[3]}/{mn[1].split('|')[4]}); median r {statistics.median(v['lm_r'] for k, v in cells.items() if k.startswith(f'Q1|{arm}|{ct}|') and k.endswith(CU[ct])):.4f}")

print("\n== A5-D 8K/4K and A0 8K/4K per cell: accuracy A/B vs 0.9*A6, H-ratio, failed conditions")
for arm in ("A0", "A5-D"):
    for d in range(1, 11):
        j = 0 if d % 2 else 1
        v = cells[f"Q1|{arm}|8K/4K|{d}|{j}|u32768"]
        print(f"  {arm:5s} d{d:02d} accA {v['acc_A']:.3f} accB {v['acc_B']:.3f} c1 margin {v['margins']['c1']:+.3f} c4 margin {v['margins']['c4']:+.3f} c6 margin {v['margins'].get('c6', 0):+.3f} failed {v['failed']}")
print("\n== WX per cell (class readout): acc, stability, failed")
for ct in ("2K/4K", "8K/16K"):
    for d in range(1, 11):
        j = 0 if d % 2 else 1
        v = cells[f"WX|WX-A5-D|{ct}|{d}|{j}|{CU[ct]}"]
        print(f"  {ct:7s} d{d:02d} accA {v['acc_A']:.3f} stab {v['stability']:.3f} auc {v.get('auc', float('nan')):.3f} failed {v['failed']}")
print("\n== probe cells")
for d in (11, 12, 13):
    v = cells[f"PR|A5-D|32K/64K|{d}|0|u131072"]
    print(f"  d{d} accA {v['acc_A']:.4f} accB {v['acc_B']:.4f} stab {v['stability']:.3f} margins {{{', '.join(f'{k}: {x:.4f}' for k, x in v['margins'].items())}}} lm r {v['lm_r']:.4f} vs A6 {v['lm_r_a6']:.4f}")
