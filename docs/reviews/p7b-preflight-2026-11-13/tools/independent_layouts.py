"""Independent rebuild of the P7-B criterion layouts (ADR-0014 section 4) and the layout-hash
confirmation file (gate (b), schema ``p7b-layout-confirmation-v1``).

Auditor role (Claude Opus 5.5), written from the ADR text. Python standard library only; no
``arborlm`` import and no implementer code. Independent engineering evidence; not Astra validation
and not human approval.

What it does, per checkpoint, at R = 2 and R = 8:
  * reads ONLY the calibration selected-slot file named in the identity manifest (role
    ``calibration.selected``; the file name must start with ``calib_``), after verifying its SHA-256;
  * f = per-slot calibration counts; A = same-query affinity (A[i][j], i != j, = number of queries
    in which i and j are both selected);
  * L-COAX (all 4,096 slots), L-BCOAX (trees: branches = slot // 256), L-PCOAX-1..5 (the five
    registered partitions, hashes verified), L-NCOAX (L-COAX built from the first calibration null
    replicate, seed 91311, regenerated here from ADR-0013 section 14 item 8 / clarification 16);
  * also L-FREQ (descending count, ties slot ID), which the re-simulation tool needs;
  * canonical hash of each (pages in page order, slot IDs sorted inside a page, '<H').

Algorithm structure is deliberately different from the implementer's: greedy fill uses a lazy
max-heap per page; refinement recomputes each candidate gain literally as the change of total
within-page affinity from the page contents (no incremental page-weight tables).

Readings pinned (the ADR text leaves no choice here, stated for the record):
  * The zero-score case of step 1: every unplaced slot with no affinity to the page has score 0;
    among them the tie rule (higher f, then lowest ID) picks the hottest unplaced slot.
  * Step 2 "constrained": y must be in x's group; page numbers are global page indices in the
    concatenated (group-ordered) page list. Running refinement globally or per group gives the
    same result (a swap in one group never changes a gain in another group, and each group gets
    at most 12 passes either way).

Usage (registered run, after the layouts stage; see AUDIT.md for the exact command):
  .venv/bin/python -I tools/independent_layouts.py --repo . \
      --hash-table results/p7b-2026-11-13/layouts/<RUN>/layout_hash_table.json \
      --layout-run-id <RUN> --out <confirmation.json> --detail <detail.json>
"""

from __future__ import annotations

import argparse
import hashlib
import heapq
import json
import os
import random
import struct
import sys
import time
from array import array
from pathlib import Path

TOOL = "independent_layouts.py (auditor role, Claude Opus 5.5, standard library only) v1"
SLOTS, TOP, BRANCH_ROWS, GROUPS, MAX_PASSES = 4096, 8, 256, 16, 12
KINDS = ("flat", "fixed_tree", "learned_tree")
PARTITION_SEEDS = (91601, 91602, 91603, 91604, 91605)
PARTITION_SHA256 = {
    91601: "ae626b43df264708466a8afc9c2b5434c3db053e7b57f27800b9674192b16487",
    91602: "0d310a05d82ef6eba8cc5adbeba16a88d74a5221353eb0208c1e755f3230e9f3",
    91603: "55cbff61076689e78f030d374b741aa28f448484694f51d3f65dbc56db183af5",
    91604: "98142918ba5f6ef34e6b9d3efc1f27a7c5ea9fd821bfb2b862641145af6f25a2",
    91605: "8d55366cd4d23a08e651161638e0b0cc34dbee0ad13764e3181ffa2b5db26a0c",
}
CAL_NULL_SEEDS = (91311, 91312, 91313)
IDENTITY_OVERALL = "77dea76d96672b13336415ff325388c9c76d8e3b09cf25f2242d9cfe44e2a86a"
ROWS = (2, 8)


