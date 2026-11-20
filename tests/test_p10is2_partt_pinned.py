# ruff: noqa: E501
"""R13 with ruling 9: in a CONSOLIDATION-REJECTED cell the pinned M-append snapshot is what every other reading of M-ii uses, CONTROL-FAILED included, marked; the unpublished M-ii state enters no label (ADR-0025
section 8.5). Tiny world, test size. Self-check only."""

import dataclasses
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402
from p10is2_engine_fixtures import world  # noqa: E402
from p10is2_partt_e2e_world import fake_gloss_bank  # noqa: E402

from studies.p10is2 import partt_run, scoring  # noqa: E402
from studies.p10is2.common import core  # noqa: E402

TOL_UNDER_TEST = 1000.0


def test_is_rejected_follows_the_dcon_rule_and_the_orders_come_from_the_registry() -> None:
    assert partt_run.is_rejected({"dcon:A": 0.50, "dcon:B": 0.60}, {"dcon:A": 0.60, "dcon:B": 0.60}, 0.02) is True  # A is more than 0.02 below M-append's
    assert partt_run.is_rejected({"dcon:A": 0.59, "dcon:B": 0.60}, {"dcon:A": 0.60, "dcon:B": 0.60}, 0.02) is False
    vals = {f"M-append|{o}|0|dcon:{c}": 0.6 for o in ("AB", "BA") for c in core.TASKS} | {f"M-ii|AB|0|dcon:{c}": 0.1 for c in core.TASKS} | {f"M-ii|BA|0|dcon:{c}": 0.6 for c in core.TASKS}
    assert partt_run.rejected_orders(vals, 0, 0.02) == {"AB"}


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory):  # type: ignore[no-untyped-def]
    d = tmp_path_factory.mktemp("pinned")
    w = world(updates=2, n_reps=1)
    gloss = fake_gloss_bank(w, {c: w.streams[0].t[c] for c in core.TASKS})
    partt_run.train_all(w, d / "snapshots", None, 2, replicates=(0,))
    return w, d, gloss


def test_a_rejected_m_ii_cell_is_read_from_the_pinned_m_append_snapshot_and_marked(run, monkeypatch: pytest.MonkeyPatch) -> None:  # type: ignore[no-untyped-def]
    w, d, gloss = run
    normal, _nside = partt_run.score_replicate(w, 0, d / "snapshots", gloss)
    real = partt_run.Thresholds.from_config

    def forced(cfg):  # type: ignore[no-untyped-def]
        return dataclasses.replace(real(cfg), modification_dcon_tolerance=-TOL_UNDER_TEST)  # M-ii is below M-append's minus (-1000): rejected in every cell

    monkeypatch.setattr(partt_run.Thresholds, "from_config", staticmethod(forced))
    scoring.ITEMS.clear()
    pinned, pside = partt_run.score_replicate(w, 0, d / "snapshots", gloss)
    for o in ("AB", "BA"):
        key = f"M-ii|{o}|0"
        assert pside[f"r0/M-ii/{o}"]["pinned_from"] == "M-append" and "unpublished_m_ii_reads" in pside[f"r0/M-ii/{o}"]
        assert {k: v for k, v in pinned[key].items() if k.startswith("dcon:")} == {k: v for k, v in normal[key].items() if k.startswith("dcon:")}  # the evidence of the rejection is the real M-ii's D_con
        assert pinned[key]["s:E_A"] == pinned[f"M-append|{o}|0"]["s:E_A"] and pinned[key]["s:E_B"] == pinned[f"M-append|{o}|0"]["s:E_B"]  # every other reading is the pinned M-append snapshot's
        assert pinned[key]["gen:token64"] == pinned[f"M-append|{o}|0"]["gen:token64"]
        assert scoring.ITEMS[f"{key}|s:E_A"]["items"] == scoring.ITEMS[f"M-append|{o}|0|s:E_A"]["items"]  # the stored per-item records say the same
    comb = partt_run.combined_replicate(w, 0, d / "snapshots", pinned_orders={"AB"})
    assert comb["M-ii|AB|0"]["pinned_from"] == "M-append" and "pinned_from" not in comb["M-ii|BA|0"]
    assert {k: v for k, v in comb["M-ii|AB|0"].items() if k != "pinned_from"} == comb["M-append|AB|0"]  # the combined record of a rejected cell is M-append's, marked
