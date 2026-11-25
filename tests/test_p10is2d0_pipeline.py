# ruff: noqa: E501
"""P10-I-S2-D0: the task list, the worker body, the ledger and cap, the reproduction comparison and the report over a tiny synthetic world (Part T's engine fixtures: a random student, 12 synthetic items per panel, synthetic
snapshots written to a temporary directory). Nothing here is a result and no real snapshot is opened."""

import json
import sys
from pathlib import Path

import pytest
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))

from p10is2_engine_fixtures import CFG_T, world  # noqa: E402

from studies.p10is2.quantities import Thresholds  # noqa: E402
from studies.p10is2d0 import finalize, gates, passes, run  # noqa: E402
from studies.p10is2d0 import report as rep  # noqa: E402
from studies.p10s2 import core as c2  # noqa: E402
from studies.p10s2.memory import MemoryArm, SparseStore  # noqa: E402
from studies.p10s2.world import save_arm  # noqa: E402


def test_the_task_list_is_96_passes_sixteen_per_cell_and_24_gate_passes() -> None:
    main = passes.main_tasks()
    ps = [t for t in main if t["kind"] == "pass"]
    assert len(ps) == 96 and len([t for t in main if t["kind"] == "stats"]) == 6
    assert main[: 6] == [t for t in main if t["kind"] == "stats"]  # statistics first (section 8.3)
    for cell in passes.cells():
        mine = [t for t in ps if (t["rep"], t["order"]) == cell]
        assert len(mine) == 16 and len([t for t in mine if t["role"] == "first"]) == 9 and len([t for t in mine if t["role"] == "second"]) == 7
        first = {(t["store"], t["cond"]) for t in mine if t["role"] == "first"}
        assert first == {("M1", "a"), ("append", "a"), ("append", "d1"), ("final", "a"), ("final", "b1"), ("final", "c"), ("final", "d1"), ("final", "e1"), ("final", "g1")}
        second = {(t["store"], t["cond"]) for t in mine if t["role"] == "second"}
        assert second == {("final", "a"), ("final", "b2"), ("final", "c"), ("final", "d2"), ("final", "e2"), ("final", "g2"), ("final", "e1")}
    assert len(passes.gate_tasks()) == 24
    assert len({t["id"] for t in main + passes.gate_tasks()}) == 96 + 6 + 24


def _tiny_cell(tmp: Path) -> tuple[object, dict[str, MemoryArm]]:
    w = world()
    codes = w.codes(0)
    width = w.cfg.width
    g = torch.Generator().manual_seed(1)
    m1 = SparseStore.new(width, 16, g)
    with torch.no_grad():
        m1.values[0].mul_(300)
        m1.gates[0].fill_(1.0)
    at = m1.clone()
    at.append_stage(16, torch.Generator().manual_seed(2))
    final = at.clone()
    with torch.no_grad():
        final.values[1].mul_(300)
        final.gates[1].fill_(0.5)
    snaps = tmp / "snapshots"
    for name, st in (("r0/M1/AB", m1), ("r0/M-append/AB@append", at), ("r0/M-append/AB", final)):
        save_arm(MemoryArm(st, w.layer, codes), snaps, name)
    return w, run.load_cell(w, 0, "AB", snaps)


@pytest.fixture(scope="module")
def tiny(tmp_path_factory: pytest.TempPathFactory) -> tuple[object, dict[str, MemoryArm], Path]:
    tmp = tmp_path_factory.mktemp("d0")
    w, arms = _tiny_cell(tmp)
    return w, arms, tmp


def _run(w: object, arms: dict[str, MemoryArm], out: Path, t: dict[str, object], cap: float = 1e9) -> dict[str, object]:
    led = passes.Ledger(out, f"t_{t['id']}".replace("|", "_"))
    assert passes.execute_task(w, arms, t, out, led, cap)
    return json.loads(passes.record_path(out, str(t["id"])).read_text())  # type: ignore[no-any-return]


def test_a_pass_with_the_a_read_reproduces_the_registered_arm_item_for_item(tiny: tuple[object, dict[str, MemoryArm], Path]) -> None:
    w, arms, tmp = tiny
    out = tmp / "out_a"
    reg = _run(w, arms, out, {"id": "G|0|AB|final|first", "kind": "gate", "rep": 0, "order": "AB", "store": "final", "role": "first"})
    got = _run(w, arms, out, {"id": "P|0|AB|final|a|first", "kind": "pass", "rep": 0, "order": "AB", "store": "final", "cond": "a", "role": "first"})
    assert gates.compare_pass(reg, got) == {"pass": True, "largest_deviation": 0.0}
    assert reg["oracle_line"] == got["oracle_line"] and "NOT A REGISTERED LABEL" in str(got["label"])


