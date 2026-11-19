# ruff: noqa: E501
"""P10IS5 tests of the audit's findings (B1 to B3, R1 to R5, the advisories). Each is written to FAIL on the earlier behaviour and stubs nothing it tests. B1 runs in a fresh interpreter inside a fully frozen
scratch repository. Fake machine and reads; a few KiB of records under experiments/_scratch, deleted at the end. Self-check only: not independent review, not Astra validation, not human approval."""

import copy
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from studies.p10is5 import (  # noqa: E402
    analysis,
    bench,
    blocks,
    core,
    device,
    e2,
    freeze,
    gates,
    rehearsal,
    report,
    stages,
    system,
)
from studies.p10is5 import plan as planmod  # noqa: E402
from studies.p10is5 import testing as T  # noqa: E402
from studies.p10is5.synthetic import QUIET_BAD, QUIET_OK, make_registry  # noqa: E402

ROOT = core.repo_root()
CFG = core.load_config()


def git(repo: Path, *a: str) -> str:
    return subprocess.run(["git", "-C", str(repo), "-c", "commit.gpgsign=false", "-c", "user.name=t", "-c", "user.email=t@t", *a], capture_output=True, text=True, check=True).stdout.strip()


# --- B1: a fully frozen repository gets PAST the preconditions ------------------------------------------------------------------------------------
def frozen_repo(d: Path) -> tuple[Path, str, Path]:
    repo = d / "repo"
    shutil.copytree(ROOT / "studies" / "p10is5", repo / "studies" / "p10is5", ignore=shutil.ignore_patterns("__pycache__", "freeze"))
    shutil.copytree(ROOT / "src" / "arborlm", repo / "src" / "arborlm", ignore=shutil.ignore_patterns("__pycache__"))
    for f in ("uv.lock", "pyproject.toml", core.SPEC):
        (repo / f).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / f, repo / f)
    cfg_text = (ROOT / core.CONFIG).read_text()
    cfg_text = cfg_text.replace("provisional = true", "provisional = false").replace("m_t = 0.0", "m_t = 0.1").replace("load_p95 = 0.0", "load_p95 = 2.0")
    (repo / core.CONFIG).parent.mkdir(parents=True, exist_ok=True)
    (repo / core.CONFIG).write_text(cfg_text)
    run_dir = d / "run"
    run_dir.mkdir()
    recs = {}
    for n in ("r1", "m"):
        (run_dir / n).write_text(n)
        recs[n] = run_dir / n
    cfg = core.load_config(repo / core.CONFIG)
    plan = planmod.build_plan(cfg, repo, d / "data.noindex", run_dir, recs)
    core.write_record(repo / core.PLAN, plan)
    (repo / planmod.FREEZE_RECORD).write_text(json.dumps({"kind": "freeze_record", "study": core.STUDY, "schema": core.SCHEMA, "plan_file_sha256": __import__("arborlm.io", fromlist=["x"]).file_sha256(repo / core.PLAN)}))
    git(repo, "init", "-q")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "freeze")
    freeze_commit = git(repo, "rev-parse", "HEAD")
    dec = repo / "results" / "p10is5-freeze-x" / "DECISION_2.md"
    dec.parent.mkdir(parents=True)
    dec.write_text(f"{freeze_commit}\nDECISION: RUN\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "decision 2")
    return repo, freeze_commit, run_dir


PROBE = """
import sys, torch
sys.path.insert(0, {root!r})
torch.set_num_threads(4)  # a fresh process is NOT the platform of record until the entry point configures it
from studies.p10is5 import stages
import argparse
a = argparse.Namespace(repo={repo!r}, run_dir={run!r}, freeze_commit={commit!r})
repo, run, cfg, plan = stages.load_registered(a, {stage!r})
print("PAST", plan.data["mode"], torch.get_num_threads(), torch.are_deterministic_algorithms_enabled())
"""


def test_b1_a_registered_stage_gets_past_its_preconditions_in_a_frozen_repository() -> None:
    with T.scratch("fix_b1") as d:
        repo, commit, run_dir = frozen_repo(d)
        for stage in ("e1", "p", "e2", "analysis", "report", "delete"):  # analysis, report and delete configured nothing before
            p = subprocess.run([sys.executable, "-c", PROBE.format(root=str(ROOT), repo=str(repo), run=str(run_dir), commit=commit, stage=stage)], capture_output=True, text=True, timeout=300)
            assert p.returncode == 0 and "PAST registered 1 True" in p.stdout, (stage, p.stdout, p.stderr[-800:])
        # the same repository refuses on identity once a frozen file differs (and exits 75 through the real entry point)
        (repo / "studies/p10is5/core.py").write_text((repo / "studies/p10is5/core.py").read_text() + "\n# tampered\n")
        p = subprocess.run([sys.executable, "-c", PROBE.format(root=str(ROOT), repo=str(repo), run=str(run_dir), commit=commit, stage="e2")], capture_output=True, text=True, timeout=300)
        assert p.returncode != 0 and "not clean" in p.stderr
        cmd = [sys.executable, "-m", "studies.p10is5.stages", "registered", "analysis", "--run-dir", str(run_dir), "--freeze-commit", commit, "--repo", str(repo)]
        q = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT, timeout=300)
        assert q.returncode == 75 and "IDENTITY" in q.stderr and not (run_dir / "analysis").exists()


# --- B2: mdfind's locale line on stderr is not a listing ---------------------------------------------------------------------------------------------
def test_b2_hygiene_reads_stdout_only_and_unknown_indexing_state_is_not_indexed() -> None:
    def run(argv: Any) -> tuple[int, str, str]:
        a = list(argv)
        if a[0] == "mdfind":
            return 0, "", "2026-11-18 10:00:00.000 mdfind[1:2] [UserQueryParser] Loading Spotlight locale\n"
        if a[0] == "mdutil":
            return 0, "/x.noindex:\n\tError: unknown indexing state.\n", ""
        return 0, "", ""

    h = system.hygiene_record(run, Path("/x.noindex"), file_exists=False)
    assert h["spotlight_indexes_directory"] is False and h["blocks_e1"] is False
    assert h["spotlight_listing"]["output"] == "" and "locale" in h["spotlight_listing"]["stderr"] and "unknown indexing state" in h["spotlight_status"]["output"]  # raw text recorded
    listed = system.hygiene_record(lambda a: (0, "/x.noindex/f\n", "") if a[0] == "mdfind" else (0, "", ""), Path("/x.noindex"), file_exists=False)
    assert listed["blocks_e1"] is True  # a real listing on stdout still counts


