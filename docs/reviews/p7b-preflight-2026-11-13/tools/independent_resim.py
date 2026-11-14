"""Independent re-simulation of the P7-B criterion settings (ADR-0014 section 10) and the
re-simulation confirmation file (gate (c), schema ``p7b-resim-confirmation-v1``), one stream at a
time.

Auditor role (Claude Opus 5.5), written from ADR-0013 section 5 / section 14 items 4, 5, 8, 10, 12, 16
and ADR-0014 sections 4, 5 and 10. Python standard library only; no ``arborlm`` import and no
implementer code. Layouts come from ``independent_layouts.py`` (the auditor's own rebuild, from the
calibration trace only). Independent engineering evidence; not Astra validation, not approval.

For each checkpoint of the registered 18-checkpoint selection (ADR-0013 section 14 item 12,
reproduced below), for R = 2, C = 32 and R = 8, C = 8, under both eviction tie rules, for the actual
stream and its three count-preserving nulls, on L-FREQ, L-COAX, L-PCOAX-1..5 and (trees) L-BCOAX
(and L-NCOAX on the actual stream): re-simulate from the trace files and compare the four counts
(misses and first-touch misses, whole stream and counted half) and the per-context quantiles with
the study's per-checkpoint simulation record. Also checks: trace file hashes against the identity
record, trace integrity, null-stream hashes against the recorded ones, the study record's effective
slot entropy and counts hash, and the auditor's layout hashes against the layout stage's table.

Simulator (written independently): per-query service; a query's distinct pages are looked up
(miss if absent; first-touch if never read before in the stream, warm-up included); then each page
of the query receives the stamp (query index, position in touch order) where touch order is
ascending page number ('asc') or descending ('desc'); while more than C pages are cached the page
with the smallest stamp is evicted (never one of the current query's pages); warm-up = first half
of the queries; m = warm capacity misses = misses - first-touch misses in the counted half.

Usage: see AUDIT.md (registered commands for streams A and B, and the validation modes).
"""

from __future__ import annotations

import argparse
import hashlib
import heapq
import json
import math
import random
import struct
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import independent_layouts as IL  # noqa: E402  (the auditor's own tool, same folder)

TOOL = "independent_resim.py (auditor role, Claude Opus 5.5, standard library only) v1"
SETTINGS = ((2, 32), (8, 8))
TIES = ("asc", "desc")
STREAMS = ("actual", "null_1", "null_2", "null_3")
NULL_SEEDS = {"A": (91301, 91302, 91303), "B": (91321, 91322, 91323)}
QUANTILES = (0.0, 0.05, 0.25, 0.5, 0.75, 0.95, 1.0)
CONTEXT = 64
P7A_SIM_WORKERS = "results/p7a-2026-11-13/simulate/P7AS-20261113T213357135402Z-af93d829f722456e95f394462eedc57b/workers"


def registered_selection(labels: list[str] | None = None) -> list[str]:
    order = labels or IL.registered_labels()
    g = random.Random(91501)
    chosen: list[str] = []
    for kind in IL.KINDS:
        mine = [lb for lb in order if IL.parse(lb)[3] == kind]
        extra = g.sample(mine[3:], 3)
        chosen += mine[:3] + sorted(extra, key=order.index)
    return chosen


def criterion_layouts(kind: str) -> list[str]:
    base = ["L-FREQ", "L-COAX", *(f"L-PCOAX-{i}" for i in range(1, 6))]
    return base + (["L-BCOAX"] if kind != "flat" else [])


# --------------------------------------------------------------------------------------------------
# simulator
# --------------------------------------------------------------------------------------------------
def page_tuples(stream: list[list[int]], pages: list[list[int]], R: int) -> list[tuple[int, ...]]:
    page_of = [0] * IL.SLOTS
    for pi, pg in enumerate(pages):
        if len(pg) != R:
            raise SystemExit("a page does not hold R rows")
        for s in pg:
            page_of[s] = pi
    return [tuple(sorted({page_of[s] for s in row})) for row in stream]


