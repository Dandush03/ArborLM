# ruff: noqa: E501
"""P9 package I3, ``studies/p9/evaluate.py``: knowledge metrics, interventions, minimal supports,
specificity and usage on hand-constructed memories whose truth is known.

Tiny sizes (128 trained facts), a random frozen backbone (plus a stand-in upper block for the
early-storage case), test seeds (>= 179001). No real data, no registered seed, no stage.

Self-check only: not independent review, not Astra validation, not human approval.
"""

import copy
import math

import pytest
import torch
from test_p9_evaluate_support import (
    CARRIER_BASE,
    FACTS,
    SITES,
    draw,
    hand_cache,
    make_model,
    nomem_of,
    r2_fixture,
    trained_mask,
)
from test_p9_evaluate_support import cell as cell_of

from studies.p9 import core, evaluate
from studies.p9.evaluate import ReadCache
from studies.p9.model import Selection


def answers(cache: ReadCache) -> torch.Tensor:
    return cache.stream.answer_targets().reshape(-1)


def scored(cache: ReadCache) -> core.AnswerScores:
    return evaluate.score_cache(cache, answers(cache))


def brute_force_logits(model, cache: ReadCache, zero_slots: torch.Tensor) -> torch.Tensor:  # type: ignore[no-untyped-def]
    """Answer-site logits of a copy of ``model`` whose value rows ``zero_slots`` are actually zero,
    through the ordinary full forward (no cache)."""
    other = copy.deepcopy(model)
    with torch.no_grad():
        other.addition.values[zero_slots] = 0.0
        logits, _ = other(cache.tokens[:, : core.INPUT_LENGTH])
    return logits[:, list(SITES)]


# --- the cache -------------------------------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("block", "match"),
    [
        ("A1", {"arch": "flat", "slots": 4096, "seed": 1701}),
        ("A2", {"slots": 4096, "seed": 1701}),
        ("A8", {"slots": 4096, "seed": 1701}),
    ],
)
def test_cache_metrics_equal_direct_forward(block: str, match: dict[str, object]) -> None:
    c = cell_of(block, **match)
    model = make_model(c)
    stream = draw().streams["panel_a"]
    cache = evaluate.build_cache(model, stream)
    with torch.no_grad():
        logits, _ = model(stream.tokens[:, : core.INPUT_LENGTH])
    direct = logits[:, list(SITES)]
    assert torch.allclose(cache.logits_answer, direct, atol=1e-5)
    mine, ref = scored(cache), core.score_answer_sites(direct.reshape(-1, 256), answers(cache))
    assert torch.equal(mine.correct, ref.correct)
    assert torch.allclose(mine.p_correct, ref.p_correct, atol=1e-5)
    # no intervention reproduces the cached logits exactly
    assert torch.equal(evaluate.logits_with(model, cache), cache.logits_answer)
    # chunking does not change the cache
    small = evaluate.build_cache(model, stream, batch_contexts=3)
    assert torch.allclose(small.logits_answer, cache.logits_answer, atol=1e-5)
    if cache.selection is not None and small.selection is not None:
        assert torch.equal(small.selection.selected, cache.selection.selected)
        assert cache.selection.candidate_ids is None  # candidates are kept at answer sites only
        assert cache.site_candidate_ids is not None and cache.site_candidate_ids.shape[1:] == (
            8,
            64,
        )


