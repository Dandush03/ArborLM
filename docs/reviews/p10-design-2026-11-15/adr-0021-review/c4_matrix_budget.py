"""C4: recount ADR-0021's matrix and recompute its training projection from the P9-I rehearsal
per-update costs (results/p9i-rehearsal-2026-11-14/rehearsal_cells.csv; six contended workers, 64-update
runs). Assumptions are the draft's (tree = 2 x flat, D-OQ = P9-I dense, H8 = R2) plus mine where P9-I
has no number (marked ASSUMED)."""
import csv
import statistics
import sys

rows = list(csv.DictReader(open(sys.argv[1])))
def med(prefix):
    v = [float(r["seconds_per_update"]) for r in rows if r["label"].startswith(prefix + "-")]
    return statistics.median(v)

cost = {
    ("FOQ", 4096): med("R1-n4096"), ("FOQ", 16384): med("R1-n16384"), ("FOQ", 65536): med("R1-n65536"),
    ("R2", 16384): med("R2-n16384"), ("R2", 4096): 0.0050, ("R2", 65536): 0.012,  # 4K ASSUMED; 64K from P9 (ADR-0017 I.10)
    ("DOQ", 16384): med("D-n16384"), ("DOQ", 4096): 0.0095, ("DOQ", 65536): med("BB-D-n65536"),  # 4K ASSUMED; 64K = BB-D
    ("D7", 16384): med("D7-n16384"), ("D7", 65536): med("D7-n65536"), ("D7", 4096): 0.0060,  # 4K ASSUMED
}
for n in (4096, 16384, 65536):
    cost[("H8", n)] = cost[("R2", n)]
    cost[("TOQ", n)] = 2 * cost[("FOQ", n)]
cost[("FOQW", 4096)] = 1.3 * cost[("FOQ", 4096)]  # ASSUMED
cost[("H8W", 4096)] = 1.2 * cost[("R2", 4096)]  # ASSUMED
cost[("H8N", 65536)] = 0.9 * cost[("R2", 65536)]  # ASSUMED
print("per-update cost (s, six contended workers):")
for k in sorted(cost):
    print(f"  {k[0]:5s} {k[1]:6d}: {cost[k]:.4f}")

SL = {"2K/4K": 4096, "8K/4K": 4096, "32K/4K": 4096, "8K/16K": 16384, "32K/16K": 16384, "8K/64K": 65536, "32K/64K": 65536}
ALL7 = list(SL)
draft = {
    "FOQ": ALL7, "H8": ALL7, "DOQ": ALL7,
    "TOQ": ["2K/4K", "8K/16K", "32K/4K", "32K/16K", "32K/64K"],
    "R2": ["2K/4K", "8K/16K", "8K/64K", "32K/64K"],
    "D7": ["2K/4K", "8K/16K", "32K/64K"],
    "FOQW": ["8K/4K"], "H8W": ["8K/4K"], "H8N": ["8K/64K"],
}
def run_len(arm, cell):
    if arm == "R2":
        return 1
    return {4096: 2, 16384: 3, 65536: 2}[SL[cell]]

def per_rep(matrix, up):
    tot, by = 0.0, {}
    for arm, cells in matrix.items():
        s = sum(cost[(arm, SL[c])] * run_len(arm, c) * up for c in cells)
        by[arm] = s
        tot += s
    return tot, by

n = sum(len(v) for v in draft.values())
print(f"\nconfigurations per replicate: {n}; x5 = {5*n}")
for up in (8192, 16384):
    tot, by = per_rep(draft, up)
    print(f"\nU_P={up}: per replicate {tot:,.0f} s; " + ", ".join(f"{a} {v:,.0f}" for a, v in by.items()))
    print(f"  5 replicates: {5*tot/3600:.1f} CPU-h; six workers (ideal packing) {5*tot/3600/6:.2f} h")
    longest = max(cost[(a, SL[c])] * run_len(a, c) * up for a, cs in draft.items() for c in cs)
    print(f"  longest single cell: {longest/60:.1f} min")

def charged(train_h, eval_h, fixed_h=0.4):
    return train_h + eval_h + fixed_h

print("\n== headroom (cap 12 h; calibration 0.3 h + rehearsal 0.45 h charged before the rule is applied)")
spent = 0.75
for up, evh in ((8192, 0.7), (16384, 0.9)):
    tot, _ = per_rep(draft, up)
    rem = charged(5 * tot / 3600 / 6, evh)
    print(f"  U_P={up}: remaining projected {rem:.2f} h; 2x = {2*rem:.2f} h vs {12-spent:.2f} h available -> {'fits' if 2*rem <= 12-spent else 'DOES NOT FIT'}")
    # cuts in the draft's order
    m = {k: list(v) for k, v in draft.items()}
    reps = 5
    for step, desc in ((2, "drop D7"), (3, "drop replicate 5"), (4, "drop 32K/4K everywhere")):
        if step == 2:
            m.pop("D7")
        if step == 3:
            reps = 4
        if step == 4:
            m = {k: [c for c in v if c != "32K/4K"] for k, v in m.items()}
        tot, _ = per_rep(m, up)
        rem = charged(reps * tot / 3600 / 6, evh * reps / 5)
        print(f"    after cut {step} ({desc}): {rem:.2f} h; 2x = {2*rem:.2f} -> {'fits' if 2*rem <= 12-spent else 'does not fit'}")

print("\n== recommended matrix (reviewer): drop iso-parameter cells and D7; T-OQ adds 8K/4K; D-OQ only at the larger cells")
rec = {
    "FOQ": ALL7, "H8": ALL7,
    "DOQ": ["8K/16K", "8K/64K", "32K/16K", "32K/64K", "2K/4K"],
    "TOQ": ["2K/4K", "8K/4K", "8K/16K", "32K/4K", "32K/16K", "32K/64K"],
    "R2": ["2K/4K", "8K/16K", "8K/64K", "32K/64K"],
}
nrec = sum(len(v) for v in rec.values())
for up in (8192,):
    tot, by = per_rep(rec, up)
    extra = 2 * sum(cost[("FOQ", SL[c])] * run_len("FOQ", c) * up for c in ALL7)  # seed block: two extra init seeds, F-OQ, replicate 1
    print(f"  configurations {nrec}; x5 = {5*nrec}; + seed block 14 cells")
    print(f"  per replicate {tot:,.0f} s; 5 replicates {5*tot/3600:.1f} CPU-h; seed block {extra/3600:.2f} CPU-h; six workers {(5*tot+extra)/3600/6:.2f} h")
    rem = charged((5 * tot + extra) / 3600 / 6, 0.7)
    print(f"  remaining projected {rem:.2f} h; 2x = {2*rem:.2f} vs 8.0 h cap less 0.75 -> {'fits' if 2*rem <= 8-0.75 else 'does not fit'}")
