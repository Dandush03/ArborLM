"""P7-B spec review, part B: co-access statistics and candidate layouts on the CALIBRATION stream only.

Auditor role (Claude Opus 5.5). Standard library only; no arborlm import; no P7-A analysis code reused.

Reads ONLY, per checkpoint:
  experiments/P7AT-.../traces/<label>/calib_selected.int16.bin   (int16 [32768, 8], row = ctx*64+pos)
  experiments/P7AT-.../traces/<label>/calib_branches.int8.bin    (trees; int8 [32768, 2]; sanity only)
and the trace records (for the recorded sha256 of those two files). It never opens eval_selected or
eval_branches, and every layout built here is evaluated only on the calibration stream (in-sample or
split-half) or on a reviewer-generated count-preserving null OF THE CALIBRATION STREAM. No ADR-0014
registered outcome (E, rho, HB, HU, UTIL, BC, co-access gain on the evaluation stream) is computed.

My reading of ADR-0014 section 4 (ambiguities are listed in REVIEW.md):
  N[i][j] = #{(t, u) in one context : 0 <= t - u <= W, i selected at t, j selected at u, i != j}
  A = N + N^T.  (So a same-query pair is counted 2x per direction, a lagged pair 1x per direction.)
  Greedy page fill exactly as section 4 steps 1-3; L-BCOAX: branches by descending total count (ties
  lowest ID), greedy inside each branch (R <= 128 only: pages never straddle branches).

Usage (repo root):
  .venv/bin/python -I docs/reviews/p7b-spec-review-2026-11-13/scripts/calib_coaccess.py [--labels L ...] [--jobs N]
Independent engineering evidence; not Astra validation; not human approval.
"""

from __future__ import annotations

import argparse
import array
import glob
import hashlib
import json
import math
import os
import random
import statistics as st
import sys
import time
from collections import OrderedDict
from multiprocessing import Pool

TRACE_RUN = "P7AT-20261113T213133591303Z-0605157511b24311919ddfab8ac89b2e"
RAW = f"experiments/{TRACE_RUN}/traces"
TREC = f"results/p7a-2026-11-13/trace/{TRACE_RUN}/checkpoints"
OUT = "docs/reviews/p7b-spec-review-2026-11-13/outputs"
Q, TOP, CTX, NCTX, SLOTS, PB, NBR = 32768, 8, 64, 512, 4096, 256, 16
SETTINGS = ((2, 32), (8, 8))
NULL_SEED = 77001  # reviewer's own seed for a count-preserving null of the CALIBRATION stream
LS_MAX_PASSES = 12


# ----------------------------------------------------------------------------- io
def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def read_i16(path):
    a = array.array("h")
    with open(path, "rb") as f:
        a.frombytes(f.read())
    if sys.byteorder != "little":
        a.byteswap()
    return a


def read_i8(path):
    a = array.array("b")
    with open(path, "rb") as f:
        a.frombytes(f.read())
    return a


# ----------------------------------------------------------------------------- statistics
def counts_of(sel, ctxs=None):
    c = [0] * SLOTS
    if ctxs is None:
        for s in sel:
            c[s] += 1
    else:
        for k in ctxs:
            for s in sel[k * CTX * TOP:(k + 1) * CTX * TOP]:
                c[s] += 1
    return c


def eff_slots(c):
    t = sum(c)
    return math.exp(-sum(x / t * math.log(x / t) for x in c if x))


def affinity(sel, W, ctxs):
    """A as dict-of-dicts, symmetric, A[i][j] = N[i][j] + N[j][i]."""
    N = {}
    for k in ctxs:
        base = k * CTX
        rows = [tuple(sel[(base + p) * TOP:(base + p + 1) * TOP]) for p in range(CTX)]
        for t in range(CTX):
            rt = rows[t]
            for u in range(max(0, t - W), t + 1):
                ru = rows[u]
                for i in rt:
                    d = N.get(i)
                    if d is None:
                        d = N[i] = {}
                    for j in ru:
                        if i != j:
                            d[j] = d.get(j, 0) + 1
    A = {}
    for i, d in N.items():
        for j, v in d.items():
            A.setdefault(i, {})
            A[i][j] = A[i].get(j, 0) + v
            A.setdefault(j, {})
            A[j][i] = A[j].get(i, 0) + v
    return A


