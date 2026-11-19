# ruff: noqa: E501
"""P10IS6: the second audit's findings and addendum 2 (rulings 16-22): the launch scripts' environment (R6), the real public inputs on copies (B1, B2), R8, R9, R10, the computing partition (R11), ruling 21, and the two end-to-end gaps of item 10 (the unmodified gates.sh through the real
``uv run --locked`` on a throw-away clone; the real r4 seed checker through ``seed_gate``). Self-check only."""

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from studies.p10i_s6 import analysis, core, cost, fetch, gates, rehearsal, synthetic, testing
from studies.p10i_s6 import plan as planmod
from studies.p10i_s6.core import FLAT
from studies.p10i_s6.synthetic import ArmSpec, Spec

REAL = core.repo_root()
CFG = core.load_config()
DATA = Path("/Users/daniellaloush/dandush03/ArborLM")  # the lead's checkout: its public inputs are READ, never written
REAL_LEDGER = DATA / "data/p10i-shared/panel_ledger.json"
REAL_S3 = DATA / "experiments/P10IS3-data-20261118/excluded_spans.json"
REAL_WT2 = DATA / "data/wikitext2"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def pilot_env() -> Iterator[Path]:
    """A FRESH locked environment with the ``pilot`` extra (offline, from the uv cache): what ``uv run --locked --extra pilot`` provides, without the project's own build."""
    with testing.scratch("pilotenv") as d:
        for f in ("pyproject.toml", "uv.lock", ".python-version"):
            shutil.copy(REAL / f, d / f)
        env = {**os.environ, "UV_PROJECT_ENVIRONMENT": str(d / "venv")}
        r = subprocess.run(["uv", "sync", "--offline", "--locked", "--extra", "pilot", "--no-install-project"], cwd=d, env=env, capture_output=True, text=True, timeout=900, check=False)  # noqa: S603, S607
        assert r.returncode == 0, r.stderr[-800:]
        yield d / "venv" / "bin" / "python"


def test_every_launch_script_runs_in_a_fresh_locked_environment(pilot_env: Path) -> None:
    launch = REAL / "studies/p10i_s6/launch"
    needs_pyarrow = {"studies.p10i_s6.d0", "studies.p10i_s6.realcheck"}
    modules = {}
    for f in sorted(launch.glob("*.sh")):
        text = f.read_text()
        run = [ln for ln in text.splitlines() if ln.startswith("exec uv run")]
        assert len(run) == 1 and "--locked" in run[0], f.name
        m = re.search(r"(studies\.p10i_s6\.\w+)", run[0])
        assert m, f.name
        modules[f.name] = m[1]
        if m[1] in needs_pyarrow:
            assert "--extra pilot" in run[0], f"{f.name} reads parquet and needs the pilot extra"
    env = {**os.environ, "PYTHONPATH": f"{REAL}:{REAL / 'src'}", "PYTHONDONTWRITEBYTECODE": "1"}
    mods = sorted(set(modules.values()) | needs_pyarrow)
    code = "import pyarrow, psutil, torch; import " + ", ".join(mods)
    r = subprocess.run([str(pilot_env), "-I", "-c", f"import sys; sys.path[:0] = ['{REAL}', '{REAL / 'src'}']; {code}"], env={k: v for k, v in env.items() if k != "PYTHONPATH"}, capture_output=True, text=True, timeout=300, check=False)  # noqa: S603
    assert r.returncode == 0, r.stderr[-800:]
    # the plain locked environment (no extra) has no pyarrow: that is why the scripts that read parquet name the extra
    assert modules["prepare-data.sh"] == "studies.p10i_s6.d0"


@pytest.mark.skipif(not (REAL_LEDGER.is_file() and REAL_S3.is_file() and (REAL_WT2 / "validation-00000-of-00001.parquet").is_file()), reason="the lead's public inputs are not on this machine")
def test_real_ledger_and_s3_excluded_set_on_copies(pilot_env: Path) -> None:
    before = (sha(REAL_LEDGER), sha(REAL_S3))
    assert before[0].startswith("62f81116") and before[1].startswith("40e63363")
    with testing.scratch("realcopy") as d:
        shutil.copy(REAL_LEDGER, d / "ledger.json")
        shutil.copy(REAL_S3, d / "s3.json")
        r = subprocess.run([str(pilot_env), "-c", f"import sys; sys.path[:0] = ['{REAL}', '{REAL / 'src'}']; from studies.p10i_s6 import realcheck; raise SystemExit(realcheck.main(['--ledger-copy', '{d / 'ledger.json'}', '--s3-excluded-copy', '{d / 's3.json'}', '--wikitext2-dir', '{REAL_WT2}']))"], capture_output=True, text=True, timeout=1500, check=False)  # noqa: S603
        assert r.returncode == 0, r.stderr[-1500:]
        rec = json.loads(r.stdout.strip().splitlines()[-1])
        assert rec["ledger_sha256_before"] == before[0] and rec["s3_spans_sha256"] == before[1] and rec["windows_before"] == 1168
        assert rec["new_panel_chunks"] == 1024 and rec["overlaps_with_full_excluded_set"] == 0  # ruling 16: with the ledger and P10-I-S3's own excluded set
        assert rec["overlaps_with_s3_set_if_only_the_ledger_were_excluded"] > 0  # the second audit's finding: without it the walk overlaps P10-I-S3's windows (153 by the audit)
        assert rec["old_windows_unchanged"] is True and rec["windows_after"] == 1168 + 1024 and rec["append"]["entries_added"] == 1024
        assert rec["append"]["sha256_before"] == before[0] and sha(d / "ledger.json") == rec["append"]["sha256_after"] != before[0]
        new = json.loads((d / "ledger.json").read_bytes())
        assert [w["source"] for w in new["windows"][1168:]].count("P10-I-S6 panel registered") == 512 and set(new) == {"format", "p10is2", "windows"}
    assert (sha(REAL_LEDGER), sha(REAL_S3)) == before  # the real files are unchanged


