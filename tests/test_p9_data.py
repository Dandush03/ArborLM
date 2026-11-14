# ruff: noqa: E501
"""P9 package I1: task data (ADR-0017 section 4) and gate G1. Tiny sizes, test (rehearsal-namespace)
seeds, no registered or rehearsal stage. Self-check only: not independent review, not Astra
validation, not human approval."""

import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402
import torch  # noqa: E402

from studies.p9 import core, data  # noqa: E402

SIZES = data.DataSizes(main_trained=512, unseen=64, lane_d_per_set=128)
SEEDS = core.rehearsal_seeds(7)


def _corpus() -> bytes:
    g = torch.Generator().manual_seed(11)
    return bytes(torch.randint(0, 256, (2048 * 65,), generator=g).tolist())


@pytest.fixture(scope="module")
def draw() -> data.StudyData:
    return data.build_study_data(SEEDS, _corpus(), sizes=SIZES)


def _cell(draw: data.StudyData, **kw: object) -> core.Cell:
    base = next(c for c in core.cells() if c.block == "A1" and c.slots == 4096 and c.seed == 1701)
    import dataclasses

    return dataclasses.replace(base, facts=SIZES.main_trained, **kw)  # type: ignore[arg-type]


def test_seeds_are_rehearsal_namespace() -> None:
    for v in [*SEEDS.data_values(), *SEEDS.null_seeds_a, *SEEDS.null_seeds_b]:
        core.assert_not_registered_seed(v)


def test_identifier_uniqueness_checksum_hamming(draw: data.StudyData) -> None:
    t = draw.facts
    codes = data.encode_identifiers(t.ident)
    assert torch.unique(codes).numel() == t.size == 512 + 64
    assert bool((t.ident[:, 4] == t.ident[:, :4].sum(1) % 32).all())
    assert bool(((t.ident >= 0) & (t.ident < 32)).all())
    # minimum pairwise Hamming distance >= 2 (brute force on the 576 ids)
    dist = (t.ident[:, None, :] != t.ident[None, :, :]).sum(-1)
    dist.fill_diagonal_(5)
    assert int(dist.min()) >= 2
    # clusters of 16, unseen -1, answers in range
    assert bool((torch.bincount(t.cluster[:512]) == 16).all()) and bool((t.cluster[512:] == -1).all())
    assert bool(((t.answer >= 0) & (t.answer < 32)).all())
    # main and Lane D identifiers are disjoint, and Lane D has its own clusters
    assert not bool(torch.isin(codes, data.encode_identifiers(draw.lane_d.ident)).any())
    assert int(draw.lane_d.cluster[:128].max()) == 7 and int(draw.lane_d.cluster[128:].min()) == 8


def test_identifier_hamming_for_hard_sizes() -> None:
    table = data.make_fact_table(core.REHEARSAL_SEED_BASE + 1, 4096, 0, cluster_seed=179002)
    codes = data.encode_identifiers(table.ident)
    assert torch.unique(codes).numel() == 4096
    for leave in range(5):
        keep = [k for k in range(5) if k != leave]
        key = sum(table.ident[:, k] * 32**n for n, k in enumerate(keep))
        assert torch.unique(key).numel() == 4096  # no two ids share four positions


def test_fact_table_is_nested_prefix_and_deterministic() -> None:
    big = data.make_fact_table(179101, 1024, 32, cluster_seed=179102)
    again = data.make_fact_table(179101, 1024, 32, cluster_seed=179102)
    assert torch.equal(big.ident, again.ident) and torch.equal(big.answer, again.answer)
    other = data.make_fact_table(179101, 1024, 32, cluster_seed=179103)
    assert not torch.equal(big.ident[:1024], other.ident[:1024])  # cluster seed regroups
    assert torch.equal(torch.sort(data.encode_identifiers(big.ident[:1024])).values, torch.sort(data.encode_identifiers(other.ident[:1024])).values)
    assert torch.equal(big.answer, other.answer)


