# ruff: noqa: E501
"""R1 revision 4, gate bugs found by the second audit (docs/reviews/m0-lineage-decision-2026-11-25/audit2_r1/AUDIT_M0_R1_2.md, section 6.3). Each test fails on the
gate as it stood at 9e32b317 and passes on the fixed gate. Self-checked only."""

from __future__ import annotations

from studies.m0 import lineage_gates as lg
from studies.m0 import lineages_r1_clusters as cl
from studies.m0 import lineages_r1_shortcuts as sc
from studies.m0.core import Item


def _item(q: str, ans: str, typ: str = "name", k: int | None = 3, structured: dict | None = None) -> Item:
    return Item("x", "R1", "A", "R1.test", "f", 1, q, structured or {}, ans, typ, k)


def test_possessive_form_of_the_answer_is_the_answer() -> None:
    q = "Flynn's job takes 3 days and starts on day 0. Ada's job takes 2 days and starts as soon as the job of Flynn is finished. Whose job finishes last?"
    it = _item(q, "Flynn")
    assert sc.credit("Flynn", it) == 1.0  # before the fix: "Flynn's" was one token, the name was "not an option", the prediction was discarded (credit 1/k)
    assert sc.credit(["Flynn"], it) == 1.0
    assert sc.credit("Ada", it) == 0.0


def test_possessive_only_answer_counts_in_the_longest_job_reading() -> None:
    lin = next(x for x in cl.registered_lineages() if x.id == "R1.temporal_critical_path")
    items = lg.sample_items(lin, 300, label="rev4-gate-poss")
    row = next(r for r in sc.run_battery(lin, items)["heuristics"] if r["heuristic"] == "longest_job")
    assert row["excess_over_chance"] > 0.05, row  # audit: true +0.13 (the gate had reported -0.09)


def test_mention_counts_see_a_possessive() -> None:
    q = "Flynn's job takes 3 days. Ada's job takes 2 days. Flynn is late. Who? Choose from Ada and Flynn."
    it = _item(q, "Flynn", k=2)
    g = sc.generic(it)
    assert g["most_mentioned"] == ["Flynn"]
    assert sc._count("Flynn's job. Flynn.", "Flynn") == 2  # before the fix only the bare mention counted (1)
    assert sc._count("Flynn's job. Flynn.", "Flynn") > sc._count("Ada's job.", "Flynn")


def test_stated_pair_reads_the_direction_in_which_it_is_stated() -> None:
    same = _item("Ada is taller than Ben. Cara is taller than Dev. Is Ada taller than Ben? Answer yes, no or cannot be determined.", "yes", "ynu")
    rev = _item("Ben is taller than Ada. Cara is taller than Dev. Is Ada taller than Ben? Answer yes, no or cannot be determined.", "no", "ynu")
    rev2 = _item("Ben is shorter than Ada. Cara is taller than Dev. Is Ada taller than Ben? Answer yes, no or cannot be determined.", "yes", "ynu")
    assert sc.generic(same)["asked_pair_stated_verbatim"] == "yes"
    assert sc.generic(rev)["asked_pair_stated_verbatim"] == "no"  # before the fix: "yes" (direction ignored)
    assert sc.generic(rev2)["asked_pair_stated_verbatim"] == "yes"


def test_stated_pair_symmetric_relation_is_unchanged() -> None:
    it = _item("Bedok is the same thing as Kolix. Is Kolix the same thing as Bedok? Answer yes, no or cannot be determined.", "yes", "ynu")
    assert sc.generic(it)["asked_pair_stated_verbatim"] == "yes"


def test_numbers_are_signed_and_structure_counts_are_not_numbers() -> None:
    q = "Two players play a game with 2 choices in a row. The game is (3 or (-7 or 5)). What is the payoff?"
    it = _item(q, "-7", "number", None)
    g = sc.generic(it)
    assert g["smallest_number"] == "-7"  # before the fix: min of unsigned digits = 2 (the depth)
    assert g["largest_number"] == "5"
    assert g["last_number"] == "5"


def test_per_level_reporting() -> None:
    lin = next(x for x in cl.registered_lineages() if x.id == "R1.order_extreme")
    items = lg.sample_items(lin, 120, label="rev4-gate-lv")
    rows = sc.run_battery(lin, items)["heuristics"]
    assert rows and all("per_level" in r for r in rows)
    r0 = rows[0]["per_level"]
    assert set(r0) == {str(i) for i in (1, 2, 3, 4, 5)}
    assert {"n", "fires", "accuracy", "chance", "departure", "anti_departure"} <= set(r0["1"])
