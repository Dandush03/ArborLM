# ruff: noqa: E501
"""P9 package I2, ``studies/p9/train.py``: answer-site loss, optimizers (AdamW as P5, row-lazy Adam), the
instrumented step, snapshots, checkpoint restoration, rehearsal whitelist and silence, Lane D hooks, and a
tiny end-to-end run for every architecture / rung / optimizer / objective combination.

Everything uses a random frozen backbone, tiny fact tables, test seeds (>= 179001) and the rehearsal seed
set: no real data, no registered seed, no learning curve is recorded or judged.

Self-check only: not independent review, not Astra validation, not human approval.
"""

import json
import math
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402
import torch  # noqa: E402
from test_p9_model_support import (  # noqa: E402
    TEST_SEED,
    Facts,
    FakeStream,
    backbone,
    base_cell,
    fake_data,
    variant,
)
from torch import nn  # noqa: E402
from torch.nn import functional as F  # noqa: E402

from arborlm import engine, p5_model  # noqa: E402
from studies.p9 import core, model, objective, train  # noqa: E402

FACTS = Facts(256)
STREAM = FakeStream(FACTS)
LUT = FACTS.lut()


def job_for(cell: core.Cell, out: Path, mode: str = "calibration", **kw: Any) -> train.TrainJob:
    params: dict[str, Any] = {
        "cell": cell,
        "exposure": 32,
        "mode": mode,
        "data": fake_data(),
        "stream": STREAM,
        "backbone": backbone(),
        "out_dir": out,
        "max_updates": 3,
        "fact_lut": LUT,
        "init_seed": TEST_SEED,
    }
    params.update(kw)
    return train.TrainJob(**params)


def fresh(cell: core.Cell) -> tuple[model.P9Model, list[Any], objective.Objective, train.Trainer]:
    m = model.build_model(cell, backbone(), fact_lut=LUT, init_seed=TEST_SEED)
    opts = train.build_optimizer(m, cell)
    obj = objective.Objective(cell)
    return m, opts, obj, train.Trainer(cell, m, opts, obj)


# --- loss ----------------------------------------------------------------------------------------------------------
def test_answer_site_loss_is_the_ce_at_answer_sites_only() -> None:
    toks = FACTS.batch(1, contexts=4)
    g = torch.Generator().manual_seed(3)
    logits = torch.randn(4, 63, 256, generator=g)
    manual = torch.stack(
        [
            F.cross_entropy(logits[b, 8 * r + 6], toks[b, 8 * r + 7])
            for b in range(4)
            for r in range(8)
        ]
    ).mean()
    assert float(train.answer_site_loss(logits, toks)) == pytest.approx(float(manual), rel=1e-6)
    # the targets of non-answer positions never enter the answer-site loss
    others = toks.clone()
    others[:, 8 * 7 + 1 : 8 * 7 + 6] = (
        0x41  # identifier bytes of the last record are inputs and targets, not answers
    )
    assert float(train.answer_site_loss(logits, others)) == float(
        train.answer_site_loss(logits, toks)
    )
    assert float(train.all_position_loss(logits, others)) != float(
        train.all_position_loss(logits, toks)
    )
    assert float(
        train.answer_site_loss(
            logits,
            toks.clone().index_put_((torch.arange(4), torch.full((4,), 7)), torch.tensor(0x41)),
        )
    ) != float(train.answer_site_loss(logits, toks))
    with pytest.raises(ValueError):
        train.answer_site_loss(logits, toks[:, :63])
    mean_all = F.cross_entropy(logits.reshape(-1, 256), toks[:, 1:].reshape(-1))
    assert float(train.all_position_loss(logits, toks)) == pytest.approx(float(mean_all), rel=1e-6)


# --- row-lazy Adam -----------------------------------------------------------------------------------------------------
def _sparse_gradient_sequence(rows: int, dim: int, steps: int, seed: int) -> list[torch.Tensor]:
    g = torch.Generator().manual_seed(seed)
    out = []
    for _ in range(steps):
        grad = torch.randn(rows, dim, generator=g)
        keep = torch.rand(rows, generator=g) < 0.4
        grad[~keep] = 0.0
        out.append(grad)
    return out


def test_row_lazy_adam_matches_independent_per_row_torch_adam() -> None:
    rows, dim, lr = 12, 5, 0.012
    start = torch.randn(rows, dim, generator=torch.Generator().manual_seed(1))
    table = nn.Parameter(start.clone())
    lazy = train.RowLazyAdam([table], lr=lr)
    singles = [nn.Parameter(start[r].clone()) for r in range(rows)]
    reference = torch.optim.Adam(singles, lr=lr, betas=(0.9, 0.999), eps=1e-8)
    for grad in _sparse_gradient_sequence(rows, dim, 25, 2):
        table.grad = grad.clone()
        lazy.step()
        for r, p in enumerate(singles):
            p.grad = (
                grad[r].clone() if bool((grad[r] != 0).any()) else None
            )  # no gradient: no step, own count
        reference.step()
    expected = torch.stack([p.detach() for p in singles])
    torch.testing.assert_close(table.detach(), expected, rtol=1e-5, atol=1e-7)
    counts = lazy.state[table]["row_step"]
    manual = torch.stack(
        [(g != 0).any(-1) for g in _sparse_gradient_sequence(rows, dim, 25, 2)]
    ).sum(0)
    assert torch.equal(counts, manual)  # each row counts its own updates


