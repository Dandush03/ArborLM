# ruff: noqa
"""Audit 3 (R2): structural capacity per lineage and level, counted from draws under three readings of 'distinct item' (R-5):
  A: proper names (towns, objects, people) relabelled; presentation order dropped where the answer does not depend on it; numbers and letters as written.
  B: A, plus symbol relabelling: letters of a string or word list (by first appearance), bracket kinds, the element labels 1..n of a mapping
     (permutation reduced to its cycle type with the start's cycle marked), and the letters of dictionary_rank (replaced by their rank).
  C: B, plus values replaced by their rank where only the order of the values matters for the answer (bst, heap, lis). Information only.
For graphs (cheapest_network) an isomorphism INVARIANT is used, so the count is a lower bound.
Seeds: random.Random(f"a3r2-cap|{lid}|{lv}|7"). Draws: D_CORE per core level, D_RES per reserve level. Also prints f1, f2 and Chao1.
Usage: ... python a3_capacity.py D_CORE D_RES OUT.json"""
import json
import random
import sys
from collections import Counter
from multiprocessing import Pool

D_CORE, D_RES, OUT = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]


def relabel_seq(xs, mp=None):
    mp = {} if mp is None else mp
    out = []
    for x in xs:
        if x not in mp:
            mp[x] = len(mp)
        out.append(mp[x])
    return out, mp


def relabel_str(s, mp):
    return "".join(chr(65 + relabel_seq([c], mp)[0][0]) for c in s)


def ranks(xs):
    srt = sorted(xs)
    return [srt.index(x) for x in xs]


def canon(lid, s, reading):
    n = lid.split(".", 1)[1]
    s = dict(s)
    if n == "cache_eviction":
        seq, mp = relabel_seq(s["seq"])
        item = None if s["item"] is None else relabel_seq([s["item"]], mp)[0][0]
        return json.dumps([s["cap"], s["policy"], s["ask"], seq, item])
    if n == "cheapest_network":
        inc = {}
        for a, b, w in s["cables"]:
            inc.setdefault(a, []).append(w)
            inc.setdefault(b, []).append(w)
        sig = {t: tuple(sorted(v)) for t, v in inc.items()}
        edges = sorted((w, tuple(sorted([sig[a], sig[b]]))) for a, b, w in s["cables"])
        return json.dumps([sorted(sig.values()), edges])
    if n == "merge_smallest_cost":
        return json.dumps(sorted(s["ws"]))
    if n == "interval_scheduling":
        return json.dumps(sorted(s["meetings"]))
    if n == "subtraction_game":
        return json.dumps([sorted(s["piles"]), s["moves"]])
    if n in ("kth_smallest", "sort_list", "count_divisible"):
        s["xs"] = sorted(s["xs"])
        return json.dumps(s, sort_keys=True)
    if n == "lcs_length":
        a, b = sorted([s["a"], s["b"]])
        if reading in "BC":
            mp = {}
            a = relabel_str(a, mp); b = relabel_str(b, mp)
        return json.dumps([a, b])
    if n == "count_letter":
        ws = sorted(s["words"])
        if reading in "BC":
            mp = {}
            letter = relabel_str(s["letter"], mp)
            ws = sorted(relabel_str(w, mp) for w in ws)
            return json.dumps([ws, letter])
        return json.dumps([ws, s["letter"]])
    if reading in "BC":
        if n in ("longest_palindromic_substring", "run_length"):
            return json.dumps(relabel_str(s["s"], {}))
        if n == "palindrome_check":
            return json.dumps(relabel_str(s["phrase"].replace(" ", "_"), {"_": -1}) + "|" + s["phrase"])  # spaces kept as positions
        if n == "string_rewrite_nonidentity":
            mp = {}
            return json.dumps([relabel_str(s["s"], mp), [[relabel_str(p, mp), relabel_str(t, mp)] for p, t in s["rules"]]])
        if n == "bracket_match":
            mp = {}
            kinds = {"(": 0, ")": 0, "[": 1, "]": 1, "{": 2, "}": 2}
            ks, _ = relabel_seq([kinds[c] for c in s["s"]])
            shape = "".join("o" if c in "([{" else "c" for c in s["s"])
            return json.dumps([shape, ks, s["ask"], s["p"]])
        if n == "dictionary_rank":
            L = sorted(s["letters"])
            w = None if s["word"] is None else [L.index(c) for c in s["word"]]
            return json.dumps([len(L), s["ask"], s["k"], w])
        if n == "permutation_power":
            img, st = s["img"], s["s"]
            seen, cycles, mark = set(), [], None
            for i in range(1, len(img) + 1):
                if i in seen:
                    continue
                c, j = [], i
                while j not in seen:
                    seen.add(j); c.append(j); j = img[j - 1]
                cycles.append(len(c))
                if st in c:
                    mark = len(c)
            return json.dumps([sorted(cycles), mark, s["t"]])
    if reading == "C" and n in ("bst_traversal", "min_heap_ops", "lis_length"):
        s["xs"] = ranks(s["xs"])
        return json.dumps(s, sort_keys=True)
    return json.dumps(s, sort_keys=True)


def run(lid):
    from studies.m0.core import ALL_LEVELS, CORE_LEVELS, build_item
    from a3_set import current
    lin = current()[lid]
    res = {}
    for lv in ALL_LEVELS:
        D = D_CORE if lv in CORE_LEVELS else D_RES
        r = random.Random(f"a3r2-cap|{lid}|{lv}|7")
        cnt = {k: Counter() for k in "ABC"}
        for _ in range(D):
            it = build_item(lin, lv, r, "A", "c")
            for k in "ABC":
                cnt[k][canon(lid, it.structured, k)] += 1
        row = {"draws": D}
        for k in "ABC":
            c = cnt[k]
            f1 = sum(1 for v in c.values() if v == 1)
            f2 = sum(1 for v in c.values() if v == 2)
            chao = len(c) + (f1 * f1 / (2 * f2) if f2 else f1 * (f1 - 1) / 2)
            row[k] = {"distinct": len(c), "f1": f1, "f2": f2, "chao1": chao}
        res[str(lv)] = row
    return lid, res


if __name__ == "__main__":
    from a3_set import current
    ids = list(current())
    if len(sys.argv) > 4:
        ids = [i for i in ids if i in sys.argv[4].split(",")]
    with Pool(14) as p:
        out = dict(p.map(run, ids, chunksize=1))
    json.dump({"D_CORE": D_CORE, "D_RES": D_RES, "lineages": out}, open(OUT, "w"), indent=1, sort_keys=True)
    print("wrote", OUT)
