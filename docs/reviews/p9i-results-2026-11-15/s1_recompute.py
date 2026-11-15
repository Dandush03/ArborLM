"""S1 (auditor, Opus 5.5): independent recomputation of every rule input, class, annotation and the
selection outcome of P9-I attempt 2 from the per-cell records, plus record integrity checks.

Imports nothing from studies.* or arborlm.*. Written from ADR-0017 sections I.5, I.7, I.8, 8.1 and 15.3-15.8.

Inputs: the run directory's cells/*/train.json, cells/*/eval/u0008192/eval.json, cells/*/updates.jsonl,
cells/*/snapshots/u0008192/*.pt (hashed only), gates.json, calibration_binding.json, stage manifests;
the committed copies in results/p9i-run-attempt2-2026-11-15/ (analysis.json, classes.csv, cells.csv, eval/,
ledger.json); the attempt-1 run directory's data_manifest.json.

Usage: s1_recompute.py RUN_DIR ATTEMPT1_RUN_DIR COMMITTED_DIR
"""
import csv
import hashlib
import json
import math
import sys
from pathlib import Path

RUN, A1, COM = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
U = 8192
SIZES = {4096: 2048, 16384: 8192, 65536: 32768}
B101, B102 = (101, 301), (102, 302)
SEEDS = (1801, 1802)
PANELS = ("A", "B")
problems: list[str] = []


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def note(msg: str) -> None:
    problems.append(msg)
    print("DIFFERENCE:", msg)


# ---------- exact binomial central interval (level 1 - 0.001/8), own implementation ----------
def log_pmf(n: int, k: int, p: float) -> float:
    return math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1) + k * math.log(p) + (n - k) * math.log1p(-p)


def interval(n: int, alpha: float = 0.001 / 8, p: float = 1 / 32) -> tuple[int, int]:
    pmf = [math.exp(log_pmf(n, k, p)) for k in range(n + 1)]
    # lo: smallest k with P(X < k) <= alpha/2 < P(X <= k); hi: largest k with P(X > k) <= alpha/2 < P(X >= k)
    cum, lo = 0.0, 0
    for k in range(n + 1):
        if cum + pmf[k] > alpha / 2:
            lo = k
            break
        cum += pmf[k]
    cum, hi = 0.0, n
    for k in range(n, -1, -1):
        if cum + pmf[k] > alpha / 2:
            hi = k
            break
        cum += pmf[k]
    return lo, hi


CI = {n: interval(n) for n in (2048, 8192, 32768)}
print("G2 intervals (own exact binomial, alpha = 0.001/8 two-sided):", CI)


def inside(c: int, n: int) -> bool:
    lo, hi = CI[n]
    return lo <= c <= hi


def above(c: int, n: int) -> bool:
    return c > CI[n][1]


# ---------- load records ----------
cells = {}
for d in sorted((RUN / "cells").iterdir()):
    tr = json.loads((d / "train.json").read_text())
    ev = json.loads((d / "eval" / f"u{U:07d}" / "eval.json").read_text())
    cells[d.name] = (tr, ev, d)
print("cells in run directory:", len(cells))

# expected matrix (section I.7)
exp = set()
for arm in ("N", "W7", "E7", "A4", "A4E", "R1", "R2", "D", "D7"):
    for s in SEEDS:
        exp.add((arm, 16384, B101, s))
for arm in ("W7", "A4", "R1", "D7"):
    exp.add((arm, 16384, B102, 1801))
for arm in ("N", "W7", "A4", "R1", "D7"):
    for s in SEEDS:
        exp.add((arm, 65536, B101, s))
for arm in ("N", "W7", "A4", "R1"):
    for s in SEEDS:
        exp.add((arm, 4096, B101, s))
for arm in ("BB", "BB-D", "BB-0"):
    for n in (16384, 65536):
        for s in SEEDS:
            exp.add((arm, n, B101, s))
exp.add(("BB", 16384, B102, 1801))
for arm in ("BB", "BB-0"):
    for s in SEEDS:
        exp.add((arm, 4096, B101, s))
print("expected cells (section I.7):", len(exp))


def key_of(label: str) -> tuple:
    tr = cells[label][0]
    return (tr["arm"], tr["slots"], tuple(tr["parent"]), tr["seed"])


have = {key_of(lb) for lb in cells}
if have != exp:
    note(f"matrix mismatch: missing {sorted(exp - have)}, extra {sorted(have - exp)}")
else:
    print("matrix: the 57 registered cells, no more, no fewer")

