#!/usr/bin/env python3
"""Independent P7-A page simulator (auditor role). Standard library only; imports nothing from arborlm.

Derived from the text of docs/decisions/ADR-0013-p7a-storage-page-locality.md (sections 3-5, 9, 10 and
section 14 clarifications 4, 5 and 7), not from the implementer's simulator. Honest statement of
independence: the auditor read src/arborlm/p7a_sim.py and p7a_core.py while auditing them before this
file was written, and three choices the ADR leaves open are taken to match the study so that a
comparison is possible at all; each is marked OPEN below:

  OPEN-1  LRU tie rule among pages last used by the same query: ascending page number is evicted first
          (the study's choice, PENDING LEAD REVIEW). ``--tie desc`` switches to descending for a
          sensitivity check; a comparison against the study is only meaningful with ``--tie asc``.
  OPEN-2  L-FREQ / L-BFREQ: the ADR fixes the order (descending calibration count, ties by ascending
          slot ID); "slot s is placed at position rank(s)" is the only reading of that definition.
  OPEN-3  Record schema of the study (field names) is taken from the implementer's code because the
          ADR does not define one.

The data structure is deliberately different from the study's (a dictionary of last-use query
indices plus a lazily invalidated min-heap keyed (last query, page), instead of an ordered dict).

What is checked, per checkpoint, on the ACTUAL evaluation stream, for every R in {1,2,8,32,128,512},
every C in {8,16,32,64,128}, and layouts L-ID, L-FREQ (all) and L-BFREQ (trees):
  * per-query distinct value pages histogram (1..8) and total page touches;
  * distinct pages over the stream and over the warm-up half; pooled page reuse within / across
    contexts; sum over contexts of distinct pages per context;
  * cache counts: misses (all), first-touch misses (all), misses in the counted half, first-touch
    misses in the counted half; warm capacity misses = the last two subtracted (the criterion metric).
Also checked independently: trace integrity (range, distinct within a query, tree selections inside the
two distinct visited branches), optional SHA-256 of trace files against the trace-stage record, and
optional reproduction of P5's recorded selected-slot histogram and unique-slot count.
L-RAND (torch.randperm) and the shuffled / frequency-matched streams (torch generators) cannot be
reproduced without torch and are NOT checked.

Trace format (ADR / study): little-endian, no header. eval_selected.int16.bin and
calib_selected.int16.bin are int16 [Q, 8]; eval_branches.int8.bin (trees) is int8 [Q, 2]; row index is
context*64 + position. Q = 32,768 for the registered study (``--allow-small`` accepts any multiple of
64 for synthetic validation; the warm-up boundary is then Q // 2).

Checkpoint selection (clarification 7), ``--registered-selection``: in the registered order (backbone
101..103, order 301..303, seed 501..503 ascending; flat, fixed_tree, learned_tree), take for each
architecture in the order flat, fixed_tree, learned_tree its first three checkpoints, then draw three
more with ONE generator ``random.Random(91501)`` shared across the architectures in that order, via
``rng.sample(remaining_24_in_registered_order, 3)``. Printed and recorded in the output.

Exit status: 0 = every compared number agrees and every integrity check passed; 1 = any difference or
integrity failure; 2 = usage error or missing input. Independent engineering evidence only; not
Astra validation, not approval.
"""

import argparse
import hashlib
import heapq
import json
import random
import sys
import time
from array import array
from pathlib import Path

SLOTS, BRANCHES, PER_BRANCH, TOP, VISIT, CONTEXT = 4096, 16, 256, 8, 2, 64
REGISTERED_Q = 32768
RS = (1, 2, 8, 32, 128, 512)
CS = (8, 16, 32, 64, 128)
KINDS = ("flat", "fixed_tree", "learned_tree")
BACKBONES, ORDERS, SEEDS = (101, 102, 103), (301, 302, 303), (501, 502, 503)
SELECTION_SEED = 91501


# --- registry and selection -------------------------------------------------------------------------
def registered_labels() -> list[str]:
    return [
        f"b{b}-o{o}-{k}-s{s}" for b in BACKBONES for o in ORDERS for s in SEEDS for k in KINDS
    ]


def kind_of(label: str) -> str:
    kind = label.split("-")[2]
    if kind not in KINDS:
        raise ValueError(f"not a P7-A checkpoint label: {label}")
    return kind


def registered_selection(seed: int = SELECTION_SEED) -> list[str]:
    order = registered_labels()
    rng = random.Random(seed)
    chosen: list[str] = []
    for kind in KINDS:
        mine = [label for label in order if kind_of(label) == kind]
        extra = rng.sample(mine[3:], 3)
        chosen += mine[:3] + sorted(extra, key=order.index)
    return chosen


