# ruff: noqa: E501
"""P10IS0 adapter and gates (ADR-0023 section 3, stage 1) at tiny sizes with a synthetic backbone and the test-range seeds: the identity gate against P10-S0's own code, part (b) and the end-to-end gate at every new slot count, the resume test,
divergence recognition, the seed check, and the memory-growth bound. Bit-exact assertions are made on the platform of record only."""

import json
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402
import torch  # noqa: E402

from studies.p9i.train import training_stream_for  # noqa: E402
from studies.p9ii.evaluate import corpus_rows  # noqa: E402
from studies.p9ii.train import Trainer, peak_rss  # noqa: E402
from studies.p10is0 import adapter, core, gates  # noqa: E402
from studies.p10s0 import core as s0core  # noqa: E402

torch.set_num_threads(1)
FACTS = 128
SPEC = core.test_set(1)
BB = adapter.synthetic_backbone()
DATA = adapter.build_data(SPEC.block(2048), adapter.SYNTHETIC_CORPUS, FACTS, tiny=True)
STREAM = training_stream_for(DATA, FACTS)
ROWS = corpus_rows(adapter.SYNTHETIC_CORPUS)
registered_only = pytest.mark.skipif(not s0core.on_registered_platform(), reason="bit-exact assertions are made on the platform of record only")


def cell(arm: str, slots: int, draw: int = 1) -> core.Cell:
    return core.Cell("TEST", "S", arm, FACTS, slots, draw, core.init_seed("TEST", arm, draw))


def job(c: core.Cell, out: Path, last: int, **kw: object) -> adapter.Job:
    return adapter.Job(c, DATA, STREAM, BB, out, DATA.seeds.r1_codes, last_update=last, **kw)  # type: ignore[arg-type]


def test_seed_check() -> None:
    adapter.check_seed_set("REG", "p10is0-draw-3")
    adapter.check_seed_set("REG", "p10is0-reserve-4")
    adapter.check_seed_set("CAL", "p10is0-cal-2-repeat-1")
    adapter.check_seed_set("CHK", s0core.REHEARSAL_SET.name, identity_gate=True)
    for role, name in (("REG", "p10s0-draw-1"), ("REG", "p10is0-cal-1"), ("CAL", "p10is0-draw-1"), ("CHK", s0core.REHEARSAL_SET.name), ("REH", "p10is0-draw-1"), ("TEST", "p10is0-draw-1")):
        with pytest.raises(adapter.SeedRefused):
            adapter.check_seed_set(role, name)


def test_new_slot_counts_run_and_p9ii_cell_still_rejects_them() -> None:
    from studies.p9ii import core as p9iicore

    for slots in (512, 1024, 2048, 8192):
        with pytest.raises(ValueError):
            p9iicore.Cell(1, "A0", slots, 1, 0, None, "x")
        seg = adapter.run_segment(job(cell("A5-D", slots), Path("/nonexistent"), 3, write_records=False))
        assert seg.record["status"] == "completed" and seg.record["end_update"] == 3


@registered_only
@pytest.mark.parametrize("arm,slots", [("A5-D", 4096), ("A0", 4096), ("A6", 4096), ("A5-D", 16384), ("A6", 16384), ("A0", 16384)])
def test_identity_part_a_against_p10s0_code(tmp_path: Path, arm: str, slots: int) -> None:
    real_facts = 8192 if slots == 16384 else 2048
    r = gates.identity_part_a(arm, real_facts, slots, backbone=BB, corpus=adapter.SYNTHETIC_CORPUS, rows=ROWS, out_dir=tmp_path, updates=12, facts=FACTS, tiny=True, cadence_new=(2, 4, 8), cadence_s0=2)
    assert r["identical"], r["differences"]
    assert "panels" in r["fields_compared"] and ("read_swap" in r["fields_compared"]) == (arm != "A6")
    assert "label" in r["excluded_fields"] and "identity" in r["excluded_fields"]


@registered_only
def test_identity_part_a_at_8k_4k_is_covered_by_the_same_function(tmp_path: Path) -> None:
    r = gates.identity_part_a("A5-D", 8192, 4096, backbone=BB, corpus=adapter.SYNTHETIC_CORPUS, rows=ROWS, out_dir=tmp_path, updates=6, facts=FACTS, tiny=True, cadence_new=(2, 4, 8), cadence_s0=2)
    assert r["identical"], r["differences"]


