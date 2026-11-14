"""Cross-check of the descriptive/sensitivity layout pieces not covered by gate (b), on three real
CALIBRATION traces (one per architecture): the windowed affinity A8 (ADR-0014 section 4 definition,
written here as a literal loop over ordered query pairs) against ``p7b_layout.window_affinity``, and
L-BCOAX / L-PCOAX-1 at R = 512 (group-level steps) and L-COAX8 / L-COAXg at R = 2 and 8 against the
implementer's builder. The auditor's side reuses tools/independent_layouts.py (greedy, refine) and
adds the group-level rule from the ADR text. Calibration files only. Auditor role.
"""

import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "docs/reviews/p7b-preflight-2026-11-13/tools"))
import independent_layouts as IL  # noqa: E402

LABELS = ["b102-o302-flat-s502", "b102-o302-fixed_tree-s502", "b102-o302-learned_tree-s502"]


def window_literal(flat, W=8, ctx=64):
    rows = [flat[q : q + 8] for q in range(0, len(flat), 8)]
    N: dict = {}
    for c in range(len(rows) // ctx):
        for t in range(ctx):
            for u in range(max(0, t - W), t + 1):
                for i in rows[c * ctx + t]:
                    for j in rows[c * ctx + u]:
                        if i != j:
                            N.setdefault(i, {})
                            N[i][j] = N[i].get(j, 0) + 1
    A: dict = {}
    for i, d in N.items():
        for j, v in d.items():
            A.setdefault(i, {})
            A[i][j] = A[i].get(j, 0) + v
            A.setdefault(j, {})
            A[j][i] = A[j].get(i, 0) + v
    return A


def group_level_512(groups, f, A, refine=True):
    gid = [0] * IL.SLOTS
    for g, mem in enumerate(groups):
        for s in mem:
            gid[s] = g
    fg = [sum(f[s] for s in g) for g in groups]
    Ag: dict = {}
    for i, d in A.items():
        for j, v in d.items():
            if gid[i] != gid[j]:
                Ag.setdefault(gid[i], {})
                Ag[gid[i]][gid[j]] = Ag[gid[i]].get(gid[j], 0) + v
    units = IL.greedy(list(range(len(groups))), 2, fg, Ag)
    if refine:
        units, _ = IL.refine(units, Ag, fg)
    return [[s for g in u for s in groups[g]] for u in units]


def main() -> int:
    sys.path.insert(0, str(REPO / "src"))
    from arborlm import p7b_core as core
    from arborlm import p7b_layout as L

    identity = core.load_identity(REPO)
    manifest = json.loads((REPO / core.IDENTITY_MANIFEST).read_text())
    out = {}
    for label in LABELS:
        t0 = time.monotonic()
        cal = IL.calibration_selected(manifest, label, REPO)
        f = IL.counts_of(cal)
        A0 = IL.same_query_affinity(cal)
        A8 = window_literal(cal)
        ct = L.CalibrationTrace.from_identity(identity, label)
        theirs8 = L.window_affinity(ct.selected)
        theirs0 = L.pair_affinity(ct.selected)
        res = {"A8_equal": A8 == theirs8, "A0_equal": A0 == theirs0}
        built, _ = L.build_layouts(ct, rows_list=(2, 8, 512))
        table = L.hash_table(built, rows_list=(2, 8, 512))
        kind = IL.parse(label)[3]
        mine = {}
        for R in (2, 8):
            mine[f"L-COAX8|R{R}"] = IL.canonical(IL.refine(IL.greedy(list(range(IL.SLOTS)), R, f, A8), A8, f)[0])
            mine[f"L-COAXg|R{R}"] = IL.canonical(IL.greedy(list(range(IL.SLOTS)), R, f, A0))
        mine["L-COAX|R512"] = IL.canonical(IL.refine(IL.greedy(list(range(IL.SLOTS)), 512, f, A0), A0, f)[0])
        mine["L-PCOAX-1|R512"] = IL.canonical(group_level_512(IL.partition(91601), f, A0))
        if kind != "flat":
            mine["L-BCOAX|R512"] = IL.canonical(group_level_512(IL.branches(), f, A0))
            mine["L-BCOAXg|R512"] = IL.canonical(group_level_512(IL.branches(), f, A0, refine=False))
            for R in (2, 8):
                mine[f"L-BCOAX8|R{R}"] = IL.canonical(IL.constrained(IL.branches(), R, f, A8)[0])
        res["layout_hash_equal"] = {k: table.get(k) == v for k, v in mine.items()}
        res["seconds"] = time.monotonic() - t0
        out[label] = res
    print(json.dumps(out, indent=1))
    ok = all(r["A8_equal"] and r["A0_equal"] and all(r["layout_hash_equal"].values()) for r in out.values())
    print("SENSITIVITY CROSS-CHECK", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
