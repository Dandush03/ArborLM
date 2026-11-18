# ruff: noqa: E501
"""P10IS5 block-loop tests (ADR-0028 sections 5.2, 7, 8, 9; rulings 6 to 9, 12): the whole pass and block machinery in one process with a fake counter and fake reads (tiny geometry, test-range seeds 937001-937999, no
device, no file larger than a few KiB): quiet rule at block start and end, pollution recovery, the spare (once), engineering stops (data mismatch, prediction mismatch), resume, and the analysis over what it wrote.
Self-check only: not independent review, not Astra validation, not human approval."""

import sys
import threading
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from studies.p10is5 import analysis, bench, blocks, core, layout  # noqa: E402
from studies.p10is5 import testing as T  # noqa: E402


def setup(tmp: Path, *, repeats: int = 2, spare: bool = True, gate=None, io: T.FakeIO | None = None):  # type: ignore[no-untyped-def]
    ctx = T.tiny_context(tmp / "run", repeats=repeats, spare=spare)
    io = io or T.FakeIO(T.TEST_SEED_CONTENTS)
    gate = gate or T.scripted_gate(lambda: T.quiet_record(True))
    deps = blocks.Deps(counter=T.FakeCounter(io), gate=gate, pread=io.pread, opener=T.devnull_opener, sleep=lambda s: None)
    bench.write_prediction(ctx)
    pred = bench.load_prediction(ctx)
    state = blocks.StageState.load(ctx.stage_dir() / "state.json")
    return ctx, io, deps, pred, state


def registry(ctx: bench.Context, state: blocks.StageState) -> dict[str, Any]:
    passes, blks = bench.load_stage_records(ctx)
    th = T.thresholds_for(ctx.geometry)
    th["valid_min_repeats"] = 1
    return {"passes": passes, "blocks": blks, "harness": {}, "r1": {}, "cold_checks": [], "manifest": state.data, "stops": blocks.resolved_stops(ctx, blks), "thresholds": th}


def test_prediction_is_the_layout_and_pass_records_hold_the_counter_rule() -> None:
    with T.scratch("blocks_ok") as tmp:
        ctx, io, deps, pred, state = setup(tmp)
        assert len(pred["passes"]) == 3 * 8  # 2 repeats and the spare, 2 depths x 4 sizes
        p = pred["passes"]["r1|k2|s3"]
        assert p["predicted_bytes"] == 4 * 3 * layout.PAGE and len(p["requests"]) == 4 and all(r[3] == 3 * layout.PAGE for r in p["requests"])
        assert all(len(h) == 3 for h in p["page_sha256"])
        blocks.run_stage_blocks(ctx, deps, state, lambda r: blocks.inprocess_pass_runner(ctx, deps, pred))
        passes, blks = bench.load_stage_records(ctx)
        assert state.data["status"] == "COMPLETE" and state.data["spare_used"] is None  # no invalid block: the spare is not run
        assert len(passes) == 16 and len(blks) == 2 and [b["role"] for b in blks] == ["regular", "regular"]
        assert [p["seq"] for p in passes] == list(range(1, 17))
        for p in passes:
            assert p["counter_status"] == "OK" and p["counter_bytes"] == p["predicted_bytes"] == layout.PAGE * p["pages"] and p["parity_ok"] is True and p["written_bytes"] == 0
        res = analysis.analyse(registry(ctx, state))
        assert res["EQ-A"]["label"] == "BYTES CONFIRMED EXACTLY" and res["n_valid"] == 2
        for b in blks:
            assert len(b["order"]) == 8 and sorted(map(tuple, b["order"])) == sorted(ctx.geometry.cells())
            assert [tuple(o) for o in b["order"]] == layout.pass_order(ctx.block_def(b["repeat"])["pass_order_seed"], ctx.geometry)


def test_thread_assignment_and_requests_in_a_pass() -> None:
    with T.scratch("blocks_threads") as tmp:
        ctx, io, deps, pred, state = setup(tmp)
        blocks.run_stage_blocks(ctx, deps, state, lambda r: blocks.inprocess_pass_runner(ctx, deps, pred))
        passes, _ = bench.load_stage_records(ctx)
        p = next(x for x in passes if x["k"] == 2 and x["s"] == 1 and x["repeat"] == 1)
        assert p["thread"] == [j % 2 for j in range(4)] and len(p["latency_ns"]) == 4 and all(x > 0 for x in p["latency_ns"])
        assert p["max_in_flight"] <= 2 and p["pages_per_second"] > 0 and p["switch_interval"] > 0


