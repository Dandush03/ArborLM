# ruff: noqa: E501
"""P10S1, ADR-0021 section 25.15: the one-time extension of the load search (candidates 393,216 at 8K/1K and 786,432 at 32K/4K; 2K/256 unchanged), its 8 cells and snapshots, the item cap, U_L read from
the new runs alone over six candidates, the comparison with the first search, the refusal when a target exists, and the extended record read downstream. Nothing is trained here except the DRY
fixture's tiny runs. Self-check only: not independent review, not Astra validation, not human approval."""

import sys
import tomllib
from collections.abc import Callable
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402
from test_p10s1_rev5_budget import CPU, make_rates  # noqa: E402
from test_p10s1_rev5_calibration import write_cell  # noqa: E402
from test_p10s1_stages import dry  # noqa: E402, F401

from arborlm.io import file_sha256  # noqa: E402
from studies.p10s1 import budget, calibrate, core, stages  # noqa: E402
from studies.p10s1 import frozen as fz  # noqa: E402

OLD_8K = (65536, 98304, 131072, 196608, 262144)
OLD_32K = (131072, 196608, 262144, 393216, 524288)
UNIT = 16  # candidates scale by 16 / 8192 (8K/1K: 128, 192, 256, 384, 512, 768; 32K/4K: 256, 384, 512, 768, 1024, 1536)


def curve(points: dict[int, float]) -> Callable[[core.Cell, int], float]:
    """A step curve: the value of the last point at or below the update (the load rule reads i* as a running maximum)."""

    def fn(_cell: core.Cell, u: int) -> float:
        return points[max(k for k in points if k <= u)]

    return fn


# i at the scaled candidates and halves. Pass at 256 and 512 are the passes at 262,144 and 524,288 in 8K/1K's and 32K/4K's registered units (and at 512 / 768 = 393,216 at 8K/1K).
PASS_AT_TWO = {0: 0.0, 256: 1.0, 512: 1.95, 768: 1.97, 1024: 2.0}  # 32K/4K: passes at 1024 (524,288) and 1536 (786,432), not before
PASS_AT_TWO_8K = {0: 0.0, 192: 1.0, 256: 1.95, 384: 2.0}  # 8K/1K: fails at 384 (196,608) and before; passes at 512 and 768 (262,144 and 393,216)
PASS_ONLY_AT_CEILING_8K = {0: 0.0, 256: 0.5, 384: 1.85, 512: 1.88, 768: 1.9}  # passes at 768 only
PASS_ONLY_AT_CEILING_32K = {0: 0.0, 384: 0.5, 768: 1.85, 1024: 1.88, 1536: 1.9}  # passes at 1536 only


def write_extension(run: Path, fn_by_slots: dict[int, Callable[[core.Cell, int], float]], unit: int = UNIT, status: dict[str, str] | None = None) -> None:
    for c in core.load_extension_cells(unit):
        st = (status or {}).get(c.label, "completed")
        write_cell(run, c, fn_by_slots[c.slots], st, None if st == "completed" else "RuntimeError: x")


# --- 1. the candidates and ceilings --------------------------------------------------------------------------------------------------------------------
def test_new_candidates_and_ceilings_and_the_config_follows() -> None:
    assert core.LOAD_CANDIDATES["8K/1K"] == (*OLD_8K, 393216) and core.LOAD_CANDIDATES["32K/4K"] == (*OLD_32K, 786432)
    assert core.load_ceiling("8K/1K") == 393216 and core.load_ceiling("32K/4K") == 786432 and core.load_ceiling("2K/256") == 262144
    assert 393216 == round(262144 * 1.5) and 786432 == round(524288 * 1.5)  # each new candidate continues the ladder (x1.5 of the last)
    cfg = tomllib.loads(Path(core.repo_root() / core.DEFAULT_CONFIG).read_text())["calibration"]
    assert cfg["load_candidates_8k_1k"] == list(core.LOAD_CANDIDATES["8K/1K"]) and cfg["load_candidates_32k_4k"] == list(core.LOAD_CANDIDATES["32K/4K"]) and cfg["load_candidates_2k_256"] == list(OLD_8K)
    assert (cfg["load_ceiling_8k_1k"], cfg["load_ceiling_32k_4k"], cfg["load_ceiling_2k_256"]) == (393216, 786432, 262144)
    assert core.first_search_candidates("8K/1K") == OLD_8K and core.first_search_candidates("32K/4K") == OLD_32K  # the first search, as it ran


