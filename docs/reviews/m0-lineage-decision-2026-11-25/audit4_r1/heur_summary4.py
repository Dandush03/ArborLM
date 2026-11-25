# ruff: noqa
"""Audit 4 (R1): summary of the shortcut battery rows (heuristics4.py or the implementer's battery rerun by impl_battery_rerun4.py).

Per shape and level: gain = the largest of eff and anti over the heuristics (fitted constant excluded here, reported as const);
low = the most negative eff; effect = max(gain, -low, const). Excluded, as in audit 3 (section 7, slip 3) and listed: heuristics that are
exact on every item (fired on all, accuracy >= 0.999), convention slips and one-command misreadings and prefix walks named in EXCL.
usage: python heur_summary4.py <rows.jsonl ...>   (prints a per-shape table and the distribution of max |effect|)
"""
import json, re, sys
from collections import defaultdict

EXCL = {"latest_start_first", "duration_end_off_by_one", "inclusive_day_reading", "ccw_as_cw", "cw270_as_90", "ignore_180s", "left_right_only",
        "ignore_last_condition", "first_cond_only_then_first", "off_by_one_low", "strict_gt_D", "turn_moves_bottom_to_top", "partial_walk_3",
        "rule_at_distance_1", "second_nearest_rule", "third_nearest_rule"}


def bare(h):
    return h.split(":", 1)[1] if h.startswith(("a3:", "a4:")) else h


rows = defaultdict(list)
for f in sys.argv[1:]:
    for line in open(f):
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        rows[(r["lineage"], r["level"])].append(r)

table = defaultdict(dict)
excluded = defaultdict(set)
for (lid, lv), rs in sorted(rows.items()):
    const = next((r for r in rs if r["heuristic"] == "constant_mfk_fitted"), None)
    use = []
    for r in rs:
        if r["heuristic"] == "constant_mfk_fitted":
            continue
        if bare(r["heuristic"]) in EXCL or (r["acc_fired"] is not None and r["acc_fired"] >= 0.999 and r["fired"] == r["n"]):
            excluded[lid].add(r["heuristic"])
            continue
        use.append(r)
    g = max(use, key=lambda r: max(r["eff"], r["anti"] if r["anti"] is not None else -9))
    gv = max(g["eff"], g["anti"] if g["anti"] is not None else -9, 0.0)
    lo = min(use, key=lambda r: r["eff"])
    cv = const["eff"] if const else 0.0
    eff = max(gv, cv)  # audit-4 change (run 2): exploitable gain = max(eff, anti, fitted constant); a raw low (-1/k for a never-right rule) is listed, not counted
    table[lid][lv] = {"gain": gv, "gain_h": g["heuristic"], "low": lo["eff"], "low_h": lo["heuristic"], "const": cv, "mode": rs[0].get("mode_rate"), "effect": eff}

dist = {"<=0.10": [], "<=0.15": [], "<=0.25": [], ">0.25": []}
print(f"{'shape':36s} {'max|eff|':>8s}  where / by                                  per-level gain (L0..L6)              low (min eff)  const")
for lid, lvs in sorted(table.items()):
    m = max(lvs.values(), key=lambda v: v["effect"])
    mlv = [k for k, v in lvs.items() if v is m][0]
    by = m["gain_h"] if m["effect"] == m["gain"] else "constant_mfk_fitted"
    gains = " ".join(f"{lvs[k]['gain']:+.2f}" for k in sorted(lvs))
    lows = " ".join(f"{lvs[k]['low']:+.2f}" for k in sorted(lvs))
    consts = " ".join(f"{lvs[k]['const']:+.2f}" for k in sorted(lvs))
    print(f"{lid:36s} {m['effect']:8.3f}  L{mlv} {by[:40]:40s} {gains}   {lows}   {consts}")
    e = m["effect"]
    dist["<=0.10" if e <= 0.10 else "<=0.15" if e <= 0.15 else "<=0.25" if e <= 0.25 else ">0.25"].append((lid.split(".")[1], round(e, 3)))
print()
for k, v in dist.items():
    print(f"max |effect| {k}: {len(v)}  {v}")
print("\nexcluded as exact / convention / misreading / prefix (per shape):")
for lid in sorted(excluded):
    print(f"  {lid}: {sorted(excluded[lid])}")
