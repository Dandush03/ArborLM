# ruff: noqa: E501
"""P10S1 models, training, evaluation, the index and the gates that need a model (ADR-0021 sections 3, 4, 5.5, 7, 8.1): F-OQ and R2 reproduce P9-I's R1 and R2 forward and one training
step bit for bit; the counters equal the formulas; H8, R2 and D-OQ gradient reach; controlled-addressing integrity; the derangement and the address swap; a tiny memorized store shows
useful retention that the ablations remove; the inverted-file index and KNN; checkpoint restoration; the rehearsal whitelist; timing helpers. Synthetic random backbone, tiny sizes, unit
test seeds only (921101-921199 here); no calibration, rehearsal or registered seed is read. Self-check only: not independent review, not Astra validation, not human approval."""

import functools
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402
import torch  # noqa: E402

from studies.p9 import controls  # noqa: E402
from studies.p9 import core as p9core  # noqa: E402
from studies.p9 import data as d  # noqa: E402
from studies.p9i import core as p9icore  # noqa: E402
from studies.p9i import model as p9imodel  # noqa: E402
from studies.p9i import train as p9itrain  # noqa: E402
from studies.p10s1 import core, evaluate, gates, index, timing, traffic, train  # noqa: E402
from studies.p10s1 import model as M  # noqa: E402

CORPUS = bytes((i * 7 + 3) % 256 for i in range(p9core.CORPUS_ROW_BYTES * 64))
FACTS = 128
ARMS = core.ARMS


@functools.cache
def data() -> d.StudyData:
    return d.build_study_data(core.test_seeds(1), CORPUS, sizes=d.DataSizes(main_trained=512, unseen=64, lane_d_per_set=128))


@functools.cache
def backbone() -> Any:
    return controls.synthetic_backbone(101, 301)


def job(tmp: Path, arm: str, *, slots: int = 4096, updates: int = 8, snapshots: tuple[int, ...] | None = None, facts: int = FACTS, mode: str = "calibration", lr: float = core.LEARNING_RATE, max_updates: int | None = None, name: str | None = None) -> train.TrainJob:
    seeds = data().seeds
    cell = core.make_cell("P", arm, facts, slots, 1, 2101, run_updates=updates, test=True, lr=lr)
    return train.TrainJob(
        cell=cell, data=data(), stream=train.training_stream_for(data(), facts), backbone=backbone(), out_dir=tmp / (name or f"{arm}-{slots}"), r1_seed=seeds.r1_codes, hash_seed=core.h8_seed(seeds), mode=mode, updates=updates,
        snapshots=snapshots, fact_lut=train.fact_lut_for(data(), facts) if arm == "R2" else None, max_updates=max_updates, log_every=4,
    )  # fmt: skip


def tokens_of(facts: int = FACTS, update: int = 1) -> torch.Tensor:
    return train.training_stream_for(data(), facts).batch(update).tokens


# --- bit-for-bit identity with P9-I ----------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("arm", ["F-OQ", "R2"])
def test_f_oq_and_r2_reproduce_p9i_r1_and_r2_bit_for_bit(tmp_path: Path, arm: str) -> None:
    r = gates.p9i_identity(job(tmp_path, arm), arm)
    assert r["passed"] and r["same_parameters"] and r["logits_identical"] and r["selection_identical"] and r["scores_identical"] and r["loss_identical"] and r["parameters_identical_after_step"]


@pytest.mark.parametrize("arm", ["F-OQ", "R2"])
def test_forward_and_training_step_equal_p9i_directly(tmp_path: Path, arm: str) -> None:
    """The same comparison written out: forward over every position, then one step of both trainers on the same batch, every parameter and the loss, ``torch.equal``."""
    p9arm = {"F-OQ": "R1", "R2": "R2"}[arm]
    j = job(tmp_path, arm)
    tokens = tokens_of()
    theirs = p9imodel.build_model(p9arm, 4096, 2101, backbone(), fact_lut=j.fact_lut, r1_seed=j.r1_seed)
    mine = train.job_model(j)
    theirs.eval()
    mine.eval()
    with torch.no_grad():
        assert torch.equal(theirs(tokens[:, :-1])[0], mine(tokens[:, :-1])[0])
    their_trainer = p9itrain.Trainer(p9icore.make_cell(p9arm, 4096), p9imodel.build_model(p9arm, 4096, 2101, backbone(), fact_lut=j.fact_lut, r1_seed=j.r1_seed), [])
    their_trainer.optimizers = p9itrain.build_optimizers(their_trainer.model)
    their_loss = their_trainer.step(tokens)["task_loss"]
    my_trainer = train.Trainer(j, train.job_model(j))
    my_loss = my_trainer.step(j.stream.batch(1))["task_loss"]
    assert their_loss == my_loss
    for n, p in my_trainer.model.named_parameters():
        if n.startswith("addition."):
            assert torch.equal(p, dict(their_trainer.model.named_parameters())[n]), n
    state_t = [s for o in their_trainer.optimizers for s in o.state.values()]
    state_m = [s for o in my_trainer.optimizers for s in o.state.values()]
    assert len(state_t) == len(state_m) and all(torch.equal(a["exp_avg"], b["exp_avg"]) and torch.equal(a["exp_avg_sq"], b["exp_avg_sq"]) for a, b in zip(state_t, state_m, strict=True))


