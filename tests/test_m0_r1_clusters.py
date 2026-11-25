# ruff: noqa: E501
"""R1 strict clusters, cluster-closed partition and the shortcut gate's own mechanics (lineage repair, rulings A, B, C). Self-checked only."""

from __future__ import annotations

import random

import pytest

from studies.m0 import lineage_gates as lg
from studies.m0 import lineages_r1_clusters as cl
from studies.m0 import lineages_r1_shortcuts as sc
from studies.m0.core import Built, Item, Lineage, lineages_of
from studies.m0.lineages_r1_common import load_pilot

ALL = {x.id: x for x in cl.all_r1_lineages()}


def test_every_merge_member_exists_and_no_lineage_is_in_two_groups() -> None:
    flat = [m for g in cl.STRICT_MERGES for m in g]
    assert len(flat) == len(set(flat))
    for m in flat:
        assert m in ALL, m


def test_the_audited_35_form_23_strict_clusters() -> None:
    audited = [*lineages_of("R1"), *[x for x in load_pilot() if x.build.__module__ == f"studies.m0.lineages_r1_{x.family}"]]
    assert len(audited) == 35
    assert len(cl.cluster_table(audited)) == 23  # the auditor's strict count (AUDIT_M0_LINEAGES_1.md)


def test_a_revision_stays_in_the_cluster_of_the_shape_it_replaces() -> None:
    for old, new in cl.SUPERSEDED.items():
        assert old in ALL and new in ALL
        assert cl.cluster_of(old) == cl.cluster_of(new)
        assert ALL[old].family == ALL[new].family
    reg = {x.id for x in cl.registered_lineages()}
    assert not reg & set(cl.SUPERSEDED)


def test_no_strict_cluster_spans_both_parts_and_the_partition_follows_the_rule() -> None:
    parts = cl.clusters_per_part()  # raises AssertionError if a cluster spans both parts
    assert parts["A"] and parts["B"] and not set(parts["A"]) & set(parts["B"])
    part = cl.partition()
    keys = sorted(part)
    assert sum(1 for v in part.values() if v == "A") == len(keys) // 2
    assert part == cl.partition()
    fg = cl.family_groups()
    for members in cl.cluster_table().values():
        assert len({fg[m.family] for m in members}) == 1  # a cluster's families are one family group


def test_the_cluster_check_can_fail() -> None:
    a = Lineage("R1.fake_a", "R1", "fam_a", lambda lv, r: Built("q", {}, "x", "name", 2))
    b = Lineage("R1.fake_b", "R1", "fam_b", lambda lv, r: Built("q", {}, "x", "name", 2))
    # two lineages of different families in the same strict cluster must land in one family group, hence one part
    old = cl.STRICT_MERGES
    try:
        cl.STRICT_MERGES = (*old, ("R1.fake_a", "R1.fake_b"))
        fg = cl.family_groups([a, b])
        assert fg["fam_a"] == fg["fam_b"] == "fam_a+fam_b"
    finally:
        cl.STRICT_MERGES = old
    assert cl.family_groups([a, b])["fam_a"] != cl.family_groups([a, b])["fam_b"]


# ---------------------------------------------------------------- shortcut gate mechanics


def _it(answer: str, k: int | None, q: str, answer_type: str = "name", structured: dict | None = None, level: int = 1) -> Item:
    return Item("i", "R1", "A", "R1.test", "f", level, q, structured or {}, answer, answer_type, k)


def test_credit_rules() -> None:
    it = _it("Ada", 4, "q")
    assert sc.credit("Ada", it) == 1.0 and sc.credit("ada", it) == 1.0 and sc.credit("Ben", it) == 0.0
    assert sc.credit(None, it) == 0.25 and sc.credit([], it) == 0.25
    assert sc.credit(["Ada", "Ben"], it) == 0.5 and sc.credit(["Ben", "Cy"], it) == 0.0
    assert sc.credit(None, _it("5", None, "q", "number")) == 0.0


def test_text_parsing_helpers() -> None:
    assert sc.parse_options("x. Who? Choose from Ada, Ben and Cara.") == ["Ada", "Ben", "Cara"]
    assert sc.parse_options("Choose from jump, run, turn left and wait.") == ["jump", "run", "turn left", "wait"]
    assert sc.parse_options("no list here") is None
    body, tail = sc.split_body("Ada is tall. Ben is short. Who is tall? Choose from Ada and Ben.")
    assert body == "Ada is tall. Ben is short." and tail.startswith("Who is tall?")


def test_the_battery_flags_a_planted_leak_and_a_constant_key() -> None:
    names = ["Ada", "Ben", "Cara", "Dev"]

    def leaky(level: int, r: random.Random) -> Built:
        order = r.sample(names, 4)
        q = f"{order[0]} came. {order[1]} came. {order[2]} came. {order[3]} came. Who came first? Choose from {', '.join(sorted(names[:3]))} and {names[3]}."
        return Built(q, {}, order[0], "name", 4)

    def constant(level: int, r: random.Random) -> Built:
        return Built(f"Pick {r.randint(1, 10**6)}. Is it yes? Answer yes or no.", {}, "yes", "yn", 2)

    items = [lg.build_item(Lineage("R1.leaky", "R1", "t", leaky), 1, random.Random(i), "A", str(i)) for i in range(300)]
    res = sc.run_battery(Lineage("R1.leaky", "R1", "t", leaky), items)
    assert res["worst"]["heuristic"] == "first_mentioned" and res["worst"]["accuracy"] == 1.0
    items2 = [lg.build_item(Lineage("R1.const", "R1", "t", constant), 1, random.Random(i), "A", str(i)) for i in range(300)]
    res2 = sc.run_battery(Lineage("R1.const", "R1", "t", constant), items2)
    assert res2["worst"]["heuristic"] == "constant_most_frequent_key" and res2["worst"]["accuracy"] == 1.0 and res2["worst"]["excess_over_chance"] == 0.5


def test_a_fair_lineage_is_near_chance_on_the_battery() -> None:
    names = ["Ada", "Ben", "Cara", "Dev"]

    def fair(level: int, r: random.Random) -> Built:
        order = r.sample(names, 4)
        return Built(f"{order[0]} came. {order[1]} came. {order[2]} came. {order[3]} came. Who is it? Choose from {', '.join(sorted(names[:3]))} and {names[3]}.", {}, r.choice(names), "name", 4)

    lin = Lineage("R1.fair", "R1", "t", fair)
    res = sc.run_battery(lin, [lg.build_item(lin, 1, random.Random(i), "A", str(i)) for i in range(2000)])
    assert res["worst"]["excess_over_chance"] < 0.06


@pytest.mark.parametrize("lid", ["R1.topological_order", "R1.instant_runoff", "R1.stable_matching"])
def test_anti_shortcut_repair_moves_the_named_heuristic_towards_chance(lid: str) -> None:
    lin = ALL[lid]
    res = sc.run_battery(lin, lg.sample_items(lin, 100, label="anti"))
    named = {"R1.topological_order": "jth_alphabetical", "R1.instant_runoff": "plurality_winner", "R1.stable_matching": "first_choice"}[lid]
    row = next(r for r in res["heuristics"] if r["heuristic"] == named)
    assert row["excess_over_chance"] < (0.18 if lid == "R1.stable_matching" else 0.12)  # stable_matching keeps about 0.11 to 0.13 over chance: a measured residual
