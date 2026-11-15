# ruff: noqa: E501
"""P10S1 core (ADR-0021 sections 5 to 7, 10): the registry (30 configurations per replicate, 150 cells, the seed block, the overload row), labels, the seeds and gate G9, the config (the
charged-hour cap is a config value), the ledger, snapshots and exposures, the calibration cells, D-OQ's width, the work formulas, the identity hashes and the fixed launch scripts.
Unit-test seeds only (921001-921999); nothing is trained. Self-check only: not independent review, not Astra validation, not human approval."""

import ast
import os
import re
import subprocess
import sys
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from studies.p10s1 import core  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
ARMS = ("F-OQ", "T-OQ", "H8", "D-OQ", "R2")


# --- registry ------------------------------------------------------------------------------------------------------------------------
def test_thirty_configurations_and_150_cells() -> None:
    plan = core.Plan(seed_block_draws=())
    cells = core.registered_cells(plan)
    assert len(cells) == 150
    per = [c for c in cells if c.draw == 1]
    assert len(per) == 30 and {a: sum(1 for c in per if c.arm == a) for a in ARMS} == {"F-OQ": 7, "T-OQ": 7, "H8": 7, "D-OQ": 5, "R2": 4}
    assert {(c.facts, c.slots) for c in per if c.arm == "D-OQ"} == {(2048, 4096), (8192, 16384), (8192, 65536), (32768, 16384), (32768, 65536)}
    assert {(c.facts, c.slots) for c in per if c.arm == "R2"} == {(2048, 4096), (8192, 16384), (8192, 65536), (32768, 65536)}
    assert all(c.facts <= c.slots for c in cells if c.arm == "R2")
    assert {(c.facts, c.slots) for c in per if c.arm == "F-OQ"} == set(core.GRID_CELLS) and len(core.GRID_CELLS) == 7
    assert [c.draw for c in cells[:150:30]] == [1, 2, 3, 4, 5] and {c.init_seed for c in cells if c.draw == 3} == {2103}


def test_run_lengths_and_u_p() -> None:
    assert core.U_P == 8192
    for c in core.registered_cells(core.Plan(seed_block_draws=())):
        expected = 8192 if c.arm == "R2" else {4096: 6, 16384: 4, 65536: 2}[c.slots] * 8192
        assert c.run_updates == expected and c.u_p == 8192 and c.lr == 0.003


def test_seed_block_lane_l_and_overload_row() -> None:
    assert len(core.registered_cells(core.Plan(seed_block_draws=(1,)))) == 164 and len(core.registered_cells(core.Plan(seed_block_draws=(1, 2)))) == 178
    sb = [c for c in core.registered_cells(core.Plan(seed_block_draws=(1, 2))) if c.kind == "SB"]
    assert {(c.draw, c.init_seed) for c in sb} == {(1, 2111), (1, 2121), (2, 2112), (2, 2122)} and all(c.arm == "F-OQ" for c in sb) and len(sb) == 28
    lane = core.lane_cells()
    assert len(lane) == 15 and {c.run_updates for c in lane} == {8192, 32768} and {(c.facts, c.slots) for c in lane} == {(2048, 4096), (8192, 4096), (8192, 16384)}
    assert all(c.kind != "LN" for c in core.registered_cells(core.Plan()))  # lane L is off unless the freeze record enables it
    assert len([c for c in core.registered_cells(core.Plan(seed_block_draws=(), lane_l=True)) if c.kind == "LN"]) == 15
    over = core.registered_cells(core.Plan(overload_u_p=16384, seed_block_draws=()))
    extra = [c for c in over if c.facts == 65536]
    assert len(extra) == 40 and {c.arm for c in extra} == {"F-OQ", "T-OQ", "H8", "D-OQ", "R2"} and all(c.u_p == 16384 for c in extra)
    assert {(c.arm, c.slots) for c in extra if c.draw == 1} == {("F-OQ", 16384), ("F-OQ", 65536), ("T-OQ", 16384), ("T-OQ", 65536), ("H8", 16384), ("H8", 65536), ("D-OQ", 65536), ("R2", 65536)}
    assert {c.run_updates for c in extra if c.slots == 16384} == {4 * 16384} and {c.run_updates for c in extra if c.slots == 65536 and c.arm != "R2"} == {2 * 16384}
    assert core.Plan(overload_u_p=8192).steps[-1].name == "B3" and core.Plan().steps[-1].name == "B2"
    with pytest.raises(ValueError):
        core.Plan(overload_u_p=12345)
    with pytest.raises(ValueError):
        core.Plan(seed_block_draws=(2,))  # cut 1 removes draw 2 before draw 1
    with pytest.raises(ValueError):
        core.Plan(dense_cut=("8K/16K",))  # only the larger cell of a step may be cut


