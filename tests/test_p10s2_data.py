# ruff: noqa: E501
"""P10S2 partitions, identity groups, panels, no-gold sources, training draws, G1, the acceptance filter, qualification and the general-language windows (ADR-0022 sections 4.3, 5.2, 5.3, 6.4, 9).
Self-check only: not independent review, not Astra validation, not human approval."""

import bz2
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402
import torch  # noqa: E402

from studies.p10s2 import core, data, filtering, windows  # noqa: E402
from studies.p10s2.synthetic import (  # noqa: E402
    Corpus,
    make_corpus,
    make_text,
    make_tokenizer,
    tgen,
)

SIZES = data.Sizes(vocabulary=40, min_words=3, max_words=10, large_group_pairs=50, evaluation_fraction=0.2, panel_eval=30, panel_eval_min=5, panel_combined=10, panel_combined_min=3, panel_open=5, panel_q_fit=20, panel_q_check=10,
                   panel_d_cal=5, panel_d_con=5, accepted_per_replicate=20, gold_per_replicate=20, sufficiency_factor=1.25, generation_sources_max=1000, check_min_accepted=3)  # fmt: skip


def corpus(eng: list[str], de: dict[int, str] | None = None, fr: dict[int, str] | None = None) -> Corpus:
    """English sentence i has id i + 1; ``de``/``fr`` map an English index to its reference text."""
    e = {i + 1: t for i, t in enumerate(eng)}
    deu, fra, ld, lf = {}, {}, [], []
    for i, t in (de or {}).items():
        deu[1000 + i] = t
        ld.append((i + 1, 1000 + i))
    for i, t in (fr or {}).items():
        fra[2000 + i] = t
        lf.append((i + 1, 2000 + i))
    return Corpus(e, deu, fra, ld, lf)


def test_identity_groups_join_on_shared_english_expansion_and_shared_references() -> None:
    eng = ["Don't go home now", "Do not go home now", "see the red car", "look at the red car", "plain alpha beta"]
    c = corpus(eng, de={0: "geh nicht heim", 1: "gehe nicht nach hause", 2: "sieh das auto", 3: "sieh das auto", 4: "schlicht"})
    p = data.build_partition(c, "test", SIZES)
    assert p.counts["pairs"] == 5
    g = p.group_of_key if p.group_of_key else {}
    n = lambda t: data.normalize(t)  # noqa: E731
    assert g[n(eng[0])] == g[n(eng[1])]  # the contraction-expanded string joins the pairs
    assert g[n(eng[2])] == g[n(eng[3])]  # a shared reference joins the pairs
    assert g[n(eng[4])] not in (g[n(eng[0])], g[n(eng[2])])
    assert p.counts["group_size_distribution"] == {1: 1, 2: 2}  # the size distribution is reported before assignment


def test_groups_larger_than_50_go_to_training_and_eval_takes_20_percent_of_pairs() -> None:
    big = [f"big alpha beta w{i}" for i in range(60)]
    singles = [f"single word s{i} here" for i in range(100)]
    c = corpus([*big, *singles], de={**{i: "gleiche referenz" for i in range(60)}, **{60 + i: f"ref {i}" for i in range(100)}})
    p = data.build_partition(c, "test", SIZES)
    assert len(p.large_groups) == 1 and p.group_sizes[p.large_groups[0]] == 60 and p.group_side[p.large_groups[0]] == "train"
    assert p.counts["remaining_pairs"] == 100 and p.counts["eval_pairs"] >= 20  # 20% of the remaining pairs, counted in pairs
    assert p.counts["eval_pairs"] <= 21
    # deterministic given the partition seed
    q = data.build_partition(c, "test", SIZES)
    assert p.panel_hashes() == q.panel_hashes() and p.group_side == q.group_side


