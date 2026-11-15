# ruff: noqa: E501
"""Tokenization record format, segment-level conventions and the pure-Python decoder (ADR-0022 sections 2 and 14.2 step 4).

The registered path never encodes text. The data-generation step tokenizes each *segment* the study uses with the reference tokenizer and stores the ids; a model input is the
concatenation of segment ids. This module holds:

* ``ReferenceTokenizer``: the interface the data-generation step needs from the reference tokenizer (the real one is ``transformers``/``tokenizers``, used only there);
* ``SyntheticTokenizer``: a tiny deterministic byte-level BPE stand-in with the same interface (tests and the dry stage);
* ``ByteDecoder``: the study's byte-level decoder, over whole sequences, with the reference's error policy (replacement);
* the prompt and target segment layout of section 5.4, and the records the data-generation step writes (``Example`` and its JSON form);
* the checks (a), (b), (c) of section 14.2 step 4 as functions of a tokenizer (the checks (d) and (e) need the student and are in ``equivalence``).

Segment convention (section 14.2 step 4; the points the ADR leaves open are listed in the report): each segment is tokenized with its leading space where whole-string tokenization
would attach one; the newline separators are their own segments; raw NFC text is tokenized (normalization is used only for identity and chrF); BOS follows the reference tokenizer's
default for this model, recorded in the record header (the draft expects "not prepended"); the position of the last subword of each in-vocabulary source word comes from the
reference tokenizer's offsets and is stored, never recomputed.
"""

import codecs
import unicodedata
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol

import torch

from arborlm.io import canonical_json, sha256

from .text import normalize

NEWLINE = "\n"
TASK_WORD = {"A": "German", "B": "French"}


class ReferenceTokenizer(Protocol):
    """What the data-generation step needs from the reference tokenizer."""

    vocab_size: int
    bos_id: int | None  # the reference default for this model; None if it is not prepended

    def encode(self, text: str) -> list[int]: ...
    def encode_offsets(self, text: str) -> tuple[list[int], list[tuple[int, int]]]: ...
    def decode(self, ids: Sequence[int]) -> str: ...
    def token_bytes(self) -> list[bytes]: ...


# --- the study's decoder ----------------------------------------------------------------------------------------------------------------------
class ByteDecoder:
    """Pure-Python byte-level decoder. ``decode`` works on whole sequences (never token by token) and uses the reference's error policy: invalid UTF-8 becomes U+FFFD. ``stop_index``
    is the stop rule of the registered path: the first generated token whose bytes contain 0x0A."""

    def __init__(self, token_bytes: Sequence[bytes]) -> None:
        self.table = list(token_bytes)

    def bytes_of(self, ids: Sequence[int]) -> bytes:
        for i in ids:
            if not 0 <= i < len(self.table):
                raise ValueError(f"token id {i} is outside the table of {len(self.table)}")
        return b"".join(self.table[i] for i in ids)

    def decode(self, ids: Sequence[int]) -> str:
        return self.bytes_of(ids).decode("utf-8", errors="replace")

    def stop_index(self, ids: Sequence[int]) -> int | None:
        for k, i in enumerate(ids):
            if b"\n" in self.table[i]:
                return k
        return None

    def answer_text(self, generated: Sequence[int]) -> str:
        """The answer: the whole generated sequence decoded, cut at the first newline."""
        return self.decode(generated).split("\n", 1)[0]


