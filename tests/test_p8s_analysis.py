"""ADR-0016 gate 4: a synthetic 60-cell run of the supplementary analysis and writers, the labels of
section 5, the allowed-difference comparison of W5, and the supplementary provenance check."""

import copy
import csv
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402
from p8_fake import Spec, make_cells  # noqa: E402

from arborlm import p8_analysis as an  # noqa: E402
from arborlm import p8_core as core  # noqa: E402
from arborlm.io import file_sha256, read_json, write_json  # noqa: E402
from supplements.p8s import analysis, common  # noqa: E402
from supplements.p8s import synthetic as syn  # noqa: E402

FIVE = common.SUPPLEMENT_CELLS
HEADER = f"# {common.SUPPLEMENT_LABEL}"


def _cells60() -> dict[str, an.CellData]:
    """Synthetic 60 cells; C04/C05 fail the quality guard; the five supplement cells are the
    single-set (fully collapsed, m = 0 everywhere) records, the rest of the 12 are ordinary."""
    specs = {("C04", "*"): Spec(gain=0.0), ("C05", "*"): Spec(gain=0.0)}
    cells = make_cells(specs)
    for label in FIVE:
        data = cells[label]
        cells[label] = an.CellData(data.cell, data.eval, syn.collapse_sim_record(data.sim))
    return cells


def _write_registered(path: Path, cells: dict[str, an.CellData]) -> None:
    """What ``run_analysis`` writes for the 55-cell, INCOMPLETE case."""
    registered = {k: v for k, v in cells.items() if k not in FIVE}
    missing = [{"label": label, "reasons": ["sim.json missing"]} for label in FIVE]
    result = an.analyse(registered, missing)
    result["dry_run"] = False
    result["inputs"] = {"eval_run": "synthetic"}
    path.mkdir(parents=True)
    write_json(path / "analysis.json", an.jsonable(result))
    an.write_csv(path / "scorecard.csv", *an.scorecard_rows(an.clean_scorecard_source(result)))
    an.write_csv(path / "cells.csv", *an.cells_rows(registered))
    an.write_csv(path / "pairs.csv", *an.pairs_rows(registered))


@pytest.fixture(scope="module")
def run_dir(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Path]:
    root = tmp_path_factory.mktemp("p8sa")
    cells = _cells60()
    _write_registered(root / "registered", cells)
    out = analysis.write_outputs(cells, [], root / "registered", root / "out", {"synthetic": True})
    return root, out


def test_synthetic_60_cell_run_completes_and_labels(run_dir: tuple[Path, Path]) -> None:
    _, out = run_dir
    wrapper = json.loads((out / "supplementary_analysis.json").read_text())
    assert wrapper["label"] == "SUPPLEMENTARY (ADR-0016) — not the registered P8 output"
    assert wrapper["registered_study_status"] == "INCOMPLETE"
    assert wrapper["registered_decision"] == "none"
    assert "60-record supplementary input only" in wrapper["note"]
    nested = wrapper["supplementary_analysis"]
    assert nested["study_status"] == "COMPLETE" and nested["cells_with_complete_records"] == 60
    assert nested["missing_cells"] == []
    assert "dry_run" not in nested and "inputs" not in nested
    for name in ("cells.csv", "pairs.csv", "scorecard.csv"):
        assert (out / name).read_text().splitlines()[0] == HEADER
    md = (out / "SUPPLEMENTARY_ANALYSIS.md").read_text()
    assert md.splitlines()[0] == f"# {common.SUPPLEMENT_LABEL}"
    assert "INCOMPLETE" in md and "not the registered study's" in md
    manifest = read_json(out / "manifest.json")
    assert all(file_sha256(out / n) == h for n, h in manifest["outputs"].items())


def test_comparison_with_registered_passes_with_exactly_the_allowed_differences(
    run_dir: tuple[Path, Path],
) -> None:
    _, out = run_dir
    cmp = json.loads((out / "supplementary_analysis.json").read_text())[
        "comparison_with_registered"
    ]
    assert cmp["analysis"]["ok"] and cmp["analysis"]["disallowed_count"] == 0
    seen = set(cmp["analysis"]["allowed_differences_seen"])
    assert {"study_status", "cells_with_complete_records", "missing_cells"} <= seen
    assert {"cases.C04", "cases.C05"} <= seen
    assert seen <= {
        "study_status",
        "cells_with_complete_records",
        "missing_cells",
        "cases.C04",
        "cases.C05",
        "decision_inputs",
    }
    assert cmp["csv"]["ok"]
    assert cmp["csv"]["cells.csv"]["rows_of_new_cells"] == 5 * 2 * 4
    assert cmp["csv"]["scorecard.csv"]["study_status_column"] == ["COMPLETE"]