def test_counters_add_no_parameter_or_buffer() -> None:
    mine = M.build_model("F-OQ", 4096, 2101, backbone(), r1_seed=7, seed_rng=False)
    theirs = p9imodel.build_model("R1", 4096, 2101, backbone(), r1_seed=7, seed_rng=False)
    assert list(mine.state_dict()) == list(theirs.state_dict()) and all(isinstance(v, int) for v in vars(mine.addition.counters).values())


# --- arms ------------------------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("slots", [4096, 16384])
def test_counters_equal_the_formulas(slots: int) -> None:
    r = gates.work_counters(data(), backbone(), slots, FACTS, init_seed=2101, tokens=tokens_of())
    assert r["passed"]
    for arm in ARMS:
        assert r[arm]["counted"]["W"] == r[arm]["formula"]["W"], arm
    assert r["F-OQ"]["counted"]["K"] == slots and r["F-OQ"]["counted"]["V"] == 8 and r["T-OQ"]["counted"]["K"] == slots // 256 + 512
    assert r["H8"]["counted"]["K"] == 0 and r["R2"]["counted"]["V"] == 1 and r["D-OQ"]["counted"]["hidden"] == core.doq_hidden(slots) and r["D-OQ"]["counted"]["bias_additions"] == core.doq_hidden(slots)
    assert r["F-OQ-IVF"]["passed"]


def test_h8_slots_are_hashed_distinct_shared_and_deterministic() -> None:
    seed = core.h8_seed(data().seeds)
    a = [M.h8_slots(seed, c, 4096) for c in range(2000)]
    assert all(len(set(s)) == 8 and all(0 <= x < 4096 for x in s) for s in a) and a == [M.h8_slots(seed, c, 4096) for c in range(2000)]
    assert M.h8_slots(seed + 1, 5, 4096) != M.h8_slots(seed, 5, 4096)
    used = torch.tensor(a).reshape(-1)
    assert int(torch.unique(used).numel()) < used.numel()  # slots are shared between facts
    mem = M.build_model("H8", 4096, 2101, backbone(), r1_seed=1, hash_seed=seed, seed_rng=False).addition
    tokens = tokens_of()[:, :63]
    h = torch.zeros(tokens.shape[0], 63, 32)
    sel = mem.select(h, tokens)
    assert sel.selected.shape == (16, 8, 8) and torch.equal(sel.scores, torch.zeros(16, 8, 8)) and torch.allclose(sel.weights(), torch.full((16, 8, 8), 0.125))
    assert [n for n, _ in mem.named_parameters()] == ["values", "wo", "gate"]  # no keys, no query projection


def test_doq_construction() -> None:
    m = M.build_model("D-OQ", 4096, 2101, backbone(), r1_seed=7, seed_rng=False)
    mem = m.addition
    h = core.doq_hidden(4096)
    assert mem.w1.shape == (h, 16) and mem.b1.shape == (h,) and mem.w2.shape == (32, h) and float(mem.gate) == -2.0
    assert float(mem.w1.abs().max()) <= 0.25 and float(mem.b1.abs().max()) <= 0.25 and float(mem.w2.abs().max()) <= 1.0 / h**0.5
    assert float(mem.b1.abs().max()) > 0.1 and float(mem.w1.abs().max()) > 0.2  # conventional fan-in initialization, not 0.02
    assert M.parameter_report(m).trainable == core.doq_trainable_parameters(h) and M.parameter_report(m).by_group["dense"] == core.doq_trainable_parameters(h)
    again = M.build_model("D-OQ", 4096, 2101, backbone(), r1_seed=7, seed_rng=False).addition
    assert torch.equal(mem.w1, again.w1) and torch.equal(mem.w2, again.w2) and not torch.equal(mem.w1, M.build_model("D-OQ", 4096, 2102, backbone(), r1_seed=7, seed_rng=False).addition.w1)
    tokens = tokens_of()[:, :63]
    delta = m.memory_delta(m.embed_block0(tokens), m.select(m.embed_block0(tokens), tokens))
    sites = list(core.ANSWER_SITE_POSITIONS)
    off_sites = [p for p in range(63) if p not in sites]
    assert float(delta[:, off_sites].abs().max()) == 0.0 and float(delta[:, sites].abs().max()) > 0.0
    foq = M.build_model("F-OQ", 4096, 2101, backbone(), r1_seed=7, seed_rng=False)
    assert M.tensor_sha256(foq.oracle_codes(tokens)) == M.tensor_sha256(m.oracle_codes(tokens))  # D-OQ's input is F-OQ's code tensor
    for n in core.SLOT_COUNTS:
        assert abs(core.doq_trainable_parameters(core.doq_hidden(n)) - core.foq_trainable_parameters(n)) / core.foq_trainable_parameters(n) <= 0.001
    assert gates.parameter_match(backbone(), data(), core.SLOT_COUNTS, init_seed=2101)["passed"]


