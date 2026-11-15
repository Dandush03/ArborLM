"""Auditor's independent recomputation of the P8 hard-trace statistics (ADR-0015 section 7.1).

Reads the raw trace binaries written by the evaluation stage (little-endian int16 selected IDs
[32768, 8], int8 branch IDs [32768, 2]) with ``struct`` only, recomputes with plain Python:

  distinct slots, N_eff = exp(entropy of selection counts), share of the 64 most-selected slots,
  per-context breadth (mean distinct slots per 64-query context), branch statistics (all visited
  columns and top column), temporal reuse (fraction of a query's slots selected in the previous up
  to 8 queries of the same context, positions >= 1), branch persistence (same top branch / same
  visited pair as a set, consecutive in-context pairs), on the actual trace and, for reuse and
  persistence, on the order-shuffled trace (permutation from ``arborlm.p7a_core.query_order``, the
  only implementation import, used solely to obtain the registered permutation indices),

and compares with eval.json (utilization) and sim.json (temporal_reuse, branch_persistence).
Also runs the same formulas on small hand-constructed traces with hand-derived answers.

Usage: python independent_trace_stats_p8.py --eval-run E --sim-run S [--labels L ...]
Auditor tool (Claude Opus 5.5). Not Astra validation, not human approval.
"""

import argparse
import hashlib
import json
import math
import struct
import sys
from collections import Counter
from pathlib import Path

CONTEXT, WINDOW, HOT = 64, 8, 64


def read_bin(path: Path, code: str, shape: list[int]) -> list[list[int]]:
    raw = path.read_bytes()
    n = shape[0] * shape[1]
    vals = struct.unpack("<" + code * n, raw)
    w = shape[1]
    return [list(vals[i * w : (i + 1) * w]) for i in range(shape[0])]


def entropy(counts: list[int]) -> float:
    tot = sum(counts)
    return -math.fsum((c / tot) * math.log(c / tot) for c in counts if c)


def util(sel: list[list[int]]) -> dict:
    cnt = Counter(s for q in sel for s in q)
    counts = list(cnt.values())
    tot = sum(counts)
    h = entropy(counts)
    hot = sum(sorted(counts, reverse=True)[:HOT]) / tot
    breadth = [len({s for q in sel[b : b + CONTEXT] for s in q}) for b in range(0, len(sel), CONTEXT)]
    return {
        "distinct_slots": len(cnt),
        "entropy_nats": h,
        "n_eff": math.exp(h),
        "hot64_share": hot,
        "context_breadth_mean": sum(breadth) / len(breadth),
    }


def branch_util(br: list[list[int]]) -> dict:
    allc = Counter(b for q in br for b in q)
    top = Counter(q[0] for q in br)
    return {
        "distinct_visited": len(allc),
        "n_eff": math.exp(entropy(list(allc.values()))),
        "top_branch_share": max(allc.values()) / sum(allc.values()),
        "top_column_distinct": len(top),
        "top_column_n_eff": math.exp(entropy(list(top.values()))),
        "top_column_top_share": max(top.values()) / sum(top.values()),
    }


def reuse(sel: list[list[int]]) -> float:
    fr = []
    for b in range(0, len(sel), CONTEXT):
        for t in range(1, CONTEXT):
            prev = set()
            for u in range(max(0, t - WINDOW), t):
                prev |= set(sel[b + u])
            q = sel[b + t]
            fr.append(sum(1 for s in q if s in prev) / len(q))
    return math.fsum(fr) / len(fr)


def persistence(br: list[list[int]]) -> tuple[float, float]:
    top = pair = n = 0
    for b in range(0, len(br), CONTEXT):
        for t in range(1, CONTEXT):
            p, c = br[b + t - 1], br[b + t]
            n += 1
            top += p[0] == c[0]
            pair += set(p) == set(c)
    return top / n, pair / n