def aff_stats(A, f, kind):
    pairs = 0
    mass = 0
    vals = []
    same_branch_mass = 0
    for i, d in A.items():
        for j, v in d.items():
            if i < j:
                pairs += 1
                mass += v
                vals.append(v)
                if i // PB == j // PB:
                    same_branch_mass += v
    used = sum(1 for x in f if x)
    vals.sort(reverse=True)
    top = lambda q: sum(vals[: max(1, int(len(vals) * q))]) / mass if mass else None
    hist = {}
    for v in vals:
        b = "1" if v == 1 else "2" if v == 2 else "3-4" if v <= 4 else "5-16" if v <= 16 else "17-256" if v <= 256 else ">256"
        hist[b] = hist.get(b, 0) + 1
    return {
        "nonzero_unordered_pairs": pairs,
        "frac_of_all_pairs": pairs / (SLOTS * (SLOTS - 1) / 2),
        "used_slots": used,
        "frac_of_used_pairs": pairs / (used * (used - 1) / 2) if used > 1 else None,
        "mean_degree_used": 2 * pairs / used if used else None,
        "mass": mass,
        "frac_pairs_value_1": hist.get("1", 0) / pairs if pairs else None,
        "frac_pairs_value_le2": (hist.get("1", 0) + hist.get("2", 0)) / pairs if pairs else None,
        "hist": hist,
        "mass_share_top1pct_pairs": top(0.01),
        "mass_share_top10pct_pairs": top(0.10),
        "same_branch_mass_share": same_branch_mass / mass if (mass and kind != "flat") else None,
    }


# ----------------------------------------------------------------------------- layouts
def layout_freq(f, slots=None):
    slots = range(SLOTS) if slots is None else slots
    return sorted(slots, key=lambda s: (-f[s], s))


def greedy_pages(S, R, f, A, stats=None):
    """ADR-0014 section 4 greedy page fill over slot set S. Returns list of pages (lists)."""
    order = sorted(S, key=lambda s: (-f[s], s))
    Sset = set(S)
    placed = set()
    ptr = 0
    pages = []
    while len(placed) < len(S):
        while order[ptr] in placed:
            ptr += 1
        seed = order[ptr]
        placed.add(seed)
        page = [seed]
        s = {}
        for j, v in A.get(seed, {}).items():
            if j in Sset and j not in placed:
                s[j] = s.get(j, 0) + v
        while len(page) < R and len(placed) < len(S):
            if s:
                best = max(s.items(), key=lambda kv: (kv[1], f[kv[0]], -kv[0]))
                nxt = best[0]
                if stats is not None:
                    top = best[1]
                    nt = sum(1 for v in s.values() if v == top)
                    stats["score_ties"] += nt > 1
                    if nt > 1:
                        ft = sum(1 for k, v in s.items() if v == top and f[k] == f[nxt])
                        stats["score_and_f_ties"] += ft > 1
                    stats["picks_by_affinity"] += 1
            else:
                while order[ptr] in placed:
                    ptr += 1
                nxt = order[ptr]
                if stats is not None:
                    stats["picks_zero_score"] += 1
                    stats["picks_zero_score_used_slot"] += f[nxt] > 0
            placed.add(nxt)
            page.append(nxt)
            s.pop(nxt, None)
            for j, v in A.get(nxt, {}).items():
                if j in Sset and j not in placed:
                    s[j] = s.get(j, 0) + v
        pages.append(page)
    return pages


def pages_to_pos(pages):
    pos = [None] * SLOTS
    p = 0
    for pg in pages:
        for s in pg:
            pos[s] = p
            p += 1
    assert p == SLOTS and None not in pos
    return pos


def order_to_pages(order, R):
    return [order[i:i + R] for i in range(0, len(order), R)]


def l_coax(R, f, A, stats=None):
    return greedy_pages(list(range(SLOTS)), R, f, A, stats)


