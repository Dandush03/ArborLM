# ruff: noqa: E501
"""P10S2 fixed launch scripts, the freeze procedure and its refusals, and the fetch guard (ADR-0022 sections 13.3, 14.1, 16, 18). Pre-freeze lessons carried from the P9-II audit and its first generation
attempt (a launch script that never passed a required flag was never executed): every launch script is run here, with a stub in place of ``uv``, and its arguments are parsed by the real parser. Nothing is
downloaded and the fetch step is never called. Self-check only: not independent review, not Astra validation, not human approval."""

import ast
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402

from studies.p10s2 import budget, core, fetch_guard, freeze, stages  # noqa: E402
from studies.p10s2.ledger import Ledger  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
LAUNCH = ROOT / "studies" / "p10s2" / "launch"
REGISTERED = ("gates", "train", "evaluate", "timing", "recompute", "analysis", "report")
PREFREEZE = ("datagen", "calibrate", "rehearse")
GIB = 2**30


def run_script(name: str, args: list[str], tmp: Path) -> tuple[subprocess.CompletedProcess[str], list[str]]:
    """Run a launch script with a stub ``uv`` first on PATH; return the process and the arguments the stub received (one per line)."""
    bindir = tmp / "bin"
    bindir.mkdir(exist_ok=True)
    out = tmp / "uv_args.txt"
    out.unlink(missing_ok=True)
    stub = bindir / "uv"
    stub.write_text(f'#!/bin/sh\nfor a in "$@"; do printf "%s\\n" "$a"; done > "{out}"\npwd >> "{out}"\n')
    stub.chmod(stub.stat().st_mode | stat.S_IEXEC)
    env = {**os.environ, "PATH": f"{bindir}:{os.environ['PATH']}"}
    p = subprocess.run(["sh", str(LAUNCH / f"{name}.sh"), *args], capture_output=True, text=True, env=env, cwd=tmp, check=False)  # noqa: S603, S607
    lines = out.read_text().splitlines() if out.exists() else []
    return p, lines


def test_every_launch_script_exists_is_executable_and_parses_as_shell() -> None:
    assert {p.stem for p in LAUNCH.glob("*.sh")} == set(REGISTERED) | set(PREFREEZE)
    for p in LAUNCH.glob("*.sh"):
        assert p.stat().st_mode & stat.S_IEXEC, p.name
        assert subprocess.run(["sh", "-n", str(p)], capture_output=True, check=False).returncode == 0, p.name  # noqa: S603, S607
        text = p.read_text()
        assert "set -eu" in text and 'exec uv run --locked' in text and "$@" not in text.replace('"$#"', "")  # no argument is re-parsed or forwarded by the shell


@pytest.mark.parametrize("name", REGISTERED)
def test_registered_scripts_pass_every_required_flag_to_the_real_parser(name: str, tmp_path: Path) -> None:
    p, lines = run_script(name, [str(tmp_path / "run"), "abc123"], tmp_path)
    assert p.returncode == 0, p.stderr
    assert lines[:5] == ["run", "--locked", "python", "-m", "studies.p10s2.stages"]
    argv = lines[5:-1]
    assert Path(lines[-1]).resolve() == ROOT.resolve()  # the script changes to the repository root before the exec
    args = stages.build_parser().parse_args(argv)  # the parser requires every flag: this fails if the script omitted one (the P9-II first-attempt failure)
    assert args.command == "registered" and args.name == name and args.freeze_commit == "abc123" and args.run_dir == str(tmp_path / "run") and args.caps == "studies/p10s2/freeze/stage_caps.json"
    assert argv.count("--caps") == 1 and all(a.startswith("--") or not a.startswith("-") for a in argv)  # nothing else is passed


