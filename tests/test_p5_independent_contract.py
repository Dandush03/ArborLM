"""Independent synthetic contracts for the P5 hierarchy ablation.

These fixtures use generated tokens and synthetic parent provenance. They do
not open the approved corpus or execute an experiment cell.
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
import torch

from arborlm import hierarchy_ablation, p5_analysis, p5_checkpoint, p5_config, p5_model
from arborlm.p2_config import CONTROL as P2_CONTROL
from arborlm.p2_config import Cell as P2Cell
from arborlm.p2_model import FollowupModel
from arborlm.p4_model import Backbone
from arborlm.p5_config import BASELINE, DENSE, FIXED, FLAT, LEARNED, Cell
from arborlm.p5_model import Model


def _parent_backbone() -> Backbone:
    parent = FollowupModel(P2Cell(101, 201, 301, P2_CONTROL))
    return Backbone(parent)


def _model(variant: str, seed: int = 501) -> Model:
    return Model(Cell(101, 301, 0 if variant == BASELINE else seed, variant), _parent_backbone())


def _tensor_state(model: Model) -> dict[str, torch.Tensor]:
    return {
        **{f"param:{name}": value.detach().clone() for name, value in model.named_parameters()},
        **{f"buffer:{name}": value.detach().clone() for name, value in model.named_buffers()},
        "buffer:backbone.mask": model.backbone.mask.detach().clone(),
    }


def test_model_variants_freeze_backbone_and_have_exact_optimizer_membership() -> None:
    expected = {
        BASELINE: (0, 0),
        FLAT: (198145, 198145),
        FIXED: (198145, 198145),
        LEARNED: (198401, 198401),
        DENSE: (198401, 198401),
    }
    backbone = _parent_backbone()
    for variant, (trainable_count, optimizer_count) in expected.items():
        model = Model(Cell(101, 301, 0 if variant == BASELINE else 501, variant), backbone)
        optimizer = p5_model.optimizer_for(model)
        names = p5_model.optimizer_names(model, optimizer)
        assert sum(parameter.numel() for parameter in model.backbone.parameters()) == 27392
        assert (
            sum(parameter.numel() for parameter in model.parameters() if parameter.requires_grad)
            == trainable_count
        )
        assert (
            sum(
                parameter.numel()
                for group in optimizer.param_groups
                for parameter in group["params"]
            )
            if optimizer is not None
            else 0
        ) == optimizer_count
        assert len(names) == len(set(names))
        assert all(not parameter.requires_grad for parameter in model.backbone.parameters())
        assert all(parameter.grad is None for parameter in model.backbone.parameters())
        assert model.backbone.mask.shape == (64, 64)
        if variant == FIXED:
            assert isinstance(model.addition, p5_model.Memory)
            assert "addition.router" not in dict(model.named_parameters())
            assert "addition.router" in dict(model.named_buffers())


def test_optimizer_rejects_group_splits_wrong_hyperparameters_and_membership() -> None:
    model = _model(FLAT)
    optimizer = p5_model.optimizer_for(model)
    assert optimizer is not None
    params = optimizer.param_groups[0]["params"]
    options = {key: value for key, value in optimizer.param_groups[0].items() if key != "params"}
    split = torch.optim.AdamW(
        [{**options, "params": params[:-1]}, {**options, "params": params[-1:]}]
    )
    with pytest.raises(ValueError, match="parameter group"):
        p5_model.optimizer_names(model, split)
    wrong_lr = torch.optim.AdamW(params, lr=0.004)
    with pytest.raises(ValueError, match="hyperparameters"):
        p5_model.optimizer_names(model, wrong_lr)
    duplicate_params = params[:-1] + [params[-1], params[-1]]
    duplicate = torch.optim.AdamW([{"params": duplicate_params, **options}])
    with pytest.raises(ValueError, match="membership or order"):
        p5_model.optimizer_names(model, duplicate)
    omitted = torch.optim.AdamW([{"params": params[:-1], **options}])
    with pytest.raises(ValueError, match="membership or order"):
        p5_model.optimizer_names(model, omitted)


def test_tied_output_is_causal_and_frozen_suffix_keeps_addition_gradient() -> None:
    model = _model(LEARNED)
    model.eval()
    tokens = torch.randint(0, 16, (2, 12), generator=torch.Generator().manual_seed(5))
    changed = tokens.clone()
    changed[:, -1] = (changed[:, -1] + 1) % 16
    logits, _ = model(tokens)
    changed_logits, _ = model(changed)
    assert logits.shape == (2, 12, 256)
    assert model.token.weight is model.backbone.token.weight
    assert torch.equal(logits[:, :-1], changed_logits[:, :-1])

    captured: list[torch.Tensor] = []

    def capture(_module: torch.nn.Module, _inputs: tuple[torch.Tensor, ...], output: Any) -> None:
        hidden = output[0]
        hidden.retain_grad()
        captured.append(hidden)

    assert isinstance(model.addition, torch.nn.Module)
    hook = model.addition.register_forward_hook(capture)
    try:
        batch = torch.randint(0, 16, (2, 13), generator=torch.Generator().manual_seed(13))
        out, _ = model(batch[:, :-1])
        loss = torch.nn.functional.cross_entropy(out.reshape(-1, 256), batch[:, 1:].reshape(-1))
        loss.backward()
    finally:
        hook.remove()
    assert captured and captured[0].grad is not None
    assert float(torch.linalg.vector_norm(captured[0].grad)) > 0
    assert all(parameter.grad is None for parameter in model.backbone.parameters())


def test_fresh_seed_initialization_is_shared_across_memory_architectures_and_parents() -> None:
    parent_a, parent_b = _parent_backbone(), _parent_backbone()
    shared_fields = ("keys", "values", "wq", "wo", "gate")
    for seed in p5_config.SEEDS:
        random_state, torch_state = random.getstate(), torch.get_rng_state().clone()
        models = [
            Model(Cell(backbone, 301, seed, variant), parent)
            for backbone, parent, variant in (
                (101, parent_a, FLAT),
                (101, parent_a, FIXED),
                (101, parent_a, LEARNED),
                (102, parent_b, FLAT),
                (102, parent_b, FIXED),
                (102, parent_b, LEARNED),
            )
        ]
        # Reconstruct after taking the RNG snapshot to establish the constructor
        # itself leaves both global generators unchanged.
        repeated = Model(Cell(101, 301, seed, FLAT), parent_a)
        assert random_state == random.getstate()
        assert torch.equal(torch_state, torch.get_rng_state())
        assert all(
            torch.equal(getattr(models[0].addition, name), getattr(model.addition, name))
            for model in models[1:]
            for name in shared_fields
        )
        assert all(
            torch.equal(models[1].addition.router, model.addition.router)
            for model in (models[2], models[4], models[5])
        )
        assert torch.equal(models[0].addition.keys, repeated.addition.keys)


@pytest.mark.parametrize("variant", [FLAT, FIXED, LEARNED, DENSE])
def test_training_preserves_frozen_tensors_and_eval_is_state_rng_isolated(variant: str) -> None:
    model = _model(variant)
    optimizer = p5_model.optimizer_for(model)
    assert optimizer is not None
    before_backbone = {
        name: value.detach().clone() for name, value in model.backbone.named_parameters()
    }
    before_mask = model.backbone.mask.detach().clone()
    before_router = (
        model.addition.router.detach().clone()
        if variant == FIXED and isinstance(model.addition, p5_model.Memory)
        else None
    )
    training = torch.randint(0, 16, (8, 65), generator=torch.Generator().manual_seed(7))
    p5_model.train_step(model, optimizer, training, 1)
    assert all(
        torch.equal(before_backbone[name], value)
        for name, value in model.backbone.named_parameters()
    )
    assert torch.equal(before_mask, model.backbone.mask)
    if before_router is not None:
        assert torch.equal(before_router, model.addition.router)

    data = torch.randint(0, 16, (9, 65), generator=torch.Generator().manual_seed(11))
    model.train()
    state = _tensor_state(model)
    py_rng, torch_rng = random.getstate(), torch.get_rng_state().clone()
    output = p5_model.evaluate(model, data, expected_targets=9 * 64)
    assert output["target_tokens"] == 576
    assert model.training
    assert py_rng == random.getstate()
    assert torch.equal(torch_rng, torch.get_rng_state())
    assert all(torch.equal(state[name], value) for name, value in _tensor_state(model).items())


def test_evaluation_nll_is_token_weighted_for_uneven_batches() -> None:
    model = _model(BASELINE)
    data = torch.randint(0, 16, (9, 65), generator=torch.Generator().manual_seed(19))
    logits, _ = model(data[:, :-1])
    targets = data[:, 1:]
    logits64 = logits.double().reshape(-1, logits.shape[-1])
    target64 = targets.reshape(-1)
    token_losses = torch.logsumexp(logits64, dim=-1) - logits64.gather(
        1, target64[:, None]
    ).squeeze(1)
    independently_weighted = float(token_losses.sum() / target64.numel())
    observed = p5_model.evaluate(model, data, expected_targets=9 * 64)["nll"]
    assert observed == pytest.approx(independently_weighted, abs=2e-6, rel=0)


def test_evaluation_exception_restores_mode_model_and_rng() -> None:
    model = _model(BASELINE)
    model.train()
    state = _tensor_state(model)
    py_rng, torch_rng = random.getstate(), torch.get_rng_state().clone()

    def fail(_tokens: torch.Tensor) -> tuple[torch.Tensor, None]:
        random.random()
        torch.rand(1)
        raise RuntimeError("synthetic forward failure")

    model.forward = fail  # type: ignore[method-assign]
    with pytest.raises(RuntimeError, match="synthetic forward failure"):
        p5_model.evaluate(model, torch.zeros((8, 65), dtype=torch.int64), expected_targets=512)
    assert model.training
    assert py_rng == random.getstate()
    assert torch.equal(torch_rng, torch.get_rng_state())
    assert all(torch.equal(state[name], value) for name, value in _tensor_state(model).items())


def test_known_logit_uneven_batch_loss_is_token_weighted() -> None:
    # Eight rows have per-token loss zero; the final row has loss log(4).
    # The correct 8+1 batch result is log(4)/9, not the unweighted batch mean.
    class KnownLogitBaseline:
        cell = Cell(101, 301, 0, BASELINE)
        training = True
        memory = None

        def eval(self) -> None:
            self.training = False

        def train(self, mode: bool = True) -> None:
            self.training = mode

        def __call__(self, tokens: torch.Tensor) -> tuple[torch.Tensor, None]:
            logits = torch.full((tokens.shape[0], tokens.shape[1], 256), -torch.inf)
            logits[..., 0] = 100.0
            if tokens.shape[0] == 1:
                logits[..., 0] = 0.0
                logits[..., 1] = torch.log(torch.tensor(3.0))
            return logits, None

    data = torch.zeros((9, 65), dtype=torch.int64)
    baseline = KnownLogitBaseline()
    expected = float(torch.log(torch.tensor(4.0, dtype=torch.float64)) / 9)
    observed = p5_model.evaluate(baseline, data, expected_targets=9 * 64)["nll"]
    assert observed == pytest.approx(expected, abs=2e-6, rel=0)
    assert baseline.training


def test_intervention_permutations_are_valid_and_do_not_touch_backbone() -> None:
    backbone = _parent_backbone()
    for variant in (FLAT, FIXED, LEARNED):
        model = Model(Cell(101, 301, 501, variant), backbone)
        before_backbone = p5_model.backbone_digest(model.backbone)
        before_keys = model.addition.keys.detach().clone()
        before_values = model.addition.values.detach().clone()
        ids, seed = p5_model.intervene(model, "values_permuted")
        assert seed == 60000 + model.cell.index
        assert torch.equal(ids.sort().values, torch.arange(4096))
        assert torch.equal(model.addition.keys, before_keys)
        assert torch.equal(model.addition.values, before_values[ids])
        assert p5_model.backbone_digest(model.backbone) == before_backbone

        fresh = Model(Cell(101, 301, 501, variant), backbone)
        before_keys = fresh.addition.keys.detach().clone()
        before_values = fresh.addition.values.detach().clone()
        ids, seed = p5_model.intervene(fresh, "joint_within_branch")
        assert seed == 70000 + fresh.cell.index
        assert torch.equal(ids.sort().values, torch.arange(4096))
        if variant != FLAT:
            for branch in range(16):
                branch_ids = ids[branch * 256 : (branch + 1) * 256]
                assert torch.equal(branch_ids // 256, torch.full((256,), branch))
        assert torch.equal(fresh.addition.keys, before_keys[ids])
        assert torch.equal(fresh.addition.values, before_values[ids])


@pytest.mark.parametrize("variant", [FLAT, FIXED, LEARNED, DENSE])
def test_checkpoint_restore_rejects_identity_mismatch_and_restores_rng(
    variant: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    model = _model(variant)
    optimizer = p5_model.optimizer_for(model)
    identity = {
        "cell": model.cell.fields(),
        "backbone_sha256": p5_model.backbone_digest(model.backbone),
        "synthetic": True,
    }
    batch = torch.randint(0, 16, (8, 65), generator=torch.Generator().manual_seed(23))
    assert optimizer is not None
    p5_model.train_step(model, optimizer, batch, 1)
    monkeypatch.setattr(p5_checkpoint, "CHECKPOINT_STEPS", (0, 1, 256, 512))
    path = tmp_path / variant
    p5_checkpoint.save(path, model, optimizer, 1, identity)
    model2 = _model(variant)
    optimizer2 = p5_model.optimizer_for(model2)
    assert optimizer2 is not None
    py_rng, torch_rng = random.getstate(), torch.get_rng_state().clone()
    restored = p5_checkpoint.restore(path, model2, optimizer2, identity)
    assert restored["additional_step"] == 1
    assert py_rng == random.getstate()
    assert torch.equal(torch_rng, torch.get_rng_state())
    assert all(
        torch.equal(a, b) for a, b in zip(model.parameters(), model2.parameters(), strict=True)
    )
    with pytest.raises(ValueError, match="identity|membership"):
        p5_checkpoint.restore(path, model2, optimizer2, {**identity, "synthetic": False})
    with (path / "state.pt").open("ab") as stream:
        stream.write(b"corruption")
    with pytest.raises(ValueError, match="checksum"):
        p5_checkpoint.restore(path, model2, optimizer2, identity)


class _SyntheticParent:
    def __init__(self, backbone: Backbone, order_path: Path, nll: float):
        self.backbone = backbone
        self.order_file = order_path
        self.order_ids = list(range(2048))
        self.final_nll = nll
        self.identity = {"order_sha256": hierarchy_ablation.file_sha256(order_path)}
        self.provenance = {
            "run_id": "SYNTHETIC-PARENT",
            "checkpoint_state_sha256": "a" * 64,
            "checkpoint_index_sha256": "b" * 64,
        }

    def check_unchanged(self) -> None:
        return None


@pytest.mark.parametrize("variant", [BASELINE, FLAT, FIXED, LEARNED, DENSE])
def test_cell_runner_handles_each_variant_on_synthetic_inputs(
    variant: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import arborlm.p5_data
    import arborlm.p5_parent

    backbone = _parent_backbone()
    p5_cell = Cell(101, 301, 0 if variant == BASELINE else 501, variant)
    run, suite, parent_suite = (tmp_path / name for name in ("run", "suite", "parents"))
    run.mkdir()
    suite.mkdir()
    parent_suite.mkdir()
    order_path = suite / "synthetic-order.json"
    order_path.write_text(json.dumps(list(range(2048))))
    shared = {
        "source_sha256": "1" * 64,
        "config_sha256": "2" * 64,
        "spec_sha256": "3" * 64,
    }
    (run / "manifest.json").write_text(json.dumps({"status": "running"}))
    (suite / "config.resolved.json").write_text("{}")
    (suite / "manifest.json").write_text(
        json.dumps(
            {
                "dataset_manifest_sha256": "4" * 64,
                "parent_provenance_sha256": "unused",
            }
        )
    )
    (suite / "baselines.json").write_text("{}")
    synthetic_train = torch.randint(0, 16, (2048, 65), generator=torch.Generator().manual_seed(29))
    validation = torch.randint(0, 16, (8, 65), generator=torch.Generator().manual_seed(31))

    eval_impl = p5_model.evaluate

    def small_eval(
        model: Model, rows: torch.Tensor, expected_targets: int = 32768
    ) -> dict[str, Any]:
        return eval_impl(model, rows, expected_targets=rows.shape[0] * 64)

    parent_nll = small_eval(Model(Cell(101, 301, 0, BASELINE), backbone), validation)["nll"]
    parent = _SyntheticParent(backbone, order_path, parent_nll)
    from arborlm.io import canonical_json, sha256

    parent_mapping = {p5_cell.parent_label: {"record": {}, "provenance": parent.provenance}}
    (suite / "parent_provenance.json").write_text(json.dumps(parent_mapping))
    (suite / "manifest.json").write_text(
        json.dumps(
            {
                "dataset_manifest_sha256": "4" * 64,
                "parent_provenance_sha256": sha256(canonical_json(parent_mapping)),
            }
        )
    )
    monkeypatch.setattr(hierarchy_ablation, "validate_config", lambda config: config)
    monkeypatch.setattr(hierarchy_ablation, "_prepare", lambda *_: ({}, {"synthetic": True}))
    monkeypatch.setattr("arborlm.engine.configure_cpu", lambda: None)
    monkeypatch.setattr(hierarchy_ablation, "_shared", lambda _: shared)
    monkeypatch.setattr(hierarchy_ablation, "_update", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(hierarchy_ablation, "_source_unchanged", lambda *_: True)
    monkeypatch.setattr(p5_model, "evaluate", small_eval)
    monkeypatch.setattr(
        arborlm.p5_data, "load_frozen", lambda *_: (synthetic_train, validation, validation, {})
    )
    monkeypatch.setattr(arborlm.p5_parent, "verify_parent", lambda *_: parent)
    monkeypatch.setattr(arborlm.p5_parent, "extract_verified", lambda _: backbone)
    monkeypatch.setattr(hierarchy_ablation, "STEPS", 1)
    monkeypatch.setattr(hierarchy_ablation, "TRAIN_TARGETS", 512)
    monkeypatch.setattr(hierarchy_ablation, "CHECKPOINT_STEPS", (1,))
    monkeypatch.setattr(p5_config, "STEPS", 1)
    monkeypatch.setattr(p5_checkpoint, "CHECKPOINT_STEPS", (0, 1))

    if variant != BASELINE:
        initial_model = Model(p5_cell, backbone)
        (suite / "baselines.json").write_text(
            json.dumps(
                {
                    p5_cell.parent_label: {
                        "nll": parent_nll,
                        "backbone_sha256": p5_model.backbone_digest(initial_model.backbone),
                        "parent_checkpoint_state_sha256": parent.provenance[
                            "checkpoint_state_sha256"
                        ],
                    }
                }
            )
        )
    hierarchy_ablation._cell(run, suite, parent_suite, p5_cell)
    result = json.loads((run / "result.json").read_text())
    assert result["outcome"] == "completed"
    assert result["cell"] == p5_cell.fields()
    assert result["additional_training_targets"] == (0 if variant == BASELINE else 512)
    assert result["checkpoint_state_sha256"].keys() == (
        {"checkpoint-0"} if variant == BASELINE else {"checkpoint-0", "checkpoint-1"}
    )
    if variant == BASELINE:
        assert set(result["interventions"]) == {"enabled"}
    elif variant == DENSE:
        assert set(result["interventions"]) == {"enabled", "disabled"}
    else:
        assert set(result["interventions"]) == set(p5_config.CONDITIONS)


def test_quality_suite_publishes_each_synthetic_cell_once_with_parent_baseline_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import arborlm.p5_data
    import arborlm.p5_parent

    cell = Cell(101, 301, 0, BASELINE)
    run, parent_suite, export = (tmp_path / name for name in ("quality", "parents", "export"))
    run.mkdir()
    parent_suite.mkdir()
    record = {"backbone": 101, "order": 301, "variant": BASELINE, "seed": 0}
    provenance = {"run_id": "SYNTHETIC-P4", "checkpoint_state_sha256": "a" * 64}
    parent = SimpleNamespace(provenance=provenance, check_unchanged=lambda: None)
    calls = {"cell_exports": 0}
    monkeypatch.setattr(hierarchy_ablation, "cells", lambda: [cell])
    monkeypatch.setattr(hierarchy_ablation, "load_config", lambda _: {})
    monkeypatch.setattr(hierarchy_ablation, "_prepare", lambda *_: ({}, {"env": "synthetic"}))
    monkeypatch.setattr(
        hierarchy_ablation,
        "_shared",
        lambda _: {"source_sha256": "1" * 64, "config_sha256": "2" * 64},
    )
    monkeypatch.setattr(hierarchy_ablation, "_update", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(hierarchy_ablation, "_source_unchanged", lambda *_: True)
    monkeypatch.setattr(arborlm.p5_parent, "verify_suite", lambda *_: {(101, 301): record})
    monkeypatch.setattr(arborlm.p5_parent, "verify_parent", lambda *_: parent)
    monkeypatch.setattr(arborlm.p5_data, "freeze", lambda *_: {"synthetic": True})
    summary = {"outcome": "completed", "cells": [{"status": "completed"}]}
    monkeypatch.setattr(hierarchy_ablation, "_summary", lambda *_args, **_kwargs: summary)

    export_impl = hierarchy_ablation._export

    def count_export(source: Path, destination: Path, names: tuple[str, ...]) -> None:
        if destination.name == cell.label:
            calls["cell_exports"] += 1
        export_impl(source, destination, names)

    monkeypatch.setattr(hierarchy_ablation, "_export", count_export)

    def fake_supervise(*args: Any, **kwargs: Any) -> tuple[Path, bool]:
        worker = Path(args[0]) / "synthetic-child"
        worker.mkdir(parents=True)
        kwargs["worker_argv"](worker)
        (worker / "manifest.json").write_text("{}")
        (worker / "result.json").write_text(
            json.dumps(
                {
                    "final": {"nll": 1.0},
                    "initial": None,
                    "interventions": {"enabled": {"nll": 1.0}},
                    "additional_training_targets": 0,
                    "checkpoint_state_sha256": {"checkpoint-0": "c" * 64},
                    "backbone_sha256": "d" * 64,
                }
            )
        )
        (worker / "terminal.json").write_text(
            json.dumps(
                {
                    "status": "completed",
                    "reason": None,
                    "process_wall_seconds": 1.0,
                    "peak_process_tree_rss_bytes": 1,
                }
            )
        )
        return worker, True

    monkeypatch.setattr(hierarchy_ablation, "supervise", fake_supervise)
    hierarchy_ablation._quality_suite(
        run,
        tmp_path / "config.toml",
        tmp_path / "data",
        parent_suite,
        export,
    )
    assert calls["cell_exports"] == 1
    assert (export / cell.label).is_dir()
    assert (export / "quality-suite").is_dir()
    assert "b101-o301-baseline" in json.loads((run / "baselines.json").read_text())


def test_timing_schedule_counts_and_synthetic_state_isolation() -> None:
    from arborlm.p5_timing import FORWARD, run_schedule, schedule

    assert len(list(schedule(0, p5_config.VARIANTS))) == 2 * 8 * (3 + 4 + 4)
    models = {variant: _model(variant) for variant in p5_config.VARIANTS}
    inputs = {
        size: tuple(
            torch.randint(0, 16, (size, 64), generator=torch.Generator().manual_seed(i + size))
            for i in range(4)
        )
        for size in (8, 1)
    }
    states = {variant: _tensor_state(model) for variant, model in models.items()}
    modes = {variant: model.training for variant, model in models.items()}
    ticks = iter(range(100_000, 100_000 + 100_000))
    result = run_schedule(models, inputs, 0, clock=lambda: next(ticks))
    assert result["call_counts"] == {
        "insertion_hidden": 32,
        "normalized_query": 24,
        "warmups": 2 * 176,
        "timed": 10 * 176,
    }
    assert all(model.training == modes[variant] for variant, model in models.items())
    assert all(
        all(
            torch.equal(states[variant][name], value)
            for name, value in _tensor_state(model).items()
        )
        for variant, model in models.items()
    )
    assert any(row["scope"] == FORWARD for row in result["records"])


@pytest.mark.parametrize("variant", [FLAT, FIXED, LEARNED])
def test_timing_operand_trace_matches_expected_key_and_router_work(variant: str) -> None:
    from arborlm.p5_timing import trace_memory

    model = _model(variant)
    tokens = torch.randint(0, 16, (2, 64), generator=torch.Generator().manual_seed(41))
    state = _tensor_state(model)
    py_rng, torch_rng = random.getstate(), torch.get_rng_state().clone()
    trace = trace_memory(model, tokens)
    assert trace["validated"] is True
    assert trace["queries"] == 128
    assert trace["key_dot_products_per_query"] == (4096 if variant == FLAT else 512)
    assert trace["router_dot_products_per_query"] == (0 if variant == FLAT else 16)
    assert trace["candidate_union"] == (4096 if variant == FLAT else trace["candidate_union"])
    assert trace["selected_values_per_query"] == 8
    assert py_rng == random.getstate()
    assert torch.equal(torch_rng, torch.get_rng_state())
    assert all(torch.equal(state[name], value) for name, value in _tensor_state(model).items())


def test_active_clock_uses_earliest_combined_or_timing_deadline() -> None:
    from arborlm.p5_clock import ActiveClock

    now = [100.0]
    combined_limited = ActiveClock(2395.0, now=lambda: now[0])
    assert combined_limited.worker_budget(45) == pytest.approx(5.0)
    now[0] += 5.0
    assert combined_limited.remaining() == pytest.approx(0.0)
    with pytest.raises(TimeoutError):
        combined_limited.worker_budget(45)

    timing_limited = ActiveClock(1700.0, now=lambda: now[0])
    assert timing_limited.worker_budget(45) == pytest.approx(45.0)
    now[0] += 601.0
    with pytest.raises(TimeoutError):
        timing_limited.worker_budget(45)


def test_ack_wait_excludes_only_exact_external_wait_and_rejects_replay(tmp_path: Path) -> None:
    from arborlm.io import write_json
    from arborlm.p5_clock import ActiveClock, wait_for_ack

    now = [0.0]
    clock = ActiveClock(2000.0, now=lambda: now[0])
    used: set[str] = set()

    def announce(expected: dict[str, Any]) -> None:
        now[0] += 2.0

    def sleep(_: float) -> None:
        now[0] += 5.0
        write_json(
            Path(expected_path[0]),
            {
                "suite_id": "suite-a",
                "worker_id": "quality-a",
                "commit": "a" * 40,
                "push_completed": True,
            },
        )

    expected_path: list[str] = []

    def announce_with_path(expected: dict[str, Any]) -> None:
        expected_path.append(expected["ack_path"])
        announce(expected)

    record = wait_for_ack(
        tmp_path,
        "suite-a",
        "quality-a",
        used,
        clock,
        announce=announce_with_path,
        sleep=sleep,
    )
    assert record["external_wait_seconds"] == 5.0
    accounting = clock.snapshot()
    assert accounting["timing_stage_wall_seconds"] == 7.0
    assert accounting["external_reporting_wait_seconds"] == 5.0
    assert accounting["timing_worker_active_seconds"] == 2.0
    assert used == {"quality-a"}
    with pytest.raises(ValueError, match="before its worker request"):
        wait_for_ack(
            tmp_path,
            "suite-a",
            "quality-a",
            used,
            clock,
            announce=lambda _: None,
            sleep=lambda _: None,
        )


def test_ack_rejects_mismatch_and_out_of_order_files(tmp_path: Path) -> None:
    from arborlm.io import write_json
    from arborlm.p5_clock import ActiveClock, wait_for_ack

    now = [10.0]
    clock = ActiveClock(100.0, now=lambda: now[0])
    inbox = tmp_path / "report-acks"
    inbox.mkdir()
    write_json(
        inbox / "unexpected.json",
        {"suite_id": "wrong", "worker_id": "wrong", "commit": "b" * 40, "push_completed": True},
    )
    with pytest.raises(ValueError, match="out-of-order"):
        wait_for_ack(
            tmp_path,
            "suite-b",
            "worker-b",
            set(),
            clock,
            announce=lambda _: None,
            sleep=lambda _: None,
        )

    other = tmp_path / "other"
    other.mkdir()
    used: set[str] = set()

    def wrong_ack(expected: dict[str, Any]) -> None:
        write_json(
            Path(expected["ack_path"]),
            {
                "suite_id": "suite-b",
                "worker_id": "different-worker",
                "commit": "c" * 40,
                "push_completed": True,
            },
        )

    with pytest.raises(ValueError, match="mismatched/reused"):
        wait_for_ack(
            other,
            "suite-b",
            "worker-b",
            used,
            clock,
            announce=wrong_ack,
            sleep=lambda _: None,
        )


def test_delayed_invalid_ack_does_not_reduce_active_worker_time(tmp_path: Path) -> None:
    from arborlm.io import write_json
    from arborlm.p5_clock import ActiveClock, wait_for_ack

    now = [20.0]
    clock = ActiveClock(100.0, now=lambda: now[0])
    ack_path: list[Path] = []

    def announce(expected: dict[str, Any]) -> None:
        ack_path.append(Path(expected["ack_path"]))

    def delayed_bad_ack(_: float) -> None:
        now[0] += 5.0
        write_json(
            ack_path[0],
            {
                "suite_id": "suite-delayed",
                "worker_id": "wrong-worker",
                "commit": "e" * 40,
                "push_completed": True,
            },
        )

    with pytest.raises(ValueError, match="mismatched/reused"):
        wait_for_ack(
            tmp_path,
            "suite-delayed",
            "worker-delayed",
            set(),
            clock,
            announce=announce,
            sleep=delayed_bad_ack,
        )
    assert clock.snapshot()["external_reporting_wait_seconds"] == 0.0
    assert clock.snapshot()["timing_worker_active_seconds"] == 5.0


def test_ack_timing_deadline_is_not_recovered_by_external_wait(tmp_path: Path) -> None:
    from arborlm.io import write_json
    from arborlm.p5_clock import ActiveClock, wait_for_ack

    now = [0.0]
    clock = ActiveClock(2399.0, now=lambda: now[0])

    def announce(expected: dict[str, Any]) -> None:
        now[0] += 3.0
        write_json(
            Path(expected["ack_path"]),
            {
                "suite_id": "suite-c",
                "worker_id": "worker-c",
                "commit": "d" * 40,
                "push_completed": True,
            },
        )

    with pytest.raises(TimeoutError):
        wait_for_ack(
            tmp_path,
            "suite-c",
            "worker-c",
            set(),
            clock,
            announce=announce,
            sleep=lambda _: None,
        )


def test_quality_finalization_time_is_charged_before_timing_stage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from arborlm import records
    from arborlm.io import write_json

    root = tmp_path / "suite"
    root.mkdir()
    quality = root / "quality-run"
    quality.mkdir()
    export = tmp_path / "export"
    now = [0.0]
    monkeypatch.setattr(hierarchy_ablation.time, "monotonic", lambda: now[0])
    monkeypatch.setattr(records, "allocate_run", lambda *_args, **_kwargs: root)
    write_json(quality / "terminal.json", {"reason": None, "process_wall_seconds": 100.0})
    write_json(quality / "result.json", {"outcome": "completed", "cells": []})

    def supervise(*_args: Any, **kwargs: Any) -> tuple[Path, bool]:
        assert kwargs["process_seconds"] == 1800.0
        now[0] += 1790.0
        return quality, True

    def finalize(*_args: Any) -> None:
        now[0] += 11.0

    monkeypatch.setattr(hierarchy_ablation, "supervise", supervise)
    monkeypatch.setattr(hierarchy_ablation, "_finalize_stage", finalize)
    monkeypatch.setattr(hierarchy_ablation, "QUALITY_SECONDS", 1800.0)
    monkeypatch.setattr(hierarchy_ablation, "_emit", lambda _: None)
    rss = SimpleNamespace(breached=False, peak=1)
    root_path, ok = hierarchy_ablation._launch(
        tmp_path / "config",
        tmp_path / "data",
        tmp_path / "output",
        tmp_path / "parent",
        export,
        rss,
    )
    assert root_path == root
    assert ok is False
    terminal = json.loads((root / "terminal.json").read_text())
    assert terminal["quality_stage_wall_seconds"] == 1801.0
    assert terminal["quality_supervised_worker_seconds"] == 100.0
    assert terminal["timing"] == "unexecuted"


def _quality_fixture() -> list[dict[str, Any]]:
    rows = []
    for backbone in p5_config.BACKBONES:
        for order in p5_config.ORDERS:
            rows.append(
                {
                    "backbone": backbone,
                    "order": order,
                    "seed": 0,
                    "variant": BASELINE,
                    "initial_nll": None,
                    "final_nll": 1.0,
                    "interventions": {"enabled": 1.0},
                }
            )
            for seed in p5_config.SEEDS:
                finals = {FLAT: 0.99, FIXED: 0.98, LEARNED: 0.97, DENSE: 0.99}
                for variant, final in finals.items():
                    interventions = {"enabled": final, "disabled": 1.0}
                    if variant in p5_config.MEMORIES:
                        interventions.update(
                            values_permuted=final + 0.01,
                            joint_within_branch=final,
                        )
                    rows.append(
                        {
                            "backbone": backbone,
                            "order": order,
                            "seed": seed,
                            "variant": variant,
                            "initial_nll": 1.1,
                            "final_nll": final,
                            "interventions": interventions,
                        }
                    )
    return rows


def _timing_fixture() -> list[dict[str, Any]]:
    workers = []
    for backbone in p5_config.BACKBONES:
        for order in p5_config.ORDERS:
            workers.append({"backbone": backbone, "order": order, "seed": 0})
            for seed in p5_config.SEEDS:
                records = []
                for size in (8, 1):
                    for scope in ("addition_forward", "model_forward"):
                        for variant, ratio in (
                            (FLAT, 1.0),
                            (FIXED, 0.75 if scope == "addition_forward" else 1.0),
                            (LEARNED, 0.75 if scope == "addition_forward" else 1.0),
                        ):
                            records.append(
                                {
                                    "batch_size": size,
                                    "scope": scope,
                                    "variant": variant,
                                    "usable": True,
                                    "median_ns": 100.0 * ratio,
                                }
                            )
                traces = {}
                for variant in p5_config.MEMORIES:
                    dots = 4096 if variant == FLAT else 512
                    router = 0 if variant == FLAT else 16
                    traces[variant] = {
                        size: [
                            {
                                "key_dot_products_per_query": dots,
                                "router_dot_products_per_query": router,
                                "candidate_key_elements_per_query": dots * 16,
                                "router_elements_per_query": router * 16,
                                "selected_values_per_query": 8,
                                "queries": int(size) * 64,
                                "validated": True,
                            }
                            for _ in range(4)
                        ]
                        for size in ("8", "1")
                    }
                workers.append(
                    {
                        "backbone": backbone,
                        "order": order,
                        "seed": seed,
                        "timing": {"records": records},
                        "traces": traces,
                    }
                )
    return workers


def test_quality_analysis_enforces_22_of_27_and_8_of_9_strict_signs() -> None:
    rows = _quality_fixture()
    # Exact boundary: three zero effects in one parent, two in another leaves
    # 22/27 strict positive B-C cells and eight positive parent means.
    for cell in rows:
        if cell["variant"] == FIXED and (
            (cell["backbone"], cell["order"]) == (101, 301)
            or ((cell["backbone"], cell["order"]) == (101, 302) and cell["seed"] in (501, 502))
        ):
            cell["final_nll"] = 0.97
            cell["interventions"]["enabled"] = 0.97
    boundary = p5_analysis.describe(rows)
    assert all(boundary["quality_flags"].values())
    assert boundary["quality_clauses"]["R"]["cells"] is True
    assert boundary["quality_clauses"]["R"]["parents"] is True
    assert boundary["sign_counts"][LEARNED]["both_positive_cells"] == 27

    below = _quality_fixture()
    for row in below:
        if row["variant"] == FIXED and (row["backbone"], row["order"]) in (
            (101, 301),
            (101, 302),
        ):
            row["final_nll"] = 0.97
            row["interventions"]["enabled"] = 0.97
    # Two fully zero parents leave exactly 21 positive cells and seven positive
    # parent means, below both strict-sign gates.
    rejected = p5_analysis.describe(below)
    assert rejected["quality_clauses"]["R"]["cells"] is False
    assert rejected["quality_clauses"]["R"]["parents"] is False
    assert rejected["sign_counts"][LEARNED]["both_positive_cells"] == 27


def test_latency_requires_all_27_reliable_pairs_and_score_work_contract() -> None:
    workers = _timing_fixture()
    latency, work = p5_analysis.timing_analysis(workers)
    assert latency[FIXED]["status"] == "PASS"
    assert latency[LEARNED]["status"] == "PASS"
    assert work[FIXED]["passed"] and work[LEARNED]["passed"]
    affected = next(
        row
        for row in workers
        if row.get("seed") == 501 and row["backbone"] == 101 and row["order"] == 301
    )
    for record in affected["timing"]["records"]:
        if (
            record["variant"] == LEARNED
            and record["scope"] == "addition_forward"
            and record["batch_size"] == 8
        ):
            record["usable"] = False
    inconclusive, _ = p5_analysis.timing_analysis(workers)
    assert inconclusive[LEARNED]["status"] == "INCONCLUSIVE"
    assert inconclusive[FIXED]["status"] == "PASS"


def test_timing_reliability_percentiles_and_rejection_boundaries() -> None:
    from arborlm.p5_timing import summarize

    exact_round_ratio = [[100] * 10 for _ in range(4)] + [[125] * 10 for _ in range(4)]
    exact = summarize(exact_round_ratio, resolution_ns=1.0)
    assert exact["round_median_ratio"] == 1.25
    assert exact["p10_ns"] == 100
    assert exact["p90_ns"] == 125
    assert exact["p95_ns"] == 125
    assert exact["usable"] is True

    nonpositive = [row.copy() for row in exact_round_ratio]
    nonpositive[0][0] = 0
    assert (
        summarize(nonpositive, resolution_ns=1.0)["reliability_criteria"]["positive_durations"]
        is False
    )
    below_resolution = [[99] * 10 for _ in range(8)]
    assert (
        summarize(below_resolution, resolution_ns=1.0)["reliability_criteria"][
            "above_clock_resolution"
        ]
        is False
    )


def test_timing_exception_restores_model_rng_and_gc_state() -> None:
    import gc

    from arborlm.p5_timing import run_schedule

    models = {variant: _model(variant) for variant in p5_config.VARIANTS}
    inputs = {
        size: tuple(
            torch.randint(
                0,
                16,
                (size, 64),
                generator=torch.Generator().manual_seed(size * 10 + index),
            )
            for index in range(4)
        )
        for size in (8, 1)
    }
    states = {variant: _tensor_state(model) for variant, model in models.items()}
    modes = {variant: model.training for variant, model in models.items()}
    py_rng, torch_rng = random.getstate(), torch.get_rng_state().clone()
    gc_before = gc.isenabled()
    ticks = iter(range(100_000, 1_000_000))

    def abort_after_block(_row: dict[str, Any]) -> None:
        raise RuntimeError("synthetic timing reporter failure")

    with pytest.raises(RuntimeError, match="synthetic timing reporter failure"):
        run_schedule(models, inputs, 0, clock=lambda: next(ticks), on_block=abort_after_block)
    assert all(model.training == modes[variant] for variant, model in models.items())
    assert py_rng == random.getstate()
    assert torch.equal(torch_rng, torch.get_rng_state())
    assert gc.isenabled() == gc_before
    assert all(
        all(
            torch.equal(states[variant][name], value)
            for name, value in _tensor_state(model).items()
        )
        for variant, model in models.items()
    )