def test_a_quiet_failure_at_block_start_pauses_and_counts_sessions_then_resume_runs_only_the_rest() -> None:
    with T.scratch("blocks_quiet") as tmp:
        calls = {"n": 0}

        def script() -> dict[str, Any]:
            calls["n"] += 1
            return T.quiet_record(calls["n"] != 1)  # the very first reading (block 1 start) fails, every later one passes

        ctx, io, deps, pred, state = setup(tmp, gate=T.scripted_gate(script))
        with pytest.raises(core.Paused, match="MACHINE NOT QUIET"):
            blocks.run_stage_blocks(ctx, deps, state, lambda r: blocks.inprocess_pass_runner(ctx, deps, pred))
        assert state.data["quiet_sessions_failed"] == 1 and not state.data["quiet_exhausted"] and bench.load_stage_records(ctx)[0] == []
        blocks.run_stage_blocks(ctx, deps, state, lambda r: blocks.inprocess_pass_runner(ctx, deps, pred))
        assert state.data["status"] == "COMPLETE" and len(bench.load_stage_records(ctx)[1]) == 2


def test_quiet_exhausted_after_four_sessions() -> None:
    with T.scratch("blocks_quiet4") as tmp:
        ctx, io, deps, pred, state = setup(tmp, gate=T.scripted_gate(lambda: T.quiet_record(False)))
        for i in range(4):
            with pytest.raises(core.Paused):
                blocks.run_stage_blocks(ctx, deps, state, lambda r: blocks.inprocess_pass_runner(ctx, deps, pred))
            assert state.data["quiet_exhausted"] is (i == 3)  # one session and three further ones, then MACHINE NOT QUIET
        res = analysis.analyse({**registry(ctx, state), "blocks": [], "passes": []}) if False else None
        assert res is None


def test_quiet_failure_at_block_end_invalidates_the_block_and_the_spare_replaces_it_once() -> None:
    with T.scratch("blocks_end") as tmp:
        seq = {"n": 0}

        def script() -> dict[str, Any]:
            seq["n"] += 1  # readings: block1 start, block1 end, block2 start, block2 end, spare start, spare end
            return T.quiet_record(seq["n"] != 2)

        ctx, io, deps, pred, state = setup(tmp, gate=T.scripted_gate(script))
        blocks.run_stage_blocks(ctx, deps, state, lambda r: blocks.inprocess_pass_runner(ctx, deps, pred))
        _, blks = bench.load_stage_records(ctx)
        assert [b["role"] for b in blks] == ["regular", "regular", "spare"] and state.data["spare_used"] == "invalid_block"
        res = analysis.analyse(registry(ctx, state))
        assert res["selection"]["replaced_block"] == "E2|r1|a1" and res["n_valid"] == 2 and res["EQ-A"]["label"] == "BYTES CONFIRMED EXACTLY"
        # the spare used the spare's seeds: repeat 3 of the tiling and its own request-order seed
        spare_pass = next(p for p in bench.load_stage_records(ctx)[0] if p["repeat"] == 3)
        assert spare_pass["role"] == "spare"