def test_oracle_codes_are_unit_fixed_and_seeded() -> None:
    codes = M.OracleCodes(11)
    ident = torch.arange(0, 200)
    c = codes.of_codes(ident)
    assert c.shape == (200, 16) and torch.allclose(c.norm(dim=1), torch.ones(200), atol=1e-6) and torch.equal(c, M.OracleCodes(11).of_codes(ident)) and not torch.equal(c, M.OracleCodes(12).of_codes(ident))
    tokens = tokens_of()
    assert M.OracleCodes(11)(tokens).shape == (16, 8, 16)


def test_every_configuration_has_gradient_reach_and_nothing_reaches_the_backbone() -> None:
    cfgs = [("F-OQ", 128, 4096), ("T-OQ", 128, 16384), ("H8", 128, 4096), ("D-OQ", 128, 4096), ("R2", 128, 4096), ("R2", 256, 16384)]
    for arm, facts, slots in cfgs:
        r = gates.reach_for_cell(data(), backbone(), arm, facts, slots, mode="calibration", init_seed=2101)
        assert r["passed"] and r["all_reached"] and r["nothing_reaches_backbone"] and not r["stray"], (arm, r)
    h8 = gates.reach_for_cell(data(), backbone(), "H8", 128, 4096, mode="calibration", init_seed=2101)
    assert h8["h8_rows_equal_hashed_rows"] is True
    r2 = gates.reach_for_cell(data(), backbone(), "R2", 128, 4096, mode="calibration", init_seed=2101)
    assert r2["r2_table_covers_every_fact"] is True
    t = gates.reach_for_cell(data(), backbone(), "T-OQ", 128, 4096, mode="calibration", init_seed=2101)
    assert {"keys", "values", "router", "wo", "gate"} <= set(t["trainable_leaves"])


def test_controlled_addressing_integrity_g6() -> None:
    tokens_all, fact_ids = gates.gate_contexts(data(), FACTS)
    r = gates.integrity(data(), backbone(), FACTS, 4096, init_seed=2101, tokens=tokens_all, fact_ids=fact_ids)
    assert r["passed"] and r["doq_input_hash_equals_foq_codes"] and r["doq_reads_tokens_only"]
    for arm in ("F-OQ", "T-OQ", "H8", "R2"):
        a = r["arms"][arm]
        assert a["selection_unchanged_when_context_permuted"] and a["selection_unchanged_when_answers_replaced"] and a["tokens_only"] and a["stray_tensor_attributes"] == []
        assert a["forward_arguments"] == {"forward": ["tokens"], "select": ["h_pre", "tokens"]}


def test_a_fact_table_attribute_would_fail_g6() -> None:
    m = M.build_model("F-OQ", 4096, 2101, backbone(), r1_seed=7, seed_rng=False)
    m.addition.answers = data().facts.answer.clone()  # a model holding the fact-to-answer table
    assert [n for n, v in vars(m.addition).items() if isinstance(v, torch.Tensor)] == ["answers"]


# --- the derangement and the address swap -------------------------------------------------------------------------------------------------------
def test_derangement_is_seeded_and_has_different_answers() -> None:
    answers = data().facts.answer[:512]
    pi = M.derangement(answers, 77)
    assert sorted(pi.tolist()) == list(range(512)) and bool((answers[pi] != answers).all()) and bool((pi != torch.arange(512)).all())
    assert torch.equal(pi, M.derangement(answers, 77)) and not torch.equal(pi, M.derangement(answers, 78))
    with pytest.raises(ValueError):
        M.derangement(torch.zeros(10, dtype=torch.int64), 1)  # no derangement with different answers exists


