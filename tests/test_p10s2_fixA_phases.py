# ruff: noqa: E501
"""P10S2: the memory of the phases AFTER the teacher step (attempt 7 stopped on the memory guard at 9.38 GiB in the bank and bundle phases): the spilled example bank gives the same files as the in-memory
bank, the phase rows, the release of the teachers and the corpus. Fakes and synthetic stand-ins only. Self-check only: not independent review, not Astra validation, not human approval."""

import inspect
import json
import sys
import zlib
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402

from arborlm.io import write_json  # noqa: E402
from studies.p10s2 import datagen, prefreeze, spill, tokenization  # noqa: E402
from studies.p10s2.data import Sizes  # noqa: E402
from studies.p10s2.model import StudentConfig, build_student  # noqa: E402
from studies.p10s2.prefreeze import WindowSpec, build_bundle  # noqa: E402
from studies.p10s2.synthetic import (  # noqa: E402
    LexiconTeacher,
    lexicon,
    make_corpus,
    make_text,
    make_tokenizer,
    tgen,
)
from studies.p10s2.world import ExampleBank  # noqa: E402
from studies.p10s2.worldio import write_bundle  # noqa: E402


def synthetic_inputs() -> tuple[Any, ...]:
    sizes = Sizes.dry()
    corpus = make_corpus(tgen(1, "synthetic corpus"), sentences=1500)
    text_val = make_text(tgen(2, "synthetic wikitext validation"), n_words=1500, marker_rate=0.06)
    text_train = make_text(tgen(3, "synthetic wikitext train"), n_words=1200, marker_rate=0.02)
    tok = make_tokenizer(corpus, text_val, merges=60, add_bos=False)
    student = build_student(StudentConfig.tiny(tok.vocab_size), tgen(4, "stand-in student weights"), std=0.4)
    _, de_map, fr_map = lexicon(25)
    teachers = {"A": LexiconTeacher("stand-in German", de_map, tgen(5, "teacher A noise")), "B": LexiconTeacher("stand-in French", fr_map, tgen(6, "teacher B noise"))}
    return corpus, tok, student, teachers, text_val, text_train, sizes


def test_a_spilled_bank_gives_every_bundle_file_unchanged(tmp_path: Path) -> None:
    manifests = []
    for name, spill_path in (("memory", None), ("spill", tmp_path / "bank_spill.tmp")):
        corpus, tok, student, teachers, text_val, text_train, sizes = synthetic_inputs()
        bundle, rec = build_bundle(corpus, tok, student, teachers, text_val, text_train, sizes, WindowSpec.dry(), "test", 2, spill_path=spill_path)
        if spill_path is not None:
            assert isinstance(bundle.bank_records, spill.StreamedRecords) and len(bundle.bank_records) > 100
        manifests.append((write_bundle(bundle, tmp_path / name), rec["tokenization"], rec["qualification"], rec["sufficiency_after_filter"]))
    assert manifests[0][0] == manifests[1][0]  # the SHA-256 of every file of the bundle, bank.json included
    assert manifests[0][1:] == manifests[1][1:]  # and the checks and the qualification that read the bank
    assert (tmp_path / "memory" / "bank.json").read_bytes() == (tmp_path / "spill" / "bank.json").read_bytes()


class MergingTok:
    bos_id: int | None = None
    vocab_size = 100000

    def encode(self, text: str) -> list[int]:
        import re

        return [zlib.crc32(p.encode()) % 99991 for p in re.findall(r"\n?\w+:?|\n|[^\w\n]+", text)]

    def encode_offsets(self, text: str) -> tuple[list[int], list[tuple[int, int]]]:
        import re

        ms = list(re.finditer(r"\n?\w+:?|\n|[^\w\n]+", text))
        return [zlib.crc32(m.group(0).encode()) % 99991 for m in ms], [(m.start(), m.end()) for m in ms]


def test_spill_bank_examples_order_and_records_equal_the_in_memory_bank(tmp_path: Path) -> None:
    tok, vocab = MergingTok(), {"red": 0, "blue": 1, "green": 2}
    mem, sp = ExampleBank(), spill.SpillBank(vocab, tmp_path / "s.tmp")
    sentences = ["red blue green", "blue red", "green green blue red", "red"]
    for k, bank in enumerate((mem, sp)):
        for i, en in enumerate(sentences):
            for c in ("A", "B"):
                bank.build_from_tokenizer(tok, vocab, c, en, None)  # type: ignore[arg-type]  # in memory in both
        if isinstance(bank, spill.SpillBank):
            bank.spilling = True
        for en in sentences:
            for c in ("A", "B"):
                bank.build_from_tokenizer(tok, vocab, c, en, "x y")  # type: ignore[arg-type]
                bank.build_from_tokenizer(tok, vocab, c, en, None)  # type: ignore[arg-type]  # a repeat: not rebuilt
        if isinstance(bank, spill.SpillBank):
            bank.spilling = False
        assert k in (0, 1)
    assert [e.key for e in spill.iter_examples(sp)] == [e.key for e in spill.iter_examples(mem)]
    assert [e for e in spill.iter_examples(sp)] == [e for e in spill.iter_examples(mem)]  # Example equality: ids, reads, marker, lengths
    assert [e.segments for e in spill.iter_examples(sp)] == [e.segments for e in spill.iter_examples(mem)]
    assert sp.to_records() == mem.to_records()
    assert sp.prompt("A", "blue red") == mem.prompt("A", "blue red")
    path = tmp_path / "bank.json"
    sp.records_stream().write_canonical_json(path)
    ref = tmp_path / "ref.json"
    write_json(ref, mem.to_records())
    assert path.read_bytes() == ref.read_bytes()
    sp.close()
    assert not (tmp_path / "s.tmp").exists()


