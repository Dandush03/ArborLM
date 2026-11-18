# ruff: noqa: E501
"""P10IS1 real calibration engine and the ``calibrate`` command (ADR-0024 section 7). The engine trains and evaluates calibration cells through the adapter on the registry's calibration seeds ONLY (249001 with 330191,
249101 with 330193: ``adapter.assert_seed_allowed('calibration', ...)`` refuses anything else), blind to every registered seed, in the fixed order ``calibrate.run_calibration`` gives (rates at a provisional readout, U_P per
row, one re-selection at U_P, loaded-cell units at 65,536, then the ladder search and H8). Runs of one (cell, rate, draw) are CONTINUED, never restarted: the cell's label carries one horizon, the runs are segments that
resume from the optimizer snapshot (gate G4: a resumed run equals an uninterrupted one bit for bit). All item records (train snapshots, evaluation counts) go into the SEALED directory; the public record is built from the
whitelist (``sealed``). A diverged run (a non-finite value, a run that ended failed, or a raw Panel A correct count inside the G2 chance interval at the readout on either draw) is recorded and left out of the selection.
The scale of a test is the config's: a tiny config shrinks every length, and ``facts_map`` shrinks the fact counts; the rules are the same."""

import argparse
import json
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

from . import adapter, calibrate, core, items, sealed
from .calibrate import RateRun

CAL_DRAWS = (1, 2)


