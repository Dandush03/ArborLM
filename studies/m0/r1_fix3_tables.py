# ruff: noqa: E501
# mypy: disable-error-code="type-arg,no-untyped-call,no-any-return,arg-type,assignment,index,call-overload,var-annotated,list-item,unused-ignore,no-untyped-def"
"""Tables of the R1 fix round 3 from the raw runs: ``manifests/r1_fix3_shortcuts.{json,md}``, ``manifests/r1_fix3_capacity.{json,md}`` (with ``r1_fix3_capacity_raw.jsonl``) and ``manifests/r1_fix3_retries.json``.
Measured values only; nothing is thresholded here. Run (worktree root): PYTHONHASHSEED=0 uv run --locked python -m studies.m0.r1_fix3_tables <measure.json> <capacity.jsonl> <seed measure> <seed capacity>"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path
from typing import Any

from studies.m0.core import Retry
from studies.m0.lineages_r1_fix3_clusters import (
    NOT_REGISTERED_V3,
    cluster_of_v3,
    cluster_table_v3,
    registered_v3,
)
from studies.m0.lineages_r1_fix3_common import REPLACES, load_fix3
from studies.m0.r1_fix3_capacity import DEMAND

MAN = Path(__file__).resolve().parents[2] / "studies/m0/manifests"


def worst(summary: dict[str, Any]) -> tuple[float, int, str]:
    lv = max(summary, key=lambda k: summary[k]["gain"])
    return summary[lv]["gain"], int(lv), summary[lv]["gain_heuristic"]


def shortcuts(measure_path: str, seed: int) -> None:
    res = json.load(open(measure_path))
    by = {(r["which"], r["id"]): r for r in res}
    out: dict[str, Any] = {"note": f"Measured with studies/m0/r1_fix3_battery.py: 500 items per level, seed {seed} (a throwaway integer, not a registered seed). gain = the largest of (accuracy - chance) and (anti accuracy - chance) over the battery at that level; low = the most negative (accuracy - chance). Rules that are an exact algorithm are listed and not counted. Not a threshold; the working target of the fix round was +-0.10.", "shapes": {}}
    rows = ["| shape | before (earlier shape): max gain, level, rule | after: max gain, level, rule | after: gain by level 0..6 | commonest answer, max over levels | status |", "|---|---|---|---|---|---|"]
    reg = {x.id for x in registered_v3()}
    for (which, lid), r in sorted(by.items(), key=lambda kv: (kv[0][1])):
        if which == "earlier_shape":
            continue
        new_summary = r["summary"]
        old_id = REPLACES.get(lid)
        old_r = by.get(("earlier_shape", old_id)) if old_id else None
        g, lv, h = worst(new_summary)
        before = None
        if old_r:
            og, olv, oh = worst(old_r["summary"])
            before = {"gain": og, "level": olv, "rule": oh, "by_level": {k: v["gain"] for k, v in old_r["summary"].items()}}
        status = "registered candidate" if lid in reg else "NOT REGISTERED (reason in r1_fix3_clusters.json)"
        out["shapes"][lid] = {"after": {"gain": g, "level": lv, "rule": h, "by_level": {k: v["gain"] for k, v in new_summary.items()}, "low_by_level": {k: v["low"] for k, v in new_summary.items()},
                                        "mode_rate_max": max((v["mode_rate"] or 0) for v in new_summary.values()), "excluded_exact": sorted({e for v in new_summary.values() for e in v["excluded_exact"]})},
                              "before": before, "status": status, "replaces": old_id}
        bl = f"{before['gain']:.3f} L{before['level']} {before['rule']}" if before else "(kept unchanged)"
        rows.append(f"| {lid} | {bl} | {g:.3f} L{lv} {h} | {' '.join(f'{new_summary[str(k)]['gain']:.2f}' for k in range(7) if str(k) in new_summary)} | {out['shapes'][lid]['after']['mode_rate_max']:.2f} | {status} |")
    old_only = sorted(i for (w, i) in by if w == "earlier_shape" and i not in {REPLACES.get(x) for x in REPLACES} and i in NOT_REGISTERED_V3)
    for lid in old_only:
        g, lv, h = worst(by[("earlier_shape", lid)]["summary"])
        out["shapes"][lid] = {"after": None, "before": {"gain": g, "level": lv, "rule": h}, "status": "NOT REGISTERED (reason in r1_fix3_clusters.json)", "replaces": None}
        rows.append(f"| {lid} | {g:.3f} L{lv} {h} | (not rebuilt) | - | - | NOT REGISTERED |")
    (MAN / "r1_fix3_shortcuts.json").write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    (MAN / "r1_fix3_shortcuts.md").write_text("\n".join(rows) + "\n")


def capacity(cap_path: str, seed: int) -> None:
    rows = [json.loads(line) for line in open(cap_path)]
    rows.sort(key=lambda r: (r["id"], r["level"]))
    (MAN / "r1_fix3_capacity_raw.jsonl").write_text("\n".join(json.dumps(r, sort_keys=True) for r in rows) + "\n")
    est = {}
    for r in rows:
        for k in ("a", "b"):
            e = r[k]
            s = e["S_collision"] if e["S_collision"] is not None else e["lower_bound_if_no_collision"]
            est[(r["id"], r["level"], k)] = max(e["distinct"], s or 0)
    ct = cluster_table_v3()
    out: dict[str, Any] = {"demand": DEMAND, "G": 11, "note": f"N = {rows[0]['N']} draws per cell, seed {seed} (throwaway). Estimates: max(distinct keys seen, collision estimate or, with no collision, the 95 % lower bound N(N-1)/6). Reading (a): names, settings, order relabelled; reading (b): labels and letters also relabelled. A shape is below its even share when its estimate is under demand / (shapes in its cluster).", "cells": {}, "clusters": {}}
    md = ["| cluster | shapes | reading (a): levels where the CLUSTER SUM is below the demand | reading (b) | shapes below the even share (a) |", "|---|---|---|---|---|"]
    for cid, members in sorted(ct.items()):
        ids = [m.id for m in members]
        sums_a = [sum(est[(i, lv, "a")] for i in ids) for lv in range(7)]
        sums_b = [sum(est[(i, lv, "b")] for i in ids) for lv in range(7)]
        share = DEMAND / len(ids)
        below = {i.split(".")[1]: [lv for lv in range(7) if est[(i, lv, "a")] < share] for i in ids}
        below = {k: v for k, v in below.items() if v}
        fail_a = [lv for lv in range(7) if sums_a[lv] < DEMAND]
        fail_b = [lv for lv in range(7) if sums_b[lv] < DEMAND]
        out["clusters"][cid] = {"shapes": ids, "sum_a": sums_a, "sum_b": sums_b, "fail_levels_a": fail_a, "fail_levels_b": fail_b, "shapes_below_even_share_a": below, "even_share": round(share)}
        md.append(f"| {cid} | {', '.join(i.split('.')[1] for i in ids)} | {fail_a or 'none'} | {fail_b or 'none'} | {below or 'none'} |")
    for r in rows:
        out["cells"][f"{r['id']}|{r['level']}"] = {"a": r["a"], "b": r["b"], "pass_a": r["pass_a"], "pass_b": r["pass_b"]}
    md += ["", "Per shape and level (reading a): estimate (distinct keys seen in brackets)", "", "| shape | L0 | L1 | L2 | L3 | L4 | L5 | L6 |", "|---|---|---|---|---|---|---|---|"]
    for lid in sorted({r["id"] for r in rows}):
        md.append(f"| {lid} | " + " | ".join(f"{est[(lid, lv, 'a')]:,} ({next(r for r in rows if r['id'] == lid and r['level'] == lv)['a']['distinct']})" for lv in range(7)) + " |")
    (MAN / "r1_fix3_capacity.json").write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    (MAN / "r1_fix3_capacity.md").write_text("\n".join(md) + "\n")


def retries(seed: int, n: int = 150) -> None:
    out: dict[str, Any] = {"note": f"Share of builder calls that raised Retry (validity: a unique answer, a non-empty candidate set, the drawn class met), {n} successes per cell, seed {seed} (throwaway)."}
    for lin in [*registered_v3(), *[x for x in load_fix3() if x.id in NOT_REGISTERED_V3]]:
        cell = {}
        for lv in range(7):
            r = random.Random(seed * 1000 + lv)
            ok = bad = 0
            while ok < n and bad < 40 * n:
                try:
                    lin.build(lv, r)
                    ok += 1
                except Retry:
                    bad += 1
            cell[str(lv)] = round(bad / (ok + bad), 3)
        out[lin.id] = cell
    (MAN / "r1_fix3_retries.json").write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")


def main() -> None:
    shortcuts(sys.argv[1], int(sys.argv[3]))
    capacity(sys.argv[2], int(sys.argv[4]))
    retries(int(sys.argv[3]))
    print("clusters", len(cluster_table_v3()), [cluster_of_v3(x.id) for x in registered_v3()][:1])


if __name__ == "__main__":
    main()
