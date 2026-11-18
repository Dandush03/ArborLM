# ruff: noqa: E501
"""P10IS1 real calibration engine and the ``calibrate`` command (ADR-0024 section 7). The engine trains and evaluates calibration cells through the adapter on the registry's calibration seeds ONLY (249001 with 330191,
249101 with 330193: ``adapter.assert_seed_allowed('calibration', ...)`` refuses anything else), blind to every registered seed, in the fixed order ``calibrate.run_calibration`` gives (rates at a provisional readout, U_P per
row, one re-selection at U_P, loaded-cell units at 65,536, then the ladder search and H8). Runs of one (cell, rate, draw) are CONTINUED, never restarted: the cell's label carries one horizon, the runs are segments that
resume from the optimizer snapshot (gate G4: a resumed run equals an uninterrupted one bit for bit). All item records (train snapshots, evaluation counts) go into the SEALED directory; the public record is built from the
whitelist (``sealed``). A diverged run (a non-finite value, a run that ended failed, or a raw Panel A correct count inside the G2 chance interval at the readout on either draw) is recorded and left out of the selection.
The scale of a test is the config's: a tiny config shrinks every length, and ``facts_map`` shrinks the fact counts; the rules are the same.

THE WORKER POOL, THE CAP AND PAUSED. The independent (unit, rate, draw) runs go to a pool of worker PROCESSES (``workers`` > 0; ``stages work-calibrate``), one single-thread process per run, under a cumulative hour cap
(``caps.calibration_hours``) kept in a ledger inside the sealed directory; a pool call that reaches the cap, an identity or environment stop, or a failed worker raises ``CalibrationPaused``: the command records PAUSED, charges
the ledger, and a resume finds every finished run (records exist) and does the rest. The arithmetic of a run is the adapter's and is the same in a worker as in one process (a run depends on its own label's seeds only), so
results are bit-identical whatever the worker count or order (``tests/test_p10is1_calibrate_engine.py`` proves it on a tiny case: 1 worker against 3). Runs of one label are never run in parallel with each other: the jobs of a
call are deduplicated by label (largest target, union of the snapshots to evaluate) and a later call continues from the optimizer snapshot."""

import argparse
import json
import sys
import time
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

from . import adapter, calibrate, core, items, runner, sealed
from .calibrate import RateRun

CAL_DRAWS = (1, 2)


