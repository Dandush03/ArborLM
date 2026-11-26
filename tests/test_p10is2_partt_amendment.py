# ruff: noqa: E501
"""P10IS2 Part T cap amendment (ruling 51, studies/p10is2/partt_amendment/AMENDMENT_NOTES.md): amended caps, the exemption from the calibration comparison, the plan and config difference checks, the targeted rehearsal's gate,
the one-at-a-time M-ii wave, the charged-time cap and the admission check. CPU only, tiny. Self-check only."""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402

from studies.p10is2 import calibration as cal  # noqa: E402
from studies.p10is2 import partt_amendment as am  # noqa: E402
from studies.p10is2 import partt_caps, partt_targeted, partt_tasks  # noqa: E402
from studies.p10is2.common import core, runner  # noqa: E402
from studies.p10is2.common import plan as planmod  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
NEW_FILES = ["studies/p10is2/partt_amendment/__init__.py", "studies/p10is2/partt_targeted.py"]


def write_record(repo: Path, **over: Any) -> dict[str, Any]:
    rec = {"kind": am.KIND, "ruling": 51, "stage_cap_keys": ["train_hours", "combined_hours"], "first_freeze_commit": "a" * 40, "pre_amendment_plan_sha256": "b" * 64, "allowed_config_paths": [".caps.study_budget_hours"], "exempt_files": ["studies/p10is2/partt_caps.py", *NEW_FILES]} | over
    p = repo / "rec.json"
    p.write_text(json.dumps(rec))
    return rec


CFG = {"cap_amendment": {"record": "rec.json", "train_hours": 125.8, "combined_hours": 6.0, "targeted_allowance_hours": 3.0}}


def test_the_real_config_amendment_loads_and_its_record_names_exactly_its_keys() -> None:
    cfg = core.load_config("T")
    a = am.load(cfg, ROOT)
    assert a is not None and set(a["caps"]) == {"train_hours", "combined_hours"} and a["allowance_hours"] == 3.0 and a["first_freeze_commit"] == "c25d4f0b1d0ff5f529072cc7983c835a0267e2fb"
    assert not set(a["exempt_files"]) & set(am.PROTECTED) and "studies/p10is2/partt_amendment/__init__.py" in a["exempt_files"]
    assert float(cfg["caps"]["study_budget_hours"]) == 205.0  # the bound is ONE key
    assert core.load_config("T")["caps"]["single_worker_arms"] == ["M-ii"] and cfg["caps"]["workers_max_single_arm"] == 1


def test_an_amendment_is_accepted_only_when_the_record_names_it(tmp_path: Path) -> None:
    assert am.load({}, tmp_path) is None  # no section: nothing changes
    with pytest.raises(core.StageRefused, match="does not exist"):
        am.load(CFG, tmp_path)
    write_record(tmp_path)
    assert am.load(CFG, tmp_path)["caps"] == {"train_hours": 125.8, "combined_hours": 6.0}
    write_record(tmp_path, stage_cap_keys=["train_hours"])
    with pytest.raises(core.StageRefused, match="not the keys the amendment record names"):
        am.load(CFG, tmp_path)
    write_record(tmp_path, exempt_files=["studies/p10is2/engine.py"])
    with pytest.raises(core.StageRefused, match="may not be exempt"):
        am.load(CFG, tmp_path)
    write_record(tmp_path)
    with pytest.raises(core.StageRefused, match="not registered stage caps"):
        am.load({"cap_amendment": {**CFG["cap_amendment"], "recompute_hours": 1.0, "nonsense_hours": 2.0}}, tmp_path)


def test_the_amended_proposal_replaces_the_stage_caps_and_recomputes_the_total() -> None:
    proposal = {"gates_hours": 0.54, "train_hours": 75.68, "evaluate_hours": 21.77, "controls_hours": 0.01, "combined_hours": 1.63, "recompute_hours": 22.66, "analysis_hours": 0.01, "report_hours": 0.01, "total_hours": 150.17}
    assert am.apply(proposal, None, 1.0, 1.0) == proposal
    a = {"caps": {"train_hours": 125.8, "combined_hours": 6.0}}
    out = am.apply(proposal, a, 87_178.16, 3.0 * 3600.0)
    assert out["train_hours"] == 125.8 and out["combined_hours"] == 6.0 and out["evaluate_hours"] == 21.77
    assert out["total_hours"] == pytest.approx(204.02, abs=0.011)  # 24.216 + 3.0 + 51.0 + 125.8, rounded up to 0.01 h: under the bound of 205 h
    assert out["total_hours"] <= 205.0


