"""P8 simulation: hand-computed statistics, calibration-only layouts, null seeds, a dry-run cell."""

import os
from fractions import Fraction
from pathlib import Path

import pytest
import torch
from p8_dry import dry_cell

from arborlm import p7a_core as a_core
from arborlm import p7b_core as b_core
from arborlm import p7b_layout as layout_mod
from arborlm import p7b_sim as sim
from arborlm import p8_core as core
from arborlm import p8_sim
from arborlm.io import write_json


def _rows_with(special: dict[int, list[int]], n: int) -> torch.Tensor:
    rows = []
    for i in range(n):
        rows.append(special.get(i, [1000 + 8 * i + j for j in range(8)]))
    return torch.tensor(rows)


def test_temporal_reuse_hand_example() -> None:
    # context 1: t1 repeats 4 of t0; t2 repeats 4 of {t0,t1}; t10 repeats {0,1} of window t2..t9
    special = {
        0: list(range(8)),
        1: [0, 1, 2, 3, 8, 9, 10, 11],
        2: [0, 1, 8, 9, 20, 21, 22, 23],
        10: list(range(8)),
    }
    first = _rows_with(special, 64)
    second = torch.tensor([[5000 + 8 * i + j for j in range(8)] for i in range(64)])
    result = p8_sim.temporal_reuse(torch.cat([first, second]))
    assert result["hits"] == 4 + 4 + 2 and result["queries_counted"] == 126
    assert result["value"] == pytest.approx(10 / (8 * 126))
    with pytest.raises(ValueError):
        p8_sim.temporal_reuse(first[:10])


def test_temporal_reuse_window_edge() -> None:
    # a slot set repeated exactly 9 queries later falls outside the 8-query window
    special = {0: list(range(8)), 9: list(range(8)), 8: list(range(8))}
    result = p8_sim.temporal_reuse(_rows_with(special, 64))
    # t8 repeats t0 (distance 8, inside); t9 repeats t8 (inside) and t0 (outside)
    assert result["hits"] == 8 + 8


def test_branch_persistence_hand_example() -> None:
    rows = [[0, 1], [0, 1], [1, 0], *([[2, 3]] * 61)]
    branches = torch.tensor(rows)
    r = p8_sim.branch_persistence(branches)
    assert (r["pairs"], r["same_top"], r["same_pair"]) == (63, 61, 62)
    order = [0, 2, 1, *range(3, 64)]
    r2 = p8_sim.branch_persistence(branches, order)
    assert (r2["same_top"], r2["same_pair"]) == (60, 62)
    assert r2["top_fraction"] == pytest.approx(60 / 63)


def test_m_fraction_exact() -> None:
    record = {
        "queries": 32768,
        "streams": {
            "actual": {
                "L-COAX|R2": {
                    "by_c": {"32": {"asc": {"misses_warm": 1000, "first_touch_warm": 40}}}
                }
            }
        },
    }
    assert p8_sim.m_fraction(record, "actual", "L-COAX", 2, "asc") == Fraction(960, 16384)


def _small_trace(
    kind: str, seed: int, queries: int = 128
) -> tuple[torch.Tensor, torch.Tensor | None]:
    from arborlm.p7a_trace import synthetic_trace

    return synthetic_trace(kind, seed, queries=queries, hot_slots=64)


def test_layouts_only_from_calibration() -> None:
    selected, branches = _small_trace("learned_tree", 3)
    evaluation = sim.EvaluationTrace(selected, branches, "learned_tree", "x", "A")
    with pytest.raises(TypeError):
        p8_sim.build_p8_layouts(evaluation)  # type: ignore[arg-type]
    calibration = layout_mod.CalibrationTrace.declared(selected, branches, "learned_tree", "x")
    with pytest.raises(TypeError):
        p8_sim.simulate_trace(calibration, {}, {})  # type: ignore[arg-type]
    orders, meta = p8_sim.build_p8_layouts(calibration)
    assert set(orders) == {
        "L-ID",
        "L-FREQ",
        *(f"{n}|R{r}" for n in ("L-COAX", "L-BCOAX", *b_core.L_PCOAX) for r in (2, 8)),
    }
    assert all(sorted(o) == list(range(core.SLOTS)) for o in orders.values())
    assert meta["built_from"].startswith("calibration")
    flat = layout_mod.CalibrationTrace.declared(_small_trace("flat", 4)[0], None, "flat", "y")
    assert not any("L-BCOAX" in k for k in p8_sim.build_p8_layouts(flat)[0])
    # the hashes are the ADR-0014 canonical hashes
    table = p8_sim.layout_hashes(orders)
    assert table["L-COAX|R2"] == b_core.canonical_hash(orders["L-COAX|R2"], 2)
    assert table["L-ID|R8"] == b_core.canonical_hash(list(range(core.SLOTS)), 8)