def test_lazy_rows_without_gradient_do_not_move_but_adamw_rows_do() -> None:
    start = torch.randn(6, 4, generator=torch.Generator().manual_seed(4))
    lazy_table, dense_table = nn.Parameter(start.clone()), nn.Parameter(start.clone())
    lazy = train.RowLazyAdam([lazy_table], lr=0.01)
    adamw = engine.optimizer_for(nn.ParameterList([dense_table]))
    first = torch.zeros(6, 4)
    first[:3] = 1.0  # rows 0-2 have a gradient on the first update, rows 3-5 never
    second = torch.zeros(6, 4)
    second[0] = 1.0  # only row 0 on the second update
    for grad in (first, second):
        lazy_table.grad, dense_table.grad = grad.clone(), grad.clone()
        lazy.step()
        adamw.step()
    moved_lazy = (lazy_table.detach() - start).abs().sum(-1) > 0
    moved_dense = (dense_table.detach() - start).abs().sum(-1) > 0
    assert moved_lazy.tolist() == [True, True, True, False, False, False]
    # AdamW (documented behaviour): rows 1 and 2 have no gradient on update two yet still move on momentum
    after_first = start.clone()
    probe = nn.Parameter(start.clone())
    probe_opt = engine.optimizer_for(nn.ParameterList([probe]))
    probe.grad = first.clone()
    probe_opt.step()
    after_first = probe.detach().clone()
    probe.grad = second.clone()
    probe_opt.step()
    assert bool(
        (probe.detach()[1:3] != after_first[1:3]).any()
    )  # row 1 and 2 moved without gradient
    assert moved_dense.tolist() == [
        True,
        True,
        True,
        False,
        False,
        False,
    ]  # rows with no gradient ever stay
    lazy_after_first = nn.Parameter(start.clone())
    check = train.RowLazyAdam([lazy_after_first], lr=0.01)
    lazy_after_first.grad = first.clone()
    check.step()
    saved = lazy_after_first.detach().clone()
    lazy_after_first.grad = second.clone()
    check.step()
    assert torch.equal(
        lazy_after_first.detach()[1:], saved[1:]
    )  # rows 1..5 untouched on update two
    assert lazy.state[lazy_table]["row_step"].tolist() == [2, 1, 1, 0, 0, 0]


def test_row_lazy_adam_rejects_non_tables_and_skips_missing_gradients() -> None:
    with pytest.raises(ValueError):
        train.RowLazyAdam([nn.Parameter(torch.zeros(3))], lr=0.1)
    p = nn.Parameter(torch.ones(2, 2))
    opt = train.RowLazyAdam([p], lr=0.1)
    opt.step()  # no gradient at all
    assert torch.equal(p.detach(), torch.ones(2, 2)) and not opt.state[p]
    p.grad = torch.zeros(2, 2)
    opt.step()
    assert torch.equal(p.detach(), torch.ones(2, 2))


# --- optimizers ----------------------------------------------------------------------------------------------------------
def test_adamw_is_exactly_p5s_registered_optimizer() -> None:
    cell = base_cell()
    m = model.build_model(cell, backbone(), init_seed=TEST_SEED)
    (opt,) = train.build_optimizer(m, cell)
    assert type(opt) is torch.optim.AdamW and len(opt.param_groups) == 1
    group = opt.param_groups[0]
    options = {k: v for k, v in group.items() if k != "params"}
    assert options.keys() == p5_model.ADAMW_OPTIONS.keys()
    for k, expected in p5_model.ADAMW_OPTIONS.items():
        assert type(options[k]) is type(expected) and options[k] == expected, k
    names = [n for n, p in m.named_parameters() if p.requires_grad]
    assert [id(p) for p in group["params"]] == [id(dict(m.named_parameters())[n]) for n in names]
    assert names == [
        "addition.keys",
        "addition.values",
        "addition.wq",
        "addition.wo",
        "addition.gate",
    ]


def test_lazy_cell_uses_row_lazy_on_tables_and_adamw_on_the_rest() -> None:
    for arch in ("flat", "learned_tree"):
        cell = base_cell(arch=arch, optimizer="lazy")
        m = model.build_model(cell, backbone(), init_seed=TEST_SEED)
        lazy, adamw = train.build_optimizer(m, cell)
        assert isinstance(lazy, train.RowLazyAdam) and type(adamw) is torch.optim.AdamW
        assert lazy.param_groups[0]["lr"] == core.LAZY_LEARNING_RATE == 0.012
        assert lazy.param_groups[0]["betas"] == (0.9, 0.999) and lazy.param_groups[0]["eps"] == 1e-8
        table_names = {
            n
            for n, p in m.named_parameters()
            if any(p is q for q in lazy.param_groups[0]["params"])
        }
        assert table_names == {"addition.keys", "addition.values"}
        rest = {
            n
            for n, p in m.named_parameters()
            if any(p is q for q in adamw.param_groups[0]["params"])
        }
        assert rest == (
            {"addition.wq", "addition.wo", "addition.gate"}
            | ({"addition.router"} if arch == "learned_tree" else set())
        )
        assert adamw.param_groups[0]["lr"] == 0.003 and adamw.param_groups[0]["weight_decay"] == 0
    with pytest.raises(ValueError):
        train.build_optimizer(
            model.build_model(base_cell(arch="dense"), backbone()),
            base_cell(arch="dense", optimizer="lazy"),
        )


def test_clip_and_adamw_step_equal_a_plain_reference_bit_for_bit() -> None:
    cell = base_cell()
    m, _, _, trainer = fresh(cell)
    twin = model.build_model(cell, backbone(), init_seed=TEST_SEED)
    ref_opt = engine.optimizer_for(
        nn.ParameterList(p for p in twin.parameters() if p.requires_grad)
    )
    for update in (1, 2, 3):
        toks = FACTS.batch(update)
        record = trainer.step(toks)
        ref_opt.zero_grad(set_to_none=True)
        logits, _ = twin(toks[:, :-1])
        loss = train.answer_site_loss(logits, toks)
        loss.backward()  # type: ignore[no-untyped-call]
        norm = nn.utils.clip_grad_norm_([p for p in twin.parameters() if p.requires_grad], 1.0)
        ref_opt.step()
        assert float(norm) == record["clip_total_norm"]
        assert record["task_loss"] == float(loss)
        for (n, a), (_, b) in zip(m.named_parameters(), twin.named_parameters(), strict=True):
            assert torch.equal(a, b), n


