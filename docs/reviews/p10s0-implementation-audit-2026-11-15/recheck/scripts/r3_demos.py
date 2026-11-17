"""Re-check of P10-S0 at 3a9a742: the first audit's demonstrations re-run against the fixed code (in-process; no seed is built except where stated;
the real worktree is only read: every refusal happens before a run directory is created; temporary directories live under the given scratch dir).
Claude (Opus 5.5) review; Astra review: NOT_PERFORMED; not a human approval."""

import contextlib
import io
import json
import math
import sys
import tempfile
from pathlib import Path

from studies.p10s0 import analysis, budget, core, report, stages
from studies.p10s0 import classes as C
from studies.p10s0 import synthetic as syn

SCRATCH = Path(sys.argv[1])
SCRATCH.mkdir(parents=True, exist_ok=True)
out: dict = {}


def main_rc(argv):
    err, so = io.StringIO(), io.StringIO()
    with contextlib.redirect_stderr(err), contextlib.redirect_stdout(so):
        try:
            rc = stages.main(argv)
        except SystemExit as e:  # argparse
            rc = f"SystemExit {e.code}"
        except Exception as e:  # noqa: BLE001
            rc = f"EXC {type(e).__name__}: {e}"
    return {"rc": rc, "stderr": err.getvalue().strip()[-300:], "stdout": so.getvalue().strip()[-300:]}


tmp = Path(tempfile.mkdtemp(dir=SCRATCH))
# --- M1: typed commands reaching registered mode -----------------------------------------------------------------------------
typed = {
    "train q1 (no mode)": ["train", "--block", "q1", "--run-dir", str(tmp / "r1")],
    "train q1 --mode registered": ["train", "--block", "q1", "--mode", "registered", "--run-dir", str(tmp / "r2")],
    "gates --mode registered": ["gates", "--mode", "registered", "--run-dir", str(tmp / "r3")],
    "q1-gate (no mode)": ["q1-gate", "--run-dir", str(tmp / "r4")],
    "q1-gate --mode registered": ["q1-gate", "--mode", "registered", "--run-dir", str(tmp / "r4")],
    "analyze --mode registered": ["analyze", "--mode", "registered", "--run-dir", str(tmp / "r5")],
    "report --mode registered": ["report", "--mode", "registered", "--run-dir", str(tmp / "r6")],
    "work train --mode registered (no freeze commit)": ["work", "train", "--mode", "registered", "--run-dir", str(tmp / "r7"), "--labels", "Q1-A0-2K4K-d01-j0"],
    "work train --mode registered --freeze-commit HEAD (no plan in tree)": ["work", "train", "--mode", "registered", "--run-dir", str(tmp / "r8"), "--labels", "Q1-A0-2K4K-d01-j0", "--freeze-commit", "HEAD"],
    "work gates --mode registered --freeze-commit HEAD": ["work", "gates", "--mode", "registered", "--run-dir", str(tmp / "r9"), "--freeze-commit", "HEAD"],
    "registered q1 (HEAD as freeze commit)": ["registered", "q1", "--run-dir", str(tmp / "r10"), "--freeze-commit", "HEAD", "--caps", stages.CAPS_FILE],
}
out["M1_typed"] = {k: main_rc(v) for k, v in typed.items()}
out["M1_no_run_dir_created"] = sorted(p.name for p in tmp.iterdir())