def test_address_swap_changes_only_the_identifier_bytes_of_trained_records() -> None:
    stream = evaluate.stream_for(data(), FACTS, "panel_a")
    tok, ids = stream.tokens[:16], stream.fact_ids[:16]
    pi = M.derangement(data().facts.answer[:FACTS], 5)
    swapped = M.swapped_tokens(tok, ids, pi, data().facts.ident, FACTS)
    trained = ids < FACTS
    changed = (swapped != tok).reshape(16, 8, 8)
    free = torch.zeros(8, dtype=torch.bool)
    free[1:5] = True
    assert not bool(changed[:, :, ~free].any()) and bool(changed[trained][:, free].any(dim=1).all())
    codes_before = p9modelcodes(tok)
    codes_after = p9modelcodes(swapped)
    keep = (ids < FACTS).reshape(-1)
    assert bool((codes_before.reshape(-1)[keep] != codes_after.reshape(-1)[keep]).all())  # every trained fact reads another fact's code
    assert bool((codes_before.reshape(-1)[~keep] == codes_after.reshape(-1)[~keep]).all())  # unseen facts are not swapped
    assert torch.equal(swapped[:, 63], tok[:, 63])  # position 63 is the last record's answer byte: not an identifier byte


def p9modelcodes(tokens: torch.Tensor) -> torch.Tensor:
    from studies.p9.model import identifier_codes

    return identifier_codes(tokens[:, :63])


# --- a memorized store: useful retention and what removes it ------------------------------------------------------------------------------------
@pytest.fixture(scope="module")
def trained(tmp_path_factory: pytest.TempPathFactory) -> dict[str, dict[str, Any]]:
    root = tmp_path_factory.mktemp("trained")
    out: dict[str, dict[str, Any]] = {}
    for arm in ARMS:
        j = job(root, arm, updates=300, snapshots=(100, 300), name=arm)
        train.train_cell(j)
        paths = evaluate.evaluate_cell(j.cell, root, data(), backbone(), readouts=[100, 300], deep_at=300, r1_seed=j.r1_seed, hash_seed=j.hash_seed, rows=None, out_dir=root / arm, require_train_record=True)
        out[arm] = {"job": j, "records": [json.loads(p.read_text()) for p in paths], "dir": root / arm}
    return out


@pytest.mark.parametrize("arm", ARMS)
def test_memorized_store_is_usefully_retained_and_ablations_remove_it(trained: dict[str, dict[str, Any]], arm: str) -> None:
    panel = trained[arm]["records"][1]["reads"]["main"]["panels"]["A"]
    n = panel["n"]
    assert n == FACTS and panel["correct"] == n and panel["useful"] == n  # a_use = 1 after 300 updates on 128 facts
    chance = core.chance_interval(n)
    assert chance.low <= panel["disabled_correct"] <= chance.high and panel["swap_correct"] <= chance.high  # memory disabled and the address swapped: no longer the answer
    if arm != "D-OQ":
        assert chance.low <= panel["shuffled_correct"] <= chance.high  # value shuffle gives chance
    assert panel["unseen_n"] == 64 and panel["unseen_correct"] <= core.chance_interval(64).high  # unseen facts at chance: no leakage
    early = trained[arm]["records"][0]["reads"]["main"]["panels"]["A"]
    assert early["useful"] <= panel["useful"]


def test_record_layout_and_deep_measures(trained: dict[str, dict[str, Any]]) -> None:
    for arm in ARMS:
        rec = trained[arm]["records"][1]
        m = rec["reads"]["main"]
        assert set(m["panels"]) == {"A", "B"} and set(m["secondary"]) == {"H1", "H2"} and set(m["work"]) >= {"K", "V", "W"} and rec["g5"]["passed"] if "g5" in rec else True
        a = m["panels"]["A"]
        assert ("robustness_correct" in a) == (arm != "D-OQ") and ("deep" in m) and (bool(m["deep"]) == (arm != "D-OQ"))
        if arm != "D-OQ":
            rb = a["robustness_correct"]
            assert set(rb) == {f"{k}_{i}" for k in ("drop5", "drop20", "noise0.1", "noise0.5") for i in range(3)}
            assert sum(rb[f"drop20_{i}"] for i in range(3)) <= sum(rb[f"drop5_{i}"] for i in range(3))  # more dropout never keeps more
            u = m["deep"]["utilization"]
            assert u["distinct_selected_slots"] + u["dead_slots"] == (4096) and u["facts_per_slot_load"] == FACTS / 4096
            assert m["deep"]["support"]["sample_facts"] == FACTS and "separability" in m["deep"]
    assert "ivf" in trained["F-OQ"]["records"][1]["reads"] and "ivf" not in trained["T-OQ"]["records"][1]["reads"]
    ivf = trained["F-OQ"]["records"][1]["reads"]["ivf"]
    assert ivf["ivf_measured"]["recall_of_exhaustive_top8"] <= 1.0 and ivf["index_lists"] == 16 and len(ivf["index_sha256"]) == 64
    assert trained["T-OQ"]["records"][1]["reads"]["main"]["deep"]["separability"]["tree_recall_of_exhaustive_top8"] <= 1.0
    for arm in ("R2", "H8", "F-OQ", "T-OQ"):
        assert "private" in json.dumps(trained[arm]["records"][1]["reads"]["main"]["deep"]["separability"])