def test_identity_gate_detects_a_difference(tmp_path: Path) -> None:
    """The comparison is not vacuous: the same arm at a different initialization seed differs."""
    a = adapter.run_segment(job(cell("A0", 4096, 1), tmp_path, 4, write_records=False)).model.state_dict()
    b = adapter.run_segment(job(cell("A0", 4096, 2), tmp_path, 4, write_records=False)).model.state_dict()
    assert gates.tensors_equal(a, b)
    assert gates.tensors_equal(a, a) == []


@pytest.mark.parametrize("slots", [512, 1024, 2048, 8192])
@pytest.mark.parametrize("arm", ["A5-D", "A0", "A6"])
def test_identity_part_b_reference(tmp_path: Path, arm: str, slots: int) -> None:
    r = gates.identity_part_b(arm, slots, facts=FACTS, backbone=BB, data=DATA, stream=STREAM, cell=cell(arm, slots), out_dir=tmp_path)
    assert r["model_differs"] == [] and r["selection_mismatches"] == []
    assert r["max_abs_parameter_difference"] <= 1e-6 and r["loss_difference"] <= 1e-6, r


@pytest.mark.parametrize("slots", [512, 1024, 2048, 8192])
def test_end_to_end_at_each_new_size(tmp_path: Path, slots: int) -> None:
    r = gates.end_to_end(cell("A5-D", slots), backbone=BB, data=DATA, stream=STREAM, rows=ROWS, out_dir=tmp_path, updates=4, swap_seed=SPEC.swap_seed(2048), facts=FACTS)
    assert r["passed"], r
    assert r["swap_twice_restores"] and r["no_fixed_point"]


def test_resume_from_snapshot_is_bit_identical(tmp_path: Path) -> None:
    """Ruling 12: model state, optimizer state and the per-update losses; ``movement_since_previous_record`` resets at a resume and is excluded."""
    c = cell("A5-D", 512)
    straight = adapter.run_segment(job(c, tmp_path / "straight", 12, snapshots=(), diag_early=4, diag_late=8, diag_switch=8))
    first = adapter.run_segment(job(c, tmp_path / "split", 6, snapshots=(6,), diag_early=4, diag_late=8, diag_switch=8))
    resumed = adapter.run_segment(job(c, tmp_path / "split", 12, snapshots=(), init_snapshot=tmp_path / "split" / "snapshots" / "u0000006", diag_early=4, diag_late=8, diag_switch=8))
    assert gates.tensors_equal(straight.model.state_dict(), resumed.model.state_dict()) == []
    so, ro = straight.trainer.optimizers[0].state_dict(), resumed.trainer.optimizers[0].state_dict()
    assert so["param_groups"] == ro["param_groups"]
    for k in so["state"]:
        for name in ("exp_avg", "exp_avg_sq", "step"):
            assert torch.equal(torch.as_tensor(so["state"][k][name]), torch.as_tensor(ro["state"][k][name]))
    losses = [json.loads(x)["task_loss"] for x in (tmp_path / "straight" / "updates_00000000.jsonl").read_text().splitlines()]
    pieces = [json.loads(x)["task_loss"] for f in ("updates_00000000.jsonl", "updates_00000006.jsonl") for x in (tmp_path / "split" / f).read_text().splitlines()]
    assert losses == pieces and first.record["end_update"] == 6 and resumed.record["start_update"] == 6
    with pytest.raises(FileExistsError):
        adapter.run_segment(job(c, tmp_path / "split", 12, snapshots=(), init_snapshot=tmp_path / "split" / "snapshots" / "u0000006"))  # a segment's files are never overwritten


def test_diagnostic_cadence() -> None:
    due = [u for u in range(1, 9000) if adapter.diag_due(u)]
    assert due[:3] == [64, 128, 192] and 4096 in due and 4160 not in due and 5120 in due and 6144 in due and len([u for u in due if u <= 4096]) == 64


