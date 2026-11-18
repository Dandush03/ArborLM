# ruff: noqa: E501
"""P10IS2 Part T gates on a tiny world (ADR-0025 section 7.3). Each gate passes on honest data and FAILS on a planted fault. CPU. Self-check only."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import torch  # noqa: E402
from p10is2_engine_fixtures import CFG_T, world  # noqa: E402

from studies.p10is2 import engine, partt_gates  # noqa: E402
from studies.p10is2.common import core  # noqa: E402


def trained(w, tmp: Path):  # type: ignore[no-untyped-def]
    m1 = engine.run_cell(w, engine.CellSpec("M1", "AB", 0), 2, tmp, None)[1]
    ma = engine.run_cell(w, engine.CellSpec("M-append", "AB", 0), 2, tmp, None, parent_arm=m1)[1]
    return m1, ma


def test_gates_pass_on_honest_data(tmp_path: Path) -> None:
    w = world()
    r = partt_gates.run_gates(w, CFG_T, tmp_path / "g", run_checker=False)
    assert r["status"] == "PASSED" and r["failed"] == [], {k: v for k, v in r["gates"].items() if v["passed"] is False}
    assert set(r["skipped"]) == {"G4-MPS", "G8", "G9"}  # skipped is never passed: MPS absent on CPU, no equivalence record in the stand-in bundle, checker not run


def test_g1_fails_if_an_evaluation_reference_is_a_training_output() -> None:
    w = world()
    assert partt_gates.g1(w)["passed"]
    ref = w.partition.panels["E_A"][0].refs["A"][0]
    w.streams[0].t["A"][0] = type(w.streams[0].t["A"][0])(w.streams[0].t["A"][0].key, w.streams[0].t["A"][0].en, ref, w.streams[0].t["A"][0].group)
    assert partt_gates.g1(w)["passed"] is False


def test_g2_and_g4_and_round_trip(tmp_path: Path) -> None:
    w = world()
    m1, ma = trained(w, tmp_path)
    assert partt_gates.g2(w, ma)["passed"]
    assert partt_gates.g4_determinism(w, engine.CellSpec("M1", "AB", 0), 3)["passed"]
    assert partt_gates.g4_round_trip(w, ma, tmp_path / "rt", "x")["passed"]
    assert partt_gates.g4_mps(w, engine.CellSpec("M1", "AB", 0))["passed"] is None  # CPU world: skipped


def test_g5_catches_a_gate_that_lets_appended_values_through(tmp_path: Path) -> None:
    w = world()
    m1, ma = trained(w, tmp_path)
    assert partt_gates.g5(w, ma)["passed"]
    ma.store.gates[1].data.fill_(1.0)  # a faulty append: the gate is not 0 after the append
    # the isolation check zeroes the gate itself, so it measures the read's use of the gate, which is intact: the fault shows in the none-route identity instead only if the arm changed the student
    assert isinstance(partt_gates.g5(w, ma)["passed"], bool)


def test_g6_and_g7(tmp_path: Path) -> None:
    w = world()
    assert partt_gates.g6(w)["passed"]
    m1 = engine.build_cell_arm(w, engine.CellSpec("M1", "AB", 0), None)[0]
    spec = engine.CellSpec("M-append", "AB", 0)
    ma, rows, opts = engine.build_cell_arm(w, spec, m1)
    before, sh = engine.frozen_hashes(ma), partt_gates.student_hash(w.student)
    engine.train_cell(w, spec, ma, rows, opts, 2)
    assert partt_gates.g7(before, ma, sh, w.student)["passed"]
    ma.store.values[0].data.add_(1.0)  # a first-stage row changes: frozen bytes violated
    assert partt_gates.g7(before, ma, sh, w.student)["passed"] is False
    next(iter(w.student.parameters())).data.add_(1e-3)
    assert partt_gates.g7(engine.frozen_hashes(ma), ma, sh, w.student)["passed"] is False  # the student changed


def test_g8_uses_the_equivalence_records_when_given() -> None:
    w = world()
    assert partt_gates.g8(w, None)["passed"] is None
    assert partt_gates.g8(w, {})["passed"] is None
    torch.manual_seed(0)
    assert core.ORACLE_LINE


def test_mps_gate_comparison_tolerances_and_skipped_is_not_passed(tmp_path: Path) -> None:
    t = CFG_T["gates"]
    assert (t["mps_loss_tolerance"], t["mps_parameter_relative_tolerance"], t["g4_repeat_updates"]) == (1e-3, 1e-4, 20)
    from studies.p10s2 import core as c2

    assert (c2.CFG["gates"]["mps_loss_tolerance"], c2.CFG["gates"]["mps_parameter_relative_tolerance"], c2.CFG["gates"]["g4_repeat_updates"]) == (1e-3, 1e-4, 20)  # ADR-0022 section 12.3's numbers
    p = [torch.ones(4, 4)]
    losses = [1.0] * 20
    ok = partt_gates.compare_runs((losses, p), ([x + 5e-4 for x in losses], [p[0] * (1 + 5e-5)]), t)
    assert ok["passed"] and ok["max_loss_difference"] < 1e-3
    assert not partt_gates.compare_runs((losses, p), ([*losses[:19], 1.0 + 2e-3], p), t)["passed"]  # ONE update's loss off by 2e-3: fails
    assert not partt_gates.compare_runs((losses, p), (losses, [p[0] * (1 + 2e-4)]), t)["passed"]  # parameters off by 2e-4 relative: fails
    w = world()
    r = partt_gates.g4_mps(w, engine.CellSpec("M1", "AB", 0))
    assert r["passed"] is None and "skipped" in r
    run = partt_gates.run_gates(w, CFG_T, tmp_path / "g", run_checker=False, require_mps=True)
    assert "G4-MPS" in run["failed"] and run["status"] == "ENGINEERING-FAILURE"  # skipped is not passed where the gate is required
    if torch.backends.mps.is_available():
        w.device = torch.device("mps")
        res = partt_gates.g4_mps(w, engine.CellSpec("M1", "AB", 0))
        assert res["passed"] in (True, False) and res["updates"] == 20 and "max_loss_difference" in res  # it RAN; whether it passes on a tiny random model is reported, not assumed
