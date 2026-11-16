"""P9-II results audit, part C1: descriptive explanations and threat checks from the records (no model is run).

Usage:
    python3 -I docs/reviews/p9ii-results-2026-11-15/c1_explain.py <raw-run-dir> <b1-output-json>

Everything printed here is descriptive and enters no registered rule.
"""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

RAW, B1 = Path(sys.argv[1]), Path(sys.argv[2])
b1 = json.loads(B1.read_text())
U = 8192


def say(*a: object) -> None:
    print(*a, flush=True)


def load(p: Path):
    return json.loads(p.read_text())


def ev(label: str, update: int) -> dict:
    return load(RAW / "cells" / label / "eval" / f"u{update:07d}" / "eval.json")


def diag(label: str) -> list[dict]:
    return [json.loads(x) for x in (RAW / "cells" / label / "diagnostics.jsonl").open()]


def labels(stage: int, arm: str) -> list[str]:
    n = {1: 4096, 2: 16384, 3: 65536}[stage]
    return sorted(p.name for p in (RAW / "cells").glob(f"S{stage}-{arm}-n{n}-d*") if p.name.split(f"-n{n}-")[0] == f"S{stage}-{arm}")


# ------------------------------------------------------------------ 1. A5-C at 4,096
say("== 1. A5-C at 4,096: per cell (Panel A, B, H1, H2, H1/A, H2/A, success)")
for lab in labels(1, "A5-C"):
    e = ev(lab, U)
    a, b = e["panels"]["A"]["accuracy"], e["panels"]["B"]["accuracy"]
    h1, h2 = e["secondary"]["H1"]["accuracy"], e["secondary"]["H2"]["accuracy"]
    k = lab.split("-d")[1]
    ok = b1["stage1"]["A5-C"]["cells"][f"{int(k[:2])}/{k[-1]}"]["success"]
    say(f"{lab}: A {a:.4f} B {b:.4f} H1 {h1:.4f} H2 {h2:.4f} H1/A {h1 / a:.3f} H2/A {h2 / a:.3f} line {0.9 * a:.4f} "
        f"probe distinct {e['probe']['distinct_top1']} largest {e['probe']['largest_top1_share']:.4f} "
        f"fact-indep share (uncentred) {e['probe']['fact_independent_share']:.3f} -> {'SUCCESS' if ok else 'FAIL'}")
say("H1/A and H2/A for the other arms at 4,096 (min over cells):")
for arm in ("A0", "A1", "A5-D"):
    rows = []
    for lab in labels(1, arm):
        e = ev(lab, U)
        a = e["panels"]["A"]["accuracy"]
        if a > 0.5:
            rows.append((e["secondary"]["H1"]["accuracy"] / a, e["secondary"]["H2"]["accuracy"] / a))
    if rows:
        say(f"  {arm}: cells with A > 0.5: {len(rows)}; min H1/A {min(r[0] for r in rows):.3f}; min H2/A {min(r[1] for r in rows):.3f}; "
            f"median H1/A {statistics.median(r[0] for r in rows):.3f}; median H2/A {statistics.median(r[1] for r in rows):.3f}")
for arm, st, ro in (("A6", 1, U), ("A7", 1, U), ("A6", 2, 4 * U), ("A7", 2, 4 * U), ("A6", 3, U), ("A7", 3, U)):
    rs = []
    for lab in labels(st, arm):
        e = ev(lab, ro)
        a = e["panels"]["A"]["accuracy"]
        rs.append((round(a, 4), round(e["panels"]["B"]["accuracy"], 4), round(e["secondary"]["H1"]["accuracy"], 4),
                   round(e["secondary"]["H2"]["accuracy"], 4)))
    say(f"  {arm} stage {st} at {ro}: (A, B, H1, H2) {rs}")

# ------------------------------------------------------------------ 2. A1 at 16,384
say("\n== 2. A1 at 16,384 (4U and U): conditions per cell")
for lab in labels(2, "A1"):
    for ro in (4 * U, U):
        e = ev(lab, ro)
        a = e["panels"]["A"]["accuracy"]
        h1, h2 = e["secondary"]["H1"]["accuracy"], e["secondary"]["H2"]["accuracy"]
        n = e["secondary"]["H1"]["facts"]
        say(f"{lab} @{ro}: A {a:.5f} B {e['panels']['B']['accuracy']:.5f} H1 {h1:.5f} ({e['secondary']['H1']['correct']}/{n}) "
            f"H2 {h2:.5f} ({e['secondary']['H2']['correct']}/{n}) line 0.9*A {0.9 * a:.5f} -> H1 margin {h1 - 0.9 * a:+.5f} "
            f"({(h1 - 0.9 * a) * n:+.2f} facts), H2 margin {h2 - 0.9 * a:+.5f} ({(h2 - 0.9 * a) * n:+.2f} facts)")

