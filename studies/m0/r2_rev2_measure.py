# ruff: noqa: E501
"""Measurement for the R2 fix round (lead ruling R-3 and R-5): per level, two-sided shortcut accuracy with the AUDITOR's heuristic battery (copied into
``r2_audit_heuristics_copy.py`` with attribution; nothing is imported from the audit folder) plus the author's own, before (batch-1 shapes) and after (rev2 shapes);
and capacity counted on structure at the G actually written. Measured, not thresholded (R-3).

``shortcuts``: for every lineage and level, N items; for every (shape, heuristic) the exact-match accuracy over the items where it applies; yes/no read two-sided
(max(acc, 1 - acc), raw also kept). ``capacity``: distinct canonical structured forms among draws (names relabelled by first appearance; presentation order ignored
where the answer does not depend on it), against 10 x demand at G.

Demand (ADR-0033 section 6.2 capacity gate, as used in ``lineage_gates.demand_at_g``): a core level demands ceil(24,000 / G) + 100 distinct items (the whole development + sealed pools of
a part on one level, plus the tuning draw), a reserve level 100; the gate is 10 x that. G used: 19 = ceil(38 / 2), the strict clusters of the R2 map (``lineages_r2_clusters``) split in two parts.

Run: ``PYTHONHASHSEED=0 uv run --locked --offline python -m studies.m0.r2_rev2_measure shortcuts --out <dir> [--only R2.x,R2.y]``.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any

from studies.m0.core import ALL_LEVELS, Lineage, build_item, stream
from studies.m0.lineages_r2_common import load_batch1
from studies.m0.lineages_r2_rev2 import load_rev2
from studies.m0.r2_audit_heuristics_copy import SHAPE_KEYS, H

SEED = 953901
G_WRITTEN = 19
POOLS_DEMANDED = 24_000
TUNING = 100
FACTOR = 10


def need(level: int, g: int = G_WRITTEN) -> int:
    return FACTOR * (TUNING if level in (0, 6) else math.ceil(POOLS_DEMANDED / g) + TUNING)


# Heuristics in the auditor's battery that are NOT cheap cues, so they are listed and left out of the 'worst' table (the auditor's own mistakes list, section 5, and valid or alternative procedures):
NOT_SHORTCUTS = (
    "Python heapq", "heapify of the whole row", "0-based floor", "capped at 7", "ends in 0 or 5", "fewest clashes first", "top half",
    "'same kind' misreading", "other neighbour order", "periodic boundary", "adjacent-only merging", "does not stop at the target",
)


# expression_eval: evaluating the item under the OTHER stated rule, or ignoring parentheses, needs a full evaluation; it agrees with the right key when the two rules happen to agree (reported in
# the manifest as a wrong-rule rate, not counted as a cue; it falls from about 0.8 at level 0 to about 0.4 at level 6)
WRONG_RULE = ("A:the other convention", "A:parentheses ignored, ranked", "X:parentheses ignored, left to right")


def shape_of(s: dict[str, Any]) -> str:
    return "|".join(f"{k}={s[k]}" for k in SHAPE_KEYS if k in s and not isinstance(s[k], list | dict))


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return round(c - h, 4), round(c + h, 4)


_NUM = re.compile(r"-?\d+")


def own_heuristics(lid: str, s: dict[str, Any], question: str, answer_type: str) -> dict[str, str | None]:
    """The author's additions for the revised shapes (the audit's battery is applied as well)."""
    out: dict[str, str | None] = {}
    nums = [int(x) for x in _NUM.findall(question)]
    if answer_type == "number" and nums:
        out["B:first number in the question"] = str(nums[0])
        out["B:last number in the question"] = str(nums[-1])
        out["B:largest number in the question"] = str(max(nums))
        out["B:smallest number in the question"] = str(min(nums))
    if lid == "R2.chip_toppling" and s.get("ask") == "topplings_of":
        row, c = s["row"], s["cell"] - 1
        out["B:chips in the cell // 2"] = str(row[c] // 2)
        out["B:chips in the cell and its neighbours // 2"] = str(sum(row[max(0, c - 1) : c + 2]) // 2)
        out["B:total chips // 2"] = str(sum(row) // 2)
    if lid == "R2.chip_toppling" and s.get("ask") == "topplings":
        out["B:chips * n / 4"] = str(sum(s["row"]) * len(s["row"]) // 4)
    if lid == "R2.coin_change_min" and s.get("ask") == "ways":
        out["B:amount // sum of coins"] = str(s["amount"] // sum(s["coins"]))
        out["B:amount // product of two smallest coins + 1"] = str(s["amount"] // (sorted(s["coins"])[0] * sorted(s["coins"])[1]) + 1)
    if lid == "R2.subtraction_game" and "piles" in s:
        n1, n2 = s["piles"]
        mv = s["moves"]
        M = max(mv) + 1
        out["B:(n1 mod (max+1)) xor (n2 mod (max+1)) nonzero"] = "yes" if (n1 % M) ^ (n2 % M) else "no"
        out["B:piles differ"] = "yes" if n1 != n2 else "no"
        out["B:one pile is a multiple of max+1 and the other is not"] = "yes" if (n1 % M == 0) != (n2 % M == 0) else "no"
    return out


def lineage_sets() -> tuple[dict[str, Lineage], dict[str, Lineage]]:
    before = {x.id: x for x in load_batch1()}
    after = dict(before)
    for x in load_rev2():
        if x.id in before:
            after[x.id] = x
    return before, after


def shortcut_record(lin: Lineage, n: int) -> dict[str, Any]:
    levels: dict[str, Any] = {}
    for lv in ALL_LEVELS:
        r = stream(SEED, "rev2-shortcut", lin.id, str(lv))
        items = [build_item(lin, lv, r, "A", f"{lin.id}/m/{lv}/{i}") for i in range(n)]
        by_shape: dict[str, list[Any]] = {}
        for it in items:
            by_shape.setdefault(shape_of(it.structured), []).append(it)
        shapes: dict[str, Any] = {}
        errors = 0
        for sh, grp in sorted(by_shape.items()):
            chance = sum((1.0 / it.k) if it.k else 0.0 for it in grp) / len(grp)
            mode_key, mode_n = Counter(it.answer for it in grp).most_common(1)[0]
            hit: dict[str, int] = {}
            tot: dict[str, int] = {}
            yesno: set[str] = set()
            for it in grp:
                try:
                    guesses = {**(H[lin.id](it.structured) if lin.id in H else {}), **own_heuristics(lin.id, it.structured, it.question, it.answer_type)}
                except Exception:  # noqa: BLE001  (a heuristic written for another shape's fields does not apply)
                    errors += 1
                    guesses = own_heuristics(lin.id, it.structured, it.question, it.answer_type)
                for name, g in guesses.items():
                    if g is None:
                        continue
                    if g in ("yes", "no"):
                        yesno.add(name)
                    tot[name] = tot.get(name, 0) + 1
                    hit[name] = hit.get(name, 0) + (g == it.answer)
            hs = {}
            for name in sorted(tot):
                if tot[name] < 100 or any(x in name for x in NOT_SHORTCUTS) or (lin.id == "R2.expression_eval" and name in WRONG_RULE):
                    continue
                raw = hit[name] / tot[name]
                acc = max(raw, 1 - raw) if chance == 0.5 and name in yesno else raw
                hs[name] = {"acc": round(acc, 4), "raw": round(raw, 4), "n": tot[name], "ci": wilson(hit[name], tot[name])}
            shapes[sh] = {"items": len(grp), "chance": round(chance, 4), "mode_key_share": round(mode_n / len(grp), 4), "distinct_answers": len({it.answer for it in grp}), "heuristics": hs}
        levels[str(lv)] = {"shapes": shapes, "heuristic_errors": errors}
    return {"levels": levels}


def worst(rec: dict[str, Any]) -> dict[str, Any]:
    """Worst two-sided heuristic over levels and shapes (largest accuracy minus that shape's chance), and the worst constant (mode) share."""
    best = {"name": "", "acc": 0.0, "chance": 0.0, "level": -1, "shape": ""}
    mode = {"share": 0.0, "chance": 0.0, "level": -1, "shape": ""}
    for lv, d in rec["levels"].items():
        for sh, sd in d["shapes"].items():
            if sd["mode_key_share"] - sd["chance"] > mode["share"] - mode["chance"]:
                mode = {"share": sd["mode_key_share"], "chance": sd["chance"], "level": int(lv), "shape": sh}
            for name, h in sd["heuristics"].items():
                if h["acc"] - sd["chance"] > best["acc"] - best["chance"]:
                    best = {"name": name, "acc": h["acc"], "chance": sd["chance"], "level": int(lv), "shape": sh}
    return {"worst_heuristic": best, "worst_mode": mode}


# ---------------------------------------------------------------- capacity on structure (R-5)


def _relabel(xs: list[str], mp: dict[str, str]) -> list[str]:
    out = []
    for x in xs:
        if x not in mp:
            mp[x] = f"#{len(mp)}"
        out.append(mp[x])
    return out


def canon(lid: str, s: dict[str, Any]) -> str:
    """Structure only: names relabelled by first appearance; order dropped where the answer does not depend on it."""
    if lid == "R2.cache_eviction":
        mp: dict[str, str] = {}
        seq = _relabel(s["seq"], mp)
        item = None if s["item"] is None else _relabel([s["item"]], mp)[0]
        return json.dumps([s["cap"], s["policy"], s["ask"], seq, item])
    if lid == "R2.cheapest_network":
        mp = {}
        return json.dumps(sorted([*_relabel([a, b], mp), w] for a, b, w in s["cables"]))
    if lid == "R2.deferred_acceptance_partner":
        P, R = s["proposers"], s["responders"]
        return json.dumps([[[R.index(r) for r in s["prefs_p"][p]] for p in P], [[P.index(p) for p in s["prefs_r"][r]] for r in R], P.index(s["who"])])
    if lid == "R2.merge_smallest_cost":
        return json.dumps(sorted(s["ws"]))
    if lid == "R2.interval_scheduling":
        return json.dumps(sorted(s["meetings"]))
    if lid == "R2.subtraction_game" and "piles" in s:
        return json.dumps([sorted(s["piles"]), s["moves"]])
    if lid == "R2.hamming_error_position":
        return json.dumps(s["bits"])
    return json.dumps(s, sort_keys=True)


def capacity_record(lin: Lineage, g: int = G_WRITTEN) -> dict[str, Any]:
    rows = []
    for lv in ALL_LEVELS:
        nd = need(lv, g)
        r = stream(SEED, "rev2-capacity", lin.id, str(lv))
        seen: set[str] = set()
        draws = 0
        cap = 2 * nd + 1000
        while len(seen) < nd and draws < cap:
            draws += 1
            seen.add(canon(lin.id, build_item(lin, lv, r, "A", "c").structured))
        rows.append({"level": lv, "need": nd, "found_structural": len(seen), "draws": draws, "passed": len(seen) >= nd})
    return {"rows": rows, "levels_failed": [x["level"] for x in rows if not x["passed"]]}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["shortcuts", "capacity"])
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--per-level", type=int, default=2000)
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    only = [x for x in a.only.split(",") if x]
    before, after = lineage_sets()
    a.out.mkdir(parents=True, exist_ok=True)
    ids = sorted(before)
    ids = [i for i in ids if not only or i in only]
    res: dict[str, Any] = {"seed": SEED, "G": G_WRITTEN, "lineages": {}}
    for lid in ids:
        if a.cmd == "shortcuts":
            revised = after[lid] is not before[lid]
            rec: dict[str, Any] = {"revised": revised, "after": shortcut_record(after[lid], a.per_level)}
            rec["after"].update(worst(rec["after"]))
            if revised:
                rec["before"] = shortcut_record(before[lid], a.per_level)
                rec["before"].update(worst(rec["before"]))
        else:
            rec = {"revised": after[lid] is not before[lid], "after": capacity_record(after[lid])}
            if rec["revised"]:
                rec["before"] = capacity_record(before[lid])
        res["lineages"][lid] = rec
        print(lid, flush=True)
    suffix = "_".join(i.split(".")[-1] for i in only)[:60] if only else "all"
    (a.out / f"{a.cmd}_{suffix}.json").write_text(json.dumps(res, indent=1, sort_keys=True))


if __name__ == "__main__":
    main()