def test_the_pool_examples_are_not_held_in_memory_while_spilling(tmp_path: Path) -> None:
    sp = spill.SpillBank({"red": 0}, tmp_path / "s.tmp")
    tok = MergingTok()
    sp.spilling = True
    for i in range(50):
        sp.build_from_tokenizer(tok, {"red": 0}, "A", f"red word{i}", "x")  # type: ignore[arg-type]
    assert len(sp) == 50 and not sp._mem and all(v is not None for v in sp._loc.values())
    sp.close()


def test_stream_check_equals_the_list_check() -> None:
    from studies.p10s2.tokenization import Segment

    tok = MergingTok()
    inputs = [[Segment("English:", tuple(tok.encode("English:"))), Segment(" red", tuple(tok.encode(" red")))], [Segment("a", (1,)), Segment("\nb", (2,))], []]
    a = tokenization.check_segments_vs_whole(inputs, tok)  # type: ignore[arg-type]
    b = spill.check_segments_stream((x for x in inputs), tok)  # type: ignore[arg-type]
    assert a == b and spill.check_segments_stream(iter(()), tok)["n"] == 0  # type: ignore[arg-type]


def test_canonical_list_writer_gives_write_json_bytes(tmp_path: Path) -> None:
    recs = [{"b": [1, 2], "a": "é\n", "c": {"z": 1, "y": None}}, {"k": 1.5}]
    spill.write_canonical_json_list(tmp_path / "a.json", (spill.canonical_text(r) for r in recs))
    write_json(tmp_path / "b.json", recs)
    assert (tmp_path / "a.json").read_bytes() == (tmp_path / "b.json").read_bytes()
    spill.write_canonical_json_list(tmp_path / "e.json", iter(()))
    write_json(tmp_path / "f.json", [])
    assert (tmp_path / "e.json").read_bytes() == (tmp_path / "f.json").read_bytes()
    assert not [p for p in tmp_path.iterdir() if p.name.startswith(".")]  # no temporary left behind
    with pytest.raises(RuntimeError):
        spill.write_canonical_json_list(tmp_path / "g.json", _raising())
    assert not [p for p in tmp_path.iterdir() if p.name.startswith(".")] and not (tmp_path / "g.json").exists()


def _raising() -> Any:
    yield "1"
    raise RuntimeError("stop")


def test_phase_rows_at_every_boundary_but_not_per_batch(capsys: pytest.CaptureFixture[str]) -> None:
    clock = datagen.StageClock(1000.0, lambda: 5.0, 2.0)
    clock.tick("teacher batch")
    clock.tick("corpus loaded")
    clock.tick("bank: pools of A")
    assert [r["phase"] for r in clock.phases] == ["corpus loaded", "bank: pools of A"]
    assert all(set(r) == {"phase", "elapsed_s", "resident_mib", "peak_mib"} and r["peak_mib"] > 0 and r["elapsed_s"] == 3.0 for r in clock.phases)
    lines = [x for x in capsys.readouterr().out.splitlines() if x.startswith("[phase]")]
    assert len(lines) == 2 and "resident" in lines[0] and "peak" in lines[0] and "elapsed 3 s" in lines[0]
    with pytest.raises(datagen.StageCapExceeded):
        datagen.StageClock(1.0, lambda: 5.0, 2.0).tick("x")


def test_release_teachers_calls_release_where_there_is_one() -> None:
    class T:
        released = False

        def release(self) -> None:
            self.released = True

    a, b = T(), object()
    prefreeze.release_teachers({"A": a, "B": b})
    assert a.released


def test_marian_teacher_release_drops_model_and_tokenizer() -> None:
    t = datagen.MarianTeacher.__new__(datagen.MarianTeacher)
    t.model, t.tokenizer = object(), object()
    t.release()
    assert t.model is None and t.tokenizer is None


def test_the_phase_order_and_what_is_freed_before_the_bank() -> None:
    src = inspect.getsource(prefreeze.build_bundle)
    assert src.index("part = build_partition(corpus") < src.index("del corpus") < src.index("bank = SpillBank")
    assert src.index('stamp("teachers on Q")') < src.index("teacher_outputs = {") < src.index("release_teachers(teachers)") < src.index("bank.build_from_tokenizer")  # the last translate call, then the release, then the bank
    assert src.index("bank.spilling = True") < src.index("bank.spilling = False") < src.index("bank.records_stream()")
    run = inspect.getsource(datagen._run)
    assert "corpus_box.pop()" in run and "del corpus" in run and "spill.unlink(missing_ok=True)" in run and run.index("finally:") > run.index("build_bundle(")
    assert 'record["steps"]["memory_by_phase"] = clock.phases' in run
    for phase in ("student converted", "tokenizer loaded", "decoder check", "corpus loaded", "teachers loaded"):
        assert f'clock.tick("{phase}")' in run
    assert 'clock.tick("bundle assembled")' in inspect.getsource(datagen._finish) and 'clock.tick("bundle written")' in inspect.getsource(datagen._finish)


def test_write_bundle_streams_a_spilled_bank_and_writes_a_list_as_before() -> None:
    src = inspect.getsource(sys.modules["studies.p10s2.worldio"].write_bundle)
    assert "write_canonical_json" in src and 'write_json(directory / "bank.json", b.bank_records)' in src


def test_json_text_is_what_the_record_hash_expects() -> None:
    assert json.loads(spill.canonical_text({"b": 1, "a": [1]})) == {"a": [1], "b": 1}
