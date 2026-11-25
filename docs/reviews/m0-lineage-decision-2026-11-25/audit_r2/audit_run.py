# ruff: noqa
"""Auditor's main run for R2 (26 batch-1 lineages + the existing 16 for capacity only).

For every lineage and level 0..6 it draws N items with the generator (auditor seed 2025112501, not a registered seed) and:
  * key check: the auditor's question-only solver on the first S items of each level (26 new lineages);
  * shortcut screen: chance, most-frequent-answer rate (overall and per shape), and every heuristic in heuristics.H, with a
    Wilson 95% interval; yes/no answers read two-sided (raw accuracy is reported, below-chance = overshoot);
  * capacity: distinct structured forms among the N draws, with names relabelled by first appearance, and (where the
    answer does not depend on order) an order-invariant count; deferred acceptance at n=3 is counted up to renaming of
    people by brute force over the 36 relabellings.
Writes JSON to the given output path. Generation goes through studies.m0 (read-only); solvers and heuristics are the
auditor's own files."""
import itertools
import json
import math
import os
import sys
import time
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from heuristics import H, SHAPE_KEYS
from solvers import SOLVERS

from studies.m0.core import ALL_LEVELS, build_item, lineages_of, stream
from studies.m0.lineages_r2_common import load_batch1

SEED = 2025112501
N = int(sys.argv[2]) if len(sys.argv) > 2 else 5000
S = int(sys.argv[3]) if len(sys.argv) > 3 else 1000
OUT = sys.argv[1]
ONLY = sys.argv[4].split(",") if len(sys.argv) > 4 and sys.argv[4] else None


def wilson(k, n, z=1.96):
    if n == 0:
        return (None, None)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (round(c - h, 4), round(c + h, 4))


def norm(a):
    return a.strip().lower()


def relabel(seq_like, mapping):
    out = []
    for x in seq_like:
        if x not in mapping:
            mapping[x] = f"#{len(mapping)}"
        out.append(mapping[x])
    return out


def canon(lid, s):
    """Structured form with names relabelled (exact up to renaming where names are mere labels)."""
    if lid == "R2.cache_eviction":
        mp = {}
        seq = relabel(s["seq"], mp)
        item = None if s["item"] is None else relabel([s["item"]], mp)[0]
        return json.dumps([s["cap"], s["policy"], s["ask"], seq, item])
    if lid == "R2.cheapest_network":
        mp = {}
        edges = [relabel([a, b], mp) + [w] for a, b, w in s["cables"]]
        return json.dumps(sorted(edges))
    if lid == "R2.deferred_acceptance_partner":
        P, R = s["proposers"], s["responders"]
        pp = [[R.index(r) for r in s["prefs_p"][p]] for p in P]
        rp = [[P.index(p) for p in s["prefs_r"][r]] for r in R]
        return json.dumps([pp, rp, P.index(s["who"])])
    return json.dumps(s, sort_keys=True)


def canon_order_free(lid, s):
    """Order-invariant key where the answer does not depend on presentation order (None otherwise)."""
    if lid == "R2.merge_smallest_cost":
        return json.dumps(sorted(s["ws"]))
    if lid == "R2.interval_scheduling":
        return json.dumps(sorted(s["meetings"]))
    if lid == "R2.cheapest_network":
        # isomorphism invariant (equal for isomorphic weighted graphs): sorted (sorted degree pair, weight) per edge
        deg = Counter()
        for a, b, _ in s["cables"]:
            deg[a] += 1; deg[b] += 1
        return json.dumps(sorted([sorted([deg[a], deg[b]]) + [w] for a, b, w in s["cables"]]))
    if lid == "R2.deferred_acceptance_partner":
        P, R = s["proposers"], s["responders"]
        n = len(P)
        if n > 3:
            return None
        pp = [[R.index(r) for r in s["prefs_p"][p]] for p in P]
        rp = [[P.index(p) for p in s["prefs_r"][r]] for r in R]
        who = P.index(s["who"])
        best = None
        for sp in itertools.permutations(range(n)):  # new index of proposer i is sp[i]
            if sp[who] != 0:
                continue
            for sr in itertools.permutations(range(n)):
                npp = [None] * n
                for i in range(n):
                    npp[sp[i]] = [sr[j] for j in pp[i]]
                nrp = [None] * n
                for j in range(n):
                    nrp[sr[j]] = [sp[i] for i in rp[j]]
                key = (tuple(map(tuple, npp)), tuple(map(tuple, nrp)))
                if best is None or key < best:
                    best = key
        return json.dumps(best)
    return None


def shape_of(s):
    return "|".join(f"{k}={s[k]}" for k in SHAPE_KEYS if k in s and not isinstance(s[k], (list, dict)))