def test_cut3_removes_only_permitted_doq_cells() -> None:
    cells = core.registered_cells(core.Plan(seed_block_draws=(), dense_cut=("8K/64K", "32K/16K")))
    assert len(cells) == 150 - 10 and not any(c.arm == "D-OQ" and c.name in ("8K/64K", "32K/16K") for c in cells)
    assert sum(1 for c in cells if c.arm == "D-OQ") == 15


def test_labels_round_trip() -> None:
    every = [*core.registered_cells(core.Plan(seed_block_draws=(1, 2), lane_l=True)), *core.calibration_cells(True), *core.registered_cells(core.Plan(overload_u_p=8192, seed_block_draws=()))]
    for c in every:
        assert core.parse_label(c.label) == c
    t = core.make_cell("P", "F-OQ", 128, 4096, 1, 921101, run_updates=8, test=True)
    assert t.label.startswith("TEST_") and core.parse_label(t.label) == t
    dense = core.make_cell("P", "D-OQ", 8192, 16384, 2, 2102, lr=0.01)
    assert "lr0.01" in dense.label and core.parse_label(dense.label).lr == 0.01
    for bad in ("nonsense", "P_F-OQ_f1_n2", "P_F-OQ_f8192_n16384_d9", "Z_F-OQ_f8192_n4096_d1_i2101", "P_R2_f8192_n4096_d1_i2101"):
        with pytest.raises(ValueError):
            core.parse_label(bad)


# --- calibration --------------------------------------------------------------------------------------------------------------------
def test_calibration_cells() -> None:
    assert len(core.calibration_cells()) == 46 and len(core.calibration_cells(True)) == 50
    load = core.load_calibration_cells()
    assert len(load) == 16 and {(c.slots, c.facts) for c in load} == {(4096, f) for f in (8192, 16384, 32768, 65536)} | {(16384, f) for f in (8192, 32768, 65536, 131072)}
    assert {c.run_updates for c in load} == {65536} and {c.draw for c in load} == {1, 2} and {c.init_seed for c in core.calibration_cells(True)} == {2191}
    assert len(core.u_p_check_cells()) == 12 and len(core.h8_report_cells()) == 6 and len(core.dense_rate_cells()) == 12 and len(core.overload_u_p_cells()) == 4
    assert {c.lr for c in core.dense_rate_cells()} == {0.001, 0.003, 0.01} and {c.arm for c in core.overload_u_p_cells()} == {"F-OQ", "R2"}
    assert core.load_snapshots(4096) == (512, 1024, 2048, 4096, 8192, 16384, 24576, 32768, 49152, 65536)
    assert core.load_snapshots(16384) == (512, 1024, 2048, 4096, 8192, 16384, 32768, 65536)
    scaled = core.calibration_cells(unit=16)
    assert len(scaled) == 46 and all(c.u_p == 16 for c in scaled) and {c.run_updates for c in scaled if c.arm == "F-OQ" and c.facts != 65536 or c.slots == 4096} >= {128}