def test_b1_on_the_final_store_reproduces_m1_by_identity(tiny: tuple[object, dict[str, MemoryArm], Path]) -> None:
    w, arms, tmp = tiny
    out = tmp / "out_b"
    m1 = _run(w, arms, out, {"id": "P|0|AB|M1|a|first", "kind": "pass", "rep": 0, "order": "AB", "store": "M1", "cond": "a", "role": "first"})
    b1 = _run(w, arms, out, {"id": "P|0|AB|final|b1|first", "kind": "pass", "rep": 0, "order": "AB", "store": "final", "cond": "b1", "role": "first"})
    assert gates.compare_pass(m1, b1) == {"pass": True, "largest_deviation": 0.0}


def test_the_identity_gates_hold_on_the_tiny_cell_and_a_pass_changes_when_the_read_does(tiny: tuple[object, dict[str, MemoryArm], Path]) -> None:
    w, arms, tmp = tiny
    q = passes.distinct_queries(w, "AB", arms["final"].codes)
    rec = gates.identity_gates(arms["M1"].store, arms["append"].store, arms["final"].store, q)
    assert all(v["pass"] for v in rec.values()), rec
    out = tmp / "out_c"
    a = _run(w, arms, out, {"id": "P|0|AB|final|a|first", "kind": "pass", "rep": 0, "order": "AB", "store": "final", "cond": "a", "role": "first"})
    c = _run(w, arms, out, {"id": "P|0|AB|final|c|first", "kind": "pass", "rep": 0, "order": "AB", "store": "final", "cond": "c", "role": "first"})
    assert len(a["items"]) == 12 and a["sequences"] != c["sequences"] or a["items"] != c["items"]  # type: ignore[arg-type]


def test_the_cap_stops_a_pass_and_writes_no_record(tiny: tuple[object, dict[str, MemoryArm], Path]) -> None:
    w, arms, tmp = tiny
    out = tmp / "out_cap"
    led = passes.Ledger(out, "capped")
    led.tick()
    t = {"id": "P|0|AB|final|a|first", "kind": "pass", "rep": 0, "order": "AB", "store": "final", "cond": "a", "role": "first"}
    assert passes.execute_task(w, arms, t, out, led, cap=-1.0) is False
    assert not passes.record_path(out, t["id"]).is_file()
    assert any(out.glob("cap_reached_*.json"))


def test_the_ledger_sums_every_process_file_and_a_paused_clock_does_not_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    now = [100.0]
    monkeypatch.setattr(passes.time, "monotonic", lambda: now[0])
    a, b = passes.Ledger(tmp_path, "w0"), passes.Ledger(tmp_path, "orch")
    now[0] += 5.0
    a.tick()
    b.pause()  # the orchestrator waits for workers: 5 s charged to it so far
    now[0] += 7.0
    a.tick()
    assert a.elapsed() == pytest.approx(12.0) and b.elapsed() == pytest.approx(5.0)
    b.unpause()
    now[0] += 1.0
    b.tick()
    assert passes.charged_total(tmp_path / "cost") == pytest.approx(12.0 + 6.0)


