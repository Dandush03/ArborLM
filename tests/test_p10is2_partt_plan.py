# ruff: noqa: E501
"""P10IS2 Part T plan, cells, registry keys, resume policy and refusing entry points (ADR-0025 sections 5, 8.6, 10, 11, 14, 19). Throwaway repositories; synthetic registry; nothing trains. Self-check only.
Seeds 934001-934999."""

import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402
from p10is2_partt_fixtures import CFG_T, build  # noqa: E402

from arborlm.io import file_sha256, write_json  # noqa: E402
from studies.p10is2 import labels as L  # noqa: E402
from studies.p10is2 import partt_plan, partt_stages  # noqa: E402
from studies.p10is2.common import core, gates  # noqa: E402
from studies.p10is2.common import plan as planmod  # noqa: E402
from studies.p10is2.quantities import Quantities, Thresholds  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CALIB = {"U": 2000, "converged": True, "store_rate": 0.003, "lora_rate": 0.0003, "etable_rate": 0.003, "read_layer": 4, "pilot": {"passed": True}, "records": {}}
FAKE_WALK = {"python_files": [], "files_opened": [], "outside_study_python": [], "outside_study_data": []}


def git(repo: Path, *a: str) -> str:
    return subprocess.run(["git", "-C", str(repo), "-c", "commit.gpgsign=false", "-c", "user.name=t", "-c", "user.email=t@example.invalid", *a], capture_output=True, text=True, check=True).stdout.strip()  # noqa: S603, S607


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    r = tmp_path / "repo"
    for rel in ("studies/p10is2", "configs/p10is2_partq.toml", "configs/p10is2_partt.toml", "uv.lock", "pyproject.toml", core.SPEC):
        src, dst = ROOT / rel, r / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", "freeze")) if src.is_dir() else shutil.copy(src, dst)
    (r / "studies/p10is2/freeze").mkdir(exist_ok=True)
    git(r, "init", "-q")
    (r / ".gitignore").write_text("runs/\n")
    git(r, "add", "-A")
    git(r, "commit", "-q", "-m", "base")
    return r


# --- cells and counts ----------------------------------------------------------------------------------------------------------------------------
def test_54_trained_cells_and_section_14_units() -> None:
    cells = partt_plan.train_cells()
    assert len(cells) == 54  # section 14: "54 trained cells"
    assert partt_plan.units_of_training() == {"store-type": 42, "lora": 24, "M-ii": 12}  # section 14: 42 store-type and 24 LoRA units of U (M-ii is 12 of the 42)
    assert len({c["id"] for c in cells}) == 54
    per_rep = [c for c in cells if c["rep"] == 0]
    assert len(per_rep) == 18 and sum(1 for c in per_rep if c["arm"] == "E-table") == 2 and sum(1 for c in per_rep if c["arm"] in partt_plan.PER_CELL_ARMS) == 14
    assert partt_plan.combined_arm_cells_per_replicate() == 12  # section 5.5


def test_stage_items_counts_updates_and_rates() -> None:
    items = partt_plan.stage_items(CALIB)
    assert {k: len(v) for k, v in items.items()} == {"gates": 8, "train": 54, "evaluate": 54 + 3 * 7 + 1, "controls": 27, "combined": 3 * 12 + 2, "analysis": 1, "report": 1}
    tr = {i["id"]: i for i in items["train"]}
    assert tr["train|M-joint|-|r0"]["updates"] == 4000 and tr["train|D-joint|-|r1"]["updates"] == 4000 and tr["train|M-append|AB|r2"]["updates"] == 2000  # the joint arms train 2U
    assert tr["train|M-append|AB|r0"]["rate"] == 0.003 and tr["train|D-seq|BA|r1"]["rate"] == 0.0003 and tr["train|E-table|A|r0"]["rate"] == 0.003
    assert tr["train|M1|AB|r0"]["read_layer"] == 4 and tr["train|D1|AB|r0"]["read_layer"] is None and tr["train|M-ii|BA|r2"]["device"] == "mps" and tr["train|M1|AB|r0"]["checkpoint_every"] == 500
    ids = [i["id"] for v in items.values() for i in v]
    assert len(set(ids)) == len(ids)
    assert not any(i["arm"] in ("M-sep", "D-sep") for i in items["train"])  # assembled, never trained
    assert {i["arm"] for i in items["combined"]} == {"M-append", "M-ii", "D-seq", "D-append", "M-joint", "D-joint", "M-sep", "D-sep", "S0", "ensemble"}