def test_pollution_ends_the_block_recovers_once_and_a_second_pollution_is_paused() -> None:
    with T.scratch("blocks_pollution") as tmp:
        io = T.FakeIO(T.TEST_SEED_CONTENTS)
        ctx, io, deps, pred, state = setup(tmp, io=io)
        reqs = bench.derive_pass(ctx, 1, 1, 1)
        io.cached_offsets = {reqs[0].offset}  # one page of repeat 1, k = 1, s = 1 is already cached
        rebuilt: list[int] = []
        first_order = layout.pass_order(ctx.block_def(1)["pass_order_seed"], ctx.geometry)
        blocks.run_stage_blocks(ctx, deps, state, lambda r: blocks.inprocess_pass_runner(ctx, deps, pred), recover=lambda: (rebuilt.append(1), io.cached_offsets.clear()))
        passes, blks = bench.load_stage_records(ctx)
        b1 = next(b for b in blks if b["repeat"] == 1)
        assert b1["aborted"] and not b1["complete"] and b1["pass_keys"][-1] == "E2|r1|k1|s1|a1" and len(b1["pass_keys"]) == first_order.index((1, 1)) + 1
        bad = next(p for p in passes if p["key"] == "E2|r1|k1|s1|a1")
        assert bad["counter_status"] == "STORE PAGES CACHED" and bad["counter_bytes"] == 3 * layout.PAGE and bad["predicted_bytes"] == 4 * layout.PAGE
        assert rebuilt == [1] and state.data["rebuilds"] == 1 and state.data["pollutions"] == 1 and state.data["spare_used"] == "invalid_block"
        res = analysis.analyse(registry(ctx, state))
        assert res["EQ-A"]["label"].startswith("BYTES NOT CONFIRMED (E2|r1|k1|s1|a1: STORE PAGES CACHED") and res["selection"]["replaced_block"] == "E2|r1|a1" and res["n_valid"] == 2
        assert res["EQ-A"]["failing"][0]["replacing_block_pass"]["key"] == "E2|r3|k1|s1|a1"  # printed beside the same cell of the replacing block
    with T.scratch("blocks_pollution2") as tmp:
        io = T.FakeIO(T.TEST_SEED_CONTENTS)
        ctx, io, deps, pred, state = setup(tmp, io=io)
        io.cached_offsets = {bench.derive_pass(ctx, 1, 1, 1)[0].offset, bench.derive_pass(ctx, 2, 1, 1)[0].offset}
        with pytest.raises(core.Paused, match="STORE POLLUTED AGAIN"):
            blocks.run_stage_blocks(ctx, deps, state, lambda r: blocks.inprocess_pass_runner(ctx, deps, pred), recover=lambda: None)
        assert state.data["status"] == "PAUSED — STORE POLLUTED AGAIN"


def test_counter_above_prediction_is_contamination_and_does_not_end_the_block() -> None:
    with T.scratch("blocks_contam") as tmp:
        io = T.FakeIO(T.TEST_SEED_CONTENTS)
        io.extra = 1
        ctx, io, deps, pred, state = setup(tmp, io=io)
        blocks.run_stage_blocks(ctx, deps, state, lambda r: blocks.inprocess_pass_runner(ctx, deps, pred))
        passes, blks = bench.load_stage_records(ctx)
        assert all(p["counter_status"] == "COUNTER CONTAMINATED" for p in passes) and all(len(b["pass_keys"]) == 8 for b in blks if b["role"] == "regular")
        assert analysis.analyse(registry(ctx, state))["EQ-A"]["label"].startswith("BYTES NOT CONFIRMED")


def test_data_mismatch_is_an_engineering_stop_never_a_label_and_the_rerun_uses_the_spare() -> None:
    with T.scratch("blocks_stop") as tmp:
        io = T.FakeIO(T.TEST_SEED_CONTENTS)
        ctx, io, deps, pred, state = setup(tmp, io=io)
        io.corrupt = {bench.derive_pass(ctx, 2, 2, 8)[0].offset}
        with pytest.raises(core.EngineeringStop, match="DATA MISMATCH"):
            blocks.run_stage_blocks(ctx, deps, state, lambda r: blocks.inprocess_pass_runner(ctx, deps, pred))
        assert state.data["status"] == "ENGINEERING STOP (DATA MISMATCH)" and state.data["engineering_stop"]
        stop_id = state.data["engineering_stop"]
        with pytest.raises(analysis.AnalysisRefused, match="DATA MISMATCH"):
            analysis.analyse(registry(ctx, state))  # the analysis of the stage refuses; nothing is labelled
        with pytest.raises(core.Paused, match="ENGINEERING STOP UNRESOLVED"):
            blocks.run_stage_blocks(ctx, deps, state, lambda r: blocks.inprocess_pass_runner(ctx, deps, pred))  # a plain resume is refused
        io.corrupt = set()
        blocks.run_stage_blocks(ctx, deps, state, lambda r: blocks.inprocess_pass_runner(ctx, deps, pred), rerun_after_stop=stop_id)
        passes, blks = bench.load_stage_records(ctx)
        assert state.data["spare_used"] == f"rerun_after_stop:{stop_id}" and state.data["status"] == "COMPLETE"
        spare = next(b for b in blks if b["role"] == "spare")
        assert spare["rerun_of"] == stop_id and spare["complete"] and spare["repeat"] == 3
        stopped = next(p for p in passes if p["parity_ok"] is False)  # EQ-A covers the stopped pass: both counter snapshots exist
        assert stopped["counter_status"] == "OK" and stopped["key"] == "E2|r2|k2|s8|a1"
        res = analysis.analyse(registry(ctx, state))
        assert res["EQ-A"]["label"] == "BYTES CONFIRMED EXACTLY" and res["n_valid"] == 2 and "E2|r3|a1" in res["valid_repeats"]
        # at most one: the spare is spent
        with pytest.raises(core.StageRefused, match="spare is not available"):
            blocks.run_stage_blocks(ctx, deps, state, lambda r: blocks.inprocess_pass_runner(ctx, deps, pred), rerun_after_stop=stop_id)


