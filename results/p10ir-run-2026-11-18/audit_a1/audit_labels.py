# ruff: noqa
"""Independent recomputation of P10-I-R stage A1 labels from the a1 item records (auditor's own code).

Reads only raw JSON: a1/items/*/read.*.json and item.json, P10-S1's eval.json main counts (for the plateau check),
and analysis.json (for the comparison only). Imports nothing from studies.* or arborlm.*.
Rules cited from ADR-0029: 8.1 retention, 8.2 accounting, 8.3 tree rows, 8.4 index rows, 9 combination and plateau.

Run: python3 -B audit_labels.py   (system python 3, standard library only)
"""

import glob
import json
import math
import os
import statistics
import sys

RUN = "/Users/daniellaloush/dandush03/ArborLM/experiments/P10IR-registered-20261118"
S1 = "/Users/daniellaloush/dandush03/ArborLM/experiments/P10S1-registered-attempt2-20261117"
OUT = os.path.dirname(os.path.abspath(__file__))

# thresholds written from the ADR text (not read from the config): sections 8.1, 8.3, 8.4, 9
GAP, MARGIN, RATIO, FLOOR_A, CLOSURE, R_MIN, H_MARGIN, PLATEAU, TREE_CAND = 0.5, 0.25, 0.90, 0.25, 0.5, 0.90, 0.25, 0.10, 512
CELLS = {  # section 4 table; role from section 9
    "2K/1K": dict(f=2048, n=1024, role="printed", up=8192, run=49152, traj=(16384, 32768)),
    "2K/4K": dict(f=2048, n=4096, role="printed", up=8192, run=49152, traj=(16384, 32768)),
    "8K/4K": dict(f=8192, n=4096, role="primary", up=8192, run=49152, traj=(16384, 32768)),
    "8K/16K": dict(f=8192, n=16384, role="printed", up=8192, run=49152, traj=(16384, 32768)),
    "32K/16K": dict(f=32768, n=16384, role="primary", up=16384, run=98304, traj=(32768, 65536)),
    "8K/1K": dict(f=8192, n=1024, role="loaded", up=8192, run=393216, traj=(49152, 196608)),
    "32K/4K": dict(f=32768, n=4096, role="loaded", up=16384, run=786432, traj=(98304, 393216)),
}
BUDGETS = [128, 256, 512, 1024, 2048]
I64_SEEDS = [298001, 298002, 298003]
PANELS = ("A", "B")


def log_binom_pmf(n, k, p):
    return math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1) + k * math.log(p) + (n - k) * math.log1p(-p)


_HIGH = {}


def chance_high(n, tests=40, alpha=0.001, p=1 / 32):
    """Largest k with P(X >= k) > alpha / tests / 2 (upper end of the exact central binomial interval; G2, 40 tests)."""
    if n in _HIGH:
        return _HIGH[n]
    tail, acc = alpha / tests / 2, 0.0
    for k in range(n, -1, -1):
        acc += math.exp(log_binom_pmf(n, k, p))
        if acc > tail:
            _HIGH[n] = k
            return k
    raise AssertionError


def fano(acc):
    e = 1.0 - acc
    h = 0.0 if e <= 0 or e >= 1 else -(e * math.log2(e) + (1 - e) * math.log2(1 - e))
    return 5.0 - h - e * math.log2(31)


def bits(useful, n):
    if n <= 0 or useful <= chance_high(n):
        return 0.0
    return fano(useful / n)


FLOOR_I = fano(FLOOR_A)


def cell_of(facts, slots):
    for name, c in CELLS.items():
        if c["f"] == facts and c["n"] == slots:
            return name
    raise KeyError((facts, slots))


def load_items():
    items = {}
    for path in sorted(glob.glob(f"{RUN}/a1/items/*/item.json")):
        d = os.path.dirname(path)
        it = json.load(open(path))
        reads = {}
        for rp in glob.glob(f"{d}/read.*.json"):
            r = json.load(open(rp))
            reads[r["read"]] = r
        key = (cell_of(it["facts"], it["slots"]), it["arm"], it["draw"], it["update"])
        assert key not in items, key
        items[key] = {"item": it, "reads": reads, "dir": d}
    return items


def gate_failures(item):
    return {k: g for k, g in item["gates"].items() if g.get("passed") is not True}


