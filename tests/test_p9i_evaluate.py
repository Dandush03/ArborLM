# ruff: noqa: E501
"""P9I evaluation: query diagnostics, per-stream measurements, value permutation and disabling, minimal
supports at the answer-site read, the unseen-fact control, the backbone's next-byte loss, G2 and exact
retrieval. Tiny sizes, test seeds, synthetic backbone. Self-check only: not independent review, not Astra
validation, not human approval."""

import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402
import torch  # noqa: E402
from torch.nn import functional as F  # noqa: E402

from studies.p9 import controls  # noqa: E402
from studies.p9 import core as p9core  # noqa: E402
from studies.p9 import data as d  # noqa: E402
from studies.p9.evaluate import build_cache  # noqa: E402
from studies.p9i import core, evaluate, model, train  # noqa: E402

SIZES = d.DataSizes(main_trained=512, unseen=64, lane_d_per_set=128)
FACTS = 128


def _corpus() -> bytes:
    g = torch.Generator().manual_seed(12)
    return bytes(torch.randint(0, 256, (2048 * 65,), generator=g).tolist())


@pytest.fixture(scope="module")
def draw() -> d.StudyData:
    return d.build_study_data(core.test_seeds(2), _corpus(), sizes=SIZES)


@pytest.fixture(scope="module")
def backbone():  # type: ignore[no-untyped-def]
    torch.manual_seed(0)
    return controls.synthetic_backbone()


def _trained(draw, backbone, arm: str, out: Path, updates: int):  # type: ignore[no-untyped-def]
    job = train.TrainJob(
        cell=core.make_cell(arm, 4096),
        updates=updates,
        mode="calibration",
        data=draw,
        stream=train.training_stream_for(draw, FACTS),
        backbone=backbone,
        out_dir=out,
        init_seed=900051,
        r1_seed=draw.seeds.r1_codes,
        fact_lut=train.fact_lut_for(draw, FACTS) if arm == "R2" else None,
        snapshots=(updates,),
    )
    return train.run_job(job), job


def test_query_statistics_match_brute_force() -> None:
    g = torch.Generator().manual_seed(1)
    q = F.normalize(torch.randn(60, 16, generator=g), dim=-1)
    out = evaluate.query_statistics(q)
    sims = q @ q.T
    off = ~torch.eye(60, dtype=torch.bool)
    assert out["mean_cosine_different"] == pytest.approx(float(sims[off].mean()), abs=1e-6)
    near = (sims.masked_fill(~off, -2.0).max(1).values > 0.9).float().mean()
    assert out["share_nearest_above_0_9"] == pytest.approx(float(near))
    same = F.normalize(torch.ones(10, 4), dim=-1)
    out = evaluate.query_statistics(same)
    assert out["mean_cosine_different"] == pytest.approx(1.0) and out["share_nearest_above_0_9"] == 1.0
    one = evaluate.query_statistics(same[:1])
    assert one["facts"] == 1 and math.isnan(one["mean_cosine_different"])
    big = evaluate.query_statistics(F.normalize(torch.randn(evaluate.QUERY_CHUNK + 50, 8, generator=g), dim=-1))
    assert 0 <= big["share_nearest_above_0_9"] <= 1  # the chunked path with a partial last block


def test_finite_replaces_non_finite_floats_only() -> None:
    out = evaluate._finite({"a": float("nan"), "b": [1.0, float("inf")], "c": {"d": -float("inf"), "e": 3, "f": "x"}})
    assert out == {"a": None, "b": [1.0, None], "c": {"d": None, "e": 3, "f": "x"}}
    json.dumps(out, allow_nan=False)


