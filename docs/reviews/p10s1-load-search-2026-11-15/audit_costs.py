"""Auditor's cost recomputation for ADR-0021 s24 (projections from measured calibration rates; NOT measurements).

Rates: seconds per update from the calibration (six single-thread workers contending), two sets:
  MAN = manifest task seconds / updates (includes start-up and the calibration-grid evaluations)  [the draft's basis]
  TRN = train.json wall seconds / updates (training only)
T-OQ = 2 x F-OQ (unmeasured; ADR s10.3 assumption). D-OQ at 4,096 slots unmeasured: assumed 0.5 x its 16,384 rate.
Charged hours = wall of a stage; a registered stage of many runs on six workers is taken as sum(run seconds)/6 (perfect packing).
Usage: python3 -I audit_costs.py <run_dir>
"""

import json
import sys
from pathlib import Path

RUN = Path(sys.argv[1])
man = json.loads((RUN / "calibrate" / "manifest.json").read_text())
MAN, TRN = {}, {}
for t in man["tasks"]:
    tr = json.loads(Path(t["result_path"]).read_text())
    key = (tr["arm"], tr["facts"], tr["slots"], tr["learning_rate"], tr["run_updates"])
    MAN.setdefault(key, []).append(t["seconds"] / tr["run_updates"])
    TRN.setdefault(key, []).append(tr["wall_seconds"] / tr["run_updates"])
avg = lambda d: {k: sum(v) / len(v) for k, v in d.items()}
MAN, TRN = avg(MAN), avg(TRN)
H = 3600.0


def rates(R):
    f = lambda facts, slots, run=65536, arm="F-OQ", lr=0.003: R[(arm, facts, slots, lr, run)]
    r = {
        ("F-OQ", 2048, 4096): f(8192, 4096), ("F-OQ", 8192, 4096): f(8192, 4096), ("F-OQ", 24576, 4096): (f(16384, 4096) + f(32768, 4096)) / 2,
        ("F-OQ", 32768, 4096): f(32768, 4096), ("F-OQ", 8192, 16384): f(8192, 16384), ("F-OQ", 32768, 16384): f(32768, 16384),
        ("F-OQ", 24576, 16384): (f(8192, 16384) + f(32768, 16384)) / 2, ("F-OQ", 65536, 16384): f(65536, 16384),
        ("F-OQ", 8192, 65536): f(32768, 65536, 8192), ("F-OQ", 32768, 65536): f(32768, 65536, 8192), ("F-OQ", 65536, 65536): f(32768, 65536, 8192),
        ("F-OQ", 24576, 65536): f(32768, 65536, 8192),
        ("H8", 4096): f(2048, 4096, 8192, "H8"), ("H8", 16384): f(8192, 16384, 8192, "H8"), ("H8", 65536): f(32768, 65536, 8192, "H8"),
        ("R2", 4096): f(2048, 4096, 8192, "R2", 0.003) if ("R2", 2048, 4096, 0.003, 8192) in R else None,
        ("D-OQ", 16384): f(8192, 16384, 32768, "D-OQ"), ("D-OQ", 65536): f(32768, 65536, 16384, "D-OQ"),
    }
    r[("D-OQ", 4096)] = 0.5 * r[("D-OQ", 16384)]
    for s, (fa, sl) in {4096: (2048, 4096), 16384: (8192, 16384), 65536: (32768, 65536)}.items():
        r[("R2", s)] = R[("R2", fa, sl, 0.003, 8192)]
    return r


def cell_cost(r, facts, slots, run, arms=("F-OQ", "T-OQ", "H8")):
    fo = r[("F-OQ", facts, slots)]
    per = {"F-OQ": fo, "T-OQ": 2 * fo, "H8": r[("H8", slots)], "D-OQ": r[("D-OQ", slots)], "R2": r[("R2", slots)]}
    return sum(per[a] for a in arms) * run


def unchanged_study(r):
    U = {4096: 49152, 16384: 32768, 65536: 16384}
    grid = [(2048, 4096), (8192, 4096), (32768, 4096), (8192, 16384), (32768, 16384), (8192, 65536), (32768, 65536)]
    s = sum(cell_cost(r, f, n, U[n]) for f, n in grid)
    s += sum(r[("D-OQ", n)] * U[n] for f, n in [(2048, 4096), (8192, 16384), (8192, 65536), (32768, 16384), (32768, 65536)])
    s += sum(r[("R2", n)] * 8192 for f, n in [(2048, 4096), (8192, 16384), (8192, 65536), (32768, 65536)])
    seed = sum(r[("F-OQ", f, n)] * U[n] for f, n in grid) * 2
    return s, seed


