# ruff: noqa
"""Final R2 audit: key check of the stored answers against the text-only solver f_solver.py, and wording flags.
Items are drawn through the repository's generator (studies.m0.core.build_item on r2_fix4_set.fix4_set()) at fresh throwaway seeds
random.Random(f"final-r2-key|{lid}|{level}|{TAG}"); only it.question goes to the solver; it.answer is compared afterwards.
Usage (cwd = audited worktree): PYTHONPATH=.:<deliver> PYTHONHASHSEED=0 PYTHONDONTWRITEBYTECODE=1 uv run --locked --offline python <this> N TAG OUT.json"""
import json, random, sys
from collections import Counter
from multiprocessing import Pool

SURV = ["binary_search_trace","caesar_shift","cellular_automaton","cheapest_network","count_divisible","crt_smallest","dictionary_rank","digit_root","expression_eval","from_base","grid_sum","interval_scheduling","list_ops","luhn_check","min_heap_ops","run_length","sort_list","string_rewrite_nonidentity","to_base_wide"]
N = int(sys.argv[1]); TAG = sys.argv[2]; OUT = sys.argv[3]


def run(nm):
    from studies.m0.core import build_item
    from studies.m0.r2_fix4_set import fix4_set
    import f_solver
    lid = "R2." + nm
    lin = fix4_set()[lid]
    res = {}
    for lv in range(7):
        r = random.Random(f"final-r2-key|{lid}|{lv}|{TAG}")
        mism = []; errs = []; flags = Counter(); n = 0; nflag_items = 0; norm_only = 0
        for i in range(N):
            it = build_item(lin, lv, r, "A", "x")
            n += 1
            try:
                a, fl = f_solver.solve(nm, it.question)
            except Exception as e:
                errs.append({"q": it.question, "key": it.answer, "err": repr(e)[:200]})
                continue
            for f in fl:
                flags[f] += 1
            if fl:
                nflag_items += 1
            if a != it.answer:
                if a.replace(" ", "") == it.answer.replace(" ", ""):
                    norm_only += 1
                else:
                    mism.append({"q": it.question, "key": it.answer, "mine": a})
        res[str(lv)] = {"n": n, "mismatch": len(mism), "errors": len(errs), "format_only_mismatch": norm_only, "flags": dict(flags), "items_with_flags": nflag_items,
                        "examples": mism[:3], "error_examples": errs[:3]}
    return lid, res


if __name__ == "__main__":
    with Pool(10) as p:
        out = dict(p.map(run, SURV, chunksize=1))
    json.dump({"N": N, "tag": TAG, "lineages": out}, open(OUT, "w"), indent=1, sort_keys=True)
    tot = sum(v["n"] for x in out.values() for v in x.values())
    mm = sum(v["mismatch"] + v["errors"] for x in out.values() for v in x.values())
    print(f"items {tot}, mismatches+errors {mm}")
    for lid, x in out.items():
        m = sum(v["mismatch"] for v in x.values()); e = sum(v["errors"] for v in x.values()); fo = sum(v["format_only_mismatch"] for v in x.values())
        fl = Counter()
        for v in x.values():
            fl.update(v["flags"])
        print(f"{lid:34s} n={sum(v['n'] for v in x.values())} mismatch={m} errors={e} format_only={fo} flags={dict(fl)}")
