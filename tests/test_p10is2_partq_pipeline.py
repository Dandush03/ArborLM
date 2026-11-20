# ruff: noqa: E501
"""P10IS2 Part Q pipeline on synthetic stand-ins (ADR-0025 section 4). No package outside the lock, no real data or model. Self-check only."""

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

from studies.p10is2.common import core  # noqa: E402
from studies.p10is2.partq import labels, pipeline  # noqa: E402
from studies.p10is2.partq.teacher import FakeTeacher  # noqa: E402


def make_ctx(tmp_path: Path, **kw):  # type: ignore[no-untyped-def]
    d = dict(
        cfg=small_cfg(), mode="test", corpus=small_corpus(), teachers=lex_teachers(), student_scores=stub_student, run_dir=tmp_path / "run", sizes=SMALL_SIZES, batch_size=8, block_sources=200,
        accepted_min=30, accepted_disjoint=60, per_replicate=20, regeneration_batches=3, digest_batches=2,
    )  # fmt: skip
    d.update(kw)
    return pipeline.QContext(**d)


def test_end_to_end_qualified_on_synthetic(tmp_path: Path) -> None:
    ctx = make_ctx(tmp_path)
    res = pipeline.run_all(ctx)
    assert res["label"].startswith("TEACHERS-QUALIFIED"), res
    assert res["part_t_started"] is False
    assert ctx.d("generation/pools.json").is_file()
    assert core.ORACLE_LINE in labels.render(res)


def test_unqualified_when_teacher_is_noise(tmp_path: Path) -> None:
    t = lex_teachers()
    t["B"] = FakeTeacher("B")  # outputs unrelated tokens: fails Q1
    ctx = make_ctx(tmp_path, teachers=t)
    res = pipeline.run_all(ctx)
    assert res["label"].startswith("QUALIFICATION-NEGATIVE: QUALITY"), res
    assert not ctx.d("generation").exists()
    assert res["part_t"] == "Part T: NOT STARTED"
    # G15: the failing teacher still had Q3 and Q4 attempted (Q4 only if Q3 produced a setting)
    assert ctx.d("qcheck/teacher_A/result.json").is_file()
    assert ctx.d("qcheck/teacher_B/result.json").is_file()


@pytest.mark.parametrize("mode", ["fresh"])
def test_resume_rereads_and_asserts_digest(tmp_path: Path, mode: str) -> None:
    ctx = make_ctx(tmp_path)
    pipeline.run_all(ctx)
    calls = {c: ctx.teachers[c].calls for c in core.TASKS}  # type: ignore[attr-defined]
    res2 = pipeline.run_all(ctx)
    assert res2["label"].startswith("TEACHERS-QUALIFIED")
    # a resume only regenerates the digest batches (2 per teacher)
    for c in core.TASKS:
        assert ctx.teachers[c].calls - calls[c] == 2  # type: ignore[attr-defined]
