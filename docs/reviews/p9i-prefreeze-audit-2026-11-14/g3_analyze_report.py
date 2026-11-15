"""G3 (auditor, Opus 5.5): the registered analyze and report code paths on synthetic records of all 57
registered cells (real registry: labels, sizes, facts, parents, seeds; U = 8,192 from the committed
calibration record; INVENTED accuracies). Nothing here is a measurement.

Each scenario builds a scratch run directory with calibration_binding.json, gates.json, train/evaluate
stage manifests, cells/<label>/train.json and cells/<label>/eval/u0008192/eval.json, then calls the
implementer's own worker entry points ``stages.main(["work", "analyze", ...])`` and
``stages.main(["work", "report", ...])`` in rehearsal mode (the only difference from registered mode in
these two workers is that registered mode refuses without the frozen tree). One scenario also goes through
the pool (``cmd_analyze`` / ``cmd_report``) with a private ledger. Expected outcomes are written by hand
from ADR-0017 section I.8 and asserted.

The G2 chance intervals are computed by my own exact binomial code (log-space pmf) and compared with
``studies.p9.core.chance_interval`` and with the attempt-1 gates record.

Usage: PYTHONPATH=. uv run --locked python <this> <scratch dir> <committed attempt-1 gates.json>
"""
import json
import math
import sys
import traceback
from pathlib import Path

from arborlm.io import file_sha256
from arborlm.io import write_json as _write_json
from studies.p9 import core as p9core
from studies.p9i import classes, core, stages

SCRATCH = Path(sys.argv[1])
GATES_RECORD = Path(sys.argv[2])
CAL = Path("results/p9i-calibration-2026-11-14/calibration.json").resolve()
U = 8192
FAILURES: list[str] = []


def write_json(path: Path, obj) -> None:  # arborlm.io.write_json does not create parents (attempt 1 failed on this)
    path.parent.mkdir(parents=True, exist_ok=True)
    _write_json(path, obj)


# --- my own chance interval ---------------------------------------------------------------------------------
def my_interval(n: int, tests: int = 8, p: float = 1 / 32, alpha: float = 0.001) -> tuple[int, int]:
    tail = alpha / tests / 2
    logpmf = [math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1) + k * math.log(p) + (n - k) * math.log1p(-p) for k in range(n + 1)]
    pmf = [math.exp(v) for v in logpmf]
    c, low = 0.0, 0
    for k in range(n + 1):
        c += pmf[k]
        if c > tail:
            low = k
            break
    c, high = 0.0, n
    for k in range(n, -1, -1):
        c += pmf[k]
        if c > tail:
            high = k
            break
    return low, high


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  [{'ok' if ok else 'FAIL'}] {name}{(': ' + detail) if detail else ''}")
    if not ok:
        FAILURES.append(name)


print("== chance intervals (mine vs implementer vs attempt-1 record)")
INTERVAL = {}
for n in (2048, 8192, 32768):
    mine = my_interval(n)
    theirs = p9core.chance_interval(n, p9core.G2_TESTS_PRIMARY)
    INTERVAL[n] = mine
    check(f"interval n={n}", mine == (theirs.low, theirs.high), f"mine {mine}, implementer ({theirs.low}, {theirs.high}), level {theirs.level}")
g = json.loads(GATES_RECORD.read_text())
for r in g["g2"]["results"]:
    lo, hi = INTERVAL[r["facts"]]
    check(f"attempt-1 G2 {r['name']}", [lo, hi] == r["interval"] and (lo <= r["correct"] <= hi) == r["inside"] and r["inside"], f"correct {r['correct']} of {r['facts']}, interval {r['interval']}")
check("attempt-1 G2 family passed and 8 tests", g["g2"]["passed"] is True and g["g2"]["tests"] == 8 and len(g["g2"]["results"]) == 8)


# --- synthetic records --------------------------------------------------------------------------------------
def panel(acc: float, facts: int, dep: bool = True, leak: bool = False) -> dict:
    lo, hi = INTERVAL[facts]
    correct = round(acc * facts)
    return {
        "stream": "x", "sha256": "0" * 64, "facts": facts, "correct": correct, "accuracy": correct / facts,
        "chance_interval": [lo, hi], "unseen_correct": 64, "unseen_facts": 2048, "unseen_accuracy": 64 / 2048, "leakage": leak,
        "i_acc_bits": 0.0, "i_acc_bits_per_fact": 0.0, "disabled_correct": 64, "disabled_accuracy": 64 / facts,
        "disabled_at_chance": dep, "permuted_accuracy": 1 / 32, "permuted_at_chance": dep, "memory_dependence_chance": dep,
        "support": {"correct_facts": correct, "with_support": correct, "share_with_support": 1.0, "mean_length": 1.0, "useful_slots": 10, "site_read_removed_stays_correct_share": 0.0},
    }  # fmt: skip