# --- seeds and G9 ------------------------------------------------------------------------------------------------------------------------
def test_seed_layout_and_g9() -> None:
    assert core.INIT_SEEDS == (2101, 2102, 2103, 2104, 2105) and core.REGISTERED_BASE == 210001
    assert [core.draw_base(r) for r in range(1, 6)] == [210001, 210101, 210201, 210301, 210401]
    s = core.registered_draw_seeds(2)
    assert s.name == "p10s1-draw-2" and s.facts == 210101 and s.null_seeds_a == (210121, 210122, 210123) and s.null_seeds_b == (210131, 210132, 210133)
    assert core.h8_seed(s) == 210141 and [core.mask_seed(s, k) for k in (0, 9)] == [210151, 210160] and core.index_seed(s) == 210161
    assert core.calibration_seeds(1).facts == 219001 and core.calibration_seeds(2).facts == 219101 and core.rehearsal_seeds().facts == 219201
    assert core.CALIBRATION_INIT_SEED == 2191 and core.REHEARSAL_INIT_SEED == 2192
    for k in range(9):
        assert core.TEST_SEED_BASE <= min(core.set_values(core.test_seeds(k))) and max(core.set_values(core.test_seeds(k))) <= core.TEST_SEED_TOP
    with pytest.raises(ValueError):
        core.test_seeds(9)
    r = core.seed_check()
    assert r["passed"] and not r["overlaps"] and r["legacy_config_seeds"] > 0
    ns = core.seed_namespaces()
    assert 3101 in ns["derived_init"] and 7105 in ns["derived_init"] and 2111 in ns["init"] and 3191 in ns["derived_init"]
    assert all(210001 <= v <= 219999 for k in ("registered", "calibration", "rehearsal") for v in ns[k])
    assert not core.seed_check(namespaces={**ns, "registered": ns["registered"] | {170001}})["passed"]  # a P9 seed
    assert not core.seed_check(namespaces={**ns, "registered": ns["registered"] | {190005}})["passed"]  # a P9-II seed
    assert not core.seed_check(namespaces={**ns, "registered": ns["registered"] | {200005}})["passed"]  # an S0 seed
    assert not core.seed_check(namespaces={**ns, "registered": ns["registered"] | {225000}})["passed"]  # an S2 seed
    assert not core.seed_check(namespaces={**ns, "registered": ns["registered"] | {2001}})["passed"]  # an S0 initialization seed
    assert not core.seed_check(namespaces={**ns, "init": ns["init"] | {1901}})["passed"]  # P9-II's initialization seed
    assert not core.seed_check(namespaces={**ns, "calibration": ns["calibration"] | set(ns["registered"])})["passed"]  # two S1 sets overlap


def test_seed_set_modes() -> None:
    core.check_seed_set("registered", "p10s1-draw-3")
    core.check_seed_set("calibration", "p10s1-cal-2")
    core.check_seed_set("calibration", "p10s1-test-0")
    core.check_seed_set("rehearsal", "p10s1-rehearsal")
    for mode, name in (("registered", "p10s1-cal-1"), ("registered", "p10s1-draw-6"), ("registered", "p10s1-test-0"), ("calibration", "p10s1-draw-1"), ("calibration", "p10s1-rehearsal"), ("rehearsal", "p10s1-cal-1"), ("rehearsal", "p10s1-draw-1"), ("registered", "p9ii-draw-1")):
        with pytest.raises(ValueError):
            core.check_seed_set(mode, name)
    with pytest.raises(ValueError):
        core.check_seed_set("other", "p10s1-draw-1")


