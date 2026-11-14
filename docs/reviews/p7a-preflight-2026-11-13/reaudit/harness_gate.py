"""Re-audit harness (synthetic only): validate independent_sim.py v2 and the analysis gate
(arborlm.p7a_study.check_independent_comparison / run_analyze) end to end. This harness imports and
drives the code under audit; independent_sim.py itself is run as a separate stdlib-only process
(``python -I``) and imports nothing from arborlm.

Part 1 (stage pipeline, dry-run flag): the study's own run_trace and run_simulate on synthetic fixture
models for ALL 27 parent/seed pairs (81 checkpoints, 8 contexts = 512 queries each), so that the
registered clarification-7 selection exists; independent_sim.py --registered-selection --allow-small;
then run_analyze with the default (registered 18) expected selection. Negative controls: a perturbed
frequency-matched count, a perturbed frequency-matched stream_sha256, --tie desc, a wrong selection
(--labels), a second simulate run (wrong run), the v1 script (no FM coverage), a study record edited
after the check (stale AGREE).
Part 2 (full size): 18 registered-selection checkpoints with 32,768-query synthetic traces written with
the study's own trace writer into <root>/full/experiments/P7AT-SYNTH/traces and study records from
simulate_checkpoint into <root>/full/results/simulate/P7AS-SYNTH/workers; independent_sim.py
--registered-selection WITHOUT --allow-small; timed; then the gate with allow_small=False.

Nothing is written under the repository's experiments/ or results/. Outputs go to reaudit/outputs/.
Run (repo root):
  uv run --locked --extra pilot python docs/reviews/p7a-preflight-2026-11-13/reaudit/harness_gate.py <scratch> [part1|part2|all]
"""

import argparse
import json
import random
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import torch

from arborlm import p6_common as common
from arborlm import p7a_core as core
from arborlm import p7a_sim as sim
from arborlm import p7a_study as study
from arborlm.p7a_trace import synthetic_trace

HERE = Path(__file__).resolve().parent
REVIEW = HERE.parent
OUT = HERE / "outputs"
INDEP = REVIEW / "independent_sim.py"
INDEP_V1 = REVIEW / "independent_sim.v1.py"
LOG: list[str] = []


def log(line: str) -> None:
    LOG.append(line)
    print(line, flush=True)


def run_indep(script: Path, args: list[str], tag: str) -> tuple[int, float, dict | None]:
    cmd = [sys.executable, "-I", str(script), *args]
    t0 = time.monotonic()
    proc = subprocess.run(cmd, capture_output=True, text=True)
    seconds = time.monotonic() - t0
    (OUT / f"gate_{tag}.stdout.txt").write_text(
        "$ " + " ".join(cmd) + "\n" + proc.stdout + proc.stderr + f"\nexit {proc.returncode}\n"
    )
    out_path = Path(args[args.index("--out") + 1])
    data = json.loads(out_path.read_text()) if out_path.is_file() else None
    return proc.returncode, seconds, data


def gate(path: Path, sim_id: str, trace_id: str, allow_small: bool) -> str:
    try:
        study.check_independent_comparison(
            path, simulate_run_id=sim_id, trace_run_id=trace_id, allow_small=allow_small
        )
        return "ACCEPTED"
    except ValueError as exc:
        return f"REFUSED: {exc}"


