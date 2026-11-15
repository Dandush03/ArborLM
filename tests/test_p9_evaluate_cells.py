# ruff: noqa: E501
"""P9 package I3, ``studies/p9/evaluate.py``: ``evaluate_snapshot`` records for every rung and the dense
adapter, LEAKAGE on a constructed leak, determinism, trace export, and the ``evaluate_cell`` snapshot
schedule. Tiny sizes, random frozen backbone, test seeds (>= 179001); nothing registered, no stage.

Self-check only: not independent review, not Astra validation, not human approval.
"""

import json
import math
from pathlib import Path

import pytest
import torch
from test_p9_evaluate_support import (
    FACTS,
    draw,
    fit_fixed_selection,
    lut_for,
    make_model,
    nomem_of,
    r2_fixture,
    trained_mask,
)
from test_p9_evaluate_support import cell as cell_of

from studies.p9 import controls, core, evaluate
from studies.p9.core import EvalRecord

SEED = 179601
CASES = [
    ("A1", {"arch": "flat", "slots": 4096, "seed": 1701}, False),
    ("A2", {"slots": 4096, "seed": 1701}, False),
    ("A3", {"seed": 1701}, False),
    ("A5", {"rung": "R1", "slots": 4096, "seed": 1701}, False),
    ("A5", {"rung": "R2", "slots": 4096, "seed": 1701}, True),
    ("A5b", {"slots": 16384, "seed": 1701}, False),
    ("A6", {"rung": "OB", "seed": 1701}, False),
    ("A7", {"slots": 16384, "rung": "R0", "seed": 1701}, False),
    ("A8", {"slots": 4096, "seed": 1701}, False),
]
RECORD_KEYS = set(EvalRecord.__annotations__)


def run_snapshot(
    c: core.Cell,
    model,
    run_dir: Path,
    *,
    stream_name: str = "panel_a",
    interventions: bool = True,
    traces: bool = False,
    update: int = 32,
    seed: int = SEED,  # type: ignore[no-untyped-def]
) -> EvalRecord:
    d = draw()
    stream = d.streams[stream_name]
    return evaluate.evaluate_snapshot(
        c,
        run_dir,
        update,
        stream,
        d,
        model,
        nomem=nomem_of(model, stream),
        interventions=interventions,
        write_traces=traces,
        seed=seed,
    )


def build(c: core.Cell):  # type: ignore[no-untyped-def]
    lut = lut_for(draw().facts) if c.rung == "R2" else None
    return make_model(c, lut=lut)


@pytest.mark.parametrize(
    ("block", "match", "_r2"),
    CASES,
    ids=[f"{b}-{m.get('rung', m.get('arch', ''))}" for b, m, _ in CASES],
)
def test_every_rung_and_dense_run_and_write_valid_records(
    block: str, match: dict[str, object], _r2: bool, tmp_path: Path
) -> None:
    c = cell_of(block, **match)
    model = build(c)
    rec = run_snapshot(c, model, tmp_path, traces=True)
    assert set(rec) == RECORD_KEYS
    path = core.eval_path(tmp_path, c.label, 32, "panel_a")
    on_disk = core.read_record(path, "eval")
    assert on_disk == json.loads(
        json.dumps(rec)
    )  # the file is exactly the record (no NaN, JSON clean)
    assert rec["facts"] == FACTS and rec["unseen_facts"] == 32
    assert 0 <= rec["correct"] <= FACTS and rec["accuracy"] == rec["correct"] / FACTS
    assert rec["information_bits"] >= 0.0 and math.isfinite(rec["logloss_gain_bits"])
    assert 0.0 <= rec["mass_outside_alphabet_mean"] <= 1.0
    assert (tmp_path / rec["per_fact_file"]).is_file() if rec["per_fact_file"] else False
    assert rec["disabled_accuracy"] is not None
    if c.arch == "dense":
        assert (
            rec["useful_slots"] is None
            and rec["value_permuted_accuracy"] is None
            and rec["usage"]["dense"] is True
            and rec["usage"]["slots"] == 0
            and "distinct" not in rec["usage"]
        )
        assert not core.trace_path(tmp_path, c.label, 32, "panel_a", "answer").exists()
    else:
        assert rec["value_permuted_accuracy"] is not None and rec["useful_slots"] is not None
        assert (
            rec["ustar_interpretable"] in (True, False)
            and "condition_2_max_drop" in rec["specificity"]
        )
        assert rec["usage"]["answer_site_queries"] == FACTS and rec["usage"]["slots"] == c.slots
    if c.rung == "R2":
        assert rec["usage"]["distinct"] == FACTS and "entropy_soft" not in rec["usage"]
        assert not core.trace_path(
            tmp_path, c.label, 32, "panel_a", "answer"
        ).exists()  # R2 reads one slot, no top-8 trace
    elif c.arch != "dense":
        for kind in ("answer", "all"):
            assert core.trace_path(tmp_path, c.label, 32, "panel_a", kind).is_file()
    if c.rung in ("R0", "R0a", "R1", "OB") and c.arch != "dense":
        assert rec["usage"]["entropy_soft"] > 0.0 and rec["usage"]["soft_mass_outside_top8"] > 0.0
    # without interventions the intervention fields are empty and nothing else changes
    plain = run_snapshot(c, model, tmp_path, interventions=False, update=16)
    assert (
        plain["useful_slots"] is None
        and plain["value_permuted_accuracy"] is None
        and plain["disabled_accuracy"] is None
    )
    assert plain["specificity"] == {} and plain["mean_support_length"] is None
    assert (
        plain["correct"] == rec["correct"]
        and plain["logloss_gain_bits"] == rec["logloss_gain_bits"]
    )


