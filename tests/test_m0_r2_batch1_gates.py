# ruff: noqa: E501
"""R2 batch 1: registry-level checks (own registry, ids, families, determinism across two processes, manifest). Self-checked only."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

from studies.m0 import lineage_gates as lg
from studies.m0.core import REGISTRY, lineages_of
from studies.m0.lineages_r2_common import BATCH1, FAMILY_MODULES, load_batch1

ROOT = Path(__file__).resolve().parents[1]
NEW = load_batch1()


def test_registry_is_separate_ids_unique_and_families_match() -> None:
    assert len(NEW) == len({x.id for x in NEW}) >= 20
    assert not {x.id for x in REGISTRY["R2"]} & {x.id for x in BATCH1}
    assert len(lineages_of("R2")) == 16  # the suite still sees exactly the 16 original lineages
    assert {x.family for x in NEW} == set(FAMILY_MODULES)


def test_builders_have_distinct_signatures() -> None:
    assert len({lg.signature(x.build) for x in NEW}) == len(NEW)


def test_every_builder_documents_its_procedure_and_structured_form() -> None:
    for x in NEW:
        doc = x.build.__doc__ or ""
        assert "structured:" in doc and "Answer" in doc, x.id


def test_generation_is_identical_in_a_second_process() -> None:
    code = (
        "import hashlib, json\n"
        "from studies.m0.core import build_item, stream\n"
        "from studies.m0.lineages_r2_common import load_batch1\n"
        "h = hashlib.sha256()\n"
        "for lin in load_batch1():\n"
        "    for lv in range(7):\n"
        "        r = stream(953820, 'det', lin.id, str(lv))\n"
        "        for i in range(5):\n"
        "            it = build_item(lin, lv, r, 'A', 'x')\n"
        "            h.update(it.to_json().encode())\n"
        "print(h.hexdigest())\n"
    )
    import os

    env = {**os.environ, "PYTHONHASHSEED": "0"}
    a = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, cwd=ROOT, env=env, check=True).stdout.strip()
    env2 = {**os.environ, "PYTHONHASHSEED": "12345"}
    b = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, cwd=ROOT, env=env2, check=True).stdout.strip()
    assert a == b and len(a) == 64


def test_capacity_at_g300_for_two_levels_of_each_lineage() -> None:
    # the full record (all 7 levels, all lineages) is in the manifest; here the cheapest and the hardest core levels
    for x in NEW:
        for lv in (0, 1, 5):
            need = lg.CAPACITY_FACTOR * lg.demand_at_g(lg.G_PROPOSED, lv)
            found, _ = lg.exhibit(x, lv, need)
            assert found >= need, (x.id, lv, found, need)


def test_manifest_matches_the_registry_and_fixtures() -> None:
    m = json.loads((ROOT / "studies" / "m0" / "manifests" / "r2_batch1_manifest.json").read_text())
    assert [e["id"] for e in m["new_lineages"]] == [x.id for x in NEW]
    for e in m["new_lineages"]:
        assert e["capacity_passed_all_levels"] and e["structured_capacity_passed_all_levels"], e["id"]
        fx = ROOT / "studies" / "m0" / "fixtures" / "r2_batch1" / f"{e['id']}.jsonl"
        assert hashlib.sha256(fx.read_bytes()).hexdigest() == e["fixture_sha256"]
        lines = fx.read_text().splitlines()
        assert len(lines) == 140
    assert {c["status"] for c in m["considered_log"]} == {"delivered", "rejected", "deferred"}
