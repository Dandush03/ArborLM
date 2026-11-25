# ruff: noqa: E501
"""Per-item storage, router snapshots and an independent recomputation from the stored records (ADR-0025 section 8.6; audit R5; rulings 8 and 11), at test size on a tiny world. Self-check only."""

import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402
from p10is2_engine_fixtures import CFG_T, world  # noqa: E402
from p10is2_partt_e2e_world import fake_gloss_bank  # noqa: E402

from studies.p10is2 import labels as L  # noqa: E402
from studies.p10is2 import (  # noqa: E402
    partt_items,
    partt_recompute,
    partt_rehearsal,
    partt_run,
    scoring,
)
from studies.p10is2.common import core  # noqa: E402
from studies.p10is2.quantities import Quantities, Registry, Thresholds  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def stored(tmp_path_factory: pytest.TempPathFactory):  # type: ignore[no-untyped-def]
    d = tmp_path_factory.mktemp("items")
    w = world(updates=2, n_reps=1)
    gloss = fake_gloss_bank(w, {c: w.streams[0].t[c] for c in core.TASKS})
    partt_run.train_all(w, d / "snapshots", None, 2, replicates=(0,))
    scoring.ITEMS.clear()
    records = partt_run.reference_task(w)
    rec, _side = partt_run.score_replicate(w, 0, d / "snapshots", gloss, routers_mode="save")
    records.update(rec)
    items = scoring.take_items()
    return w, d, gloss, scoring.registry_from_reads(records), items


def test_the_stored_items_reproduce_every_item_based_figure_without_the_engine(stored) -> None:  # type: ignore[no-untyped-def]
    _w, _d, _gloss, reg, items = stored
    tree = ast.parse((ROOT / "studies/p10is2/partt_items.py").read_text())
    imported = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            imported |= {a.name.split(".")[0] for a in n.names}
        elif isinstance(n, ast.ImportFrom) and n.module:
            imported.add(n.module.split(".")[0])
    assert imported <= {"math", "collections", "typing"}  # no model, no torch, no study code: the recomputation reads the stored records only
    cmp = partt_items.compare(reg.values, items)
    assert cmp["differ"] == [] and cmp["checked"] > 100 and all(k.startswith("E-table|") and "|em:" in k for k in cmp["not_in_registry"])  # E-table registers its s: reads only
    assert all(k.split("|")[-1].startswith(("gen:", "modification")) for k in cmp["not_covered_by_items"]), cmp["not_covered_by_items"][:5]  # only the reads that rest on no item list
    sample = next(k for k in items if k.startswith("M-append|AB|0|s:E_A"))
    assert items[sample]["sequences"] and len(items[sample]["items"]) == len(items[sample]["sequences"]) == len(items[sample]["exact"])  # scores, greedy sequences and exact flags per item


def test_a_cells_label_derived_from_the_stored_records_equals_the_one_from_the_registry(stored) -> None:  # type: ignore[no-untyped-def]
    _w, _d, _gloss, reg, items = stored
    again = {**reg.values, **partt_items.recompute_registry(items)}  # the item-based figures from the items alone; the scalar-only reads (GEN, modification) as stored
    a, _ = partt_rehearsal.fill_registry(reg.values)
    b, _ = partt_rehearsal.fill_registry(again)
    la = L.derive_all(Quantities(Registry(a), Thresholds.from_config(CFG_T)))
    lb = L.derive_all(Quantities(Registry(b), Thresholds.from_config(CFG_T)))
    labels = lambda d: {k: v["label"] for k, v in d.items() if isinstance(v, dict) and "label" in v}  # noqa: E731
    assert labels(la) == labels(lb) and labels(la)["ACQUISITION"]


def test_routers_are_snapshotted_with_hashes_and_the_recomputation_rereads_them(stored) -> None:  # type: ignore[no-untyped-def]
    w, d, gloss, reg, items = stored
    routers = scoring.load_routers(d / "snapshots" / "routers" / "r0")
    assert set(routers) == {("A",), ("B",), ("A", "B")} and all(r.state_hash() for r, _ in routers.values())
    rec = partt_recompute.recompute(w, d, gloss, reg.values, None, replicates=(0,), stored_items=items)  # routers_mode "load"
    assert rec["ok"] is True and rec["routers_mode"] == "load" and rec["item_records_compared"] == len(items)
    bad = {k: ({**v, "items": [x + 0.5 for x in v["items"]]} if k.startswith("M1|AB|0|s:E_A") else v) for k, v in items.items()}
    assert partt_recompute.recompute(w, d, gloss, reg.values, None, replicates=(0,), stored_items=bad)["ok"] is False  # a stored per-item record that differs from the recomputation is an engineering stop
    f = next((d / "snapshots" / "routers" / "r0").glob("*.pt"))
    keep = f.read_bytes()
    f.write_bytes(keep + b"x")
    with pytest.raises(core.StageRefused, match="router manifest"):
        scoring.load_routers(d / "snapshots" / "routers" / "r0")
    f.write_bytes(keep)
    with pytest.raises(FileExistsError):
        scoring.save_routers(routers, d / "snapshots" / "routers" / "r0")  # a snapshot is never overwritten