def test_every_record_is_counts_only_and_hashes_the_snapshot(trained: dict[str, dict[str, Any]]) -> None:
    for arm in ARMS:
        tr = core.read_record(trained[arm]["dir"] / "train.json", "train")
        assert tr["status"] == "completed" and set(tr["snapshot_meta"]) == {"100", "300"} and tr["snapshot_meta"]["300"]["cpu_seconds"] >= tr["snapshot_meta"]["100"]["cpu_seconds"] > 0
        mv = tr["snapshot_meta"]["300"]["movement"]
        assert mv["total"] == pytest.approx(mv["with_own_gradient"] + mv["without_own_gradient"]) and 0.0 <= mv["share_without"] <= 1.0
        assert (mv["total"] > 0) == (arm != "D-OQ")  # D-OQ has no value rows
        assert tr["identity"]["source_sha256"] and tr["environment"]["python"] and tr["environment"]["torch"] and set(tr["snapshot_sha256"]) == {"100", "300"} and tr["trainable_backbone_parameters"] == 0
        for rec in trained[arm]["records"]:
            for panel in rec["reads"]["main"]["panels"].values():
                assert all(isinstance(panel[k], int) for k in ("n", "correct", "useful", "disabled_correct", "swap_correct", "unseen_n", "unseen_correct"))


def test_evaluation_refuses_a_snapshot_that_does_not_match_its_train_record(trained: dict[str, dict[str, Any]], tmp_path: Path) -> None:
    j = trained["R2"]["job"]
    folder = tmp_path / "tamper"
    folder.mkdir()
    import shutil

    shutil.copytree(trained["R2"]["dir"], folder / "cell")
    rec = json.loads((folder / "cell" / "train.json").read_text())
    rec["snapshot_sha256"]["300"] = "0" * 64
    (folder / "cell" / "train.json").write_text(json.dumps(rec))
    shutil.rmtree(folder / "cell" / "eval")
    with pytest.raises(ValueError):
        evaluate.evaluate_cell(j.cell, tmp_path, data(), backbone(), readouts=[300], deep_at=None, r1_seed=j.r1_seed, hash_seed=j.hash_seed, rows=None, out_dir=folder / "cell", require_train_record=True)
    with pytest.raises(FileExistsError):
        evaluate.evaluate_cell(j.cell, tmp_path, data(), backbone(), readouts=[300], deep_at=None, r1_seed=j.r1_seed, hash_seed=j.hash_seed, rows=None, out_dir=trained["R2"]["dir"], require_train_record=True)


def test_chunked_evaluation_equals_unchunked(trained: dict[str, dict[str, Any]]) -> None:
    j = trained["F-OQ"]["job"]
    model = train.job_model(j, seed_rng=False)
    train.load_model_state(trained["F-OQ"]["dir"] / "snapshots" / core.snapshot_stem(300), model)
    seeds = data().seeds
    pi = evaluate._deranged(data(), FACTS, core.mask_seed(seeds, 0))
    stream = evaluate.stream_for(data(), FACTS, "panel_a")
    with evaluate.eval_chunking(model, 1 << 24):
        big = evaluate.panel_counts(model, data(), FACTS, stream, pi=pi, batch_contexts=64)
    with evaluate.eval_chunking(model, 1 << 11):
        small = evaluate.panel_counts(model, data(), FACTS, stream, pi=pi, batch_contexts=5)
    assert big == small


