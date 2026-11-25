# ruff: noqa: E501
"""C1 batch 1, revision 2: fixtures in the new directory, the manifest and the recorded measurements. Self-checked only; no threshold is registered."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from studies.m0.c1grammar import render, run_isolated
from studies.m0.core import ALL_LEVELS, lineages_of
from studies.m0.lineages_c1_common import load_batch1
from studies.m0.lineages_c1_rev2 import PROPOSED, SUPERSEDES, load_rev2
from studies.m0.solvers_c1 import c1_trace

ROOT = Path(__file__).resolve().parents[1]
M = ROOT / "studies" / "m0"
MANIFEST = json.loads((M / "manifests" / "c1_batch1_rev2_manifest.json").read_text())


def test_fixtures_are_in_the_new_directory_hash_matched_complete_and_agree_with_both_checkers() -> None:
    by_id = {r["id"]: r for r in MANIFEST["revised"]}
    assert set(by_id) == {x.id for x in load_rev2()}
    for lid, rec in sorted(by_id.items()):
        raw = (M / "fixtures" / "c1_batch1_rev2" / f"{lid}.jsonl").read_bytes()
        assert hashlib.sha256(raw).hexdigest() == rec["fixture"]["sha256"]
        rows = [json.loads(x) for x in raw.decode().splitlines()]
        assert len(rows) == 140 and len({r["question"] for r in rows}) == 140
        assert {lv: sum(1 for r in rows if r["level"] == lv) for lv in ALL_LEVELS} == dict.fromkeys(ALL_LEVELS, 20)
        assert all(r["proposed"] == (lid in PROPOSED) for r in rows)
        srcs = [render(r["structured"]["program"]) for r in rows]
        run1, run2 = run_isolated(srcs), run_isolated(srcs)  # every fixture item twice in the isolated runner, then the existing second solver
        for r, a, b in zip(rows, run1, run2, strict=True):
            assert a["out"] == b["out"] == r["answer"] == c1_trace(r["structured"]), r["id"]


def test_the_old_fixtures_are_kept_and_marked_superseded() -> None:
    note = (M / "fixtures" / "c1_batch1" / "SUPERSEDED.txt").read_text()
    for old in sorted(set(SUPERSEDES.values())):
        assert old in note
        assert (M / "fixtures" / "c1_batch1" / f"{old}.jsonl").exists()


def test_manifest_records_clusters_capacity_and_not_registered_shapes() -> None:
    c = MANIFEST["clusters"]
    assert c["strict_map_over_39"]["count"] == 28 and c["strictest_over_39"]["count"] == 22
    assert c["current_set"]["lineages"] == 40 and c["current_set"]["strict_clusters"] == 29 and c["current_set"]["strictest_clusters"] == 23
    cap = MANIFEST["capacity"]
    assert cap["g_part"] == 20 and cap["need_even"]["3"] == 10 * (1200 // 5 + 100)
    existing = {x.id for x in lineages_of("C1")} | {x.id for x in load_batch1()}
    assert {b["lineage"] for b in cap["below_need_even"]} <= {"C1.nested_pairs", "C1.list_build", "C1.cond_chain"}  # only existing lineages fall short
    assert {b["lineage"] for b in cap["below_need_even"]} <= existing
    assert len(MANIFEST["not_registered"]) >= 6
    assert set(MANIFEST["superseded_kept_on_file"]) == set(SUPERSEDES.values())


def test_the_shortcut_battery_covers_every_lineage_old_and_revised_at_2000_per_level() -> None:
    sc = json.loads((M / "manifests" / "c1_batch1_rev2_shortcuts.json").read_text())
    assert sc["per_level"] == 2000
    assert set(sc["lineages"]) == {x.id for x in load_batch1()} | {x.id for x in load_rev2()}
    for v in sc["lineages"].values():
        assert len(v["levels"]) == 7 and all(lv["n"] == 2000 for lv in v["levels"].values())
