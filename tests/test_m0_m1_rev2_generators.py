# ruff: noqa: E501
"""M1 rev2, generator defects: the question type is drawn outside any retry (so the design's shape mix holds at every level), nothing is redrawn on a heuristic (R-1),
and the fixtures have no repeated structure across levels. Each test also shows the batch-1 defect."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pytest

from studies.m0.core import ALL_LEVELS, CORE_LEVELS, Retry, build_item, stream
from studies.m0.lineages_m1_common import load_batch
from studies.m0.lineages_m1_rev2 import REV2, load_rev2
from studies.m0.m1_rev2_gates import canon_key

OLD = {x.id: x for x in load_batch()}
NEW = {x.id: x for x in load_rev2()}
ROOT = Path(__file__).resolve().parents[1]


def mix(lin, level: int, key: str, n: int = 1500) -> dict[str, float]:  # type: ignore[no-untyped-def]
    rng = stream(953802, lin.id, str(level))
    c = Counter(str(build_item(lin, level, rng, "A", "t").structured[key]) for _ in range(n))
    return {k: v / n for k, v in c.items()}


def test_batch1_gcd_lcm_collapsed_to_lcm_only_and_division_counting_was_lopsided() -> None:
    assert mix(OLD["M1.gcd_lcm"], 5, "ask", 600).get("gcd", 0.0) < 0.05  # defect D1
    m = mix(OLD["M1.division_counting"], 2, "shape", 1200)
    assert m["multiples"] < 0.15 and m["empty_seats"] > 0.5  # defect D2


@pytest.mark.parametrize(("lid", "key", "values"), [
    ("M1.gcd_lcm_r2", "ask", {"gcd", "lcm"}),
    ("M1.division_counting_r2", "shape", {"pallets", "empty_seats"}),
    ("M1.pigeonhole_worst_case_r2", "goal", {"same", "all"}),
    ("M1.binomial_choose_r2", "shape", {"plain", "include", "two_groups"}),
    ("M1.mode_tally_r2", "ask", {"mode", "mode_count"}),
    ("M1.prime_factors_r2", "ask", {"divisors", "largest", "distinct_sum", "factor_count"}),
    ("M1.pythagoras_r2", "shape", {"ladder_top", "ladder_base", "walk", "diagonal", "perimeter"}),
    ("M1.painted_cube_r2", "faces", {"0", "1", "2"}),
])
def test_shape_mix_is_the_designs_uniform_mix_at_every_level(lid: str, key: str, values: set[str]) -> None:
    for lv in ALL_LEVELS:
        m = mix(NEW[lid], lv, key)
        assert set(m) == values, (lid, lv)
        for v, share in m.items():
            assert abs(share - 1 / len(values)) < 0.06, (lid, lv, v, share)


def test_inclusion_exclusion_ask_mix_is_uniform_over_the_asks_of_its_level() -> None:
    for lv in ALL_LEVELS:
        m = mix(NEW["M1.inclusion_exclusion_r2"], lv, "ask")
        want = 4 if lv >= 5 else 2
        assert len(m) == want and all(abs(v - 1 / want) < 0.06 for v in m.values()), (lv, m)


def test_no_revised_builder_ever_raises_retry() -> None:
    for lin in REV2:
        for lv in ALL_LEVELS:
            rng = stream(953803, lin.id, str(lv))
            for _ in range(150):
                try:
                    lin.build(lv, rng)
                except Retry:  # a Retry is a redraw: it would re-draw the question type (D1/D2) and can be conditional on a heuristic (R-1)
                    pytest.fail(f"{lin.id} L{lv} raised Retry")


def test_revised_source_has_no_retry_and_no_heuristic_conditional_redraw() -> None:
    src = (ROOT / "studies" / "m0" / "lineages_m1_rev2.py").read_text()
    code = "\n".join(line for line in src.splitlines() if not line.lstrip().startswith(("#", '"""')))
    assert "raise Retry" not in code and "except Retry" not in code


def _dups(path: Path) -> int:
    seen: set[str] = set()
    d = 0
    for line in path.read_text().splitlines():
        it = json.loads(line)
        k = canon_key(it["lineage"], it["structured"])
        d += k in seen
        seen.add(k)
    return d


def test_fixtures_have_no_repeated_structure_across_levels_and_batch1_had() -> None:
    old_dirs = ROOT / "studies" / "m0" / "fixtures" / "m1_batch1"
    assert sum(_dups(old_dirs / f"M1.{n}.jsonl") for n in ("binomial_choose", "slot_permutations", "digit_puzzle")) > 0  # defect D4, kept on file
    new_dir = ROOT / "studies" / "m0" / "fixtures" / "m1_batch1_rev2"
    files = sorted(new_dir.glob("M1.*_r2.jsonl"))
    assert len(files) == len(REV2) == 17
    for f in files:
        assert _dups(f) == 0, f.name
        assert len(f.read_text().splitlines()) == 20 * len(ALL_LEVELS)


def test_levels_core_is_five() -> None:
    assert CORE_LEVELS == (1, 2, 3, 4, 5)