# --- the index and the baselines ----------------------------------------------------------------------------------------------------------------
def test_index_is_deterministic_and_the_candidate_rule_holds() -> None:
    gen = torch.Generator().manual_seed(3)
    keys = torch.randn(4096, 16, generator=gen)
    a, b = index.build_index(keys, 99), index.build_index(keys, 99)
    assert a.sha256() == b.sha256() and torch.equal(a.assign, b.assign) and a.lists == 16 and int(a.sizes.sum()) == 4096 and index.build_index(keys, 100).sha256() != a.sha256()
    q = torch.nn.functional.normalize(torch.randn(50, 16, generator=gen), dim=-1)
    mask, counts = index.candidate_mask(a, q)
    assert bool((counts >= 512).all()) and bool((mask.sum(1) == counts).all())
    one = index.build_index(keys, 99, lists=1)  # one list holds every key: the candidate set is everything
    assert bool(index.candidate_mask(one, q)[0].all())
    with pytest.raises(ValueError):
        index.kmeans_plus_plus(keys, 0, 1)


def test_ivf_reads_equal_f_oq_when_the_candidates_are_everything() -> None:
    m = M.build_model("F-OQ", 4096, 2101, backbone(), r1_seed=7, seed_rng=False)
    idx = index.build_index(m.addition.keys.detach(), 5, lists=1)
    ivf = index.IVFMemory(m.addition, idx)
    codes = m.oracle_codes(tokens_of())[:, :, :].reshape(-1, 16)
    v0, i0 = m.addition._top_flat(codes)
    v1, i1 = ivf._top_flat(codes)
    assert torch.equal(i0[:, :8], i1[:, :8]) and torch.allclose(v0[:, :8], v1[:, :8]) and ivf.measured()["recall_of_exhaustive_top8"] == 1.0
    assert ivf.measured()["candidates_mean"] == 4096.0 and ivf.measured()["K_mean"] == 4096.0 + 1


def test_knn_predictions_match_brute_force_and_ties_are_wrong() -> None:
    gen = torch.Generator().manual_seed(1)
    keys = torch.nn.functional.normalize(torch.randn(300, 224, generator=gen), dim=-1)
    answers = torch.randint(0, 32, (300,), generator=gen)
    q = torch.nn.functional.normalize(torch.randn(40, 224, generator=gen), dim=-1)
    pred, scored = index.knn_predict(keys, answers, q)
    assert torch.equal(pred, answers[(q @ keys.T).argmax(1)]) and bool((scored == 300).all())
    dup = torch.cat([keys, keys[:1]])
    ans = torch.cat([answers, answers[:1] + 1])
    tied, _ = index.knn_predict(dup, ans, keys[:1])
    assert int(tied[0]) == -1  # an exact tie is counted wrong
    ivf = index.build_index(keys, 3, lists=3)
    pred_ivf, scored_ivf = index.knn_predict(keys, answers, q, ivf)
    assert bool((scored_ivf >= 3).all()) and pred_ivf.shape == (40,)
    assert index.knn_costs(300, None, 300.0) == {"stored_values": 67200.0, "stored_values_per_fact": 224.0, "madds_per_query": 67200.0, "lists": 0.0}