# --------------------------------------------------------------------------------------------------
# registry (ADR-0013 / P5 order: backbone, order, seed ascending; flat, fixed, learned)
# --------------------------------------------------------------------------------------------------
def registered_labels() -> list[str]:
    out = []
    for b in (101, 102, 103):
        for o in (301, 302, 303):
            for s in (501, 502, 503):
                for k in KINDS:
                    out.append(f"b{b}-o{o}-{k}-s{s}")
    return out


def parse(label: str) -> tuple[int, int, int, str]:
    b, o, rest = label.split("-", 2)
    kind, s = rest.rsplit("-", 1)
    return int(b[1:]), int(o[1:]), int(s[1:]), kind


def cell_index(label: str) -> int:
    b, o, s, kind = parse(label)
    pair = (b - 101) * 9 + (o - 301) * 3 + (s - 501)
    return pair * 3 + KINDS.index(kind)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def read_int16(path: Path) -> list[int]:
    data = array("h")
    data.frombytes(path.read_bytes())
    if sys.byteorder != "little":  # pragma: no cover
        data.byteswap()
    return data.tolist()


def pack_int16(values: list[int]) -> bytes:
    return struct.pack(f"<{len(values)}h", *values)


# --------------------------------------------------------------------------------------------------
# identity manifest: calibration files only
# --------------------------------------------------------------------------------------------------
def manifest_overall(data: dict) -> str:
    triples = []
    for c in sorted(data["checkpoints"], key=lambda c: c["cell_index"]):
        for f in sorted(c["files"], key=lambda f: f["role"]):
            triples.append([c["label"], f["role"], f["recorded_sha256"]])
    return sha256_bytes(json.dumps(triples, separators=(",", ":"), ensure_ascii=True).encode())


def load_manifest(path: Path, registered: bool) -> dict:
    data = json.loads(path.read_text())
    if manifest_overall(data) != data["overall_hash"]["sha256"]:
        raise SystemExit("identity manifest does not verify (overall hash)")
    if registered and data["overall_hash"]["sha256"] != IDENTITY_OVERALL:
        raise SystemExit("identity manifest overall hash differs from ADR-0014 section 3")
    for c in data["checkpoints"]:
        if cell_index(c["label"]) != c["cell_index"]:
            raise SystemExit(f"cell index of {c['label']} differs from the registered order")
    return data


def calibration_selected(manifest: dict, label: str, base: Path) -> list[int]:
    """The calibration selected IDs of ``label``. Refuses anything that is not a calibration file.
    No other role is ever resolved to a path by this tool."""
    entry = next(c for c in manifest["checkpoints"] if c["label"] == label)
    files = [f for f in entry["files"] if f["role"] == "calibration.selected"]
    if len(files) != 1:
        raise SystemExit(f"{label}: expected exactly one calibration.selected entry")
    f = files[0]
    path = base / f["relpath"]
    if not path.name.startswith("calib_"):
        raise SystemExit(f"{label}: refusing {path.name}: not a calibration file")
    if file_sha256(path) != f["recorded_sha256"]:
        raise SystemExit(f"{label}: calibration file hash differs from the identity manifest")
    values = read_int16(path)
    if len(values) % TOP or any(v < 0 or v >= SLOTS for v in values):
        raise SystemExit(f"{label}: malformed calibration trace")
    for q in range(0, len(values), TOP):
        if len(set(values[q : q + TOP])) != TOP:
            raise SystemExit(f"{label}: duplicate slot in a calibration query")
    return values


# --------------------------------------------------------------------------------------------------
# counts, affinity, the count-preserving null (ADR-0013 section 14 items 8 and 16)
# --------------------------------------------------------------------------------------------------
def counts_of(flat: list[int]) -> list[int]:
    f = [0] * SLOTS
    for s in flat:
        f[s] += 1
    return f


