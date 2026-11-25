# ruff: noqa: E501
"""Capacity of the R2 fix-round-3 set under two readings of 'distinct item' (ruling R-5, R-16 not ruled): counted on STRUCTURE, per lineage and level, from draws.

reading A: proper names (objects, towns, people) relabelled by first appearance, and the order of a list dropped where the answer does not depend on it; numbers, letters and symbols as written.
reading B: A, plus letters and labels relabelled by first appearance (letters of a string or word list, bracket kinds, the element labels of a mapping reduced to its cycle type with the start's cycle marked, the letters of dictionary_rank by rank).
Demand per cluster and level: ``r2_fix3_clusters.demand(G)`` (R-11) with G = 17 (as briefed); reserve levels carry the same demand (R-10). A cluster's capacity is the SUM of its members' distinct counts.
A count is a LOWER BOUND from D draws (distinct canonical forms seen); 'saturated' means distinct < 0.9 D (the draws have seen most of the space). For graphs (cheapest_network) an isomorphism INVARIANT is used, so the count is a lower bound.

Usage: ``PYTHONHASHSEED=0 uv run --locked --offline python -m studies.m0.r2_fix3_capacity run --draws 40000 --out OUT.json [--only a,b] [--set fix3|current]`` and ``... summarise IN.json --g 17``.
Seeds are string seeds ``fix3-cap|<lineage>|<level>|7`` (throwaway). Self-check, not independent review.
"""

from __future__ import annotations

import argparse
import json
import random
from collections import Counter
from multiprocessing import Pool
from pathlib import Path
from typing import Any

from studies.m0.core import ALL_LEVELS, build_item


def _relabel(xs: list[Any], mp: dict[Any, int] | None = None) -> tuple[list[int], dict[Any, int]]:
    mp = {} if mp is None else mp
    out = []
    for x in xs:
        if x not in mp:
            mp[x] = len(mp)
        out.append(mp[x])
    return out, mp


def _relabel_str(s: str, mp: dict[Any, int]) -> str:
    return "".join(chr(65 + _relabel([c], mp)[0][0]) for c in s)


def canon(lid: str, s: dict[str, Any], reading: str) -> str:
    n = lid.split(".", 1)[1]
    s = dict(s)
    b = reading == "B"
    if n == "cache_eviction":
        seq, _mp = _relabel(s["seq"])
        return json.dumps([s["cap"], s["policy"], s["ask"], seq])
    if n == "cheapest_network":
        inc: dict[str, list[int]] = {}
        for x, y, w in s["cables"]:
            inc.setdefault(x, []).append(w)
            inc.setdefault(y, []).append(w)
        sig = {t: tuple(sorted(v)) for t, v in inc.items()}
        edges = sorted((w, tuple(sorted([sig[x], sig[y]]))) for x, y, w in s["cables"])
        return json.dumps([sorted(sig.values()), edges])
    if n == "merge_smallest_cost":
        return json.dumps(sorted(s["ws"]))
    if n == "interval_scheduling":
        return json.dumps(sorted(s["meetings"]))
    if n == "subtraction_game":
        return json.dumps([sorted(s["piles"]), s["moves"]])
    if n in ("kth_smallest", "sort_list"):
        s["xs"] = sorted(s["xs"])
        return json.dumps(s, sort_keys=True)
    if n == "count_divisible":
        s["xs"] = sorted(s["xs"])
        return json.dumps(s, sort_keys=True)
    if n == "lcs_length":
        a, c = sorted([s["a"], s["b"]])
        if b:
            mp: dict[Any, int] = {}
            a, c = _relabel_str(a, mp), _relabel_str(c, mp)
        return json.dumps([a, c])
    if n == "count_letter":
        ws = sorted(s["words"])
        if b:
            mp = {}
            letter = _relabel_str(s["letter"], mp)
            return json.dumps([sorted(_relabel_str(w, mp) for w in ws), letter])
        return json.dumps([ws, s["letter"]])
    if b:
        if n in ("longest_palindromic_substring", "run_length"):
            return json.dumps(_relabel_str(s["s"], {}))
        if n == "palindrome_check":
            mp = {}
            return json.dumps("".join(" " if c == " " else _relabel_str(c, mp) for c in s["phrase"]))
        if n == "string_rewrite_nonidentity":
            mp = {}
            return json.dumps([_relabel_str(s["s"], mp), [[_relabel_str(p, mp), _relabel_str(t, mp)] for p, t in s["rules"]]])
        if n == "bracket_match":
            kinds = {"(": 0, ")": 0, "[": 1, "]": 1, "{": 2, "}": 2}
            ks, kmp = _relabel([kinds[c] for c in s["s"]])
            shape = "".join("o" if c in "([{" else "c" for c in s["s"])
            kind = None if s.get("kind") is None else kmp.get(kinds[s["kind"]])
            return json.dumps([shape, ks, s["ask"], kind])
        if n == "dictionary_rank":
            letters = sorted(s["letters"])
            w = None if s["word"] is None else [letters.index(c) for c in s["word"]]
            return json.dumps([len(letters), s.get("length", len(letters)), s["ask"], s["k"], w])
        if n == "permutation_power":
            img, st = s["img"], s["s"]
            seen: set[int] = set()
            cycles: list[int] = []
            mark = None
            for i in range(1, len(img) + 1):
                if i in seen:
                    continue
                c, j = [], i
                while j not in seen:
                    seen.add(j)
                    c.append(j)
                    j = img[j - 1]
                cycles.append(len(c))
                if st in c:
                    mark = len(c)
            return json.dumps([sorted(cycles), mark, s["t"]])
    return json.dumps(s, sort_keys=True)