@pytest.mark.parametrize("name", PREFREEZE)
def test_prefreeze_scripts_pass_the_stage_cap_and_every_required_flag(name: str, tmp_path: Path) -> None:
    p, lines = run_script(name, [str(tmp_path / "run"), "deadbeef"], tmp_path)
    assert p.returncode == 0, p.stderr
    if name == "datagen":  # the locked pyarrow comes from an extra of the lock, so the launch script may add "--extra pilot" before the requirements
        assert lines[:2] == ["run", "--locked"] and lines[lines.index("--with-requirements") + 1] == "studies/p10s2/requirements-datagen.txt" and lines.index("--with-requirements") < lines.index("python")
    else:
        assert lines[:3] == ["run", "--locked", "python"]
    mod = "studies.p10s2.datagen" if name == "datagen" else "studies.p10s2.stages"
    i = lines.index("-m")
    assert lines[i + 1] == mod
    argv = lines[i + 2 : -1]
    cap = float(argv[argv.index("--stage-cap-seconds") + 1])
    assert cap == float(core.CFG["prefreeze_caps"][name])  # the stage cap equals the configured one
    assert "--code-commit" in argv and argv[argv.index("--code-commit") + 1] == "deadbeef"
    if name == "datagen":
        flags = set(re.findall(r'add_argument\("(--[a-z-]+)"[^)]*required=True', (ROOT / "studies/p10s2/datagen.py").read_text()))
        assert flags <= set(argv) and {"--downloads", "--out", "--code-commit", "--stage-cap-seconds"} <= flags
    else:
        args = stages.build_parser().parse_args(argv)
        assert args.command == name and args.stage_cap_seconds == cap and args.code_commit == "deadbeef" and args.run_dir == str(tmp_path / "run")


def test_script_argument_handling(tmp_path: Path) -> None:
    for name in (*REGISTERED, *PREFREEZE):
        p, lines = run_script(name, [], tmp_path)
        assert p.returncode == 2 and "usage:" in p.stderr and lines == []  # nothing is launched without exactly the run directory and the commit
        p, lines = run_script(name, ["a", "b", "c"], tmp_path)
        assert p.returncode == 2 and lines == []
    p, lines = run_script("gates", ["relative/run", "c1"], tmp_path)
    assert lines[lines.index("--run-dir") + 1] == str(tmp_path / "relative/run")  # a relative run directory is made absolute against the caller's directory
    with pytest.raises(SystemExit):
        stages.build_parser().parse_args(["registered", "gates", "--run-dir", "x", "--freeze-commit", "c"])  # --caps is required (every script passes it)
    with pytest.raises(SystemExit):
        stages.build_parser().parse_args(["registered", "invent", "--run-dir", "x", "--freeze-commit", "c", "--caps", "y"])
    with pytest.raises(SystemExit):
        stages.build_parser().parse_args(["calibrate", "--run-dir", "x", "--code-commit", "c", "--data-dir", "d", "--updates", "1"])  # --stage-cap-seconds is required


def test_prefreeze_stage_caps_are_the_upper_end_of_the_adr_projections() -> None:
    caps = core.CFG["prefreeze_caps"]
    assert caps == {"datagen": 6480, "calibrate": 7920, "rehearse": 11520} and caps["datagen"] == pytest.approx(1.8 * 3600) and caps["calibrate"] == pytest.approx(2.2 * 3600) and caps["rehearse"] == pytest.approx(3.2 * 3600)


# --- the freeze procedure -------------------------------------------------------------------------------------------------------------------------
def git(repo: Path, *a: str) -> str:
    r = subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@example.invalid", "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null", *a], capture_output=True, text=True, check=True)  # noqa: S603, S607
    return r.stdout.strip()


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    r = tmp_path / "repo"
    for rel, content in (("studies/p10s2/x.py", "x = 1\n"), ("src/arborlm/a.py", "a = 1\n"), ("uv.lock", "lock\n"), ("pyproject.toml", "[project]\n"), ("tests/test_p10s2_a.py", "def test_a(): pass\n"), ("tests/test_other.py", "")):
        (r / rel).parent.mkdir(parents=True, exist_ok=True)
        (r / rel).write_text(content)
    (r / core.DEFAULT_CONFIG).parent.mkdir(parents=True, exist_ok=True)
    (r / core.DEFAULT_CONFIG).write_text((ROOT / core.DEFAULT_CONFIG).read_text())
    (r / core.SPEC).parent.mkdir(parents=True, exist_ok=True)
    (r / core.SPEC).write_text("adr\n")
    git(r, "init", "-q", "-b", "main")
    git(r, "add", "-A")
    git(r, "commit", "-q", "-m", "freeze")
    return r


