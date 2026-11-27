# ruff: noqa: E501
"""R2 fix round 4: the shortcut measurement over the UNION of the batteries (R-24): the auditor's audit-4 rules (``r2_fix4_a4_heur``), audit 3's rules (``r2_fix4_a3_heur``) and the fix-round-3 implementer's own rules
(``r2_fix3_heuristics.OWN``), per lineage, level and shape, two-sided. The measurement follows the auditor's ``a4_shortcuts.py`` (audit 4, R2; package copy of the rules, this harness re-typed from it):
open answers: effect = accuracy over all items of the shape (a rule that does not apply counts as wrong), chance 0; yes/no: |accuracy among the items where it applies - 0.5|; 'most frequent answer' is learned on a separate
training draw. The classes (cue, partial, construct, P, artifact) are the auditor's (``klass``, copied from his ``a4_summ2.py``). R-24 counts cue + partial + construct; P and artifact are reported, not counted.
Seeds are throwaway string seeds: seed set 'a4' = the auditor's (``a4r2|<id>|<level>|5`` train, ``|6`` test), so the unchanged lineages reproduce his numbers; seed set 'f4' = ``fix4|<id>|<level>|5/6``.
Usage: ``PYTHONHASHSEED=0 uv run --locked --offline python -m studies.m0.r2_fix4_battery run --n 2000 --seeds a4 --out OUT.json`` then ``... summary OUT.json``. Self-check, not independent review."""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter
from multiprocessing import Pool
from pathlib import Path
from typing import Any

from studies.m0.core import ALL_LEVELS, build_item

CLASSES = ("cue", "partial", "construct")
# classification copied (with attribution) from audit 4's a4_summ2.py; the lists are the auditor's
MISREAD = [
    "[a3] digits read right to left", "[a3] k-th largest", "[a3] syndrome read with the bits reversed", "[a3] doubling the other parity",
    "[a3] check digit: payload total without the new digit", "[mine] check digit: payload's own last digit not doubled",
    "[a3] first occurrence only per rule", "[a3] largest: largest prime <= sqrt(n) dividing n", "[a3] (b-a)//m + 1",
    "[mine] latest start first", "[mine] Floyd bottom-up heapify", "[mine] inverse mapping t times",
]
PARTIAL = [
    "letter pairs", "[a3] outer two letters each side match", "[a3] first letter equals last letter",
    "centres only", "[a3] longest odd palindrome only", "[a3] longest even palindrome only", "longest palindrome of length <= 7",
    "scanning only primes up to 61", "first failing check", "plain digit sum",
    "count of piles that are a win alone is odd", "odd number of piles that are first-player wins alone", "[cond] ignore",
]
CONSTRUCT = ["t mod (n-1) applications", "t mod 10 applications"]


def klass(hn: str, sh: str, lv: int) -> str:
    if "(P" in hn:
        return "P"
    if hn in ("[a3] ignore reverses", "[a3] ignore moves to the end"):
        return "artifact"
    if hn == "[a3] removal by deleting the minimum and keeping the order of the rest" and sh == "removals=0":
        return "artifact"
    if hn in ("[a3] only the first rule", "[a3] only the last rule, on the start string", "[a3] rules in reverse order") and lv == 0:
        return "artifact"
    if hn == "[a3] rules in reverse order" or hn == "[mine] [cond] rules in reverse order" or hn == "[mine] [cond] all rules applied to the start string at once (left to right, first matching rule)":
        return "P"
    if any(hn.startswith(m) for m in MISREAD):
        return "P"
    if any(p in hn for p in PARTIAL):
        return "partial"
    if any(c in hn for c in CONSTRUCT):
        return "construct"
    return "cue"


def shape(lid: str, s: dict[str, Any]) -> str:
    for k in ("ask", "convention", "kind"):
        if k in s and isinstance(s[k], str):
            v = s[k]
            if lid.endswith("cache_eviction"):
                v = s["policy"] + "/" + v
            return str(v)
    if lid.endswith("min_heap_ops"):
        return f"removals={s['removals']}"
    if lid.endswith("sort_list"):
        return f"desc={s['desc']}"
    return "-"


def batteries(name: str) -> list[tuple[str, Any]]:
    from studies.m0 import r2_fix4_a3_heur, r2_fix4_a4_heur
    from studies.m0.r2_fix3_heuristics import OWN

    out = []
    for src, h in (("mine", r2_fix4_a4_heur.H), ("a3", r2_fix4_a3_heur.H), ("impl", OWN)):
        for hn, fn in h.get(name, []):
            out.append((f"[{src}] {hn}", fn))
    return out