def test_b2_r0_runs_its_probes_when_spotlight_indexes_the_directory(monkeypatch: pytest.MonkeyPatch) -> None:
    from studies.p10is5 import r0

    for n in ("PROBE_A_BYTES", "PROBE_B_BYTES", "PROBE_C_BYTES"):
        monkeypatch.setattr(r0, n, 1 << 20)  # 1 MiB each: 3 MiB really written
    cfg = copy.deepcopy(dict(CFG))
    cfg["budget"] = {**cfg["budget"], "probe_bytes": 3 << 20, "free_space_min_bytes": 1}
    with T.scratch("fix_b2") as d:
        clk = T.Clock()
        fs = T.FakeSystem(clk)
        io = T.FakeIO(1)
        deps = blocks.Deps(counter=T.FakeCounter(io), gate=T.scripted_gate(lambda: T.quiet_record(True)), run=lambda a: (0, "Indexing enabled.", "") if a[0] == "mdutil" else fs.run(a), run_b=fs.run_b, sleep=clk.sleep, clock=clk, pread=io.pread, opener=io.opener)
        rec = r0.run_r0(cfg, d / "data.noindex", d / "run", deps, device.WriteLedger(d / "run" / "w.json", 10**9), [])
        assert rec["hygiene"]["blocks_e1"] is True and set(rec["probes"]) == {"probe_1", "probe_2", "probe_3"}  # recorded, not paused: the pause is before E1


# --- B3: a block that stopped halfway resumes at the first pass not completed -------------------------------------------------------------------
def test_b3_resume_after_a_refusal_continues_at_the_first_pass_not_completed() -> None:
    with T.scratch("fix_b3") as d:
        ctx = T.tiny_context(d / "run", repeats=2, spare=True)
        io = T.FakeIO(T.TEST_SEED_CONTENTS)
        deps = blocks.Deps(counter=T.FakeCounter(io), gate=T.scripted_gate(lambda: T.quiet_record(True)), pread=io.pread, opener=T.devnull_opener, sleep=lambda s: None)
        bench.write_prediction(ctx)
        pred = bench.load_prediction(ctx)
        state = blocks.StageState.load(ctx.stage_dir() / "state.json")
        good = blocks.inprocess_pass_runner(ctx, deps, pred)
        n = {"i": 0}

        def flaky(*a: Any) -> dict[str, Any]:
            n["i"] += 1
            if n["i"] == 4:
                raise core.Paused(core.PAUSED_IDENTITY, "a worker refused (exit 75) before reading anything")
            return good(*a)

        with pytest.raises(core.Paused):
            blocks.run_stage_blocks(ctx, deps, state, lambda r: flaky)
        assert len(bench.load_stage_records(ctx)[0]) == 3
        blocks.run_stage_blocks(ctx, deps, state, lambda r: good)  # earlier code: FileExistsError -> ENGINEERING STOP (WORKER FAILED), spending the spare
        passes, blks = bench.load_stage_records(ctx)
        keys = [p["key"] for p in passes]
        assert len(keys) == len(set(keys)) == 16 and all(k.endswith("|a1") for k in keys) and state.data["status"] == "COMPLETE" and state.data["spare_used"] is None and state.data["engineering_stop"] is None
        assert next(b for b in blks if b["repeat"] == 1)["resumed"] is True and not any(p.get("incomplete") for p in passes)