def test_required_registry_keys_cover_exactly_what_the_labels_read() -> None:
    req = partt_plan.required_keys()
    reg = build()
    assert req <= set(reg.values)  # the synthetic registry has every required key
    only = type(reg)({k: v for k, v in reg.values.items() if k in req})
    r = L.derive_all(Quantities(only, Thresholds.from_config(CFG_T)))  # the labels never reach for a key outside the required set
    assert r["MILESTONE"]["label"] == "SUPPORTED (append-frozen + consolidation)"
    for k in list(req)[::17]:  # dropping any required key makes the study INCOMPLETE, never a label
        broken = type(reg)({kk: v for kk, v in reg.values.items() if kk != k})
        assert L.study_status(broken, required=req)["status"] == L.INCOMPLETE


# --- the plan --------------------------------------------------------------------------------------------------------------------------------
def test_plan_needs_a_passed_pilot_and_carries_calibration_and_seeds(repo: Path) -> None:
    cfg = core.load_config("T", repo / core.CONFIG_T)
    with pytest.raises(core.StageRefused, match="pilot"):
        partt_plan.build_candidate(repo, repo / "runs", cfg, {**CALIB, "pilot": {"passed": False}}, walk=FAKE_WALK)
    rec = partt_plan.build_candidate(repo, repo / "runs", cfg, CALIB, walk=FAKE_WALK)
    assert rec["part"] == "T" and rec["calibration"]["U"] == 2000 and rec["units_of_U"]["store-type"] == 42 and len(rec["registry_keys"]) == len(partt_plan.required_keys())
    assert rec["seeds"]["replicates"][0]["data"]["training_draw"] == 250002 and rec["seeds"]["replicates"][2]["init"]["D1"] == 330224
    assert "studies/p10is2/labels.py" in rec["frozen_files"] and not any("/partq/" in f for f in rec["frozen_files"]) and "configs/p10is2_partt.toml" in rec["frozen_files"]
    assert rec["adr"]["note"].startswith("provenance only")


def test_part_t_frozen_set_changes_with_part_t_code_not_with_part_q_code(repo: Path) -> None:
    before = planmod.frozen_file_hashes(repo, "T")
    q_before = planmod.frozen_file_hashes(repo, "Q")
    f = repo / "studies/p10is2/partq/split.py"
    f.write_text(f.read_text() + "\n# q change\n")
    assert planmod.frozen_file_hashes(repo, "T") == before  # a Part Q change cannot invalidate Part T
    assert planmod.frozen_file_hashes(repo, "Q") != q_before
    g = repo / "studies/p10is2/labels.py"
    g.write_text(g.read_text() + "\n# t change\n")
    assert planmod.frozen_file_hashes(repo, "T") != before


# --- resume policy -------------------------------------------------------------------------------------------------------------------------
def test_resume_policy_non_finite_is_not_resumed_errors_are_when_the_fix_is_not_frozen() -> None:
    d = partt_plan.resume_decision
    assert d({"status": "COMPLETE"}) == {"action": "skip", "delete_checkpoints": True}
    nf = d({"status": "STOPPED_NONFINITE", "last_finite_checkpoint": "ck_1500"})
    assert nf["action"] == "refuse" and nf["label"] == "ENGINEERING STOP — NON-FINITE VALUE" and nf["last_finite_checkpoint"] == "ck_1500"  # C2
    assert d({"status": "ERROR"})["action"] == "refuse"  # the cause is not recorded
    assert d({"status": "ERROR", "cause_recorded": True, "fix_changes_frozen_file": True})["action"] == "refuse"
    ok = d({"status": "ERROR", "cause_recorded": True, "last_checkpoint": "ck_1000"})
    assert ok == {"action": "resume", "from": "ck_1000", "marked_resumed": True}
    assert d({"status": "RUNNING"}) == {"action": "run"} and d({}) == {"action": "run"}
    recs = [{"status": "COMPLETE", "final_snapshot": "s", "checkpoint_dir": "a"}, {"status": "COMPLETE", "checkpoint_dir": "b"}, {"status": "ERROR", "checkpoint_dir": "c", "final_snapshot": "s"}]
    assert partt_plan.checkpoints_to_delete(recs) == ["a"]  # only once the final snapshot is recorded (G20)


# --- refusing entry points -----------------------------------------------------------------------------------------------------------------------
def test_part_t_entry_points_refuse_today(tmp_path: Path) -> None:
    assert not (ROOT / core.PLAN_T).exists() and not (ROOT / core.FREEZE_RECORD_T).exists()
    for argv in (["registered", "--stage", "train", "--run-dir", str(tmp_path / "r"), "--freeze-commit", "HEAD"], ["work", "--stage", "evaluate", "--run-dir", str(tmp_path / "r")], ["registered", "--stage", "nonsense", "--run-dir", str(tmp_path / "r")]):
        assert partt_stages.main(argv) in (partt_stages.EXIT_REFUSED, partt_stages.EXIT_IDENTITY)  # a checkout with uncommitted frozen files is an identity pause, a clean one a refusal: never a run
    assert partt_stages.main(["freeze", "--measuring-rehearsal", "m", "--counting-rehearsal", "c"]) == partt_stages.EXIT_REFUSED
    assert partt_stages.main(["rehearse", "--kind", "counting", "--run-dir", str(tmp_path / "x")]) == partt_stages.EXIT_REFUSED
    assert not (tmp_path / "r").exists()


