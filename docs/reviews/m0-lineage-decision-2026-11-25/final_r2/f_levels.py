# ruff: noqa
"""Final R2 audit: are the 7 levels distinct, and does a difficulty parameter rise? My own test, from the question TEXT only.
Per lineage and level, N items at fresh seeds random.Random(f"finalr2-lv|{lid}|{level}"). Reported:
  - texts shared between levels (normalised exact text, NFKC + casefold + whitespace collapsed, my own normaliser) and within a level;
  - per level the mean of one or more difficulty parameters parsed from the text;
  - per adjacent pair the AUC P(param at L+1 > param at L) + 0.5 P(equal) (0.5 = no rise; 1 = every L+1 item larger), for the main parameter.
My reading (not a registered threshold): a pair 'rises' if the main parameter's mean is strictly larger AND AUC >= 0.6.
Usage (cwd = audited worktree): PYTHONPATH=. PYTHONHASHSEED=0 PYTHONDONTWRITEBYTECODE=1 uv run --locked --offline python <this> N OUT.json"""
import json, math, random, re, sys, unicodedata
from multiprocessing import Pool

N = int(sys.argv[1]); OUT = sys.argv[2]


def norm(t):
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", t).casefold()).strip()


def nums(s):
    return [int(x) for x in re.findall(r"-?\d+", s)]


def P(nm, q):
    """name -> {param: value}; first key = main parameter."""
    if nm == "binary_search_trace":
        return {"list length": int(re.search(r"A sorted list of (\d+)", q).group(1))}
    if nm == "caesar_shift":
        t = re.search(r"letter of '([^']*)'", q).group(1)
        return {"letters": sum(c.isalpha() for c in t)}
    if nm == "cellular_automaton":
        n = int(re.search(r"A row of (\d+) cells", q).group(1)); st = int(re.search(r"After (\d+) step", q).group(1))
        return {"cells x steps": n * st, "cells": n, "steps": st}
    if nm == "cheapest_network":
        return {"towns": len(re.split(r", | and ", re.search(r"The towns (.*?) must", q).group(1))), "cables": q.count("A cable between")}
    if nm == "count_divisible":
        xs = nums(re.search(r"List: (.*)\.$", q.strip()).group(1))
        return {"list length": len(xs), "max value": max(xs)}
    if nm == "crt_smallest":
        p = [(int(r), int(m)) for r, m in re.findall(r"remainder (\d+) when divided by (\d+)", q)]
        L = 1
        for _, m in p:
            L = L * m // math.gcd(L, m)
        return {"log10 lcm": math.log10(L), "congruences": len(p), "mean modulus": sum(m for _, m in p) / len(p)}
    if nm == "dictionary_rank":
        k = int(re.search(r"word of (\d+) letters", q).group(1))
        n = len(re.findall(r"\b[a-z]\b", re.search(r"from the letters (.*?) when", q).group(1)))
        tot = 1
        for i in range(k):
            tot *= n - i
        return {"log10 list size": math.log10(tot), "word length": k, "alphabet": n}
    if nm == "digit_root":
        return {"digits": len(re.search(r"digits of (\d+)", q).group(1))}
    if nm == "expression_eval":
        e = re.search(r"Work out (.*?)(?:\. Use these| by this rule)", q).group(1)
        return {"operators": len(re.findall(r"[-+*]", e)), "parentheses": e.count("(")}
    if nm == "from_base":
        b, d = re.search(r"base-(\d+) number ([0-9a-z]+)", q).groups()
        v = 0
        for c in d:
            v = v * int(b) + (int(c) if c.isdigit() else ord(c) - 87)
        return {"log10 value": math.log10(max(v, 1)), "digits": len(d)}
    if nm == "to_base_wide":
        n, b = re.search(r"decimal number (\d+) in base (\d+)", q).groups()
        return {"log10 n": math.log10(int(n)), "answer digits": math.floor(math.log(int(n), int(b))) + 1}
    if nm == "grid_sum":
        r, c = re.search(r"(\d+) rows and (\d+) columns", q).groups()
        return {"cells": int(r) * int(c)}
    if nm == "interval_scheduling":
        return {"meetings": len(re.findall(r"meeting \d+ runs", q))}
    if nm == "list_ops":
        ops = re.search(r"in order: (.*?)\. What", q).group(1).split("; ")
        return {"steps": len(ops), "start length": len(nums(re.search(r"the list (.*?)\. Do", q).group(1)))}
    if nm == "luhn_check":
        m = re.search(r"(?:right end of|Is the number) (\d+)", q).group(1)
        return {"digits": len(m)}
    if nm == "min_heap_ops":
        xs = nums(re.search(r"in order: (.*?)\.", q).group(1)); k = re.search(r"smallest (\d+) time", q)
        return {"inserts + removals": len(xs) + (int(k.group(1)) if k else 0), "inserts": len(xs)}
    if nm == "run_length":
        s = re.search(r"Compress ([a-z]+)", q).group(1)
        return {"length": len(s), "runs": len(re.findall(r"(.)\1*", s))}
    if nm == "sort_list":
        xs = nums(q.split("commas:")[1])
        return {"count": len(xs), "max |x|": max(abs(x) for x in xs)}
    if nm == "string_rewrite_nonidentity":
        s = re.search(r"the string ([a-z]+)\.", q).group(1)
        st = re.search(r"step starts: (.*?)\. What", q).group(1).split("; ")
        return {"steps x length": len(st) * len(s), "steps": len(st), "length": len(s)}
    raise KeyError(nm)


