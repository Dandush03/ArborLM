# ruff: noqa: E501
"""P10IS5 tests of CV_R and the margin from M, K's registered enumeration, and E2's start (the 10-minute wait, the cold check, STORE CANNOT BE HELD COLD, recovery from pollution) with fakes and a tiny geometry.
No device; 'files' are empty placeholders. Self-check only: not independent review, not Astra validation, not human approval."""

import copy
import math
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from studies.p10is5 import analysis, bench, blocks, core, device, e2, rehearsal  # noqa: E402
from studies.p10is5 import plan as planmod  # noqa: E402
from studies.p10is5 import testing as T  # noqa: E402

CFG = core.load_config()


def mp(repeat: int, k: int, s: int, med: int, status: str = "OK") -> dict[str, Any]:
    return {"key": core.pass_key("M", repeat, k, s), "repeat": repeat, "k": k, "s": s, "counter_status": status, "latency_ns": [med] * 5, "wall_ns": 1_000_000_000}


def test_cv_r_and_margin_by_hand() -> None:
    c1 = [50, 55, 60, 65, 70]  # CV = sqrt(62.5) / 60
    c3 = [100, 100, 100, 100, 100]
    passes = [mp(r + 1, 1, 1, c1[r] * 1000) for r in range(5)] + [mp(r + 1, 1, 3, c3[r] * 1000) for r in range(5)] + [mp(1, 2, 1, 1)]
    out = rehearsal.cv_r(passes, [])
    want = math.sqrt(62.5) / 60
    assert out["cells"]["c(1)"]["cv"] == pytest.approx(want) and out["cells"]["c(3)"]["cv"] == 0.0 and out["cv_r"] == pytest.approx(want)
    m, spread = core.margin_from_cv(out["cv_r"], CFG)
    assert m == pytest.approx(max(0.10, 2 * want)) and not spread  # 2 x 0.1318 = 0.2635
    bad = rehearsal.cv_r([p if p["repeat"] != 2 else {**p, "counter_status": "STORE PAGES CACHED"} for p in passes], [])
    assert len(bad["cells"]["c(1)"]["medians_ns"]) == 4 and bad["cells"]["c(1)"]["left_out"]  # a failed counter pass is left out and listed
    assert rehearsal.cv_r([mp(1, 1, 1, 5), mp(1, 1, 3, 5)], [])["cv_r"] is None


def test_k_enumeration_from_a_plan() -> None:
    with T.scratch("e2_plan") as d:
        recs = {}
        for n in ("r1", "m"):
            (d / n).write_text(n)
            recs[n] = d / n
        plan = planmod.Plan(planmod.build_plan(CFG, ROOT, Path("/x/d.noindex"), d, recs))
        c = rehearsal.enumerate_registered_from_plan(plan)
        assert c["tiles_dealt"] == 3996 and c["passes"] == 144 and c["pages"] == 251_136 and c["distinct_pages"] == 251_136
        assert plan.geometry("rehearsal").tiles_needed() == 840 and plan.section("k")["tile_assignment_seed"] == 289242


ROOT = core.repo_root()


def tiny_cfg() -> dict[str, Any]:
    c = copy.deepcopy(dict(CFG))
    c["device"] = {**c["device"], "store_tiles": 24, "control_tiles": 24}
    return c


def e2_setup(d: Path, io: T.FakeIO, cfg: dict[str, Any]):  # type: ignore[no-untyped-def]
    ctx = T.tiny_context(d / "run", file_path=d / "store.bin", repeats=2, spare=True)
    (d / "store.bin").write_bytes(b"")
    clk = T.Clock()
    fs = T.FakeSystem(clk)
    deps = blocks.Deps(counter=T.FakeCounter(io), gate=T.scripted_gate(lambda: T.quiet_record(True)), run=fs.run, run_b=fs.run_b, sleep=clk.sleep, clock=clk, pread=io.pread, opener=io.opener)
    bench.write_prediction(ctx)
    pred = bench.load_prediction(ctx)
    led = device.WriteLedger(d / "run" / "w.json", 10**9)
    hours = core.HoursLedger(d / "run" / "h.json", 3600.0 * 5)
    return ctx, clk, deps, pred, led, hours


