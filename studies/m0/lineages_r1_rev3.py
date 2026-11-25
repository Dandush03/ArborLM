# ruff: noqa: E501
"""R1 retuned revisions (ruling 2 of 2025-11-25): the redraw probabilities of the generator-side shortcut repair are retuned so that each repaired heuristic sits near
chance on BOTH sides (a heuristic pushed clearly below chance is as exploitable as one above it).

Each shape here calls the builder of the earlier revision with different redraw probabilities (``anti_override``); nothing else changes. The probabilities were
fitted by ``experiments``-style calibration (``lineage_gates.calibrate_anti``) on test-seed items and are fixed constants here; the measured before/after band is in
``studies/m0/manifests/r1_two_sided.json`` and ``NOTES_LINEAGE_REPAIR.md``. THIS REPAIR CONDITIONS THE ITEM DISTRIBUTION ON A HEURISTIC'S OUTCOME: items that a named
heuristic answers correctly are drawn again with the probability below, so the items kept are not a plain sample of the lineage's rule. The band is a measurement, not a
registered threshold.
"""

from __future__ import annotations

import random

from studies.m0.core import Built, Item, Retry
from studies.m0.lineages_r1_common import pilot
from studies.m0.lineages_r1_new2 import instant_runoff, stable_matching, topological_order
from studies.m0.lineages_r1_rev2 import (
    conditional_threshold_rule_r2,
    containers_stack_piles_r2,
    elimination_bracket_r2,
    kinship_ancestor_r2,
    kinship_descendants_r2,
)
from studies.m0.lineages_r1_shortcuts import ANTI_P, anti_override, credit, generic, spec_for
from studies.m0.vocab import NAMES, PSEUDO

# redraw probabilities per heuristic, fitted by iterating generate / measure / adjust on test-seed items (24 rounds of 1,500, mean of the last 8; NOTES_LINEAGE_REPAIR.md)
P: dict[str, dict[str, float]] = {
    "R1.kinship_descendants_r2": {
        "most_children": 0.829,
        "most_mentioned": 0.829,
        "first_mentioned": 0.64
    },
    "R1.kinship_ancestor_r2": {
        "most_mentioned": 0.785
    },
    "R1.elimination_bracket_r2": {
        "most_wins_logic": 0.649
    },
    "R1.conditional_threshold_rule_r2": {
        "yes_count_majority": 0.873
    },
    "R1.containers_stack_piles_r2": {
        "last_block_moved_onto_asked": 0.87,
        "initial_top": 0.36
    },
    "R1.topological_order": {
        "jth_alphabetical": 0.566
    },
    "R1.instant_runoff": {
        "plurality_winner": 0.921
    },
    "R1.stable_matching": {
        "first_choice": 0.757,
        "first_mentioned": 0.0
    }
}


def _anti(b: Built, lid: str, r: random.Random, names: tuple[str, ...], p_reject: float = 0.5, key: str | None = None) -> Built:
    it = Item("x", "R1", "A", lid, "f", 1, b.question, b.structured, b.answer, b.answer_type, b.k)
    fns = spec_for(lid)
    g = generic(it)
    pk = P.get(key or lid, {})
    for n in names:
        p = fns[n](it) if n in fns else g.get(n)
        if p not in (None, []) and credit(p, it) >= 0.5 and r.random() < pk.get(n, ANTI_P.get(key or lid, {}).get(n, p_reject)):
            raise Retry
    return b


def _wrap(base, lid: str, level: int, r: random.Random, shape: str = "", extra: tuple[str, ...] = ()) -> Built:  # type: ignore[no-untyped-def]
    """Call the earlier revision with the retuned probabilities; ``extra`` names heuristics that the earlier builder does not check and that are redrawn here."""
    with anti_override(lid, P.get(lid, {})):
        b: Built = base(level, r)
    return _anti(b, shape, r, extra, key=lid) if extra else b


@pilot("kinship", "?")
def kinship_descendants_r3(level: int, r: random.Random) -> Built:
    """kinship_descendants_r2 with retuned redraw probabilities (P['R1.kinship_descendants_r2'])."""
    return _wrap(kinship_descendants_r2, "R1.kinship_descendants_r2", level, r)


@pilot("kinship", "?")
def kinship_ancestor_r3(level: int, r: random.Random) -> Built:
    """kinship_ancestor_r2 with retuned redraw probabilities."""
    return _wrap(kinship_ancestor_r2, "R1.kinship_ancestor_r2", level, r)


@pilot("elimination", "?")
def elimination_bracket_r3(level: int, r: random.Random) -> Built:
    """elimination_bracket_r2 with retuned redraw probabilities."""
    return _wrap(elimination_bracket_r2, "R1.elimination_bracket_r2", level, r)