# --- config, cap, ledger ------------------------------------------------------------------------------------------------------------
def test_config_matches_constants_and_the_cap_is_a_config_value(tmp_path: Path) -> None:
    text = (ROOT / core.DEFAULT_CONFIG).read_text()
    cap = tomllib.loads(text)["resources"]["cap_hours"]
    assert text == core.render_config_toml(cap) and core.render_config_toml() == core.render_config_toml(core.CAP_HOURS_DEFAULT) and cap == 16.0
    assert core.load_config()["resources"]["rss_aggregate_bytes"] == 18 * 1024**3 and core.load_config()["resources"]["workers"] == 6 and core.load_config()["resources"]["rss_worker_bytes"] == 3 * 1024**3
    assert core.cap_seconds() == cap * 3600.0
    other = tmp_path / "cap20.toml"
    other.write_text(core.render_config_toml(20.0))
    assert core.cap_seconds(other) == 20 * 3600.0  # the lead may change the cap: it is read, never hard-coded
    assert core.Ledger.from_config(tmp_path, other).cap_seconds == 20 * 3600.0
    tampered = tmp_path / "bad.toml"
    tampered.write_text(core.render_config_toml().replace("u_p = 8192", "u_p = 4096"))
    with pytest.raises(ValueError):
        core.load_config(tampered)
    for bad in ("cap_hours = 0.0", "cap_hours = -1.0", "cap_hours = 16"):
        broken = tmp_path / "broken.toml"
        broken.write_text(core.render_config_toml().replace("cap_hours = 16.0", bad))
        with pytest.raises(ValueError):
            core.load_config(broken)
    src = (ROOT / "studies" / "p10s1" / "core.py").read_text()
    assert "CAP_HOURS_DEFAULT" in src and not re.search(r"Ledger\([^)]*12", src)
    assert core.config_sha256() != core.config_sha256(other)


def test_ledger_charges_and_refuses(tmp_path: Path) -> None:
    ledger = core.Ledger(tmp_path / "l.json", 3600.0)
    assert ledger.remaining() == 3600.0 and ledger.charged() == 0.0
    ledger.require_room("a", 3600.0)
    ledger.charge("a", "run1", 1000.0)
    ledger.charge("b", "run2", 500.0)
    assert ledger.charged() == 1500.0 and ledger.remaining() == 2100.0 and len(ledger.entries()) == 2
    ledger.require_room("c", 2100.0)
    with pytest.raises(core.LedgerRefused):
        ledger.require_room("c", 2100.1)  # a stage refuses to start if the remaining cap is below its stage cap
    for bad in (0.0, -1.0, float("nan"), float("inf")):
        with pytest.raises(core.LedgerRefused):
            ledger.require_room("c", bad)
    ledger.charge("d", "run3", 99999.0)
    assert ledger.remaining() == 0.0
    with pytest.raises(ValueError):
        core.Ledger(tmp_path / "x.json", 0.0)
    (tmp_path / "other.json").write_text('{"study": "P9II", "kind": "ledger", "entries": []}')
    with pytest.raises(ValueError):
        core.Ledger(tmp_path / "other.json", 10.0).entries()


# --- snapshots, exposures ---------------------------------------------------------------------------------------------------------------------
def test_snapshots_and_exposures() -> None:
    assert core.snapshot_updates(8192, 49152) == (512, 1024, 2048, 4096, 8192, 16384, 24576, 32768, 49152)
    assert core.snapshot_updates(8192, 32768) == (512, 1024, 2048, 4096, 8192, 16384, 32768)
    assert core.snapshot_updates(8192, 16384) == (512, 1024, 2048, 4096, 8192, 16384)
    assert core.snapshot_updates(8192, 8192) == (512, 1024, 2048, 4096, 8192)
    assert core.snapshot_updates(8192, 49152, (10240, 12288, 49152)) == (512, 1024, 2048, 4096, 8192, 10240, 12288, 16384, 24576, 32768, 49152)
    assert core.snapshot_updates(8192, 16384, (40000,)) == (512, 1024, 2048, 4096, 8192, 16384)  # a matched-compute snapshot beyond the run is not a snapshot
    assert core.exposures_per_fact(8192, 8192) == 128.0 and core.exposures_per_fact(8192, 32768) == 32.0 and core.exposures_per_fact(8192, 2048) == 512.0
    assert core.me_updates(8192) == 2048 and core.me_updates(2048) == 512 and core.me_updates(32768) == 8192  # ME: U_P/4 at 8,192 facts, U_P/16 at 2,048
    assert core.multiple_of(8192, 1.25) == 10240
    with pytest.raises(ValueError):
        core.multiple_of(7, 1.25)


