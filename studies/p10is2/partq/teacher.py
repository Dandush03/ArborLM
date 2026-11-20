# ruff: noqa: E501
"""The teacher interface of Part Q, a tiny deterministic fake for tests, and the adapter over P10-S2's Marian teacher (ADR-0025 sections 4.3 rule 9, 13 item 6).

Every teacher run goes through ``generate_batch``: one WHOLE batch of at most 32 sources in, one ``Generated`` per source out (token ids, decoded text, length-normalized beam score). The fake needs no package and no
model; tests never import the Marian adapter's dependencies. ``MarianBatchTeacher`` is the real path and is only built inside a Part Q process that has the 28 packages on its path by the steps the ADR names.
"""

import hashlib
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class Generated:
    tokens: tuple[int, ...]
    text: str
    score: float


class BatchTeacher(Protocol):
    name: str
    revision: str

    def generate_batch(self, sources: Sequence[str]) -> list[Generated]: ...


class FakeTeacher:
    """A deterministic stand-in: each source word maps to a pseudo target word by a hash of (name, word); a share of the outputs is damaged (a word dropped) and given a worse score. No randomness: the same
    source gives the same output in any batch composition, unless ``batch_dependent`` is set (then the first output of a batch of more than one source gets its last token altered: a stand-in for a
    thread- or layout-dependent real teacher, used to test the zero-tolerance regeneration check)."""

    def __init__(self, name: str, *, damage_every: int = 4, batch_dependent: bool = False, vocab: int = 5000) -> None:
        self.name, self.revision = name, "fake"
        self.damage_every, self.batch_dependent, self.vocab = damage_every, batch_dependent, vocab
        self.calls = 0

    def _word_id(self, w: str) -> int:
        return int(hashlib.sha256(f"{self.name}|{w}".encode()).hexdigest()[:8], 16) % self.vocab

    def word_text(self, w: str) -> str:
        return f"{self.name[:1].lower()}{self._word_id(w)}"

    def generate_batch(self, sources: Sequence[str]) -> list[Generated]:
        from studies.p10s2.text import normalize

        self.calls += 1
        out: list[Generated] = []
        for k, s in enumerate(sources):
            words = normalize(s).split()
            h = int(hashlib.sha256(f"{self.name}|{normalize(s)}".encode()).hexdigest()[:8], 16)
            damaged = self.damage_every > 0 and h % self.damage_every == 0 and len(words) > 1
            kept = words[1:] if damaged else words
            toks = [self._word_id(w) for w in kept]
            if self.batch_dependent and k == 0 and len(sources) > 1 and toks:
                toks[-1] = (toks[-1] + 1) % self.vocab
            text = " ".join(f"{self.name[:1].lower()}{t}" for t in toks)
            score = -0.45 - 0.01 * (h % 10) if damaged else -0.05 - 0.005 * (h % 10)
            out.append(Generated(tuple(toks), text, score))
        return out


def marian_batch_teacher(downloads: Any, label: str, name: str, revision: str, tick: Callable[[str], None]) -> BatchTeacher:  # pragma: no cover - needs transformers and the 28 packages
    """The real teacher: P10-S2's pinned Marian loader (files re-hashed before loading, weights-only load, local files only, beam 4, at most 48 new tokens), returning token ids per source.

    It subclasses ``studies.p10s2.datagen.MarianTeacher`` and adds ``generate_batch``, which runs ONE batch through the same ``generate`` call ``translate`` uses and keeps the generated token ids. Never
    called by a test and not exercised in this implementation (no real model is run here)."""
    import torch

    from studies.p10s2 import datagen as dg

    class _Marian(dg.MarianTeacher):
        @torch.no_grad()
        def generate_batch(self, sources: Sequence[str]) -> list[Generated]:
            from studies.p10s2 import core as c2

            if len(sources) > 32:
                raise ValueError("a teacher batch holds at most 32 sources (the frozen layout)")
            dg.check_generation_config(self.model.generation_config, self.generation_config)
            enc = self.tokenizer(list(sources), return_tensors="pt", padding=True)
            gen = self.model.generate(**enc, num_beams=c2.CFG["data"]["generation_beam"], max_new_tokens=c2.CFG["data"]["generation_new_tokens"], length_penalty=1.0, return_dict_in_generate=True, output_scores=True)
            trans = dg.streaming_transition_scores(gen.sequences, gen.scores, gen.beam_indices, int(self.model.config.get_text_config().vocab_size))
            mine = dg.recompute_sequence_scores(trans, gen.sequences[:, -trans.shape[1] :], self.pad_id)
            texts = self.tokenizer.batch_decode(gen.sequences, skip_special_tokens=True)
            out = []
            for row, text, sc in zip(gen.sequences.tolist(), texts, mine, strict=True):
                ids = [int(t) for t in row]
                while ids and ids[-1] == self.pad_id:
                    ids.pop()
                out.append(Generated(tuple(ids), text, float(sc)))
            del gen, trans, enc
            return out

    return _Marian(downloads, label, name, revision, tick)
