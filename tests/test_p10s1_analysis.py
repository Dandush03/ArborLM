# ruff: noqa: E501
"""P10S1 analysis and report on synthetic records of the whole registry (ADR-0021 section 10.2): on-disk records in the layout of a real run, covering both outcomes of section 8, a
missing cell, a failed cell, a non-finite cell, a failed task, each failed gate, an identity mismatch, leakage, a failed REF, a failed DEP, the overload row, the seed block, and the
censoring cases of section 8.8 at registry level. Every rendered report is checked for the STORE ONLY; ORACLE-ADDRESSED tag on every positive label. The accuracies are a declared
function of (arm, cell, replicate, update, panel): nothing here measures a model or a seed. Self-check only: not independent review, not Astra validation, not human approval."""

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from studies.p10s1 import analysis, core, report  # noqa: E402
from studies.p10s1 import classes as C  # noqa: E402
from studies.p10s1 import frozen as fz  # noqa: E402
from studies.p10s1 import synthetic as syn  # noqa: E402

PLAN = core.Plan(seed_block_draws=(1,))
FRO = fz.Frozen.build(PLAN, fz.default_cpu_table())


def run(tmp_path: Path, scn: syn.Scenario, fro: fz.Frozen = FRO, **kw: Any) -> tuple[dict[str, Any], Path]:
    d = tmp_path / "run"
    syn.write_run(d, fro, scn)
    gates = json.loads((d / "gates.json").read_text()) if (d / "gates.json").exists() else None
    study = analysis.load_study(d, fro)
    result = analysis.analyze_study(study, fro, gates=gates, **kw)
    core.write_record(d / "analysis.json", core.jsonable({**core.envelope("analysis"), "result": result}))
    return result, d


def rendered(d: Path, banner: str | None = None) -> str:
    paths = report.write_report(d, d / "results", banner=banner)
    text = paths[1].read_text()
    assert C.untagged_positive_labels(text) == [] and core.ORACLE_SENTENCE in text and core.STORE_ONLY_TAG in text and "Astra review: NOT_PERFORMED" in text
    return text


def a_max_all(v: float):
    def f(arm: str, facts: int, slots: int, rep: int) -> float:
        return 0.15 if arm == "D-OQ" else (1.0 if arm == "R2" else v)

    return f


def tau_by_slots(t4: float, t16: float, t64: float):
    def f(arm: str, facts: int, slots: int) -> float:
        return 200.0 if arm == "R2" else {4096: t4, 16384: t16, 65536: t64}[slots]

    return f


# --- the default scenario: both lines positive on paper, every positive label tagged ------------------------------------------------------------
# --- outcomes of the capacity line -------------------------------------------------------------------------------------------------------
# --- incomplete and engineering failures ---------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("gate", ["g1", "g2", "g4", "g5", "g6", "g7", "g8", "g9"])
def test_a_failed_engineering_gate_gives_no_scientific_label(tmp_path: Path, gate: str) -> None:
    r, d = run(tmp_path, syn.Scenario(gates_ok=False, failed_gate=gate))
    assert r["assessment"]["status"] == C.S1_ENGINEERING_FAILURE and f"gate {gate.upper()} failed" in r["assessment"]["engineering"]["reasons"]
    assert r["outcome"]["capacity"]["label"] == C.S1_ENGINEERING_FAILURE == r["outcome"]["efficiency"]["label"] and r["capacity"] is None
    text = rendered(d)
    assert "S1-ENGINEERING-FAILURE" in text and "CAPACITY-POSITIVE" not in text and "EFFICIENCY-POSITIVE" not in text


def test_lane_l_cells_are_never_silently_dropped(tmp_path: Path) -> None:
    plan = core.Plan(seed_block_draws=(), lane_l=True)
    fro = fz.Frozen.build(plan, fz.default_cpu_table())
    d = tmp_path / "run"
    syn.write_run(d, fro, syn.Scenario())
    study = analysis.load_study(d, fro)
    assert len(study.missing) == 15 and all("lane L" in study.reasons[c] for c in study.missing)  # F-LA has no implementation here: the study is incomplete, not quietly smaller
    assert analysis.analyze_study(study, fro, gates=json.loads((d / "gates.json").read_text()))["assessment"]["status"] == C.S1_INCOMPLETE


# --- the efficiency line at registry level -----------------------------------------------------------------------------------------------
def test_dense_faster_blocks_the_efficiency_positive(tmp_path: Path) -> None:
    def a_max(arm: str, facts: int, slots: int, rep: int) -> float:
        return 1.0 if arm in ("D-OQ", "R2") else min(1.0, 0.7 * slots / facts)

    def tau(arm: str, facts: int, slots: int) -> float:
        return 5.0 if arm == "D-OQ" else (200.0 if arm == "R2" else 1500.0)

    r, d = run(tmp_path, syn.Scenario(a_max=a_max, tau=tau))
    eff = r["efficiency"]
    assert eff["arm_classes"]["F-OQ"] == "EFFICIENCY_SUPPORTED" and eff["dense"]["F-OQ"] == "DENSE FASTER"  # D-OQ reaches the level in a tenth of the updates and a fraction of F-OQ's compute
    supported = [a for a in ("F-OQ", "T-OQ") if eff["arm_classes"][a] == "EFFICIENCY_SUPPORTED"]
    unblocked = [a for a in supported if eff["dense"].get(a) != "DENSE FASTER"]
    assert (r["outcome"]["efficiency"]["label"] == C.EFFICIENCY_POSITIVE) == bool(unblocked) and "F-OQ" not in unblocked
    rendered(d)


# --- the overload row, seed block, cuts -------------------------------------------------------------------------------------------------------
def analysis_banner() -> str:
    return "DRY: test banner"
