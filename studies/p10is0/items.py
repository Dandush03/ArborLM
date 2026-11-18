# ruff: noqa: E501
"""P10IS0 items (ADR-0023 sections 4.3, 5.2): the work of one registered cell (``run_cell``: train to T with snapshots at the three readouts, evaluate each, write the cell record), of one Stage R cell type
(``stage_r_cell_type``: four runs in doubling rounds, each round resuming from the previous round's snapshot, the plateau rule evaluated after each round by code, every measurement written only to ``sealed/``), and the loader that
turns cell records into the analysis registry. No registered seed is touched by Stage R: it runs on the calibration draws.

Classification of failures (section 12): a divergence is exactly the trainer's own three checks (the cell is a scientific outcome); an out-of-memory or file-system error raises ``adapter.EnvironmentStop`` (PAUSED — ENVIRONMENT); any other
exception propagates as an item error (ENGINEERING STOP). The three are never mixed.
"""

import functools
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from arborlm.io import read_json

from . import adapter, analysis, core, ladder, sealed
from .core import Cell, CellType
from .labels import Obs


class Env:
    """The inputs a worker needs: the corpus bytes, the backbone, the evaluation rows (tiny for tests)."""

    def __init__(self, corpus: bytes, backbone: Any, tiny: bool = False, facts_override: int | None = None) -> None:
        from studies.p9ii.evaluate import corpus_rows

        self.corpus, self.backbone, self.tiny, self.facts_override = corpus, backbone, tiny, facts_override
        self.rows = corpus_rows(corpus)

    def facts_of(self, real: int) -> int:
        return self.facts_override or real


@functools.cache
def _data(seed_block: Any, corpus: bytes, facts: int, tiny: bool) -> Any:
    return adapter.build_data(seed_block, corpus, facts, tiny=tiny)


def data_for(env: Env, spec: core.SetSpec, real_facts: int, cfg: Mapping[str, Any] | None = None) -> Any:
    return _data(spec.block(real_facts, cfg), env.corpus, env.facts_of(real_facts), env.tiny)


def obs_to_json(o: Obs) -> dict[str, Any]:
    return {
        "a": list(o.a), "b": list(o.b), "h1": list(o.h1), "h2": list(o.h2), "dep_chance_a": o.dep_chance_a, "dep_chance_b": o.dep_chance_b, "leakage": o.leakage, "distinct_top1": o.distinct_top1, "largest_share": o.largest_share,
        "probe_facts": o.probe_facts, "lm_rise": o.lm_rise, "address_stability": o.address_stability, "a_use_a": o.a_use_a, "a_use_b": o.a_use_b,
    }  # fmt: skip


def obs_from_json(d: Mapping[str, Any]) -> Obs:
    nan = float("nan")
    f = lambda k: nan if d.get(k) is None else float(d[k])  # noqa: E731
    return Obs((int(d["a"][0]), int(d["a"][1])), (int(d["b"][0]), int(d["b"][1])), (int(d["h1"][0]), int(d["h1"][1])), (int(d["h2"][0]), int(d["h2"][1])), bool(d["dep_chance_a"]), bool(d["dep_chance_b"]), bool(d["leakage"]),
               int(d["distinct_top1"]), f("largest_share"), int(d["probe_facts"]), f("lm_rise"), f("address_stability"), f("a_use_a"), f("a_use_b"))  # fmt: skip


