"""Calibration-only: a data-derived partition control (reviewer suggestion, NOT registered).
Q-partition: 16 groups of 256 from step-1 greedy at page size 256 on the calibration A0; then the
L-BCOAX construction inside those groups (L-QCOAX). Compared with L-COAX (flat, trees) and L-BCOAX
(trees), in-sample on the calibration stream, both tie rules. Never opens an evaluation trace.
Usage: .venv/bin/python -I .../rereview/scripts/calib_learned_partition.py --jobs 16"""
import argparse, json, statistics as st, sys
from multiprocessing import Pool
sys.dont_write_bytecode = True
HERE = __file__.rsplit("/", 1)[0]
sys.path.insert(0, HERE); sys.path.insert(0, HERE.rsplit("/rereview", 1)[0] + "/scripts")
import calib_coaccess as old  # noqa: E402
import rev3_layouts as L  # noqa: E402
from calib_partitions import sim  # noqa: E402
OUT = "docs/reviews/p7b-spec-review-2026-11-13/rereview/outputs"

def work(args):
    label, kind, idx = args
    rec = json.load(open(f"{old.TREC}/{label}.json"))
    cs = rec["files"]["calibration"]["selected"]
    path = f"{old.RAW}/{rec['trace_dir']}/{cs['file']}"
    assert "eval_" not in path and old.sha256(path) == cs["sha256"]
    sel = old.read_i16(path)
    f = L.counts_of(sel); A = L.affinity0(sel, 32768)
    qgroups = L.greedy_pages(list(range(L.SLOTS)), 256, f, A)
    out = {"label": label, "kind": kind, "m": {}, "files_read": [path]}
    for R, C in ((2, 32), (8, 8)):
        lay = {"COAX": L.coax(R, f, A)[0], "Q": L.group_coax(qgroups, R, f, A)[0]}
        if kind != "flat":
            lay["B"] = L.group_coax(L.branch_groups(), R, f, A)[0]
        for n, pg in lay.items():
            out["m"][f"{n}|R{R}C{C}"] = sim(sel, pg, R, C)
    return out

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--jobs", type=int, default=16); a = ap.parse_args()
    with Pool(a.jobs) as p:
        res = p.map(work, old.registered(), chunksize=1)
    assert not any("eval_" in x for r in res for x in r["files_read"])
    json.dump(res, open(f"{OUT}/calib_learned_partition.json", "w"))
    for key in ("R2C32", "R8C8"):
        for tie in ("asc", "desc"):
            for kind in ("flat", "fixed_tree", "learned_tree"):
                rr = [r for r in res if r["kind"] == kind]
                mc = st.fmean(r["m"][f"COAX|{key}"][tie] for r in rr)
                mq = st.fmean(r["m"][f"Q|{key}"][tie] for r in rr)
                s = f"{key} {tie} {kind:12s} m(QCOAX)/m(COAX) {mq / mc:.3f}"
                if kind != "flat":
                    mb = st.fmean(r["m"][f"B|{key}"][tie] for r in rr)
                    s += f"  m(BCOAX)/m(COAX) {mb / mc:.3f}  m(BCOAX)/m(QCOAX) {mb / mq:.3f}"
                print(s)
    print("evaluation files read: 0; calibration files read:", len(res))

if __name__ == "__main__":
    main()