def part1(root: Path) -> dict[str, Any]:
    args = argparse.Namespace(
        data_dir=root / "data", parent_suite=root / "suite", output_root=root / "experiments",
        results_root=root / "results", p5_results=root / "p5", supersede=None, reason=None,
    )
    opt = study.Options(args)
    opt.dry_run, opt.synthetic = True, True
    opt.pair_list, opt.contexts = common.pairs(), 8
    t0 = time.monotonic()
    code_t, trace_run = study.run_trace(opt)
    code_s, sim_run = study.run_simulate(opt)
    log(f"P1 trace={code_t} simulate={code_s} ({time.monotonic() - t0:.0f}s) trace={trace_run.name} sim={sim_run.name}")
    trace_compact = opt.results_root / "trace" / trace_run.name
    sim_compact = opt.results_root / "simulate" / sim_run.name
    workers = sim_compact / "workers"
    common_args = ["--trace-root", str(trace_run / "traces"), "--trace-records",
                   str(trace_compact / "checkpoints")]
    res: dict[str, Any] = {}

    # genuine AGREE on the registered selection
    agree = root / "indep_agree.json"
    code, secs, data = run_indep(INDEP, [*common_args, "--sim-workers", str(workers),
                                         "--registered-selection", "--allow-small", "--out", str(agree)], "p1_agree")
    log(f"P1 independent_sim registered selection: exit {code}, verdict {data and data['verdict']}, {secs:.1f}s")
    res["agree"] = {"exit": code, "verdict": data and data["verdict"], "seconds": secs,
                    "gate_direct": gate(agree, sim_run.name, trace_run.name, True)}
    log(f"P1 gate (direct, dry-run): {res['agree']['gate_direct']}")
    opt.independent_check, opt.independent_expected = agree, None  # default = registered 18
    try:
        code_a, ana_run = study.run_analyze(opt)
        manifest = json.loads((ana_run / "manifest.json").read_text())
        res["analyze"] = {"exit": code_a, "status": manifest["status"],
                          "independent_check_sha256": manifest["linkage"]["independent_check_sha256"]}
    except Exception as exc:  # noqa: BLE001
        res["analyze"] = {"error": f"{type(exc).__name__}: {exc}"}
    log(f"P1 run_analyze with the genuine file: {res['analyze']}")

    # negative control 1: perturbed FM count in a copy of the workers folder (same final path parts)
    def perturbed_copy(tag: str, mutate) -> Path:  # type: ignore[no-untyped-def]
        copy = root / tag / "simulate" / sim_run.name / "workers"
        shutil.copytree(workers, copy)
        label = core.independent_selection()[7]  # a fixed_tree of the selection
        path = copy / f"{label}.result.json"
        rec = json.loads(path.read_text())
        mutate(rec)
        path.write_text(json.dumps(rec))
        return copy

    def bump_fm(rec: dict) -> None:
        rec["record"]["streams"]["freq_matched_2"]["L-FREQ|R2"]["by_c"]["32"]["misses_warm"] += 1

    def bad_sha(rec: dict) -> None:
        rec["record"]["frequency_matched"]["freq_matched_3"]["stream_sha256"] = "0" * 64

    for tag, mutate in (("neg_fm_count", bump_fm), ("neg_fm_sha", bad_sha)):
        copy = perturbed_copy(tag, mutate)
        out = root / f"{tag}.json"
        code, secs, data = run_indep(INDEP, [*common_args, "--sim-workers", str(copy),
                                             "--registered-selection", "--allow-small", "--out", str(out)], tag)
        diffs = [d for v in (data or {}).get("checkpoints", {}).values() for d in v["differences"]]
        res[tag] = {"exit": code, "verdict": data and data["verdict"], "differences": diffs,
                    "gate": gate(out, sim_run.name, trace_run.name, True)}
        log(f"P1 {tag}: exit {code} verdict {res[tag]['verdict']} differences {diffs} gate {res[tag]['gate'][:120]}")

    # negative control 2: tie rule desc
    out = root / "neg_tie.json"
    code, secs, data = run_indep(INDEP, [*common_args, "--sim-workers", str(workers), "--registered-selection",
                                         "--allow-small", "--tie", "desc", "--out", str(out)], "neg_tie_desc")
    res["neg_tie_desc"] = {"exit": code, "verdict": data and data["verdict"],
                           "gate": gate(out, sim_run.name, trace_run.name, True)}
    log(f"P1 neg_tie_desc: exit {code} verdict {res['neg_tie_desc']['verdict']} gate {res['neg_tie_desc']['gate'][:160]}")

    # negative control 3: wrong selection (18 other labels), AGREEing on what it checked
    others = [lb for lb in [core.cell_label(p, k) for p, k in core.registered_checkpoints()]
              if lb not in core.independent_selection()][:18]
    out = root / "neg_selection.json"
    code, secs, data = run_indep(INDEP, [*common_args, "--sim-workers", str(workers), "--labels", *others,
                                         "--allow-small", "--out", str(out)], "neg_wrong_selection")
    res["neg_wrong_selection"] = {"exit": code, "verdict": data and data["verdict"],
                                  "gate": gate(out, sim_run.name, trace_run.name, True)}
    log(f"P1 neg_wrong_selection: exit {code} verdict {res['neg_wrong_selection']['verdict']} gate {res['neg_wrong_selection']['gate'][:200]}")

    # negative control 4: wrong run - a second (dry-run) simulate run; analyze it with the first file
    code_s2, sim_run2 = study.run_simulate(opt)
    opt.simulate_run = sim_run2.name
    try:
        study.run_analyze(opt)
        res["neg_wrong_run"] = "ACCEPTED (unexpected)"
    except ValueError as exc:
        res["neg_wrong_run"] = f"REFUSED: {exc}"
    log(f"P1 neg_wrong_run (second simulate {sim_run2.name}, exit {code_s2}): {res['neg_wrong_run'][:200]}")
    opt.simulate_run = None

    # finding demonstration: the v1 script (actual stream only, no FM) also passes the gate
    out = root / "v1_agree.json"
    code, secs, data = run_indep(INDEP_V1, [*common_args, "--sim-workers", str(workers),
                                            "--registered-selection", "--allow-small", "--out", str(out)], "v1_no_fm")
    res["v1_no_fm"] = {"exit": code, "verdict": data and data["verdict"],
                       "gate": gate(out, sim_run.name, trace_run.name, True)}
    log(f"P1 v1 script (no FM coverage): exit {code} verdict {res['v1_no_fm']['verdict']} gate {res['v1_no_fm']['gate'][:120]}")

    # finding demonstration: a study record edited AFTER an AGREE check is not detected by the gate
    label = core.independent_selection()[0]
    path = workers / f"{label}.result.json"
    original = path.read_text()
    try:
        rec = json.loads(original)
        rec["record"]["streams"]["actual"]["L-FREQ|R2"]["by_c"]["32"]["misses_warm"] += 5
        path.write_text(json.dumps(rec))
        res["stale_agree_after_edit"] = gate(agree, sim_run.name, trace_run.name, True)
    finally:
        path.write_text(original)
    log(f"P1 stale AGREE after a post-check edit of a study record: {res['stale_agree_after_edit'][:120]}")
    return res


