# ruff: noqa: E501
"""P9I training: the alphabet loss, optimizer groups, matched updates, snapshots, determinism, checkpoint
restoration, the rehearsal whitelist and the mode/seed checks. Tiny sizes, test seeds, synthetic backbone.
Self-check only: not independent review, not Astra validation, not human approval."""

import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402
import torch  # noqa: E402
from torch.nn import functional as F  # noqa: E402

from studies.p9 import controls  # noqa: E402
from studies.p9 import data as d  # noqa: E402
from studies.p9i import core, model, train  # noqa: E402

SIZES = d.DataSizes(main_trained=512, unseen=64, lane_d_per_set=128)
FACTS = 128


def _corpus() -> bytes:
    g = torch.Generator().manual_seed(12)
    return bytes(torch.randint(0, 256, (2048 * 65,), generator=g).tolist())


@pytest.fixture(scope="module")
def draw() -> d.StudyData:
    return d.build_study_data(core.test_seeds(1), _corpus(), sizes=SIZES)


@pytest.fixture(scope="module")
def backbone():  # type: ignore[no-untyped-def]
    torch.manual_seed(0)
    return controls.synthetic_backbone()


def _job(draw: d.StudyData, backbone, arm: str, out: Path, updates: int = 6, **kw) -> train.TrainJob:  # type: ignore[no-untyped-def]
    cell = core.make_cell(arm, 4096)
    return train.TrainJob(
        cell=cell,
        updates=updates,
        mode=kw.pop("mode", "calibration"),
        data=draw,
        stream=train.training_stream_for(draw, FACTS),
        backbone=backbone,
        out_dir=out,
        init_seed=900041,
        r1_seed=draw.seeds.r1_codes,
        fact_lut=train.fact_lut_for(draw, FACTS) if arm == "R2" else None,
        **kw,
    )


# --- the loss -----------------------------------------------------------------------------------------------------------
def test_alphabet_loss_is_cross_entropy_over_the_32_symbols_at_answer_sites() -> None:
    g = torch.Generator().manual_seed(3)
    logits = torch.randn(4, 63, 256, generator=g, requires_grad=True)
    tokens = torch.randint(0x40, 0x60, (4, 64), generator=g)
    loss = train.alphabet_loss(logits, tokens)
    sites = torch.tensor(core.ANSWER_SITE_POSITIONS)
    manual = F.cross_entropy(logits[:, sites][..., 0x40:0x60].reshape(-1, 32), (tokens[:, 1:][:, sites] - 0x40).reshape(-1))
    assert torch.equal(loss, manual)
    loss.backward()  # type: ignore[no-untyped-call]
    grad = logits.grad
    assert grad is not None
    non_site = [p for p in range(63) if p not in core.ANSWER_SITE_POSITIONS]
    assert float(grad[:, non_site].abs().max()) == 0.0  # other targets are masked
    outside = [b for b in range(256) if not 0x40 <= b < 0x60]
    assert float(grad[:, sites][..., outside].abs().max()) == 0.0  # the 256-way output set is not used
    uniform = train.alphabet_loss(torch.zeros(2, 63, 256), tokens[:2])
    assert float(uniform) == pytest.approx(math.log(32))
    with pytest.raises(ValueError):
        train.alphabet_loss(logits, tokens[:, :63])
    bad = tokens.clone()
    bad[:, 7] = 5  # an answer byte outside the alphabet
    with pytest.raises(ValueError):
        train.alphabet_loss(logits, bad)


# --- optimizers ------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("arm", core.ARMS)
def test_every_arm_has_a_single_adamw_over_exactly_the_trainable_parameters(arm: str, backbone) -> None:  # type: ignore[no-untyped-def]
    net = model.build_model(arm, 4096, 900041, backbone, fact_lut=torch.zeros(32**4, dtype=torch.int64) if arm == "R2" else None)
    optimizers = train.build_optimizers(net)
    assert len(optimizers) == 1 and type(optimizers[0]) is torch.optim.AdamW
    assert len(optimizers[0].param_groups) == 1
    group = optimizers[0].param_groups[0]
    assert group["lr"] == 0.003 and group["weight_decay"] == 0 and group["betas"] == (0.9, 0.999) and group["eps"] == 1e-8
    assert [id(p) for p in group["params"]] == [id(p) for _, p in net.trainable()]
    assert not hasattr(train, "RowLazyAdam")
    if arm.startswith("BB"):
        assert any(p.shape == (96, 32) for p in group["params"])  # the block-0 qkv is in the same group


