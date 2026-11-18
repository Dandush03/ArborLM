# ruff: noqa: E501
"""Gloss word token ids for R-gloss-icl (ADR-0025 section 4.1 step 8 and section 5.2).

At Part Q the token ids of every target-language word type of each capability's accepted pool are stored, each word as its own segment with a leading space, together with the separator segment (" =") and
the newline segment of R-gloss-icl's template. With these in the bank Part T encodes no text and needs no tokenizer and no package outside the lock.

Template. Before the task prompt that S0 receives, unchanged, one line per in-vocabulary source word that has an entry in the replicate's lexicon, in source order, repeated words included: the source word,
the separator " =", the top gloss word, a newline. A word with no entry gives no line. The prompt is a concatenation of stored segments only. Tokenization test (a) of ADR-0022 section 14.2 is run at Part Q on
the R-gloss-icl prompts of every E_A, E_B and D_cal item with a lexicon built from the whole accepted pool; zero mismatches are required.
"""

from collections.abc import Mapping, Sequence
from typing import Any

from studies.p10s2.data import Item, TrainItem
from studies.p10s2.retrieval import gloss_lexicon
from studies.p10s2.text import normalize
from studies.p10s2.tokenization import (
    NEWLINE,
    ReferenceTokenizer,
    prompt_segments,
    tokenize_segment,
)

SEPARATOR = " ="


def word_types(pool: Sequence[TrainItem]) -> list[str]:
    """Every target-language word type of an accepted pool (normalized words of the outputs), sorted."""
    return sorted({w for x in pool for w in normalize(x.target).split()})


def gloss_bank(tok: ReferenceTokenizer, pools: Mapping[str, Sequence[TrainItem]], vocab: Sequence[str] = ()) -> dict[str, Any]:
    """The stored token ids: per capability ``{word: ids}`` (the segment ``" " + word``), the source words of the closed vocabulary the same way (``source_words``: the source word's segment of the template), plus the separator and the newline segments."""
    return {
        "words": {c: {w: list(tokenize_segment(tok, " " + w).ids) for w in word_types(pool)} for c, pool in pools.items()},
        "source_words": {w: list(tokenize_segment(tok, " " + w).ids) for w in vocab}, "separator": list(tokenize_segment(tok, SEPARATOR).ids), "newline": list(tokenize_segment(tok, NEWLINE).ids),
    }  # fmt: skip


def icl_lines(source: str, lexicon: Mapping[str, str], in_vocab: Mapping[str, int] | set[str]) -> list[tuple[str, str]]:
    """(source word, top gloss word) for every in-vocabulary source word with a lexicon entry, in source order, repeats included."""
    return [(w, lexicon[w]) for w in normalize(source).split() if w in in_vocab and w in lexicon]


def icl_prompt_text(lines: Sequence[tuple[str, str]]) -> str:
    """One line per pair: the source word (leading space, as every word segment of the bank), the separator, the gloss word (leading space), a newline. READING: the ADR does not say whether the source
    word's segment has a leading space; the bank's convention (``prompt_segments`` tokenizes ``" " + source``) is followed and the question is listed."""
    return "".join(f" {w}{SEPARATOR} {g}{NEWLINE}" for w, g in lines)


def icl_prompt_ids(lines: Sequence[tuple[str, str]], source_word_ids: Mapping[str, Sequence[int]], bank: Mapping[str, Any], capability: str) -> list[int]:
    """The ids of the lines, from stored segments only: the source word's segment from the ADR-0022 bank, the separator segment, the gloss word's segment stored at Part Q, the newline segment. No tokenizer."""
    ids: list[int] = []
    for w, g in lines:
        ids += [*source_word_ids[w], *bank["separator"], *bank["words"][capability][g], *bank["newline"]]
    return ids


def tokenization_test_a(tok: ReferenceTokenizer, items: Sequence[Item], lexicon: Mapping[str, str], in_vocab: set[str], capability: str, bank: Mapping[str, Any]) -> dict[str, Any]:
    """Test (a) on R-gloss-icl prompts: the segment-wise ids equal the ids of the whole text, for every item. Every word segment, source and gloss, carries a leading space (reading, see ``icl_prompt_text``).
    Returns the count of mismatches (zero is required) and the first few."""
    mism: list[dict[str, Any]] = []
    for it in items:
        lines = icl_lines(it.en, lexicon, in_vocab)
        text = icl_prompt_text(lines)
        # the whole-text ids: the prompt is the concatenation of independent segments, so the whole is the concatenation of the segments' own ids (test (a): segments vs whole)
        seg_ids = icl_prompt_ids(lines, {w: tok.encode(" " + w) for w, _ in lines}, bank, capability)
        whole: list[int] = tok.encode(text) if text else []
        # a prompt with no line has no ids at all; the task prompt follows unchanged
        if seg_ids != whole:
            mism.append({"key": it.key, "segments": seg_ids[:20], "whole": whole[:20]})
    return {"checked": len(items), "mismatches": len(mism), "first": mism[:3]}


__all__ = ["SEPARATOR", "gloss_bank", "gloss_lexicon", "icl_lines", "icl_prompt_ids", "icl_prompt_text", "prompt_segments", "tokenization_test_a", "word_types"]