def test_predictions_are_checked_and_written(run_dir: tuple[Path, Path]) -> None:
    _, out = run_dir
    wrapper = json.loads((out / "supplementary_analysis.json").read_text())
    preds = wrapper["predictions_check"]["predictions"]
    assert sorted(preds) == [str(i) for i in range(1, 10)]
    for number in ("1", "2", "3", "4", "5", "6", "7", "9"):
        assert preds[number]["holds"], (number, preds[number])
    assert preds["9"]["checked"] == 1
    md = (out / "SUPPLEMENTARY_ANALYSIS.md").read_text()
    assert "Predictions of ADR-0016 section 2" in md
    nested = wrapper["supplementary_analysis"]
    assert nested["decision_inputs"]["section_8_option_indicated"] == "c"
    for case in ("C04", "C05"):
        assert nested["cases"][case]["study_classification"]["class"] == "QUALITY-FAILED"


def test_a_difference_outside_the_allowed_set_stops(tmp_path: Path) -> None:
    cells = _cells60()
    _write_registered(tmp_path / "registered", cells)
    changed = copy.deepcopy(cells["b101-o301-s601-C06"].sim)
    changed["panels"]["A"]["streams"]["actual"]["L-COAX|R2"]["by_c"]["32"]["asc"][
        "misses_warm"
    ] += 900
    cells["b101-o301-s601-C06"] = an.CellData(
        cells["b101-o301-s601-C06"].cell, cells["b101-o301-s601-C06"].eval, changed
    )
    with pytest.raises(common.SupplementError, match="STOP"):
        analysis.write_outputs(cells, [], tmp_path / "registered", tmp_path / "out", {})
    assert not (tmp_path / "out").exists()  # nothing written


def test_incomplete_supplement_is_refused(tmp_path: Path) -> None:
    cells = _cells60()
    _write_registered(tmp_path / "registered", cells)
    with pytest.raises(common.SupplementError, match="incomplete"):
        analysis.write_outputs(
            cells,
            [{"label": FIVE[0], "reasons": ["x"]}],
            tmp_path / "registered",
            tmp_path / "out",
            {},
        )


def test_diff_paths_and_allowed_rule() -> None:
    a = {"x": 1, "cases": {"C04": {"v": 1}, "C06": {"v": 1}}, "l": [1, {"k": 2}]}
    b = {"x": 1, "cases": {"C04": {"v": 2}, "C06": {"v": 1}}, "l": [1, {"k": 3}]}
    paths = analysis.diff_paths(a, b)
    assert ("cases", "C04", "v") in paths and ("l", 1, "k") in paths
    assert analysis.is_allowed(("cases", "C04", "v")) and analysis.is_allowed(("cases", "C05"))
    assert not analysis.is_allowed(("cases", "C06", "v"))
    assert not analysis.is_allowed(("decision_inputs", "open_questions"))
    assert analysis.is_allowed(("decision_inputs", "section_8_reason"))
    assert not analysis.is_allowed(("concentration_controls_bind",))
    assert analysis.diff_paths({"a": 1}, {"a": 1, "b": 2}) == [("b",)]
    assert analysis.diff_paths({"a": [1]}, {"a": [1, 2]}) == [("a",)]
    comp = analysis.compare_analysis(
        {"dry_run": False, "inputs": {}, "concentration_controls_bind": False},
        {"concentration_controls_bind": True},
    )
    assert not comp["ok"] and comp["disallowed_differences"] == ["concentration_controls_bind"]


