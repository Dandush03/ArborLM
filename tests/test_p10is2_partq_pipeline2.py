# ruff: noqa: E501
"""P10IS2 Part Q pipeline, further rows of section 4.4 and step 8 (ADR-0025 sections 4.1, 4.3, 4.4; rulings G15, G17). Synthetic stand-ins only; seeds 934001-934999. Self-check only."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402
import torch  # noqa: E402
from p10is2_fixtures import (  # noqa: E402
    SMALL_SIZES,
    LexTeacher,
    lex_teachers,
    small_cfg,
    small_corpus,
    stub_student,
)

from studies.p10is2.common import core  # noqa: E402
from studies.p10is2.common.panel_ledger import Span  # noqa: E402
from studies.p10is2.partq import batches as bt  # noqa: E402
from studies.p10is2.partq import labels, partition, pipeline, step8  # noqa: E402
from studies.p10is2.partq.teacher import FakeTeacher  # noqa: E402
from studies.p10s2.data import Item  # noqa: E402
from studies.p10s2.synthetic import make_tokenizer  # noqa: E402
from studies.p10s2.text import normalize  # noqa: E402


def ctx_of(tmp: Path, **kw):  # type: ignore[no-untyped-def]
    d = dict(cfg=small_cfg(), mode="test", corpus=small_corpus(), teachers=lex_teachers(), student_scores=stub_student, run_dir=tmp / "run", sizes=SMALL_SIZES, batch_size=8, block_sources=100, accepted_min=30, accepted_disjoint=60, per_replicate=20, regeneration_batches=3, digest_batches=2)
    d.update(kw)
    return pipeline.QContext(**d)


def rec(ctx: pipeline.QContext, name: str) -> dict:  # type: ignore[type-arg]
    return json.loads(ctx.d(name).read_text())  # type: ignore[no-any-return]


# --- the rows of section 4.4 ---------------------------------------------------------------------------------------------------------------
def test_row_2_data_insufficient_before_any_teacher_runs(tmp_path: Path) -> None:
    ctx = ctx_of(tmp_path, sizes={**SMALL_SIZES, "e_eval_min": 10_000})
    res = pipeline.run_all(ctx)
    assert res["label"] == labels.DATA_INSUFFICIENT and "E_A" in res["why"]
    assert all(t.calls == 0 for t in ctx.teachers.values())  # type: ignore[attr-defined]
    assert not ctx.d("qfit").exists()


def test_step_2_counts_windows_and_training_side_supply() -> None:
    p = partition.build_partition(small_corpus(), small_cfg(), core.partq_seeds(small_cfg(), "test"), core.test_range(small_cfg()), sizes=SMALL_SIZES)
    assert partition.fixed_input_problems(p, small_cfg(), ordinary_windows_left=4, marker_like_windows=44, sizes={**SMALL_SIZES, "gen_marker_like": 44}) == []
    assert any("marker-like" in x for x in partition.fixed_input_problems(p, small_cfg(), marker_like_windows=43, sizes={"gen_marker_like": 44}))
    assert any("ordinary" in x for x in partition.fixed_input_problems(p, small_cfg(), ordinary_windows_left=99, sizes={"gen_ordinary": 100}))
    assert any("training-side" in x for x in partition.fixed_input_problems(p, small_cfg(), sizes={**SMALL_SIZES, "q_fit": 10**6}))


def test_row_4_reserve_exhausted_before_the_minimum_gives_data_exhausted(tmp_path: Path) -> None:
    cfg = small_cfg(q4_min_accepted=10**6)
    ctx = ctx_of(tmp_path, cfg=cfg)
    res = pipeline.run_all(ctx)
    assert res["label"] == labels.DATA_EXHAUSTED and "reserve" in res["why"]
    assert not ctx.d("generation").exists() and res["part_t"] == labels.PART_T_NOT_STARTED
    assert rec(ctx, "qcheck/teacher_A/stop.json")["exhausted"] is True and rec(ctx, "qcheck/teacher_A/stop.json")["blocks_drawn"] == 6  # the whole reserve of the small panel was drawn


def test_row_4_pool_ends_below_the_minimum(tmp_path: Path) -> None:
    res = pipeline.run_all(ctx_of(tmp_path, accepted_min=10**6, accepted_disjoint=10**7))
    assert res["label"] == labels.DATA_EXHAUSTED and "below 10,000" in res["why"]


def test_row_5_overlapping_draws_by_rule_and_no_draw_in_part_q(tmp_path: Path) -> None:
    ctx = ctx_of(tmp_path, accepted_disjoint=10**7)
    res = pipeline.run_all(ctx)
    assert res["label"] == "TEACHERS-QUALIFIED (OVERLAPPING DRAWS)"
    g = rec(ctx, "generation/result.json")
    assert g["draws_label"] == "OVERLAPPING DRAWS" and g["draws"] is None and "training-draw seed" in g["draws_note"]


def test_row_5_disjoint_draws_are_the_permutation_positions(tmp_path: Path) -> None:
    ctx = ctx_of(tmp_path, accepted_disjoint=60, accepted_min=30, per_replicate=20)
    res = pipeline.run_all(ctx)
    assert res["label"] == "TEACHERS-QUALIFIED (DISJOINT DRAWS)"
    g = rec(ctx, "generation/result.json")
    for i, c in enumerate(core.TASKS):
        n = g["counts"][c]
        assert n >= 60
        gen = torch.Generator().manual_seed(934016 + i)  # 250916 / 250917 in test mode: offsets 15 and 16 of the test base
        perm = torch.randperm(n, generator=gen).tolist()
        # the test-mode seeds are test_low + index of the name; recompute from the table rather than assume the offsets
        seed = core.partq_seeds(small_cfg(), "test")["disjoint_permutation_a" if c == "A" else "disjoint_permutation_b"]
        perm = torch.randperm(n, generator=torch.Generator().manual_seed(seed)).tolist()
        assert g["draws"]["indices"][c] == [perm[0:20], perm[20:40], perm[40:60]]
        assert g["draws"]["shared_share"][c] == 0.0


def test_generation_stops_at_the_first_block_boundary_at_or_above_the_target(tmp_path: Path) -> None:
    ctx = ctx_of(tmp_path, block_sources=60, accepted_disjoint=40, accepted_min=20)
    pipeline.run_all(ctx)
    g = rec(ctx, "generation/result.json")
    for c in core.TASKS:
        pc = g["per_capability"][c]
        assert pc["reached_target"] and pc["accepted"] >= 40
        assert pc["accepted"] - pc["accepted_by_block"][-1] < 40  # the last block was needed: stopping happened at the first boundary reaching 40
        assert pc["blocks"] == len(pc["accepted_by_block"]) and pc["sources_generated"] == min(pc["blocks"] * 60, pc["sources_generated"])


def test_split_gives_each_teacher_only_its_own_sources_and_shared_units_go_one_way(tmp_path: Path) -> None:
    ctx = ctx_of(tmp_path)
    pipeline.run_all(ctx)
    pa = [json.loads(json.dumps(x)) for x in rec(ctx, "generation/pools.json")["pools"]["A"]]
    pb = [x for x in rec(ctx, "generation/pools.json")["pools"]["B"]]
    from studies.p10s2.data import expand_key

    ua = {expand_key(x["en"]) for x in pa}
    ub = {expand_key(x["en"]) for x in pb}
    assert not (ua & ub)  # no source unit is generated for both capabilities
    sp = rec(ctx, "generation/result.json")["split"]
    assert sp["shared_to_A"] + sp["shared_to_B"] == sp["shared_units"] and sp["shared_units"] > 0
    assert sp["A_sources"] + sp["B_sources"] == sp["A_pool"] + sp["B_pool"] - sp["shared_units"]


def test_pools_never_contain_a_panel_group_or_an_evaluation_reference(tmp_path: Path) -> None:
    ctx = ctx_of(tmp_path)
    pipeline.run_all(ctx)
    p = pipeline.step_partition(ctx)
    groups = p.panel_groups()
    pools = rec(ctx, "generation/pools.json")["pools"]
    assert all(x["group"] not in groups or x["group"] < 0 for c in core.TASKS for x in pools[c])
    eval_norm = {normalize(r) for n in ("E_A", "E_B", "E_C", "E_open") for it in p.panels[n] for refs in it.refs.values() for r in refs}
    assert all(normalize(x["target"]) not in eval_norm for c in core.TASKS for x in pools[c])  # the evaluation-equal drop


def test_reserve_blocks_are_whole_blocks_outside_every_panel() -> None:
    p = partition.build_partition(small_corpus(), small_cfg(), core.partq_seeds(small_cfg(), "test"), core.test_range(small_cfg()), sizes=SMALL_SIZES)
    assert all(len(b) == 40 for b in p.reserve_blocks) and len(p.reserve_blocks) == 6
    res_groups = {i.group for b in p.reserve_blocks for i in b}
    panel_groups = {i.group for items in p.panels.values() for i in items}
    assert not (res_groups & panel_groups)  # the reserve is blocked together with every panel
    in_pools = {i.group for c in core.TASKS for i in p.source_pool[c] if i.group >= 0}
    assert not (in_pools & (res_groups | panel_groups))  # blocked BEFORE the pools are defined
    assert len(p.panels["Q_fit"]) == 120 and len({i.group for i in p.panels["Q_fit"]}) == 120


# --- engineering failures --------------------------------------------------------------------------------------------------------------------
def test_regeneration_difference_is_an_engineering_failure_and_persists_across_resume(tmp_path: Path) -> None:
    ctx = ctx_of(tmp_path)
    p = pipeline.step_partition(ctx)
    qf = pipeline.step_qfit(ctx, p)
    pipeline.step_qcheck(ctx, p, qf)
    pipeline.step_generation(ctx, p, qf)
    ctx.teachers = {**ctx.teachers, "A": LexTeacher("A", ctx.teachers["A"].mapping, batch_dependent=True)}  # type: ignore[attr-defined]
    pipeline.step_regeneration(ctx, p)
    assert any("regeneration difference, teacher A" in f for f in ctx.engineering_failures)
    res = labels.part_q_label(pipeline.facts_of(ctx))
    assert res["label"] == labels.ENGINEERING_FAILURE and res["part_t"] == labels.PART_T_NOT_STARTED
    fresh = ctx_of(tmp_path)  # a new process: the failure is read from the record, not from memory
    assert labels.part_q_label(pipeline.facts_of(fresh))["label"] == labels.ENGINEERING_FAILURE
    reg = rec(ctx, "regeneration.json")
    assert reg["ok"] is False and reg["teachers"]["A"]["token_mismatches"][0]["item"] == 0 and reg["teachers"]["B"]["ok"] is True


def test_digest_mismatch_at_a_resume_is_an_engineering_failure(tmp_path: Path) -> None:
    ctx = ctx_of(tmp_path)
    assert pipeline.run_all(ctx)["label"].startswith("TEACHERS-QUALIFIED")
    ctx2 = ctx_of(tmp_path, teachers={"A": LexTeacher("A", ctx.teachers["A"].mapping, batch_dependent=True), "B": ctx.teachers["B"]})  # type: ignore[attr-defined]
    res = pipeline.run_all(ctx2)
    assert res["label"] == labels.ENGINEERING_FAILURE and "digest mismatch" in res["why"]
    assert not (tmp_path / "run" / "sealed").exists()


def test_cap_stop_pauses_and_resume_completes_with_the_same_result(tmp_path: Path) -> None:
    whole = pipeline.run_all(ctx_of(tmp_path / "a"))
    n = {"k": 0}

    def deadline() -> bool:
        n["k"] += 1
        return n["k"] > 30

    ctx = ctx_of(tmp_path / "b", deadline=deadline)
    with pytest.raises(bt.StageCapExceeded):
        pipeline.run_all(ctx)
    ctx.deadline = None
    resumed = pipeline.run_all(ctx)
    assert resumed["label"] == whole["label"]
    a = {k: v for k, v in pipeline.hashes_of(ctx_of(tmp_path / "a")).items() if "teacher_" in k and k.endswith(".json") and "batch_" in k}
    b = {k: v for k, v in pipeline.hashes_of(ctx_of(tmp_path / "b")).items() if "teacher_" in k and k.endswith(".json") and "batch_" in k}
    assert a == b and len(a) > 50  # identical stored batches whether or not the run was paused


def test_q_fit_is_never_extended_when_q3_fails(tmp_path: Path) -> None:
    noise = {"A": FakeTeacher("A"), "B": FakeTeacher("B")}
    ctx = ctx_of(tmp_path, teachers=noise)
    res = pipeline.run_all(ctx)
    assert res["label"].startswith(labels.NEGATIVE_QUALITY)
    for c in core.TASKS:
        assert noise[c].calls == 15 + 0 or noise[c].calls >= 15  # 120 Q_fit sources in batches of 8: 15 batches, then the Q_check batches only if Q3 produced a setting
        assert len(list(ctx.d(f"qfit/teacher_{c}").glob("batch_*.json"))) == 15  # never extended
    q = rec(ctx, "qcheck/teacher_A/result.json")
    assert q["ran"] is False and "Q3 failed" in q["reason"]  # G15: a failed Q3 leaves the teacher without Q4


def test_q1_failing_teacher_still_has_q3_and_q4_run_and_printed(tmp_path: Path) -> None:
    class Weak(LexTeacher):
        """Translates only the first two words: a poor Q1 score but outputs of one length whose precision the filter can still measure."""

    ctx = ctx_of(tmp_path, student_scores=lambda items, p=None: {"A": 0.0, "B": 0.0})
    # force Q1 to fail for B only by raising the bar on a copy of the config: the teacher stays the same, the criterion moves
    ctx.cfg = {**ctx.cfg, "quality": {**ctx.cfg["quality"], "q1_own_score_min": 0.999}}  # type: ignore[index]
    res = pipeline.run_all(ctx)
    assert res["label"].startswith(labels.NEGATIVE_QUALITY) and "Q1" in res["label"]
    assert ctx.d("qcheck/teacher_A/result.json").is_file() and ctx.d("qcheck/teacher_B/result.json").is_file()
    assert res["per_teacher"]["A"]["q4"] is not None  # Q4 was run and is printed although Q1 failed
    assert not ctx.d("generation").exists()  # generation (step 7) does not run


# --- sealing -----------------------------------------------------------------------------------------------------------------------------------
def test_sealed_run_writes_values_under_sealed_and_displays_only_the_whitelist(tmp_path: Path) -> None:
    ctx = ctx_of(tmp_path, seal=True)
    pipeline.run_all(ctx)
    shown = pipeline.summary_for_display(ctx)
    assert set(shown) == {"counts", "batches"}  # L1: nothing the lead can read depends on Q1-Q4
    assert "q1" not in json.dumps(shown) and "filter" not in json.dumps(shown) and "yield" not in json.dumps(shown)
    sealed_path = pipeline.write_sealed_summary(ctx)
    sealed = json.loads(sealed_path.read_text())
    assert sealed["filter_setting"]["A"]["tau"] <= -0.05 and "yields" in sealed and (sealed_path.stat().st_mode & 0o777) == 0o600
    assert (sealed_path.parent.stat().st_mode & 0o777) == 0o700
    assert not ctx.d("qfit/record.json").exists() and ctx.d("sealed/qfit_record.json").is_file() and ctx.d("sealed/qfit_values.json").is_file()
    assert ctx.d("sealed/qcheck_A_values.json").is_file() and ctx.d("sealed/qcheck_A_result.json").is_file()
    assert not any("sealed" in k for k in pipeline.hashes_of(ctx))  # the manifest never lists a sealed file
    unsealed = ctx_of(tmp_path / "u")
    pipeline.run_all(unsealed)
    assert unsealed.d("qcheck/teacher_A/values.json").is_file() and unsealed.d("qualification.json").is_file()


# --- step 8 -------------------------------------------------------------------------------------------------------------------------------------
def test_step_outputs_stores_teacher_outputs_on_the_six_panels_unscored(tmp_path: Path) -> None:
    ctx = ctx_of(tmp_path)
    p = pipeline.step_partition(ctx)
    r = step8.step_outputs(ctx, p)
    assert r["scored"] is False and set(r["outputs"]) == {f"{c}/{n}" for c in core.TASKS for n in step8.PANEL_OUTPUT_PANELS}
    assert r["outputs"]["A/E_A"]["sources"] == 30 and r["outputs"]["B/D_con"]["sources"] == 10
    assert "chrf" not in json.dumps(r).lower() and "score" not in json.dumps({k: v for k, v in r["outputs"].items()}).lower()


def test_step_ledger_records_44_plus_100_and_excludes_foreign_spans(tmp_path: Path) -> None:
    ctx = ctx_of(tmp_path, sizes={**SMALL_SIZES, "gen_marker_like": 44, "gen_ordinary": 100})
    markers = [Span(i * 1000, i * 1000 + 900, i, i) for i in range(44)]
    foreign = [Span(50_000 + i * 1000, 50_000 + i * 1000 + 900, 50 + i, 50 + i, "panel", "P10IS3") for i in range(20)]
    cand = [Span(50_000 + i * 1000, 50_000 + i * 1000 + 900, 50 + i, 50 + i) for i in range(140)]  # the first 20 overlap the foreign panels
    path = tmp_path / "ledger.json"
    core.write_record(path, {**core.envelope("panel_ledger", "Q"), "windows": [s.to_json() for s in foreign]})
    out = step8.step_ledger(ctx, path, markers, cand)
    assert out["ok"] and out["eligible_ordinary"] == 120 and out["counts"] == {"marker": 44, "ordinary": 100}
    led = json.loads(path.read_text())
    assert led["p10is2"]["end_exclusive"] is True and led["format"] == "p10i-panel-ledger-v1" and len(led["windows"]) == 20 + 144
    mine = [s for s in led["windows"] if s["owner"] == "P10IS2-partq" and s["kind"] == "ordinary"]
    assert len(mine) == 100 and all(s["start"] >= 70_000 for s in mine)  # none of the 20 candidates that overlap a foreign span
    with pytest.raises(core.PendingLeadReview):
        step8.step_ledger(ctx, tmp_path / "l2.json", markers[:43], cand)
    with pytest.raises(Exception, match="ordinary windows overlap no recorded span"):
        step8.step_ledger(ctx_of(tmp_path / "z", sizes={**SMALL_SIZES, "gen_marker_like": 44, "gen_ordinary": 100}), tmp_path / "l3.json", markers, cand[:99])


def test_step_gloss_bank_and_tokenization_test(tmp_path: Path) -> None:
    corpus = small_corpus()
    ctx = ctx_of(tmp_path)
    pipeline.run_all(ctx)
    p = pipeline.step_partition(ctx)
    text = " ".join(corpus.eng.values())[:3000]
    tok = make_tokenizer(corpus, text, merges=40)
    r = step8.step_gloss(ctx, tok, {n: p.panels[n] for n in ("E_A", "E_B", "D_cal")}, set(p.vocab))
    assert r["mismatches"] == 0 and not ctx.engineering_failures
    bank = json.loads(ctx.d("outputs/gloss_bank.json").read_text())["bank"]
    pool_words = {w for x in pipeline.accepted_pool(ctx, "A") for w in normalize(x.target).split()}
    assert set(bank["words"]["A"]) == pool_words and bank["separator"] == tok.encode(" =") and bank["newline"] == tok.encode("\n")
    assert all(ids == tok.encode(" " + w) for w, ids in bank["words"]["A"].items())


def test_gloss_icl_prompt_is_stored_segments_only_and_matches_text_for_hand_case() -> None:
    from studies.p10is2.partq import gloss

    lex = {"cat": "katze", "sits": "sitzt"}
    lines = gloss.icl_lines("The cat sits. cat!", lex, {"the", "cat", "sits"})
    assert lines == [("cat", "katze"), ("sits", "sitzt"), ("cat", "katze")]  # source order, repeated words included, "the" has no entry
    assert gloss.icl_prompt_text(lines) == " cat = katze\n sits = sitzt\n cat = katze\n"
    assert gloss.icl_lines("zzz", lex, {"zzz"}) == [] and gloss.icl_prompt_text([]) == ""
    bank = {"separator": [9], "newline": [10], "words": {"A": {"katze": [1, 2], "sitzt": [3]}}, "source_words": {"cat": [7], "sits": [8]}, "source_words_after_newline": {"cat": [10, 7], "sits": [10, 8]}, "last_newline": {"rule": "own-segment"}}
    ids = gloss.icl_prompt_ids(lines, bank, "A")  # the amended rule: the first line as before, every later line begins with the newline stored with its source word, the last newline is its own segment
    assert ids == [7, 9, 1, 2, 10, 8, 9, 3, 10, 7, 9, 1, 2, 10]


def test_item_class_unused_marker() -> None:
    assert Item("a", "a", {}, -1).group == -1


def test_ledger_file_format_is_the_stable_one(tmp_path: Path) -> None:
    from studies.p10is2.common.panel_ledger import LEDGER_FORMAT, RowMap

    rows = ["x" * 300] * 400
    rm = RowMap.from_rows(rows)
    ctx = ctx_of(tmp_path, sizes={**SMALL_SIZES, "gen_marker_like": 44, "gen_ordinary": 100})
    markers = [Span(i * 1000, i * 1000 + 900, i // 3, (i * 1000 + 899) // 300) for i in range(44)]
    cand = [Span(60_000 + i * 150, 60_000 + i * 150 + 100, 200 + i // 2, 200 + i // 2) for i in range(140)]
    p = tmp_path / "ledger.json"
    step8.step_ledger(ctx, p, markers, cand, row_map=rm)
    d = json.loads(p.read_text())
    assert d["format"] == LEDGER_FORMAT == "p10i-panel-ledger-v1" and d["p10is2"]["end_exclusive"] is True and len(d["windows"]) == 144
    w = d["windows"][0]
    assert {"start", "end", "first_row", "last_row", "kind", "owner", "per_row", "stratum", "source"} <= set(w) and w["stratum"] == "marker" and w["per_row"][0][0] == 0
    assert sum(b - a for _, a, b in w["per_row"]) == w["end"] - w["start"]


def test_shared_ledger_keeps_other_studies_entries_verbatim_and_is_written_once(tmp_path: Path) -> None:
    """The file is shared with the longer-training study: its entries (without ``owner``, with ``source``) and its unknown top-level keys survive; this study's windows are written once; a reader needs only the four keys."""
    ctx = ctx_of(tmp_path, sizes={**SMALL_SIZES, "gen_marker_like": 44, "gen_ordinary": 100})
    foreign = {"end": 65, "first_row": 0, "last_row": 0, "source": "P10-I-S3 panel registered", "start": 0}
    p = tmp_path / "shared.json"
    p.write_text(json.dumps({"format": "p10i-panel-ledger-v1", "windows": [foreign], "their_extra": {"x": 1}}))
    markers = [Span(1000 + i * 1000, 1900 + i * 1000, 3, 3) for i in range(44)]
    cand = [Span(60_000 + i * 150, 60_000 + i * 150 + 100, 200, 200) for i in range(140)]
    step8.step_ledger(ctx, p, markers, cand)
    d = json.loads(p.read_text())
    assert d["windows"][0] == foreign and d["their_extra"] == {"x": 1} and len(d["windows"]) == 145
    mine = [w for w in d["windows"] if w.get("owner") == "P10IS2-partq"]
    assert sum(w["stratum"] == "marker" for w in mine) == 44 and sum(w["stratum"] == "ordinary" for w in mine) == 100 and all(isinstance(w[k], int) for w in mine for k in ("start", "end", "first_row", "last_row"))
    with pytest.raises(core.StageRefused, match="written once"):
        step8.step_ledger(ctx, p, markers, cand)
    v = step8.verify_study_ledger(ctx.cfg, p, markers, cand, sizes={"gen_marker_like": 44, "gen_ordinary": 100})
    assert v["verified"] and v["marker_like"] == 44 and v["ordinary"] == 100
    before = p.read_text()
    with pytest.raises(core.StageRefused, match="does not verify"):
        step8.verify_study_ledger(ctx.cfg, p, markers[:43], cand, sizes={"gen_marker_like": 44, "gen_ordinary": 100})
    assert p.read_text() == before  # verification never writes
