# ruff: noqa: E501
"""P10S1 revision 5: the arms at the new sizes (T-OQ at 1,024 slots, the index read at 1,024, F-OQ at 256, R2 at 32,768 rows), G7 at every slot count, the item-cap deadline, and the guards (the
refusal while a study of the project is running, the registered-mode refusals, G9 with 2193 and its derived seeds; brief groups 1, 13 and the confirmations of section 3). The process list of every
concurrency test is injected: no test reads the real process list. Self-check only: not independent review, not Astra validation, not human approval."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402
import torch  # noqa: E402
from test_p10s1_model import FACTS, backbone, data, job, tokens_of  # noqa: E402

from studies.p10s1 import core, evaluate, gates, index, stages, timing, train  # noqa: E402
from studies.p10s1 import model as M  # noqa: E402


# --- the arms at the new sizes --------------------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("slots", [256, 1024])
def test_counters_equal_the_formulas_at_256_and_1024_slots(slots: int) -> None:
    r = gates.work_counters(data(), backbone(), slots, FACTS, init_seed=2101, tokens=tokens_of())
    arms = [a for a, ns in core.arm_slot_counts().items() if slots in ns]
    assert arms == (["F-OQ"] if slots == 256 else ["F-OQ", "T-OQ", "H8", "D-OQ"]) and r["passed"]
    for arm in arms:
        assert r[arm]["counted"]["W"] == r[arm]["formula"]["W"], arm
    assert r["F-OQ"]["counted"]["K"] == slots and r["F-OQ"]["counted"]["W"] == (5376 if slots == 256 else 17664)
    assert ("F-OQ-IVF" in r) == (slots == 1024)  # the index read is not defined at 256 slots
    if slots == 1024:
        assert r["T-OQ"]["counted"]["K"] == 4 + 512 and r["D-OQ"]["counted"]["hidden"] == 1024 and r["F-OQ-IVF"]["passed"]


def test_t_oq_at_1024_slots_has_four_branches_and_reads_two_of_them() -> None:
    m = M.build_model("T-OQ", 1024, 2101, backbone(), r1_seed=7, seed_rng=False)
    assert m.slots // core.BRANCH_SIZE == 4 and core.VISIT == 2 and core.TREE_CANDIDATES == 512 and core.work_formula("T-OQ", 1024)["K"] == 4 + 512  # 512 of the 1,024 keys


def test_the_index_read_at_1024_slots_has_four_centroids_and_at_least_512_candidates() -> None:
    gen = torch.Generator().manual_seed(11)
    keys = torch.randn(1024, 16, generator=gen)
    idx = index.build_index(keys, 5)
    assert idx.lists == 4 and int(idx.sizes.sum()) == 1024
    q = torch.nn.functional.normalize(torch.randn(40, 16, generator=gen), dim=-1)
    _mask, counts = index.candidate_mask(idx, q)
    assert bool((counts >= 512).all()) and bool((counts <= 1024).all())
    m = M.build_model("F-OQ", 256, 2101, backbone(), r1_seed=7, seed_rng=False)
    with pytest.raises(ValueError, match="256 slots"):
        evaluate.ivf_model(m, data().seeds)  # one list would read every key


def test_256_slots_is_f_oq_only_and_an_r2_table_of_32768_rows_is_built() -> None:
    for arm in ("T-OQ", "H8", "D-OQ"):
        with pytest.raises(ValueError, match="256 slots"):
            M.build_model(arm, 256, 2101, backbone(), r1_seed=7, seed_rng=False)
        with pytest.raises(ValueError):
            core.work_formula(arm, 256)
    foq = M.build_model("F-OQ", 256, 2101, backbone(), r1_seed=7, seed_rng=False)
    assert foq.slots == 256 and core.foq_trainable_parameters(256) == 13313
    lut = train.fact_lut_for(data(), FACTS)
    r2 = M.build_model("R2", 32768, 2101, backbone(), fact_lut=lut, r1_seed=7, seed_rng=False)
    assert r2.slots == 32768 and core.work_formula("R2", 32768)["W"] == 1056
    out = r2(tokens_of()[:, : core.INPUT_LENGTH].contiguous())
    assert out is not None
    with pytest.raises(ValueError):
        core.make_cell("R2", "R2", 2048, 32768 * 2, 1, 2101)  # no 65,536-slot table


def test_training_at_256_slots_runs_and_the_whitelist_takes_the_new_sizes(tmp_path: Path) -> None:
    j = job(tmp_path, "F-OQ", slots=256, updates=2, snapshots=(2,))
    record = train.train_cell(j)
    assert record["status"] == "completed" and record["slots"] == 256
    rec = {**core.envelope("rehearsal"), "mode": "rehearsal", "arm": "R2", "slots": 32768, "facts": 32768}
    train.validate_rehearsal_record(rec)
    with pytest.raises(train.RehearsalRecordError):
        train.validate_rehearsal_record({**rec, "slots": 65536})


def test_a_run_still_running_at_its_item_cap_is_stopped_kept_and_marked(tmp_path: Path) -> None:
    j = job(tmp_path, "F-OQ", slots=1024, updates=50, snapshots=(50,), name="capped")
    j.deadline_epoch = 0.0  # the item's cap passed before the first update
    with pytest.raises(train.ItemCapReached):
        train.train_cell(j)
    rec = core.read_record(j.out_dir / "train.json", "train")
    assert rec["status"] == "failed" and "ItemCapReached" in str(rec["reason"])  # kept and marked: no U_L, never re-run


# --- group 13: the guards ------------------------------------------------------------------------------------------------------------------------------
S0_LINE = "/usr/bin/python3 -m studies.p10s0.stages registered train --run-dir /x"
S2_LINE = "python -m studies.p10s2.stages train"


def test_the_concurrency_check_refuses_while_a_p10s0_or_p10s2_stage_process_is_alive() -> None:
    quiet = ["/bin/zsh", "python -m studies.p10s1.stages timing --preview", "uv run pytest tests/test_p10s0_core.py", "grep p10s2"]
    assert timing.other_study_processes(quiet) == []
    rec = timing.concurrency_check(quiet)
    assert rec["checked"] and rec["other_study_processes"] == [] and rec["statement"] == timing.CONCURRENCY_STATEMENT and rec["source"] == "injected"
    for line in (S0_LINE, S2_LINE):
        assert timing.other_study_processes([*quiet, line]) == [line]
        with pytest.raises(timing.OtherStudyRunning):
            timing.concurrency_check([*quiet, line])
    assert timing.other_study_processes(["python -m studies.p10s0x.stages", "python -m studies.p10s10.stages"]) == []  # only the two studies' own modules


def test_the_stages_that_must_not_overlap_refuse_and_calibration_may(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(timing, "running_commands", lambda: [S0_LINE])
    args = stages.build_parser().parse_args(["timing", "--mode", "rehearsal", "--run-dir", str(tmp_path)])
    for name in ("timing", "rehearse", "timing-preview"):
        with pytest.raises(timing.OtherStudyRunning):
            stages.concurrency_guard(name, args)
    reg = stages.build_parser().parse_args(["train", "--mode", "registered", "--run-dir", str(tmp_path)])
    with pytest.raises(timing.OtherStudyRunning):
        stages.concurrency_guard("train", reg)  # every registered stage
    cal = stages.build_parser().parse_args(["calibrate", "--mode", "calibration", "--run-dir", str(tmp_path)])
    assert stages.concurrency_guard("calibrate-load-row-up", cal) is None  # calibration training may overlap another study's training
    dry = stages.build_parser().parse_args(["timing", "--mode", "rehearsal", "--dry", "--run-dir", str(tmp_path)])
    assert stages.concurrency_guard("timing", dry)["checked"] is False  # the DRY profile measures nothing
    monkeypatch.setattr(timing, "running_commands", lambda: [])
    assert stages.concurrency_guard("timing", args)["checked"] is True


def test_the_timing_preview_the_isolated_timing_and_the_rehearsal_exit_2_while_another_study_runs(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(timing, "running_commands", lambda: [S2_LINE])
    common = ["--experiments-root", str(tmp_path), "--ledger-root", str(tmp_path)]
    assert stages.main(["timing", "--preview", "--mode", "rehearsal", "--run-dir", str(tmp_path / "a"), *common]) == 2
    assert stages.main(["timing", "--mode", "rehearsal", "--run-dir", str(tmp_path / "b"), *common]) == 2
    assert stages.main(["rehearse", "--calibration", str(tmp_path / "no.json"), "--run-dir", str(tmp_path / "c"), *common]) == 2  # refused before anything is read or run
    assert not any((tmp_path / n / "timing_preview.json").exists() for n in "ab") and not (tmp_path / "P10S1-ledger.json").exists()  # nothing was charged or written
    assert stages.main(["timing", "--preview", "--mode", "registered", "--run-dir", str(tmp_path / "d"), *common]) == 2  # a preview is never a registered stage


def test_registered_mode_is_refused_without_a_freeze_whatever_the_tree_and_whatever_is_typed(tmp_path: Path) -> None:
    for argv in (
        ["registered", "gates", "--run-dir", str(tmp_path), "--freeze-commit", "0" * 40],
        ["registered", "train", "--run-dir", str(tmp_path), "--freeze-commit", "0" * 40, "--stage-cap-seconds", "99999"],
        ["registered", "evaluate", "--run-dir", str(tmp_path), "--freeze-commit", "0" * 40, "--only", "x"],
        ["work", "train", "--mode", "registered", "--run-dir", str(tmp_path), "--freeze-commit", "0" * 40, "--labels", "x"],
        ["work", "gates", "--mode", "registered", "--run-dir", str(tmp_path), "--freeze-plan", str(tmp_path / "plan.json"), "--freeze-plan-sha256", "0" * 64],
        ["train", "--mode", "registered", "--run-dir", str(tmp_path)],
        ["timing", "--preview", "--mode", "registered", "--run-dir", str(tmp_path)],
        ["calibrate", "--mode", "registered", "--run-dir", str(tmp_path), "--items", "load,row-up"],
    ):
        assert stages.main(argv) == 2, argv


def test_calibration_refuses_what_it_must(tmp_path: Path) -> None:
    common = ["--experiments-root", str(tmp_path), "--ledger-root", str(tmp_path), "--dry"]
    assert stages.main(["calibrate", "--run-dir", str(tmp_path / "x"), "--items", "load,row-up", *common]) == 2  # no timing preview: nothing starts on an assumed cost
    assert stages.main(["calibrate", "--run-dir", str(tmp_path / "x"), "--items", "load", *common]) == 2  # an item alone is not a group
    good = tmp_path / "good.json"
    core.write_record(good, {**core.envelope("timing"), "preview": True, "status": "MEASURED", "wall_per_update": {}})
    assert stages.main(["calibrate", "--run-dir", str(tmp_path / "x"), "--items", "h8,dense", "--timing", str(good), *common]) == 2  # items 2 and 3 need the finalized items 0b and 1
    assert stages.main(["calibrate", "--run-dir", str(tmp_path / "x"), "--items", "load,row-up", "--timing", str(tmp_path / "missing.json"), *common]) == 2
    assert stages.main(["calibrate", *common]) == 2  # nothing to do
    assert stages.main(["calibrate", "--finalize", *common]) == 2  # --run-dir is required
    preview = tmp_path / "preview.json"
    core.write_record(preview, {**core.envelope("timing"), "preview": False, "status": "MEASURED", "wall_per_update": {}})
    assert stages.main(["calibrate", "--run-dir", str(tmp_path / "x"), "--items", "load,row-up", "--timing", str(preview), *common]) == 2  # not a timing preview
    cell = core.load_search_cells(8)[0]
    with pytest.raises(stages.CalibrationRefused):
        stages.calibration_guard(core.make_cell("P", "F-OQ", 8192, 1024, 1, 2101), 8192)  # a registered cell
    with pytest.raises(stages.CalibrationRefused):
        stages.calibration_guard(core.make_cell("CAL", "F-OQ", 8192, 1024, 3, 2191, run_updates=262144), 8192)  # a draw that is not a calibration draw
    stages.calibration_guard(core.load_search_cells()[0], 8192)
    stages.calibration_guard(core.dense_rate_cells({2048: 16384, 8192: 8192, 32768: 32768})[0], 8192)  # items 2 and 3 run at any of the candidates
    assert cell.draw in core.CALIBRATION_DRAWS


def test_g9_declares_2193_and_its_derived_seeds_and_checks_them() -> None:
    ns = core.seed_namespaces()
    assert 2193 in ns["init"] and 2191 in ns["init"] and 2192 in ns["init"] and {3193, 4193, 5193, 6193, 7193} <= ns["derived_init"]
    assert core.seed_check()["passed"] and core.CALIBRATION_INIT_SEEDS_BY_DRAW == {1: 2191, 2: 2193}
    assert not core.seed_check(namespaces={**ns, "init": ns["init"] | {1701}})["passed"]  # P9's initialization seed
    assert not core.seed_check(namespaces={**ns, "derived_init": ns["derived_init"] | {3091}})["passed"]  # S0's derived initialization seed (2091 + 1000)
    assert not core.seed_check(namespaces={**ns, "calibration": ns["calibration"] | {2193}, "init": ns["init"]})["passed"]  # a calibration seed that collides with an initialization seed
    for k, c in enumerate(core.calibration_cells()):
        assert c.init_seed in (2191, 2193) and c.draw in (1, 2) and (c.init_seed == 2191) == (c.draw == 1), k
    json.dumps(core.seed_check())
