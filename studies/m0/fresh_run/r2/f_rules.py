# ruff: noqa
"""Final R2 audit: re-run of the rule scripts on FRESH seeds for the fix-4 survivors.
Batteries (run as written, imported read-only from the audited worktree): audit 4's a4_heur.H and audit 3's a3_heur.H from their review folders
(the ORIGINAL files, not the package copies; the copies were diffed equal apart from header, import line and three sorted(set()) edits),
and the fix-3 implementer's studies.m0.r2_fix3_heuristics.OWN. Rule names carry the same prefixes as the implementer's fix-4 battery
('[mine]' = audit 4, '[a3]', '[impl]') so the counts can be pooled per rule.
Measurement (my own harness, typed from the description in audit 4 section 4; nothing imported from r2_fix4_battery): per lineage, level and
question shape (the audit-4 shape key), a training draw of N items (seed |5) for 'most frequent answer (train draw)', and a test draw of N items (seed |6);
per rule k = right answers, napp = items where the rule returns an answer, nerr = exceptions (counted as not applying).
Seeds: random.Random(f"finalr2|{lid}|{level}|5") and |6 (throwaway; differ from the implementer's 'a4r2|' and 'fix4|').
Usage (cwd = audited worktree): PYTHONPATH=. PYTHONHASHSEED=0 PYTHONDONTWRITEBYTECODE=1 uv run --locked --offline python <this> N OUT.json [names]"""
import json, random, sys, time
from collections import Counter
from multiprocessing import Pool

SURV = ["binary_search_trace","caesar_shift","cellular_automaton","cheapest_network","count_divisible","crt_smallest","dictionary_rank","digit_root","expression_eval","from_base","grid_sum","interval_scheduling","list_ops","luhn_check","min_heap_ops","run_length","sort_list","string_rewrite_nonidentity","to_base_wide"]
REV = "docs/reviews/m0-lineage-decision-2026-11-25/"
N = int(sys.argv[1]); OUT = sys.argv[2]
NAMES = sys.argv[3].split(",") if len(sys.argv) > 3 else SURV
EXTRA = None  # set by f_rules_new.py to add NEW rules


def shape(lid, s):
    # audit-4 shape key (a4_shortcuts.shape), re-typed
    for k in ("ask", "convention", "kind"):
        if k in s and isinstance(s[k], str):
            v = s[k]
            if lid.endswith("cache_eviction"):
                v = s["policy"] + "/" + v
            return v
    if lid.endswith("min_heap_ops"):
        return f"removals={s['removals']}"
    if lid.endswith("sort_list"):
        return f"desc={s['desc']}"
    return "-"


def batteries(name):
    sys.path.insert(0, REV + "audit4_r2")
    sys.path.insert(0, REV + "audit3_r2")
    import a4_heur, a3_heur
    from studies.m0.r2_fix3_heuristics import OWN
    out = []
    for src, H in (("mine", a4_heur.H), ("a3", a3_heur.H), ("impl", OWN)):
        for hn, fn in H.get(name, []):
            out.append((f"[{src}] {hn}", fn))
    if EXTRA is not None:
        out += [(f"[NEW] {hn}", fn) for hn, fn in EXTRA.get(name, [])]
    return out


def run(nm):
    from studies.m0.core import build_item
    from studies.m0.r2_fix4_set import fix4_set
    lid = "R2." + nm
    lin = fix4_set()[lid]
    hs = batteries(nm)
    res = {}
    t0 = time.time()
    for lv in range(7):
        rtr = random.Random(f"{__import__('os').environ['M0_FR_TAG']}|{lid}|{lv}|5")
        rte = random.Random(f"{__import__('os').environ['M0_FR_TAG']}|{lid}|{lv}|6")
        tr = [build_item(lin, lv, rtr, "A", "t") for _ in range(N)]
        te = [build_item(lin, lv, rte, "A", "e") for _ in range(N)]
        gtr, gte = {}, {}
        for it in tr:
            gtr.setdefault(shape(lid, it.structured), []).append(it)
        for it in te:
            gte.setdefault(shape(lid, it.structured), []).append(it)
        rows = {}
        for sh, grp in sorted(gte.items()):
            at = grp[0].answer_type
            assert all(it.answer_type == at for it in grp)
            ent = {"n": len(grp), "answer_type": at, "rules": {}, "distinct_answers": len({it.answer for it in grp})}
            mode = Counter(it.answer for it in gtr.get(sh, grp)).most_common(1)[0][0]
            ent["rules"]["most frequent answer (train draw)"] = {"k": sum(it.answer == mode for it in grp), "napp": len(grp), "nerr": 0}
            for hn, fn in hs:
                kk = napp = nerr = 0
                for it in grp:
                    try:
                        a = fn(it.structured, it.question)
                    except Exception:
                        nerr += 1
                        a = None
                    if a is None:
                        continue
                    napp += 1
                    kk += a == it.answer
                ent["rules"][hn] = {"k": kk, "napp": napp, "nerr": nerr}
            rows[sh] = ent
        res[str(lv)] = rows
    return lid, res, time.time() - t0


if __name__ == "__main__":
    with Pool(10) as p:
        got = p.map(run, NAMES, chunksize=1)
    out = {lid: r for lid, r, _ in got}
    json.dump({"n": N, "seeds": "finalr2|<lid>|<level>|5 train, |6 test", "lineages": out}, open(OUT, "w"), indent=1, sort_keys=True)
    for lid, _, t in got:
        print(f"{lid} {t:.1f}s")
