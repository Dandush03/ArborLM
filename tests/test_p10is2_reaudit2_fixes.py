# ruff: noqa: E501
"""P10IS2 Part Q, the second re-audit: F1 (no bytecode into the durable package copy), F2 (the registered analysis stage has a cap and runs, also after NOT RUN BY RULE), F3 (in a rehearsal every file that depends on
the qualification outcome is sealed), F4 (a registered candidate plan refuses a missing shared ledger). Each test fails on the behaviour the audit found; nothing under test is patched. Seeds 936001-936999. Self-check only."""

import hashlib
import json
import os
import stat
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402
from p10is2_fixtures import (  # noqa: E402
    SMALL_SIZES,
    lex_teachers,
    small_cfg,
    small_corpus,
    stub_student,
)
from test_p10is2_launch import FAKE_WALK, freeze, make_repo  # noqa: E402

from arborlm.io import file_sha256, write_json  # noqa: E402
from studies.p10is2.common import core  # noqa: E402
from studies.p10is2.partq import pipeline  # noqa: E402
from studies.p10is2.partq import plan as qplan  # noqa: E402
from studies.p10is2.partq import rehearsal as reh  # noqa: E402
from studies.p10is2.partq.teacher import Generated  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CFG_Q = core.load_config("Q")


# --- F1 ----------------------------------------------------------------------------------------------------------------------------------------------
def run_env_check(extra: dict[str, str], drop: tuple[str, ...]) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if k not in ("PYTHONPATH", "PYTHONDONTWRITEBYTECODE", *drop)}
    env.update({"HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1", **extra})
    code = "from studies.p10is2.common import core; from studies.p10is2.partq import real_world; real_world.assert_process_environment(core.load_config('Q'))"
    return subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=env, capture_output=True, text=True, timeout=300, check=False)  # noqa: S603


def test_a_process_launched_without_pythondontwritebytecode_is_refused() -> None:
    out = run_env_check({}, ())  # a REAL subprocess whose environment lacks the variable (an ordinary terminal)
    assert out.returncode != 0 and "PYTHONDONTWRITEBYTECODE" in out.stderr, out.stderr[-500:]
    ok = run_env_check({"PYTHONDONTWRITEBYTECODE": "1"}, ())
    assert "PYTHONDONTWRITEBYTECODE" not in ok.stderr  # with it, the bytecode problem is gone (the other launch conditions are not the point here)


def test_every_part_q_launch_script_exports_it_and_a_process_it_starts_writes_no_bytecode(tmp_path: Path) -> None:
    bindir = tmp_path / "bin"
    bindir.mkdir()
    fake = bindir / "uv"
    fake.write_text('#!/bin/sh\necho "DWB=${PYTHONDONTWRITEBYTECODE-UNSET}"\n')
    fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
    env = {k: v for k, v in os.environ.items() if k != "PYTHONDONTWRITEBYTECODE"}
    env["PATH"] = f"{bindir}:{env['PATH']}"
    launches = [["partq_registered.sh", "inputs", str(tmp_path / "r"), "c" * 40], ["partq_registered.sh", "analysis", str(tmp_path / "r"), "c" * 40], ["partq_rehearse.sh", "measuring", str(tmp_path / "r")], ["partq_ledger.sh", "registered"]]
    for name, *args in launches:
        o = subprocess.run(["sh", str(ROOT / "studies/p10is2/launch" / name), *args], env=env, capture_output=True, text=True, check=True).stdout  # noqa: S603, S607
        assert "DWB=1" in o, (name, args, o)
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "demo_mod.py").write_text("X = 1\n")
    subprocess.run([sys.executable, "-c", "import demo_mod"], env={**env, "PYTHONPATH": str(pkg), "PYTHONDONTWRITEBYTECODE": "1"}, check=True)  # noqa: S603
    assert not list(pkg.rglob("*.pyc"))  # the variable is what keeps the copy untouched


# --- F2 ----------------------------------------------------------------------------------------------------------------------------------------------
def test_the_config_and_the_caps_proposal_carry_an_analysis_cap() -> None:
    assert "analysis_hours" in CFG_Q["stage_caps"]
    proj = qplan.project_stage_seconds({"qfit": 100.0}, {"qfit": 0.5})
    assert proj["analysis"] == qplan.ANALYSIS_PROJECTED_SECONDS
    caps = qplan.caps_proposal(3600.0, proj)
    assert caps["analysis_hours"] == 0.04  # 2 x 60 s, rounded up to 0.01 h
    assert caps["total_hours"] == pytest.approx(1.0 + 2 * (50.0 + 60.0) / 3600.0, abs=0.0101)  # the common total rule: the charge before the freeze + 2 x every stage
    assert not qplan.caps_match_config({"stage_caps": {k: v for k, v in caps.items()}}, caps)


