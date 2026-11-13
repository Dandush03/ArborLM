# Preserve the executed import order in this archival checker.
# ruff: noqa: I001
"""Root hand-calculated arithmetic checks; synthetic scalar records only."""

import copy
import json
import runpy
from pathlib import Path
from arborlm.p5_analysis import describe, timing_analysis

f = runpy.run_path("tests/test_p5_independent_contract.py")
base = f["_quality_fixture"]()
checks = {}


def outcome(rows):
    return describe(rows)


r = outcome(base)
assert all(r["quality_flags"].values())
for key, expected in [
    ("G_flat", 0.01),
    ("G_fixed_tree", 0.02),
    ("G_learned_tree", 0.03),
    ("P_learned_tree", 0.01),
    ("R", 0.01),
    ("T_learned_tree", -0.02),
    ("Q_learned_tree", 0.02),
]:
    assert abs(r["summary"][key]["mean"] - expected) < 1e-12
checks["hand_calculated_positive_effects_all_flags"] = True
for mode, clause in [
    ("gain", "mean_gain"),
    ("shuffle", "mean_shuffle"),
    ("initial", "mean_final_below_initial"),
]:
    rows = copy.deepcopy(base)
    for x in rows:
        if x["variant"] == "learned_tree":
            if mode == "gain":
                x["final_nll"] = 0.996
                x["interventions"]["enabled"] = 0.996
                x["interventions"]["values_permuted"] = 1.006
            elif mode == "shuffle":
                x["interventions"]["values_permuted"] = x["final_nll"] + 0.004
            else:
                x["initial_nll"] = x["final_nll"]
    r = outcome(rows)
    assert not r["quality_clauses"]["U_learned_tree"][clause]
    assert not r["quality_flags"]["U_learned_tree"] and not r["quality_flags"]["R"]
    checks["usefulness_" + clause] = True
rows = copy.deepcopy(base)
for x in rows:
    if x["variant"] == "flat":
        x["final_nll"] = 0.96
        x["interventions"]["enabled"] = 0.96
r = outcome(rows)
assert not any(r["quality_clauses"]["Q_learned_tree"].values())
assert not any(r["quality_clauses"]["Q_fixed_tree"].values())
checks["quality_penalty_all_clauses_reject"] = True
rows = copy.deepcopy(base)
for x in rows:
    if x["variant"] == "dense":
        x["final_nll"] = 0.95
        x["interventions"]["enabled"] = 0.95
r = outcome(rows)
for v in ("flat", "fixed_tree", "learned_tree"):
    assert not any(r["quality_clauses"]["dense_tolerance_" + v].values())
checks["dense_tolerance_all_clauses_reject"] = True
for zeros, expected in [(5, True), (6, False)]:
    rows = copy.deepcopy(base)
    selected = [x for x in rows if x["variant"] == "learned_tree"][:zeros]
    for x in selected:
        x["final_nll"] = 1.0
        x["interventions"]["enabled"] = 1.0
        x["interventions"]["values_permuted"] = 1.0
    r = outcome(rows)
    assert r["quality_clauses"]["U_learned_tree"]["cells"] is expected
    assert r["quality_clauses"]["U_learned_tree"]["parents"] is expected
checks["usefulness_22cell_8parent_strict_sign_boundaries"] = True
workers = f["_timing_fixture"]()
for worker in workers:
    for x in worker.get("timing", {}).get("records", []):
        if x["variant"] in ("fixed_tree", "learned_tree"):
            x["median_ns"] = 80.0 if x["scope"] == "addition_forward" else 105.0
latency, work = timing_analysis(workers)
assert all(x["status"] == "PASS" for x in latency.values())
assert all(x["passed"] for x in work.values())
checks["latency_point8_and1point05_boundaries"] = True
for worker in workers:
    for x in worker.get("timing", {}).get("records", []):
        if x["variant"] == "learned_tree" and x["scope"] == "addition_forward":
            x["median_ns"] = 81.0
latency, _ = timing_analysis(workers)
assert latency["learned_tree"]["status"] == "FAIL"
assert latency["fixed_tree"]["status"] == "PASS"
checks["latency_geometric_margin_reject"] = True
report = {
    "status": "PASS",
    "checks": checks,
    "method": (
        "Root hand calculations against separate-reviewer scalar fixtures; "
        "no model forward, corpus, or timing call"
    ),
    "scientific_evaluations": 0,
}
Path("experiments/review/p5-root-preflight/analysis-clauses.json").write_text(
    json.dumps(report, indent=2) + "\n"
)
print(json.dumps(report, indent=2))
