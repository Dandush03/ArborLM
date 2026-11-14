"""Auditor harness (synthetic only): produce study-format traces and study simulation records so that
independent_sim.py can be validated against the implementer's simulator. This harness DOES import
arborlm (it drives the code under audit); independent_sim.py does not.

Part 1: the study's own stage pipeline (run_trace + run_simulate, dry-run flag, synthetic fixture
         models, 2 parent/seed pairs x 3 kinds, 8 contexts = 512 queries) in a scratch folder.
Part 2: full-size (32,768-query) synthetic traces for 4 checkpoints, written by the auditor's own
         little-endian writer; two from the implementer's synthetic generator, two from an auditor
         stdlib generator with heavy count ties and within-context persistence. Each is simulated
         with arborlm.p7a_sim.simulate_checkpoint and stored as workers/<label>.result.json.

Nothing is written under experiments/ or results/. No real checkpoint or trace is used.

Run: uv run --locked --extra pilot python docs/reviews/p7a-preflight-2026-11-13/harness_synthetic.py <scratch>
"""

import argparse
import json
import random
import shutil
import struct
import sys
import time
from pathlib import Path

import torch

from arborlm import p6_common as common
from arborlm import p7a_core as core
from arborlm import p7a_sim as sim
from arborlm import p7a_study as study
from arborlm.p7a_trace import synthetic_trace

HERE = Path(__file__).resolve().parent
Q = 32768


def write_le(path: Path, rows: list[list[int]], code: str) -> None:
    flat = [v for row in rows for v in row]
    path.write_bytes(struct.pack(f"<{len(flat)}{code}", *flat))


def auditor_flat(seed: int) -> list[list[int]]:
    """Flat: 300 hot slots, weights in 4 tiers (many exact ties), 8 distinct per query; with
    persistence: 40% of queries inside a context reuse 4 of the previous query's slots."""
    rng = random.Random(seed)
    hot = rng.sample(range(4096), 300)
    weights = [8] * 20 + [4] * 60 + [2] * 100 + [1] * 120
    rows: list[list[int]] = []
    for i in range(Q):
        keep: list[int] = []
        if i % 64 and rng.random() < 0.4:
            keep = rng.sample(rows[-1], 4)
        chosen = list(keep)
        while len(chosen) < 8:
            s = rng.choices(hot, weights)[0]
            if s not in chosen:
                chosen.append(s)
        rows.append(chosen)
    return rows


def auditor_tree(seed: int) -> tuple[list[list[int]], list[list[int]]]:
    """Tree: two distinct visited branches (rank order), eight distinct slots inside them; branch
    pairs persist within a context; slots drawn from 20 hot slots per branch with tied weights."""
    rng = random.Random(seed)
    hot = {b: rng.sample(range(b * 256, (b + 1) * 256), 20) for b in range(16)}
    bweights = [16 - b for b in range(16)]
    rows: list[list[int]] = []
    branches: list[list[int]] = []
    for i in range(Q):
        if i % 64 and rng.random() < 0.6:
            pair = list(branches[-1])
        else:
            first = rng.choices(range(16), bweights)[0]
            second = first
            while second == first:
                second = rng.choices(range(16), bweights)[0]
            pair = [first, second]
        pool = hot[pair[0]] + hot[pair[1]]
        w = [3] * 10 + [1] * 10 + [3] * 10 + [1] * 10
        chosen: list[int] = []
        while len(chosen) < 8:
            s = rng.choices(pool, w)[0]
            if s not in chosen:
                chosen.append(s)
        rows.append(chosen)
        branches.append(pair)
    return rows, branches


def to_tensor(rows: list[list[int]]) -> torch.Tensor:
    return torch.tensor(rows, dtype=torch.int64)