def test_record_values_on_a_memory_that_knows_every_fact(tmp_path: Path) -> None:
    model, cache, c = r2_fixture()
    rec = run_snapshot(c, model, tmp_path)
    assert rec["correct"] == FACTS and rec["accuracy"] == 1.0
    assert rec["information_bits"] == pytest.approx(5.0 * FACTS)  # e = 0: 5 bits per fact
    scores = evaluate.score_cache(cache, cache.stream.answer_targets().reshape(-1))
    tr = trained_mask(cache)
    expect = float((5.0 + torch.log2(scores.p_correct[tr].double())).sum())
    assert rec["logloss_gain_bits"] == pytest.approx(expect, rel=1e-4)
    assert rec["unseen_facts"] == 32 and rec["leakage"] is False
    assert rec["unseen_correct"] <= core.chance_interval(32, 8).high
    assert rec["value_permuted_accuracy"] * FACTS <= core.chance_interval(FACTS, 8).high
    assert rec["disabled_accuracy"] * FACTS <= core.chance_interval(FACTS, 8).high
    assert rec["ustar_interpretable"] is True and rec["mean_support_length"] == 1.0
    assert rec["useful_slots"] >= 100 and rec["share_correct_with_support"] >= 0.95
    assert (
        rec["share_stay_correct_without_site_read"] <= 0.05
    )  # removing the site read breaks (almost) every fact
    assert (
        rec["accuracy_with_neighbour"] is not None or rec["accuracy_without_neighbour"] is not None
    )
    fact_acc = [
        a
        for a in (rec["accuracy_with_neighbour"], rec["accuracy_without_neighbour"])
        if a is not None
    ]
    assert all(a == 1.0 for a in fact_acc)
    per_fact = torch.load(tmp_path / rec["per_fact_file"], weights_only=True)
    assert per_fact["support_length"].shape == per_fact["correct"].shape
    assert rec["usage"]["per_fact_median"]["p_correct"] > 0.0


def test_constructed_leak_sets_the_leakage_flag(tmp_path: Path) -> None:
    """A memory fitted on the unseen facts too (their identifiers have slots and trained values) answers
    them: unseen accuracy outside the G2 interval, LEAKAGE true; the honest memory is inside it."""
    d = draw()
    c = cell_of("A5", rung="R2", slots=4096, seed=1701)
    model = make_model(c, lut=lut_for(d.facts, FACTS + 32))  # unseen identifiers get slots 128..159
    stream = d.streams["panel_a"]
    cache = evaluate.build_cache(model, stream)
    fit_fixed_selection(model, cache, steps=500)
    leaky = run_snapshot(c, model, tmp_path)
    assert leaky["unseen_correct"] > core.chance_interval(32, 8).high
    assert leaky["leakage"] is True
    honest_model, _, c2 = r2_fixture()
    honest = run_snapshot(c2, honest_model, tmp_path / "honest")
    assert honest["leakage"] is False


def test_evaluation_is_deterministic_and_the_seed_only_moves_the_interventions(
    tmp_path: Path,
) -> None:
    model, _, c = r2_fixture()
    a = run_snapshot(c, model, tmp_path / "a", seed=SEED)
    b = run_snapshot(c, model, tmp_path / "b", seed=SEED)
    assert a == b
    pa = torch.load(tmp_path / "a" / a["per_fact_file"], weights_only=True)
    pb = torch.load(tmp_path / "b" / b["per_fact_file"], weights_only=True)
    assert all(torch.equal(pa[k], pb[k]) for k in pa)
    other = run_snapshot(c, model, tmp_path / "c", seed=SEED + 1)
    for key in (
        "correct",
        "information_bits",
        "logloss_gain_bits",
        "useful_slots",
        "mean_support_length",
    ):
        assert other[key] == a[key]  # supports do not depend on the seed