def test_no_gold_sources_follow_the_normalized_and_expanded_rules() -> None:
    eng = ["we can not go", "we cannot go home", "Can't we go now", "have a nice day", "have a nice day!", "quite new unique line"]
    c = corpus(eng, de={3: "habt einen schönen tag"}, fr={4: "bonne journée"})
    p = data.build_partition(c, "test", SIZES)
    src_a = {i.key for i in p.source_pool["A"]}
    src_b = {i.key for i in p.source_pool["B"]}
    assert "have a nice day" not in src_a  # its normalized string has a German reference (also through the other sentence with the same normalized form)
    assert "have a nice day" not in src_b  # likewise a French reference
    assert "quite new unique line" in src_a and "quite new unique line" in src_b
    # a sentence is not a source if the evaluation side holds its string
    for k in src_a:
        assert k not in p.eval_strings


def test_vocabulary_ties_break_lexicographically_and_panels_respect_it() -> None:
    eng = [f"alpha beta gamma {w}" for w in ("delta", "delta", "delta", "zeta", "eta")] * 3 + ["omega kappa lambda unique"]
    c = corpus(eng)
    p = data.build_partition(c, "test", data.Sizes(**{**SIZES.__dict__, "vocabulary": 5}))
    assert p.vocab == ["alpha", "beta", "gamma", "delta", "eta"]  # most frequent first (alpha, beta, gamma tie at 15, then delta 9); ties alphabetical (eta and zeta tie at 3; eta first)
    assert p.vocab_index["alpha"] == 0


def test_panels_are_in_vocabulary_group_disjoint_and_stratified() -> None:
    g = tgen(71, "data corpus")
    c = make_corpus(g, sentences=900)
    p = data.build_partition(c, "test", SIZES)
    vocab = set(p.vocab)
    for name in ("E_A", "E_B", "E_C", "Q_fit", "Q_check", "D_cal", "D_con"):
        for it in p.panels[name]:
            assert 3 <= len(it.key.split()) <= 10 and all(w in vocab for w in it.key.split())
    assert all(it.refs.keys() >= {"A", "B"} for n in ("E_C", "Q_fit", "Q_check", "D_cal", "D_con") for it in p.panels[n])  # both references where both are needed
    assert all("A" in it.refs for it in p.panels["E_A"]) and all("B" in it.refs for it in p.panels["E_B"])
    names = sorted(p.panels)
    for i, a in enumerate(names):
        for b in names[i + 1 :]:
            ga, gb = {x.group for x in p.panels[a]}, {x.group for x in p.panels[b]}
            assert not (ga & gb), (a, b)  # disjoint in identity groups
    q = {x.key for x in p.panels["Q_fit"]} & {x.key for x in p.panels["Q_check"]}
    assert not q
    assert sum(len(v) for v in p.panels.values()) > 0 and p.counts["reference_count_distribution"]["E_A"]
    assert p.counts["panel_sizes"]["Q_fit"] + p.counts["panel_sizes"]["Q_check"] <= SIZES.panel_q_fit + SIZES.panel_q_check
    for it in p.panels["E_open"]:
        assert any(w not in vocab for w in it.key.split())
    # the draw order of the partition seed: groups, then Q, D_cal, D_con, E_A, E_B, E_C, E_open (a changed panel size moves only later panels)
    p2 = data.build_partition(c, "test", data.Sizes(**{**SIZES.__dict__, "panel_open": 3}))
    assert [i.key for i in p.panels["Q_fit"]] == [i.key for i in p2.panels["Q_fit"]] and [i.key for i in p.panels["E_C"]] == [i.key for i in p2.panels["E_C"]]