# ---- R8 / ruling 18
def test_probes_are_long_enough_and_a_non_positive_rate_stops_the_rehearsal() -> None:
    assert CFG["rehearsal"]["r2_updates"] >= 2048 and CFG["rehearsal"]["r2_min_updates"] == 2048
    probes = [{"arm": a, "kind": "train", "seconds": 5.0 + 100 * 0.01, "updates": 100} for a in core.ARMS] + [{"arm": a, "kind": "eval", "seconds": 5.5, "evals": {m: 2 if m == "full" else 0 for m in core.MODES}} for a in core.ARMS]
    probes += [{"arm": a, "kind": "eval", "seconds": 5.5, "evals": {m: 2 if m == mm else 0 for m in core.MODES}} for a in core.ARMS for mm in ("step0", "enabled", "triple")]
    assert cost.unit_costs_from_probes({"seconds": 5.0}, probes, 4, 1.0)["arms"][FLAT]["seconds_per_update"] == pytest.approx(0.01)
    for bad_seconds in (4.9, 5.0, float("nan")):  # below the overhead, equal to it, not finite
        bad = [{**p, "seconds": bad_seconds} if p["kind"] == "train" and p["arm"] == FLAT else p for p in probes]
        with pytest.raises(core.EngineeringStop, match="non-positive or non-finite"):
            cost.unit_costs_from_probes({"seconds": 5.0}, bad, 4, 1.0)
    with testing.scratch("r2min") as d:
        with pytest.raises(core.EngineeringStop, match="ruling 18"):
            rehearsal.run_r2(REAL, d, d / "sealed", rate_table=synthetic.rate_table(2), k_max=2, synthetic=True, cfg_override={"rehearsal": {"r2_updates": 100}})


# ---- R9 / ruling 20
def test_the_sealed_directory_is_checked_before_anything_is_written() -> None:
    inside = REAL / "experiments" / "_scratch" / "p10i_s6_tests" / "sealed-inside-test"
    with testing.scratch("run") as d:
        for call in (lambda: rehearsal.run_r1(REAL, d, inside, synthetic=False, data_args={}, k_max=2), lambda: rehearsal.run_r2(REAL, d, inside, rate_table=synthetic.rate_table(2), k_max=2, synthetic=False, data_args={}), lambda: rehearsal.run_r3(REAL, d, inside, synthetic=False, data_args={})):
            with pytest.raises(core.EngineeringStop, match="sealed folder"):
                call()
            assert not inside.exists() and not list(d.iterdir())  # nothing was written anywhere


# ---- R10 / ruling 22
@pytest.mark.parametrize("names,why", [(["train-00000-of-00002.parquet"], "missing shard 1"), (["train-00001-of-00002.parquet"], "missing shard 0"), (["train-00000-of-00002.parquet", "train-00000-of-00002.parquet"], "duplicate"), (["train-00000-of-00002.parquet", "train-00001-of-00003.parquet"], "mixed N"), (["train-00000-of-00001.parquet", "train-00001-of-00001.parquet"], "index out of range")])
def test_pin_refuses_an_incomplete_shard_list(names: list[str], why: str) -> None:
    called: list[str] = []

    def opener(url: str, timeout: int = 0) -> Any:
        called.append(url)
        raise AssertionError("no pointer is fetched for an incomplete list")

    with testing.scratch("pin") as d, pytest.raises(core.EngineeringStop, match="incomplete or inconsistent"):
        fetch.pin(names, CFG, opener, d / "pins.json")
    assert not called, why


# ---- R11 / ruling 19
def test_the_two_lists_partition_the_package_and_each_files_side_is_named() -> None:
    stems = {p.stem for p in (REAL / "studies/p10i_s6").glob("*.py")}
    comp, orch = set(planmod.COMPUTING), set(planmod.ORCHESTRATION)
    assert comp | orch == stems and not comp & orch, sorted(stems ^ (comp | orch))
    for n in ("core", "labels", "analysis", "calibration", "model", "items", "corpus", "parents", "gates", "synthetic", "fetch", "plan", "stages", "rehearsal", "d0", "p0", "cost", "testing", "realcheck"):
        assert n in comp, n  # BASE values and panel slices (stages), calibration curves (rehearsal), data tables (d0), parents (p0), caps (plan, cost): all produce numbers
    assert orch == {"runner", "__init__"}  # supervision only: it cannot change a number
    ch = planmod.computing_hashes(REAL)
    assert set(ch) == {f"studies/p10i_s6/{n}.py" for n in comp} | {str(core.CONFIG)}
    assert not any("printing" in f for f in ch)


