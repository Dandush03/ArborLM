"""Auditor check: marginal distortion of the registered frequency-matched null (ADR-0013 sec. 14
clarification 2) on the PUBLISHED P5 selection histograms. Does not import arborlm.

For each of the 81 final P5 memory cells it re-implements clarification 2 from the ADR text
(generator seed s*1000+cell_index, torch.multinomial(counts, 8, replacement=False) per query, drawn in
chunks of 2048 rows like the study; chunking was shown by the implementer's test to equal one call per
query) and compares the realized marginal slot frequencies to the target (the P5 counts themselves).

It deliberately computes NO page or cache metric on these histograms (no m, no CONC value), so that
the choice of null is not informed by outcome-adjacent numbers.

Also checks the existence condition of an exact count-preserving null (max count <= 32768 queries;
Gale-Ryser with one side of uniform degree 8).

Run:  uv run --locked --extra pilot python docs/reviews/p7a-preflight-2026-11-13/check_fm_distortion.py
"""

import json
import math
import sys
import time
from pathlib import Path

import torch

P5 = Path("results/p5-2026-11-13")
KINDS = ("flat", "fixed_tree", "learned_tree")
SEEDS = (91301, 91302, 91303)
Q, TOP, SLOTS = 32768, 8, 4096


def cell_index(b: int, o: int, s: int, kind: str) -> int:
    return ((b - 101) * 9 + (o - 301) * 3 + (s - 501)) * 3 + KINDS.index(kind)


def draw(counts: list[int], seed: int) -> list[int]:
    weights = torch.tensor(counts, dtype=torch.float32)
    gen = torch.Generator().manual_seed(seed)
    out = torch.zeros(SLOTS, dtype=torch.int64)
    for start in range(0, Q, 2048):
        rows = torch.multinomial(weights.expand(2048, SLOTS), TOP, replacement=False, generator=gen)
        out += torch.bincount(rows.flatten(), minlength=SLOTS)
    return out.tolist()


def stats(target: list[int], realized: list[int]) -> dict[str, float]:
    total = sum(target)
    order = sorted(range(SLOTS), key=lambda i: (-target[i], i))
    p = [c / total for c in target]
    r = [c / sum(realized) for c in realized]

    def share(v: list[float], k: int) -> float:
        return sum(v[i] for i in order[:k])

    def eff(v: list[float]) -> float:
        return math.exp(-sum(x * math.log(x) for x in v if x > 0))

    return {
        "top1_target": share(p, 1),
        "top1_realized": share(r, 1),
        "top8_target": share(p, 8),
        "top8_realized": share(r, 8),
        "top32_target": share(p, 32),
        "top32_realized": share(r, 32),
        "eff_target": eff(p),
        "eff_realized": eff(r),
        "tvd": 0.5 * sum(abs(a - b) for a, b in zip(p, r, strict=True)),
        "max_count": max(target),
        "hottest_inclusion_target": max(target) / Q,
    }


def main() -> int:
    t0 = time.time()
    torch.set_num_threads(1)
    rows = []
    for b in (101, 102, 103):
        for o in (301, 302, 303):
            for s in (501, 502, 503):
                for kind in KINDS:
                    label = f"b{b}-o{o}-{kind}-s{s}"
                    rec = json.loads((P5 / label / "result.json").read_text())
                    counts = rec["final"]["retrieval"]["selected_slot_counts"]
                    assert sum(counts) == Q * TOP, label
                    idx = cell_index(b, o, s, kind)
                    reps = [stats(counts, draw(counts, seed * 1000 + idx)) for seed in SEEDS]
                    avg = {k: sum(r[k] for r in reps) / 3 for k in reps[0]}
                    rows.append({"label": label, "kind": kind, "cell_index": idx, **avg})
    out = {"cells": rows, "by_kind": {}}
    for kind in KINDS:
        sel = [r for r in rows if r["kind"] == kind]
        keys = [k for k in sel[0] if k not in ("label", "kind", "cell_index")]
        summary = {}
        for k in keys:
            vals = [r[k] for r in sel]
            summary[k] = {"mean": sum(vals) / len(vals), "min": min(vals), "max": max(vals)}
        rel_eff = [r["eff_realized"] / r["eff_target"] for r in sel]
        rel_top8 = [r["top8_realized"] / r["top8_target"] for r in sel]
        summary["eff_realized_over_target"] = {
            "mean": sum(rel_eff) / len(rel_eff), "min": min(rel_eff), "max": max(rel_eff)
        }
        summary["top8_realized_over_target"] = {
            "mean": sum(rel_top8) / len(rel_top8), "min": min(rel_top8), "max": max(rel_top8)
        }
        out["by_kind"][kind] = summary
    out["exact_null_exists_all_cells"] = all(r["max_count"] <= Q for r in rows)
    out["largest_max_count"] = max(r["max_count"] for r in rows)
    out["seconds"] = time.time() - t0
    out["torch"] = torch.__version__
    dest = Path(__file__).parent / "outputs" / "fm_distortion.json"
    dest.write_text(json.dumps(out, indent=1, sort_keys=True))
    for kind in KINDS:
        s = out["by_kind"][kind]
        print(kind)
        for k in ("top1_target", "top1_realized", "top8_target", "top8_realized", "top32_target",
                  "top32_realized", "eff_target", "eff_realized", "eff_realized_over_target",
                  "top8_realized_over_target", "tvd", "max_count"):
            v = s[k]
            print(f"  {k:28s} mean {v['mean']:.4f}  min {v['min']:.4f}  max {v['max']:.4f}")
    print("exact count-preserving null exists for all 81 cells:", out["exact_null_exists_all_cells"],
          "largest max count", out["largest_max_count"], "of", Q)
    print(f"seconds {out['seconds']:.1f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
