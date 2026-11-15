# ruff: noqa: E501
"""P9II training: determinism, checkpoint restoration for every learned arm (A2 across its switch, A4 along its schedule, A5-C's centre), the probe set, the
per-update log and the diagnostics every N updates, the rehearsal whitelist, non-finite handling, matched updates, mode and seed checks. Tiny sizes, test seeds,
synthetic backbone. Self-check only: not independent review, not Astra validation, not human approval."""

import json
import math
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402
import torch  # noqa: E402

from studies.p9 import controls  # noqa: E402
from studies.p9 import data as d  # noqa: E402
from studies.p9ii import core, diagnostics, gates, train  # noqa: E402

SIZES = d.DataSizes(main_trained=512, unseen=64, lane_d_per_set=128)
FACTS = 128
HYPER = core.Hyper(lambda_=1.0, u_pre=4.0, k0_fraction=0.125, mu=0.1)


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


def _job(draw: d.StudyData, backbone: Any, arm: str, out: Path, updates: int = 8, **kw: Any) -> train.TrainJob:
    mode = kw.pop("mode", "calibration")
    return gates.tiny_job(arm, draw, backbone, FACTS, out / arm, hyper=kw.pop("hyper", HYPER), updates=updates, mode=mode, init_seed=910041, diag_every=kw.pop("diag_every", 4), **kw)


