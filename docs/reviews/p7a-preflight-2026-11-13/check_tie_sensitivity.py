"""Auditor check (stdlib only, synthetic only): how much does the LRU tie rule among pages last used
by the same query change warm capacity misses, and can it shift a tree/flat ratio?

Uses the auditor's independent simulator functions (independent_sim.py). Synthetic Zipf histograms
over 400 hot slots with two concentrations (exponents chosen so the effective slot counts are near
the published flat ~132 and tree ~83-96 levels; no published histogram is used), an i.i.d. stream and
a stream with within-context persistence; L-FREQ fitted on an independent calibration draw.
Computes asc (study rule: lowest page of the oldest query evicted first; under L-FREQ that is the
HOTTEST page) versus desc (coldest first).

Run: python3 docs/reviews/p7a-preflight-2026-11-13/check_tie_sensitivity.py
"""

import json
import math
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import independent_sim as ind  # noqa: E402

Q = 32768


def weights_for(exponent: float, seed: int) -> list[float]:
    rng = random.Random(seed)
    hot = rng.sample(range(4096), 400)
    w = [0.0] * 4096
    for rank, slot in enumerate(hot, start=1):
        w[slot] = rank ** -exponent
    return w


def effective(w: list[float]) -> float:
    total = sum(w)
    return math.exp(-sum((x / total) * math.log(x / total) for x in w if x > 0))


def stream(w: list[float], seed: int, persist: float) -> list[list[int]]:
    rng = random.Random(seed)
    slots = [i for i, x in enumerate(w) if x > 0]
    ws = [w[i] for i in slots]
    rows: list[list[int]] = []
    for i in range(Q):
        chosen = rng.sample(rows[-1], 4) if (i % 64 and rng.random() < persist) else []
        while len(chosen) < 8:
            s = rng.choices(slots, ws)[0]
            if s not in chosen:
                chosen.append(s)
        rows.append(chosen)
    return rows


def main() -> int:
    t0 = time.time()
    results = {}
    for name, exponent in (("flat_like", 0.95), ("tree_like", 1.15)):
        w = weights_for(exponent, 1)
        cal = stream(w, 2, 0.0)
        pos = ind.layout_freq(ind.counts_of(cal))
        for sname, persist in (("iid", 0.0), ("persistent", 0.5)):
            ev = stream(w, 3, persist)
            eff = math.exp(-sum((c / (Q * 8)) * math.log(c / (Q * 8))
                                for c in ind.counts_of(ev) if c))
            for rows in (1, 2, 8):
                pages = ind.query_pages(ev, pos, rows)
                for c in (8, 16, 32, 64, 128):
                    a = ind.lru_counts(pages, c, "asc")
                    d = ind.lru_counts(pages, c, "desc")
                    wa = a["misses_warm"] - a["first_touch_warm"]
                    wd = d["misses_warm"] - d["first_touch_warm"]
                    results[f"{name}|{sname}|R{rows}|C{c}"] = {
                        "effective_slots_eval": eff,
                        "asc_warm_capacity_per_query": wa / (Q // 2),
                        "desc_warm_capacity_per_query": wd / (Q // 2),
                        "asc_over_desc": wa / wd if wd else None,
                    }
    for sname in ("iid", "persistent"):
        for rows in (1, 2, 8):
            for c in (8, 16, 32, 64, 128):
                f = results[f"flat_like|{sname}|R{rows}|C{c}"]
                t = results[f"tree_like|{sname}|R{rows}|C{c}"]
                ra = (t["asc_warm_capacity_per_query"] / f["asc_warm_capacity_per_query"]
                      if f["asc_warm_capacity_per_query"] else float("nan"))
                rd = (t["desc_warm_capacity_per_query"] / f["desc_warm_capacity_per_query"]
                      if f["desc_warm_capacity_per_query"] else float("nan"))
                print(f"{sname:10s} R{rows} C{c:3d}  flat asc {f['asc_warm_capacity_per_query']:.4f} "
                      f"desc {f['desc_warm_capacity_per_query']:.4f} | tree asc "
                      f"{t['asc_warm_capacity_per_query']:.4f} desc "
                      f"{t['desc_warm_capacity_per_query']:.4f} | ratio tree/flat asc {ra:.4f} "
                      f"desc {rd:.4f}")
    eff_note = {k.split("|")[0] + "|" + k.split("|")[1]: v["effective_slots_eval"]
                for k, v in results.items()}
    print("effective slots of the synthetic eval streams:",
          {k: round(v, 1) for k, v in eff_note.items()})
    print(f"seconds {time.time() - t0:.0f}")
    Path(__file__).parent.joinpath("outputs", "tie_sensitivity.json").write_text(
        json.dumps(results, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
