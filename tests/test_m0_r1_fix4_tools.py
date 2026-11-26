# ruff: noqa: E501
"""R1 fix round 4: the measurement tools (classification, per-level table), the two package-hygiene edits (outputs unchanged, hash-seed independent), the capacity wiring against ``core.generate_pool``
as written, and the demand formula (lead rulings R-24, R-26, R-27, R-28)."""

from __future__ import annotations

import math
import os
import random
import subprocess
import sys
from pathlib import Path

from studies.m0 import core
from studies.m0 import r1_fix4_a3_heur as h3
from studies.m0 import r1_fix4_a4_heur as h4
from studies.m0 import r1_fix4_capacity as cap
from studies.m0 import r1_fix4_table as T
from studies.m0.lineages_r1_fix4_clusters import candidates_v4
from studies.m0.r1_fix4_tells import feature_rows

ROOT = Path(__file__).resolve().parents[1]
BY = {x.id: x for x in candidates_v4()}


def test_rule_classes_follow_the_audit() -> None:
    assert T.cls("a4:fewest_negated_matches") == "C" and T.cls("constant_mfk_fitted") == "C" and T.cls("a4:round_0_75n") == "C"
    assert T.cls("a3:lift_no_only") == "A" and T.cls("a4:half_best_then_h2h") == "A"
    assert T.cls("abstain_as_no") == "M" and T.cls("a4:signed_axis_merged") == "M"
    assert T.cls("a3:partial_walk_3") is None and T.cls("ccw_as_cw") is None
    assert T.cls("feat:kind+#groups") == "C" and T.cls("feat:options in the child s family tree") == "A"


def test_per_level_takes_the_larger_of_eff_and_anti_drops_exact_rules_and_keeps_m_apart() -> None:
    rows = [
        {"lineage": "L", "level": 0, "heuristic": "a4:round_0_75n", "eff": 0.20, "anti": None, "acc_fired": 0.6, "fired": 90, "n": 100},
        {"lineage": "L", "level": 0, "heuristic": "a3:lift_no_only", "eff": -0.30, "anti": 0.31, "acc_fired": 0.2, "fired": 90, "n": 100},
        {"lineage": "L", "level": 0, "heuristic": "exact_solver", "eff": 0.5, "anti": 0.0, "acc_fired": 1.0, "fired": 100, "n": 100},
        {"lineage": "L", "level": 0, "heuristic": "abstain_as_no", "eff": 0.9, "anti": None, "acc_fired": 0.9, "fired": 100, "n": 100},
        {"lineage": "L", "level": 1, "heuristic": "a4:foo_error", "eff": 0.9, "anti": None, "acc_fired": None, "fired": 0, "n": 100},
        {"lineage": "L", "level": 1, "heuristic": "a4:round_0_75n", "eff": 0.1, "anti": 0.05, "acc_fired": 0.6, "fired": 90, "n": 100},
    ]
    t = T.per_level(rows)["L"]
    assert t[0]["C"] == (0.2, "round_0_75n") and t[0]["A"] == (0.31, "lift_no_only") and t[0]["M"] == (0.9, "abstain_as_no")
    assert T.level_max(t[0]) == (0.31, "lift_no_only", "A")
    assert t[1]["C"][0] == 0.1 and t[1]["A"][0] == 0.0
    assert T.shape_max(t) == (0.31, 0, "lift_no_only", "A")


def test_the_copied_auditor_battery_gives_the_repaired_shapes_the_rules_written_for_their_r5_builders() -> None:
    lin = BY["R1.knights_knaves_r6"]
    b = core.build_item(lin, 2, random.Random(3), "A", "x")
    built = lin.build(2, random.Random(3))
    p = h4.preds(lin.id, built)
    assert any(k.startswith("a4:") for k in p), sorted(p)[:8]
    assert any(k.startswith("a3:") for k in p) or "first_mentioned" in p
    assert b.answer in ("knight", "knave") and h3.chance(built) == 0.5