# --- the synthetic stand-in ------------------------------------------------------------------------------------------------------------------
class SyntheticTokenizer:
    """Byte-level BPE with ``merges`` learned deterministically from a text sample (the most frequent pair first, ties to the smaller pair). 256 byte tokens, then one token per merge.
    ``bos_id`` is None unless ``add_bos`` is set (then the token after the merges). Same interface as the reference tokenizer."""

    def __init__(self, sample: str, merges: int = 64, add_bos: bool = False) -> None:
        self._token_bytes: list[bytes] = [bytes([i]) for i in range(256)]
        words = Counter(tuple(bytes([b]) for b in w.encode("utf-8")) for w in sample.replace("\n", " \n ").split(" ") if w)
        self.merge_rank: dict[tuple[bytes, bytes], int] = {}
        word_seqs = {w: c for w, c in words.items()}
        for _ in range(merges):
            pairs: Counter[tuple[bytes, bytes]] = Counter()
            for w, c in word_seqs.items():
                for a, b in zip(w, w[1:], strict=False):
                    pairs[(a, b)] += c
            if not pairs:
                break
            best = min(pairs, key=lambda p: (-pairs[p], p))
            self.merge_rank[best] = len(self.merge_rank)
            self._token_bytes.append(best[0] + best[1])
            new: Counter[tuple[bytes, ...]] = Counter()
            for w, c in word_seqs.items():
                new[self._merge_word(w, best)] += c
            word_seqs = dict(new)
        self._index = {b: i for i, b in enumerate(self._token_bytes)}
        self.bos_id: int | None = len(self._token_bytes) if add_bos else None
        if add_bos:
            self._token_bytes.append(b"<bos>")
        self.vocab_size = len(self._token_bytes)

    @staticmethod
    def _merge_word(w: tuple[bytes, ...], pair: tuple[bytes, bytes]) -> tuple[bytes, ...]:
        out: list[bytes] = []
        i = 0
        while i < len(w):
            if i + 1 < len(w) and (w[i], w[i + 1]) == pair:
                out.append(pair[0] + pair[1])
                i += 2
            else:
                out.append(w[i])
                i += 1
        return tuple(out)

    def _pieces(self, text: str) -> list[bytes]:
        """BPE over the whole text, pre-split at spaces (a space starts a word, as GPT-2 style tokenizers do) and at newlines (a newline is its own word)."""
        data = text.encode("utf-8")
        chunks: list[bytes] = []
        cur = b""
        for b in data:
            if b == 0x0A:
                if cur:
                    chunks.append(cur)
                chunks.append(b"\n")
                cur = b""
            elif b == 0x20 and cur and cur != b" ":
                chunks.append(cur)
                cur = b" "
            else:
                cur += bytes([b])
        if cur:
            chunks.append(cur)
        out: list[bytes] = []
        for ch in chunks:
            seq = tuple(bytes([b]) for b in ch)
            while len(seq) > 1:
                ranked = [(self.merge_rank[p], p) for p in zip(seq, seq[1:], strict=False) if p in self.merge_rank]
                if not ranked:
                    break
                seq = self._merge_word(seq, min(ranked)[1])
            out.extend(seq)
        return out

    def encode(self, text: str) -> list[int]:
        return [self._index[p] for p in self._pieces(text)]

    def encode_offsets(self, text: str) -> tuple[list[int], list[tuple[int, int]]]:
        pieces = self._pieces(text)
        char_of_byte: list[int] = []
        for ci, ch in enumerate(text):
            char_of_byte.extend([ci] * len(ch.encode("utf-8")))
        ids, offs, pos = [], [], 0
        for p in pieces:
            ids.append(self._index[p])
            offs.append((char_of_byte[pos], char_of_byte[pos + len(p) - 1] + 1))
            pos += len(p)
        return ids, offs

    def decode(self, ids: Sequence[int]) -> str:
        """Reference decode, by a different code path than ``ByteDecoder``: an incremental UTF-8 decoder fed byte by byte (replacement policy)."""
        dec = codecs.getincrementaldecoder("utf-8")(errors="replace")
        out: list[str] = []
        for i in ids:
            for b in self._token_bytes[i]:
                out.append(dec.decode(bytes([b])))
        out.append(dec.decode(b"", final=True))
        return "".join(out)

    def token_bytes(self) -> list[bytes]:
        return list(self._token_bytes)


# --- segments, examples and the data-generation record -----------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Segment:
    """One separately tokenized text segment. ``word_last`` holds, for a source segment, ``(index of the last subword within the segment, normalized word)`` for each source word."""

    text: str
    ids: tuple[int, ...]
    word_last: tuple[tuple[int, str], ...] = ()

    def to_json(self) -> dict[str, Any]:
        return {"text": self.text, "ids": list(self.ids), "word_last": [[i, w] for i, w in self.word_last]}

    @staticmethod
    def from_json(obj: Mapping[str, Any]) -> "Segment":
        return Segment(str(obj["text"]), tuple(int(i) for i in obj["ids"]), tuple((int(i), str(w)) for i, w in obj.get("word_last", [])))


def tokenize_segment(tok: ReferenceTokenizer, text: str, *, with_words: bool = False) -> Segment:
    """Tokenize one segment. For a source segment (``with_words``) the last subword of each whitespace-delimited word is found from the tokenizer's character offsets."""
    if not with_words:
        return Segment(text, tuple(tok.encode(text)))
    ids, offs = tok.encode_offsets(text)
    out: list[tuple[int, str]] = []
    pos = 0
    for raw in text.split():
        start = text.index(raw, pos)
        end = start + len(raw)
        pos = end
        norm = normalize(raw)
        if not norm:
            continue
        last = max((k for k, (s, _e) in enumerate(offs) if s < end), default=None)
        if last is not None:
            out.append((last, norm))
    return Segment(text, tuple(ids), tuple(out))


def prompt_segments(tok: ReferenceTokenizer, task: str, source: str) -> list[Segment]:
    """``English: {source}\\n{German|French}:`` as segments: the label, the source (leading space), the newline, the task marker."""
    segs: list[Segment] = []
    if tok.bos_id is not None:
        segs.append(Segment("<bos>", (tok.bos_id,)))
    segs.append(tokenize_segment(tok, "English:"))
    segs.append(tokenize_segment(tok, " " + source, with_words=True))
    segs.append(tokenize_segment(tok, NEWLINE))
    segs.append(tokenize_segment(tok, TASK_WORD[task] + ":"))
    return segs


def target_segments(tok: ReferenceTokenizer, target: str) -> list[Segment]:
    """The translation (leading space) and a newline."""
    return [tokenize_segment(tok, " " + target), tokenize_segment(tok, NEWLINE)]


