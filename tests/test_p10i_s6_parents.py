# ruff: noqa: E501
"""P10IS6 parent adapter (ADR-0031 section 7): equal to the whitelisted code path for the registered seeds, usable for new seeds, deterministic. Synthetic train rows, few updates. Self-check only."""

import copy

import pytest
import torch

from studies.p10i_s6 import core, parents, testing

CFG = core.load_config()
ROWS = testing.random_rows(4096, core.test_seed(10, CFG))
STEPS = 6


def reference_digest(b: int, o: int, steps: int) -> str:
    """The same recipe through the code paths that carry the whitelists: ``p2_config.Cell`` and ``p2_data.order_ids``."""
    from arborlm.longer_training import _isolated_rng
    from arborlm.optimization_followup import _optimizer, _training_step
    from arborlm.p2_config import CONTROL, Cell
    from arborlm.p2_data import order_ids
    from arborlm.p2_model import FollowupModel
    from arborlm.p4_model import backbone_digest, extract

    ordered = ROWS[:2048][order_ids(o)]
    with _isolated_rng():
        m = FollowupModel(Cell(b, 201, o, CONTROL))
        opt = _optimizer(m)
        for s in range(1, steps + 1):
            off = ((s - 1) * 8) % 2048
            _training_step(m, opt, ordered[off : off + 8], s)
        return backbone_digest(extract(m))


@pytest.mark.parametrize("p", [0, 4, 8])
def test_adapter_equals_the_whitelisted_path_for_registered_seeds(p: int) -> None:
    b, o = core.old_parent_ids(p)
    assert torch.equal(parents.order_permutation(o), __import__("arborlm.p2_data", fromlist=["order_ids"]).order_ids(o))
    _, d = parents.train_backbone(b, o, ROWS, steps=STEPS, control_memory=201)
    assert d == reference_digest(b, o, STEPS)


def gate_record(steps: int = STEPS) -> dict:
    rec = {p: reference_digest(*core.old_parent_ids(p), steps) for p in range(9)}
    return parents.identity_gate(core.repo_root(), ROWS, CFG, steps=steps, recorded=rec)


def test_new_parent_path_without_control_memory_equals_the_old_recipe() -> None:
    """Ruling 12 / G9: the control memory is not constructed for new parents and the backbone is the same, bitwise (so the identity gate passes on the new-parent path and 201 is never re-used)."""
    for p in (0, 4):
        b, o = core.old_parent_ids(p)
        assert parents.train_backbone(b, o, ROWS, steps=STEPS, control_memory=None)[1] == reference_digest(b, o, STEPS) == parents.train_backbone(b, o, ROWS, steps=STEPS, control_memory=201)[1]


def test_identity_gate_passes_fails_and_names_the_declared_reuse_only_when_needed() -> None:
    g = gate_record()
    assert g["passed"] is True and len(g["parents"]) == 9 and g["control_memory"] is None and g["declared_reuse"] is None and [a["all_nine_equal"] for a in g["attempts"]] == [True]
    rec = {p: reference_digest(*core.old_parent_ids(p), STEPS) for p in range(9)}
    bad = dict(rec)
    bad[3] = "0" * 64
    f = parents.identity_gate(core.repo_root(), ROWS, CFG, steps=STEPS, recorded=bad)
    assert f["passed"] is False and f["control_memory"] is None and len(f["attempts"]) == 2  # both paths were tried and neither reproduces the wrong record
    assert parents.require_identity(g) is None
    for broken in (None, f, {**g, "passed": False}, {**g, "parents": {k: v for k, v in list(g["parents"].items())[:8]}}, {**g, "parents": {**g["parents"], "b101-o301": {**g["parents"]["b101-o301"], "digest": "1" * 64}}}):
        with pytest.raises(core.EngineeringStop, match="identity record"):
            parents.require_identity(broken)


def test_new_parents_need_the_identity_record_and_files_are_verified_by_recomputation() -> None:
    gate = gate_record()
    with testing.scratch("parents") as d:
        with pytest.raises(core.EngineeringStop, match="identity record"):
            parents.train_new_parents(CFG, ROWS, d, group="calibration", identity=None, steps=2)
        assert not list(d.glob("*.pt"))  # nothing was trained
        rec = parents.train_new_parents(CFG, ROWS, d, group="calibration", identity=gate, steps=2)
        assert len(rec) == 3 and all(not v["reused_file"] for v in rec.values())
        again = parents.train_new_parents(CFG, ROWS, d, group="calibration", identity=gate, steps=2)
        assert all(v["reused_file"] and v["digest_recomputed"] for v in again.values()) and {k: v["digest"] for k, v in rec.items()} == {k: v["digest"] for k, v in again.items()}
        from arborlm.p4_model import backbone_digest

        bb = parents.load_new_backbone(d / "calibration00.pt", testing.synthetic_backbone())
        assert backbone_digest(bb) == rec["calibration00"]["digest"] and backbone_digest(copy.deepcopy(bb)) == rec["calibration00"]["digest"]
        # tamper with a stored tensor but keep the stored digest: the recomputed digest differs, the file is kept aside and the parent retrained, with the attempt logged
        state = torch.load(d / "calibration01.pt", weights_only=True)
        key = next(iter(state["backbone"]))
        state["backbone"][key] = state["backbone"][key] + 1.0
        torch.save(state, d / "calibration01.pt")
        third = parents.train_new_parents(CFG, ROWS, d, group="calibration", identity=gate, steps=2)
        assert third["calibration01"]["reused_file"] is False and third["calibration01"]["digest"] == rec["calibration01"]["digest"] and third["calibration00"]["reused_file"] is True
        assert len(list(d.glob("calibration01.pt.aside-*"))) == 1 and len(list((d / "attempts").glob("*.json"))) == 1
    for s in (CFG["seeds"]["backbone_registered"], CFG["seeds"]["order_registered"]):
        assert len(set(s)) == 9  # no two new parents share a backbone seed or an order seed


def test_the_load_template_and_synthetic_backbones_use_test_range_seeds() -> None:
    import inspect

    src = inspect.getsource(testing.synthetic_backbone)
    assert "test_seed" in src and "PilotModel" not in src
    lo, hi = CFG["seeds"]["test_range"]
    assert lo <= core.test_seed(700, CFG) <= hi
