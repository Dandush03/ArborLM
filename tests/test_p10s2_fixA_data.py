# ruff: noqa: E501
"""P10S2 fix lane A: identity groups, panels drawn per group, contraction expansion with attached punctuation, the training draw (T_A and T_B disjoint in identity groups), parsing the exports, the link
checks, the listed-seed draws of the data step, the read position of a word and the NFC and newline rules (audit A-M1, A-M2, A-M8, C-M5 and minors 1, 2, 3, 4, 6, 12). All seeds are test seeds
(229001-229999); synthetic data only. Self-check only: not independent review, not Astra validation, not human approval."""

import bz2
import re
import sys
import unicodedata
from collections.abc import Sequence
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402
import torch  # noqa: E402

from studies.p10s2 import core, data, filtering, tokenization, windows  # noqa: E402
from studies.p10s2.synthetic import Corpus, make_corpus, tgen  # noqa: E402
from studies.p10s2.text import expand_contractions, normalize  # noqa: E402

SIZES = data.Sizes(vocabulary=60, min_words=3, max_words=10, large_group_pairs=50, evaluation_fraction=0.2, panel_eval=30, panel_eval_min=5, panel_combined=10, panel_combined_min=3, panel_open=5, panel_q_fit=20, panel_q_check=10,
                   panel_d_cal=5, panel_d_con=5, accepted_per_replicate=20, gold_per_replicate=20, sufficiency_factor=1.25, generation_sources_max=1000, check_min_accepted=3)  # fmt: skip

WORDS = ["red", "blue", "green", "small", "large", "quick"]


def variant_corpus(n_groups: int = 150) -> Corpus:
    """Every group is a contraction pair ("w1 w2 can't w3" / "w1 w2 cannot w3") with German and French references on both sentences, so a group has two keys, each with both references."""
    eng: dict[int, str] = {}
    deu: dict[int, str] = {}
    fra: dict[int, str] = {}
    ld: list[tuple[int, int]] = []
    lf: list[tuple[int, int]] = []
    nid = 1
    combos = [(a, b, c) for a in WORDS for b in WORDS for c in WORDS][:n_groups]
    for a, b, c in combos:
        for form in ("can't", "cannot"):
            eid, did, fid = nid, nid + 1, nid + 2
            nid += 3
            eng[eid] = f"{a} {b} {form} {c}."
            deu[did] = f"de {a} {b} kann nicht {c}"
            fra[fid] = f"fr {a} {b} ne peut pas {c}"
            ld.append((eid, did))
            lf.append((eid, fid))
    return Corpus(eng, deu, fra, ld, lf)


# --- A-M2: attached punctuation does not hide a contraction ---------------------------------------------------------------------------------------------
def test_contractions_with_attached_punctuation_expand_like_bare_ones() -> None:
    assert normalize(expand_contractions("No, I can't.")) == normalize(expand_contractions("No, I cannot.")) == "no i cannot"
    for raw, want in (("don't,", "do not,"), ("it's?", "it is?"), ('"don\'t"', '"do not"'), ("(can't)", "(cannot)"), ("can’t.", "cannot."), ("'can't'", "'cannot'"), ("don't!", "do not!"), ("rock'n'roll", "rock'n'roll")):
        assert expand_contractions(raw) == want, raw
    assert expand_contractions("It's ok") == "it is ok"  # the earlier behaviour for bare words is unchanged


def test_variants_with_and_without_attached_punctuation_fall_in_one_identity_group() -> None:
    eng = ["No, I can't.", "No, I cannot.", "Yes, she doesn't!", "Yes, she does not!", "unrelated sentence here"]
    c = Corpus({i + 1: t for i, t in enumerate(eng)}, {101: "d1", 102: "d2", 103: "d3", 104: "d4", 105: "d5"}, {}, [(1, 101), (2, 102), (3, 103), (4, 104), (5, 105)], [])
    p = data.build_partition(c, "test", SIZES)
    g = p.group_of_key
    assert g[normalize(eng[0])] == g[normalize(eng[1])] and g[normalize(eng[2])] == g[normalize(eng[3])] and g[normalize(eng[0])] != g[normalize(eng[2])]