@dataclass(frozen=True)
class Example:
    """A model input built from segment ids. ``reads`` are ``(position, vocabulary index j)`` for each in-vocabulary source word, ``marker`` the position of the last token of the task
    marker. ``target_len`` is 0 for an evaluation prompt. ``segments`` keeps the text pieces for hashing and for the whole-string check (a)."""

    key: str
    task: str
    ids: tuple[int, ...]
    prompt_len: int
    reads: tuple[tuple[int, int], ...]
    marker: int
    target_len: int
    segments: tuple[Segment, ...] = field(default=(), compare=False)

    @property
    def prompt_ids(self) -> tuple[int, ...]:
        return self.ids[: self.prompt_len]

    def to_json(self) -> dict[str, Any]:
        return {"key": self.key, "task": self.task, "segments": [s.to_json() for s in self.segments], "prompt_segments": self.prompt_len_segments(), "reads": [list(r) for r in self.reads], "marker": self.marker}

    def prompt_len_segments(self) -> int:
        n, acc = 0, 0
        for s in self.segments:
            if acc >= self.prompt_len:
                break
            acc += len(s.ids)
            n += 1
        return n


def build_example(
    tok: ReferenceTokenizer, task: str, source: str, target: str | None, vocab_index: Mapping[str, int], key: str
) -> Example:
    """Build an example from the reference tokenizer (data-generation side). The vocabulary table maps a normalized word to its index j; out-of-vocabulary words are never read."""
    segs = prompt_segments(tok, task, source)
    prompt_len = sum(len(s.ids) for s in segs)
    reads: list[tuple[int, int]] = []
    off = 0
    for s in segs:
        for last, word in s.word_last:
            if word in vocab_index:
                reads.append((off + last, vocab_index[word]))
        off += len(s.ids)
    marker = prompt_len - 1
    if target is not None:
        segs = [*segs, *target_segments(tok, target)]
    ids = tuple(i for s in segs for i in s.ids)
    return Example(key, task, ids, prompt_len, tuple(reads), marker, len(ids) - prompt_len, tuple(segs))


def example_from_json(obj: Mapping[str, Any], vocab_index: Mapping[str, int]) -> Example:
    """Rebuild an example from its stored record, without any tokenizer: ids are the concatenation of the stored segment ids, the read positions from the stored last-subword indices."""
    segs = tuple(Segment.from_json(s) for s in obj["segments"])
    n_prompt = int(obj["prompt_segments"])
    prompt_len = sum(len(s.ids) for s in segs[:n_prompt])
    reads: list[tuple[int, int]] = []
    off = 0
    for s in segs[:n_prompt]:
        for last, word in s.word_last:
            if word in vocab_index:
                reads.append((off + last, vocab_index[word]))
        off += len(s.ids)
    ids = tuple(i for s in segs for i in s.ids)
    return Example(str(obj["key"]), str(obj["task"]), ids, prompt_len, tuple(reads), prompt_len - 1, len(ids) - prompt_len, segs)


def record_hash(records: Sequence[Mapping[str, Any]]) -> str:
    return sha256(canonical_json(list(records)))


# --- checks (a), (b), (c) of section 14.2 step 4 ---------------------------------------------------------------------------------------------------
def check_segments_vs_whole(inputs: Sequence[Sequence[Segment]], tok: ReferenceTokenizer) -> dict[str, Any]:
    """(a) segment ids against whole-string ids, for every input given. Returns the mismatch rate and the mismatching indices. The ADR requires 0 on prompts and lists target
    mismatches; the training loss uses the segment ids either way."""
    bad: list[int] = []
    for n, segs in enumerate(inputs):
        text_segs = [s for s in segs if s.text != "<bos>"]
        whole = tok.encode("".join(s.text for s in text_segs))
        parts = [i for s in text_segs for i in s.ids]
        if whole != parts:
            bad.append(n)
    return {"n": len(inputs), "mismatches": bad, "mismatch_rate": len(bad) / len(inputs) if inputs else 0.0}


def check_roundtrip(texts: Sequence[str], tok: ReferenceTokenizer, decoder: ByteDecoder) -> dict[str, Any]:
    """(b) ``decode(encode(x)) == x`` for every text, by the study's decoder and by the reference's."""
    bad = [n for n, t in enumerate(texts) if decoder.decode(tok.encode(unicodedata.normalize("NFC", t))) != unicodedata.normalize("NFC", t) or tok.decode(tok.encode(t)) != t]
    return {"n": len(texts), "failures": bad}


def random_id_sequences(vocab: int, count: int, generator: torch.Generator, max_len: int = 24) -> list[list[int]]:
    seqs: list[list[int]] = []
    for _ in range(count):
        n = int(torch.randint(1, max_len + 1, (1,), generator=generator).item())
        seqs.append([int(v) for v in torch.randint(0, vocab, (n,), generator=generator).tolist()])
    return seqs


def check_decoder(decoder: ByteDecoder, tok: ReferenceTokenizer, sequences: Sequence[Sequence[int]]) -> dict[str, Any]:
    """(c) the study's decoder against the reference on random id sequences, including split multi-byte characters (not only valid text)."""
    bad = [n for n, s in enumerate(sequences) if decoder.decode(s) != tok.decode(s)]
    return {"n": len(sequences), "failures": bad}
