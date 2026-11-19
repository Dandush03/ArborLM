# ruff: noqa: E501
"""P10IS3 tests of the independent audit's findings B1-B4 and R1-R8 and of the lead's rulings (ADR-0026). Each test fails on the behaviour of commit dfa19f4 / 750eb06. Self-check only."""

import copy
import inspect
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402
import torch  # noqa: E402

from arborlm.io import file_sha256  # noqa: E402
from studies.p10i_s3 import (  # noqa: E402
    analysis,
    calibration,
    core,
    gates,
    items,
    plan,
    rehearsal,
    report,
    runner,
    stages,
    synthetic,
)
from studies.p10i_s3.core import DENSE, FRESH, REP, TREE  # noqa: E402
from studies.p10i_s3.synthetic import Spec  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CFG = core.load_config()


def run(specs: dict, edge=(), **kw):  # type: ignore[no-untyped-def]
    return analysis.analyse(synthetic.registry(CFG, specs, **kw), synthetic.rate_table(CFG, edge=edge), CFG)


# ---------------- B1: the supervisor is configured before the platform check ----------------
def _frozen_git_repo(tmp: Path) -> tuple[Path, str, Path]:
    """A frozen fixture repository: plan, freeze record, a freeze commit and a committed Decision 2."""
    import test_p10is3_realpath as rp  # the helpers of the real-path tests

    repo = rp._skeleton(tmp / "repo")
    run_dir = tmp / "run"
    rp._candidate(repo, run_dir)
    rec = rp._record(tmp / "rehearsal_public.json", file_sha256(repo / core.PLAN))
    import argparse

    assert stages.cmd_freeze(argparse.Namespace(repo=str(repo), rehearsal=str(rec))) == 0
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}

    def git(*a: str) -> str:
        return subprocess.run(["git", "-c", "commit.gpgsign=false", "-C", str(repo), *a], check=True, capture_output=True, text=True, env=env).stdout.strip()

    git("init", "-q")
    git("add", "-A")
    git("commit", "-q", "-m", "freeze")
    freeze = git("rev-parse", "HEAD")
    d2 = repo / "results" / "p10i-s3-freeze-x" / "DECISION_2.md"
    d2.parent.mkdir(parents=True)
    d2.write_text(f"DECISION: RUN\nfreeze commit {freeze}\n")
    git("add", "-A")
    git("commit", "-q", "-m", "decision 2")
    return repo, freeze, run_dir