# --- D-OQ width, work formulas --------------------------------------------------------------------------------------------------------------
def test_doq_width_and_work_formulas() -> None:
    for n in core.SLOT_COUNTS:
        h = core.doq_hidden(n)
        assert abs(core.doq_trainable_parameters(h) - core.foq_trainable_parameters(n)) / core.foq_trainable_parameters(n) <= 0.001
    assert core.foq_trainable_parameters(4096) == 197633 and core.doq_hidden(4096) == 4033
    f = {n: core.work_formula("F-OQ", n)["W"] for n in core.SLOT_COUNTS}
    assert f == {4096: 66816, 16384: 263424, 65536: 1049856}
    t = {n: core.work_formula("T-OQ", n)["W"] for n in core.SLOT_COUNTS}
    assert t == {4096: 9728, 16384: 10496, 65536: 13568}
    assert core.work_formula("H8", 65536)["W"] == 1280 and core.work_formula("R2", 4096)["W"] == 1056 and core.work_formula("D-OQ", 4096)["W"] == 48 * 4033
    assert core.work_formula("F-OQ-IVF", 16384, candidates=600)["K"] == 64 + 600
    with pytest.raises(ValueError):
        core.work_formula("F-OQ-IVF", 16384)  # F-OQ-IVF's work is measured, not analytic


# --- identity ----------------------------------------------------------------------------------------------------------------------------
def test_source_hashes_cover_every_imported_module_and_script() -> None:
    hashes = core.source_hashes()
    for p in (ROOT / "studies" / "p10s1").glob("*.py"):
        assert f"studies/p10s1/{p.name}" in hashes
    for p in (ROOT / "studies" / "p10s1" / "launch").glob("*.sh"):
        assert f"studies/p10s1/launch/{p.name}" in hashes
    imported: set[tuple[str, str]] = set()
    for path in (ROOT / "studies" / "p10s1").glob("*.py"):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("studies.p9"):
                parts = node.module.split(".")
                pkg = parts[1]
                if len(parts) > 2:
                    imported.add((pkg, parts[2]))
                else:
                    imported.update((pkg, alias.name) for alias in node.names)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith("studies.p9"):
                        imported.add((alias.name.split(".")[1], alias.name.split(".")[2] if alias.name.count(".") > 1 else "__init__"))
    listed = {("p9", m) for m in core.IMPORTED_P9_MODULES} | {("p9i", m) for m in core.IMPORTED_P9I_MODULES} | {("p9ii", m) for m in core.IMPORTED_P9II_MODULES}
    assert imported <= listed, sorted(imported - listed)
    assert core.source_digest() == core.source_digest() and len(core.code_identity()) == 4


def test_no_existing_file_is_edited_and_p9_modules_are_imported_not_patched() -> None:
    status = subprocess.run(["git", "-C", str(ROOT), "status", "--porcelain"], capture_output=True, text=True, check=True).stdout.splitlines()
    protected = ("src/", "uv.lock", "pyproject.toml", "studies/p9", "supplements/", "docs/decisions/", "experiments/")
    own = ("studies/p10s1/", "configs/p10s1_capacity.toml", "tests/test_p10s1_", "docs/decisions/ADR-0021")
    touched = [line for line in status if line[3:].startswith(protected) and not line[3:].startswith(own)]
    assert not touched, touched  # only the paths P1-P9 own are checked: an unrelated untracked file (a review folder, results) does not fail the test (audit m5)
    other_configs = [line for line in status if line[3:].startswith("configs/") and not line[3:].startswith(own)]
    assert not other_configs, other_configs
    text = " ".join(p.read_text() for p in (ROOT / "studies" / "p10s1").glob("*.py"))
    assert "monkeypatch" not in text.replace("no monkeypatching", "") and "setattr(p9" not in text and "mock.patch" not in text