def branch_order(f):
    tot = [sum(f[b * PB:(b + 1) * PB]) for b in range(NBR)]
    return sorted(range(NBR), key=lambda b: (-tot[b], b))


def l_bcoax(R, f, A, stats=None):
    assert R <= PB
    pages = []
    for b in branch_order(f):
        pages += greedy_pages(list(range(b * PB, (b + 1) * PB)), R, f, A, stats)
    return pages


def l_bfreq(R, f):
    order = []
    for b in range(NBR):
        order += layout_freq(f, range(b * PB, (b + 1) * PB))
    return order_to_pages(order, R)


def within_mass(pages, A):
    tot = 0
    for pg in pages:
        for a in range(len(pg)):
            d = A.get(pg[a])
            if d:
                for b in range(a + 1, len(pg)):
                    tot += d.get(pg[b], 0)
    return tot


def local_search(pages, A, f, constrained):
    """Bounded first-improvement swap search maximising within-page affinity mass.
    Swap x (page P) with y (page Q) when the within-page mass strictly increases. If constrained,
    y must be in x's branch (keeps branches contiguous). Deterministic order: x by (-f, id)."""
    pages = [list(p) for p in pages]
    where = {}
    for pi, pg in enumerate(pages):
        for s in pg:
            where[s] = pi
    W = lambda x, pi: sum(A.get(x, {}).get(z, 0) for z in pages[pi] if z != x)
    active = sorted(A.keys(), key=lambda s: (-f[s], s))
    passes = 0
    swaps = 0
    while passes < LS_MAX_PASSES:
        passes += 1
        improved = 0
        for x in active:
            P = where[x]
            ax = A[x]
            wxP = W(x, P)
            cand = {}
            for z, v in ax.items():
                qz = where[z]
                if qz != P:
                    cand[qz] = cand.get(qz, 0) + v  # = w(x, Q)
            best = (0, None, None)
            for Qi, wxQ in cand.items():
                for y in pages[Qi]:
                    if constrained and y // PB != x // PB:
                        continue
                    axy = ax.get(y, 0)
                    gain = (wxQ - axy) + (W(y, P) - axy) - wxP - W(y, Qi)
                    if gain > best[0]:
                        best = (gain, Qi, y)
            if best[1] is not None:
                g, Qi, y = best
                pages[P][pages[P].index(x)] = y
                pages[Qi][pages[Qi].index(y)] = x
                where[x], where[y] = Qi, P
                improved += 1
                swaps += 1
        if not improved:
            break
    return pages, {"passes": passes, "swaps": swaps}