def test_trace_export_round_trips_and_matches_the_selections(tmp_path: Path) -> None:
    c = cell_of("A2", slots=4096, seed=1701)  # learned tree: branches are traced
    model = build(c)
    stream = draw().streams["panel_a"]
    cache = evaluate.build_cache(model, stream)
    sel = cache.selection
    assert sel is not None and sel.branches is not None
    written = evaluate.export_traces(c, 32, cache, tmp_path)
    assert set(written) == {"answer", "all"}
    n_ctx = stream.tokens.shape[0]
    for kind, (path, sha) in written.items():
        assert path == core.trace_path(tmp_path, c.label, 32, "panel_a", kind)
        tr = core.read_trace(path, expected_sha256=sha)
        assert (tr.label, tr.update, tr.stream, tr.kind, tr.slots) == (
            c.label,
            32,
            "panel_a",
            kind,
            4096,
        )
        per = 8 if kind == "answer" else 63
        assert (
            tr.selected.shape == (n_ctx * per, 8)
            and tr.branches is not None
            and tr.branches.shape == (n_ctx * per, 2)
        )
        assert torch.equal(tr.context, torch.arange(n_ctx).repeat_interleave(per))
        if kind == "answer":
            assert bool((tr.position % 8 == 6).all()) and torch.equal(
                tr.position[:8], torch.tensor(core.ANSWER_SITE_POSITIONS)
            )
        else:
            assert torch.equal(tr.position[:63], torch.arange(63))
        # the rows are the cached selections, position by position
        cols = [int(p) for p in tr.position[:per]]
        expected = sel.selected[:, cols].reshape(-1, 8)
        assert torch.equal(tr.selected, expected)
        assert torch.equal(tr.branches, sel.branches[:, cols].reshape(-1, 2))
        assert torch.equal(tr.fact, stream.fact_ids[tr.context, tr.position // 8])
        assert torch.equal(tr.cluster, stream.cluster[tr.context])
    answer = core.read_trace(written["answer"][0])
    unseen_rows = answer.fact >= FACTS
    assert int(unseen_rows.sum()) == 32 and bool((answer.cluster[unseen_rows] == -1).all())
    assert bool((answer.cluster[~unseen_rows] >= 0).all())
    assert evaluate.trace_from_cache(c, 32, cache, "answer").selected.dtype == torch.int64
    # a flat memory has no branches; the dense adapter and R2 cannot be traced
    flat = evaluate.build_cache(build(cell_of("A1", arch="flat", slots=4096, seed=1701)), stream)
    assert evaluate.trace_from_cache(c, 32, flat, "all").branches is None
    with pytest.raises(ValueError):
        evaluate.trace_from_cache(
            c,
            32,
            evaluate.build_cache(build(cell_of("A8", slots=4096, seed=1701)), stream),
            "answer",
        )
    with pytest.raises(ValueError):
        evaluate.trace_from_cache(c, 32, flat, "bogus")


def test_evaluate_cell_runs_the_intervention_schedule(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A cell of 128 facts at E = 32: snapshots U/2 = 16 and U = 32 (matched) and 1,024 / 2,048 (fixed
    compute). Interventions only at 32 and 2,048; traces only at 32. Snapshot files are written in
    ``train.save_snapshot``'s model format; the backbone loader is replaced by the random test backbone."""
    c = cell_of("A1", arch="flat", slots=4096, seed=1701)
    model = build(c)
    for update in core.snapshots(c, 32):
        folder = core.snapshot_dir(tmp_path, c.label, update)
        folder.mkdir(parents=True)
        torch.save(
            {"update": update, "label": c.label, "model": model.state_dict()}, folder / "model.pt"
        )
    monkeypatch.setattr(controls, "load_backbone", lambda parent, root=None: (model.backbone, {}))
    d = draw()
    records = evaluate.evaluate_cell(c, tmp_path, d, tmp_path, 32, secondary=True)
    assert core.snapshots(c, 32) == (16, 32, 1024, 2048)
    by = {(r["update"], r["stream"]): r for r in records}
    for update in (16, 32, 1024, 2048):
        for stream in ("panel_a", "panel_b"):
            rec = by[(update, stream)]
            deep = update in (32, 2048)
            assert (rec["useful_slots"] is not None) == deep and (
                rec["disabled_accuracy"] is not None
            ) == deep
            assert core.eval_path(tmp_path, c.label, update, stream).is_file()
    assert {(u, s) for (u, s) in by if s in ("h1", "h2", "mixed")} == {
        (u, s) for u in (32, 2048) for s in ("h1", "h2", "mixed")
    }
    assert all(
        by[(u, s)]["useful_slots"] is None
        for (u, s) in by
        if s in ("h1", "h2", "mixed", "calibration")
    )
    assert (32, "calibration") in by and (2048, "calibration") not in by
    for stream in ("panel_a", "panel_b", "calibration"):
        for kind in ("answer", "all"):
            assert core.trace_path(tmp_path, c.label, 32, stream, kind).is_file()
            assert not core.trace_path(tmp_path, c.label, 2048, stream, kind).exists()
    # the same model at every snapshot: knowledge metrics agree across snapshots
    assert len({by[(u, "panel_a")]["correct"] for u in (16, 32, 1024, 2048)}) == 1
    # a non-trace block writes no traces; Lane D has no fixed-compute snapshot
    lane_d = next(x for x in core.cells() if x.lane_d_arm == "sequential" and x.arch == "flat")
    assert core.snapshots(lane_d, 32) == (core.updates(lane_d, 32) // 2, core.updates(lane_d, 32))


def test_the_command_line_refuses_rehearsal_mode() -> None:
    with pytest.raises(SystemExit):
        evaluate.main(["cell", "--label", "x", "--run-dir", "y", "--mode", "rehearsal"])
