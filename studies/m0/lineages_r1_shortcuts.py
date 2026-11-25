# ruff: noqa: E501
"""The shortcut gate for R1 lineages (lineage repair, ruling C): a fixed battery of trivial heuristics, scored on 2,000 items per lineage
(400 at each of the five core levels), recorded against the chance level mean(1/k).

MEASURED, NOT THRESHOLDED: no value is registered. A heuristic that fires only sometimes is scored as "its prediction when it fires, a uniform random
guess (credit 1/k) when it does not"; ties between predicted candidates split the credit. Open answers (k = None) have chance 0.

Generic battery (reads the question TEXT only): constant most-frequent key; for closed name answers listed after "Choose from": first mentioned in the body,
last mentioned, most mentioned, least mentioned (zero counts), never the first word of a sentence, alphabetically first, alphabetically last; for yes/no answers:
"the asked pair is stated verbatim" (polarity from the sentence), "an asked entity is never mentioned"; for numeric answers: the largest, the smallest and the last
number in the body. Lineage-specific heuristics (``SPECIFIC``) read the structured form, which a text-level shortcut could equally compute; they implement the
shortcuts named by the pilot audit (parentless root, nearest neighbour, last joiner, vetoing no, never-toggled lamp, ...) and the obvious ones for the other lineages.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Callable, Sequence
from typing import Any

from studies.m0.core import ALL_LEVELS, CORE_LEVELS, Item, Lineage
from studies.m0.vocab import NAMES, OBJECTS, PSEUDO, TOWNS

Pred = str | list[str] | None
_ENT = set(NAMES) | set(TOWNS) | set(OBJECTS) | set(PSEUDO) | {w.capitalize() for w in PSEUDO}
_WORD = re.compile(r"[A-Za-z']+")
_NEG = {"different", "not", "never", "rivals", "cannot", "no"}


# ---------------------------------------------------------------- text helpers


def split_body(q: str) -> tuple[str, str]:
    sents = re.split(r"(?<=[.?!])\s+", q)
    qi = max((i for i, s in enumerate(sents) if "?" in s), default=len(sents) - 1)
    return " ".join(sents[:qi]), " ".join(sents[qi:])


def parse_options(q: str) -> list[str] | None:
    m = re.search(r"Choose from (.+?)\.(?:\s|$)", q)
    if not m:
        return None
    parts = m.group(1).split(", ")
    last = parts[-1].rsplit(" and ", 1)
    return [*parts[:-1], *last]


def _count(body: str, o: str) -> int:
    return len(re.findall(r"(?<![A-Za-z'])" + re.escape(o) + r"(?![A-Za-z'])", body))


def _last(body: str, o: str) -> int:
    ms = list(re.finditer(r"(?<![A-Za-z'])" + re.escape(o) + r"(?![A-Za-z'])", body))
    return ms[-1].start() if ms else -1


def _first(body: str, o: str) -> int:
    m = re.search(r"(?<![A-Za-z'])" + re.escape(o) + r"(?![A-Za-z'])", body)
    return m.start() if m else -1


def _pick(cands: list[str], key: Callable[[str], float], best: str) -> list[str]:
    vals = {c: key(c) for c in cands}
    tgt = max(vals.values()) if best == "max" else min(vals.values())
    return [c for c in cands if vals[c] == tgt]


def generic(it: Item) -> dict[str, Pred]:
    body, tail = split_body(it.question)
    out: dict[str, Pred] = {}
    opts = parse_options(it.question)
    if opts and it.answer_type in ("name", "text", "word", "letter"):
        men = [o for o in opts if _count(body, o)]
        if men:
            out["first_mentioned"] = _pick(men, lambda o: _first(body, o), "min")
            out["last_mentioned"] = _pick(men, lambda o: _last(body, o), "max")
        out["most_mentioned"] = _pick(opts, lambda o: _count(body, o), "max")
        out["least_mentioned"] = _pick(opts, lambda o: _count(body, o), "min")
        starts = [s for s in re.split(r"(?<=[.?!])\s+", body) if s]
        never = [o for o in opts if not any(s.startswith(o) for s in starts)]
        out["never_sentence_subject"] = never or None
        out["alphabetical_first"] = [sorted(opts)[0]]
        out["alphabetical_last"] = [sorted(opts)[-1]]
    if it.answer_type in ("yn", "ynu"):
        q1 = next((s for s in re.split(r"(?<=[.?!])\s+", tail) if "?" in s), tail)
        ents = [w for w in _WORD.findall(q1) if w in _ENT]
        ents = list(dict.fromkeys(ents))[:2]
        if len(ents) == 2:
            hit = [s for s in re.split(r"(?<=[.?!])\s+", body) if ents[0] in s and ents[1] in s]
            out["asked_pair_stated_verbatim"] = (("no" if any(w.lower() in _NEG for w in _WORD.findall(hit[0])) else "yes") if hit else None)
            out["asked_entity_never_mentioned"] = ("cannot be determined" if it.answer_type == "ynu" else "no") if any(e not in body for e in ents) else None
    if it.answer_type == "number":
        nums = [int(x) for x in re.findall(r"\d+", body)]
        if nums:
            out["largest_number"] = str(max(nums))
            out["smallest_number"] = str(min(nums))
            out["last_number"] = str(nums[-1])
    return out


# ---------------------------------------------------------------- lineage-specific heuristics (structured form)


def _parentless(it: Item) -> Pred:
    s = it.structured
    return [p for p in s["people"] if p not in s["parent"]]


def _most_children(it: Item) -> Pred:
    s = it.structured
    cnt = Counter(s["parent"].values())
    cands = s.get("candidates") or s["people"]
    top = max(cnt.get(p, 0) for p in cands)
    return [p for p in cands if cnt.get(p, 0) == top]


def _stated_pair(it: Item) -> Pred:
    s = it.structured
    p = {s["x"], s["y"]}
    if any({a, b} == p for a, b in s["same"]):
        return "yes"
    if any({a, b} == p for a, b in s["different"]):
        return "no"
    return None


def _bracket_old_runner(it: Item) -> Pred:
    s = it.structured
    pl = s["players"]
    if it.structured["ask"][0] != "runner_up":
        return None
    half = len(pl) // 2
    top = max(pl, key=lambda x: x[1])[0]
    other = pl[half:] if top in [p[0] for p in pl[:half]] else pl[:half]
    return max(other, key=lambda x: x[1])[0]


def _bracket_old_champion(it: Item) -> Pred:
    s = it.structured
    return max(s["players"], key=lambda x: x[1])[0] if s["ask"][0] == "beaten_by" else None


def _bracket_wins(it: Item) -> Pred:
    s = it.structured
    w = Counter(a for a, _ in s["results"])
    order = sorted(s["players"], key=lambda p: -w.get(p, 0))
    if s["ask"][0] == "runner_up":
        return [order[1]]
    return [order[0]] if order[0] != s["ask"][1] else [order[1]]


def _queue_old(it: Item) -> Pred:
    s = it.structured
    kind = "join" if s["ask"] == "back" else "cut"
    names = [o[1] for o in s["ops"] if o[0] == kind]
    return names[-1] if names else None


def _queue_initial(it: Item) -> Pred:
    s = it.structured
    j = s["ask"][1] - 1
    return s["line"][j] if j < len(s["line"]) else None


def _def_agree(it: Item) -> Pred:
    s = it.structured
    signs = {x[2] for x in s["rules"] if x[1] == s["verb"]}
    return ("yes" if True in signs else "no") if len(signs) == 1 else None


def _def_own(it: Item) -> Pred:
    s = it.structured
    own = [x for x in s["rules"] if x[1] == s["verb"] and x[0] == s["chain"][0]]
    return ("yes" if own[0][2] else "no") if own else None


def _def_majority(it: Item) -> Pred:
    s = it.structured
    sg = [x[2] for x in s["rules"] if x[1] == s["verb"]]
    return None if sum(sg) * 2 == len(sg) else ("yes" if sum(sg) * 2 > len(sg) else "no")


def _def_last_listed(it: Item) -> Pred:
    s = it.structured
    sg = [x[2] for x in s["rules"] if x[1] == s["verb"]]
    return ("yes" if sg[-1] else "no") if sg else None


def _def_largest_group(it: Item) -> Pred:  # the rule of the group furthest from the member (the opposite of the stated priority rule)
    s = it.structured
    rs = sorted((s["chain"].index(x[0]), x[2]) for x in s["rules"] if x[1] == s["verb"])
    return ("yes" if rs[-1][1] else "no") if rs else None


def _veto_no(it: Item) -> Pred:
    s = it.structured
    return "no" if any(s["votes"].get(v) == "no" for v in s.get("vetoes", [])) else None


def _yes_majority(it: Item) -> Pred:
    s = it.structured
    y = sum(1 for v in s["votes"].values() if v == "yes")
    n = sum(1 for v in s["votes"].values() if v == "no")
    return None if y == n else ("yes" if y > n else "no")


def _lamp_untoggled(it: Item) -> Pred:
    s = it.structured
    tog = sum(1 for c in s["presses"] for lamp in s["switches"][c] if lamp == s["ask"])
    return None if tog else ("yes" if s["initial"][s["ask"] - 1] else "no")


def _lamp_initial(it: Item) -> Pred:
    s = it.structured
    return "yes" if s["initial"][s["ask"] - 1] else "no"


def _greedy(it: Item) -> Pred:
    s = it.structured
    near = min((r for r in s["roads"] if s["start"] in r[:2]), key=lambda r: r[2], default=None)
    if near is None:
        return None
    return [near[1] if near[0] == s["start"] else near[0]]


def _direct_road(it: Item) -> Pred:
    s = it.structured
    for a, b, w in s["roads"]:
        if {a, b} == {s["start"], s["end"]}:
            return str(w)
    return None


def _stack_last_onto(it: Item) -> Pred:
    s = it.structured
    moved = None
    st = {p: list(v) for p, v in s["initial"].items()}
    for op in s["ops"]:
        if op[0] == "move":
            blk = st[op[1]].pop()
            st[op[2]].append(blk)
            if op[2] == s["ask"]:
                moved = blk
        else:
            st[op[1]].reverse()
    return moved


def _stack_initial_top(it: Item) -> Pred:
    s = it.structured
    v = s["initial"][s["ask"]]
    return v[-1] if v else None


def _start_cell(it: Item) -> Pred:
    s = it.structured
    return s["grid"][s["start"][0]][s["start"][1]]


def _largest_offset(it: Item) -> Pred:
    s = it.structured
    top = max(s["facts"], key=lambda f: f[2])
    return [x for x in (top[0], top[3]) if x != s["anchor"]]


def _longest_job(it: Item) -> Pred:
    s = it.structured
    top = max(j[1] for j in s["jobs"])
    return [j[0] for j in s["jobs"] if j[1] == top]


def _richest_start(it: Item) -> Pred:
    s = it.structured
    vals = s["start"]
    t = max(vals.values()) if s["ask"] == "most" else min(vals.values())
    return [p for p, v in vals.items() if v == t]


def _own_item(it: Item) -> Pred:
    s = it.structured
    return s["hold"][s["who"]]


def _start_dir(it: Item) -> Pred:
    return it.structured["start"]


def _anchor_day(it: Item) -> Pred:
    return it.structured["anchor"][1]


def _most_wins(it: Item) -> Pred:
    s = it.structured
    w = Counter(a for a, _ in s["results"])
    vals = [w.get(p, 0) for p in s["players"]]
    t = max(vals) if s["ask"] == "most" else min(vals)
    return [p for p in s["players"] if w.get(p, 0) == t]



def _jth_alphabetical(it: Item) -> Pred:
    s = it.structured
    return [sorted(j[0] for j in s["jobs"])[s["day"] - 1]]


def _greedy_by_start(it: Item) -> Pred:
    cnt, last = 0, -1
    for _, a, b in sorted(it.structured["meetings"], key=lambda m: (m[1], m[2])):
        if a >= last:
            cnt += 1
            last = b
    return str(cnt)


def _smallest_roads(it: Item) -> Pred:
    s = it.structured
    return str(sum(sorted(w for _, _, w in s["roads"])[: len(s["towns"]) - 1]))


def _plurality_winner(it: Item) -> Pred:
    cnt: Counter[str] = Counter()
    for c, rk in it.structured["ballots"]:
        cnt[rk[0]] += c
    top = max(cnt.values())
    return [k for k, v in cnt.items() if v == top]


def _first_choice(it: Item) -> Pred:
    s = it.structured
    return s["prefs_p"][s["ask"]][0]


def _odd_total(it: Item) -> Pred:
    return "first" if sum(it.structured["piles"]) % 2 else "second"


SPECIFIC: dict[str, dict[str, Callable[[Item], Pred]]] = {
    "R1.topological_order": {"jth_alphabetical": _jth_alphabetical},
    "R1.activity_selection": {"greedy_by_start": _greedy_by_start},
    "R1.mst_cost": {"smallest_n_minus_1_roads": _smallest_roads},
    "R1.instant_runoff": {"plurality_winner": _plurality_winner},
    "R1.stable_matching": {"first_choice": _first_choice},
    "R1.nim_xor": {"odd_total_means_first": _odd_total},
    "R1.kinship_descendants": {"parentless_person": _parentless, "most_children": _most_children},
    "R1.kinship_descendants_r2": {"parentless_person": _parentless, "most_children": _most_children},
    "R1.kinship_ancestor": {"parentless_person": _parentless},
    "R1.kinship_ancestor_r2": {"parentless_person": _parentless},
    "R1.equivalence_classes": {"stated_pair": _stated_pair},
    "R1.equivalence_classes_r2": {"stated_pair": _stated_pair},
    "R1.elimination_bracket": {"runner_up_is_best_of_other_half": _bracket_old_runner, "knocked_out_by_top_rating": _bracket_old_champion},
    "R1.elimination_bracket_r2": {"most_wins_logic": _bracket_wins},
    "R1.containers_queue_line": {"last_joiner_or_last_cutter": _queue_old},
    "R1.containers_queue_line_r2": {"initial_line_position": _queue_initial},
    "R1.categories_default_exceptions": {"all_rules_agree": _def_agree, "member_group_rule": _def_own, "majority_sign": _def_majority, "last_listed": _def_last_listed},
    "R1.categories_default_exceptions_r2": {"all_rules_agree": _def_agree, "member_group_rule": _def_own, "majority_sign": _def_majority, "last_listed": _def_last_listed, "least_specific_rule": _def_largest_group},
    "R1.conditional_threshold_rule": {"veto_no_means_no": _veto_no},
    "R1.conditional_threshold_rule_r2": {"yes_count_majority": _yes_majority},
    "R1.boolean_lights": {"never_toggled_means_initial": _lamp_untoggled, "initial_state": _lamp_initial},
    "R1.boolean_lights_r2": {"never_toggled_means_initial": _lamp_untoggled, "initial_state": _lamp_initial},
    "R1.graph_shortest_route": {"nearest_neighbour_of_start": _greedy},
    "R1.graph_shortest_route_r2": {"direct_road_length": _direct_road},
    "R1.containers_stack_piles": {"last_block_moved_onto_asked": _stack_last_onto, "initial_top": _stack_initial_top},
    "R1.containers_stack_piles_r2": {"last_block_moved_onto_asked": _stack_last_onto, "initial_top": _stack_initial_top},
    "R1.spatial_grid_walk": {"start_cell": _start_cell},
    "R1.spatial_grid_walk_r2": {"start_cell": _start_cell},
    "R1.spatial_relative_directions": {"endpoint_of_largest_offset": _largest_offset},
    "R1.temporal_critical_path": {"longest_job": _longest_job},
    "R1.tracking_accounts": {"richest_or_poorest_at_start": _richest_start},
    "R1.swap_tracking": {"own_initial_item": _own_item},
    "R1.compass_turns": {"start_direction": _start_dir},
    "R1.temporal_weekday_shift": {"anchor_weekday": _anchor_day},
}


# ---------------------------------------------------------------- scoring


def credit(pred: Pred, it: Item) -> float | None:
    """Expected credit of one prediction: ties split, no prediction = a random guess (credit 1/k; 0 for open answers)."""
    chance = (1.0 / it.k) if it.k else 0.0
    if pred is None:
        return chance
    if isinstance(pred, str):
        return 1.0 if pred.lower() == it.answer.lower() else 0.0
    if not pred:
        return chance
    return (1.0 / len(pred)) if it.answer in pred else 0.0


def run_battery(lin: Lineage, items: Sequence[Item]) -> dict[str, Any]:
    chance = sum((1.0 / it.k) if it.k else 0.0 for it in items) / len(items)
    keys = Counter(it.answer for it in items)
    rows: list[dict[str, Any]] = []
    per: dict[str, dict[int, list[float]]] = {}
    fired: dict[str, list[float]] = {}
    const_key = keys.most_common(1)[0][0]
    spec = SPECIFIC.get(lin.id, {})
    for it in items:
        preds: dict[str, Pred] = {"constant_most_frequent_key": const_key, **generic(it)}
        for n, fn in spec.items():
            preds[n] = fn(it)
        for n, p in preds.items():
            c = credit(p, it)
            per.setdefault(n, {}).setdefault(it.level, []).append(c if c is not None else 0.0)
            if p is not None and p != []:
                fired.setdefault(n, []).append(credit(p, it) or 0.0)
    for n, lv in per.items():
        allc = [x for v in lv.values() for x in v]
        acc = sum(allc) / len(allc)
        bylevel = {level: (sum(v) / len(v) - (sum((1.0 / it.k) if it.k else 0.0 for it in items if it.level == level) / max(1, sum(1 for it in items if it.level == level)))) for level, v in lv.items() if len(v) >= 100}
        rows.append({"heuristic": n, "accuracy": round(acc, 4), "excess_over_chance": round(acc - chance, 4), "fires": len(fired.get(n, [])), "accuracy_when_fires": round(sum(fired[n]) / len(fired[n]), 4) if fired.get(n) else None,
                     "worst_level": max(bylevel, key=lambda x: bylevel[x]) if bylevel else None, "worst_level_excess": round(max(bylevel.values()), 4) if bylevel else None})
    rows.sort(key=lambda r: -r["excess_over_chance"])
    return {"id": lin.id, "n_items": len(items), "chance": round(chance, 4), "k_mean": round(sum(it.k for it in items if it.k) / max(1, sum(1 for it in items if it.k)), 2), "worst": rows[0], "heuristics": rows}


def shortcut_gate(lins: Sequence[Lineage], per_level: int = 400, levels: Sequence[int] = CORE_LEVELS) -> dict[str, Any]:
    from studies.m0.lineage_gates import sample_items

    out = {}
    for lin in lins:
        out[lin.id] = run_battery(lin, sample_items(lin, per_level, levels, label="shortcuts"))
    return out


def markdown(results: dict[str, Any], superseded: Sequence[str] = ()) -> str:
    rows = ["| id | chance | worst heuristic | accuracy | excess over chance | fires | worst level (excess) | note |", "|---|---|---|---|---|---|---|---|"]
    for lid, r in sorted(results.items()):
        w = r["worst"]
        rows.append(f"| {lid} | {r['chance']} | {w['heuristic']} | {w['accuracy']} | {w['excess_over_chance']} | {w['fires']} | {w['worst_level']} ({w['worst_level_excess']}) | {'superseded' if lid in superseded else ''} |")
    return "\n".join(rows) + "\n"


ALL = ALL_LEVELS
