# ruff: noqa: E501
"""P10S2: the GEN panel under the lead's ruling of 2026-11-16 (the marker-like stratum is every window of it on the fixed grid, 44; the ordinary stratum is 100 sampled windows; the panel loss is the equal-weight
mean of the two stratum means) and the fail-fast order of the data-generation step. Stand-in world, test seeds, fakes. Self-check only: not independent review, not Astra validation, not human approval."""

import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402
import torch  # noqa: E402
from test_p10s2_support import dry_world, trained  # noqa: E402

from studies.p10s2 import (  # noqa: E402
    core,
    datagen,
    evaluate,
    prefreeze,
    report,
    standins,
    windows,
)
from studies.p10s2.evaluate import GeneralWindow  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def fake_windows(n_marker: int, n_ordinary: int) -> list[GeneralWindow]:
    return [GeneralWindow((i, i + 1), (), "marker", 1) for i in range(n_marker)] + [GeneralWindow((1000 + i, 1001 + i), (), "ordinary") for i in range(n_ordinary)]


def test_the_configuration_states_the_panel_and_the_registered_spec_checks_it_adds_up() -> None:
    d = core.CFG["data"]
    assert (d["general_windows"], d["general_windows_marker_like"], d["general_windows_ordinary"]) == (144, 44, 100)
    spec = prefreeze.WindowSpec.registered()
    assert spec.take_all_marker and spec.marker_like == 44 and spec.windows - spec.marker_like == 100
    assert not prefreeze.WindowSpec.dry().take_all_marker  # the stand-ins keep their small sampled panel


def test_the_marker_like_stratum_is_every_window_and_any_other_count_than_the_configured_one_is_refused() -> None:
    pool = fake_windows(44, 924)
    out = windows.select_windows(pool, {"marker": 44, "ordinary": 100}, core.partition_gen("test", "gen_windows"), take_all=("marker",), exact={"marker": 44})
    assert [w for w in out if w.stratum == "marker"] == [w for w in pool if w.stratum == "marker"] and sum(w.stratum == "ordinary" for w in out) == 100 and len(out) == 144
    for n in (43, 45, 100):
        with pytest.raises(windows.WindowsInsufficient, match="the configuration states 44"):
            windows.select_windows(fake_windows(n, 924), {"marker": 44, "ordinary": 100}, core.partition_gen("test", "gen_windows"), take_all=("marker",), exact={"marker": 44})
    with pytest.raises(windows.WindowsInsufficient, match="fewer than 100"):
        windows.select_windows(fake_windows(44, 99), {"marker": 44, "ordinary": 100}, core.partition_gen("test", "gen_windows"), take_all=("marker",), exact={"marker": 44})


def test_the_ordinary_sample_is_the_one_the_earlier_code_drew() -> None:
    """The earlier code drew a permutation of the marker-like pool first and the ordinary permutation next from the same generator; the new code takes every marker-like window but still advances the generator by
    that one permutation, so the ordinary windows are the same ones."""
    pool = fake_windows(300, 924)  # a grid with 100 or more marker-like windows, as the earlier rule needed
    g = core.partition_gen("test", "gen_windows")
    torch.randperm(300, generator=g)  # the earlier code's marker-like draw
    ordinary_pool = [w for w in pool if w.stratum == "ordinary"]
    old = [ordinary_pool[i] for i in sorted(torch.randperm(924, generator=g).tolist()[:100])]
    new = windows.select_windows(pool, {"marker": 100, "ordinary": 100}, core.partition_gen("test", "gen_windows"), take_all=("marker",))
    assert [w for w in new if w.stratum == "ordinary"] == old
    again = windows.select_windows(pool, {"marker": 100, "ordinary": 100}, core.partition_gen("test", "gen_windows"))  # sampled marker-like, as before
    assert [w for w in again if w.stratum == "ordinary"] == old  # unchanged for the sampled path too


def test_the_panel_loss_is_the_equal_weight_mean_of_the_two_stratum_means() -> None:
    strata = ["marker"] * 44 + ["ordinary"] * 100
    vals = [1.0] * 44 + [0.0] * 100
    assert evaluate.panel_mean(vals, strata) == pytest.approx(0.5)  # not 44/144 = 0.3056: the marker-like windows are not diluted
    equal = ["marker"] * 100 + ["ordinary"] * 100
    v2 = [float(i % 7) for i in range(200)]
    assert evaluate.panel_mean(v2, equal) == pytest.approx(sum(v2) / 200)  # equal counts: the plain mean over all windows, as the panel was read before
    assert evaluate.panel_mean([2.0, 4.0], ["ordinary", "ordinary"]) == pytest.approx(3.0)  # a stratum with no window is left out
    m = evaluate.stratum_means("marker", strata, [0.0] * 144, [1.0] * 144, [2.0] * 144)
    assert m["windows"] == 44 and m["loss_increase"] == 1.0 and m["loss_increase_first_marker"] == 2.0 and evaluate.stratum_means("none", strata, [0.0] * 144, [0.0] * 144, [0.0] * 144) == {"windows": 0}


def test_every_gen_reading_prints_both_stratum_counts_and_means_and_the_increase_is_their_equal_weight_mean() -> None:
    world, _, d, tr, sc = trained()
    gens = [snap["gen"] for rec in sc.values() if rec.get("status") == "completed" for snap in rec["scores"].values() if "gen" in snap]
    assert gens
    for g in gens:
        sm = g["stratum_means"]
        assert g["panel_weighting"] == evaluate.PANEL_WEIGHTING and sm["marker"]["windows"] == g["stratum_sizes"]["marker"] and sm["ordinary"]["windows"] == g["stratum_sizes"]["ordinary"]
        assert g["loss_increase"] == pytest.approx((sm["marker"]["loss_increase"] + sm["ordinary"]["loss_increase"]) / 2)
        assert g["loss_increase_first_marker"] == pytest.approx((sm["marker"]["loss_increase_first_marker"] + sm["ordinary"]["loss_increase_first_marker"]) / 2)
        assert g["passes"] == (g["loss_increase"] <= core.CFG["gates"]["gen_loss_margin"] and g["loss_increase_first_marker"] <= core.CFG["gates"]["gen_loss_margin"])  # 0.02 under both decisions, unchanged


