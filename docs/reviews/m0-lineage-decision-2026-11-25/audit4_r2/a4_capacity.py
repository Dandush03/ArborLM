# ruff: noqa
"""Audit 4 (R2): capacity on structure. For each lineage and level draw N items (seed random.Random(f"a4r2-cap|{lid}|{lv}|7"), throwaway), map each to a canonical
form under three readings and count distinct forms D, singletons f1, doubletons f2 and Chao1 = D + f1^2/(2 f2) (f2 = 0: D + f1(f1-1)/2).
  a: proper names, setting sentence and presentation order relabelled (order-free where the answer ignores order; names by first appearance; graphs by a weighted WL hash = a LOWER bound on classes)
  b: a + letters/labels relabelled (letters by first appearance; bracket kinds; numbers of a mapping (cycle type + start's cycle + t); dictionary letters by index)
  c: b + only the order of values counts where the solution path depends only on order (sort, kth, bst, heap, lis, binary search, interval endpoints, hash homes)
Usage (cwd = audited worktree): PYTHONHASHSEED=0 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:<deliver> uv run --locked --offline python a4_capacity.py N OUT.json"""
import hashlib
import json
import random
import sys
from collections import Counter
from multiprocessing import Pool

N = int(sys.argv[1])
OUT = sys.argv[2]


def relabel_str(s, keep=" "):
    mp = {}
    out = []
    for ch in s:
        if ch in keep:
            out.append(ch)
            continue
        if ch not in mp:
            mp[ch] = chr(65 + len(mp))
        out.append(mp[ch])
    return "".join(out)


def ranks(xs):
    srt = sorted(set(xs))
    r = {v: i for i, v in enumerate(srt)}
    return tuple(r[x] for x in xs)


def wl_hash(names, cables):
    idx = {t: i for i, t in enumerate(names)}
    adj = {i: [] for i in range(len(names))}
    for a, b, w in cables:
        adj[idx[a]].append((w, idx[b]))
        adj[idx[b]].append((w, idx[a]))
    col = {i: "" for i in adj}
    for _ in range(4):
        col = {i: hashlib.sha1((col[i] + "|" + ",".join(sorted(f"{w}:{col[j]}" for w, j in adj[i]))).encode()).hexdigest()[:16] for i in adj}
    return tuple(sorted(col.values()))


def cycle_canon(img, s, t):
    n = len(img)
    seen = set()
    lens = []
    scyc = None
    for st in range(1, n + 1):
        if st in seen:
            continue
        c = [st]
        seen.add(st)
        while img[c[-1] - 1] != st:
            c.append(img[c[-1] - 1])
            seen.add(c[-1])
        lens.append(len(c))
        if s in c:
            scyc = len(c)
    return (tuple(sorted(lens)), scyc, t)


