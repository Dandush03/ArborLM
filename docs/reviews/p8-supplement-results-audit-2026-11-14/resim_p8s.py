"""Auditor's independent re-simulation of the five ADR-0016 supplement cells (task 2).

For each of b101-o301-s601-C04, b101-o301-s601-C05, b101-o301-s602-C04, b101-o301-s602-C05,
b102-o302-s601-C05 and each panel (A, B):

  * reads the raw trace binaries of evaluation run P8E-...ab076488 with ``struct`` (hash-checked
    against eval.json);
  * checks the ADR-0016 section 3 precondition (exactly 8 non-zero counts, each == Q) and, separately,
    that every query's set is the same set S; checks the identity null equals the trace as sets;
  * rebuilds every layout from the calibration trace only with the auditor's own P7-B layout tool
    (``docs/reviews/p7b-preflight-2026-11-13/tools/independent_layouts.py``, hash-pinned, standard
    library only) and adds L-ID (identity) and L-FREQ; compares canonical hashes with the record's
    hash table, page membership with the run's ``layouts.int16.bin`` and with the failed P8S cell's
    ``layouts.int16.bin``, and the refinement meta;
  * re-simulates every recorded configuration (actual under every layout; order-shuffled and the
    three nulls under L-FREQ and L-COAX; R=2/C=32 and R=8/C=8; asc and desc) with the auditor's own
    LRU (``independent_resim.py``, hash-pinned) and the page statistics re-typed here;
  * recomputes temporal reuse and branch persistence (re-typed from ADR-0015 section 7.1);
  * compares every leaf of ``panels.<P>`` (and the layout meta/hash table) of the run's sim.json.

The only ``arborlm`` import is ``arborlm.p7a_core.query_order`` (registered order-shuffle permutation
indices), exactly as in the auditor's P8 results audit. Nothing from ``supplements.p8s`` is imported.

Usage (repository root):
  uv run --locked python -I docs/reviews/p8-supplement-results-audit-2026-11-14/resim_p8s.py OUT.json
Auditor tool (Claude Opus 5.5). Not Astra validation, not human approval.
"""

import hashlib
import importlib.util
import json
import math
import struct
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
EXP = Path("/Users/daniellaloush/dandush03/ArborLM/experiments")
EVAL = EXP / "P8E-20261114T043753008527Z-ab07648862054617b63d9e4d83e5407f"
SUP = EXP / "P8SUP-20261114T144104227089Z-fbfb3d18513749b081f9cdd93f22ad81"
REGSIM = EXP / "P8S-20261114T043952694180Z-088e6814edcd465894aebd125d53ddc3"
FIVE = ("b101-o301-s601-C04", "b101-o301-s601-C05", "b101-o301-s602-C04", "b101-o301-s602-C05", "b102-o302-s601-C05")
TOOLS = ROOT / "docs/reviews/p7b-preflight-2026-11-13/tools"
PIN = {
    "independent_layouts.py": "bfb21a577f03b4643caf418b99f04bab59b7c2f2de1eb324effb63bae10477b9",
    "independent_resim.py": "4e53ebbce18418393e97cfba6f595cc419cf3fd2691c4704b901a448a38f02f1",
}
SLOTS, TOP, CONTEXT, WINDOW = 4096, 8, 64, 8
CAP = {2: 32, 8: 8}
NULL_SEEDS = {"A": (91331, 91332, 91333), "B": (91341, 91342, 91343)}
PARENTS = ((101, 301), (102, 302), (103, 303))
SEEDS = (601, 602)
PCOAX = tuple(f"L-PCOAX-{i}" for i in range(1, 6))


def load_tool(name: str):
    path = TOOLS / name
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != PIN[name]:
        raise SystemExit(f"{name}: sha256 {digest} differs from the pinned hash")
    spec = importlib.util.spec_from_file_location(name[:-3], path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name[:-3]] = mod
    spec.loader.exec_module(mod)
    return mod


