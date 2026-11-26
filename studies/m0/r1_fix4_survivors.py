# ruff: noqa: E501
# mypy: disable-error-code="type-arg,no-untyped-call,no-any-return,arg-type,assignment,index,call-overload,var-annotated,list-item,unused-ignore,no-untyped-def"
"""Builds ``manifests/r1_fix4_survivors.json`` (lead rulings R-24 to R-29): for every shape of the fix-round-3 set its name, strict cluster, status (SURVIVES or NOT_REGISTERED), reason, and per level the largest
excess of a counted rule over the base rate with the rule's name; then the surviving clusters and the capacity result.
Two sources of rule measurements: the round-4 run directory (``r1_fix4_measure``) for the shapes that entered the re-run, and, for the shapes dropped at the first stage, the fourth auditor's own data files
(``audit4_r1/heur_run2_all.jsonl``, ``impl_run1_all.jsonl``, ``feature_tells_run1.txt``, ``kept_tells_run1.txt``), read as they are and NOT re-measured; each shape's entry says which.
Run (worktree root): uv run --locked python -m studies.m0.r1_fix4_survivors <run dir> <capacity.json or ''> <out.json> [replicate run dir]
"""

from __future__ import annotations

import json
import os
import re
import sys
from typing import Any

from studies.m0 import lineages_r1_fix3_clusters as v3
from studies.m0 import lineages_r1_fix4_clusters as c4
from studies.m0 import r1_fix4_table as T
from studies.m0.r1_fix4_levels import level_classes

AUDIT = "docs/reviews/m0-lineage-decision-2026-11-25/audit4_r1"
BOUND = 0.15