for name, R in (("MAN (manifest, draft's basis)", MAN), ("TRN (training wall only)", TRN)):
    r = rates(R)
    print(f"\n######## rate set {name}")
    print("  F-OQ s/upd: " + ", ".join(f"{k[1]}/{k[2]}={v:.5f}" for k, v in r.items() if k[0] == "F-OQ"))
    print("  H8/D-OQ/R2: " + ", ".join(f"{k[0]}@{k[1]}={v:.5f}" for k, v in r.items() if k[0] != "F-OQ"))
    # --- extension stages
    cands = [65536, 131072, 196608, 262144, 393216, 524288]
    x8, x6, y4 = r[("F-OQ", 32768, 4096)], r[("F-OQ", 24576, 4096)], r[("F-OQ", 65536, 16384)]
    cum, cpu = 0.0, 0.0
    print("  extension stages (wall per run; stage wall = max):")
    for a, b in zip(cands, cands[1:]):
        w8 = (b - a) * x8
        w6 = (b if a == 65536 else b - a) * x6
        w4 = (b - a) * y4 if b <= 262144 else 0.0
        st = max(w8, w6, w4)
        cum += st
        cpu += 2 * (w8 + w6 + w4)
        print(f"    to {b:7d}: X8 {w8:6.0f}  X6 {w6:6.0f}  Y4 {w4:6.0f}  stage {st:6.0f} s  cumulative {cum / H:.2f} h")
    print(f"    worker-seconds of all six runs to ceiling: {cpu:.0f} ({cpu / H:.1f} h)")
    # --- unchanged study
    s, seed = unchanged_study(r)
    print(f"  unchanged registered training per replicate: {s:.0f} s  -> 5 replicates / 6 workers = {5 * s / 6 / H:.2f} h; seed block per draw {seed / 6 / H:.2f} h")
    print("    (ADR s10.3 projection: 15,440 s per replicate, 3.6 h; remaining total incl. eval 1.0 h, gates etc 0.4 h, both seed blocks: 5.6 h)")
    remaining = 5 * s / 6 / H + 2 * seed / 6 / H + 1.0 + 0.4
    print(f"    remaining with the s10.3 eval/gates allowances and both seed blocks: {remaining:.2f} h (draft uses 5.6)")
    # --- row L, F* = 32,768, U_P' = 16,384
    fo4, h4 = r[("F-OQ", 32768, 4096)], r[("H8", 4096)]
    small = (fo4 * 3 + h4)
    large_ext = (r[("F-OQ", 32768, 16384)] * 3 + r[("H8", 16384)] + r[("D-OQ", 16384)]) * (65536 - 32768)
    print(f"  row L smaller cell per update per replicate (F-OQ+T-OQ+H8): {small:.4f} s; 1 x 131,072 updates x 5 / 6 = {small * 131072 * 5 / 6 / H:.2f} h")
    base_ext = {"expected": 2.3, "worst (ceiling stages, no dense)": 2.03 + 0.51 + 1.22}
    for UL in (131072, 196608, 262144, 393216, 524288):
        add32 = (small * (UL - 49152) + large_ext) * 5 / 6 / H
        f6 = r[("F-OQ", 24576, 4096)]
        small6 = f6 * 3 + h4
        l6 = (r[("F-OQ", 24576, 16384)] * 3 + r[("H8", 16384)] + r[("D-OQ", 16384)])
        add24_16 = (small6 * UL + l6 * 65536 + r[("R2", 65536)] * 8192) * 5 / 6 / H
        add24_32 = (small6 * UL + l6 * 131072 + r[("R2", 65536)] * 8192) * 5 / 6 / H
        print(f"    U_L={UL:7d}: added h  F*=32K {add32:5.2f} | F*=24K U_P'=16K {add24_16:5.2f} | F*=24K U_P'=32K {add24_32:5.2f}")
    s16 = r[("F-OQ", 65536, 16384)] * 3 + r[("H8", 16384)]
    for upp in (16384, 32768):
        l64 = (r[("F-OQ", 65536, 65536)] * 3 + r[("H8", 65536)] + r[("D-OQ", 65536)]) * 2 * upp + r[("R2", 65536)] * upp
        for UL in (131072, 196608, 262144):
            print(f"    16K row, U_P'={upp}, U_L={UL}: added {(s16 * UL + l64) * 5 / 6 / H:5.2f} h")
    print("  cap needed (twofold rule) = charged so far 1.57 + extension (actual) + rehearsal 0.45 + 2 x (remaining + added rows)")
    for ext_label, ext in (("ext 2.3", 2.3), ("ext 3.8", 3.8), ("ext 7.5 (ceiling)", 7.5)):
        for UL in (196608, 262144, 393216, 524288):
            add32 = (small * (UL - 49152) + large_ext) * 5 / 6 / H
            print(f"    {ext_label:18s} L(F*=32K) U_L={UL:7d}: {1.57 + ext + 0.45 + 2 * (remaining + add32):5.1f} h   [with draft's 5.6 remaining: {1.57 + ext + 0.45 + 2 * (5.6 + add32):5.1f}]")