sys.path.insert(0, str(TOOLS))
IL = load_tool("independent_layouts.py")
IR = load_tool("independent_resim.py")
from arborlm.p7a_core import query_order  # noqa: E402  (registered permutation indices only)


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def read_rows(path: Path, code: str, shape: list[int], want: str) -> list[list[int]]:
    raw = path.read_bytes()
    if sha(raw) != want:
        raise SystemExit(f"{path}: sha256 differs from eval.json")
    n, w = shape
    vals = struct.unpack("<" + code * (n * w), raw)
    return [list(vals[i * w:(i + 1) * w]) for i in range(n)]


def cell_index(label: str) -> int:
    b, o, s, c = label.split("-")
    p = [x[0] for x in PARENTS].index(int(b[1:]))
    return 20 * p + 10 * SEEDS.index(int(s[1:])) + int(c[1:]) - 1


def counts(rows: list[list[int]]) -> list[int]:
    f = [0] * SLOTS
    for r in rows:
        for s in r:
            f[s] += 1
    return f


def pages_of(order: list[int], R: int) -> list[list[int]]:
    return [order[k:k + R] for k in range(0, SLOTS, R)]


def stats(q: list[tuple[int, ...]]) -> dict:
    hist = [0] * TOP
    seen: set[int] = set()
    first_half = None
    warm = len(q) // 2
    for i, p in enumerate(q):
        hist[len(p) - 1] += 1
        seen.update(p)
        if i + 1 == warm:
            first_half = len(seen)
    return {"distinct_first_half": first_half, "distinct_stream": len(seen), "hist": hist,
            "pages_sum": sum((i + 1) * c for i, c in enumerate(hist))}


def temporal_reuse(rows: list[list[int]]) -> dict:
    hits = counted = 0
    for b in range(0, len(rows), CONTEXT):
        for t in range(1, CONTEXT):
            prev = set()
            for u in range(max(0, t - WINDOW), t):
                prev |= set(rows[b + u])
            hits += sum(1 for s in rows[b + t] if s in prev)
            counted += 1
    return {"hits": hits, "queries_counted": counted, "slots_per_query": TOP,
            "value": hits / (TOP * counted), "window": WINDOW}


def persistence(br: list[list[int]]) -> dict:
    st = sp = n = 0
    for b in range(0, len(br), CONTEXT):
        for t in range(1, CONTEXT):
            a, c = br[b + t - 1], br[b + t]
            n += 1
            st += a[0] == c[0]
            sp += set(a) == set(c)
    return {"pairs": n, "same_top": st, "same_pair": sp, "top_fraction": st / n, "pair_fraction": sp / n}


def entropy(f: list[int]) -> float:
    tot = sum(f)
    return -math.fsum((c / tot) * math.log(c / tot) for c in f if c)


def group(q: list[tuple[int, ...]], R: int) -> dict:
    st = stats(q)
    return {"stats": st, "by_c": {str(CAP[R]): {t: IR.lru(q, CAP[R], t) for t in ("asc", "desc")}}}


def leaves(x, p=""):
    if isinstance(x, dict):
        for k, v in x.items():
            yield from leaves(v, f"{p}.{k}" if p else k)
    elif isinstance(x, list) and x and isinstance(x[0], dict | list):
        for i, v in enumerate(x):
            yield from leaves(v, f"{p}[{i}]")
    else:
        yield p, x


def compare(mine: dict, rec: dict, where: str, out: dict) -> None:
    lm, lr = dict(leaves(mine)), dict(leaves(rec))
    for k, v in lm.items():
        if k not in lr:
            out["missing_in_record"].append(f"{where}:{k}")
            continue
        r = lr[k]
        out["compared"] += 1
        same = (v == r) and (type(v) is type(r) or {type(v), type(r)} <= {int, float})
        if isinstance(v, float) or isinstance(r, float):
            d = abs(float(v) - float(r))
            out["max_abs_float_diff"] = max(out["max_abs_float_diff"], d)
            if d != 0.0:
                out["float_nonzero_diffs"].append(f"{where}:{k} mine={v!r} rec={r!r}")
            same = d <= 1e-12
        if not same:
            out["differences"].append(f"{where}:{k} mine={v!r} rec={r!r}")
    for k in lr:
        if k not in lm:
            out["not_recomputed"].append(f"{where}:{k}")


