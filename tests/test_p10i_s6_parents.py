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


def test_identity_gate_passes_and_fails_on_a_wrong_record() -> None:
    rec = {p: reference_digest(*core.old_parent_ids(p), STEPS) for p in range(9)}
    g = parents.identity_gate(core.repo_root(), ROWS, CFG, steps=STEPS, recorded=rec)
    assert g["passed"] is True and len(g["parents"]) == 9 and g["declared_reuse"]["control_memory_seed"] == 201
    bad = dict(rec)
    bad[3] = "0" * 64
    assert parents.identity_gate(core.repo_root(), ROWS, CFG, steps=STEPS, recorded=bad)["passed"] is False


def test_new_seeds_train_are_deterministic_and_distinct_and_resumable_files() -> None:
    bs, os_ = core.backbone_seed(CFG, "registered", 0), core.order_seed(CFG, "registered", 0)
    _, d1 = parents.train_backbone(bs, os_, ROWS, steps=STEPS, control_memory=201)
    _, d2 = parents.train_backbone(bs, os_, ROWS, steps=STEPS, control_memory=201)
    _, d3 = parents.train_backbone(core.backbone_seed(CFG, "registered", 1), core.order_seed(CFG, "registered", 1), ROWS, steps=STEPS, control_memory=201)
    assert d1 == d2 != d3
    with testing.scratch("parents") as d:
        rec = parents.train_new_parents(CFG, ROWS, d, group="calibration", steps=2)
        assert len(rec) == 3 and all(not v["reused_file"] for v in rec.values())
        again = parents.train_new_parents(CFG, ROWS, d, group="calibration", steps=2)
        assert all(v["reused_file"] for v in again.values()) and {k: v["digest"] for k, v in rec.items()} == {k: v["digest"] for k, v in again.items()}
        bb = parents.load_new_backbone(d / "calibration00.pt", testing.synthetic_backbone())
        from arborlm.p4_model import backbone_digest

        assert backbone_digest(bb) == rec["calibration00"]["digest"]
        assert backbone_digest(copy.deepcopy(bb)) == rec["calibration00"]["digest"]
    for s in (CFG["seeds"]["backbone_registered"], CFG["seeds"]["order_registered"]):
        assert len(set(s)) == 9  # no two new parents share a backbone seed or an order seed