def part1(root: Path) -> dict:
    import argparse as ap

    args = ap.Namespace(
        data_dir=root / "data", parent_suite=root / "suite", output_root=root / "experiments",
        results_root=root / "results", p5_results=root / "p5", supersede=None, reason=None,
    )
    opt = study.Options(args)
    opt.dry_run, opt.synthetic = True, True
    opt.pair_list, opt.contexts = common.pairs()[:2], 8
    code_t, trace_run = study.run_trace(opt)
    code_s, sim_run = study.run_simulate(opt)
    code_a, ana_run = study.run_analyze(opt)
    trace_compact = opt.results_root / "trace" / trace_run.name
    sim_compact = opt.results_root / "simulate" / sim_run.name
    keep = HERE / "outputs" / "dryrun_manifests"
    keep.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(trace_compact / "manifest.json", keep / "trace_stage_manifest.json")
    shutil.copyfile(sim_compact / "manifest.json", keep / "simulate_stage_manifest.json")
    worker = next((trace_compact / "workers").glob("*.manifest.json"))
    shutil.copyfile(worker, keep / "trace_worker_manifest.json")
    sworker = next((sim_compact / "workers").glob("*.manifest.json"))
    shutil.copyfile(sworker, keep / "simulate_worker_manifest.json")
    envs = sorted((trace_run / "workers").glob("*/environment.json"))
    if envs:
        shutil.copyfile(envs[0], keep / "trace_worker_environment.json")
    return {
        "codes": [code_t, code_s, code_a],
        "trace_root": str(trace_run / "traces"),
        "sim_workers": str(sim_compact / "workers"),
        "trace_records": str(trace_compact / "checkpoints"),
        "labels": [core.cell_label(p, k) for p in opt.pair_list for k in core.KINDS],
    }


def part2(root: Path) -> dict:
    traces, workers = root / "full" / "traces", root / "full" / "workers"
    workers.mkdir(parents=True, exist_ok=True)
    plan = []
    s_flat, _ = synthetic_trace("flat", 7001)
    c_flat, _ = synthetic_trace("flat", 8001)
    plan.append(("b101-o301-flat-s501", s_flat.tolist(), None, c_flat.tolist(), None))
    s_fix, b_fix = synthetic_trace("fixed_tree", 7002)
    c_fix, cb_fix = synthetic_trace("fixed_tree", 8002)
    plan.append(("b101-o301-fixed_tree-s501", s_fix.tolist(), b_fix.tolist(), c_fix.tolist(),
                 cb_fix.tolist()))
    plan.append(("b101-o301-flat-s502", auditor_flat(11), None, auditor_flat(12), None))
    t_sel, t_br = auditor_tree(21)
    c_sel, c_br = auditor_tree(22)
    plan.append(("b101-o301-learned_tree-s502", t_sel, t_br, c_sel, c_br))
    timings = {}
    for label, sel, br, cal, cbr in plan:
        pair, kind = core.parse_label(label)
        d = traces / label
        d.mkdir(parents=True, exist_ok=True)
        write_le(d / "eval_selected.int16.bin", sel, "h")
        write_le(d / "calib_selected.int16.bin", cal, "h")
        if br is not None:
            write_le(d / "eval_branches.int8.bin", br, "b")
            write_le(d / "calib_branches.int8.bin", cbr, "b")
        core.check_trace(to_tensor(sel), None if br is None else to_tensor(br), kind)
        t0 = time.monotonic()
        record = sim.simulate_checkpoint(
            kind=kind, index=core.cell_index(pair, kind), eval_selected=to_tensor(sel),
            eval_branches=None if br is None else to_tensor(br), calibration_selected=to_tensor(cal),
        )
        timings[label] = time.monotonic() - t0
        (workers / f"{label}.result.json").write_text(json.dumps(
            {"outcome": "completed", "label": label, "queries": Q, "record": record}))
    return {"trace_root": str(traces), "sim_workers": str(workers),
            "labels": [p[0] for p in plan], "study_sim_seconds": timings}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("scratch", type=Path)
    a = ap.parse_args()
    root = a.scratch.resolve()
    repo = Path.cwd().resolve()
    for protected in (repo / "experiments", repo / "results"):
        if root.is_relative_to(protected):
            raise SystemExit("scratch must be outside experiments/ and results/")
    root.mkdir(parents=True, exist_ok=True)
    torch.set_num_threads(1)
    out = {"part1": part1(root / "stage"), "part2": part2(root)}
    (HERE / "outputs" / "harness_paths.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
