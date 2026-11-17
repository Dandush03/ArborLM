"""Re-check B, R3: the recomputation rule on the kept end-to-end run (stand-ins, test seeds). The registered records are evaluate/, the recomputed ones recompute/; each probe edits a COPY of the
recomputed study in memory and passes both to recompute.outcome_under_recomputation (the object under test). My own checks, independent of the implementation's reading of the rule:
  (1) every edited leaf appears in the listed differences;  (2) the cells marked NOT_EVALUATED are exactly the edited cells;  (3) the label is ENGINEERING-FAILURE iff a verdict differs between the
  registered study and the recomputed one (the verdict comparison uses analysis.verdicts, the function the ruling names);  (4) incomplete inputs give INCOMPLETE with no class printed.
Run with the clone's code: cwd = clone, PYTHONPATH = clone/src.  Usage: python r3_recompute.py <e2e parent dir> <out.json>
"""

import copy
import json
import sys
from pathlib import Path

E = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(E / "clone"))
from studies.p10s2 import analysis, recompute, stages  # noqa: E402

REG = E / "registered-run"
plan = json.loads((E / "clone" / "studies/p10s2/freeze/plan.json").read_text())
design, pre = plan["design"], plan["prefreeze"]
gates = json.loads((REG / "gates.json").read_text())
registered = stages.assemble_study(REG, design, pre, gates)
recomputed0 = stages.assemble_study(REG, design, pre, gates, subdir="recompute")


def leaf_set(d: dict, path: list) -> None:  # noqa: ANN001
    *head, last = path
    for k in head:
        d = d[k]
    d[last] = d[last]


def run(name: str, edit, *, memory: bool = False) -> dict:  # noqa: ANN001
    rec = copy.deepcopy(recomputed0)
    edited = edit(rec) if edit else []
    out = recompute.outcome_under_recomputation(registered, rec, "frozen-code", memory_exceeded=memory)
    st = out["recomputation"]
    diffs = st.get("differences", [])
    listed = {(d["cell"], d["path"]) for d in diffs}
    v_reg = analysis.verdicts(registered)
    v_rec = analysis.verdicts({**copy.deepcopy(registered), "baseline": rec.get("baseline", {}), "replicates": rec.get("replicates", [])})
    changed = analysis.verdict_changes(v_reg, v_rec)
    edited_cells = sorted({c for c, _p in edited if c.startswith("r")and "/" in c and c.count("/") == 2})
    row = {
        "probe": name, "label": out["label"], "state": st.get("state"), "n_differences": len(diffs), "edited": [f"{c} {p}" for c, p in edited],
        "every_edit_listed": all(any(c == lc and (p == lp or lp.startswith(p) or p.startswith(lp)) for lc, lp in listed) for c, p in edited),
        "not_evaluated_cells": st.get("not_evaluated_cells"), "ne_equals_edited_cells": sorted(st.get("not_evaluated_cells") or []) == edited_cells,
        "verdict_changes_mine": changed[:8], "ef_iff_verdict_change": (out["label"].startswith("ENGINEERING-FAILURE")) == bool(changed) if st.get("state") == "complete" else None,
        "classes_printed": any(c.get("class") not in (None, "NO CLASS (INCOMPLETE)") for by in out.get("classes", {}).values() for c in by.values()),
        "study_level": st.get("study_level"),
    }
    return row


def cell_score(rec: dict, r: int, lab: str, snap: str, panel: str, delta: float) -> list:
    sc = rec["replicates"][r]["cells"][lab]["scores"][snap]["panels"][panel]
    sc["mean"] = sc["mean"] + delta
    return [(lab, f"/scores/{snap}/panels/{panel}/mean")]


def baseline(rec: dict, who: str, panel: str, delta: float) -> list:
    b = rec["baseline"][who][panel]
    if who == "student":
        b["panel"]["mean"] += delta
        return [("baseline", f"/{who}/{panel}/panel/mean")]
    b["mean"] += delta
    return [("baseline", f"/{who}/{panel}/mean")]


def gen_all(rec: dict, group: str, value: float) -> list:
    out = []
    for r, rep in enumerate(rec["replicates"]):
        for lab, c in rep["cells"].items():
            if f"/{group}/" in lab and c.get("status") == "completed":
                for snap, s in c["scores"].items():
                    if "gen" in s:
                        s["gen"]["loss_increase"] = value
                        out.append((lab, f"/scores/{snap}/gen/loss_increase"))
    return out


def ablation_to_unablated(rec: dict, r: int, lab: str) -> list:
    out = []
    s = rec["replicates"][r]["cells"][lab]["scores"][lab]
    ab = s.get("ablations", {})
    for kind, by in ab.items():
        if isinstance(by, dict):
            for panel, v in by.items():
                if isinstance(v, dict) and "mean" in v:
                    v["mean"] = 1.0
                    out.append((lab, f"/scores/{lab}/ablations/{kind}/{panel}/mean"))
    return out


def router_acc(rec: dict, r: int, value: float) -> list:
    rec["replicates"][r]["routers"]["AB"]["accuracy"]["A"] = value
    return [(f"r{r}/routers", "/AB/accuracy/A")]


def drop_rep_section(rec: dict, r: int, sec: str) -> list:
    rec["replicates"][r][sec] = {}
    return []


probes = [
    run("identical", None),
    run("cell score +1e-15 (one ulp-scale change, MAF/AB E_A)", lambda rec: cell_score(rec, 0, "r0/MAF/AB", "r0/MAF/AB", "E_A", 1e-15)),
    run("cell score +0.25 (ETABLE/A E_A, the exercise's own probe)", lambda rec: cell_score(rec, 0, "r0/ETABLE/A", "r0/ETABLE/A", "E_A", 0.25)),
    run("Stage 0 student E_A mean +0.05", lambda rec: baseline(rec, "student", "E_A", 0.05)),
    run("teacher E_A mean -0.6 (gap undefined)", lambda rec: baseline(rec, "teacher", "E_A", -0.6)),
    run("GEN loss increase 1.0 nats on every M-append-frozen snapshot", lambda rec: gen_all(rec, "MAF", 1.0)),
    run("permutation ablations of r0/MAF/AB set to 1.0 (control)", lambda rec: ablation_to_unablated(rec, 0, "r0/MAF/AB")),
    run("router r0 AB accuracy on A set to 1.0", lambda rec: router_acc(rec, 0, 1.0)),
    run("recomputed r1 ensemble missing", lambda rec: drop_rep_section(rec, 1, "ensemble")),
    run("memory exceeded in the recomputation", None, memory=True),
]
Path(sys.argv[2]).write_text(json.dumps(probes, indent=1, default=str))
for p in probes:
    print(json.dumps(p, default=str)[:900])
