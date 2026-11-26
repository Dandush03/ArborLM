# ruff: noqa: E501
# mypy: disable-error-code="type-arg,no-untyped-call,no-any-return,arg-type,assignment,index,call-overload,var-annotated,list-item,unused-ignore,no-untyped-def"
"""Are the levels of a shape distinct? (lead ruling R-21, R-25 (c), R-26.) Adapted from the fourth auditor's ``level_identity4.py`` (``audit4_r1/``, Claude Opus 5.5): with one seed, 200 items are drawn at level a
and at level b from ``random.Random(seed)`` (a ``Retry`` is skipped on the same stream); if every question and answer coincide, the level does not enter the builder between a and b (an identical generator).
Seeds 4242 (200 items) and 777 (50 items), as the auditor used them. Also ``item_distinct_across_levels``: with different streams the items of two levels share no question text in a draw
of a few hundred, and the mean question length (characters) is reported per level as one measured size of the item, beside the stated parameter."""

from __future__ import annotations

import random
import statistics

from studies.m0.core import Lineage, Retry


def stream(lin: Lineage, lv: int, seed: int, n: int = 200) -> list[tuple[str, str]]:
    r = random.Random(seed)
    out: list[tuple[str, str]] = []
    while len(out) < n:
        try:
            b = lin.build(lv, r)
            out.append((b.question, b.answer))
        except Retry:
            pass
    return out


def level_classes(lin: Lineage) -> list[list[int]]:
    classes: list[tuple[list[int], tuple]] = []
    for lv in range(7):
        s = (stream(lin, lv, 4242), stream(lin, lv, 777, 50))
        for c in classes:
            if c[1] == s:
                c[0].append(lv)
                break
        else:
            classes.append(([lv], s))
    return [c[0] for c in classes]


def mean_question_length(lin: Lineage, lv: int, seed: int = 4242, n: int = 100) -> float:
    return round(statistics.mean(len(q) for q, _ in stream(lin, lv, seed, n)), 1)


# the stated size parameter of each surviving shape, read from the structured form (a count that the level sets); measured as a mean over items, per level
PARAM = {
    "boolean_lights": ("presses (3 + 2 level)", lambda s: len(s["presses"])),
    "categories_default_exceptions": ("groups in the chain (T + 8 + 2 level)", lambda s: len(s["chain"])),
    "compass_turns": ("commands (3 + 2 level)", lambda s: len(s["seq"])),
    "conditional_decision_tree": ("lights stated (depth + 2 + level)", lambda s: len(s["facts"])),
    "conditional_threshold_rule": ("members (6 + level)", lambda s: len(s["members"])),
    "equivalence_exchange_rates": ("rates stated (3 + level spine rates + 2 + level // 3 others)", lambda s: len(s["rates"])),
    "event_timeline": ("statements (4 + level spine + 2 + level // 3 others)", lambda s: len(s["rel"])),
    "graph_shortest_route": ("towns (h + 3 + level)", lambda s: len(s["towns"])),
    "knights_knaves": ("people (4 + level)", lambda s: len(s["people"])),
    "spatial_grid_walk": ("moves (4 + level + 0 to 3 free, 3 + level // 3 blocked)", lambda s: len(s["moves"])),
    "spatial_relative_directions": ("facts (5 + level spine + 2 + level // 3 others)", lambda s: len(s["facts"])),
    "swap_tracking": ("operations (6 + 2 level)", lambda s: len(s["ops"])),
    "temporal_weekday_shift": ("links (5 + level spine + 2 + level // 3 others)", lambda s: len(s["links"])),
    "venn_counting": ("groups (2 to 4 by level; regions 1 to 24 + 4 level)", lambda s: len(s["groups"])),
}


def table(lin: Lineage, n: int = 300, root: int = 8800) -> dict:
    """Per level: the mean stated parameter, the mean question length, the Retry rate (Retry raised per accepted item) over n items from random.Random(root + level)."""
    import re

    from studies.m0.r1_fix4_gen import items

    name, fn = PARAM[re.sub(r"_r\d+$", "", lin.id.split(".", 1)[1])]
    out: dict = {"parameter": name, "levels": {}}
    for lv in range(7):
        its, retries = items(lin, lv, n, root, count_retries=True)
        out["levels"][str(lv)] = {"mean_parameter": round(statistics.mean(fn(b.structured) for b in its), 2), "mean_question_chars": round(statistics.mean(len(b.question) for b in its), 1), "retry_rate": round(retries / n, 3)}
    return out


def main() -> None:
    import json
    import sys

    from studies.m0.r1_fix4_gen import lineages

    out = {}
    for lid, lin in sorted(lineages().items()):
        t = table(lin)
        t["distinct_level_classes"] = [c for c in level_classes(lin)]
        out[lid] = t
        print(lid, t["distinct_level_classes"], [t["levels"][str(lv)]["mean_parameter"] for lv in range(7)], flush=True)
    with open(sys.argv[1], "w") as f:
        json.dump(out, f, indent=1, sort_keys=True)


if __name__ == "__main__":
    main()