def same_query_affinity(flat: list[int]) -> dict[int, dict[int, int]]:
    A: dict[int, dict[int, int]] = {}
    for q in range(0, len(flat), TOP):
        row = flat[q : q + TOP]
        for a in range(TOP):
            i = row[a]
            for b in range(a + 1, TOP):
                j = row[b]
                di = A.setdefault(i, {})
                di[j] = di.get(j, 0) + 1
                dj = A.setdefault(j, {})
                dj[i] = dj.get(i, 0) + 1
    return A


def count_preserving_null(counts: list[int], replicate_seed: int, index: int) -> list[list[int]]:
    """Item 8: shuffle all occurrences (slot-ID order) with g; deal 8 per query; repair duplicates
    (first duplicated pair in entry order, its later member; scan following queries cyclically for
    the first that lacks x and holds an entry absent from q, lowest such position); permute the
    queries with g. Hard checks: counts preserved, eight distinct slots per query."""
    total = sum(counts)
    if total % TOP:
        raise SystemExit("counts are not a whole number of queries")
    nq = total // TOP
    g = random.Random(replicate_seed * 1000 + index)
    occ: list[int] = []
    for slot in range(len(counts)):
        occ.extend([slot] * counts[slot])
    g.shuffle(occ)
    rows = [occ[k * TOP : (k + 1) * TOP] for k in range(nq)]
    for q in range(nq):
        row = rows[q]
        while True:
            seen: set[int] = set()
            pos = None
            for k, v in enumerate(row):
                if v in seen:
                    pos = k
                    break
                seen.add(v)
            if pos is None:
                break
            x = row[pos]
            present = set(row)
            done = False
            for step in range(1, nq):
                other = rows[(q + step) % nq]
                if x in other:
                    continue
                for k2, y in enumerate(other):
                    if y not in present:
                        row[pos], other[k2] = y, x
                        done = True
                        break
                if done:
                    break
            if not done:
                raise SystemExit("null repair dead end")
    order = list(range(nq))
    g.shuffle(order)
    stream = [rows[i] for i in order]
    got = [0] * len(counts)
    for row in stream:
        if len(set(row)) != TOP:
            raise SystemExit("null: a query lacks distinct slots")
        for v in row:
            got[v] += 1
    if got != list(counts):
        raise SystemExit("null: counts not preserved")
    return stream


def stream_sha256(stream: list[list[int]]) -> str:
    return sha256_bytes(pack_int16([v for row in stream for v in row]))


# --------------------------------------------------------------------------------------------------
# step 1 (greedy page fill) and step 2 (bounded swap refinement), written from section 4
# --------------------------------------------------------------------------------------------------
def greedy(slots: list[int], R: int, f: list[int], A: dict[int, dict[int, int]]) -> list[list[int]]:
    members = set(slots)
    hot = sorted(slots, key=lambda s: (-f[s], s))
    placed: set[int] = set()
    ptr = 0
    pages: list[list[int]] = []
    while len(placed) < len(members):
        while hot[ptr] in placed:
            ptr += 1
        seed = hot[ptr]
        placed.add(seed)
        page = [seed]
        score: dict[int, int] = {}
        heap: list[tuple[int, int, int]] = []

        def absorb(u: int) -> None:
            for v, a in A.get(u, {}).items():
                if v in members and v not in placed:
                    score[v] = score.get(v, 0) + a
                    heapq.heappush(heap, (-score[v], -f[v], v))

        absorb(seed)
        while len(page) < R and len(placed) < len(members):
            nxt = None
            while heap:
                neg, _, v = heapq.heappop(heap)
                if v in placed or score[v] != -neg:
                    continue  # stale entry (scores only grow)
                nxt = v
                break
            if nxt is None:  # every unplaced slot has score 0: higher f, then lowest ID
                while hot[ptr] in placed:
                    ptr += 1
                nxt = hot[ptr]
            placed.add(nxt)
            page.append(nxt)
            absorb(nxt)
        pages.append(page)
    return pages