def test_csv_comparison_detects_changes_outside_the_allowed_rows(
    run_dir: tuple[Path, Path], tmp_path: Path
) -> None:
    root, out = run_dir
    registered = root / "registered"
    assert analysis.compare_csvs(registered, out)["ok"]
    for name, edit in (("cells.csv", "label"), ("pairs.csv", "case"), ("scorecard.csv", "case")):
        bad = tmp_path / name.replace(".", "_")
        bad.mkdir()
        for n in ("cells.csv", "pairs.csv", "scorecard.csv"):
            (bad / n).write_text((out / n).read_text())
        lines = (bad / name).read_text().splitlines()
        header = next(csv.reader([lines[1]]))
        idx = header.index(edit)
        # corrupt the first body row whose case/label is not among the allowed ones
        for i in range(2, len(lines)):
            row = next(csv.reader([lines[i]]))
            if row[idx] not in (*FIVE, "C04", "C05"):
                row[-1] = row[-1] + "9"
                lines[i] = ",".join(row)
                break
        (bad / name).write_text("\n".join(lines) + "\n")
        verdict = analysis.compare_csvs(registered, bad)
        assert not verdict["ok"] and not verdict[name]["ok"], name


def _fake_sim(label: str, eval_path: Path) -> dict[str, Any]:
    return {
        "outcome": "completed",
        "label": label,
        "panels": {"A": {}, "B": {}},
        "eval_json_sha256": file_sha256(eval_path),
    }


def test_load_cell_data_reasons_match_the_frozen_loader(tmp_path: Path) -> None:
    eval_run, sim_run, sup_run = tmp_path / "e", tmp_path / "s", tmp_path / "u"
    labels = core.all_labels()
    for label in (labels[0], labels[1], FIVE[0]):
        (eval_run / "cells" / label).mkdir(parents=True)
        write_json(
            eval_run / "cells" / label / "eval.json", {"outcome": "completed", "label": label}
        )
    for label, run in ((labels[0], sim_run), (FIVE[0], sup_run)):
        (run / "cells" / label).mkdir(parents=True)
        write_json(
            run / "cells" / label / "sim.json",
            _fake_sim(label, eval_run / "cells" / label / "eval.json"),
        )
    (sim_run / "cells" / labels[1]).mkdir(parents=True)
    bad = _fake_sim(labels[1], eval_run / "cells" / labels[1] / "eval.json")
    bad["eval_json_sha256"] = "0" * 64
    write_json(sim_run / "cells" / labels[1] / "sim.json", bad)
    cells, missing = analysis.load_cell_data(eval_run, sim_run, sup_run)
    assert set(cells) == {labels[0], FIVE[0]}
    reasons = {m["label"]: m["reasons"] for m in missing}
    assert len(missing) == 58
    assert reasons[labels[1]] == ["sim.json was built from a different eval.json"]
    assert reasons[labels[2]] == ["eval.json missing", "sim.json missing"]
    # without a supplement run the five labels are looked up in the registered sim run (missing)
    cells2, missing2 = analysis.load_cell_data(eval_run, sim_run, None)
    assert FIVE[0] not in cells2 and len(missing2) == 59


def _provenance_fixture(tmp_path: Path) -> tuple[Path, Path]:
    eval_run, sup = tmp_path / "eval", tmp_path / "sup"
    freeze = {"commit": "a" * 40, "tree": "b" * 40}
    for label in FIVE:
        (eval_run / "cells" / label).mkdir(parents=True)
        eval_path = eval_run / "cells" / label / "eval.json"
        write_json(eval_path, {"outcome": "completed", "label": label})
        (sup / "cells" / label).mkdir(parents=True)
        write_json(
            sup / "cells" / label / "sim.json",
            {
                **_fake_sim(label, eval_path),
                "supplement": "ADR-0016",
                "supplement_spec_sha256": common.supplement_spec_sha256(),
                "supplement_source_sha256": common.supplement_source_digest(),
                "supplement_freeze_commit": freeze,
                "source_sha256": common.FROZEN_SOURCE_DIGEST,
                "frozen_inputs": {
                    "source_sha256": common.FROZEN_SOURCE_DIGEST,
                    "p7b_reproduction_record_cited": common.p7b_reproduction_record_cited(),
                },
            },
        )
    write_json(
        sup / "manifest.json",
        {
            "status": "completed",
            "cells_completed": 5,
            "supplement_spec_sha256": common.supplement_spec_sha256(),
            "supplement_freeze_commit": freeze,
            "p7b_reproduction_record_cited": common.p7b_reproduction_record_cited(),
            "wall_seconds": 12.0,
        },
    )
    return eval_run, sup


