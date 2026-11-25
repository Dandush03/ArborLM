# ruff: noqa: E501
"""Two-sided, per-level shortcut measurement for the R1 revision-4 set (lead ruling R-3).

Battery per shape = the generic text battery of ``lineages_r1_shortcuts`` (with the three audit-2 gate bugs fixed) + a constant most-frequent-key reading + the author's lineage-specific
heuristics of ``lineages_r1_shortcuts.SPECIFIC`` + the auditor's heuristics of ``r1_rev4_audit_heuristics`` (a copy of audit2_r1/heuristics.py, imported from the copy, never from the audit folder)
+ the extra heuristics defined here for the revision-4 schemas (``EXTRA``). Heuristic functions that raise on a shape's schema are skipped for that item (recorded as not firing).

For each (heuristic, level) cell: ``fires`` items on which the heuristic names something among the item's options, ``accuracy`` on those items, ``chance`` on those items (mean 1/k, 0 for open
answers), ``departure`` = accuracy - chance, ``anti_departure`` = the accuracy of picking uniformly among the options the heuristic did NOT choose, minus chance (closed answers), and
``gain`` = max(departure, anti_departure): what a solver gains by following it or by avoiding it. For OPEN answers the baseline is the share of the level's commonest answer (the auditor's
baseline) and the gain is accuracy minus that share (ruling 5 of the earlier round: the absolute exact-match rate is always printed). ``z`` = gain / standard error.
MEASURED, NOT THRESHOLDED: no bound is registered (ruling R-3); the table goes to the human lead.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from collections.abc import Callable, Sequence
from typing import Any

from studies.m0 import lineage_gates as lg
from studies.m0 import lineages_r1_shortcuts as sc
from studies.m0 import r1_rev4_audit_heuristics as aud
from studies.m0.core import ALL_LEVELS, Item, Lineage

Pred = sc.Pred
EXTRA: dict[str, Callable[[Item], dict[str, Pred]]] = {}  # base id (no revision suffix) -> extra heuristics, filled by r1_rev4_extra


def base(lid: str) -> str:
    return re.sub(r"_r\d+$", "", lid.removeprefix("R1."))


_AUD = {re.sub(r"_r\d+$", "", k): fn for k, fn in aud.H.items()}


def item_preds(it: Item, const_key: str | None = None) -> dict[str, Pred]:
    out: dict[str, Pred] = {}
    if const_key is not None:
        out["constant_most_frequent_key"] = const_key
    out.update(sc.generic(it))
    for n, fn in sc.spec_for(it.lineage).items():
        try:
            out[n] = fn(it)
        except Exception:  # noqa: BLE001 - a heuristic written for another schema does not fire
            pass
    if it.answer_type in ("name", "text") and sc.parse_options(it.question) is None:
        out.update(_mention_fallback(it))
    row = {"s": it.structured, "q": it.question, "a": it.answer, "k": it.k, "level": it.level}
    fn2 = _AUD.get(base(it.lineage))
    if fn2 is not None:
        try:
            out.update(fn2(row))
        except Exception:  # noqa: BLE001
            pass
    ex = EXTRA.get(base(it.lineage))
    if ex is not None:
        try:
            out.update(ex(it))
        except Exception:  # noqa: BLE001
            pass
    if it.answer_type == "number":  # an open numeric answer: a heuristic that names a person or a place does not predict a number
        out = {n: p for n, p in out.items() if p is None or (isinstance(p, str) and re.fullmatch(r"-?\d+", p))}
    return out


def _mention_fallback(it: Item) -> dict[str, Pred]:
    """Mention-order heuristics for a name answer whose question has no "Choose from" list: the options are the entities the question mentions (the generic battery needs a list)."""
    body, _ = sc.split_body(it.question)
    ents = list(dict.fromkeys(w for w in sc.words(it.question) if w in sc._ENT))
    if len(ents) < 2:
        return {}
    men = [e for e in ents if sc._count(body, e)]
    out: dict[str, Pred] = {"F:most_mentioned": sc._pick(ents, lambda o: sc._count(body, o), "max"), "F:least_mentioned": sc._pick(ents, lambda o: sc._count(body, o), "min"),
                            "F:alphabetical_first": [sorted(ents)[0]], "F:alphabetical_last": [sorted(ents)[-1]]}
    if men:
        out["F:first_mentioned"] = sc._pick(men, lambda o: sc._first(body, o), "min")
        out["F:last_mentioned"] = sc._pick(men, lambda o: sc._last(body, o), "max")
    return out


def _cell(items: Sequence[Item], pb: Sequence[dict[str, Pred]], name: str, idx: Sequence[int]) -> dict[str, Any] | None:
    fired = [i for i in idx if sc._valid(pb[i].get(name), items[i]) not in (None, [])]
    if not fired:
        return None
    acc = sum(sc.credit(pb[i][name], items[i]) or 0.0 for i in fired) / len(fired)
    closed = all(items[i].k for i in fired)
    if closed:
        ch = sum(1.0 / items[i].k for i in fired) / len(fired)  # type: ignore[operator]
        aa = [sc.anti_credit(pb[i][name], items[i]) or 0.0 for i in fired]
        anti = sum(aa) / len(aa) - ch
        dep = acc - ch
        gain = max(dep, anti)
        se = math.sqrt(max(ch * (1 - ch), 1e-9) / len(fired))
        base_rate = ch
    else:  # open answers: baseline = the share of the commonest answer among all the level's items
        cnt = Counter(items[i].answer for i in idx)
        base_rate = cnt.most_common(1)[0][1] / len(idx)
        dep, anti = acc, None
        gain = acc - base_rate
        se = math.sqrt(max(base_rate * (1 - base_rate), 1e-9) / len(fired))
    rate = len(fired) / len(idx)
    return {"n": len(idx), "fires": len(fired), "fire_rate": round(rate, 4), "accuracy": round(acc, 4), "baseline": round(base_rate, 4), "departure": round(dep, 4), "anti_departure": None if anti is None else round(anti, 4),
            "gain": round(gain, 4), "effective_gain": round(gain * rate, 4), "z": round(gain / se, 2), "open": not closed}


def measure(lin: Lineage, per_level: int = 700, levels: Sequence[int] = ALL_LEVELS, label: str = "rev4-measure", items: Sequence[Item] | None = None) -> dict[str, Any]:
    items = list(items) if items is not None else lg.sample_items(lin, per_level, levels, label=label)
    keys = Counter(it.answer for it in items)
    const_key = keys.most_common(1)[0][0]
    pb = [item_preds(it, const_key) for it in items]
    names = sorted({n for p in pb for n in p})
    by_level = {lv: [i for i, it in enumerate(items) if it.level == lv] for lv in sorted({it.level for it in items})}
    cells: dict[str, dict[str, Any]] = {}
    for n in names:
        row: dict[str, Any] = {}
        pooled = _cell(items, pb, n, range(len(items)))
        if pooled:
            row["all"] = pooled
        for lv, idx in by_level.items():
            c = _cell(items, pb, n, idx)
            if c:
                row[str(lv)] = c
        cells[n] = row
    return {"id": lin.id, "n_items": len(items), "open_answers": all(it.k is None for it in items), "top_answers": keys.most_common(3), "heuristics": cells}


def worst(res: dict[str, Any], min_fires: int = 100, key: str = "effective_gain") -> dict[str, Any]:
    """Per level, the heuristic with the largest ``key`` (default the EFFECTIVE gain: the gain on the items it fires on times the share of items it fires on, i.e. what a solver gains by using the
    heuristic where it fires and guessing elsewhere) among cells with at least ``min_fires`` firings; and the worst pooled one."""
    out: dict[str, Any] = {"per_level": {}, "pooled": None, "procedure_cells": []}
    best_pool = None
    for n, row in res["heuristics"].items():
        for lv, c in row.items():
            if c["fires"] < min_fires:
                continue
            if c["accuracy"] >= 0.99 and c["fire_rate"] >= 0.9 and not c["open"] or (c["open"] and c["accuracy"] >= 0.99 and c["fire_rate"] >= 0.9):
                # right on (essentially) every item it is asked about: at this level it IS the solution (the algorithm itself, or its exact special case), not a shortcut
                out["procedure_cells"].append({"heuristic": n, "level": lv, "accuracy": c["accuracy"], "fire_rate": c["fire_rate"]})
                continue
            if lv == "all":
                if best_pool is None or c[key] > best_pool[key]:
                    best_pool = {"heuristic": n, **c}
            elif lv not in out["per_level"] or c[key] > out["per_level"][lv][key]:
                out["per_level"][lv] = {"heuristic": n, **c}
    out["pooled"] = best_pool
    return out


def table(results: dict[str, dict[str, Any]], title: str, min_fires: int = 100) -> str:
    lines = [f"# {title}", "", "Gain = the better of following a heuristic and avoiding it (accuracy minus chance, or minus the commonest-answer share for open answers), on the items it fires on. EFFECTIVE gain = gain x the share",
             "of items the heuristic fires on (what a solver gains by using it where it fires and guessing elsewhere); the worst heuristic is picked by effective gain, per level.",
             f"Cells with fewer than {min_fires} firings are not shown; a cell where the heuristic is right on at least 99 % of the items it fires on and fires on at least 90 % of all items is the SOLUTION at that level (its exact special case: for example "
             "the two-step ancestor when the asked term is grandparent) and is listed under `procedure` instead of being picked as the worst shortcut. MEASURED, not thresholded. `z` is gain over its standard error (about 3 or more is not noise; with about 40 heuristics x 7 levels a few cells reach 3 by chance).", "",
             "| shape | status | answers | worst cell: level, heuristic, effective gain (gain, z), accuracy vs baseline | per level 0..6: worst effective gain | procedure cells (excluded) |", "|---|---|---|---|---|---|"]
    for lid in sorted(results):
        res = results[lid]
        w = worst(res, min_fires)
        pl = w["per_level"]
        status = "rev4" if lid.endswith("_r4") else "unchanged"
        if not pl:
            lines.append(f"| {lid} | {status} | {'open' if res['open_answers'] else 'closed'} | no heuristic fires enough | | |")
            continue
        wc_lv = max(pl, key=lambda x: pl[x]["effective_gain"])
        wc = pl[wc_lv]
        per = " / ".join(f"{pl[str(lv)]['effective_gain']:+.2f}" if str(lv) in pl else "-" for lv in range(7))
        proc = "; ".join(f"{c['heuristic']} L{c['level']}" for c in w["procedure_cells"] if c["level"] != "all") or "-"
        lines.append(f"| {lid} | {status} | {'open' if res['open_answers'] else 'closed'} | L{wc_lv}, {wc['heuristic']}, {wc['effective_gain']:+.3f} ({wc['gain']:+.3f}, z {wc['z']}), {wc['accuracy']} vs {wc['baseline']} | {per} | {proc} |")
    return "\n".join(lines) + "\n"


def run_one(args: tuple[str, int, str]) -> tuple[str, dict[str, Any]]:  # for multiprocessing
    lid, per_level, label = args
    from studies.m0 import lineages_r1_clusters_v2 as v2

    lin = next(x for x in v2.all_lineages_v2() if x.id == lid)
    return lid, measure(lin, per_level, label=label)


from studies.m0 import r1_rev4_extra  # noqa: E402,F401,I001  (registers EXTRA; imported last because it needs EXTRA from this module)
