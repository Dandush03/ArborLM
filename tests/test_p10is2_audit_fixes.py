# ruff: noqa: E501
"""P10IS2 Part Q audit fixes (the independent audit of 3ee23d0): B1 fresh-process launch without patching the platform check, B2 the shared ledger, B3 rehearsals reach generation whatever Q1-Q4 give, B4 the
environment of each stage, R1-R8 and the advisories. Each test fails on the behaviour the audit found and patches nothing under test. Seeds 934001-934999. Self-check only."""

import json
import os
import platform
import stat
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402
import torch  # noqa: E402
from p10is2_fixtures import SMALL_SIZES, small_cfg, small_corpus, stub_student  # noqa: E402
from test_p10is2_launch import freeze, make_repo  # noqa: E402

from studies.p10is2.common import core, gates, procs  # noqa: E402
from studies.p10is2.common import plan as planmod  # noqa: E402
from studies.p10is2.common.panel_ledger import RowMap  # noqa: E402
from studies.p10is2.partq import (  # noqa: E402
    labels,
    partition,
    pipeline,
    real_stages,
    real_world,
    split,
)
from studies.p10is2.partq import rehearsal as reh  # noqa: E402
from studies.p10is2.partq.teacher import FakeTeacher  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
ON_RECORD = platform.system() == "Darwin" and platform.machine() == "arm64" and torch.__version__.split("+")[0] == "2.8.0"
CFG_Q = core.load_config("Q")


def ctx_of(tmp: Path, **kw):  # type: ignore[no-untyped-def]
    from p10is2_fixtures import lex_teachers

    d = dict(cfg=small_cfg(), mode="test", corpus=small_corpus(), teachers=lex_teachers(), student_scores=stub_student, run_dir=tmp / "run", sizes=SMALL_SIZES, batch_size=8, block_sources=100, accepted_min=30, accepted_disjoint=60, per_replicate=20, regeneration_batches=3, digest_batches=2)
    d.update(kw)
    return pipeline.QContext(**d)


# --- B1: a FRESH process reaches its first stage (nothing is patched, threads are the machine's default) -----------------------------------------------
@pytest.mark.skipif(not ON_RECORD, reason="the platform of record")
def test_fresh_process_part_q_launch_reaches_its_stage_not_the_platform_refusal(tmp_path: Path) -> None:
    r = make_repo(tmp_path)
    commit = freeze(r, "Q")
    env = {k: v for k, v in os.environ.items() if k not in ("PYTHONPATH", "OMP_NUM_THREADS", "UV_OFFLINE", "HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE")}
    out = subprocess.run([sys.executable, "-m", "studies.p10is2.partq.stages", "registered", "--stage", "inputs", "--run-dir", str(r / "runs"), "--freeze-commit", commit, "--repo", str(r)], cwd=ROOT, env=env, capture_output=True, text=True, timeout=300, check=False)  # noqa: S603
    err = out.stderr
    assert "platform of record" not in err and "frozen file" not in err and "not clean" not in err, err[-600:]
    assert out.returncode == 75 and "differs from the plan" in err  # the stage body itself ran its first check (the plan inputs, R7) and found the fixture plan's fake input absent: the stage was reached


@pytest.mark.skipif(not ON_RECORD, reason="the platform of record")
def test_fresh_process_part_t_launch_reaches_its_stage(tmp_path: Path) -> None:
    r = make_repo(tmp_path)
    commit = freeze(r, "T")
    env = {k: v for k, v in os.environ.items() if k not in ("PYTHONPATH", "OMP_NUM_THREADS")}
    out = subprocess.run([sys.executable, "-m", "studies.p10is2.partt_stages", "registered", "--stage", "analysis", "--run-dir", str(r / "runs"), "--freeze-commit", commit, "--repo", str(r), "--part-q-dir", str(tmp_path / "noq")], cwd=ROOT, env=env, capture_output=True, text=True, timeout=300, check=False)  # noqa: S603
    assert "platform of record" not in out.stderr and "REFUSED" not in out.stderr and "FileNotFoundError" in out.stderr, out.stderr[-600:]  # it got to Part Q's missing outputs