def test_optimizer_state_bytes_counts_every_state_tensor() -> None:
    cell = base_cell()
    _, opts, _, trainer = fresh(cell)
    assert train.optimizer_state_bytes(opts) == 0
    trainer.step(FACTS.batch(1))
    assert (
        train.optimizer_state_bytes(opts) == 2 * 198145 * 4 + 5 * 4
    )  # two moments and a step counter per tensor
    lazy_cell = base_cell(optimizer="lazy")
    _, lazy_opts, _, lazy_trainer = fresh(lazy_cell)
    lazy_trainer.step(FACTS.batch(1))
    tables = 4096 * 16 + 4096 * 32
    assert (
        train.optimizer_state_bytes(lazy_opts)
        == 2 * tables * 4 + 2 * 4096 * 8 + 2 * (16 * 32 + 32 * 32 + 1) * 4 + 3 * 4
    )


# --- the instrumented step ---------------------------------------------------------------------------------------------------
def test_update_record_fields_and_group_norm_consistency() -> None:
    cell = base_cell()
    m, _, _, trainer = fresh(cell)
    record = trainer.step(FACTS.batch(1))
    assert set(record) == set(core.UpdateRecord.__annotations__)
    assert (
        record["update"] == 1
        and math.isfinite(record["task_loss"])
        and math.isfinite(record["all_position_loss"])
    )
    for key in ("grad_norm_task", "grad_norm_usage", "grad_norm_coaccess", "param_change_norm"):
        assert set(record[key]) == set(core.PARAM_GROUPS)  # type: ignore[literal-required]
    task = record["grad_norm_task"]
    assert math.sqrt(sum(v * v for v in task.values())) == pytest.approx(
        record["clip_total_norm"], rel=1e-5
    )
    assert (
        task["router"] == 0.0
        and task["dense"] == 0.0
        and task["values"] > 0
        and task["projections"] > 0
    )
    assert task["keys_selected"] > 0
    assert (
        all(v == 0.0 for v in record["grad_norm_usage"].values()) and record["usage_penalty"] == 0.0
    )
    assert record["hinge_usage_active"] is False and record["hinge_coaccess_active"] is False
    assert record["usage_entropy_soft"] is not None and record["usage_entropy_hard"] is not None
    change = record["param_change_norm"]
    assert change["values"] > 0 and change["projections"] > 0
    # AdamW moves values by about lr per row on the first update: the change norm is of that order
    assert change["values"] == pytest.approx(
        0.003 * math.sqrt(int((m.addition.values.grad != 0).any(-1).sum()) * 32), rel=0.2
    )  # type: ignore[union-attr]


def test_groups_of_the_update_follow_the_answer_site_queries() -> None:
    cell = base_cell()
    m, _, _, trainer = fresh(cell)
    toks = FACTS.batch(1)
    with torch.no_grad():
        _, selection = m(toks[:, :-1])
    assert selection is not None and selection.candidate_ids is not None
    masks = trainer._masks(selection)
    assert masks is not None
    chosen, candidate, untouched = masks
    sites = list(core.ANSWER_SITE_POSITIONS)
    assert set(chosen.nonzero().flatten().tolist()) == set(
        selection.selected[:, sites].unique().tolist()
    )
    top64 = set(selection.candidate_ids[:, sites].unique().tolist())
    assert set((chosen | candidate).nonzero().flatten().tolist()) == top64
    assert not bool((chosen & candidate).any()) and bool((chosen | candidate | untouched).all())
    assert not bool(((chosen | candidate) & untouched).any())


def test_movement_split_matches_an_independent_replay() -> None:
    for optimizer in ("adamw", "lazy"):
        cell = base_cell(optimizer=optimizer)
        m, _, _, trainer = fresh(cell)
        keys_with = torch.zeros(4096)
        keys_without = torch.zeros(4096)
        values_with = torch.zeros(4096)
        values_without = torch.zeros(4096)
        for update in range(1, 5):
            toks = FACTS.batch(update)
            with (
                torch.no_grad()
            ):  # the rows that carry a task gradient = the rows read at any position
                _, selection = m(toks[:, :-1])
            assert selection is not None
            had = torch.zeros(4096, dtype=torch.bool)
            had[selection.selected.flatten()] = True
            before_k, before_v = (
                m.addition.keys.detach().clone(),
                m.addition.values.detach().clone(),
            )  # type: ignore[union-attr]
            trainer.step(toks)
            moved_k = (m.addition.keys.detach() - before_k).norm(dim=-1)  # type: ignore[union-attr]
            moved_v = (m.addition.values.detach() - before_v).norm(dim=-1)  # type: ignore[union-attr]
            keys_with += moved_k * had
            keys_without += moved_k * ~had
            values_with += moved_v * had
            values_without += moved_v * ~had
        for name, expected in (
            ("key_with", keys_with),
            ("key_without", keys_without),
            ("value_with", values_with),
            ("value_without", values_without),
        ):
            torch.testing.assert_close(trainer.movement[name], expected, rtol=1e-4, atol=1e-7)
        if (
            optimizer == "lazy"
        ):  # rows without a task gradient never move under row-lazy Adam (no regularizer)
            assert (
                float(trainer.movement["key_without"].sum()) == 0.0
                and float(trainer.movement["value_without"].sum()) == 0.0
            )
        else:  # AdamW moves them on momentum: the movement the ADR wants measured
            assert (
                float(trainer.movement["key_without"].sum()) > 0.0
                and float(trainer.movement["value_without"].sum()) > 0.0
            )
        assert float(trainer.movement["key_with"].sum()) > 0.0


def test_regularizer_movement_is_counted_without_task_gradient_under_lazy_adam() -> None:
    """A usage term can give a row a gradient the task loss does not: the row-lazy arm moves it, and the
    movement lands in the 'without a task gradient' accumulator (REGULARIZER-DRIVEN MOVEMENT, ADR 6.3)."""
    cell = base_cell(optimizer="lazy", alpha_u=1.0)
    _, _, _, trainer = fresh(cell)
    for update in range(1, 4):
        trainer.step(FACTS.batch(update))
    assert float(trainer.movement["key_without"].sum()) > 0.0


