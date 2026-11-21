# ruff: noqa: E501
"""P10IS2 Part Q recomputation from stored per-item records (ADR-0025 section 4.4). Self-check; the independent recomputation is the auditor's. Seeds 934001-934999."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_p10is2_partq_pipeline2 import ctx_of  # noqa: E402

from studies.p10is2.partq import pipeline, recompute  # noqa: E402


def test_recompute_agrees_on_a_clean_run_sealed_or_not(tmp_path: Path) -> None:
    for seal in (False, True):
        ctx = ctx_of(tmp_path / str(seal), seal=seal)
        pipeline.run_all(ctx)
        r = recompute.recompute(ctx, regeneration={"ok": True})
        assert r["ok"] and r["differences"] == [] and r["outcome"] is None and r["regeneration_included"]


def test_recompute_stops_on_a_changed_value_or_stored_batch_or_regeneration(tmp_path: Path) -> None:
    ctx = ctx_of(tmp_path)
    pipeline.run_all(ctx)
    vp = ctx.d("qfit/values.json")
    v = json.loads(vp.read_text())
    v["mean_chrf"]["A"]["A"] += 2e-6  # beyond the 1e-6 tolerance
    vp.write_text(json.dumps(v))
    r = recompute.recompute(ctx)
    assert not r["ok"] and r["outcome"] == "ENGINEERING STOP — RECOMPUTATION" and any("mean chrF teacher A on A" in d for d in r["differences"])
    v["mean_chrf"]["A"]["A"] -= 2e-6
    v["mean_chrf"]["A"]["A"] += 5e-7  # inside the tolerance
    vp.write_text(json.dumps(v))
    assert recompute.recompute(ctx)["ok"]
    v["per_item"]["B"][3]["accepted"] = not v["per_item"]["B"][3]["accepted"]
    vp.write_text(json.dumps(v))
    r2 = recompute.recompute(ctx)
    assert not r2["ok"] and any("accept indicator differs, teacher B item 3" in d for d in r2["differences"])
    v["per_item"]["B"][3]["accepted"] = not v["per_item"]["B"][3]["accepted"]
    vp.write_text(json.dumps(v))
    assert not recompute.recompute(ctx, regeneration={"ok": False})["ok"]