def test_the_scripts_set_the_adr_thread_count_and_give_each_stage_its_environment(tmp_path: Path) -> None:
    """B1 and B4 by running the launch scripts with a fake ``uv`` that prints the environment it receives. Package stages get the durable path (and offline), ``analysis`` none; every script has six threads."""
    bindir = tmp_path / "bin"
    bindir.mkdir()
    fake = bindir / "uv"
    fake.write_text('#!/bin/sh\necho "PYTHONPATH=${PYTHONPATH-UNSET} OMP=${OMP_NUM_THREADS-UNSET} UVOFF=${UV_OFFLINE-UNSET} HFOFF=${HF_HUB_OFFLINE-UNSET} ARGS=$*"\n')
    fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
    env = {**os.environ, "PATH": f"{bindir}:{os.environ['PATH']}"}
    env.pop("PYTHONPATH", None)
    durable = CFG_Q["paths"]["durable_packages"]
    for stage in ("inputs", "partition", "qfit", "qcheck", "generation", "regeneration", "outputs"):
        o = subprocess.run(["sh", str(ROOT / "studies/p10is2/launch/partq_registered.sh"), stage, str(tmp_path / "r"), "c" * 40], env=env, capture_output=True, text=True, check=True).stdout  # noqa: S603, S607
        assert f"PYTHONPATH={durable}" in o and "OMP=6" in o and "UVOFF=1" in o and "HFOFF=1" in o and "--offline" in o and f"--stage {stage}" in o, (stage, o)
    o = subprocess.run(["sh", str(ROOT / "studies/p10is2/launch/partq_registered.sh"), "analysis", str(tmp_path / "r"), "c" * 40], env={**env, "PYTHONPATH": durable}, capture_output=True, text=True, check=True).stdout  # noqa: S603, S607
    assert "PYTHONPATH=UNSET" in o and "OMP=6" in o  # records only: no package, even if the caller had one on the path
    o = subprocess.run(["sh", str(ROOT / "studies/p10is2/launch/partt_registered.sh"), "train", str(tmp_path / "r"), "c" * 40], env={**env, "PYTHONPATH": durable}, capture_output=True, text=True, check=True).stdout  # noqa: S603, S607
    assert "PYTHONPATH=UNSET" in o and "OMP=6" in o  # Part T: the lock alone
    o = subprocess.run(["sh", str(ROOT / "studies/p10is2/launch/partq_ledger.sh"), "registered"], env=env, capture_output=True, text=True, check=True).stdout  # noqa: S603, S607
    assert f"PYTHONPATH={durable}" in o and "stages ledger --mode registered" in o
    assert CFG_Q["generation"]["threads"] == 6


def test_launch_scripts_are_in_the_frozen_sets() -> None:
    q, t = planmod.frozen_file_hashes(ROOT, "Q"), planmod.frozen_file_hashes(ROOT, "T")
    for f in ("studies/p10is2/launch/partq_registered.sh", "studies/p10is2/launch/partq_rehearse.sh", "studies/p10is2/launch/partq_ledger.sh"):
        assert f in q and f not in t
    assert "studies/p10is2/launch/partt_registered.sh" in t and "studies/p10is2/launch/partt_registered.sh" not in q


# --- B2 / R8: the ledger, from bytes ---------------------------------------------------------------------------------------------------------------------
class WordTok:
    """A stand-in tokenizer: whitespace-delimited words (with their leading space) are the tokens; ids index a byte table."""

    def __init__(self, text: str) -> None:
        self.table: list[bytes] = []
        self.index: dict[bytes, int] = {}
        self.encode_offsets(text)

    def encode_offsets(self, text: str):  # type: ignore[no-untyped-def]
        ids, offs, i = [], [], 0
        while i < len(text):
            j = i + 1
            while j < len(text) and not text[j].isspace():
                j += 1
            b = text[i:j].encode()
            if b not in self.index:
                self.index[b] = len(self.table)
                self.table.append(b)
            ids.append(self.index[b])
            offs.append((i, j))
            i = j
        return ids, offs

    def token_bytes(self) -> list[bytes]:
        return self.table