def test_make_fact_table_excludes() -> None:
    a = data.make_fact_table(179201, 256, 0, cluster_seed=179202)
    b = data.make_fact_table(179203, 256, 0, exclude=data.encode_identifiers(a.ident).tolist(), cluster_seed=179204)
    assert not bool(torch.isin(data.encode_identifiers(b.ident), data.encode_identifiers(a.ident)).any())


def test_templates_byte_sets_disjoint(draw: data.StudyData) -> None:
    t = draw.templates
    sets = {s: t.byte_set(s) for s in data.TEMPLATE_SETS}
    assert len(sets["T"]) == 32 and len(sets["H1"]) == 8 and len(sets["H2"]) == 8
    assert not sets["T"] & sets["H1"] and not sets["T"] & sets["H2"] and not sets["H1"] & sets["H2"]
    assert not (sets["T"] | sets["H1"] | sets["H2"]) & set(core.ALPHABET)
    assert len(t.train) == 16 and len(t.h1) == 8 and len(t.h2) == 8
    assert len({x.separator for x in t.train}) == 16 and len({x.binding for x in t.train}) == 16
    assert len({x.separator for x in t.h1}) == 4 and len({x.binding for x in t.h1}) == 4
    assert len(set(t.h1)) == 8 and len(set(t.h2)) == 8
    assert sets["T"] | sets["H1"] | sets["H2"] == set(draw.pool)
    # deterministic in the seed, different for another seed
    assert data.split_templates(draw.pool, SEEDS.templates) == t
    assert data.split_templates(draw.pool, SEEDS.templates + 5) != t


