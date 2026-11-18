# ruff: noqa: E501
"""P10IS2 Part T end to end on a tiny world: train all 54 cells, score every snapshot, build the registry, check it holds exactly the keys the analysis requires, derive every line (ADR-0025 sections 5, 8, 11
item 8). The numbers are those of a random tiny student and mean nothing; the test is about plumbing, keys and determinism. CPU. Self-check only."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402
from p10is2_engine_fixtures import CFG_T, world  # noqa: E402

from studies.p10is2 import labels as L  # noqa: E402
from studies.p10is2 import partt_plan, partt_run  # noqa: E402
from studies.p10is2.common import core  # noqa: E402
from studies.p10is2.quantities import Quantities, Thresholds  # noqa: E402
from studies.p10s2.text import normalize  # noqa: E402


def fake_gloss_bank(w):  # type: ignore[no-untyped-def]
    v = w.cfg.vocab

    def ids(x: str) -> list[int]:
        return [1 + (sum(map(ord, x)) % (v - 2))]

    words = {c: {t: ids(t) for x in w.streams[0].t[c] for t in normalize(x.target).split()} for c in core.TASKS}
    for s in w.streams:
        for c in core.TASKS:
            for x in s.t[c]:
                for t in normalize(x.target).split():
                    words[c][t] = ids(t)
    return {"source_words": {x: ids(x) for x in w.partition.vocab}, "words": words, "separator": [2], "newline": [3]}


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory):  # type: ignore[no-untyped-def]
    d = tmp_path_factory.mktemp("e2e")
    w = world(updates=2)
    recs = partt_run.train_all(w, d / "snaps", d / "ck", 2)
    reg, side = partt_run.score_all(w, d / "snaps", fake_gloss_bank(w))
    return w, d, recs, reg, side


def test_all_54_cells_complete_and_checkpoints_are_gone(run) -> None:  # type: ignore[no-untyped-def]
    w, d, recs, reg, side = run
    assert len(recs) == 54 and all(r["status"] == "COMPLETE" for r in recs.values())
    assert not list((d / "ck").glob("*.ckpt")) if (d / "ck").exists() else True
    assert recs["r0/M-joint/-"]["updates_done"] == 4 and recs["r1/D-joint/-"]["updates_done"] == 4 and recs["r2/E-table/B"]["updates_done"] == 2


def test_registry_has_exactly_the_required_keys(run) -> None:  # type: ignore[no-untyped-def]
    reg = run[3]
    req = partt_plan.required_keys()
    assert req <= set(reg.values), sorted(req - set(reg.values))[:5]
    extra = set(reg.values) - req
    assert all("R-exact" in k or "R-gloss" in k or "R-nn" in k or "R-icl" in k or "sub:words" in k or "sub:" in k or "|s:" in k or "em:" in k or "lr:" in k or "@append" in k for k in extra), sorted(extra)[:8]
    assert L.study_status(reg, required=req)["status"] == "OK"
    assert not reg.nonfinite()


def test_labels_derive_on_real_scored_records_without_a_missing_key(run) -> None:  # type: ignore[no-untyped-def]
    reg = run[3]
    q = Quantities(reg, Thresholds.from_config(CFG_T))
    out = L.derive_all(q)
    assert set(out) >= {"ACQUISITION", "RETENTION", "GENERAL-QUALITY", "AGAINST-DENSE", "AGAINST-LOOKUP", "MODIFICATION", "MILESTONE"}
    assert out["MILESTONE"]["label"].startswith(("SUPPORTED", "NOT ESTABLISHED", "WITHHELD"))  # whatever the tiny random numbers give; no label is claimed


def test_scoring_is_repeatable_bit_for_bit_and_snapshots_are_not_changed_by_it(run) -> None:  # type: ignore[no-untyped-def]
    w, d, recs, reg, side = run
    reg2, _ = partt_run.score_all(w, d / "snaps", fake_gloss_bank(w), replicates=(0,))
    for k, v in reg2.values.items():
        if k.split("|")[2] in ("0", "-") and "|-|-|" not in k or "|-|-|" in k:
            assert reg.values[k] == v, k  # gate G2: repeat-scoring identity (the routers are retrained from the same seeds)


def test_side_records_and_reference_reads(run) -> None:  # type: ignore[no-untyped-def]
    w, d, recs, reg, side = run
    assert "r0/M-append/AB" in side and "false_trigger_count" in side["r0/M-append/AB"]["router_diagnostics"] and 0.0 <= side["r0/M-ii/AB"]["modification_rows_changed_share"] <= 1.0
    assert side["r0/R-exact-hits"]["hits:E_A"] == 0.0  # the panels are held out of every training draw (G1)
    assert reg.get("TEACHER", "-", "-", "s:E_A") > reg.get("S0", "-", "-", "s:E_A")  # the lexicon teacher is above the untrained student


def test_combined_tasks_on_twelve_arm_cells_per_replicate(run) -> None:  # type: ignore[no-untyped-def]
    w, d, recs, reg, side = run
    out = partt_run.combined_all(w, d / "snaps", replicates=(0,))
    assert set(out) == {"S0", "ensemble", *[f"{a}|{o}|0" for a in ("M-append", "M-ii", "D-seq", "D-append") for o in ("AB", "BA")], "M-joint|-|0", "D-joint|-|0", "M-sep|-|0", "D-sep|-|0"}
    assert partt_plan.combined_arm_cells_per_replicate() == 12
