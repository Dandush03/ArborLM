# ruff: noqa
"""Seed block (descriptive, section 6.2): i on Panel A at U_P and U_run for the main cell and the two extra init seeds of each draw."""
import os, sys, json
sys.path.insert(0, os.path.dirname(__file__))
from auditlib import View, load_cells, U_P_ROW
cells = load_cells()
for d in (1, 2):
    for (f, n) in ((2048,1024),(2048,4096),(8192,1024),(8192,4096),(8192,16384),(32768,4096),(32768,16384)):
        keys = [("P","F-OQ",f,n,d,2100+d)] + [("SB","F-OQ",f,n,d,s) for s in ((2111,2121) if d==1 else (2112,2122))]
        up = U_P_ROW[f]
        row = []
        for k in keys:
            c = cells[k]; v = View(c, "A")
            row.append((k[5], c["meta"]["learning_rate"], c["meta"]["run_updates"], round(v.i(up),3), round(v.i(v.run),3), round(v.a_use(v.run),4)))
        across = [round(View(cells[("P","F-OQ",f,n,r,2100+r)],"A").i(View(cells[("P","F-OQ",f,n,r,2100+r)],"A").run),3) for r in range(1,6)]
        print(f"draw{d} {f}/{n}: (init, lr, run, i@U_P, i@U_run, a_use@U_run) {row}   main cells i@U_run across draws {across}")