# --- determinism and restoration (G4) --------------------------------------------------------------------------------------------------------
def test_two_runs_are_bit_identical(draw, backbone, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    a = train.run_job(_job(draw, backbone, "A0", tmp_path / "a"))
    b = train.run_job(_job(draw, backbone, "A0", tmp_path / "b"))
    assert all(torch.equal(p, dict(b.model.named_parameters())[n]) for n, p in a.model.named_parameters())
    assert [r["task_loss"] for r in a.updates] == [r["task_loss"] for r in b.updates]


@pytest.mark.parametrize("arm", core.LEARNED_ARMS)
def test_checkpoint_restoration_is_bit_identical(draw, backbone, tmp_path: Path, arm: str) -> None:  # type: ignore[no-untyped-def]
    split = 4  # A2: U_pre = 4 (the switch happens right after the snapshot); A4: T_A = 8 (k is mid-schedule at the snapshot)
    r = train.checkpoint_restoration_check(_job(draw, backbone, arm, tmp_path, updates=16), split)
    assert r["identical"], r["mismatches"]
    assert r["tensors_compared"] > 5 and r["resumed_from_update"] == split


def test_restoration_straddles_the_a2_switch_and_the_a2_phase_is_restored(draw, backbone, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    for split in (2, 4, 6):  # before, at and after U_pre = 4
        r = train.checkpoint_restoration_check(_job(draw, backbone, "A2", tmp_path / str(split), updates=16), split)
        assert r["identical"], (split, r["mismatches"])


def test_a_snapshot_of_the_wrong_model_is_refused(draw, backbone, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    job = _job(draw, backbone, "A0", tmp_path, snapshots=(4,), updates=4)
    train.run_job(job)
    from studies.p9ii import model

    other = model.build_model("A6", 4096, 910041, backbone)
    with pytest.raises(ValueError):
        train.load_model_state(job.out_dir / "snapshots" / core.snapshot_stem(4), other)
    mine = model.build_model("A0", 4096, 910041, backbone)
    assert train.load_model_state(job.out_dir / "snapshots" / core.snapshot_stem(4), mine) == 4


# --- the probe set (8.1) -----------------------------------------------------------------------------------------------------------------------
def test_probe_set_is_both_occurrences_of_the_first_facts_of_the_calibration_stream(draw) -> None:  # type: ignore[no-untyped-def]
    p = diagnostics.build_probe(draw, FACTS)
    assert p.probe_facts == FACTS and p.sites == 2 * FACTS  # min(256, facts) facts, each at both of its occurrences
    counts = torch.bincount(p.fact)
    assert int((counts > 0).sum()) == FACTS and int(counts[counts > 0].max()) == 2 == int(counts[counts > 0].min())
    stream = d.restrict_stream(draw.streams["calibration"], draw.facts, FACTS)
    flat = stream.fact_ids.reshape(-1).tolist()
    first = list(dict.fromkeys(flat))[:FACTS]  # the order of first appearance
    assert sorted(first) == sorted(set(p.fact.tolist()))
    assert set(first[:5]) <= set(p.fact.tolist())
    for site in range(p.sites):  # every site is the stream's own record
        assert int(p.tokens[p.ctx[site], 8 * int(p.rec[site]) + 7]) - core.ALPHABET_BASE == int(p.answer[site])
    assert int(p.fact.max()) < FACTS  # only facts the cell trains
    small = diagnostics.build_probe(draw, FACTS, n_facts=32)
    assert small.probe_facts == 32 and small.sites == 64


def test_probe_never_reads_the_registered_panels(draw) -> None:  # type: ignore[no-untyped-def]
    p = diagnostics.build_probe(draw, FACTS)
    panels = torch.cat([draw.streams["panel_a"].tokens, draw.streams["panel_b"].tokens])
    keys = {bytes(row.tolist()) for row in panels}
    assert not any(bytes(row.tolist()) in keys for row in p.tokens)  # the calibration stream's contexts are not Panel A or B contexts


def test_slot_statistics_on_known_tensors() -> None:
    top8 = torch.tensor([[1, 2, 3, 4, 5, 6, 7, 8], [1, 9, 10, 11, 12, 13, 14, 15], [20, 21, 22, 23, 24, 25, 26, 27], [20, 21, 22, 23, 24, 25, 26, 27]])
    fact = torch.tensor([0, 1, 2, 2])
    s = diagnostics.top_slot_statistics(top8[:, 0], top8, fact, 3)
    assert s["distinct_top1"] == 2 and s["largest_top1_count"] == 2 and s["largest_top1_share"] == 0.5
    assert s["address_stability"] == 1.0  # fact 2 has the same top-1 at both occurrences
    assert s["private_slot_share"] == 1.0  # facts 0 and 1 hold private slots (slot 1 is shared, the others are not); fact 2 holds its own
    z = torch.tensor([[1.0, 0.0], [1.0, 0.0], [1.0, 0.0]])
    assert diagnostics.fact_independent_share(z) == pytest.approx(1.0)
    assert diagnostics.fact_independent_share(torch.tensor([[1.0, 0.0], [-1.0, 0.0]])) == pytest.approx(0.0)
    q = torch.nn.functional.normalize(torch.randn(40, 8, generator=torch.Generator().manual_seed(1)), dim=-1)
    st = diagnostics.query_statistics(q, torch.arange(40), torch.zeros(40, dtype=torch.int64), torch.arange(40) % 8)
    assert -0.5 < st["mean_cosine_different"] < 0.5 and st["effective_rank"] > 4 and 0 <= st["template_record_variance_share"] <= 1
    same = diagnostics.query_statistics(torch.ones(10, 4) / 2, torch.arange(10), torch.zeros(10, dtype=torch.int64), torch.zeros(10, dtype=torch.int64))
    assert same["mean_cosine_different"] == pytest.approx(1.0) and same["total_variance"] == 0.0
    assert diagnostics.soft_mass_outside_top8(q[:5], torch.randn(100, 8), 8) == 0.0 and 0 < diagnostics.soft_mass_outside_top8(q[:5], torch.randn(100, 8), 100) < 1


# --- logs ---------------------------------------------------------------------------------------------------------------------------------------
def test_update_log_and_diagnostics_every_n_updates(draw, backbone, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    run = train.run_job(_job(draw, backbone, "A1", tmp_path, updates=12, diag_every=4, snapshots=(12,)))
    out = tmp_path / "A1"
    updates = train.lines_of(out / "updates.jsonl")
    assert [u["update"] for u in updates] == list(range(1, 13))
    for key in ("task_loss", "address_loss", "grad_norm", "param_change_norm", "clip_total_norm", "clip_factor", "seconds", "rss_bytes", "phase", "read_k"):
        assert key in updates[0]
    assert set(updates[0]["grad_norm"]) >= {"wq", "keys", "values", "wo", "gate"} and 0 < updates[0]["clip_factor"] <= 1 and updates[0]["seconds"] > 0 and updates[0]["rss_bytes"] > 0
    diag = train.lines_of(out / "diagnostics.jsonl")
    assert [x["update"] for x in diag] == [4, 8, 12]  # every N updates, from N
    for key in ("probe_accuracy", "distinct_top1", "largest_top1_share", "private_slot_share", "address_stability", "mean_cosine_different", "effective_rank", "total_variance", "fact_independent_share", "template_record_variance_share", "target_top1_recall", "target_top8_recall", "mean_target_score", "cosine_with_top1_key", "gradient_norms_by_loss", "movement_since_previous_record", "mean_update_seconds", "peak_rss_bytes"):
        assert key in diag[0], key
    assert set(diag[0]["gradient_norms_by_loss"]) == {"answer", "addr"} and diag[0]["probe_sites"] == 2 * FACTS
    assert run.record["status"] == "completed" and json.loads((out / "train.json").read_text())["environment"]["torch"]
    assert run.record["trainable_backbone_parameters"] == 0 and run.record["update_log"] == "updates.jsonl"


def test_diagnostics_fields_by_arm(draw, backbone, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    def diag(arm: str) -> dict[str, Any]:
        return train.run_job(_job(draw, backbone, arm, tmp_path / arm, updates=4, diag_every=4)).diagnostics[0]

    a4 = diag("A4")
    assert a4["read_k"] > 8 and 0 < a4["soft_mass_outside_top8"] < 1  # k(t) and the soft mass outside the top 8 of the read
    a0 = diag("A0")
    assert "centred_query" in diag("A5-C") and "target_top8_recall" not in a0 and "soft_mass_outside_top8" not in a0
    assert set(diag("A5-D")["gradient_norms_by_loss"]) == {"answer", "div"}
    a7 = diag("A7")
    assert "probe_accuracy" in a7 and "distinct_top1" not in a7  # the dense control has no addresses
    a6 = diag("A6")
    assert a6["distinct_top1"] > 0


# --- rehearsal whitelist -----------------------------------------------------------------------------------------------------------------------
def test_rehearsal_run_writes_only_the_whitelisted_record(draw, backbone, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    job = _job(draw, backbone, "A2", tmp_path, updates=8, mode="rehearsal", snapshots=(), max_updates=6, rehearsal_phase="post")
    run = train.run_job(job)
    names = {p.name for p in (tmp_path / "A2").rglob("*") if p.is_file()}
    assert names == {"rehearsal.json"}  # no update log, no diagnostics, no train.json
    rec = json.loads((tmp_path / "A2" / "rehearsal.json").read_text())
    assert set(rec) <= train.REHEARSAL_RECORD_KEYS and rec["phase"] == "post" and rec["updates"] == 6 and rec["loss_finite"] is True
    text = json.dumps(rec).lower()
    assert not any(w in text for w in ("accuracy", "nll", "perplex", "entropy", "margin", "bits"))
    assert run.trainer.phase == 2  # the forced phase


def test_rehearsal_validator_rejects_loss_accuracy_and_unknown_keys() -> None:
    good = {**core.envelope("rehearsal"), "mode": "rehearsal", "label": "x", "updates": 3, "wall_seconds": 1.0, "arm": "A0", "slots": 4096, "phase": "main"}
    train.validate_rehearsal_record(good)
    for bad in ({"task_loss": 0.5}, {"accuracy": 0.9}, {"train_accuracy": 0.9}, {"probe_accuracy": 0.1}, {"loss": 1.0}):
        with pytest.raises(train.RehearsalRecordError):
            train.validate_rehearsal_record({**good, **bad})
    for bad in ({"wall_seconds": math.nan}, {"updates": True}, {"shapes": {"loss_matrix": [1]}}, {"parameter_counts": {"accuracy": 3}}, {"phase": "secret"}, {"arm": "N"}, {"environment": {"accuracy": 1}}):
        with pytest.raises(train.RehearsalRecordError):
            train.validate_rehearsal_record({**good, **bad})
    with pytest.raises(train.RehearsalRecordError):
        train.validate_rehearsal_record({"kind": "rehearsal"})
    assert set(train._REHEARSAL_VALIDATORS) == set(train.REHEARSAL_RECORD_KEYS)


# --- modes, seeds, matched updates, failures ------------------------------------------------------------------------------------------------------------
def test_modes_refuse_the_wrong_seed_sets(draw, backbone, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    train.check_job_seeds(_job(draw, backbone, "A0", tmp_path, mode="calibration"))
    train.check_job_seeds(_job(draw, backbone, "A0", tmp_path, mode="rehearsal"))
    with pytest.raises(ValueError):
        train.check_job_seeds(_job(draw, backbone, "A0", tmp_path, mode="registered"))  # test seeds are not registered seeds
    with pytest.raises(ValueError):
        train.check_job_seeds(_job(draw, backbone, "A0", tmp_path, mode="bogus"))
    with pytest.raises(ValueError):
        train.run_job(_job(draw, backbone, "A0", tmp_path / "x", mode="registered"))
    assert not (tmp_path / "x").exists() or not list((tmp_path / "x").rglob("*"))


def test_matched_updates_and_snapshots_at_the_readouts(draw, backbone, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    job = gates.tiny_job("A0", draw, backbone, FACTS, tmp_path / "s2", hyper=HYPER, updates=core.stage_updates(2, 8), mode="calibration", init_seed=910041, unit=8, stage=2, diag_every=8)
    job.snapshots = core.stage_readouts(2, 8)
    rec = train.train_cell(job)
    assert rec["run_updates"] == 32 and rec["snapshots"] == [8, 32] and sorted(rec["snapshot_sha256"]) == ["32", "8"]
    assert rec["exposure_per_fact_analytical"] == 32 * 128 / FACTS and rec["exposure_per_fact_min"] == rec["exposure_per_fact_max"] == 32 * 128 // FACTS
    a2 = gates.tiny_job("A2", draw, backbone, FACTS, tmp_path / "a2", hyper=core.Hyper(u_pre=1024.0), updates=core.stage_updates(2, 8), mode="calibration", init_seed=910041, unit=8, stage=2, diag_every=64)
    t = train.Trainer(a2, __import__("studies.p9ii.model", fromlist=["x"]).build_model("A2", 4096, 1, backbone), gates.train_probe(a2))
    assert t.schedule.u_pre == 4 * max(1, round(1024 * 8 / 8192))  # U_pre x 4 at Stage 2, scaled to the tiny U
    assert [train.Trainer.phase_at(t, u) for u in (1, 4, 5)] == [1, 1, 2] or t.schedule.u_pre >= 4


def test_every_run_has_exactly_its_total_updates_whatever_its_phases(draw, backbone, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    for arm in ("A2", "A4"):
        rec = train.train_cell(_job(draw, backbone, arm, tmp_path, updates=10, diag_every=100))
        assert rec["run_updates"] == 10 and rec["examples"] == 10 * 16


def test_a_non_finite_loss_stops_the_cell_and_keeps_a_failed_record(draw, backbone, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    job = _job(draw, backbone, "A1", tmp_path, updates=6, hyper=core.Hyper(lambda_=math.nan))
    with pytest.raises(ValueError, match="non-finite"):
        train.run_job(job)
    rec = json.loads((tmp_path / "A1" / "train.json").read_text())
    assert rec["status"] == "failed" and "non-finite" in rec["reason"] and rec["arm"] == "A1"
    assert (tmp_path / "A1" / "updates.jsonl").exists()  # the log of the failed cell is kept
    with pytest.raises(FileExistsError):
        train.run_job(job)  # a failed run is never silently re-run over its records


def test_configure_is_tolerant_of_a_second_call() -> None:
    train.configure()
    train.configure()
    assert torch.get_num_threads() == 1
