# ruff: noqa: E501
"""P10S2: the memory of teacher generation (attempt 7 stopped on the memory guard at 9.38 GiB): the streaming transition scores equal the library's, a batch's tensors are not held into the next one,
a progress line is written every ``PROGRESS_EVERY`` batches, and the allocator's free pages are given back. Fakes only. Self-check only: not independent review, not Astra validation, not human approval."""

import inspect
import sys
import weakref
from pathlib import Path
from types import SimpleNamespace
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402
import torch  # noqa: E402

from studies.p10s2 import datagen  # noqa: E402


def library_transition_scores(sequences: torch.Tensor, scores: tuple[torch.Tensor, ...], beam_indices: torch.Tensor, vocab: int) -> torch.Tensor:
    """transformers 4.57.1 ``compute_transition_scores`` with ``normalize_logits=False``, copied (steps 2 and 4 to 9)."""
    scores_t = torch.stack(scores).reshape(len(scores), -1).transpose(0, 1)
    mask = beam_indices < 0
    max_len = (1 - mask.long()).sum(-1).max()
    beam_indices = beam_indices.clone()[:, :max_len]
    mask = mask[:, :max_len]
    beam_indices[mask] = 0
    cut = sequences.shape[-1] - max_len
    indices = sequences[:, cut:] + beam_indices * vocab
    out = scores_t.gather(0, indices)
    out[mask] = 0
    return out


def make_generation(n: int, rows: int, vocab: int, steps: int, lengths: list[int], seed: int) -> tuple[torch.Tensor, tuple[torch.Tensor, ...], torch.Tensor]:
    """``n`` returned hypotheses over ``rows`` = batch x beams score rows (as the library returns them: ``beam_indices`` and ``sequences`` have one row per returned hypothesis)."""
    g = torch.Generator().manual_seed(seed)
    scores = tuple(torch.log_softmax(torch.randn(rows, vocab, generator=g), dim=-1) for _ in range(steps))
    seqs = torch.randint(1, vocab, (n, 3 + steps), generator=g)
    beams = torch.full((n, steps), -1, dtype=torch.long)
    for r, k in enumerate(lengths):
        beams[r, :k] = torch.randint(0, rows, (k,), generator=g)
    return seqs, scores, beams


@pytest.mark.parametrize("lengths", [[5, 5, 5, 5], [5, 3, 4, 1], [2, 2, 2, 2]])
def test_streaming_scores_equal_the_library_function_bit_for_bit(lengths: list[int]) -> None:
    vocab = 17
    seqs, scores, beams = make_generation(4, 8, vocab, 5, lengths, seed=229001)
    a = datagen.streaming_transition_scores(seqs, scores, beams, vocab)
    b = library_transition_scores(seqs, scores, beams, vocab)
    assert a.shape == b.shape and a.dtype == b.dtype
    assert torch.equal(a, b)  # the same floats, not close ones
    assert torch.equal(a.view(torch.int32), b.view(torch.int32))


class Tok:
    pad = 0

    def __call__(self, batch: list[str], return_tensors: str, padding: bool) -> dict[str, torch.Tensor]:
        return {"input_ids": torch.ones(len(batch), 2, dtype=torch.long)}

    def batch_decode(self, seqs: torch.Tensor, skip_special_tokens: bool) -> list[str]:
        return [f"t{int(r[0])}" for r in seqs]


class FakeGenModel:
    vocab = 11

    def __init__(self) -> None:
        self.config = SimpleNamespace(get_text_config=lambda: SimpleNamespace(vocab_size=self.vocab), pad_token_id=0)
        self.generation_config = None
        self.calls = 0
        self.refs: list[list[weakref.ref[torch.Tensor]]] = []
        self.alive_at_call: list[int] = []

    def generate(self, **kw: Any) -> Any:
        # at the start of every call, the previous call's score tensors must already be freed (the batch's tensors are not held into the next batch)
        self.alive_at_call.append(sum(r() is not None for refs in self.refs for r in refs))
        n = kw["input_ids"].shape[0]
        seqs, scores, beams = make_generation(n, n * kw["num_beams"], self.vocab, 4, [4] * n, seed=229100 + self.calls)
        trans = library_transition_scores(seqs, scores, beams, self.vocab)
        self.refs.append([weakref.ref(t) for t in scores])
        self.calls += 1
        return SimpleNamespace(sequences=seqs, scores=scores, beam_indices=beams, sequences_scores=trans.sum(1) / 4.0)