def test_knockout_equals_brute_force_with_values_zeroed() -> None:
    model = make_model(cell_of("A1", arch="flat", slots=4096, seed=1701))
    with torch.no_grad():
        model.addition.values.mul_(40.0)  # make the memory matter
        model.addition.gate.fill_(2.0)
    cache = evaluate.build_cache(model, draw().streams["panel_a"])
    sel = cache.selection
    assert sel is not None
    counts = torch.bincount(sel.selected.reshape(-1), minlength=4096)
    chosen = counts.topk(25).indices
    mask = torch.isin(sel.selected, chosen)
    assert int(mask.sum()) > 100
    fast = evaluate.logits_with(model, cache, knockout=mask)
    slow = brute_force_logits(model, cache, chosen)
    assert torch.allclose(fast, slow, atol=1e-5)
    assert not torch.allclose(
        fast, cache.logits_answer, atol=1e-3
    )  # the intervention did something
    # value-table replacement equals brute force too
    zeroed = model.addition.values.detach().clone()
    zeroed[chosen] = 0.0
    assert torch.allclose(evaluate.logits_with(model, cache, values=zeroed), slow, atol=1e-5)
    # disabling equals the frozen backbone alone
    off = evaluate.logits_with(model, cache, disabled=True)
    assert torch.allclose(off, nomem_logits(model, cache), atol=1e-5)


def nomem_logits(model, cache: ReadCache) -> torch.Tensor:  # type: ignore[no-untyped-def]
    from studies.p9 import controls

    return controls.answer_site_logits_no_memory(model.backbone, cache.stream).reshape(
        cache.tokens.shape[0], 8, 256
    )


def test_context_knockout_matches_brute_force_per_fact() -> None:
    """``_Upper.context``: values of drawn slots removed wherever selected up to a fact's answer site
    equals zeroing those rows and running the ordinary forward, fact by fact (with slot sharing)."""
    model = make_model(cell_of("A1", arch="flat", slots=4096, seed=1701))
    with torch.no_grad():
        model.addition.values.mul_(40.0)
        model.addition.gate.fill_(2.0)
    cache = evaluate.build_cache(model, draw().streams["panel_a"])
    sc = scored(cache)
    sel = cache.selection
    assert sel is not None
    up = evaluate._upper(model, cache)
    g = torch.Generator().manual_seed(179101)
    checked = 0
    for r in (0, 3, 7):
        ctx = torch.arange(0, 12)
        # slots drawn from the selections of the same contexts so that the knock-out acts
        pool = sel.selected[ctx][:, : 8 * r + 7].reshape(len(ctx), -1)
        pick = torch.randint(0, pool.shape[1], (len(ctx), 8), generator=g)
        slots = pool.gather(1, pick)
        got = up.context(model, cache, ctx, r, slots, sc.answer[ctx * 8 + r], only_record=False)
        for i in range(len(ctx)):
            expect = brute_force_logits(model, cache, slots[i])[int(ctx[i]), r]
            ref = core.score_answer_sites(expect[None], sc.answer[ctx[i : i + 1] * 8 + r])
            assert torch.allclose(got.p_correct[i], ref.p_correct[0], atol=1e-5)
            checked += 1
    assert checked == 36
    # the literal 'record only' reading cannot change anything for slots outside the record
    pool_all = torch.arange(3000, 3008)[None].expand(12, 8)
    plain = up.context(
        model,
        cache,
        torch.arange(12),
        5,
        pool_all,
        sc.answer[torch.arange(12) * 8 + 5],
        only_record=True,
    )
    assert torch.allclose(plain.p_correct, sc.p_correct[torch.arange(12) * 8 + 5], atol=1e-5)


def test_value_permutation_is_a_seeded_derangement_and_gives_chance() -> None:
    model, cache, _ = r2_fixture()
    p1 = evaluate.permute_values(model, 179201)
    assert torch.equal(p1, evaluate.permute_values(model, 179201))
    assert not torch.equal(p1, evaluate.permute_values(model, 179202))
    table = model.addition.values.detach()
    assert sorted(p1.sum(1).tolist()) == pytest.approx(
        sorted(table.sum(1).tolist()), abs=1e-4
    )  # a permutation of the rows
    assert not bool((p1 == table).all(dim=1).any())  # no row keeps its own value
    tr = trained_mask(cache)
    assert float(scored(cache).correct[tr].float().mean()) == 1.0
    wrong = evaluate.logits_with(model, cache, values=p1)
    perm = core.score_answer_sites(wrong.reshape(-1, 256), answers(cache))
    n = int(tr.sum())
    assert int(perm.correct[tr].sum()) <= core.chance_interval(n, 8).high
    off = core.score_answer_sites(
        evaluate.logits_with(model, cache, disabled=True).reshape(-1, 256), answers(cache)
    )
    assert int(off.correct[tr].sum()) <= core.chance_interval(n, 8).high