# --- running, snapshots, determinism --------------------------------------------------------------------------------------
def test_every_arm_runs_matched_updates_and_writes_its_records(draw, backbone, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    for arm in core.ARMS:
        out = tmp_path / arm
        run = train.run_job(_job(draw, backbone, arm, out, updates=5, snapshots=(2, 5)))
        rec = run.record
        assert rec["status"] == "completed" and rec["matched_updates"] == 5 and rec["run_updates"] == 5
        assert rec["study"] == "P9I" and rec["snapshots"] == [2, 5] and rec["facts"] == FACTS
        assert (out / "train.json").is_file() and (out / "updates.jsonl").is_file()
        for u in (2, 5):
            folder = out / "snapshots" / core.snapshot_stem(u)
            assert {p.name for p in folder.iterdir()} == {"model.pt", "optimizer.pt", "movement.pt", "snapshot.json"}
        lines = (out / "updates.jsonl").read_text().splitlines()
        assert len(lines) == 5 and json.loads(lines[0])["update"] == 1
        first = json.loads(lines[0])
        assert set(first["grad_norm"]) == set(train.NORM_GROUPS) and first["clip_total_norm"] > 0
        assert rec["trainable_backbone_parameters"] == (4224 if arm in core.BB_ARMS else 0)
        assert rec["exposure_per_fact_min"] == rec["exposure_per_fact_max"] == 5  # 128 facts: one update is one epoch
        if arm in core.MEMORY_ARMS:
            moved = torch.load(out / "snapshots" / core.snapshot_stem(5) / "movement.pt", weights_only=True)
            assert float(moved["value_with"].sum()) > 0 and float(moved["value_without"].sum()) >= 0
        assert rec["optimizer_state_bytes"] > 0


def test_training_is_deterministic(draw, backbone, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    for arm in ("N", "BB", "A4"):
        a = train.run_job(_job(draw, backbone, arm, tmp_path / f"a-{arm}", snapshots=()))
        b = train.run_job(_job(draw, backbone, arm, tmp_path / f"b-{arm}", snapshots=()))
        for (n, p), (_, q) in zip(a.model.named_parameters(), b.model.named_parameters(), strict=True):
            assert torch.equal(p, q), n
        la = (tmp_path / f"a-{arm}" / "updates.jsonl").read_text()
        lb = (tmp_path / f"b-{arm}" / "updates.jsonl").read_text()
        assert [json.loads(x)["task_loss"] for x in la.splitlines()] == [json.loads(x)["task_loss"] for x in lb.splitlines()]


@pytest.mark.parametrize("arm", ["N", "BB", "R1", "R2", "D"])
def test_checkpoint_restoration_is_bit_identical(arm: str, draw, backbone, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    result = train.checkpoint_restoration_check(_job(draw, backbone, arm, tmp_path, updates=8), 4)
    assert result["identical"], result["mismatches"]
    assert result["tensors_compared"] > 5 and result["resumed_from_update"] == 4


def test_snapshot_round_trip_restores_the_trained_block0_attention(draw, backbone, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    run = train.run_job(_job(draw, backbone, "BB", tmp_path, updates=4, snapshots=(4,)))
    fresh = model.build_model("BB", 4096, 900041, backbone, seed_rng=False)
    assert not torch.equal(fresh.backbone.blocks[0].qkv.weight, run.model.backbone.blocks[0].qkv.weight)
    train.load_snapshot(tmp_path / "snapshots" / core.snapshot_stem(4), fresh)
    for (n, p), (_, q) in zip(run.model.named_parameters(), fresh.named_parameters(), strict=True):
        assert torch.equal(p, q), n
    # a frozen backbone tensor that differs from the live one is refused
    other = controls.synthetic_backbone(102, 302)
    wrong = model.build_model("BB", 4096, 900041, other, seed_rng=False)
    with pytest.raises(ValueError):
        train.load_snapshot(tmp_path / "snapshots" / core.snapshot_stem(4), wrong)


# --- rehearsal -------------------------------------------------------------------------------------------------------------
GOOD = {
    "kind": "rehearsal", "schema": 1, "study": "P9I", "label": "x", "mode": "rehearsal", "stage": "rehearse",
    "identity": {"source_sha256": "a"}, "updates": 3, "wall_seconds": 1.5, "seconds_per_update": 0.5,
    "peak_rss_bytes": 10, "sampled_rss_bytes": 9, "load_average": [0.1, 0.2, 0.3], "loss_finite": True,
    "parameters_finite": True, "gradients_finite": True, "shapes": {"addition.keys": [4096, 16]},
    "parameter_counts": {"keys": 65536}, "trainable_parameters": 5, "stored_parameters": 6,
    "optimizer_state_bytes": 7, "trainable_backbone_parameters": 4224,
}  # fmt: skip


def test_rehearsal_whitelist_accepts_time_memory_shapes_counts_and_rejects_loss_and_accuracy(tmp_path: Path) -> None:
    train.validate_rehearsal_record(dict(GOOD))
    train.write_rehearsal_record(tmp_path / "ok.json", dict(GOOD))
    for key, value in (("task_loss", 1.0), ("loss", 3.4), ("accuracy", 0.5), ("train_accuracy", 0.1), ("nll", 1.0), ("correct", 3), ("bits", 2.0), ("margin", 0.1)):
        with pytest.raises(train.RehearsalRecordError):
            train.validate_rehearsal_record({**GOOD, key: value})
    with pytest.raises(train.RehearsalRecordError):
        train.validate_rehearsal_record({**GOOD, "shapes": {"val_loss": [1]}})  # a nested name that looks like a loss
    with pytest.raises(train.RehearsalRecordError):
        train.validate_rehearsal_record({**GOOD, "parameter_counts": {"accuracy": 3}})
    with pytest.raises(train.RehearsalRecordError):
        train.validate_rehearsal_record({**GOOD, "loss_finite": 3.4})  # a finiteness flag must be a bool
    with pytest.raises(train.RehearsalRecordError):
        train.validate_rehearsal_record({**GOOD, "identity": {"loss": "x"}})
    with pytest.raises(train.RehearsalRecordError):
        train.validate_rehearsal_record({**GOOD, "study": "P9"})
    with pytest.raises(train.RehearsalRecordError):
        train.write_rehearsal_record(tmp_path / "bad.json", {**GOOD, "final_accuracy": 0.9})
    assert not (tmp_path / "bad.json").exists()
    incomplete = {k: v for k, v in GOOD.items() if k != "mode"}
    with pytest.raises(train.RehearsalRecordError):
        train.validate_rehearsal_record(incomplete)


def test_rehearsal_mode_writes_only_the_whitelisted_record_and_binary_files(draw, backbone, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    run = train.run_job(_job(draw, backbone, "BB", tmp_path, updates=3, mode="rehearsal", snapshots=(3,)))
    names = {p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*") if p.is_file()}
    assert "rehearsal.json" in names
    assert not any(n.endswith(("updates.jsonl", "train.json", "snapshot.json")) for n in names)
    assert {n for n in names if n.startswith("snapshots/")} == {f"snapshots/{core.snapshot_stem(3)}/{f}" for f in ("model.pt", "optimizer.pt", "movement.pt")}
    record = json.loads((tmp_path / "rehearsal.json").read_text())
    train.validate_rehearsal_record(record)
    assert not set(record) - set(train.REHEARSAL_RECORD_KEYS)
    text = (tmp_path / "rehearsal.json").read_text().lower()
    assert "task_loss" not in text and "accuracy" not in text
    assert record["trainable_backbone_parameters"] == 4224 and record["updates"] == 3
    assert run.updates == []  # no per-update records are kept in rehearsal mode


def test_exceptions_do_not_carry_loss_values(draw, backbone, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    job = _job(draw, backbone, "N", tmp_path, updates=3)
    run = train.run_job(job)
    run.trainer.model.addition.values.data.fill_(float("nan"))
    with pytest.raises(ValueError) as info:
        run.trainer.step(job.stream.batch(4).tokens)
    assert "non-finite" in str(info.value) and "nan" not in str(info.value).lower()


# --- modes and seeds --------------------------------------------------------------------------------------------------------
def test_mode_and_seed_set_must_agree(draw, backbone, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(ValueError):
        train.run_job(_job(draw, backbone, "N", tmp_path / "r", mode="registered"))  # test seeds in a registered run
    with pytest.raises(ValueError):
        train.run_job(_job(draw, backbone, "N", tmp_path / "x", mode="nonsense"))
    assert not (tmp_path / "r").exists()


def test_training_stream_is_p9s_schedule_on_the_first_facts(draw) -> None:  # type: ignore[no-untyped-def]
    stream = train.training_stream_for(draw, FACTS)
    assert stream.facts.tolist() == list(range(FACTS))
    batch = stream.batch(1)
    assert batch.tokens.shape == (16, 64) and batch.fact_ids.shape == (16, 8)
    assert train.fact_lut_for(draw, FACTS).max() == FACTS - 1