def test_baseline_record_has_dict_knn_and_no_memory(trained: dict[str, dict[str, Any]]) -> None:
    stream = train.training_stream_for(data(), FACTS)
    rec = evaluate.baseline_record(data(), backbone(), FACTS, 1, index.first_epoch(stream), data().seeds)
    p = rec["panels"]["A"]
    assert p["DICT"]["correct"] == p["DICT"]["n"] == FACTS and p["DICT"]["bits_per_fact"] == 25 and p["DICT"]["probes_per_query"] == 1
    assert p["KNN-W"]["stored_values_per_fact"] == 224.0 and p["KNN-W"]["madds_per_query"] == 224.0 * FACTS and p["KNN-W-IVF"]["lists"] == max(1, FACTS // 256)
    assert core.chance_interval(64).low <= p["NO-MEMORY"]["unseen_correct"] <= 64 and p["NO-MEMORY"]["n"] == FACTS
    keys, mean = index.knn_keys(backbone(), data(), FACTS, index.first_epoch(stream))
    assert keys.shape == (FACTS, 224) and torch.allclose(keys.norm(dim=1), torch.ones(FACTS), atol=1e-5) and mean.shape == (224,)


# --- training ---------------------------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("arm", ARMS)
def test_checkpoint_restoration_is_bit_identical(tmp_path: Path, arm: str) -> None:
    r = train.checkpoint_restoration_check(job(tmp_path, arm, updates=64), 4)
    assert r["identical"] and r["mismatches"] == [] and r["tensors_compared"] > 5 and r["resumed_from_update"] == 4


def test_two_identical_runs_are_identical_and_a_snapshot_is_a_valid_shorter_run(tmp_path: Path) -> None:
    a = train.run_job(job(tmp_path, "F-OQ", updates=10, name="a"))
    b = train.run_job(job(tmp_path, "F-OQ", updates=10, name="b"))
    assert all(torch.equal(p, dict(b.model.named_parameters())[n]) for n, p in a.model.named_parameters())
    long = train.run_job(job(tmp_path, "F-OQ", updates=20, snapshots=(10,), name="long"))
    short = train.run_job(job(tmp_path, "F-OQ", updates=10, name="short"))
    model = train.job_model(job(tmp_path, "F-OQ"), seed_rng=False)
    train.load_model_state(tmp_path / "long" / "snapshots" / core.snapshot_stem(10), model)
    assert all(torch.equal(p, dict(short.model.named_parameters())[n]) for n, p in model.named_parameters()) and long.record["status"] == "completed"  # gate G4: a snapshot is a valid shorter run


def test_one_adamw_with_the_registered_hyperparameters(tmp_path: Path) -> None:
    for arm, lr in (("F-OQ", 0.003), ("D-OQ", 0.01), ("D-OQ", 0.001)):
        t = train.Trainer(job(tmp_path, arm, lr=lr), train.job_model(job(tmp_path, arm, lr=lr)))
        assert len(t.optimizers) == 1 and type(t.optimizers[0]).__name__ == "AdamW"
        g = t.optimizers[0].param_groups[0]
        assert g["lr"] == lr and g["weight_decay"] == 0 and g["betas"] == (0.9, 0.999) and g["eps"] == 1e-8 and g["amsgrad"] is False
        assert all(p.requires_grad for _, p in t.named) and not any(n.startswith("backbone.") for n, _ in t.named)


def test_failed_run_is_recorded_and_not_rerun(tmp_path: Path) -> None:
    bad = job(tmp_path, "D-OQ", updates=6, lr=1e30, name="bad")
    with pytest.raises(ValueError):
        train.train_cell(bad)
    rec = core.read_record(tmp_path / "bad" / "train.json", "train")
    assert rec["status"] == "failed" and "non-finite" in rec["reason"]
    with pytest.raises((FileExistsError, ValueError)):
        train.train_cell(bad)  # the logs are opened exclusively: a cell is never silently re-run over its records


def test_rehearsal_mode_writes_only_the_whitelisted_record(tmp_path: Path) -> None:
    j = job(tmp_path, "F-OQ", updates=64, mode="rehearsal", snapshots=(), max_updates=4)
    run = train.run_job(j)
    files = sorted(p.name for p in (tmp_path / "F-OQ-4096").rglob("*") if p.is_file())
    assert files == ["rehearsal.json"] and run.record["status"] == "completed"
    rec = core.read_record(tmp_path / "F-OQ-4096" / "rehearsal.json", "rehearsal")
    assert set(rec) <= train.REHEARSAL_RECORD_KEYS and rec["loss_finite"] is True and rec["updates"] == 4 and rec["cpu_seconds_per_update"] > 0 and not any(w in k for k in rec if k != "loss_finite" for w in train.FORBIDDEN_WORDS)  # the one loss-like key is the boolean loss_finite
    base = dict(rec)
    for key, value in (("task_loss", 1.0), ("accuracy", 0.5), ("bits", 3), ("answer_loss", 2.0), ("extra", 1)):
        with pytest.raises(train.RehearsalRecordError):
            train.validate_rehearsal_record({**base, key: value})
    with pytest.raises(train.RehearsalRecordError):
        train.validate_rehearsal_record({**base, "shapes": {"loss_head": [1]}})  # a name that looks like a loss
    with pytest.raises(train.RehearsalRecordError):
        train.validate_rehearsal_record({**base, "loss_finite": 0.5})
    with pytest.raises(train.RehearsalRecordError):
        train.validate_rehearsal_record({k: v for k, v in base.items() if k != "study"})
    with pytest.raises(ValueError):
        train.run_job(job(tmp_path, "F-OQ", mode="registered", name="reg"))  # registered mode refuses a rehearsal-set data draw (seed namespace)


def test_gate_g2_reads_the_no_memory_baseline_against_the_exact_interval() -> None:
    counts = gates.no_memory_counts(backbone(), data(), [128, 256])
    assert set(counts) == {"A", "B"} and set(counts["A"]) == {"128", "256", "unseen"}
    rep = gates.g2_report({"1": counts})
    assert rep["tests"] == 6 and rep["level_tests"] == 40
    bad = json.loads(json.dumps(counts))
    bad["A"]["256"]["correct"] = 200
    assert not gates.g2_report({"1": bad})["passed"] and not gates.g2_report({})["passed"]


def test_g1_extra_checks_the_training_schedule_against_every_evaluation_stream() -> None:
    r = gates.g1_s1(data(), core.Plan(unit=8), [128, 256])
    assert r["passed"] and any("streams_disjoint" in c for c in r["checks"]) and all(c["passed"] for c in r["checks"])
    ck = r["checks"][0]
    assert ck["equal_frequency"] and sum(ck["hits_in_evaluation_streams"].values()) == 0 and ck["epochs"] >= 1


def test_traffic_record_is_labelled_as_arithmetic_and_simulation(trained: dict[str, dict[str, Any]]) -> None:
    j = trained["F-OQ"]["job"]
    model = train.job_model(j, seed_rng=False)
    train.load_model_state(trained["F-OQ"]["dir"] / "snapshots" / core.snapshot_stem(300), model)
    rec = traffic.traffic_record(model, data(), FACTS, "x", 300, data().seeds)
    assert "no device" in rec["disclaimer"] and rec["setting"] == {"rows_per_page": 8, "cache_fraction": 0.25, "tie": "asc"} and "PENDING LEAD REVIEW" in rec["setting_note"]
    assert rec["value_bytes_per_query"] == 1024 and set(rec["pages_per_query_identity_layout"]) == {"8", "32"} and rec["key_bytes_scored_per_query_if_keys_on_storage"] == 4 * 16 * 4096
    assert isinstance(rec["degenerate"], bool) and rec["working_set_slots"] > 0 and len(rec["null_capacity_misses"]) == 3 and "not an estimate" in rec["key_bytes_label"]
    with pytest.raises(ValueError):
        traffic.traffic_record(train.job_model(job(Path("/nonexistent"), "D-OQ"), seed_rng=False), data(), FACTS, "x", 1, data().seeds)


# --- timing helpers ---------------------------------------------------------------------------------------------------------------------------
def test_timing_waits_for_a_quiet_machine_and_gives_up_after_three_retries() -> None:
    slept: list[float] = []
    assert timing.wait_for_quiet(lambda: 0.4, slept.append) == {"quiet": True, "attempts": 1, "load_averages": [0.4]} and slept == []
    loads = iter([3.0, 2.0, 0.9])
    r = timing.wait_for_quiet(lambda: next(loads), slept.append, pause=5.0)
    assert r["quiet"] and r["attempts"] == 3 and slept == [5.0, 5.0]
    slept.clear()
    never = timing.wait_for_quiet(lambda: 4.0, slept.append, pause=1.0)
    assert never["quiet"] is False and never["attempts"] == 4 and len(slept) == 3  # three retries after the first refusal
    assert timing.NOT_MEASURED == "NOT MEASURED" and timing.THROUGHPUT_NOT_MEASURED == "THROUGHPUT NOT MEASURED"


def test_throughput_stability_rule_and_cpu_timing(tmp_path: Path) -> None:
    steady = timing.measure_qps(lambda b: sum(range(2000)) and None, 1, repeats=5, min_seconds=0.02)
    assert steady["stable"] == (steady["cv"] <= core.THROUGHPUT_CV_MAX) and len(steady["qps"]) == 5 and steady["label"] in ("STABLE", "UNSTABLE")
    state = {"i": 0}

    def erratic(b: int) -> None:
        state["i"] += 1
        for _ in range(100 if (state["i"] // 7) % 2 else 40000):
            pass

    wild = timing.measure_qps(erratic, 1, repeats=5, min_seconds=0.01)
    assert wild["label"] in ("STABLE", "UNSTABLE") and wild["stable"] == (wild["cv"] <= 0.05)
    r = timing.cpu_seconds_per_update(job(tmp_path, "H8", updates=1000, mode="rehearsal", snapshots=()), warmup=2, updates=4, repeats=3)
    assert r["cpu_seconds_per_update"] > 0 and len(r["runs"]) == 3 and r["warmup_updates"] == 2 and core.TIMING_WARMUP_UPDATES == 32 and core.TIMING_UPDATES == 256 and core.TIMING_REPEATS == 3
    for arm in ("F-OQ", "T-OQ", "H8", "D-OQ"):
        model = M.build_model(arm, 4096, 2101, backbone(), r1_seed=7, hash_seed=1, seed_rng=False)
        rec = timing.throughput_record(model, data(), FACTS, data().seeds)
        assert set(rec) == {"1", "128"} and rec["128"]["median_qps"] > 0
    ivf = timing.throughput_record(M.build_model("F-OQ", 4096, 2101, backbone(), r1_seed=7, seed_rng=False), data(), FACTS, data().seeds, "F-OQ-IVF")
    assert set(ivf) == {"1", "128"}