def write_trace_set(trace_dir: Path, sel, br, cal, cbr) -> dict:  # type: ignore[no-untyped-def]
    return {
        "evaluation": core.write_trace(trace_dir, "eval", sel, br),
        "calibration": core.write_trace(trace_dir, "calib", cal, cbr),
    }


def auditor_tree(seed: int) -> tuple[torch.Tensor, torch.Tensor]:
    rng = random.Random(seed)
    hot = {b: rng.sample(range(b * 256, (b + 1) * 256), 20) for b in range(16)}
    bweights = [16 - b for b in range(16)]
    rows, branches = [], []
    for i in range(core.QUERIES):
        if i % 64 and rng.random() < 0.6:
            pair = list(branches[-1])
        else:
            first = rng.choices(range(16), bweights)[0]
            second = first
            while second == first:
                second = rng.choices(range(16), bweights)[0]
            pair = [first, second]
        pool = hot[pair[0]] + hot[pair[1]]
        chosen: list[int] = []
        while len(chosen) < 8:
            s = rng.choices(pool, [3] * 10 + [1] * 10 + [3] * 10 + [1] * 10)[0]
            if s not in chosen:
                chosen.append(s)
        rows.append(chosen)
        branches.append(pair)
    return torch.tensor(rows), torch.tensor(branches)