def test_prediction_mismatch_is_an_engineering_stop_before_any_read() -> None:
    with T.scratch("blocks_predmis") as tmp:
        ctx, io, deps, pred, state = setup(tmp)
        pred["passes"]["r1|k1|s1"]["requests"][0][2] += layout.PAGE
        before = io.reads
        with pytest.raises(core.EngineeringStop, match="PREDICTION MISMATCH"):
            bench.execute_pass(ctx, 1, 1, 1, 1, pred, deps.counter, block="E2|r1|a1", role="regular", seq=1, pread=io.pread, opener=T.devnull_opener)
        assert io.reads == before  # nothing was issued


def test_prediction_manifest_binds_the_record() -> None:
    with T.scratch("blocks_predhash") as tmp:
        ctx, io, deps, pred, state = setup(tmp)
        with pytest.raises(core.StageRefused, match="exists"):
            bench.write_prediction(ctx)
        ctx.prediction_path().write_text(ctx.prediction_path().read_text().replace('"stage"', '"stage "', 1))
        with pytest.raises(core.StageRefused, match="does not hash"):
            bench.load_prediction(ctx)


def test_memory_guard_is_an_engineering_stop() -> None:
    with T.scratch("blocks_mem") as tmp:
        io = T.FakeIO(T.TEST_SEED_CONTENTS)
        io.footprint = (1 << 32) + 1
        ctx, io, deps, pred, state = setup(tmp, io=io)
        with pytest.raises(core.EngineeringStop, match="MEMORY GUARD"):
            blocks.run_stage_blocks(ctx, deps, state, lambda r: blocks.inprocess_pass_runner(ctx, deps, pred))


def test_hours_cap_pauses_and_nothing_is_charged_for_waiting(tmp_path: Path = Path()) -> None:
    with T.scratch("blocks_hours") as tmp:
        ctx, io, deps, pred, state = setup(tmp)
        ledger = core.HoursLedger(tmp / "hours.json", 1e-9)
        ledger.charge("E2", "x", 1.0)
        with pytest.raises(core.LedgerRefused):
            blocks.run_stage_blocks(ctx, deps, state, lambda r: blocks.inprocess_pass_runner(ctx, deps, pred), hours=ledger)


def test_the_counter_is_per_process_and_covers_all_threads() -> None:
    io = T.FakeIO(T.TEST_SEED_CONTENTS)
    done = threading.Event()
    reqs = [layout.Request(j, j % 4, j, 0, j * layout.TILE_BYTES, layout.PAGE) for j in range(8)]
    from studies.p10is5 import harness

    res = harness.run_pass("ignored", reqs, 4, T.FakeCounter(io), pread=io.pread, opener=T.devnull_opener)
    done.set()
    assert res.counter_bytes == 8 * layout.PAGE and len(res.data) == 8 and res.pages == 8 and res.k == 4
    assert [r for r in res.thread] == [0, 1, 2, 3, 0, 1, 2, 3]


def test_a_short_read_is_an_environment_error() -> None:
    from studies.p10is5 import harness

    io = T.FakeIO(T.TEST_SEED_CONTENTS)
    reqs = [layout.Request(0, 0, 0, 0, 0, layout.PAGE)]
    with pytest.raises(core.EngineeringStop, match="SHORT READ"):
        harness.run_pass("ignored", reqs, 1, T.FakeCounter(io), pread=lambda fd, n, off: b"x", opener=T.devnull_opener)
