# ruff: noqa
"""Audit 4 (C1), step 10: clusters left on MY strict map under shortcut bounds 0.10 / 0.15 / 0.25, with and without the two variants.
A lineage counts under bound b when its max over levels of the level-wide battery effect (EFF_S cheap; EFF_SM with partial-trace
mutations) is <= b AND it has no closed form above 0.25 in any shape. Closed-form lineages (F > 0.25 in a shape): partition_pass_f3 (all
shapes), loop_sum (all), sieve_marking_f3 (flags shape; also shown with that shape dropped, using the strikesum-only effect), grid_path_table
(count shape 0.37 at L0). Capacity is NOT applied here (see s9). Usage: python3 s10_counts.py s5_v2.json"""
import json, sys
sys.path.insert(0, __import__("os").path.dirname(__file__))
from s9_capacity_table import MAP

d = json.load(open(sys.argv[1]))
CLOSED = {"partition_pass_f3", "loop_sum", "sieve_marking_f3", "grid_path_table"}


def eff(lid, key, drop_shape=None):
    per = d["C1." + lid]
    if drop_shape is None:
        return max(per[str(l)][key] for l in range(7))
    # recompute with one shape removed: best effect is bounded by the max over remaining shapes' in-shape best rule; use rule table
    best = 0.0
    for l in range(7):
        p = per[str(l)]
        n_keep = sum(v for s, v in p["shapes"].items() if s != drop_shape)
        tot = 0.0
        for s, ns in p["shapes"].items():
            if s == drop_shape:
                continue
            cands = [v["rate_in_shape"] for k, v in p["rules"].items() if k.split("|")[0] == s and (k.split("|")[1].startswith(("S.", "MF")) or (key == "EFF_SM" and k.split("|")[1].startswith("M.")))]
            tot += max(cands + [0.0]) * ns
        best = max(best, tot / n_keep)
    return best


for key in ("EFF_S", "EFF_SM"):
    for sieve_fixed in (False, True):
        for b in (0.10, 0.15, 0.25):
            ok = set()
            for cl, mem in MAP.items():
                for m in mem:
                    if m in CLOSED and not (sieve_fixed and m == "sieve_marking_f3"):
                        continue
                    e = eff(m, key, "flags") if (sieve_fixed and m == "sieve_marking_f3") else eff(m, key)
                    if e <= b + 1e-9:
                        ok.add(cl)
                        break
            wo = {c for c in ok if not c.startswith("VARIANT")}
            print(f"{key} sieve_flags_dropped={sieve_fixed} bound {b:.2f}: {len(wo)} clusters without variants, {len(ok)} with; out: {sorted(set(MAP) - ok)}")