# --- candidates --------------------------------------------------------------------------------------------------
def test_candidate_union_orders_by_summed_weight_with_id_ties() -> None:
    ids = torch.tensor(
        [[[5, 9, 2, -1, 7, 7, 3, 1], [9, 4, 2, 8, 8, 8, 0, -1]]]
    )  # [1, 2 positions, 8]
    w = torch.tensor(
        [[[0.4, 0.2, 0.1, 0.0, 0.05, 0.05, 0.1, 0.1], [0.3, 0.2, 0.1, 0.1, 0.1, 0.1, 0.1, 0.0]]]
    )
    cand, count = evaluate._candidates(ids, w)
    sums = {5: 0.4, 9: 0.5, 2: 0.2, 7: 0.1, 3: 0.1, 1: 0.1, 4: 0.2, 8: 0.3, 0: 0.1}
    assert int(count[0]) == len(sums)  # -1 is not a slot; duplicates are merged
    got = cand[0, : len(sums)].tolist()
    assert got == [9, 5, 8, 2, 4, 0, 1, 3, 7]  # weight descending, equal sums by ascending id
    assert [round(sums[s], 3) for s in got] == sorted(
        (round(v, 3) for v in sums.values()), reverse=True
    )
    assert bool((cand[0, len(sums) :] == -2).all())


def test_other_slot_draw_invariants() -> None:
    pool = torch.arange(100, 140)
    own = torch.tensor([[100, 101, 102, -1], [139, 138, 120, 121], [100, 101, 102, 103]])
    out = evaluate._draw_other_slots(pool, own, torch.Generator().manual_seed(179301), 8)
    assert out.shape == (3, 8)
    for row in range(3):
        drawn = [int(s) for s in out[row] if s >= 0]
        assert len(drawn) == len(set(drawn)) == 8
        assert set(drawn) <= set(pool.tolist()) and not set(drawn) & set(own[row].tolist())
    tiny = evaluate._draw_other_slots(
        torch.tensor([5, 6, 7]), torch.tensor([[6]]), torch.Generator().manual_seed(1), 8
    )
    assert sorted(int(s) for s in tiny[0] if s >= 0) == [5, 7] and int((tiny[0] == -2).sum()) == 6


# --- minimal supports --------------------------------------------------------------------------------------------
def test_dedicated_slot_memory_has_support_one_and_ustar_equals_facts() -> None:
    model, cache, _ = r2_fixture()
    tr = trained_mask(cache)
    sc = scored(cache)
    nomem = nomem_of(model, cache.stream)
    assert float(sc.correct[tr].float().mean()) == 1.0
    sup = evaluate.minimal_supports(model, cache, nomem, sc, facts=tr)
    expected = (
        tr & sc.correct & ~nomem.correct
    )  # a fact the frozen model already answers has no support
    assert int(expected.sum()) >= 100
    covered = sup.has_support & expected
    assert int(covered.sum()) >= 0.95 * int(expected.sum())
    assert not bool((sup.has_support & ~expected).any())
    assert set(sup.length[sup.has_support].tolist()) == {1}
    fact_ids = cache.stream.fact_ids.reshape(-1)
    for i in sup.has_support.nonzero().squeeze(1).tolist():
        assert sup.slots[i] == [int(fact_ids[i])]  # the support is the fact's dedicated slot
    assert len(sup.useful) == int(sup.has_support.sum())  # U* = number of facts that have a support
    assert sup.useful == sorted(set(int(fact_ids[i]) for i in sup.has_support.nonzero().squeeze(1)))
    # independent brute force: zero the dedicated row, run the ordinary forward, apply the definition
    threshold = torch.clamp(nomem.p_correct + 0.02, min=2 / 32)
    for i in sup.has_support.nonzero().squeeze(1).tolist()[:30]:
        after = brute_force_logits(model, cache, torch.tensor([int(fact_ids[i])]))
        ref = core.score_answer_sites(after.reshape(-1, 256), answers(cache))
        assert not bool(ref.correct[i]) and float(ref.p_correct[i]) <= float(threshold[i]) + 1e-6
    # facts without support keep their baseline status: no support for facts the frozen model knows
    assert not bool(sup.has_support[tr & nomem.correct].any())