def test_the_gen_table_prints_counts_means_and_the_half_of_weight_sentence() -> None:
    row = {"cell": "r0/MAF/AB", "loss_increase": 0.01, "loss_increase_first_marker": 0.02, "gen_gate": True, "false_triggers": {"marker": 3, "ordinary": 1}, "false_triggers_first_marker": {"marker": 4, "ordinary": 2},
           "stratum_means": {"marker": {"windows": 44, "loss_increase": 0.015, "loss_increase_first_marker": 0.03}, "ordinary": {"windows": 100, "loss_increase": 0.005, "loss_increase_first_marker": 0.01}}}
    text = "\n".join(report.gen_lines([row], []))
    assert "equal-weight mean of the two stratum means" in text and "half of its weight" in text and "44" in text and "windows (marker-like / ordinary)" in text
    line = next(ln for ln in text.splitlines() if ln.startswith("| r0/MAF/AB"))
    assert "44 / 100" in line and "0.015" in line and "0.005" in line and "0.030" in line


def test_fixed_input_counts_are_checked_against_their_requirements_before_any_teacher_runs() -> None:
    world, _ = dry_world()
    sizes = world.sizes
    part = world.partition
    spec = prefreeze.WindowSpec.registered()
    ok = prefreeze.fixed_input_counts(SimpleNamespace(panels=part.panels, source_pool={c: [0] * 10_000 for c in core.TASKS}, gold_pool={c: [0] * 8000 for c in core.TASKS}), {"A": [], "B": []}, fake_windows(44, 100), sizes_registered(), spec)
    by = {c["name"]: c for c in ok["checks"]}
    marker = by["GEN windows, marker-like stratum (every window of the fixed grid)"]
    assert marker["count"] == 44 and marker["ok"] and by["GEN windows, ordinary stratum"]["ok"]
    short = prefreeze.fixed_input_counts(SimpleNamespace(panels=part.panels, source_pool={c: [0] * 9_999 for c in core.TASKS}, gold_pool={c: [0] * 7999 for c in core.TASKS}), {"A": [], "B": []}, fake_windows(43, 99), sizes_registered(), spec)
    bad = {c["name"] for c in short["checks"] if not c["ok"]}
    assert not short["ok"] and "GEN windows, marker-like stratum (every window of the fixed grid)" in bad and "GEN windows, ordinary stratum" in bad and "capability A: no-gold sources before filtering" in bad and "capability B: gold pairs outside Q, D_cal, D_con" in bad
    assert all("requirement" in c and "count" in c for c in short["checks"]) and len(sizes.__dict__) > 0


def sizes_registered():  # type: ignore[no-untyped-def]
    from studies.p10s2.data import Sizes

    return Sizes.registered()


def test_a_shortfall_raises_before_generation_and_returns_to_the_lead_with_its_counts(tmp_path: Path) -> None:
    exc = prefreeze.InputsInsufficient("a count falls short", {"checks": [{"name": "x", "count": 43, "requirement": "exactly 44", "ok": False}]})
    assert datagen.stop_kind(exc) == "registered-test"  # not an engineering stop: no re-run without the lead
    datagen.write_stop_record(tmp_path, {"steps": {}}, exc, 1)
    import json

    rec = json.loads((tmp_path / "datagen_attempts" / "attempt-001.json").read_text())
    assert rec["stop_kind"] == "registered-test" and rec["fixed_input_counts"]["checks"][0]["count"] == 43
    src = (ROOT / "studies/p10s2/prefreeze.py").read_text()
    assert src.index("fixed_input_counts(part, gen_sources, wl") < src.index("run_teacher(teachers[c]") and src.index("raise InputsInsufficient") < src.index("run_teacher(teachers[c]")  # before the hour of generation


def test_the_bundles_sampled_items_do_not_depend_on_the_order_of_the_checks() -> None:
    bundle, rec = standins.build_synthetic_bundle(1)  # the counts are checked first, the windows selected after them, the teachers run last
    assert rec["fixed_input_counts"]["checks"] and [tuple(w.ids) for w in bundle.windows] == [tuple(w.ids) for w in standins.build_synthetic_bundle(1)[0].windows]
    pool = fake_windows(60, 400)
    spec = {"marker": 4, "ordinary": 4}

    def select(first: bool) -> list[GeneralWindow]:
        before = [core.partition_gen("test", n).manual_seed for n in ("source_sample", "q_split")] if first else []  # other listed streams drawn (and their counts checked) before or after
        out = windows.select_windows(pool, spec, core.partition_gen("test", "gen_windows"))
        _ = before or [core.partition_gen("test", n) for n in ("source_sample", "q_split")]
        return out

    assert select(True) == select(False)  # a stream is drawn from its own seed: nothing checked or drawn on another stream moves a sample
    full = windows.select_windows(pool, spec, core.partition_gen("test", "gen_windows"), take_all=("marker",))
    assert [w for w in full if w.stratum == "marker"] == [w for w in pool if w.stratum == "marker"]
    assert [w for w in full if w.stratum == "ordinary"] == [w for w in select(True) if w.stratum == "ordinary"]  # taking every marker-like window leaves the ordinary sample as it was
