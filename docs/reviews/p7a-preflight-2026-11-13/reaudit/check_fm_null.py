"""Re-audit check (synthetic only): the exact count-preserving frequency-matched null of ADR-0013
section 14 item 8, as implemented in arborlm.p7a_core.frequency_matched_detail (the code under audit),
against the auditor's own standard-library regeneration (independent_sim.fm_stream, written from the
ADR text). No real trace, checkpoint or P5 record is read, except part E, which reads only the
auditor's own earlier output file outputs/fm_distortion.json (max count and top-8 share per published
P5 histogram; computed in the pre-freeze audit) to evaluate a sufficient condition for the repair.

A. Bit-for-bit: stream rows, stream_sha256, generator seed and swap count on synthetic histograms.
B. Feasible histograms on which the greedy repair cannot find a partner: does it stop loudly?
C. Artificial adjacency: slots and pages shared by consecutive queries before and after step 4,
   against the independence value sum_i (c_i / Q)^2 (expected shared slots of two independent queries
   whose slot-inclusion probabilities are c_i / Q).
D. The registered hard-stop check fires on a corrupted arrangement.
E. Sufficient condition for the repair on the 81 published histograms (no generation run on them).

Run (repo root):
  uv run --locked --extra pilot python docs/reviews/p7a-preflight-2026-11-13/reaudit/check_fm_null.py
"""

import importlib.util
import json
import random
import sys
import time
from pathlib import Path

from arborlm import p7a_core as core

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("independent_sim", HERE.parent / "independent_sim.py")
assert spec is not None and spec.loader is not None
indep = importlib.util.module_from_spec(spec)
spec.loader.exec_module(indep)

SLOTS, TOP = 4096, 8


def zipf_counts(q: int, active: int, exponent: float, hottest: int | None, rng: random.Random) -> list[int]:
    total = TOP * q
    slots = rng.sample(range(SLOTS), active)
    weights = [1 / (r + 1) ** exponent for r in range(active)]
    counts = [0] * SLOTS
    scale = total / sum(weights)
    for s, w in zip(slots, weights):
        counts[s] = min(q, int(w * scale))
    if hottest is not None:
        counts[slots[0]] = min(q, hottest)
    # fix the total exactly
    i = 0
    while sum(counts) != total:
        s = slots[i % active]
        if sum(counts) < total and counts[s] < q:
            counts[s] += 1
        elif sum(counts) > total and counts[s] > 1 and s != slots[0]:
            counts[s] -= 1
        i += 1
    assert sum(counts) == total and max(counts) <= q
    return counts


def tight(q: int, k: int) -> list[int]:
    """k slots sharing 8q occurrences as evenly as possible (k >= 8); k = 8 forces every query to hold
    all eight."""
    counts = [0] * SLOTS
    for i in range(TOP * q):
        counts[i % k] += 1
    assert max(counts) <= q
    return counts


def shared(rows: list[list[int]]) -> tuple[float, float]:
    """Mean number of slots shared by consecutive queries, and fraction of pairs sharing >= 1."""
    tot = anyc = 0
    prev = set(rows[0])
    for row in rows[1:]:
        cur = set(row)
        n = len(cur & prev)
        tot += n
        anyc += n > 0
        prev = cur
    return tot / (len(rows) - 1), anyc / (len(rows) - 1)