def part2(root: Path) -> dict[str, Any]:
    base = root / "full"
    traces = base / "experiments" / "P7AT-SYNTH" / "traces"
    workers = base / "results" / "simulate" / "P7AS-SYNTH" / "workers"
    records = base / "results" / "trace" / "P7AT-SYNTH" / "checkpoints"
    workers.mkdir(parents=True, exist_ok=True)
    records.mkdir(parents=True, exist_ok=True)
    study_seconds = {}
    for n, label in enumerate(core.independent_selection()):
        pair, kind = core.parse_label(label)
        if n % 3 == 2 and kind != "flat":
            sel, br = auditor_tree(500 + n)
            cal, cbr = auditor_tree(900 + n)
        else:
            sel, br = synthetic_trace(kind, 7000 + n)
            cal, cbr = synthetic_trace(kind, 8000 + n)
        files = write_trace_set(traces / label, sel, br, cal, cbr)
        (records / f"{label}.json").write_text(json.dumps({"label": label, "trace_dir": label, "files": files}))
        t0 = time.monotonic()
        record = sim.simulate_checkpoint(kind=kind, index=core.cell_index(pair, kind), eval_selected=sel,
                                         eval_branches=br, calibration_selected=cal)
        study_seconds[label] = time.monotonic() - t0
        (workers / f"{label}.result.json").write_text(json.dumps({
            "outcome": "completed", "label": label, "kind": kind, "pair": list(pair),
            "cell_index": core.cell_index(pair, kind), "queries": core.QUERIES,
            "trace": {"run_id": "P7AT-SYNTH", "files": files, "record": f"{label}.json"},
            "record": record}))
        log(f"P2 study record {label}: {study_seconds[label]:.1f}s")
    out = root / "full_agree.json"
    code, secs, data = run_indep(INDEP, ["--trace-root", str(traces), "--trace-records", str(records),
                                         "--sim-workers", str(workers), "--registered-selection",
                                         "--out", str(out)], "p2_full_agree")
    shutil.copyfile(out, OUT / "gate_p2_full_agree.summary.json")
    per = {k: round(v["seconds"], 1) for k, v in (data or {}).get("checkpoints", {}).items()}
    res = {"exit": code, "verdict": data and data["verdict"], "independent_seconds_total": secs,
           "independent_seconds_per_checkpoint": per, "study_seconds": study_seconds,
           "gate_registered": gate(out, "P7AS-SYNTH", "P7AT-SYNTH", False),
           "gate_wrong_sim_run": gate(out, "P7AS-OTHER", "P7AT-SYNTH", False),
           "gate_wrong_trace_run": gate(out, "P7AS-SYNTH", "P7AT-OTHER", False)}
    log(f"P2 independent_sim 18 full-size: exit {code} verdict {res['verdict']} total {secs:.0f}s "
        f"(cap 1800 s); gate registered: {res['gate_registered'][:80]}; wrong sim run: "
        f"{res['gate_wrong_sim_run'][:60]}; wrong trace run: {res['gate_wrong_trace_run'][:60]}")
    return res


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("scratch", type=Path)
    ap.add_argument("part", nargs="?", default="all", choices=("part1", "part2", "all"))
    a = ap.parse_args()
    root = a.scratch.resolve()
    repo = Path.cwd().resolve()
    for protected in (repo / "experiments", repo / "results"):
        if root.is_relative_to(protected):
            raise SystemExit("scratch must be outside experiments/ and results/")
    root.mkdir(parents=True, exist_ok=True)
    torch.set_num_threads(1)
    log(f"python {sys.version.split()[0]} torch {torch.__version__}")
    result: dict[str, Any] = {}
    if a.part in ("part1", "all"):
        result["part1"] = part1(root / "p1")
    if a.part in ("part2", "all"):
        result["part2"] = part2(root / "p2")
    (OUT / f"harness_gate_{a.part}.json").write_text(json.dumps(result, indent=1, default=str))
    (OUT / f"harness_gate_{a.part}.txt").write_text("\n".join(LOG) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
