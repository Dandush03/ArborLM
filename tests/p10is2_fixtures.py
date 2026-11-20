# ruff: noqa: E501
"""Synthetic fixtures of the P10IS2 tests: a word-for-word corpus, fake teachers and a stub student. No package outside the lock, no real data, no real model. Seeds: 934001-934999 only."""

import sys
from collections.abc import Sequence
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from studies.p10is2.common import core  # noqa: E402
from studies.p10is2.partq.teacher import FakeTeacher  # noqa: E402
from studies.p10s2.synthetic import lexicon, make_corpus  # noqa: E402
from studies.p10s2.text import chrf_item, normalize  # noqa: E402

CFG_Q = core.load_config("Q")
CFG_T = core.load_config("T")
TEST_ALLOWED = core.test_range(CFG_Q)


def test_gen(k: int):  # type: ignore[no-untyped-def]
    return core.seeded_generator(int(CFG_Q["seeds"]["test_low"]) + 900 + k, "unit test", TEST_ALLOWED)


def small_corpus(sentences: int = 3000, n_words: int = 25, link_share: float = 0.7):  # type: ignore[no-untyped-def]
    return make_corpus(test_gen(1), sentences=sentences, n_words=n_words, link_share=link_share)


class LexTeacher(FakeTeacher):
    """A FakeTeacher that translates word for word with the synthetic lexicon of its own language (so its output scores well on its own capability), damaging a share of the outputs."""

    def __init__(self, name: str, mapping: dict[str, str], **kw) -> None:  # type: ignore[no-untyped-def]
        super().__init__(name, **kw)
        self.mapping = mapping

    def generate_batch(self, sources: Sequence[str]):  # type: ignore[no-untyped-def]
        from studies.p10is2.partq.teacher import Generated

        base = super().generate_batch(sources)
        out = []
        for s, g in zip(sources, base, strict=True):
            words = normalize(s).split()
            damaged = len(g.tokens) < len(words)
            kept = words[1:] if damaged else words
            text = " ".join(self.mapping.get(w, w) for w in kept)
            out.append(Generated(g.tokens, text, g.score))
        return out


def lex_teachers(**kw):  # type: ignore[no-untyped-def]
    _, de, fr = lexicon(25)
    return {"A": LexTeacher("A", de, **kw), "B": LexTeacher("B", fr, **kw)}


def stub_student(items, p=None, caps=("A", "B")):  # type: ignore[no-untyped-def]
    """The untrained student copies the English: low chrF against any reference."""
    return {c: sum(chrf_item(i.en, i.refs[c]) for i in items) / max(1, len(items)) for c in caps}


SMALL_SIZES = {"q_fit": 120, "q_check_block": 40, "q_check_blocks_max": 6, "d_cal": 20, "d_con": 10, "e_eval": 30, "e_eval_min": 10, "e_combined": 15, "e_combined_min": 5, "e_open": 5, "gen_ordinary": 4}


def small_cfg(**quality):  # type: ignore[no-untyped-def]
    """The Part Q config with the count thresholds scaled down for synthetic data (tests only; the registered values are asserted in test_p10is2_config.py)."""
    import copy

    cfg = copy.deepcopy(CFG_Q)
    cfg["quality"]["q4_min_accepted"] = quality.get("q4_min_accepted", 10)
    return cfg