def restored(ix, iy):
    if iy < FLOOR_I:
        return "WEAK"
    return "RESTORED" if (iy - ix <= MARGIN + 1e-12 and ix >= RATIO * iy - 1e-12) else "NOT RESTORED"


def tree_row(i, cr8):
    if any(i["F0"][p] < FLOOR_I for p in PANELS):
        return "NOT EVALUABLE", {}
    gap = {p: i["F0"][p] - i["T0"][p] >= GAP - 1e-12 for p in PANELS}
    if not any(gap.values()):
        return "NO GAP", {}
    if not all(gap.values()):
        return "MIXED-PANEL", {}
    g = {r: {p: (i[r][p] - i["T0"][p]) / (i["F0"][p] - i["T0"][p]) for p in PANELS} for r in ("T1", "T3", "T2")}

    def cond(r):  # literal: (RESTORED on both panels) or (closure >= 0.5 on both panels)
        return all(restored(i[r][p], i["F0"][p]) == "RESTORED" for p in PANELS) or all(g[r][p] >= CLOSURE - 1e-12 for p in PANELS)

    P, C, J = cond("T1"), cond("T3"), cond("T2")
    H = all(i["T2"][p] <= i["T0"][p] - H_MARGIN + 1e-12 for p in PANELS)
    R = cr8 >= R_MIN - 1e-12
    tags = dict(P=P, C=C, J=J, H=H, R=R, g_P=g["T1"], g_C=g["T3"], g_PC=g["T2"])
    if P and C:
        row = "PRIORS AND CANDIDATES, SEPARATELY"
    elif P:
        row = "PRIORS"
    elif C:
        row = "CANDIDATES"
    elif J:
        row = "JOINT"
    elif H:
        row = "EXACT SEARCH HARMS"
    elif R:
        row = "CONTENT"
    else:
        row = "NOT IDENTIFIED"
    return row, tags


def index_row(i_f0, i_c, feasible):
    if any(i_f0[p] < FLOOR_I for p in PANELS):
        return "NOT EVALUABLE", None
    ok = {c: all(restored(i_c[c][p], i_f0[p]) == "RESTORED" for p in PANELS) for c in feasible}
    cstar = None
    for k, c in enumerate(feasible):
        if all(ok[x] for x in feasible[k:]):
            cstar = c
            break
    if cstar is None:
        return "INDEX DOES NOT APPROACH FLAT", None
    return ("SPARSE INDEX APPROACHES FLAT" if cstar <= TREE_CAND else "INDEX APPROACHES FLAT ONLY ABOVE 512"), cstar


def cell_rule(rows):
    assert len(rows) == 5
    if sum(r == "NOT EVALUABLE" for r in rows) >= 2:
        return "NOT EVALUABLE"
    for r in set(rows):
        if r not in ("NOT EVALUABLE", "MIXED-PANEL") and rows.count(r) >= 4:
            return r
    return "MIXED"


def i_star(series, limit):
    vals = [v for u, v in series.items() if u <= limit]
    return max(vals) if vals else None