def test_fitted_lookup_rows_cover_every_level_for_a_closed_answer_shape() -> None:
    rows = feature_rows(BY["R1.knights_knaves_r6"], 150, 100)
    assert {r["level"] for r in rows} == set(range(7)) and {r["heuristic"] for r in rows} == {"feat:own statement kind", "feat:own kind + is self in args"}
    assert all(-0.5 <= r["eff"] <= 0.5 for r in rows)


# ---------------------------------------------------------------- hygiene edits (R-27)


def test_the_two_hygiene_edits_left_no_set_iteration_in_the_two_files() -> None:
    import ast

    for name in ("r1_fix3_battery.py", "r1_fix3_capacity.py"):
        tree = ast.parse((ROOT / "studies/m0" / name).read_text())
        for node in ast.walk(tree):
            its = [node.iter] if isinstance(node, ast.For | ast.comprehension) else []
            for it in its:
                assert not (isinstance(it, ast.Call) and isinstance(it.func, ast.Name) and it.func.id in ("set", "frozenset")), (name, it.lineno)


def test_the_structural_key_does_not_depend_on_the_hash_seed() -> None:
    code = (
        "import hashlib, random, sys\n"
        "sys.path.insert(0, '.')\n"
        "from studies.m0.core import Retry\n"
        "from studies.m0.lineages_r1_fix4_clusters import candidates_v4\n"
        "from studies.m0 import r1_fix3_capacity as C\n"
        "h = hashlib.sha256()\n"
        "for lin in candidates_v4():\n"
        "    r = random.Random(77)\n"
        "    for lv in (0, 3, 6):\n"
        "        k = 0\n"
        "        while k < 4:\n"
        "            try:\n"
        "                b = lin.build(lv, r)\n"
        "            except Retry:\n"
        "                continue\n"
        "            k += 1\n"
        "            h.update(repr(C.keys_of(lin.id, b.structured)).encode())\n"
        "print(h.hexdigest())\n"
    )
    outs = []
    for seed in ("1", "2"):
        env = {**os.environ, "PYTHONHASHSEED": seed}
        outs.append(subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=env, capture_output=True, text=True, check=True, timeout=600).stdout.strip())
    assert outs[0] == outs[1] and len(outs[0]) == 64


# ---------------------------------------------------------------- capacity against generate_pool as written (R-28)


def test_demand_formula_matches_the_rulings() -> None:
    assert cap.demand(11) == 22830  # the round-3 value
    assert cap.demand(10) == 10 * (math.ceil(4000 / 10) + math.ceil(20000 / 10) + 100) == 25000
    assert cap.demand(5) == 49000


def test_a_cell_calls_generate_pool_unchanged_and_restores_the_part_lookup() -> None:
    before = core.part_lineages
    out = cap._cell(("A", 2, 6, 11))
    assert core.part_lineages is before
    assert out["items"] == 6 * out["lineages"] and out["shortfalls"] == [] and out["text_repeats"] == 0
    assert set(out["supplied"].values()) == {6}


def test_a_lineage_that_cannot_supply_the_quota_is_reported_as_a_shortfall() -> None:
    from studies.m0.core import Built, Lineage

    tiny = Lineage("R1.tiny", "R1", "x", lambda lv, r: Built(f"Pick a number {r.randint(1, 3)}.", {}, "1", "number", None))
    sf: list[tuple[str, int, int, int]] = []
    saved = core.part_lineages
    core.part_lineages = lambda e, p, s=400004: [tiny]  # noqa: ARG005
    try:
        pool = core.generate_pool("R1", "A", "development", 5, 50, {0: 1.0}, set(), shortfalls=sf)
    finally:
        core.part_lineages = saved
    assert len(pool) == 3 and sf == [("R1.tiny", 0, 50, 3)]


def test_parts_partition_the_survivors_and_a_cluster_is_in_one_part() -> None:
    p = cap.parts()
    assert sorted(p["A"]["lineages"] + p["B"]["lineages"]) == sorted(x.id for x in candidates_v4() if x.id in {*p["A"]["lineages"], *p["B"]["lineages"]})
    assert len(p["A"]["clusters"]) + len(p["B"]["clusters"]) == 10 and p["A"]["m_min"] == p["B"]["m_min"] == 1