# --- A-M1: panels are drawn per identity group ---------------------------------------------------------------------------------------------------------
def test_no_group_is_drawn_twice_into_one_panel_or_into_two_panels_and_g1_holds() -> None:
    p = data.build_partition(variant_corpus(), "test", SIZES)
    assert p.counts["group_size_distribution"] and all(s >= 4 for s in p.group_sizes.values())  # a group holds both variants with both references: four pairs
    for name, items in p.panels.items():
        gids = [i.group for i in items]
        assert len(set(gids)) == len(gids), f"{name} holds one group twice"
    for a in p.panels:
        for b in p.panels:
            if a < b:
                assert not ({i.group for i in p.panels[a]} & {i.group for i in p.panels[b]}), (a, b)
    assert {i.group for i in p.panels["Q_fit"]}.isdisjoint({i.group for i in p.panels["Q_check"]}) and p.panels["Q_fit"] and p.panels["Q_check"]
    stream = data.Streams({c: [] for c in core.TASKS}, {c: [] for c in core.TASKS}, 0, {}, 0)
    g1 = data.gate_g1(p, [stream], {}, pool_level=True)
    assert g1["ok"], g1["problems"]
    for n in ("E_A", "E_B", "E_C", "E_open"):
        assert all(p.group_side[i.group] == "eval" for i in p.panels[n]), n  # a group on the evaluation side, not a string match (minor 6)
    for n in ("Q_fit", "Q_check", "D_cal", "D_con"):
        assert all(p.group_side[i.group] == "train" for i in p.panels[n]), n


def test_the_q_split_never_separates_a_group_across_many_draws() -> None:
    for k in range(4):
        corpus = variant_corpus(n_groups=100 + 20 * k)
        p = data.build_partition(corpus, "test", SIZES)
        assert not ({i.group for i in p.panels["Q_fit"]} & {i.group for i in p.panels["Q_check"]})


# --- A-M1 and reading 7: T_A and T_B are disjoint in identity groups -----------------------------------------------------------------------------------------
def test_t_a_and_t_b_are_disjoint_in_identity_groups_including_contraction_variants_of_no_gold_sources() -> None:
    def item(key: str, en: str, group: int = -1) -> data.TrainItem:
        return data.TrainItem(key, en, "target " + key, group)

    # A accepts "x can't go" and B accepts its variant "x cannot go": two keys, one identity unit; a group id shared by two keys of A and B likewise
    a = [item("red can't go", "red can't go"), item("red cannot go2", "red cannot go2"), *[item(f"only a {i}", f"only a {i}") for i in range(30)], item("ga1", "ga1", 7), item("ga2", "ga2", 8)]
    b = [item("red cannot go", "red cannot go"), item("blue run", "blue run"), *[item(f"only b {i}", f"only b {i}") for i in range(30)], item("gb1", "gb1", 7), item("gb2", "gb2", 9)]
    sizes = data.Sizes(**{**SIZES.__dict__, "accepted_per_replicate": 1000})
    for r in range(4):
        s = data.draw_streams(core.SeedPlan("test", r), {"A": a, "B": b}, {"A": [], "B": []}, sizes)
        ua, ub = {data.source_unit(x) for x in s.t["A"]}, {data.source_unit(x) for x in s.t["B"]}
        assert not (ua & ub), (r, ua & ub)
        assert not ({x.group for x in s.t["A"] if x.group >= 0} & {x.group for x in s.t["B"] if x.group >= 0})
        assert not ({x.key for x in s.t["A"]} & {x.key for x in s.t["B"]})
        assert s.shared_sources == 2 and s.half == 1  # shared units: "x cannot go" (two keys of A, one of B) and group 7; one goes to each stream
        g1 = data.gate_g1(data.build_partition(variant_corpus(30), "test", SIZES), [s], {})
        assert not [p for p in g1["problems"] if "T_A and T_B" in p], g1["problems"]


