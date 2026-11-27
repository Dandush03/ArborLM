# ruff: noqa: E501
"""M1 fix round 4: capacity of the surviving lineages (R-22, R-28), against ``core.generate_pool`` AS WRITTEN and, separately, a HYPOTHETICAL per-cluster builder.

Measurement: the audit-4 script ``capacity_a4.py`` is read from the audit directory with ``importlib`` (unmodified; its loader is replaced by the fix-4 set in memory): the canonical structural key of the
auditor (a different structural item is a different numeric configuration; names, setting sentences and the order of commutative parts do not count), M draws per lineage and level, n_eff = M (M - 1) / (2 P) from the
colliding pairs P (a level with no collision is given M (M - 1) / 6 as in the audit and in round 3), Chao1 as a second estimate. All sampled lower bounds, MEASURED.

Demand (R-10, R-11): per cluster and level 10 x (ceil(4000 / G) + ceil(20000 / G) + 100), reserve levels the same (ANALYTICAL).

As written: ``generate_pool`` takes ``part_lineages`` (the lineages whose FAMILY is in the part, by ``family_partition``) and allocates the pool EQUALLY PER LINEAGE; ``m0_draw`` balances per lineage id; ``draw_items``
de-duplicates on the normalised text, names included. So the unit that must meet the demand is a LINEAGE, and the G of the formula is the number of lineages in its part. ``as_written`` below applies
``family_partition``'s own rule (the SHA-256 shuffle of the sorted family names with partition seed 400004, part A the smaller half) to the families of the surviving lineages, because the surviving set is not in
``core.REGISTRY``; the structural key (not the text) is the counted unit, which is stricter than the builder's text de-duplication.
Hypothetical per-cluster builder (NOT written): equal split by strict cluster, then equally inside the cluster, de-duplicated structurally; G = the smaller part's cluster count, floor(clusters / 2).
Three bases per cluster and level: equal-weight mixture n_eff (L^2 / sum 1 / n_i), Chao1 sum, and equal share (every member alone must supply demand / L).
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
import types
from pathlib import Path
from typing import Any

from studies.m0.core import ALL_LEVELS, stream
from studies.m0.lineages_m1_fix4 import load_all, load_registered, stem
from studies.m0.lineages_m1_fix4_clusters import strict_clusters

ROOT = Path(__file__).resolve().parents[2]
A4 = ROOT / "docs" / "reviews" / "m0-lineage-decision-2026-11-25" / "audit4_m1"
M_DEFAULT = 30000


def demand(g: int) -> int:
    return 10 * (math.ceil(4000 / g) + math.ceil(20000 / g) + 100)


def a4_capacity_module() -> types.ModuleType:
    from studies.m0.m1_fix4_battery import _current_set, _load

    common = _load(A4 / "common_a4.py", "common_a4")
    common.current_set = _current_set  # type: ignore[attr-defined]
    common.stem = stem  # type: ignore[attr-defined]
    return _load(A4 / "capacity_a4.py", "capacity_a4_fix4")


def cap_task(args: tuple[str, int, int]) -> tuple[str, int, dict[str, Any]]:
    return a4_capacity_module().one(args)  # type: ignore[no-any-return]


def text_task(args: tuple[str, int, int]) -> tuple[str, int, dict[str, Any]]:
    """n_eff on the normalised TEXT (names and setting included), the unit ``draw_items`` de-duplicates on; informational (R-16 is not ruled)."""
    from collections import Counter

    from studies.m0.core import build_item, text_hash

    lid, lv, m = args
    lin = {x.id: x for x in load_all()}[lid]
    rng = stream(23, "fix4-text-capacity", lid, str(lv))
    cnt = Counter(text_hash(build_item(lin, lv, rng, "A", f"t/{i}").question) for i in range(m))
    pairs = sum(c * (c - 1) // 2 for c in cnt.values())
    return lid, lv, {"M": m, "D": len(cnt), "pairs": pairs, "n_eff": (m * (m - 1) / (2 * pairs)) if pairs else None}


def family_parts(families: list[str], seed: int = 400004, eval_id: str = "M1") -> dict[str, str]:
    """``core.family_partition``'s rule on an arbitrary family list (the surviving set is not in ``core.REGISTRY``)."""
    fams = sorted(set(families))
    r = stream(seed, "family-partition", eval_id)
    shuffled = fams[:]
    r.shuffle(shuffled)
    half = len(shuffled) // 2
    return {f: ("A" if i < half else "B") for i, f in enumerate(shuffled)}


def n_eff(r: dict[str, Any], m: int) -> float:
    return float(r["n_eff"]) if r["n_eff"] is not None else m * (m - 1) / 6


