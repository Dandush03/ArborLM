# ruff: noqa: E501
"""R2 fix round 3: shortcut battery. Applies the auditor's heuristics (``a3_heur.py`` of audit 3, imported READ-ONLY from the review folder) plus this round's own
heuristics (``r2_fix3_heuristics``) to a set of lineages, per level and shape, with a training draw for the 'most frequent answer' rule and a separate test draw.

Measured, not thresholded: the +-0.10 figure is the lead's working target and is NOT a registered bound. Open answers: effect = accuracy (chance 0). Yes/no: effect = |accuracy - 0.5|.
A heuristic marked (P) is a valid alternative procedure or a full solve under a misreading; it is reported separately and not counted as a cue.
Seeds are string seeds ``fix3|<lineage>|<level>|1`` (test) and ``|2`` (train): throwaway, not registered. Self-check, not independent review.

Usage: ``PYTHONHASHSEED=0 uv run --locked --offline python -m studies.m0.r2_fix3_battery --set fix3|current --n 2000 --out OUT.json [--only a,b]``
"""

from __future__ import annotations

import argparse
import json
import math
import random
from collections import Counter
from collections.abc import Callable
from multiprocessing import Pool
from pathlib import Path
from typing import Any

from studies.m0.core import ALL_LEVELS, Lineage, build_item

ROOT = Path(__file__).resolve().parents[2]
AUDIT_DIR = ROOT / "docs" / "reviews" / "m0-lineage-decision-2026-11-25" / "audit3_r2"


def shape_of(lid: str, s: dict[str, Any]) -> str:
    for k in ("ask", "convention", "kind"):
        if k in s and isinstance(s[k], str):
            v = s[k]
            if lid.endswith("cache_eviction") and "policy" in s:
                v = s["policy"] + "/" + v
            return str(v)
    if lid.endswith("min_heap_ops"):
        return f"removals={s['removals']}"
    return "-"


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    w = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return round(c - w, 4), round(c + w, 4)


def heuristics_for(name: str, own: bool = True) -> list[tuple[str, Callable[[dict[str, Any], str], str | None]]]:
    """The auditor's battery for this lineage name plus (own=True) this round's own heuristics. The 'current' (before) set is measured with the auditor's battery only: the own rules were written for the new shapes."""
    from studies.m0 import (
        r2_fix4_a3_heur as a3_heur,  # package copy, with attribution, of the auditor's a3_heur.py (fix round 4 hygiene edit)
    )
    from studies.m0.r2_fix3_heuristics import OWN

    return [*a3_heur.H.get(name, []), *(OWN.get(name, []) if own else [])]


def lineage_set(which: str) -> dict[str, Lineage]:
    from studies.m0.r2_fix3_set import current_set, fix3_set

    return fix3_set() if which == "fix3" else current_set()