def test_fact_stored_one_position_early_is_caught_by_seven_position_knockout_only() -> None:
    model, cache, _ = hand_cache("early")
    tr = trained_mask(cache)
    sc = scored(cache)
    nomem = nomem_of(model, cache.stream)
    assert float(sc.correct[tr].float().mean()) == 1.0
    sup = evaluate.minimal_supports(model, cache, nomem, sc, facts=tr)
    expected = tr & sc.correct & ~nomem.correct
    assert int((sup.has_support & expected).sum()) >= 0.95 * int(expected.sum())
    # removing the whole answer-site read changes nothing: every fact stays correct
    assert bool(sup.removing_site_read_stays_correct[tr].all())
    sel = cache.selection
    assert sel is not None
    pos = sel.positions.tolist()
    site_only = torch.zeros_like(sel.selected, dtype=torch.bool)
    for p in SITES:
        site_only[:, pos.index(p)] = True
    after_site = core.score_answer_sites(
        evaluate.logits_with(model, cache, knockout=site_only).reshape(-1, 256), answers(cache)
    )
    assert torch.equal(
        after_site.correct[tr], sc.correct[tr]
    )  # answer-site-only removal does not catch it
    # the seven-position knock-out of the carrier does
    fact_ids = cache.stream.fact_ids.reshape(-1)
    for i in sup.has_support.nonzero().squeeze(1).tolist():
        assert sup.slots[i] == [CARRIER_BASE + int(fact_ids[i])] and sup.length[i] == 1
    carriers = torch.tensor(sup.useful)
    everywhere = torch.isin(sel.selected, carriers)
    gone = core.score_answer_sites(
        evaluate.logits_with(model, cache, knockout=everywhere).reshape(-1, 256), answers(cache)
    )
    assert float(gone.correct[tr].float().mean()) <= 0.15
    assert len(sup.useful) == int(sup.has_support.sum())


@pytest.mark.parametrize("kind", ["diffuse", "dedicated_site"])
def test_diffuse_read_with_one_carrier_has_support_one_not_eight(kind: str) -> None:
    model, cache, _ = hand_cache(kind)
    tr = trained_mask(cache)
    sc = scored(cache)
    nomem = nomem_of(model, cache.stream)
    sel = cache.selection
    assert sel is not None
    weights = sel.scores.softmax(-1)
    if (
        kind == "diffuse"
    ):  # every one of the 8 slots has a weight near 1/8, so a weight threshold would count all of them
        site_w = weights[:, evaluate.site_columns(sel)]
        assert float(site_w.min()) > 0.05 and float(site_w.max()) < 0.2
    sup = evaluate.minimal_supports(model, cache, nomem, sc, facts=tr)
    expected = tr & sc.correct & ~nomem.correct
    assert int((sup.has_support & expected).sum()) >= 0.95 * int(expected.sum())
    assert set(sup.length[sup.has_support].tolist()) == {1}  # not 8
    n_supported = int(sup.has_support.sum())
    assert len(sup.useful) == n_supported  # one useful slot per stored fact, not eight
    assert all(s >= CARRIER_BASE for s in sup.useful)  # and never a junk slot
    selected_slots = torch.unique(sel.selected[:, evaluate.site_columns(sel)])
    assert (
        selected_slots.numel() >= 8 * n_supported
    )  # what an 'every selected slot' count would give


