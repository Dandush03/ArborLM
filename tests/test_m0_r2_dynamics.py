# ruff: noqa: E501
"""R2 batch 1, family dynamics: mechanical checks and test-local cross-checks (not the registered second solvers)."""

from __future__ import annotations

import random

from studies.m0.core import ALL_LEVELS, build_item, stream
from studies.m0.lineages_r2_common import check_family_r2, load_batch1

LIN = {x.id: x for x in load_batch1()}


def items(lid: str, per: int = 30):  # type: ignore[no-untyped-def]
    for lv in ALL_LEVELS:
        r = stream(953808, "t", lid, str(lv))
        for i in range(per):
            yield build_item(LIN[lid], lv, r, "A", f"t/{lv}/{i}")


def test_family_checks() -> None:
    assert check_family_r2("dynamics") == []


def test_cellular_automaton_by_string_windows() -> None:
    for it in items("R2.cellular_automaton"):
        s = it.structured
        row = "".join(map(str, s["row"]))
        for _ in range(s["steps"]):
            padded = "0" + row + "0"
            row = "".join(str(s["table"][padded[i : i + 3]]) for i in range(len(row)))
        assert it.answer == (row if s["ask"] == "row" else str(row.count("1")))


def test_toppling_end_state_does_not_depend_on_the_order() -> None:
    for it in items("R2.chip_toppling", 12):
        row = list(it.structured["row"])
        rnd = random.Random(7)
        top = lost = 0
        while True:
            ok = [i for i, v in enumerate(row) if v >= 2]
            if not ok:
                break
            i = rnd.choice(ok)
            row[i] -= 2
            top += 1
            for j in (i - 1, i + 1):
                if 0 <= j < len(row):
                    row[j] += 1
                else:
                    lost += 1
        ask = it.structured["ask"]
        assert it.answer == (", ".join(map(str, row)) if ask == "final" else str(top) if ask == "topplings" else str(lost))