def test_regularized_step_gradient_is_task_plus_regularizers() -> None:
    cell = base_cell(alpha_u=1.0, alpha_c=0.05)
    cell = variant(cell, alpha_u=0.25, alpha_c=0.05)
    m, _, obj, trainer = fresh(cell)
    twin = model.build_model(cell, backbone(), fact_lut=LUT, init_seed=TEST_SEED)
    twin_obj = objective.Objective(cell)
    toks = FACTS.batch(1)
    record = trainer.step(toks)
    logits, selection = twin(toks[:, :-1])
    result = twin_obj(train.answer_site_loss(logits, toks), selection)
    result.total.backward()  # type: ignore[no-untyped-call]
    coef = min(1.0, 1.0 / (record["clip_total_norm"] + 1e-6))
    for (n, a), (_, b) in zip(m.named_parameters(), twin.named_parameters(), strict=True):
        if b.grad is not None:
            torch.testing.assert_close(a.grad, b.grad * coef, rtol=1e-4, atol=1e-8)
    assert record["hinge_usage_active"] is True and record["hinge_coaccess_active"] is True
    assert record["usage_penalty"] > 0 and record["coaccess_penalty"] >= 0
    assert (
        max(record["grad_norm_usage"].values()) > 0
        and max(record["grad_norm_coaccess"].values()) > 0
    )
    assert record["grad_norm_usage"]["values"] == 0.0 and record["grad_norm_usage"]["router"] == 0.0
    assert obj.floor is not None and obj.floor.updates == 1


def test_tree_router_receives_task_and_regularizer_gradient_groups() -> None:
    cell = base_cell(arch="learned_tree", alpha_u=0.25, alpha_c=0.05)
    _, _, _, trainer = fresh(cell)
    record = trainer.step(FACTS.batch(1))
    assert record["grad_norm_task"]["router"] > 0
    assert record["grad_norm_usage"]["router"] > 0 and record["grad_norm_coaccess"]["router"] > 0


def test_trackers_dead_slots_and_top64_entry_match_an_independent_replay() -> None:
    cell = base_cell()
    m, _, _, trainer = fresh(cell)
    sites = list(core.ANSWER_SITE_POSITIONS)
    selected = torch.zeros(4096, dtype=torch.bool)
    top64 = torch.zeros(4096, dtype=torch.bool)
    first: torch.Tensor | None = None
    for update in range(1, 5):
        toks = FACTS.batch(update)
        with torch.no_grad():
            _, sel = m(toks[:, :-1])
        assert sel is not None and sel.candidate_ids is not None
        selected[sel.selected[:, sites].flatten()] = True
        batch_top = torch.zeros(4096, dtype=torch.bool)
        batch_top[sel.candidate_ids[:, sites].flatten()] = True
        top64 |= batch_top
        if first is None:
            first = batch_top
        trainer.step(toks)
    assert first is not None
    diag = trainer.snapshot_diagnostics(FACTS.batch(4))
    assert diag["dead_slots"] == 4096 - int(selected.sum())
    assert diag["keys_entered_top64_after_0"] == int((top64 & ~first).sum())
    assert torch.equal(trainer.ever_selected, selected) and torch.equal(trainer.ever_top64, top64)


def test_margin_saturated_state_is_detected_by_the_snapshot_diagnostics() -> None:
    cell = base_cell()
    m, _, _, trainer = fresh(cell)
    toks = FACTS.batch(1)
    fresh_diag = trainer.snapshot_diagnostics(toks)
    q50 = fresh_diag["margin_8_9_quantiles"]["q50"]
    assert (
        q50 < 0.5 and fresh_diag["soft_mass_outside_top8"] > 1.0
    )  # random keys: tiny margins, mass outside the top 8
    mem = m.addition
    assert isinstance(mem, model.ScalableMemory)
    with torch.no_grad():  # queries become +-e0; eight keys per sign align exactly; every other key is orthogonal to e0
        mem.wq.zero_()
        mem.wq[0] = torch.randn(32, generator=torch.Generator().manual_seed(1))
        mem.keys[:, 0] = 0.0
        mem.keys[:8] = torch.nn.functional.one_hot(torch.tensor(0), 16).float()
        mem.keys[8:16] = -torch.nn.functional.one_hot(torch.tensor(0), 16).float()
    saturated = trainer.snapshot_diagnostics(toks)
    quantiles = saturated["margin_8_9_quantiles"]
    assert set(quantiles) == {"q00", "q05", "q25", "q50", "q75", "q95", "q100", "mean"}
    assert quantiles["q00"] == pytest.approx(5.0, abs=1e-3) and quantiles["q50"] == pytest.approx(
        5.0, abs=1e-3
    )
    assert saturated["soft_mass_outside_top8"] < 0.01
    assert saturated["hinge_active"] == {"usage": False, "coaccess": False}


def test_dense_and_r2_snapshot_diagnostics_are_defined() -> None:
    _, _, _, dense = fresh(base_cell(arch="dense"))
    d = dense.snapshot_diagnostics(FACTS.batch(1))
    assert d["margin_8_9_quantiles"] == {} and d["dead_slots"] == 0
    _, _, _, r2 = fresh(base_cell(rung="R2"))
    r2.step(FACTS.batch(1))
    diag = r2.snapshot_diagnostics(FACTS.batch(1))
    assert diag["margin_8_9_quantiles"] == {} and diag["dead_slots"] == 4096 - 128


def test_non_finite_values_stop_the_step_without_printing_them(
    capsys: pytest.CaptureFixture[str],
) -> None:
    cell = base_cell()
    m, _, _, trainer = fresh(cell)
    with torch.no_grad():
        m.addition.values.fill_(float("nan"))  # type: ignore[union-attr]
    with pytest.raises(ValueError, match="non-finite task loss at update 1") as info:
        trainer.step(FACTS.batch(1))
    assert "nan" not in str(info.value).lower()
    assert trainer.all_finite["loss"] is False
    out = capsys.readouterr()
    assert out.out == "" and out.err == ""