def test_supplement_provenance_accepts_a_consistent_set_and_refuses_changes(tmp_path: Path) -> None:
    eval_run, sup = _provenance_fixture(tmp_path)
    ok = analysis.check_supplement_provenance(sup, eval_run)
    assert ok["p7b_reproduction_record_cited"] == common.p7b_reproduction_record_cited()
    assert ok["supplement_freeze_commit"]["tree"] == "b" * 40 and ok["stage_wall_seconds"] == 12.0
    target = sup / "cells" / FIVE[2] / "sim.json"
    original = read_json(target)
    for key, value in (
        ("supplement_spec_sha256", "0" * 64),
        ("supplement_source_sha256", "0" * 64),
        ("source_sha256", "0" * 64),
        ("eval_json_sha256", "0" * 64),
        ("supplement_freeze_commit", {"commit": "c" * 40, "tree": "d" * 40}),  # inconsistent
        ("supplement_freeze_commit", {"commit": "a" * 40}),  # no tree hash
        ("supplement", "ADR-0015"),
    ):
        write_json(target, {**original, key: value})
        with pytest.raises(common.SupplementError):
            analysis.check_supplement_provenance(sup, eval_run)
    # the cited P7-B reproduction record must be present and equal in every record and the manifest
    stale = {"sha256": "0" * 64, "status": "x", "source": "y"}
    stale_inputs = {**original["frozen_inputs"], "p7b_reproduction_record_cited": stale}
    write_json(target, {**original, "frozen_inputs": stale_inputs})
    with pytest.raises(common.SupplementError, match="p7b_reproduction_record_cited"):
        analysis.check_supplement_provenance(sup, eval_run)
    write_json(target, original)
    manifest = read_json(sup / "manifest.json")
    write_json(sup / "manifest.json", {**manifest, "p7b_reproduction_record_cited": stale})
    with pytest.raises(common.SupplementError, match="p7b_reproduction_record_cited"):
        analysis.check_supplement_provenance(sup, eval_run)
    write_json(sup / "manifest.json", manifest)
    (sup / "cells" / FIVE[0] / "sim.json").unlink()
    with pytest.raises(common.SupplementError, match="no supplementary sim.json"):
        analysis.check_supplement_provenance(sup, eval_run)


def test_records_from_the_real_simulation_path_run_through_analysis_and_predictions(
    tmp_path: Path,
) -> None:
    """The five cells simulated from synthetic single-set traces by ``simulate_cell_s`` (the real
    code path, real record shape) replace the collapsed stand-ins; the analysis, the W5 comparison
    and predictions 1-4, 6 and 7 all work on them. (Evaluation records stay synthetic.)"""
    from arborlm.p7a_trace import configure_deterministic_cpu
    from supplements.p8s import null
    from supplements.p8s import sim as ssim

    configure_deterministic_cpu()
    cells = _cells60()
    for label in FIVE:
        cell = core.parse_label(label)
        eval_dir = syn.write_single_set_cell(tmp_path / "eval", cell)
        out_dir = tmp_path / "sim" / label
        out_dir.mkdir(parents=True)
        record = ssim.simulate_cell_s(cell, eval_dir, out_dir, null.supplement_null_provider)
        cells[label] = an.CellData(cell, cells[label].eval, record)
    _write_registered(tmp_path / "registered", cells)
    out = analysis.write_outputs(cells, [], tmp_path / "registered", tmp_path / "out", {})
    wrapper = json.loads((out / "supplementary_analysis.json").read_text())
    assert wrapper["comparison_with_registered"]["analysis"]["ok"]
    assert wrapper["comparison_with_registered"]["csv"]["ok"]
    preds = wrapper["predictions_check"]["predictions"]
    for number in ("1", "2", "3", "4", "6", "7"):
        assert preds[number]["holds"], (number, preds[number])
    # m = 0 everywhere for the five cells, E undefined
    for label in FIVE:
        data = cells[label]
        assert data.m("A", 2, "asc", "L-COAX") == 0 and data.m("B", 8, "desc", "L-FREQ") == 0
        assert data.e("A", 2, "asc", "L-COAX")[0] is None


def test_wrapper_cites_the_p7b_reproduction_record_and_is_utf8(run_dir: tuple[Path, Path]) -> None:
    _, out = run_dir
    raw = (out / "supplementary_analysis.json").read_bytes()
    wrapper = json.loads(raw.decode("utf-8"))
    assert wrapper["p7b_reproduction_record_cited"] == common.p7b_reproduction_record_cited()
    assert (
        "—" in raw.decode("utf-8") and "—".encode() in raw
    )  # em dash stored as UTF-8, not escaped