def _read_dir(run: str, lid: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for kind in ("aud", "impl", "feat"):
        p = os.path.join(run, f"{lid}.{kind}.jsonl")
        if os.path.exists(p):
            rows += T.load_rows(p)
    return rows


def audit_rows() -> list[dict[str, Any]]:
    """The fourth auditor's rows as final_table4.py read them (the one_culprit 'true count' feature row is the auditor's invalid feature and is left out, as there)."""
    rows = T.load_rows(f"{AUDIT}/heur_run2_all.jsonl") + T.load_rows(f"{AUDIT}/impl_run1_all.jsonl")
    for fn in ("feature_tells_run1.txt", "kept_tells_run1.txt"):
        with open(f"{AUDIT}/{fn}") as f:
            for line in f:
                m = re.match(r"(R1\.\S+)\s+(.+?)\s+((?:[+-]\d\.\d{3}\s*){7})$", line.strip())
                if not m or m.group(1) == "R1.one_culprit":
                    continue
                for lv, x in enumerate(m.group(3).split()):
                    rows.append({"lineage": m.group(1), "level": lv, "heuristic": f"feat:{m.group(2)}", "eff": float(x), "anti": None, "acc_fired": None, "fired": 0, "n": 0})
    return rows


def _levels_entry(levels: dict[int, dict[str, tuple[float, str]]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for lv in range(7):
        slot = levels.get(lv, {"C": (0.0, ""), "A": (0.0, ""), "M": (0.0, "")})
        v, name, c = T.level_max(slot)
        out[str(lv)] = {"max_excess": v, "rule": name, "class": c, "M_not_counted": {"excess": slot["M"][0], "rule": slot["M"][1]}}
    return out


def main() -> None:
    run, capfile, out = sys.argv[1], sys.argv[2], sys.argv[3]
    rep = sys.argv[4] if len(sys.argv) > 4 else ""
    cands = {x.id: x for x in c4.candidates_v4()}
    arows = audit_rows()
    a_tab = T.per_level(arows)
    shapes = []
    for old in c4.all_v3_ids():
        new = next((n for n, o in sorted(c4.REPAIRED.items()) if o == old), None)
        lid = new or old
        entry: dict[str, Any] = {"name": lid, "earlier_id": old if new else None, "strict_cluster": v3.cluster_of_v3(lid)}
        if old in c4.AUDIT4_DROPS:
            entry.update(status="NOT_REGISTERED", stage=1, reason=c4.AUDIT4_DROPS[old], measured_by="audit 4 data files (not re-measured)")
            levels = a_tab.get(old, {})
        else:
            rows = _read_dir(run, lid)
            levels = T.per_level(rows).get(lid, {})
            entry["measured_by"] = f"round-4 run {os.path.basename(run.rstrip('/'))}"
            if rep:
                rl = T.per_level(_read_dir(rep, lid)).get(lid, {})
                entry["replicate_max_excess"] = None if not rl else {"value": T.shape_max(rl)[0], "level": T.shape_max(rl)[1], "rule": T.shape_max(rl)[2], "run": os.path.basename(rep.rstrip("/"))}
            entry["levels_distinct"] = len(level_classes(cands[lid]))
            if lid in c4.SECOND_STAGE_DROPS:
                entry.update(status="NOT_REGISTERED", stage=2, reason=c4.SECOND_STAGE_DROPS[lid])
            else:
                entry.update(status="SURVIVES", reason="largest counted excess at or below 0.15 at every level in the re-run" + ("; levels repaired (round 4)" if new else "; unchanged shape"))
        entry["per_level"] = _levels_entry(levels)
        if levels:
            v, lv, name, cl = T.shape_max(levels)
            entry["largest"] = {"excess": v, "level": lv, "rule": name, "class": cl}
        shapes.append(entry)
    surv = [s for s in shapes if s["status"] == "SURVIVES"]
    clusters = sorted({s["strict_cluster"] for s in surv})
    res: dict[str, Any] = {"bound": BOUND, "bound_two_sided": True, "shapes": shapes, "surviving_shapes": [s["name"] for s in surv], "surviving_clusters": clusters, "surviving_cluster_count": len(clusters),
                           "cluster_members": {c: sorted(s["name"] for s in surv if s["strict_cluster"] == c) for c in clusters}}
    mx = max(surv, key=lambda s: s["largest"]["excess"])
    res["largest_excess_among_survivors"] = {"shape": mx["name"], **mx["largest"]}
    res["largest_replicate_excess_among_survivors"] = max(({"shape": s["name"], **s["replicate_max_excess"]} for s in surv if s.get("replicate_max_excess")), key=lambda d: d["value"], default=None)
    if capfile:
        cap = json.load(open(capfile))
        cells = cap["cells"]
        res["capacity"] = {"builder": "core.generate_pool as written, core.part_lineages pointed at the surviving shapes of the part (r1_fix4_capacity)", "G_total": cap["G_total"], "G_part": cap["G_part"], "D_total": cap["D_total"],
                           "D_part_used": cap["D_part"], "pool_seed": cap["pool_seed"], "cells_total": len(cells), "cells_with_shortfall": sum(1 for c in cells if c["shortfalls"]),
                           "cells_with_repeated_text": sum(1 for c in cells if c["text_repeats"]),
                           "per_cluster_and_level": {cl: {str(c["level"]): {"part": c["part"], "per_lineage_quota": c["per_lineage_quota"], "supplied": sum(c["supplied"].get(m, 0) for m in members), "demand_G_part": cap["D_part"], "demand_G_total": cap["D_total"],
                                                         "result": "PASS" if not c["shortfalls"] and sum(c["supplied"].get(m, 0) for m in members) >= cap["D_part"] else "FAIL"}
                                                        for c in cells if c["part"] == ("A" if cl in cap["parts"]["A"]["clusters"] else "B")}
                                                    for cl, members in sorted({k: v for p in ("A", "B") for k, v in cap["parts"][p]["clusters"].items()}.items())},
                           "parts": {p: {"clusters": sorted(cap["parts"][p]["clusters"]), "lineages": cap["parts"][p]["lineages"]} for p in ("A", "B")}}
    with open(out, "w") as f:
        json.dump(res, f, indent=1, sort_keys=True)
    for s in shapes:
        lg = s.get("largest")
        print(f"{s['name']:42s} {s['status']:14s} {s['strict_cluster']:34s} " + (f"{lg['excess']:.3f} L{lg['level']} {lg['rule']}" if lg else ""))


if __name__ == "__main__":
    main()
