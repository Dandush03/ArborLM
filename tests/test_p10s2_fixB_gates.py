# ruff: noqa: E501
"""P10S2 audit-fix tests, lane B: gate G9 cannot pass on an empty seed record, cannot be fooled by a mode label, covers every replicate and the +10 code seed, lists 220901-220912 and allows 220906 in the
analysis stage only (audit A M4, the lead's rulings); G7 compares files with digests recorded at creation; G4 is never "not applicable" in a registered run (audit B M8). Stand-in world and test seeds. Self-check
only: not independent review, not Astra validation, not human approval."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402
import torch  # noqa: E402
from test_p10s2_support import dry_world  # noqa: E402

from studies.p10s2 import core, gates, stages  # noqa: E402


def good_records(n: int = 2) -> list[core.SeedUse]:
    return [core.SeedUse(core.SeedPlan("registered-run", r).seed(o), f"use +{o}", "registered-run") for r in range(n) for o in (0, 1, 2, 5, 10)]


def reg_planned(n: int = 2) -> list[int]:
    return gates.planned_all("registered-run", n)


def test_g9_passes_on_a_complete_registered_record_and_lists_the_partition_seeds() -> None:
    g = gates.g9(reg_planned(), "registered-run", records=good_records(), replicates=2)
    assert g["ok"] and g["seeds"]["problems"] == [] and g["source"]["ok"]
    assert g["listed_partition_seeds"] == list(range(220901, 220913)) and g["bootstrap_seed"] == {"seed": 220906, "allowed_in_stage": "analysis"}
    assert reg_planned(4) == sorted({b + o for b in (220001, 220101, 220201, 220301) for o in range(11)})  # every replicate and the +10 code seed are planned


def test_g9_cannot_pass_on_an_empty_record_or_an_empty_plan() -> None:
    g = gates.g9(reg_planned(), "registered-run", records=[], replicates=2)
    assert not g["ok"] and any("empty seed record" in p for p in g["seeds"]["problems"])
    assert not gates.g9([], "registered-run", records=good_records())["ok"]


def test_g9_cannot_be_fooled_by_a_mode_label() -> None:
    fooled = [*good_records(), core.SeedUse(229001, "a test seed inside a registered process", "test")]
    g = gates.g9(reg_planned(), "registered-run", records=fooled, replicates=2)
    assert not g["ok"] and any("carries mode 'test'" in p for p in g["seeds"]["problems"])
    relabelled = [*good_records(), core.SeedUse(229001, "a test seed with the registered label", "registered-run")]
    g2 = gates.g9(reg_planned(), "registered-run", records=relabelled, replicates=2)
    assert not g2["ok"] and any("229001" in p for p in g2["seeds"]["problems"])  # read by its value: not a listed registered seed, not planned
    off_plan = [*good_records(), core.SeedUse(220050, "inside the registered range but not listed", "registered-run")]
    assert not gates.g9(reg_planned(), "registered-run", records=off_plan, replicates=2)["ok"]
    wrong_stage = gates.g9(reg_planned(), "registered-run", records=[core.SeedUse(221001, "calibration", "calibration")], replicates=2)
    assert not wrong_stage["ok"]


def test_g9_requires_every_replicates_draws_and_the_code_seed_and_refuses_partition_seeds_in_a_registered_run() -> None:
    no_code = [u for u in good_records() if u.seed != 220101 + 10]  # replicate 1's +10 code seed is not recorded
    g = gates.g9(reg_planned(), "registered-run", records=no_code, replicates=2)
    assert not g["ok"] and any("replicate 1" in p and "+10" in p and "code seed" in p for p in g["seeds"]["problems"])
    no_draw = [u for u in good_records() if u.seed != 220001 + 1]
    assert any("replicate 0" in p and "+1" in p for p in gates.g9(reg_planned(), "registered-run", records=no_draw, replicates=2)["seeds"]["problems"])
    for s in (220901, 220906, 220912):
        g2 = gates.g9(reg_planned(), "registered-run", records=[*good_records(), core.SeedUse(s, "partition-side", "registered-run")], replicates=2)
        assert not g2["ok"] and any(str(s) in p for p in g2["seeds"]["problems"])  # 220906 is drawn in the analysis stage and nowhere else


def test_the_analysis_stage_is_the_only_place_for_220906() -> None:
    assert gates.BOOTSTRAP_SEED == 220906 and gates.ANALYSIS_STAGE == "analysis"
    assert gates.analysis_seed_check([core.SeedUse(220906, "interval", "registered-data")])["ok"]
    assert not gates.analysis_seed_check([core.SeedUse(220001, "stage-1 store", "registered-run")])["ok"]


def test_g7_reads_digests_recorded_at_creation_and_the_stage_never_computes_them_from_the_same_files(tmp_path: Path) -> None:
    from arborlm.io import file_sha256

    (tmp_path / "a.json").write_text("{}")
    good = {"a.json": {"algo": "sha256", "digest": file_sha256(tmp_path / "a.json")}}
    (tmp_path / "manifest.json").write_text(json.dumps({"files": good}))
    assert stages.manifest_gates(tmp_path) == good and gates.g7(good, tmp_path)["ok"]
    (tmp_path / "a.json").write_text('{"changed": 1}')
    assert not gates.g7(stages.manifest_gates(tmp_path), tmp_path)["ok"]  # a changed file is caught against the digest recorded at creation (a manifest computed now would have hidden it)
    import inspect

    assert "file_sha256" not in inspect.getsource(stages.manifest_gates)


def test_g4_is_never_not_applicable_in_a_registered_run() -> None:
    world, _ = dry_world()
    plan = core.SeedPlan("test", 0)
    reg = gates.g4(world, plan, 2, require_mps=True)  # the stand-in world trains on CPU: a registered process on CPU fails G4
    assert not reg["ok"] and reg["mps_agreement"]["ok"] is False and "mandatory" in reg["mps_agreement"]["status"] and reg["repeated_updates"] == 2
    dry = gates.g4(world, plan, 2)
    assert dry["ok"] and dry["mps_agreement"]["ok"] and "dry stage and tests only" in dry["mps_agreement"]["status"]


@pytest.mark.skipif(not torch.backends.mps.is_available(), reason="MPS is not available on this machine")
def test_g4_compares_mps_with_cpu_where_the_frozen_device_is_mps() -> None:
    import dataclasses

    world, _ = dry_world()
    g = gates.g4(dataclasses.replace(world, device=torch.device("mps")), core.SeedPlan("test", 0), 3, require_mps=True)
    assert "max_loss_difference" in g["mps_agreement"] and g["repeated_updates_bit_identical"]
    assert all(p.device.type == "cpu" for p in world.student.parameters())  # the student is back on CPU: every score is computed on CPU


def test_record_code_seeds_records_the_plus_10_seed_of_every_replicate() -> None:
    core.reset_seed_record()
    gates.record_code_seeds(3, "test")
    assert [u.seed for u in core.seed_record()] == [core.SeedPlan("test", r).seed(10) for r in range(3)]
    core.reset_seed_record()
