# ruff: noqa: E501
"""P10IS2 Part T: the study budget bound raised to 151 h by the human lead (docs/decisions/ADR-0025-addendum-part-t-budget-bound.md, ruling 46) and its carrier. Self-check only."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402
from test_p10is2_partt_plan import CALIB, FAKE_WALK, repo  # noqa: E402, F401

from arborlm.io import file_sha256, write_json  # noqa: E402
from studies.p10is2 import calibration as cal  # noqa: E402
from studies.p10is2 import partt_plan, partt_stages  # noqa: E402
from studies.p10is2.common import core  # noqa: E402
from studies.p10is2.common import plan as planmod  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / "results/p10is2-partt-budget-bound-20261121"
APPROVAL_SHA = "2dd7aa9012e9c699714c3544ef6fa9a0c803e228ecf514085768aeeb5f39148e"


def entry() -> dict[str, object]:
    return json.loads((DIR / "manifest_entry.json").read_text())["budget_bound_approval"]  # type: ignore[no-any-return]


def test_the_config_holds_151_the_approval_says_151_and_the_entry_agrees() -> None:
    cfg = core.load_config("T")
    text = (DIR / "APPROVAL.md").read_text()
    e = entry()
    assert float(cfg["caps"]["study_budget_hours"]) == 205.0 and e["approved_bound_hours"] == 151.0  # ruling 51 raised the bound to 205 after the 151 h of ruling 46 (the approval record and its entry are history)
    assert e["registered_bound_hours"] == 95.68
    assert "Raise to 151 h" in text and "95.68" in text and "151 h" in text and "Astra review: NOT_PERFORMED" in text
    assert "No rule, threshold, grid, seed, cell count, U, padding factor or stage-cap rule changes" in text and "Calibration is not repeated" in text
    assert file_sha256(DIR / "APPROVAL.md") == APPROVAL_SHA == e["sha256"] and e["path"] == "results/p10is2-partt-budget-bound-20261121/APPROVAL.md"


def test_the_bound_still_refuses_a_total_above_it_and_passes_the_plans_total() -> None:
    cfg = core.load_config("T")
    partt_stages.check_study_budget(cfg, 204.02, 3.0)  # the amended plan's total cap fits
    partt_stages.check_study_budget(cfg, 205.0, 3.0)  # equal passes
    with pytest.raises(core.StageRefused, match="exceeds the study's budget bound 205.0 h"):
        partt_stages.check_study_budget(cfg, 205.01, 3.0)  # ruling 33's check is unchanged


def test_the_calibration_records_validity_check_ignores_the_config_key_the_bound_lives_in() -> None:
    """The plan and the freeze check a calibration record's hashes of the frozen studies/p10is2/*.py only: a record whose config hash differs (the bound edited after calibration) stays valid; a changed .py file does not."""
    now = planmod.frozen_file_hashes(ROOT, "T")
    files = [f for f in now if f.startswith("studies/p10is2/") and f.endswith(".py")]
    assert files and "configs/p10is2_partt.toml" in now
    record = {"code_hashes": {**now, "configs/p10is2_partt.toml": "0" * 64}}  # the config as it was at calibration
    assert cal.code_identity_problems(record, now, files) == []
    stale = {"code_hashes": {**now, files[0]: "0" * 64}}
    assert cal.code_identity_problems(stale, now, files) != []


def test_the_plan_records_the_approval_and_both_numbers_and_every_registered_stage_rehashes_it(repo: Path, tmp_path: Path) -> None:  # noqa: F811
    cfg = core.load_config("T", repo / core.CONFIG_T)
    approval = repo / "results/p10is2-partt-budget-bound-20261121/APPROVAL.md"
    approval.parent.mkdir(parents=True)
    approval.write_text((DIR / "APPROVAL.md").read_text())
    manifests = {"budget_bound_approval": {**entry(), "sha256": file_sha256(approval)}}
    rec = partt_plan.build_candidate(repo, repo / "runs", cfg, CALIB, walk=FAKE_WALK, manifests=manifests)
    got = rec["manifests"]["budget_bound_approval"]
    assert got["registered_bound_hours"] == 95.68 and got["approved_bound_hours"] == 151.0 and got["sha256"] == file_sha256(approval) and got["path"].endswith("APPROVAL.md")
    path = repo / "plan.json"
    write_json(path, core.jsonable(rec))
    plan = planmod.Plan.load(path, "T")
    planmod.verify_plan(plan, repo, repo / "runs", candidate=True)  # holds
    approval.write_text(approval.read_text() + "\nedited\n")
    with pytest.raises(core.StageRefused, match="does not hash to the frozen manifest budget_bound_approval"):
        planmod.verify_plan(plan, repo, repo / "runs", candidate=True)  # PAUSED - IDENTITY: the approval record is hash-pinned by the plan