def plateau_ok(per_panel, run):
    for p in PANELS:
        top, half = i_star(per_panel[p], run), i_star(per_panel[p], run // 2)
        if top is None or half is None or not (top - half <= PLATEAU + 1e-12 and half >= FLOOR_I - 1e-12):
            return False
    return True


def s1_label(arm, cell, d):
    c = CELLS[cell]
    lab = f"P_{arm}_f{c['f']}_n{c['n']}_d{d}_i{2100 + d}"
    cands = [x for x in os.listdir(f"{S1}/cells") if (x == lab or x.startswith(lab + "_")) and "_lr" not in x]
    assert len(cands) == 1, (lab, cands)
    return cands[0]


def s1_series(label):
    out = {p: {} for p in PANELS}
    root = f"{S1}/cells/{label}/eval"
    for u in sorted(os.listdir(root)):
        e = json.load(open(f"{root}/{u}/eval.json"))
        for p in PANELS:
            pc = e["reads"]["main"]["panels"][p]
            out[p][int(u[1:])] = bits(int(pc["useful"]), int(pc["n"]))
    return out


def main():
    items = load_items()
    log, diffs, ncmp = [], [], [0]

    def cmp(what, mine, theirs, tol=0.0):
        ncmp[0] += 1
        if isinstance(mine, float) or isinstance(theirs, float):
            same = mine is not None and theirs is not None and abs(float(mine) - float(theirs)) <= tol
        else:
            same = mine == theirs
        if not same:
            diffs.append(f"{what}: mine={mine!r} theirs={theirs!r}")

    n_reads, max_i_err = 0, 0.0
    for key, rec in items.items():
        for name, r in rec["reads"].items():
            for p in PANELS:
                pc = r["panels"][p]
                mine = bits(int(pc["useful"]), int(pc["n"]))
                err = abs(mine - float(pc["i"]))
                max_i_err = max(max_i_err, err)
                ncmp[0] += 2
                if err > 1e-12:
                    diffs.append(f"i of {key} {name} {p}: mine {mine} recorded {pc['i']}")
                if int(pc["useful"]) / int(pc["n"]) != float(pc["a_use"]):
                    diffs.append(f"a_use of {key} {name} {p}")
                n_reads += 1
    log.append(f"per-read i recomputed from counts: {n_reads} read-panels, max |i_mine - i_rec| = {max_i_err:.3e}; floor i = {FLOOR_I:.6f}")
    fails = {k: gate_failures(v["item"]) for k, v in items.items()}
    log.append(f"items: {len(items)}; items with a non-passed gate: {sum(1 for v in fails.values() if v)}")

    ana = json.load(open(f"{RUN}/analysis/analysis.json"))["A1"]
    mine_labels = {}
    for cell, c in CELLS.items():
        cps = {"U_P": c["up"], "RUN": c["run"], "TRAJ1": c["traj"][0], "TRAJ2": c["traj"][1]}
        feasible = [b for b in BUDGETS if b < c["n"]]
        for cp, u in cps.items():
            trows, irows, cstars = [], [], []
            for d in range(1, 6):
                t, f = items.get((cell, "T-OQ", d, u)), items.get((cell, "F-OQ", d, u))
                theirs_t = ana["cells"][cell]["checkpoints"][cp]["tree"]["replicates"][d - 1]
                theirs_i = ana["cells"][cell]["checkpoints"][cp]["index"]["replicates"][d - 1]
                t_bad = t is None or bool(fails[(cell, "T-OQ", d, u)])
                f0_bad = f is None or any(g.get("scope") == "f0" for g in fails[(cell, "F-OQ", d, u)].values())
                idx_bad = f is None or any(g.get("scope") == "index" for g in fails[(cell, "F-OQ", d, u)].values())
                if t_bad or f0_bad:
                    row, tags = "NOT EVALUABLE", {}
                else:
                    i = {r: {p: float(t["reads"][r]["panels"][p]["i"]) for p in PANELS} for r in ("T0", "T1", "T1w", "T2", "T3")}
                    i["F0"] = {p: float(f["reads"]["F0"]["panels"][p]["i"]) for p in PANELS}
                    row, tags = tree_row(i, float(t["reads"]["T0"]["facts"]["cr8"]))
                trows.append(row)
                cmp(f"tree row {cell} {cp} d{d}", row, theirs_t["row"])
                for k in ("P", "C", "J", "H", "R"):
                    if k in tags:
                        cmp(f"tree tag {k} {cell} {cp} d{d}", tags[k], theirs_t["tags"].get(k))
                for k in ("g_P", "g_C", "g_PC"):
                    if k in tags:
                        for p in PANELS:
                            cmp(f"tree {k} {cell} {cp} d{d} {p}", tags[k][p], theirs_t["tags"][k][p], 1e-12)
                if idx_bad or f0_bad:
                    irow, cs = "NOT EVALUABLE", None
                else:
                    i_f0 = {p: float(f["reads"]["F0"]["panels"][p]["i"]) for p in PANELS}
                    i_c = {b: {p: sum(float(f["reads"][f"I64@{b}/s{s}"]["panels"][p]["i"]) for s in I64_SEEDS) / 3 for p in PANELS} for b in feasible}
                    irow, cs = index_row(i_f0, i_c, feasible)
                irows.append(irow)
                cstars.append(cs)
                cmp(f"index row {cell} {cp} d{d}", irow, theirs_i["row"])
                cmp(f"c* {cell} {cp} d{d}", cs, theirs_i["tags"].get("c_star"))
            tl, il = cell_rule(trows), cell_rule(irows)
            got = [x for x in cstars if x is not None]
            med = float(statistics.median(got)) if got else None
            cmp(f"cell tree label {cell} {cp}", tl, ana["cells"][cell]["checkpoints"][cp]["tree"]["label"])
            cmp(f"cell index label {cell} {cp}", il, ana["cells"][cell]["checkpoints"][cp]["index"]["label"])
            cmp(f"median c* {cell} {cp}", med, ana["cells"][cell]["checkpoints"][cp]["index"]["c_star_median"], 0.0)
            mine_labels[(cell, cp)] = (tl, il)
            log.append(f"{cell:8s} {cp:5s} u={u:7d} tree={tl:22s} {trows}  index={il:38s} c*={cstars} median={med}")

    for cell in ("8K/4K", "32K/16K"):
        c = CELLS[cell]
        tags = []
        for arm, tag in (("T-OQ", "TREE STILL LEARNING"), ("F-OQ", "FLAT STILL LEARNING")):
            fails_n, detail = 0, []
            for d in range(1, 6):
                lab = s1_label(arm, cell, d)
                s = s1_series(lab)
                ok = plateau_ok(s, c["run"])
                fails_n += not ok
                detail.append({p: (round(i_star(s[p], c["run"]), 4), round(i_star(s[p], c["run"] // 2), 4)) for p in PANELS} | {"snaps": len(s["A"])})
            if fails_n >= 2:
                tags.append(tag)
            log.append(f"plateau {cell} {arm}: failing replicates {fails_n}/5; (i*(run), i*(run/2)) per panel: {detail}")
        cmp(f"plateau tags {cell}", tags, ana["cells"][cell]["checkpoints"]["RUN"]["plateau"]["tags"])
        log.append(f"plateau tags {cell} RUN: {tags}")

    prim = ["8K/4K", "32K/16K"]
    comp, ne = {}, []
    for k, name in ((0, "tree"), (1, "index")):
        at = {}
        for cp in ("U_P", "RUN"):
            vals = {cell: mine_labels[(cell, cp)][k] for cell in prim}
            ne += [(name, cell, cp) for cell, v in vals.items() if v == "NOT EVALUABLE"]
            at[cp] = vals[prim[0]] if len(set(vals.values())) == 1 else ("CELL-DEPENDENT", tuple(sorted(vals.items())))
        comp[name] = at["U_P"] if at["U_P"] == at["RUN"] else ("CHECKPOINT-DEPENDENT", at["U_P"], at["RUN"])
    evaluable = not ne
    rd = ana["r_diagnosis"]
    cmp("R-DIAGNOSIS evaluable", evaluable, rd["evaluable"])
    cmp("tree component", comp["tree"], rd["components"]["tree"]["value"])
    cmp("index component", comp["index"], rd["components"]["index"]["value"])
    actions_tree = {"PRIORS AND CANDIDATES, SEPARATELY", "PRIORS", "CANDIDATES", "CONTENT"}
    rec_tree = comp["tree"] if isinstance(comp["tree"], str) and comp["tree"] in actions_tree else None
    rec_index = comp["index"] if comp["index"] == "SPARSE INDEX APPROACHES FLAT" else None
    cmp("tree action is none", rec_tree is None, rd["recommended"]["tree"] is None)
    cmp("index action is none", rec_index is None, rd["recommended"]["index"] is None)
    nrtc = comp["tree"] in ("EXACT SEARCH HARMS", "NOT IDENTIFIED") and comp["index"] == "INDEX DOES NOT APPROACH FLAT"
    cmp("NO READ-TIME CAUSE banner", nrtc, rd["no_read_time_cause_identified"])
    log.append(f"R-DIAGNOSIS evaluable={evaluable}; tree={comp['tree']}; index={comp['index']}; actions tree={rec_tree} index={rec_index}; NO READ-TIME CAUSE={nrtc}")
    for cell in ("8K/1K", "32K/4K"):
        for cp in ("U_P", "RUN"):
            tl, il = mine_labels[(cell, cp)]
            cmp(f"loaded tree {cell} {cp}", tl, ana["r_diagnosis_loaded"]["cells"][cell][cp]["tree"])
            cmp(f"loaded index {cell} {cp}", il, ana["r_diagnosis_loaded"]["cells"][cell][cp]["index"])
            log.append(f"LOADED {cell} {cp}: tree {tl}, index {il}")

    def rd_(cell, arm, d, u, read):
        return items[(cell, arm, d, u)]["reads"][read]

    def mean_ause(cell, u, arm, read):
        return sum(sum(rd_(cell, arm, d, u, read)["panels"][p]["useful"] / rd_(cell, arm, d, u, read)["panels"][p]["n"] for p in PANELS) / 2 for d in range(1, 6)) / 5

    def mean_i(cell, u, arm, read):
        return sum(sum(float(rd_(cell, arm, d, u, read)["panels"][p]["i"]) for p in PANELS) / 2 for d in range(1, 6)) / 5

    def mean_fact(cell, u, arm, read, k):
        return sum(float(rd_(cell, arm, d, u, read)["facts"][k]) for d in range(1, 6)) / 5

    for cell, u, tag in (("32K/16K", 98304, "RUN"), ("32K/16K", 16384, "U_P"), ("8K/4K", 49152, "RUN"), ("8K/4K", 8192, "U_P")):
        desc = {r: round(mean_ause(cell, u, "T-OQ", r), 3) for r in ("T0", "T1", "T1w", "T3", "T2")}
        desc["F0"] = round(mean_ause(cell, u, "F-OQ", "F0"), 3)
        desc["I256@512"] = round(mean_ause(cell, u, "F-OQ", "I256@512"), 3)
        log.append(f"{cell} {tag} mean a_use: {desc}; T0 CR8 {mean_fact(cell, u, 'T-OQ', 'T0', 'cr8'):.4f} CR1 {mean_fact(cell, u, 'T-OQ', 'T0', 'cr1'):.4f} AM_C {mean_fact(cell, u, 'T-OQ', 'T0', 'am_c'):.4f}; T1 SR8 {mean_fact(cell, u, 'T-OQ', 'T1', 'sr8'):.4f}; T3 SR8 {mean_fact(cell, u, 'T-OQ', 'T3', 'sr8'):.4f}; T2 SR8 {mean_fact(cell, u, 'T-OQ', 'T2', 'sr8'):.4f}")
        vs = [v for v in (1, 2, 4, 8) if v <= CELLS[cell]["n"] // 256]
        name_on = {1: "Tv1_on", 2: "T0", 4: "Tv4_on", 8: "Tv8_on"}
        name_off = {1: "Tv1_off", 2: "T1", 4: "Tv4_off", 8: "Tv8_off"}
        if CELLS[cell]["n"] // 256 == 16:
            name_on[16], name_off[16] = "T3", "T2"
        log.append(f"   sweep i(on) { {v: round(mean_i(cell, u, 'T-OQ', name_on[v]), 3) for v in vs} } i(off) { {v: round(mean_i(cell, u, 'T-OQ', name_off[v]), 3) for v in vs} } CR8(on) { {v: round(mean_fact(cell, u, 'T-OQ', name_on[v], 'cr8'), 4) for v in vs} } a_use(on) { {v: round(mean_ause(cell, u, 'T-OQ', name_on[v]), 3) for v in vs} }")
        idx = {}
        for b in [x for x in BUDGETS if x < CELLS[cell]["n"]]:
            recs = [rd_(cell, "F-OQ", d, u, f"I64@{b}/s{s}") for d in range(1, 6) for s in I64_SEEDS]
            a = sum(sum(r["panels"][p]["useful"] / r["panels"][p]["n"] for p in PANELS) / 2 for r in recs) / 15
            idx[b] = tuple(round(x, 3) for x in (a, sum(float(r["facts"]["cr8"]) for r in recs) / 15, sum(float(r["facts"]["am_c"]) for r in recs) / 15, sum(float(r["facts"]["cr1"]) for r in recs) / 15))
        log.append(f"   index (a_use, CR8, AM_C, CR1) per budget: {idx}")

    log.append(f"COMPARISONS {ncmp[0]}; DIFFERENCES {len(diffs)}")
    log += ["DIFF " + x for x in diffs[:200]]
    text = "\n".join(log)
    print(text)
    open(f"{OUT}/audit_labels.out.txt", "w").write(text + "\n")


if __name__ == "__main__":
    sys.exit(main())