def test_e2_waits_ten_minutes_checks_cold_then_runs_blocks() -> None:
    cfg = tiny_cfg()
    cfg["seeds"] = {**cfg["seeds"], "store_contents": T.TEST_SEED_CONTENTS}
    with T.scratch("e2_ok") as d:
        io = T.FakeIO(T.TEST_SEED_CONTENTS)
        io.model_cache = True
        ctx, clk, deps, pred, led, hours = e2_setup(d, io, cfg)
        st = e2.run_e2(ctx, cfg, deps, led, hours, lambda r: blocks.inprocess_pass_runner(ctx, deps, pred), d / "control.bin", now=clk, e1_built_at=0.0)
        assert st.data["status"] == "COMPLETE" and clk.t >= 600  # no sooner than 10 minutes after E1's last write
        cold = e2.load_cold_checks(ctx)
        assert cold[0]["outcome"] == "COLD" and not cold[0]["rebuilt"]
        assert e2.harness_log_path(ctx).is_file() and hours.charged() >= 0
        reg = e2.build_registry(ctx, cfg, {"not_evaluable_reasons": []})
        reg["thresholds"]["valid_min_repeats"] = 1
        assert analysis.analyse(reg)["EQ-A"]["label"] == "BYTES CONFIRMED EXACTLY"
        assert e2.run_e2(ctx, cfg, deps, led, hours, lambda r: None, d / "control.bin", now=clk, e1_built_at=0.0).data["status"] == "COMPLETE"  # resume does nothing


def test_e2_store_that_cannot_be_held_cold() -> None:
    cfg = tiny_cfg()
    cfg["seeds"] = {**cfg["seeds"], "store_contents": T.TEST_SEED_CONTENTS}
    with T.scratch("e2_cold") as d:
        io = T.FakeIO(T.TEST_SEED_CONTENTS)
        io.model_cache = True
        io.cache = {("rest", 5)}
        ctx, clk, deps, pred, led, hours = e2_setup(d, io, cfg)
        built: list[int] = []
        st = e2.run_e2(ctx, cfg, deps, led, hours, lambda r: blocks.inprocess_pass_runner(ctx, deps, pred), d / "control.bin", now=clk, e1_built_at=0.0, builder=lambda p, *a, **k: (built.append(1), p.write_bytes(b""), {})[2])
        assert st.data["status"] == "ENGINEERING NOT EVALUABLE — STORE CANNOT BE HELD COLD" and built == [1] and bench.load_stage_records(ctx)[0] == []  # one rebuild, no pass read
        reg = e2.build_registry(ctx, cfg, {})
        res = e2.labels_of(reg)
        assert res["EQ-A"]["label"] == "ENGINEERING NOT EVALUABLE (STORE CANNOT BE HELD COLD)"


def test_e2_pollution_recovery_rebuilds_once_within_the_cap() -> None:
    cfg = tiny_cfg()
    cfg["seeds"] = {**cfg["seeds"], "store_contents": T.TEST_SEED_CONTENTS}
    with T.scratch("e2_poll") as d:
        io = T.FakeIO(T.TEST_SEED_CONTENTS)
        ctx, clk, deps, pred, led, hours = e2_setup(d, io, cfg)
        io.cached_offsets = {bench.derive_pass(ctx, 1, 1, 1)[0].offset}
        built: list[int] = []

        def builder(p: Path, *a: Any, **k: Any) -> dict[str, Any]:
            built.append(1)
            p.write_bytes(b"")
            io.cached_offsets.clear()
            return {}

        st = e2.run_e2(ctx, cfg, deps, led, hours, lambda r: blocks.inprocess_pass_runner(ctx, deps, pred), d / "control.bin", now=clk, e1_built_at=0.0, builder=builder)
        assert built == [1] and st.data["rebuilds"] == 1 and st.data["spare_used"] == "invalid_block" and st.data["status"] == "COMPLETE"
        assert [c["outcome"] for c in e2.load_cold_checks(ctx)] == ["COLD", "COLD"]


def test_e2_quiet_failure_before_the_cold_check_is_paused_and_counted() -> None:
    cfg = tiny_cfg()
    with T.scratch("e2_quiet") as d:
        io = T.FakeIO(T.TEST_SEED_CONTENTS)
        ctx, clk, deps, pred, led, hours = e2_setup(d, io, cfg)
        deps.gate = T.scripted_gate(lambda: T.quiet_record(False))
        with pytest.raises(core.Paused, match="NOT QUIET"):
            e2.run_e2(ctx, cfg, deps, led, hours, lambda r: None, d / "control.bin", now=clk, e1_built_at=0.0)
        assert blocks.StageState.load(ctx.stage_dir() / "state.json").data["quiet_sessions_failed"] == 1


def test_check_order_refusals() -> None:
    cfg = tiny_cfg()
    with T.scratch("e2_order") as d:
        io = T.FakeIO(1)
        ctx, clk, deps, pred, led, hours = e2_setup(d, io, cfg)
        ok = e2.check_order({**cfg, "budget": {**cfg["budget"], "free_space_min_bytes": 1}}, deps, d, d, "x", needed_bytes=1, ledger=led, file_exists=False)
        assert ok["ec3"]["health_ok"] and ok["hygiene"]["blocks_e1"] is False
        with pytest.raises(core.WriteBudgetExceeded):
            e2.check_order({**cfg, "budget": {**cfg["budget"], "free_space_min_bytes": 1}}, deps, d, d, "x", needed_bytes=10**10, ledger=led, file_exists=False)
        with pytest.raises(core.Paused, match="FREE SPACE"):
            device.require_free_space(d, 10**18)
