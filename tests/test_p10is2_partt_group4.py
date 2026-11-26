# ruff: noqa: E501
"""Third-audit items: the rehearsal draw is cleaned of stand-in reference matches so that G1 passes unchanged (ruling 24, N9), the counting rehearsal at the calibrated U with its allowance projected accordingly and the
measuring rehearsal at 200 (ruling 27), D_cal's real size in the calibration cap. Tiny world, test size. Self-check only."""

import dataclasses
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from p10is2_engine_fixtures import CFG_T, bundle, world  # noqa: E402

from studies.p10is2 import (  # noqa: E402
    engine,
    partt_caps,
    partt_gates,
    partt_real,
    partt_rehearsal,
)
from studies.p10is2.common import core  # noqa: E402
from studies.p10s2.routing import RouterSpec  # noqa: E402
from studies.p10s2.text import normalize  # noqa: E402


def planted_world(drop: bool):  # type: ignore[no-untyped-def]
    """A rehearsal world whose training draw holds one item per capability whose output equals a stand-in reference (the collision the audit estimates at about two in three on real data)."""
    b = bundle()
    rb = partt_rehearsal.rehearsal_bundle(b, CFG_T)
    ref = {c: rb.panels["E_A"][0].refs[c][0] for c in core.TASKS}
    a_keys = {x.key for x in b.accepted["A"]}
    disjoint = {"A": list(b.accepted["A"]), "B": [x for x in b.accepted["B"] if x.key not in a_keys]}  # Part Q's pools are disjoint in sources
    pool = {c: [dataclasses.replace(x, target=ref[c]) if i == 0 else x for i, x in enumerate(disjoint[c])] for c in core.TASKS}
    refs = {normalize(r) for n in ("E_A", "E_B", "E_C") for it in rb.panels[n] for rr in it.refs.values() for r in rr}
    info: dict = {}  # type: ignore[type-arg]
    draws = partt_real.rehearsal_draws(pool, CFG_T, per=len(pool["A"]), forbidden=refs if drop else None, report=info)
    base = world(updates=2, n_reps=1)
    run = engine.run_config(CFG_T, layer=1, updates=2, store_rate=0.003, lora_rate=0.001, device="cpu", batch=4, rows=16, router=RouterSpec.dry(), decision_token=8, window_tokens=24, ranks=(2, 4), replay=4)
    w = engine.build_world_t(rb, CFG_T, draws, run, plan_mode="test")
    del base
    return w, info, ref


def test_the_rehearsal_draw_is_cleaned_of_stand_in_matches_and_g1_passes_but_fails_without_the_drop() -> None:
    w, info, ref = planted_world(drop=True)
    assert info["applied"] is True and all(n >= 1 for n in info["dropped_per_capability"].values())  # the planted match is dropped and counted
    assert all(normalize(x.target) != normalize(ref[c]) for c in core.TASKS for x in w.streams[0].t[c])
    assert partt_gates.g1(w)["passed"] is True  # G1 runs UNCHANGED and passes
    w2, info2, _ = planted_world(drop=False)
    assert info2["applied"] is False
    assert partt_gates.g1(w2)["passed"] is False  # with the drop disabled the planted match fails G1: G1 is neither weakened nor report-only


def test_the_counting_allowance_is_projected_at_the_calibrated_u_and_the_measuring_record_carries_its_updates() -> None:
    rates = {"train:M1": 0.1, "score:plain": 0.01}
    meas = {"rates_seconds_per_unit": rates, "overhead_seconds": {"train": 5.0, "evaluate": 1.0}, "subset_units": {"train:M1": 200.0, "score:plain": 100.0}, "subset_processes": {"train": 1, "evaluate": 1}, "updates": 200}
    at200 = partt_caps.counting_projection_seconds(meas, {}, 200)["seconds"]
    at2000 = partt_caps.counting_projection_seconds(meas, {}, 2000)["seconds"]
    assert abs((at2000 - at200) - 0.1 * 200.0 * 9) < 1e-9  # only the training units scale: 200 updates x 10, at the measured rate
    assert partt_caps.counting_allowance_hours(meas, {}, 2000) > partt_caps.counting_allowance_hours(meas, {}, 200)


def test_the_measuring_rehearsal_trains_200_and_the_counting_rehearsal_the_calibrated_u() -> None:
    class P:
        data = {"calibration": {"U": 2000, "converged": True}}

    assert partt_real.calibration_of(CFG_T, P, "rehearsal", "measuring")["U"] == CFG_T["rehearsal"]["updates"] == 200
    assert partt_real.calibration_of(CFG_T, P, "rehearsal", "counting")["U"] == 2000  # ADR section 11 item 5: full U, so the checkpoint cadence and stability at full U are rehearsed
    assert partt_real.calibration_of(CFG_T, P, "registered", "counting")["U"] == 2000


def test_the_calibration_cap_counts_d_cals_real_size() -> None:
    assert CFG_T["data"]["d_cal_panel"] == 500
    meas = {"rates_seconds_per_unit": {"train:M1": 0.1, "train:D1": 0.1, "train:E-table": 0.1, "score:plain": 0.01}, "overhead_seconds": {"train": 1.0}}
    small = {**CFG_T, "data": {**CFG_T["data"], "d_cal_panel": 100}}
    assert partt_caps.calibration_projection_seconds(meas, CFG_T) > partt_caps.calibration_projection_seconds(meas, small)
