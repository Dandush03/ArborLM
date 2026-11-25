# ruff: noqa: E501
"""R2 fix round 3: the set, the strict cluster map, the exclusions (R-12), the demand formula (R-11), the capacity counting semantics, and the consistency of the recorded files. Self-checks, not independent review."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from studies.m0 import core
from studies.m0.lineages_r2_clusters import strict_clusters as old_strict_clusters
from studies.m0.lineages_r2_fix3 import FIX3, SUPERSEDES, load_fix3
from studies.m0.r2_fix3_battery import is_p
from studies.m0.r2_fix3_build import DROPPED_SHAPES, FIXES
from studies.m0.r2_fix3_capacity import canon
from studies.m0.r2_fix3_clusters import (
    BORDERLINE_GROUPS,
    CROSS_EVAL,
    STRICT_MERGES,
    cluster_of,
    clusters,
    cross_eval_for_cluster,
    demand,
    working_ids,
)
from studies.m0.r2_fix3_set import NOT_REGISTERED, current_set, fix3_set

ROOT = Path(__file__).resolve().parents[1]
MAN = ROOT / "studies" / "m0" / "manifests"
FX = ROOT / "studies" / "m0" / "fixtures" / "r2_fix3"
EXCLUDED = {"R2.deferred_acceptance_partner", "R2.chip_toppling"}


def test_excluded_lineages_are_out_everywhere() -> None:
    assert set(NOT_REGISTERED) == EXCLUDED
    assert not EXCLUDED & set(fix3_set())
    assert not EXCLUDED & set(working_ids())
    assert not any(m in EXCLUDED for v in clusters().values() for m in v)
    assert not EXCLUDED & {x.id for x in FIX3}
    # the earlier round's map still counted deferred acceptance (the defect this test guards)
    old = old_strict_clusters()
    assert len(old) == 38 and any("deferred_acceptance_partner" in m for v in old.values() for m in v)
    assert "R2.deferred_acceptance_partner" not in current_set()


def test_set_has_forty_lineages_and_replaces_only_revised_shapes() -> None:
    new, old = fix3_set(), current_set()
    assert len(new) == 40 and len(old) == 41
    assert set(old) - set(new) == {"R2.chip_toppling"}
    assert set(new) <= set(old)
    assert "R2.to_base_wide" in new and "R2.string_rewrite_nonidentity" in new and "R2.to_base" not in new and "R2.string_rewrite" not in new
    for x in load_fix3():
        assert new[x.id] is x  # the revised shape replaces the earlier one
    assert sum(1 for k in new if new[k] is not old[k]) == len(load_fix3())


def test_strict_map_has_36_clusters_and_every_lineage_once() -> None:
    cl = clusters()
    assert len(cl) == 36
    members = [m for v in cl.values() for m in v]
    assert sorted(members) == working_ids() and len(set(members)) == len(members) == 40
    for grp in STRICT_MERGES:
        assert len({cluster_of(m) for m in grp}) == 1
    assert [len(v) for v in cl.values()].count(2) == 4 and max(len(v) for v in cl.values()) == 2


def test_borderline_groups_are_listed_not_merged() -> None:
    merged = {frozenset(g) for g in STRICT_MERGES}
    for g in BORDERLINE_GROUPS:
        present = [m for m in g if m in fix3_set()]
        if frozenset(present) in merged:
            continue
        assert len({cluster_of(m) for m in present}) > 1, g


def test_cross_evaluation_listing_refers_to_real_members() -> None:
    ids = set(working_ids())
    assert set(CROSS_EVAL) <= ids
    # 18 of the strict clusters share an algorithm with another evaluation (audit): at least that many are listed
    assert sum(1 for k in clusters() if cross_eval_for_cluster(k)) >= 18


def test_demand_formula_r11_and_reserve_levels_carry_it() -> None:
    assert demand(17) == 10 * (236 + 1177 + 100) == 15130
    assert demand(18) == 10 * (223 + 1112 + 100) == 14350
    assert demand(17) >= 10 * (-(-24000 // 17) + 100)  # at least the earlier 10 x (ceil(24,000 / G) + 100)


def test_registry_untouched() -> None:
    before = {x.build for x in core.lineages_of("R2")}
    assert len(before) == 16
    load_fix3()
    after = {x.build for x in core.lineages_of("R2")}
    assert before == after
    assert not {x.build for x in FIX3} & after


def test_every_revised_shape_has_a_supersedes_a_defect_and_a_fix() -> None:
    for x in load_fix3():
        assert x.id in SUPERSEDES and SUPERSEDES[x.id].startswith("R2.")
        assert x.id in FIXES and all(FIXES[x.id])
    assert set(DROPPED_SHAPES) <= {x.id for x in FIX3} | EXCLUDED
    assert len(load_fix3()) == 24


def test_battery_classification_of_valid_alternatives() -> None:
    assert is_p("(P) the other policy", "x")
    assert is_p("removal by deleting the minimum and keeping the order of the rest", "removals=0")
    assert not is_p("removal by deleting the minimum and keeping the order of the rest", "removals=1")
    assert is_p("(b-a)//m + 1", "count", "R2.multiples_between") and not is_p("(b-a)//m + 1", "sum", "R2.multiples_between")
    assert is_p("latest start first", "-", "R2.interval_scheduling") and not is_p("latest start first", "-", "R2.cheapest_network")


def test_capacity_readings_a_and_b_differ_only_in_labels() -> None:
    s1, s2 = {"s": "aabxx"}, {"s": "ccdzz"}
    assert canon("R2.run_length", s1, "A") != canon("R2.run_length", s2, "A")
    assert canon("R2.run_length", s1, "B") == canon("R2.run_length", s2, "B")
    d1 = {"letters": ["a", "c", "f", "h"], "length": 2, "ask": "position", "k": None, "word": "fa"}
    d2 = {"letters": ["b", "d", "g", "x"], "length": 2, "ask": "position", "k": None, "word": "gb"}
    assert canon("R2.dictionary_rank", d1, "A") != canon("R2.dictionary_rank", d2, "A")
    assert canon("R2.dictionary_rank", d1, "B") == canon("R2.dictionary_rank", d2, "B")
    c1 = {"cap": 3, "policy": "fifo", "ask": "evicted", "seq": ["apple", "book", "apple"]}
    c2 = {"cap": 3, "policy": "fifo", "ask": "evicted", "seq": ["drum", "flute", "drum"]}
    assert canon("R2.cache_eviction", c1, "A") == canon("R2.cache_eviction", c2, "A")


# ---------------------------------------------------------------- the recorded files (written by r2_fix3_build)
def _manifest() -> dict:  # type: ignore[type-arg]
    p = MAN / "r2_fix3_manifest.json"
    if not p.exists():
        pytest.skip("manifest not built yet")
    return json.loads(p.read_text())  # type: ignore[no-any-return]


def test_manifest_fixtures_and_exclusions_are_consistent() -> None:
    m = _manifest()
    ids = [x["id"] for x in m["revised_shapes"]]
    assert ids == sorted(ids) and len(ids) == 24 and not EXCLUDED & set(ids)
    assert set(m["not_registered"]) == EXCLUDED
    for x in m["revised_shapes"]:
        text = (FX / f"{x['id']}.jsonl").read_text()
        assert hashlib.sha256(text.encode()).hexdigest() == x["fixture_sha256"]
        assert len(text.strip().split("\n")) == 140
    assert not any((FX / f"{i}.jsonl").exists() for i in EXCLUDED)
    assert m["clusters"]["strict_count"] == 36 and m["set_size"] == 40
    cm = json.loads((MAN / "r2_fix3_cluster_map.json").read_text())
    assert cm["cluster_count"] == 36 and not any(i in str(cm["clusters"]) for i in EXCLUDED)
    cap = json.loads((MAN / "r2_fix3_capacity.json").read_text())
    assert cap["G"] == 17 and cap["demand"] == 15130 and not any(i in cap["per_lineage"] for i in EXCLUDED)