def report(cap: dict[str, Any], ids: list[str], cluster_ids: dict[str, list[str]] | None = None, text: dict[str, Any] | None = None) -> dict[str, Any]:
    """Capacity of the surviving lineages ``ids`` from a capacity JSON (``capacity_a4`` format) under both builders."""
    m = int(cap["M"])
    lv = cap["levels"]
    clusters = cluster_ids if cluster_ids is not None else strict_clusters(ids)
    n_cl = len(clusters)
    g_part = n_cl // 2
    fam_of = {x.id: x.family for x in load_all()}
    parts = family_parts([fam_of[i] for i in ids])
    n_in_part = {p: sum(1 for i in ids if parts[fam_of[i]] == p) for p in ("A", "B")}
    out: dict[str, Any] = {
        "M": m, "seed": cap.get("seed"), "clusters": n_cl, "G_per_part_smaller": g_part, "demand_G_per_part": demand(g_part), "demand_literal_G_equals_all_clusters": demand(n_cl),
        "demand_formula": "10 x (ceil(4000 / G) + ceil(20000 / G) + 100)", "basis": "MEASURED sampled n_eff (lower bound) per lineage-level; demand ANALYTICAL",
    }
    # ---- as written: per lineage, G = lineages in its part
    def lv_ok(i: str, x: int) -> bool:
        return n_eff(lv[i][str(x)], m) >= demand(n_in_part[parts[fam_of[i]]])

    aw: dict[str, Any] = {"partition_rule": "core.family_partition rule applied to the surviving families", "lineages_in_part": n_in_part,
                          "demand_per_lineage_part": {p: demand(n) for p, n in n_in_part.items()}, "lineages": {}, "fails": {}}
    for i in sorted(ids):
        p = parts[fam_of[i]]
        d = demand(n_in_part[p])
        row = [round(n_eff(lv[i][str(x)], m)) for x in ALL_LEVELS]
        aw["lineages"][i] = {"part": p, "demand": d, "n_eff_per_level": row, "min_margin": round(min(row) / d, 3)}
        bad = [x for x, v in zip(ALL_LEVELS, row, strict=True) if v < d]
        if bad:
            aw["fails"][i] = bad
    aw["by_cluster"] = {cl: {str(x): ("PASS" if all(lv_ok(i, x) for i in mem) else "FAIL: " + ", ".join(i for i in mem if not lv_ok(i, x))) for x in ALL_LEVELS} for cl, mem in clusters.items()}
    if text is not None:
        mt = int(text["M"])
        aw["informational_text_dedup_n_eff"] = {"note": "n_eff on the normalised text, names and setting included (what draw_items de-duplicates on); a LOWER bound from M draws, a level without a collision is given M(M-1)/6",
                                                "M": mt, "min_over_levels": {i: round(min(n_eff(text["levels"][i][str(x)], mt) for x in ALL_LEVELS)) for i in sorted(ids)},
                                                "fails_at_levels_against_the_lineage_demand": {i: [x for x in ALL_LEVELS if n_eff(text["levels"][i][str(x)], mt) < demand(n_in_part[parts[fam_of[i]]])] for i in sorted(ids)
                                                                                               if any(n_eff(text["levels"][i][str(x)], mt) < demand(n_in_part[parts[fam_of[i]]]) for x in ALL_LEVELS)}}
    out["as_written"] = aw
    # ---- hypothetical per-cluster builder
    d = demand(g_part)
    hyp: dict[str, Any] = {"LABEL": "HYPOTHETICAL: no per-cluster pool builder exists; nothing below is a pass under core.generate_pool", "G": g_part, "demand": d, "clusters": {}, "fails": {}}
    for cl, mem in clusters.items():
        k = len(mem)
        rows: dict[str, list[int]] = {"mixture": [], "chao1": [], "equal_share": []}
        for x in ALL_LEVELS:
            rs = [lv[i][str(x)] for i in mem]
            rows["mixture"].append(round(k * k / sum(1 / n_eff(r, m) for r in rs)))
            rows["chao1"].append(sum(int(r["chao1"]) for r in rs))
            rows["equal_share"].append(round(min(n_eff(r, m) for r in rs) * k))
        fails = {b: [x for x, v in zip(ALL_LEVELS, vals, strict=True) if v < d] for b, vals in rows.items()}
        hyp["clusters"][cl] = {"members": mem, "n_eff": rows, "fails": fails}
        if any(fails.values()):
            hyp["fails"][cl] = {b: v for b, v in fails.items() if v}
    out["hypothetical_per_cluster"] = hyp
    return out


def main() -> None:
    import multiprocessing as mp

    ap = argparse.ArgumentParser(description="M1 fix-4 capacity sampling (audit-4 canonical keys)")
    ap.add_argument("--m", type=int, default=M_DEFAULT)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--out", required=True)
    ap.add_argument("--only", default="")
    ap.add_argument("--text", action="store_true", help="measure the n_eff on the normalised text instead (informational)")
    ap.add_argument("--all", action="store_true", help="also the lineages marked NOT REGISTERED (digit_puzzle is always skipped: it needs its own M)")
    a = ap.parse_args()
    ids = sorted(x.id for x in (load_all() if a.all else load_registered()) if "digit_puzzle" not in x.id)
    if a.only:
        ids = [i for i in ids if any(o in i for o in a.only.split(","))]
    t0 = time.time()
    tasks = [(i, lv, a.m) for i in ids for lv in ALL_LEVELS]
    res: dict[str, dict[str, Any]] = {}
    with mp.get_context("spawn").Pool(a.workers) as pool:
        for lid, lv, r in pool.imap_unordered(text_task if a.text else cap_task, tasks, chunksize=1):
            res.setdefault(lid, {})[str(lv)] = r
    Path(a.out).write_text(json.dumps({"M": a.m, "seed": 23, "text": a.text, "levels": res}, indent=1, sort_keys=True))
    print("seconds", round(time.time() - t0, 1), file=sys.stderr)


if __name__ == "__main__":
    main()