@pilot("categories", "?")
def categories_default_exceptions_r3(level: int, r: random.Random) -> Built:
    """Same schema as categories_default_exceptions. The asked verb has rules in FIVE groups above the member's own group (never in its own group). The sign vector of the five
    rules (most specific first; the most specific decides) is drawn by CONSTRUCTION so that three trivial shortcuts are independent of the answer: the least specific rule agrees with the
    answer with probability 1/2, and of the three middle rules none or two (equally likely) agree, so that P(majority = answer) = 1/2 and P(a random listed rule = answer) = 1/2,
    with no redraw. (The r2 shape's redraw pushed 'the least specific rule' to 98 % opposite to the answer;
    the r3 draft with three or four rules could not make the majority and the least specific rule both unbiased.) The chain has 6 + level // 2 groups; the member is in the smallest."""
    c = 6 + level // 2
    chain = r.sample(PSEUDO, c)
    verbs = r.sample(("swim", "glow", "hum", "jump", "float", "climb"), 2)
    ask, other = verbs
    idx = sorted(r.sample(range(1, c), 5))
    want = r.choice((True, False))
    n_mid_want = r.choice((0, 2))  # of the three middle rules: none or two agree with the answer
    mid = [want] * n_mid_want + [not want] * (3 - n_mid_want)
    r.shuffle(mid)
    last = want if r.random() < 0.5 else not want  # the least specific rule: a fair coin against the answer
    signs = [want, *mid, last]
    rules = [[chain[i], ask, sg] for i, sg in zip(idx, signs, strict=True)]
    for i in range(c):
        if r.random() < 0.4:
            rules.append([chain[i], other, r.random() < 0.5])
    member = r.choice(NAMES)
    r.shuffle(rules)
    chain_text = " ".join(f"Every {chain[i]} is a {chain[i + 1]}." for i in range(c - 1))
    rule_text = " ".join(f"A {g} {'can' if ok else 'cannot'} {v}." for g, v, ok in rules)
    q = (f"{chain_text} {rule_text} When two rules about the same thing disagree, the rule about the smaller (more specific) group wins. "
         f"{member} is a {chain[0]}. Can {member} {ask}? Answer yes or no.")
    return Built(q, {"chain": chain, "rules": rules, "member": member, "verb": ask}, "yes" if want else "no", "yn", 2)


@pilot("conditional", "?")
def conditional_threshold_rule_r3(level: int, r: random.Random) -> Built:
    """conditional_threshold_rule_r2 with retuned redraw probabilities."""
    return _wrap(conditional_threshold_rule_r2, "R1.conditional_threshold_rule_r2", level, r)


@pilot("containers", "?")
def containers_stack_piles_r3(level: int, r: random.Random) -> Built:
    """containers_stack_piles_r2 with retuned redraw probabilities."""
    return _wrap(containers_stack_piles_r2, "R1.containers_stack_piles_r2", level, r, "R1.containers_stack_piles_r3", ("initial_top",))


@pilot("scheduling", "?")
def topological_order_r2(level: int, r: random.Random) -> Built:
    """topological_order with retuned redraw probabilities."""
    return _wrap(topological_order, "R1.topological_order", level, r)


@pilot("voting", "?")
def instant_runoff_r2(level: int, r: random.Random) -> Built:
    """instant_runoff with retuned redraw probabilities."""
    return _wrap(instant_runoff, "R1.instant_runoff", level, r)


@pilot("matching", "?")
def stable_matching_r2(level: int, r: random.Random) -> Built:
    """stable_matching with retuned redraw probabilities."""
    return _wrap(stable_matching, "R1.stable_matching", level, r, "R1.stable_matching_r2", ("first_mentioned",))


# (shape id) -> (base shape id it retunes, the heuristics whose redraw probability is retuned)
RETUNED: dict[str, tuple[str, tuple[str, ...]]] = {
    "R1.kinship_descendants_r3": ("R1.kinship_descendants_r2", ("most_children", "most_mentioned", "first_mentioned")),
    "R1.kinship_ancestor_r3": ("R1.kinship_ancestor_r2", ("most_mentioned",)),
    "R1.elimination_bracket_r3": ("R1.elimination_bracket_r2", ("most_wins_logic",)),
    "R1.conditional_threshold_rule_r3": ("R1.conditional_threshold_rule_r2", ("yes_count_majority",)),
    "R1.containers_stack_piles_r3": ("R1.containers_stack_piles_r2", ("last_block_moved_onto_asked", "initial_top")),
    "R1.topological_order_r2": ("R1.topological_order", ("jth_alphabetical",)),
    "R1.instant_runoff_r2": ("R1.instant_runoff", ("plurality_winner",)),
    "R1.stable_matching_r2": ("R1.stable_matching", ("first_choice", "first_mentioned")),
}


# every lineage whose items are conditioned on a named heuristic's outcome (the generator-side repair of the earlier revisions and of this one)
ANTI_REPAIRED: tuple[str, ...] = (
    "R1.kinship_descendants_r2", "R1.kinship_ancestor_r2", "R1.elimination_bracket_r2", "R1.categories_default_exceptions_r2", "R1.conditional_threshold_rule_r2",
    "R1.containers_stack_piles_r2", "R1.topological_order", "R1.activity_selection", "R1.mst_cost", "R1.instant_runoff", "R1.stable_matching", *RETUNED,
)
REPAIR_NOTE = (
    "This repair CONDITIONS THE ITEM DISTRIBUTION ON A HEURISTIC'S OUTCOME: items that a named trivial heuristic answers correctly are drawn again with a probability fitted so that the "
    "heuristic sits near chance on both sides, so the kept items are not a plain sample of the lineage's rule. The band is a measurement, not a registered threshold."
)