SURV = ["binary_search_trace","caesar_shift","cellular_automaton","cheapest_network","count_divisible","crt_smallest","dictionary_rank","digit_root","expression_eval","from_base","grid_sum","interval_scheduling","list_ops","luhn_check","min_heap_ops","run_length","sort_list","string_rewrite_nonidentity","to_base_wide"]


def auc(a, b):
    # P(b > a) + 0.5 P(b == a), via sorting
    sa = sorted(a)
    import bisect
    s = 0.0
    for x in b:
        lo = bisect.bisect_left(sa, x); hi = bisect.bisect_right(sa, x)
        s += lo + 0.5 * (hi - lo)
    return s / (len(a) * len(b))


def run(nm):
    from studies.m0.core import build_item
    from studies.m0.r2_fix4_set import fix4_set
    lid = "R2." + nm
    lin = fix4_set()[lid]
    texts, params = [], []
    for lv in range(7):
        r = random.Random(f"finalr2-lv|{lid}|{lv}")
        its = [build_item(lin, lv, r, "A", "x") for _ in range(N)]
        texts.append([norm(it.question) for it in its])
        params.append([P(nm, it.question) for it in its])
    keys = list(params[0][0])
    main = keys[0]
    res = {"main": main, "levels": {}, "pairs": {}}
    for lv in range(7):
        res["levels"][lv] = {"distinct_texts": len(set(texts[lv])), "n": N, **{f"mean {k}": round(sum(p[k] for p in params[lv]) / N, 3) for k in keys},
                             f"min {main}": round(min(p[main] for p in params[lv]), 3), f"max {main}": round(max(p[main] for p in params[lv]), 3)}
    allshared = 0
    for lv in range(6):
        a = [p[main] for p in params[lv]]; b = [p[main] for p in params[lv + 1]]
        shared = len(set(texts[lv]) & set(texts[lv + 1]))
        ma, mb = sum(a) / N, sum(b) / N
        u = auc(a, b)
        res["pairs"][f"{lv}-{lv+1}"] = {"auc": round(u, 3), "mean_rises": mb > ma, "rises_my_reading": (mb > ma and u >= 0.6), "shared_texts": shared}
    for i in range(7):
        for j in range(i + 1, 7):
            allshared += len(set(texts[i]) & set(texts[j]))
    res["shared_texts_any_two_levels"] = allshared
    res["all_pairs_rise"] = all(v["rises_my_reading"] for v in res["pairs"].values())
    return lid, res


if __name__ == "__main__":
    with Pool(10) as p:
        out = dict(p.map(run, SURV, chunksize=1))
    json.dump(out, open(OUT, "w"), indent=1, sort_keys=True)
    for lid, r in out.items():
        m = r["main"]
        print(f"{lid[3:]:28s} main={m:18s} means " + " ".join(f"{r['levels'][lv]['mean ' + m]:.2f}" for lv in range(7))
              + "  AUC " + " ".join(f"{v['auc']:.2f}" for v in r["pairs"].values()) + f"  shared(any 2 levels)={r['shared_texts_any_two_levels']}"
              + f"  within-level distinct min={min(r['levels'][lv]['distinct_texts'] for lv in range(7))}/{N}  ALL_RISE={r['all_pairs_rise']}")