def test_gold_pool_excludes_q_dcal_dcon_groups_and_g1_passes_then_detects_leaks() -> None:
    c = make_corpus(tgen(72, "g1 corpus"), sentences=900)
    p = data.build_partition(c, "test", SIZES)
    held = {x.group for n in ("Q_fit", "Q_check", "D_cal", "D_con") for x in p.panels[n]}
    for cap in core.TASKS:
        assert not ({x.group for x in p.gold_pool[cap]} & held)
    accepted = {cap: [data.TrainItem(x.key, x.en, "teacher text " + x.key, x.group) for x in p.source_pool[cap][:60]] for cap in core.TASKS}
    plan = core.SeedPlan("test", 0)
    s = data.draw_streams(plan, accepted, p.gold_pool, SIZES)
    ok = data.gate_g1(p, [s], {cap: [x.target for x in accepted[cap]] for cap in core.TASKS})
    assert ok["ok"], ok["problems"]
    # inject leaks: a target equal to an evaluation reference; a source with an evaluation panel's group; shared English between T_A and T_B
    ev = p.panels["E_A"][0]
    leak_t = data.TrainItem("x", "x", ev.refs["A"][0], -1)
    bad = data.Streams({"A": [leak_t, *s.t["A"][:3]], "B": list(s.t["B"][:3])}, s.gold, 0, {}, 0)
    assert any("equal to an evaluation reference" in m for m in data.gate_g1(p, [bad], {})["problems"])
    group_leak = data.Streams({"A": [data.TrainItem("g", "g", "zz", ev.group), *s.t["A"][:2]], "B": s.t["B"][:2]}, s.gold, 0, {}, 0)
    assert any("identity groups" in m for m in data.gate_g1(p, [group_leak], {})["problems"])
    shared = data.Streams({"A": [s.t["A"][0]], "B": [s.t["A"][0]]}, s.gold, 0, {}, 0)
    assert any("share English sources" in m for m in data.gate_g1(p, [shared], {})["problems"])
    pool = data.gate_g1(p, [shared], {}, pool_level=True)
    assert not any("share English sources" in m for m in pool["problems"])  # pool level skips only the T_A/T_B English check
    assert 0.0 <= ok["neighbour_share_distance_1"] <= 1.0
    assert data.word_distance_one(("a", "b", "c"), ("a", "x", "c")) and data.word_distance_one(("a", "b"), ("a", "b", "c")) and not data.word_distance_one(("a", "b"), ("a", "b"))


def test_sufficiency_rules_and_training_draws() -> None:
    mk = lambda keys: [data.TrainItem(k, k, "t " + k) for k in keys]  # noqa: E731
    only_a = [f"a{i}" for i in range(15)]
    only_b = [f"b{i}" for i in range(15)]
    shared = [f"s{i}" for i in range(11)]  # odd: the half is the smaller one
    acc = {"A": mk(only_a + shared), "B": mk(only_b + shared)}
    gold = {c: [data.Item(f"g{c}{i}", f"g{c}{i}", {c: ("r",)}, i) for i in range(20)] for c in core.TASKS}
    s = data.sufficiency_after_filter(acc, gold, SIZES)
    assert s["shared"] == 11 and s["half"] == 5 and s["available"] == {"A": 20, "B": 20} and s["needed"] == 25 and not s["ok"] and s["outcome"] == "TRANSFER-INCONCLUSIVE: DATA-INSUFFICIENT"
    acc2 = {"A": mk(only_a + [f"a{i}" for i in range(15, 40)] + shared), "B": mk(only_b + [f"b{i}" for i in range(15, 40)] + shared)}
    assert data.sufficiency_after_filter(acc2, gold, SIZES)["ok"]
    assert not data.sufficiency_after_filter(acc2, {"A": gold["A"][:5], "B": gold["B"]}, SIZES)["ok"]  # gold pairs outside Q, D_cal, D_con: 8,000 per capability
    p1, p2 = core.SeedPlan("test", 0), core.SeedPlan("test", 1)
    s1 = data.draw_streams(p1, acc2, gold, SIZES)
    s1b = data.draw_streams(p1, acc2, gold, SIZES)
    s2 = data.draw_streams(p2, acc2, gold, SIZES)
    assert [x.key for x in s1.t["A"]] == [x.key for x in s1b.t["A"]] and [x.key for x in s1.t["A"]] != [x.key for x in s2.t["A"]]
    assert len(s1.t["A"]) == len(s1.t["B"]) == SIZES.accepted_per_replicate and not ({x.key for x in s1.t["A"]} & {x.key for x in s1.t["B"]})  # disjoint in English
    assert s1.half == 5 and len(s1.gold["A"]) == 20
    ov = data.replicate_overlap([s1, s2])
    assert set(ov) == {"r0-r1-A", "r0-r1-B"} and all(0.0 <= v <= 1.0 for v in ov.values())  # the overlap between replicates is reported
    # the seeds used: +1 (training draw) and +5 (gold draw), each a fresh generator
    core.reset_seed_record()
    data.draw_streams(p1, acc2, gold, SIZES)
    assert [(u.seed - p1.base) for u in core.seed_record()] == [1, 5]
    core.reset_seed_record()