def fake_teacher(monkeypatch: pytest.MonkeyPatch) -> tuple[datagen.MarianTeacher, FakeGenModel, list[str]]:
    t = datagen.MarianTeacher.__new__(datagen.MarianTeacher)
    model = FakeGenModel()
    ticks: list[str] = []
    t.name, t.revision, t.tick = "fake-mt", "r0", ticks.append
    t.model, t.tokenizer, t.pad_id = model, Tok(), 0
    t.generation_config = {}
    t.batches = 0
    t.progress = []
    t.score_record = {"first_batch": None, "max_abs_difference_all_batches": 0.0, "batches": 0}
    monkeypatch.setattr(datagen, "check_generation_config", lambda a, b: None)
    monkeypatch.setattr(datagen.core, "CFG", {**datagen.core.CFG, "data": {**datagen.core.CFG["data"], "generation_beam": 2, "generation_new_tokens": 4}})
    return t, model, ticks


def test_translate_holds_only_text_and_score_and_frees_each_batch(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    t, model, ticks = fake_teacher(monkeypatch)
    monkeypatch.setattr(datagen, "PROGRESS_EVERY", 2)
    out = t.translate([f"s{i}" for i in range(32 * 5)])
    assert len(out) == 160 and all(isinstance(x, str) and isinstance(y, float) for x, y in out)
    assert ticks == ["teacher batch"] * 5
    assert model.calls == 5 and model.alive_at_call == [0] * 5  # no score tensor of an earlier batch is alive when the next batch is generated
    assert sum(r() is not None for refs in model.refs for r in refs) == 0  # and none after the last
    assert t.score_record["batches"] == 5 and t.score_record["first_batch"]["ok"]


def test_progress_line_every_n_batches_with_elapsed_and_resident_set(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    t, _model, _ = fake_teacher(monkeypatch)
    monkeypatch.setattr(datagen, "PROGRESS_EVERY", 2)
    t.translate([f"s{i}" for i in range(32 * 5)])
    lines = [x for x in capsys.readouterr().out.splitlines() if x.startswith("[progress]")]
    assert len(lines) == 3 == len(t.progress) and lines == t.progress  # batches 0, 2 and 4
    assert "teacher fake-mt batch 0 of 5" in lines[0] and "batch 4 of 5" in lines[2]
    for ln in lines:
        assert "elapsed" in ln and "resident" in ln and "MiB" in ln and "peak" in ln


def test_the_registered_progress_interval_is_every_100_batches() -> None:
    assert datagen.PROGRESS_EVERY == 100


def test_release_freed_memory_is_harmless_and_readings_are_numbers() -> None:
    datagen.release_freed_memory()
    datagen.release_freed_memory()
    assert datagen.peak_rss_mib() > 0
    assert datagen.current_rss_mib() >= 0.0


def test_translate_source_has_no_library_stack_and_frees_the_batch() -> None:
    src = inspect.getsource(datagen.MarianTeacher.translate)
    assert "compute_transition_scores" not in src and "streaming_transition_scores" in src
    assert "del gen, trans, enc" in src and "release_freed_memory()" in src


def test_run_gives_the_freed_pages_back_after_the_collection() -> None:
    src = inspect.getsource(datagen._run)
    assert src.index("del ref, ids, vec, prompts, train_ids") < src.index("gc.collect()") < src.index("release_freed_memory()") < src.index("load_corpus(downloads")