# ----------------------------------------------------------------------------- simulation
def query_pages(sel, pos, R, qrange):
    out = []
    for q in qrange:
        out.append(tuple(sorted({pos[s] // R for s in sel[q * TOP:(q + 1) * TOP]})))
    return out


def lru(pq, C, warm_start, track_age=False, descending=False):
    """Per-query service, LRU, ascending page number among a query's own pages (ADR-0013 item 10).
    Returns warm capacity misses (misses on pages already seen) and, optionally, eviction ages."""
    cache = OrderedDict()
    seen = set()
    last = {}
    capw = 0
    ages = []
    for qi, ps in enumerate(pq):
        for p in (reversed(ps) if descending else ps):
            if p in cache:
                cache.move_to_end(p)
            else:
                if p in seen and qi >= warm_start:
                    capw += 1
                seen.add(p)
                cache[p] = None
            last[p] = qi
        while len(cache) > C:
            ev, _ = cache.popitem(last=False)
            if track_age and qi >= warm_start:
                ages.append(qi - last[ev])
        assert len(cache) <= C
    n = len(pq) - warm_start
    return (capw / n, ages) if track_age else capw / n


def ctx_queries(ctxs):
    return [k * CTX + p for k in ctxs for p in range(CTX)]


def null_stream(c, idx):
    """Exact count-preserving null of the CALIBRATION stream (ADR-0013 item 8 algorithm, reviewer seed)."""
    g = random.Random(NULL_SEED * 1000 + idx)
    occ = []
    for s, k in enumerate(c):
        occ.extend([s] * k)
    g.shuffle(occ)
    nq = len(occ) // TOP
    rows = [occ[i * TOP:(i + 1) * TOP] for i in range(nq)]
    for q in range(nq):
        row = rows[q]
        while len(set(row)) < TOP:
            seen = set()
            for jpos, s in enumerate(row):
                if s in seen:
                    break
                seen.add(s)
            x = row[jpos]
            mine = set(row)
            done = False
            for step in range(1, nq):
                other = rows[(q + step) % nq]
                if x in other:
                    continue
                for k, y in enumerate(other):
                    if y not in mine:
                        row[jpos], other[k] = y, x
                        done = True
                        break
                if done:
                    break
            assert done
    order = list(range(nq))
    g.shuffle(order)
    flat = array.array("h", [s for i in order for s in rows[i]])
    assert counts_of(flat) == c
    return flat


# ----------------------------------------------------------------------------- one checkpoint
def work(args):
    label, kind, idx = args
    t0 = time.perf_counter()
    rec = json.load(open(f"{TREC}/{label}.json"))
    d = f"{RAW}/{rec['trace_dir']}"
    out = {"label": label, "kind": kind, "files_read": []}
    cs = rec["files"]["calibration"]["selected"]
    assert sha256(f"{d}/{cs['file']}") == cs["sha256"]
    out["files_read"].append(f"{d}/{cs['file']}")
    sel = read_i16(f"{d}/{cs['file']}")
    assert len(sel) == Q * TOP
    if kind != "flat":
        cb = rec["files"]["calibration"]["branches"]
        assert sha256(f"{d}/{cb['file']}") == cb["sha256"]
        out["files_read"].append(f"{d}/{cb['file']}")
        br = read_i8(f"{d}/{cb['file']}")
        out["branch_membership_ok"] = all(
            sel[q * TOP + j] // PB in (br[2 * q], br[2 * q + 1]) for q in range(Q) for j in range(TOP))
    ALL = list(range(NCTX))
    HA, HB = list(range(NCTX // 2)), list(range(NCTX // 2, NCTX))
    f = counts_of(sel)
    out["calib_eff_slots"] = eff_slots(f)
    out["calib_unique"] = sum(1 for x in f if x)

    # --- affinity, timing, sparsity
    ta = time.perf_counter()
    A8 = affinity(sel, 8, ALL)
    out["sec_affinity_W8"] = time.perf_counter() - ta
    ta = time.perf_counter()
    A0 = affinity(sel, 0, ALL)
    out["sec_affinity_W0"] = time.perf_counter() - ta
    out["aff_W8"] = aff_stats(A8, f, kind)
    out["aff_W0"] = aff_stats(A0, f, kind)
    nul = null_stream(f, idx)
    An8 = affinity(nul, 8, ALL)
    out["aff_W8_null"] = aff_stats(An8, f, kind)
    keys = set((i, j) for i, d in A8.items() for j in d if i < j) | set((i, j) for i, d in An8.items() for j in d if i < j)
    tv = sum(abs(A8.get(i, {}).get(j, 0) - An8.get(i, {}).get(j, 0)) for i, j in keys)
    out["aff_W8_tv_actual_vs_null"] = 0.5 * tv / out["aff_W8"]["mass"]
    An0 = affinity(nul, 0, ALL)
    keys = set((i, j) for i, d in A0.items() for j in d if i < j) | set((i, j) for i, d in An0.items() for j in d if i < j)
    tv = sum(abs(A0.get(i, {}).get(j, 0) - An0.get(i, {}).get(j, 0)) for i, j in keys)
    out["aff_W0_tv_actual_vs_null"] = 0.5 * tv / out["aff_W0"]["mass"]
    out["aff_W0_null"] = aff_stats(An0, f, kind)

    # --- layouts on full calibration
    lay = {}
    gstats = {}
    tg = time.perf_counter()
    for R in (2, 8):
        lay[("FREQ", R)] = order_to_pages(layout_freq(f), R)
        for name, Am in (("COAX", A8), ("COAX0", A0), ("COAXnullfit", An8)):
            stt = {"score_ties": 0, "score_and_f_ties": 0, "picks_by_affinity": 0,
                   "picks_zero_score": 0, "picks_zero_score_used_slot": 0}
            lay[(name, R)] = l_coax(R, f, Am, stt)
            gstats[f"{name}|R{R}"] = stt
        rp = list(range(SLOTS))
        random.Random(91601).shuffle(rp)
        rpp = []
        for g in range(NBR):
            rpp += greedy_pages(rp[g * PB:(g + 1) * PB], R, f, A8)
        lay[("RPCOAX", R)] = rpp
        if kind != "flat":
            lay[("BCOAX_idorder", R)] = [pg for b in range(NBR) for pg in greedy_pages(list(range(b * PB, (b + 1) * PB)), R, f, A8)]
            stt = {"score_ties": 0, "score_and_f_ties": 0, "picks_by_affinity": 0,
                   "picks_zero_score": 0, "picks_zero_score_used_slot": 0}
            lay[("BCOAX", R)] = l_bcoax(R, f, A8, stt)
            gstats[f"BCOAX|R{R}"] = stt
            lay[("BCOAX0", R)] = l_bcoax(R, f, A0)
            lay[("BFREQ", R)] = l_bfreq(R, f)
    out["sec_greedy_layouts"] = time.perf_counter() - tg
    out["greedy_tie_stats"] = gstats
    # R=1 invariance: greedy at R=1 must reproduce L-FREQ exactly
    out["R1_coax_equals_freq"] = [p[0] for p in l_coax(1, f, A8)] == layout_freq(f)
    # zero-affinity greedy equals L-FREQ (R=8)
    out["zeroA_coax_equals_freq_R8"] = l_coax(8, f, {}) == lay[("FREQ", 8)]
    # page creation order irrelevance: reverse the page order of L-COAX (R=2) and re-simulate below
    out["within_page_mass_W8"] = {f"{n}|R{R}": within_mass(p, A8) / out["aff_W8"]["mass"]
                                  for (n, R), p in lay.items()}
    for (n, R), p in lay.items():
        assert sorted(s for pg in p for s in pg) == list(range(SLOTS)), (n, R)
        if n.startswith("B") and n != "BFREQ_":
            assert all(len({s // PB for s in pg}) == 1 for pg in p), (n, R)

    # --- in-sample simulation on the full calibration stream (warm 256 ctx, count 256), + calibration null
    allq = list(range(Q))
    sims = {}
    for (n, R), p in lay.items():
        pos = pages_to_pos(p)
        for C in [c for (r, c) in SETTINGS if r == R]:
            sims[f"actual|{n}|R{R}C{C}"] = lru(query_pages(sel, pos, R, allq), C, Q // 2)
            if n in ("FREQ", "COAX", "BCOAX", "BFREQ", "COAXnullfit", "RPCOAX"):
                sims[f"null|{n}|R{R}C{C}"] = lru(query_pages(nul, pos, R, allq), C, Q // 2)
            if n in ("FREQ", "COAX", "BCOAX"):
                sims[f"actual_desc|{n}|R{R}C{C}"] = lru(query_pages(sel, pos, R, allq), C, Q // 2, descending=True)
    # page-number relabelling: reverse page order of L-COAX (only the eviction tie rule can change)
    for R, C in SETTINGS:
        p = list(reversed(lay[("COAX", R)]))
        sims[f"actual|COAX_pages_reversed|R{R}C{C}"] = lru(query_pages(sel, pages_to_pos(p), R, allq), C, Q // 2)
        p = list(reversed(lay[("FREQ", R)]))
        sims[f"actual|FREQ_pages_reversed|R{R}C{C}"] = lru(query_pages(sel, pages_to_pos(p), R, allq), C, Q // 2)
        if kind != "flat":
            p = list(reversed(lay[("BCOAX", R)]))
            sims[f"actual|BCOAX_pages_reversed|R{R}C{C}"] = lru(query_pages(sel, pages_to_pos(p), R, allq), C, Q // 2)
        pr = [list(reversed(pg)) for pg in lay[("COAX", R)]]
        sims[f"actual|COAX_rows_reversed|R{R}C{C}"] = lru(query_pages(sel, pages_to_pos(pr), R, allq), C, Q // 2)
    out["insample"] = sims
    # eviction age (queries since last use at eviction), counted half, L-FREQ and L-COAX
    ages = {}
    for R, C in SETTINGS:
        for n in ("FREQ", "COAX"):
            _, a = lru(query_pages(sel, pages_to_pos(lay[(n, R)]), R, allq), C, Q // 2, track_age=True)
            a.sort()
            ages[f"{n}|R{R}C{C}"] = {"n": len(a), "mean": st.fmean(a) if a else None,
                                     "p10": a[len(a) // 10] if a else None, "median": a[len(a) // 2] if a else None,
                                     "p90": a[9 * len(a) // 10] if a else None,
                                     "frac_le_8": sum(1 for x in a if x <= 8) / len(a) if a else None}
    out["eviction_age_queries"] = ages

    # --- split-half: fit on one half, evaluate on the other (warm first 128 ctx, count last 128)
    split = {}
    tl = time.perf_counter()
    ls_info = {}
    for fitname, fit, other in (("A", HA, HB), ("B", HB, HA)):
        fh = counts_of(sel, fit)
        Ah = affinity(sel, 8, fit)
        for R in (2, 8):
            L = {"FREQ": order_to_pages(layout_freq(fh), R), "COAX": l_coax(R, fh, Ah)}
            L["COAX_LS"], ls_info[f"COAX|{fitname}|R{R}"] = local_search(L["COAX"], Ah, fh, False)
            if kind != "flat":
                L["BFREQ"] = l_bfreq(R, fh)
                L["BCOAX"] = l_bcoax(R, fh, Ah)
                L["BCOAX_LS"], ls_info[f"BCOAX|{fitname}|R{R}"] = local_search(L["BCOAX"], Ah, fh, True)
            for n, p in L.items():
                pos = pages_to_pos(p)
                split[f"wpm_fit|{n}|{fitname}|R{R}"] = within_mass(p, Ah)
                for C in [c for (r, c) in SETTINGS if r == R]:
                    for evname, ev in ((fitname, fit), ("A" if fitname == "B" else "B", other)):
                        qq = ctx_queries(ev)
                        split[f"m|{n}|fit{fitname}|eval{evname}|R{R}C{C}"] = lru(
                            query_pages(sel, pos, R, qq), C, len(qq) // 2)
    out["sec_split_half"] = time.perf_counter() - tl
    out["split"] = split
    out["local_search"] = ls_info
    out["seconds"] = time.perf_counter() - t0
    return out


def registered():
    labels = []
    for p in sorted(glob.glob(f"{TREC}/*.json")):
        d = json.load(open(p))
        labels.append((d["cell_index"], d["label"]))
    labels.sort()
    res = []
    for idx, lb in labels:
        b, o, *k, s = lb.split("-")
        res.append((lb, "-".join(k), idx))
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--labels", nargs="*")
    ap.add_argument("--jobs", type=int, default=12)
    ap.add_argument("--out", default=f"{OUT}/calib_coaccess.json")
    a = ap.parse_args()
    todo = registered()
    if a.labels:
        todo = [t for t in todo if t[0] in a.labels]
    t0 = time.perf_counter()
    with Pool(a.jobs) as pool:
        res = pool.map(work, todo, chunksize=1)
    files = sorted({x for r in res for x in r["files_read"]})
    assert not any("eval_" in x for x in files)
    out = {"wall_seconds": time.perf_counter() - t0, "n": len(res), "files_read": files,
           "eval_files_read": [x for x in files if "eval_" in x], "per_checkpoint": res}
    with open(a.out, "w") as fh:
        json.dump(out, fh, indent=0, sort_keys=True)
    print("done", len(res), "checkpoints in", round(out["wall_seconds"], 1), "s; files read", len(files),
          "; evaluation files read:", len(out["eval_files_read"]))


if __name__ == "__main__":
    main()