# --- the acceptance filter and qualification ----------------------------------------------------------------------------------------------------------
def out(text: str, score: float, source: str = "one two three four") -> filtering.Output:
    return filtering.Output(source, text, score)


def test_accepts_applies_the_three_conditions() -> None:
    f = filtering.FilterSetting(-0.2, 0.5, 2.0)
    assert filtering.accepts(out("eins zwei drei vier", -0.1), f)
    assert not filtering.accepts(out("eins zwei drei vier", -0.3), f)  # (a) score below tau
    assert not filtering.accepts(out("eins", -0.1), f)  # (b) ratio 0.25
    assert not filtering.accepts(out("One, two three FOUR", -0.1), f)  # (c) equals the source after normalization
    assert not filtering.accepts(out("eins zwei drei vier", float("nan")), f)


def test_filter_fit_most_permissive_with_tie_break_and_wilson_bound() -> None:
    ref = ["gleich eins zwei drei"]
    good = [out("gleich eins zwei drei", -0.04 - 0.01 * (k % 3)) for k in range(80)]  # correct outputs with high scores
    bad = [out("quatsch qwertz yxcv", -0.55, "five six seven eight") for _ in range(20)]  # wrong, low scores
    refs = [ref] * 80 + [["voellig anderer satz hier"]] * 20
    fit = filtering.fit_filter([*good, *bad], refs)
    assert fit.setting is not None and fit.precision == 1.0 and fit.wilson[0] >= 0.90 and fit.accepted == 80
    assert fit.setting.tau >= -0.3  # the bad outputs (score -0.55) stay out; among equal accepted share the larger tau is taken
    assert fit.setting.rho2 - fit.setting.rho1 == pytest.approx(1.0)  # then the narrower length-ratio range [0.6, 1.6]
    small = filtering.fit_filter(good[:10], [ref] * 10)
    assert small.setting is None  # 10 correct of 10 has a Wilson lower bound of 0.72 < 0.90: no setting qualifies
    chk = filtering.check_filter(fit.setting, good[:20], [ref] * 20, 5)
    assert chk["ok"] and chk["accepted"] == 20
    assert not filtering.check_filter(fit.setting, good[:2], [ref] * 2, 5)["ok"]  # fewer than the required accepted items
    wrong = filtering.check_filter(fit.setting, good[:20], [["x y z"]] * 20, 5)
    assert not wrong["ok"] and wrong["precision"] == 0.0


def test_accepted_pool_drops_outputs_equal_to_an_evaluation_reference() -> None:
    f = filtering.FilterSetting(-0.5, 0.5, 2.0)
    items = [data.Item("one two three", "one two three", {}, -1), data.Item("four five six", "four five six", {}, -1)]
    outs = [filtering.Output("one two three", "eins zwei drei", -0.1), filtering.Output("four five six", "vier fuenf sechs", -0.1)]
    pool, dropped = filtering.accepted_pool(outs, items, f, {data.normalize("Vier fuenf sechs.")})
    assert [x.key for x in pool] == ["one two three"] and dropped == 1