def test_ledger_spans_are_derived_from_bytes_not_character_offsets() -> None:
    rows = [f" café {i} naïve straße {i * 3} über" for i in range(40)]  # multi-byte characters: character offsets differ from byte offsets
    text = "".join(rows)
    tok = WordTok(text)
    grid = real_world.window_grid(tok, text, 8, 4)
    spans = real_world.window_spans(grid, tok.token_bytes(), rows)
    rm = RowMap.from_rows(rows)
    assert len(spans) == len(grid) > 3
    for g, s in zip(grid, spans, strict=True):
        assert text.encode()[s.start : s.end] == b"".join(tok.table[i] for i in g["ids"])  # the bytes of the span are the window's token bytes
        assert (s.first_row, s.last_row) == (rm.row_of(s.start), rm.row_of(s.end - 1))
    assert any(s.start != g["char_start"] for g, s in zip(grid, spans, strict=True))  # a character offset would have been wrong
    from studies.p10is2.partq.real_world import find_once

    assert find_once(b"abcabc", b"abc") is None and find_once(b"abcab", b"cab") == 2


def test_a_window_that_occurs_twice_stops_the_step() -> None:
    from studies.p10s2.datagen import RegisteredTestStop

    rows = [" alpha beta gamma delta"] * 6  # every window occurs in several places
    text = "".join(rows)
    tok = WordTok(text)
    grid = real_world.window_grid(tok, text, 4, 2)
    with pytest.raises(RegisteredTestStop, match="more than once"):
        real_world.window_spans(grid, tok.token_bytes(), rows)


# --- B3: the rehearsal reaches generation, regeneration and step 8 whatever Q1-Q4 give ---------------------------------------------------------------
def test_rehearsal_runs_generation_even_when_both_teachers_fail(tmp_path: Path) -> None:
    noise = {"A": FakeTeacher("A"), "B": FakeTeacher("B")}  # fails Q1
    plain = ctx_of(tmp_path / "plain", teachers=noise)
    res = pipeline.run_all(plain)
    assert res["label"].startswith(labels.NEGATIVE_QUALITY) and not plain.d("generation").exists()  # a registered run stops there
    with pytest.raises(core.StageRefused, match="both teachers pass"):
        pipeline.step_generation(plain, pipeline.step_partition(plain), pipeline.step_qfit(plain, pipeline.step_partition(plain)))
    forced = ctx_of(tmp_path / "forced", teachers={"A": FakeTeacher("A"), "B": FakeTeacher("B")}, force_generation=True, seal=True, accepted_min=1, accepted_disjoint=10**7)
    pipeline.run_all(forced)
    assert forced.d("generation/result.json").is_file() and forced.d("regeneration.json").is_file()  # every stage ran: which stages ran reveals nothing
    st = reh.stage_statuses(forced)
    assert st["generation"] and st["regeneration"] and st["qcheck"]
    assert not forced.d("qualification.json").exists() and forced.d("sealed/qualification.json").is_file()
    shown = json.dumps(pipeline.summary_for_display(forced))
    assert "NEGATIVE" not in shown and "QUALIFIED" not in shown


def test_measuring_rehearsal_gives_caps_by_code_rates_for_generation(tmp_path: Path) -> None:
    from studies.p10is2.partq import plan as qplan

    def factory():  # type: ignore[no-untyped-def]
        c = ctx_of(tmp_path / "m", teachers={"A": FakeTeacher("A"), "B": FakeTeacher("B")}, seal=True)
        c.force_generation = True
        return c

    rec = reh.run_measuring(factory, cap_seconds=3600.0, charged_before_freeze_seconds=5.0)
    assert {"generation", "regeneration", "qfit", "qcheck"} <= set(rec["rates_seconds_per_unit"]) and rec["projection_units"]["generation"] > 0
    proj = qplan.project_stage_seconds({k: v for k, v in rec["projection_units"].items() if k in rec["rates_seconds_per_unit"]}, rec["rates_seconds_per_unit"])
    assert qplan.caps_proposal(5.0, proj)["generation_hours"] > 0  # caps-proposal no longer refuses for lack of a generation rate


# --- R1-R3: caps, memory guard, order, item errors, records -----------------------------------------------------------------------------------------
def test_guard_stops_on_the_cumulative_cap_and_on_memory() -> None:
    t = {"now": 0.0}
    g = real_stages.Guard(100.0, 12.0, clock=lambda: t["now"], rss=lambda: 3.0)
    assert g() is False and g.reason is None
    t["now"] = 100.0
    assert g() is True and g.reason.startswith("cap")  # type: ignore[union-attr]
    m = real_stages.Guard(1e9, 12.0, clock=lambda: 0.0, rss=lambda: 12.5)
    assert m() is True and m.reason.startswith("memory")  # type: ignore[union-attr]
    assert procs.rss_gib() > 0


