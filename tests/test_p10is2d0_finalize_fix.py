# ruff: noqa: E501
"""P10-I-S2-D0, lead decision 1: the report's statistics loop must skip top-level scalar keys of a stats record (id, label, oracle_line, pid, task_seconds, worker). The values here are synthetic; nothing is a result."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from p10is2_engine_fixtures import CFG_T  # noqa: E402
from test_p10is2d0_pipeline import _run, tiny  # noqa: E402, F401

from studies.p10is2.quantities import Thresholds  # noqa: E402
from studies.p10is2d0 import finalize, passes  # noqa: E402


def _stats_record() -> dict[str, object]:
    q = {"n": 10, "undefined": 0, "mean": 0.1, "median": 0.1, "p5": 0.0, "p95": 0.2}
    store = {"panel": "E_A", "protected_stage": 1, "reads": 20, "marker_reads": 5, "gates": [0.5, 0.5], "words": {"q1": q}, "markers": {"q1": q}}
    return {
        "rep": 0, "order": "AB", "append|first": store, "final|first": store, "final|second": store,
        "id": "S|0|AB", "label": "POST-HOC EXPLORATORY DIAGNOSTIC OF AN OBSERVED RUN; NOT A REGISTERED LABEL", "oracle_line": "x", "pid": 123, "task_seconds": 1.5, "worker": 0,
    }  # fmt: skip


def test_render_skips_the_scalar_top_level_keys_of_a_stats_record(tiny) -> None:  # type: ignore[no-untyped-def]  # noqa: F811
    w, arms, tmp = tiny
    out = tmp / "out_fix"
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
    text = finalize.render(rec, {"identity": {"pass": True}}, {"0/AB": _stats_record()}, {"worker_hours_total": 0.0}, "deadbeef", "SYNTHETIC TEST")
    assert "READ STATISTICS (section 5.2) cell 0/AB" in text
    assert text.count("panel=E_A protected_stage=1") == 3  # the three per-store entries, nothing from the scalar keys
    assert "worker" not in text.split("READ STATISTICS")[1].split("SCORES")[0].replace("worker_hours", "")