def train_record(cell: core.Cell) -> dict:
    return {
        **core.envelope("train"), "label": cell.label, "block": cell.block, "arm": cell.arm, "slots": cell.slots, "facts": cell.facts,
        "parent": list(cell.parent), "seed": cell.seed, "init_seed": cell.seed, "mode": "registered", "matched_updates": U, "run_updates": U,
        "snapshots": [U], "examples": 0, "tokens": 0, "answer_site_exposures": 0, "unique_facts": cell.facts,
        "exposure_per_fact_min": 1, "exposure_per_fact_max": 1, "exposure_per_fact_mean": U * 128 / cell.facts,
        "trainable_parameters": 1, "trainable_backbone_parameters": 0, "stored_parameters": 1, "parameters_by_group": {},
        "interface_extra_parameters": 0, "dense_hidden": 0, "optimizer_state_bytes": 0, "wall_seconds": 0.0, "peak_rss_bytes": 0,
        "update_log": "updates.jsonl", "snapshot_sha256": {str(U): "0" * 64}, "identity": {}, "status": "completed", "reason": None, "seed_set": "SYNTHETIC",
    }  # fmt: skip


def build(name: str, acc, *, drop: tuple[str, ...] = (), gates_over: dict | None = None, leak: tuple[str, ...] = (), lm_rise: float = 0.01) -> Path:
    run = SCRATCH / name
    run.mkdir(parents=True)
    binding = {"calibration_sha256": file_sha256(CAL), "calibration_selected_updates": U, "calibration_failed_sizes": {}}
    write_json(run / "calibration_binding.json", binding)
    gates = {**core.envelope("gates"), "g1_passed": True, "g2_passed": True, "g4_passed": True, "g4_defects": [], "dry": False, **(gates_over or {})}
    write_json(run / "gates.json", gates)
    tasks = []
    for cell in core.cells():
        tasks.append({"label": cell.label, "status": "completed"})
        if cell.label in drop:
            continue
        d = core.cell_dir(run, cell.label)
        write_json(d / "train.json", train_record(cell))
        a, dep = acc(cell)
        rec = {**core.envelope("eval"), "label": cell.label, "arm": cell.arm, "slots": cell.slots, "parent": list(cell.parent), "seed": cell.seed,
               "update": U, "facts": cell.facts, "identity": {}, "panels": {p: panel(a(p) if callable(a) else a, cell.facts, dep, cell.label in leak and p == "A") for p in core.PANELS}, "secondary": {}, **binding}  # fmt: skip
        if cell.arm in core.BB_ARMS:
            rec["language_modelling"] = {"before_nats": 2.0, "after_nats": 2.0 * (1 + lm_rise), "relative_rise": lm_rise, "degraded": lm_rise > 0.05}
        write_json(core.eval_path(run, cell.label, U, "eval").with_name("eval.json"), rec)
    for stage in ("train", "evaluate"):
        write_json(run / stage / "manifest.json", {**core.envelope("stage_manifest"), "stage": stage, "status": "COMPLETE", "tasks": tasks})
    return run


def base(cell: core.Cell, works: tuple[str, ...] = (), *, r1: float = 0.95, override=None):
    if override is not None:
        hit = override(cell)
        if hit is not None:
            return hit
    if cell.arm == "R1":
        return r1, True
    if cell.arm == "R2":
        return 1.0, True
    if cell.arm in ("D", "D7", "BB-D"):
        return 0.10, False
    if cell.arm == "BB-0":
        return 1 / 32, True
    return (0.93, True) if cell.arm in works else (0.03, True)


def run_workers(run: Path) -> tuple[int | None, int | None, str]:
    common = ["--mode", "rehearsal", "--run-dir", str(run), "--calibration", str(CAL), "--calibration-sha256", file_sha256(CAL), "--experiments-root", str(SCRATCH)]
    try:
        a = stages.main(["work", "analyze", *common])
    except Exception:  # noqa: BLE001
        return None, None, traceback.format_exc(limit=3)
    try:
        r = stages.main(["work", "report", *common])
    except Exception:  # noqa: BLE001
        return a, None, traceback.format_exc(limit=3)
    return a, r, ""