def test_zero_knowledge_memory_has_chance_accuracy_no_supports_ustar_zero() -> None:
    model = make_model(cell_of("A1", arch="flat", slots=4096, seed=1701))
    with torch.no_grad():
        model.addition.values.zero_()
    stream = draw().streams["panel_a"]
    cache = evaluate.build_cache(model, stream)
    tr = trained_mask(cache)
    sc = scored(cache)
    nomem = nomem_of(model, stream)
    assert torch.equal(sc.correct, nomem.correct)
    n = int(tr.sum())
    correct = int(sc.correct[tr].sum())
    assert correct <= core.chance_interval(n, 8).high
    assert core.information_bits(correct, n, 8) == 0.0
    sup = evaluate.minimal_supports(model, cache, nomem, sc, facts=tr)
    assert not bool(sup.has_support.any()) and sup.useful == []
    spec = evaluate.specificity(model, cache, sup, sc, seed=179401, facts=tr)
    assert (
        spec["condition_1_vacuous"] and spec["interpretable"]
    )  # nothing to interpret, nothing contradicted


# --- specificity -------------------------------------------------------------------------------------------------
def test_specificity_passes_for_a_dedicated_memory_and_flags_wrong_supports() -> None:
    model, cache, _ = r2_fixture()
    tr = trained_mask(cache)
    sc = scored(cache)
    nomem = nomem_of(model, cache.stream)
    sup = evaluate.minimal_supports(model, cache, nomem, sc, facts=tr)
    good = evaluate.specificity(model, cache, sup, sc, seed=179501, facts=tr)
    assert good["condition_1"] and good["condition_2"] and good["interpretable"]
    assert good["condition_2_groups"] == 64 and len(good["condition_2_group_drops"]) == 64
    assert good["condition_1_mean_slots_drawn"] == 8.0
    # a U* that claims slots nobody reads: facts whose 'support' avoids a group lose accuracy when it is zeroed
    fake = evaluate.SupportResult(
        length=sup.length.clone(),
        has_support=sup.has_support.clone(),
        slots=[[3000 + (i % 500)] if sup.has_support[i] else [] for i in range(len(sup.slots))],
        useful=[],
        removing_site_read_stays_correct=sup.removing_site_read_stays_correct,
    )
    fake.useful = sorted({s for f in fake.slots for s in f})
    bad = evaluate.specificity(model, cache, fake, sc, seed=179501, facts=tr)
    assert not bad["condition_2"] and not bad["interpretable"]
    assert bad["condition_2_max_drop"] > core.SPECIFICITY_GROUP_TOLERANCE
    assert bad["condition_2_groups_failing"] > 0


def test_specificity_condition_one_failure_marks_not_interpretable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model, cache, _ = r2_fixture()
    tr = trained_mask(cache)
    sc = scored(cache)
    sup = evaluate.minimal_supports(model, cache, nomem_of(model, cache.stream), sc, facts=tr)
    monkeypatch.setattr(
        core, "SPECIFICITY_DELTA", 0.0
    )  # no change is small enough: condition 1 must fail
    out = evaluate.specificity(model, cache, sup, sc, seed=179502, facts=tr)
    assert not out["condition_1"] and not out["interpretable"]
    assert out["condition_1_share_unchanged"] == 0.0
    with pytest.raises(ValueError):
        evaluate.specificity(model, cache, sup, sc, seed=1, scope="bogus")


# --- usage -------------------------------------------------------------------------------------------------------
def test_usage_statistics_on_a_dedicated_memory() -> None:
    model, cache, _ = r2_fixture()
    tr = trained_mask(cache)
    sc = scored(cache)
    sup = evaluate.minimal_supports(model, cache, nomem_of(model, cache.stream), sc, facts=tr)
    u = evaluate.usage_statistics(cache, sup, rows=tr)
    assert u["distinct"] == FACTS and u["dead_slots"] == 4096 - FACTS
    assert u["entropy_effective_hard"] == pytest.approx(
        FACTS, rel=1e-6
    )  # each fact read exactly once
    assert u["hot64_share"] == pytest.approx(64 / FACTS)
    assert u["facts_per_slot_mean"] == 1.0 and u["facts_per_slot_max"] == 1
    assert u["weight_entropy_mean"] == pytest.approx(0.0, abs=1e-6)  # one slot, weight 1
    assert "entropy_soft" not in u  # R2 has no candidate scores
    assert u["facts_per_useful_slot_mean"] == 1.0


