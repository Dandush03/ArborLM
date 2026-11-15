"""Re-check of ADR-0021 revision 3: registry, budget, cuts and a 16 h comparison (stdlib only).

Inputs are the numbers printed in revision 3 itself (sections 5.1, 5.4, 6.1, 10.1, 10.3) and the
per-update costs that revision 3 cites (adr-0021-review/outputs/c4b_matrix_budget_final.txt).
No ArborLM code, no seed.
"""

U_P = 8192
RUN = {4096: 6 * U_P, 16384: 4 * U_P, 65536: 2 * U_P}  # section 5.4
COST = {  # s per update, six contended workers, from c4b (cited by revision 3, section 10.3)
    "F": {4096: 0.0095, 16384: 0.0143, 65536: 0.0368},
    "T": {4096: 0.0189, 16384: 0.0285, 65536: 0.0735},
    "H8": {4096: 0.0050, 16384: 0.0063, 65536: 0.0120},
    "D": {4096: 0.0095, 16384: 0.0143, 65536: 0.0487},
    "R2": {4096: 0.0050, 16384: 0.0063, 65536: 0.0120},
}
ALL7 = [(2048, 4096), (8192, 4096), (32768, 4096), (8192, 16384), (32768, 16384), (8192, 65536), (32768, 65536)]
CELLS = {
    "F": ALL7,
    "T": ALL7,
    "H8": ALL7,
    "D": [(2048, 4096), (8192, 16384), (8192, 65536), (32768, 16384), (32768, 65536)],
    "R2": [(2048, 4096), (8192, 16384), (8192, 65536), (32768, 65536)],
}


def updates(arm, slots):
    return U_P if arm == "R2" else RUN[slots]


per_arm = {a: sum(COST[a][s] * updates(a, s) for _, s in CELLS[a]) for a in CELLS}
n_cfg = sum(len(v) for v in CELLS.values())
per_rep = sum(per_arm.values())
print(f"configurations per replicate {n_cfg}; registered cells x5 = {5 * n_cfg}")
print("per replicate s: " + ", ".join(f"{a} {v:,.0f}" for a, v in per_arm.items()) + f"; total {per_rep:,.0f}")
train_cpu_h = 5 * per_rep / 3600
seed_block_cpu_h = 2 * per_arm["F"] / 3600
print(f"training 150 cells {train_cpu_h:.2f} CPU-h -> {train_cpu_h / 6:.2f} charged h; seed block per draw (14 cells) {seed_block_cpu_h:.2f} CPU-h -> {seed_block_cpu_h / 6:.2f} h")

# calibration, section 10.1
load = 2 * (4 * 65536 * COST["F"][4096] + 3 * 65536 * COST["F"][16384])
diag = [(2048, 4096), (8192, 16384), (32768, 65536)]
upcheck = 2 * sum(U_P * (COST["F"][s] + COST["R2"][s]) for _, s in diag)
h8 = 2 * sum(U_P * COST["H8"][s] for _, s in diag)
dense = 2 * 3 * (RUN[16384] * COST["D"][16384] + RUN[65536] * COST["D"][65536])
cal = load + upcheck + h8 + dense
print(f"calibration runs 14+12+6+12 = {14 + 12 + 6 + 12}; CPU-h load {load / 3600:.2f}, U_P+H8 {(upcheck + h8) / 3600:.2f}, dense {dense / 3600:.2f}, total {cal / 3600:.2f} -> {cal / 3600 / 6:.2f} charged h")

before = 1.4  # revision 3 table: calibration ~0.9 + rehearsal ~0.45
ev, fixed = 1.0, 0.4
rem1 = train_cpu_h / 6 + seed_block_cpu_h / 6 + ev + fixed
rem2 = rem1 + seed_block_cpu_h / 6
for cap in (12.0, 16.0):
    print(f"\n== cap {cap:.0f} h; charged before rule {before}")
    for name, rem in (("draw-1 block", rem1), ("draws 1+2 blocks", rem2), ("no seed block", rem1 - seed_block_cpu_h / 6)):
        tot = before + 2 * rem
        print(f"  {name}: remaining {rem:.2f} h; charged + 2x = {tot:.2f} h; slack {cap - tot:+.2f} h; tolerable overrun of remaining {(cap - before) / 2 - rem:+.2f} h ({((cap - before) / 2 / rem - 1) * 100:+.0f}%)")

d864 = 5 * COST["D"][65536] * RUN[65536] / 3600 / 6
d3216 = 5 * COST["D"][16384] * RUN[16384] / 3600 / 6
print(f"\ncut 2 (draw-1 block) saves {seed_block_cpu_h / 6:.2f} h ({2 * seed_block_cpu_h / 6:.2f} doubled)")
print(f"cut 3 D-OQ 8K/64K (A2) saves {d864:.2f} h ({2 * d864:.2f} doubled); D-OQ 32K/16K (B1) saves {d3216:.2f} h ({2 * d3216:.2f} doubled); both {2 * (d864 + d3216):.2f} doubled")
print(f"sensitivity, doubled: T-OQ 2.5x instead of 2x +{2 * 5 * 0.25 * per_arm['T'] / 3600 / 6:.2f} h; D-OQ +20% +{2 * 0.2 * 5 * per_arm['D'] / 3600 / 6:.2f} h; evaluation +20% +{2 * 0.2 * ev:.2f} h")

print("\n== overload row, per its U_P' (training only; evaluation and its 4 calibration runs not included)")
for up in (8192, 16384, 32768):
    base = sum(COST[a][16384] * 4 * up + COST[a][65536] * 2 * up for a in ("F", "T", "H8")) + COST["R2"][65536] * up
    d_large = COST["D"][65536] * 2 * up
    d_both = d_large + COST["D"][16384] * 4 * up
    lo, hi = 5 * (base + d_large) / 3600 / 6, 5 * (base + d_both) / 3600 / 6
    print(f"  U_P'={up:>6}: charged {lo:.2f}-{hi:.2f} h (D-OQ at larger cell only / at both cells); doubled {2 * lo:.2f}-{2 * hi:.2f} h")