def within(pages: list[list[int]], A: dict[int, dict[int, int]]) -> int:
    t = 0
    for pg in pages:
        for a in range(len(pg)):
            row = A.get(pg[a], {})
            for b in range(a + 1, len(pg)):
                t += row.get(pg[b], 0)
    return t


def refine(
    pages: list[list[int]],
    A: dict[int, dict[int, int]],
    f: list[int],
    group: list[int] | None = None,
) -> tuple[list[list[int]], dict]:
    pages = [list(p) for p in pages]
    where = {}
    for pi, pg in enumerate(pages):
        for s in pg:
            where[s] = pi
    visit = sorted((s for s, row in A.items() if any(row.values())), key=lambda s: (-f[s], s))
    start = within(pages, A)
    passes = swaps = 0
    converged = False
    while passes < MAX_PASSES:
        passes += 1
        made = 0
        for x in visit:
            P = where[x]
            Ax = A[x]
            candidate_pages = sorted({where[z] for z, a in Ax.items() if a > 0} - {P})
            pageP = pages[P]
            x_on_P = sum(Ax.get(z, 0) for z in pageP if z != x)
            best = None
            for Q in candidate_pages:
                pageQ = pages[Q]
                for y in pageQ:
                    if group is not None and group[y] != group[x]:
                        continue
                    Ay = A.get(y, {})
                    x_on_Q = sum(Ax.get(z, 0) for z in pageQ if z != y)
                    y_on_P = sum(Ay.get(z, 0) for z in pageP if z != x)
                    y_on_Q = sum(Ay.get(z, 0) for z in pageQ if z != y)
                    gain = (x_on_Q + y_on_P) - (x_on_P + y_on_Q)
                    if gain > 0:
                        key = (gain, -Q, -y)
                        if best is None or key > best:
                            best = key
            if best is None:
                continue
            Q, y = -best[1], -best[2]
            ix, iy = pages[P].index(x), pages[Q].index(y)
            pages[P][ix], pages[Q][iy] = y, x  # each takes the position the other held
            where[x], where[y] = Q, P
            made += 1
            swaps += 1
        if made == 0:
            converged = True
            break
    end = within(pages, A)
    if end < start:
        raise SystemExit("refinement decreased within-page affinity")
    return pages, {"passes": passes, "swaps": swaps, "converged": converged,
                   "within_before": start, "within_after": end}


def partition(seed: int) -> list[list[int]]:
    lst = list(range(SLOTS))
    random.Random(seed).shuffle(lst)
    digest = sha256_bytes(struct.pack(f"<{SLOTS}H", *lst))
    if digest != PARTITION_SHA256[seed]:
        raise SystemExit(f"partition {seed}: hash {digest} differs from the registered one")
    return [lst[g * BRANCH_ROWS : (g + 1) * BRANCH_ROWS] for g in range(GROUPS)]


def branches() -> list[list[int]]:
    return [list(range(b * BRANCH_ROWS, (b + 1) * BRANCH_ROWS)) for b in range(GROUPS)]


def unconstrained(R: int, f: list[int], A: dict) -> tuple[list[list[int]], dict]:
    return refine(greedy(list(range(SLOTS)), R, f, A), A, f)


def constrained(groups: list[list[int]], R: int, f: list[int], A: dict) -> tuple[list, dict]:
    if R > BRANCH_ROWS:
        raise SystemExit("this tool builds R <= 256 only (the registered check uses R = 2, 8)")
    totals = [sum(f[s] for s in g) for g in groups]
    order = sorted(range(len(groups)), key=lambda g: (-totals[g], g))
    pages: list[list[int]] = []
    for g in order:
        pages += greedy(groups[g], R, f, A)
    gid = [0] * SLOTS
    for g, members in enumerate(groups):
        for s in members:
            gid[s] = g
    out, info = refine(pages, A, f, gid)
    pos = {s: k for k, s in enumerate(s for pg in out for s in pg)}
    for g, members in enumerate(groups):
        places = sorted(pos[s] for s in members)
        if places[-1] - places[0] + 1 != len(members):
            raise SystemExit(f"group {g} not contiguous")
    return out, info