def test_stage_order_is_enforced_and_generation_needs_both_teachers(tmp_path: Path) -> None:
    with pytest.raises(core.StageRefused, match="needs 'inputs'"):
        real_stages.require_prerequisites(tmp_path, "partition")
    real_stages._mark(tmp_path, "inputs", "COMPLETE")
    real_stages.require_prerequisites(tmp_path, "partition")
    with pytest.raises(core.StageRefused, match="needs 'partition'"):
        real_stages.require_prerequisites(tmp_path, "qfit")
    ctx = ctx_of(tmp_path / "x", teachers={"A": FakeTeacher("A"), "B": FakeTeacher("B")})
    p = pipeline.step_partition(ctx)
    qf = pipeline.step_qfit(ctx, p)
    pipeline.step_qcheck(ctx, p, qf)
    for fn in (lambda: pipeline.step_generation(ctx, p, qf), lambda: pipeline.step_regeneration(ctx, p)):
        with pytest.raises(core.StageRefused, match="both teachers pass"):
            fn()


def test_item_errors_and_paused_stages_reach_the_analysis(tmp_path: Path) -> None:
    ctx = ctx_of(tmp_path)
    pipeline.run_all(ctx)
    assert labels.part_q_label(pipeline.facts_of(ctx))["label"].startswith("TEACHERS-QUALIFIED")
    pipeline.record_item_error(ctx, "qfit", "OSError: no space left on device")
    res = labels.part_q_label(pipeline.facts_of(ctx))
    assert res["label"] == labels.ENGINEERING_STOP_ITEMS and res["derived"] is False  # the analysis refuses: never a scientific label
    (ctx.d("item_errors") / "qfit.json").unlink()
    real_stages._mark(ctx.run_dir, "generation", "PAUSED")
    assert labels.part_q_label(pipeline.facts_of(ctx))["label"] == labels.PAUSED
    real_stages._mark(ctx.run_dir, "generation", "COMPLETE")
    assert labels.part_q_label(pipeline.facts_of(ctx))["label"].startswith("TEACHERS-QUALIFIED") and real_stages.completion_path(ctx.run_dir, "generation").is_file()


def test_a_digest_mismatch_leaves_a_record_that_a_new_process_reads(tmp_path: Path) -> None:
    from p10is2_fixtures import LexTeacher, lex_teachers

    ctx = ctx_of(tmp_path)
    pipeline.run_all(ctx)
    t = lex_teachers()
    ctx2 = ctx_of(tmp_path, teachers={"A": LexTeacher("A", t["A"].mapping, batch_dependent=True), "B": t["B"]})
    assert pipeline.run_all(ctx2)["label"] == labels.ENGINEERING_FAILURE
    assert (tmp_path / "run" / "engineering_failures.json").is_file() and labels.part_q_label(pipeline.facts_of(ctx_of(tmp_path)))["label"] == labels.ENGINEERING_FAILURE


# --- R6: the forced identity probe never counts a refusal as a pass ---------------------------------------------------------------------------------
def test_only_the_forced_identity_pause_counts_not_any_refusal(tmp_path: Path) -> None:
    def factory():  # type: ignore[no-untyped-def]
        return ctx_of(tmp_path / "p", seal=True)

    def refuses() -> None:
        raise core.StageRefused("refused: some other precondition")

    with pytest.raises(core.StageRefused, match="some other precondition"):
        reh.run_counting(factory, plan_file_sha256="a" * 64, caps_provisional=False, cap_seconds=1e6, identity_probe=refuses, pause_after_batches=3)

    def observed() -> None:
        raise core.ForcedIdentityPause("PAUSED — IDENTITY forced and restored")

    rec = reh.run_counting(factory, plan_file_sha256="a" * 64, caps_provisional=False, cap_seconds=1e6, identity_probe=observed, pause_after_batches=3)
    assert rec["forced"]["paused_identity_restore"] is True