def test_preconditions_clean_tree_ancestor_and_frozen_paths(repo: Path) -> None:
    c = git(repo, "rev-parse", "HEAD")
    ident = freeze.check_preconditions(repo, c)
    assert ident["commit"] == c and len(ident["tree"]) == 40
    with pytest.raises(freeze.FreezeRefused, match="requires --freeze-commit"):
        freeze.check_preconditions(repo, None)
    with pytest.raises(freeze.FreezeRefused, match="not a commit"):
        freeze.check_preconditions(repo, "0" * 40)
    (repo / "scratch.txt").write_text("x")
    with pytest.raises(freeze.FreezeRefused, match="not clean"):
        freeze.check_preconditions(repo, c)  # an untracked file also makes the tree unclean
    (repo / "scratch.txt").unlink()
    for rel in ("studies/p10s2/x.py", "src/arborlm/a.py", "uv.lock", "pyproject.toml", core.SPEC, "studies/p10s2/new.py", str(core.DEFAULT_CONFIG)):
        p = repo / rel
        old = p.read_text() if p.exists() else None
        p.write_text((old or "") + "# changed\n")
        git(repo, "add", "-A")
        git(repo, "commit", "-q", "-m", f"change {rel}")
        with pytest.raises(freeze.FreezeRefused, match="differs from the freeze commit"):
            freeze.check_preconditions(repo, c)
        git(repo, "reset", "-q", "--hard", c)
    t = repo / "tests/test_p10s2_a.py"
    t.write_text("def test_a(): assert True\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "test changed")
    with pytest.raises(freeze.FreezeRefused, match="test_p10s2_a.py differs"):
        freeze.check_preconditions(repo, c)
    git(repo, "reset", "-q", "--hard", c)
    (repo / "tests/test_other.py").write_text("changed")  # a test of another study is not frozen here
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "other test")
    assert freeze.check_preconditions(repo, c)["commit"] == c
    # a commit that is not an ancestor of HEAD
    git(repo, "checkout", "-q", "-b", "side", c)
    (repo / "studies/p10s2/side.py").write_text("s = 1\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "side")
    side = git(repo, "rev-parse", "HEAD")
    git(repo, "checkout", "-q", "main")
    with pytest.raises(freeze.FreezeRefused, match="not an ancestor"):
        freeze.check_preconditions(repo, side)


def test_code_commit_must_equal_a_clean_head(repo: Path) -> None:
    head = git(repo, "rev-parse", "HEAD")
    assert freeze.check_code_commit(repo, head) == head
    with pytest.raises(freeze.FreezeRefused):
        freeze.check_code_commit(repo, None)
    (repo / "studies/p10s2/x.py").write_text("x = 2\n")
    with pytest.raises(freeze.FreezeRefused, match="not clean"):
        freeze.check_code_commit(repo, head)
    git(repo, "commit", "-q", "-a", "-m", "next")
    with pytest.raises(freeze.FreezeRefused, match="not a clean HEAD"):
        freeze.check_code_commit(repo, head)


def rehearsal_inputs(tmp: Path, scale_hours: float = 10.0, peaks: dict[str, int] | None = None) -> tuple[budget.Rates, Ledger, Path, Path, Path]:
    from test_p10s2_budget import hours, rates  # noqa: PLC0415

    r = rates(scale_hours / hours(1.0, 4, 2000), **(peaks or {}))
    led = Ledger(tmp / "ledger.jsonl")
    led.record("datagen", 1.0 * 3600)
    led.record("calibration", 1.0 * 3600)
    led.record("rehearsal", 1.5 * 3600)
    data = tmp / "repo" / "data"
    data.mkdir(parents=True, exist_ok=True)
    (data / "manifest.json").write_text('{"files": {}}')
    cal = tmp / "repo" / "calibration.json"
    cal.write_text(json.dumps({"selection": {"read_layer": 4}}))
    pre = tmp / "repo" / "prefreeze.json"
    pre.write_text(json.dumps({"teacher_only": True, "stop": None, "g1": {"ok": True}, "g3": {"ok": True}, "combined_whole_string": {"ok": True}}))
    return r, led, data, cal, pre


def freeze_into(repo_dir: Path, tmp: Path, **kw: object) -> dict[str, object]:
    r, led, data, cal, pre = rehearsal_inputs(tmp, **kw)  # type: ignore[arg-type]
    return freeze.write_freeze(repo_dir, rates=r, ledger=led, run_dir=tmp / "registered-run", data_dir="data", calibration=cal, prefreeze=pre, design_layer=4, store_lr=0.003, lora_lr=0.001)


def plain_repo(tmp: Path) -> Path:
    r = tmp / "repo"
    (r / "studies/p10s2").mkdir(parents=True, exist_ok=True)
    (r / "studies/p10s2/x.py").write_text("x = 1\n")
    (r / core.DEFAULT_CONFIG).parent.mkdir(parents=True, exist_ok=True)
    (r / core.DEFAULT_CONFIG).write_text((ROOT / core.DEFAULT_CONFIG).read_text())
    return r


def test_freeze_writes_the_frozen_plan_and_cap_files_and_verify_plan_checks_every_identity(tmp_path: Path) -> None:
    core.reset_seed_record()
    r = plain_repo(tmp_path)
    rec = freeze_into(r, tmp_path)
    assert set(Path(x).name for x in rec["written"]) == {"plan.json", "stage_caps.json", "rehearsal_outcome.json", "projection.json"}  # type: ignore[attr-defined]
    plan = freeze.load_plan(r)
    assert plan["design"] == {"replicates": 4, "updates": 2000, "layer": 4, "store_lr": 0.003, "lora_lr": 0.001, "rung": "rung 1"} and plan["cap_hours"] == 36.0 and plan["cap_raise_sha256"] is None
    assert plan["charged_hours_at_freeze"] == pytest.approx(3.5) and len(plan["planned_seeds"]) == 44 and "studies/p10s2/x.py" in plan["code"]
    assert core.seed_gate([], plan["planned_seeds"])["ok"]  # the planned seeds are the replicate seeds, all listed and in range
    caps = json.loads((r / core.CAPS_FILE).read_text())
    assert set(caps) == {"n4-U2000", "n3-U2000", "n4-U1000", "n3-U1000"} and budget.cap_for(caps, "train", 4, 2000) > 0
    outcome = json.loads((r / core.FREEZE_DIR / "rehearsal_outcome.json").read_text())
    assert outcome["outcome"] == "rung 1" and outcome["headroom_check"]["proposal"] is None
    run_dir = tmp_path / "registered-run"
    freeze.verify_plan(plan, r, run_dir)
    # every identity is checked
    for target, why in (
        (r / core.DEFAULT_CONFIG, "configuration"), (r / core.CAPS_FILE, "stage-cap table"), (r / "data/manifest.json", "data manifest"), (r / "calibration.json", "calibration"), (r / "prefreeze.json", "prefreeze_record"),
        (r / core.FREEZE_DIR / "projection.json", "projection"),
    ):  # fmt: skip
        old = target.read_bytes()
        target.write_bytes(old + b" ")
        with pytest.raises(freeze.FreezeRefused, match="does not hash"):
            freeze.verify_plan(plan, r, run_dir)
        target.write_bytes(old)
    with pytest.raises(freeze.FreezeRefused, match="run directory"):
        freeze.verify_plan(plan, r, tmp_path / "elsewhere")
    with pytest.raises(freeze.FreezeRefused, match="not a registered rung"):
        freeze.verify_plan({**plan, "design": {**plan["design"], "replicates": 2}}, r, run_dir)
    (r / core.RAISE_FILE).write_text(json.dumps({"new_cap_hours": 50.0}))
    with pytest.raises(freeze.FreezeRefused, match="cap-raise record exists"):
        freeze.verify_plan(plan, r, run_dir)  # a raise the plan does not name
    (r / core.RAISE_FILE).unlink()
    with pytest.raises(freeze.FreezeRefused, match="no freeze plan"):
        freeze.load_plan(tmp_path)


def test_freeze_records_the_cap_raise_and_binds_it(tmp_path: Path) -> None:
    from test_p10s2_budget import hours, rates  # noqa: PLC0415

    core.reset_seed_record()
    r = plain_repo(tmp_path)
    rt, led, data, cal, pre = rehearsal_inputs(tmp_path, scale_hours=20.28)
    prop = budget.propose_raise(led.total_hours(), rt)
    assert prop is not None
    (r / core.FREEZE_DIR).mkdir(parents=True, exist_ok=True)
    budget.record_raise(prop, r / core.RAISE_FILE, led)
    rec = freeze.write_freeze(r, rates=rt, ledger=led, run_dir=tmp_path / "registered-run", data_dir="data", calibration=cal, prefreeze=pre, design_layer=4, store_lr=0.003, lora_lr=0.001)
    plan = freeze.load_plan(r)
    assert plan["design"]["rung"] == "rung 1" and plan["cap_hours"] == prop.new_cap_hours > 36.0 and plan["cap_raise_sha256"]
    freeze.verify_plan(plan, r, tmp_path / "registered-run")
    (r / core.RAISE_FILE).write_text(json.dumps({**json.loads((r / core.RAISE_FILE).read_text()), "new_cap_hours": 71.0}))
    with pytest.raises(freeze.FreezeRefused):
        freeze.verify_plan(plan, r, tmp_path / "registered-run")  # the raise record is bound by its hash
    assert rec["decision"]["outcome"] == "rung 1" and hours(1.0, 4, 2000) > 0 and rates(1.0)


def test_freeze_refuses_not_started_budget_a_registered_seed_and_missing_inputs(tmp_path: Path) -> None:
    from test_p10s2_budget import hours  # noqa: PLC0415

    core.reset_seed_record()
    r = plain_repo(tmp_path)
    with pytest.raises(freeze.FreezeRefused, match="NOT STARTED: BUDGET"):
        freeze_into(r, tmp_path, scale_hours=200.0)
    out = json.loads((r / core.FREEZE_DIR / "rehearsal_outcome.json").read_text())
    assert out["outcome"] == "NOT STARTED: BUDGET" and out["decision"]["replicates"] is None  # recorded with the rehearsal record; no plan is written
    assert not (r / core.PLAN_FILE).exists() and not (r / core.CAPS_FILE).exists()
    with pytest.raises(freeze.FreezeRefused, match="NOT STARTED: BUDGET"):
        freeze_into(r, tmp_path, scale_hours=10.0, peaks={"eval_peak_bytes": 5 * GIB})  # an evaluation peak over the limit is not started either
    rt, led, data, cal, pre = rehearsal_inputs(tmp_path)
    led.record("train", 1.0, registered=True)
    with pytest.raises(freeze.FreezeRefused, match="registered seed has been observed"):
        freeze.write_freeze(r, rates=rt, ledger=led, run_dir=tmp_path / "x", data_dir="data", calibration=cal, prefreeze=pre, design_layer=4, store_lr=0.003, lora_lr=0.001)
    assert hours(1.0, 4, 2000) > 0


def test_the_study_stops_before_the_freeze_when_teachers_or_data_do_not_qualify(tmp_path: Path) -> None:
    from studies.p10s2.prefreeze import prefreeze_summary

    ok = {"g1": {"ok": True}, "combined_whole_string": {"ok": True}, "qualification": {"ok": True, "outcome": None}, "sufficiency_pools": {"outcome": None}, "sufficiency_after_filter": {"outcome": None}}
    assert prefreeze_summary(ok) == {"stop": None, "teacher_only": True, "g1_pool_level_ok": True, "combined_whole_string_ok": True}
    assert prefreeze_summary({**ok, "g1": {"ok": False}})["teacher_only"] is False
    nq = {**ok, "qualification": {"ok": False, "outcome": "TRANSFER-INCONCLUSIVE: TEACHERS-NOT-QUALIFIED"}}
    assert prefreeze_summary(nq)["stop"] == "TRANSFER-INCONCLUSIVE: TEACHERS-NOT-QUALIFIED" and prefreeze_summary(nq)["teacher_only"] is False
    di = {**ok, "sufficiency_after_filter": {"outcome": "TRANSFER-INCONCLUSIVE: DATA-INSUFFICIENT"}}
    assert prefreeze_summary(di)["stop"] == "TRANSFER-INCONCLUSIVE: DATA-INSUFFICIENT"
    bad_ws = {**ok, "combined_whole_string": {"ok": False}}
    assert prefreeze_summary(bad_ws)["combined_whole_string_ok"] is False
    core.reset_seed_record()
    r = plain_repo(tmp_path)
    rt, led, data, cal, pre = rehearsal_inputs(tmp_path)
    pre.write_text(json.dumps(bad_ws))
    with pytest.raises(freeze.FreezeRefused, match="whole-string check"):
        freeze.write_freeze(r, rates=rt, ledger=led, run_dir=tmp_path / "x", data_dir="data", calibration=cal, prefreeze=pre, design_layer=4, store_lr=0.003, lora_lr=0.001)  # the same consequence as a prompt mismatch in test (a)
    pre.write_text(json.dumps(nq))
    with pytest.raises(freeze.FreezeRefused, match="TEACHERS-NOT-QUALIFIED"):
        freeze.write_freeze(r, rates=rt, ledger=led, run_dir=tmp_path / "x", data_dir="data", calibration=cal, prefreeze=pre, design_layer=4, store_lr=0.003, lora_lr=0.001)
    assert json.loads((r / core.FREEZE_DIR / "prefreeze_stop.json").read_text())["label"] == "TRANSFER-INCONCLUSIVE: TEACHERS-NOT-QUALIFIED" and not (r / core.PLAN_FILE).exists()


def test_the_freeze_refuses_while_a_prefreeze_cap_is_provisional_and_replaces_it_with_twice_the_measured_time(tmp_path: Path) -> None:
    core.reset_seed_record()
    r = plain_repo(tmp_path)
    rt, led, data, cal, pre = rehearsal_inputs(tmp_path)
    assert core.CFG["prefreeze_caps"] == {"datagen": 6480, "calibrate": 7920, "rehearse": 11520}  # provisional configuration values
    short = Ledger(tmp_path / "short.jsonl")
    short.record("datagen", 3600.0)
    short.record("rehearsal", 5400.0)  # no calibration was measured
    with pytest.raises(freeze.FreezeRefused, match="still provisional"):
        freeze.write_freeze(r, rates=rt, ledger=short, run_dir=tmp_path / "x", data_dir="data", calibration=cal, prefreeze=pre, design_layer=4, store_lr=0.003, lora_lr=0.001)
    assert json.loads((r / core.FREEZE_DIR / "prefreeze_caps.json").read_text())["provisional"] is True and not (r / core.PLAN_FILE).exists()
    freeze.write_freeze(r, rates=rt, ledger=led, run_dir=tmp_path / "x", data_dir="data", calibration=cal, prefreeze=pre, design_layer=4, store_lr=0.003, lora_lr=0.001)
    caps = json.loads((r / core.FREEZE_DIR / "prefreeze_caps.json").read_text())
    assert caps["provisional"] is False and caps["caps_seconds"] == {"datagen": 7200.0, "calibrate": 7200.0, "rehearse": 10800.0}  # 2 x the measured wall time
    assert freeze.load_plan(r)["prefreeze_caps"]["provisional"] is False


def test_registered_stage_refuses_without_a_freeze(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code = stages.main(["registered", "gates", "--run-dir", str(tmp_path / "run"), "--freeze-commit", "abc", "--caps", "studies/p10s2/freeze/stage_caps.json", "--repo", str(tmp_path)])
    assert code == 2 and "refused" in capsys.readouterr().err
    assert not (core.ROOT / core.PLAN_FILE).exists() and not (core.ROOT / core.CAPS_FILE).exists()  # nothing registered runs before the freeze


def test_registered_stage_refuses_a_stage_without_a_cap_and_a_full_ledger(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    caps = {"n4-U2000": {"train": 3600.0}}
    assert budget.cap_for(caps, "train", 4, 2000) == 3600.0
    with pytest.raises(budget.CapMissing):
        budget.cap_for(caps, "gates", 4, 2000)
    led = Ledger(tmp_path / "ledger.jsonl")
    led.record("train", 35.5 * 3600)
    from studies.p10s2.ledger import LedgerRefused

    with pytest.raises(LedgerRefused):
        led.refuse_if_over(3600.0 / 3600.0, 36.0, "stage train")
    assert not capsys.readouterr().err


# --- the fetch guard (nothing is downloaded; the fetch step is never called) ------------------------------------------------------------------------------
def test_pinned_identities_equal_the_adr() -> None:
    adr = (ROOT / core.SPEC).read_text()
    for repo_rev in (fetch_guard.TEACHER_A, fetch_guard.TEACHER_B, fetch_guard.STUDENT, fetch_guard.FALLBACK):
        assert repo_rev[0] in adr and repo_rev[1] in adr
    for name, (digest, size) in fetch_guard.LARGE.items():
        assert digest in adr and f"{size:,}" in adr, name
    for _name, (rel, size) in {**fetch_guard.TATOEBA_FILES, **fetch_guard.FALLBACK_DATA}.items():
        assert rel.split("/")[-1] in adr and f"{size:,}" in adr
    assert fetch_guard.TATOEBA == "https://downloads.tatoeba.org/exports/per_language"


def test_authorization_flag_and_manifest_are_required(tmp_path: Path) -> None:
    m = tmp_path / "manifest.json"
    with pytest.raises(fetch_guard.FetchRefused, match="--i-have-recorded-human-approval"):
        fetch_guard.check_authorization(False, m)
    with pytest.raises(fetch_guard.FetchRefused, match="manifest path is required"):
        fetch_guard.check_authorization(True, None)
    with pytest.raises(fetch_guard.FetchRefused, match="does not exist"):
        fetch_guard.check_authorization(True, m)
    m.write_text("{}")
    fetch_guard.check_authorization(True, m)
    assert fetch_guard.APPROVAL_FLAG == "--i-have-recorded-human-approval"


def test_manifest_lists_exactly_the_approved_downloads_and_demands_digests() -> None:
    man = fetch_guard.build_manifest()
    names = {f["name"] for f in man["files"]}
    assert "teacher_a/pytorch_model.bin" in names and "student/model.safetensors" in names and "tatoeba/deu_eng_links.tsv.bz2" in names
    assert not any(n.startswith("fallback/") or "spa" in n for n in names)  # the fallback files only if the fallback rule is invoked
    files = fetch_guard.validate_manifest(man)  # every digest is a constant of reviewed code (git-blob SHA-1 for the small files, SHA-256 for the large ones), filled in by build_manifest
    assert all((f["sha256"] is None) != (f["git_sha1"] is None) for f in files if f["kind"] != "tatoeba") and all(f["sha256"] is None and f["git_sha1"] is None for f in files if f["kind"] == "tatoeba")
    assert sum(int(f["size"] or 0) for f in files) < 1.5e9 and sum(f["size"] or 0 for f in man["files"] if f["kind"] == "tatoeba") == 24947715 + 12144786 + 9805546 + 3557634 + 2679128 + 3552331 + 2678076
    big = json.loads(json.dumps(man))
    big["files"][0]["size"] = int(2e9)
    with pytest.raises(fetch_guard.FetchRefused, match="size other than"):
        fetch_guard.validate_manifest(big)
    other = json.loads(json.dumps(man))
    other["files"].append({"name": "tatoeba/other.tsv.bz2", "url": "https://example.invalid/x"})
    with pytest.raises(fetch_guard.FetchRefused, match="not an approved download"):
        fetch_guard.validate_manifest(other)
    wrong_url = json.loads(json.dumps(man))
    wrong_url["files"][0]["url"] = "https://example.invalid/model.bin"
    with pytest.raises(fetch_guard.FetchRefused, match="URL other than the approved"):
        fetch_guard.validate_manifest(wrong_url)
    wrong_sha = json.loads(json.dumps(man))
    wrong_sha["files"][0]["sha256"] = "1" * 64
    with pytest.raises(fetch_guard.FetchRefused, match="other than the pinned"):
        fetch_guard.validate_manifest(wrong_sha)
    dup = json.loads(json.dumps(man))
    dup["files"].append(dup["files"][0])
    with pytest.raises(fetch_guard.FetchRefused, match="listed twice"):
        fetch_guard.validate_manifest(dup)
    with pytest.raises(fetch_guard.FetchRefused, match="no file"):
        fetch_guard.validate_manifest({"files": []})


def test_fallback_files_need_a_recorded_human_decision(tmp_path: Path) -> None:
    # the fallback is invoked by a decision that names a committed record (path and commit), not by any non-empty string; the fallback manifest lists the fallback rows only
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "decision.md").write_text("the human lead invoked the fallback\n")
    git(repo, "init", "-q")
    git(repo, "add", "decision.md")
    git(repo, "commit", "-q", "-m", "decision")
    commit = git(repo, "rev-parse", "HEAD")
    decision = {"path": "decision.md", "commit": commit}
    man = fetch_guard.build_manifest(fallback_human_decision=decision)
    names = {f["name"] for f in man["files"]}
    assert "fallback/pytorch_model.bin" in names and "tatoeba/spa_sentences.tsv.bz2" in names and man["fallback_human_decision"] == decision
    assert not any(n.startswith(("teacher_a/", "teacher_b/", "student/")) or n in fetch_guard.TATOEBA_NAMES for n in names)  # the primary files stay frozen and are not listed again
    assert fetch_guard.validate_manifest(man, root=repo)
    for bad in ("the human lead invoked the fallback on <date> (recorded in the ADR)", None, {"path": "decision.md"}, {"path": "decision.md", "commit": "abc"}, {"path": "missing.md", "commit": commit}, {"path": "../x", "commit": commit}):
        man["fallback_human_decision"] = bad
        with pytest.raises(fetch_guard.FetchRefused, match="fallback"):
            fetch_guard.validate_manifest(man, root=repo)


def test_verify_file_and_tatoeba_digests_are_recorded_at_first_download(tmp_path: Path) -> None:
    p = tmp_path / "f.bin"
    p.write_bytes(b"abc")
    d = fetch_guard.sha256_file(p)
    fetch_guard.verify_file(p, d)
    with pytest.raises(fetch_guard.FetchRefused):
        fetch_guard.verify_file(p, "0" * 64)
    assert fetch_guard.record_tatoeba_digests([p]) == {"f.bin": d}


def test_the_fetch_step_checks_authorization_first_and_touches_the_network_only_in_one_function() -> None:
    src = (ROOT / "studies/p10s2/fetch.py").read_text()
    tree = ast.parse(src)
    main = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main")
    calls = [n.func.attr if isinstance(n.func, ast.Attribute) else getattr(n.func, "id", "") for n in ast.walk(main) if isinstance(n, ast.Call)]
    assert calls.index("check_authorization") < calls.index("run")  # the guard runs before anything is fetched
    for path in sorted((ROOT / "studies" / "p10s2").glob("*.py")):
        t = ast.parse(path.read_text())
        for fn in [n for n in ast.walk(t) if isinstance(n, ast.FunctionDef)]:
            for node in ast.walk(fn):
                if isinstance(node, ast.Import | ast.ImportFrom):
                    mods = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module or ""]
                    if any(m.split(".")[0] in ("urllib", "socket", "http", "requests", "ftplib") for m in mods):
                        assert (path.name, fn.name) == ("fetch.py", "_download")
        for node in t.body:
            if isinstance(node, ast.Import | ast.ImportFrom):
                mods = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module or ""]
                assert not any(m.split(".")[0] in ("urllib", "socket", "http", "requests", "ftplib", "huggingface_hub", "transformers", "tokenizers", "safetensors", "sacrebleu", "numpy") for m in mods), (path.name, mods)