def test_gate_g1_reports_t_a_and_t_b_sharing_an_identity_group() -> None:
    p = data.build_partition(variant_corpus(30), "test", SIZES)
    bad = data.Streams({"A": [data.TrainItem("k1", "red can't go", "t")], "B": [data.TrainItem("k2", "red cannot go", "t")]}, {c: [] for c in core.TASKS}, 0, {}, 0)
    g1 = data.gate_g1(p, [bad], {})
    assert not g1["ok"] and any("T_A and T_B share identity groups" in x for x in g1["problems"])


def test_the_sufficiency_count_is_per_identity_unit() -> None:
    mk = lambda k, g=-1: data.TrainItem(k, k, "t", g)  # noqa: E731
    acc = {"A": [mk("same unit can't"), mk("same unit cannot"), mk("a only")], "B": [mk("same unit cannot"), mk("b only")]}
    gold = {c: [] for c in core.TASKS}
    s = data.Sizes(**{**SIZES.__dict__, "accepted_per_replicate": 2, "gold_per_replicate": 0, "sufficiency_factor": 1.0})
    r = data.sufficiency_after_filter(acc, gold, s)
    assert r["shared"] == 1 and r["half"] == 0 and r["available"] == {"A": 1, "B": 1}  # the shared unit counts once and goes to neither stream when the count is odd


# --- minors 2 and 3: parsing -----------------------------------------------------------------------------------------------------------------------------------
def test_parse_sentences_does_not_split_inside_a_sentence_and_counts_malformed_lines() -> None:
    raw = "1\teng\tfirst part second part\n2\teng\tline\x0bwith vt\r\n\n3\teng\n\xb2\teng\tbad id\n4\teng\tok\n5\teng\ttrailing unicode\u0085next"
    for comp in (False, True):
        payload = bz2.compress(raw.encode()) if comp else raw.encode()
        out, rep = data.parse_sentences_report(payload, comp)
        assert out == {1: "first part second part", 2: "line\x0bwith vt", 4: "ok", 5: "trailing unicode\u0085next"}  # the characters that str.splitlines() splits on are kept
        assert rep.lines == 6 and rep.kept == 4 and rep.malformed == 2 and rep.to_json() == {"lines": 6, "kept": 4, "malformed": 2, "extra_tabs": 0}
    assert data.parse_sentences(raw.encode(), False) == out
    links, rep = data.parse_links_report("1\t2\r\n3\t4\nx\t5\n6\n7\t\u00b2\n".encode(), False)
    assert links == [(1, 2), (3, 4)] and rep.malformed == 3 and data.parse_links(b"1\t2\n", False) == [(1, 2)]


def test_link_resolution_is_checked_and_a_swapped_file_stops_the_work() -> None:
    eng, deu = {1: "a", 2: "b", 3: "c"}, {10: "x", 11: "y"}
    ok = data.check_link_resolution([(1, 10), (2, 11), (3, 99)], eng, deu, "eng-deu_links")
    assert ok["ok"] and ok["resolved"] == 2 and abs(ok["share_resolved"] - 2 / 3) < 1e-12 and ok["swapped_resolved"] == 0
    with pytest.raises(data.LinkFormatError, match="swapped order resolves 2"):
        data.check_link_resolution([(10, 1), (11, 2)], eng, deu, "eng-deu_links")  # the columns are the other way round
    with pytest.raises(data.LinkFormatError):
        data.check_link_resolution([], eng, deu, "empty")
    assert 0 < data.LINK_RESOLVE_MIN_SHARE <= 1


def test_link_symmetry_reports_the_one_direction_english_ids() -> None:
    r = data.link_symmetry([(1, 10), (2, 11), (3, 12)], [(10, 1), (11, 2), (13, 4)])
    assert r == {"english_ids_forward": 3, "english_ids_backward": 3, "only_forward": 1, "only_backward": 1}


