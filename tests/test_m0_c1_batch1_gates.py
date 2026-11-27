# ruff: noqa: E501
"""C1 batch 1: the batch's bookkeeping. Self-checked only. No threshold is registered here: the shortcut numbers are measurements; only
the capacity factor (10 at the G = 300 demand) is a rule of ADR-0033."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

from studies.m0 import lineage_gates as lg
from studies.m0.c1grammar import render, run_isolated
from studies.m0.core import ALL_LEVELS, REGISTRY, build_item, lineages_of, stream
from studies.m0.lineages_c1_common import BATCH1, FAMILY_MODULES, load_batch1
from studies.m0.solvers_c1 import c1_trace

ROOT = Path(__file__).resolve().parents[1]
NEW = load_batch1()
FIX = ROOT / "studies" / "m0" / "fixtures" / "c1_batch1"
MANIFEST = ROOT / "studies" / "m0" / "manifests" / "c1_batch1_manifest.json"
SHORTCUTS = ROOT / "studies" / "m0" / "manifests" / "c1_batch1_shortcuts.json"


def test_ids_are_unique_in_a_private_registry_and_every_family_module_is_used() -> None:
    assert len(NEW) == len({x.id for x in NEW}) == len(BATCH1) >= 20
    core_ids = {x.id for x in REGISTRY["C1"]}
    assert not core_ids & {x.id for x in NEW}
    assert len(lineages_of("C1")) == 14  # the suite's solver tests still see exactly the 14 original lineages
    assert {x.family for x in NEW} == set(FAMILY_MODULES)
    assert all(x.eval == "C1" and x.id.startswith("C1.") for x in NEW)


def test_signatures_are_distinct_between_old_and_new_builders() -> None:
    sigs = [lg.signature(x.build) for x in [*lineages_of("C1"), *NEW]]
    assert len(set(sigs)) == len(sigs)


def test_generation_is_identical_in_two_processes() -> None:
    code = (
        "import hashlib\n"
        "from studies.m0.core import build_item, stream\n"
        "from studies.m0.lineages_c1_common import load_batch1\n"
        "h = hashlib.sha256()\n"
        "for lin in load_batch1():\n"
        "    for lv in range(7):\n"
        "        r = stream(953703, 'two-process', lin.id, str(lv))\n"
        "        for i in range(5):\n"
        "            it = build_item(lin, lv, r, 'A', 'x')\n"
        "            h.update((it.question + '|' + it.answer).encode())\n"
        "print(h.hexdigest())\n"
    )
    env = {**os.environ, "PYTHONHASHSEED": "0", "PYTHONPATH": str(ROOT)}
    outs = [subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, cwd=ROOT, env=env, check=True).stdout.strip() for _ in range(2)]
    assert outs[0] == outs[1] and len(outs[0]) == 64


def test_capacity_exhibit_at_a_light_demand_for_every_lineage_and_level() -> None:
    # the full registered demand (1,800 per core level) was exhibited by studies.m0.c1_batch1_build and is recorded in the manifest; here a light 200
    for lin in NEW:
        for lv in ALL_LEVELS:
            found, _ = lg.exhibit(lin, lv, 200)
            assert found >= 200, (lin.id, lv, found)


def test_fixtures_are_complete_distinct_hash_matched_and_agree_with_both_checkers() -> None:
    manifest = json.loads(MANIFEST.read_text())
    by_id = {m["id"]: m for m in manifest["new_lineages"]}
    assert set(by_id) == {x.id for x in NEW}
    for lin in NEW:
        raw = (FIX / f"{lin.id}.jsonl").read_bytes()
        assert hashlib.sha256(raw).hexdigest() == by_id[lin.id]["fixture_sha256"]
        rows = [json.loads(x) for x in raw.decode().splitlines()]
        assert len(rows) == 140
        assert {lv: sum(1 for r in rows if r["level"] == lv) for lv in ALL_LEVELS} == dict.fromkeys(ALL_LEVELS, 20)
        assert len({r["question"] for r in rows}) == 140
        srcs = [render(r["structured"]["program"]) for r in rows]
        assert all(r["question"].split("\n\n")[1] == s for r, s in zip(rows, srcs, strict=True))
        run1, run2 = run_isolated(srcs), run_isolated(srcs)
        for r, a, b in zip(rows, run1, run2, strict=True):
            assert a["out"] == b["out"] == r["answer"] == c1_trace(r["structured"]), r["id"]
            assert r["answer_type"] == "line" and r["k"] is None and set(r["structured"]) == {"program"}


def test_manifest_records_capacity_and_the_shortcut_check_for_every_lineage() -> None:
    manifest = json.loads(MANIFEST.read_text())
    for m in manifest["new_lineages"]:
        assert m["capacity"]["capacity_passed_all_levels"], m["id"]
        assert all(r["found"] >= r["need"] for r in m["capacity"]["capacity_gate_g300"])
        assert m["capacity"]["up_to_renaming_passed_all_levels"], m["id"]
        assert m["strict_confidence"] in ("clear", "borderline")
    sc = json.loads(SHORTCUTS.read_text())
    assert sc["per_level"] == 2000 and set(sc["lineages"]) == {x.id for x in NEW}
    assert all(len(v["levels"]) == 7 and all(r["n"] == 2000 for r in v["levels"].values()) for v in sc["lineages"].values())
    assert manifest["counts"]["new_delivered"] == len(NEW)
    assert all(e["status"] in ("delivered", "rejected", "held_back", "blocked") for e in manifest["log"])


def test_the_levels_are_graded_by_trace_size_where_measured() -> None:
    # reserve level 0 is not larger than level 6 for any lineage (median tree-walker ticks over 100 items each)
    from studies.m0.solvers_c1 import _Interp

    for lin in NEW:
        med = {}
        for lv in (0, 6):
            r = stream(953704, "ticks", lin.id, str(lv))
            vals = []
            for _ in range(60):
                it = build_item(lin, lv, r, "A", "t")
                w = _Interp()
                w.run(it.structured["program"], {})
                vals.append(w.steps)
            med[lv] = sorted(vals)[len(vals) // 2]
        assert med[0] < med[6], (lin.id, med)