def test_no_test_imports_the_fetch_step_or_the_data_generation_step() -> None:
    # only the fix-A tests may import them, and only to run their pure helpers on synthetic files (never ``_download`` and never ``run``); every other test file still may not
    for path in sorted((ROOT / "tests").glob("test_p10s2_*.py")):
        if path.name.startswith("test_p10s2_fixA_"):
            continue
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.ImportFrom):
                names = [a.name for a in node.names]
                assert not (node.module == "studies.p10s2" and any(n in ("fetch", "datagen") for n in names)), path.name
                assert node.module not in ("studies.p10s2.fetch", "studies.p10s2.datagen"), path.name
            if isinstance(node, ast.Import):
                assert not any(a.name in ("studies.p10s2.fetch", "studies.p10s2.datagen") for a in node.names), path.name


def test_the_requirements_file_lists_only_the_eight_named_packages_unfetched() -> None:
    text = (ROOT / "studies/p10s2/requirements-datagen.txt").read_text()
    pins = [ln for ln in text.splitlines() if ln and not ln.startswith("#")]
    assert pins == ["transformers==4.57.1", "tokenizers==0.22.1", "safetensors==0.6.2", "huggingface-hub==0.35.3", "sentencepiece==0.2.1", "numpy==2.3.3", "sacremoses==0.1.1", "sacrebleu==2.5.1"]
    assert "NOT INSTALLED, NOT FETCHED" in text and "RESOLUTION WITH HASHES PENDING" in text and "30gb" in text  # the standing permission, not the earlier pending confirmation
    with tempfile.TemporaryDirectory() as d:
        assert not any(Path(d).iterdir())
