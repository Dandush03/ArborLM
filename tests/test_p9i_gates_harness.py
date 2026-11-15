# ruff: noqa: E501
"""P9I gates harness: the gradient-reach inputs must belong to the cell being checked (a defect of the first
registered attempt, where 8 Panel A rows held no fact of the 4,096-slot cell and R2 read no slot); the
harness assertion; real-proportion coverage of the fact subsets and lookup tables; the gates stage in
rehearsal mode. Test seeds only. Self-check only: not independent review, not Astra validation, not human
approval."""

import dataclasses
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402
import torch  # noqa: E402

from studies.p9 import controls  # noqa: E402
from studies.p9 import data as d  # noqa: E402
from studies.p9i import core, evaluate, model, stages, train  # noqa: E402

FACTS = 128


def _study(sizes: d.DataSizes = stages.DRY_SIZES) -> d.StudyData:
    return d.build_study_data(core.test_seeds(3), stages.SYNTHETIC_CORPUS, sizes=sizes)


@pytest.fixture(scope="module")
def study() -> d.StudyData:
    return _study()


@pytest.fixture(scope="module")
def backbone():  # type: ignore[no-untyped-def]
    return controls.synthetic_backbone()


def _front_loaded_with_foreign_rows(study: d.StudyData, facts: int) -> d.StudyData:
    """The registered situation: Panel A reordered so that its first 8 rows hold no fact of the cell."""
    stream = study.streams["panel_a"]
    foreign = (stream.fact_ids >= facts).all(dim=1)
    order = torch.cat([foreign.nonzero().squeeze(1), (~foreign).nonzero().squeeze(1)])
    moved = dataclasses.replace(stream, tokens=stream.tokens[order], fact_ids=stream.fact_ids[order], cluster=stream.cluster[order], template=stream.template[order])
    assert not bool((moved.fact_ids[:8] < facts).any())
    return dataclasses.replace(study, streams={**study.streams, "panel_a": moved})


def _reach(arm: str, backbone, study: d.StudyData, tokens: torch.Tensor) -> dict:  # type: ignore[no-untyped-def,type-arg]
    lut = train.fact_lut_for(study, FACTS) if arm == "R2" else None
    net = model.build_model(arm, 4096, core.INIT_SEEDS[0], backbone, fact_lut=lut, r1_seed=study.seeds.r1_codes)
    return train.gradient_reach(net, tokens)


def test_old_selection_fails_for_r2_and_the_new_selection_passes_for_every_arm(study: d.StudyData, backbone) -> None:  # type: ignore[no-untyped-def]
    bad = _front_loaded_with_foreign_rows(study, FACTS)
    old = bad.streams["panel_a"].tokens[:8]  # what the first attempt used
    r_old = _reach("R2", backbone, bad, old)
    assert not all(r_old["reached"].values())  # values, wo and gate get no gradient: no slot was read
    tokens, ids = stages.gate_contexts(bad, FACTS)
    assert bool((ids < FACTS).all()) and tokens.shape == (8, 64)
    for arm in core.ARMS:
        lut = train.fact_lut_for(bad, FACTS) if arm == "R2" else None
        stages.assert_covered(tokens, ids, FACTS, lut)
        r = _reach(arm, backbone, bad, tokens)
        assert r["stray"] == [] and all(r["reached"].values()), (arm, [n for n, ok in r["reached"].items() if not ok])


def test_gate_contexts_come_from_the_evaluate_paths_restricted_stream(study: d.StudyData) -> None:
    tokens, ids = stages.gate_contexts(study, FACTS)
    stream = evaluate.stream_for(study, FACTS, "panel_a")
    keep = (stream.fact_ids < FACTS).all(dim=1).nonzero().squeeze(1)[:8]
    assert torch.equal(tokens, stream.tokens[keep]) and torch.equal(ids, stream.fact_ids[keep])
    with pytest.raises(stages.HarnessError, match="contexts"):
        stages.gate_contexts(study, 16, count=10_000)