def scenario(name: str, acc, expect: dict, **kw) -> dict | None:
    print(f"== scenario {name}")
    run = build(name, acc, **kw)
    a, r, err = run_workers(run)
    if err:
        print("  exception:\n    " + err.strip().replace("\n", "\n    "))
    check(f"{name}: analyze exit 0 and report exit 0", a == 0 and r == 0, f"analyze {a}, report {r}")
    if a != 0 or not (run / "analysis.json").is_file():
        return None
    an = json.loads((run / "analysis.json").read_text())
    sel = an["analysis"]["selection"]
    print(f"  status {an['status']}, interpretable {an['interpretable']}, outcome {sel['outcome']} step {sel['step']}, inconclusive {sel['inconclusive_sizes']}, missing {len(an['missing_cells'])}, cells read {len(an['cells_read'])}, updates {an['updates']}")
    print(f"  classes {json.dumps(an['analysis']['classes'], sort_keys=True)}")
    for k, v in expect.items():
        got = {"outcome": sel["outcome"], "step": sel["step"], "status": an["status"], "interpretable": an["interpretable"], "cells_read": len(an["cells_read"]), "missing": an["missing_cells"],
               "inconclusive": sel["inconclusive_sizes"]}.get(k) if not k.startswith("class:") else an["analysis"]["classes"].get(k.split(":")[1], {}).get(k.split(":")[2])  # fmt: skip
        check(f"{name}: {k}", got == v, f"got {got!r}, expected {v!r}")
    if r == 0:
        res = run / "results"
        md = (res / "RESULTS.md").read_text()
        cells_csv = (res / "cells.csv").read_text().splitlines()
        cls_csv = (res / "classes.csv").read_text().splitlines()
        check(f"{name}: report rows", len(cells_csv) - 1 == 57 - len(kw.get("drop", ())), f"cells.csv rows {len(cells_csv) - 1}, classes.csv rows {len(cls_csv) - 1}")
        check(f"{name}: NOT INTERPRETED banner iff not interpretable", ("**NOT INTERPRETED**" in md) == (not an["interpretable"]))
        check(f"{name}: outcome printed", f"Outcome: **{sel['outcome']}**" in md)
    return an


ALL = classes.SLOTS_BY_SIZE if hasattr(classes, "SLOTS_BY_SIZE") else core.SLOTS_BY_SIZE
print(f"registry: {len(core.cells())} cells; facts per size {core.FACTS_PROPORTIONAL}; U {U}; calibration {CAL} sha256 {file_sha256(CAL)}")

# S1 BB works everywhere, BB-0 at chance, BB-D far below -> BB selected at step 1, BEATS DENSE, LM preserved
an = scenario("S1_bb_works", lambda c: base(c, ("BB",)), {"outcome": "BB", "step": 1, "status": "COMPLETE", "interpretable": True, "cells_read": 57, "class:BB:4096": "INTERFACE_WORKS", "class:BB:16384": "INTERFACE_WORKS", "class:BB:65536": "INTERFACE_WORKS", "class:W7:16384": "INTERFACE_FAILS"})
if an:
    note = an["analysis"]["annotations"]["BB"]["65536"]
    check("S1: BB dense comparison BEATS DENSE, LM preserved", note["dense_comparison"]["label"] == "BEATS DENSE" and note["language_modelling"]["label"] == "LANGUAGE MODELLING PRESERVED", json.dumps({k: v.get("label") for k, v in note.items()}))
    check("S1: backbone contrasts not printed (both arms fail)", an["analysis"]["backbone_contrast"] == {"E7/W7": None, "A4E/A4": None})

# S2 only W7 (and E7, so the contrast is ADDS NOTHING) works -> W7 at step 3 with the encoder and W7 scope lines
an = scenario("S2_only_w7_works", lambda c: base(c, ("W7", "E7")), {"outcome": "W7", "step": 3, "status": "COMPLETE", "interpretable": True, "class:W7:4096": "INTERFACE_WORKS", "class:W7:65536": "INTERFACE_WORKS", "class:BB:16384": "INTERFACE_FAILS"})
if an:
    check("S2: contrast E7/W7 ADDS NOTHING", an["analysis"]["backbone_contrast"]["E7/W7"]["label"] == classes.BACKBONE_NOTHING)
    check("S2: scope", an["analysis"]["selection"]["scope"] == [classes.SCOPE_ENCODER, classes.SCOPE_W7_LIMIT, classes.SCOPE_A4_W7_SYSTEM])
    check("S2: W7 dense comparison vs D7 BEATS DENSE", an["analysis"]["annotations"]["W7"]["16384"]["dense_comparison"]["label"] == "BEATS DENSE")

# S3 nothing works
scenario("S3_none", lambda c: base(c, ()), {"outcome": "NO_INTERFACE_SELECTED", "step": 4, "status": "COMPLETE", "interpretable": True, "class:A4:4096": "INTERFACE_FAILS"})

# S4 R1 below 0.5 at 65,536 -> that size NOT_EVALUATED, INCONCLUSIVE at step 0
scenario("S4_65536_not_evaluated", lambda c: base(c, ("BB",), r1=0.40 if c.slots == 65536 else 0.95), {"outcome": "INCONCLUSIVE", "step": 0, "inconclusive": {"65536": "NOT_EVALUATED"}, "class:BB:65536": "NOT_EVALUATED", "class:BB:16384": "INTERFACE_WORKS"})