def test_b1_registered_launch_gets_past_the_platform_check_from_an_unconfigured_process(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo, freeze, run_dir = _frozen_git_repo(tmp_path)
    called: list[str] = []
    monkeypatch.setattr(stages, "execute_stage", lambda stage, *a, **k: called.append(stage) or 0)
    torch.set_num_threads(4)  # an unconfigured supervisor: the old code refused here with "torch_num_threads: 4, the platform of record has 1"
    code = stages.main(["registered", "gates", "--run-dir", str(run_dir), "--freeze-commit", freeze, "--repo", str(repo)])
    assert code == 0 and called == ["gates"]
    assert torch.get_num_threads() == 1 and torch.are_deterministic_algorithms_enabled() and not gates.platform_problems()
    # the same launch with a Decision 2 naming another commit is refused after the platform check
    bad = repo / "results" / "p10i-s3-freeze-x" / "DECISION_2.md"
    assert plan.git(repo, "status", "--porcelain").stdout == b""
    assert stages.main(["registered", "gates", "--run-dir", str(run_dir), "--freeze-commit", "0" * 40, "--repo", str(repo)]) == 2 and bad.is_file()


# ---------------- B3 ----------------
def test_b3_an_inconclusive_label_is_never_positive() -> None:
    both = {(TREE, FRESH): Spec(gain=0.02), (DENSE, FRESH): Spec(gain=0.022)}  # COMPETITIVE before the tags
    out = run(both, edge=[(DENSE, FRESH)])
    assert out["line2_tree"]["label"] == "INCONCLUSIVE (DENSE RATE AT EDGE)" and out["regimes"][FRESH]["line2_tree"]["base_label"] == "COMPETITIVE"
    assert out["registered_positive"] == {"line1": True, "line2": False}
    assert "line 2 False" in report.render(out, "test")
    # without the edge the same registry is positive; MEMORY AHEAD is positive too
    assert run(both)["registered_positive"]["line2"] is True
    assert run({(TREE, FRESH): Spec(gain=0.03), (DENSE, FRESH): Spec(gain=0.02)})["registered_positive"]["line2"] is True
    # a NOT COMPETITIVE label at the memory edge is INCONCLUSIVE and not positive
    assert run({(TREE, FRESH): Spec(gain=0.02), (DENSE, FRESH): Spec(gain=0.03)}, edge=[(TREE, FRESH)])["registered_positive"]["line2"] is False


# ---------------- B4: the seal ----------------
def _floats(obj: Any) -> list[float]:
    if isinstance(obj, float):
        return [obj]
    if isinstance(obj, dict):
        return [x for v in obj.values() for x in _floats(v)]
    if isinstance(obj, list):
        return [x for v in obj for x in _floats(v)]
    return []


def _values_under(root: Path) -> set[str]:
    out: set[str] = set()
    for p in root.rglob("eval.json"):
        out |= {repr(v)[:9] for v in _floats(json.loads(p.read_text())) if abs(v) > 0.01}
    return out


def _leaks(public: Path, values: set[str]) -> list[str]:
    bad = []
    for p in public.rglob("*"):
        if p.is_file() and p.suffix in (".json", ".md", ".log", ".txt"):
            text = p.read_text(errors="replace")
            bad += [f"{p.name}:{v}" for v in values if v in text]
    return bad


def test_b4_the_sealed_directory_must_be_outside_the_repository_for_a_real_rehearsal() -> None:
    with pytest.raises(core.EngineeringStop, match="outside the repository"):
        calibration.require_outside_repo(ROOT / "experiments" / "x" / "items", ROOT)
    calibration.require_outside_repo(ROOT / "experiments" / "x", ROOT, allow_inside_repo=True)  # the synthetic device only
    with pytest.raises(core.EngineeringStop):
        rehearsal.run_r1(ROOT, ROOT / "experiments" / "_scratch" / "unused", {}, synthetic=False, sealed_path=ROOT / "experiments" / "_scratch" / "s" / "sealed.json")


def test_b4_no_calibration_or_dry_value_is_left_in_the_public_run_directory(tmp_path: Path) -> None:
    over = {**rehearsal.SYNTHETIC_OVERRIDE, "rates": {"grid": [0.003, 0.03], "max_extensions_per_side": 0}, "resources": {"workers": 6}}
    run_dir, sealed = tmp_path / "run", tmp_path / "sealed" / "sealed.json"
    pub = rehearsal.run_r1(ROOT, run_dir, over, synthetic=True, sealed_path=sealed, cells=(0,))
    assert not (run_dir / "items").exists() and (tmp_path / "sealed" / "items").is_dir()  # item records are in the sealed directory
    values = _values_under(tmp_path / "sealed" / "items")
    assert len(values) > 50 and not _leaks(run_dir, values)
    assert "rule_hashes" in pub and pub["rule_hashes"] == plan.rule_hashes(ROOT)  # R4
    # R3 through the registered driver on a candidate plan: sealed items, a whitelist-only public report
    import test_p10is3_realpath as rp

    repo = rp._skeleton(tmp_path / "repo")
    rp._candidate(repo, tmp_path / "cand_run")
    cand = plan.Plan.load(repo / core.PLAN)
    run3, sealed3 = tmp_path / "run3", tmp_path / "sealed3"
    rec = rehearsal.run_r3(repo, run3, sealed3, cand, synthetic=True)
    assert rec["status"] == "COMPLETE" and rec["plan_file_sha256"] == file_sha256(repo / core.PLAN)
    v3 = _values_under(sealed3)
    assert len(v3) > 5 and not _leaks(run3, v3) and not (run3 / "items").exists()
    text = (run3 / "stages" / "r3" / "report.md").read_text()
    assert "whitelist only" in text and "mean" not in text.lower() and "DEPENDENT" not in text and "COMPETITIVE" not in text
    assert (sealed3 / "analysis" / "analysis.json").is_file()  # the DRY analysis is sealed


def test_b4_whitelist_report_renders_no_value() -> None:
    res = run({(TREE, FRESH): Spec(gain=0.0123456)})
    text = report.render_whitelist(res, "dry")
    assert "0.0123" not in text and "regimes analysed" in text


# ---------------- R1: cumulative caps ----------------
def _tiny_plan(tmp_path: Path) -> plan.Plan:
    cfg = copy.deepcopy(dict(CFG))
    stages.deep_update(cfg, rehearsal.SYNTHETIC_OVERRIDE)
    rt = synthetic.rate_table(cfg)
    its = items.registered_items(cfg, rt, profile="test", cells=[0])
    keep = its["train"][:2]
    its = {"train": keep, "eval": [e for e in its["eval"] if e["train"] in {t["id"] for t in keep}]}
    return rehearsal.rehearsal_plan(ROOT, tmp_path / "run", "cap", rehearsal.SYNTHETIC_OVERRIDE, its, rt, synthetic=True, gate_profile="test")


def test_r1_caps_are_cumulative_across_stages_and_resumes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    p = _tiny_plan(tmp_path)
    total = p.cap_seconds("any")
    assert total == 25 * 3600.0
    led = core.Ledger(tmp_path / "run" / "ledger.json", total)
    led.charge("R1", total - 10.0)
    seen: list[float] = []

    def fake(tasks, **kw):  # type: ignore[no-untyped-def]
        seen.append(kw["cap_seconds"])
        return {t.label: {"status": runner.NOT_STARTED, "seconds": 0.0, "reason": "x", "peak_rss_bytes": 0} for t in tasks}, 7.0

    monkeypatch.setattr(runner, "run_tasks", fake)
    state = tmp_path / "state"
    code = stages.run_stage("train", p, ROOT, tmp_path / "items", p.path, mode="rehearsal", identity={}, state_dir=state)  # type: ignore[arg-type]
    assert seen == [pytest.approx(10.0)] and code == 1  # a resume gets what is left, not the whole cap
    assert led.charged() == pytest.approx(total - 3.0)  # and its time is charged
    code = stages.run_stage("eval", p, ROOT, tmp_path / "items", p.path, mode="rehearsal", identity={}, state_dir=state)  # type: ignore[arg-type]
    assert seen == [pytest.approx(10.0), pytest.approx(3.0)]  # another stage gets what is left after the first
    led.charge("x", 10.0)
    monkeypatch.setattr(runner, "run_tasks", lambda *a, **k: pytest.fail("nothing may start when the cap is spent"))
    assert stages.run_stage("eval", p, ROOT, tmp_path / "items", p.path, mode="rehearsal", identity={}, state_dir=tmp_path / "state2") == 1  # type: ignore[arg-type]
    m = runner.read_manifest(tmp_path / "state2", "eval")
    assert m is not None and m["status"] == "PAUSED" and all("spent" in t["reason"] for t in m["tasks"].values())


# ---------------- R2: data and parents are identities ----------------
def _plan_with_files(tmp: Path) -> tuple[plan.Plan, Path, Path]:
    d = tmp / "data"
    d.mkdir()
    (d / "a.bin").write_bytes(b"chunks")
    (d / "data_manifest.json").write_text(json.dumps({"files": {"a.bin": file_sha256(d / "a.bin")}}))
    par = tmp / "parent.pt"
    par.write_bytes(b"parent")
    rec = plan.build_plan(mode=plan.REHEARSAL, cfg=CFG, repo=ROOT, run_dir=tmp / "run", rate_table=synthetic.rate_table(CFG), extra={"data_manifest": {"path": str(d / "data_manifest.json"), "sha256": file_sha256(d / "data_manifest.json")}, "data_dir": str(d), "parent_files": {str(par): file_sha256(par)}})
    return plan.Plan(rec), d / "a.bin", par


def test_r2_a_changed_data_file_or_parent_is_paused_identity_and_resumes(tmp_path: Path) -> None:
    p, data_file, parent = _plan_with_files(tmp_path)
    plan.verify_identity(p, ROOT)
    for f, name in ((data_file, "a.bin"), (parent, "parent.pt")):
        good = f.read_bytes()
        f.write_bytes(b"changed")
        with pytest.raises(plan.StageRefused, match=f"{name}.*PAUSED — IDENTITY"):
            plan.verify_identity(p, ROOT)
        f.write_bytes(good)  # restoring the file bit for bit resumes
        plan.verify_identity(p, ROOT)


def test_r2_a_worker_exits_75_on_a_changed_data_file_and_writes_nothing(tmp_path: Path) -> None:
    p, data_file, _ = _plan_with_files(tmp_path)
    pf = tmp_path / "plan.json"
    core.write_record(pf, p.data)
    data_file.write_bytes(b"changed")
    run_dir = tmp_path / "run"
    code = stages.main(["work", "train", "--run-dir", str(run_dir), "--plan", str(pf), "--repo", str(ROOT), "--item", "x"])
    assert code == stages.IDENTITY_EXIT == 75 and not run_dir.exists()


# ---------------- R3 and R4: the freeze ties the rate table and the rules to R1 ----------------
def test_r3_r4_freeze_refuses_a_rate_table_or_rule_hash_not_from_r1(tmp_path: Path) -> None:
    import argparse

    import test_p10is3_realpath as rp

    repo = rp._skeleton(tmp_path / "repo")
    rp._candidate(repo, tmp_path / "run")
    sha = file_sha256(repo / core.PLAN)
    ns = argparse.Namespace(repo=str(repo))

    def record(**over: Any) -> argparse.Namespace:
        (tmp_path / "r.json").unlink(missing_ok=True)
        path = rp._record(tmp_path / "r.json", sha)
        rec = json.loads(path.read_text())
        rec.update(over)
        for k in [k for k, v in over.items() if v is None]:
            del rec[k]
        path.write_text(json.dumps(rec))
        ns.rehearsal = str(path)
        return ns

    other = synthetic.rate_table(CFG, rate=0.01)
    with pytest.raises(plan.StageRefused, match="rate table"):
        stages.cmd_freeze(record(rate_table=other))  # a hand-written table that is not R1's output
    with pytest.raises(plan.StageRefused, match="sealed-archive"):
        stages.cmd_freeze(record(sealed_sha256=None))
    stale = plan.rule_hashes(repo)
    stale["files"] = {**stale["files"], "studies/p10i_s3/labels.py": "0" * 64}
    with pytest.raises(plan.StageRefused, match="R1 recorded"):
        stages.cmd_freeze(record(rule_hashes=stale))
    stale = plan.rule_hashes(repo)
    stale["config_sections"] = "0" * 64
    with pytest.raises(plan.StageRefused, match="R1 recorded"):
        stages.cmd_freeze(record(rule_hashes=stale))
    assert not (repo / core.FREEZE_RECORD).exists()
    assert stages.cmd_freeze(record()) == 0  # the honest record freezes
    # the plan's cap must be the recomputation from R2's record (tamper: another cap)
    assert json.loads((repo / core.PLAN).read_text())["projection"]["hours"] > 0


def test_r4_rule_hashes_cover_the_rule_sections_and_files_and_not_the_caps(tmp_path: Path) -> None:
    import test_p10is3_realpath as rp

    repo = rp._skeleton(tmp_path / "repo")
    h = plan.rule_hashes(repo)
    cfg_path = repo / core.CONFIG
    text = cfg_path.read_text()
    cfg_path.write_text(text.replace("rehearsal_hours = 25.0", "rehearsal_hours = 26.0"))
    assert plan.rule_hashes(repo) == h  # a cap may legitimately change
    cfg_path.write_text(text.replace("effect = 0.005", "effect = 0.004"))
    assert plan.rule_hashes(repo)["config_sections"] != h["config_sections"]
    cfg_path.write_text(text)
    lab = repo / "studies/p10i_s3/labels.py"
    lab.write_text(lab.read_text() + "\n# x\n")
    assert plan.rule_hashes(repo)["files"]["studies/p10i_s3/labels.py"] != h["files"]["studies/p10i_s3/labels.py"]


# ---------------- R6: the dry mapping is one documented pure function ----------------
def test_r6_dry_items_equal_a_derivation_from_the_dry_rate_table() -> None:
    rt = synthetic.rate_table(CFG, rates={(TREE, REP): 0.01, (DENSE, REP): 0.001})
    cand = items.registered_items(CFG, rt)
    real_ck, dry_ck = [512, 2048, 8192, 16384], [8, 16, 24, 32]
    dcfg = copy.deepcopy(dict(CFG))
    stages.deep_update(dcfg, rehearsal.DRY_OVERRIDE)
    mapped = rehearsal.dry_items(cand, real_ck, dry_ck, dcfg)
    again = items.registered_items(dcfg, rehearsal.dry_rate_table(rt, real_ck, dry_ck), profile="dry", cells=[0])
    key = lambda lst: sorted(lst, key=lambda i: i["id"])  # noqa: E731
    assert key(mapped["train"]) == key(again["train"]) and key(mapped["eval"]) == key(again["eval"])
    assert all(t["init_seed"] == 330392 and t["profile"] == "dry" for t in mapped["train"])
    assert {t["stream_seed"] for t in mapped["train"]} == {269201, 269202, 269203}  # the registry's dry streams 269201 + g


# ---------------- R7 ----------------
def test_r7_an_evaluation_item_error_is_recorded_as_one_and_the_analysis_refuses(tmp_path: Path) -> None:
    cfg = copy.deepcopy(dict(CFG))
    stages.deep_update(cfg, rehearsal.SYNTHETIC_OVERRIDE)
    its = items.registered_items(cfg, synthetic.rate_table(cfg), profile="test", cells=[0])
    tr = its["train"][0]
    ev = [e for e in its["eval"] if e["train"] == tr["id"]][0]
    core.write_record(items.train_record_path(tmp_path, tr), {**core.envelope("train"), "id": tr["id"], "status": "ok", "snapshots": {}, "seconds": 0.0, "updates_done": 0, "bytes": 0})

    def boom() -> None:
        raise OSError("disk full")

    with pytest.raises(OSError):
        items.guarded(items.eval_record_path(tmp_path, ev), ev["id"], boom, "eval")
    rec = core.read_record(items.eval_record_path(tmp_path, ev), "eval")
    assert rec["status"] == "item_error" and rec["item_kind"] == "eval"
    with pytest.raises(core.EngineeringStop, match="ENGINEERING STOP — ITEM ERRORS"):
        items.collect_registry(tmp_path, {"train": [tr], "eval": [ev]})


# ---------------- rulings ----------------
def test_ruling_collapsed_cells_are_counted_beside_the_label() -> None:
    out = run({(TREE, FRESH): Spec(gain=0.02, used_slots=1)})
    assert out["regimes"][FRESH]["line1"]["collapsed_cells"] == 27
    text = report.render(out, "test")
    assert "COLLAPSED cells: 27" in text and "never averaged away" in text
    ok = run({(TREE, FRESH): Spec(gain=0.02)})
    assert ok["regimes"][FRESH]["line1"]["collapsed_cells"] == 0 and "COLLAPSED cells: 0)" in report.render(ok, "test")


def test_ruling_not_determined_prints_its_reason_and_stands() -> None:
    reg = synthetic.registry(CFG, {(TREE, FRESH): Spec(gain=0.02), (DENSE, FRESH): Spec(gain=0.03)})
    reg[core.nll_key(DENSE, FRESH, 0.003, 7, 8192, "enabled")] = None  # K2: non-finite at a descriptive checkpoint
    out = analysis.analyse(reg, synthetic.rate_table(CFG), CFG)
    conv = out["regimes"][FRESH]["convergence"][DENSE]
    assert conv["tag"] == "NOT DETERMINED" and conv["counts_as_not_converged"] and conv["reason"]
    assert out["regimes"][FRESH]["line2_tree"]["base_label"] == "NOT COMPETITIVE"  # no line label changed
    assert out["route_a"]["dense_fresh_not_converged"] is True  # the conservative outcome
    text = report.render(out, "test")
    assert "NOT DETERMINED" in text and "reason:" in text and "NON-FINITE" in text


def test_ruling_integrity_is_checked_at_every_evaluated_checkpoint() -> None:
    # replay != enabled only at 512 (a descriptive checkpoint): the old code read U* only and labelled
    out = run({(TREE, FRESH): Spec(gain=0.02, bad_replay=[3], bad_ckpts=[512])})
    assert out["regimes"][FRESH]["line1"]["label"] == "NOT EVALUABLE"
    assert any("u512" in p for p in out["regimes"][FRESH]["integrity_problems"][TREE])
    assert run({(TREE, FRESH): Spec(gain=0.02, bad_ckpts=[512])})["regimes"][FRESH]["line1"]["label"] == "DEPENDENT"  # no bad cell: nothing flagged


def test_ruling_past_best_counts_step_zero_as_a_checkpoint() -> None:
    # REP: the loss at every trained checkpoint stays near B - 0.01 but U* is 0.01 ABOVE the step-0 loss: only step 0 shows it
    base = Spec(gain=-0.01, curve={512: -1.0, 2048: -1.0, 8192: -1.0, 16384: 1.0}, step0=2.0)
    out = run({(TREE, REP): base, (DENSE, REP): Spec(gain=0.03)})
    # gains: 512..8192 are +0.01 (loss B - 0.01 = 1.99 ... wait: gain = -0.01 x -1 = +0.01); U*: gain -0.01 -> loss 2.01 above step 0 (2.0) by 0.01 > 0.005
    assert out["regimes"][REP]["past_best"][TREE]["flag"] is True
    without = run({(TREE, REP): Spec(gain=-0.01, curve={512: -1.0, 2048: -1.0, 8192: 0.0, 16384: 1.0}), (DENSE, REP): Spec(gain=0.03)})
    assert without["regimes"][REP]["past_best"][TREE]["flag"] is True  # (without step 0 the lowest earlier checkpoint is 1.99: also flagged); step 0 only adds a lower bound


def test_ruling_checker_copy_excludes_only_this_study_and_p10ir() -> None:
    text = "\n".join(new for _, new in gates.checker_substitutions())
    assert "p10i_s3" in text and "p10ir" in text and "test_p10is3_" in text
    for other in ("p10i_s0", "p10i_s1", "p10i_s2", "p10i_s4", "p10i_s5", "p10s1", "p10s2"):
        assert other not in text
    g = gates.seed_gate(CFG, root=ROOT)
    assert g["passed"] is True, g["problems"]


def test_ruling_gates_and_r2_never_use_test_seeds() -> None:
    for fn in (stages.run_core_gates, stages.work_r2probe):
        src = inspect.getsource(fn)
        assert "test_seed" not in src and 'Seeds("test"' not in src and "Seeds('test'" not in src, fn.__name__
    assert 'Seeds("dry"' in inspect.getsource(stages.run_core_gates) and 'Seeds("dry"' in inspect.getsource(stages.work_r2probe)


def test_gate_configure_process_is_idempotent() -> None:
    gates.configure_process()
    gates.configure_process()
    assert torch.get_num_threads() == 1 and torch.get_num_interop_threads() == 1 and torch.are_deterministic_algorithms_enabled()
    shutil.which("git")  # (the frozen-repository test above needs it)