# ---------- integrity per cell ----------
idents = set()
for label, (tr, ev, d) in cells.items():
    idents.add(json.dumps(tr["identity"], sort_keys=True))
    idents.add(json.dumps(ev["identity"], sort_keys=True))
    checks = {
        "status completed": tr["status"] == "completed",
        "mode registered": tr["mode"] == "registered",
        "seed_set p9i-registered": tr["seed_set"] == "p9i-registered",
        "init_seed == seed in {1801,1802}": tr["init_seed"] == tr["seed"] and tr["seed"] in SEEDS,
        "matched_updates == run_updates == 8192": tr["matched_updates"] == U and tr["run_updates"] == U,
        "examples == 16 * 8192": tr["examples"] == 16 * U,
        "facts by size": tr["facts"] == SIZES[tr["slots"]] and ev["facts"] == SIZES[tr["slots"]],
        "exposure per fact constant": tr["exposure_per_fact_min"] == tr["exposure_per_fact_max"] == 128 * U // SIZES[tr["slots"]],
        "snapshots == [8192]": tr["snapshots"] == [U],
        "calibration binding": tr["calibration_sha256"] == "087bf0b5885859a78781e32cb0e0ce8d3b154dfcc471965cf82f06718c509f44"
        and tr["calibration_selected_updates"] == U and tr["calibration_failed_sizes"] == {},
        "eval binding": ev["calibration_sha256"] == tr["calibration_sha256"] and ev["calibration_selected_updates"] == U and ev["update"] == U,
        "snapshot model.pt hash": sha(d / "snapshots" / f"u{U:07d}" / "model.pt") == tr["snapshot_sha256"][str(U)],
        "updates.jsonl 8192 lines": sum(1 for _ in (d / "updates.jsonl").open()) == U,
        "only one snapshot dir": [p.name for p in (d / "snapshots").iterdir()] == [f"u{U:07d}"],
        "only one eval dir": [p.name for p in (d / "eval").iterdir()] == [f"u{U:07d}"],
        "committed eval copy identical": sha(COM / "eval" / f"{label}.eval.json") == sha(d / "eval" / f"u{U:07d}" / "eval.json"),
    }
    bad = [k for k, v in checks.items() if not v]
    if bad:
        note(f"{label}: failed integrity checks {bad}")
print("distinct code identities across train and eval records:", len(idents))
for i in idents:
    print("   ", i)
print("integrity checks done for", len(cells), "cells")

# ---------- calibration binding, data manifest vs attempt 1 ----------
cb = json.loads((RUN / "calibration_binding.json").read_text())
print("calibration_binding.json:", cb)
calib_file = COM.parent / "p9i-calibration-2026-11-14" / "calibration.json"
print("calibration.json sha256:", sha(calib_file), "== binding:", sha(calib_file) == cb["calibration_sha256"])
m2 = json.loads((RUN / "data_manifest.json").read_text())
m1 = json.loads((A1 / "data_manifest.json").read_text())
print("data_manifest sha256 attempt 2:", sha(RUN / "data_manifest.json"), "(ADR 15.8 states e1bec1e3...)")
print("data_manifest sha256 attempt 1:", sha(A1 / "data_manifest.json"), "(ADR 15.5 states 8d73e555...)")
print("number of stream/data hashes:", len(m2["sha256s"]), "identical to attempt 1:", m2["sha256s"] == m1["sha256s"])
for k in sorted(m2):
    if k != "identity" and m2[k] != m1[k]:
        note(f"data manifest field {k} differs from attempt 1")
print("non-identity manifest fields identical to attempt 1:", all(m2[k] == m1[k] for k in m2 if k != "identity"))
print("g1.json identical to attempt 1:", sha(RUN / "g1.json") == sha(A1 / "g1.json"))
print("data seeds:", json.dumps(m2["seeds"])[:400])

# ---------- gates ----------
g = json.loads((RUN / "gates.json").read_text())
nm = g["controls"]["no_memory"]
g2ok = True
for panel in PANELS:
    for n in ("2048", "8192", "32768", "unseen"):
        c = nm[panel][n]["correct"]
        nn = nm[panel][n]["facts"]
        ok = inside(c, nn)
        g2ok &= ok
        print(f"G2 {panel}/{n}: {c}/{nn} inside {CI[nn]}: {ok}")
print("G2 recomputed:", g2ok, "| record:", g["g2_passed"], "| G1:", g["g1_passed"], "| G4:", g["g4_passed"], g["g4_defects"])
rep = g["controls"].get("no_memory_replicate")
if rep:
    for panel in PANELS:
        for n in ("2048", "8192", "32768", "unseen"):
            c, nn = rep[panel][n]["correct"], rep[panel][n]["facts"]
            print(f"   (B102 no-memory, reported, not a G2 test) {panel}/{n}: {c}/{nn} inside: {inside(c, nn)}")

