# ruff: noqa: E501
"""Gloss word token ids for R-gloss-icl (ADR-0025 section 4.1 step 8 and section 5.2).

At Part Q the token ids of every target-language word type of each capability's accepted pool are stored, each word as its own segment with a leading space, together with the separator segment (" =") and
the newline segment of R-gloss-icl's template (and, under the amended rule of the attempt-3 addendum, each source word also in the form that carries the newline before it). With these in the bank Part T encodes no text and needs no tokenizer and no package outside the lock.

Template. Before the task prompt that S0 receives, unchanged, one line per in-vocabulary source word that has an entry in the replicate's lexicon, in source order, repeated words included: the source word,
the separator " =", the top gloss word, a newline. A word with no entry gives no line. The prompt is a concatenation of stored segments only, cut by the amended rule of ADR-0025's attempt-3 addendum section 3 (``icl_prompt_ids``). Tokenization test (a) of ADR-0022 section 14.2 is run at Part Q on
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


SEGMENT_RULE = "gloss-lines-v2: ADR-0025 addendum (attempt 3) section 3"
TASK_FIRST_PIECE = "English:"  # the first piece of the task prompt that follows the gloss lines (``tokenization.prompt_segments``), after the optional BOS


def first_task_pieces(tok: ReferenceTokenizer, items_by_task: Mapping[str, Sequence[Item]]) -> list[str]:
    """The text of the first stored piece (after any BOS) of the task prompt of every item, as ``prompt_segments`` builds it: the distinct values, from the tokenizer and the items alone."""
    seen: set[str] = set()
    for task, items in items_by_task.items():
        for it in items:
            segs = prompt_segments(tok, task, it.en)
            seen.add(next(s.text for s in segs if s.text != "<bos>"))
    return sorted(seen)


def last_newline_rule(tok: ReferenceTokenizer, pieces: Sequence[str]) -> dict[str, Any]:
    """Addendum section 3, the newline that ends the LAST gloss line: kept as its own segment if, for the first piece of the task prompt of every item, tokenizing the newline and the piece in one call gives exactly
    the newline's ids followed by the piece's ids; otherwise stored together with that first piece (which must then be one and the same piece for all items). Decided from the tokenizer alone, before any teacher
    output is read, and recorded in the bank."""
    nl = list(tok.encode(NEWLINE))
    fused = [p for p in pieces if list(tok.encode(NEWLINE + p)) != nl + list(tok.encode(p))]
    if not fused:
        return {"rule": "own-segment", "pieces_checked": list(pieces)}
    if len(pieces) != 1:
        raise ValueError(f"the newline fuses with the first task piece of some items but the pieces differ ({list(pieces)}): the rule cannot store one fused segment")
    piece = pieces[0]
    return {"rule": "fused-with-first-task-piece", "pieces_checked": list(pieces), "first_task_piece_ids": list(tok.encode(piece)), "fused_ids": list(tok.encode(NEWLINE + piece))}


def gloss_bank(tok: ReferenceTokenizer, pools: Mapping[str, Sequence[TrainItem]], vocab: Sequence[str] = (), pieces: Sequence[str] = (TASK_FIRST_PIECE,)) -> dict[str, Any]:
    """The stored token ids: per capability ``{word: ids}`` (the segment ``" " + word``), the source words of the closed vocabulary in the two forms of the amended rule (``source_words``: ``" " + word``, for the FIRST
    gloss line; ``source_words_after_newline``: the tokenization of ``"\\n" + " " + word`` in ONE call, for every LATER line), the separator and the newline segments, and the recorded decision for the last newline."""
    return {
        "segment_rule": SEGMENT_RULE,
        "words": {c: {w: list(tokenize_segment(tok, " " + w).ids) for w in word_types(pool)} for c, pool in pools.items()},
        "source_words": {w: list(tokenize_segment(tok, " " + w).ids) for w in vocab},
        "source_words_after_newline": {w: list(tokenize_segment(tok, NEWLINE + " " + w).ids) for w in vocab},
        "separator": list(tokenize_segment(tok, SEPARATOR).ids), "newline": list(tokenize_segment(tok, NEWLINE).ids), "last_newline": last_newline_rule(tok, pieces),
    }  # fmt: skip


def icl_lines(source: str, lexicon: Mapping[str, str], in_vocab: Mapping[str, int] | set[str]) -> list[tuple[str, str]]:
    """(source word, top gloss word) for every in-vocabulary source word with a lexicon entry, in source order, repeats included."""
    return [(w, lexicon[w]) for w in normalize(source).split() if w in in_vocab and w in lexicon]


def icl_prompt_text(lines: Sequence[tuple[str, str]]) -> str:
    """One line per pair: the source word (leading space, as every word segment of the bank), the separator, the gloss word (leading space), a newline. READING: the ADR does not say whether the source
    word's segment has a leading space; the bank's convention (``prompt_segments`` tokenizes ``" " + source``) is followed and the question is listed."""
    return "".join(f" {w}{SEPARATOR} {g}{NEWLINE}" for w, g in lines)


def icl_prompt_ids(lines: Sequence[tuple[str, str]], bank: Mapping[str, Any], capability: str) -> list[int]:
    """The ids of the gloss lines and of everything up to and including the first piece of the task prompt, from stored segments only (the amended rule): the FIRST line is the source word's segment, the
    separator segment, the gloss word's segment; every LATER line begins with the stored segment of the previous line's newline together with that line's source word; the last newline is its own segment
    followed by the task prompt's first piece, or fused with that piece, as the bank's ``last_newline`` records. No tokenizer. Returns [] for a prompt with no line."""
    ids: list[int] = []
    for i, (w, g) in enumerate(lines):
        ids += bank["source_words"][w] if i == 0 else bank["source_words_after_newline"][w]
        ids += [*bank["separator"], *bank["words"][capability][g]]
    if not lines:
        return ids
    ln = bank["last_newline"]
    if ln["rule"] == "own-segment":
        ids += bank["newline"]  # the task prompt's first piece follows as its own stored segment (the caller adds it)
    else:
        ids += ln["fused_ids"]
    return ids


def tokenization_test_a(tok: ReferenceTokenizer, items: Sequence[Item], lexicon: Mapping[str, str], in_vocab: set[str], capability: str, bank: Mapping[str, Any]) -> dict[str, Any]:
    """Test (a) on R-gloss-icl prompts, unchanged in what it requires: the concatenation of the stored segments equals the tokenization of the whole prompt string, for every item. The whole string is the gloss
    lines followed by the first piece of the task prompt (``TASK_FIRST_PIECE``), so that the last newline's rule is tested too. Returns the count of mismatches (zero is required) and the first few."""
    mism: list[dict[str, Any]] = []
    own = bank["last_newline"]["rule"] == "own-segment"
    first_piece_ids = list(tok.encode(TASK_FIRST_PIECE))
    for it in items:
        lines = icl_lines(it.en, lexicon, in_vocab)
        if not lines:
            continue  # a prompt with no line has no ids at all; the task prompt follows unchanged
        seg_ids = icl_prompt_ids(lines, bank, capability) + (first_piece_ids if own else [])
        whole: list[int] = list(tok.encode(icl_prompt_text(lines) + TASK_FIRST_PIECE))
        if seg_ids != whole:
            mism.append({"key": it.key, "segments": seg_ids[:20], "whole": whole[:20]})
    return {"checked": len(items), "mismatches": len(mism), "first": mism[:3]}


__all__ = ["SEGMENT_RULE", "SEPARATOR", "TASK_FIRST_PIECE", "first_task_pieces", "last_newline_rule", "gloss_bank", "gloss_lexicon", "icl_lines", "icl_prompt_ids", "icl_prompt_text", "prompt_segments", "tokenization_test_a", "word_types"]
