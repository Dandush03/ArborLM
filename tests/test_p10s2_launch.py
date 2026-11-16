# ruff: noqa: E501
"""P10S2 launch scripts (audit B B2, m1, M5, M8): every launch script is run here with a stub in place of ``uv`` and its argv is parsed by the real parser AND executed through ``stages.main`` where the stage
can be executed cheaply: ``rehearse.sh`` passes no layer, and the rehearsal reads the layer and the calibrated LoRA learning rate from ``calibration.json`` (a regression test of the P9-II GENERATE_ATTEMPT1 class of
failure: the argv parsed, the command crashed). Self-check only: not independent review, not Astra validation, not human approval."""

import json
import os
import re
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402

from studies.p10s2 import budget, core, freeze, ledger, rehearsal, stages  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
LAUNCH = ROOT / "studies" / "p10s2" / "launch"
REGISTERED = ("gates", "train", "evaluate", "timing", "recompute", "analysis", "report")
PREFREEZE = ("datagen", "calibrate", "prefreeze_gates", "rehearse")


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
    return p, (out.read_text().splitlines() if out.exists() else [])


def test_every_launch_script_exists_is_executable_and_parses_as_shell() -> None:
    assert {p.stem for p in LAUNCH.glob("*.sh")} == set(REGISTERED) | set(PREFREEZE)  # the pre-freeze gates stage has its own script
    for p in LAUNCH.glob("*.sh"):
        assert p.stat().st_mode & stat.S_IEXEC, p.name
        assert subprocess.run(["sh", "-n", str(p)], capture_output=True, check=False).returncode == 0, p.name  # noqa: S603, S607
        text = p.read_text()
        assert "set -eu" in text and "exec uv run --locked" in text and "$@" not in text.replace('"$#"', "")  # no argument is re-parsed or forwarded by the shell


@pytest.mark.parametrize("name", REGISTERED)
def test_registered_scripts_pass_every_required_flag_to_the_real_parser_and_nothing_else(name: str, tmp_path: Path) -> None:
    p, lines = run_script(name, [str(tmp_path / "run"), "abc123"], tmp_path)
    assert p.returncode == 0, p.stderr
    assert lines[:5] == ["run", "--locked", "python", "-m", "studies.p10s2.stages"]
    argv = lines[5:-1]
    assert Path(lines[-1]).resolve() == ROOT.resolve()  # the script changes to the repository root before the exec
    args = stages.build_parser().parse_args(argv)
    assert args.command == "registered" and args.name == name and args.freeze_commit == "abc123" and args.run_dir == str(tmp_path / "run") and args.caps == "studies/p10s2/freeze/stage_caps.json"
    assert argv.count("--caps") == 1 and "--repo" not in argv and all(a.startswith("--") or not a.startswith("-") for a in argv)  # nothing else is passed


@pytest.mark.parametrize("name", PREFREEZE)
def test_prefreeze_scripts_pass_the_stage_cap_equal_to_the_configured_one_and_no_typed_design_value(name: str, tmp_path: Path) -> None:
    p, lines = run_script(name, [str(tmp_path / "run"), "deadbeef"], tmp_path)
    assert p.returncode == 0, p.stderr
    i = lines.index("-m")
    argv = lines[i + 2 : -1]
    cap = float(argv[argv.index("--stage-cap-seconds") + 1])
    configured = {"datagen": core.CFG["prefreeze_caps"]["datagen"], "calibrate": core.CFG["prefreeze_caps"]["calibrate"], "rehearse": core.CFG["prefreeze_caps"]["rehearse"], "prefreeze_gates": core.CFG["rehearsal"]["prefreeze_gates_cap_seconds"]}[name]
    assert cap == float(configured) and "--code-commit" in argv and argv[argv.index("--code-commit") + 1] == "deadbeef"
    if name == "datagen":
        assert lines[i + 1] == "studies.p10s2.datagen"
        return
    assert lines[i + 1] == "studies.p10s2.stages"
    for typed in ("--updates", "--full-updates", "--layer", "--lora-lr", "--store-lr", "--device", "--repo"):
        assert typed not in argv, f"{name}.sh passes the typed value {typed}: the configuration and the calibration record supply it"
    args = stages.build_parser().parse_args(argv)
    assert args.command == name.replace("_", "-") and args.stage_cap_seconds == cap and args.code_commit == "deadbeef" and args.run_dir == str(tmp_path / "run") and args.data_dir == str(tmp_path / "run" / "data" / "bundle")


