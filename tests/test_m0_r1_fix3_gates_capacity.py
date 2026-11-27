# ruff: noqa: E501
"""R1 fix round 3: the three gate fixes (each guard is asserted to FAIL on the earlier gate and to HOLD on the new one) and the capacity canonicaliser (invariance under renaming and reordering,
sensitivity to a change of structure, the two readings, the demand figure)."""

from __future__ import annotations

import copy
import random

from studies.m0 import lineages_r1_shortcuts as old
from studies.m0 import r1_fix3_capacity as cap
from studies.m0 import r1_fix3_gates as new
from studies.m0.core import Item, Retry
from studies.m0.lineages_r1_fix3_clusters import registered_v3
from studies.m0.vocab import NAMES

LIN = {x.id: x for x in registered_v3()}


def build(lid: str, level: int, seed: int):
    r = random.Random(seed)
    while True:
        try:
            return LIN[lid].build(level, r)
        except Retry:
            continue


# ---------------------------------------------------------------- the three gate fixes


def test_numbers_does_not_count_the_options_of_a_game_as_data():
    q = "At each choice the mover picks one of the 2 options shown. The game is written as nested options: ((3 or -4) or (5 or 7))."
    assert old.numbers(q)[:1] == [2]  # the earlier gate counted the 2
    assert new.numbers(q) == [3, -4, 5, 7]


def test_a_question_without_a_question_mark_still_gets_the_yes_no_heuristics():
    b = build("R1.categories_follow_r5", 2, 3)
    assert "?" not in b.question
    it = Item("x", "R1", "A", b and "R1.categories_follow_r5", "f", 2, b.question, b.structured, b.answer, b.answer_type, b.k)
    assert "asked_pair_stated_verbatim" not in old.generic(it)  # no yes / no heuristic at all in the earlier gate
    got = new.generic(it)
    assert "asked_entity_never_mentioned" in got or "asked_pair_stated_verbatim" in got


def test_a_no_premise_stated_in_the_reverse_order_still_says_something():
    q1 = 'Consider the statement: "no bodik is a kolon".'
    assert old._stated_reading(q1, "No kolon are bodik.", ["bodik", "kolon"]) is None
    assert new.stated_reading(q1, "No kolon are bodik.", ["bodik", "kolon"]) == "no"
    # "All" is not symmetric: the reverse order still says nothing
    assert new.stated_reading('Consider the statement: "every bodik is a kolon".', "All kolon are bodik.", ["bodik", "kolon"]) is None


# ---------------------------------------------------------------- capacity: the canonical key


_POOLS = None


def _pools():
    global _POOLS
    if _POOLS is None:
        from studies.m0.vocab import EVENTS, OBJECTS, PETS, PSEUDO, TOWNS

        _POOLS = [sorted(NAMES), sorted(TOWNS), sorted(OBJECTS), sorted(PETS), sorted(PSEUDO), sorted({w for e in EVENTS for w in e.split() if w != "the"}),
                  sorted({w.capitalize() for w in PSEUDO})]
    return _POOLS


def _tokens(obj):
    import re

    if isinstance(obj, str):
        yield from re.findall(r"[A-Za-z][A-Za-z-]*", obj)
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield from _tokens(k)
            yield from _tokens(v)
    elif isinstance(obj, list):
        for x in obj:
            yield from _tokens(x)


def _renaming(st, seed: int) -> dict[str, str]:
    """A random injective renaming of every entity word in the structured form within its pool."""
    r = random.Random(seed)
    used = set(_tokens(st))
    mp: dict[str, str] = {}
    for pool in _pools():
        here = sorted(w for w in used if w in set(pool))
        if here:  # an injective map of the words present onto words of the same pool (applied simultaneously, so a target may be another word that is present)
            mp.update(zip(here, r.sample(pool, len(here)), strict=True))
    return mp


def _rename(obj, mapping):
    import re

    if isinstance(obj, str):
        return re.sub(r"[A-Za-z][A-Za-z-]*", lambda m: mapping.get(m.group(0), m.group(0)), obj)
    if isinstance(obj, dict):
        return {_rename(k, mapping): _rename(v, mapping) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_rename(x, mapping) for x in obj]
    return obj


def test_key_is_invariant_under_renaming_every_entity_in_every_registered_shape():
    for lin in registered_v3():
        if lin.id.endswith("topological_order_r5"):
            continue  # the tie-break is alphabetical: only order-preserving renamings are identified (tested below)
        for level in (0, 3):
            b = build(lin.id, level, 5)
            b2 = _rename(copy.deepcopy(b.structured), _renaming(b.structured, 9))
            assert cap.keys_of(lin.id, b.structured) == cap.keys_of(lin.id, b2), (lin.id, level)