def test_streams_exist_and_shapes(draw: data.StudyData) -> None:
    names = {*core.STREAM_NAMES, "lane_d_a_A", "lane_d_a_B", "lane_d_b_A", "lane_d_b_B"}
    assert set(draw.streams) == names
    assert draw.streams["calibration"].tokens.shape == (2 * 512 // 8, 64)
    assert draw.streams["panel_a"].tokens.shape == ((512 + 64) // 8, 64)
    for name in ("h1", "h2", "mixed"):
        assert draw.streams[name].tokens.shape == (512 // 8, 64)
    for s in draw.streams.values():
        assert s.tokens.dtype == torch.int64 and s.sha256 == data.stream_sha256(s)


def test_equal_frequency_and_exact_coverage(draw: data.StudyData) -> None:
    t = draw.facts
    for name, passes in (("calibration", 2), ("h1", 1), ("h2", 1), ("mixed", 1)):
        counts = torch.bincount(draw.streams[name].fact_ids.reshape(-1), minlength=t.size)
        assert bool((counts[:512] == passes).all()) and bool((counts[512:] == 0).all()), name
    for name in ("panel_a", "panel_b"):
        counts = torch.bincount(draw.streams[name].fact_ids.reshape(-1), minlength=t.size)
        assert bool((counts == 1).all()), name
    for name in ("lane_d_a_A", "lane_d_a_B", "lane_d_b_A", "lane_d_b_B"):
        counts = torch.bincount(draw.streams[name].fact_ids.reshape(-1), minlength=draw.lane_d.size)
        expected = torch.zeros(draw.lane_d.size, dtype=torch.int64)
        lo = 0 if name.endswith("A") else 128
        expected[lo : lo + 128] = 1
        assert torch.equal(counts, expected), name


def test_answer_site_positions_and_layout(draw: data.StudyData) -> None:
    s = draw.streams["panel_a"]
    t = draw.facts
    seps, binds = draw.templates.tensors("T")
    rec = s.tokens.reshape(-1, 8, 8)
    alphabet = torch.tensor(core.ALPHABET)
    for r in range(8):
        pos = core.answer_site_position(r)
        assert pos == 8 * r + 6 and core.answer_target_position(r) == 8 * r + 7
        assert bool((s.tokens[:, pos] == binds[s.template]).all())  # the binding byte is the answer site
        assert bool((s.tokens[:, pos + 1] == alphabet[t.answer[s.fact_ids[:, r]]]).all())
        assert bool((s.tokens[:, 8 * r] == seps[s.template]).all())
    assert bool((rec[:, :, 1:6] == alphabet[t.ident[s.fact_ids]]).all())
    assert torch.equal(s.answer_targets(), t.answer[s.fact_ids])
    assert s.tokens.shape[1] == 64 and 8 * 63 // 8 == 63  # 63 targets, 8 answer sites per context


def test_cluster_rule(draw: data.StudyData) -> None:
    t = draw.facts
    for name in ("calibration", "h1", "h2", "panel_a", "panel_b"):
        s = draw.streams[name]
        cl = t.cluster[s.fact_ids]
        unseen = (s.fact_ids >= 512).all(dim=1)
        assert bool(((cl == cl[:, :1]).all(1) | unseen).all()), name
        srt = s.fact_ids.sort(1).values
        assert bool((srt[:, 1:] != srt[:, :-1]).all()), name  # eight distinct facts
    mixed = draw.streams["mixed"]
    cl = t.cluster[mixed.fact_ids].sort(1).values
    assert bool((cl[:, 1:] != cl[:, :-1]).all())  # eight different clusters
    # training contexts too
    ts = data.training_stream_for(draw, _cell(draw))
    b = ts.batch(3)
    assert bool((t.cluster[b.fact_ids] == t.cluster[b.fact_ids][:, :1]).all())
    assert b.fact_ids.shape == (16, 8) and b.tokens.shape == (16, 64)


def test_unseen_controls_in_separate_contexts(draw: data.StudyData) -> None:
    for name in ("panel_a", "panel_b"):
        s = draw.streams[name]
        unseen = s.fact_ids >= 512
        assert bool((unseen.all(1) | (~unseen).all(1)).all())
        assert int(unseen.all(1).sum()) == 8
        assert bool((s.cluster[unseen.all(1)] == -1).all())


def test_panel_contexts_absent_from_training_by_hash(draw: data.StudyData) -> None:
    ts = data.training_stream_for(draw, _cell(draw))
    keys = ts.keys(300)
    for name in ("calibration", "panel_a", "panel_b", "h1", "h2", "mixed"):
        stream_keys = data.context_keys(draw.streams[name].fact_ids)
        assert not bool(torch.isin(stream_keys, keys).any()), name
    # the evaluation streams do not overlap each other either (apart from A/B sharing unseen groups by chance)
    a = data.context_keys(draw.streams["panel_a"].fact_ids[:-8])
    b = data.context_keys(draw.streams["panel_b"].fact_ids[:-8])
    cal = data.context_keys(draw.streams["calibration"].fact_ids)
    assert not bool(torch.isin(a, b).any()) and not bool(torch.isin(a, cal).any()) and not bool(torch.isin(b, cal).any())
    # a context of the training schedule would be detected
    batch = ts.batch(1)
    assert bool(torch.isin(data.context_keys(batch.fact_ids), keys).all())
    assert data.context_key(batch.fact_ids[0]) == int(data.context_keys(batch.fact_ids[:1])[0]).to_bytes(8, "little", signed=True)


def test_pair_classes_are_roughly_uniform() -> None:
    perm = torch.rand(20000, 16, generator=torch.Generator().manual_seed(3)).argsort(1)
    cls = data._partition_class(perm, torch.randint(0, 2048, (20000,), generator=torch.Generator().manual_seed(4)), 12345)
    freq = torch.bincount(cls, minlength=32).double() / 20000
    assert float(freq.min()) > 0.02 and float(freq.max()) < 0.045


def test_training_stream_equal_frequency_and_purity(draw: data.StudyData) -> None:
    cell = _cell(draw)
    ts = data.training_stream_for(draw, cell)
    upe = ts.updates_per_epoch
    assert upe == 512 // 128 == 4
    expo = ts.exposures(upe * 5)
    assert bool((expo == 5).all())
    part = ts.exposures(upe * 5 + 2)
    assert int(part.min()) == 5 and int(part.max()) == 6 and int((part - 5).sum()) == 2 * 128
    # one epoch covers every fact exactly once
    seen = torch.cat([ts.batch(u).fact_ids.reshape(-1) for u in range(1, upe + 1)])
    assert torch.equal(torch.sort(seen).values, torch.arange(512))
    # purity: batch(u) is a function of u only, independent of call order
    first = [ts.batch(u) for u in (1, 7, 3, 7, 1)]
    assert torch.equal(first[0].tokens, first[4].tokens) and torch.equal(first[1].tokens, first[3].tokens)
    fresh = data.training_stream_for(draw, cell)
    assert torch.equal(fresh.batch(7).tokens, first[1].tokens)
    assert torch.equal(fresh.batch(7).fact_ids, first[1].fact_ids)
    # different epochs differ
    assert not torch.equal(ts.batch(1).fact_ids, ts.batch(1 + upe).fact_ids)
    with pytest.raises(ValueError):
        ts.batch(0)


def test_training_tokens_have_training_templates_only(draw: data.StudyData) -> None:
    ts = data.training_stream_for(draw, _cell(draw))
    b = ts.batch(2)
    seps, binds = draw.templates.tensors("T")
    assert bool(torch.isin(b.tokens[:, 0], seps).all()) and bool(torch.isin(b.tokens[:, 6], binds).all())


def test_lane_d_schedules(draw: data.StudyData) -> None:
    arms = {c.lane_d_arm: c for c in core.cells() if c.block in ("D1", "D2") and c.seed == 1701 and c.arch == "flat"}
    import dataclasses

    def tiny(c: core.Cell, facts: int) -> core.Cell:
        return dataclasses.replace(c, facts=facts)

    a = data.training_stream_for(draw, tiny(arms["phaseA"], 128))
    b = data.training_stream_for(draw, tiny(arms["sequential"], 128))
    j = data.training_stream_for(draw, tiny(arms["joint"], 256))
    r = data.training_stream_for(draw, tiny(arms["replay"], 128))
    assert bool((a.facts < 128).all()) and bool((b.facts >= 128).all()) and j.facts.shape[0] == 256
    bat = r.batch(1)
    assert bat.replay_tokens is not None and bat.replay_fact_ids is not None
    assert bool((bat.fact_ids >= 128).all()) and bool((bat.replay_fact_ids < 128).all())
    assert bat.replay_tokens.shape == (16, 64)
    assert data.training_stream_for(draw, tiny(arms["memory_only"], 128)).batch(1).replay_tokens is None
    # Lane D panels
    panels = data.panel_streams(draw, tiny(arms["sequential"], 128), "A")
    assert [p.name for p in panels] == ["lane_d_a_A", "lane_d_a_B"]


def test_panel_streams_restrict_to_cell_facts(draw: data.StudyData) -> None:
    c = _cell(draw)
    full = data.panel_streams(draw, c, "A")[0]
    assert full is draw.streams["panel_a"]
    import dataclasses

    small = data.panel_streams(draw, dataclasses.replace(c, facts=128), "B")[0]
    ids = small.fact_ids
    assert bool(((ids < 128).all(1) | (ids >= 512).all(1)).all())
    assert int(((ids < 128).all(1)).sum()) == 16 and int((ids >= 512).all(1).sum()) == 8
    assert small.sha256 == data.stream_sha256(small) and small.sha256 != draw.streams["panel_b"].sha256
    with pytest.raises(ValueError):
        data.panel_streams(draw, c, "C")


def test_facts_of_and_lut(draw: data.StudyData) -> None:
    c = _cell(draw)
    ids = data.facts_of(draw, c)
    assert torch.equal(ids, torch.arange(512))
    lut = data.identifier_lut(draw.facts, ids)
    codes = data.encode_identifiers(draw.facts.ident[ids])
    assert torch.equal(lut[codes], torch.arange(512))
    unseen_codes = data.encode_identifiers(draw.facts.ident[512:])
    assert bool((lut[unseen_codes] == -1).all()) and int((lut >= 0).sum()) == 512


def test_neighbour_flags_matches_brute_force() -> None:
    table = data.make_fact_table(179301, 2048, 0, cluster_seed=179302)
    flags = data.neighbour_flags(table)
    dist = (table.ident[:, None, :] != table.ident[None, :, :]).sum(-1)
    dist.fill_diagonal_(5)
    assert torch.equal(flags, (dist <= 2).any(1))
    sub = data.neighbour_flags(table, among=512)
    assert torch.equal(sub, (dist[:, :512] <= 2).any(1))
    assert 0.2 < float(flags.double().mean()) < 0.8  # about 45-49% at 2,048 facts (ADR 4.1)


def test_determinism_same_seeds_same_hashes(draw: data.StudyData) -> None:
    again = data.build_study_data(SEEDS, _corpus(), sizes=SIZES)
    assert draw.sha256s() == again.sha256s()
    other = data.build_study_data(core.rehearsal_seeds(8), _corpus(), sizes=SIZES)
    assert draw.sha256s()["stream:panel_a"] != other.sha256s()["stream:panel_a"]
    assert draw.sha256s()["facts"] != other.sha256s()["facts"]


def test_registered_pool_mismatch_is_refused() -> None:
    with pytest.raises(ValueError):
        data.build_study_data(core.registered_seeds(), _corpus(), sizes=SIZES)


def test_sizes_validation() -> None:
    with pytest.raises(ValueError):
        data.DataSizes(main_trained=100)
    with pytest.raises(ValueError):
        data.make_fact_table(179401, 100, 0, cluster_seed=179402)


# --- G1 --------------------------------------------------------------------------------------------------
def _g1(d: data.StudyData, **kw: object) -> data.G1Report:
    return data.run_g1(d, permutations=400, train_epochs=6, **kw)  # type: ignore[arg-type]


def _failed(report: data.G1Report) -> set[str]:
    return {c["name"] for c in report["checks"] if not c["passed"]}


def test_g1_passes_on_a_good_draw(draw: data.StudyData) -> None:
    report = _g1(draw)
    assert report["passed"], [c for c in report["checks"] if not c["passed"]]
    assert set(report["tests_per_stream"]) == set(draw.streams)
    assert all(v == core.G1_TESTS_PER_STREAM == 8 for v in report["tests_per_stream"].values())
    names = {c["name"] for c in report["checks"]}
    assert {"identifiers", "coverage", "layout", "context_rules", "independence", "equal_frequency", "panel_not_in_training", "dictionary_lookup", "seeds_disjoint", "identifiers_disjoint_worlds"} <= names
    independence = [c for c in report["checks"] if c["name"] == "independence"]
    assert all(c["detail"]["k"] == 8 for c in independence)


def test_g1_fails_on_duplicated_identifier(draw: data.StudyData) -> None:
    bad = copy.deepcopy(draw)
    bad.facts.ident[5] = bad.facts.ident[9]
    assert "identifiers" in _failed(_g1(bad, only_streams=["panel_a"]))


def test_g1_fails_on_bad_checksum(draw: data.StudyData) -> None:
    bad = copy.deepcopy(draw)
    bad.facts.ident[7, 4] = (bad.facts.ident[7, 4] + 1) % 32
    assert "identifiers" in _failed(_g1(bad, only_streams=["panel_a"]))


def test_g1_fails_on_one_symbol_neighbour(draw: data.StudyData) -> None:
    bad = copy.deepcopy(draw)
    bad.facts.ident[20] = bad.facts.ident[21]
    bad.facts.ident[20, 3] = (bad.facts.ident[20, 3] + 1) % 32  # distance 1 from fact 21, checksum now wrong too
    report = _g1(bad, only_streams=["panel_a"])
    detail = next(c for c in report["checks"] if c["name"] == "identifiers" and c["detail"]["world"] == "main")["detail"]
    assert detail["min_hamming_at_least_2"] is False and detail["checksum"] is False


def test_g1_fails_when_a_panel_context_is_copied_from_training(draw: data.StudyData) -> None:
    bad = copy.deepcopy(draw)
    ts = data.training_stream_for(bad, _cell(bad))
    ids, template, cluster = ts.epoch_contexts(0)
    s = bad.streams["panel_a"]
    s.fact_ids[0] = ids[0]
    s.cluster[0] = cluster[0]
    s.template[0] = template[0]
    s.tokens[0] = ts.batch(1).tokens[0] if torch.equal(ts.batch(1).fact_ids[0], ids[0]) else data._build_tokens(
        bad.facts, ids[:1], draw.templates.tensors("T")[0][template[:1]], draw.templates.tensors("T")[1][template[:1]]
    )[0]
    s.sha256 = data.stream_sha256(s)
    failed = _failed(_g1(bad, only_streams=["panel_a"]))
    assert "panel_not_in_training" in failed


def test_g1_fails_on_unequal_frequency(draw: data.StudyData) -> None:
    bad = copy.deepcopy(draw)
    s = bad.streams["h1"]
    s.fact_ids[1] = s.fact_ids[0]  # one context appears twice, another's facts vanish
    s.tokens[1] = s.tokens[0]
    s.cluster[1], s.template[1] = s.cluster[0], s.template[0]
    s.sha256 = data.stream_sha256(s)
    failed = _failed(_g1(bad, only_streams=["h1"]))
    assert "coverage" in failed


def test_g1_fails_on_corrupt_layout_and_context_rule(draw: data.StudyData) -> None:
    bad = copy.deepcopy(draw)
    s = bad.streams["h2"]
    s.tokens[2, 7] = (s.tokens[2, 7] - 1) % 256 if s.tokens[2, 7] != 0x40 else 0x41  # wrong answer byte
    failed = _failed(_g1(bad, only_streams=["h2"]))
    assert "layout" in failed
    bad = copy.deepcopy(draw)
    s = bad.streams["h2"]
    s.fact_ids[3, 1] = s.fact_ids[3, 0]  # a record repeats an earlier fact
    assert "context_rules" in _failed(_g1(bad, only_streams=["h2"]))


def test_independence_detects_answer_correlated_with_identifier_position(draw: data.StudyData) -> None:
    bad = copy.deepcopy(draw)
    t = bad.facts
    t.answer[:512] = t.ident[:512, 2]  # answer equals identifier symbol 3 for every trained fact
    s = bad.streams["h1"]
    check = data.stream_independence(s, t, 8100, SEEDS.permutation_tests)
    assert not check["passed"]
    failing = [x["name"] for x in check["detail"]["tests"] if x["p_adjusted"] < core.G1_P_THRESHOLD]
    assert "identifier_3" in failing
    good = data.stream_independence(draw.streams["h1"], draw.facts, 8100, SEEDS.permutation_tests)
    assert good["passed"], good["detail"]["tests"]
    assert good["detail"]["smallest_adjusted_p"] >= core.G1_P_THRESHOLD


def test_independence_detects_cluster_and_template_dependence(draw: data.StudyData) -> None:
    t = copy.deepcopy(draw.facts)
    t.answer[:512] = t.cluster[:512] % 32  # answer a function of the cluster
    check = data.stream_independence(draw.streams["h2"], t, 8100, SEEDS.permutation_tests)
    assert "cluster" in [x["name"] for x in check["detail"]["tests"] if x["p_adjusted"] < core.G1_P_THRESHOLD]
    # answers correlated with the record's template are detected on the record level
    s = draw.streams["h1"]
    flat = s.fact_ids.reshape(-1)
    tmpl = s.template.repeat_interleave(8)
    res = data.independence_tests(
        (tmpl * 4) % 32, [("template", tmpl)], 500, torch.Generator().manual_seed(1)
    )
    assert res[0]["p"] < 0.01 and flat.numel() == tmpl.numel()


def test_independence_p_values_are_uniform_under_the_null() -> None:
    g = torch.Generator().manual_seed(21)
    ps = []
    for i in range(30):
        ans = torch.randint(0, 32, (400,), generator=g)
        var = torch.randint(0, 6, (400,), generator=g)
        ps.append(data.independence_tests(ans, [("v", var)], 200, torch.Generator().manual_seed(i))[0]["p"])
    p = torch.tensor(ps)
    assert 0.25 < float(p.mean()) < 0.75 and float((p < 0.01).sum()) <= 1


def test_g1_fails_for_registered_namespace_violation() -> None:
    bad = core.SeedSet(**{**core.rehearsal_seeds(7).__dict__, "facts": 170001})
    d = data.build_study_data(bad, _corpus(), sizes=SIZES)
    assert "seeds_disjoint" in _failed(_g1(d, only_streams=["h1"]))