def canon(name, s, reading):
    b = reading in "bc"
    c = reading == "c"
    if name == "binary_search_trace":
        if c:
            xs, t = s["xs"], s["target"]
            pos = sum(x < t for x in xs)
            return (len(xs), pos, t in xs, s["ask"])
        return (tuple(s["xs"]), s["target"], s["ask"])
    if name == "bracket_match":
        t = s["s"]
        if b:
            mp = {}
            for ch in t:
                if ch in "([{" and ch not in mp:
                    mp[ch] = len(mp)
            tt = "".join("<" + str(mp[ch]) if ch in "([{" else ">" + str(mp["([{"[")]}".index(ch)]]) for ch in t)
            return (tt, s["ask"], mp.get(s["kind"]) if s["kind"] else None)
        return (t, s["ask"], s["kind"])
    if name == "bst_traversal":
        return (ranks(s["xs"]) if c else tuple(s["xs"]), s["kind"])
    if name == "min_heap_ops":
        return (ranks(s["xs"]) if c else tuple(s["xs"]), s["removals"])
    if name == "lis_length":
        return ranks(s["xs"]) if c else tuple(s["xs"])
    if name == "sort_list":
        return (ranks(s["xs"]) if c else tuple(sorted(s["xs"])), s["desc"])
    if name == "kth_smallest":
        return (ranks(s["xs"]) if c else tuple(sorted(s["xs"])), s["k"])
    if name == "interval_scheduling":
        iv = sorted(tuple(x) for x in s["meetings"])
        if c:
            r = {v: i for i, v in enumerate(sorted({v for x in iv for v in x}))}
            iv = sorted((r[a], r[b_]) for a, b_ in iv)
        return tuple(iv)
    if name == "hash_probe":
        if c:
            return (s["m"], tuple(k % s["m"] for k in s["keys"]), s["ask"])
        return (s["m"], tuple(s["keys"]), s["ask"])
    if name == "cache_eviction":
        return (s["cap"], s["policy"], s["ask"], relabel_str(s["seq"], keep=()) if False else tuple(_rl_list(s["seq"])))
    if name == "cheapest_network":
        return wl_hash(s["towns"], s["cables"])
    if name == "coin_change_min":
        return (tuple(s["coins"]), tuple(sorted(s["amounts"])))
    if name == "count_divisible":
        return (s["m"], s["t"], tuple(sorted(s["xs"])))
    if name == "count_letter":
        if b:
            return tuple(sorted((len(w), w.count(s["letter"])) for w in s["words"]))
        return (s["letter"], tuple(sorted(s["words"])))
    if name == "dictionary_rank":
        if b:
            m = len(s["letters"])
            if s["ask"] == "word":
                return (m, s["length"], "w", s["k"])
            return (m, s["length"], "p", tuple(s["letters"].index(ch) for ch in s["word"]))
        return (tuple(s["letters"]), s["length"], s["ask"], s["k"], s["word"])
    if name in ("lcs_length",):
        if b:
            rl = relabel_str(s["a"] + "|" + s["b"], keep="|")
            return rl
        return (s["a"], s["b"])
    if name in ("longest_palindromic_substring",):
        return relabel_str(s["s"]) if b else s["s"]
    if name == "palindrome_check":
        return relabel_str(s["phrase"]) if b else s["phrase"]
    if name == "run_length":
        return relabel_str(s["s"]) if b else s["s"]
    if name == "string_rewrite_nonidentity":
        if b:
            joined = s["s"] + "|" + "|".join(p + ">" + t for p, t in s["rules"])
            return relabel_str(joined, keep="|>")
        return (s["s"], tuple(map(tuple, s["rules"])))
    if name == "permutation_power":
        return cycle_canon(s["img"], s["s"], s["t"]) if b else (tuple(s["img"]), s["s"], s["t"])
    if name == "merge_smallest_cost":
        return tuple(sorted(s["ws"]))
    if name == "subtraction_game":
        return (tuple(sorted(s["piles"])), tuple(s["moves"]))
    # everything else: the structured form itself (no names, no letters to relabel)
    return json.dumps(s, sort_keys=True)


def _rl_list(seq):
    mp = {}
    out = []
    for x in seq:
        if x not in mp:
            mp[x] = len(mp)
        out.append(mp[x])
    return out


def run(args):
    lid, lv = args
    from studies.m0.core import build_item
    from studies.m0.r2_fix3_set import fix3_set

    lin = fix3_set()[lid]
    name = lid.split(".", 1)[1]
    r = random.Random(f"a4r2-cap|{lid}|{lv}|7")
    cnt = {k: Counter() for k in "abc"}
    for i in range(N):
        it = build_item(lin, lv, r, "A", "c")
        for k in "abc":
            key = hashlib.blake2b(repr(canon(name, it.structured, k)).encode(), digest_size=12).digest()
            cnt[k][key] += 1
    out = {}
    for k in "abc":
        D = len(cnt[k])
        ff = Counter(cnt[k].values())
        f1, f2 = ff.get(1, 0), ff.get(2, 0)
        chao = D + (f1 * f1 / (2 * f2) if f2 else f1 * (f1 - 1) / 2)
        out[k] = {"D": D, "f1": f1, "f2": f2, "chao1": round(chao, 1)}
    return lid, lv, out


if __name__ == "__main__":
    sys.path.insert(0, ".")
    from studies.m0.r2_fix3_set import fix3_set

    ids = sorted(fix3_set())
    if len(sys.argv) > 3:
        ids = [i for i in ids if i.split(".")[1] in sys.argv[3].split(",")]
    jobs = [(lid, lv) for lid in ids for lv in range(7)]
    with Pool(12) as p:
        res = p.map(run, jobs, chunksize=1)
    out = {}
    for lid, lv, o in res:
        out.setdefault(lid, {})[str(lv)] = o
    json.dump({"N": N, "lineages": out}, open(OUT, "w"), indent=1, sort_keys=True)
    print("wrote", OUT)