def test_2k_256_is_unchanged_in_cells_snapshots_and_caps() -> None:
    assert core.load_candidates("2K/256") == OLD_8K and core.load_candidates("2K/256", UNIT) == (128, 192, 256, 384, 512)
    first = {c.label: c for c in core.load_search_cells()}
    s256 = [c for c in first.values() if (c.facts, c.slots) == core.SATURATION_ONLY_CELL]
    assert len(s256) == 2 and {c.run_updates for c in s256} == {262144}
    assert not [c for c in core.load_extension_cells() if (c.facts, c.slots) == core.SATURATION_ONLY_CELL and c.arm]  # 2K/256 is not rerun
    for c in s256:
        assert calibrate.calibration_snapshots(c) == tuple(sorted({512 * 2**k for k in range(10)} | set(OLD_8K) | {x // 2 for x in OLD_8K}))
    reg = core.make_cell("P", "F-OQ", 2048, 256, 1, 2101, run_updates=262144)
    assert max(core.cell_snapshot_updates(reg, 8192)) == 262144 and 393216 not in core.cell_snapshot_updates(reg, 8192)
    assert core.loaded_marks("2K/256", 262144) == core.loaded_marks("2K/256", 393216)  # a longer run length adds nothing at 2K/256: it has no 393,216 candidate
    assert core.Plan(u_l=(131072, 131072), u_l_256=262144, sat256=True).u_l_256 == 262144
    with pytest.raises(ValueError):
        core.Plan(u_l=(131072, 131072), u_l_256=393216, sat256=True)  # 2K/256's U_L is one of its own five candidates


# --- 2. the 8 cells and their snapshots -----------------------------------------------------------------------------------------------------------------
def test_the_eight_extension_cells_and_their_snapshots() -> None:
    ext = core.load_extension_cells()
    assert len(ext) == 8 and {(c.arm, c.facts, c.slots, c.draw) for c in ext} == {(a, f, n, d) for a in ("F-OQ", "T-OQ") for f, n in core.LOADED_CELLS for d in (1, 2)}
    assert {c.run_updates for c in ext if c.slots == 1024} == {393216} and {c.run_updates for c in ext if c.slots == 4096} == {786432}
    assert {(c.draw, c.init_seed) for c in ext} == {(1, 2191), (2, 2193)} and all(c.kind == "CAL" and c.lr == core.LEARNING_RATE for c in ext)
    first = core.load_search_cells()
    assert not {c.label for c in ext} & {c.label for c in core.calibration_cells()}  # nothing existing is overwritten: the run length is part of the label
    assert all("_y" in c.label for c in ext)
    assert not {core.cell_dir(Path("x"), c.label) for c in ext} & {core.cell_dir(Path("x"), c.label) for c in first}
    for c in ext:
        cands = core.load_candidates(core.cell_name(c.facts, c.slots))
        assert len(cands) == 6 and cands[-1] == c.run_updates
        snaps = calibrate.calibration_snapshots(c)
        assert set(cands) <= set(snaps) and {x // 2 for x in cands} <= set(snaps) and {512 * 2**k for k in range(0, 11) if 512 * 2**k <= c.run_updates} <= set(snaps) and max(snaps) == c.run_updates
    # the first search's own snapshots stay what they were (every one of them is also an extension snapshot, which is what the comparison reads)
    f8 = next(c for c in first if c.arm == "F-OQ" and c.slots == 1024 and c.draw == 1)
    e8 = next(c for c in ext if c.arm == "F-OQ" and c.slots == 1024 and c.draw == 1)
    assert set(calibrate.calibration_snapshots(f8)) < set(calibrate.calibration_snapshots(e8)) and max(calibrate.calibration_snapshots(f8)) == 262144
    f32 = next(c for c in first if c.arm == "T-OQ" and c.slots == 4096 and c.draw == 2)
    e32 = next(c for c in ext if c.arm == "T-OQ" and c.slots == 4096 and c.draw == 2)
    assert set(calibrate.calibration_snapshots(f32)) < set(calibrate.calibration_snapshots(e32)) and max(calibrate.calibration_snapshots(f32)) == 524288
    assert core.calibration_cells_of(("load-ext",)) == ext and len(core.calibration_cells()) == 70  # the registered count of calibration runs is not the extension's
    stages.calibration_guard(ext[0], core.U_P)  # the calibration guard allows the extension's cells (and only them: see the universe)
    with pytest.raises(stages.CalibrationRefused):
        stages.calibration_guard(core.make_cell("CAL", "F-OQ", 8192, 1024, 1, 2191, run_updates=524288), core.U_P)


# --- the item cap --------------------------------------------------------------------------------------------------------------------------------------
def test_the_item_cap_is_twice_the_projected_dispatch_of_the_eight_runs_and_the_other_caps_do_not_move() -> None:
    wall = {(a, n): 0.01 * (1 + n / 4096) for a, ns in core.arm_slot_counts().items() for n in ns}
    ev = {(c.arm, c.facts, c.slots): 3.0 for c in core.calibration_cells()}
    proj = budget.item_projection(wall, startup_seconds=1.5, evaluation_seconds=ev)
    ordered = budget.dispatch_order(("load-ext",))
    assert [i for i, _c in ordered] == ["load-ext"] * 8 and [c.run_updates for _i, c in ordered] == sorted((c.run_updates for _i, c in ordered), reverse=True)
    times = budget.simulate_dispatch([1.5 + c.run_updates * wall[(c.arm, c.slots)] + 3.0 * len(calibrate.calibration_snapshots(c)) for _i, c in ordered], core.WORKERS)
    assert proj["load-ext"]["runs"] == 8 and proj["load-ext"]["projected_wall_seconds"] == pytest.approx(max(e for _s, e in times))
    assert proj["load-ext"]["cap_seconds"] == pytest.approx(2.0 * proj["load-ext"]["projected_wall_seconds"]) and proj["load-ext"]["missing_rates"] == []
    longest = max(c.run_updates * wall[(c.arm, c.slots)] for _i, c in ordered)
    assert proj["load-ext"]["projected_wall_seconds"] >= longest
    # the first search's items are projected from the first search's cells, exactly as before the extension
    before = budget.simulate_dispatch([1.5 + c.run_updates * wall[(c.arm, c.slots)] + 3.0 * len(calibrate.calibration_snapshots(c)) for _i, c in budget.dispatch_order(("row-up", "load"))], core.WORKERS)
    n_row = 12
    assert proj["load"]["projected_wall_seconds"] == pytest.approx(max(e for _s, e in before[n_row:])) and {c.run_updates for _i, c in budget.dispatch_order(("load",))} == {262144, 524288}
    partial = budget.item_projection({k: v for k, v in wall.items() if k != ("T-OQ", 4096)})
    assert partial["load-ext"]["cap_seconds"] is None and partial["load-ext"]["missing_rates"] == ["T-OQ|4096"]  # nothing starts on an assumed cost


# --- U_L from the extension over six candidates ---------------------------------------------------------------------------------------------------------
def test_u_l_is_read_from_the_new_runs_over_the_whole_six_candidate_ladder(tmp_path: Path) -> None:
    run = tmp_path / "cal"
    write_extension(run, {1024: curve(PASS_AT_TWO_8K), 4096: curve(PASS_AT_TWO)})
    load, returns = calibrate._load_block(run, UNIT, extension=True)
    assert load["8K/1K"]["u_l"] == core.scaled(393216, UNIT) and load["32K/4K"]["u_l"] == core.scaled(786432, UNIT) and returns == []
    assert load["8K/1K"]["arms"]["F-OQ"]["candidates"] == [128, 192, 256, 384, 512, 768] and load["32K/4K"]["status"] == "BOTH ARMS"
    # 786,432 at 32K/4K and 393,216 at 8K/1K are the registered values (unit 8192)
    assert core.scaled(393216, UNIT) * 8192 // UNIT == 393216
    # a pass only at the new ceiling is not a U_L: two consecutive candidates are required
    only = tmp_path / "only"
    write_extension(only, {1024: curve(PASS_ONLY_AT_CEILING_8K), 4096: curve(PASS_ONLY_AT_CEILING_32K)})
    load2, returns2 = calibrate._load_block(only, UNIT, extension=True)
    for name in ("8K/1K", "32K/4K"):
        assert load2[name]["u_l"] is None and load2[name]["action"] == calibrate.RETURN_TO_LEAD and load2[name]["status"] == calibrate.NOT_LOADED_WITHIN_CEILING and load2[name]["arms"]["F-OQ"]["failed_conditions"]
    assert len(returns2) == 2 and all("the record returns to the human lead" in r for r in returns2)
    # the same curve as a first search of five candidates would have found U_L at the old ceiling: the extension's rule is the unchanged rule on a longer ladder
    assert calibrate.arm_u_l(calibrate._views_of_arm(run, "F-OQ", 8192, 1024, UNIT, extension=True)[0], core.load_candidates("8K/1K", UNIT)[:5]) is None  # 8K/1K passes at 512 only within five
    # T-OQ without a U_L: F-OQ's stands and T-OQ is PREDICTED NOT LOADED, exactly as in item 0b
    mixed = tmp_path / "mixed"
    for c in core.load_extension_cells(UNIT):
        fn = curve(PASS_AT_TWO_8K if c.slots == 1024 else PASS_AT_TWO) if c.arm == "F-OQ" else curve(PASS_ONLY_AT_CEILING_8K if c.slots == 1024 else PASS_ONLY_AT_CEILING_32K)
        write_cell(mixed, c, fn)
    load3, _ = calibrate._load_block(mixed, UNIT, extension=True)
    assert load3["8K/1K"]["u_l"] == 768 and load3["8K/1K"]["toq_predicted_not_loaded"] and load3["8K/1K"]["status"] == "F-OQ ONLY"
    # a run stopped by its item cap or without a record is not 'not loaded'
    capped = tmp_path / "capped"
    victim = next(c for c in core.load_extension_cells(UNIT) if c.arm == "F-OQ" and c.slots == 1024 and c.draw == 2)
    for c in core.load_extension_cells(UNIT):
        if c.label == victim.label:
            write_cell(capped, c, curve(PASS_AT_TWO_8K), "failed", "ItemCapReached: stopped at update 5")
        else:
            write_cell(capped, c, curve(PASS_AT_TWO_8K if c.slots == 1024 else PASS_AT_TWO))
    load4, returns4 = calibrate._load_block(capped, UNIT, extension=True)
    assert load4["8K/1K"]["status"].startswith(f"F-OQ: {calibrate.STOPPED_BY_CAP}") and load4["8K/1K"]["u_l"] is None and load4["32K/4K"]["u_l"] == 1536 and any(calibrate.STOPPED_BY_CAP in r for r in returns4)


# --- the record: the comparison, the carried blocks, the note -------------------------------------------------------------------------------------------
def first_search_record(tmp: Path, unit: int, dry_flag: bool = True) -> tuple[Path, Path]:
    """A run directory holding the first search's 10 cells and 12 row cells (identical curves for the shared snapshots) and its items record."""
    run = tmp / "cal"
    for c in core.load_search_cells(unit):
        write_cell(run, c, curve({0: 0.0, 2: 0.5, 4: 1.0, 8: 1.5, 16: 1.9, 4096: 2.0}))
    for c in core.row_u_p_cells(unit):
        write_cell(run, c, lambda cell, u: 4.9)
    rec = calibrate.finalize_load_and_row_up(run, unit=unit, dry=dry_flag)
    path = run / stages.ITEMS_FILE
    core.write_record(path, core.jsonable({**core.envelope("calibration"), **rec, "items": ["load", "row-up"], "stage_complete": {"stage": "calibrate-load-row-up"}}))
    return run, path


def test_the_comparison_reports_every_shared_snapshot_and_the_largest_difference(tmp_path: Path) -> None:
    unit = 16
    run, first_path = first_search_record(tmp_path, unit)
    same = curve({0: 0.0, 2: 0.5, 4: 1.0, 8: 1.5, 16: 1.9, 4096: 2.0})
    write_extension(run, {1024: same, 4096: same}, unit)
    cmp_ = calibrate.compare_with_first_search(run, unit)
    assert cmp_["max_abs_difference_overall"] == pytest.approx(0.0, abs=1e-9) and cmp_["unreadable"] == []
    ent = cmp_["cells"]["8K/1K"]["F-OQ"]
    assert set(ent) == {"d1A", "d1B", "d2A", "d2B"} and set(cmp_["cells"]["32K/4K"]["T-OQ"]) == {"d1A", "d1B", "d2A", "d2B"}  # every arm, cell, draw and panel
    shared = set(calibrate.calibration_snapshots(next(c for c in core.load_search_cells(unit) if c.arm == "F-OQ" and c.slots == 1024))) & set(calibrate.calibration_snapshots(next(c for c in core.load_extension_cells(unit) if c.arm == "F-OQ" and c.slots == 1024)))
    assert {int(k) for k in ent["d1A"]["snapshots"]} == shared and ent["d1A"]["shared_snapshots"] == len(shared)
    one = ent["d1A"]["snapshots"][str(max(shared))]
    assert set(one) == {"first_i", "new_i", "abs_difference"} and one["first_i"] == pytest.approx(one["new_i"], abs=1e-9)
    # a difference at one shared snapshot is reported as measured, and is the maximum
    run2 = tmp_path / "second"
    run2.mkdir()
    for c in core.load_search_cells(unit):
        write_cell(run2, c, curve({0: 0.0, 2: 0.5, 4: 1.0, 8: 1.5, 16: 1.9, 4096: 2.0}))
    shifted = curve({0: 0.0, 2: 0.5, 4: 1.0, 8: 1.5, 16: 1.9, 24: 1.9, 4096: 2.0})
    victim = next(c for c in core.load_extension_cells(unit) if c.arm == "F-OQ" and c.slots == 1024 and c.draw == 1)
    for c in core.load_extension_cells(unit):
        write_cell(run2, c, (curve({0: 0.0, 2: 0.5, 4: 1.0, 8: 1.5, 16: 1.7, 4096: 2.0}) if c.label == victim.label else shifted) if c.slots == 1024 else same)
    cmp2 = calibrate.compare_with_first_search(run2, unit)
    assert cmp2["max_abs_difference_overall"] == pytest.approx(0.2, abs=2e-2) and cmp2["cells"]["8K/1K"]["F-OQ"]["d1A"]["max_abs_difference"] == pytest.approx(0.2, abs=2e-2)
    assert cmp2["cells"]["8K/1K"]["F-OQ"]["d2A"]["max_abs_difference"] == pytest.approx(0.0, abs=1e-9)
    # a first-search run that cannot be read is listed, never silently dropped
    run3 = tmp_path / "third"
    write_extension(run3, {1024: same, 4096: same}, unit)
    import shutil

    for c in core.load_search_cells(unit):
        if c.arm == "F-OQ" and c.slots == 1024 and c.draw == 1:
            shutil.rmtree(core.cell_dir(run3, c.label), ignore_errors=True)
    gone = calibrate.compare_with_first_search(run3, unit)["unreadable"]  # run3 never held the first search: all ten first runs are unreadable, none is dropped silently
    assert len(gone) == 8 and all("no train record" in g for g in gone)


def test_finalize_extension_writes_a_new_record_that_carries_the_first_one_and_the_note(tmp_path: Path) -> None:
    unit = 16
    run, first_path = first_search_record(tmp_path, unit)
    before = first_path.read_bytes()
    first = core.read_record(first_path, "calibration")
    write_extension(run, {1024: curve(PASS_AT_TWO_8K), 4096: curve(PASS_AT_TWO)}, unit)
    sha = file_sha256(first_path)
    rec = calibrate.finalize_load_extension(run, first, first_path.name, sha, unit=unit)
    assert rec["load"]["8K/1K"]["u_l"] == 768 and rec["load"]["32K/4K"]["u_l"] == 1536 and rec["returns_to_lead"] == []
    assert rec["row_u_p"] == first["row_u_p"] and rec["saturation_256"] == first["saturation_256"]  # verbatim
    assert rec["carried_over"]["from"] == stages.ITEMS_FILE and rec["carried_over"]["sha256"] == sha and set(rec["carried_over"]["blocks"]) == {"row_u_p", "saturation_256"}
    assert "comparison_with_first_search" in rec and rec["comparison_with_first_search"]["max_abs_difference_overall"] is not None
    assert "raised once" in rec["extension_note"] and "25.15" in rec["extension_note"] and "human lead" in rec["extension_note"]
    assert first_path.read_bytes() == before  # the first record is never touched
    # F-OQ again without a U_L: the cell returns to the human lead exactly as before, and nothing proposes a further candidate
    bad = tmp_path / "bad"
    bad.mkdir()
    for c in core.load_search_cells(unit):
        write_cell(bad, c, curve({0: 0.0, 2: 0.5, 4: 1.0, 8: 1.5, 16: 1.9, 4096: 2.0}))
    write_extension(bad, {1024: curve(PASS_ONLY_AT_CEILING_8K), 4096: curve(PASS_AT_TWO)}, unit)
    rec2 = calibrate.finalize_load_extension(bad, first, first_path.name, sha, unit=unit)
    assert rec2["load"]["8K/1K"]["status"] == calibrate.NOT_LOADED_WITHIN_CEILING and any("8K/1K" in r and "returns to the human lead" in r for r in rec2["returns_to_lead"]) and "further candidate" in rec2["extension_note"]


def test_the_cli_finalizes_the_extension_into_a_new_file_once_and_refuses_while_incomplete(tmp_path: Path) -> None:
    unit = stages.DRY_UNIT
    run, first_path = first_search_record(tmp_path, unit)
    first_bytes = first_path.read_bytes()
    common = ["--dry", "--run-dir", str(run), "--experiments-root", str(tmp_path), "--ledger-root", str(tmp_path)]
    assert stages.main(["calibrate", "--finalize-items", "load-ext,row-up", *common]) == 2 and not (run / stages.EXT_ITEMS_FILE).exists()  # no extension stage manifest: nothing is finalized while runs may be in progress
    ext = core.load_extension_cells(unit)
    flat = curve({0: 0.0, 2: 0.5, 4: 1.0, 8: 1.5, 16: 1.9, 4096: 2.0})
    for c in ext:
        write_cell(run, c, flat)
    core.write_record(run / "calibrate-load-ext" / "manifest.json", {**core.envelope("stage_manifest"), "tasks": [{"label": c.label, "status": "completed"} for c in ext]})
    code = stages.main(["calibrate", "--finalize-items", "load-ext,row-up", *common])
    new = run / stages.EXT_ITEMS_FILE
    assert new.is_file() and first_path.read_bytes() == first_bytes and code in (0, 1)
    rec = core.read_record(new, "calibration")
    assert rec["items"] == ["load-ext", "row-up"] and rec["carried_over"]["sha256"] == file_sha256(first_path) and rec["dry"] is True
    assert stages.main(["calibrate", "--finalize-items", "load-ext,row-up", *common]) == 2  # applied once
    assert stages.main(["calibrate", "--finalize-items", "load,row-up", *common]) == 2  # the first record is never overwritten
    assert stages.items_file_of(run) == new  # the later steps read the extended record
    # downstream: the row U_P map, and the final record, with the load block from the extension and the first search's rows
    assert calibrate.row_u_p_map(rec) == calibrate.row_u_p_map(core.read_record(first_path, "calibration"))


# --- refusal when a target exists; the cap record ---------------------------------------------------------------------------------------------------
def test_the_extension_refuses_to_start_if_any_target_exists_and_writes_nothing(tmp_path: Path) -> None:
    unit = stages.DRY_UNIT
    run = tmp_path / "cal"
    run.mkdir()
    preview = tmp_path / "timing_preview.json"
    wall = {f"{a}|{n}": 0.001 for a, ns in core.arm_slot_counts().items() for n in ns}
    core.write_record(preview, {**core.envelope("timing"), "preview": True, "status": "MEASURED", "wall_per_update": wall, "startup_seconds": 1.0, "evaluation_seconds": {}})
    argv = ["calibrate", "--dry", "--items", "load-ext", "--timing", str(preview), "--run-dir", str(run), "--experiments-root", str(tmp_path), "--ledger-root", str(tmp_path), "--workers", "6"]
    target = core.cell_dir(run, core.load_extension_cells(unit)[3].label)
    target.mkdir(parents=True)
    assert stages.main(argv) == 2
    assert [p.name for p in (run / "cells").iterdir()] == [target.name] and not (run / stages.EXT_CAP_FILE).exists() and not (run / "calibrate-load-ext").exists()
    assert stages.main([*argv[:-4], "--experiments-root", str(tmp_path)]) == 2  # same without the worker count
    # without --run-dir the extension would land in a new directory: refused
    assert stages.main(["calibrate", "--dry", "--items", "load-ext", "--timing", str(preview), "--experiments-root", str(tmp_path), "--ledger-root", str(tmp_path)]) == 2


def test_close_stage_and_the_item_groups_know_the_extension() -> None:
    assert stages.STAGE_ITEMS["calibrate-load-ext"] == ("load-ext",) and ("load-ext",) in stages.ITEM_GROUPS and budget.ITEM_GROUPS[-1] == ("load-ext",)
    assert stages.EXT_ITEMS_FILE != stages.ITEMS_FILE and stages.EXT_CAP_FILE.endswith(".json")


# --- the extended record accepted downstream -----------------------------------------------------------------------------------------------------------
def test_the_extended_record_feeds_the_plan_the_registered_snapshots_and_the_caps(tmp_path: Path) -> None:
    # a calibration record whose U_L are the new ceilings
    rec = {
        "returns_to_lead": [], "u_l": {"8K/1K": 393216, "32K/4K": 786432}, "saturation_256": {"runs": False, "u_l": None}, "toq_predicted_not_loaded": [],
        "row_u_p": {"2048": {"u_p": 8192}, "8192": {"u_p": 8192}, "32768": {"u_p": 16384}},
    }
    values = calibrate.plan_values(rec)
    plan = core.Plan(**values)
    assert plan.u_l == (393216, 786432)
    cell32 = next(c for c in core.registered_cells(plan) if c.arm == "F-OQ" and (c.facts, c.slots) == (32768, 4096) and c.draw == 1)
    cell8 = next(c for c in core.registered_cells(plan) if c.arm == "F-OQ" and (c.facts, c.slots) == (8192, 1024) and c.draw == 1)
    assert cell32.run_updates == 786432 and cell8.run_updates == 393216
    s32 = core.cell_snapshot_updates(cell32, 8192)
    assert {32768, 49152, 65536, 131072, 196608, 262144, 393216, 524288, 786432} <= set(s32) and max(s32) == 786432
    assert all(c // 2 in s32 for c in core.load_candidates("32K/4K"))  # every candidate's half
    s8 = core.cell_snapshot_updates(cell8, 8192)
    assert {196608, 262144, 393216} <= set(s8) and max(s8) == 393216 and 786432 not in s8
    fro = fz.Frozen.build(plan, CPU, dense_rates={"4096": 0.01, "16384": 0.03, "8K/1K": 0.003, "32K/4K": 0.01}, h8_undertrained=[], cuts=[])
    assert fz.Frozen.from_json(fro.as_json()).plan.u_l == (393216, 786432) and max(fro.snapshots(cell32)) == 786432
    table = budget.caps_table(make_rates(), budget.Fixed(60.0, 300.0, 60.0, 30.0, 30.0), CPU, base=plan)
    assert budget.cap_for(table, "train", plan) > 0 and budget.cap_for(table, "evaluate", plan) > 0
    # a U_L outside the candidates is still refused; the old ceilings are not the maximum any more
    with pytest.raises(ValueError):
        core.Plan(u_l=(393216, 1048576))
    with pytest.raises(ValueError):
        core.Plan(u_l=(524288, 786432))  # 524,288 is not a candidate at 8K/1K


def test_the_final_record_reads_the_load_block_from_the_extension(tmp_path: Path) -> None:
    unit = 16
    run, first_path = first_search_record(tmp_path, unit)
    write_extension(run, {1024: curve(PASS_AT_TWO_8K), 4096: curve(PASS_AT_TWO)}, unit)
    rows = dict.fromkeys(core.ROW_FACTS, unit)
    for c in core.h8_report_cells(rows, unit):
        write_cell(run, c, lambda cell, u: 0.95)
    for c in core.dense_rate_cells(rows, unit):
        write_cell(run, c, lambda cell, u: 0.2 + cell.lr)
    plain = calibrate.finalize(run, unit=unit, charged_seconds=1.0)
    ext = calibrate.finalize(run, unit=unit, charged_seconds=1.0, extended=True)
    assert plain["load_search"] == "first search" and ext["load_search"].startswith("extended") and ext["u_l"] == {"8K/1K": 768, "32K/4K": 1536}
    assert ext["row_u_p"] == plain["row_u_p"] and ext["saturation_256"] == plain["saturation_256"] and ext["returns_to_lead"] == []
    assert calibrate.plan_values({**ext, "dry": False})["u_l"] == (768, 1536)


# --- the DRY stage runs the extension end to end -----------------------------------------------------------------------------------------------------
def test_dry_runs_the_extension_and_the_later_steps_read_its_record(dry: dict[str, Any]) -> None:  # noqa: F811
    cal = dry["cal"]
    assert dry["summary"]["stages"]["calibrate-load-ext"] == 0 and dry["summary"]["stages"]["calibrate-finalize-ext"] == 0
    assert (cal / stages.EXT_ITEMS_FILE).is_file() and (cal / stages.ITEMS_FILE).is_file() and (cal / stages.EXT_CAP_FILE).is_file()
    ext = core.read_record(cal / stages.EXT_ITEMS_FILE, "calibration")
    assert ext["carried_over"]["sha256"] == file_sha256(cal / stages.ITEMS_FILE) and "comparison_with_first_search" in ext
    cap = core.read_record(cal / stages.EXT_CAP_FILE, "calibration_item_cap")
    assert cap["item"] == "load-ext" and cap["workers"] == 6 and cap["timing_preview_sha256"] == file_sha256(cal / "timing_preview.json")
    final = core.read_record(cal / "calibration.json", "calibration")
    assert final["load_search"].startswith("extended")
    assert len(list((cal / "cells").glob("CAL_*_y*"))) >= 8


# --- audit fixes: a refused launch leaves nothing behind; the calibration record carries the first record; ordering; messages -----------------------------
def real_size_launch(tmp_path: Path, run: Path, *extra: str) -> list[str]:
    preview = tmp_path / "timing_preview.json"
    if not preview.exists():
        wall = {f"{a}|{n}": 0.001 for a, ns in core.arm_slot_counts().items() for n in ns}
        ev = {f"{c.arm}|{c.facts}|{c.slots}": 1.0 for c in core.calibration_cells()}
        core.write_record(preview, {**core.envelope("timing"), "preview": True, "status": "MEASURED", "wall_per_update": wall, "startup_seconds": 1.0, "evaluation_seconds": ev})
    return ["calibrate", "--items", "load-ext", "--timing", str(preview), "--run-dir", str(run), "--experiments-root", str(tmp_path), "--ledger-root", str(tmp_path), *extra]


def test_a_refused_launch_leaves_nothing_behind_and_a_started_one_blocks_a_second(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    run = tmp_path / "cal"
    run.mkdir()
    core.write_record(run / stages.ITEMS_FILE, {**core.envelope("calibration"), "returns_to_lead": []})
    manifest = tmp_path / "s0.json"
    # (a) no --s0-training-manifest: refused by the evidence check, which runs after the cap is computed
    assert stages.main(real_size_launch(tmp_path, run)) == 2
    assert not (run / stages.EXT_CAP_FILE).exists() and not (run / "cells").exists()
    # (b) refused by the concurrency guard
    def busy(*_a: object, **_k: object) -> dict[str, Any]:
        raise stages.timing.OtherStudyRunning("a process of studies.p10s0 is alive")

    monkeypatch.setattr(stages.timing, "concurrency_check", busy)
    manifest.write_text("{}")
    assert stages.main(real_size_launch(tmp_path, run, "--s0-training-manifest", str(manifest))) == 2
    assert not (run / stages.EXT_CAP_FILE).exists() and not (run / "calibrate-load-ext").exists()
    # (c) a later launch is accepted: it gets as far as the pool, which is stubbed to stop; the cap file is written then, and a second launch is refused
    monkeypatch.setattr(stages.timing, "concurrency_check", lambda *a, **k: {"checked": True})
    monkeypatch.setattr(stages.timing, "validate_s0_evidence", lambda *a, **k: {"s0": "ok"})

    def stop(*_a: object, **_k: object) -> None:
        raise RuntimeError("pool reached")

    monkeypatch.setattr(stages.pool, "run_stage", stop)
    with pytest.raises(RuntimeError, match="pool reached"):
        stages.main(real_size_launch(tmp_path, run, "--s0-training-manifest", str(manifest)))
    assert (run / stages.EXT_CAP_FILE).is_file()
    assert stages.main(real_size_launch(tmp_path, run, "--s0-training-manifest", str(manifest))) == 2  # the extension is made once


def test_the_extension_refuses_without_the_first_items_record_and_names_the_file_read(tmp_path: Path) -> None:
    run = tmp_path / "cal"
    run.mkdir()
    assert stages.main(real_size_launch(tmp_path, run)) == 2 and not (run / stages.EXT_CAP_FILE).exists()


def test_finalize_waits_for_the_extended_items_record_and_copies_the_first_search_blocks(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    unit = stages.DRY_UNIT
    run, first_path = first_search_record(tmp_path, unit)
    common = ["--dry", "--run-dir", str(run), "--experiments-root", str(tmp_path), "--ledger-root", str(tmp_path)]
    flat = curve({0: 0.0, 2: 0.5, 4: 1.0, 8: 1.5, 16: 1.9, 4096: 2.0})
    for c in core.load_extension_cells(unit):
        write_cell(run, c, flat)
    assert stages.main(["calibrate", "--finalize", *common]) == 2 and not (run / "calibration.json").exists()  # extension runs exist, extended record does not
    assert stages.EXT_ITEMS_FILE in capsys.readouterr().err
    core.write_record(run / "calibrate-load-ext" / "manifest.json", {**core.envelope("stage_manifest"), "tasks": [{"label": c.label, "status": "completed"} for c in core.load_extension_cells(unit)]})
    stages.main(["calibrate", "--finalize-items", "load-ext,row-up", *common])
    ext = core.read_record(run / stages.EXT_ITEMS_FILE, "calibration")
    rows = dict.fromkeys(core.ROW_FACTS, unit)
    for c in core.h8_report_cells(rows, unit):
        write_cell(run, c, lambda cell, u: 0.95)
    for c in core.dense_rate_cells(rows, unit):
        write_cell(run, c, lambda cell, u: 0.2 + cell.lr)
    rec = calibrate.finalize(run, unit=unit, charged_seconds=1.0, extended=True, extended_items=ext)
    assert rec["row_u_p"] == ext["row_u_p"] and rec["saturation_256"] == ext["saturation_256"] and rec["first_items_record_sha256"] == file_sha256(first_path)