# --- gradient reach -----------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("arch", "rung", "groups"),
    [
        ("flat", "R0", {"keys", "values", "projections"}),
        ("learned_tree", "R0", {"keys", "values", "router", "projections"}),
        ("fixed_tree", "R0", {"keys", "values", "projections"}),
        ("flat", "R1", {"keys", "values", "projections"}),
        ("flat", "R2", {"values", "projections"}),
        ("learned_tree", "OB", {"keys", "values", "projections"}),
        ("dense", "R0", {"dense"}),
    ],
)
def test_gradient_reach_check(arch: str, rung: str, groups: set[str]) -> None:
    m = model.build_model(
        base_cell(arch=arch, rung=rung), backbone(), fact_lut=LUT, init_seed=TEST_SEED
    )
    reach = train.gradient_reach(m, FACTS.batch(1))
    assert set(reach) == groups and all(reach.values())
    assert all(p.grad is None for p in m.parameters())  # leaves no gradient behind


def test_gradient_reach_detects_an_unreachable_group() -> None:
    m = model.build_model(base_cell(), backbone(), init_seed=TEST_SEED)
    with torch.no_grad():
        m.addition.gate.fill_(-1e4)  # sigmoid(gate) == 0: the memory cannot influence the loss
    reach = train.gradient_reach(m, FACTS.batch(1))
    assert reach["values"] is False and reach["keys"] is False


# --- snapshots and restoration ------------------------------------------------------------------------------------------------------------
def test_snapshot_roundtrip_files_and_record(tmp_path: Path) -> None:
    cell = base_cell(alpha_u=0.25)
    record = train.train_cell(job_for(cell, tmp_path, max_updates=4, snapshot_updates=(2, 4)))
    assert record["status"] == "completed" and record["snapshots"] == [2, 4]
    folder = tmp_path / "snapshots" / core.snapshot_stem(4)
    assert {p.name for p in folder.iterdir()} == {
        "model.pt",
        "optimizer.pt",
        "movement.pt",
        "snapshot.json",
    }
    snap = core.read_record(folder / "snapshot.json", "snapshot")
    assert set(snap) >= set(core.SnapshotRecord.__annotations__)
    assert (
        snap["update"] == 4
        and set(snap["hinge_active"]) == {"usage", "coaccess"}
        and snap["dead_slots"] >= 0
    )
    assert record["snapshot_sha256"]["4"] == snap["model_sha256"]
    # the model snapshot restores a fresh model exactly
    final = train.run_job(
        job_for(cell, tmp_path / "again", max_updates=4, snapshot_updates=())
    ).model
    restored = model.build_model(cell, backbone(), init_seed=1)
    extra = train.load_snapshot(folder, restored)
    assert extra == {"update": 4}
    for (n, a), (_, b) in zip(final.named_parameters(), restored.named_parameters(), strict=True):
        assert torch.equal(a, b), n
    with pytest.raises(FileExistsError):
        train.save_snapshot(
            tmp_path,
            4,
            final,
            [],
            {
                "objective": {},
                "rng": {},
                "trackers": {},
                "movement": {},
                "diagnostics": {},
                "label": "x",
            },
        )
    other = model.build_model(base_cell(arch="learned_tree"), backbone(), init_seed=1)
    with pytest.raises(ValueError):
        train.load_snapshot(folder, other)
    wrong_backbone = model.build_model(cell, backbone(), init_seed=1)
    with torch.no_grad():
        next(wrong_backbone.backbone.parameters()).add_(1.0)
    with pytest.raises(ValueError, match="backbone"):
        train.load_snapshot(folder, wrong_backbone)


@pytest.mark.parametrize(
    "changes",
    [
        {},
        {"optimizer": "lazy"},
        {"alpha_u": 0.25, "alpha_c": 0.05},
        {"alpha_u": 1.0},
        {"arch": "learned_tree", "alpha_u": 0.25},
        {"arch": "learned_tree", "optimizer": "lazy"},
        {"arch": "fixed_tree"},
        {"arch": "dense"},
        {"rung": "R1"},
        {"rung": "R2"},
        {"rung": "R0a"},
        {"arch": "learned_tree", "rung": "OB"},
    ],
)
def test_checkpoint_restoration_is_bit_identical(tmp_path: Path, changes: dict[str, Any]) -> None:
    cell = base_cell(**changes)
    result = train.checkpoint_restoration_check(job_for(cell, tmp_path, max_updates=None), 2)
    assert result["identical"] is True, result["mismatches"]
    assert result["updates"] == 4 and result["tensors_compared"] > 10


def test_restoration_check_has_power_a_wrong_continuation_is_not_identical(tmp_path: Path) -> None:
    cell = variant(base_cell(), alpha_u=0.25)
    straight = train.run_job(job_for(cell, tmp_path / "s", max_updates=4, snapshot_updates=()))
    first = train.run_job(job_for(cell, tmp_path / "f", max_updates=2, snapshot_updates=(2,)))
    del first
    snapshot = tmp_path / "f" / "snapshots" / core.snapshot_stem(2)
    fresh_optimizer = train.run_job(
        job_for(
            cell,
            tmp_path / "r",
            max_updates=4,
            snapshot_updates=(),
            init_snapshot=snapshot,
            restore_optimizer=False,
        )
    )
    a = {n: p.detach() for n, p in straight.model.named_parameters()}
    b = {n: p.detach() for n, p in fresh_optimizer.model.named_parameters()}
    assert any(not torch.equal(a[n], b[n]) for n in a)


def test_two_identical_runs_are_deterministic(tmp_path: Path) -> None:
    cell = variant(base_cell(arch="learned_tree"), alpha_u=0.25, alpha_c=0.05)
    one = train.run_job(job_for(cell, tmp_path / "a", max_updates=3, snapshot_updates=()))
    two = train.run_job(job_for(cell, tmp_path / "b", max_updates=3, snapshot_updates=()))
    for (n, a), (_, b) in zip(
        one.model.named_parameters(), two.model.named_parameters(), strict=True
    ):
        assert torch.equal(a, b), n
    assert one.updates == two.updates and len(one.updates) == 3