def pow2_points(readouts: Sequence[int]) -> set[int]:
    """readout / 2^k (k = 0..4) of every readout: the snapshots the selections and the tie walk read."""
    return {r // d for r in readouts for d in (1, 2, 4, 8, 16) if r % d == 0 and r // d >= 1}


class RealEngine:
    """Trains and evaluates calibration cells; implements ``calibrate.Engine``. ``ctx`` has ``run_dir`` = the sealed directory."""

    def __init__(self, ctx: items.Ctx, cfg: Mapping[str, Any] | None = None, facts_map: Mapping[int, int] | None = None, *, workers: int = 0, ledger: core.Ledger | None = None, env: Mapping[str, str] | None = None) -> None:
        self.ctx, self.cfg = ctx, core.cfg_of(cfg)
        self.workers, self.ledger, self.env = workers, ledger, dict(env or {})
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

    # --- jobs: one (label, target, snapshots to evaluate) each; the pool or this process runs them ------------------------------------------------------------
    def job_done(self, spec: Mapping[str, Any], to: int, need: Sequence[int]) -> bool:
        out = adapter.cell_dir(self.ctx.run_dir, spec["label"])
        if (out / adapter.FAILED_RECORD).is_file():
            return True
        return to in adapter.completed_snapshots(out) and all(self.ctx.eval_path(spec["label"], u).is_file() for u in need)

    def run_jobs(self, jobs: Sequence[tuple[dict[str, Any], int, Sequence[int]]]) -> None:
        """Run the jobs not yet finished (a finished job is not recomputed). Jobs are deduplicated by label: the largest target and the union of the snapshots. With ``workers`` > 0 they run as single-thread worker processes
        under the cumulative calibration cap; otherwise one after the other in this process. Raises ``CalibrationPaused`` if any job did not finish (cap, identity, environment, failure); the ledger is charged in a ``finally``."""
        merged: dict[str, tuple[dict[str, Any], int, set[int]]] = {}
        for spec, to, need in jobs:
            lab = spec["label"]
            cur = merged.get(lab)
            merged[lab] = (spec, max(to, cur[1]) if cur else to, (cur[2] if cur else set()) | set(need))
        todo = [(sp, to, sorted(nd)) for sp, to, nd in merged.values() if not self.job_done(sp, to, nd)]
        if not todo:
            return
        began = time.monotonic()
        try:
            if self.ledger is not None:
                self.ledger.require_room("calibration")
            if self.workers <= 0:
                for sp, to, nd in todo:
                    work_job(self.ctx.run_dir, {"spec": sp, "to": to, "need": nd}, self.cfg, self.ctx)
                    self.runs.append(f"{sp['label']}@{to}")
                return
            jobdir = self.ctx.run_dir / "jobs"
            jobdir.mkdir(parents=True, exist_ok=True)
            tasks = []
            for sp, to, nd in todo:
                safe = f"{sp['label']}@{to}"
                jf, done = jobdir / f"{safe}.job.json", jobdir / f"{safe}.done.json"
                jf.write_text(json.dumps(core.jsonable({"spec": sp, "to": to, "need": nd})))
                argv = [sys.executable, "-m", "studies.p10is1.stages", "work-calibrate", "--job", str(jf), "--sealed-dir", str(self.ctx.run_dir), "--done", str(done)]
                if self.ctx.synthetic:
                    argv.append("--synthetic")
                if self.ctx.config_path:
                    argv += ["--config", str(self.ctx.config_path)]
                argv += ["--table-facts", str(self.ctx.sizes["table_facts"]), "--unseen", str(self.ctx.sizes["unseen"])]
                tasks.append(runner.Task(safe, tuple(argv), done, jobdir / f"{safe}.failed.json", jobdir / f"{safe}.log"))
            res = self.cfg["resources"]
            left = (self.ledger.remaining() if self.ledger is not None else 1e12)
            outcomes, secs = runner.run_tasks(tasks, workers=self.workers, cap_seconds=left, rss_worker_bytes=int(res["rss_worker_bytes"]), rss_aggregate_bytes=int(res["rss_aggregate_bytes"]), env=self.env)
            bad = {k: v for k, v in outcomes.items() if v["status"] != runner.COMPLETED}
            for sp, to, nd in todo:
                if f"{sp['label']}@{to}" not in bad:
                    self.runs.append(f"{sp['label']}@{to}")
            if bad:
                raise CalibrationPaused({k: v["status"] for k, v in bad.items()})
        finally:
            if self.ledger is not None:
                self.ledger.charge("calibration", "calibrate", time.monotonic() - began)

    def obs(self, spec: dict[str, Any], to: int, need: Sequence[int]) -> dict[int, dict[str, dict[str, Any]]] | None:
        """Train ``spec`` up to ``to`` (continuing), evaluate the snapshots ``need`` and return update -> panel -> counts; None if the run failed non-finite (recorded, kept)."""
        self.run_jobs([(spec, to, need)])
        if (adapter.cell_dir(self.ctx.run_dir, spec["label"]) / adapter.FAILED_RECORD).is_file():
            return None
        return {u: core.read_record(self.ctx.eval_path(spec["label"], u), "eval")["reads"]["main"]["panels"] for u in need}

    # --- the Engine protocol --------------------------------------------------------------------------------------------------------------
    def unit_cell(self, unit: str) -> tuple[str, int, int, str | None]:
        arm = unit.split("|")[0]
        f, n = core.unit_selection_cell(unit, self.cfg)
        ladder = core.cell_name(f, n) if (core.unit_is_loaded(unit, self.cfg) and arm in ("F-OQ", "T-OQ")) else None
        return arm, f, n, ladder

    def measure_jobs(self, unit: str, rate: float, readout: int) -> list[tuple[dict[str, Any], int, list[int]]]:
        arm, f, n, ladder = self.unit_cell(unit)
        need = sorted({readout, *calibrate.tie_snapshots(readout, int(self.cfg["rates"]["walk_steps"]))})
        return [(self.spec(arm, f, n, k, rate, ladder_name=ladder), readout, need) for k in CAL_DRAWS]

    def prefetch(self, requests: Sequence[tuple[str, float, int]]) -> None:
        """Run the runs of many (unit, rate, readout) requests at once on the pool (every request's two draws are independent runs). ``measure`` then only reads records."""
        jobs: list[tuple[dict[str, Any], int, list[int]]] = []
        for unit, rate, readout in requests:
            jobs += self.measure_jobs(unit, rate, readout)
        self.run_jobs(jobs)

    def measure(self, unit: str, rate: float, readout: int) -> RateRun:
        need = sorted({readout, *calibrate.tie_snapshots(readout, int(self.cfg["rates"]["walk_steps"]))})
        per: dict[int, dict[int, dict[str, dict[str, Any]]]] = {}
        diverged = False
        self.run_jobs(self.measure_jobs(unit, rate, readout))
        for spec, _to, _need in self.measure_jobs(unit, rate, readout):
            got = self.obs(spec, readout, need)
            if got is None:
                diverged = True
                continue
            per[int(spec["draw"])] = got
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
        arms = (("F-OQ", tuple(c["grid"]["u_p_larger_step_cell"][str(row)]), foq_rate), ("R2", tuple(c["grid"]["r2_reference_cell"][str(row)]), r2_rate))
        self.run_jobs([(self.spec(arm, int(cell[0]), int(cell[1]), k, rate), self.horizon, cands) for arm, cell, rate in arms for k in CAL_DRAWS])
        out: list[dict[int, dict[tuple[int, str], float]]] = []
        for arm, cell, rate in arms:
            views: dict[int, dict[tuple[int, str], float]] = {u: {} for u in cands}
            for k in CAL_DRAWS:
                got = self.obs(self.spec(arm, int(cell[0]), int(cell[1]), k, rate), self.horizon, cands)
                for u in cands:
                    for p in core.PANELS:
                        if got is not None:
                            views[u][(k, p)] = int(got[u][p]["useful"]) / int(got[u][p]["n"])
            out.append(views)
        return out[0], out[1]

    def ladder_batch(self, requests: Sequence[tuple[str, str, float, int]]) -> dict[tuple[str, str], Mapping[tuple[int, str], Mapping[int, float]]]:
        """The ladder search of several (cell, arm) pairs together, ROUND BY ROUND: in a round every pair that is still searching trains both draws to its next ladder point (a continuation of its loaded-readout run: no new run
        is started) on the pool, and is then judged. A pair stops when it is full on all four views, when any view's i* exceeds 4.0 bits, or at its ceiling. ADR-0024 section 7.2 item 4: in the calibration "full" also requires
        i*(U) <= 4.0 on every view, and i* never falls with further updates, so a view above 4.0 bits makes every later ladder point not full: the outcome is fixed and running on to the ceiling would only spend hours."""
        state: dict[tuple[str, str], dict[str, Any]] = {}
        for name, arm, rate, ceiling in requests:
            f, n = next((a, b) for a, b in core.ladder_cells(self.cfg) if core.cell_name(a, b) == name)
            state[(name, arm)] = {"f": f, "n": n, "rate": rate, "ceiling": ceiling, "pts": core.ladder_points(ceiling, self.cfg), "idx": 0, "active": True, "series": {(k, p): {} for k in CAL_DRAWS for p in core.PANELS}}
        while any(st["active"] for st in state.values()):
            jobs, live = [], []
            for key, st in state.items():
                if not st["active"]:
                    continue
                point = st["pts"][st["idx"]]
                need = sorted({point, point // 2} - set(st["series"][(1, "A")]))
                for k in CAL_DRAWS:
                    jobs.append((self.spec(key[1], st["f"], st["n"], k, st["rate"], ladder_name=key[0]), point, need))
                live.append(key)
            self.run_jobs(jobs)
            for key in live:
                st = state[key]
                point = st["pts"][st["idx"]]
                need = sorted({point, point // 2} - set(st["series"][(1, "A")]))
                for k in CAL_DRAWS:
                    got = self.obs(self.spec(key[1], st["f"], st["n"], k, st["rate"], ladder_name=key[0]), point, need)
                    if got is None:
                        st["series"] = {}
                        st["active"] = False
                        break
                    for u in need:
                        for p in core.PANELS:
                            st["series"][(k, p)][u] = core.bits(int(got[u][p]["useful"]), int(got[u][p]["n"]))
                if not st["active"]:
                    continue
                over = any(max(v for u, v in s_.items() if u <= point) > float(self.cfg["ladder"]["calibration_i_max"]) + 1e-12 for s_ in st["series"].values() if s_)
                full = st["idx"] >= 1 and calibrate.arm_calibrated_length(st["series"], point, self.cfg) is not None
                st["idx"] += 1
                if over or full or st["idx"] >= len(st["pts"]):
                    st["active"] = False
        return {k: v["series"] for k, v in state.items()}

    def ladder_views(self, name: str, arm: str, rate: float, ceiling: int) -> Mapping[tuple[int, str], Mapping[int, float]]:
        """One (cell, arm) of ``ladder_batch``."""
        return self.ladder_batch([(name, arm, rate, ceiling)])[(name, arm)]

    def h8_extra(self, unit_rate: Mapping[str, float], row_u_p: Mapping[int, int]) -> Mapping[str, float]:
        """H8 at its selected rate, to U_P of its row, at 2K/4K and 8K/16K on both draws (four runs, in parallel): the minimum a_use over draws and panels."""
        cells = ((2048, 4096), (8192, 16384))
        jobs = [(self.spec("H8", f, n, k, float(unit_rate[core.unit_key("H8", f, n, self.cfg)])), int(row_u_p[f]), [int(row_u_p[f])]) for f, n in cells for k in CAL_DRAWS]
        self.run_jobs(jobs)
        out: dict[str, float] = {}
        for (f, n), _ in zip(cells, cells, strict=True):
            rate, u_p = float(unit_rate[core.unit_key("H8", f, n, self.cfg)]), int(row_u_p[f])
            vals = []
            for k in CAL_DRAWS:
                got = self.obs(self.spec("H8", f, n, k, rate), u_p, [u_p])
                if got is not None:
                    vals += [int(got[u_p][p]["useful"]) / int(got[u_p][p]["n"]) for p in core.PANELS]
            out[core.cell_name(f, n)] = min(vals) if vals else 0.0
        return out


class CalibrationPaused(RuntimeError):
    """A pool call did not finish (the cap, an identity or environment stop, a failed worker): the calibration is PAUSED and resumes from its records."""

    def __init__(self, statuses: Mapping[str, str]) -> None:
        super().__init__("PAUSED: " + ", ".join(f"{k}: {v}" for k, v in list(statuses.items())[:5]))
        self.statuses = dict(statuses)


def work_job(sealed_dir: Path, job: Mapping[str, Any], cfg: Mapping[str, Any], ctx: items.Ctx) -> None:
    """One job in one process (the body of a worker, also the in-process path): train the cell to its target (a continuation), evaluate the snapshots. A non-finite value is recorded by the adapter (``cell_failed.json``,
    kept) and is a finished job, not an error."""
    spec, to, need = dict(job["spec"]), int(job["to"]), [int(u) for u in job["need"]]
    data, seeds = items.load_data(ctx, spec, verify=False)
    try:
        adapter.train_to(data, seeds, items.backbone_of(ctx), sealed_dir, spec, to, mode="calibration", cfg=cfg)
    except (adapter.NonFinite, adapter.CellFailedBefore):
        return
    for u in need:
        items.evaluate_snapshot(ctx, spec, u, data=data, seeds=seeds)


def worker_main(args: argparse.Namespace) -> int:
    """``stages work-calibrate``: one calibration job in a fresh single-thread process (one thread, one interop thread, deterministic algorithms, set before anything runs). Exit 0 finished; 76 an environment error
    (PAUSED — ENVIRONMENT); 1 a code error (never a result)."""
    from . import freeze, gates

    try:
        cfg = core.load_config(Path(args.config)) if args.config else core.load_config()
        gates.configure_worker(cfg)
        sd = Path(args.sealed_dir)
        ctx = items.Ctx("calibration", sd, None if args.synthetic else freeze.experiments_root(), synthetic=args.synthetic, sizes={"table_facts": int(args.table_facts), "unseen": int(args.unseen)}, config_path=Path(args.config) if args.config else None)
        work_job(sd, json.loads(Path(args.job).read_text()), cfg, ctx)
        Path(args.done).write_text(json.dumps({"done": True}))
        return 0
    except (MemoryError, OSError) as exc:
        print(f"PAUSED — ENVIRONMENT: {type(exc).__name__}: {exc}", file=sys.stderr)
        return runner.ENVIRONMENT_EXIT
    except Exception as exc:  # noqa: BLE001
        print(f"ITEM ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


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

    cfg = core.load_config()
    ctx = items.Ctx("calibration", sd, freeze.experiments_root())
    sd.mkdir(parents=True, exist_ok=True)
    ledger = core.Ledger(sd / "P10IS1-calibration-ledger.json", float(cfg["caps"]["calibration_hours"]) * 3600.0)
    workers = int(args.workers) if getattr(args, "workers", None) else int(cfg["resources"]["workers"])
    engine = make_engine(ctx) if make_engine else RealEngine(ctx, workers=workers, ledger=ledger, env={"PYTHONUNBUFFERED": "1"})
    try:
        pub = run_and_seal(engine, sd, Path(args.run_dir))
    except (CalibrationPaused, core.LedgerRefused) as exc:  # PAUSED: nothing is final, the records are kept, the same command resumes; only the status and the charged hours are public
        led = getattr(engine, "ledger", None) or ledger
        Path(args.run_dir).mkdir(parents=True, exist_ok=True)
        core.write_record(Path(args.run_dir) / "calibration_status.json", {**core.envelope("calibration"), "status": "PAUSED", "reason": str(exc)[:300], "charged_hours": led.charged() / 3600.0, "cap_hours": led.total_seconds / 3600.0}, overwrite=True)
        print(json.dumps({"status": "PAUSED", "charged_hours": led.charged() / 3600.0, "cap_hours": led.total_seconds / 3600.0}))
        return 4
    print(json.dumps({"complete": pub["complete"], "rates": len(pub["rates"]), "row_u_p": pub["row_u_p"], "u0": pub["u0"], "returns_to_lead": pub["returns_to_lead"], "public": str(Path(args.run_dir) / "calibration_public.json")}))
    return 0 if pub["complete"] else 3

