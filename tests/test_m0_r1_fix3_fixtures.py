# ruff: noqa: E501
"""R1 fix round 3: the fixtures, schema document and manifests exist for the registered shapes only (ruling R-12), match the code, and are reproducible."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from studies.m0 import lineage_gates as lg
from studies.m0 import lineages_r1_fix3_clusters as c3
from studies.m0.core import stream
from studies.m0.lineages_r1_fix3_common import load_fix3

ROOT = Path(__file__).resolve().parents[1]
FX = ROOT / "studies/m0/fixtures/r1_fix3"
MAN = ROOT / "studies/m0/manifests"
REG = [x for x in load_fix3() if x.id not in c3.NOT_REGISTERED_V3]


def test_fixtures_exist_for_exactly_the_registered_new_shapes_with_20_items_per_level():
    files = sorted(p.name for p in FX.glob("R1.*.jsonl"))
    assert files == sorted(f"{x.id}.jsonl" for x in REG) and len(files) == 27
    for p in FX.glob("R1.*.jsonl"):
        lines = p.read_text().splitlines()
        assert len(lines) == 140
        rows = [json.loads(line) for line in lines]
        assert sorted({r["level"] for r in rows}) == list(range(7))
        assert all(r["lineage"] == p.stem for r in rows)


def test_no_fixture_schema_or_manifest_entry_for_a_not_registered_shape():
    schema = (ROOT / "studies/m0/fixtures/R1_FIX3_SCHEMA.md").read_text()
    man = json.loads((MAN / "r1_fix3_manifest.json").read_text())
    cm = json.loads((MAN / "r1_fix3_clusters.json").read_text())
    for lid in c3.NOT_REGISTERED_V3:
        assert f"### `{lid}`" not in schema
        assert lid not in man["shapes"]
        assert all(lid not in members for members in cm["clusters"].values())
        assert not (FX / f"{lid}.jsonl").exists()
    for x in REG:
        assert f"### `{x.id}`" in schema


def test_manifest_hashes_match_the_files_and_the_map_matches_the_code():
    man = json.loads((MAN / "r1_fix3_manifest.json").read_text())
    for x in REG:
        text = (FX / f"{x.id}.jsonl").read_text()
        assert hashlib.sha256(text.encode()).hexdigest() == man["shapes"][x.id]["fixture_sha256"]
        assert man["shapes"][x.id]["signature"] == lg.signature(x.build)  # the builder in the file is the builder that produced the fixture
    cm = json.loads((MAN / "r1_fix3_clusters.json").read_text())
    assert cm["n_clusters"] == len(c3.cluster_table_v3()) == 23 and cm["n_shapes"] == 37
    assert cm["clusters"] == {cid: sorted(m.id for m in ms) for cid, ms in sorted(c3.cluster_table_v3().items())}


def test_fixtures_are_reproducible_in_a_second_pass():
    for lid in ("R1.order_compare_r5", "R1.seating_row_r5", "R1.temporal_critical_path_r5"):
        lin = next(x for x in REG if x.id == lid)
        lines = []
        for lv in range(7):
            r = stream(lg.STAT_SEED, "fixture", lin.id, str(lv))
            for i in range(20):
                it = lg.build_item(lin, lv, r, "A", f"{lin.id}/fixture/{lv}/{i}")
                lines.append(json.dumps({"id": it.id, "lineage": it.lineage, "level": it.level, "question": it.question, "structured": it.structured, "answer": it.answer, "answer_type": it.answer_type, "k": it.k}, sort_keys=True, ensure_ascii=True))
        assert "\n".join(lines) + "\n" == (FX / f"{lid}.jsonl").read_text()


def test_superseded_note_lists_every_not_registered_shape():
    note = (FX / "SUPERSEDED.txt").read_text()
    for lid in c3.NOT_REGISTERED_V3:
        assert lid in note