# --- R7, the corpus-level supply counts identity groups ---------------------------------------------------------------------------------------------
def test_corpus_supply_counts_identity_groups_not_keys() -> None:
    from studies.p10s2.synthetic import Corpus

    eng = {1: "the cat sat now", 2: "The cat sat now.", 3: "a dog ran home", 4: "my red bird flew"}
    deu = {10: "d1", 11: "d3", 12: "d4"}
    fra = {20: "f1", 21: "f4"}
    corpus = Corpus(eng, deu, fra, [(1, 10), (2, 10), (3, 11), (4, 12)], [(1, 20), (4, 21)])
    cfg = small_cfg()
    sup = partition.corpus_supply(corpus, cfg)
    # sentences 1 and 2 are one normalized key and share a reference: one identity group; 3 and 4 are separate groups
    assert sup == {"in_vocabulary_groups_with_german": 3, "in_vocabulary_groups_with_french": 2, "in_vocabulary_groups_with_both": 2, "unit": "identity groups"}


# --- A1 / A2 -----------------------------------------------------------------------------------------------------------------------------------
def test_the_seed_gate_cannot_be_blind_past_the_checkers_print_limit() -> None:
    assert any(old == "    for p_ in problems[:40]:" and new == "    for p_ in problems:" for old, new in gates.CHECKER_SUBSTITUTIONS)
    text = (ROOT / CFG_Q["seeds"]["registry_checker"]).read_text()
    assert gates.checker_copy(text, ROOT).count("problems[:40]") == 0
    r = gates.run_checker_copy(ROOT / CFG_Q["seeds"]["registry_checker"], ROOT, 300.0)
    assert r["all_problems_printed"] and r["reported_problem_count"] == r["problems"] and r["problems_naming_this_study"] == []


def test_draw_order_loop_equals_the_vector_draw_at_the_sizes_used() -> None:
    g = torch.Generator().manual_seed(934004)
    vec = torch.rand(5000, generator=g)
    g2 = torch.Generator().manual_seed(934004)
    loop = torch.tensor([float(torch.rand(1, generator=g2).item()) for _ in range(5000)])
    assert torch.equal(vec, loop)
    assert "700,000" in (split.assign_shared.__doc__ or "")


def test_a_registered_stage_takes_its_parameters_from_the_plan_not_the_config(tmp_path: Path) -> None:
    from studies.p10is2.partq import plan as qplan

    cfg = core.load_config("Q")
    rec = qplan.build_candidate(ROOT, tmp_path / "run", cfg, inputs={}, walk={"python_files": [], "files_opened": [], "outside_study_python": [], "outside_study_data": []})
    rec["layout"]["batch_size"] = 16  # a plan that differs from the config
    rec["layout"]["digest"]["batches"] = 2
    rec["items"]["qfit"] = [i for i in rec["items"]["qfit"] if i["teacher"] == "A"]  # a plan that names one teacher
    plan = planmod.Plan(rec, "Q")
    w = real_world.RealWorld(cfg, ROOT, tmp_path / "run", tmp_path)
    w.teachers = {"A": FakeTeacher("A"), "B": FakeTeacher("B")}
    with pytest.raises(core.StageRefused, match="inputs record is missing"):
        real_stages.make_ctx(w, "registered", plan=plan)  # the window counts of the inputs stage cannot be skipped
    (tmp_path / "run" / "inputs").mkdir(parents=True)
    (tmp_path / "run" / "inputs" / "record.json").write_text(json.dumps({"ordinary_windows_left": 120, "marker_like_windows": 44}))
    ctx = real_stages.make_ctx(w, "registered", plan=plan)
    assert ctx.ordinary_windows_left == 120 and ctx.marker_like_windows == 44 and ctx.batch_size == 16 and cfg["generation"]["batch_size"] == 32 and ctx.digest_batches == 2 and set(ctx.teachers) == {"A"}
    assert ctx.check_target == 150 and ctx.accepted_disjoint == 24000 and ctx.accepted_min == 10000 and ctx.block_sources == 20000


def test_the_part_q_manifest_lists_every_output_with_its_hash(tmp_path: Path) -> None:
    ctx = ctx_of(tmp_path, seal=True)
    pipeline.run_all(ctx)
    files = real_stages.write_manifest(ctx)
    m = json.loads((tmp_path / "run" / "manifest.json").read_text())
    assert m["files"] and set(m["files"]) == set(files) and not any("sealed" in k for k in m["files"])
    assert "generation/result.json" in m["files"] and all(len(v) == 64 for v in m["files"].values())
