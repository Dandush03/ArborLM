# ruff: noqa: E501
"""P10S2 end-to-end exercise (audit B M12): a FAST structural test that is always on, and the FULL exercise (``python -m studies.p10s2.e2e``: the whole registered sequence through the real launch scripts on test
seeds in a source-only throwaway clone, with the current interpreter and no new virtual environment) that runs only with ``P10S2_E2E=1``. Self-check only: not independent review, not Astra validation, not
human approval."""

import json
import os
import subprocess
import sys
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402

from studies.p10s2 import core, e2e  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def test_the_exercise_configuration_substitutes_seed_sets_sizes_and_rungs_and_touches_no_threshold() -> None:
    base = core.load_config()
    cfg, subs = e2e.test_configuration(base, training_device="cpu")
    s = cfg["seeds"]
    assert all(229001 <= b <= 229399 for b in s["replicate_bases"]) and (s["calibration_low"], s["rehearsal_low"]) == (229401, 229601)  # registered, calibration, rehearsal and test sets all inside 229001-229999
    ranges = sorted([(s["registered_low"], s["registered_high"]), (s["calibration_low"], s["calibration_high"]), (s["rehearsal_low"], s["rehearsal_high"]), (s["test_low"], s["test_high"])])
    assert all(a[1] < b[0] for a, b in zip(ranges, ranges[1:], strict=False)) and ranges[0][0] >= 229001 and ranges[-1][1] <= 229999
    for base_off in range(s["draw_count"]):
        for lo, hi, b in ((s["calibration_low"], s["calibration_high"], s["calibration_base"]), (s["rehearsal_low"], s["rehearsal_high"], s["rehearsal_base"])):
            assert lo <= b + s["draw_stride"] * base_off <= b + s["draw_stride"] * base_off + 10 <= hi
    assert cfg["budget"]["rungs"] == [[2, 4], [1, 4], [2, 2], [1, 2]] and cfg["memory"]["read_layers"] == [0, 1] and cfg["budget"]["training_device"] == "cpu"
    for table in ("teachers", "scoring", "recompute", "filter"):
        assert cfg[table] == base[table]  # no threshold of the real configuration is changed
    changed_gates = {k for k in base["gates"] if cfg["gates"][k] != base["gates"][k]}
    assert changed_gates == {"g4_repeat_updates"}  # the number of repeated updates only (a size, not a threshold)
    relaxed, rsubs = e2e.test_configuration(base, training_device="cpu", relax_pilot=True)
    assert {k for k in base["gates"] if relaxed["gates"][k] != base["gates"][k]} == {"g4_repeat_updates", "pilot_gap_min"} and rsubs["gates.pilot_gap_min"] == {"real": 0.25, "exercise": -1.0}  # only after the real threshold has stopped the sequence once
    assert cfg["budget"]["cap_hours"] == 36.0 and cfg["budget"]["headroom"] == 2.0 and cfg["budget"]["memory_per_worker_gib"] == 8.0
    assert {"seeds.replicate_bases", "budget.rungs", "calibration.updates"} <= set(subs) and all(set(v) == {"real", "exercise"} for v in subs.values())  # every substitution is listed


def test_the_toml_writer_round_trips_the_real_configuration() -> None:
    base = core.load_config()
    assert tomllib.loads(e2e.dumps_toml(base)) == base


def test_the_clone_is_source_only_has_the_launch_scripts_a_stub_uv_and_the_test_configuration(tmp_path: Path) -> None:
    clone, subs, env = e2e.make_clone(tmp_path, training_device="cpu")
    assert (clone / "studies/p10s2/launch/rehearse.sh").exists() and (clone / "studies/p10s2/launch/prefreeze_gates.sh").exists() and (clone / "src/arborlm").is_dir()
    assert not (clone / "data").exists() and not (clone / ".venv").exists() and not (clone / "results").exists() and not any(clone.rglob("*.pt"))  # source only: no data, no weights, no environment
    assert tomllib.loads((clone / core.DEFAULT_CONFIG).read_text())["budget"]["rungs"] == [[2, 4], [1, 4], [2, 2], [1, 2]]
    assert (clone / core.DEFAULT_CONFIG).read_text() != (ROOT / core.DEFAULT_CONFIG).read_text() and (ROOT / core.DEFAULT_CONFIG).read_text().startswith("# ADR-0022")  # the real configuration is untouched
    status = subprocess.run(["git", "-C", str(clone), "status", "--porcelain"], capture_output=True, text=True, check=True).stdout  # noqa: S603, S607
    assert status == ""  # a clean HEAD: the pre-freeze stages accept it as the code commit
    # the stub: `uv run --locked python -c ...` runs the CURRENT interpreter with the clone's library first, and creates no environment
    p = subprocess.run(["uv", "run", "--locked", "python", "-c", "import arborlm, sys; print(arborlm.__file__); print(sys.executable)"], cwd=clone, env=env, capture_output=True, text=True, check=False)  # noqa: S603, S607
    out = p.stdout.splitlines()
    assert p.returncode == 0 and Path(out[0]).resolve().is_relative_to(clone.resolve()) and out[1] == sys.executable
    assert not list(tmp_path.rglob("pyvenv.cfg"))  # no new virtual environment anywhere under the exercise's folder
    assert subs["budget.training_device"]["exercise"] == "cpu"
    # the registered stages refuse in the clone before a freeze exists: nothing registered runs, nothing is charged
    r = subprocess.run(["sh", str(clone / "studies/p10s2/launch/gates.sh"), str(tmp_path / "run"), "abc"], cwd=clone, env=env, capture_output=True, text=True, check=False)  # noqa: S603, S607
    assert r.returncode == 2 and "refused" in r.stderr
    led = clone / "experiments" / "P10S2" / "ledger.jsonl"
    assert not led.exists() or led.read_text().strip() == ""


def test_the_exercise_uses_the_real_launch_scripts_in_the_documented_order() -> None:
    text = (ROOT / "studies/p10s2/e2e.py").read_text()
    order = [text.rindex(f'script(clone, env, "{n}"') for n in ("calibrate", "prefreeze_gates", "rehearse")]  # the last occurrence of each: the main run (an earlier calibrate/rehearse pair exercises the failed pilot)
    assert order == sorted(order)
    reg = text.index('for name in ("gates", "train", "evaluate", "timing", "recompute", "analysis", "report")')
    assert text.index('"freeze"') < reg and text.index("DECISION: RUN") < reg


@pytest.mark.skipif(os.environ.get("P10S2_E2E") != "1", reason="the full end-to-end exercise is opt-in: P10S2_E2E=1 (it takes many minutes)")
def test_the_full_registered_sequence_through_the_real_launch_scripts(tmp_path: Path) -> None:
    rec = e2e.exercise(tmp_path)
    assert rec["ok"] and rec["new_virtual_environment"] is False
    steps = [s["step"] for s in rec["steps"]]
    assert any("cap stop" in s for s in steps) and any("refused" in s for s in steps) and any("tampered" in s for s in steps)
    assert {"gates.sh", "train.sh", "evaluate.sh", "timing.sh", "recompute.sh", "analysis.sh", "report.sh"} <= set(steps)
    json.dumps(core.jsonable(rec), default=str)
    assert not list(tmp_path.glob("p10s2-e2e-*"))  # the exercise deletes itself
