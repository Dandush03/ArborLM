# ruff: noqa: E501
"""R2 fix round 4: the survivors manifest, the hygiene edits and the package copies of the auditors' rules, the measurement harness and the capacity harness (small runs). Self-checks, not independent review."""

from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path
from typing import Any

import pytest

from studies.m0.core import ALL_LEVELS, build_item
from studies.m0.r2_fix3_set import fix3_set
from studies.m0.r2_fix4_set import fix4_set

ROOT = Path(__file__).resolve().parents[1]
M0 = ROOT / "studies" / "m0"
REVIEW = ROOT / "docs" / "reviews" / "m0-lineage-decision-2026-11-25"
MANIFEST: dict[str, Any] = json.loads((M0 / "manifests" / "r2_fix4_survivors.json").read_text())


def test_manifest_covers_the_40_lineages_and_36_strict_clusters() -> None:
    ids = sorted(fix4_set())
    assert len(ids) == 40 and sorted(MANIFEST["lineages"]) == ids
    assert len(MANIFEST["clusters"]) == 36
    assert "R2.chip_toppling" not in ids and "R2.deferred_acceptance_partner" not in ids
    for lid, r in MANIFEST["lineages"].items():
        assert r["status"] in ("SURVIVES", "NOT_REGISTERED"), lid
        assert r["reason"] and r["strict_cluster"] in MANIFEST["clusters"]
        assert sorted(r["per_level_largest_abs_excess"]) == [str(lv) for lv in ALL_LEVELS]
        for v in r["per_level_largest_abs_excess"].values():
            assert v["rule"] != "" or v["largest_abs_excess"] == 0.0


def test_every_survivor_is_within_the_bound_distinct_and_has_capacity() -> None:
    surv = [r for r in MANIFEST["lineages"].values() if r["status"] == "SURVIVES"]
    assert surv and len(surv) == len(MANIFEST["surviving_lineages"])
    for r in surv:
        for lv, v in r["per_level_largest_abs_excess"].items():
            assert v["largest_abs_excess"] <= MANIFEST["shortcut_bound"] == 0.15, (r["id"], lv, v)
            assert all(x <= 0.15 for x in v["by_seed_set"].values())
        assert r["levels_check"] is not None and r["levels_check"]["levels_distinct"], r["id"]
        assert r["capacity"]["checked"] and r["capacity"]["passes_as_written"], r["id"]
        assert r["capacity"]["g_used"] == MANIFEST["G_per_part"] == MANIFEST["G_final"] // 2


def test_dropped_lineages_carry_a_measured_or_cited_reason() -> None:
    dropped = {lid: r for lid, r in MANIFEST["lineages"].items() if r["status"] == "NOT_REGISTERED"}
    assert len(dropped) + len(MANIFEST["surviving_lineages"]) == 40
    for lid in ("gcd_euclid", "permutation_power", "max_subarray_sum", "cache_eviction", "coin_change_min", "count_letter", "palindrome_check", "kth_smallest", "merge_smallest_cost"):
        r = dropped["R2." + lid]
        assert "audit 4" in r["reason"] and "above 0.15" in r["reason"], lid
    assert "R-18" in dropped["R2.subtraction_game"]["reason"]
    assert "(b - a)/m + 1" in dropped["R2.multiples_between"]["reason"]
    for lid, r in dropped.items():
        shortcut = any(v["largest_abs_excess"] > 0.15 for v in r["per_level_largest_abs_excess"].values())
        assert shortcut or "R-18" in r["reason"] or "multiples" in lid or "capacity" in r["reason"], lid