def freq_pages(R: int, f: list[int]) -> list[list[int]]:
    order = sorted(range(SLOTS), key=lambda s: (-f[s], s))
    return [order[k : k + R] for k in range(0, SLOTS, R)]


def canonical(pages: list[list[int]]) -> str:
    flat = sorted(s for pg in pages for s in pg)
    if flat != list(range(SLOTS)):
        raise SystemExit("a layout is not a permutation of 0..4095")
    out = bytearray()
    for pg in pages:
        srt = sorted(pg)
        out += struct.pack(f"<{len(srt)}H", *srt)
    return sha256_bytes(bytes(out))


def build_checkpoint(label: str, cal: list[int], rows=ROWS) -> dict:
    """All criterion layouts of one checkpoint: {R: {name: pages}} plus diagnostics."""
    kind = parse(label)[3]
    f = counts_of(cal)
    t0 = time.monotonic()
    A = same_query_affinity(cal)
    null = count_preserving_null(f, CAL_NULL_SEEDS[0], cell_index(label))
    null_hash = stream_sha256(null)
    An = same_query_affinity([v for row in null for v in row])
    parts = {f"L-PCOAX-{i + 1}": partition(seed) for i, seed in enumerate(PARTITION_SEEDS)}
    layouts: dict[int, dict[str, list[list[int]]]] = {}
    info: dict[str, dict] = {}
    for R in rows:
        per: dict[str, list[list[int]]] = {"L-FREQ": freq_pages(R, f)}
        per["L-COAX"], info[f"L-COAX|R{R}"] = unconstrained(R, f, A)
        per["L-NCOAX"], info[f"L-NCOAX|R{R}"] = unconstrained(R, f, An)
        for name, groups in parts.items():
            per[name], info[f"{name}|R{R}"] = constrained(groups, R, f, A)
        if kind != "flat":
            per["L-BCOAX"], info[f"L-BCOAX|R{R}"] = constrained(branches(), R, f, A)
        layouts[R] = per
    return {
        "label": label,
        "kind": kind,
        "layouts": layouts,
        "info": info,
        "calibration_counts_sha256": sha256_bytes(struct.pack(f"<{SLOTS}I", *f)),
        "calibration_null_1_stream_sha256": null_hash,
        "unique_selected_slots": sum(1 for c in f if c),
        "seconds": time.monotonic() - t0,
    }


def required(kind: str) -> list[str]:
    base = ["L-COAX", "L-NCOAX", *(f"L-PCOAX-{i}" for i in range(1, 6))]
    return base + (["L-BCOAX"] if kind != "flat" else [])