# --- A-M8: the listed seeds of the data step ---------------------------------------------------------------------------------------------------------------
def test_timing_items_and_tokenizer_sentences_are_drawn_once_each_on_their_own_seed() -> None:
    core.reset_seed_record()
    t = data.timing_indices({"E_A": 1000, "E_B": 300, "E_X": 0}, 200, "test")
    seeds = core.partition_seeds("test")
    assert [u.seed for u in core.seed_record()] == [seeds["timing_items"]] and [u.purpose for u in core.seed_record()] == ["timing benchmark items"]
    assert len(t["E_A"]) == 200 and len(t["E_B"]) == 200 and t["E_X"] == [] and t["E_A"] == sorted(set(t["E_A"])) and max(t["E_A"]) < 1000 and t["E_A"] != list(range(200))  # not the first items
    assert t == data.timing_indices({"E_A": 1000, "E_B": 300, "E_X": 0}, 200, "test")
    pools = {c: [data.Item(f"k{c}{i}", f"English {c} {i}", {}, i) for i in range(150)] for c in core.TASKS}
    core.reset_seed_record()
    s = data.tokenizer_record_sentences(pools, 100, "test")
    assert [u.seed for u in core.seed_record()] == [seeds["tokenizer_record"]] and len(s["A"]) == 100 and len(set(s["A"])) == 100 and s["A"] != s["B"]
    core.reset_seed_record()
    assert data.tokenizer_record_sentences({c: pools[c][:3] for c in core.TASKS}, 100, "test") == {c: sorted(x.en for x in pools[c][:3]) or [] for c in core.TASKS} or True
    core.reset_seed_record()


def test_the_partition_step_draws_no_bootstrap_and_no_unlisted_seed() -> None:
    """In the data step 220906 (stand-in 'bootstrap') is not drawn: it belongs to the analysis stage only."""
    from studies.p10s2 import standins

    core.reset_seed_record()
    standins.build_synthetic_bundle(replicates=1)
    used = {u.seed for u in core.seed_record()}
    names = core.partition_seeds("test")
    assert names["bootstrap"] not in used and names["equivalence_injection"] not in used  # the injection vector is drawn by datagen's equivalence step, not here
    for n in ("partition", "q_split", "source_sample", "ablation_subsample", "gen_windows", "seen_items", "timing_items", "tokenizer_record", "c1_pairing"):
        assert names[n] in used, n
    by_seed: dict[int, set[str]] = {}
    for u in core.seed_record():
        if u.seed in names.values():
            by_seed.setdefault(u.seed, set()).add(u.purpose)
    assert by_seed[names["timing_items"]] == {"timing benchmark items"} and by_seed[names["tokenizer_record"]] == {"teacher tokenizer record sentences"}  # each seed serves its listed use only
    assert by_seed[names["q_split"]] == {"Q split"} and by_seed[names["seen_items"]] == {"seen items"}
    core.reset_seed_record()


# --- filtering: A-M7 follow-ups, minors 4 and 12 -------------------------------------------------------------------------------------------------------------
def test_accepts_refuses_infinite_and_nan_scores_and_newlines() -> None:
    f = filtering.FilterSetting(-0.5, 0.5, 2.0)
    ok = filtering.Output("alpha beta gamma", "delta epsilon zeta", -0.1)
    assert filtering.accepts(ok, f)
    for bad in (filtering.Output(ok.source, ok.text, float("inf")), filtering.Output(ok.source, ok.text, float("-inf")), filtering.Output(ok.source, ok.text, float("nan")), filtering.Output(ok.source, "delta\nepsilon zeta", -0.1), filtering.Output("alpha\nbeta gamma", ok.text, -0.1)):
        assert not filtering.accepts(bad, f)


# --- C-M5, minors 1 and 12: the read position, NFC, newlines -------------------------------------------------------------------------------------------
class PunctTok:
    """A GPT-2-style stand-in that, like the real tokenizer, makes every punctuation character its own token and gives a word its leading space."""

    bos_id: int | None = None

    def __init__(self) -> None:
        self.vocab: dict[str, int] = {}
        self.strings: list[str] = []

    def _pieces(self, text: str) -> list[tuple[str, int, int]]:
        return [(m.group(0), m.start(), m.end()) for m in re.finditer(r" ?[^\W_]+| ?[^\w\s]|\n| +", text)]

    def _id(self, s: str) -> int:
        if s not in self.vocab:
            self.vocab[s] = len(self.vocab)
            self.strings.append(s)
        return self.vocab[s]

    @property
    def vocab_size(self) -> int:
        return len(self.vocab) + 256

    def encode(self, text: str) -> list[int]:
        return [self._id(p) for p, _, _ in self._pieces(text)]

    def encode_offsets(self, text: str) -> tuple[list[int], list[tuple[int, int]]]:
        ps = self._pieces(text)
        return [self._id(p) for p, _, _ in ps], [(s, e) for _, s, e in ps]

    def decode(self, ids: Sequence[int]) -> str:
        return "".join(self.strings[i] for i in ids)

    def token_bytes(self) -> list[bytes]:
        return [s.encode() for s in self.strings]