def hand_checks() -> list[str]:
    fails = []
    # one context of 64 queries: every query selects slots {0..7} -> reuse 1, breadth 8
    rep = [list(range(8))] * 64
    if abs(reuse(rep) - 1.0) > 1e-15 or util(rep)["context_breadth_mean"] != 8:
        fails.append("repeating trace")
    # never-repeating: query t selects 8t..8t+7 -> reuse 0, breadth 512, N_eff 512
    nr = [list(range(8 * t, 8 * t + 8)) for t in range(64)]
    u = util(nr)
    if reuse(nr) != 0 or u["context_breadth_mean"] != 512 or abs(u["n_eff"] - 512) > 1e-9:
        fails.append("never-repeating trace")
    # period-9 pattern: query t selects block (t mod 9); with window 8, block t mod 9 last seen at
    # t-9, outside the window -> reuse 0; period 8 -> seen at t-8, inside -> reuse = 56/63
    p9 = [list(range(8 * (t % 9), 8 * (t % 9) + 8)) for t in range(64)]
    p8 = [list(range(8 * (t % 8), 8 * (t % 8) + 8)) for t in range(64)]
    if reuse(p9) != 0 or abs(reuse(p8) - 56 / 63) > 1e-15:
        fails.append("window boundary")
    # persistence: top branches alternate 0,1 -> top 0; pairs {0,1},{1,0} -> pair persistence 1
    br = [[t % 2, (t + 1) % 2] for t in range(64)]
    if persistence(br) != (0.0, 1.0):
        fails.append("persistence")
    return fails


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--eval-run", type=Path, required=True)
    ap.add_argument("--sim-run", type=Path, required=True)
    ap.add_argument("--labels", nargs="*")
    args = ap.parse_args()
    from arborlm.p7a_core import STREAM_ORDER, query_order  # registered permutation indices only

    fails = hand_checks()
    print("hand-constructed checks:", "PASS" if not fails else f"FAIL {fails}")
    labels = args.labels or sorted(p.name for p in (args.eval_run / "cells").iterdir())
    order = query_order(STREAM_ORDER, 32768)
    compared, maxdiff, mism = 0, 0.0, []
    for label in labels:
        cdir = args.eval_run / "cells" / label
        ev = json.loads((cdir / "eval.json").read_text())
        sm = json.loads((args.sim_run / "cells" / label / "sim.json").read_text())
        for name in ("calibration", "A", "B"):
            tr = ev["traces"][name]
            fs = tr["files"]
            for k in ("selected", "branches"):
                if fs.get(k) and hashlib.sha256((cdir / fs[k]["file"]).read_bytes()).hexdigest() != fs[k]["sha256"]:
                    mism.append(f"{label}|{name}|{k}|file hash")
            sel = read_bin(cdir / fs["selected"]["file"], "h", fs["selected"]["shape"])
            br = read_bin(cdir / fs["branches"]["file"], "b", fs["branches"]["shape"]) if fs.get("branches") else None
            mine = util(sel)
            impl = tr["utilization"]
            pairs = [(k, mine[k], impl[k]) for k in mine]
            if br is not None:
                mb = branch_util(br)
                pairs += [(f"branches.{k}", mb[k], impl["branches"][k]) for k in mb]
            if name in ("A", "B"):
                sp = sm["panels"][name]
                pairs.append(("reuse.actual", reuse(sel), sp["temporal_reuse"]["actual"]["value"]))
                shuffled = [sel[i] for i in order]
                pairs.append(("reuse.order_shuffled", reuse(shuffled), sp["temporal_reuse"]["order_shuffled"]["value"]))
                if br is not None:
                    t, p = persistence(br)
                    ts, ps = persistence([br[i] for i in order])
                    bp = sp["branch_persistence"]
                    pairs += [
                        ("persist.top", t, bp["actual"]["top_fraction"]),
                        ("persist.pair", p, bp["actual"]["pair_fraction"]),
                        ("persist.top_shuffled", ts, bp["order_shuffled"]["top_fraction"]),
                        ("persist.pair_shuffled", ps, bp["order_shuffled"]["pair_fraction"]),
                    ]
                elif sp["branch_persistence"] is not None:
                    mism.append(f"{label}|{name}|flat cell has branch persistence")
            for k, a, b in pairs:
                compared += 1
                d = abs(float(a) - float(b))
                maxdiff = max(maxdiff, d)
                if d > 1e-9 * max(1.0, abs(float(b))):
                    mism.append(f"{label}|{name}|{k}: auditor {a} impl {b}")
    print(json.dumps({"labels": len(labels), "compared": compared, "max_abs_diff": maxdiff, "mismatches": mism[:50], "mismatch_count": len(mism)}, indent=1))
    return 0 if not mism and not fails else 1


if __name__ == "__main__":
    sys.exit(main())
