# ruff: noqa: E501
"""P10IS0 items (ADR-0023 sections 4.3, 5.2): the work of one registered cell (``run_cell``: train to T with snapshots at the three readouts, evaluate each, write the cell record), of one Stage R cell type
(``stage_r_cell_type``: four runs in doubling rounds, each round resuming from the previous round's snapshot, the plateau rule evaluated after each round by code, every measurement written only to ``sealed/``), and the loader that
turns cell records into the analysis registry. No registered seed is touched by Stage R: it runs on the calibration draws.

Classification of failures (section 12): a divergence is exactly the trainer's own three checks (the cell is a scientific outcome); an out-of-memory or file-system error raises ``adapter.EnvironmentStop`` (PAUSED — ENVIRONMENT); any other
exception propagates as an item error (ENGINEERING STOP). The three are never mixed.
"""

import functools
from collections.abc import Mapping, Sequence
from dataclasses import dataclass as _dataclass
from pathlib import Path
from typing import Any

from arborlm.io import read_json

from . import adapter, analysis, core, ladder, sealed
from .core import Cell, CellType
from .labels import Obs
from .profile import REGISTERED, TEST, Profile


class Env:
    """The inputs a worker needs: the corpus bytes, the backbone, the evaluation rows and the profile (tiny for tests)."""

    def __init__(self, corpus: bytes, backbone: Any, tiny: bool = False, facts_override: int | None = None, profile: Profile | None = None) -> None:
        from studies.p9ii.evaluate import corpus_rows

        self.profile = profile or (TEST if tiny else REGISTERED)
        self.corpus, self.backbone, self.tiny, self.facts_override = corpus, backbone, self.profile.tiny, facts_override
        self.rows = corpus_rows(corpus)

    def facts_of(self, real: int) -> int:
        return self.facts_override or self.profile.facts_of(real)


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


def run_cell(cell: Cell, ct: CellType, t_exposures: int, run_dir: Path, env: Env, cfg: Mapping[str, Any] | None = None, *, spec: core.SetSpec | None = None, diag: tuple[int, int, int] | None = None, reference_swap: bool = False) -> dict[str, Any]:
    """Train one registered cell to T with snapshots at the readouts, evaluate each, and write ``result.json`` (the cell record). A finished cell is not recomputed; a divergence is recorded as ``nonfinite`` with its update;
    a resume restarts from the last snapshot whose hash is recorded."""
    from studies.p9i.train import training_stream_for
    from studies.p9ii.train import load_model_state  # noqa: F401

    c = cfg or core.load_config()
    out = cell_dir(run_dir, cell.label)
    result_path = out / "result.json"
    if result_path.is_file():
        return read_json(result_path)
    spec = spec or core.set_for(cell.role, cell.draw, cell.attempt, c, env.profile.name)
    data = data_for(env, spec, ct.facts, c)
    facts = env.facts_of(ct.facts)
    stream = training_stream_for(data, facts)
    ru = readout_updates(ct, t_exposures) if not env.tiny else readout_updates_tiny(facts, t_exposures, env.profile)
    marks = sorted(set(ru.values()))
    early, late, switch = diag or env.profile.diag or (int(c["draws"]["checkpoint_probe_every"]), int(c["draws"]["checkpoint_probe_every_late"]), int(c["draws"]["checkpoint_probe_switch"]))
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