# ------------------------------------------------------------------ 3. A0 at 16,384, U vs 4U; trajectories
say("\n== 3. A0 and A5-D at 16,384: readouts at U and 4U; trajectory from the 64-update probe records")
for arm in ("A0", "A5-D", "A1"):
    for lab in labels(2, arm):
        eu, e4 = ev(lab, U), ev(lab, 4 * U)
        a6 = ev(lab.replace(f"-{arm}-", "-A6-")[:-1] + "0", 4 * U)["panels"]["A"]["accuracy"]
        d = diag(lab)
        onset = next((r["update"] for r in d if r["distinct_top1"] <= 32), None)
        first_succ = next((r["update"] for r in d if r["probe_accuracy"] >= 0.90 * a6), None)
        first_half = next((r["update"] for r in d if r["probe_accuracy"] >= 0.5), None)
        at_u = next(r for r in d if r["update"] == U)
        tr = b1["annotations"][f"2/{arm}"]["trajectories"]
        k = lab.split("-d")[1]
        esc = tr[f"{int(k[:2])}/{k[-1]}"]["escape"]
        say(f"{lab}: U A {eu['panels']['A']['accuracy']:.4f} B {eu['panels']['B']['accuracy']:.4f} probe distinct "
            f"{eu['probe']['distinct_top1']} largest {eu['probe']['largest_top1_share']:.3f} | 4U A {e4['panels']['A']['accuracy']:.4f} "
            f"B {e4['panels']['B']['accuracy']:.4f} | onset {onset} escape {esc} first probe acc>=0.5 {first_half} "
            f"time-to-first-success {first_succ} | diag@U distinct {at_u['distinct_top1']} (eval {eu['probe']['distinct_top1']})")

# ------------------------------------------------------------------ 4. probe consistency: last diagnostics record vs eval probe
say("\n== 4. last diagnostics record vs the readout's probe (same model, same probe set)")
mism = []
n = 0
for d in sorted((RAW / "cells").iterdir()):
    if not (d / "diagnostics.jsonl").exists():
        continue
    recs = {r["update"]: r for r in diag(d.name)}
    for e_dir in (d / "eval").iterdir():
        ro = int(e_dir.name[1:])
        e = load(e_dir / "eval.json")
        if ro in recs and "distinct_top1" in e["probe"]:
            n += 1
            r = recs[ro]
            if (r["distinct_top1"], round(r["largest_top1_share"], 9)) != (e["probe"]["distinct_top1"], round(e["probe"]["largest_top1_share"], 9)):
                mism.append((d.name, ro, r["distinct_top1"], e["probe"]["distinct_top1"], r["largest_top1_share"], e["probe"]["largest_top1_share"],
                             r["probe_accuracy"], e["probe"]["probe_accuracy"]))
say(f"readouts compared {n}; slot statistics differing {len(mism)}")
for m in mism[:20]:
    say("  ", m)

# ------------------------------------------------------------------ 5. leakage, unseen control, memory dependence
say("\n== 5. leakage flags, unseen-fact control, permuted/disabled accuracy")
leaks, unseen = [], []
for p in sorted(RAW.glob("cells/*/eval/*/eval.json")):
    e = load(p)
    for pn in ("A", "B"):
        P = e["panels"][pn]
        if P["leakage"]:
            leaks.append((p.parts[-4], pn))
        unseen.append(P["unseen_accuracy"])
say(f"leakage flags: {leaks}; unseen-fact accuracy range {min(unseen):.4f}..{max(unseen):.4f} over {len(unseen)} panel readouts")

# ------------------------------------------------------------------ 6. A1 vs A1-S: does the control receive an address-loss gradient of the same size
say("\n== 6. A1 vs A1-S (Stage 1): address loss, clip factor and query-projection gradient, updates 1-8192")
for arm in ("A1", "A1-S"):
    vals = {"address_loss": [], "clip_factor": [], "wq": [], "keys": []}
    for lab in labels(1, arm):
        ups = [json.loads(x) for x in (RAW / "cells" / lab / "updates.jsonl").open()]
        late = ups[1024:]
        vals["address_loss"].append(statistics.median(u["address_loss"] for u in late))
        vals["clip_factor"].append(statistics.median(u["clip_factor"] for u in late))
        vals["wq"].append(statistics.median(u["grad_norm"]["wq"] for u in late))
        vals["keys"].append(statistics.median(u["grad_norm"]["keys"] for u in late))
    say(f"  {arm}: medians over cells of the per-cell median over updates 1025-8192: "
        + ", ".join(f"{k} {statistics.median(v):.4g} (range {min(v):.4g}..{max(v):.4g})" for k, v in vals.items()))