def test_qualification_gate_each_failure() -> None:
    fits = {c: filtering.FilterFit(filtering.FilterSetting(-0.1, 0.5, 2.0), 100, 0.5, 0.95, (0.9, 0.98), 3) for c in core.TASKS}
    checks = {c: {"ok": True, "accepted": 200, "precision": 0.95, "wilson": [0.9, 0.97], "correct": 190} for c in core.TASKS}
    teach = {"A": {"A": 0.70, "B": 0.10}, "B": {"A": 0.12, "B": 0.72}}
    ok = filtering.qualify(teach, {"A": 0.05, "B": 0.05}, fits, checks, {"A": 9000, "B": 9000}, 8000)
    assert ok["ok"] and ok["outcome"] is None
    low = filtering.qualify({"A": {"A": 0.50, "B": 0.1}, "B": teach["B"]}, {"A": 0.05, "B": 0.05}, fits, checks, {"A": 9000, "B": 9000}, 8000)
    assert not low["ok"] and "own score" in " ".join(low["failed"]) and low["outcome"] == "TRANSFER-INCONCLUSIVE: TEACHERS-NOT-QUALIFIED"
    margin = filtering.qualify({"A": {"A": 0.60, "B": 0.1}, "B": {"A": 0.40, "B": 0.72}}, {"A": 0.05, "B": 0.05}, fits, checks, {"A": 9000, "B": 9000}, 8000)
    assert "margin" in " ".join(margin["failed"])  # 0.60 - max(0.40, 0.05) = 0.20 < 0.30
    pool = filtering.qualify(teach, {"A": 0.05, "B": 0.05}, fits, checks, {"A": 7999, "B": 9000}, 8000)
    assert "accepted pool" in " ".join(pool["failed"])
    nf = {**fits, "A": filtering.FilterFit(None, 0, 0.0, float("nan"), (0.0, 1.0), 0)}
    assert "acceptance filter" in " ".join(filtering.qualify(teach, {"A": 0.05, "B": 0.05}, nf, checks, {"A": 9000, "B": 9000}, 8000)["failed"])
    # the teacher and the untrained student bound the margin: the larger of the other teacher's and the student's score
    st = filtering.qualify(teach, {"A": 0.50, "B": 0.05}, fits, checks, {"A": 9000, "B": 9000}, 8000)
    assert not st["ok"] and st["detail"]["A"]["margin"] == pytest.approx(0.20)


def test_teacher_only_training_material_is_never_gold() -> None:
    c = make_corpus(tgen(73, "teacher-only corpus"), sentences=900)
    p = data.build_partition(c, "test", SIZES)
    for cap in core.TASKS:
        for it in p.source_pool[cap]:
            assert cap not in it.refs  # a no-gold source has no reference in that language


# --- the general-language windows ---------------------------------------------------------------------------------------------------------------------
def test_window_strata_and_grid() -> None:
    corpus_ = make_corpus(tgen(74, "win corpus"), sentences=100)
    txt = make_text(tgen(75, "win text"), n_words=1200, marker_rate=0.05)
    tok = make_tokenizer(corpus_, txt, merges=40)
    vocab = {"wabc": 0}
    wl = windows.cut_windows(tok, txt, vocab, 48, 16)
    ids, _ = tok.encode_offsets(txt)
    assert len(wl) <= len(ids) // 48 and all(len(w.ids) == 48 for w in wl)  # consecutive non-overlapping windows; the remainder is dropped
    for w in wl:
        text = tok.decode(w.ids)
        head = tok.decode(w.ids[:16])
        if w.stratum == "marker":
            assert windows.first_marker(head) is not None or windows.first_marker(text) is not None
            assert 0 <= w.marker_end < 16
        else:
            assert windows.first_marker(text) is None  # the ordinary stratum contains none of the strings anywhere
    assert {w.stratum for w in wl} == {"marker", "ordinary"}
    sel = windows.select_windows(wl, {"marker": 3, "ordinary": 3}, core.partition_gen("test", "gen_windows"))
    assert len(sel) == 6 and sum(w.stratum == "marker" for w in sel) == 3
    with pytest.raises(windows.WindowsInsufficient):
        windows.select_windows(wl, {"marker": 10**6, "ordinary": 1}, core.partition_gen("test", "gen_windows"))  # nothing is relaxed; the work returns to the lead


