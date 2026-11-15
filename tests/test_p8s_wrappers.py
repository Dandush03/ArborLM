"""ADR-0016 gate 4: the copied wrappers reproduce the frozen ones (registered null provider)."""

import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402
import torch  # noqa: E402
from p8_dry import dry_cell  # noqa: E402

from arborlm import p7b_layout as layout_mod  # noqa: E402
from arborlm import p8_core as core  # noqa: E402
from arborlm import p8_sim  # noqa: E402
from arborlm.io import read_json  # noqa: E402
from arborlm.p7a_trace import synthetic_trace  # noqa: E402
from supplements.p8s import null, preflight  # noqa: E402
from supplements.p8s import sim as ssim  # noqa: E402

EXTRA = {"method", "precondition"}


def _panel_inputs(
    kind: str, label: str
) -> tuple[core.Cell, torch.Tensor, torch.Tensor | None, dict]:
    cell = core.parse_label(label)
    selected, branches = synthetic_trace(kind, 5, queries=128, hot_slots=64)
    cal_selected, cal_branches = synthetic_trace(kind, 6, queries=128, hot_slots=64)
    calibration = layout_mod.CalibrationTrace.declared(cal_selected, cal_branches, kind, label)
    orders, _ = p8_sim.build_p8_layouts(calibration)
    return cell, selected, branches, orders


@pytest.mark.parametrize(
    ("kind", "label"),
    [("flat", "b102-o302-s601-C04"), ("learned_tree", "b102-o302-s602-C07")],
)
def test_simulate_panel_s_equals_frozen_with_registered_provider(kind: str, label: str) -> None:
    cell, selected, branches, orders = _panel_inputs(kind, label)
    for panel in ("A", "B"):
        frozen = p8_sim.simulate_panel(cell, panel, selected, branches, orders)
        for provider in (null.registered_null_provider, null.supplement_null_provider):
            mine = ssim.simulate_panel_s(cell, panel, selected, branches, orders, provider)
            extras = [
                set(e) - set(f)
                for e, f in zip(mine["null_streams"], frozen["null_streams"], strict=True)
            ]
            assert all(x == EXTRA for x in extras)
            stripped = copy.deepcopy(mine)
            for entry in stripped["null_streams"]:
                assert entry.pop("precondition") is False
                assert entry.pop("method").startswith("exact count-preserving")
            assert stripped == frozen


def test_simulate_cell_s_replays_a_dry_cell_through_the_new_wrappers(tmp_path: Path) -> None:
    eval_dir, sim_dir = dry_cell()
    cell = core.parse_label("b101-o301-s601-C03")  # a registered tree cell, random-init checkpoints
    registered = read_json(sim_dir / "sim.json")
    mine = ssim.simulate_cell_s(cell, eval_dir, tmp_path, null.supplement_null_provider)
    verdict = preflight.compare_replay(registered, mine)
    assert verdict["ok"], verdict["problems"]
    assert not any(v["holds"] for v in mine["supplement_null_preconditions"].values())
    assert mine["layouts"]["file_sha256"] == registered["layouts"]["file_sha256"]


def test_replay_comparison_detects_tampering(tmp_path: Path) -> None:
    eval_dir, sim_dir = dry_cell()
    cell = core.parse_label("b101-o301-s601-C03")
    registered = read_json(sim_dir / "sim.json")
    mine = ssim.simulate_cell_s(cell, eval_dir, tmp_path, null.supplement_null_provider)
    bad = copy.deepcopy(mine)
    group = bad["panels"]["A"]["streams"]["actual"]["L-COAX|R2"]["by_c"]["32"]["asc"]
    group["misses_warm"] += 1
    assert not preflight.compare_replay(registered, bad)["ok"]
    bad = copy.deepcopy(mine)
    del bad["panels"]["B"]["null_streams"][0]["precondition"]
    assert not preflight.compare_replay(registered, bad)["ok"]
    bad = copy.deepcopy(mine)
    bad["panels"]["B"]["null_streams"][1]["precondition"] = True
    assert not preflight.compare_replay(registered, bad)["ok"]
    bad = copy.deepcopy(mine)
    bad["unexpected_key"] = 1
    assert not preflight.compare_replay(registered, bad)["ok"]
    bad = copy.deepcopy(mine)
    bad["layouts"]["file_sha256"] = "0" * 64
    assert not preflight.compare_replay(registered, bad)["ok"]
    bad = copy.deepcopy(mine)
    bad["supplementary_extra"] = (
        1  # starts with "supplement" but is neither `supplement` nor `supplement_*`
    )
    assert not preflight.compare_replay(registered, bad)["ok"]
    ok = copy.deepcopy(mine)
    ok["supplement_anything"] = 1
    ok["supplement"] = "ADR-0016"
    assert preflight.compare_replay(registered, ok)["ok"]


def test_supplement_key_rule_is_exactly_w6() -> None:
    assert preflight.is_supplement_key("supplement")
    assert preflight.is_supplement_key("supplement_label")
    assert not preflight.is_supplement_key("supplementary")
    assert not preflight.is_supplement_key("supplements")
    assert not preflight.is_supplement_key("frozen_inputs")