# ---- ruling 21
def spec21(**kw: Any) -> Spec:
    gd = {-1: 0.1, 0: 0.1005, 1: 0.101, 2: 0.1015, 3: 0.102, 4: 0.1025}
    gf = {k: v + 0.02 for k, v in gd.items()}
    return Spec(ArmSpec(gf, {k: 0.0005 for k in range(5)}), ArmSpec(gd, {k: 0.0005 for k in range(5)}), p_used=lambda k, c: 0.08, x_mean=lambda k, c: 0.08, **kw)


def test_a_failed_run_that_also_shows_an_integrity_break_reads_row_1() -> None:
    def row(**kw: Any) -> dict[str, Any]:
        return analysis.analyse(synthetic.registry(CFG, spec21(**kw)), synthetic.rate_table(4), CFG, k_max=4, bitwise=True)

    only_failed = row(failed=frozenset({(FLAT, 4, 0)}))
    assert only_failed["line_p"]["row"] == 2
    both = row(failed=frozenset({(FLAT, 4, 0)}), failed_keep=frozenset({(FLAT, 4, 0)}), bad_disabled=frozenset({(FLAT, 4, 0)}))
    assert both["line_p"]["row"] == 1 and 2 in both["line_p"]["cause_ids"] and both["r16"]["label"] == "NOT EVALUABLE"  # NOT EVALUABLE (the integrity cause), not MEMORY UNSTABLE
    clean_kept = row(failed=frozenset({(FLAT, 4, 0)}), failed_keep=frozenset({(FLAT, 4, 0)}))
    assert clean_kept["line_p"]["row"] == 2  # a produced snapshot that is clean does not change the row
    dense = row(failed=frozenset({(synthetic.DENSE, 4, 0)}), failed_keep=frozenset({(synthetic.DENSE, 4, 0)}), bad_disabled=frozenset({(synthetic.DENSE, 4, 0)}))
    assert dense["line_p"]["row"] == 1 and set(dense["line_p"]["cause_ids"]) >= {2, 3}


# ---- item 10 (b): the REAL r4 checker through seed_gate
def test_the_real_r4_seed_checker_through_seed_gate() -> None:
    g = gates.seed_gate(CFG, root=REAL)
    assert g["passed"] is True, g["problems"]
    assert g["checker"]["result_line"] == "RESULT: PASS" and g["checker"]["sha256"] == CFG["seed_ranges"]["checker_sha256"] and g["checker"]["own_allocation_rows"] == 12
    assert g["checker"]["own_globs"] == CFG["seed_ranges"]["own_globs"]


# ---- item 10 (a): the UNMODIFIED gates.sh through the real `uv run --locked` on a throw-away clone
def test_unmodified_gates_script_passes_the_preconditions_and_refuses_at_decision_2(pilot_env: Path) -> None:
    if subprocess.run(["git", "-C", str(REAL), "rev-parse", "--is-inside-work-tree"], capture_output=True, check=False).returncode != 0:  # noqa: S603, S607
        pytest.skip("a clone needs the code to be in a git work tree; every other test runs from a git archive copy")
    with testing.scratch("clone") as d:
        clone = d / "clone"
        subprocess.run(["git", "clone", "--no-local", "--quiet", str(REAL), str(clone)], check=True, capture_output=True, timeout=300)  # noqa: S603, S607
        head = subprocess.run(["git", "-C", str(clone), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()  # noqa: S603, S607
        env = {**os.environ, "UV_PROJECT_ENVIRONMENT": str(d / "venv"), "UV_OFFLINE": "1", "PYTHONDONTWRITEBYTECODE": "1"}
        script = clone / "studies/p10i_s6/launch/gates.sh"
        assert "exec uv run --locked python -m studies.p10i_s6.stages registered gates" in script.read_text()  # unmodified: the real wrapper
        r = subprocess.run([str(script), str(d / "run"), head], cwd=clone, env=env, capture_output=True, text=True, timeout=1500, check=False)  # noqa: S603
        assert r.returncode == 2, r.stdout[-800:] + r.stderr[-1500:]
        err = r.stderr
        assert "Decision 2" in err and "not clean" not in err and "not an ancestor" not in err and "platform of record" not in err and "requires --freeze-commit" not in err  # it got past the clean-tree, ancestor, frozen-files and platform checks
        status = subprocess.run(["git", "-C", str(clone), "status", "--porcelain", "--untracked-files=all"], capture_output=True, text=True, check=True).stdout  # noqa: S603, S607
        assert status == "" and sys.platform == "darwin"  # the refusal left the tree clean