def test_the_answer_site_read_has_only_the_answer_site_as_its_read_position(draw, backbone, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    run, _ = _trained(draw, backbone, "W7", tmp_path, 2)
    stream = evaluate.stream_for(draw, FACTS, "panel_a")
    cache = build_cache(run.model, stream)
    assert cache.selection is not None and cache.selection.positions.tolist() == list(core.ANSWER_SITE_POSITIONS)
    assert cache.selection.selected.shape[1] == 8


def test_evaluate_stream_fields_and_consistency(draw, backbone, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    run, _ = _trained(draw, backbone, "R2", tmp_path, 60)
    net = run.model
    net.eval()
    rec = evaluate.evaluate_stream(net, draw, FACTS, "panel_a", primary=True)
    stream = evaluate.stream_for(draw, FACTS, "panel_a")
    trained = (stream.fact_ids.reshape(-1) < FACTS)
    assert rec["facts"] == int(trained.sum()) == FACTS and rec["sha256"] == stream.sha256
    assert rec["accuracy"] == rec["correct"] / rec["facts"]
    for key in ("i_acc_bits", "logloss_gain_bits", "loss_256_nats", "mass_in_alphabet", "disabled_accuracy", "permuted_accuracy", "accuracy_with_neighbour", "support", "unseen_accuracy", "leakage", "distinct_selected_slots"):
        assert key in rec, key
    assert rec["chance_interval"] == list(p9core.chance_interval(FACTS)[2:4])
    # unseen facts were never trained and have random answers: at chance, no leakage flag expected
    assert rec["unseen_facts"] == 64 and isinstance(rec["leakage"], bool)
    assert rec["support"]["correct_facts"] == rec["correct"]
    # an independent recomputation of accuracy from the logits
    with torch.no_grad():
        logits = torch.cat([net(stream.tokens[i : i + 64, :63])[0][:, list(core.ANSWER_SITE_POSITIONS)] for i in range(0, stream.tokens.shape[0], 64)]).reshape(-1, 256)
    scores = p9core.score_answer_sites(logits, stream.answer_targets().reshape(-1))
    assert int(scores.correct[trained].sum()) == rec["correct"]
    # a trained R2 beats chance and depends on its memory: disabling and permuting its values remove it
    assert rec["accuracy"] > rec["chance_interval"][1] / FACTS
    assert rec["disabled_accuracy"] <= rec["accuracy"] and rec["permuted_accuracy"] <= rec["accuracy"]
    assert rec["permuted_at_chance"] and rec["disabled_at_chance"] and rec["memory_dependence_chance"]
    assert rec["support"]["with_support"] > 0


def test_untrained_dense_arm_has_no_memory_fields(draw, backbone, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    run, _ = _trained(draw, backbone, "D7", tmp_path, 2)
    rec = evaluate.evaluate_stream(run.model, draw, FACTS, "panel_b", primary=True)
    assert rec["permuted_accuracy"] is None and "support" not in rec and "query" not in rec
    assert "disabled_accuracy" in rec and rec["memory_dependence_chance"] in (True, False)


def test_secondary_streams_report_accuracy_only(draw, backbone, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    run, _ = _trained(draw, backbone, "N", tmp_path, 2)
    for name in ("h1", "h2", "mixed"):
        rec = evaluate.evaluate_stream(run.model, draw, FACTS, name, primary=False)
        assert set(rec) >= {"accuracy", "correct", "facts"} and "disabled_accuracy" not in rec


def test_query_and_attention_diagnostics_per_arm(draw, backbone, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    expect = {"N": (True, False), "W7": (True, False), "A4": (True, True), "A4E": (True, True), "R1": (True, False), "BB": (True, True), "BB-D": (False, True), "BB-0": (False, True), "D7": (False, False), "R2": (False, False)}
    for arm, (has_q, has_a) in expect.items():
        run, _ = _trained(draw, backbone, arm, tmp_path / arm, 1)
        rec = evaluate.evaluate_stream(run.model, draw, FACTS, "panel_a", primary=True)
        assert ("query" in rec) == has_q and ("attention" in rec) == has_a, arm
        if has_a:
            att = rec["attention"]
            assert len(att["identifier_mass_per_head"]) == 4 and 0 <= att["identifier_mass_mean"] <= 1
        if has_q:
            assert -1 <= rec["query"]["mean_cosine_different"] <= 1
    # R1's queries are the oracle codes: nearly orthogonal
    run, _ = _trained(draw, backbone, "R1", tmp_path / "r1b", 1)
    rec = evaluate.evaluate_stream(run.model, draw, FACTS, "panel_a", primary=True)
    assert abs(rec["query"]["mean_cosine_different"]) < 0.1 and rec["query"]["share_nearest_above_0_9"] == 0.0


def test_next_byte_loss_before_and_after(draw, backbone, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    rows = evaluate.corpus_rows(_corpus())[:32]
    assert rows.shape == (32, 65)
    loss = evaluate.next_byte_loss(backbone, rows)
    with torch.no_grad():
        logits = controls.logits_from_hidden(backbone, controls.insertion_hidden(backbone, rows[:, :64]))
    assert loss == pytest.approx(float(F.cross_entropy(logits.reshape(-1, 256), rows[:, 1:65].reshape(-1))), rel=1e-5)
    fresh = model.build_model("BB", 4096, 900051, backbone, seed_rng=False)
    same = evaluate.language_modelling(fresh, backbone, rows)
    assert same["relative_rise"] == 0.0 and same["degraded"] is False  # at initialization nothing has moved
    run, _ = _trained(draw, backbone, "BB-0", tmp_path, 5)
    after = evaluate.language_modelling(run.model, backbone, rows)
    assert after["after_nats"] != after["before_nats"] and after["before_nats"] == pytest.approx(loss)
    assert after["degraded"] == (after["relative_rise"] > 0.05)
    # the model with a frozen backbone has the same loss as the original (nothing trained)
    run_n, _ = _trained(draw, backbone, "N", tmp_path / "n", 3)
    assert evaluate.language_modelling(run_n.model, backbone, rows)["relative_rise"] == 0.0


def test_evaluate_cell_writes_one_record_and_never_overwrites(draw, backbone, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    for arm in ("BB", "A4", "R1"):
        out = tmp_path / arm
        run, job = _trained(draw, backbone, arm, out, 3)
        rows = evaluate.corpus_rows(_corpus())[:16] if arm == "BB" else None
        written = evaluate.evaluate_cell(core.make_cell(arm, 4096), tmp_path, draw, backbone, facts=FACTS, updates=[3], init_seed=job.init_seed, r1_seed=job.r1_seed, rows=rows, out_dir=out)
        rec = core.read_record(written[0], "eval")
        assert rec["arm"] == arm and rec["update"] == 3 and set(rec["panels"]) == {"A", "B"} and set(rec["secondary"]) == {"H1", "H2", "MIXED"}
        assert ("language_modelling" in rec) == (arm == "BB")
        with pytest.raises(FileExistsError):
            evaluate.evaluate_cell(core.make_cell(arm, 4096), tmp_path, draw, backbone, facts=FACTS, updates=[3], init_seed=job.init_seed, r1_seed=job.r1_seed, rows=rows, out_dir=out)


def test_controls_no_memory_exact_and_g2(draw, backbone) -> None:  # type: ignore[no-untyped-def]
    backbones = {core.PRIMARY_PARENT: backbone, core.REPLICATE_PARENT: controls.synthetic_backbone(102, 302)}
    rec = evaluate.controls_record(draw, backbones, [128, 512])
    assert rec["fact_counts"] == [128, 512]
    assert set(rec["no_memory"]) == {"A", "B"} and set(rec["no_memory"]["A"]) == {"128", "512", "unseen"}
    assert rec["no_memory"]["A"]["unseen"]["facts"] == 64 and rec["no_memory"]["A"]["512"]["facts"] == 512
    assert rec["exact_accuracy"] == {"128": 1.0, "512": 1.0}
    assert len(rec["g2"]["results"]) == 6 and rec["g2"]["tests"] == 8 and isinstance(rec["g2"]["passed"], bool)
    assert rec["no_memory_replicate"] is not None
    only_primary = evaluate.controls_record(draw, {core.PRIMARY_PARENT: backbone}, [128])
    assert only_primary["no_memory_replicate"] is None
