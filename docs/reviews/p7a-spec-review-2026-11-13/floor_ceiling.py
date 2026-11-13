"""Auditor floor/ceiling estimate for ADR-0013 from the published P5 selection histograms.

Reads only results/p5-2026-11-13/<cell>/result.json (field final.retrieval.selected_slot_counts,
final.retrieval.router.*). No model, checkpoint or trace is used. Standard library only.

For each of the 81 memory cells (27 flat, 27 fixed_tree, 27 learned_tree) and each page size
R (rows per page), report how many pages hold the slots accounting for 90%, 99% and 100% of
the 262,144 evaluation-panel selections:

  * FREQ-oracle: slots packed by descending EVALUATION count (ties ascending slot ID). This is a
    lower bound for ADR-0013 L-FREQ, which is fitted on the calibration stream instead.
  * L-ID: slot s on page floor(s / R); pages ranked by their selection mass.

and compare with the registered cache capacities, which in every geometry and block size equal
512 / 1,024 / 2,048 rows (12.5 / 25 / 50% of 4,096 rows).

Run: python3 -I floor_ceiling.py <repo>/results/p5-2026-11-13
"""

import json
import math
import statistics
import sys
from pathlib import Path

ARCHS = ("flat", "fixed_tree", "learned_tree")
# (label, rows per page)
GRANULARITIES = (
    ("actual 4KiB", 32),
    ("actual 16KiB", 128),
    ("actual 64KiB", 512),
    ("hyp 4KiB", 2),
    ("hyp 16KiB", 8),
    ("hyp 64KiB", 32),
)
CACHE_ROWS = (512, 1024, 2048)
FRACTIONS = (0.90, 0.99, 1.00)


def pages_to_cover(page_mass: list[int], total: int, fraction: float) -> int:
    need = math.ceil(fraction * total) if fraction < 1 else total
    acc = 0
    for i, m in enumerate(sorted(page_mass, reverse=True)):
        acc += m
        if acc >= need:
            return i + 1
    raise AssertionError


def slots_to_cover(counts: list[int], total: int, fraction: float) -> int:
    need = math.ceil(fraction * total) if fraction < 1 else total
    acc = 0
    for i, c in enumerate(sorted(counts, reverse=True)):
        acc += c
        if acc >= need:
            return i + 1
    raise AssertionError


def summarize(values: list[float]) -> str:
    return (
        f"min {min(values):g} / median {statistics.median(values):g} / "
        f"mean {statistics.fmean(values):.4g} / max {max(values):g}"
    )


def main() -> None:
    root = Path(sys.argv[1])
    rows: dict[str, list[dict]] = {a: [] for a in ARCHS}
    for cell in sorted(root.iterdir()):
        parts = cell.name.split("-")
        if len(parts) != 4 or parts[2] not in ARCHS:
            continue
        record = json.loads((cell / "result.json").read_text())
        retrieval = record["final"]["retrieval"]
        counts = retrieval["selected_slot_counts"]
        total = sum(counts)
        assert len(counts) == 4096 and total == 32768 * 8, cell.name
        unique = sum(1 for c in counts if c)
        assert unique == retrieval["unique_selected_slots"], cell.name
        entry: dict = {
            "cell": cell.name,
            "unique": unique,
            "effective": retrieval["effective_selected_slots"],
            "hottest_fraction": retrieval["hottest_selected_slot_fraction"],
            "slots90": slots_to_cover(counts, total, 0.90),
            "slots99": slots_to_cover(counts, total, 0.99),
        }
        if parts[2] != "flat":
            router = retrieval["router"]
            sv = router["selected_value_branch_counts"]
            entry["branches_with_selections"] = sum(1 for c in sv if c)
            entry["top_branch_selection_share"] = max(sv) / total
            entry["nonzero_top1_branches"] = router["nonzero_top1_branches"]
        for label, r in GRANULARITIES:
            ordered = sorted(range(4096), key=lambda s: (-counts[s], s))
            freq_mass = [0] * (4096 // r)
            for pos, s in enumerate(ordered):
                freq_mass[pos // r] += counts[s]
            id_mass = [0] * (4096 // r)
            for s, c in enumerate(counts):
                id_mass[s // r] += c
            for f in FRACTIONS:
                entry[f"{label} FREQ {f:.2f}"] = pages_to_cover(freq_mass, total, f)
                entry[f"{label} LID {f:.2f}"] = pages_to_cover(id_mass, total, f)
        rows[parts[2]].append(entry)

    out = []
    out.append("Cache capacity in rows is 512 / 1024 / 2048 in every geometry and block size;")
    out.append("in pages: " + "; ".join(
        f"{label}: {'/'.join(str(c // r) for c in CACHE_ROWS)}" for label, r in GRANULARITIES))
    for arch in ARCHS:
        es = rows[arch]
        out.append("")
        out.append(f"== {arch}: {len(es)} cells ==")
        for key in ("unique", "effective", "hottest_fraction", "slots90", "slots99"):
            out.append(f"  {key}: {summarize([e[key] for e in es])}")
        if arch != "flat":
            for key in ("branches_with_selections", "top_branch_selection_share", "nonzero_top1_branches"):
                out.append(f"  {key}: {summarize([e[key] for e in es])}")
        for label, r in GRANULARITIES:
            cache_pages = CACHE_ROWS[0] // r
            for layout in ("FREQ", "LID"):
                parts_txt = []
                for f in FRACTIONS:
                    vals = [e[f"{label} {layout} {f:.2f}"] for e in es]
                    parts_txt.append(f"{int(f * 100)}%: {summarize(vals)}")
                fits = sum(1 for e in es if e[f"{label} {layout} 1.00"] <= cache_pages)
                fits99 = sum(1 for e in es if e[f"{label} {layout} 0.99"] <= cache_pages)
                out.append(
                    f"  {label} {layout:4s} pages | " + " | ".join(parts_txt)
                    + f" | cells whose 99% / 100% set fits the smallest cache ({cache_pages} pages): "
                    + f"{fits99}/{len(es)} / {fits}/{len(es)}"
                )
    print("\n".join(out))
    with open(Path(__file__).with_name("floor_ceiling.cells.json"), "w") as fh:
        json.dump(rows, fh, indent=1, sort_keys=True)


if __name__ == "__main__":
    main()
