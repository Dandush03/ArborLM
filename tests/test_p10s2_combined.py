# ruff: noqa: E501
"""P10S2 combined tasks C1 and C2 and the strengthened COMPOSES rule (ADR-0022 combined-tasks addendum, human-approved 2026-11-15), on synthetic stand-ins and test seeds. Every number is a mechanics check,
not a result. Self-check only: not independent review, not Astra validation, not human approval."""

import copy
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402
import torch  # noqa: E402
from test_p10s2_classes import cell, comb_rec, study  # noqa: E402
from test_p10s2_support import dry_world, trained  # noqa: E402

from studies.p10s2 import (  # noqa: E402
    analysis,
    budget,
    cells,
    combined,
    core,
    evaluate,
    memory,
    output,
    prefreeze,
    rehearsal,
    report,
    standins,
)
from studies.p10s2 import classes as C  # noqa: E402
from studies.p10s2.memory import NullArm  # noqa: E402
from studies.p10s2.model import PositionAdapter  # noqa: E402
from studies.p10s2.synthetic import tgen  # noqa: E402

LINE, SECOND = core.ORACLE_LINE, core.COMBINED_LINE


# --- the pair list and the new seed (section 3) ------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("n", [6, 7, 2, 5])
def test_pair_list_is_a_permutation_with_every_sentence_once_as_s1_and_once_as_s2(n: int) -> None:
    sigma = combined.draw_sigma(n, "test")
    assert sorted(sigma) == list(range(n)) and sigma == combined.draw_sigma(n, "test")  # a permutation; identical when redrawn from the same seed
    pairs = combined.pair_list(n, sigma)
    assert sorted(p.i1 for p in pairs) == list(range(n)) and sorted(p.i2 for p in pairs) == list(range(n)) and all(p.i1 != p.i2 for p in pairs)
    assert all(p.t1 == ("A" if p.j % 2 == 0 else "B") and p.t2 == core.other_task(p.t1) for p in pairs)  # German first for even j, French first for odd j
    assert all(pairs[j].i2 == pairs[(j + 1) % n].i1 for j in range(n))  # item j = (sigma(j), sigma(j + 1 mod n))
    second = {"A": sum(p.t2 == "A" for p in pairs), "B": sum(p.t2 == "B" for p in pairs)}
    if n % 2 == 0:
        assert second == {"A": n // 2, "B": n // 2}  # each language is second on n/2 items
        # the sentences sigma(even) are answered in German only, sigma(odd) in French only
        assert {p.i1 for p in pairs if p.t1 == "A"} == {sigma[j] for j in range(0, n, 2)} and {p.i2 for p in pairs if p.t2 == "A"} == {sigma[j] for j in range(0, n, 2)}
    else:
        assert sorted(second.values()) == [(n - 1) // 2, (n + 1) // 2]  # items n-1 and 0 are both German-first
        assert pairs[n - 1].t1 == "A" and pairs[0].t1 == "A"


def test_pairing_without_sigma_and_the_refusals() -> None:
    p = combined.pair_list(4, None)
    assert [(x.i1, x.i2) for x in p] == [(0, 1), (1, 2), (2, 3), (3, 0)] and [x.t1 for x in p] == ["A", "B", "A", "B"]  # rehearsal and tests: item i with i + 1 mod m, no seed
    with pytest.raises(ValueError):
        combined.pair_list(1, None)
    with pytest.raises(ValueError, match="permutation"):
        combined.pair_list(3, [0, 0, 1])
    assert combined.pairs_digest(p) == combined.pairs_digest(combined.pair_list(4, None)) != combined.pairs_digest(combined.pair_list(4, [1, 0, 2, 3]))
    assert combined.duplicate_normalized(["A b.", "a  B", "c"]) == 1 and combined.duplicate_normalized(["x", "y"]) == 0


def test_seed_220911_is_listed_and_drawn_only_in_the_partition_step() -> None:
    assert core.PARTITION_STREAMS["c1_pairing"] == 220911 and core.partition_seeds("registered-data")["c1_pairing"] == 220911
    assert 220911 in core.listed_registered_seeds() and 220911 in core.CFG["seeds"]["partition_streams"]
    lo, hi = core.RANGES["registered"]
    assert lo <= 220911 <= hi and not any(a <= 220911 <= b for a, b in (core.RANGES["calibration"], core.RANGES["rehearsal"], core.RANGES["test"])) and core.foreign_seed_hit(220911) is None
    assert 220911 not in core.allowed_seeds("registered-run")  # not a replicate offset
    with pytest.raises(core.SeedRefused):
        core.seeded_generator(220911, "C1 pairing in the run", "registered-run")
    core.reset_seed_record()
    core.seeded_generator(220911, "C1 pairing", "registered-data")
    assert core.seed_gate(core.seed_record(), planned_mode="registered-data")["ok"]
    core.reset_seed_record()
    assert core.partition_seeds("test")["c1_pairing"] in core.allowed_seeds("test")


def test_the_pairing_is_stored_with_the_data_manifest_and_checked_at_load() -> None:
    world, rec = dry_world()
    ec = world.ctx.ec
    assert rec["c1_pairing"]["pairs_sha256"] == combined.pairs_digest(ec.pairs) and rec["c1_pairing"]["n"] == len(ec.sentences) and rec["c1_pairing"]["duplicate_normalized_english"] == 0
    assert ec.sigma is not None and sorted(ec.sigma) == list(range(len(ec.sentences)))
    assert rec["combined_whole_string"]["ok"] and rec["combined_whole_string"]["checked"] == 2 * len(ec.sentences)


# --- layouts and reads (sections 4.1, 4.2, 5.1, 5.2) ----------------------------------------------------------------------------------------------------
def test_c1_step_2_input_is_the_concatenation_of_the_stored_segments_for_both_task_orders() -> None:
    world, _ = dry_world()
    ctx, cs = world.ctx, world.ctx.ec
    nl = list(ctx.newline_ids)
    for j in (0, 1, 2, 3):
        p = cs.pairs[j]
        ids1, reads1, suffix_fn = combined.c1_layout(ctx, cs, p)
        ex1, ex2 = cs.sentences[p.i1].ex[p.t1], cs.sentences[p.i2].ex[p.t2]
        assert ids1 == list(ex1.prompt_ids) and reads1 == [*[(pos, p.t1, jj) for pos, jj in ex1.reads], (ex1.marker, p.t1, ctx.marker_index)]
        a1 = [11, 12, 13]
        suffix, reads2 = suffix_fn(a1, False)
        body2 = [i for s in ex2.segments for i in s.ids][len(ex2.segments[0].ids) if ex2.segments[0].text == "<bos>" else 0 : len([i for s in ex2.segments[:-0 or None] for i in s.ids]) - 0]
        full = ids1 + a1 + suffix
        expect_tail = nl + [i for s in ex2.segments if s.text != "<bos>" for i in s.ids][: len(ex2.prompt_ids) - (len(ex2.segments[0].ids) if ex2.segments[0].text == "<bos>" else 0)]
        assert full == ids1 + a1 + expect_tail and body2 is not None  # [BOS] E S(s1) NL M_T1 . a1 . NL . E S(s2) NL M_T2; no BOS before the second E
        off = len(ids1) + len(a1) + len(nl)
        bos = len(ex2.segments[0].ids) if ex2.segments[0].text == "<bos>" else 0
        want = {(off + pos - bos, p.t2, jj) for pos, jj in ex2.reads} | {(off + ex2.marker - bos, p.t2, ctx.marker_index)}
        assert {(len(ids1) + len(a1) + q, t, jj) for q, t, jj in reads2} == want  # read positions = stored positions plus the offset of the formula
        banned = set(range(len(ids1), len(ids1) + len(a1) + len(nl)))
        assert not ({len(ids1) + len(a1) + q for q, _t, _j in reads2} & banned) and not ({q for q, _t, _j in reads1} & banned)  # the answer and the newline after it are never read
        assert full[len(ids1) + len(a1) + len(nl) + ex2.marker - bos] == ex2.prompt_ids[ex2.marker]
        # at the token limit the last token of a1 is fed first and the offsets move by one
        suffix_h, reads_h = suffix_fn(a1, True)
        assert suffix_h[0] == a1[-1] and suffix_h[1:] == suffix and [(q - 1, t, jj) for q, t, jj in reads_h] == reads2
    assert [cs.pairs[j].t1 for j in (0, 1)] == ["A", "B"]  # the parity alternation: even j German first, odd j French first


def test_c2_layout_reads_both_tasks_at_every_source_word_and_each_marker_with_its_own_code() -> None:
    world, _ = dry_world()
    ctx, cs = world.ctx, world.ctx.ec
    ids1, reads1, suffix_fn, ma = combined.c2_layout(ctx, cs, 2)
    exa, exb = cs.sentences[2].ex["A"], cs.sentences[2].ex["B"]
    assert ids1 == list(exa.prompt_ids) and ma == len(exa.segments[-1].ids)
    for pos, j in exa.reads:
        assert (pos, "A", j) in reads1 and (pos, "B", j) in reads1  # the summed word reads are present from step 1
    assert [r for r in reads1 if r[2] == ctx.marker_index] == [(exa.marker, "A", ctx.marker_index)]  # the marker of A only
    suffix, reads2 = suffix_fn([5, 6], False)
    assert suffix == list(ctx.newline_ids) + list(exb.segments[-1].ids) and reads2 == [(len(suffix) - 1, "B", ctx.marker_index)]  # M_B read with its own code where it stands; the German answer is in the context
    assert suffix_fn([5, 6], True)[0][0] == 6


def test_c2_word_read_is_the_sum_of_two_separate_reads_not_one_read_of_a_summed_query() -> None:
    world, _ = dry_world()
    store = memory.SparseStore.new(world.cfg.width, 24, tgen(61, "c2 store"))
    with torch.no_grad():
        store.values[0].copy_(torch.randn(24, world.cfg.width, generator=tgen(62, "values")))
        store.gates[0].fill_(1.0)
    arm = memory.MemoryArm(store, world.layer, world.codes(0))
    j = 3
    add, _ = arm.prepare([[(2, "A", j), (2, "B", j)]], 1, 5, torch.device("cpu"))
    assert add is not None
    qa, qb = arm.codes.get("A", j)[None], arm.codes.get("B", j)[None]
    assert torch.allclose(add[0, 2], store.read(qa)[0] + store.read(qb)[0], atol=1e-6)  # each read has its own top-8 and softmax; the results are added
    summed = torch.nn.functional.normalize(qa + qb, dim=-1)
    assert not torch.allclose(add[0, 2], store.read(summed)[0], atol=1e-6)  # one read with a summed query is a different thing
    sep = combined_sep_arm(world)
    assert sep is not None


def combined_sep_arm(world: Any) -> Any:
    return cells.CompositeStoreArm({c: memory.MemoryArm(memory.SparseStore.new(world.cfg.width, 8, tgen(63 + i, "sep")), world.layer, world.codes(0)) for i, c in enumerate(("A", "B"))})


# --- continuation, first answers, L-sep (sections 4.1, 7) --------------------------------------------------------------------------------------------------
def test_cache_continuation_equals_full_recomputation_for_a_store_arm_an_adapter_arm_and_lsep_on_c1() -> None:
    world, _, d, tr, _ = trained()
    ctx = world.ctx
    ctx.seed_plan = core.SeedPlan("test", 0)
    lsep = cells.AdapterRouteArm({c: cells.load_arm(world, 0, d, f"r0/LORA1/{c}{core.other_task(c)}") for c in core.TASKS})  # type: ignore[misc]
    for label in ("r0/MAF/AB", "r0/LSEQ/AB", "r0/MJOINT/-"):
        arm = cells.load_arm(world, 0, d, label)
        r = combined.check_continuation(ctx, arm, ctx.ec, 4)
        assert r["ok"], (label, r)
    r = combined.check_continuation(ctx, lsep, ctx.ec, 4)
    assert r["ok"], r  # position-wise adapters on C1; C2 is the full computation of section 7
    assert combined.check_continuation(ctx, NullArm(), ctx.ec, 3)["ok"] and combined.check_continuation(ctx, combined_sep_arm(world), ctx.ec, 3)["ok"]


def test_the_first_answer_of_every_c1_item_is_bit_identical_to_the_single_task_answer() -> None:
    world, _, d, tr, _ = trained()
    ctx = world.ctx
    ctx.seed_plan = core.SeedPlan("test", 0)
    for label in ("r0/MAF/AB", "r0/LJOINT/-"):
        arm = cells.load_arm(world, 0, d, label)
        rec = combined.score_combined_cell(ctx, arm, ctx.ec)
        for it in rec["C1"]["items"]:
            (i1, _i2), (t1, _t2) = it["i"], it["langs"]
            assert it["ids"][0] == evaluate.generate(ctx, arm, ctx.ec.sentences[i1].ex[t1], [t1])  # generated twice by different paths, identical
            assert rec["single"]["sequences"][t1][i1] == it["ids"][0]
        n = len(ctx.ec.sentences)
        assert rec["single"]["separate_answers"] == n and len(rec["C1"]["items"]) == n and len(rec["C2"]["items"]) == n  # n separate single answers (n even)
        assert rec["C1"]["first_by_language"].keys() == {"A", "B"} and rec["pairs_sha256"] == combined.pairs_digest(ctx.ec.pairs)
        assert all(it["length_ok"] for it in rec["C1"]["items"]) and "hit_limit" in rec["C1"] and "stop_extra_bytes" in rec["C2"] and "single_reference_mean" in rec["C1"]


def test_lsep_c2_step_2_is_the_full_computation_with_the_adapters_of_section_7() -> None:
    world, _, d, tr, _ = trained()
    ctx = world.ctx
    ctx.seed_plan = core.SeedPlan("test", 0)
    arms = {c: cells.load_arm(world, 0, d, f"r0/LORA1/{c}{core.other_task(c)}") for c in core.TASKS}
    lsep = cells.AdapterRouteArm(arms)  # type: ignore[arg-type]
    idx = 1
    out = combined.run_c2(ctx, lsep, ctx.ec, idx)
    ids1, _reads, _sfx, ma = combined.c2_layout(ctx, ctx.ec, idx)
    st, table = ctx.student, ctx.decoder.table
    st.read_layer = None
    g1, _ = st.greedy_cached(torch.tensor([ids1]), add=None, adapter=arms["A"].adapter, max_new=ctx.max_new, stop_bytes=table)  # type: ignore[attr-defined]
    assert g1 == out.g1  # step 1: A's adapter on the whole sequence
    a1, _hit, _x = combined.split_answer(ctx, g1)
    marker_b = list(ctx.ec.sentences[idx].ex["B"].segments[-1].ids)
    full = ids1 + a1 + list(ctx.newline_ids) + marker_b
    prefix, end_a = len(ids1) - ma, len(ids1) + len(a1)
    owner = {i: ("A" if prefix <= i < end_a else "B") for i in range(len(full) + ctx.max_new + 1)}
    pa = PositionAdapter({"A": arms["A"].adapter, "B": arms["B"].adapter}, lambda i: owner[i])  # type: ignore[attr-defined]
    g2 = st.greedy(torch.tensor([full]), add=None, adapter=pa, max_new=ctx.max_new, stop_bytes=table, use_cache=False)  # recomputed from nothing: B on [BOS] E S NL, A on M_A and a1, B on NL, M_B and a2
    assert g2 == out.g2
    # the position-wise adapter equals the single adapter where one task owns every position (bit for bit)
    ids = torch.tensor([full])
    only_a = PositionAdapter({"A": arms["A"].adapter, "B": arms["B"].adapter}, lambda i: "A")  # type: ignore[attr-defined]
    assert torch.equal(st(ids, adapter=only_a), st(ids, adapter=arms["A"].adapter))  # type: ignore[attr-defined]


# --- the ensemble, Stage 0 and the rule (sections 6, 7, 8) ------------------------------------------------------------------------------------------------
def test_ensemble_answers_inside_c1_and_c2_equal_its_single_task_answers() -> None:
    world, _ = dry_world()
    ec = world.ctx.ec
    text = {c: world.teacher_outputs[c]["E_C"] for c in core.TASKS}
    e = combined.ensemble_record(ec, text)
    for kind in ("C1", "C2"):
        for lang in core.TASKS:
            assert combined.tested_mean(e, kind, lang) == pytest.approx(combined.single_mean_on(e, kind, lang))  # no context reaches a teacher
    s0 = combined.score_combined_cell(world.ctx, NullArm(), ec)
    for lang in core.TASKS:
        cell_ens = C.comp_cell({a: combined.tested_mean(e, "C1", a) for a in core.TASKS}, {a: combined.single_mean_on(e, "C1", a) for a in core.TASKS}, {a: combined.tested_mean(s0, "C1", a) for a in core.TASKS}, {a: combined.single_mean_on(s0, "C1", a) for a in core.TASKS}, {a: combined.single_mean_on(e, "C1", a) for a in core.TASKS})
        assert cell_ens.h[lang] is not None and cell_ens.h[lang] <= 1.0 + 1e-12  # never more than 1


def test_stage_0_do_nothing_arm_is_not_evaluated_under_b_i_and_never_composes() -> None:
    world, _ = dry_world()
    ctx = world.ctx
    ctx.seed_plan = core.SeedPlan("test", 0)
    s0 = combined.score_combined_cell(ctx, NullArm(), ctx.ec)  # a do-nothing arm is the untrained student itself
    ens = combined.ensemble_record(ctx.ec, {c: world.teacher_outputs[c]["E_C"] for c in core.TASKS})
    for kind in ("C1", "C2"):
        cellr = analysis._comp_inputs(s0, kind, s0, ens)
        assert cellr.passes is None and any("single-task gap below 0.50" in r or "teacher gap" in r for r in cellr.reasons)
        name, reasons = C.composition_class({"-": [cellr, cellr]})
        assert name == core.NOT_EVALUATED and reasons


def synth(single: tuple[float, float], c1: tuple[float, float], c2: tuple[float, float], s0: tuple[float, float] = (0.1, 0.1), s0_c1: tuple[float, float] = (0.1, 0.1), s0_c2: tuple[float, float] = (0.1, 0.1), teacher: float = 0.9) -> C.CompCell:
    return C.comp_cell(
        {"A": c1[0], "B": c1[1]}, {"A": single[0], "B": single[1]}, {"A": s0_c1[0], "B": s0_c1[1]}, {"A": s0[0], "B": s0[1]}, {"A": teacher, "B": teacher},
    )  # fmt: skip


def test_the_rule_on_synthetic_arms_do_nothing_first_answer_only_and_copy_the_first_answer_do_not_compose() -> None:
    good = synth((0.8, 0.8), (0.78, 0.78), (0.78, 0.78))
    assert good.passes is True and good.h["A"] == pytest.approx((0.78 - 0.1) / (0.8 - 0.1)) and good.g["A"] == pytest.approx((0.8 - 0.1) / (0.9 - 0.1))
    assert C.composition_class({"AB": [good, good], "BA": [good, good]}) == (C.COMPOSES, ())
    do_nothing = synth((0.1, 0.1), (0.1, 0.1), (0.1, 0.1))  # the untrained student: single-task gap 0 < 0.50
    first_only = synth((0.8, 0.8), (0.8, 0.0), (0.8, 0.0))  # answers only the first segment: the second answer is empty
    copy_first = synth((0.8, 0.8), (0.8, 0.1), (0.8, 0.1))  # the French answer is the German one copied: it scores like Stage 0
    for arm in (do_nothing, first_only, copy_first):
        name, _ = C.composition_class({"AB": [arm, arm], "BA": [arm, arm]})
        assert name != C.COMPOSES
    assert do_nothing.passes is None and any("single-task gap below 0.50" in r for r in do_nothing.reasons)
    assert C.composition_class({"AB": [do_nothing]})[0] == core.NOT_EVALUATED
    assert first_only.h["B"] is not None and first_only.h["B"] < 0 and C.composition_class({"AB": [first_only, first_only]})[0] == C.DOES_NOT
    assert copy_first.h["B"] == pytest.approx(0.0) and C.composition_class({"AB": [copy_first, copy_first]})[0] == C.DOES_NOT


def test_rule_thresholds_floors_and_order_of_the_outcomes() -> None:
    assert synth((0.8, 0.8), (0.1 + 0.801 * 0.7, 0.78), (0.78, 0.78)).passes is True and synth((0.8, 0.8), (0.1 + 0.799 * 0.7, 0.78), (0.78, 0.78)).passes is False  # H just above 0.80 passes, just below does not
    assert C.composition_class({"AB": [synth((0.8, 0.8), (0.1 + 0.51 * 0.7, 0.78), (0.78, 0.78))] * 2})[0] == C.INCONCLUSIVE  # H = 0.51 is not below 0.50
    assert C.composition_class({"AB": [synth((0.8, 0.8), (0.1 + 0.49 * 0.7, 0.78), (0.78, 0.78))] * 2})[0] == C.DOES_NOT
    mixed = [synth((0.8, 0.8), (0.1 + 0.3 * 0.7, 0.78), (0.78, 0.78)), synth((0.8, 0.8), (0.78, 0.78), (0.78, 0.78))]
    assert C.composition_class({"AB": mixed})[0] == C.INCONCLUSIVE  # DOES NOT COMPOSE needs the shortfall in every replicate of the order
    bad_o, good_o = [synth((0.8, 0.8), (0.1, 0.78), (0.78, 0.78))] * 2, [synth((0.8, 0.8), (0.78, 0.78), (0.78, 0.78))] * 2
    assert C.composition_class({"AB": good_o, "BA": bad_o})[0] == C.DOES_NOT and C.composition_class({"AB": good_o, "BA": good_o + bad_o[:1]})[0] == C.INCONCLUSIVE
    # B(ii): the floor is the larger of Stage 0's combined and single-task scores
    floor = synth((0.8, 0.8), (0.78, 0.78), (0.78, 0.78), s0=(0.1, 0.1), s0_c1=(0.4, 0.4))
    assert floor.h["A"] == pytest.approx((0.78 - 0.4) / (0.8 - 0.1)) and floor.passes is False  # with Stage 0's combined score alone the arm would be credited with Stage 0's own gain
    # B(i): the two definedness floors, each with its reason; a non-finite score; NOT_EVALUATED comes first
    low_teacher = synth((0.35, 0.8), (0.3, 0.78), (0.3, 0.78), teacher=0.35)
    assert low_teacher.passes is None and any("teacher gap on E_C below 0.30" in r for r in low_teacher.reasons)
    assert synth((0.8, 0.8), (0.78, 0.78), (0.78, 0.78), teacher=0.39).passes is None and synth((0.8, 0.8), (0.78, 0.78), (0.78, 0.78), teacher=0.4).passes is True  # the gap of exactly 0.30 is defined
    low_single = synth((0.45, 0.8), (0.4, 0.78), (0.4, 0.78))
    assert low_single.passes is None and low_single.g["A"] < 0.5 and any("single-task gap below 0.50" in r for r in low_single.reasons)
    nan = synth((0.8, 0.8), (float("nan"), 0.78), (0.78, 0.78))
    assert nan.passes is None and any("undefined" in r for r in nan.reasons)
    assert C.composition_class({"AB": [good_o[0], low_single], "BA": bad_o})[0] == core.NOT_EVALUATED  # first match wins
    assert C.composition_class({"AB": good_o + [None]})[0] == core.NOT_EVALUATED and C.composition_class({"AB": good_o}, rejected=True)[0] == core.NOT_EVALUATED


# --- analysis and report on synthetic records of the whole registry (sections 8, 9) --------------------------------------------------------------------------
def test_composition_lines_for_every_arm_with_the_reasons_and_without_effect_on_the_label() -> None:
    out = analysis.analyze(study())
    comp = out["composition"]
    assert comp["n_replicates"] == 2 and set(comp["arms"]) == {"C1", "C2"}
    for kind in ("C1", "C2"):
        arms = comp["arms"][kind]
        assert set(arms) == {"M-append-frozen", "M-ii", "L-seq", "M-joint", "L-joint", "M-i-separate", "L-sep", "_stage0", "_ensemble"}  # M-seq and E-table are not scored
        assert arms["M-append-frozen"]["composition"] == "COMPOSES" and set(arms["M-append-frozen"]["orders"]) == {"AB", "BA"} and len(arms["M-append-frozen"]["orders"]["AB"]) == 2
        assert arms["M-joint"]["orders"].keys() == {"-"} and arms["_ensemble"]["H"] == {"A": pytest.approx(1.0), "B": pytest.approx(1.0)}  # H = 1: Stage 0's combined score does not exceed its single-task score
        assert arms["_stage0"]["s_combined"] == {"A": pytest.approx(0.1), "B": pytest.approx(0.1)}
        assert arms["M-append-frozen"]["revision5_ratio_replaced"]["AB"] == pytest.approx(0.78 / (0.8 * 0.8)) and "replaced" in arms["M-append-frozen"]["label"]
    # no value of C1 or C2 can produce, withhold or change a label or a class
    bad = analysis.analyze(study(tweak=lambda s: [cell(s, r, "MAF", o)["scores"][f"r{r}/MAF/{o}"].update(combined=comb_rec(c1=(0.1, 0.1), c2=(0.1, 0.1))) for r in range(2) for o in core.ORDERS]))
    assert bad["composition"]["arms"]["C1"]["M-append-frozen"]["composition"] == "DOES NOT COMPOSE" and bad["label"] == out["label"] and bad["classes"] == out["classes"] and bad["gates"] == out["gates"]


def test_rejected_m_ii_a_missing_record_and_the_floors_in_the_analysis() -> None:
    rej = analysis.analyze(study(tweak=lambda s: cell(s, 1, "MII", "BA")["extras"]["consolidation"].update(rejected=True, published=False)))
    m = rej["composition"]["arms"]["C1"]["M-ii"]
    assert m["composition"] == core.NOT_EVALUATED and "CONSOLIDATION-REJECTED cell" in m["reasons"] and rej["composition"]["arms"]["C1"]["M-append-frozen"]["composition"] == "COMPOSES"

    def missing(s: dict[str, Any]) -> None:
        del cell(s, 0, "LJOINT", "-")["scores"]["r0/LJOINT/-"]["combined"]

    inc = analysis.analyze(study(tweak=missing))
    assert inc["label"] == "INCOMPLETE" and any("combined-task scores are missing" in x for x in inc["incomplete"]) and inc["composition"] == {}  # a registered score is missing: section 11.3 row 2

    def teacher(s: dict[str, Any]) -> None:
        s["baseline"]["combined"]["ensemble"] = comb_rec(0.3, 0.3, (0.3, 0.3), (0.3, 0.3))

    ne = analysis.analyze(study(tweak=teacher))["composition"]["arms"]["C2"]["M-append-frozen"]
    assert ne["composition"] == core.NOT_EVALUATED and any("teacher gap on E_C below 0.30" in r for r in ne["reasons"])

    def forgot(s: dict[str, Any]) -> None:
        for r in range(2):
            cell(s, r, "LSEQ", "AB")["scores"][f"r{r}/LSEQ/AB"]["combined"] = comb_rec(0.2, 0.8, (0.2, 0.7), (0.2, 0.7))  # a forgotten capability is not read as a failure to compose

    fg = analysis.analyze(study(tweak=forgot))["composition"]["arms"]["C1"]["L-seq"]
    assert fg["composition"] == core.NOT_EVALUATED and any("single-task gap below 0.50 (A)" in r for r in fg["reasons"])

    def nonfinite(s: dict[str, Any]) -> None:
        cell(s, 0, "MAF", "AB")["scores"]["r0/MAF/AB"]["combined"]["C1"]["tested_by_language"]["B"] = "nan"

    assert analysis.analyze(study(tweak=nonfinite))["composition"]["arms"]["C1"]["M-append-frozen"]["composition"] == core.NOT_EVALUATED


def test_every_composition_line_is_under_both_fixed_lines_and_the_ensemble_and_stage_0_carry_no_composition_word() -> None:
    out = analysis.analyze(study())
    text = report.render_report(out)
    output.check_text(text)
    i = text.index("Table 4. Composition on E_C")
    blk = text[text.rfind("\n\n", 0, i) + 2 :].split("\n\n")[0].split("\n")
    assert blk[0] == LINE and blk[1] == SECOND  # the oracle-assisted line, then the combined-tasks line, directly above the table and its caption
    assert "descriptive; enters no gate, class or label" in SECOND and "neither combined task was trained on" in SECOND
    for ln in blk:
        if "ensemble (BY CONSTRUCTION" in ln or "Stage 0 (the floor" in ln:
            assert not output.is_composition(ln)  # no composition word for the ensemble or Stage 0
    assert any("revision 5's raw-score rule, replaced by the human lead" in ln for ln in blk) and any("H {'A'" in ln for ln in blk) and any("single-task G" in ln for ln in blk) and any("pass rate" in ln for ln in blk)
    assert "(2 replicates, U = 2000)" in blk[2] and any(ln.startswith("- C1 M-append-frozen: COMPOSES (n replicates = 2)") for ln in blk)
    # refusal without them
    stripped_second = text.replace(SECOND + "\n", "")
    with pytest.raises(output.OracleLineMissing, match="second fixed line"):
        output.check_text(stripped_second)
    with pytest.raises(output.OracleLineMissing):
        output.check_text(text.replace(LINE + "\n", ""))
    assert output.positive_wording_without_line("C1 M-append-frozen: COMPOSES") and output.positive_wording_without_line(f"{LINE}\nC1 M-append-frozen: COMPOSES")
    assert not output.positive_wording_without_line(f"{LINE}\n{SECOND}\nC1 M-append-frozen: DOES NOT COMPOSE")
    assert output.positive_wording_without_line(f"{LINE}\n{SECOND}\nx\n\n{LINE}\nC2: COMPOSITION INCONCLUSIVE")  # the second block lacks the second line
    # the record
    rec = report.render_json(out)
    assert rec["outcome"]["combined_line"] == SECOND and rec["outcome"]["oracle_line"] == LINE  # both lines are fields of the record that carries the composition field
    bad = copy.deepcopy(rec)
    del bad["outcome"]["combined_line"]
    with pytest.raises(output.OracleLineMissing, match="second fixed line"):
        output.check_record(bad)
    assert core.GUARDED_WORDS.count("DOES NOT COMPOSE") == 1 and "COMPOSITION INCONCLUSIVE" in core.GUARDED_WORDS


def test_log_summary_of_a_composition_line_carries_both_lines(capsys: pytest.CaptureFixture[str]) -> None:
    output.emit(["C1 M-append-frozen: COMPOSES (2 replicates, U = 2000)"])
    lines = capsys.readouterr().out.splitlines()
    assert lines[:2] == [LINE, SECOND] and "COMPOSES" in lines[2]
    output.emit(["C2 L-sep: COMPOSITION INCONCLUSIVE"])
    assert capsys.readouterr().out.splitlines()[:2] == [LINE, SECOND]


def test_odd_and_even_numbers_of_sentences_in_the_engine() -> None:
    world, _ = dry_world()
    ctx = world.ctx
    ctx.seed_plan = core.SeedPlan("test", 0)
    for n in (4, 5):
        cs = combined.combined_set(ctx.ec.sentences[:n], None)
        rec = combined.score_combined_cell(ctx, NullArm(), cs)
        t1 = [it["langs"][0] for it in rec["C1"]["items"]]
        assert t1 == ["A" if j % 2 == 0 else "B" for j in range(n)] and rec["n"] == n and len(rec["C2"]["items"]) == n
        sizes = sorted(len(v) for v in rec["C1"]["tested_sentences"].values())
        assert sizes == ([n // 2, n // 2] if n % 2 == 0 else [(n - 1) // 2, (n + 1) // 2])  # each H_a rests on about n/2 items
        assert all(len(v) == n for v in rec["C2"]["tested_sentences"].values())  # C2 tests both answers on every item
        assert rec["single"]["separate_answers"] == (n if n % 2 == 0 else n)  # n separate single answers whatever the parity
        assert rec["C1"]["n"] == n and 0.0 <= rec["C1"]["pass_rate"] <= 1.0 and rec["C1"]["mean"] == pytest.approx(sum(rec["C1"]["item_scores"]) / n)


def test_length_assertion_makes_the_cell_not_evaluated_and_drops_no_item() -> None:
    world, _ = dry_world()
    ctx = copy.copy(world.ctx)
    ctx.seed_plan = core.SeedPlan("test", 0)
    cfg = ctx.student.cfg
    original = cfg.max_positions
    object.__setattr__(cfg, "max_positions", 100)  # the step-2 input plus the limit cannot fit
    try:
        rec = combined.score_combined_cell(ctx, NullArm(), ctx.ec)
    finally:
        object.__setattr__(cfg, "max_positions", original)
    assert rec["C1"]["length_not_ok"] > 0 and len(rec["C1"]["items"]) == len(ctx.ec.sentences)  # not dropped; no denominator is reduced
    assert rec["C1"]["mean"] != rec["C1"]["mean"]  # NaN: the cell's combined score is undefined, so the line is NOT_EVALUATED


# --- the whole-string check (section 4.4) and the rehearsal (sections 3, 10, 11) -----------------------------------------------------------------------
class ByteTok:
    """A byte tokenizer in which the whole string merges a trailing 'x' with the newline after it into one token (id 999): a boundary mismatch."""

    vocab_size = 1000
    bos_id = None

    def _pieces(self, text: str) -> list[tuple[int, int, int]]:
        raw = text.encode()
        out, k = [], 0
        while k < len(raw):
            if raw[k : k + 2] == b"x\n":
                out.append((999, k, k + 2))
                k += 2
            else:
                out.append((raw[k], k, k + 1))
                k += 1
        return out

    def encode(self, text: str) -> list[int]:
        return [i for i, _, _ in self._pieces(text)]

    def encode_offsets(self, text: str) -> tuple[list[int], list[tuple[int, int]]]:
        p = self._pieces(text)
        return [i for i, _, _ in p], [(a, b) for _, a, b in p]

    def decode(self, ids: Any) -> str:
        return bytes(i for i in ids if i < 256).decode(errors="replace")

    def token_bytes(self) -> list[bytes]:
        return [bytes([i]) for i in range(256)]


def test_whole_string_check_lists_mismatches_inside_the_reference_and_requires_none_elsewhere() -> None:
    from studies.p10s2.data import Item

    items = [Item(f"w{i}", f"word{i} here", {"A": (f"ref{i}x" if i == 0 else f"ref{i}",), "B": (f"fr{i}",)}, i) for i in range(4)]
    pairs = combined.pair_list(4, None)
    r = prefreeze.check_combined_whole_string(ByteTok(), items, pairs)  # the merge sits at the end of a reference of item 0 (German first): listed, nothing required
    assert r["ok"] and r["required_mismatches"] == [] and r["listed_inside_reference"] >= 1 and r["checked"] == 8
    sources = [Item(f"w{i}", f"wordx{i}" if i == 1 else f"word{i}", {"A": ("a",), "B": ("b",)}, i) for i in range(4)]  # an 'x' + newline boundary after a source: required
    sources[1] = Item("w1", "word1x", {"A": ("a",), "B": ("b",)}, 1)
    bad = prefreeze.check_combined_whole_string(ByteTok(), sources, pairs)
    assert not bad["ok"] and bad["required_mismatches"]
    world, _ = dry_world()
    synthetic = standins.build_synthetic_bundle(1)[1]["combined_whole_string"]
    assert synthetic["ok"]


def poison_world(world: Any) -> Any:
    """A copy of the world whose evaluation panels (E_A, E_B, E_C, E_open) raise if anything reads them."""

    class Trap(list):  # type: ignore[type-arg]
        def __iter__(self) -> Any:
            raise AssertionError("a registered panel was read by the rehearsal")

        def __getitem__(self, i: Any) -> Any:
            raise AssertionError("a registered panel was read by the rehearsal")

        def __len__(self) -> int:
            return 3

    w = copy.copy(world)
    ctx = copy.copy(world.ctx)
    ctx.panels = {k: type(v)(v.name, v.task, Trap(v.examples), Trap(v.refs)) for k, v in world.ctx.panels.items()}  # type: ignore[call-arg]
    ctx.ec = combined.CombinedSet(Trap(world.ctx.ec.sentences), world.ctx.ec.pairs, world.ctx.ec.sigma)
    w.ctx = ctx
    part = copy.copy(world.partition)
    part.panels = {k: (Trap(v) if k in ("E_A", "E_B", "E_C", "E_open") else v) for k, v in world.partition.panels.items()}
    w.partition = part
    w.teacher_outputs = {c: {k: (Trap(v) if k in ("E_A", "E_B", "E_C") else v) for k, v in d.items()} for c, d in world.teacher_outputs.items()}
    return w


def test_rehearsal_scorings_never_touch_e_c_or_any_registered_panel_and_check_the_continuation(tmp_path: Path) -> None:
    world, _ = dry_world()
    from studies.p10s2.worldio import write_bundle

    bundle, _rec = standins.build_synthetic_bundle(1)
    write_bundle(bundle, tmp_path / "data")
    ov = rehearsal.measure_task_overhead(tmp_path / "data")
    poisoned = poison_world(world)
    rates, raw = rehearsal.measure_rates(poisoned, 0, updates=2, full_updates=3, overhead=ov, timing_items=2)  # raises if any registered panel is read
    c = raw["combined"]
    assert all(c[f"continuation_{k}"]["ok"] for k in ("store", "adapter", "lsep")) and c["items"] == len(world.partition.panels["D_cal"])
    assert rates.combined_cell_seconds == c["cell_seconds_at_panel_size"] > 0 and rates.combined_stage0_seconds > 0
    rw = rehearsal.rehearsal_world(world)
    assert [s.key for s in rw.ctx.ec.sentences] == [i.key for i in world.partition.panels["D_cal"]] and rw.ctx.ec.sigma is None  # the first items of the rehearsal's own scoring set, paired by index
    assert all(p.i2 == (p.i1 + 1) % len(rw.ctx.ec.sentences) for p in rw.ctx.ec.pairs)


def test_a_continuation_difference_in_the_rehearsal_is_a_g4_class_defect(monkeypatch: pytest.MonkeyPatch) -> None:
    world, _ = dry_world()
    rw = rehearsal.rehearsal_world(world)
    plan = rw.plan(0)
    arm = memory.MemoryArm(memory.SparseStore.new(rw.cfg.width, rw.rows_per_stage, plan.gen(0, "store")), rw.layer, rw.codes(0))
    monkeypatch.setattr(combined, "check_continuation", lambda *a, **k: {"ok": False, "differences": ["C1 item 0"], "items": 1})
    with pytest.raises(RuntimeError, match="G4-class defect"):
        rehearsal.measure_combined(rw, 0, arm)


def test_combined_cost_is_charged_inside_r_with_its_recomputation() -> None:
    from test_p10s2_budget import rates as base_rates

    r0 = base_rates(1.0)
    r1 = budget.Rates(**{**r0.to_json(), "combined_cell_seconds": 60.0, "combined_stage0_seconds": 30.0})
    assert budget.COMBINED_CELLS == 10  # M-append-frozen 2, M-ii 2, M-joint 1, L-joint 1, L-seq 2, M-i-separate 1, L-sep 1
    d = budget.scoring_seconds(4, r1) - budget.scoring_seconds(4, r0)
    assert d == pytest.approx(4 * 10 * 60.0 + 30.0)
    assert budget.recompute_seconds(4, r1) - budget.recompute_seconds(4, r0) == pytest.approx(d)  # the recomputation repeats the combined scorings
    p0, p1 = budget.registered_run_seconds(4, 2000, r0), budget.registered_run_seconds(4, 2000, r1)
    assert p1["total"] - p0["total"] == pytest.approx(2 * d)  # scoring and its recomputation, both inside R
    assert budget.stage_caps(r1)["n4-U2000"]["evaluate"] > budget.stage_caps(r0)["n4-U2000"]["evaluate"] and budget.stage_caps(r1)["n4-U2000"]["recompute"] > budget.stage_caps(r0)["n4-U2000"]["recompute"]