def test_script_argument_handling(tmp_path: Path) -> None:
    for name in (*REGISTERED, *PREFREEZE):
        p, lines = run_script(name, [], tmp_path)
        assert p.returncode == 2 and "usage:" in p.stderr and lines == []  # nothing is launched without exactly the run directory and the commit
        p, lines = run_script(name, ["a", "b", "c"], tmp_path)
        assert p.returncode == 2 and lines == []
    p, lines = run_script("gates", ["relative/run", "c1"], tmp_path)
    assert lines[lines.index("--run-dir") + 1] == str(tmp_path / "relative/run")  # a relative run directory is made absolute against the caller's directory
    with pytest.raises(SystemExit):
        stages.build_parser().parse_args(["calibrate", "--run-dir", "x", "--code-commit", "c", "--data-dir", "d"])  # --stage-cap-seconds is required


def test_prefreeze_stage_caps_are_the_upper_end_of_the_adr_projections() -> None:
    caps = core.CFG["prefreeze_caps"]
    assert caps == {"datagen": 6480, "calibrate": 7920, "rehearse": 11520} and caps["datagen"] == pytest.approx(1.8 * 3600) and caps["calibrate"] == pytest.approx(2.2 * 3600) and caps["rehearse"] == pytest.approx(3.2 * 3600)
    assert core.CFG["rehearsal"]["prefreeze_gates_cap_seconds"] == pytest.approx(0.4 * 3600)  # the upper end of the second gates stage's projection (section 13.3)
    for stage in ("datagen", "calibrate", "prefreeze_gates", "rehearse"):
        assert re.search(r"--stage-cap-seconds \d+", (LAUNCH / f"{stage}.sh").read_text())


# --- the rehearsal reads the layer and the calibrated LoRA learning rate from calibration.json (audit B2) ----------------------------------------
def prefreeze_argv(run: Path, name: str = "rehearse") -> list[str]:
    p, lines = run_script(name, [str(run), "deadbeef"], run.parent)
    assert p.returncode == 0
    return lines[lines.index("-m") + 2 : -1]


@pytest.fixture()
def pre_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(freeze, "check_code_commit", lambda repo, commit: commit or "")
    monkeypatch.setattr(ledger, "study_ledger_path", lambda: tmp_path / "ledger.jsonl")
    run = tmp_path / "run"
    run.mkdir()
    return run


def test_rehearse_refuses_without_the_calibration_record_and_after_a_failed_pilot(pre_env: Path, capsys: pytest.CaptureFixture[str]) -> None:
    argv = prefreeze_argv(pre_env)
    assert stages.main(argv) == 2 and "calibration record" in capsys.readouterr().err  # the argv used to reach int(None) and crash; now it refuses cleanly
    (pre_env / "calibration.json").write_text(json.dumps({"selection": {"read_layer": 12, "lora_lr": 0.001}, "pilot": {"ok": False, "outcome": "NOT STARTED: STUDENT CANNOT USE THE MEMORY ON THIS TASK"}}))
    assert stages.main(argv) == 2 and "STUDENT CANNOT USE THE MEMORY" in capsys.readouterr().err
    (pre_env / "calibration.json").write_text(json.dumps({"selection": {"read_layer": 12, "lora_lr": 0.001}, "pilot": {"ok": True}}))
    assert stages.main(argv) == 2 and "prefreeze_gates.json" in capsys.readouterr().err  # the pre-freeze gates stage runs before the rehearsal
    (pre_env / "prefreeze_gates.json").write_text(json.dumps({"ok": False}))
    assert stages.main(argv) == 2 and "gates stage failed" in capsys.readouterr().err