def test_divergence_is_only_the_trainers_own_checks(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake = SimpleNamespace(all_finite={"loss": False, "gradients": True, "parameters": True})
    assert adapter.trainer_check(ValueError("non-finite loss at update 7"), fake) == ("loss", 7)  # type: ignore[arg-type]
    assert adapter.trainer_check(ValueError("non-finite gradient norm at update 9"), fake) == ("gradient norm", 9)  # type: ignore[arg-type]
    assert adapter.trainer_check(ValueError("non-finite parameter at update 2"), fake) == ("parameter", 2)  # type: ignore[arg-type]
    assert adapter.trainer_check(ValueError("non-finite loss at update 7 extra"), fake) is None  # type: ignore[arg-type]
    assert adapter.trainer_check(ValueError("something else"), fake) is None  # type: ignore[arg-type]
    healthy = SimpleNamespace(all_finite={"loss": True, "gradients": True, "parameters": True})
    assert adapter.trainer_check(ValueError("non-finite loss at update 7"), healthy) is None  # type: ignore[arg-type]
    assert adapter.trainer_check(RuntimeError("non-finite loss at update 7"), fake) is None  # type: ignore[arg-type]

    real_step = Trainer.step

    def diverge(self: Trainer, batch: object) -> dict[str, object]:
        if self.update == 2:
            self.all_finite["loss"] = False
            raise ValueError("non-finite loss at update 3")
        return real_step(self, batch)  # type: ignore[arg-type]

    monkeypatch.setattr(Trainer, "step", diverge)
    seg = adapter.run_segment(job(cell("A0", 512), tmp_path / "d", 6))
    assert seg.diverged == {"check": "loss", "update": 3} and seg.record["status"] == "diverged" and seg.record["end_update"] == 2

    def code_error(self: Trainer, batch: object) -> dict[str, object]:
        raise RuntimeError("a bug")

    monkeypatch.setattr(Trainer, "step", code_error)
    with pytest.raises(RuntimeError):
        adapter.run_segment(job(cell("A0", 512), tmp_path / "e", 3))

    def env_error(self: Trainer, batch: object) -> dict[str, object]:
        raise OSError(28, "No space left on device")

    monkeypatch.setattr(Trainer, "step", env_error)
    with pytest.raises(adapter.EnvironmentStop):
        adapter.run_segment(job(cell("A0", 512), tmp_path / "f", 3))


def test_records_are_streamed_not_kept(tmp_path: Path) -> None:
    seg = adapter.run_segment(job(cell("A0", 512), tmp_path, 10, diag_early=5))
    assert len((tmp_path / "updates_00000000.jsonl").read_text().splitlines()) == 10
    assert len((tmp_path / "diagnostics_00000000.jsonl").read_text().splitlines()) == 2
    assert not hasattr(seg, "updates") and not hasattr(seg, "diagnostics")


def test_evaluation_runs_under_no_grad_and_counts_are_integers(tmp_path: Path) -> None:
    c = cell("A5-D", 512)
    seg = adapter.run_segment(job(c, tmp_path, 4))
    before = {k: v.clone() for k, v in seg.model.state_dict().items()}
    rec = adapter.evaluate_readout(c, seg.model, DATA, FACTS, 4, backbone=BB, rows=ROWS, target_seed=0, swap_seed=SPEC.swap_seed(2048))
    assert gates.tensors_equal(before, seg.model.state_dict()) == []  # an evaluation changes nothing
    got = adapter.counts_of(rec)
    assert all(isinstance(x, int) for p in ("a", "b", "h1", "h2") for x in getattr(got["obs"], p))


def test_memory_does_not_grow_with_run_length(tmp_path: Path) -> None:
    """Section 9: the loop's peak resident memory after 16,384 updates is within 64 MiB of its peak after 4,096 (tiny model, records written to disk and none kept)."""
    c = cell("A0", 512)
    adapter.run_segment(job(c, tmp_path / "a", 4096, diag_late=2048))
    after_short = peak_rss()
    adapter.run_segment(job(c, tmp_path / "b", 16384, diag_late=2048))
    after_long = peak_rss()
    assert after_long - after_short <= 64 * 2**20, (after_short, after_long)