# --- M2: each override on the driver (refused before the preconditions) -------------------------------------------------------
over = {
    "--stage-cap-seconds 1e9": ["--stage-cap-seconds", "1e9"], "--ledger-root": ["--ledger-root", str(tmp / "fresh")], "--experiments-root": ["--experiments-root", str(tmp)],
    "--rss-worker-bytes 1e12": ["--rss-worker-bytes", str(10**12)], "--rss-aggregate-bytes": ["--rss-aggregate-bytes", str(10**13)], "--synthetic-backbone": ["--synthetic-backbone"],
    "--only": ["--only", "Q1-A5-D-2K4K-d01-j0"], "--cut3": ["--cut3"], "--restore-split 1": ["--restore-split", "1"],
    # options whose value EQUALS the parser default are not detectable by a default comparison: try them explicitly
    "--restore-split <default>": ["--restore-split", str(stages._common_parser().parse_args([]).restore_split)],
    "--workers 6": ["--workers", "6"],
}
out["M2_driver"] = {k: main_rc(["registered", "q1", "--run-dir", str(tmp / "o"), "--freeze-commit", "HEAD", "--caps", stages.CAPS_FILE, *v]) for k, v in over.items()}
ns = stages.build_parser().parse_args(["registered", "q1", "--run-dir", "x", "--freeze-commit", "c", "--caps", stages.CAPS_FILE, "--stage-cap-seconds", "1e9", "--ledger-root", "/x", "--experiments-root", "/y", "--rss-worker-bytes", "1"])
ns.mode = "registered"
out["M2_functions_in_registered_mode_even_if_an_override_got_through"] = {"stage_cap(frozen 100)": stages.stage_cap(ns, 100.0), "ledger_root": str(stages.ledger_root(ns)), "experiments_root": str(stages.experiments_root(ns)), "limits": stages.limits(ns)}
out["M2_note"] = "stage_cap still returns a typed value first; it is only unreachable because cmd_registered refuses overrides before run_block"

# --- generation guards (m13, item 2) -------------------------------------------------------------------------------------------
gen = {
    "typed cap": ["generate", "--mode", "registered", "--draw", "1", "--run-dir", str(tmp / "g1"), "--i-understand-freeze-time", "--stage-cap-seconds", "1800"],
    "no cap flag": ["generate", "--mode", "registered", "--draw", "1", "--run-dir", str(tmp / "g2"), "--i-understand-freeze-time"],
    "flags ok, ledger override": ["generate", "--mode", "registered", "--draw", "1", "--run-dir", str(tmp / "g3"), "--i-understand-freeze-time", "--generation-cap-from-config", "--ledger-root", str(tmp)],
    "flags ok (this tree: no DECISION.md, provisional cap)": ["generate", "--mode", "registered", "--draw", "1", "--run-dir", str(tmp / "g4"), "--i-understand-freeze-time", "--generation-cap-from-config"],
}
out["generation_guards"] = {k: main_rc(v) for k, v in gen.items()}
out["generation_block_in_tree"] = core.generation_block()

# --- cap raise before the freeze (M5 ruling): does changing cap_hours in the config alone work? --------------------------------
cfg = core.load_config()
cfg2 = json.loads(json.dumps(cfg))
cfg2["resources"]["cap_hours"] = 20.0
try:
    core.validate_config(cfg2)
    out["cap_raise_config_only"] = "accepted"
except ValueError as e:
    out["cap_raise_config_only"] = f"REFUSED: {e}"[:300]
out["cap_used_by_holds_and_ledger"] = {"budget.holds default cap": core.CAP_HOURS, "Ledger default cap_seconds": core.Ledger(tmp / "l.json").cap_seconds}

# --- M6: reserve with the 60 s floor --------------------------------------------------------------------------------------------
A, R = 5.0, 5.0
caps_ar = {"analysis": max(60.0, 2 * A), "report": max(60.0, 2 * R)}
cap = core.CAP_HOURS * 3600
q1 = 20000.0
charged0 = cap - 2 * (q1 + A + R)
dec = budget.pre_q1_decision(charged0, 0.0, q1, q1 * 0.8, reserve_seconds=A + R)
led = core.Ledger(tmp / "m6.json")
led.charge("pre", "x", charged0)
led.charge("train-q1", "x", 2 * q1)  # Q1 ran to its cap (allowed)
try:
    led.require_room("analysis", caps_ar["analysis"])
    m6 = "analysis allowed"
except core.LedgerRefused as e:
    m6 = f"analysis REFUSED: {e}"