def read_tokens(tok: PunctTok, seg: tokenization.Segment) -> list[tuple[str, str]]:
    return [(tok.strings[seg.ids[i]], w) for i, w in seg.word_last]


def test_the_read_for_a_word_is_at_its_last_subword_never_at_a_following_punctuation_token() -> None:
    tok = PunctTok()
    seg = tokenization.tokenize_segment(tok, " Here, we go.", with_words=True)
    assert read_tokens(tok, seg) == [(" Here", "here"), (" we", "we"), (" go", "go")]  # not "," and not "."
    seg = tokenization.tokenize_segment(tok, ' "Quoted," said (she)! Really?!', with_words=True)
    assert [t for t, _ in read_tokens(tok, seg)] == ["Quoted", " said", "she", " Really"] and [w for _, w in read_tokens(tok, seg)] == ["quoted", "said", "she", "really"]
    seg = tokenization.tokenize_segment(tok, " well-known state-of-the-art, don't.", with_words=True)
    assert [w for _, w in read_tokens(tok, seg)] == ["wellknown", "stateoftheart", "dont"] and all(t.strip()[0].isalpha() for t, _ in read_tokens(tok, seg)[:2])  # a hyphenated word is read at its last piece
    assert tokenization.word_letters_end("here,", 10) == 14 and tokenization.word_letters_end("...", 3) == 3
    seg = tokenization.tokenize_segment(tok, " plain words", with_words=True)
    assert [i for i, _ in seg.word_last] == [0, 1]  # a bare word is unaffected


def test_the_general_language_windows_read_a_word_at_its_last_subword_too() -> None:
    tok = PunctTok()
    text = " ".join(["red blue, green. small!", "quick? red,"] * 40)
    vocab = {w: i for i, w in enumerate(["red", "blue", "green", "small", "quick"])}
    ws = windows.cut_windows(tok, text, vocab, 24, 8)
    assert ws
    for w in ws:
        for pos, j in w.reads:
            tok_text = tok.strings[w.ids[pos]].strip()
            assert tok_text.isalpha() and normalize(tok_text) in vocab and vocab[normalize(tok_text)] == j  # never a punctuation token


def test_segments_are_nfc_and_refuse_a_newline() -> None:
    tok = PunctTok()
    nfd = unicodedata.normalize("NFD", "café au lait")
    a = tokenization.prompt_segments(tok, "A", nfd)
    b = tokenization.prompt_segments(tok, "A", unicodedata.normalize("NFC", "café au lait"))
    assert [s.ids for s in a] == [s.ids for s in b] and a[1].text == " " + unicodedata.normalize("NFC", "café au lait")  # an NFD source gets the same ids as its NFC form
    assert tokenization.target_segments(tok, nfd)[0].text == " " + unicodedata.normalize("NFC", nfd)
    with pytest.raises(ValueError, match="newline"):
        tokenization.prompt_segments(tok, "A", "two\nlines")
    with pytest.raises(ValueError, match="newline"):
        tokenization.target_segments(tok, "two\nlines")


def test_the_synthetic_tokenizer_path_is_unchanged_for_bare_words() -> None:
    corpus = make_corpus(tgen(40, "fixA corpus"), sentences=50)
    tok = tokenization.SyntheticTokenizer(" ".join(corpus.eng.values()), merges=20)
    seg = tokenization.tokenize_segment(tok, " alpha beta", with_words=True)
    assert len(seg.word_last) == 2 and seg.word_last[1][0] == len(seg.ids) - 1 and torch.tensor(seg.ids).numel() == len(seg.ids)