def test_stage_codes_and_run_names() -> None:
    n = core.run_name("calibrate", unique="abc")
    assert n.startswith("P10S1C-") and core.parse_run_name(n)[0] == "calibrate" and core.run_name("dry", unique="x").startswith("P10S1D-")
    with pytest.raises(ValueError):
        core.run_name("stage1")
    with pytest.raises(ValueError):
        core.parse_run_name("P9IIC-20261115T000000000000Z-x")
    assert core.default_experiments_root().name == "experiments"


# --- the fixed launch scripts -----------------------------------------------------------------------------------------------------------------
STAGES = ("gates", "train", "evaluate", "timing", "simulate", "analysis", "report")


def test_launch_scripts_are_fixed_and_complete() -> None:
    launch = ROOT / "studies" / "p10s1" / "launch"
    assert {p.name for p in launch.glob("*.sh")} == {f"{s}.sh" for s in (*STAGES, "generate")}
    for s in STAGES:
        text = (launch / f"{s}.sh").read_text()
        assert os.access(launch / f"{s}.sh", os.X_OK) and text.startswith("#!/bin/sh\n") and "set -eu" in text
        assert '[ "$#" -ne 2 ]' in text and "exit 2" in text  # exactly two arguments: the run directory and the freeze commit
        assert f"studies.p10s1.stages registered {s} " in text and '--run-dir "$RUN_DIR"' in text and '--freeze-commit "$FREEZE_COMMIT"' in text
        assert "--caps studies/p10s1/freeze/stage_caps.json" in text  # every stage cap comes from the frozen table
        assert "eval " not in text and "$@" not in text and "$*" not in text
        assert re.search(r'exec uv run --locked python -m studies\.p10s1\.stages registered \w+ --run-dir "\$RUN_DIR" --freeze-commit "\$FREEZE_COMMIT" --caps \S+$', text.strip().splitlines()[-1])
    gen = (launch / "generate.sh").read_text()
    assert "--mode registered" in gen and "--i-understand-freeze-time" in gen and "--stage-cap-seconds" not in gen and "for k in 1 2 3 4 5" in gen and 'HEAD' in gen and "git status --porcelain" in gen
    from studies.p10s1 import stages

    assert set(STAGES) == set(stages.REGISTERED_STAGES) and stages.CAPS_FILE == "studies/p10s1/freeze/stage_caps.json"


def test_launch_scripts_refuse_a_wrong_number_of_arguments_and_unfrozen_runs(tmp_path: Path) -> None:
    for s in (*STAGES, "generate"):
        for argv in ([], ["only-one"], ["a", "b", "c"]):
            r = subprocess.run(["sh", str(ROOT / "studies" / "p10s1" / "launch" / f"{s}.sh"), *argv], capture_output=True, text=True, check=False)
            assert r.returncode == 2 and "usage:" in r.stderr, (s, argv, r.stderr)
    # two arguments: the driver itself refuses (no plan, no clean freeze commit): exit 2, nothing runs, no run directory is created
    r = subprocess.run(["sh", str(ROOT / "studies" / "p10s1" / "launch" / "train.sh"), str(tmp_path / "run"), "deadbeef"], capture_output=True, text=True, check=False, cwd=ROOT)
    assert r.returncode == 2 and "REFUSED" in r.stderr and not (tmp_path / "run").exists()
    r = subprocess.run(["sh", str(ROOT / "studies" / "p10s1" / "launch" / "generate.sh"), str(tmp_path / "run"), "deadbeef"], capture_output=True, text=True, check=False, cwd=ROOT)
    assert r.returncode == 2 and not (tmp_path / "run").exists()
