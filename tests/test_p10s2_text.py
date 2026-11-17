# ruff: noqa: E501
"""P10S2 text, chrF-norm, gap closed, intervals and the tokenization conventions with checks (a)-(e) of section 14.2 on synthetic text (ADR-0022 sections 5.2, 10.1, 14.2). Self-check only: not independent review,
not Astra validation, not human approval."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402
import torch  # noqa: E402

from studies.p10s2 import core, equivalence, text, tokenization  # noqa: E402
from studies.p10s2.model import StudentConfig, build_student, export_hf_state_dict  # noqa: E402
from studies.p10s2.reference_standin import ReferenceLlama  # noqa: E402
from studies.p10s2.synthetic import (  # noqa: E402
    SyntheticTokenizer,
    make_corpus,
    make_text,
    make_tokenizer,
    tgen,
)


# --- normalization and chrF-norm (hand cases) -------------------------------------------------------------------------------------------------------
def test_normalization() -> None:
    assert text.normalize("  Hello,   WORLD!  ") == "hello world"
    assert text.normalize("Don't stop.") == "dont stop"
    assert text.normalize("é") == text.normalize("é")  # NFC
    assert text.expand_contractions("Don't stop") == "do not stop" and text.expand_contractions("It’s fine") == "it is fine"
    assert text.normalize(text.expand_contractions("Don't")) != text.normalize("Don't")  # the expanded form differs


def test_chrf_hand_cases() -> None:
    assert text.chrf_pair("hello", "hello") == 1.0
    assert text.chrf_pair("abc", "xyz") == 0.0
    assert text.chrf_pair("", "abc") == 0.0 and text.chrf_pair("abc", "") == 0.0  # no effective order
    # whitespace is removed before n-gram extraction
    assert text.chrf_pair("a b c", "abc") == 1.0
    # one effective order only (strings of length 1): P = R = 1 at order 1
    assert text.chrf_pair("a", "a") == 1.0
    # hand computation: hyp "abcd" against ref "abcf": orders 1..4 are effective on both (length 4)
    # matches: 1-gram 3 of 4, 2-gram 2 of 3, 3-gram 1 of 2, 4-gram 0 of 1; P = R = mean(0.75, 2/3, 0.5, 0) over the 4 effective orders
    p = (0.75 + 2 / 3 + 0.5 + 0.0) / 4
    assert text.chrf_pair("abcd", "abcf") == pytest.approx(p)  # precision equals recall here, so F2 equals the same value
    # asymmetric: F with beta 2 weights recall; hyp "ab" vs ref "abcd": orders 1,2 effective; P = (1 + 1)/2 = 1, R = (2/4 + 1/3)/2
    r = (2 / 4 + 1 / 3) / 2
    assert text.chrf_pair("ab", "abcd") == pytest.approx(5 * 1.0 * r / (4 * 1.0 + r))
    assert text.chrf_item("abcd", ["xyz", "abcd"]) == 1.0  # maximum over references
    assert text.chrf_item("abcd", []) == 0.0
    mean, items = text.panel_chrf(["abcd", "xyz"], [["abcd"], ["abcd"]])
    assert mean == pytest.approx(0.5) and items[0] == 1.0


def test_chrf_is_normalized_and_bounded() -> None:
    assert text.chrf_pair("Hello, World!", "hello world") == 1.0
    for h, rf in (("abc def", "abd"), ("zz", "zzzz"), ("a", "b")):
        assert 0.0 <= text.chrf_pair(h, rf) <= 1.0


def test_sacrebleu_is_not_in_the_lock_so_the_score_is_implemented_here() -> None:
    lock = (core.ROOT / "uv.lock").read_text()
    assert "sacrebleu" not in lock  # the cross-check against sacrebleu 2.5.1 is made in the data-generation step (studies/p10s2/datagen.py), not here


# --- gap closed --------------------------------------------------------------------------------------------------------------------------------------
def test_gap_closed_and_not_evaluated() -> None:
    assert text.gap_closed(0.6, 0.1, 0.9) == pytest.approx(0.625)
    assert text.gap_closed(0.1, 0.1, 0.9) == 0.0
    assert text.gap_closed(0.5, 0.2, 0.49) is None  # denominator 0.29 < 0.30
    assert text.gap_closed(0.5, 0.2, 0.5) == pytest.approx(1.0)  # denominator exactly 0.30 is defined
    assert text.gap_closed(float("nan"), 0.1, 0.9) is None and text.gap_closed(0.5, float("inf"), 0.9) is None


def test_wilson_and_bootstrap() -> None:
    lo, hi = text.wilson(150, 150)
    assert lo == pytest.approx(0.9751, abs=1e-3) and hi == 1.0
    lo, hi = text.wilson(135, 150)  # precision 0.90 with 150 accepted: the ADR quotes about 0.84-0.94
    assert 0.83 < lo < 0.86 and 0.93 < hi < 0.95
    assert text.wilson(0, 0) == (0.0, 1.0)
    core.reset_seed_record()
    a = text.bootstrap_interval([0.1, 0.4, 0.5, 0.9, 0.2], core.seeded_generator(229011, "bootstrap", "test"), resamples=200)
    b = text.bootstrap_interval([0.1, 0.4, 0.5, 0.9, 0.2], core.seeded_generator(229011, "bootstrap", "test"), resamples=200)
    assert a == b and a[0] <= 0.42 <= a[1]


# --- tokenization conventions and checks (a)-(e) ----------------------------------------------------------------------------------------------------
def tiny() -> SyntheticTokenizer:
    corpus = make_corpus(tgen(21, "tok corpus"), sentences=200)
    return make_tokenizer(corpus, make_text(tgen(22, "tok text"), n_words=300), merges=60)


def test_segment_ids_are_concatenated_and_words_have_stored_last_subword() -> None:
    tok = tiny()
    vocab = {"wbake": 0}
    ex = tokenization.build_example(tok, "A", "wbake wkemo extra", " wbake wkemo", vocab, "k")
    assert ex.ids == tuple(i for s in ex.segments for i in s.ids)
    assert ex.prompt_len == sum(len(s.ids) for s in ex.segments[:4]) and ex.marker == ex.prompt_len - 1
    assert ex.target_len == len(ex.ids) - ex.prompt_len > 0
    # the read position of an in-vocabulary word is the last subword of that word, from the tokenizer's offsets
    src_seg = ex.segments[1]
    assert src_seg.text == " wbake wkemo extra" and all(w for _i, w in src_seg.word_last)
    for pos, j in ex.reads:
        assert j == 0 and pos < ex.prompt_len
    # out-of-vocabulary words are never read
    assert len(ex.reads) == sum(1 for _i, w in src_seg.word_last if w in vocab)


def test_example_json_round_trip_needs_no_tokenizer() -> None:
    tok = tiny()
    vocab = {"wbake": 0, "wkemo": 1}
    ex = tokenization.build_example(tok, "B", "wbake wkemo", "fx fy", vocab, "key-1")
    back = tokenization.example_from_json(ex.to_json(), vocab)
    assert (back.ids, back.reads, back.marker, back.prompt_len, back.target_len, back.task) == (ex.ids, ex.reads, ex.marker, ex.prompt_len, ex.target_len, ex.task)


def test_check_a_segment_ids_against_whole_string_ids() -> None:
    tok = tiny()
    vocab = {"wbake": 0}
    ex = tokenization.build_example(tok, "A", "wbake wkemo", None, vocab, "k")
    r = tokenization.check_segments_vs_whole([ex.segments], tok)
    assert r["n"] == 1 and "mismatch_rate" in r
    # a tokenizer whose merges cross a segment boundary yields a mismatch, which the check reports
    crossing = SyntheticTokenizer("English: German:\nGerman: x x x\nGerman:", merges=30)
    segs = [tokenization.tokenize_segment(crossing, "ab"), tokenization.tokenize_segment(crossing, "\n"), tokenization.tokenize_segment(crossing, "German:")]
    rep = tokenization.check_segments_vs_whole([segs], crossing)
    assert rep["n"] == 1 and rep["mismatches"] in ([], [0])  # reported either way; the rate is the share of inputs that differ
    # a hand-made mismatch is always reported
    class Odd(SyntheticTokenizer):
        def encode(self, text: str) -> list[int]:
            return super().encode(text)[::-1] if "\n" in text else super().encode(text)

    odd = Odd("abc\ndef", merges=5)
    assert tokenization.check_segments_vs_whole([[tokenization.tokenize_segment(odd, "abc"), tokenization.tokenize_segment(odd, "\n")]], odd)["mismatch_rate"] == 1.0


def test_check_b_roundtrip_and_check_c_decoder_on_random_ids_including_split_multibyte() -> None:
    tok = tiny()
    dec = tokenization.ByteDecoder(tok.token_bytes())
    texts = ["Hello world", "déjà vu – naïve", "line one\nline two", "中文 \U0001f600"]
    assert tokenization.check_roundtrip(texts, tok, dec)["failures"] == []
    core.reset_seed_record()
    seqs = tokenization.random_id_sequences(tok.vocab_size, 300, core.seeded_generator(229012, "random id sequences", "test"))
    r = tokenization.check_decoder(dec, tok, seqs)
    assert r["failures"] == [] and r["n"] == 300
    # a split multi-byte character decodes to the replacement character under both
    euro = list("€".encode())
    ids = euro[:2]  # byte tokens 0..255 are the single bytes
    assert dec.decode(ids) == tok.decode(ids) and "�" in dec.decode(ids)
    # a broken decoder is caught
    class Broken(tokenization.ByteDecoder):
        def decode(self, ids):  # type: ignore[no-untyped-def]
            return super().decode(ids).replace("�", "?")

    assert tokenization.check_decoder(Broken(tok.token_bytes()), tok, [ids])["failures"] == [0]


def test_stop_rule_and_answer_text() -> None:
    tok = tiny()
    dec = tokenization.ByteDecoder(tok.token_bytes())
    ids = tok.encode(" answer words\nnext line")
    assert dec.answer_text(ids) == " answer words"
    k = dec.stop_index(ids)
    assert k is not None and b"\n" in dec.table[ids[k]]
    assert dec.stop_index(tok.encode(" no newline here")) is None
    with pytest.raises(ValueError):
        dec.decode([10**6])


def test_bos_follows_the_reference_default() -> None:
    plain, with_bos = SyntheticTokenizer("a b c", merges=5), SyntheticTokenizer("a b c", merges=5, add_bos=True)
    assert plain.bos_id is None and with_bos.bos_id is not None
    a = tokenization.build_example(plain, "A", "a b", None, {"a": 0}, "k")
    b = tokenization.build_example(with_bos, "A", "a b", None, {"a": 0}, "k")
    assert b.ids[0] == with_bos.bos_id and len(b.ids) == len(a.ids) + 1 and b.segments[0].text == "<bos>"
    assert b.marker == len(b.ids) - 1 and all(pos >= 1 for pos, _ in b.reads)


# --- (d) and (e): the injection point and greedy decoding, against an independently written reference -------------------------------------------------
def _student_and_reference(layers: int = 3):  # type: ignore[no-untyped-def]
    cfg = StudentConfig.tiny(64, layers=layers)
    st = build_student(cfg, tgen(31, "equivalence student"))
    return st, ReferenceLlama(cfg, export_hf_state_dict(st))


def test_equivalence_record_and_gate_g8_machinery() -> None:
    st, ref = _student_and_reference()
    g = tgen(32, "equivalence inputs")
    ids = torch.randint(0, 64, (1, 12), generator=g)
    vec = torch.randn(st.cfg.width, generator=g)
    prompts = [[int(x) for x in torch.randint(0, 64, (5,), generator=g).tolist()] for _ in range(4)]
    rec = equivalence.build_record(st, ref, ids, vec, 1, prompts, 4)
    assert rec["at_creation"]["logits"]["ok"] and rec["at_creation"]["injection"]["ok"]
    v = equivalence.verify_record(st, rec)
    assert v["ok"] and v["greedy_matches_reference"] and v["cache_matches_recomputation"]
    # a perturbed weight is caught
    with torch.no_grad():
        st.blocks[0].q_proj.weight[0, 0] += 0.5
    assert not equivalence.verify_record(st, rec)["ok"]


def test_injection_index_off_by_one_is_caught() -> None:
    st, ref = _student_and_reference()
    g = tgen(33, "off-by-one inputs")
    ids = torch.randint(0, 64, (1, 10), generator=g)
    vec = torch.randn(st.cfg.width, generator=g)
    # the study's "output of block L" is hidden_states[L + 1]; a reference that injects at layer L + 1 instead disagrees
    wrong = ref.logits_with_injection(ids, 2, vec)
    st.read_layer = 1
    add = torch.zeros(1, 10, st.cfg.width)
    add[:] = vec
    mine = st(ids, add=add)
    right = ref.logits_with_injection(ids, 1, vec)
    assert equivalence.compare_logits(mine, right)["ok"] and not equivalence.compare_logits(mine, wrong)["ok"]


def test_greedy_with_cache_equals_full_recomputation() -> None:
    st, _ = _student_and_reference()
    g = tgen(34, "greedy prompts")
    for _ in range(5):
        p = torch.randint(0, 64, (1, 7), generator=g)
        assert st.greedy(p, add=None, adapter=None, max_new=6, stop_bytes=None, use_cache=True) == st.greedy(p, add=None, adapter=None, max_new=6, stop_bytes=None, use_cache=False)