def ints_in(q):
    import re
    return [int(x) for x in re.findall(r"-?\d+", q)]


def main():
    existing = lineages_of("R2")
    new = load_batch1()
    res = {"seed": SEED, "N_per_level": N, "solver_checked_per_level": S, "lineages": {}}
    t0 = time.time()
    for lin in [*new, *existing]:
        if ONLY and lin.id not in ONLY:
            continue
        is_new = lin in new
        rec = {"new": is_new, "family": lin.family, "levels": {}}
        for lv in ALL_LEVELS:
            r = stream(SEED, "audit", lin.id, str(lv))
            items = [build_item(lin, lv, r, "A", f"{lin.id}/aud/{lv}/{i}") for i in range(N)]
            d = {}
            # capacity
            d["distinct_structured"] = len({canon(lin.id, it.structured) for it in items})
            d["distinct_question_text"] = len({it.question for it in items})
            of = [canon_order_free(lin.id, it.structured) for it in items]
            if of[0] is not None:
                d["distinct_order_free"] = len(set(of))
            if not is_new:
                rec["levels"][str(lv)] = d
                continue
            # key check with the auditor's question-only solver
            bad, errs = [], []
            for it in items[:S]:
                try:
                    g = SOLVERS[lin.id](it.question)
                    if norm(g) != norm(it.answer):
                        bad.append([it.id, it.answer, g])
                except Exception as e:
                    errs.append([it.id, f"{type(e).__name__}: {e}"])
            d["solver_checked"] = min(S, len(items))
            d["solver_disagree"] = bad[:20]
            d["solver_disagree_n"] = len(bad)
            d["solver_error"] = errs[:20]
            d["solver_error_n"] = len(errs)
            # answer distribution
            ans = Counter(norm(it.answer) for it in items)
            d["n"] = len(items)
            d["chance"] = round(sum(1 / it.k if it.k else 0 for it in items) / len(items), 4)
            top = ans.most_common(1)[0]
            d["mode_answer"] = top[0][:40]
            d["mode_rate"] = round(top[1] / len(items), 4)
            d["distinct_answers"] = len(ans)
            shapes = {}
            for it in items:
                shapes.setdefault(shape_of(it.structured), []).append(it)
            d["shapes"] = {}
            for sh, grp in sorted(shapes.items()):
                c = Counter(norm(it.answer) for it in grp)
                mc = c.most_common(1)[0]
                d["shapes"][sh] = {"n": len(grp), "mode_answer": mc[0][:40], "mode_rate": round(mc[1] / len(grp), 4),
                                   "chance": round(sum(1 / it.k if it.k else 0 for it in grp) / len(grp), 4)}
            d["answer_token_in_question"] = round(sum(1 for it in items if it.answer_type == "number" and int(it.answer) in ints_in(it.question)) / len(items), 4)
            # heuristics
            hs = {}
            for it in items:
                g = H[lin.id](it.structured)
                yes_no = it.answer_type == "yn"
                for name, guess in g.items():
                    if guess is None:
                        continue
                    h = hs.setdefault(name, {"n": 0, "hit": 0, "chance_sum": 0.0, "yn": 0})
                    h["n"] += 1
                    h["hit"] += norm(guess) == norm(it.answer)
                    h["chance_sum"] += (1 / it.k) if it.k else 0.0
                    h["yn"] += yes_no
                # generic numeric heuristics
                if it.answer_type == "number":
                    xs = ints_in(it.question)
                    for name, pick in (("G:first number in question", lambda v: v[0]), ("G:last number in question", lambda v: v[-1]),
                                       ("G:largest number in question", max), ("G:smallest number in question", min)):
                        if xs:
                            h = hs.setdefault(name, {"n": 0, "hit": 0, "chance_sum": 0.0, "yn": 0})
                            h["n"] += 1
                            h["hit"] += str(pick(xs)) == it.answer
            out = {}
            for name, h in hs.items():
                acc = h["hit"] / h["n"]
                ci = wilson(h["hit"], h["n"])
                ch = h["chance_sum"] / h["n"]
                e = {"n": h["n"], "acc": round(acc, 4), "ci95": ci, "chance": round(ch, 4)}
                if h["yn"] == h["n"] and h["n"]:
                    e["two_sided"] = round(max(acc, 1 - acc), 4)
                    e["direction"] = "above" if ci[0] > 0.5 else ("below (overshoot)" if ci[1] < 0.5 else "not distinguishable from 0.5")
                out[name] = e
            d["heuristics"] = out
            rec["levels"][str(lv)] = d
        res["lineages"][lin.id] = rec
        print(f"{lin.id} done at {time.time() - t0:.0f}s", flush=True)
    with open(OUT, "w") as f:
        json.dump(res, f, indent=1, sort_keys=True)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
