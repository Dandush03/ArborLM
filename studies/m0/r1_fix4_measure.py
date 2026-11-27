# ruff: noqa: E501
# mypy: disable-error-code="type-arg,no-untyped-call,no-any-return,arg-type,assignment,index,call-overload,var-annotated,list-item,unused-ignore,no-untyped-def"
"""Round-4 shortcut measurement of the candidate shapes with the union of the three batteries (lead rulings R-24, R-26): the fourth auditor's battery (``r1_fix4_a4_heur``, which includes audit 3's),
the implementer's battery of round 3 (``r1_fix3_battery.measure``) and the fitted count-feature lookups (``r1_fix4_tells``). Throwaway seeds from the command line (never registered study seeds).
One process per shape; each writes one JSON-lines file of rows into the output directory: ``<id>.aud.jsonl``, ``<id>.impl.jsonl``, ``<id>.feat.jsonl``.
Run (worktree root): PYTHONHASHSEED=0 uv run --locked python -m studies.m0.r1_fix4_measure <n_per_level> <aud_seed> <aud_fit> <impl_seed> <impl_fit> <out_dir> [shape id ...]
"""

from __future__ import annotations

import json
import os
import sys
from multiprocessing import Pool


def _one(args):
    lid, n, aud_seed, aud_fit, impl_seed, impl_fit, out = args
    import statistics
    from collections import Counter, defaultdict  # noqa: F401

    from studies.m0 import r1_fix3_battery as B
    from studies.m0 import r1_fix4_a3_heur as H3
    from studies.m0 import r1_fix4_a4_heur as H4
    from studies.m0 import r1_fix4_gen as gen
    from studies.m0.r1_fix4_tells import feature_rows

    lin = gen.lineages()[lid]
    # --- the auditor's battery: the body of r1_fix4_a4_heur.main for one lineage (same code path, rows written to a per-shape file)
    rows = []
    bs = H4.base_of(lid)
    for lv in range(7):
        fit_items = gen.items(lin, lv, 400, aud_fit)
        mfk = Counter(b.answer for b in fit_items).most_common(1)[0][0]
        ratio = None
        if bs in H4.SIZE and fit_items[0].k is None:
            ratio = statistics.median([int(b.answer) / max(1, H4.SIZE[bs](b.structured)) for b in fit_items])
        if bs == "knights_knaves":
            tab = defaultdict(Counter)
            for b in fit_items:
                tab[b.structured["statements"][b.structured["who"]][0]][b.answer] += 1
            for k, c in sorted(tab.items()):
                H4.KK_TABLE[(lv, k)] = c.most_common(1)[0][0]
        its = gen.items(lin, lv, n, aud_seed)
        acc = defaultdict(lambda: {"eff": [], "anti": [], "hit": []})
        allp = []
        for b in its:
            b.structured["_level"] = lv
            p = {"constant_mfk_fitted": mfk, **H4.preds(lid, b)}
            if ratio is not None:
                p["fitted_ratio_times_size"] = str(round(ratio * H4.SIZE[bs](b.structured)))
            allp.append(p)
            del b.structured["_level"]
        names = sorted({h for p in allp for h in p})
        for b, p0 in zip(its, allp, strict=True):
            ch = H3.chance(b)
            for h in names:
                p = p0.get(h)
                c = H3.credit(p, b)
                a = H3.anti(p, b)
                r = acc[h]
                r["eff"].append(ch if c is None else c)
                r["anti"].append(ch if a is None else a)
                if c is not None:
                    r["hit"].append(c)
        chm = statistics.mean(H3.chance(b) for b in its)
        for h, r in sorted(acc.items()):
            rows.append({"lineage": lid, "level": lv, "heuristic": h, "n": len(its), "chance": round(chm, 4), "fired": len(r["hit"]),
                         "acc_fired": round(statistics.mean(r["hit"]), 4) if r["hit"] else None, "eff": round(statistics.mean(r["eff"]) - chm, 4),
                         "anti": round(statistics.mean(r["anti"]) - chm, 4) if its[0].k else None})
    with open(os.path.join(out, f"{lid}.aud.jsonl"), "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    # --- the implementer's battery, unchanged
    rows2 = B.measure(lin, n, impl_seed, impl_fit)
    with open(os.path.join(out, f"{lid}.impl.jsonl"), "w") as f:
        for r in rows2:
            f.write(json.dumps({k: r[k] for k in ("lineage", "level", "heuristic", "fired", "acc_fired", "eff", "anti", "chance", "n")}) + "\n")
    # --- fitted lookups
    rows3 = feature_rows(lin)
    with open(os.path.join(out, f"{lid}.feat.jsonl"), "w") as f:
        for r in rows3:
            f.write(json.dumps(r) + "\n")
    return lid


def main() -> None:
    n, aud_seed, aud_fit, impl_seed, impl_fit = (int(x) for x in sys.argv[1:6])
    out = sys.argv[6]
    from studies.m0.r1_fix4_gen import lineages

    ids = sys.argv[7:] or sorted(lineages())
    os.makedirs(out, exist_ok=True)
    with Pool(min(len(ids), 10)) as p:
        for lid in p.imap_unordered(_one, [(i, n, aud_seed, aud_fit, impl_seed, impl_fit, out) for i in ids]):
            print(lid, "done", flush=True)


if __name__ == "__main__":
    main()