def run_one(args: tuple[str, int, str]) -> tuple[str, dict[str, Any]]:
    lid, n_items, seeds = args
    from studies.m0.r2_fix4_set import fix4_set

    lin = fix4_set()[lid]
    hs = batteries(lid.split(".", 1)[1])
    tag = "a4r2" if seeds == "a4" else __import__("os").environ["M0_FR_TAG"]
    res: dict[str, Any] = {}
    for lv in ALL_LEVELS:
        rtr = random.Random(f"{tag}|{lid}|{lv}|5")
        rte = random.Random(f"{tag}|{lid}|{lv}|6")
        tr = [build_item(lin, lv, rtr, "A", "t") for _ in range(n_items)]
        te = [build_item(lin, lv, rte, "A", "e") for _ in range(n_items)]
        gtr: dict[str, list[Any]] = {}
        gte: dict[str, list[Any]] = {}
        for it in tr:
            gtr.setdefault(shape(lid, it.structured), []).append(it)
        for it in te:
            gte.setdefault(shape(lid, it.structured), []).append(it)
        rows: dict[str, Any] = {}
        for sh, grp in gte.items():
            at = grp[0].answer_type
            ent: dict[str, Any] = {"n": len(grp), "answer_type": at, "rules": {}, "distinct_answers": len({it.answer for it in grp})}
            if at == "yn":
                ent["yes_share"] = sum(it.answer == "yes" for it in grp) / len(grp)
            mode = Counter(it.answer for it in gtr.get(sh, grp)).most_common(1)[0][0]
            ent["rules"]["most frequent answer (train draw)"] = {"k": sum(it.answer == mode for it in grp), "napp": len(grp), "nerr": 0}
            for hn, fn in hs:
                kk = napp = nerr = 0
                for it in grp:
                    try:
                        a = fn(it.structured, it.question)
                    except Exception:  # counted, never hidden
                        nerr += 1
                        a = None
                    if a is None:
                        continue
                    napp += 1
                    kk += a == it.answer
                if napp:
                    ent["rules"][hn] = {"k": kk, "napp": napp, "nerr": nerr}
            for v in ent["rules"].values():
                v["acc_all"] = v["k"] / len(grp)
                v["acc_app"] = v["k"] / v["napp"]
            rows[sh] = ent
        res[str(lv)] = rows
    return lid, res


def effect(hn: str, v: dict[str, Any], at: str) -> float:
    """The auditor's effect: yes/no |acc among applicable - 0.5|; open: accuracy over all items (a [cond] rule: where it applies)."""
    if at == "yn":
        return abs(v["acc_app"] - 0.5)
    return float(v["acc_app"] if "[cond]" in hn else v["acc_all"])


def worst(d: dict[str, Any]) -> dict[str, Any]:
    """Per lineage: for each level the largest effect over cue + partial + construct rules and shapes (name, shape, class), and the same for the P and artifact classes (reported only)."""
    out: dict[str, Any] = {}
    for lid, lv_rows in sorted(d["lineages"].items()):
        per: dict[str, Any] = {}
        for lv, rows in sorted(lv_rows.items(), key=lambda kv: int(kv[0])):
            best = (0.0, "", "", "")
            other = (0.0, "", "", "")
            for sh, ent in sorted(rows.items()):
                for hn, v in sorted(ent["rules"].items()):
                    c = klass(hn, sh, int(lv))
                    e = effect(hn, v, ent["answer_type"])
                    if c in CLASSES:
                        if e > best[0]:
                            best = (e, hn, sh, c)
                    elif e > other[0]:
                        other = (e, hn, sh, c)
            per[lv] = {"max_counted": round(best[0], 4), "rule": best[1], "shape": best[2], "class": best[3], "max_not_counted": round(other[0], 4), "not_counted_rule": other[1], "not_counted_class": other[3]}
        out[lid] = per
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--n", type=int, default=2000)
    r.add_argument("--seeds", choices=("a4", "f4"), default="a4")
    r.add_argument("--out", type=Path, required=True)
    r.add_argument("--only", default="")
    r.add_argument("--procs", type=int, default=8)
    s = sub.add_parser("summary")
    s.add_argument("inp", type=Path)
    a = ap.parse_args()
    if a.cmd == "run":
        from studies.m0.r2_fix4_set import fix4_set

        ids = sorted(fix4_set())
        if a.only:
            want = {w if "." in w else f"R2.{w}" for w in a.only.split(",")}
            ids = [i for i in ids if i in want]
        with Pool(a.procs) as p:
            res = dict(p.map(run_one, [(i, a.n, a.seeds) for i in ids], chunksize=1))
        a.out.write_text(json.dumps({"n": a.n, "seeds": a.seeds, "lineages": res}, indent=1, sort_keys=True))
        print("wrote", a.out, file=sys.stderr)
    else:
        d = json.loads(a.inp.read_text())
        for lid, per in worst(d).items():
            m = max(per.values(), key=lambda x: x["max_counted"])
            print(f"{lid:40s} max counted {m['max_counted']:.3f}  [{m['class']}] {m['rule'][:70]} ({m['shape']})")


if __name__ == "__main__":
    main()
