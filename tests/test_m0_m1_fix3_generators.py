# ruff: noqa: E501
"""M1 fix round 3, generator defects. Each check is a function of ``studies.m0.m1_fix3_checks`` that returns problems; the new shapes must return none, and ``m1_fix3_failing_first.py`` shows the
same function returning problems on the pre-fix shapes. Self-check only: not independent review."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from studies.m0.core import ALL_LEVELS, build_item, lineages_of, stream
from studies.m0.lineages_m1_fix3 import (
    EXCLUDED_EVERYWHERE,
    NOT_REGISTERED,
    load_all,
    load_registered,
)
from studies.m0.m1_fix3_checks import (
    format_problems,
    retry_levels,
    shape_mix_problems,
    structured_problems,
)
from studies.m0.m1_fix3_verify import verify

ROOT = Path(__file__).resolve().parents[1]
ALL = {x.id: x for x in load_all()}


def stem(lid: str) -> str:
    return lid.split(".", 1)[1].removesuffix("_r3")


def test_the_set_is_36_lineages_with_min_cost_packs_nowhere() -> None:
    assert len(ALL) == 36
    assert not any("min_cost" in i for i in ALL)
    assert set(NOT_REGISTERED) <= set(ALL)
    assert len(load_registered()) == 36 - len(NOT_REGISTERED)
    for bad in EXCLUDED_EVERYWHERE:
        assert bad not in ALL
    fixtures = {p.name for p in (ROOT / "studies" / "m0" / "fixtures" / "m1_fix3").glob("*.jsonl")} if (ROOT / "studies" / "m0" / "fixtures" / "m1_fix3").exists() else set()
    assert not any("min_cost" in n for n in fixtures)
    assert not (fixtures & {f"{i}.jsonl" for i in NOT_REGISTERED}), "a NOT REGISTERED lineage has fixtures"


def test_nothing_enters_core_registry() -> None:
    core_ids = {x.id for x in lineages_of("M1")}
    assert not (core_ids & set(ALL)) or core_ids & set(ALL) == {"M1.tiered_pricing"} - core_ids  # no r3 id in core.REGISTRY
    assert not any(i.endswith("_r3") for i in core_ids)


@pytest.mark.parametrize("lid", sorted(ALL))
def test_no_builder_raises_retry_including_the_carried_over_shape(lid: str) -> None:
    assert retry_levels(ALL[lid]) == [], lid


def test_no_new_module_imports_or_raises_retry() -> None:
    for name in ("lineages_m1_fix3_common", "lineages_m1_fix3_a", "lineages_m1_fix3_b", "lineages_m1_fix3_c", "lineages_m1_fix3"):
        text = (ROOT / "studies" / "m0" / f"{name}.py").read_text()
        assert "raise Retry" not in text and "import Retry" not in text and ", Retry" not in text, name


@pytest.mark.parametrize("lid", sorted(ALL))
def test_every_question_states_its_answer_format(lid: str) -> None:
    assert format_problems(ALL[lid]) == [], lid


@pytest.mark.parametrize("lid", sorted(ALL))
def test_structured_forms_are_json_stable_and_number_answers(lid: str) -> None:
    assert structured_problems(ALL[lid]) == [], lid


@pytest.mark.parametrize("lid", sorted(ALL))
def test_every_key_equals_the_bruteforce_rederivation_from_the_structured_form(lid: str) -> None:
    lin = ALL[lid]
    checked = 0
    for lv in ALL_LEVELS:
        rng = stream(411101, "verify", lid, str(lv))
        for i in range(12):
            it = build_item(lin, lv, rng, "A", f"v/{i}")
            try:
                got = verify(stem(lid), it.structured)
            except ValueError as e:
                if "too large" in str(e):
                    continue
                raise AssertionError(f"{lid} L{lv}: {e}") from e
            assert got == it.answer, (lid, lv, it.structured, it.answer, got)
            checked += 1
    assert checked >= 40, (lid, checked)


@pytest.mark.parametrize(("lid", "key", "values"), [
    ("M1.gcd_lcm_r3", "ask", {"gcd", "lcm"}),
    ("M1.division_counting_r3", "shape", {"pallets", "empty_seats"}),
    ("M1.pigeonhole_worst_case_r3", "goal", {"same", "all"}),
    ("M1.mode_tally_r3", "ask", {"mode", "others"}),
    ("M1.prime_factors_r3", "ask", {"divisors", "largest", "distinct_sum", "factor_count"}),
    ("M1.painted_cube_r3", "faces", {"0", "1", "2"}),
    ("M1.ages_r3", "ask", {"younger", "older"}),
    ("M1.consecutive_r3", "ask", {"largest", "smallest"}),
    ("M1.coins_r3", "ask", {"lo", "hi"}),
    ("M1.quadratic_area_r3", "shape", {"rect_area", "rect_perimeter", "product", "squares"}),
])
def test_shape_mix_is_uniform_at_every_level(lid: str, key: str, values: set[str]) -> None:
    assert shape_mix_problems(ALL[lid], key, values) == []


def test_rectangle_shape_mix_is_the_designed_three_tenths() -> None:
    for lv in ALL_LEVELS:
        rng = stream(411102, "rect", str(lv))
        share = sum(build_item(ALL["M1.rectangle_r3"], lv, rng, "A", "t").structured["shape"] == "ratio" for _ in range(2000)) / 2000
        assert abs(share - 0.3) < 0.05, (lv, share)


def test_inclusion_exclusion_ask_mix_is_uniform_over_the_asks_of_its_level() -> None:
    for lv in ALL_LEVELS:
        rng = stream(411103, "ie", str(lv))
        from collections import Counter

        c = Counter(build_item(ALL["M1.inclusion_exclusion_r3"], lv, rng, "A", "t").structured["ask"] for _ in range(1500))
        want = 4 if lv >= 5 else 2
        assert len(c) == want and all(abs(v / 1500 - 1 / want) < 0.06 for v in c.values()), (lv, c)


def test_mixture_validity_is_by_construction_not_by_retry() -> None:
    """Batch 1's retry (whole number of cents) favoured equal weights; here the share of equal weights is small and every mean is exact in cents."""
    for lv in ALL_LEVELS:
        rng = stream(411104, "mix", str(lv))
        eq = n = 0
        for _ in range(1500):
            s = build_item(ALL["M1.mixture_r3"], lv, rng, "A", "t").structured
            eq += s["x"] == s["y"]
            n += 1
            assert s["a"] != s["b"]
        assert eq / n < 0.06, (lv, eq / n)