def test_rehearse_executes_with_the_layer_and_the_lora_learning_rate_of_the_calibration_record(pre_env: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    (pre_env / "calibration.json").write_text(json.dumps({"selection": {"read_layer": 12, "lora_lr": 0.001}, "pilot": {"ok": True}}))  # the second value listed: not lora_learning_rates[0]
    (pre_env / "prefreeze_gates.json").write_text(json.dumps({"ok": True, "seconds_scaled_to_registered_panels": 12.5}))
    seen: dict[str, Any] = {}
    (pre_env / "data" / "bundle").mkdir(parents=True)
    (pre_env / "data" / "bundle" / "manifest.json").write_text("{}")  # the identity of the record names the bundle's manifest digest
    monkeypatch.setattr(stages.train, "mps_attempt", lambda: {"ok": True, "error": ""})
    monkeypatch.setattr(stages, "read_bundle", lambda d: "bundle")
    monkeypatch.setattr(stages, "build_world", lambda b, mode, n, run: seen.update(mode=mode, layer=run.layer, lora_lr=run.lora_lr, store_lr=run.store_lr, device=run.device, n=n) or "world")
    monkeypatch.setattr(stages.train, "select_device", lambda name: seen.update(selected=name))
    monkeypatch.setattr(rehearsal, "measure_task_overhead", lambda data_dir, repo, layer, lora_lr: seen.update(overhead_layer=layer, overhead_lr=lora_lr) or {"seconds": 1.0, "peak_bytes": 1.0})

    def fake_rates(world: Any, replicate: int, **kw: Any) -> tuple[Any, dict[str, Any]]:
        from test_p10s2_budget import rates

        seen.update(gates2=kw["gates2_seconds"], updates=kw["updates"], full=kw["full_updates"])
        return rates(0.001), {"raw": True}

    monkeypatch.setattr(rehearsal, "measure_rates", fake_rates)
    assert stages.main(prefreeze_argv(pre_env)) == 0
    assert seen["layer"] == 12 and seen["overhead_layer"] == 12 and seen["lora_lr"] == 0.001 == seen["overhead_lr"] and seen["mode"] == "rehearsal" and seen["n"] == max(a for a, _b in budget.rungs())  # the calibrated layer and LoRA rate, on rehearsal seeds, in a world of the largest rung's replicates (re-check B, m1)
    assert seen["store_lr"] == core.CFG["training"]["store_learning_rate"] and seen["device"] == "mps"  # no automatic device
    assert seen["gates2"] == 12.5 and seen["updates"] == core.CFG["rehearsal"]["short_updates"] == 200 and seen["full"] == core.CFG["rehearsal"]["full_updates"] == 2000
    rec = json.loads((pre_env / "rehearsal.json").read_text())
    assert (pre_env / "rates.json").exists() and rec["headroom_check"]["decision"]["outcome"] and rec["charged_hours_at_end_of_rehearsal"] >= 0
    ident = rec["identity"]  # re-check B, N3: the record says what produced it
    assert ident["seed_mode"] == "rehearsal" and ident["device"] == "mps" and ident["update_counts"] == {"updates": 200, "full_updates": 2000} and ident["code_commit"] == "deadbeef" and len(ident["bundle_manifest_sha256"]) == 64 and ident["config_sha256"]
    assert rec["mps_attempt"] == {"ok": True, "error": ""}
    assert "rung rule outcome" in capsys.readouterr().out
    led = ledger.Ledger(pre_env.parent / "ledger.jsonl")
    assert [e["kind"] for e in led.entries() if e["status"] != "started"] == ["rehearsal"]  # charged to the one study ledger, not to the run directory
    assert not (pre_env / "ledger.jsonl").exists()
    assert stages.main(prefreeze_argv(pre_env)) == 2  # the rehearsal record is write-once: a second rehearsal is refused
    assert "write-once" in capsys.readouterr().err


def test_rehearse_refuses_a_non_mps_device_without_a_reason_and_calibrate_refuses_an_unusable_device(pre_env: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    (pre_env / "calibration.json").write_text(json.dumps({"selection": {"read_layer": 4, "lora_lr": 0.0003}, "pilot": {"ok": True}}))
    (pre_env / "prefreeze_gates.json").write_text(json.dumps({"ok": True, "seconds_scaled_to_registered_panels": 1.0}))
    monkeypatch.setattr(stages.train, "mps_attempt", lambda: {"ok": True, "error": ""})
    assert stages.main([*prefreeze_argv(pre_env), "--device", "cpu"]) == 2 and "CPU is frozen only if the rehearsal itself cannot run on MPS" in capsys.readouterr().err  # a typed CPU while MPS works is refused
    monkeypatch.delenv("PYTEST_CURRENT_TEST")
    assert stages.main([*prefreeze_argv(pre_env), "--device", "cpu"]) == 2 and "not typed outside tests" in capsys.readouterr().err  # re-check B, N3 (b): a typed device is refused outside tests
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "x")
    monkeypatch.setattr(stages.train, "select_device", lambda name: (_ for _ in ()).throw(RuntimeError("device mps requested but unavailable")))
    assert stages.main(prefreeze_argv(pre_env.parent / "run2", "calibrate")) == 2 and "no fallback" in capsys.readouterr().err


def test_a_prefreeze_stage_refuses_when_the_study_ledger_has_no_room_for_its_cap(pre_env: Path, capsys: pytest.CaptureFixture[str]) -> None:
    led = ledger.Ledger(pre_env.parent / "ledger.jsonl")
    led.record("datagen", 35.5 * 3600)  # P is read from the one study ledger: 0.5 h remain, the calibration cap is 2.2 h
    assert stages.main(prefreeze_argv(pre_env, "calibrate")) == 2 and "over the cap of 36.0 h" in capsys.readouterr().err
    assert not (pre_env / "calibration.json").exists()


def test_the_launch_scripts_are_listed_in_the_freeze_readme_and_the_readme_names_the_decision_file() -> None:
    text = (ROOT / "studies/p10s2/freeze/README.md").read_text()
    for stage in ("calibrate.sh", "prefreeze_gates.sh", "rehearse.sh", "datagen.sh"):
        assert stage in text
    assert "results/p10s2-freeze-" in text and "DECISION: RUN" in text and "experiments/P10S2/ledger.jsonl" in text
