# ruff: noqa: E501
"""Part Q recomputation from the stored per-item records (ADR-0025 section 4.4, "Recomputation of Part Q").

It rebuilds the partition from the corpus and the listed seeds, re-reads the STORED teacher batches (no teacher is run), recomputes every per-item chrF, every accept indicator, the grid, Q1, Q2, Q3 and Q4, and
compares with the registered records. A difference of a value of Q1-Q4 beyond 1e-6, or in any accept indicator, is an engineering stop (ENGINEERING STOP — RECOMPUTATION; no label is then derived). The
regeneration of the 32 whole batches per teacher at six threads is ``batches.regeneration_check`` and needs the teachers: the caller runs it and passes its report. This module is a self-check; the independent
recomputation is the auditor's.
"""

from collections.abc import Mapping
from typing import Any

from arborlm.io import read_json
from studies.p10s2.filtering import FilterSetting, accepts

from ..common import core
from . import batches as bt
from . import generation as gen
from . import pipeline, qualify

TOLERANCE = 1e-6


def recompute(ctx: pipeline.QContext, regeneration: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Recompute Q1-Q4 and the accept indicators from the stored batches; returns the comparison record. ``ok`` False means ENGINEERING STOP — RECOMPUTATION."""
    p = pipeline.step_partition(ctx)
    items = p.panels["Q_fit"]
    keys, srcs = [i.key for i in items], [i.en for i in items]
    src_of = dict(zip(keys, srcs, strict=True))
    qf = pipeline._have(ctx, "qfit/record.json")
    if qf is None:
        raise core.StageRefused("refused: no Q_fit record to recompute")
    values = read_json(ctx.d("sealed/qfit_values.json" if ctx.sealed else "qfit/values.json"))
    diffs: list[str] = []
    outs = {}
    for c in core.TASKS:
        stored = [bt.read_batch(ctx.d(f"qfit/teacher_{c}"), i) for i in bt.stored_indices(ctx.d(f"qfit/teacher_{c}"))]
        outs[c] = gen.outputs_of(stored, src_of)
        recorded = values["per_item"][c]
        if len(recorded) != len(outs[c]):
            diffs.append(f"Q_fit teacher {c}: {len(outs[c])} stored outputs, {len(recorded)} recorded")
            continue
        for n, (o, r) in enumerate(zip(outs[c], recorded, strict=True)):
            if o.text != r["text"] or o.score != r["score"]:
                diffs.append(f"Q_fit teacher {c} item {n}: stored batch differs from the per-item record")
    mean: dict[str, dict[str, float]] = {t: {} for t in core.TASKS}
    scores: dict[str, dict[str, list[float]]] = {t: {} for t in core.TASKS}
    for t in core.TASKS:
        for c in core.TASKS:
            scores[t][c] = qualify.item_scores(outs[t], [list(i.refs[c]) for i in items])
            mean[t][c] = sum(scores[t][c]) / len(scores[t][c])
    for t in core.TASKS:
        for c in core.TASKS:
            if abs(mean[t][c] - values["mean_chrf"][t][c]) > TOLERANCE:
                diffs.append(f"mean chrF teacher {t} on {c}: recomputed {mean[t][c]:.9f}, registered {values['mean_chrf'][t][c]:.9f}")
    q1 = qualify.q1({c: mean[c][c] for c in core.TASKS}, ctx.cfg)
    q2 = qualify.q2(mean, values["student"], ctx.cfg)
    if q1 != qf["q1"] or {c: bool(q2[c]["pass"]) for c in core.TASKS} != qf["q2"]:
        diffs.append("Q1 or Q2 verdict differs")
    for c in core.TASKS:
        table = qualify.grid_table(outs[c], scores[c][c], ctx.cfg)
        sel = qualify.select_filter(table, ctx.cfg)
        reg = qf["filter_setting"][c]
        if (None if sel.setting is None else sel.setting.to_json()) != reg:
            diffs.append(f"Q3 teacher {c}: the recomputed setting differs from the registered one")
        for row, rrow in zip(table, values["grid"][c], strict=True):
            if row["accepted"] != rrow["accepted"] or abs((row["wilson_lower"] or 0.0) - (rrow["wilson_lower"] or 0.0)) > TOLERANCE:
                diffs.append(f"grid row tau {row['tau']} rho {row['rho1']}-{row['rho2']} teacher {c}: accepted or Wilson bound differs")
        for n, o in enumerate(outs[c]):
            ind = None if sel.setting is None else accepts(o, sel.setting)
            if ind != values["per_item"][c][n]["accepted"]:
                diffs.append(f"accept indicator differs, teacher {c} item {n}")
        q4 = pipeline._have(ctx, f"qcheck/teacher_{c}/result.json")
        if q4 and q4.get("ran"):
            vals4 = read_json(ctx.d(f"sealed/qcheck_{c}_values.json" if ctx.sealed else f"qcheck/teacher_{c}/values.json"))
            drawn = [it for b in p.reserve_blocks[: q4["stop"]["blocks_drawn"]] for it in b]
            stored = [b for bi in range(q4["stop"]["blocks_drawn"]) for b in (bt.read_batch(ctx.d(f"qcheck/teacher_{c}/block_{bi:03d}"), i) for i in bt.stored_indices(ctx.d(f"qcheck/teacher_{c}/block_{bi:03d}")))]
            o4 = gen.outputs_of(stored, {it.key: it.en for it in drawn})
            s4 = qualify.item_scores(o4, [list(it.refs[c]) for it in drawn])
            if any(abs(a - b) > TOLERANCE for a, b in zip(s4, vals4["per_item_chrf"], strict=True)):
                diffs.append(f"Q_check chrF teacher {c}: a per-item score differs beyond {TOLERANCE}")
            r4 = qualify.precision_on_check(o4, s4, FilterSetting(reg["tau"], reg["rho1"], reg["rho2"]), ctx.cfg)
            if r4["pass"] != q4["pass"] or r4["read_ok"] != q4["read_ok"] or r4["accepted"] != q4["accepted"]:
                diffs.append(f"Q4 verdict or accepted count differs, teacher {c}")
    reg_ok = True if regeneration is None else bool(regeneration.get("ok"))
    if regeneration is not None and not reg_ok:
        diffs.append("regeneration: a token sequence differs from the stored one (QUALIFICATION-ENGINEERING-FAILURE)")
    return {"ok": not diffs, "differences": diffs, "outcome": None if not diffs else "ENGINEERING STOP — RECOMPUTATION", "regeneration_included": regeneration is not None, "tolerance": TOLERANCE}
