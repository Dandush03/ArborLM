# ruff: noqa: E501
"""The amended R-gloss-icl segment rule (ADR-0025 addendum, attempt 3, section 3) on line boundaries followed by a digit, a letter, punctuation and a repeated word, with NO data: a toy tokenizer that reproduces the
mechanism of the stop of attempt 2 (a newline and the following space fuse into one token when the next character is a digit, which separately stored segments cannot reproduce). The invariant is the test: for every
prompt, the concatenation of the stored segments equals the tokenization of the whole string. Self-check only."""

import re
import sys
from collections.abc import Sequence
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from studies.p10is2.partq import gloss  # noqa: E402
from studies.p10is2.partq.gloss import SEPARATOR  # noqa: E402
from studies.p10s2.data import TrainItem  # noqa: E402

PRE = re.compile(r"\n (?=\d)|\n|\s?\d|\s?[A-Za-z]+|\s?[^\sA-Za-z\d]+|\s")


class ToyTok:
    """A pre-tokenizer in the manner of the student's: digits are isolated, and the whitespace before a digit is its own pre-token, so ``"\\n "`` before a digit is ONE token; before a letter the newline stays alone
    and the space joins the word. ``fuse_english`` also fuses a newline with a following ``E`` (to exercise the other branch of the last-newline rule)."""

    bos_id = None
    vocab_size = 10**6

    def __init__(self, fuse_english: bool = False) -> None:
        self.table: dict[str, int] = {}
        self.pre = re.compile(r"\nE(?=nglish)|" + PRE.pattern) if fuse_english else PRE

    def _id(self, tok: str) -> int:
        return self.table.setdefault(tok, len(self.table))

    def encode_offsets(self, text: str) -> tuple[list[int], list[tuple[int, int]]]:
        ids, offs = [], []
        for m in self.pre.finditer(text):
            ids.append(self._id(m.group()))
            offs.append((m.start(), m.end()))
        return ids, offs

    def encode(self, text: str) -> list[int]:
        return self.encode_offsets(text)[0]

    def decode(self, ids: Sequence[int]) -> str:
        inv = {v: k for k, v in self.table.items()}
        return "".join(inv[i] for i in ids)

    def token_bytes(self) -> list[bytes]:
        return [k.encode() for k in self.table]


WORDS = ["alpha", "230", "beta", "?!", "alpha", "9th", "gamma"]  # a letter, a digit, a letter, punctuation, a REPEATED word, a digit again, a letter
LEXICON = {w: "gl" for w in WORDS}
POOL = {"A": [TrainItem("k", "alpha", "gl", 0)], "B": [TrainItem("k", "alpha", "gl", 0)]}


def item(*words: str) -> SimpleNamespace:
    return SimpleNamespace(key=" ".join(words), en=" ".join(words))


def old_rule_ids(tok: ToyTok, lines: Sequence[tuple[str, str]]) -> list[int]:
    """The rule of attempt 2: every line is the source word's segment, the separator, the gloss word's segment and a newline segment."""
    ids: list[int] = []
    for w, g in lines:
        ids += [*tok.encode(" " + w), *tok.encode(SEPARATOR), *tok.encode(" " + g), *tok.encode("\n")]
    return ids + tok.encode(gloss.TASK_FIRST_PIECE)


def bank_for(tok: ToyTok) -> dict:  # type: ignore[type-arg]
    items = [item(*WORDS)]
    pieces = gloss.first_task_pieces(tok, {"A": items})
    return gloss.gloss_bank(tok, POOL, sorted(set(WORDS)), pieces)


def test_the_old_rule_fails_on_a_digit_after_a_newline_and_passes_before_a_letter() -> None:
    tok = ToyTok()
    assert tok.encode("\n 230") != tok.encode("\n") + tok.encode(" 230")  # the mechanism of attempt 2
    assert tok.encode("\n alpha") == tok.encode("\n") + tok.encode(" alpha")
    lines = [("alpha", "gl"), ("230", "gl")]
    whole = tok.encode(gloss.icl_prompt_text(lines) + gloss.TASK_FIRST_PIECE)
    assert old_rule_ids(tok, lines) != whole  # the old segments cannot reproduce the whole string
    assert old_rule_ids(tok, [("alpha", "gl"), ("beta", "gl")]) == tok.encode(gloss.icl_prompt_text([("alpha", "gl"), ("beta", "gl")]) + gloss.TASK_FIRST_PIECE)  # a letter after the newline was fine