# --- Lane D hooks ------------------------------------------------------------------------------------------------------------------------------
def test_lane_d_fresh_optimizer_and_memory_only_arm(tmp_path: Path) -> None:
    cell = base_cell()
    train.train_cell(job_for(cell, tmp_path / "phaseA", max_updates=3, snapshot_updates=(3,)))
    v1 = tmp_path / "phaseA" / "snapshots" / core.snapshot_stem(3)
    start = model.build_model(cell, backbone(), init_seed=1)
    train.load_snapshot(v1, start)
    memory_only = train.run_job(
        job_for(
            cell,
            tmp_path / "mem",
            max_updates=2,
            snapshot_updates=(),
            init_snapshot=v1,
            restore_optimizer=False,
            trainable_groups=("keys", "values"),
        )
    )
    assert (
        memory_only.trainer.update == 2
    )  # a fresh optimizer: the update counter restarts, phase B starts at update 1
    a, b = dict(start.named_parameters()), dict(memory_only.model.named_parameters())
    assert not torch.equal(a["addition.keys"], b["addition.keys"]) and not torch.equal(
        a["addition.values"], b["addition.values"]
    )
    for frozen in ("addition.wq", "addition.wo", "addition.gate"):
        assert torch.equal(a[frozen], b[frozen])
    assert memory_only.record["trainable_parameters"] == 4096 * 16 + 4096 * 32
    assert (
        len(memory_only.optimizers) == 1
        and len(memory_only.optimizers[0].param_groups[0]["params"]) == 2
    )
    sequential = train.run_job(
        job_for(
            cell,
            tmp_path / "seq",
            max_updates=2,
            snapshot_updates=(),
            init_snapshot=v1,
            restore_optimizer=False,
        )
    )
    c = dict(sequential.model.named_parameters())
    assert not torch.equal(
        a["addition.wq"], c["addition.wq"]
    )  # sequential trains every addition parameter
    assert sequential.record["trainable_parameters"] == 198145
    # the fresh optimizer has no history: its step counters count phase-B updates only
    steps = [s["step"] for s in sequential.optimizers[0].state.values()]
    assert all(float(s) == 2.0 for s in steps)  # two updates since phase B began, not 5


def test_replay_contexts_are_added_to_every_update(tmp_path: Path) -> None:
    replay = Facts(256, seed=TEST_SEED + 5)
    stream = FakeStream(FACTS, replay)
    cell = variant(base_cell(), lane_d_arm="replay", facts=4096)
    record = train.train_cell(
        job_for(cell, tmp_path, max_updates=2, snapshot_updates=(), stream=stream)
    )
    assert record["examples"] == 2 * 32 and record["tokens"] == 2 * 32 * 63


# --- run records ----------------------------------------------------------------------------------------------------------------------------------
def test_train_cell_writes_records_and_logs(tmp_path: Path) -> None:
    cell = variant(base_cell(), alpha_u=0.25)
    record = train.train_cell(job_for(cell, tmp_path, max_updates=3, snapshot_updates=(2,)))
    on_disk = core.read_record(tmp_path / "train.json", "train")
    assert on_disk == json.loads(json.dumps(record))
    assert set(record) == set(core.TrainRecord.__annotations__)
    assert (
        record["status"] == "completed"
        and record["reason"] is None
        and record["mode"] == "calibration"
    )
    assert (
        record["label"] == cell.label
        and record["exposure"] == 32
        and record["matched_updates"] == 512
    )
    assert record["run_updates"] == 3 and record["snapshots"] == [2]
    assert record["examples"] == 48 and record["tokens"] == 48 * 63
    assert (
        record["unique_facts"] == 256
        and record["exposure_per_fact_min"] == 1
        and record["exposure_per_fact_max"] == 2
    )
    assert (
        record["trainable_parameters"] == 198145
        and record["stored_parameters"] == 225537
        and record["initialized_slots"] == 4096
    )
    assert record["optimizer_state_bytes"] == 2 * 198145 * 4 + 5 * 4
    assert (
        record["lambda_u"] == pytest.approx(core.lambda_u_for(cell)) and record["lambda_c"] == 0.0
    )
    assert (
        record["wall_seconds"] > 0
        and record["peak_rss_bytes"] > 0
        and record["update_log"] == "updates.jsonl"
    )
    assert set(record["identity"]) == {
        "source_sha256",
        "spec_sha256",
        "config_sha256",
        "frozen_source_sha256",
    }
    lines = (tmp_path / "updates.jsonl").read_text().splitlines()
    assert len(lines) == 3
    for i, line in enumerate(lines, start=1):
        parsed = json.loads(line)
        assert parsed["update"] == i and set(parsed) == set(core.UpdateRecord.__annotations__)


def test_failed_run_keeps_a_failed_record_and_reraises(tmp_path: Path) -> None:
    class Exploding(FakeStream):
        def batch(self, update: int) -> Any:
            if update == 2:
                raise RuntimeError("stream broke")
            return super().batch(update)

    with pytest.raises(RuntimeError, match="stream broke"):
        train.train_cell(job_for(base_cell(), tmp_path, stream=Exploding(FACTS)))
    record = core.read_record(tmp_path / "train.json", "train")
    assert record["status"] == "failed" and "stream broke" in str(record["reason"])
    assert (
        len((tmp_path / "updates.jsonl").read_text().splitlines()) == 1
    )  # the completed update is kept