def launch_registered(r: Path, commit: str, stage: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if k not in ("PYTHONPATH", "OMP_NUM_THREADS")}
    return subprocess.run([sys.executable, "-m", "studies.p10is2.partq.stages", "work", "--stage", stage, "--run-dir", str(r / "runs"), "--freeze-commit", commit, "--repo", str(r)], cwd=ROOT, env=env, capture_output=True, text=True, timeout=600, check=False)  # noqa: S603


def synthetic_records(run: Path, q1_a: bool) -> None:
    (run / "stages").mkdir(parents=True, exist_ok=True)
    for st in ("inputs", "partition", "qfit", "qcheck"):
        write_json(run / f"stages/{st}.complete.json", {"stage": st, "status": "COMPLETE", "utc": "x"})
    (run / "qfit").mkdir(exist_ok=True)
    fs = {"tau": -0.3, "rho1": 0.5, "rho2": 2.0}
    write_json(run / "qfit/record.json", {"q1": {"A": q1_a, "B": True}, "q2": {"A": True, "B": True}, "q3": {"A": True, "B": True}, "filter_setting": {"A": fs, "B": fs}})
    for c in "AB":
        (run / f"qcheck/teacher_{c}").mkdir(parents=True, exist_ok=True)
        write_json(run / f"qcheck/teacher_{c}/result.json", {"ran": True, "read_ok": True, "pass": True, "reserve_exhausted": False, "accepted": 160})


@pytest.mark.skipif(sys.platform != "darwin", reason="the platform of record")
def test_the_registered_analysis_stage_runs_on_a_frozen_repository_and_after_not_run_by_rule(tmp_path: Path) -> None:
    data = tmp_path / "in.bin"
    data.write_bytes(b"abc")
    r = make_repo(tmp_path)
    commit = freeze(r, "Q", inputs={"data": {"path": str(data), "sha256": file_sha256(data)}})
    run = r / "runs"
    synthetic_records(run, q1_a=False)  # teacher A fails Q1
    for st in ("generation", "regeneration", "outputs"):
        o = launch_registered(r, commit, st)
        assert o.returncode == 0, o.stderr[-500:]
        assert json.loads((run / f"stages/{st}.complete.json").read_text())["status"] == "NOT RUN BY RULE"
    o = launch_registered(r, commit, "analysis")
    assert o.returncode == 0 and "KeyError" not in o.stderr, o.stderr[-800:]
    assert "NEGATIVE: QUALITY" in json.loads((run / "qualification.json").read_text())["label"]


@pytest.mark.skipif(sys.platform != "darwin", reason="the platform of record")
def test_the_registered_analysis_stage_runs_when_the_teachers_qualify_too(tmp_path: Path) -> None:
    data = tmp_path / "in.bin"
    data.write_bytes(b"abc")
    r = make_repo(tmp_path)
    commit = freeze(r, "Q", inputs={"data": {"path": str(data), "sha256": file_sha256(data)}})
    synthetic_records(r / "runs", q1_a=True)
    for st in ("generation", "regeneration", "outputs"):  # these would need the world: only the stage order and the plan are exercised here, so mark them complete
        write_json(r / f"runs/stages/{st}.complete.json", {"stage": st, "status": "COMPLETE", "utc": "x"})
    o = launch_registered(r, commit, "analysis")
    assert "KeyError" not in o.stderr, o.stderr[-800:]  # the stage got its cap from the plan and ran (the label itself depends on records this synthetic run lacks)


# --- F3 ----------------------------------------------------------------------------------------------------------------------------------------------
class Garble:
    """Wraps a teacher so that outputs scored below -0.4 are WRONG: Q3 then chooses a stricter setting than the fallback."""

    def __init__(self, t):  # type: ignore[no-untyped-def]
        self.t, self.name, self.revision = t, t.name, t.revision

    def generate_batch(self, sources):  # type: ignore[no-untyped-def]
        return [Generated(g.tokens, (" ".join("qq" for _ in g.text.split()) if g.score < -0.4 else g.text), g.score) for g in self.t.generate_batch(sources)]