def test_the_amended_rule_reproduces_the_whole_string_after_a_digit_a_letter_punctuation_and_a_repeated_word() -> None:
    tok = ToyTok()
    bank = bank_for(tok)
    for words in (WORDS, ["230", "alpha"], ["alpha", "230"], ["alpha", "?!", "alpha", "alpha"], ["230", "230", "9th"], ["gamma"], ["?!", "230"], ["9th"]):
        lines = gloss.icl_lines(" ".join(words), LEXICON, set(WORDS))
        ids = gloss.icl_prompt_ids(lines, bank, "A") + tok.encode(gloss.TASK_FIRST_PIECE)
        assert ids == tok.encode(gloss.icl_prompt_text(lines) + gloss.TASK_FIRST_PIECE), words  # the invariant: segments == whole string
    res = gloss.tokenization_test_a(tok, [item(*WORDS), item("230", "alpha"), item("alpha", "?!", "alpha")], LEXICON, set(WORDS), "A", bank)
    assert res["mismatches"] == 0 and res["checked"] == 3


def test_the_later_lines_carry_the_newline_with_their_source_word_and_the_first_line_does_not() -> None:
    tok = ToyTok()
    bank = bank_for(tok)
    assert bank["source_words"]["230"] == tok.encode(" 230") and bank["source_words_after_newline"]["230"] == tok.encode("\n 230")
    lines = [("alpha", "gl"), ("230", "gl")]
    ids = gloss.icl_prompt_ids(lines, bank, "A")
    assert ids[: len(bank["source_words"]["alpha"])] == bank["source_words"]["alpha"] and bank["source_words_after_newline"]["230"] == ids[len(ids) - len(bank["newline"]) - len(bank["words"]["A"]["gl"]) - len(bank["separator"]) - len(bank["source_words_after_newline"]["230"]) : len(ids) - len(bank["newline"]) - len(bank["words"]["A"]["gl"]) - len(bank["separator"])]
    assert bank["segment_rule"] == gloss.SEGMENT_RULE


def test_the_last_newline_is_decided_from_the_tokenizer_alone_and_recorded() -> None:
    tok = ToyTok()
    assert bank_for(tok)["last_newline"]["rule"] == "own-segment" and gloss.first_task_pieces(tok, {"A": [item("alpha")], "B": [item("230")]}) == ["English:"]
    fused = ToyTok(fuse_english=True)
    bank = bank_for(fused)
    assert bank["last_newline"]["rule"] == "fused-with-first-task-piece" and bank["last_newline"]["fused_ids"] == fused.encode("\nEnglish:")
    res = gloss.tokenization_test_a(fused, [item(*WORDS), item("alpha", "230")], LEXICON, set(WORDS), "A", bank)
    assert res["mismatches"] == 0  # the fused branch also reproduces the whole string


def test_part_t_builds_the_same_ids_from_the_bank_in_both_branches() -> None:
    from studies.p10is2.scoring import gloss_icl_ids

    for tok in (ToyTok(), ToyTok(fuse_english=True)):
        bank = bank_for(tok)
        query = SimpleNamespace(prompt_ids=tok.encode("English:") + tok.encode(" alpha"))
        got = gloss_icl_ids("alpha 230", query, LEXICON, set(WORDS), bank, "A", 0)
        lines = gloss.icl_lines("alpha 230", LEXICON, set(WORDS))
        assert got == tok.encode(gloss.icl_prompt_text(lines) + "English: alpha")
        assert gloss_icl_ids("unknown", query, LEXICON, set(WORDS), bank, "A", 0) == list(query.prompt_ids)  # no line: the task prompt alone
