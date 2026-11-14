"""P8 evaluation: utilization hand examples, intervention, git gate, a full-size dry-run cell."""

import json
import subprocess
from pathlib import Path

import pytest
import torch
from p8_dry import dry_cell

from arborlm import p7a_core as a_core
from arborlm import p7b_core as b_core
from arborlm import p8_core as core
from arborlm import p8_eval
from arborlm.io import file_sha256


def test_utilization_flat_hand_example() -> None:
    # 64 queries, each its own 8 slots: 512 distinct slots, each once
    selected = torch.arange(512).reshape(64, 8)
    u = p8_eval.utilization(selected, None)
    assert u["distinct_slots"] == 512 and u["selections"] == 512
    assert u["n_eff"] == pytest.approx(512.0)
    assert u["hot64_share"] == pytest.approx(64 / 512)
    assert u["context_breadth_mean"] == 512.0
    assert "branches" not in u


def test_context_breadth_hand_example() -> None:
    first = torch.tensor([list(range(8))] * 64)  # one fixed set per context
    alternating = torch.tensor([list(range(8)), list(range(8, 16))] * 32)
    assert p8_eval.context_breadth(torch.cat([first, alternating])) == pytest.approx((8 + 16) / 2)
    with pytest.raises(ValueError):
        p8_eval.context_breadth(first[:10])


def test_utilization_tree_branches() -> None:
    selected = torch.arange(512).reshape(64, 8) % 512
    branches = torch.tensor([[0, 1]] * 64)
    u = p8_eval.utilization(selected, branches)["branches"]
    assert u["distinct_visited"] == 2 and u["n_eff"] == pytest.approx(2.0)
    assert u["top_branch_share"] == pytest.approx(0.5)
    assert u["top_column_distinct"] == 1 and u["top_column_top_share"] == 1.0


def test_value_permutation_is_seeded_and_restorable() -> None:
    cell = core.parse_label("b101-o301-s601-C01")
    model = core.build_model(cell, core.synthetic_backbone(cell))
    assert model.addition is not None
    before = model.addition.values.detach().clone()  # type: ignore[union-attr]
    keys = model.addition.keys.detach().clone()  # type: ignore[union-attr]
    info = p8_eval.permute_values(model, cell)
    generator = torch.Generator(device="cpu").manual_seed(80000 + cell.index)
    ids = torch.randperm(core.SLOTS, generator=generator, device="cpu")
    assert info["seed"] == 80000 + cell.index
    assert torch.equal(model.addition.values, before[ids])  # type: ignore[union-attr]
    assert torch.equal(model.addition.keys, keys)  # type: ignore[union-attr]


def _git_repo(tmp_path: Path) -> Path:
    def git(*args: str) -> None:
        subprocess.run(
            ["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )

    git("init", "-q")
    record = tmp_path / "panel_record.json"
    record.write_text("{}")
    git("add", "panel_record.json")
    git("commit", "-q", "-m", "freeze")
    return record


def test_git_gate(tmp_path: Path) -> None:
    loose = tmp_path / "loose" / "panel_record.json"
    loose.parent.mkdir()
    loose.write_text("{}")
    with pytest.raises(b_core.GateError):  # not tracked
        p8_eval.git_gate(loose, "HEAD")
    repo = tmp_path / "repo"
    repo.mkdir()
    record = _git_repo(repo)
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True, check=True
    ).stdout.strip()
    assert p8_eval.git_gate(record, head)["equal_to_freeze_content"] is True
    assert p8_eval.git_gate(record, head)["stand_in"] is False
    record.write_text('{"changed": 1}')
    with pytest.raises(b_core.GateError):  # modified relative to HEAD
        p8_eval.git_gate(record, head)


def test_registered_run_needs_freeze_and_inputs(tmp_path: Path) -> None:
    with pytest.raises(b_core.GateError, match="--freeze-commit"):
        p8_eval.run_stage(["b101-o301-s601-C01"], out_root=tmp_path, dry_run=False)
    with pytest.raises(b_core.GateError, match="--freeze-commit"):
        p8_eval.git_gate(tmp_path / "panel_record.json", None)


def test_dry_cell_eval_record() -> None:
    eval_dir, _ = dry_cell()
    record = json.loads((eval_dir / "eval.json").read_text())
    assert record["dry_run"] is True and record["variant"] == "learned_tree"
    nll = record["nll"]
    assert set(nll["step0"]) == {"enabled"}
    assert set(nll["step512"]) == {"enabled", "disabled", "values_permuted"}
    for cond in nll["step512"].values():
        assert set(cond) == {"A", "B"} and all(5.0 < v < 6.0 for v in cond.values())
    assert record["intervention"]["values_permuted"]["seed"] == 80000 + record["cell_index"]
    assert set(record["traces"]) == {"calibration", "A", "B"}
    for name, entry in record["traces"].items():
        selected, branches = a_core.read_trace(eval_dir, entry["prefix"], entry["files"])
        assert tuple(selected.shape) == (core.EVAL_QUERIES, 8)
        assert branches is not None and tuple(branches.shape) == (core.EVAL_QUERIES, 2)
        counts = a_core.selection_counts(selected)
        assert b_core.counts_sha256(counts) == entry["utilization"]["counts_sha256"]
        assert entry["synthetic_substitute"] is True and name in ("calibration", "A", "B")
        assert entry["utilization"]["branches"]["distinct_visited"] >= 1
    # the files hash to what the record says
    first = record["traces"]["A"]["files"]["selected"]
    assert file_sha256(eval_dir / first["file"]) == first["sha256"]
    assert record["digests"]["backbone_unchanged"]