def test_speed_distance_legs_have_distinct_hours_and_integral_averages() -> None:
    for lv in ALL_LEVELS:
        rng = stream(411105, "sd", str(lv))
        for _ in range(300):
            s = build_item(ALL["M1.speed_distance_r3"], lv, rng, "A", "t").structured
            hours = [h for h, _ in s["legs"]]
            assert len(set(hours)) == len(hours)
            if s["average"]:
                assert sum(h * v for h, v in s["legs"]) % sum(hours) == 0


def test_gcd_lcm_structure_removes_the_partial_gcd_and_partial_lcm_shortcuts() -> None:
    import math

    for lv in ALL_LEVELS:
        rng = stream(411106, "gl", str(lv))
        for _ in range(300):
            it = build_item(ALL["M1.gcd_lcm_r3"], lv, rng, "A", "t")
            v, ans = it.structured["values"], int(it.answer)
            if len(v) < 3:
                continue
            for i in range(len(v)):
                rest = v[:i] + v[i + 1:]
                if it.structured["ask"] == "gcd":
                    assert math.gcd(*rest) > ans
                else:
                    assert math.lcm(*rest) < ans


def test_painted_cube_closed_form_equals_the_loop_over_every_cube() -> None:
    from studies.m0.lineages_m1_fix3_c import painted_count

    for a, b, c in ((3, 3, 3), (3, 4, 5), (5, 7, 3), (9, 3, 8), (6, 6, 6)):
        for ba in (True, False):
            for f in (0, 1, 2):
                brute = sum(1 for x in range(a) for y in range(b) for z in range(c) if (x in (0, a - 1)) + (y in (0, b - 1)) + (z == c - 1) + (z == 0 and not ba) == f)
                assert painted_count(a, b, c, ba, f) == brute


def test_slot_count_equals_enumeration_on_small_cases() -> None:
    import itertools

    from studies.m0.lineages_m1_fix3_b import _RULES_FIRST, _RULES_LAST, slot_count

    digs = [0, 2, 3, 5, 6, 8, 9]
    for s in (3, 4):
        for rep in (False, True):
            for fr in _RULES_FIRST:
                for la in _RULES_LAST:
                    gen = itertools.product(digs, repeat=s) if rep else itertools.permutations(digs, s)
                    brute = sum(1 for c in gen if _RULES_FIRST[fr](c[0]) and _RULES_LAST[la](c[-1]))
                    assert slot_count(digs, s, rep, fr, la) == brute


def test_determinism_across_hash_seeds() -> None:
    code = (
        "import hashlib, json, sys\n"
        "from studies.m0.core import ALL_LEVELS, build_item, stream\n"
        "from studies.m0.lineages_m1_fix3 import load_all\n"
        "h = hashlib.sha256()\n"
        "for lin in load_all():\n"
        "    for lv in ALL_LEVELS:\n"
        "        rng = stream(411107, 'det', lin.id, str(lv))\n"
        "        for i in range(4):\n"
        "            it = build_item(lin, lv, rng, 'A', 'd')\n"
        "            h.update(json.dumps([it.question, it.answer, it.structured], sort_keys=True).encode())\n"
        "print(h.hexdigest())\n"
    )
    outs = []
    for hs in ("0", "1"):
        env = {"PYTHONHASHSEED": hs, "PATH": "/usr/bin:/bin"}
        import os

        env = {**os.environ, "PYTHONHASHSEED": hs}
        r = subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=env, capture_output=True, text=True, timeout=240)
        assert r.returncode == 0, r.stderr[-500:]
        outs.append(r.stdout.strip())
    assert outs[0] == outs[1] and len(outs[0]) == 64
    assert hashlib.sha256(b"").hexdigest() != outs[0]


def test_fixtures_exist_for_registered_lineages_and_are_structurally_distinct() -> None:
    from studies.m0.m1_fix3_gates import canon_key

    d = ROOT / "studies" / "m0" / "fixtures" / "m1_fix3"
    if not d.exists():
        pytest.skip("fixtures not written yet")
    for lin in load_registered():
        f = d / f"{lin.id}.jsonl"
        rows = [json.loads(x) for x in f.read_text().splitlines()]
        assert len(rows) == 140, lin.id
        keys = [canon_key(lin.id, r["structured"]) for r in rows]
        assert len(set(keys)) == 140, lin.id
        assert all(r["lineage"] == lin.id for r in rows)