def readout_updates_tiny(facts: int, t: int, profile: Profile = TEST) -> dict[str, int]:
    """Test profile: updates = exposures x facts / 128 at the tiny fact count, the first readout at the profile's 512."""
    return {"e512": core.updates_for(min(profile.exp(512), t), facts), "half": core.updates_for(t // 2, facts), "T": core.updates_for(t, facts)}


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
# Everything Stage R produces per run (the per-update losses, the probe records, the snapshots, the evaluation counts) goes into the sealed directory (B1); nothing per cell type is public before durations.json exists (B3). One RUN
# (arm, calibration draw) is one unit of work: ``stage_r_run`` trains it to the next ladder exposure, resuming from its previous snapshot, so the driver can run the four runs of a cell type, and the runs of different cell types, in parallel.
# The decision is made by code from the sealed points (``read_state``); the arithmetic of a run does not depend on which process runs it or in what order (a test proves it).
def sealed_stem(ct: CellType) -> str:
    return ct.name.replace("/", "-")


def point_name(ct: CellType, arm: str, draw: int, attempt: int, e: int) -> str:
    return f"{sealed_stem(ct)}-{arm}-c{draw}-r{attempt}-e{e}.json"


def nonfinite_name(ct: CellType, arm: str, draw: int, attempt: int) -> str:
    return f"{sealed_stem(ct)}-{arm}-c{draw}-r{attempt}-nonfinite.json"


def cal_cell(ct: CellType, arm: str, draw: int, attempt: int, cfg: Mapping[str, Any], profile: Profile) -> Cell:
    return core.Cell("CAL", ct.series, arm, ct.facts, ct.slots, draw, core.init_seed("CAL", arm, draw, attempt, cfg, profile.name), attempt)


def stage_r_run(
    ct: CellType, arm: str, draw: int, e: int, sealed_base: Path, env: Env, cfg: Mapping[str, Any] | None = None, *, attempt: int = 0, diag: tuple[int, int, int] | None = None, lad: Sequence[int] | None = None
) -> str:
    """Train one calibration run to ``e`` exposures per fact (from its last snapshot), evaluate there and write the sealed point (or the sealed non-finite record). Returns "ok", "nonfinite" or "present" (already done)."""
    from studies.p9i.train import training_stream_for

    c = cfg or core.load_config()
    lad = list(lad or [env.profile.exp(int(x)) for x in c["ladder"]["base"]])
    sdir = sealed.sealed_dir(sealed_base)
    if (sdir / point_name(ct, arm, draw, attempt, e)).is_file() or (sdir / nonfinite_name(ct, arm, draw, attempt)).is_file():
        return "present"
    early, late, switch = diag or env.profile.diag or (int(c["draws"]["checkpoint_probe_every"]), int(c["draws"]["checkpoint_probe_every_late"]), int(c["draws"]["checkpoint_probe_switch"]))
    facts = env.facts_of(ct.facts)
    cell = cal_cell(ct, arm, draw, attempt, c, env.profile)
    prev = max((x for x in lad if x < e and (sdir / point_name(ct, arm, draw, attempt, x)).is_file()), default=0)
    out = sdir / "cal" / cell.label
    spec = core.calibration_set(draw, attempt, c, env.profile.name)
    data = data_for(env, spec, ct.facts, c)
    stream = training_stream_for(data, facts)
    u = core.updates_for(e, facts)
    snap = out / "snapshots" / f"u{core.updates_for(prev, facts):07d}" if prev else None
    seg = adapter.run_segment(adapter.Job(cell, data, stream, env.backbone, out, data.seeds.r1_codes, last_update=u, snapshots=(u,), init_snapshot=snap, diag_early=early, diag_late=late, diag_switch=switch))
    if seg.diverged is not None:
        sealed.write_sealed(sealed_base, nonfinite_name(ct, arm, draw, attempt), {"diverged": seg.diverged})
        return "nonfinite"
    rec = adapter.evaluate_snapshot(cell, out / "snapshots" / f"u{u:07d}", data, facts, u, backbone=env.backbone, rows=env.rows, r1_seed=data.seeds.r1_codes, swap_seed=spec.swap_seed(ct.facts, c), reference_swap=arm == "A6")
    sealed.write_sealed(sealed_base, point_name(ct, arm, draw, attempt, e), {"obs": obs_to_json(adapter.counts_of(rec)["obs"]), "exposures": e})
    return "ok"


@_dataclass
class RState:
    decision: ladder.Decision
    curves: dict[tuple[str, int], ladder.Curve]
    obs_at: dict[tuple[tuple[str, int], int], Obs]


def read_state(ct: CellType, sealed_base: Path, th: core.Thresholds, cfg: Mapping[str, Any], profile: Profile, *, attempt: int = 0, lad: Sequence[int] | None = None, ceiling: int | None = None) -> RState:
    """The plateau rule applied by code to the sealed points of a cell type. The reads are the code's own (``stage-r-code``); no person reads them."""
    c = cfg
    base = [profile.exp(int(x)) for x in c["ladder"]["base"]]
    lad = list(lad or base)
    top = ceiling or max(lad)
    sdir = sealed.sealed_dir(sealed_base)
    curves = {k: ladder.Curve(k[0], k[1]) for k in ladder.RUN_KEYS}
    obs_at: dict[tuple[tuple[str, int], int], Obs] = {}
    for key, cv in curves.items():
        arm, draw = key
        nf = nonfinite_name(ct, arm, draw, attempt)
        if (sdir / nf).is_file():
            cv.nonfinite_update = int(sealed.read_sealed(sealed_base, nf, reader="stage-r-code", why="decision")["diverged"]["update"])
        for e in [x for x in lad if x <= top]:
            nm = point_name(ct, arm, draw, attempt, e)
            if (sdir / nm).is_file():
                o = obs_from_json(sealed.read_sealed(sealed_base, nm, reader="stage-r-code", why="decision")["obs"])
                obs_at[(key, e)] = o
                cv.points[e] = ladder.Point(o.m_p, o.m_h)
    # the barrier of ruling 11: the plateau rule reads a round only once every run has it (a run that diverged does not hold the others back)
    live = [cv for cv in curves.values() if cv.nonfinite_update is None]
    barrier = min((max(cv.points, default=0) for cv in live), default=0)
    for cv in live:
        cv.points = {e: p for e, p in cv.points.items() if e <= barrier}
    decision = ladder.decide_cell_type(curves, ct.floor(th), top, th, lad, cfg=c, base_top=base[-1], t_values=_t_values(profile, c))
    return RState(decision, curves, obs_at)


def stage_r_needs(state: RState, lad: Sequence[int], profile: Profile, cfg: Mapping[str, Any], *, ceiling: int | None = None) -> list[tuple[str, int, int]]:
    """The (arm, draw, e) runs still to train. UNDECIDED: every run to the next ladder value. NON_FINITE (B2): the surviving runs continue, one ladder value at a time, to the base ceiling T so that the reference flags can be computed
    there. Anything else: none."""
    d = state.decision
    top = ceiling or max(lad)
    live = {k: cv for k, cv in state.curves.items() if cv.nonfinite_update is None}
    out: list[tuple[str, int, int]] = []
    if d.status == ladder.STATUS_UNDECIDED:
        reached = {k: max((e for (kk, e) in state.obs_at if kk == k), default=0) for k in live}
        nxt = next((x for x in lad if x > min(reached.values(), default=0) and x <= top), None)
        if nxt is not None:
            out = [(k[0], k[1], nxt) for k in live if reached[k] < nxt]
    elif d.status == ladder.STATUS_NONFINITE:
        stop = _t_values(profile, cfg)[0]
        for k in live:
            r = max((e for (kk, e) in state.obs_at if kk == k), default=0)
            if r < stop:
                nxt = next((x for x in lad if x > r), None)
                if nxt is not None:
                    out.append((k[0], k[1], nxt))
    return out


def stage_r_flags(state: RState, ct: CellType, th: core.Thresholds) -> dict[str, Any]:
    """The reference flags at the cell type's final T (rulings 3 and 4). ``computed`` is False, explicitly, when no A6 run has a usable point there (both diverged, or both below the floor): an empty flag set is never a silent result (B2)."""
    d = state.decision
    if d.t is None:
        return {"reference_flags": None, "computed": False, "reference_below_floor_at_t": [], "reference_nonfinite": False}
    t_obs = {draw: state.obs_at.get((("A6", draw), d.t)) for draw in (1, 2)}
    refl, info = ladder.reference_flags(t_obs, ct.floor(th), th)
    nonf = [draw for draw in (1, 2) if state.curves[("A6", draw)].nonfinite_update is not None]
    return {
        "reference_flags": {"cond4": refl.cond4, "other": list(refl.other)}, "computed": bool(info["computed_on_draws"]), "reference_below_floor_at_t": info["reference_below_floor_at_t_draws"],
        "reference_nonfinite": len(nonf) == 2, "reference_nonfinite_draws": nonf,
    }  # fmt: skip


def stage_r_cell_type(
    ct: CellType, sealed_base: Path, env: Env, th: core.Thresholds, cfg: Mapping[str, Any] | None = None, *, attempt: int = 0, ladder_values: Sequence[int] | None = None, ceiling: int | None = None, diag: tuple[int, int, int] | None = None
) -> dict[str, Any]:
    """The sequential reference of Stage R for one cell type: the same ``stage_r_run`` calls the driver farms out to workers, in order, with the decision by code after each round. Used by tests and single-process runs; the driver runs the same
    runs in parallel and a test shows the sealed points are identical."""
    c = cfg or core.load_config()
    lad = list(ladder_values or [env.profile.exp(int(x)) for x in c["ladder"]["base"]])
    top = ceiling or max(lad)
    while True:
        state = read_state(ct, sealed_base, th, c, env.profile, attempt=attempt, lad=lad, ceiling=top)
        todo = stage_r_needs(state, lad, env.profile, c, ceiling=top)
        if not todo:
            break
        for arm, draw, e in todo:
            stage_r_run(ct, arm, draw, e, sealed_base, env, c, attempt=attempt, diag=diag, lad=lad)
    flags = stage_r_flags(state, ct, th)
    return {"decision": state.decision, **flags, "curves": state.curves}


def _t_values(profile: Profile, c: Mapping[str, Any]) -> tuple[int, int]:
    """T at the base ceiling and at the extended ceiling in this profile's exposures."""
    return profile.exp(int(c["ladder"]["base_ceiling_t"])), profile.exp(int(c["ladder"]["extended_ceiling_t"]))