def lru(queries: list[tuple[int, ...]], C: int, tie: str) -> dict:
    n = len(queries)
    if n % CONTEXT or (n // CONTEXT) % 2:
        raise SystemExit("stream is not an even number of whole contexts")
    warm = n // 2
    stamp: dict[int, tuple[int, int]] = {}
    heap: list[tuple[int, int, int]] = []
    seen: set[int] = set()
    misses_all = first_all = misses_warm = first_warm = 0
    per_context: list[int] = []
    ctx_cap = 0
    for t, pages in enumerate(queries):
        counted = t >= warm
        for p in pages:
            if p not in stamp:
                misses_all += 1
                if counted:
                    misses_warm += 1
                if p not in seen:
                    seen.add(p)
                    first_all += 1
                    if counted:
                        first_warm += 1
                elif counted:
                    ctx_cap += 1
        order = pages if tie == "asc" else tuple(reversed(pages))
        for r, p in enumerate(order):
            stamp[p] = (t, r)
            heapq.heappush(heap, (t, r, p))
        current = set(pages)
        while len(stamp) > C:
            st, r, p = heapq.heappop(heap)
            if stamp.get(p) != (st, r):
                continue
            if p in current:
                raise SystemExit("simulator would evict a page of the current query")
            del stamp[p]
        if len(stamp) > C:
            raise SystemExit("cache above capacity")
        if counted and (t + 1) % CONTEXT == 0:
            per_context.append(ctx_cap)
            ctx_cap = 0
    ordered = sorted(per_context)
    k = len(ordered)
    return {
        "misses_all": misses_all,
        "first_touch_all": first_all,
        "misses_warm": misses_warm,
        "first_touch_warm": first_warm,
        "ctx_q": [ordered[int(q * (k - 1))] for q in QUANTILES],
    }


# --------------------------------------------------------------------------------------------------
# inputs
# --------------------------------------------------------------------------------------------------
def rows_of(flat: list[int]) -> list[list[int]]:
    return [flat[q : q + IL.TOP] for q in range(0, len(flat), IL.TOP)]


def read_checked(path: Path, sha: str, prefix: str) -> bytes:
    if not path.name.startswith(prefix):
        raise SystemExit(f"refusing {path.name}: expected prefix {prefix}")
    data = path.read_bytes()
    if IL.sha256_bytes(data) != sha:
        raise SystemExit(f"{path}: SHA-256 differs from its record")
    return data


def int8(data: bytes) -> list[int]:
    return list(struct.unpack(f"<{len(data)}b", data))


def int16(data: bytes) -> list[int]:
    return list(struct.unpack(f"<{len(data) // 2}h", data))


def integrity(selected: list[int], branches: list[int] | None, kind: str) -> list[str]:
    problems = []
    if any(v < 0 or v >= IL.SLOTS for v in selected):
        problems.append("slot ID out of range")
    rows = rows_of(selected)
    if any(len(set(r)) != IL.TOP for r in rows):
        problems.append("duplicate slot within a query")
    if (kind != "flat") != (branches is not None):
        problems.append("branch file presence does not match the architecture")
    if branches is not None:
        pairs = [branches[k : k + 2] for k in range(0, len(branches), 2)]
        if len(pairs) != len(rows):
            problems.append("branch trace length differs")
        else:
            for r, b in zip(rows, pairs):
                if b[0] == b[1] or min(b) < 0 or max(b) >= IL.GROUPS:
                    problems.append("bad visited branch pair")
                    break
                if any(s // IL.BRANCH_ROWS not in b for s in r):
                    problems.append("selected slot outside the visited branches")
                    break
    return problems


def stream_inputs(args, label: str, manifest: dict, base: Path) -> dict:
    """The stream's selected IDs (and branches) with recorded hashes and null-hash references."""
    kind = IL.parse(label)[3]
    entry = next(c for c in manifest["checkpoints"] if c["label"] == label)
    files = {f["role"]: f for f in entry["files"]}
    out: dict = {"null_refs": {}}
    if args.stream_source == "calibration":  # validation mode only
        sel_f, br_f = files["calibration.selected"], files.get("calibration.branches")
        prefix = "calib_"
        out["selected"] = int16(read_checked(base / sel_f["relpath"], sel_f["recorded_sha256"], prefix))
        out["branches"] = (None if br_f is None else
                           int8(read_checked(base / br_f["relpath"], br_f["recorded_sha256"], prefix)))
        out["files_sha256"] = {"selected": sel_f["recorded_sha256"],
                               "branches": None if br_f is None else br_f["recorded_sha256"]}
    elif args.stream == "A":
        sel_f, br_f = files["evaluation.selected"], files.get("evaluation.branches")
        prefix = "eval_"
        out["selected"] = int16(read_checked(base / sel_f["relpath"], sel_f["recorded_sha256"], prefix))
        out["branches"] = (None if br_f is None else
                           int8(read_checked(base / br_f["relpath"], br_f["recorded_sha256"], prefix)))
        out["files_sha256"] = {"selected": sel_f["recorded_sha256"],
                               "branches": None if br_f is None else br_f["recorded_sha256"]}
        ref_dir = args.p7a_reference or (args.repo / P7A_SIM_WORKERS)
        ref = json.loads((Path(ref_dir) / f"{label}.result.json").read_text())
        fm = ref["record"]["frequency_matched"]
        out["null_refs"]["p7a_record"] = [fm[f"freq_matched_{i}"]["stream_sha256"] for i in (1, 2, 3)]
    else:  # stream B: the committed stream-B identity manifest and the trace-b records
        sb = json.loads(args.stream_b_manifest.read_text())
        me = sb["checkpoints"][label]
        rec = json.loads((args.trace_b_compact / "checkpoints" / f"{label}.json").read_text())
        stored = rec["files"]["stream_b"]
        directory = args.trace_b_dir / label
        if stored["selected"]["sha256"] != me["selected_sha256"]:
            raise SystemExit(f"{label}: trace-b record and stream-B manifest disagree (selected)")
        out["selected"] = int16(read_checked(directory / stored["selected"]["file"],
                                             me["selected_sha256"], "streamB_"))
        if stored.get("branches"):
            if stored["branches"]["sha256"] != me["branches_sha256"]:
                raise SystemExit(f"{label}: trace-b record and manifest disagree (branches)")
            out["branches"] = int8(read_checked(directory / stored["branches"]["file"],
                                                me["branches_sha256"], "streamB_"))
        else:
            out["branches"] = None
        out["files_sha256"] = {"selected": me["selected_sha256"], "branches": me["branches_sha256"]}
        out["null_refs"]["stream_b_manifest"] = [n["stream_sha256"] for n in me["null_streams"]]
        out["counts_sha256_manifest"] = me["counts_sha256"]
    return out


# --------------------------------------------------------------------------------------------------
def check_one(task: tuple) -> dict:
    label, args = task
    t0 = time.monotonic()
    kind = IL.parse(label)[3]
    manifest = json.loads(args.identity_path.read_text())
    base = args.base
    diffs: list[dict] = []
    problems: list[str] = []
    cal = IL.calibration_selected(manifest, label, base)
    built = IL.build_checkpoint(label, cal)
    layouts = built["layouts"]
    table = json.loads(args.hash_table.read_text())["layouts"].get(label, {})
    for R in (2, 8):
        for name in [*criterion_layouts(kind), "L-NCOAX"]:
            mine = IL.canonical(layouts[R][name])
            if table.get(f"{name}|R{R}") != mine:
                problems.append(f"layout {name}|R{R}: auditor canonical hash differs from the table")
    inputs = stream_inputs(args, label, manifest, base)
    selected, branches = inputs["selected"], inputs["branches"]
    problems += integrity(selected, branches, kind)
    rows = rows_of(selected)
    counts = IL.counts_of(selected)
    total = sum(counts)
    entropy = -math.fsum(c / total * math.log(c / total) for c in counts if c)
    counts_sha = IL.sha256_bytes(struct.pack(f"<{IL.SLOTS}I", *counts))
    if "counts_sha256_manifest" in inputs and inputs["counts_sha256_manifest"] != counts_sha:
        problems.append("per-slot counts hash differs from the stream-B identity manifest")
    seeds = args.null_seeds or NULL_SEEDS[args.stream]
    index = IL.cell_index(label)
    nulls = [IL.count_preserving_null(counts, s, index) for s in seeds]
    null_hashes = [IL.stream_sha256(nl) for nl in nulls]
    for ref_name, ref in inputs["null_refs"].items():
        if ref != null_hashes:
            problems.append(f"null stream hashes differ from {ref_name}")
    record_path = args.simulate_dir / "workers" / f"{label}.result.json"
    raw = record_path.read_bytes()
    record_sha = IL.sha256_bytes(raw)
    result = json.loads(raw)
    if result.get("outcome") != "completed" or not result.get("record", {}).get("complete"):
        problems.append("simulation record is not a completed record")
    rec = result.get("record", {})
    if result.get("stream") != args.stream or rec.get("stream") != args.stream:
        problems.append("simulation record is for a different stream")
    if [n["stream_sha256"] for n in result.get("null_streams", [])] != null_hashes:
        problems.append("simulation record's null stream hashes differ from the auditor's")
    if [n["generator_seed"] for n in result.get("null_streams", [])] != [s * 1000 + index for s in seeds]:
        problems.append("simulation record's null generator seeds are not the registered ones")
    tfiles = result.get("trace", {}).get("files", {})
    if tfiles.get("selected", {}).get("sha256") != inputs["files_sha256"]["selected"]:
        problems.append("simulation record's trace file hash differs")
    binding = result.get("layout_binding", {})
    if binding.get("hash_table_sha256") != IL.file_sha256(args.hash_table):
        problems.append("simulation record was bound to a different layout hash table")
    ev = rec.get("evaluation_counts", {})
    if ev.get("counts_sha256") != counts_sha:
        problems.append("record's evaluation counts hash differs")
    if ev.get("entropy_nats") != entropy:
        problems.append(f"record's entropy {ev.get('entropy_nats')!r} != auditor's {entropy!r}")
    if rec.get("queries") != len(rows):
        problems.append("record's query count differs")
    sims = 0
    streams = {"actual": rows, "null_1": nulls[0], "null_2": nulls[1], "null_3": nulls[2]}
    for R, C in args.settings:
        for st_name, st in streams.items():
            names = criterion_layouts(kind) + (["L-NCOAX"] if st_name == "actual" else [])
            for name in names:
                q = page_tuples(st, layouts[R][name], R)
                group = rec.get("streams", {}).get(st_name, {}).get(f"{name}|R{R}")
                for tie in TIES:
                    mine = lru(q, C, tie)
                    sims += 1
                    theirs = None if group is None else group["by_c"].get(str(C), {}).get(tie)
                    if theirs is None:
                        diffs.append({"stream": st_name, "layout": name, "R": R, "C": C,
                                      "tie": tie, "problem": "missing in the study record"})
                        continue
                    for key in ("misses_all", "first_touch_all", "misses_warm",
                                "first_touch_warm", "ctx_q"):
                        if mine[key] != theirs.get(key):
                            diffs.append({"stream": st_name, "layout": name, "R": R, "C": C,
                                          "tie": tie, "field": key, "auditor": mine[key],
                                          "study": theirs.get(key)})
    return {
        "label": label,
        "kind": kind,
        "record_sha256": record_sha,
        "differences": diffs,
        "integrity_problems": problems,
        "simulations": sims,
        "null_stream_sha256": null_hashes,
        "entropy_nats": entropy,
        "seconds": time.monotonic() - t0,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", type=Path, default=Path("."))
    ap.add_argument("--stream", choices=("A", "B"), required=True)
    ap.add_argument("--stream-source", choices=("evaluation", "calibration"), default="evaluation",
                    help="'calibration' = validation mode only (calibration trace treated as a stream)")
    ap.add_argument("--identity", type=Path, default=None)
    ap.add_argument("--base", type=Path, default=None)
    ap.add_argument("--hash-table", type=Path, required=True)
    ap.add_argument("--simulate-dir", type=Path, required=True,
                    help="compact folder of the simulate stage run (holds workers/<label>.result.json)")
    ap.add_argument("--simulate-run-id", default=None)
    ap.add_argument("--p7a-reference", type=Path, default=None)
    ap.add_argument("--trace-b-compact", type=Path, default=None)
    ap.add_argument("--trace-b-dir", type=Path, default=None)
    ap.add_argument("--stream-b-manifest", type=Path, default=None)
    ap.add_argument("--selection", nargs="*", default=None, help="validation only")
    ap.add_argument("--null-seeds", type=int, nargs=3, default=None, help="validation only")
    ap.add_argument("--jobs", type=int, default=1)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--detail", type=Path, required=True)
    args = ap.parse_args()
    started = time.monotonic()
    args.repo = args.repo.resolve()
    registered = args.identity is None
    args.identity_path = (args.repo / "docs/reviews/p7b-spec-inputs-2026-11-13/identity_manifest.json"
                          if registered else args.identity.resolve())
    manifest = IL.load_manifest(args.identity_path, registered)
    args.base = (args.base or args.repo).resolve()
    args.settings = SETTINGS
    if args.stream == "B" and args.stream_source == "evaluation":
        if not (args.trace_b_compact and args.trace_b_dir):
            raise SystemExit("stream B needs --trace-b-compact and --trace-b-dir")
        args.stream_b_manifest = (args.stream_b_manifest
                                  or args.trace_b_compact / "stream_b_identity_manifest.json")
    labels_all = sorted((c["cell_index"], c["label"]) for c in manifest["checkpoints"])
    selection = args.selection or registered_selection()
    if not registered and args.selection is None:
        raise SystemExit("a non-registered identity manifest needs an explicit --selection")
    tasks = [(lb, args) for lb in selection]
    if args.jobs > 1:
        from concurrent.futures import ProcessPoolExecutor

        with ProcessPoolExecutor(max_workers=args.jobs) as pool:
            results = list(pool.map(check_one, tasks))
    else:
        results = [check_one(t) for t in tasks]
    agree = all(not r["differences"] and not r["integrity_problems"] for r in results)
    run_id = args.simulate_run_id or args.simulate_dir.resolve().name
    tool_sha = IL.file_sha256(Path(__file__))
    layouts_used = sorted({n for r in results for n in criterion_layouts(r["kind"])})
    confirmation = {
        "schema": "p7b-resim-confirmation-v1",
        "verdict": "AGREE" if agree else "DISAGREE",
        "tool": f"{TOOL}; sha256 {tool_sha}; layouts by independent_layouts.py sha256 "
        f"{IL.file_sha256(Path(IL.__file__))}",
        "tool_sha256": tool_sha,
        "stream": args.stream,
        "simulate_stage_run_id": run_id,
        "selection": selection,
        "settings": [{"R": r, "C": c} for r, c in SETTINGS],
        "tie_rules": list(TIES),
        "streams_compared": list(STREAMS),
        "layouts_compared": layouts_used + ["L-NCOAX (actual stream only)"],
        "record_sha256": {r["label"]: r["record_sha256"] for r in results},
        "checkpoints": {r["label"]: {"differences": r["differences"],
                                     "integrity_problems": r["integrity_problems"]}
                        for r in results},
        "stream_source": args.stream_source,
        "label": "independent engineering evidence; not Astra validation; not human approval",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(confirmation, indent=1, sort_keys=True) + "\n")
    detail = {
        "tool_sha256": tool_sha,
        "python": sys.version,
        "registered_selection_used": args.selection is None,
        "labels_in_manifest": len(labels_all),
        "results": results,
        "wall_seconds": time.monotonic() - started,
        "jobs": args.jobs,
    }
    args.detail.parent.mkdir(parents=True, exist_ok=True)
    args.detail.write_text(json.dumps(detail, indent=1, sort_keys=True) + "\n")
    n_diff = sum(len(r["differences"]) for r in results)
    n_prob = sum(len(r["integrity_problems"]) for r in results)
    print(f"{confirmation['verdict']}: stream {args.stream} ({args.stream_source}), "
          f"{len(results)} checkpoints, {sum(r['simulations'] for r in results)} simulations, "
          f"{n_diff} differences, {n_prob} integrity problems, {detail['wall_seconds']:.1f} s wall, "
          f"jobs={args.jobs}")
    return 0 if agree else 2


if __name__ == "__main__":
    sys.exit(main())