def all_pages(requests: list[tuple[int, int]]) -> list[int]:
    return [p for off, n in requests for p in range(off // 16384, (off + n - 1) // 16384 + 1)]


def interrupted_run(d: Path, interrupt_at: list[tuple[int, int]]) -> tuple[Any, blocks.StageState, list[tuple[int, int]]]:
    """Run the tiny stage; the n-th pass ordered in ``interrupt_at`` = (repeat, pass index in that block's order) is KILLED after its reads were issued (no record written, the process dies); then resume until complete.
    Returns the context, the state and every (offset, length) ever requested."""
    from studies.p10is5 import harness

    ctx = T.tiny_context(d / "run", repeats=2, spare=True)
    io = T.FakeIO(T.TEST_SEED_CONTENTS)
    issued: list[tuple[int, int]] = []
    inner = io.pread

    def rec_pread(fd: int, n: int, off: int) -> bytes:
        issued.append((off, n))
        return inner(fd, n, off)

    deps = blocks.Deps(counter=T.FakeCounter(io), gate=T.scripted_gate(lambda: T.quiet_record(True)), pread=rec_pread, opener=T.devnull_opener, sleep=lambda s: None)
    bench.write_prediction(ctx)
    pred = bench.load_prediction(ctx)
    state = blocks.StageState.load(ctx.stage_dir() / "state.json")
    good = blocks.inprocess_pass_runner(ctx, deps, pred)
    pending = list(interrupt_at)
    count: dict[int, int] = {}

    def killer(*a: Any) -> dict[str, Any]:
        repeat = a[0]
        idx = count.get(repeat, 0)
        count[repeat] = idx + 1
        if (repeat, idx) in pending and (len(a) < 8 or a[7] is None):
            pending.remove((repeat, idx))
            reqs = bench.derive_pass(ctx, repeat, a[1], a[2])
            harness.run_pass(ctx.file_path, reqs, a[1], deps.counter, pread=rec_pread, opener=T.devnull_opener)  # the reads were issued ...
            raise KeyboardInterrupt  # ... and the process died before it wrote its record
        return good(*a)

    for _ in range(len(interrupt_at) + 1):
        try:
            blocks.run_stage_blocks(ctx, deps, state, lambda r: killer)
            break
        except KeyboardInterrupt:
            count.clear()  # a resumed block starts counting its passes again
    return ctx, state, issued


@pytest.mark.parametrize("which", range(8))
def test_n3_after_any_single_interruption_no_page_is_requested_twice(which: int) -> None:
    with T.scratch(f"fix_n3_{which}") as d:
        ctx, state, issued = interrupted_run(d, [(1, which)])
        pages = all_pages(issued)
        assert len(pages) == len(set(pages)), "a page was requested twice"  # enumeration over EVERY request ever issued, the interrupted pass's included
        passes, blks = bench.load_stage_records(ctx)
        inc = [p for p in passes if p.get("incomplete")]
        assert state.data["status"] == "COMPLETE" and len(inc) == 1 and state.data["spare_used"] == "pass_level"
        cell = (inc[0]["k"], inc[0]["s"])
        b1 = next(b for b in blks if b["repeat"] == 1)
        assert b1["spare_cells_used"] == [list(cell)] and b1["complete"] and b1["invalid_cells"] == []
        spare_pass = next(p for p in passes if p["repeat"] == 1 and (p["k"], p["s"]) == cell and not p.get("incomplete"))
        assert spare_pass["attempt"] == 2 and spare_pass["source_repeat"] == 3 and spare_pass["key"] in b1["pass_keys"]  # the spare's tiles and seeds, recorded
        reg = {"passes": passes, "blocks": blks, "harness": {}, "r1": {}, "cold_checks": [], "manifest": state.data, "stops": [], "thresholds": {**T.thresholds_for(ctx.geometry), "valid_min_repeats": 1}}
        res = analysis.analyse(reg)
        assert res["EQ-A"]["label"] == "BYTES CONFIRMED EXACTLY" and res["EQ-A"]["incomplete"] == [inc[0]["key"]] and res["EQ-A"]["passes"] == len(passes)  # the incomplete pass is counted as attempted
        assert res["selection"]["spare_block"] is None  # the spare block is not run too: it serves one use


def test_n3_when_the_spare_cell_is_already_used_that_cell_of_the_repeat_is_invalid() -> None:
    with T.scratch("fix_n3_two") as d:
        probe = T.tiny_context(d / "p", repeats=2, spare=True)
        order1 = layout_order(probe, 1)
        order2 = layout_order(probe, 2)
        same = next(i for i, c in enumerate(order2) if c == order1[0])
        ctx, state, issued = interrupted_run(d, [(1, 0), (2, same)])  # the same (k, s) cell is interrupted in repeats 1 and 2
        pages = all_pages(issued)
        assert len(pages) == len(set(pages))
        passes, blks = bench.load_stage_records(ctx)
        b2 = next(b for b in blks if b["repeat"] == 2)
        assert b2["invalid_cells"] == [list(order1[0])] and b2["complete"] is False  # the spare's tiles for that cell were used: the validity rule decides
        reg = {"passes": passes, "blocks": blks, "harness": {}, "r1": {}, "cold_checks": [], "manifest": state.data, "stops": [], "thresholds": {**T.thresholds_for(ctx.geometry), "valid_min_repeats": 1}}
        res = analysis.analyse(reg)
        assert res["n_valid"] == 1 and "E2|r2|a1" not in res["valid_repeats"] and len([p for p in passes if p.get("incomplete")]) == 2


def layout_order(ctx: Any, repeat: int) -> list[tuple[int, int]]:
    from studies.p10is5 import layout

    return layout.pass_order(int(ctx.block_def(repeat)["pass_order_seed"]), ctx.geometry)


# --- N1, N2, N4 ----------------------------------------------------------------------------------------------------------------------------------
def test_n1_a_paused_m_writes_no_m_json_and_never_consumes_the_repeat(monkeypatch: pytest.MonkeyPatch) -> None:
    with T.scratch("fix_n1") as d:
        run = d / "run"
        (run / "r1").mkdir(parents=True)
        r1p = run / "r1" / "r1.json"
        core.write_record(r1p, {**core.envelope("r1"), "passed": True, "idle_figures": {k: 1.0 for k in freeze.FIGURE_KEYS}})
        monkeypatch.setattr(stages, "make_deps", lambda cfg, where: blocks.Deps(counter=T.FakeCounter(T.FakeIO(1)), gate=T.scripted_gate(lambda: T.quiet_record(True))))

        def paused(*a: Any, **k: Any) -> None:
            raise core.Paused("PAUSED — MACHINE NOT QUIET", "a quiet session failed")

        monkeypatch.setattr(rehearsal, "run_rehearsal_stage", paused)
        a = type("A", (), {"run_dir": str(run), "data_dir": str(d / "x.noindex"), "r1_record": str(r1p), "repeat_cause": None})()
        for _ in range(2):  # a resume after a pause is a plain resume: it asks for no --repeat-cause
            with pytest.raises(core.Paused):
                stages.cmd_m(a)  # type: ignore[arg-type]
            assert not (run / "M" / "m.json").exists() and (run / "M" / "pause.json").is_file() and not (run / "M_attempt1").exists()
        # a COMPLETED M with too few valid medians is what consumes the repeat
        monkeypatch.setattr(rehearsal, "run_rehearsal_stage", lambda *x, **k: None)
        monkeypatch.setattr(rehearsal, "m_summary", lambda ctx, cfg, h: {"cv": {"cv_r": None}, "margin": None, "passes": 0})
        assert stages.cmd_m(a) == 1  # type: ignore[arg-type]
        assert core.read_record(run / "M" / "m.json")["outcome"].startswith("m_t NOT DETERMINED")
        with pytest.raises(core.StageRefused, match="--repeat-cause"):
            stages.cmd_m(a)  # type: ignore[arg-type]


def test_n2_m_and_k_blocks_are_charged_once() -> None:
    cfg = copy.deepcopy(dict(CFG))
    cfg["device"] = {**cfg["device"], "control_tiles": 24}
    with T.scratch("fix_n2") as d:
        ctx = T.tiny_context(d / "run", repeats=2, spare=False, stage="M")
        io = T.FakeIO(T.TEST_SEED_CONTENTS)
        io.model_cache = True
        clk = T.Clock()
        fs = T.FakeSystem(clk)
        deps = blocks.Deps(counter=T.FakeCounter(io), gate=T.scripted_gate(lambda: T.quiet_record(True)), run=fs.run, run_b=fs.run_b, pread=io.pread, opener=io.opener, sleep=clk.sleep, clock=clk)
        hours = core.hours_ledger_for(d / "run" / "h.json", CFG)
        good = blocks.inprocess_pass_runner(ctx, deps, {})  # replaced below once the prediction exists

        def slow(*a: Any) -> dict[str, Any]:
            clk.t += 10.0
            return runner(*a)

        bench.write_prediction(ctx)
        runner = blocks.inprocess_pass_runner(ctx, deps, bench.load_prediction(ctx))
        del good
        rehearsal.run_rehearsal_stage(ctx, cfg, deps, hours, lambda r: slow, d / "control.bin", {})
        assert clk.t == 160.0 and hours.charged("rehearsal") == pytest.approx(160.0)  # 16 passes x 10 s of wall time, charged once (320 s before)


def test_n4_an_unhandled_error_is_written_where_the_analysis_reads_it_and_makes_it_refuse(capsys: pytest.CaptureFixture[str]) -> None:
    with T.scratch("fix_n4") as d:
        ctx = T.tiny_context(d / "run", repeats=2, spare=True)
        args = type("A", (), {"command": "registered", "stage": "e2", "run_dir": str(d / "run")})()
        stages.record_unhandled(d / "run", args, ZeroDivisionError("division"))  # type: ignore[arg-type]
        assert len(list((d / "run" / "E2" / "stops").glob("unhandled_*.json"))) == 1  # <run>/E2/stops: the directory e2.build_registry reads
        reg = e2.build_registry(ctx, CFG, {})
        assert [s["cause"] for s in reg["stops"]] == ["ZeroDivisionError"] and reg["stops"][0]["resolved"] is False
        with pytest.raises(analysis.AnalysisRefused, match="ZeroDivisionError"):
            analysis.analyse(reg)
        assert blocks.resolved_stops(ctx, [{"role": "spare", "complete": True, "rerun_of": reg["stops"][0]["id"]}])[0]["resolved"] is False  # a rerun never resolves it


# --- R1 (resolution): every stop inside the rerun block is resolved --------------------------------------------------------------------------------
def test_r1_pass_level_and_block_level_stops_are_both_resolved_by_the_one_rerun() -> None:
    with T.scratch("fix_r1") as d:
        ctx = T.tiny_context(d / "run", repeats=2, spare=True)
        io = T.FakeIO(T.TEST_SEED_CONTENTS)
        deps = blocks.Deps(counter=T.FakeCounter(io), gate=T.scripted_gate(lambda: T.quiet_record(True)), pread=io.pread, opener=T.devnull_opener, sleep=lambda s: None)
        bench.write_prediction(ctx)
        pred = bench.load_prediction(ctx)
        state = blocks.StageState.load(ctx.stage_dir() / "state.json")
        io.corrupt = {bench.derive_pass(ctx, 2, 2, 8)[0].offset}
        # the worker process records a per-pass stop before the stage records its per-block stop
        runner = blocks.inprocess_pass_runner(ctx, deps, pred)

        def worker_like(*a: Any) -> dict[str, Any]:
            try:
                return runner(*a)
            except core.EngineeringStop as e:
                blocks.record_stop(ctx, core.pass_key(ctx.stage, a[0], a[1], a[2], a[6]), e.cause, e.detail)
                raise

        with pytest.raises(core.EngineeringStop):
            blocks.run_stage_blocks(ctx, deps, state, lambda r: worker_like)
        assert len(blocks.load_stops(ctx)) == 2
        io.corrupt = set()
        blocks.run_stage_blocks(ctx, deps, state, lambda r: runner, rerun_after_stop=state.data["engineering_stop"])
        _, blks = bench.load_stage_records(ctx)
        stops = blocks.resolved_stops(ctx, blks)
        assert len(stops) == 2 and all(s["resolved"] for s in stops)  # the per-pass record used to stay unresolved for good
        passes, _ = bench.load_stage_records(ctx)
        res = analysis.analyse({"passes": passes, "blocks": blks, "harness": {}, "r1": {}, "cold_checks": [], "manifest": state.data, "stops": stops, "thresholds": {**T.thresholds_for(ctx.geometry), "valid_min_repeats": 1}})
        assert res["EQ-A"]["label"] == "BYTES CONFIRMED EXACTLY"


def test_r1_advisory_the_rerun_replaces_the_block_it_names() -> None:
    reg = make_registry(spare=True, quiet={2: (QUIET_OK, QUIET_BAD), 4: (QUIET_BAD, QUIET_OK)})
    reg["blocks"][-1]["rerun_of"] = "E2|E2|r4|a1|DATA MISMATCH"
    sel = analysis.analyse(reg)["selection"]
    assert sel["replaced_block"] == "E2|r4|a1"  # not the first invalid one (r2)
    reg["blocks"][-1]["rerun_of"] = None
    assert analysis.analyse(reg)["selection"]["replaced_block"] == "E2|r2|a1"


# --- R2: MACHINE NOT QUIET and WRITE BUDGET EXHAUSTED are reachable and final --------------------------------------------------------------------
def test_r2_machine_not_quiet_is_final_after_four_sessions_and_the_analysis_accepts_it() -> None:
    with T.scratch("fix_r2") as d:
        ctx = T.tiny_context(d / "run", repeats=2, spare=True)
        io = T.FakeIO(T.TEST_SEED_CONTENTS)
        deps = blocks.Deps(counter=T.FakeCounter(io), gate=T.scripted_gate(lambda: T.quiet_record(False)), pread=io.pread, opener=T.devnull_opener, sleep=lambda s: None)
        bench.write_prediction(ctx)
        pred = bench.load_prediction(ctx)
        state = blocks.StageState.load(ctx.stage_dir() / "state.json")
        for _ in range(4):
            with pytest.raises(core.Paused):
                blocks.run_stage_blocks(ctx, deps, state, lambda r: blocks.inprocess_pass_runner(ctx, deps, pred))
        assert state.data["status"] == "ENGINEERING NOT EVALUABLE — MACHINE NOT QUIET" and state.data["status"] in core.FINAL_STATUSES
        with pytest.raises(core.StageRefused, match="final"):
            blocks.run_stage_blocks(ctx, deps, state, lambda r: blocks.inprocess_pass_runner(ctx, deps, pred))  # a fifth session does not run
        reg = e2.build_registry(ctx, CFG, {})
        res = e2.labels_of(reg)  # no pass exists and the stage is final: it is labelled, not refused
        assert res["EQ-B"]["label"] == res["EQ-D"]["label"] == "ENGINEERING NOT EVALUABLE (MACHINE NOT QUIET)" and res["EQ-A"]["label"] == "NOT READ (NO PASS WAS RUN)"


def test_r2_write_budget_exhausted_is_reached_when_the_lead_declines_more() -> None:
    with T.scratch("fix_r2b") as d:
        state = blocks.StageState.load(d / "state.json")
        with pytest.raises(core.StageRefused, match="PAUSED on the write budget"):
            blocks.decline_write_budget(state)
        state.data["status"] = "PAUSED — WRITE BUDGET"
        blocks.decline_write_budget(state)
        assert state.data["write_budget_declined"] and state.data["status"] == "ENGINEERING NOT EVALUABLE — WRITE BUDGET EXHAUSTED"
        reg = make_registry(manifest={"write_budget_declined": True})
        res = analysis.analyse(reg)
        assert all(res[x]["label"] == "ENGINEERING NOT EVALUABLE (WRITE BUDGET EXHAUSTED)" for x in ("EQ-A", "EQ-B", "EQ-D"))
        with pytest.raises(core.StageRefused):
            blocks.refuse_if_final(state)


# --- R3: one run directory, one ledger ----------------------------------------------------------------------------------------------------------
def test_r3_candidate_plan_refuses_records_and_ledgers_from_another_run_directory() -> None:
    with T.scratch("fix_r3") as d:
        run = d / "run"
        (run / "r1").mkdir(parents=True)
        (run / "M").mkdir()
        r1p, mp = run / "r1" / "r1.json", run / "M" / "m.json"
        r1p.write_text("{}")
        mp.write_text("{}")
        assert any("no write ledger" in p for p in freeze.one_run_dir_problems(run, r1p, mp))
        led = device.WriteLedger(run / "write_ledger.json", 10**9)
        led.begin("probe_a.bin", 10)
        led.end()
        assert any("R1 build" in p for p in freeze.one_run_dir_problems(run, r1p, mp))
        led.begin("rehearsal.bin#chunk0", 10)
        led.end()
        assert freeze.one_run_dir_problems(run, r1p, mp) == []
        other = d / "other" / "r1"
        other.mkdir(parents=True)
        (other / "r1.json").write_text("{}")
        assert any("is not" in p for p in freeze.one_run_dir_problems(run, other / "r1.json", mp))
        led2 = d / "run2"
        assert any("no write ledger" in p for p in freeze.one_run_dir_problems(led2, r1p, mp))  # a fresh directory would restart the cap at 0
        with pytest.raises(core.StageRefused, match="not under this run directory"):
            stages.cmd_m(type("A", (), {"run_dir": str(run), "data_dir": str(d / "x.noindex"), "r1_record": str(other / "r1.json"), "repeat_cause": None})())  # type: ignore[arg-type]


# --- R4: a rebuild checks the whole file and the build count BEFORE deleting ---------------------------------------------------------------------------
def test_r4_rebuild_guard_runs_before_the_file_is_deleted() -> None:
    cfg = copy.deepcopy(dict(CFG))
    cfg["device"] = {**cfg["device"], "store_tiles": 24, "control_tiles": 24}
    cfg["budget"] = {**cfg["budget"], "store_file_bytes": 24 << 20}
    cfg["seeds"] = {**cfg["seeds"], "store_contents": T.TEST_SEED_CONTENTS}
    with T.scratch("fix_r4") as d:
        io = T.FakeIO(T.TEST_SEED_CONTENTS)
        ctx = T.tiny_context(d / "run", file_path=d / "store.bin", repeats=2, spare=True)
        (d / "store.bin").write_bytes(b"")
        clk = T.Clock()
        fs = T.FakeSystem(clk)
        deps = blocks.Deps(counter=T.FakeCounter(io), gate=T.scripted_gate(lambda: T.quiet_record(True)), run=fs.run, run_b=fs.run_b, sleep=clk.sleep, clock=clk, pread=io.pread, opener=io.opener)
        bench.write_prediction(ctx)
        pred = bench.load_prediction(ctx)
        io.cached_offsets = {bench.derive_pass(ctx, 1, 1, 1)[0].offset}
        led = device.WriteLedger(d / "run" / "w.json", 10 << 20)  # less than the 24 MiB file
        built: list[int] = []
        with pytest.raises(core.WriteBudgetExceeded, match="not deleted"):
            e2.run_e2(ctx, cfg, deps, led, core.HoursLedger(d / "run" / "h.json", 10**6), lambda r: blocks.inprocess_pass_runner(ctx, deps, pred), d / "control.bin", now=clk, e1_built_at=0.0, builder=lambda *a, **k: built.append(1) or {})
        assert (d / "store.bin").exists() and built == []  # the earlier code deleted the file first and stopped partway
        assert blocks.StageState.load(ctx.stage_dir() / "state.json").data["status"] == "PAUSED — WRITE BUDGET"
    with T.scratch("fix_r4b") as d:
        led = device.WriteLedger(d / "w.json", 10**12)
        for _ in range(2):
            led.begin("store.bin#chunk0", 1)
            led.end()
        assert device.builds_of(led, "store.bin") == 2
        with pytest.raises(core.Paused, match="BUILD LIMIT"):
            device.guard_rebuild(led, "store.bin", 1, int(CFG["budget"]["max_builds_per_file"]))
        with pytest.raises(core.Paused, match="BUILD LIMIT"):
            device.build_file(d / "store.bin", 1, T.TEST_SEED_CONTENTS, led, T.FakeCounter(T.RealFileIO()), chunk_bytes=1 << 20, max_builds=2)  # no third build, nothing written
        assert not (d / "store.bin").exists()


# --- R5: hours caps ------------------------------------------------------------------------------------------------------------------------------
def test_r5_hours_caps_are_per_group_cumulative_and_charge_every_stage() -> None:
    with T.scratch("fix_r5") as d:
        led = core.HoursLedger(d / "h.json", 1000.0, {"rehearsal": 100.0, "e1": 50.0, "e2": 400.0})
        clk = T.Clock()
        slept = {"s": 0.0}
        with led.timed("R1", "r1", clk, lambda: slept["s"]):
            clk.sleep(130.0)
            slept["s"] += 100.0  # a wait is not charged
        assert led.charged("rehearsal") == 30.0
        with pytest.raises(core.LedgerRefused):
            with led.timed("M", "m", clk, lambda: slept["s"]):
                clk.sleep(80.0)  # charged even though it raised below
                raise core.LedgerRefused("x")
        assert led.charged("rehearsal") == 110.0  # R1 and M share the rehearsal cap across resumes
        with pytest.raises(core.LedgerRefused, match="group rehearsal"):
            led.require_room("K")
        led.require_room("E2")  # another group is untouched
        led.charge("E1", "e1", 60.0)
        with pytest.raises(core.LedgerRefused, match="group e1"):
            led.require_room("P")  # P is in the e1 group
        led.charge("E2", "x", 350.0)
        led.charge("R0", "r0", 500.0)  # 110 + 60 + 350 + 500 > 1000
        with pytest.raises(core.LedgerRefused, match="total cap"):
            led.require_room("E2")  # the total counts every stage
        assert core.hours_ledger_for(d / "h2.json", CFG).group_caps.keys() == {"rehearsal", "e1", "e2"}


def test_r5_the_cap_is_checked_before_every_pass_not_only_at_a_block_start() -> None:
    with T.scratch("fix_r5b") as d:
        ctx = T.tiny_context(d / "run", repeats=2, spare=True)
        io = T.FakeIO(T.TEST_SEED_CONTENTS)
        clk = T.Clock()
        deps = blocks.Deps(counter=T.FakeCounter(io), gate=T.scripted_gate(lambda: T.quiet_record(True)), pread=io.pread, opener=T.devnull_opener, sleep=clk.sleep, clock=clk)
        bench.write_prediction(ctx)
        pred = bench.load_prediction(ctx)
        state = blocks.StageState.load(ctx.stage_dir() / "state.json")
        base = blocks.inprocess_pass_runner(ctx, deps, pred)

        def slow(*a: Any) -> dict[str, Any]:
            clk.t += 100.0
            return base(*a)

        hours = core.HoursLedger(d / "run" / "h.json", 10**6, {"e2": 250.0})
        with pytest.raises(core.LedgerRefused):
            blocks.run_stage_blocks(ctx, deps, state, lambda r: slow, hours=hours)
        assert len(bench.load_stage_records(ctx)[0]) == 3 and state.data["status"] == "PAUSED — CHARGED HOURS"  # stopped inside the first block
        assert hours.charged("e2") == pytest.approx(300.0)  # what ran was charged


# --- advisories ------------------------------------------------------------------------------------------------------------------------------
def test_adv_ordinary_errors_are_recorded_stops_not_tracebacks(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    with T.scratch("fix_adv1") as d:
        def boom(args: Any) -> int:
            raise ZeroDivisionError("division")

        monkeypatch.setattr(stages, "cmd_r1", boom)
        rc = stages.main(["r1", "--run-dir", str(d / "run"), "--data-dir", str(d / "x.noindex")])
        assert rc == core.ENGINEERING_STOP_EXIT == 70 and "ENGINEERING STOP (ZeroDivisionError)" in capsys.readouterr().err
        rec = json.loads(next((d / "run" / "R1" / "stops").glob("unhandled_*.json")).read_text())
        assert rec["cause"] == "ZeroDivisionError" and rec["resolved"] is False


def test_adv_cleanup_command_refuses_without_confirmation_and_after_a_freeze() -> None:
    with T.scratch("fix_adv2") as d:
        a = type("A", (), {"run_dir": str(d), "data_dir": str(d / "x.noindex"), "confirm_study_stopped": False})()
        with pytest.raises(core.StageRefused, match="confirm"):
            stages.cmd_cleanup(a)  # type: ignore[arg-type]
        a.confirm_study_stopped = True  # type: ignore[attr-defined]
        with pytest.raises(core.StageRefused, match="worktree|home"):
            stages.cmd_cleanup(a)  # type: ignore[arg-type]  # the data folder must be outside every worktree


def test_adv_cleanup_deletes_r1_files_and_records_the_hygiene(monkeypatch: pytest.MonkeyPatch) -> None:
    with T.scratch("fix_adv3") as d:
        (d / "x.noindex").mkdir()
        for n in ("control.bin", "rehearsal.bin"):
            (d / "x.noindex" / n).write_bytes(b"")
        monkeypatch.setattr(planmod, "require_data_dir_outside", lambda *a, **k: None)  # the scratch folder is inside the worktree; the placement rule is tested elsewhere
        monkeypatch.setattr(system, "run_command", lambda argv, timeout=60.0: (0, "", ""))
        a = type("A", (), {"run_dir": str(d / "run"), "data_dir": str(d / "x.noindex"), "confirm_study_stopped": True})()
        if (ROOT / planmod.FREEZE_RECORD).exists():
            pytest.skip("a freeze record exists in this tree")
        assert stages.cmd_cleanup(a) == 0  # type: ignore[arg-type]
        assert not list((d / "x.noindex").glob("*.bin")) and (d / "run" / "cleanup" / "cleanup.json").is_file()


def test_adv_r1_own_quiet_check_is_acted_on(monkeypatch: pytest.MonkeyPatch) -> None:
    from studies.p10is5 import r1

    cfg = copy.deepcopy(dict(CFG))
    cfg["device"] = {**cfg["device"], "band_start_tile": 8, "rehearsal_tiles": 64, "control_tiles": 24}
    cfg["cells"] = {**cfg["cells"], "r1_reread_working_set_tiles": [2, 4, 8]}
    real = system.idle_baseline

    def own_fails(*a: Any, **k: Any) -> dict[str, Any]:
        out = real(*a, **k)
        out["own_check_passed"] = False
        return out

    monkeypatch.setattr(system, "idle_baseline", own_fails)
    with T.scratch("fix_adv4") as d:
        clk = T.Clock()
        fs = T.FakeSystem(clk)
        io = T.FakeIO(int(CFG["seeds"]["r1_rehearsal_file_contents"]))
        io.model_cache = True
        deps = blocks.Deps(counter=T.FakeCounter(io), gate=T.scripted_gate(lambda: T.quiet_record(True)), run=fs.run, run_b=fs.run_b, sleep=clk.sleep, clock=clk, pread=io.pread, opener=io.opener)

        def build(path: Path, tiles: int, seed: int, ledger: device.WriteLedger, counter: Any, **kw: Any) -> dict[str, Any]:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"")
            return {}

        rec = r1.run_r1(cfg, d / "data", d / "run", deps, device.WriteLedger(d / "l.json", 10**9), now=clk, builder=build)
        assert not rec["passed"] and "R1's own quiet check on its idle window" in rec["checks_not_shown"] and "mapping" not in rec and "NO PHYSICAL COUNTER" in rec["reading_of_adr_section_7"]


def test_adv_report_prints_r1_harness_per_repeat_percentiles_and_the_record_tally() -> None:
    res = analysis.analyse(make_registry())
    text = report.render_report(res, {"record_bytes": 1234, "r1_harness": {"1": {"status": "MEASURED", "median_ns": 2500}, "2": {"status": "HARNESS FIGURE NOT MEASURED"}}}, [(k, s) for k in (1, 2, 4, 8, 16, 32) for s in (1, 3, 8, 64)])
    assert "tallied separately and NOT charged to the 10 GB ledger): 1234 B" in text and "R1's harness figure h(k)" in text and "| 1 | 2.5 | MEASURED |" in text
    assert "| depth k | pages s | repeat | median | p90 | p99 | max | pages/s |" in text and "| 1 | 1 | 1 | 50.0 | 50.0 | 50.0 | 500.0 | 1,000 |" in text


def test_adv_e1_does_not_overlap_another_studys_stage() -> None:
    cfg = copy.deepcopy(dict(CFG))
    cfg["budget"] = {**cfg["budget"], "free_space_min_bytes": 1}
    with T.scratch("fix_adv5") as d:
        recs = {}
        for n in ("r1", "m"):
            (d / n).write_text(n)
            recs[n] = d / n
        plan = planmod.Plan(planmod.build_plan(cfg, ROOT, d / "data.noindex", d, recs))
        clk = T.Clock()
        fs = T.FakeSystem(clk, other_windows=[(0.0, 1e9)])
        deps = blocks.Deps(counter=T.FakeCounter(T.FakeIO(1)), gate=T.scripted_gate(lambda: T.quiet_record(True)), run=fs.run, run_b=fs.run_b, sleep=clk.sleep, clock=clk)
        built: list[int] = []
        with pytest.raises(core.Paused, match="ANOTHER STUDY"):
            e2.run_e1(plan, cfg, deps, device.WriteLedger(d / "w.json", 10**12), d, now=clk, builder=lambda *a, **k: built.append(1) or {})
        assert built == []


def test_adv_seed_gate_accepts_only_the_known_self_collision_pattern() -> None:
    known = "FAIL: P10-I-R ADR-0029 / data: bridge draw sets (5) [id] 290001..290001 hits inventory: P10IR / config literal [id] (configs/p10ir_routing.toml)"
    assert gates.KNOWN_SELF_COLLISION.search(known)
    assert not gates.KNOWN_SELF_COLLISION.search(known.replace("P10-I-R ADR-0029", "P10-I-S4 ADR-0027"))
    assert not gates.KNOWN_SELF_COLLISION.search(known.replace("P10IR / config literal", "P10-S1 / config literal"))
    res = gates.seed_gate()
    assert res["passed"] and res["checker"]["unknown_fail_lines"] == []


def test_adv_quiet_rule_excludes_the_launcher_and_counts_any_other_arborlm_process() -> None:
    ps = "  PID COMMAND\n  101 -zsh\n  102 /usr/bin/caffeinate -i /x/ArborLM/.venv/bin/python -m studies.p10is5.stages r1\n  103 /x/ArborLM/.venv/bin/python -m studies.p10is5.stages r1\n  200 -zsh /Users/x/dandush03/ArborLM/.claude/worktrees/other/run.sh\n  201 /x/ArborLM/.venv/bin/python -m pytest\n"
    ppid = "  PID  PPID\n  101     1\n  102   101\n  103   102\n  200     1\n  201   200\n"
    fam = system.process_family(system.parse_ppids(ppid), 103)
    assert fam == {101, 102, 103}  # the shell that launched the stage, caffeinate, and the stage itself
    others = system.other_study_processes(system.parse_ps(ps), fam, CFG["quiet"]["process_markers"])
    assert [p for p, _ in others] == [200, 201]  # another shell with ArborLM in its command line, and its pytest, count
    assert "ancestors" in system.PROCESS_RULE and "arborlm" in system.PROCESS_RULE


def test_adv_quiet_record_lists_the_matched_processes_by_command() -> None:
    clk = T.Clock()
    fs = T.FakeSystem(clk, other_windows=[(0.0, 1e9)])
    rec = system.read_quiet(fs.run, fs.run_b, CFG, clk.sleep, clk, None)
    assert rec["readings"]["other_process_count"] == 1 and rec["readings"]["other_processes"][0][1].endswith("pytest") and "ancestors" in rec["readings"]["rule"]


# --- point 7: m_t is NOT DETERMINED with fewer than five valid medians; M is repeated once --------------------------------------------------------
def mpass(r: int, s: int, med: int, status: str = "OK") -> dict[str, Any]:
    return {"key": core.pass_key("M", r, 1, s), "repeat": r, "k": 1, "s": s, "counter_status": status, "latency_ns": [med] * 3, "wall_ns": 10**9}


def test_point7_cv_r_needs_five_valid_medians_and_m_repeats_once() -> None:
    five = [mpass(r, s, 1000 * r + 100 * s) for r in range(1, 6) for s in (1, 3)]
    assert rehearsal.cv_r(five, [])["cv_r"] is not None
    four = [p if not (p["repeat"] == 3 and p["s"] == 3) else {**p, "counter_status": "STORE PAGES CACHED"} for p in five]
    out = rehearsal.cv_r(four, [])
    assert out["cv_r"] is None and out["cells"]["c(3)"]["valid_medians"] == 4 and out["cells"]["c(3)"]["cv"] is None  # NOT DETERMINED
    with T.scratch("fix_p7") as d:
        run = d / "run"
        (run / "r1").mkdir(parents=True)
        r1p = run / "r1" / "r1.json"
        core.write_record(r1p, {**core.envelope("r1"), "passed": True, "idle_figures": {k: 1.0 for k in freeze.FIGURE_KEYS}})
        (run / "M").mkdir()
        core.write_record(run / "M" / "m.json", {**core.envelope("rehearsal"), "stage": "M", "summary": {"margin": None}})
        a = type("A", (), {"run_dir": str(run), "data_dir": str(d / "x.noindex"), "r1_record": str(r1p), "repeat_cause": None})()
        with pytest.raises(core.StageRefused, match="repeat it once with --repeat-cause"):
            stages.cmd_m(a)  # type: ignore[arg-type]
        (run / "M_attempt1").mkdir()
        a.repeat_cause = "a worker was killed"  # type: ignore[attr-defined]
        with pytest.raises(core.StageRefused, match="already been repeated once"):
            stages.cmd_m(a)  # type: ignore[arg-type]
        core.write_record(run / "M" / "m.json", {**core.envelope("rehearsal"), "stage": "M", "summary": {"margin": {"m_t": 0.1, "timing_spread": False}}}, overwrite=True)
        shutil.rmtree(run / "M_attempt1")
        with pytest.raises(core.StageRefused, match="not repeated"):
            stages.cmd_m(a)  # type: ignore[arg-type]
    # the candidate plan is refused on a margin that is not determined
    with pytest.raises(core.StageRefused, match="no margin"):
        freeze.figures_from_records({"passed": True, "idle_figures": {k: 1.0 for k in freeze.FIGURE_KEYS}}, {"summary": {"margin": None}})




# --- second re-audit: F1, F2, A1, A3 -----------------------------------------------------------------------------------------------------------
def test_f1_m_summary_skips_incomplete_passes_and_counts_them() -> None:
    with T.scratch("fix_f1") as d:
        ctx, state, issued = interrupted_run(d, [(1, 2)])
        summary = rehearsal.m_summary(ctx, CFG, 0.0)  # earlier code: KeyError 'wall_ns' on the INCOMPLETE record
        assert len(summary["incomplete_passes"]) == 1 and summary["passes"] == len(bench.load_stage_records(ctx)[0]) - 1
        assert summary["mean_read_seconds_per_pass_measured"] is not None


def test_a3_sequence_numbers_are_unique_across_a_resume() -> None:
    with T.scratch("fix_a3") as d:
        ctx, state, issued = interrupted_run(d, [(1, 3)])
        seqs = [p["seq"] for p in bench.load_stage_records(ctx)[0]]
        assert len(seqs) == len(set(seqs))


def test_f2_unhandled_stops_go_to_the_stage_own_folder_and_pre_freeze_commands_write_none() -> None:
    with T.scratch("fix_f2") as d:
        run = d / "run"
        for stage, folder in (("e1", "E1"), ("p", "P"), ("report", "report"), ("delete", "delete"), ("analysis", "analysis"), ("e2", "E2")):
            a = type("A", (), {"command": "registered", "stage": stage, "run_dir": str(run)})()
            stages.record_unhandled(run, a, KeyError("x"))  # type: ignore[arg-type]
            assert len(list((run / folder / "stops").glob("unhandled_*.json"))) == 1, stage
        assert len(list((run / "E2" / "stops").iterdir())) == 1  # only the E2 stage's own stop is in E2/stops
        for command in ("candidate-plan", "freeze", "config-proposal", "caps-proposal", "seed-gate"):
            before = sorted(run.rglob("*"))
            stages.record_unhandled(run, type("A", (), {"command": command, "run_dir": str(run)})(), OSError("mistyped path"))  # type: ignore[arg-type]
            assert sorted(run.rglob("*")) == before, command
        ctx = T.tiny_context(run, repeats=2, spare=True)
        reg = e2.build_registry(ctx, CFG, {})
        assert [s["cause"] for s in reg["stops"]] == ["KeyError"]  # the E2 analysis sees E2's own stop only


def test_a1_a_resumed_repeat_of_m_records_attempt_two(monkeypatch: pytest.MonkeyPatch) -> None:
    with T.scratch("fix_a1") as d:
        run = d / "run"
        (run / "r1").mkdir(parents=True)
        r1p = run / "r1" / "r1.json"
        core.write_record(r1p, {**core.envelope("r1"), "passed": True, "idle_figures": {k: 1.0 for k in freeze.FIGURE_KEYS}})
        (run / "M_attempt1").mkdir()  # the first attempt was kept; the repeat was paused before it wrote m.json
        monkeypatch.setattr(stages, "make_deps", lambda cfg, where: blocks.Deps(counter=T.FakeCounter(T.FakeIO(1)), gate=T.scripted_gate(lambda: T.quiet_record(True))))
        monkeypatch.setattr(rehearsal, "run_rehearsal_stage", lambda *x, **k: None)
        monkeypatch.setattr(rehearsal, "m_summary", lambda ctx, cfg, h: {"cv": {"cv_r": None}, "margin": None, "passes": 0})
        a = type("A", (), {"run_dir": str(run), "data_dir": str(d / "x.noindex"), "r1_record": str(r1p), "repeat_cause": None})()
        stages.cmd_m(a)  # type: ignore[arg-type]
        rec = core.read_record(run / "M" / "m.json")
        assert rec["attempt"] == 2 and rec["outcome"] == "ENGINEERING NOT EVALUABLE — MARGIN NOT DETERMINED"


# --- the launcher's keep-awake watcher is not another study's process --------------------------------------------------------------------------
LAUNCH_TABLE = """  PID  PPID COMM
69270     1 /usr/bin/timeout
69271 69270 /opt/homebrew/bin/uv
69275 69271 /usr/bin/caffeinate
69276 69271 /Users/x/ArborLM/.venv/bin/python
69300     1 -zsh
69301 69300 /Users/x/ArborLM/.venv/bin/python
69400     1 /usr/bin/caffeinate
"""
LAUNCH_PS = """  PID COMMAND
69270 timeout 3h sh studies/p10is5/launch/r1.sh /Users/x/ArborLM/run /Users/x/data.noindex
69271 uv run --locked python -m studies.p10is5.stages r1 --run-dir /Users/x/ArborLM/run
69275 caffeinate -i uv run --locked python -m studies.p10is5.stages r1 --run-dir /Users/x/ArborLM/run
69276 /Users/x/ArborLM/.venv/bin/python -m studies.p10is5.stages r1 --run-dir /Users/x/ArborLM/run
69301 /Users/x/ArborLM/.venv/bin/python -m studies.p10s1.stages registered a1
69400 caffeinate -i /Users/x/ArborLM/.venv/bin/python -m studies.p10is3.stages rehearse
"""


def test_launcher_watcher_is_family_but_a_sibling_study_and_a_foreign_caffeinate_are_not(monkeypatch: pytest.MonkeyPatch) -> None:
    import os

    monkeypatch.setattr(os, "getpid", lambda: 69276)

    def run(argv: Any) -> tuple[int, str, str]:
        return (0, LAUNCH_TABLE, "") if "pid,ppid,comm" in argv else (0, LAUNCH_PS, "")

    fam = system.own_family(run)
    assert {69270, 69271, 69276, 69275} <= fam and 69301 not in fam and 69400 not in fam
    others = system.read_other_processes(run, CFG["quiet"]["process_markers"])
    assert [p for p, _ in others] == [69301, 69400]  # a second study from another shell counts; a caffeinate that is not the child of an ancestor counts, as its command carries a marker
    # the rule is nothing wider: a caffeinate child of an ancestor is family, a non-caffeinate sibling of the stage with a marker is not
    table = system.parse_ps_comm(LAUNCH_TABLE)
    assert system.launcher_watchers(table, {69271}) == {69275} and system.launcher_watchers(table, {69300}) == set()


def test_idle_window_records_every_sample_and_attempt_as_it_happens() -> None:
    with T.scratch("fix_idle_rec") as d:
        clk = T.Clock()
        fs = T.FakeSystem(clk, other_windows=[(25.0, 35.0)])
        path = d / "r1" / "idle_attempts.jsonl"
        seen: list[int] = []

        def rec(ev: dict[str, Any]) -> None:
            core.append_jsonl(path, ev)
            seen.append(len(path.read_text().splitlines()))  # the line is on disk before the next sample is taken

        base = system.idle_baseline(fs.run, fs.run_b, CFG, clk.sleep, clk, rec)
        lines = [json.loads(x) for x in path.read_text().splitlines()]
        assert seen == list(range(1, len(lines) + 1)) and base["status"] == "MEASURED"
        attempts = [x for x in lines if x["kind"] == "attempt"]
        assert [a["discarded"] for a in attempts] == [True, False] and attempts[0]["failing"]["other_processes"]  # the discarded window's reading survives
        assert sum(1 for x in lines if x["kind"] == "sample" and x["attempt"] == 2) == 60


def test_real_launch_shape_exec_caffeinate_does_not_list_the_watcher() -> None:
    import shutil

    if sys.platform != "darwin" or not shutil.which("caffeinate"):
        pytest.skip("macOS caffeinate only")
    script = (
        "import sys, json\nsys.path.insert(0, {root!r})\nfrom studies.p10is5 import system\nrun = system.run_command\n"
        "rc, out, _ = run(['ps', '-Ao', 'pid,ppid,comm'])\ntable = system.parse_ps_comm(out)\nfam = system.own_family(run)\n"
        "others = system.read_other_processes(run, {markers!r})\n"
        "print(json.dumps({{'caffeinate_in_table': [p for p, pp, c in table if c.rsplit('/', 1)[-1] == 'caffeinate'], 'family': sorted(fam), 'others': [[p, c[:100]] for p, c in others]}}))\n"
    
    ).format(root=str(ROOT), markers=list(CFG["quiet"]["process_markers"]))
    p = subprocess.run(["sh", "-c", f'exec caffeinate -i "{sys.executable}" -c "$0"', script], capture_output=True, text=True, timeout=120)  # the shape of the fixed launch scripts
    assert p.returncode == 0, p.stderr[-500:]
    out = json.loads(p.stdout.strip().splitlines()[-1])
    assert out["caffeinate_in_table"], "no caffeinate process was seen: the test would be vacuous"
    assert not [o for o in out["others"] if o[1].lstrip().startswith("caffeinate")], out["others"]  # the launcher's own keep-awake watcher is not 'another study's process'