def test_mode_and_seed_set_must_agree(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        train.train_cell(
            job_for(base_cell(), tmp_path / "a", mode="registered")
        )  # rehearsal seeds, registered mode
    registered = type(fake_data())(seeds=core.registered_seeds())
    with pytest.raises(ValueError):
        train.train_cell(job_for(base_cell(), tmp_path / "b", mode="rehearsal", data=registered))
    with pytest.raises(ValueError):
        train.train_cell(job_for(base_cell(), tmp_path / "c", mode="production"))
    ok = job_for(
        base_cell(),
        tmp_path / "d",
        mode="registered",
        data=registered,
        max_updates=1,
        snapshot_updates=(),
    )
    assert train.train_cell(ok)["mode"] == "registered"


# --- rehearsal ------------------------------------------------------------------------------------------------------------------------------------
GOOD_REHEARSAL: dict[str, Any] = {
    **core.envelope("rehearsal"),
    "label": "x",
    "mode": "rehearsal",
    "stage": "rehearse",
    "identity": {"source_sha256": "a" * 64},
    "updates": 3,
    "wall_seconds": 1.5,
    "seconds_per_update": 0.5,
    "peak_rss_bytes": 1000,
    "sampled_rss_bytes": 900,
    "load_average": [1.0, 2.0, 3.0],
    "loss_finite": True,
    "parameters_finite": True,
    "gradients_finite": True,
    "shapes": {"addition.keys": [4096, 16]},
    "parameter_counts": {"keys": 65536},
    "trainable_parameters": 198145,
    "stored_parameters": 225537,
    "optimizer_state_bytes": 10,
}


def test_rehearsal_validator_allows_only_the_whitelist(tmp_path: Path) -> None:
    assert set(GOOD_REHEARSAL) == core.REHEARSAL_RECORD_KEYS
    train.write_rehearsal_record(tmp_path / "ok.json", GOOD_REHEARSAL)
    assert core.read_record(tmp_path / "ok.json", "rehearsal")["updates"] == 3
    for extra in (
        "task_loss",
        "loss",
        "accuracy",
        "nll",
        "usage_entropy_soft",
        "margin",
        "grad_norm_task",
        "exposure",
    ):
        with pytest.raises(train.RehearsalRecordError):
            train.write_rehearsal_record(tmp_path / "bad.json", {**GOOD_REHEARSAL, extra: 0.5})
    for key in ("loss_finite", "parameters_finite", "gradients_finite"):
        for value in (0.693, 1, "yes", None):
            with pytest.raises(train.RehearsalRecordError):
                train.write_rehearsal_record(tmp_path / "bad.json", {**GOOD_REHEARSAL, key: value})
    nested = [
        {"shapes": {"loss": [1]}},
        {"shapes": {"keys": [1.5]}},
        {"parameter_counts": {"accuracy": 3}},
        {"parameter_counts": {"keys": 0.5}},
        {"identity": {"loss": "x"}},
        {"load_average": [float("nan")]},
        {"wall_seconds": float("inf")},
        {"updates": True},
        {"mode": "calibration"},
        {"kind": "train"},
    ]
    for change in nested:
        with pytest.raises(train.RehearsalRecordError):
            train.write_rehearsal_record(tmp_path / "bad.json", {**GOOD_REHEARSAL, **change})
    missing = {k: v for k, v in GOOD_REHEARSAL.items() if k != "kind"}
    with pytest.raises(train.RehearsalRecordError):
        train.write_rehearsal_record(tmp_path / "bad.json", missing)
    assert not (tmp_path / "bad.json").exists()


def _all_text(folder: Path) -> str:
    chunks = []
    for p in sorted(folder.rglob("*")):
        if p.is_file() and p.suffix in {".json", ".jsonl", ".txt", ".log"}:
            chunks.append(p.read_text())
    return "\n".join(chunks)


@pytest.mark.parametrize(
    "changes",
    [
        {},
        {"alpha_u": 0.25, "alpha_c": 0.05},
        {"arch": "learned_tree"},
        {"arch": "dense"},
        {"rung": "R2"},
    ],
)
def test_rehearsal_mode_writes_only_whitelisted_records_and_prints_nothing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], changes: dict[str, Any]
) -> None:
    cell = base_cell(**changes)
    calibration = train.run_job(
        job_for(
            cell, tmp_path / "reference", mode="calibration", max_updates=3, snapshot_updates=()
        )
    )
    losses = [f"{u['task_loss']:.6g}"[:7] for u in calibration.updates] + [
        f"{u['all_position_loss']:.6g}"[:7] for u in calibration.updates
    ]
    capsys.readouterr()
    out = tmp_path / "rehearsal"
    record = train.train_cell(
        job_for(cell, out, mode="rehearsal", max_updates=3, snapshot_updates=(2, 3))
    )
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == ""  # no progress display, nothing printed
    files = sorted(p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file())
    json_files = [f for f in files if f.endswith((".json", ".jsonl"))]
    assert json_files == ["rehearsal.json"]  # no updates.jsonl, no train.json, no snapshot.json
    written = json.loads((out / "rehearsal.json").read_text())
    assert set(written) <= core.REHEARSAL_RECORD_KEYS
    assert (
        written["updates"] == 3
        and written["loss_finite"]
        and written["parameters_finite"]
        and written["gradients_finite"]
    )
    assert record["mode"] == "rehearsal" and record["update_log"] == ""
    text = _all_text(out) + captured.out + captured.err
    lowered = text.lower().replace(
        "loss_finite", ""
    )  # the whitelisted finiteness flag is the only allowed mention
    assert (
        "loss" not in lowered
        and "accuracy" not in lowered
        and "nll" not in lowered
        and "entropy" not in lowered
    )
    assert not any(
        value in text for value in losses
    )  # no loss digit string of the reference run appears anywhere
    # the binary snapshot files exist (the rehearsal times their IO) but no JSON beside them
    assert (out / "snapshots" / core.snapshot_stem(3) / "model.pt").is_file()