def run_one(args: tuple[str, str, int]) -> tuple[str, dict[str, Any]]:
    which, lid, draws = args
    from studies.m0.r2_fix3_battery import lineage_set

    lin = lineage_set(which)[lid]
    res: dict[str, Any] = {}
    for lv in ALL_LEVELS:
        r = random.Random(f"fix3-cap|{lid}|{lv}|7")
        cnt = {k: Counter[str]() for k in "AB"}
        for _ in range(draws):
            it = build_item(lin, lv, r, "A", "c")
            for k in "AB":
                cnt[k][canon(lid, it.structured, k)] += 1
        row: dict[str, Any] = {"draws": draws}
        for k in "AB":
            c = cnt[k]
            f1 = sum(1 for v in c.values() if v == 1)
            f2 = sum(1 for v in c.values() if v == 2)
            chao = len(c) + (f1 * f1 / (2 * f2) if f2 else f1 * (f1 - 1) / 2)
            row[k] = {"distinct": len(c), "f1": f1, "f2": f2, "chao1": round(chao), "saturated": len(c) < 0.9 * draws}
        res[str(lv)] = row
    return lid, res


def summarise(data: dict[str, Any], g: int) -> tuple[str, dict[str, Any]]:
    from studies.m0.r2_fix3_clusters import clusters, demand

    need = demand(g)
    cl = {k: v for k, v in clusters().items()}
    lines = [f"G = {g}: demand per cluster and level = {need}; clusters = {len(cl)}; draws per lineage-level = {next(iter(data['lineages'].values()))['0']['draws']}"]
    fails: dict[str, list[tuple[str, int, int]]] = {"A": [], "B": []}
    table: dict[str, Any] = {}
    for reading in "AB":
        for key, members in cl.items():
            for lv in range(7):
                tot = sum(data["lineages"][m][str(lv)][reading]["distinct"] for m in members)
                table.setdefault(reading, {}).setdefault(key, {})[lv] = tot
                if tot < need:
                    fails[reading].append((key, lv, tot))
        lines.append(f"reading {reading}: {len(fails[reading])} failing cluster-levels")
        for key, lv, tot in fails[reading]:
            mem = cl[key]
            parts = "; ".join(f"{m.split('.')[1]}={data['lineages'][m][str(lv)][reading]['distinct']}" for m in mem)
            lines.append(f"  {key} L{lv}: {tot} < {need}  [{parts}]")
    return "\n".join(lines), {"need": need, "table": table, "fails": fails}


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("run")
    a.add_argument("--draws", type=int, default=40000)
    a.add_argument("--out", type=Path, required=True)
    a.add_argument("--only", default="")
    a.add_argument("--set", default="fix3")
    a.add_argument("--procs", type=int, default=8)
    b = sub.add_parser("summarise")
    b.add_argument("inp", type=Path)
    b.add_argument("--g", type=int, default=17)
    ns = ap.parse_args()
    if ns.cmd == "run":
        from studies.m0.r2_fix3_battery import lineage_set

        ids = sorted(lineage_set(ns.set))
        if ns.only:
            want = {w if "." in w else f"R2.{w}" for w in ns.only.split(",")}
            ids = [i for i in ids if i in want]
        with Pool(ns.procs) as p:
            res = dict(p.map(run_one, [(ns.set, i, ns.draws) for i in ids], chunksize=1))
        ns.out.write_text(json.dumps({"draws": ns.draws, "set": ns.set, "lineages": res}, indent=1, sort_keys=True))
        print("wrote", ns.out)
    else:
        text, _ = summarise(json.loads(ns.inp.read_text()), ns.g)
        print(text)


if __name__ == "__main__":
    main()