def test_null_seeds_and_plan_on_small_trace() -> None:
    assert p8_sim.PANEL_SEEDS == {"A": (91331, 91332, 91333), "B": (91341, 91342, 91343)}
    cell = core.parse_label("b102-o302-s602-C07")
    selected, branches = _small_trace("learned_tree", 5)
    calibration = layout_mod.CalibrationTrace.declared(
        _small_trace("learned_tree", 6)[0],
        _small_trace("learned_tree", 6)[1],
        cell.variant,
        cell.label,
    )
    orders, _ = p8_sim.build_p8_layouts(calibration)
    for panel, seeds in p8_sim.PANEL_SEEDS.items():
        rec = p8_sim.simulate_panel(cell, panel, selected, branches, orders)
        assert [n["replicate_seed"] for n in rec["null_streams"]] == list(seeds)
        assert [n["generator_seed"] for n in rec["null_streams"]] == [
            s * 1000 + cell.index for s in seeds
        ]
        counts = a_core.selection_counts(selected)
        expect, _ = b_core.null_streams(counts, seeds, cell.index)
        assert (
            rec["null_streams"][0]["stream_sha256"]
            == a_core.frequency_matched_detail(counts, seeds[0], cell.index, queries=128)[1][
                "stream_sha256"
            ]
        )
        assert len(expect) == 3
        streams = rec["streams"]
        assert set(streams["actual"]) == {
            f"{n}|R{r}" for n in ("L-COAX", "L-BCOAX", *b_core.L_PCOAX) for r in (2, 8)
        } | {f"{n}|R{r}" for n in ("L-ID", "L-FREQ") for r in (2, 8)}
        for s in ("null_1", "null_2", "null_3", "order_shuffled"):
            assert set(streams[s]) == {f"{n}|R{r}" for n in ("L-FREQ", "L-COAX") for r in (2, 8)}
        for group in streams["actual"].values():
            assert set(group["by_c"]) in ({"32"}, {"8"})
            (counts_by_tie,) = group["by_c"].values()
            assert set(counts_by_tie) == {"asc", "desc"}
        assert rec["branch_persistence"]["actual"]["pairs"] == 126
        assert set(rec["temporal_reuse"]) == {
            "actual",
            "order_shuffled",
            "null_1",
            "null_2",
            "null_3",
        }


def test_registered_stage_requires_reproduction_record(tmp_path: Path) -> None:
    with pytest.raises(b_core.GateError, match="--freeze-commit"):
        p8_sim.run_stage(tmp_path, out_root=tmp_path, dry_run=False)
    bogus = tmp_path / "r.json"
    write_json(bogus, {"schema": p8_sim.SCHEMA_REPRO, "verdict": "DIFFERENT", "source_sha256": "x"})
    with pytest.raises(b_core.GateError):
        p8_sim.check_reproduction_record(bogus)


def test_dry_cell_pipeline_records() -> None:
    eval_dir, sim_dir = dry_cell()
    import json

    record = json.loads((sim_dir / "sim.json").read_text())
    assert record["variant"] == "learned_tree" and set(record["panels"]) == {"A", "B"}
    for panel in ("A", "B"):
        assert record["panels"][panel]["queries"] == core.EVAL_QUERIES
    ev = json.loads((eval_dir / "eval.json").read_text())
    assert (
        ev["digests"]["backbone_unchanged"]
        and ev["digests"]["fresh_restore_equals_evaluated_state"]
    )
    assert record["eval_json_sha256"] == __import__("arborlm.io", fromlist=["x"]).file_sha256(
        eval_dir / "eval.json"
    )


@pytest.mark.skipif(
    not Path(os.environ.get("ARBORLM_EXPERIMENTS_ROOT", "experiments")).is_dir(),
    reason="local P7-A traces not present",
)
def test_p7b_reproduction_gate() -> None:
    record = p8_sim.p7b_reproduction(
        Path(os.environ.get("ARBORLM_EXPERIMENTS_ROOT", "experiments")), Path.cwd()
    )
    assert record["verdict"] == "ALL_EQUAL"