def test_report_over_full_synthetic_passes_has_every_block_labelled_and_the_decomposition_telescopes(tiny: tuple[object, dict[str, MemoryArm], Path]) -> None:
    w, arms, tmp = tiny
    out = tmp / "out_full"
    # fill all 96 passes of the cell (0, AB) from the tiny world, and copy them to the other five cells' ids so the report has the full shape
    recs: dict[str, dict[str, object]] = {}
    for t in passes.main_tasks():
        if t["kind"] == "pass" and (t["rep"], t["order"]) == (0, "AB"):
            recs[t["id"]] = _run(w, arms, out, t)
    for t in passes.main_tasks():
        if t["kind"] == "pass" and (t["rep"], t["order"]) != (0, "AB"):
            src = recs[t["id"].replace(f"P|{t['rep']}|{t['order']}", "P|0|AB")]
            p = passes.record_path(out, t["id"])
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps({**src, "id": t["id"]}))
    reg: dict[str, float] = {}
    for cap in "AB":
        reg[f"S0|-|-|s:E_{cap}"] = 0.1
        reg[f"TEACHER|-|-|s:E_{cap}"] = 0.9
    for r, o in passes.cells():
        for pan in ("E_A", "E_B"):
            for arm in ("M1", "M-append"):
                reg[f"{arm}|{o}|{r}|s:{pan}"] = 0.5
    rec = finalize.build_records(out, reg, Thresholds.from_config(CFG_T))
    assert rec["passes_present"] == 96 and not rec["missing"]
    for cell in rec["cells"].values():
        d = cell["decomposition"]
        assert d["i"] + d["ii"] + d["iii"] == pytest.approx(d["T"], abs=1e-12)
    text = finalize.render(rec, {"identity": {"pass": True}}, {}, {"worker_hours_total": 0.0}, "deadbeef", "SYNTHETIC TEST")
    assert rep.require_labelled(text) == text
    assert "SUMMARY WORDS" in text and "COUNTERFACTUAL RET ARITHMETIC" in text and "REGISTERED SCORES FOR SCALE" in text
    # the record writer copies small records and writes tables from them
    from studies.p10is2d0 import record_md

    (out / "records").mkdir()
    (out / "records" / "readings.json").write_text(json.dumps(rec))
    (out / "records" / "cost.json").write_text(json.dumps({"worker_hours_total": 0.0}))
    (out / "launch.json").write_text(json.dumps({"commit": "deadbeef", "branch": "b", "torch": "2.8.0"}))
    (out / "report.txt").write_text(text)
    assert record_md.main(["--run-dir", str(out), "--results-dir", str(tmp / "results_copy")]) == 0
    md = (tmp / "results_copy" / "RECORD.md").read_text()
    assert "### Decomposition" in md and "deadbeef" in md and "Summary words" in md and rep.POSTHOC in md
    assert not (tmp / "results_copy" / "passes").exists()  # the per-item bulk is not copied


def test_an_incomplete_set_of_passes_prints_no_table_and_no_word(tiny: tuple[object, dict[str, MemoryArm], Path]) -> None:
    w, arms, tmp = tiny
    out = tmp / "out_partial"
    _run(w, arms, out, {"id": "P|0|AB|final|a|first", "kind": "pass", "rep": 0, "order": "AB", "store": "final", "cond": "a", "role": "first"})
    rec = finalize.build_records(out, {}, Thresholds.from_config(CFG_T))
    assert rec["passes_present"] == 1 and len(rec["missing"]) == 95 and not rec["cells"]
    text = finalize.render(rec, {}, {}, {}, "x", "INCOMPLETE")
    assert "INCOMPLETE" in text and "SUMMARY WORDS" not in text and "DECOMPOSITION" not in text


def test_cell_statistics_run_on_the_tiny_cell(tiny: tuple[object, dict[str, MemoryArm], Path]) -> None:
    w, arms, tmp = tiny
    out = tmp / "out_stats"
    rec = _run(w, arms, out, {"id": "S|0|AB", "kind": "stats", "rep": 0, "order": "AB"})
    assert set(rec) >= {"append|first", "final|first", "final|second"}
    fs = rec["final|first"]
    assert fs["protected_stage"] == 1 and fs["reads"] > 0 and fs["words"]["n_p"]["n"] > 0 and fs["markers"]["n_p"]["n"] > 0
    assert rec["final|second"]["protected_stage"] == 2
    assert fs["gates"] == [1.0, 0.5] and rec["append|first"]["gates"] == [1.0, 0.0]
    assert c2.TOP == 8


def test_chunked_decoding_equals_one_score_panel_call(tiny: tuple[object, dict[str, MemoryArm], Path], monkeypatch: pytest.MonkeyPatch) -> None:
    from studies.p10s2.evaluate import score_panel

    w, arms, tmp = tiny
    monkeypatch.setattr(passes, "CHUNK", 5)
    got = _run(w, arms, tmp / "out_chunk", {"id": "G|0|AB|final|first", "kind": "gate", "rep": 0, "order": "AB", "store": "final", "role": "first"})
    with torch.no_grad():
        full = score_panel(w.ctx, arms["final"], w.ctx.panels["E_A"])  # type: ignore[attr-defined]
    assert got["items"] == full.items and got["sequences"] == full.sequences and got["mean"] == full.mean