# ---------- per-cell accuracies, LEAKAGE ----------
acc: dict = {}
print()
print(f"{'cell':30s} {'A corr':>6} {'A acc':>7} {'B corr':>6} {'B acc':>7} unseenA unseenB leakage(own)")
for label, (tr, ev, d) in cells.items():
    k = key_of(label)
    row = {}
    for p in PANELS:
        r = ev["panels"][p]
        n = r["facts"]
        if r["correct"] / n != r["accuracy"]:
            note(f"{label} {p}: accuracy {r['accuracy']} != correct/facts")
        if list(CI[n]) != list(r["chance_interval"]):
            note(f"{label} {p}: chance interval {r['chance_interval']} != own {CI[n]}")
        leak = not inside(r["unseen_correct"], r["unseen_facts"])
        if leak != r["leakage"]:
            note(f"{label} {p}: leakage flag {r['leakage']} != own {leak}")
        row[p] = r
    acc[k] = row
    print(f"{label:30s} {row['A']['correct']:6d} {row['A']['accuracy']:7.4f} {row['B']['correct']:6d} {row['B']['accuracy']:7.4f} "
          f"{row['A']['unseen_correct']:7d} {row['B']['unseen_correct']:7d} {not inside(row['A']['unseen_correct'], 2048) or not inside(row['B']['unseen_correct'], 2048)}")


# ---------- classes (section I.8.1) ----------
def raw_class(arm, n, parent, seed, panel):
    r1 = acc[("R1", n, parent, seed)][panel]["accuracy"]
    r = acc[(arm, n, parent, seed)][panel]
    a, c, f = r["accuracy"], r["correct"], r["facts"]
    eta = a / r1
    perm = r.get("permuted_correct")
    dis = r.get("disabled_correct")
    mem_chance = (perm is None or inside(perm, f)) and dis is not None and inside(dis, f)
    if a >= 0.5 and eta >= 0.90 and mem_chance:
        return "WORKS", eta
    if above(c, f) and a >= 0.25:
        return "PARTIAL", eta
    return "FAILS", eta


ours: dict = {}
etas = {}
print()
for arm in ("N", "W7", "E7", "A4", "A4E", "BB"):
    for n in SIZES:
        if (arm, n, B101, 1801) not in acc:
            continue
        r1_low = any(acc[("R1", n, B101, s)][p]["accuracy"] < 0.5 for s in SEEDS for p in PANELS)
        raws = {}
        for s in SEEDS:
            for p in PANELS:
                rc, eta = raw_class(arm, n, B101, s, p)
                etas[(arm, n, s, p)] = eta
                raws[f"{s}/{p}"] = "NOT_EVALUATED" if r1_low else rc
        if r1_low:
            cls = "NOT_EVALUATED"
        elif any(raws[f"{s}/A"] != raws[f"{s}/B"] for s in SEEDS):
            cls = "NOT REPLICATED"
        elif raws["1801/A"] != raws["1802/A"]:
            cls = "INTERMEDIATE"
        else:
            cls = "INTERFACE_" + raws["1801/A"]
        b102 = (arm, n, B102, 1801) in acc
        demoted = False
        b102_raw = None
        if b102:
            b102_raw = {p: raw_class(arm, n, B102, 1801, p)[0] for p in PANELS}
            if cls == "INTERFACE_WORKS" and any(v == "FAILS" for v in b102_raw.values()):
                cls, demoted = "INTERMEDIATE", True
        stores = None
        if arm == "BB":
            bb0 = [acc[("BB-0", n, B101, s)][p] for s in SEEDS for p in PANELS]
            stores = any(above(r["correct"], r["facts"]) for r in bb0)
            if cls == "INTERFACE_WORKS" and stores:
                cls = "MODEL_STORES_FACTS"
        ours[(arm, n)] = cls
        print(f"{arm:4s} {n:6d} raw {raws} B102 raw {b102_raw} demoted {demoted} BB-0 above G2 {stores} -> {cls}")
        print("      eta:", {f"{s}/{p}": round(etas[(arm, n, s, p)], 5) for s in SEEDS for p in PANELS})

# compare with classes.csv
with (COM / "classes.csv").open() as f:
    for row in csv.DictReader(f):
        k = (row["arm"], int(row["slots"]))
        if ours.get(k) != row["class"]:
            note(f"class {k}: record {row['class']} own {ours.get(k)}")
print("classes compared with classes.csv:", len(ours), "arm-size pairs")