# --------------------------------------------------------------------------------------------------
def worker(task: tuple[str, str, str]) -> dict:
    label, manifest_path, base = task
    manifest = json.loads(Path(manifest_path).read_text())
    cal = calibration_selected(manifest, label, Path(base))
    built = build_checkpoint(label, cal)
    hashes = {
        f"R{R}": {name: canonical(pages) for name, pages in per.items()}
        for R, per in built["layouts"].items()
    }
    return {k: v for k, v in built.items() if k != "layouts"} | {"hashes": hashes}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", type=Path, default=Path("."))
    ap.add_argument("--identity", type=Path, default=None,
                    help="identity manifest (default: the registered one)")
    ap.add_argument("--base", type=Path, default=None,
                    help="directory the manifest relpaths are relative to (default: --repo)")
    ap.add_argument("--hash-table", type=Path, required=True,
                    help="the layout stage's layout_hash_table.json")
    ap.add_argument("--layout-run-id", required=True)
    ap.add_argument("--labels", nargs="*", default=None,
                    help="synthetic validation only: the labels to cover")
    ap.add_argument("--jobs", type=int, default=1)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--detail", type=Path, required=True)
    args = ap.parse_args()
    started = time.monotonic()
    repo = args.repo.resolve()
    registered = args.identity is None
    manifest_path = (repo / "docs/reviews/p7b-spec-inputs-2026-11-13/identity_manifest.json"
                     if registered else args.identity.resolve())
    manifest = load_manifest(manifest_path, registered)
    labels = args.labels if args.labels else registered_labels()
    listed = sorted(c["label"] for c in manifest["checkpoints"])
    if sorted(labels) != listed:
        raise SystemExit("the identity manifest does not list exactly the labels to cover")
    base = str((args.base or repo).resolve())
    tasks = [(lb, str(manifest_path), base) for lb in labels]
    if args.jobs > 1:
        from concurrent.futures import ProcessPoolExecutor

        with ProcessPoolExecutor(max_workers=args.jobs) as pool:
            results = list(pool.map(worker, tasks))
    else:
        results = [worker(t) for t in tasks]
    table_path = args.hash_table.resolve()
    table = json.loads(table_path.read_text())["layouts"]
    differences = []
    extra_checks = []
    checkpoints = {}
    for res in results:
        label, kind = res["label"], res["kind"]
        checkpoints[label] = {f"R{R}": {n: res["hashes"][f"R{R}"][n] for n in required(kind)}
                              for R in ROWS}
        for R in ROWS:
            for name in required(kind):
                theirs = table.get(label, {}).get(f"{name}|R{R}")
                if theirs != res["hashes"][f"R{R}"][name]:
                    differences.append({"label": label, "layout": name, "R": R,
                                        "auditor": res["hashes"][f"R{R}"][name],
                                        "implementer": theirs})
            theirs = table.get(label, {}).get(f"L-FREQ|R{R}")
            extra_checks.append({"label": label, "layout": "L-FREQ", "R": R,
                                 "equal": theirs == res["hashes"][f"R{R}"]["L-FREQ"]})
    verdict = "AGREE" if not differences else "DISAGREE"
    tool_sha = file_sha256(Path(__file__))
    confirmation = {
        "schema": "p7b-layout-confirmation-v1",
        "verdict": verdict,
        "tool": f"{TOOL}; sha256 {tool_sha}",
        "tool_sha256": tool_sha,
        "layout_stage_run_id": args.layout_run_id,
        "layout_hash_table_sha256": file_sha256(table_path),
        "rows": list(ROWS),
        "checkpoints": checkpoints,
        "differences": differences,
        "label": "independent engineering evidence; not Astra validation; not human approval",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(confirmation, indent=1, sort_keys=True) + "\n")
    detail = {
        "tool": TOOL,
        "tool_sha256": tool_sha,
        "python": sys.version,
        "identity_manifest": str(manifest_path),
        "identity_manifest_sha256": file_sha256(manifest_path),
        "hash_table": str(table_path),
        "verdict": verdict,
        "differences": differences,
        "l_freq_extra_check_all_equal": all(e["equal"] for e in extra_checks),
        "per_checkpoint": results,
        "wall_seconds": time.monotonic() - started,
        "jobs": args.jobs,
        "files_opened": "identity manifest, layout hash table, calibration.selected files only",
    }
    args.detail.parent.mkdir(parents=True, exist_ok=True)
    args.detail.write_text(json.dumps(detail, indent=1, sort_keys=True) + "\n")
    print(f"{verdict}: {len(results)} checkpoints, {len(differences)} differences, "
          f"L-FREQ extra check equal={detail['l_freq_extra_check_all_equal']}, "
          f"{detail['wall_seconds']:.1f} s wall, jobs={args.jobs}")
    return 0 if verdict == "AGREE" else 2


if __name__ == "__main__":
    os.environ.setdefault("PYTHONHASHSEED", "0")
    sys.exit(main())