def readout_updates(ct: CellType, t: int) -> dict[str, int]:
    """e512, T/2 and T in updates (ruling 6: where e* = 512, T/2 = 512 exposures and the evaluation is made once and recorded under both names)."""
    return {"e512": ct.updates(512), "half": ct.updates(t // 2), "T": ct.updates(t)}


def cell_dir(run_dir: Path, label: str) -> Path:
    return run_dir / "cells" / label


def run_cell(cell: Cell, ct: CellType, t_exposures: int, run_dir: Path, env: Env, cfg: Mapping[str, Any] | None = None, *, diag: tuple[int, int, int] | None = None, reference_swap: bool = False) -> dict[str, Any]:
    """Train one registered cell to T with snapshots at the readouts, evaluate each, and write ``result.json`` (the cell record). A finished cell is not recomputed; a divergence is recorded as ``nonfinite`` with its update;
    a resume restarts from the last snapshot whose hash is recorded."""
    from studies.p9i.train import training_stream_for
    from studies.p9ii.train import load_model_state  # noqa: F401

    c = cfg or core.load_config()
    out = cell_dir(run_dir, cell.label)
    result_path = out / "result.json"
    if result_path.is_file():
        return read_json(result_path)
    spec = core.set_for(cell.role, cell.draw, cell.attempt, c)
    data = data_for(env, spec, ct.facts, c)
    facts = env.facts_of(ct.facts)
    stream = training_stream_for(data, facts)
    ru = readout_updates(ct, t_exposures) if not env.tiny else readout_updates_tiny(facts, t_exposures)
    marks = sorted(set(ru.values()))
    early, late, switch = diag or (int(c["draws"]["checkpoint_probe_every"]), int(c["draws"]["checkpoint_probe_every_late"]), int(c["draws"]["checkpoint_probe_switch"]))
    hashes: dict[str, str] = {}
    resume: Path | None = None
    start = 0
    for tr in sorted(out.glob("train_*.json")):
        rec = core.read_record(tr, "train")
        hashes.update(rec["snapshot_sha256"])
        if rec["status"] == "diverged":
            return _write_result(result_path, cell, "nonfinite", {}, rec["diverged"]["update"])
    for m in marks:
        if str(m) in hashes and (out / "snapshots" / f"u{m:07d}" / "model.pt").is_file():
            resume, start = out / "snapshots" / f"u{m:07d}", m
    job = adapter.Job(cell, data, stream, env.backbone, out, data.seeds.r1_codes, last_update=marks[-1], snapshots=tuple(m for m in marks if m > start), init_snapshot=resume, diag_early=early, diag_late=late, diag_switch=switch)
    seg = adapter.run_segment(job)
    hashes.update(seg.record["snapshot_sha256"])
    if seg.diverged is not None:
        return _write_result(result_path, cell, "nonfinite", {}, seg.diverged["update"])
    readouts: dict[str, Any] = {}
    cache: dict[int, dict[str, Any]] = {}
    for name, u in ru.items():
        if u not in cache:
            snap = out / "snapshots" / f"u{u:07d}"
            rec = adapter.evaluate_snapshot(cell, snap, data, facts, u, backbone=env.backbone, rows=env.rows, r1_seed=data.seeds.r1_codes, swap_seed=spec.swap_seed(ct.facts, c), expected_sha256=hashes[str(u)], reference_swap=reference_swap)
            cache[u] = adapter.counts_of(rec)
        readouts[name] = obs_to_json(cache[u]["obs"])
    return _write_result(result_path, cell, "ok", readouts, None)


def readout_updates_tiny(facts: int, t: int) -> dict[str, int]:
    """Tests: updates = exposures x facts / 128 at the tiny fact count."""
    return {"e512": core.updates_for(min(512, t), facts), "half": core.updates_for(t // 2, facts), "T": core.updates_for(t, facts)}


def _write_result(path: Path, cell: Cell, status: str, readouts: Mapping[str, Any], nonfinite_update: int | None) -> dict[str, Any]:
    rec = {**core.envelope("eval"), "label": cell.label, "status": status, "readouts": dict(readouts), "nonfinite_update": nonfinite_update}
    core.write_record(path, rec)
    return rec


def load_registry(run_dir: Path, cells: Sequence[Mapping[str, Any]]) -> tuple[dict[analysis.Key, analysis.CellRecord], list[str]]:
    """The analysis registry from the cell records of the plan's items; an item without ``result.json`` is simply absent (step 0's business); an unreadable record is an item error."""
    reg: dict[analysis.Key, analysis.CellRecord] = {}
    errors: list[str] = []
    for it in cells:
        p = cell_dir(run_dir, it["label"]) / "result.json"
        if not p.is_file():
            continue
        try:
            rec = core.read_record(p, "eval")
            ro = {k: obs_from_json(v) for k, v in rec["readouts"].items()}
            reg[(it["cell_type"], it["arm"], int(it["draw"]))] = analysis.CellRecord(rec["status"], ro, rec.get("nonfinite_update"))
        except Exception as exc:  # an unreadable record is an item error, never a label
            errors.append(f"{it['label']}: {type(exc).__name__}")
    return reg, errors


# --- Stage R (section 5.2) ----------------------------------------------------------------------------------------------------------------------
def stage_r_cell_type(
    ct: CellType, run_dir: Path, env: Env, th: core.Thresholds, cfg: Mapping[str, Any] | None = None, *, attempt: int = 0, ladder_values: Sequence[int] | None = None, ceiling: int | None = None, diag: tuple[int, int, int] | None = None
) -> dict[str, Any]:
    """The four runs of a cell type (A5-D and A6, calibration draws 1 and 2) train in doubling rounds, each resuming from the previous round's snapshot; after each round (the barrier of ruling 11) the plateau rule is evaluated
    by code; the cell type stops at the first decision or at its ceiling. Every measurement goes to ``sealed/``; the return value holds only what ``durations.json`` may hold (no accuracy)."""
    from studies.p9i.train import training_stream_for

    c = cfg or core.load_config()
    lad = list(ladder_values or c["ladder"]["base"])
    top = ceiling or max(lad)
    early, late, switch = diag or (int(c["draws"]["checkpoint_probe_every"]), int(c["draws"]["checkpoint_probe_every_late"]), int(c["draws"]["checkpoint_probe_switch"]))
    facts = env.facts_of(ct.facts)
    curves = {k: ladder.Curve(k[0], k[1]) for k in ladder.RUN_KEYS}
    cells = {k: core.Cell("CAL", ct.series, k[0], facts if env.tiny else ct.facts, ct.slots, k[1], core.init_seed("CAL", k[0], k[1], attempt, c), attempt) for k in ladder.RUN_KEYS}
    last: dict[tuple[str, int], int] = dict.fromkeys(ladder.RUN_KEYS, 0)
    obs_at: dict[tuple[tuple[str, int], int], Obs] = {}
    decision = ladder.Decision(ladder.STATUS_UNDECIDED)
    for e in [x for x in lad if x <= top]:
        for key, cell in cells.items():
            spec = core.calibration_set(key[1], attempt, c)
            data = data_for(env, spec, ct.facts, c)
            stream = training_stream_for(data, facts)
            u = core.updates_for(e, facts)
            out = run_dir / "cal" / cell.label
            snap = out / "snapshots" / f"u{last[key]:07d}" if last[key] else None
            seg = adapter.run_segment(adapter.Job(cell, data, stream, env.backbone, out, data.seeds.r1_codes, last_update=u, snapshots=(u,), init_snapshot=snap, diag_early=early, diag_late=late, diag_switch=switch))
            if seg.diverged is not None:
                curves[key].nonfinite_update = seg.diverged["update"]
                sealed.write_sealed(run_dir, f"{ct.name.replace('/', '-')}-{key[0]}-c{key[1]}-r{attempt}-nonfinite.json", {"diverged": seg.diverged})
                continue
            last[key] = u
            rec = adapter.evaluate_snapshot(cell, out / "snapshots" / f"u{u:07d}", data, facts, u, backbone=env.backbone, rows=env.rows, r1_seed=data.seeds.r1_codes, swap_seed=spec.swap_seed(ct.facts, c), reference_swap=key[0] == "A6")
            o = adapter.counts_of(rec)["obs"]
            obs_at[(key, e)] = o
            curves[key].points[e] = ladder.Point(o.m_p, o.m_h)
            sealed.write_sealed(run_dir, f"{ct.name.replace('/', '-')}-{key[0]}-c{key[1]}-r{attempt}-e{e}.json", {"obs": obs_to_json(o), "exposures": e})
        decision = ladder.decide_cell_type(curves, ct.floor(th), top, th, lad, cfg=c)
        if decision.status != ladder.STATUS_UNDECIDED:
            break
    flags: dict[str, Any] = {}
    refl = labels_flags = None
    if decision.t is not None:
        t_obs = {d: obs_at.get((("A6", d), decision.t)) for d in (1, 2)}
        refl, info = ladder.reference_flags(t_obs, ct.floor(th), th)
        labels_flags = {"cond4": refl.cond4, "other": list(refl.other)}
        flags = {"reference_below_floor_at_t": info["reference_below_floor_at_t_draws"], "reference_nonfinite": any(curves[("A6", d)].nonfinite_update is not None for d in (1, 2))}
    return {"decision": decision, "reference_flags": labels_flags, **flags, "curves": curves}