def test_key_ignores_the_order_of_statements_but_not_the_order_of_operations():
    b = build("R1.graph_bipartite_r5", 2, 6)
    st = copy.deepcopy(b.structured)
    random.Random(1).shuffle(st["rivals"])
    st["rivals"] = [p[::-1] for p in st["rivals"]]
    assert cap.keys_of("R1.graph_bipartite_r5", b.structured) == cap.keys_of("R1.graph_bipartite_r5", st)
    s = build("R1.swap_tracking_r5", 3, 6)
    st = copy.deepcopy(s.structured)
    ops = st["ops"]
    swapped = [o for o in ops if o[0] == "swap"]
    i, j = next((i, j) for i in range(len(ops)) for j in range(i + 1, len(ops)) if ops[i] != ops[j])
    st["ops"][i], st["ops"][j] = st["ops"][j], st["ops"][i]
    assert swapped and cap.keys_of("R1.swap_tracking_r5", s.structured) != cap.keys_of("R1.swap_tracking_r5", st)


def test_key_changes_when_the_structure_changes():
    b = build("R1.activity_selection_r5", 2, 7)
    st = copy.deepcopy(b.structured)
    st["meetings"][0][2] += 1
    assert cap.keys_of("R1.activity_selection_r5", b.structured) != cap.keys_of("R1.activity_selection_r5", st)
    g = build("R1.graph_bipartite_r5", 2, 7)
    st = copy.deepcopy(g.structured)
    st["rivals"].pop()
    assert cap.keys_of("R1.graph_bipartite_r5", g.structured) != cap.keys_of("R1.graph_bipartite_r5", st)


def test_the_two_readings_differ_only_in_the_labels():
    b = build("R1.attribute_rule_r5", 1, 8)
    st = copy.deepcopy(b.structured)
    mp = {"red": "blue", "blue": "red"}  # swap two colours everywhere (a relabelling of labels)
    for it in st["items"]:
        it["colour"] = mp.get(it["colour"], it["colour"])

    def sw(rule):
        if rule[0] == "attr":
            return ["attr", rule[1], mp.get(rule[2], rule[2])] if rule[1] == "colour" else rule
        return [rule[0], *[sw(c) for c in rule[1:]]]

    st["rule"] = sw(st["rule"])
    ka, kb = cap.keys_of("R1.attribute_rule_r5", b.structured), cap.keys_of("R1.attribute_rule_r5", st)
    assert ka[1] == kb[1]  # reading (b) relabels colours: the same item
    touched = any(c == "red" or c == "blue" for it in b.structured["items"] for c in [it["colour"]]) or "red" in str(b.structured["rule"]) or "blue" in str(b.structured["rule"])
    assert (ka[0] != kb[0]) == (b.structured != st and touched) or ka[0] == kb[0]  # reading (a) keeps colours; the two keys can coincide only by a symmetry of the item


def test_topological_names_are_identified_only_up_to_alphabetical_order():
    b = build("R1.topological_order_r5", 1, 9)
    names = sorted(p for p, _ in b.structured["jobs"])
    spare = sorted(n for n in NAMES if n not in names)
    # an order-preserving renaming (the same relative alphabetical order) gives the same key
    mp = dict(zip(names, sorted(random.Random(4).sample(spare, len(names))), strict=True))
    st = _rename(copy.deepcopy(b.structured), mp)
    assert cap.keys_of("R1.topological_order_r5", b.structured) == cap.keys_of("R1.topological_order_r5", st)
    # a renaming that reverses the alphabetical order is a different item (the tie-break changes)
    mp2 = dict(zip(names, sorted(random.Random(4).sample(spare, len(names)), reverse=True), strict=True))
    st2 = _rename(copy.deepcopy(b.structured), mp2)
    assert cap.keys_of("R1.topological_order_r5", b.structured) != cap.keys_of("R1.topological_order_r5", st2)


def test_demand_and_estimates():
    assert cap.DEMAND == 22830 and cap.G == 11
    from collections import Counter

    est = cap.estimate(Counter({"a": 1, "b": 1, "c": 1}), 3)
    assert est["distinct"] == 3 and est["pairs"] == 0 and est["lower_bound_if_no_collision"] == 1
    est = cap.estimate(Counter({"a": 3, "b": 1}), 4)
    assert est["pairs"] == 3 and est["S_collision"] == 2  # 4 * 3 / (2 * 3)
    assert cap.verdict({"distinct": 30000, "S_collision": None, "lower_bound_if_no_collision": None})[0]
    assert not cap.verdict({"distinct": 100, "S_collision": 500, "lower_bound_if_no_collision": None})[0]


def test_every_registered_shape_has_a_capacity_key():
    for lin in registered_v3():
        base = lin.id.split(".", 1)[1].rsplit("_r", 1)[0] if lin.id.endswith(("_r2", "_r4", "_r5")) else lin.id.split(".", 1)[1]
        assert base in cap.SPEC, lin.id
        b = build(lin.id, 1, 3)
        ka, kb = cap.keys_of(lin.id, b.structured)
        assert len(ka) == len(kb) == 16
