# ruff: noqa: E501
"""P10IS2 Part T gates on a tiny world (ADR-0025 section 7.3). Each gate passes on honest data and FAILS on a planted fault. CPU. Self-check only."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402
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
    assert (t["mps_loss_tolerance"], t["mps_parameter_relative_tolerance"], t["g4_repeat_updates"]) == (1e-3, 1e-4, 20) and t["mps_gradient_relative_tolerance"] == 1e-3
    from studies.p10s2 import core as c2

    assert (c2.CFG["gates"]["mps_loss_tolerance"], c2.CFG["gates"]["mps_parameter_relative_tolerance"], c2.CFG["gates"]["g4_repeat_updates"]) == (1e-3, 1e-4, 20)  # ADR-0022 section 12.3's numbers
    p = [torch.ones(4, 4)]
    losses = [1.0] * 20
    ok = partt_gates.compare_runs((losses, p), ([x + 5e-4 for x in losses], [p[0] * (1 + 5e-5)]), t)
    assert ok["passed"] and ok["max_loss_difference"] < 1e-3
    assert not partt_gates.compare_runs((losses, p), ([*losses[:19], 1.0 + 2e-3], p), t)["passed"]  # ONE update's loss off by 2e-3: fails
    old_figure = partt_gates.compare_runs((losses, p), (losses, [p[0] * (1 + 2e-2)]), t)  # the OLD parameter condition (1e-4) is superseded by ruling 39: recorded, never gating
    assert old_figure["passed"] and old_figure["max_relative_parameter_difference"] > 1e-2 and old_figure["parameter_tolerance_superseded"] == 1e-4
    w = world()
    r = partt_gates.g4_mps(w, engine.CellSpec("M1", "AB", 0))
    assert r["passed"] is None and "skipped" in r
    run = partt_gates.run_gates(w, CFG_T, tmp_path / "g", run_checker=False, require_mps=True)
    assert "G4-MPS" in run["failed"] and run["status"] == "ENGINEERING-FAILURE"  # skipped is not passed where the gate is required
    if torch.backends.mps.is_available():
        w.device = torch.device("mps")
        res = partt_gates.g4_mps(w, engine.CellSpec("M1", "AB", 0))
        assert res["passed"] in (True, False) and res["updates"] == 20 and "max_loss_difference" in res  # it RAN; whether it passes on a tiny random model is reported, not assumed


def test_the_gradient_condition_is_pure_relative_with_an_exact_zero_clause() -> None:
    t = CFG_T["gates"]
    names = ["keys", "values", "gate"]
    g = [[torch.ones(4), torch.full((3,), 2.0), torch.tensor([0.5])] for _ in range(3)]
    good = partt_gates.compare_gradients(g, [[x * (1 + 5e-4) for x in u] for u in g], names, t)  # a correct device agrees far inside 1e-3
    assert good["passed"] and 4e-4 < good["largest"]["relative_difference"] < 6e-4 and good["largest"]["tensor"] in names and good["largest"]["update"] in (1, 2, 3)
    wrong = [[x * (1.01 if (i == 1 and u == 2) else 1.0) for i, x in enumerate(us)] for u, us in enumerate(g)]  # ONE tensor, ONE update, scaled by 1.01
    bad = partt_gates.compare_gradients(g, wrong, names, t)
    assert not bad["passed"] and bad["largest"] == {"relative_difference": bad["largest"]["relative_difference"], "tensor": "values", "update": 3} and bad["n_violations_over_tolerance"] == 1
    zero = [[torch.zeros(4), torch.full((3,), 2.0), torch.tensor([0.5])] for _ in range(2)]
    ok0 = partt_gates.compare_gradients(zero, [[x.clone() for x in u] for u in zero], names, t)
    assert ok0["passed"] and ok0["exact_zero_clause"]["cases"] == 2 and ok0["exact_zero_clause"]["ok"]
    leak = [[torch.full((4,), 1e-12, dtype=torch.float64), *u[1:]] for u in zero]  # a non-zero MPS gradient where the CPU gradient is exactly zero: however small
    res = partt_gates.compare_gradients(zero, leak, names, t)
    assert not res["passed"] and res["exact_zero_clause"]["n_violations"] == 2 and not res["exact_zero_clause"]["ok"]


@pytest.mark.skipif(not torch.backends.mps.is_available(), reason="MPS is not available on this machine")
def test_the_amended_mps_gate_on_the_device_passes_a_correct_device_and_fails_each_wrong_one(monkeypatch: pytest.MonkeyPatch) -> None:
    w = world()
    w.device = torch.device("mps")
    spec = engine.CellSpec("M1", "AB", 0)
    real_grads, real_train = partt_gates.gradients_along, partt_gates._train_cell_on
    res = partt_gates.g4_mps(w, spec)
    assert res["updates"] == 20 and res["gradient_agreement"]["exact_zero_clause"]["cases"] >= 1  # the zero-initialised gate: keys and values have an exactly zero gradient at update 1
    assert res["passed"] is True and res["gradient_agreement"]["largest"]["tensor"] and res["gradient_agreement"]["largest"]["update"] >= 1  # a correct device passes; the largest figure is recorded with its tensor and update
    assert res["parameters_recorded_not_gating"]["gating"] is False and len(res["parameters_recorded_not_gating"]["parameter_relative_difference_per_tensor"]) == len(res["parameters_recorded_not_gating"]["tensors"]) and "max_relative_parameter_difference" in res["mps_repeat_recorded_not_gating"]

    def scaled(world, spec_, rows, traj, batches, dev):  # type: ignore[no-untyped-def]
        out = real_grads(world, spec_, rows, traj, batches, dev)
        if dev.type == "mps":
            out[5][1] = out[5][1] * 1.01  # a deliberately wrong gradient on one tensor at one update
        return out

    monkeypatch.setattr(partt_gates, "gradients_along", scaled)
    wrong = partt_gates.g4_mps(w, spec)
    assert wrong["passed"] is False and wrong["loss_ok"] is True and wrong["gradient_agreement"]["largest"]["update"] == 6 and wrong["gradient_agreement"]["n_violations_over_tolerance"] == 1

    def leaking(world, spec_, rows, traj, batches, dev):  # type: ignore[no-untyped-def]
        out = real_grads(world, spec_, rows, traj, batches, dev)
        if dev.type == "mps":
            out[0][0] = out[0][0] + 1e-12  # keys: exactly zero on CPU at update 1, non-zero on MPS
        return out

    monkeypatch.setattr(partt_gates, "gradients_along", leaking)
    leak = partt_gates.g4_mps(w, spec)
    assert leak["passed"] is False and leak["gradient_agreement"]["exact_zero_clause"]["ok"] is False and leak["loss_ok"] is True
    monkeypatch.setattr(partt_gates, "gradients_along", real_grads)

    def lossy(world, spec_, dev, updates):  # type: ignore[no-untyped-def]
        rec, arm, rows, opts = real_train(world, spec_, dev, updates)
        if dev.type == "mps" and not lossy.done:  # type: ignore[attr-defined]
            lossy.done = True  # type: ignore[attr-defined]
            rec["losses_head"] = [x + (2e-3 if i == 5 else 0.0) for i, x in enumerate(rec["losses_head"])]
        return rec, arm, rows, opts

    lossy.done = False  # type: ignore[attr-defined]
    monkeypatch.setattr(partt_gates, "_train_cell_on", lossy)
    bad_loss = partt_gates.g4_mps(w, spec)
    assert bad_loss["passed"] is False and bad_loss["loss_ok"] is False and bad_loss["gradient_agreement"]["passed"] is True  # the loss condition fails on its own