def test_harness_assertion_is_distinct_from_a_gradient_defect(study: d.StudyData) -> None:
    tokens, ids = stages.gate_contexts(study, FACTS)
    stages.assert_covered(tokens, ids, FACTS, train.fact_lut_for(study, FACTS))
    foreign = study.streams["panel_a"]
    keep = (foreign.fact_ids >= FACTS).all(dim=1).nonzero().squeeze(1)[:8]
    with pytest.raises(stages.HarnessError, match="does not cover"):
        stages.assert_covered(foreign.tokens[keep], foreign.fact_ids[keep], FACTS)
    with pytest.raises(stages.HarnessError, match="lookup table"):  # a table for fewer facts than the cell has
        stages.assert_covered(tokens, ids, FACTS, train.fact_lut_for(study, FACTS // 2))
    assert not issubclass(stages.HarnessError, AssertionError) and not issubclass(stages.HarnessError, ValueError)
    # a wrong choice of contexts is never recorded as a G4 defect: the exception propagates out of the gates worker
    with pytest.raises(stages.HarnessError):
        stages.assert_covered(foreign.tokens[keep], foreign.fact_ids[keep], FACTS, train.fact_lut_for(study, FACTS))


def test_real_proportion_subsets_streams_and_luts_match_every_cell_size() -> None:
    real = _study(d.DataSizes())  # 32,768 trained facts, 2,048 unseen: the registered proportions
    for slots in core.SLOTS_BY_SIZE:
        facts = core.FACTS_PROPORTIONAL[slots]
        lut = train.fact_lut_for(real, facts)
        assert int((lut >= 0).sum()) == facts  # one slot per fact of the cell, none outside it
        stream = train.training_stream_for(real, facts)
        assert stream.facts.tolist() == list(range(facts))
        for name in ("panel_a", "panel_b"):
            restricted = evaluate.stream_for(real, facts, name)
            ids = restricted.fact_ids.reshape(-1)
            trained = ids[ids < real.facts.trained]
            assert int((trained < facts).sum()) == facts and int(trained.numel()) == facts  # every fact of the cell once
            unseen = ids[ids >= real.facts.trained]
            assert int(unseen.numel()) == real.facts.size - real.facts.trained
        tokens, ids2 = stages.gate_contexts(real, facts)
        stages.assert_covered(tokens, ids2, facts, lut)
    # the first attempt's inputs: eight raw Panel A rows rarely hold a fact of the 4,096-slot cell
    raw = real.streams["panel_a"].fact_ids[:8]
    assert int((raw < 2048).sum()) < raw.numel()


def test_dry_proportion_matches_the_registered_smallest_size() -> None:
    assert stages.DRY_SIZES.main_trained == 2048 and stages.DRY_FACTS[4096] / stages.DRY_SIZES.main_trained == core.FACTS_PROPORTIONAL[4096] / core.FACTS_PROPORTIONAL[65536]


def test_gates_stage_runs_in_rehearsal_mode(tmp_path: Path) -> None:
    run = tmp_path / "run"
    base = ["--dry", "--mode", "rehearsal", "--run-dir", str(run), "--experiments-root", str(tmp_path), "--ledger", str(tmp_path / "l.json"), "--stage-cap-seconds", "900", "--workers", "2"]
    assert stages.main(["generate", *base]) == 0
    assert stages.main(["gates", *base]) == 0
    gates = json.loads((run / "gates.json").read_text())
    assert gates["g4_passed"] is True and gates["g4_defects"] == [] and gates["g1_passed"] is True
    assert set(gates["gradient_reach"]) == set(core.ARMS) and all(r["all_reached"] for r in gates["gradient_reach"].values())
    manifest = json.loads((run / "gates" / "manifest.json").read_text())
    assert manifest["mode"] == "rehearsal" and manifest["status"] == "COMPLETE"
    data_manifest = json.loads((run / "data_manifest.json").read_text())
    assert data_manifest["seed_set"] == "p9i-test-0"