# ---------- annotations ----------
print()
for arm, dense in (("W7", "D7"), ("BB", "BB-D")):
    for n in SIZES:
        if (arm, n, B101, 1801) not in acc or (dense, n, B101, 1801) not in acc:
            print(f"dense comparison {arm}/{dense} at {n}: no dense cell -> no annotation")
            continue
        cls = ours[(arm, n)]
        ratios = [acc[(arm, n, B101, s)][p]["accuracy"] / acc[(dense, n, B101, s)][p]["accuracy"] for s in SEEDS for p in PANELS]
        label = ("BEATS DENSE" if min(ratios) >= 1.10 else "DENSE SUFFICES") if cls in ("INTERFACE_WORKS", "INTERFACE_PARTIAL") else "NOT COMPARED"
        print(f"dense comparison {arm}/{dense} at {n}: class {cls} -> {label}; ratios (descriptive) {[round(x, 4) for x in ratios]}")
for emb, st in (("E7", "W7"), ("A4E", "A4")):
    n = 16384
    ratios = [acc[(emb, n, B101, s)][p]["accuracy"] / acc[(st, n, B101, s)][p]["accuracy"] for s in SEEDS for p in PANELS]
    both_fail = ours[(emb, n)] == "INTERFACE_FAILS" and ours[(st, n)] == "INTERFACE_FAILS"
    if both_fail:
        lab = "not printed (both INTERFACE_FAILS)"
    elif all(r >= 1.03 for r in ratios):
        lab = "BACKBONE HURTS ADDRESSING"
    elif all(r >= 0.97 for r in ratios):
        lab = "BACKBONE ADDS NOTHING"
    elif all(r < 0.97 for r in ratios):
        lab = "BACKBONE CONTRIBUTES"
    else:
        lab = "BACKBONE CONTRAST MIXED"
    print(f"backbone contrast {emb}/{st}: {lab}; ratios (descriptive) {[round(x, 4) for x in ratios]}")
for arm in ("BB", "BB-D", "BB-0"):
    for n in SIZES:
        rises = {}
        for s in SEEDS:
            k = (arm, n, B101, s)
            if k in acc:
                lm = cells[[lb for lb in cells if key_of(lb) == k][0]][1]["language_modelling"]
                own = (lm["after_nats"] - lm["before_nats"]) / lm["before_nats"]
                if abs(own - lm["relative_rise"]) > 1e-12:
                    note(f"LM rise {k}: record {lm['relative_rise']} own {own}")
                rises[s] = (round(lm["before_nats"], 4), round(lm["after_nats"], 4), round(own, 4))
        if rises:
            deg = any(v[2] > 0.05 for v in rises.values())
            print(f"LM {arm:4s} {n:6d}: (before, after, rise) {rises} -> {'LANGUAGE MODELLING DEGRADED' if deg else 'not degraded'}")
for k in sorted(acc):
    if k[0] == "BB" and k[2] == B102:
        lm = cells[[lb for lb in cells if key_of(lb) == k][0]][1]["language_modelling"]
        print(f"LM BB B102 replicate (reported only): {lm}")

# ---------- selection (section I.8.3) ----------
size_bad = [n for n in SIZES if any(acc[("R1", n, B101, s)][p]["accuracy"] < 0.5 for s in SEEDS for p in PANELS)]
if size_bad:
    outcome = f"INCONCLUSIVE AT {size_bad}"
elif all(ours[("BB", n)] == "INTERFACE_WORKS" for n in SIZES):
    outcome = "BB"
elif all(ours[("A4", n)] == "INTERFACE_WORKS" for n in SIZES):
    outcome = "A4"
elif all(ours[("W7", n)] == "INTERFACE_WORKS" for n in SIZES):
    outcome = "W7"
else:
    outcome = "NO_INTERFACE_SELECTED (step 4)"
an = json.loads((COM / "analysis.json").read_text())
print()
print("selection (own):", outcome)
print("selection (record):", json.dumps(an["analysis"].get("selection", an["analysis"].get("outcome")))[:300])

# ---------- ledger ----------
led = json.loads((COM / "ledger.json").read_text())
tot = sum(e["seconds"] for e in led["entries"])
a2 = [e for e in led["entries"] if e["run"] == RUN.name]
print()
print(f"ledger: {len(led['entries'])} entries, total charged {tot:.1f} s of cap {led['cap_seconds']:.0f} s; attempt-2 entries {[(e['stage'], round(e['seconds'], 1)) for e in a2]}")
print("attempt-2 stages charged once each:", sorted(e["stage"] for e in a2) == sorted(["generate", "gates", "train", "evaluate", "analyze", "report"]))
for st in ("gates", "train", "evaluate", "analyze", "report"):
    m = json.loads((RUN / st / "manifest.json").read_text())
    print(f"manifest {st}: status {m['status']} tasks {len(m['tasks'])} started {m['started_utc']} finished {m['finished_utc']} cap {m['caps']['stage_seconds']} workers {m['workers']} mode {m['mode']}")
print()
print("TOTAL DIFFERENCES:", len(problems))
for p in problems:
    print("  -", p)