def test_marker_matching_is_case_sensitive_substring_and_colon_newline() -> None:
    assert windows.first_marker("a Germany b") == (2, 8)  # "Germany" matches "German"
    assert windows.first_marker("a german b") is None  # case-sensitive
    assert windows.first_marker("key:\nvalue") == (3, 5)  # a ':' immediately followed by a newline
    assert windows.first_marker("key: value\n") is None and windows.first_marker("key :\n") == (4, 6)
    assert windows.first_marker("a French and English") == (2, 8)  # the earliest string


def test_a_window_whose_only_marker_lies_after_token_64_is_in_neither_stratum() -> None:
    tok = make_tokenizer(make_corpus(tgen(76, "c"), sentences=50), "x y z", merges=10)
    filler = "aa bb cc dd ee ff gg hh ii jj kk ll"
    txt = (filler + " ") * 4 + "German " + filler + " " + filler  # "German" lies well after token 16 of its window
    ids, offs = tok.encode_offsets(txt)
    c = txt.index("German")
    k = next(i for i, (s0, _e) in enumerate(offs) if s0 >= c)
    window, decision = 80, 16
    assert k % window >= decision  # the scenario: the string is after the part the router sees
    wl = windows.cut_windows(tok, txt, {}, window, decision)
    containing = tuple(ids[(k // window) * window : (k // window + 1) * window])
    assert containing not in [w.ids for w in wl]  # neither marker-like (the string is after token 16) nor ordinary (it contains a string): the window is not used
    assert any(w.stratum == "ordinary" for w in wl)  # the clean windows around it remain


# --- the exports ------------------------------------------------------------------------------------------------------------------------------------
def test_parse_exports_and_link_symmetry() -> None:
    sent = bz2.compress(b"1\teng\tHello there\n2\teng\tSecond one\nx\tbad\tline\n")
    links = bz2.compress(b"1\t10\n2\t11\n3\t12\n")
    back = bz2.compress(b"10\t1\n11\t2\n")
    assert data.parse_sentences(sent) == {1: "Hello there", 2: "Second one"}
    assert data.parse_links(links) == [(1, 10), (2, 11), (3, 12)]
    sym = data.link_symmetry(data.parse_links(links), data.parse_links(back))
    assert sym == {"english_ids_forward": 3, "english_ids_backward": 2, "only_forward": 1, "only_backward": 0}
    # English ids with a link in only one direction are counted: forward has English 3 with translation 12; backward lists translation ids 10 and 11
    assert data.link_symmetry([(1, 10), (3, 12)], [(10, 1), (11, 2)]) == {"english_ids_forward": 2, "english_ids_backward": 2, "only_forward": 1, "only_backward": 1}


def test_sample_and_subsample_are_seeded_by_their_listed_streams() -> None:
    p = data.build_partition(make_corpus(tgen(77, "sub corpus"), sentences=700), "test", SIZES)
    a = data.fixed_subsample(p.panels["E_A"], 5, "test", "ablation_subsample")
    b = data.fixed_subsample(p.panels["E_A"], 5, "test", "ablation_subsample")
    assert [x.key for x in a] == [x.key for x in b] and len(a) == 5
    plan = data.plan_generation(p, "test")
    assert set(plan) == {"A", "B"} and all(len(v) <= SIZES.generation_sources_max for v in plan.values())
    a2 = torch.randperm(5, generator=core.partition_gen("test", "q_split")).tolist()
    assert a2 == torch.randperm(5, generator=core.partition_gen("test", "q_split")).tolist()  # a listed stream seed starts a fresh generator at every use