def pow2_points(readouts: Sequence[int]) -> set[int]:
    """readout / 2^k (k = 0..4) of every readout: the snapshots the selections and the tie walk read."""
    return {r // d for r in readouts for d in (1, 2, 4, 8, 16) if r % d == 0 and r // d >= 1}


class RealEngine:
    """Trains and evaluates calibration cells; implements ``calibrate.Engine``. ``ctx`` has ``run_dir`` = the sealed directory."""

    def __init__(self, ctx: items.Ctx, cfg: Mapping[str, Any] | None = None, facts_map: Mapping[int, int] | None = None) -> None:
        self.ctx, self.cfg = ctx, core.cfg_of(cfg)
        self.facts_map = dict(facts_map or {})
        c = self.cfg
        self.readouts = sorted({*(int(v) for v in c["rates"]["provisional_readout"].values()), *(int(x) for x in c["ladder"]["u_p_candidates"]), int(c["rates"]["loaded_readout"])})
        self.horizon = max(self.readouts)
        self._data: dict[int, tuple[Any, Any]] = {}
        self.runs: list[str] = []

    # --- specs and runs -----------------------------------------------------------------------------------------------------------------
    def facts_of(self, facts: int) -> int:
        return self.facts_map.get(facts, facts)

    def ladder_snapshots(self, name: str) -> list[int]:
        top = calibrate.ladder_ceiling(name, self.cfg)
        pts = core.ladder_points(top, self.cfg)
        return sorted({*pow2_points(self.readouts), *pts, *(p // 2 for p in pts)})

    def spec(self, arm: str, facts: int, slots: int, k: int, rate: float, *, ladder_name: str | None = None) -> dict[str, Any]:
        seeds, init = core.calibration_seeds(k, self.cfg), core.calibration_init(k, self.cfg)
        row_facts = self.facts_of(facts)
        run = calibrate.ladder_ceiling(ladder_name, self.cfg) if ladder_name else self.horizon
        snaps = self.ladder_snapshots(ladder_name) if ladder_name else sorted(pow2_points(self.readouts))
        cell = core.make_cell("calibration", arm, row_facts, slots, k, init, u_p=self.readouts[0], run=run, lr=rate, kind="CAL", test=False)
        return {"label": cell.label, "arm": arm, "facts": row_facts, "slots": slots, "draw": k, "init_seed": init, "seed_name": seeds.name, "seed_base": seeds.facts, "u_p": self.readouts[0], "lr": rate, "run": run, "ladder_cell": False, "snapshots": snaps, "mode": "calibration", "kind": "CAL", "test_label": False}

    def data_for(self, spec: Mapping[str, Any]) -> tuple[Any, Any]:
        k = int(spec["draw"])
        if k not in self._data:
            self._data[k] = items.load_data(self.ctx, spec, verify=False)
        return self._data[k]

    def obs(self, spec: dict[str, Any], to: int, need: Sequence[int]) -> dict[int, dict[str, dict[str, Any]]] | None:
        """Train ``spec`` up to ``to`` (continuing), evaluate the snapshots ``need`` and return update -> panel -> counts; None if the run failed non-finite (recorded, kept)."""
        data, seeds = self.data_for(spec)
        try:
            adapter.train_to(data, seeds, items.backbone_of(self.ctx), self.ctx.run_dir, spec, to, mode="calibration", cfg=self.cfg)
        except adapter.NonFinite:
            return None
        except RuntimeError as exc:
            if "kept, not re-run" in str(exc):
                return None
            raise
        out = {}
        for u in need:
            p = items.evaluate_snapshot(self.ctx, spec, u, data=data, seeds=seeds)
            out[u] = core.read_record(p, "eval")["reads"]["main"]["panels"]
        self.runs.append(f"{spec['label']}@{to}")
        return out

    # --- the Engine protocol --------------------------------------------------------------------------------------------------------------
    def unit_cell(self, unit: str) -> tuple[str, int, int, str | None]:
        arm = unit.split("|")[0]
        f, n = core.unit_selection_cell(unit, self.cfg)
        ladder = core.cell_name(f, n) if (core.unit_is_loaded(unit, self.cfg) and arm in ("F-OQ", "T-OQ")) else None
        return arm, f, n, ladder

    def measure(self, unit: str, rate: float, readout: int) -> RateRun:
        arm, f, n, ladder = self.unit_cell(unit)
        need = sorted({readout, *calibrate.tie_snapshots(readout, int(self.cfg["rates"]["walk_steps"]))})
        per: dict[int, dict[int, dict[str, dict[str, Any]]]] = {}
        diverged = False
        for k in CAL_DRAWS:
            got = self.obs(self.spec(arm, f, n, k, rate, ladder_name=ladder), readout, need)
            if got is None:
                diverged = True
                continue
            per[k] = got
        if diverged or len(per) != len(CAL_DRAWS):
            return RateRun(0.0, 0.0, {}, True)

        def a_use(rec: Mapping[str, Any]) -> float:
            return int(rec["useful"]) / int(rec["n"])

        for k in CAL_DRAWS:
            a = per[k][readout]["A"]
            if core.at_chance(int(a["correct"]), int(a["n"])):
                diverged = True  # the raw Panel A correct count inside the G2 chance interval on either draw
        return RateRun(
            readout_a_use=min(a_use(per[k][readout]["A"]) for k in CAL_DRAWS), min_all=min(a_use(per[k][readout][p]) for k in CAL_DRAWS for p in core.PANELS),
            walk={u: min(a_use(per[k][u]["A"]) for k in CAL_DRAWS) for u in need if u != readout}, diverged=diverged,
        )  # fmt: skip

    def row_up(self, row: int, foq_rate: float, r2_rate: float) -> tuple[calibrate.Views, calibrate.Views]:
        c = self.cfg
        cands = [int(x) for x in c["ladder"]["u_p_candidates"]]
        out: list[dict[int, dict[tuple[int, str], float]]] = []
        for arm, cell, rate in (("F-OQ", tuple(c["grid"]["u_p_larger_step_cell"][str(row)]), foq_rate), ("R2", tuple(c["grid"]["r2_reference_cell"][str(row)]), r2_rate)):
            views: dict[int, dict[tuple[int, str], float]] = {u: {} for u in cands}
            for k in CAL_DRAWS:
                got = self.obs(self.spec(arm, int(cell[0]), int(cell[1]), k, rate), self.horizon, cands)
                for u in cands:
                    for p in core.PANELS:
                        if got is not None:
                            views[u][(k, p)] = int(got[u][p]["useful"]) / int(got[u][p]["n"])
            out.append(views)
        return out[0], out[1]

    def ladder_views(self, name: str, arm: str, rate: float, ceiling: int) -> Mapping[tuple[int, str], Mapping[int, float]]:
        """Continue the selected-rate runs from their loaded-readout checkpoints up the ladder, one ladder point at a time, until the arm is full on all four views (or the ceiling): no new run is started."""
        f, n = next((a, b) for a, b in core.ladder_cells(self.cfg) if core.cell_name(a, b) == name)
        pts = [p for p in core.ladder_points(ceiling, self.cfg)]
        series: dict[tuple[int, str], dict[int, float]] = {(k, p): {} for k in CAL_DRAWS for p in core.PANELS}
        for idx, point in enumerate(pts):
            need = sorted({point, point // 2} - set(series[(1, "A")]))
            for k in CAL_DRAWS:
                got = self.obs(self.spec(arm, f, n, k, rate, ladder_name=name), point, [u for u in need])
                if got is None:
                    return {}
                for u in need:
                    for p in core.PANELS:
                        r = got[u][p]
                        series[(k, p)][u] = core.bits(int(r["useful"]), int(r["n"]))
            if idx >= 1 and calibrate.arm_calibrated_length(series, point, self.cfg) is not None:
                break
        return series

    def h8_extra(self, unit_rate: Mapping[str, float], row_u_p: Mapping[int, int]) -> Mapping[str, float]:
        """H8 at its selected rate, to U_P of its row, at 2K/4K and 8K/16K on both draws (four runs): the minimum a_use over draws and panels."""
        out: dict[str, float] = {}
        for facts, slots in ((2048, 4096), (8192, 16384)):
            rate = float(unit_rate[core.unit_key("H8", facts, slots, self.cfg)])
            u_p = int(row_u_p[facts])
            vals = []
            for k in CAL_DRAWS:
                got = self.obs(self.spec("H8", facts, slots, k, rate), u_p, [u_p])
                if got is not None:
                    vals += [int(got[u_p][p]["useful"]) / int(got[u_p][p]["n"]) for p in core.PANELS]
            out[core.cell_name(facts, slots)] = min(vals) if vals else 0.0
        return out


def run_and_seal(engine: calibrate.Engine, sealed_dir: Path, public_dir: Path, cfg: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Run the calibration, write the FULL record into the sealed directory and the whitelisted public record (and the whitelist file) into ``public_dir``. Returns the public record."""
    cal = calibrate.run_calibration(engine, cfg)
    full = calibrate.to_record(cal)
    sealed_dir.mkdir(parents=True, exist_ok=True)
    (sealed_dir / "calibration_full.json").write_text(json.dumps(core.jsonable(full), indent=2, sort_keys=True) + "\n")
    pub = sealed.public_record(full)
    public_dir.mkdir(parents=True, exist_ok=True)
    sealed.write_whitelist(public_dir / "calibration_public_whitelist.json")
    core.write_record(public_dir / "calibration_public.json", pub, overwrite=True)
    return pub


def cmd_calibrate(args: argparse.Namespace, make_engine: Callable[[items.Ctx], calibrate.Engine] | None = None) -> int:
    """``calibrate --sealed-dir D --run-dir R``: the sealed directory is checked first (outside every git working tree and the ArborLM checkout, symlinks resolved); the calibration draws are generated from the registry's calibration
    seeds; nothing registered is read."""
    sd = sealed.check_sealed_dir(Path(args.sealed_dir))
    from . import freeze

    ctx = items.Ctx("calibration", sd, freeze.experiments_root())
    engine = make_engine(ctx) if make_engine else RealEngine(ctx)
    pub = run_and_seal(engine, sd, Path(args.run_dir))
    print(json.dumps({"complete": pub["complete"], "rates": len(pub["rates"]), "row_u_p": pub["row_u_p"], "u0": pub["u0"], "returns_to_lead": pub["returns_to_lead"], "public": str(Path(args.run_dir) / "calibration_public.json")}))
    return 0 if pub["complete"] else 3