# --- trace reading ----------------------------------------------------------------------------------
def read_ints(path: Path, code: str, width: int) -> list[list[int]]:
    data = path.read_bytes()
    values = array(code)
    if len(data) % values.itemsize:
        raise ValueError(f"{path}: length not a whole number of elements")
    values.frombytes(data)
    if sys.byteorder != "little":
        values.byteswap()
    if len(values) % width:
        raise ValueError(f"{path}: element count not a multiple of {width}")
    return [list(values[i : i + width]) for i in range(0, len(values), width)]


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def integrity(selected: list[list[int]], branches: list[list[int]] | None, kind: str) -> list[str]:
    problems: list[str] = []
    for i, row in enumerate(selected):
        if len(row) != TOP or any(not 0 <= s < SLOTS for s in row):
            problems.append(f"query {i}: slot ID out of range")
        if len(set(row)) != TOP:
            problems.append(f"query {i}: duplicate slot ID")
        if len(problems) > 20:
            return problems
    if (kind != "flat") != (branches is not None):
        problems.append("branch trace presence does not match the architecture")
        return problems
    if branches is not None:
        if len(branches) != len(selected):
            problems.append("branch trace length differs from the selected trace")
            return problems
        for i, (row, br) in enumerate(zip(selected, branches)):
            if any(not 0 <= b < BRANCHES for b in br) or br[0] == br[1]:
                problems.append(f"query {i}: bad visited branches {br}")
            elif any(s // PER_BRANCH not in br for s in row):
                problems.append(f"query {i}: selected slot outside the visited branches")
            if len(problems) > 20:
                return problems
    return problems


# --- layouts (ADR section 4) ------------------------------------------------------------------------
def counts_of(selected: list[list[int]]) -> list[int]:
    counts = [0] * SLOTS
    for row in selected:
        for s in row:
            counts[s] += 1
    return counts


def layout_id() -> list[int]:
    return list(range(SLOTS))


def layout_freq(cal: list[int]) -> list[int]:
    pos = [0] * SLOTS
    for rank, slot in enumerate(sorted(range(SLOTS), key=lambda s: (-cal[s], s))):
        pos[slot] = rank
    return pos


def layout_bfreq(cal: list[int]) -> list[int]:
    pos = [0] * SLOTS
    for b in range(BRANCHES):
        members = sorted(range(b * PER_BRANCH, (b + 1) * PER_BRANCH), key=lambda s: (-cal[s], s))
        for rank, slot in enumerate(members):
            pos[slot] = b * PER_BRANCH + rank
    return pos


# --- per-query pages, C-independent statistics -------------------------------------------------------
def query_pages(selected: list[list[int]], pos: list[int], rows: int) -> list[frozenset[int]]:
    return [frozenset(pos[s] // rows for s in row) for row in selected]


def stream_statistics(pages: list[frozenset[int]]) -> dict:
    n = len(pages)
    warm = n // 2
    hist = [0] * TOP
    touches = 0
    seen: set[int] = set()
    first_half = None
    reuse = {"within": [0, 0], "cross": [0, 0]}
    per_context = 0
    for i, ps in enumerate(pages):
        hist[len(ps) - 1] += 1
        touches += len(ps)
        if i > 0:
            bucket = reuse["within"] if i % CONTEXT != 0 else reuse["cross"]
            bucket[0] += len(ps & pages[i - 1])
            bucket[1] += len(ps)
        seen.update(ps)
        if i == warm - 1:
            first_half = len(seen)
    for start in range(0, n, CONTEXT):
        per_context += len(frozenset().union(*pages[start : start + CONTEXT]))
    return {
        "hist": hist,
        "pages_sum": touches,
        "distinct_stream": len(seen),
        "distinct_first_half": first_half,
        "reuse_within": reuse["within"],
        "reuse_cross": reuse["cross"],
        "distinct_per_context_sum": per_context,
    }


# --- cache model (ADR section 5, clarifications 4-5) -------------------------------------------------
def lru_counts(pages: list[frozenset[int]], capacity: int, tie: str = "asc") -> dict[str, int]:
    """Per-query service. Misses = the query's distinct pages not cached at its start. Then every page
    of the query is cached with recency = this query; while the cache exceeds C, evict the least
    recently used page not used by this query (tie among equal recency: OPEN-1). First-touch = the
    page was never read before in the stream (warm-up included); counted half = queries >= Q // 2."""
    warm = len(pages) // 2
    last: dict[int, int] = {}  # cached page -> index of the query that last used it
    heap: list[tuple[int, int]] = []
    seen: set[int] = set()
    sign = 1 if tie == "asc" else -1
    m_all = f_all = m_warm = f_warm = 0
    for qi, ps in enumerate(pages):
        counted = qi >= warm
        for p in ps:
            if p not in last:
                m_all += 1
                first = p not in seen
                if first:
                    seen.add(p)
                    f_all += 1
                if counted:
                    m_warm += 1
                    f_warm += first
            last[p] = qi
            heapq.heappush(heap, (qi, sign * p))
        while len(last) > capacity:
            t, key = heapq.heappop(heap)
            p = sign * key
            if last.get(p) != t:
                continue  # stale heap entry
            if t == qi:
                raise AssertionError("a query needs more pages than the cache holds")
            del last[p]
        if len(heap) > 8 * capacity + 4096:  # compact stale entries
            heap = [(t, sign * p) for p, t in last.items()]
            heapq.heapify(heap)
    return {
        "misses_all": m_all,
        "first_touch_all": f_all,
        "misses_warm": m_warm,
        "first_touch_warm": f_warm,
    }


# --- one checkpoint -------------------------------------------------------------------------------
def simulate(trace_dir: Path, kind: str, allow_small: bool, tie: str) -> tuple[dict, dict, list[str]]:
    sel = read_ints(trace_dir / "eval_selected.int16.bin", "h", TOP)
    cal = read_ints(trace_dir / "calib_selected.int16.bin", "h", TOP)
    br = (
        read_ints(trace_dir / "eval_branches.int8.bin", "b", VISIT) if kind != "flat" else None
    )
    cal_br = (
        read_ints(trace_dir / "calib_branches.int8.bin", "b", VISIT) if kind != "flat" else None
    )
    problems: list[str] = []
    q = len(sel)
    if q != REGISTERED_Q and not (allow_small and q % CONTEXT == 0 and q >= 2 * CONTEXT):
        problems.append(f"evaluation trace has {q} queries, expected {REGISTERED_Q}")
    if len(cal) != q:
        problems.append(f"calibration trace has {len(cal)} queries, evaluation {q}")
    problems += ["evaluation: " + p for p in integrity(sel, br, kind)]
    problems += ["calibration: " + p for p in integrity(cal, cal_br, kind)]
    cal_counts = counts_of(cal)
    layouts = {"L-ID": layout_id(), "L-FREQ": layout_freq(cal_counts)}
    if kind != "flat":
        layouts["L-BFREQ"] = layout_bfreq(cal_counts)
    for name, pos in layouts.items():
        if sorted(pos) != list(range(SLOTS)):
            problems.append(f"{name} is not a permutation")
    if "L-BFREQ" in layouts and any(
        layouts["L-BFREQ"][s] // PER_BRANCH != s // PER_BRANCH for s in range(SLOTS)
    ):
        problems.append("L-BFREQ moved a slot out of its branch")
    out: dict = {}
    for name, pos in layouts.items():
        for rows in RS:
            pages = query_pages(sel, pos, rows)
            stats = stream_statistics(pages)
            by_c = {str(c): lru_counts(pages, c, tie) for c in CS}
            out[f"{name}|R{rows}"] = {"stats": stats, "by_c": by_c}
    meta = {"queries": q, "eval_counts": counts_of(sel)}
    return out, meta, problems


def compare(mine: dict, record: dict) -> list[str]:
    diffs: list[str] = []
    streams = record.get("streams", {}).get("actual")
    if streams is None:
        return ["study record has no actual stream"]
    for key, group in mine.items():
        theirs = streams.get(key)
        if theirs is None:
            diffs.append(f"{key}: missing in the study record")
            continue
        for field in ("hist", "pages_sum", "distinct_stream", "distinct_first_half",
                      "reuse_within", "reuse_cross", "distinct_per_context_sum"):
            a, b = group["stats"][field], theirs["stats"].get(field)
            if a != b:
                diffs.append(f"{key} stats.{field}: independent {a} study {b}")
        for c, counts in group["by_c"].items():
            other = theirs["by_c"].get(c)
            if other is None:
                diffs.append(f"{key} C={c}: missing in the study record")
                continue
            for field, value in counts.items():
                if other.get(field) != value:
                    diffs.append(f"{key} C={c} {field}: independent {value} study {other.get(field)}")
            wc_mine = counts["misses_warm"] - counts["first_touch_warm"]
            wc_theirs = other.get("misses_warm", 0) - other.get("first_touch_warm", 0)
            if wc_mine != wc_theirs:
                diffs.append(
                    f"{key} C={c} warm capacity misses: independent {wc_mine} study {wc_theirs}"
                )
    return diffs


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--trace-root", type=Path, required=True,
                    help="<trace run>/traces (holds one folder per checkpoint label)")
    ap.add_argument("--sim-workers", type=Path, required=True,
                    help="<results root>/simulate/<run id>/workers (holds <label>.result.json)")
    ap.add_argument("--trace-records", type=Path,
                    help="<results root>/trace/<run id>/checkpoints: verify trace file SHA-256")
    ap.add_argument("--p5-results", type=Path,
                    help="results/p5-2026-11-13: verify the evaluation histogram against P5")
    sel = ap.add_mutually_exclusive_group(required=True)
    sel.add_argument("--registered-selection", action="store_true",
                     help="clarification 7 selection (first three per architecture + 3 via 91501)")
    sel.add_argument("--labels", nargs="+")
    ap.add_argument("--allow-small", action="store_true", help="synthetic validation only")
    ap.add_argument("--tie", choices=("asc", "desc"), default="asc")
    ap.add_argument("--out", type=Path, required=True, help="JSON summary (review folder)")
    args = ap.parse_args()

    labels = registered_selection() if args.registered_selection else args.labels
    started = time.monotonic()
    summary: dict = {
        "tool": "independent_sim.py (auditor, stdlib only)",
        "python": sys.version,
        "argv": sys.argv,
        "selection": labels,
        "selection_rule": "first three per architecture + random.Random(91501).sample(rest, 3), "
        "architectures in order flat, fixed_tree, learned_tree"
        if args.registered_selection else "explicit --labels",
        "tie_rule": args.tie,
        "checkpoints": {},
    }
    failed = False
    for label in labels:
        t0 = time.monotonic()
        kind = kind_of(label)
        trace_dir = args.trace_root / label
        result_path = args.sim_workers / f"{label}.result.json"
        if not trace_dir.is_dir() or not result_path.is_file():
            print(f"MISSING INPUT for {label}: {trace_dir} or {result_path}", file=sys.stderr)
            return 2
        study = json.loads(result_path.read_text())
        problems: list[str] = []
        if study.get("outcome") != "completed" or not study.get("record", {}).get("complete"):
            problems.append("study simulation record is not completed")
        if args.trace_records is not None:
            trace_record = json.loads((args.trace_records / f"{label}.json").read_text())
            for part, prefix in (("evaluation", "eval"), ("calibration", "calib")):
                for name, entry in trace_record["files"][part].items():
                    if entry is None:
                        continue
                    if sha256_file(trace_dir / entry["file"]) != entry["sha256"]:
                        problems.append(f"{entry['file']}: SHA-256 differs from the trace record")
            if study.get("trace", {}).get("files") != trace_record["files"]:
                problems.append("simulation record cites different trace files")
        mine, meta, more = simulate(trace_dir, kind, args.allow_small, args.tie)
        problems += more
        if study.get("queries") not in (None, meta["queries"]):
            problems.append(f"queries: independent {meta['queries']} study {study.get('queries')}")
        if args.p5_results is not None:
            p5 = json.loads((args.p5_results / label / "result.json").read_text())
            retrieval = p5["final"]["retrieval"]
            if meta["eval_counts"] != retrieval["selected_slot_counts"]:
                problems.append("evaluation histogram differs from the P5 record")
            if sum(1 for c in meta["eval_counts"] if c) != retrieval["unique_selected_slots"]:
                problems.append("unique selected slots differ from the P5 record")
        diffs = compare(mine, study.get("record", {}))
        compared = sum(len(g["by_c"]) for g in mine.values())
        summary["checkpoints"][label] = {
            "kind": kind,
            "queries": meta["queries"],
            "layout_R_groups": len(mine),
            "cache_configurations_compared": compared,
            "integrity_problems": problems,
            "differences": diffs,
            "seconds": time.monotonic() - t0,
            "warm_capacity_misses_L_FREQ_R2_C32": mine["L-FREQ|R2"]["by_c"]["32"]["misses_warm"]
            - mine["L-FREQ|R2"]["by_c"]["32"]["first_touch_warm"],
        }
        status = "AGREE" if not diffs and not problems else "DIFFER"
        failed |= status != "AGREE"
        print(f"{label}: {status}  configs={compared}  integrity_problems={len(problems)}  "
              f"differences={len(diffs)}  {time.monotonic() - t0:.1f}s", flush=True)
        for line in problems[:50] + diffs[:200]:
            print(f"    {line}")
    summary["total_seconds"] = time.monotonic() - started
    summary["verdict"] = "DIFFER" if failed else "AGREE"
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(summary, indent=1, sort_keys=True))
    print(f"VERDICT {summary['verdict']}  checkpoints={len(labels)}  "
          f"seconds={summary['total_seconds']:.1f}  summary={args.out}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