def main() -> int:
    t0 = time.monotonic()
    out = {"compared": 0, "differences": [], "missing_in_record": [], "not_recomputed": [],
           "max_abs_float_diff": 0.0, "float_nonzero_diffs": [], "cells": {}}
    pred = {str(i): {"checked": 0, "violations": []} for i in (1, 2, 3, 4, 6, 7)}
    for label in FIVE:
        cd = EVAL / "cells" / label
        ev = json.loads((cd / "eval.json").read_text())
        rec = json.loads((SUP / "cells" / label / "sim.json").read_text())
        kind = ev["variant"]
        tree = kind != "flat"
        ci = cell_index(label)
        info: dict = {"kind": kind, "cell_index": ci, "cell_index_recorded": rec["cell_index"]}
        if ci != rec["cell_index"]:
            out["differences"].append(f"{label}: cell_index {ci} vs {rec['cell_index']}")
        if sha((cd / "eval.json").read_bytes()) != rec["eval_json_sha256"]:
            out["differences"].append(f"{label}: eval_json_sha256")

        def trace(name: str):
            fl = ev["traces"][name]["files"]
            sel = read_rows(cd / fl["selected"]["file"], "h", fl["selected"]["shape"], fl["selected"]["sha256"])
            br = None
            if fl.get("branches"):
                br = read_rows(cd / fl["branches"]["file"], "b", fl["branches"]["shape"], fl["branches"]["sha256"])
            return sel, br, fl

        cal, cal_br, cal_files = trace("calibration")
        if cal_files != rec["calibration_files"]:
            out["differences"].append(f"{label}: calibration_files")
        f = counts(cal)
        flat = [v for r in cal for v in r]
        A = IL.same_query_affinity(flat)
        # layouts (calibration only)
        orders: dict[str, list[int]] = {"L-ID": list(range(SLOTS)),
                                        "L-FREQ": sorted(range(SLOTS), key=lambda s: (-f[s], s))}
        meta_ref: dict = {}
        parts = {f"L-PCOAX-{i + 1}": IL.partition(sd) for i, sd in enumerate(IL.PARTITION_SEEDS)}
        built_pages: dict[str, list[list[int]]] = {}
        for R in (2, 8):
            pg, inf = IL.unconstrained(R, f, A)
            built_pages[f"L-COAX|R{R}"] = pg
            meta_ref[f"L-COAX|R{R}"] = inf
            for name, groups in parts.items():
                pg, inf = IL.constrained(groups, R, f, A)
                built_pages[f"{name}|R{R}"] = pg
                meta_ref[f"{name}|R{R}"] = inf
            if tree:
                pg, inf = IL.constrained(IL.branches(), R, f, A)
                built_pages[f"L-BCOAX|R{R}"] = pg
                meta_ref[f"L-BCOAX|R{R}"] = inf

        def pages(name: str, R: int) -> list[list[int]]:
            if name in ("L-ID", "L-FREQ"):
                return pages_of(orders[name], R)
            return built_pages[f"{name}|R{R}"]

        names = ["L-ID", "L-FREQ", "L-COAX", *PCOAX] + (["L-BCOAX"] if tree else [])
        my_hash = {f"{n}|R{R}": IL.canonical(pages(n, R)) for n in names for R in (2, 8)}
        my_layouts = {
            "hash_table": my_hash,
            "meta": {
                "affinity_nonzero_entries": sum(len(v) for v in A.values()),
                "calibration_counts_sha256": sha(struct.pack(f"<{SLOTS}I", *f)),
                "unique_selected_slots": sum(1 for c in f if c),
                "refinement": {k: {"converged": v["converged"], "passes": v["passes"], "swaps": v["swaps"],
                                   "within_page_affinity_before": v["within_before"],
                                   "within_page_affinity_after": v["within_after"]} for k, v in meta_ref.items()},
            },
        }
        compare(my_layouts, rec["layouts"], f"{label}:layouts", out)
        # layout files: run directory and failed P8S directory
        lf = {}
        for tag, path in (("supplement_run", SUP / "cells" / label / "layouts.int16.bin"),
                          ("failed_P8S_dir", REGSIM / "cells" / label / "layouts.int16.bin")):
            raw = path.read_bytes()
            lf[tag] = sha(raw)
            vals = struct.unpack(f"<{len(raw) // 2}h", raw)
            bad = []
            for e in rec["layouts"]["index"]:
                order = list(vals[e["bytes_offset"] // 2: e["bytes_offset"] // 2 + SLOTS])
                Rs = (2, 8) if e["rows"] is None else (e["rows"],)
                for R in Rs:
                    theirs = [sorted(p) for p in pages_of(order, R)]
                    ours = [sorted(p) for p in pages(e["name"], R)]
                    out["compared"] += 1
                    if theirs != ours:
                        bad.append(f"{e['name']}|R{R}")
            if bad:
                out["differences"].append(f"{label}:{tag}: page membership differs {bad}")
        if lf["supplement_run"] != rec["layouts"]["file_sha256"] or lf["failed_P8S_dir"] != lf["supplement_run"]:
            out["differences"].append(f"{label}: layout file hashes {lf} vs {rec['layouts']['file_sha256']}")
        out["compared"] += 1
        info["layout_file_sha256"] = lf
        reorder = query_order("order_shuffled", 32768)
        if sorted(reorder) != list(range(32768)):
            raise SystemExit("query_order is not a permutation")
        for panel in ("A", "B"):
            sel, br, files = trace(panel)
            Q = len(sel)
            c = counts(sel)
            nz = [s for s in range(SLOTS) if c[s]]
            precond = len(nz) == 8 and all(c[s] == Q for s in nz)
            S = sorted(nz)
            all_same = all(sorted(r) == S for r in sel)
            null = [list(S) for _ in range(Q)]
            identity_equals_trace = all(set(a) == set(b) for a, b in zip(null, sel))
            nsha = sha(struct.pack(f"<{Q * TOP}h", *[v for r in null for v in r]))
            info[f"panel_{panel}"] = {"precondition": precond, "every_query_same_set": all_same,
                                      "identity_null_equals_trace_as_sets": identity_equals_trace,
                                      "S": S, "null_sha256": nsha}
            pre_rec = rec["supplement_null_preconditions"][panel]
            compare({"holds": precond, "nonzero_slots": len(nz), "queries": Q, "slots": S, "reasons": []},
                    pre_rec, f"{label}:{panel}:precondition", out)
            shuffled_rows = [sel[i] for i in reorder]
            streams_rows = {"actual": sel, "order_shuffled": shuffled_rows, "null_1": null, "null_2": null, "null_3": null}
            my_streams: dict = {s: {} for s in streams_rows}
            for R in (2, 8):
                for name in names:
                    pg = pages(name, R)
                    for s, rows in streams_rows.items():
                        if s != "actual" and name not in ("L-FREQ", "L-COAX"):
                            continue
                        q = IR.page_tuples(rows, pg, R)
                        my_streams[s][f"{name}|R{R}"] = group(q, R)
            fe = entropy(c)
            mine_panel = {
                "kind": kind, "label": label, "stream": panel, "queries": Q,
                "evaluation_counts": {"unique_selected_slots": len(nz), "entropy_nats": fe,
                                      "effective_slots": math.exp(fe),
                                      "counts_sha256": sha(struct.pack(f"<{SLOTS}I", *c))},
                "streams": my_streams,
                "null_streams": [{"replicate_seed": s, "generator_seed": s * 1000 + ci,
                                  "stream_sha256": nsha, "precondition": True,
                                  "method": "single-set identity null (ADR-0016 §3)"} for s in NULL_SEEDS[panel]],
                "temporal_reuse": {s: temporal_reuse(r) for s, r in
                                   (("actual", sel), ("order_shuffled", shuffled_rows), ("null_1", null),
                                    ("null_2", null), ("null_3", null))},
                "branch_persistence": None if br is None else {
                    "actual": persistence(br), "order_shuffled": persistence([br[i] for i in reorder])},
                "trace_files": files,
            }
            rp = rec["panels"][panel]
            compare(mine_panel, rp, f"{label}:{panel}", out)
            if (rp["branch_persistence"] is None) != (br is None):
                out["differences"].append(f"{label}:{panel}: branch_persistence presence")
            # predictions 1, 2, 3, 4, 6, 7 on MY recomputation
            for s, g in my_streams.items():
                for key, grp in g.items():
                    dist = grp["stats"]["distinct_stream"]
                    for C, ties in grp["by_c"].items():
                        for tie, cnt in ties.items():
                            if s == "actual":
                                pred["1"]["checked"] += 1
                                if cnt["misses_warm"] - cnt["first_touch_warm"] != 0:
                                    pred["1"]["violations"].append(f"{label}:{panel}:{key}:{tie}")
                            pred["6"]["checked"] += 1
                            if not (cnt["misses_warm"] == cnt["first_touch_warm"] == 0
                                    and cnt["misses_all"] == cnt["first_touch_all"] == dist <= 8):
                                pred["6"]["violations"].append(f"{label}:{panel}:{s}:{key}:{tie}")
                    if s != "actual":
                        pred["2"]["checked"] += 1
                        if grp != my_streams["actual"][key]:
                            pred["2"]["violations"].append(f"{label}:{panel}:{s}:{key}")
            tr = mine_panel["temporal_reuse"]
            nm = sum(tr[f"null_{k}"]["value"] for k in (1, 2, 3)) / 3
            pred["3"]["checked"] += 1
            if tr["actual"]["value"] / nm != 1.0:
                pred["3"]["violations"].append(f"{label}:{panel}")
            for s in ("order_shuffled", "null_1", "null_2", "null_3"):
                pred["2"]["checked"] += 1
                if tr[s] != tr["actual"]:
                    pred["2"]["violations"].append(f"{label}:{panel}:temporal_reuse:{s}")
            for R in (2, 8):
                for tie in ("asc", "desc"):
                    pred["4"]["checked"] += 1
                    ms = []
                    for k in (1, 2, 3):
                        cnt = my_streams[f"null_{k}"][f"L-FREQ|R{R}"]["by_c"][str(CAP[R])][tie]
                        ms.append((cnt["misses_warm"] - cnt["first_touch_warm"]) / (Q - Q // 2))
                    if not sum(ms) / 3 < 0.05:
                        pred["4"]["violations"].append(f"{label}:{panel}:R{R}:{tie}")
            pred["7"]["checked"] += 1
            if len({d["stream_sha256"] for d in rp["null_streams"]}) != 1:
                pred["7"]["violations"].append(f"{label}:{panel}")
        out["cells"][label] = info
    out["predictions_recomputed"] = {k: {"checked": v["checked"], "violations": v["violations"],
                                         "holds": not v["violations"]} for k, v in pred.items()}
    out["seconds"] = time.monotonic() - t0
    Path(sys.argv[1]).write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps({k: (v if not isinstance(v, list) else len(v)) for k, v in out.items() if k != "cells"}, indent=1, ensure_ascii=False))
    print({k: v["holds"] for k, v in out["predictions_recomputed"].items()})
    return 0 if not out["differences"] else 1


if __name__ == "__main__":
    sys.exit(main())