def test_rehearsal_cli_prints_only_the_whitelisted_record(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    cell = base_cell()

    def prepared(args: Any) -> train.TrainJob:
        return job_for(
            cell, Path(args.run_dir) / "cell", mode=args.mode, max_updates=2, snapshot_updates=()
        )

    monkeypatch.setattr(
        train, "prepare_job", prepared
    )  # my own module's loader; nothing in arborlm is patched
    code = train.main(["rehearsal", "--label", cell.label, "--run-dir", str(tmp_path)])
    captured = capsys.readouterr()
    assert code == 0 and captured.err == ""
    printed = json.loads(captured.out)
    assert set(printed) <= core.REHEARSAL_RECORD_KEYS and printed["updates"] == 2
    lowered = captured.out.lower().replace("loss_finite", "")
    assert "loss" not in lowered and "accuracy" not in lowered
    assert train.main(["stage"]) == 2
    capsys.readouterr()
    with pytest.raises(SystemExit):
        train.main(["--help"])
    capsys.readouterr()


def test_cli_cell_and_restore_check_print_no_loss(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    cell = base_cell()

    def prepared(args: Any) -> train.TrainJob:
        return job_for(
            cell, Path(args.run_dir) / "cell", mode=args.mode, max_updates=2, snapshot_updates=()
        )

    monkeypatch.setattr(train, "prepare_job", prepared)
    assert train.main(["cell", "--label", cell.label, "--run-dir", str(tmp_path / "c")]) == 0
    printed = json.loads(capsys.readouterr().out)
    assert set(printed) == {"label", "status", "record"} and printed["status"] == "completed"
    assert (
        train.main(
            [
                "restore-check",
                "--label",
                cell.label,
                "--run-dir",
                str(tmp_path / "r"),
                "--split",
                "1",
            ]
        )
        == 0
    )
    printed = json.loads(capsys.readouterr().out)
    assert printed == {"restoration_identical": True, "mismatches": []}


def test_source_prints_only_from_the_command_line_entry_point() -> None:
    import ast

    tree = ast.parse(Path(train.__file__).read_text())
    offenders = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name != "main":
            for call in ast.walk(node):
                if (
                    isinstance(call, ast.Call)
                    and isinstance(call.func, ast.Name)
                    and call.func.id == "print"
                ):
                    offenders.append(node.name)
    assert offenders == []
    source = Path(train.__file__).read_text()
    assert "tqdm" not in source and "logging" not in source


# --- tiny end-to-end runs: every architecture / rung / optimizer / objective combination ----------------------------------------------------------------
STRUCTURES = [
    ("flat", "R0"),
    ("flat", "R0a"),
    ("flat", "R1"),
    ("flat", "R2"),
    ("fixed_tree", "R0"),
    ("learned_tree", "R0"),
    ("learned_tree", "R1"),
    ("learned_tree", "OB"),
    ("dense", "R0"),
]
OBJECTIVES = [(0.0, 0.0), (0.25, 0.0), (1.0, 0.0), (0.25, 0.05), (0.25, 0.25)]


def _combinations() -> list[tuple[str, str, str, float, float]]:
    out = []
    for arch, rung in STRUCTURES:
        for optimizer in ("adamw", "lazy"):
            if arch == "dense" and optimizer == "lazy":
                continue
            for au, ac in OBJECTIVES:
                if (au, ac) != (0.0, 0.0) and (arch == "dense" or rung == "R2"):
                    continue  # regularizers act on selection candidates: none for dense or R2
                out.append((arch, rung, optimizer, au, ac))
    return out


@pytest.mark.parametrize(("arch", "rung", "optimizer", "au", "ac"), _combinations())
def test_tiny_end_to_end_run_finishes_finite(
    tmp_path: Path, arch: str, rung: str, optimizer: str, au: float, ac: float
) -> None:
    cell = base_cell(arch=arch, rung=rung, optimizer=optimizer, alpha_u=au, alpha_c=ac)
    run = train.run_job(job_for(cell, tmp_path, max_updates=3, snapshot_updates=(3,)))
    assert run.record["status"] == "completed" and run.trainer.update == 3
    for u in run.updates:
        for key in (
            "task_loss",
            "all_position_loss",
            "usage_penalty",
            "coaccess_penalty",
            "clip_total_norm",
        ):
            assert math.isfinite(u[key])  # type: ignore[literal-required]
        for key in ("grad_norm_task", "grad_norm_usage", "grad_norm_coaccess", "param_change_norm"):
            assert all(math.isfinite(v) for v in u[key].values())  # type: ignore[literal-required]
    assert all(bool(p.isfinite().all()) for p in run.model.parameters())
    assert all(p.grad is None for p in run.model.backbone.parameters())
    counts = model.parameter_counts(run.model)
    assert run.record["trainable_parameters"] == counts.trainable > 0
    if rung in ("R0", "R0a") and arch != "dense":
        assert counts.trainable == core.memory_parameters(
            "learned_tree" if arch == "learned_tree" else "flat", 4096
        )
    if arch == "dense":
        assert counts.trainable == 64 * core.dense_hidden_width(4096) + 1
    snap = core.read_record(
        tmp_path / "snapshots" / core.snapshot_stem(3) / "snapshot.json", "snapshot"
    )
    assert snap["dead_slots"] >= 0 and snap["keys_entered_top64_after_0"] >= 0
    first = run.updates[0]
    if au == 0.0:
        assert first["usage_penalty"] == 0.0 and first["hinge_usage_active"] is False
        assert max(first["grad_norm_usage"].values()) == 0.0
    else:
        # an inactive hinge (usage already spread) is a recorded property, not a failure: it gives no gradient
        assert isinstance(first["hinge_usage_active"], bool) and first["usage_penalty"] >= 0
        assert (max(first["grad_norm_usage"].values()) > 0) == first["hinge_usage_active"]
    assert (max(first["grad_norm_coaccess"].values()) > 0) == (ac > 0)
    reach = train.gradient_reach(
        model.build_model(cell, backbone(), fact_lut=LUT, init_seed=TEST_SEED), FACTS.batch(1)
    )
    assert reach and all(reach.values())


def test_combination_matrix_covers_every_structure_optimizer_and_objective() -> None:
    combos = _combinations()
    assert {(a, r) for a, r, *_ in combos} == set(STRUCTURES)
    assert {c[2] for c in combos} == {"adamw", "lazy"}
    assert {(c[3], c[4]) for c in combos} == set(OBJECTIVES)
    assert len(combos) == len(set(combos))