# ------------------------------------------------------------------ 7. LM margins and success margins per arm
say("\n== 7. smallest margins of the deciding conditions among successful cells, and LM margins")
for key, ro in (("stage1", U), ("stage2", 4 * U)):
    for arm, v in b1[key].items():
        succ = [c for c in v["cells"].values() if c["success"]]
        lm = min(c["margins"]["lm"] for c in v["cells"].values())
        if succ:
            mins = {m: min(c["margins"][m] for c in succ) for m in ("c1_A", "c1_B", "c4_H1", "c4_H2")}
            say(f"  {key} {arm}: successes {len(succ)}; min margins {({k: round(x, 4) for k, x in mins.items()})}; "
                f"min probe distinct {min(c['probe_distinct'] for c in succ)}, max largest share {max(c['probe_largest_share'] for c in succ):.4f}; "
                f"min LM margin (all cells) {lm:.4f}")
        else:
            say(f"  {key} {arm}: no success; min LM margin {lm:.4f}")

# ------------------------------------------------------------------ 8. A2 after the switch; A4 schedule
say("\n== 8. A2 around the switch (U_pre = 2048) and A4 read_k schedule")
for lab in labels(1, "A2")[:4]:
    d = {r["update"]: r for r in diag(lab)}
    say(f"  {lab}: " + "; ".join(f"u{u}: distinct {d[u]['distinct_top1']} top8 recall {d[u].get('target_top8_recall')} phase {d[u]['phase']}"
                                  for u in (1984, 2048, 2112, 2560, 4096, 8192)))
lab = labels(1, "A4")[0]
ups = [json.loads(x) for x in (RAW / "cells" / lab / "updates.jsonl").open()]
say(f"  {lab}: read_k at updates 1, 2, 2048, 4095, 4096, 4097, 8192: "
    f"{[ups[i - 1]['read_k'] for i in (1, 2, 2048, 4095, 4096, 4097, 8192)]}")

# ------------------------------------------------------------------ 9. lead README claims
say("\n== 9. ranges quoted in the lead's README")


def rng(stage: int, arm: str, ro: int, f) -> str:
    xs = [f(ev(lab, ro)) for lab in labels(stage, arm)]
    return f"{min(xs):.4f}..{max(xs):.4f}"


say("A0 S2 Panel A at U:", rng(2, "A0", U, lambda e: e["panels"]["A"]["accuracy"]),
    "distinct top1 at U:", rng(2, "A0", U, lambda e: e["probe"]["distinct_top1"]),
    "Panel A at 4U:", rng(2, "A0", 4 * U, lambda e: e["panels"]["A"]["accuracy"]))
say("A5-D S2 Panel A at U:", rng(2, "A5-D", U, lambda e: e["panels"]["A"]["accuracy"]), "at 4U:", rng(2, "A5-D", 4 * U, lambda e: e["panels"]["A"]["accuracy"]))
fails = [lab for lab in labels(1, "A5-C") if not b1["stage1"]["A5-C"]["cells"][f"{int(lab.split('-d')[1][:2])}/{lab[-1]}"]["success"]]
say("A5-C failing cells Panel A:", f"{min(ev(lb, U)['panels']['A']['accuracy'] for lb in fails):.4f}..{max(ev(lb, U)['panels']['A']['accuracy'] for lb in fails):.4f}")
say("A7 S1 Panel A:", rng(1, "A7", U, lambda e: e["panels"]["A"]["accuracy"]), "A7 S2 4U Panel A:", rng(2, "A7", 4 * U, lambda e: e["panels"]["A"]["accuracy"]),
    "A7 S2 4U H1:", rng(2, "A7", 4 * U, lambda e: e["secondary"]["H1"]["accuracy"]), "H2:", rng(2, "A7", 4 * U, lambda e: e["secondary"]["H2"]["accuracy"]))
peaks = []
for st in ("train1", "train2", "train3", "evaluate1", "evaluate2", "evaluate3"):
    peaks += [(t.get("peak_rss_bytes") or 0, st, t["label"]) for t in load(RAW / st / "manifest.json")["tasks"]]
peaks.sort(reverse=True)
say("largest task peak RSS (GiB):", [(round(p / 2**30, 3), s, lab) for p, s, lab in peaks[:3]])
say("largest training-record peak RSS (GiB):", round(max(load(p)["peak_rss_bytes"] for p in RAW.glob("cells/*/train.json")) / 2**30, 3))