# S5 one registered cell missing -> NOT_INTERPRETED (INCOMPLETE), no classes
scenario("S5_missing_cell", lambda c: base(c, ("BB",)), {"outcome": "NOT_INTERPRETED (INCOMPLETE)", "status": "INCOMPLETE", "interpretable": False, "missing": ["BB-0-n65536-b101-o301-s1802"], "cells_read": 56}, drop=("BB-0-n65536-b101-o301-s1802",))

# S6 BB's B102 replicate fails at 16,384 -> BB INTERMEDIATE there; A4 works -> A4 at step 2
def s6(c):
    if c.arm == "BB" and c.replicate:
        return 0.03, True
    return None
scenario("S6_b102_demotes_bb_a4_works", lambda c: base(c, ("BB", "A4"), override=s6), {"outcome": "A4", "step": 2, "class:BB:16384": "INTERMEDIATE", "class:BB:4096": "INTERFACE_WORKS", "class:A4:16384": "INTERFACE_WORKS"})

# S7 BB works but BB-0 above chance at 65,536 -> MODEL_STORES_FACTS there; LM degraded (rise 0.08)
def s7(c):
    if c.arm == "BB-0" and c.slots == 65536:
        return 0.30, True
    return None
an = scenario("S7_model_stores_facts", lambda c: base(c, ("BB",), override=s7), {"outcome": "NO_INTERFACE_SELECTED", "class:BB:65536": "MODEL_STORES_FACTS", "class:BB:4096": "INTERFACE_WORKS"}, lm_rise=0.08)
if an:
    note = an["analysis"]["annotations"]["BB"]["65536"]
    check("S7: MODEL_STORES_FACTS -> NOT COMPARED; LM DEGRADED", note["dense_comparison"]["label"] == "NOT COMPARED" and note["language_modelling"]["label"] == "LANGUAGE MODELLING DEGRADED", json.dumps({k: v.get("label") for k, v in note.items()}))

# S8 G2 failed and one LEAKAGE flag -> NOT_INTERPRETED with both reasons, status COMPLETE
an = scenario("S8_g2_failed_leakage", lambda c: base(c, ("BB",)), {"outcome": "NOT_INTERPRETED", "status": "COMPLETE", "interpretable": False}, gates_over={"g2_passed": False}, leak=("W7-n4096-b101-o301-s1801",))
if an:
    check("S8: reasons", an["gate_reasons"] == ["G2 failed", "LEAKAGE: W7-n4096-b101-o301-s1801/A"], str(an["gate_reasons"]))

# S9 a zero accuracy in a ratio denominator: D7 at 0 correct while W7 is PARTIAL (dense comparison is made),
# and W7 at 0 while E7 is positive at 16,384 (the backbone contrast is printed). classes.ratio gives +inf.
def s9(c):
    if c.arm == "D7" and c.slots == 65536:
        return 0.0, False
    if c.arm == "W7" and c.slots == 65536:
        return 0.40, False
    if c.arm == "W7" and c.slots == 16384:
        return 0.0, True
    if c.arm == "E7":
        return 0.40, False
    return None
scenario("S9_zero_denominator", lambda c: base(c, (), override=s9), {"outcome": "NO_INTERFACE_SELECTED", "class:W7:65536": "INTERFACE_PARTIAL"})

# S10 the pool path (cmd_analyze, cmd_report) on a copy of S1's inputs, private ledger, rehearsal mode
print("== S10 pool path (cmd_analyze, cmd_report) on S1-like inputs")
run = build("S10_pool", lambda c: base(c, ("BB",)))
common = ["--mode", "rehearsal", "--run-dir", str(run), "--calibration", str(CAL), "--experiments-root", str(SCRATCH), "--ledger", str(SCRATCH / "ledger.json"), "--stage-cap-seconds", "300", "--workers", "1"]
a = stages.main(["analyze", *common])
r = stages.main(["report", *common])
an = json.loads((run / "analysis.json").read_text()) if (run / "analysis.json").is_file() else {}
check("S10: cmd_analyze 0, cmd_report 0, outcome BB, analyze manifest COMPLETE", a == 0 and r == 0 and an.get("analysis", {}).get("selection", {}).get("outcome") == "BB" and json.loads((run / "analyze" / "manifest.json").read_text())["status"] == "COMPLETE", f"analyze {a}, report {r}")
check("S10: failed_tasks empty although the analyze/report manifests are now in the run directory", an.get("failed_tasks") == [], str(an.get("failed_tasks")))

print(f"\nFAILED CHECKS: {len(FAILURES)} {FAILURES}")
