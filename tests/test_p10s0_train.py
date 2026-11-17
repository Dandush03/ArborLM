# ruff: noqa: E501
"""P10S0 training, evaluation, the read swap and the model-dependent gates. Tiny sizes, test seeds 920001-920999 only, synthetic backbone; no registered, rehearsal or check seed is built. Covers: records carry the
study code P10S0; every arm trains, is deterministic and restores bit for bit (A2 across its switch); S0's arms equal studies.p9ii's on a shared seed set; the seed-set and cell-type guards; the rehearsal
whitelist; the read swap against a naive one-site-at-a-time implementation; a_use and i; G4/G5/G6 on tiny draws. Self-check only: not independent review, not Astra validation, not human approval."""

import json
import math
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402
import torch  # noqa: E402

from studies.p9 import controls  # noqa: E402
from studies.p9ii import core as p9iicore  # noqa: E402
from studies.p9ii import model as p9iimodel  # noqa: E402
from studies.p10s0 import core, evaluate, gates, model, train  # noqa: E402
from studies.p10s0 import synthetic as syn  # noqa: E402

SPEC = core.test_set(2)
HYPER = core.HYPER._replace(u_pre=4.0)
ARMS = ("A0", "A1", "A2", "A5-D", "A6", "A7", "WX-A5-D", "WX-A1")
LEARNED = core.LEARNED_ARMS


@pytest.fixture(scope="module")
def backbone():  # type: ignore[no-untyped-def]
    torch.manual_seed(0)
    return controls.synthetic_backbone()


@pytest.fixture(scope="module")
def draw():  # type: ignore[no-untyped-def]
    return syn.tiny_data(SPEC, 2048)


@pytest.fixture(scope="module")
def draw8k():  # type: ignore[no-untyped-def]
    return syn.tiny_data(SPEC, 8192)


@pytest.fixture(scope="module")
def rows():  # type: ignore[no-untyped-def]
    return evaluate.corpus_rows(syn.tiny_corpus())[:64]


def job(arm: str, draw, backbone, out: Path, *, ct: str = "2K/4K", facts: int = 128, updates: int = 8, mode: str = "dry", **kw: Any) -> train.Job:  # type: ignore[no-untyped-def]
    cell = core.make_cell(arm, ct, "Q1", 1, kw.pop("j", 0))
    return train.Job(cell=cell, mode=mode, data=draw, stream=train.training_stream_for(draw, facts), backbone=backbone, out_dir=out / arm, init_seed=920041, r1_seed=draw.seeds.r1_codes, target_seed=SPEC.target_seed(ct, 0), hyper=kw.pop("hyper", HYPER), unit=8, diag_every=kw.pop("diag_every", 4), max_updates=updates, **kw)