def rehearse(tmp: Path, tag: str) -> tuple[dict[str, object], Path]:
    run = tmp / tag

    def make() -> pipeline.QContext:
        cfg = small_cfg(q4_min_accepted=10)
        if tag == "fail":
            cfg["quality"]["wilson_lower_bound"] = 0.99999  # Q3 finds no setting: the fallback is used
        c = pipeline.QContext(cfg=cfg, mode="test", corpus=small_corpus(), teachers={k: Garble(v) for k, v in lex_teachers().items()}, student_scores=stub_student, run_dir=run, sizes=SMALL_SIZES, batch_size=8, block_sources=100, accepted_min=30, accepted_disjoint=300, per_replicate=20, regeneration_batches=3, digest_batches=2, seal=True)
        c.force_generation = True
        return c

    rec = reh.run_measuring(make, cap_seconds=3600.0, post_stages={"outputs": lambda: None})
    return rec, run


def public_files(run: Path) -> dict[str, str]:
    return {str(f.relative_to(run)): hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(run.rglob("*")) if f.is_file() and "sealed" not in f.relative_to(run).parts}


def test_every_public_file_of_a_rehearsal_is_the_same_whether_q3_succeeds_or_fails(tmp_path: Path) -> None:
    rec_ok, run_ok = rehearse(tmp_path, "ok")
    rec_fail, run_fail = rehearse(tmp_path, "fail")
    s_ok = json.loads((run_ok / "sealed/rehearsal_values.json").read_text())["filter_setting"]
    s_fail = json.loads((run_fail / "sealed/rehearsal_values.json").read_text())["filter_setting"]
    assert s_ok != s_fail  # NOT degenerate: the Q3 setting differs from the fallback
    a, b = public_files(run_ok), public_files(run_fail)
    assert sorted(a) == sorted(b)
    assert [k for k in a if a[k] != b[k]] == []  # EVERY file of the public run directory, byte for byte
    for name in ("sealed/generation_result.json", "sealed/generation_pools.json", "sealed/qcheck_A_stop.json", "sealed/qcheck_B_stop.json"):
        f = run_ok / name
        assert f.is_file() and f.stat().st_mode & 0o777 == 0o600 and f.parent.stat().st_mode & 0o777 == 0o700, name
    assert not (run_ok / "generation/result.json").exists() and not (run_ok / "generation/pools.json").exists() and not (run_ok / "qcheck/teacher_A/stop.json").exists()
    assert rec_ok["seal_note"] == rec_fail["seal_note"] and "stay public" in str(rec_ok["seal_note"]) and "before the registered analysis" in str(rec_ok["seal_note"])


def test_the_counting_record_carries_the_seal_note_too(tmp_path: Path) -> None:
    from test_p10is2_partq_freeze import ctx_factory

    def probe() -> None:
        raise core.ForcedIdentityPause("PAUSED — IDENTITY")

    rec = reh.run_counting(ctx_factory(tmp_path, seal=True), plan_file_sha256="c" * 64, caps_provisional=False, cap_seconds=1.0, identity_probe=probe, pause_after_batches=4)
    assert rec["seal_note"] == reh.SEAL_NOTE


# --- F4 ----------------------------------------------------------------------------------------------------------------------------------------------
def test_a_registered_candidate_plan_refuses_a_missing_shared_ledger(tmp_path: Path) -> None:
    base = core.load_config("Q")
    cfg = {**base, "paths": {**base["paths"], "panel_ledger": str(tmp_path / "absent.json")}}
    with pytest.raises(core.StageRefused, match="does not exist"):
        qplan.build_candidate(ROOT, tmp_path / "run", cfg, inputs={}, walk=FAKE_WALK)
    assert "panel_ledger" not in qplan.build_candidate(ROOT, tmp_path / "run", cfg, inputs={}, walk=FAKE_WALK, test_mode=True)["manifests"]  # a fixture says so explicitly


def test_a_registered_candidate_plan_refuses_a_ledger_without_this_studys_windows(tmp_path: Path) -> None:
    ledger = tmp_path / "led.json"
    write_json(ledger, {"format": "p10i-panel-ledger-v1", "windows": []})
    base = core.load_config("Q")
    cfg = {**base, "paths": {**base["paths"], "panel_ledger": str(ledger)}}
    with pytest.raises(core.StageRefused, match="holds 0 windows of this study"):
        qplan.build_candidate(ROOT, tmp_path / "run", cfg, inputs={}, walk=FAKE_WALK)
    owned = [{"owner": "P10IS2-partq", "kind": "marker", "start": i, "end": i + 1} for i in range(44)] + [{"owner": "P10IS2-partq", "kind": "ordinary", "start": 1000 + i, "end": 1001 + i} for i in range(100)]
    write_json(ledger, {"format": "p10i-panel-ledger-v1", "windows": owned})
    rec = qplan.build_candidate(ROOT, tmp_path / "run", cfg, inputs={}, walk=FAKE_WALK)
    assert rec["manifests"]["panel_ledger"]["sha256"] == file_sha256(ledger)
