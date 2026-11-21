# ruff: noqa: E501
"""P10IS2 Part Q step 8 (the ``outputs`` stage) through P10-S2's REAL imported functions on a tiny synthetic partition: ``prefreeze.tokenization_checks`` and ``check_combined_whole_string``, ``combined.pair_list``,
``ExampleBank`` / ``SpillBank``, ``tokenization`` (segments, ``ByteDecoder``), ``windows.cut_windows``, ``worldio.write_bundle`` / ``read_bundle``, ``model.build_student``, and the gloss test. The tokenizer is P10-S2's
synthetic byte-pair tokenizer (a real implementation of the same interface; no download, no package outside the lock), the student a tiny random one, the teachers lexicon fakes, the seeds test-range seeds.
The stage ``outputs`` died on the first real run with ``'QPartition' object has no attribute 'gold_pool'``: no test ran the real path. Self-check only."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402
from p10is2_fixtures import (  # noqa: E402
    SMALL_SIZES,
    lex_teachers,
    small_cfg,
    small_corpus,
    stub_student,
)
from p10is2_fixtures import test_gen as tgen  # noqa: E402

from studies.p10is2.common import core  # noqa: E402
from studies.p10is2.partq import pipeline, real_bundle, real_stages, real_world  # noqa: E402
from studies.p10s2 import datagen  # noqa: E402
from studies.p10s2.model import StudentConfig, build_student  # noqa: E402
from studies.p10s2.synthetic import make_text, make_tokenizer  # noqa: E402
from studies.p10s2.worldio import read_bundle  # noqa: E402


def build(tmp: Path):  # type: ignore[no-untyped-def]
    corpus = small_corpus()
    text = make_text(tgen(31), n_words=900)
    tok = make_tokenizer(corpus, text, merges=60)
    ctx = pipeline.QContext(cfg=small_cfg(), mode="test", corpus=corpus, teachers=lex_teachers(), student_scores=stub_student, run_dir=tmp / "run", sizes=SMALL_SIZES, batch_size=8, block_sources=100, accepted_min=30, accepted_disjoint=300, per_replicate=20, regeneration_batches=3, digest_batches=2)
    pipeline.run_all(ctx)
    p = pipeline.step_partition(ctx)
    student = build_student(StudentConfig.tiny(len(tok.token_bytes())), tgen(32))
    w = real_world.RealWorld(ctx.cfg, tmp, ctx.run_dir, tmp / "downloads", tok=tok, student=student, corpus=corpus, record={"wikitext": {"x": 1}, "hashes": {"tatoeba": {"y": 2}}}, texts={"train": text, "validation": text})
    return ctx, p, w, tok, text


def test_the_outputs_stage_runs_through_the_real_p10s2_functions(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ctx, p, w, tok, text = build(tmp_path)
    vocab_index = {x: i for i, x in enumerate(p.vocab)}
    windows = real_world.cut_general_windows(tok, text, vocab_index, 24, 6)  # P10-S2's windows.cut_windows, un-stubbed
    assert windows
    monkeypatch.setattr(real_stages, "_stored_windows", lambda *a, **k: windows[:6])  # FAKE: the ledger's 144 real GEN windows need the real WikiText file and ledger
    monkeypatch.setattr(datagen, "crosscheck_chrf", lambda pairs: {"n": len(pairs), "max_abs_difference": 0.0, "ok": True})  # FAKE: sacrebleu is outside the lock
    out = real_stages.stage_outputs(w, ctx, p, "test")  # the REAL stage body: step8.step_outputs, make_bundle (PartView), the gloss test, write_bundle, the manifest
    assert out["tokenization"]["required_ok"] is True and out["c1_pairing"]["whole_string"]["ok"] is True and out["gloss_test_mismatches"] == 0
    assert out["tokenization"]["b_roundtrip"]["mismatch_count"] == 0
    bundle = read_bundle(Path(out["bundle"]))  # the container Part T reads
    assert set(bundle.panels) == set(p.panels) and bundle.gold_pool == {c: [] for c in core.TASKS} and len(bundle.accepted["A"]) > 0
    assert (ctx.run_dir / "manifest.json").is_file() and json.loads((ctx.run_dir / "manifest.json").read_text())["files"]


def test_the_part_view_gives_the_data_step_exactly_what_it_reads(tmp_path: Path) -> None:
    ctx, p, _w, _tok, _text = build(tmp_path)
    v = real_bundle.PartView(p)
    assert v.panels is p.panels and v.gold_pool == {c: [] for c in core.TASKS}  # the design is teacher-only: ADR-0025 section 5.2
    with pytest.raises(AttributeError):
        v.reserve_blocks  # noqa: B018 - an attribute the data step does not read is not silently forwarded
    assert not hasattr(p, "gold_pool")  # the old failure: the partition itself has none