def synthetic_cache(slots: int = 8192) -> ReadCache:
    """Hand-written reads: every answer-site query selects the same eight slots (hard usage concentrated)
    while its 64 candidates are all tied, so the soft inclusion spreads over 56 further slots per query."""
    stream = draw().streams["panel_a"]
    n_ctx = stream.tokens.shape[0]
    n_q = n_ctx * 8
    selected = torch.arange(8).expand(n_ctx, 8, 8).contiguous()
    extra = (8 + torch.arange(n_q * 56).reshape(n_ctx, 8, 56)) % slots
    cand_ids = torch.cat([selected, extra], dim=-1)
    sel = Selection(
        positions=torch.tensor(core.ANSWER_SITE_POSITIONS),
        selected=selected,
        scores=torch.zeros(n_ctx, 8, 8),
        candidate_ids=None,
        candidate_scores=None,
        branches=None,
        route_scores=None,
        length=63,
    )
    return ReadCache(
        stream=stream,
        tokens=stream.tokens,
        h_pre=torch.zeros(n_ctx, 63, 32),
        selection=sel,
        logits_answer=torch.zeros(n_ctx, 8, 256),
        site_candidate_ids=cand_ids,
        site_candidate_scores=torch.zeros(n_ctx, 8, 64),
        slots=slots,
    )


def test_hard_and_soft_usage_differ_on_a_constructed_case() -> None:
    u = evaluate.usage_statistics(synthetic_cache())
    assert u["distinct"] == 8 and u["entropy_effective_hard"] == pytest.approx(8.0, rel=1e-5)
    assert (
        u["entropy_effective_soft"] > 100 * u["entropy_effective_hard"]
    )  # the floor could be met by soft mass alone
    assert u["soft_mass_outside_top8"] == pytest.approx(28.0, rel=1e-5)  # 56 candidates at pi = 0.5
    assert u["margin_8_9"]["mean"] == 0.0
    assert math.isfinite(u["entropy_soft"]) and u["entropy_soft"] > u["entropy_hard"]


# --- accuracy classes, LEAKAGE, revival --------------------------------------------------------------------------
def test_accuracy_by_neighbour_splits_by_class() -> None:
    correct = torch.tensor([True, True, False, False, True, False])
    flags = torch.tensor([True, True, True, False, False, False])
    scores = core.AnswerScores(
        logp_sigma=torch.zeros(6, 32),
        p_correct=torch.zeros(6),
        correct=correct,
        mass_sigma=torch.ones(6),
        answer=torch.zeros(6, dtype=torch.int64),
    )
    assert evaluate.accuracy_by_neighbour(scores, flags) == (
        pytest.approx(2 / 3),
        pytest.approx(1 / 3),
    )
    assert evaluate.accuracy_by_neighbour(scores, torch.ones(6, dtype=torch.bool)) == (
        pytest.approx(0.5),
        None,
    )


def test_leakage_flag_boundaries() -> None:
    interval = core.chance_interval(2048, 8)
    assert not evaluate.leakage_flag(interval.high, 2048) and evaluate.leakage_flag(
        interval.high + 1, 2048
    )
    assert not evaluate.leakage_flag(interval.low, 2048) and evaluate.leakage_flag(
        interval.low - 1, 2048
    )
    assert not evaluate.leakage_flag(0, 0)  # a stream without unseen facts cannot leak


def test_first_entering_top64_counts_new_keys() -> None:
    c = cell_of("A1", arch="flat", slots=4096, seed=1701)
    a = make_model(c)
    stream = draw().streams["panel_a"]
    assert evaluate.first_entering_top64(a, a, stream) == 0
    b = copy.deepcopy(a)
    with torch.no_grad():
        b.addition.keys.copy_(torch.randn_like(b.addition.keys))
    entered = evaluate.first_entering_top64(a, b, stream)
    assert 0 < entered < 4096