# --- records and determinism ----------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("arm", ARMS)
def test_every_arm_trains_and_writes_p10s0_records(arm: str, draw, backbone, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    j = job(arm, draw, backbone, tmp_path, snapshots=(8,))
    ex = train.run_job(j)
    rec = core.read_record(j.out_dir / "train.json", "train")
    assert rec["study"] == "P10S0" and rec["arm"] == arm and rec["celltype"] == "2K/4K" and rec["status"] == "completed" and rec["trainable_backbone_parameters"] == 0 and rec["facts"] == 128
    assert rec["identity"] == core.code_identity() and rec["environment"]["torch"] and rec["matched_updates"] == 8 and rec["snapshots"] == [8]
    assert (j.out_dir / "snapshots/u0000008/snapshot.json").is_file() and core.read_record(j.out_dir / "snapshots/u0000008/snapshot.json", "snapshot")["label"] == j.cell.label
    assert len(ex.updates) == 8 and (j.out_dir / "updates.jsonl").is_file() and len(train.lines_of(j.out_dir / "diagnostics.jsonl")) == 2
    assert rec["cost"]["label"] == "analytical counts, not measurements" and "no efficiency claim" in rec["cost"]["cpu_seconds_label"]


def test_two_runs_are_bit_identical(draw, backbone, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    for arm in ("A5-D", "WX-A1"):
        a = train.run_job(job(arm, draw, backbone, tmp_path / "a"))
        b = train.run_job(job(arm, draw, backbone, tmp_path / "b"))
        assert all(torch.equal(p, dict(b.model.named_parameters())[n]) for n, p in a.model.named_parameters())
        assert [r["task_loss"] for r in a.updates] == [r["task_loss"] for r in b.updates]


@pytest.mark.parametrize("arm", LEARNED)
def test_checkpoint_restoration_is_bit_identical(arm: str, draw, backbone, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    r = train.checkpoint_restoration_check(job(arm, draw, backbone, tmp_path, updates=16), 4)  # A2: U_pre = 4, so the switch happens right after the snapshot
    assert r["identical"], r["mismatches"]
    assert r["tensors_compared"] > 5 and r["resumed_from_update"] == 4


def test_restoration_straddles_the_a2_switch(draw, backbone, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    for split in (2, 4, 6):
        r = train.checkpoint_restoration_check(job("A2", draw, backbone, tmp_path / str(split), updates=16), split)
        assert r["identical"], (split, r["mismatches"])


def test_a2_u_pre_scales_with_the_cell_type(draw8k, backbone, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    """The calibrated U_pre (2,048 at 2,048 facts) scaled by U / 8,192 for the tiny unit 8: 2 at 2K/4K and 8 (four times) at 8K/16K."""
    ex = train.run_job(job("A2", draw8k, backbone, tmp_path, ct="8K/16K", facts=256, hyper=core.HYPER, updates=8))
    assert ex.record["schedule"]["u_pre"] == 8
    ex2 = train.run_job(job("A2", draw8k, backbone, tmp_path / "x", ct="2K/4K", facts=128, hyper=core.HYPER, updates=4))
    assert ex2.record["schedule"]["u_pre"] == 2


# --- cell types ------------------------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("arm", ["A1", "A2", "WX-A1"])
def test_supervised_arms_are_refused_at_8k_4k(arm: str, draw8k, backbone, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    cell = core.make_cell(arm, "8K/4K", "WX" if core.is_wx(arm) else "Q1", 1, 0)
    j = train.Job(cell=cell, mode="dry", data=draw8k, stream=train.training_stream_for(draw8k, 256), backbone=backbone, out_dir=tmp_path, init_seed=1, r1_seed=1, target_seed=1)
    with pytest.raises(ValueError, match="no target injection"):
        train.run_job(j)


def test_two_facts_per_slot_cell_trains_and_evaluates(draw8k, backbone, rows, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    for arm in ("A0", "A5-D", "A6"):
        j = job(arm, draw8k, backbone, tmp_path, ct="8K/4K", facts=256, updates=8, snapshots=(8,))
        ex = train.run_job(j)
        assert ex.record["slots"] == 4096 and ex.record["facts"] == 256 and ex.record["unique_facts"] <= 256
        rec = evaluate.evaluate_readout(j.cell, ex.model, draw8k, 256, 8, frozen_backbone=backbone, rows=rows, target_seed=j.target_seed, swap_seed=SPEC.swap_seed(8192))
        assert rec["celltype"] == "8K/4K" and rec["facts"] == 256 and rec["slots"] == 4096


def test_probe_cell_type_has_sixteen_u_updates() -> None:
    assert core.CELLTYPES["32K/64K"].updates() == 131072 and core.CELLTYPES["32K/64K"].facts == 32768


# --- seed sets and modes ---------------------------------------------------------------------------------------------------------------------
def test_seed_set_guards(draw, backbone, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    for mode in ("registered", "check", "rehearsal"):
        with pytest.raises(ValueError, match="cannot use"):
            train.run_job(job("A0", draw, backbone, tmp_path / mode, mode=mode))
    train.run_job(job("A0", draw, backbone, tmp_path / "ok", mode="dry"))
    with pytest.raises(ValueError, match="cannot use"):
        train.run_job(job("A0", syn.tiny_data(core.test_set(3), 2048), backbone, tmp_path / "other", mode="registered"))


def test_p9ii_test_seeds_are_not_s0_seeds() -> None:
    with pytest.raises(ValueError):
        core.check_seed_set("registered", "p9ii-test-1")
    core.check_seed_set("dry", "p9ii-test-1")  # allowed only in dry mode, for the identity check against studies.p9ii


# --- identity with studies.p9ii (G4) ------------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("arm", ["A0", "A1", "A2", "A5-D", "A6", "A7"])
def test_arms_equal_p9ii_on_a_shared_seed_set(arm: str, backbone, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    shared = syn.tiny_corpus()
    from studies.p9 import data as d

    data = d.build_study_data(p9iicore.test_seeds(1), shared, sizes=d.DataSizes(main_trained=512, unseen=64, lane_d_per_set=128))
    r = gates.identity_against_p9ii(arm, data, backbone, tmp_path, p9ii_mode="calibration", s0_mode="dry", init_seed=910041, unit=8, facts=128, updates=2)
    assert r["passed"], r


# --- the rehearsal whitelist ---------------------------------------------------------------------------------------------------------------------------
def test_rehearsal_mode_writes_only_the_whitelisted_record(draw, backbone, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    j = job("A2", draw, backbone, tmp_path, mode="dry", rehearsal_phase="post", snapshots=(), whitelist_only=True, extra={"busy_processes": 12})
    train.run_job(j)
    files = sorted(p.name for p in j.out_dir.iterdir())
    assert files == ["rehearsal.json"]
    rec = core.read_record(j.out_dir / "rehearsal.json", "rehearsal")
    assert set(rec) <= train.REHEARSAL_RECORD_KEYS and rec["phase"] == "post" and rec["busy_processes"] == 12 and rec["mode"] == "dry" and rec["block"] == "Q1"
    text = json.dumps(rec).lower()
    assert "task_loss" not in text and "accuracy" not in text and rec["loss_finite"] is True


def test_the_whitelist_rejects_forbidden_keys_values_and_names() -> None:
    good = {**core.envelope("rehearsal"), "mode": "rehearsal", "label": "x", "arm": "A0", "celltype": "2K/4K", "slots": 4096, "facts": 2048, "phase": "main", "updates": 256, "wall_seconds": 1.0}
    train.validate_rehearsal_record(good)
    for extra in ({"task_loss": 0.1}, {"accuracy": 0.5}, {"shapes": {"loss_head": [1]}}, {"parameter_counts": {"bits": 3}}):
        with pytest.raises(train.RehearsalRecordError):
            train.validate_rehearsal_record({**good, **extra})
    for bad in ({"arm": "A9"}, {"celltype": "nope"}, {"phase": "k0"}, {"wall_seconds": float("nan")}, {"loss_finite": 1}, {"slots": 1000}, {"study": "P9II"}):
        with pytest.raises(train.RehearsalRecordError):
            train.validate_rehearsal_record({**good, **bad})
    with pytest.raises(train.RehearsalRecordError):
        train.validate_rehearsal_record({"kind": "rehearsal", "schema": 1, "study": "P10S0"})  # lacks mode


def test_a_misplaced_rehearsal_phase_is_refused(draw, backbone, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(ValueError, match="rehearsal phase"):
        train.run_job(job("A0", draw, backbone, tmp_path, rehearsal_phase="pre"))


def test_a_failed_cell_keeps_its_record(draw, backbone, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    j = job("A1", draw, backbone, tmp_path, hyper=core.HYPER._replace(lambda_=float("nan")))  # a non-finite loss from the first update
    with pytest.raises(ValueError, match="non-finite"):
        train.run_job(j)
    rec = core.read_record(j.out_dir / "train.json", "train")
    assert rec["status"] == "failed" and "non-finite" in rec["reason"] and rec["arm"] == "A1"


# --- evaluation and the read swap ---------------------------------------------------------------------------------------------------------------------
def _trained(arm: str, draw, backbone, tmp: Path, updates: int = 8):  # type: ignore[no-untyped-def]
    j = job(arm, draw, backbone, tmp, updates=updates, snapshots=(updates,))
    return j, train.run_job(j)


def test_evaluation_record_is_p9ii_s_with_s0_s_envelope_and_the_swap(draw, backbone, rows, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    for arm in ("A5-D", "WX-A1", "A6", "A7"):
        j, ex = _trained(arm, draw, backbone, tmp_path)
        rec = evaluate.evaluate_readout(j.cell, ex.model, draw, 128, 8, frozen_backbone=backbone, rows=rows, target_seed=j.target_seed, swap_seed=SPEC.swap_seed(2048))
        assert rec["study"] == "P10S0" and rec["kind"] == "eval" and rec["arm"] == arm and rec["block"] == "Q1" and rec["identity"] == core.code_identity() and "stage" not in rec
        assert {"panels", "secondary", "probe", "language_modelling", "g5", "panel_statistics"} <= set(rec) and rec["g5"]["passed"]
        assert ("read_swap" in rec) == (arm in core.LEARNED_ARMS)
        if "read_swap" in rec:
            for p in ("A", "B"):
                s = rec["read_swap"][p]
                assert 0 <= s["a_use"] <= s["accuracy"] <= 1 and s["facts"] == 128 and s["a_use_count"] <= s["correct"] and s["accuracy"] == pytest.approx(rec["panels"][p]["accuracy"])
        json.dumps(core.jsonable(rec))


def _naive_swap(m: Any, data: Any, facts: int, panel: str, perm: torch.Tensor) -> dict[str, int]:
    """One site at a time, contexts one at a time, written independently of ``evaluate.read_swap``."""
    from studies.p9 import core as p9core
    from studies.p9i.evaluate import stream_for

    stream = stream_for(data, facts, core.PANEL_STREAM[panel])
    keep = (stream.fact_ids < facts).all(dim=1)
    tokens, ids, answers = stream.tokens[keep][:, :63], stream.fact_ids[keep], stream.answer_targets()[keep]
    where: dict[int, tuple[int, int]] = {int(f): (c, r) for c in range(ids.shape[0]) for r, f in enumerate(ids[c].tolist())}
    sites = p9iimodel.SITES
    m.eval()
    correct = used = 0
    index = torch.tensor(p9core.ALPHABET)
    with torch.no_grad():
        deltas, hs = [], []
        for c in range(tokens.shape[0]):
            h = m.embed_block0(tokens[c : c + 1])
            hs.append(h)
            deltas.append(m.memory_delta(h, m.select(h, tokens[c : c + 1])))
        for c in range(tokens.shape[0]):
            own = m.finish(hs[c], deltas[c])
            for r in range(8):
                f = int(ids[c, r])
                site_logits = own[0, sites[r]][None]
                ok = bool(p9core.score_answer_sites(site_logits, answers[c, r][None]).correct[0])
                pc, pr = where[int(perm[f])]
                replaced = deltas[c].clone()
                replaced[0, sites[r]] = deltas[pc][0, sites[pr]]
                swapped = m.finish(hs[c], replaced)[0, sites[r]]
                inside = swapped[index]
                still = bool(inside[answers[c, r]] >= inside.max())
                correct += ok
                used += int(ok and not still)
    return {"correct": correct, "used": used}


@pytest.mark.parametrize("arm", ["A5-D", "WX-A5-D", "A1"])
def test_read_swap_equals_a_naive_one_site_at_a_time_implementation(arm: str, draw, backbone, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    j, ex = _trained(arm, draw, backbone, tmp_path, updates=24)
    perm = evaluate.swap_permutation(draw, 128, SPEC.swap_seed(2048))
    for panel in ("A", "B"):
        mine = evaluate.read_swap(ex.model, draw, 128, panel, perm)
        naive = _naive_swap(ex.model, draw, 128, panel, perm)
        assert (mine["correct"], mine["a_use_count"]) == (naive["correct"], naive["used"]), (arm, panel)


def test_a_model_with_no_read_has_a_use_zero_and_a_perfect_reader_has_a_use_equal_to_accuracy(draw, backbone, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    perm = evaluate.swap_permutation(draw, 128, SPEC.swap_seed(2048))
    m = model.build_model("A0", 4096, 920041, backbone)
    with torch.no_grad():
        m.addition.wo.zero_()  # the read contributes nothing: swapping it changes nothing
    s = evaluate.read_swap(m, draw, 128, "A", perm)
    assert s["a_use_count"] == 0 and s["swapped_still_answer"] == s["correct"]


def test_a_use_is_a_share_of_all_facts_and_the_conditional_share_is_recorded() -> None:
    assert evaluate.ALPHABET_INDEX.numel() == 32


@pytest.mark.parametrize("a_use,bits", [(0.5, 1.523), (0.8, 3.287), (0.9, 4.036), (0.95, 4.466)])
def test_information_bits_follow_adr_0021(a_use: float, bits: float) -> None:
    n = 2048
    assert evaluate.information_bits(int(round(a_use * n)), n) == pytest.approx(bits, abs=5e-3)


def test_information_bits_are_zero_at_or_below_the_chance_interval() -> None:
    from studies.p9 import core as p9core

    n = 2048
    high = p9core.chance_interval(n, p9core.G2_TESTS_PRIMARY).high
    assert evaluate.information_bits(high, n) == 0.0 and evaluate.information_bits(high + 1, n) > 0.0 and evaluate.information_bits(0, n) == 0.0
    assert evaluate.binary_entropy(0.0) == 0.0 == evaluate.binary_entropy(1.0) and evaluate.binary_entropy(0.5) == pytest.approx(1.0) and math.isfinite(evaluate.information_bits(n, n))


def test_evaluate_cell_checks_the_snapshot_hash(draw, backbone, rows, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    j, _ = _trained("A5-D", draw, backbone, tmp_path)
    args = {"facts": 128, "readouts": [8], "init_seed": j.init_seed, "r1_seed": j.r1_seed, "rows": rows, "target_seed": j.target_seed, "swap_seed": SPEC.swap_seed(2048), "out_dir": j.out_dir, "require_train_record": True}
    paths = evaluate.evaluate_cell(j.cell, tmp_path, draw, backbone, **args)
    assert paths[0].is_file() and core.read_record(paths[0], "eval")["update"] == 8
    with pytest.raises(FileExistsError):
        evaluate.evaluate_cell(j.cell, tmp_path, draw, backbone, **args)
    snap = j.out_dir / "snapshots/u0000008/model.pt"
    blob = bytearray(snap.read_bytes())
    blob[-9] ^= 1
    snap.write_bytes(bytes(blob))
    paths[0].unlink()
    with pytest.raises(ValueError, match="does not match the hash"):
        evaluate.evaluate_cell(j.cell, tmp_path, draw, backbone, **args)
    with pytest.raises(ValueError, match="no train record"):
        evaluate.evaluate_cell(j.cell, tmp_path, draw, backbone, **{**args, "out_dir": tmp_path / "nowhere"})


# --- gates (tiny) ------------------------------------------------------------------------------------------------------------------------------
def test_g4_g5_g6_pass_on_a_tiny_draw_at_every_cell_type(backbone, draw, draw8k, rows, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    d32 = syn.tiny_data(SPEC, 32768)
    out = gates.run_g4_g5_g6(
        {2048: draw, 8192: draw8k, 32768: d32}, backbone, mode="dry", restore_split=4, out_dir=tmp_path, init_seed=920041, rows=rows, swap_seed=SPEC.swap_seed(2048), unit=8,
        facts_of=lambda real: {2048: 128, 8192: 256, 32768: 256}[real],
    )  # fmt: skip
    assert out["g4_defects"] == [] and out["harness_errors"] == [] and out["g4_passed"] and out["g5_passed"] and out["g6_passed"], out["g4_defects"]
    c = out["checks"]
    assert set(c["read_swap"]) == {"2K/4K", "8K/16K", "8K/4K", "32K/64K"} and all(v["passed"] for v in c["read_swap"].values())
    assert {k.split("@")[0] for k in c["gradient_reach"]} == {"A0", "A1", "A2", "A5-D", "A6", "A7", "WX-A5-D", "WX-A1"}
    assert "A1@8K/4K" not in c["gradient_reach"] and "A2@8K/4K" not in c["gradient_reach"] and "A0@32K/64K" not in c["gradient_reach"]  # no target injection at 8K/4K; only candidates at 32K/64K
    assert set(c["restoration"]) >= {"WX-A5-D@2K/4K", "WX-A1@8K/16K", "A5-D@8K/4K", "A1@32K/64K"} and all(v["identical"] for v in c["restoration"].values())
    assert set(c["a2_switch"]) == {"2K/4K", "8K/16K"} and c["wx_equivalence"]["passed"] and c["schedules"]["passed"] and c["registry"]["passed"] and c["determinism"]["identical"]
    assert set(out["g6"]["arms"]) == set(core.LEARNED_ARMS) and out["g6"]["trained"]["passed"] and set(out["g5"]) >= {"WX-A1@2K/4K", "A6@32K/64K"}


def test_a_gate_with_no_data_for_a_cell_type_is_a_harness_error_not_a_defect(backbone, draw, rows, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    out = gates.run_g4_g5_g6({2048: draw}, backbone, mode="dry", restore_split=2, out_dir=tmp_path, init_seed=920041, rows=rows, swap_seed=SPEC.swap_seed(2048), unit=8, facts_of=lambda real: 128, celltypes=("2K/4K", "8K/16K"))
    assert out["harness_errors"] == ["no data for 8192 facts: 8K/16K was not checked"] and out["g4_defects"] == [] and not out["g4_passed"]


def test_schedule_and_registry_checks() -> None:
    assert gates.schedule_checks()["passed"] and gates.registry_checks()["passed"]
    assert gates.registry_checks()["protocol_identical_to_p9ii"] == {"2K/4K = Stage 1": True, "8K/16K = Stage 2": True, "readouts": True}


def test_wx_equivalence_gate_asserts_bitwise_only_on_the_registered_platform(backbone, draw) -> None:  # type: ignore[no-untyped-def]
    tokens = train.training_stream_for(draw, 128).batch(1).tokens[:, :63]
    r = gates.wx_equivalence(backbone, 4096, 920041, tokens)
    assert r["passed"] and r["max_abs_difference"] <= 1e-6 and r["asserted_bitwise"] == core.on_registered_platform() and r["parameters"] == 32768 and r["zero_padding_before_position_0"]
    if core.on_registered_platform():
        assert r["bit_identical"]


def test_read_swap_checks_with_a_model(draw, backbone) -> None:  # type: ignore[no-untyped-def]
    m = model.build_model("A5-D", 4096, 920041, backbone)
    r = gates.read_swap_checks(draw, 128, SPEC.swap_seed(2048), m)
    assert r["passed"] and r["swap_twice_restores_logits"] and r["tie_counts_as_answer"] and r["no_fixed_point"] and r["no_equal_answer_pair"]


def test_g6_check_without_a_changed_table_fails(backbone) -> None:  # type: ignore[no-untyped-def]
    same = torch.arange(10)
    assert not gates.g6_check(backbone, 4096, 920041, torch.zeros(2, 63, dtype=torch.int64), same, same)["passed"]  # the two tables must differ for the check to mean anything