def test_cluster_counts_and_demand_are_consistent() -> None:
    surv_clusters = [k for k, v in MANIFEST["clusters"].items() if v["survives"]]
    assert sorted(surv_clusters) == MANIFEST["surviving_clusters"] and len(surv_clusters) == MANIFEST["surviving_cluster_count"] == MANIFEST["G_final"]
    assert MANIFEST["capacity_consistent_with_G_per_part"] is True
    g = MANIFEST["G_final"] // 2  # G is clusters PER PART (lead's correction)
    assert MANIFEST["demand_at_G_per_part"] == 10 * (-(-4000 // g) + -(-20000 // g) + 100)
    for k in surv_clusters:
        cap = MANIFEST["clusters"][k]["capacity_as_written"]
        assert sorted(cap) == [str(lv) for lv in ALL_LEVELS]
        assert all(c["every_surviving_member_passes_as_written"] and c["demand"] == MANIFEST["demand_at_G_per_part"] for c in cap.values())
    # a cluster survives iff at least one member survives (R-24)
    for k, v in MANIFEST["clusters"].items():
        assert v["survives"] == any(s == "SURVIVES" for s in v["member_status"].values()), k


def test_inputs_are_recorded_with_hashes() -> None:
    for key in ("battery_a4", "battery_f4", "levels", "capacity"):
        assert MANIFEST["inputs"][key] and all(len(x["sha256"]) == 64 for x in MANIFEST["inputs"][key])


# ---------------------------------------------------------------- hygiene


def test_count_letter_and_count_divisible_items_are_unchanged_by_the_sorted_edit() -> None:
    # sha256 over 300 items per level, measured with the code BEFORE the edit `for ch in sorted(set(w))` (PYTHONHASHSEED 0, 1 and 7 agreed): scratch hyg_before.txt
    want = {
        "R2.count_divisible": "5b5f4adc6e42f4528f88d0b87173557506eba5a019ef8e0b1062909a2404c5c0",
        "R2.count_letter": "ec8e4045992912e156bdcfb97a9cd7cc876b37e93f1700325a9eed0abf78a81c",
    }
    s = fix3_set()
    for lid, h in want.items():
        hh = hashlib.sha256()
        for lv in ALL_LEVELS:
            r = random.Random(f"fix4-hyg|{lid}|{lv}")
            for _ in range(300):
                it = build_item(s[lid] if lid in s else _fix3_only(lid), lv, r, "A", "x")
                hh.update((it.question + "\x00" + it.answer + "\x00" + repr(sorted(it.structured.items())) + "\n").encode())
        assert hh.hexdigest() == h, lid


def _fix3_only(lid: str) -> Any:
    from studies.m0.lineages_r2_fix3 import load_fix3

    return next(x for x in load_fix3() if x.id == lid)


def test_the_fix3_battery_no_longer_imports_from_the_review_folder() -> None:
    text = (M0 / "r2_fix3_battery.py").read_text()
    assert "import a3_heur" not in text.replace("r2_fix4_a3_heur as a3_heur", "")
    assert "r2_fix4_a3_heur" in text and "sys.path.append" not in text


@pytest.mark.parametrize(
    ("copy", "orig"),
    [("r2_fix4_a3_solvers.py", "audit3_r2/a3_solvers.py"), ("r2_fix4_a3_heur.py", "audit3_r2/a3_heur.py"), ("r2_fix4_a4_heur.py", "audit4_r2/a4_heur.py")],
)
def test_package_copies_of_the_auditors_files_are_faithful(copy: str, orig: str) -> None:
    c = (M0 / copy).read_text()
    o = (REVIEW / orig).read_text()
    c_lines = c.split("\n")
    head = [x for x in c_lines[:5] if x.startswith("# COPY")]
    assert head and hashlib.sha256((REVIEW / orig).read_bytes()).hexdigest() in head[0]
    body = "\n".join(c_lines[c_lines.index("# ruff: noqa") :])
    if copy == "r2_fix4_a3_heur.py":  # the four listed edits, undone
        body = body.replace("from studies.m0 import r2_fix4_a3_solvers as S", "import a3_solvers as S").replace("sorted(set(t))", "set(t)").replace("sorted(set(a))", "set(a)")
    assert body == o


def test_copies_import_only_the_standard_library_and_the_package() -> None:
    import ast
    import sys

    for f in ("r2_fix4_a3_solvers.py", "r2_fix4_a3_heur.py", "r2_fix4_a4_heur.py", "r2_fix4_battery.py", "r2_fix4_levels.py", "r2_fix4_capacity.py", "r2_fix4_build.py", "r2_fix4_set.py", "lineages_r2_fix4.py"):
        for node in ast.walk(ast.parse((M0 / f).read_text())):
            names = [a.name.split(".")[0] for a in node.names] if isinstance(node, ast.Import) else [node.module.split(".")[0]] if isinstance(node, ast.ImportFrom) and node.module and node.level == 0 else []
            for n in names:
                assert n in sys.stdlib_module_names or n in ("torch", "studies"), (f, n)


def test_no_hash_builtin_and_no_set_iteration_in_the_new_files() -> None:
    import ast

    for f in M0.glob("*fix4*.py"):
        for node in ast.walk(ast.parse(f.read_text())):
            assert not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "hash"), f.name
            its = [node.iter] if isinstance(node, ast.For | ast.comprehension) else []
            for it in its:
                assert not isinstance(it, ast.Set | ast.SetComp), (f.name, it.lineno)
                assert not (isinstance(it, ast.Call) and isinstance(it.func, ast.Name) and it.func.id in ("set", "frozenset")), (f.name, it.lineno)


# ---------------------------------------------------------------- the harnesses (small runs)


def test_klass_follows_the_auditors_classes() -> None:
    from studies.m0.r2_fix4_battery import klass

    assert klass("[a3] digit-root rule (P)", "-", 0) == "P"
    assert klass("[mine] t mod (n-1) applications (cycle length assumed n-1)", "-", 0) == "construct"
    assert klass("[a3] first failing check position only", "-", 2) == "partial"
    assert klass("most frequent answer (train draw)", "-", 0) == "cue"
    assert klass("[a3] ignore reverses", "-", 0) == "artifact"


def test_battery_smoke_run_has_every_level_and_the_mode_rule() -> None:
    from studies.m0.r2_fix4_battery import run_one, worst

    lid, res = run_one(("R2.caesar_shift", 30, "f4"))
    assert lid == "R2.caesar_shift" and sorted(res) == [str(lv) for lv in ALL_LEVELS]
    assert all("most frequent answer (train draw)" in ent["rules"] for rows in res.values() for ent in rows.values())
    w = worst({"lineages": {lid: res}})
    assert sorted(w[lid]) == [str(lv) for lv in ALL_LEVELS]


def test_capacity_demand_formula_and_a_small_pool_as_written() -> None:
    from studies.m0.r2_fix4_capacity import demand, run_one

    assert demand(18) == 14350 and demand(17) == 15130 and demand(6) == 41010
    lid, res = run_one(("R2.digit_root", 60))
    assert lid == "R2.digit_root" and res["shortfalls"] == [] and all(v == 60 for v in res["supplied"].values())


def test_capacity_reports_a_shortfall_when_the_space_is_too_small(monkeypatch: pytest.MonkeyPatch) -> None:
    from studies.m0 import r2_fix4_set
    from studies.m0.core import Built, Lineage
    from studies.m0.r2_fix4_capacity import run_one

    def tiny(level: int, r: random.Random) -> Built:
        n = r.randint(1, 5)  # five distinct texts at every level
        return Built(f"What is {n}?", {"n": n}, str(n), "number", None)

    monkeypatch.setattr(r2_fix4_set, "fix4_set", lambda: {"R2.tiny": Lineage("R2.tiny", "R2", "x", tiny)})
    lid, res = run_one(("R2.tiny", 30))
    # one pool over the 7 levels: the text hash is shared across the levels, so the five texts are used up by the first level that asks
    assert lid == "R2.tiny" and res["shortfalls"] and sum(res["supplied"].values()) == 5
    assert max(res["supplied"].values()) == 5


def test_the_capacity_harness_restores_core_part_lineages() -> None:
    from studies.m0 import core
    from studies.m0.r2_fix4_capacity import run_one

    before = core.part_lineages
    run_one(("R2.digit_root", 20))
    assert core.part_lineages is before