def test_proposal_from_record_applies_the_amendment_and_is_unchanged_without_one(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(partt_caps, "project_stage_seconds", lambda *a, **k: {"train": 36000.0, "combined": 1000.0})
    meas = {"caps_formula": partt_caps.CAPS_FORMULA, "rates_seconds_per_unit": {}, "overhead_seconds": {}}
    plain = partt_caps.proposal_from_record(meas, {}, {}, 3600.0, 0.0)
    assert plain["train_hours"] == 20.0 and plain["combined_hours"] == pytest.approx(0.56, abs=0.01)  # 2 x the projection
    amended = partt_caps.proposal_from_record(meas, {}, {}, 3600.0, 0.0, {"caps": {"train_hours": 30.0}})
    assert amended["train_hours"] == 30.0 and amended["combined_hours"] == plain["combined_hours"] and amended["total_hours"] == pytest.approx(1.0 + 30.0 + plain["combined_hours"], abs=0.02)


def test_the_exemption_covers_the_named_files_only_and_the_calibration_comparison_still_checks_the_rest() -> None:
    now = {"studies/p10is2/partt_caps.py": "n1", "studies/p10is2/engine.py": "e1", NEW_FILES[0]: "n2"}
    files = list(now)
    record = {"code_hashes": {"studies/p10is2/partt_caps.py": "old", "studies/p10is2/engine.py": "e1"}}  # the new module did not exist at calibration; partt_caps.py differs
    assert cal.code_identity_problems(record, now, files) != []
    a = {"exempt_files": ["studies/p10is2/partt_caps.py", NEW_FILES[0]]}
    assert cal.code_identity_problems(record, now, am.checked_files(files, a)) == []
    changed = {"code_hashes": {"studies/p10is2/partt_caps.py": "old", "studies/p10is2/engine.py": "other"}}  # a training file differs: never exempt
    assert cal.code_identity_problems(changed, now, am.checked_files(files, a)) != []


def test_the_plan_must_name_the_amendment_record_by_its_hash(tmp_path: Path) -> None:
    write_record(tmp_path)
    a = am.load(CFG, tmp_path)
    assert a is not None
    good = {"cap_amendment_record": {"path": "rec.json", "sha256": a["record"]["sha256"]}}
    assert am.manifest_problem(good, a, tmp_path) is None and am.manifest_problem({}, a, tmp_path) is not None and am.manifest_problem(None, None, tmp_path) is None
    assert am.manifest_problem({"cap_amendment_record": {"path": "rec.json", "sha256": "0" * 64}}, a, tmp_path) is not None


A = {"caps": {"train_hours": 125.8, "combined_hours": 6.0}, "exempt_files": ["studies/p10is2/partt_caps.py"], "allowed_config_paths": [".caps.study_budget_hours"]}


def base_plan() -> dict[str, Any]:
    return {"config_sha256": "c0", "counting_allowance_hours": 18.26, "charge_before_freeze": {"seconds": 1.0, "ledgers": {"x": 1.0}}, "manifests": {"panel_ledger": {"path": "p", "sha256": "s"}}, "stage_caps": {"train_hours": 75.68, "combined_hours": 1.63, "total_hours": 150.17, "evaluate_hours": 21.77},
            "frozen_files": {"configs/p10is2_partt.toml": "h1", "studies/p10is2/partt_caps.py": "h2", "studies/p10is2/engine.py": "h3"}, "import_walk": {"python_files": ["a.py"], "files_opened": ["a.py"]}, "items": {"train": [{"id": "x"}]}, "calibration": {"U": 8000}, "seeds": {"replicates": [1]}}


def amended_plan() -> dict[str, Any]:
    p = json.loads(json.dumps(base_plan()))
    p["config_sha256"] = "c1"
    p["counting_allowance_hours"] = 3.0
    p["charge_before_freeze"] = {"seconds": 9.0, "ledgers": {"x": 1.0, "y": 8.0}}
    p["manifests"]["cap_amendment_record"] = {"path": "r", "sha256": "z"}
    p["stage_caps"] |= {"train_hours": 125.8, "combined_hours": 6.0, "total_hours": 204.02}
    p["frozen_files"] |= {"configs/p10is2_partt.toml": "h1b", "studies/p10is2/partt_caps.py": "h2b", "studies/p10is2/partt_amendment/__init__.py": "n"}
    p["import_walk"] = {"python_files": ["a.py", "studies/p10is2/partt_amendment/__init__.py"], "files_opened": ["a.py", "studies/p10is2/partt_amendment/__init__.py"]}
    return p


def test_the_amended_plan_may_differ_from_the_first_only_in_the_listed_places() -> None:
    assert am.plan_diff_problems(base_plan(), amended_plan(), A) == []
    for mutate, expect in (
        (lambda p: p["items"]["train"].append({"id": "y"}), ".items.train"),
        (lambda p: p["calibration"].update(U=4000), ".calibration.U"),
        (lambda p: p["seeds"].update(replicates=[2]), ".seeds.replicates"),
        (lambda p: p["stage_caps"].update(evaluate_hours=99.0), ".stage_caps.evaluate_hours"),
        (lambda p: p["frozen_files"].update({"studies/p10is2/engine.py": "other"}), ".frozen_files.studies/p10is2/engine.py"),
        (lambda p: p["import_walk"]["python_files"].append("studies/p10s2/other.py"), ".import_walk.python_files"),
    ):
        p = amended_plan()
        mutate(p)
        assert expect in am.plan_diff_problems(base_plan(), p, A), expect


def test_the_config_may_differ_from_the_first_freezes_only_at_the_listed_paths() -> None:
    old = {"caps": {"study_budget_hours": 151.0, "workers_max": 3}, "stage_caps": {"train_hours": 75.68, "total_hours": 150.17, "evaluate_hours": 21.77}, "rehearsal": {"updates": 200}}
    new = {"caps": {"study_budget_hours": 205.0, "workers_max": 3}, "stage_caps": {"train_hours": 125.8, "total_hours": 204.02, "evaluate_hours": 21.77}, "rehearsal": {"updates": 200}, "cap_amendment": {"record": "r", "train_hours": 125.8}}
    assert am.config_diff_problems(old, new, A) == []
    new["rehearsal"]["updates"] = 100
    new["caps"]["workers_max"] = 4
    assert sorted(am.config_diff_problems(old, new, A)) == [".caps.workers_max", ".rehearsal.updates"]


def test_the_freeze_reads_the_first_freezes_plan_and_config_from_version_control(tmp_path: Path) -> None:
    def g(*a: str) -> str:
        return subprocess.run(["git", "-C", str(tmp_path), "-c", "commit.gpgsign=false", "-c", "user.name=t", "-c", "user.email=t@example.invalid", *a], capture_output=True, text=True, check=True).stdout.strip()  # noqa: S603, S607

    g("init", "-q")
    (tmp_path / "studies/p10is2/freeze").mkdir(parents=True)
    (tmp_path / "configs").mkdir()
    plan_bytes = json.dumps(base_plan()).encode()
    (tmp_path / "studies/p10is2/freeze/partt_plan.json").write_bytes(plan_bytes)
    (tmp_path / "configs/p10is2_partt.toml").write_text('[caps]\nstudy_budget_hours = 151.0\n[stage_caps]\ntrain_hours = 75.68\ntotal_hours = 150.17\nevaluate_hours = 21.77\n')
    g("add", "-A")
    g("commit", "-q", "-m", "first freeze")
    commit = g("rev-parse", "HEAD")
    import hashlib

    a = {**A, "first_freeze_commit": commit, "pre_amendment_plan_sha256": hashlib.sha256(plan_bytes).hexdigest()}
    cfg = {"caps": {"study_budget_hours": 205.0}, "stage_caps": {"train_hours": 125.8, "total_hours": 204.02, "evaluate_hours": 21.77}, "cap_amendment": {"record": "r"}}
    assert am.freeze_problems(tmp_path, cfg, amended_plan(), a) == []
    assert am.freeze_problems(tmp_path, cfg, amended_plan(), {**a, "pre_amendment_plan_sha256": "0" * 64}) != []
    bad = amended_plan()
    bad["items"]["train"].append({"id": "y"})
    assert any("plan differs at .items.train" in p for p in am.freeze_problems(tmp_path, cfg, bad, a))
    assert any("config differs at .stage_caps.evaluate_hours" in p for p in am.freeze_problems(tmp_path, {**cfg, "stage_caps": {**cfg["stage_caps"], "evaluate_hours": 1.0}}, amended_plan(), a))
    assert am.freeze_problems(tmp_path, cfg, amended_plan(), {**a, "first_freeze_commit": ""}) == ["the amendment record names no first freeze commit"]


def test_the_targeted_rehearsals_record_gates_the_freeze() -> None:
    ok = {"kind_of_rehearsal": "targeted", "status": "COMPLETE", "plan_file_sha256": "p", "caps_provisional": False, "checks": {c: {"passed": True} for c in am.REQUIRED_CHECKS}}
    assert am.targeted_gate(ok, "p")["passed"] is True
    assert am.targeted_gate(None, "p")["passed"] is False and am.targeted_gate(ok, "q")["passed"] is False
    assert am.targeted_gate({**ok, "status": "INCOMPLETE"}, "p")["passed"] is False and am.targeted_gate({**ok, "kind_of_rehearsal": "counting"}, "p")["passed"] is False
    broken = {**ok, "checks": {**ok["checks"], "memory_admission_refused_once": {"passed": False}}}
    assert am.targeted_gate(broken, "p")["failed_checks"] == ["memory_admission_refused_once"]


def a_train_plan() -> planmod.Plan:
    items = [{"id": f"train|{arm}|AB|r0", "stage": "train", "arm": arm, "order": "AB", "rep": 0} for arm in ("M1", "M-append", "M-ii", "D1")]
    return planmod.Plan({"kind": "freeze_plan", "study": core.STUDY, "schema": core.SCHEMA, "part": "T", "items": {"train": items}, "stage_caps": {}}, "T")


def test_the_m_ii_wave_runs_one_worker_and_a_rehearsal_can_train_named_arms_only() -> None:
    cfg = core.load_config("T")
    pol = partt_tasks.worker_policy(cfg, False)
    waves = partt_tasks.waves_of("train", a_train_plan())
    assert [[i["arm"] for i in w] for w in waves] == [["M1", "D1"], ["M-append"], ["M-ii"]]
    assert [partt_tasks.wave_workers(cfg, w, pol) for w in waves] == [3, 3, 1]  # only the M-ii wave is limited
    assert partt_tasks.wave_workers({"caps": {"workers_max": 3, "workers_max_shared": 2}}, waves[2], pol) == 3  # no key, no limit
    named = partt_tasks.waves_of("train", a_train_plan(), False, ["M1", "M-append"])
    assert [[i["arm"] for i in w] for w in named] == [["M1"], ["M-append"], []]


def test_the_runner_compares_the_cap_with_charged_time_and_holds_a_worker_for_memory(tmp_path: Path) -> None:
    cap, adm = partt_targeted.cap_and_admission_checks(tmp_path)
    assert cap["passed"] is True and set(cap["statuses"].values()) == {runner.KILLED_CAP} and cap["wall_seconds"] < partt_targeted.TINY_SECONDS  # two 3 s workers are stopped inside 1.5 s of charged time, not after 3 s of wall clock
    assert adm["passed"] is True and adm["second_started_after_first_ended"] is True


def test_one_worker_under_a_cap_is_stopped_at_its_charged_time_as_before(tmp_path: Path) -> None:
    out, wall = runner.run_tasks(partt_targeted.tiny_tasks(tmp_path, 1, 3.0), workers=1, cap_seconds=1.0, rss_worker_bytes=2**30, rss_aggregate_bytes=2**31, poll=0.05)
    assert out["tiny0"]["status"] == runner.KILLED_CAP and wall < 2.5
    out2, _ = runner.run_tasks(partt_targeted.tiny_tasks(tmp_path / "b", 1, 0.3), workers=1, cap_seconds=30.0, rss_worker_bytes=2**30, rss_aggregate_bytes=2**31, poll=0.05)
    assert out2["tiny0"]["status"] == runner.COMPLETED


def test_the_admission_threshold_follows_system_memory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(runner, "free_memory_bytes", lambda: 10)
    out, _ = runner.run_tasks(partt_targeted.tiny_tasks(tmp_path / "x", 2, 0.5), workers=2, cap_seconds=30.0, rss_worker_bytes=2**30, rss_aggregate_bytes=2**31, poll=0.05, admit_free_bytes=1000)
    t = sorted(json.loads((tmp_path / "x" / f"t{i}.result.json").read_text())["t"] for i in range(2))
    assert {v["status"] for v in out.values()} == {runner.COMPLETED} and t[1] - t[0] >= 0.45  # held: sequential
    monkeypatch.setattr(runner, "free_memory_bytes", lambda: 2**60)
    runner.run_tasks(partt_targeted.tiny_tasks(tmp_path / "y", 2, 0.5), workers=2, cap_seconds=30.0, rss_worker_bytes=2**30, rss_aggregate_bytes=2**31, poll=0.05, admit_free_bytes=1000)
    t2 = sorted(json.loads((tmp_path / "y" / f"t{i}.result.json").read_text())["t"] for i in range(2))
    assert t2[1] - t2[0] < 0.3  # admitted: concurrent
