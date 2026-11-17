# ruff: noqa: E501
"""Synthetic stand-ins (tests and the dry stage only): a Tatoeba-like corpus of a made-up translation pair, teacher stand-ins, a WikiText-like text and a tiny tokenizer.

The made-up pair is word-for-word: each English word has a fixed German and a fixed French pseudo-word, so a lexical store can in principle learn it, and the teacher stand-ins are
lexicon translators with seeded noise. Nothing here is a real model, a real dataset or a result; all draws come from test-seed generators (229001-229999).
"""

from collections.abc import Sequence
from dataclasses import dataclass

import torch

from . import core
from .tokenization import SyntheticTokenizer

SYLL = ["ba", "ke", "mo", "ti", "ru", "so", "la", "ne", "pi", "do", "fu", "ga", "he", "ji", "ko", "wu", "ze", "vo", "ra", "ni"]


def pseudo_word(i: int, salt: int) -> str:
    """A deterministic pseudo-word from an index and a salt (distinct words for distinct (i, salt) in the ranges used)."""
    a, b, c = (i * 7 + salt) % 20, (i * 3 + salt * 5 + 1) % 20, (i + salt * 11) % 20
    return SYLL[a] + SYLL[b] + (SYLL[c] if i % 2 else "")


@dataclass(frozen=True)
class Corpus:
    eng: dict[int, str]
    deu: dict[int, str]
    fra: dict[int, str]
    links_de: list[tuple[int, int]]
    links_fr: list[tuple[int, int]]


def lexicon(n_words: int) -> tuple[list[str], dict[str, str], dict[str, str]]:
    en = [f"w{pseudo_word(i, 0)}" for i in range(n_words)]
    de = {w: f"d{pseudo_word(i, 3)}{i}" for i, w in enumerate(en)}
    fr = {w: f"f{pseudo_word(i, 7)}{i}" for i, w in enumerate(en)}
    return en, de, fr


def make_corpus(generator: torch.Generator, sentences: int = 1500, n_words: int = 25, link_share: float = 0.6, with_duplicates: bool = True) -> Corpus:
    """Word-for-word corpus: English sentences of 3-6 words drawn with Zipf-like weights (the last word is rare, so a closed vocabulary of ``n_words - 1`` leaves it out), a German and a
    French sentence per linked English sentence. Punctuation and capitals are varied so that normalization matters; a few sentences repeat with different case."""
    en_words, de_map, fr_map = lexicon(n_words)
    weights = torch.tensor([1.0 / (r + 1) for r in range(n_words - 1)] + [0.01])
    eng: dict[int, str] = {}
    deu: dict[int, str] = {}
    fra: dict[int, str] = {}
    links_de: list[tuple[int, int]] = []
    links_fr: list[tuple[int, int]] = []
    next_id = 1
    for n in range(sentences):
        length = 3 + int(torch.randint(0, 4, (1,), generator=generator).item())
        idx = torch.multinomial(weights, length, replacement=True, generator=generator).tolist()
        toks = [en_words[i] for i in idx]
        text = " ".join(toks)
        if with_duplicates and n % 40 == 0:
            text = text.capitalize() + "."
        eid = next_id
        next_id += 1
        eng[eid] = text
        u = torch.rand(2, generator=generator)
        for cap, mp, store, links in (("A", de_map, deu, links_de), ("B", fr_map, fra, links_fr)):
            if float(u[0 if cap == "A" else 1]) < link_share:
                tid = next_id
                next_id += 1
                store[tid] = " ".join(mp[w] for w in toks)
                links.append((eid, tid))
    return Corpus(eng, deu, fra, links_de, links_fr)


class LexiconTeacher:
    """A teacher stand-in: translates word by word with a lexicon; a seeded share of outputs is corrupted (a word dropped or replaced) and given a worse length-normalized score.
    Interface: ``translate(sources) -> [(text, normalized_log_probability)]``, ``name``, ``revision``, ``parameters``."""

    def __init__(self, name: str, lexicon_map: dict[str, str], generator: torch.Generator, corrupt: float = 0.25) -> None:
        self.name, self.revision, self.parameters = name, "synthetic", 0
        self.lexicon, self.gen, self.corrupt = lexicon_map, generator, corrupt

    def translate(self, sources: Sequence[str]) -> list[tuple[str, float]]:
        from .text import normalize

        out: list[tuple[str, float]] = []
        for s in sources:
            ws = [self.lexicon.get(w, w) for w in normalize(s).split()]
            r = torch.rand(2, generator=self.gen)
            if float(r[0]) < self.corrupt and len(ws) > 1:
                k = int(torch.randint(0, len(ws), (1,), generator=self.gen).item())
                ws = ws[:k] + ws[k + 1 :] if float(r[1]) < 0.5 else [*ws[:k], "zzz", *ws[k + 1 :]]
                score = -0.45 - 0.2 * float(r[1])
            else:
                score = -0.05 - 0.1 * float(r[1])
            out.append((" ".join(ws), score))
        return out


def make_text(generator: torch.Generator, n_words: int = 4000, marker_rate: float = 0.04) -> str:
    """A WikiText-like text: pseudo-words with some of the marker strings and lines ending in a colon."""
    en_words, _, _ = lexicon(25)
    pool = [*en_words, "The", "of", "and", "in", "to"]
    out: list[str] = []
    r = torch.rand(n_words, generator=generator)
    picks = torch.randint(0, len(pool), (n_words,), generator=generator)
    markers = ["German", "French", "English", "translation", "Germany"]
    mk = torch.randint(0, len(markers), (n_words,), generator=generator)
    for i in range(n_words):
        x = float(r[i])
        if x < marker_rate:
            out.append(markers[int(mk[i])])
        elif x < marker_rate * 1.5:
            out.append("note:\n")
        elif x > 0.97:
            out.append(pool[int(picks[i])] + "\n")
        else:
            out.append(pool[int(picks[i])])
    return " ".join(out)


def make_tokenizer(corpus: Corpus, text: str, merges: int = 60, add_bos: bool = False) -> SyntheticTokenizer:
    sample = " ".join(list(corpus.eng.values())[:200]) + " English: German: French:\n" + " ".join(list(corpus.deu.values())[:100]) + " " + " ".join(list(corpus.fra.values())[:100]) + " " + text[:3000]
    return SyntheticTokenizer(sample, merges=merges, add_bos=add_bos)


def tgen(offset: int, purpose: str = "synthetic") -> torch.Generator:
    """A generator on a test seed (229001-229999)."""
    return core.seeded_generator(core.SEEDS["test_low"] + 500 + offset, purpose, "test")