out["M6_floor_case"] = {"measured_analysis_s": A, "measured_report_s": R, "caps": caps_ar, "pre_q1_action": dec.action, "remaining_after_q1_at_cap_s": led.remaining(), "analysis_require_room": m6}
dec_none = budget.pre_q1_decision(cap - 2 * q1, 0.0, q1, q1 * 0.8, reserve_seconds=A + R)
dec_old = budget.pre_q1_decision(cap - 2 * q1, 0.0, q1, q1 * 0.8)
out["M6_reserve_changes_decision"] = {"with_reserve": dec_none.action, "without_reserve": dec_old.action}
post = budget.post_q1_decision(cap - 2 * (100 + 1000) - 2 * 10 + 1, 100, 1000, reserve_seconds=10)
out["M6_post_q1_reserve"] = {"cuts_when_reserve_tips": list(post.cuts)}

# --- M3: A5-D positive label: strings in every product -------------------------------------------------------------------------
run = syn.make_run(syn.a0_unreliable(), candidate="A5-D")
res = analysis.analyze(run)
d = Path(tempfile.mkdtemp(dir=SCRATCH))
core.write_record(d / "analysis.json", {**core.envelope("analysis"), "result": core.jsonable(res)})
core.write_record(d / "q1_gate.json", {**core.envelope("q1_gate"), "candidate": "A5-D", "outcome_row": 4, "blocks": {}})
paths = report.write_report(d, d / "results")
so = io.StringIO()
with contextlib.redirect_stdout(so):
    core.emit_stdout({"outcome": res["outcome"]["outcome"], "row": res["outcome"]["row"], "arm": res["outcome"]["arm"]})
strings = {"fourth": core.FOURTH_ARM_STRING, "f1": core.F1_ANNOTATION, "sentence": core.PROVENANCE_SENTENCE}
texts = {p.name: p.read_text(encoding="utf-8") for p in [d / "analysis.json", d / "q1_gate.json", *paths]}
texts["stdout"] = so.getvalue()
m3 = {}
for name, t in texts.items():
    t2 = json.dumps(json.loads(t), ensure_ascii=False) if name.endswith(".json") or name == "stdout" else t
    m3[name] = {"mentions_A5-D": "A5-D" in t2, **{k: (v in t2) for k, v in strings.items()}}
out["M3_outcome"] = (res["outcome"]["row"], res["outcome"]["label"], res["outcome"]["arm"])
out["M3_products"] = m3
# can a hand-built product kind that is not stamped carry an A5-D candidate without the strings?
core.write_record(d / "gates.json", {**core.envelope("gates"), "g10": {"candidates": ["A5-D", "A1"]}})
gt = (d / "gates.json").read_text()
out["M3_unstamped_kind_gates_json"] = {"mentions_A5-D": "A5-D" in gt, "has_provenance": core.has_provenance(json.dumps(json.loads(gt), ensure_ascii=False))}

# --- m1 ADDRESS STABLE ----------------------------------------------------------------------------------------------------------
obs = {(d_, j): C.SObservation(0.97, 0.97, True, True, 0.97, 0.97, False, 256, 0.01, 256, 0.1, (0.9 if (d_ * 2 + j) < 11 else math.nan), math.nan, 0.97, 0.97, 0.97) for d_ in range(1, 11) for j in (0, 1)}
out["m1_address_stable_11_of_20_nonfinite"] = C.address_stable(obs, {k: C.CellVerdict(C.SUCCEEDED) for k in obs})

# --- M9 banner, M10 cut-3 label ---------------------------------------------------------------------------------------------------
out["M9_banner_from_tree"] = report.banner_text({"p9ii_acceptance": core.p9ii_acceptance()})
out["M9_banner_missing"] = report.banner_text({})
run3 = syn.make_run(syn.a0_unreliable(), candidate="A5-D", cut3=True)
r3 = analysis.analyze(run3)
md3 = report.render_markdown(r3)
out["M10_cut3"] = {"outcome_label": r3["outcome"]["label"], "row": r3["outcome"]["row"], "label_in_md_count": md3.count(core.CUT3_LABEL), "item4_line": [l for l in md3.splitlines() if l.startswith("4. **Per size:**")], "classes_csv_has_label": core.CUT3_LABEL in report.classes_csv(r3), "pooled_8k16k": r3["arms"]["A0"]["8K/16K"].get("pooled")}
print(json.dumps(out, indent=1, ensure_ascii=False, default=str))