def page_reuse(rows: list[list[int]], r: int) -> float:
    """Pooled page reuse with the previous query (L-ID, R rows per page), all consecutive pairs."""
    reused = touched = 0
    prev: set[int] = set()
    for i, row in enumerate(rows):
        cur = {s // r for s in row}
        if i:
            reused += len(cur & prev)
            touched += len(cur)
        prev = cur
    return reused / touched


def part_a(log: list[str]) -> dict:
    rng = random.Random(20261113)
    cases = []
    for q in (64, 512, 4096, 32768):
        cases.append((f"zipf1.0 q={q}", zipf_counts(q, min(700, 8 * q), 1.0, None, rng), q))
        cases.append((f"zipf1.2 hot=0.56q q={q}", zipf_counts(q, min(500, 8 * q), 1.2, int(0.5634 * q), rng), q))
    cases.append(("hot=q (slot in every query) q=4096", zipf_counts(4096, 600, 1.0, 4096, rng), 4096))
    cases.append(("tight k=9 q=512", tight(512, 9), 512))
    cases.append(("tight k=8 q=128 (unique arrangement)", tight(128, 8), 128))
    cases.append(("uniform 4096 slots q=32768", tight(32768, 4096), 32768))
    results = {}
    for name, counts, q in cases:
        for rep in (91301, 91302, 91303):
            for index in (0, 40, 80):
                key = f"{name} | s={rep} idx={index}"
                t0 = time.monotonic()
                try:
                    theirs, info = core.frequency_matched_detail(counts, rep, index, queries=q)
                    their_rows = theirs.tolist()
                    their_err = None
                except Exception as exc:  # noqa: BLE001
                    their_rows, info, their_err = None, None, f"{type(exc).__name__}: {exc}"
                t1 = time.monotonic()
                try:
                    mine, swaps = indep.fm_stream(counts, rep, index, q)
                    my_err = None
                except Exception as exc:  # noqa: BLE001
                    mine, swaps, my_err = None, None, f"{type(exc).__name__}: {exc}"
                t2 = time.monotonic()
                if their_err or my_err:
                    same = (their_err is None) == (my_err is None)
                    results[key] = {"study_error": their_err, "auditor_error": my_err, "agree": same}
                    log.append(f"A {key}: study error={their_err!r} auditor error={my_err!r}")
                    continue
                ok = (
                    mine == their_rows
                    and indep.stream_sha256(mine) == info["stream_sha256"]
                    and swaps == info["repair_swaps"]
                    and info["generator_seed"] == rep * 1000 + index
                    and indep.counts_of(mine) == counts
                    and all(len(set(r)) == TOP for r in mine)
                )
                results[key] = {
                    "agree": ok,
                    "stream_sha256": info["stream_sha256"],
                    "swaps": swaps,
                    "study_seconds": round(t1 - t0, 3),
                    "auditor_seconds": round(t2 - t1, 3),
                }
                if not ok:
                    log.append(f"A {key}: DIFFER")
    n_ok = sum(1 for v in results.values() if v["agree"])
    log.append(f"A bit-for-bit: {n_ok}/{len(results)} cases agree (rows, sha256, swaps, seed)")
    full = [v for k, v in results.items() if "q=32768" in k and "study_seconds" in v]
    if full:
        log.append(
            "A full-size generation seconds: study max %.2f mean %.2f; auditor max %.2f mean %.2f"
            % (
                max(v["study_seconds"] for v in full),
                sum(v["study_seconds"] for v in full) / len(full),
                max(v["auditor_seconds"] for v in full),
                sum(v["auditor_seconds"] for v in full) / len(full),
            )
        )
    return results


def part_b(log: list[str]) -> dict:
    """Feasible histograms where the greedy repair may have no partner."""
    out = {}
    for label, counts, q in (
        ("k=8 all slots count q, q=8", tight(8, 8), 8),
        ("k=8 all slots count q, q=16", tight(16, 8), 16),
        ("k=8 all slots count q, q=128", tight(128, 8), 128),
        ("k=9, q=16", tight(16, 9), 16),
        ("k=9, q=64", tight(64, 9), 64),
        ("k=10, q=16", tight(16, 10), 16),
    ):
        fails = errs = 0
        trials = 300
        for t in range(trials):
            try:
                core.frequency_matched_detail(counts, 91301 + t, 0, queries=q)
            except core.InvariantError:
                fails += 1
            except Exception:  # noqa: BLE001
                errs += 1
            # the auditor's generator must fail on exactly the same seeds
        mine_fail = 0
        for t in range(trials):
            try:
                indep.fm_stream(counts, 91301 + t, 0, q)
            except RuntimeError:
                mine_fail += 1
        out[label] = {"trials": trials, "study_InvariantError": fails, "other_errors": errs,
                      "auditor_failures": mine_fail}
        log.append(f"B {label}: study InvariantError {fails}/{trials}, other {errs}, auditor {mine_fail}/{trials}")
    return out


def part_c(log: list[str]) -> dict:
    rng = random.Random(7)
    out = {}
    for name, counts in (
        ("zipf1.0, 700 slots, hot 0.56Q", zipf_counts(32768, 700, 1.0, 18460, rng)),
        ("zipf1.2, 300 slots, hot 0.46Q", zipf_counts(32768, 300, 1.2, 15136, rng)),
        ("zipf0.8, 1500 slots", zipf_counts(32768, 1500, 0.8, None, rng)),
    ):
        q = 32768
        g = random.Random(91301 * 1000 + 5)
        # steps 1-3 only, with the study's own function (rows before step 4)
        rows, swaps = core._deal_and_repair(counts, g, q, TOP)
        before = [list(r) for r in rows]
        order = list(range(q))
        g.shuffle(order)
        after = [before[i] for i in order]
        assert after == core.frequency_matched(counts, 91301, 5).tolist()
        independent = sum((c / q) ** 2 for c in counts)
        sb, ab = shared(before)
        sa, aa = shared(after)
        # random (non-adjacent) pairs as a second reference: query i vs query (i + q//2) of `before`
        far = [before[i] for i in range(0, q, 2)]
        far_pairs = sum(len(set(before[i]) & set(before[(i + q // 2) % q])) for i in range(q)) / q
        res = {
            "repair_swaps": swaps,
            "expected_shared_slots_independent": independent,
            "shared_slots_consecutive_before_step4": sb,
            "shared_slots_consecutive_after_step4": sa,
            "shared_slots_far_pairs_before_step4": far_pairs,
            "pairs_sharing_any_before": ab,
            "pairs_sharing_any_after": aa,
        }
        for r in (2, 8, 32):
            res[f"page_reuse_L-ID_R{r}_before"] = page_reuse(before, r)
            res[f"page_reuse_L-ID_R{r}_after"] = page_reuse(after, r)
        _ = far
        out[name] = res
        log.append(
            f"C {name}: shared slots consecutive before {sb:.4f} after {sa:.4f} far-pairs {far_pairs:.4f} "
            f"independent {independent:.4f}; page reuse R2 before {res['page_reuse_L-ID_R2_before']:.4f} "
            f"after {res['page_reuse_L-ID_R2_after']:.4f}; swaps {swaps}"
        )
    return out


def part_d(log: list[str]) -> dict:
    counts = tight(512, 40)
    original = core._deal_and_repair

    def broken(c, g, queries, top):  # type: ignore[no-untyped-def]
        rows, swaps = original(c, g, queries, top)
        rows[3][2] = rows[3][1]  # a duplicate inside one query; counts also change
        return rows, swaps

    def swapped(c, g, queries, top):  # type: ignore[no-untyped-def]
        rows, swaps = original(c, g, queries, top)
        a = rows[0][0]
        b = next(s for s in range(SLOTS) if s not in rows[0])
        rows[0][0] = b  # distinct slots kept, one count moved from a to b
        return rows, swaps

    out = {}
    for name, fake in (("duplicate", broken), ("count moved", swapped)):
        core._deal_and_repair = fake  # type: ignore[assignment]
        try:
            core.frequency_matched_detail(counts, 91301, 0, queries=512)
            out[name] = "NOT STOPPED"
        except core.InvariantError as exc:
            out[name] = f"InvariantError: {exc}"
        finally:
            core._deal_and_repair = original  # type: ignore[assignment]
        log.append(f"D corrupted arrangement ({name}): {out[name]}")
    return out


def part_e(log: list[str]) -> dict:
    data = json.loads((HERE.parent / "outputs" / "fm_distortion.json").read_text())
    q = 32768
    worst = None
    rows = []
    for cell in data["cells"]:
        lhs = TOP * (q - int(cell["max_count"]) + 1)
        rhs = cell["top8_target"] * TOP * q  # top-8 sum bounds the six-slot sum from above
        rows.append((cell["label"], lhs, rhs))
        if worst is None or lhs - rhs < worst[1] - worst[2]:
            worst = (cell["label"], lhs, rhs)
    holds = all(lhs > rhs for _, lhs, rhs in rows)
    log.append(
        f"E sufficient condition 8(Q - c_max + 1) > top-8 sum holds for {sum(l > r for _, l, r in rows)}/81 "
        f"published histograms; tightest {worst[0]}: {worst[1]} > {worst[2]:.0f}"
    )
    return {"holds_for_all": holds, "tightest": worst, "cells": len(rows)}


def main() -> int:
    log: list[str] = [f"python {sys.version.split()[0]}"]
    started = time.monotonic()
    out = {
        "A_bit_for_bit": part_a(log),
        "B_repair_dead_ends": part_b(log),
        "C_adjacency": part_c(log),
        "D_hard_stop": part_d(log),
        "E_published_bound": part_e(log),
    }
    log.append(f"total {time.monotonic() - started:.1f}s")
    (HERE / "outputs" / "fm_null.json").write_text(json.dumps(out, indent=1, default=str))
    (HERE / "outputs" / "fm_null.txt").write_text("\n".join(log) + "\n")
    print("\n".join(log))
    return 0


if __name__ == "__main__":
    sys.exit(main())