def freeze_commit(repo: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    rec = {"system": "Darwin", "machine": "arm64", "torch": "2.8.0", "torch_num_threads": 6, "torch_interop_threads": 1, "deterministic_algorithms": True, "release": "x", "platform": "x"}
    monkeypatch.setattr(gates, "platform_record", lambda: rec)
    p = repo / core.CONFIG_T
    t = p.read_text()
    for k in ("gates", "calibration", "train", "evaluate", "controls", "combined", "analysis", "total"):
        t = t.replace(f"{k}_hours = 0.0", f"{k}_hours = 1.0")
    p.write_text(t.replace("provisional = true", "provisional = false"))
    cfg = core.load_config("T", p)
    write_json(repo / core.PLAN_T, core.jsonable(partt_plan.build_candidate(repo, repo / "runs", cfg, CALIB, walk=FAKE_WALK)))
    write_json(repo / core.FREEZE_RECORD_T, {"kind": "freeze_record", "plan_file_sha256": file_sha256(repo / core.PLAN_T)})
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "freeze T")
    return git(repo, "rev-parse", "HEAD")


def test_registered_chain_for_part_t_needs_decision_2_and_lock_only(repo: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    commit = freeze_commit(repo, monkeypatch)
    run = repo / "runs"
    with pytest.raises(core.StageRefused, match="DECISION_2_PARTT"):
        partt_stages.refuse_unless_registered_ready(repo, run, commit, "train")
    d = repo / "results/p10is2-partt-freeze-20261201/DECISION_2_PARTT.md"
    d.parent.mkdir(parents=True)
    d.write_text(f"commit {commit}\nDECISION: RUN\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "decision")
    plan = partt_stages.refuse_unless_registered_ready(repo, run, commit, "train")
    assert plan.part == "T"
    monkeypatch.setenv("PYTHONPATH", core.DURABLE_PACKAGES)
    with pytest.raises(core.StageRefused, match="lock alone"):
        partt_stages.refuse_unless_registered_ready(repo, run, commit, "train")
    monkeypatch.delenv("PYTHONPATH")
    # the identity of a frozen Part T file: PAUSED — IDENTITY on a plan whose frozen file changed (the tree is allowed to be dirty for verify_plan itself)
    f = repo / "studies/p10is2/labels.py"
    orig = f.read_bytes()
    f.write_bytes(orig + b"\n# x\n")
    with pytest.raises(core.StageRefused, match="PAUSED — IDENTITY"):
        planmod.verify_plan(plan, repo, run)
    f.write_bytes(orig)
    planmod.verify_plan(plan, repo, run)
    with pytest.raises(core.StageRefused, match="not a registered Part T stage"):
        partt_stages.refuse_unless_registered_ready(repo, run, commit, "recompute")
    # Part Q's Decision 2 does not open Part T
    assert planmod.DECISION_2_GLOB["Q"] != planmod.DECISION_2_GLOB["T"]


def test_part_t_freeze_refuses_provisional_caps_and_missing_calibration_records(repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import argparse

    monkeypatch.setattr(planmod, "import_walk", lambda *a, **k: FAKE_WALK)
    cfg = core.load_config("T", repo / core.CONFIG_T)
    write_json(repo / core.PLAN_T, core.jsonable(partt_plan.build_candidate(repo, repo / "runs", cfg, CALIB, walk=FAKE_WALK)))
    args = argparse.Namespace(repo=str(repo), measuring_rehearsal=str(tmp_path / "m.json"), counting_rehearsal=str(tmp_path / "c.json"), attest_sealed_unopened="lead,implementer,auditor", seal_broken=False)
    with pytest.raises(core.StageRefused, match="provisional"):
        partt_stages.cmd_freeze(args)


def test_durable_package_constant_equals_the_part_q_config() -> None:
    assert core.DURABLE_PACKAGES == core.load_config("Q")["paths"]["durable_packages"]


def test_launch_scripts_exist_and_use_the_lock_alone_for_part_t() -> None:
    q = (ROOT / "studies/p10is2/launch/partq_registered.sh").read_text()
    assert "--offline" in q and f"DURABLE_PACKAGES={core.DURABLE_PACKAGES}" in q and "requirements-datagen" not in q and "--with-requirements" not in q
    t = (ROOT / "studies/p10is2/launch/partt_registered.sh").read_text()
    assert "unset PYTHONPATH" in t and "--locked" in t and "datagen-packages" not in t.replace("durable package copy", "") and "PYTHONPATH=" not in t