def run_one(args: tuple[str, str, int, str | None]) -> tuple[str, dict[str, Any]]:
    which, lid, n, only_level = args
    lin = lineage_set(which)[lid]
    name = lid.split(".", 1)[1]
    hs = heuristics_for(name, own=(which == "fix3"))
    res: dict[str, Any] = {}
    levels = ALL_LEVELS if only_level is None else tuple(int(x) for x in only_level.split(","))
    for lv in levels:
        rte = random.Random(f"fix3|{lid}|{lv}|1")
        rtr = random.Random(f"fix3|{lid}|{lv}|2")
        te = [build_item(lin, lv, rte, "A", "e") for _ in range(n)]
        tr = [build_item(lin, lv, rtr, "A", "t") for _ in range(n)]
        groups: dict[str, list[Any]] = {}
        for it in te:
            groups.setdefault(shape_of(lid, it.structured), []).append(it)
        modes: dict[str, str] = {}
        tg: dict[str, list[Any]] = {}
        for it in tr:
            tg.setdefault(shape_of(lid, it.structured), []).append(it)
        for sh, g in tg.items():
            modes[sh] = Counter(i.answer for i in g).most_common(1)[0][0]
        rows: dict[str, Any] = {}
        for sh, grp in sorted(groups.items()):
            at, k = grp[0].answer_type, grp[0].k
            chance = 0.5 if at == "yn" else (1 / k if k else 0.0)
            ent: dict[str, Any] = {"n": len(grp), "answer_type": at, "chance": chance, "heur": {}, "distinct": len({i.answer for i in grp})}
            if at == "yn":
                ent["yes_share"] = sum(i.answer == "yes" for i in grp) / len(grp)
            m = modes.get(sh)
            c = sum(i.answer == m for i in grp)
            ent["heur"]["most frequent answer (train draw)"] = {"n": len(grp), "k": c, "acc": c / len(grp)}
            errs: Counter[str] = Counter()
            for hn, fn in hs:
                kk = nn = 0
                for it in grp:
                    try:
                        a = fn(it.structured, it.question)
                    except Exception:  # a failing heuristic is counted, never hidden
                        errs[hn] += 1
                        continue
                    if a is None:
                        continue
                    nn += 1
                    kk += a == it.answer
                if nn >= max(20, len(grp) // 20):
                    ent["heur"][hn] = {"n": nn, "k": kk, "acc": kk / nn}
            for v in ent["heur"].values():
                v["lo"], v["hi"] = wilson(v["k"], v["n"])
                v["effect"] = abs(v["acc"] - 0.5) if at == "yn" else v["acc"] - chance
            if errs:
                ent["heur_errors"] = dict(errs)
            rows[sh] = ent
        res[str(lv)] = rows
    return lid, res


def is_p(hn: str, sh: str, lid: str = "") -> bool:
    """(P) rules, plus the auditor's own coverage artifacts: for 0 removals the rule 'delete the minimum' IS the solver; the 'latest start first' greedy is the mirror of the stated rule;
    for multiples_between (both ends are multiples) the counting rule (b-a)//m + 1 IS the procedure; for prime_factor_query the rule 'largest prime up to the square root' IS trial division."""
    return (
        "(P)" in hn
        or (sh == "removals=0" and hn.startswith("removal by deleting the minimum"))
        or (lid.endswith("multiples_between") and hn == "(b-a)//m + 1" and sh == "count")
        or (lid.endswith("prime_factor_query") and (hn == "largest: largest prime <= sqrt(n) dividing n" or hn.startswith("largest: largest prime <= 97 dividing n, scanning only")))  # trial division itself, or with a bounded prime table
        or (lid.endswith("interval_scheduling") and hn == "latest start first")  # the mirror of the earliest-finish greedy: a valid optimal strategy (the audit's own mistakes list)
    )


def fm(xs: list[float]) -> str:
    return " ".join(f"{x:.2f}" for x in xs)


def summarise(results: dict[str, Any], thr: float = 0.0) -> str:
    out: list[str] = []
    for lid, res in sorted(results.items()):
        shapes = sorted({sh for lv in res.values() for sh in lv})
        for sh in shapes:
            hn_all = sorted({hn for lv in res.values() if sh in lv for hn in lv[sh]["heur"]})
            worst_cue = [0.0] * 7
            worst_cue_n = [""] * 7
            worst_p = [0.0] * 7
            mode = [0.0] * 7
            for lv_s, rows in res.items():
                lv = int(lv_s)
                if sh not in rows:
                    continue
                for hn in hn_all:
                    e = rows[sh]["heur"].get(hn)
                    if e is None:
                        continue
                    if hn.startswith("most frequent"):
                        mode[lv] = e["effect"]
                    elif is_p(hn, sh, lid):
                        worst_p[lv] = max(worst_p[lv], e["effect"])
                    elif e["effect"] > worst_cue[lv]:
                        worst_cue[lv], worst_cue_n[lv] = e["effect"], hn
            if max(worst_cue + mode) < thr and max(worst_p) < thr:
                continue
            out.append(f"{lid} [{sh}] cue max : {fm(worst_cue)}  (max {max(worst_cue):.2f})")
            out.append(f"{'':{len(lid) + len(sh) + 3}}mode    : {fm(mode)}  (max {max(mode):.2f})")
            if max(worst_p) > 0:
                out.append(f"{'':{len(lid) + len(sh) + 3}}(P) max  : {fm(worst_p)}")
            lv_w = max(range(7), key=lambda i: worst_cue[i])
            out.append(f"{'':{len(lid) + len(sh) + 3}}worst cue at L{lv_w}: {worst_cue_n[lv_w]}")
    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", default="fix3", choices=("fix3", "current"))
    ap.add_argument("--n", type=int, default=1000)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--only", default="")
    ap.add_argument("--levels", default=None)
    ap.add_argument("--procs", type=int, default=8)
    a = ap.parse_args()
    ids = sorted(lineage_set(a.set))
    if a.only:
        want = {w if "." in w else f"R2.{w}" for w in a.only.split(",")}
        ids = [i for i in ids if i in want]
    with Pool(a.procs) as p:
        res = dict(p.map(run_one, [(a.set, i, a.n, a.levels) for i in ids], chunksize=1))
    a.out.write_text(json.dumps({"set": a.set, "n": a.n, "lineages": res}, indent=1, sort_keys=True))
    print(summarise(res))


if __name__ == "__main__":
    main()
