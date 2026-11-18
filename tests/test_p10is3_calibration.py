# ruff: noqa: E501
"""P10IS3 rate search, edge rule, convergence tags, sealing (ADR-0026 section 5; rulings 5 and 18; K1). Hand-derived answers. Self-check only."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from studies.p10i_s3 import calibration, core  # noqa: E402

CFG = core.load_config()
CK = [512, 2048, 8192, 16384]
GRID = [0.0003, 0.001, 0.003, 0.01, 0.03]
UP, DOWN = [0.1, 0.3], [0.0001, 0.00003]
TOL = 0.0005


def curves(by_rate: dict[float, float | None | list], cells: int = 3) -> dict:  # type: ignore[type-arg]
    """``by_rate[rate]`` is the NLL at every duration (a float), None (diverged), or a list of four per-duration values."""
    out = {}
    for r, v in by_rate.items():
        per = v if isinstance(v, list) else [v] * 4
        out[r] = {c: dict(zip(CK, per, strict=True)) for c in range(cells)}
    return out


def test_selection_tie_rule_picks_the_smallest_rate_within_tolerance() -> None:
    # means: 2.00, 1.9996 (within 0.0005 of the minimum 1.9992), 1.9992, 2.05, 2.1: the minimum is at 0.003 and the smallest rate within 0.0005 of it is 0.001
    c = curves({0.0003: 2.0, 0.001: 1.9996, 0.003: 1.9992, 0.01: 2.05, 0.03: 2.1})
    s = calibration.selection(c, 512, TOL)
    assert s["minimiser"] == 0.003 and s["selected"] == 0.001 and s["edge"] is None
    # exactly at the margin the rate is within (inclusive): 1.9992 + 0.0005
    c = curves({0.0003: 2.0, 0.001: 1.9997, 0.003: 1.9992, 0.01: 2.05, 0.03: 2.1})
    assert calibration.selection(c, 512, TOL)["selected"] == 0.001
    c = curves({0.0003: 2.0, 0.001: 1.9998, 0.003: 1.9992, 0.01: 2.05, 0.03: 2.1})
    assert calibration.selection(c, 512, TOL)["selected"] == 0.003  # 0.0006 above the minimum: not within


def test_exact_tie_minimiser_is_the_smaller_rate() -> None:
    c = curves({0.0003: 2.0, 0.001: 1.5, 0.003: 1.5, 0.01: 1.9, 0.03: 2.1})
    s = calibration.selection(c, 512, TOL)
    assert s["minimiser"] == 0.001 and s["selected"] == 0.001


def test_edge_is_read_from_the_minimiser_not_the_tie_selected_rate() -> None:
    # a flat loss: every rate within tolerance, so the tie rule selects the lowest rate, but the minimiser is 0.003, inside the grid: no edge, no extension
    flat = curves({0.0003: 1.50005, 0.001: 1.50004, 0.003: 1.5, 0.01: 1.50003, 0.03: 1.50002})
    s = calibration.selection(flat, 512, TOL)
    assert s["selected"] == 0.0003 and s["edge"] is None
    assert calibration.extension_needed(flat, CK, GRID, UP, DOWN, TOL, 2) == {"up": None, "down": None}
    # an optimum at the end that the tie rule would hide: the minimiser is 0.03 (the highest rate) while the tie-selected rate is 0.01
    hid = curves({0.0003: 2.0, 0.001: 1.9, 0.003: 1.8, 0.01: 1.70004, 0.03: 1.7})
    s = calibration.selection(hid, 512, TOL)
    assert s["selected"] == 0.01 and s["minimiser"] == 0.03 and s["edge"] == "high"
    assert calibration.extension_needed(hid, CK, GRID, UP, DOWN, TOL, 2) == {"up": 0.1, "down": None}


def test_extension_at_most_two_per_side_and_edge_tag_remains() -> None:
    c = curves({0.0003: 2.0, 0.001: 1.9, 0.003: 1.8, 0.01: 1.7, 0.03: 1.6, 0.1: 1.5})
    assert calibration.extension_needed(c, CK, GRID, UP, DOWN, TOL, 2) == {"up": 0.3, "down": None}
    c = curves({0.0003: 2.0, 0.001: 1.9, 0.003: 1.8, 0.01: 1.7, 0.03: 1.6, 0.1: 1.5, 0.3: 1.4})
    assert calibration.extension_needed(c, CK, GRID, UP, DOWN, TOL, 2) == {"up": None, "down": None}  # two steps up done: no third
    rt = calibration.rate_table({("M-TREE", "FRESH"): c}, CK, 16384, TOL)
    assert rt["edge"]["M-TREE|FRESH"] is True and rt["rates"]["M-TREE|FRESH"]["16384"] == 0.3  # RATE-AT-EDGE: the selected rate is still used
    low = curves({0.00003: 1.4, 0.0001: 1.5, 0.0003: 1.6, 0.001: 1.7, 0.003: 1.8, 0.01: 1.9, 0.03: 2.0})
    assert calibration.extension_needed(low, CK, GRID, UP, DOWN, TOL, 2) == {"up": None, "down": None}
    assert calibration.rate_table({("M-TREE", "REP"): low}, CK, 16384, TOL)["edge"]["M-TREE|REP"] is True


def test_any_duration_at_the_edge_triggers_an_extension() -> None:
    # at 512 the best rate is the highest; at 16384 it is 0.003
    c = curves({0.0003: [2.0, 2.0, 2.0, 2.0], 0.001: [1.9, 1.9, 1.9, 1.9], 0.003: [1.8, 1.7, 1.6, 1.5], 0.01: [1.85, 1.9, 1.9, 1.9], 0.03: [1.7, 2.0, 2.0, 2.0]})
    assert calibration.extension_needed(c, CK, GRID, UP, DOWN, TOL, 2)["up"] == 0.1


def test_diverged_neighbour_is_not_an_edge_and_a_rate_must_be_finite_in_all_cells() -> None:
    c = curves({0.0003: 2.0, 0.001: 1.9, 0.003: 1.8, 0.01: 1.7, 0.03: None})  # 0.03 diverged in every cell: the best finite rate is 0.01 and its neighbour is non-finite
    s = calibration.selection(c, 512, TOL)
    assert s["minimiser"] == 0.01 and s["edge"] is None
    # finite in two of three cells is not finite
    c2 = curves({0.0003: 2.0, 0.001: 1.9, 0.003: 1.8, 0.01: 1.7, 0.03: 1.0})
    c2[0.03][1][512] = None
    s2 = calibration.selection(c2, 512, TOL)
    assert s2["minimiser"] == 0.01
    # a rate that diverged before c cannot be selected for c but may be for an earlier duration (ruling 5)
    c3 = curves({0.0003: 2.0, 0.001: 1.9, 0.003: 1.8, 0.01: 1.7, 0.03: [1.0, 1.0, None, None]})
    assert calibration.selection(c3, 512, TOL)["minimiser"] == 0.03 and calibration.selection(c3, 8192, TOL)["minimiser"] == 0.01


def test_no_finite_rate_is_an_engineering_stop() -> None:
    with pytest.raises(core.EngineeringStop, match="no rate is finite"):
        calibration.selection(curves({0.003: None, 0.01: None}), 512, TOL)


def test_convergence_tags_from_the_selected_rate_runs() -> None:
    # M-TREE|REP selected rate 0.003 at U*: means 1.5 at 8192 and 1.4995 at 16384 (delta 0.0005 < 0.001): CONVERGED; D-ADAPT 1.5 -> 1.49 (0.01): NOT CONVERGED
    tree = curves({0.003: [1.9, 1.7, 1.5, 1.4995]})
    dense = curves({0.003: [1.9, 1.7, 1.5, 1.49]})
    rt = {"rates": {"M-TREE|REP": dict.fromkeys(map(str, CK), 0.003), "D-ADAPT|REP": dict.fromkeys(map(str, CK), 0.003)}}
    t = calibration.tags({("M-TREE", "REP"): tree, ("D-ADAPT", "REP"): dense}, rt, CK, 16384, 0.001, 0.005)
    assert t["M-TREE|REP"]["tag"] == "CONVERGED" and t["D-ADAPT|REP"]["tag"] == "NOT CONVERGED"
    assert t["M-TREE|REP"]["past_best"] is None
    # PAST BEST: the U* mean is 0.01 above the lowest earlier one
    over = curves({0.003: [1.9, 1.7, 1.5, 1.51]})
    t = calibration.tags({("M-TREE", "REP"): over}, {"rates": {"M-TREE|REP": dict.fromkeys(map(str, CK), 0.003)}}, CK, 16384, 0.001, 0.005)
    assert t["M-TREE|REP"]["past_best"] == "PAST BEST CHECKPOINT" and t["M-TREE|REP"]["tag"] == "CONVERGED"  # rising loss is converged
    # a failed cell at the selected rate: NOT DETERMINED
    bad = curves({0.003: [1.9, 1.7, 1.5, 1.49]})
    bad[0.003][2][16384] = None
    t = calibration.tags({("M-TREE", "FRESH"): bad}, {"rates": {"M-TREE|FRESH": dict.fromkeys(map(str, CK), 0.003)}}, CK, 16384, 0.001, 0.005)
    assert t["M-TREE|FRESH"]["tag"] == "NOT DETERMINED" and "past_best" not in t["M-TREE|FRESH"]  # FRESH has no PAST BEST tag


def _full_curves() -> dict:  # type: ignore[type-arg]
    out = {}
    for a, g in calibration.ARM_REGIMES:
        out[(a, g)] = curves({r: [2.0 - 0.1 * i - 0.01 * j for j in range(4)] for i, r in enumerate(GRID[:3])} | {0.01: 2.5, 0.03: None})
    return out


def test_public_file_has_no_loss_values_and_the_checker_agrees_or_names_fields() -> None:
    cb = _full_curves()
    sealed = calibration.sealed_bytes(cb, {"statistics": {"C": 0.0123456}})
    import hashlib

    sha = hashlib.sha256(sealed).hexdigest()
    pub = calibration.public_summary(cb, CFG, gates={"neg_ref": {"passed": True}}, timing={}, storage={}, sealed_sha256=sha)
    text = str(pub)
    assert "0.0123456" not in text and set(pub) >= {"rate_table", "convergence", "gates", "sealed_sha256"}
    assert len(pub["rate_table"]["rates"]) == 8  # 8 arm-regimes (M-FLAT is not run in REP-U)
    assert calibration.check_public_against_sealed(pub, sealed, CFG) == {"result": "agree", "fields": []}
    tampered = dict(pub)
    tampered["rate_table"] = {**pub["rate_table"], "rates": {**pub["rate_table"]["rates"], "M-TREE|REP": dict.fromkeys(map(str, CK), 0.03)}}
    r = calibration.check_public_against_sealed(tampered, sealed, CFG)
    assert r == {"result": "disagree", "fields": ["rate_table"]}  # only the name of the field is reported
    assert calibration.check_public_against_sealed({**pub, "sealed_sha256": "0" * 64}, sealed, CFG)["fields"] == ["sealed_sha256"]


def test_sealed_archive_is_written_outside_the_repository_only(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[1]
    with pytest.raises(core.EngineeringStop, match="outside the repository"):
        calibration.write_sealed(repo / "experiments" / "_scratch" / "x_sealed.json", repo, b"{}")
    sha = calibration.write_sealed(tmp_path / "s" / "sealed.json", repo, b"{}")
    assert len(sha) == 64
    with pytest.raises(FileExistsError):
        calibration.write_sealed(tmp_path / "s" / "sealed.json", repo, b"{}")