def test_nan_is_refused_and_the_failure_is_recorded(tmp_path: Path) -> None:
    cells = _cells60()
    _write_registered(tmp_path / "registered", cells)
    with pytest.raises(ValueError, match="Out of range float"):
        analysis.write_outputs(
            cells, [], tmp_path / "registered", tmp_path / "out", {"bad": float("nan")}
        )
    (folder,) = (tmp_path / "out").iterdir()
    failed = json.loads((folder / "failed.json").read_text(encoding="utf-8"))
    assert failed["status"] == "FAILED" and failed["exception_type"] == "ValueError"
    assert "Out of range float" in failed["exception_message"]
    assert "Traceback" in failed["traceback"]


def test_main_records_an_unexpected_exception_then_reraises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(*_: object, **__: object) -> Path:
        raise KeyError("malformed record")

    monkeypatch.setattr(analysis, "run", boom)
    out_root = tmp_path / "out"
    with pytest.raises(KeyError):
        analysis.main(["--supplement-run", str(tmp_path), "--out-root", str(out_root)])
    (stopped,) = out_root.glob("STOPPED-*.json")
    record = json.loads(stopped.read_text(encoding="utf-8"))
    assert (
        record["exception_type"] == "KeyError" and "malformed record" in record["exception_message"]
    )
    assert "Traceback" in record["traceback"]


def _pred_inputs() -> dict[str, an.CellData]:
    return _cells60()


def test_pred_8_checks_both_halves() -> None:
    good = {"concentration_controls_bind": False, "open_questions": [{"case": "C09"}]}
    assert analysis.pred_8(good)["holds"]
    for bad in (
        {**good, "concentration_controls_bind": True},
        {**good, "concentration_controls_bind": None},
        {**good, "open_questions": []},
        {**good, "open_questions": [{"case": "C09"}, {"case": "C10"}]},
        {**good, "open_questions": [{"case": "C10"}]},
    ):
        result = analysis.pred_8(bad)
        assert not result["holds"] and result["violation_count"] >= 1


def test_pred_2_fails_on_an_empty_or_different_key_set() -> None:
    cells = _pred_inputs()
    assert analysis.pred_2(cells)["holds"]
    label = FIVE[0]
    for stream in ("order_shuffled", "null_2"):
        mutated = copy.deepcopy(cells[label].sim)
        mutated["panels"]["A"]["streams"][stream] = {}  # vacuous: nothing to compare
        broken = {**cells, label: an.CellData(cells[label].cell, cells[label].eval, mutated)}
        result = analysis.pred_2(broken)
        assert not result["holds"] and result["violation_count"] >= 1
    mutated = copy.deepcopy(cells[label].sim)
    streams = mutated["panels"]["B"]["streams"]
    streams["null_1"].pop("L-FREQ|R8")  # a key is missing from one stream
    broken = {**cells, label: an.CellData(cells[label].cell, cells[label].eval, mutated)}
    assert not analysis.pred_2(broken)["holds"]
    mutated = copy.deepcopy(cells[label].sim)
    streams = mutated["panels"]["B"]["streams"]
    streams["null_1"]["L-ID|R2"] = copy.deepcopy(streams["null_1"]["L-FREQ|R2"])  # an extra key
    broken = {**cells, label: an.CellData(cells[label].cell, cells[label].eval, mutated)}
    assert not analysis.pred_2(broken)["holds"]
    assert analysis.expected_layout_keys("flat") == analysis.expected_layout_keys("tree") == {
        "L-FREQ|R2", "L-COAX|R2", "L-FREQ|R8", "L-COAX|R8",
    }  # fmt: skip


def test_pred_6_requires_at_most_eight_distinct_pages() -> None:
    cells = _pred_inputs()
    assert analysis.pred_6(cells)["holds"]
    label = FIVE[0]
    mutated = copy.deepcopy(cells[label].sim)
    # self-consistent counts for nine pages: only the distinct <= 8 assertion can catch this
    mutated["panels"]["A"]["streams"]["actual"]["L-FREQ|R2"] = syn.collapsed_group(9)
    broken = {**cells, label: an.CellData(cells[label].cell, cells[label].eval, mutated)}
    result = analysis.pred_6(broken)
    assert not result["holds"] and result["violation_count"] > 0
