# ruff: noqa: E501
"""Builds the revision-2 bookkeeping for C1 batch 1: fixtures into a NEW directory, a SUPERSEDED note in the old one, the schema for the second-solver agent,
and the manifest. Run after ``c1_shortcut_check_rev2`` and ``c1_batch1_rev2_capacity`` have written their JSON under ``manifests/``:
``PYTHONHASHSEED=0 uv run --locked --offline python -m studies.m0.c1_batch1_rev2_build``. No threshold is registered here. Self-checked only.
"""

from __future__ import annotations

import hashlib
import inspect
import json
import platform
import subprocess
import time
from pathlib import Path

from studies.m0.c1grammar import render, run_isolated
from studies.m0.core import ALL_LEVELS, build_item, draw_items, stream
from studies.m0.lineages_c1_clusters import (
    DISAGREEMENTS,
    STRICT_GROUPS,
    STRICTEST_EXTRA,
    current_ids,
    current_strict_clusters,
    current_strictest_clusters,
    joined_family_groups,
    strict_clusters,
    strictest_clusters,
)
from studies.m0.lineages_c1_rev2 import NOT_REGISTERED, PROPOSED, SUPERSEDES, load_rev2
from studies.m0.solvers_c1 import c1_trace

ROOT = Path(__file__).resolve().parents[2]
M = ROOT / "studies" / "m0"
FIX2 = M / "fixtures" / "c1_batch1_rev2"
FIX1 = M / "fixtures" / "c1_batch1"
SCHEMA2 = M / "fixtures" / "C1_BATCH1_REV2_SCHEMA.md"
MANIFEST = M / "manifests" / "c1_batch1_rev2_manifest.json"
SEED = 953601


def write_fixtures(lins: list) -> dict[str, dict]:
    FIX2.mkdir(parents=True, exist_ok=True)
    out = {}
    for lin in lins:
        lines, progs, keys = [], [], []
        for lv in ALL_LEVELS:
            r = stream(SEED, "c1-rev2-fixture", lin.id, str(lv))
            for i, it in enumerate(draw_items(lin, "A", lv, 20, r, set(), "fixture")):
                lines.append(json.dumps({"id": f"{lin.id}/fixture/{lv}/{i}", "lineage": it.lineage, "level": it.level, "question": it.question, "structured": it.structured, "answer": it.answer, "answer_type": it.answer_type, "k": it.k, "proposed": lin.id in PROPOSED}, sort_keys=True, ensure_ascii=True))
                progs.append(render(it.structured["program"]))
                keys.append((it.answer, it.structured))
        first, second = run_isolated(progs), run_isolated(progs)  # every fixture item twice in fresh restricted processes
        bad = [i for i, ((a, s), x, y) in enumerate(zip(keys, first, second, strict=True)) if not (x["out"] == y["out"] == a == c1_trace(s))]
        text = "\n".join(lines) + "\n"
        (FIX2 / f"{lin.id}.jsonl").write_text(text)
        out[lin.id] = {"sha256": hashlib.sha256(text.encode()).hexdigest(), "items": len(lines), "isolated_runs_twice_and_second_solver_disagreements": len(bad)}
        assert not bad, (lin.id, bad[:3])
    return out


def write_superseded() -> None:
    lines = ["SUPERSEDED (C1 batch 1, revision 2). Nothing in this directory is edited or removed; the lineages below are superseded by the revised shapes in",
             "studies/m0/fixtures/c1_batch1_rev2/ (generators in studies/m0/lineages_c1_rev2.py). Written by studies/m0/c1_batch1_rev2_build.py.\n"]
    reasons = {
        "C1.cellular_update": "fixed accumulator name 'w' collides with the drawn names (audit: 4 fixtures, 3.7 % of weighted-shape draws print another quantity)",
        "C1.turtle_walk": "'count the F commands' is the key in 0.53 of items at level 1 and about 0.8 inside the distance shapes (audit)",
        "C1.bytecode_loop": "'sum of all arguments' is the key in 0.82-0.89 of the sum-of-arguments shape (audit)",
        "C1.merge_two_sorted": "partial-list shape = sorted(a + b) without the last element (0.50-0.57); the comparison count = len(a) + len(b) - 1 in 0.50-0.57 of its shape",
        "C1.sieve_marking": "count shape: ones at indices 0, 1 and at primes explain 0.36-0.50 of it",
        "C1.recursive_calls": "audit B6: shapes 'two' and 'tri' are the fib_like recurrence; split into fib_shapes_recursive (fib_like cluster) and recursive_calls_r2; space also widened",
        "C1.fast_power": "level-0 space thin; widened (shapes unchanged; formula-answerable status unchanged and reserved to the human lead)",
        "C1.circle_elimination": "level-0 space thin; widened (shapes unchanged)",
        "C1.majority_vote_scan": "its redraws (candidate neither first nor last; mode 25 %) were conditioned on heuristic outcomes (ruling R-1) and moved the tell to the elements next to the last (battery literal-position rule 0.85); the candidate-alone shape cannot be made tell-free by construction",
    }
    for new, old in sorted(SUPERSEDES.items(), key=lambda kv: kv[1]):
        lines.append(f"{old}  superseded by  {new}\n    reason: {reasons[old]}")
    (FIX1 / "SUPERSEDED.txt").write_text("\n".join(lines) + "\n")


def write_schema(lins: list) -> None:
    parts = ["# C1 batch 1, revision 2: structured-form schema for the second-solver agent\n",
             "Written by the implementer (Sonnet 5.5). Not a result; nothing here approves anything. Own checks only: not independent review, not Astra validation, not human approval. "
             "The interface, the key, the checker and the Python conventions are exactly those of `C1_BATCH1_SCHEMA.md` (same structured form `{\"program\": <tree>}`, same existing tree-walking second solver "
             "`solvers_c1.c1_trace`). Fixtures: `studies/m0/fixtures/c1_batch1_rev2/<lineage id>.jsonl`, 20 distinct items for each of the 7 levels; PROPOSED lineages are marked `\"proposed\": true` in every line.\n",
             "## Lineages\n"]
    for lin in lins:
        r = stream(SEED, "c1-rev2-schema-example", lin.id)
        it = build_item(lin, 2, r, "A", "example")
        sup = SUPERSEDES.get(lin.id)
        parts.append(f"### `{lin.id}` ({'PROPOSED additional shapes' if lin.id in PROPOSED else 'supersedes ' + sup if sup else 'revised'}; family {lin.family})\n\n{inspect.getdoc(lin.build)}\n")
        parts.append("Example (level 2):\n\n```\n" + it.question.split("\n\n")[1] + "\n```\n\nanswer: `" + it.answer + "`\n")
    parts.append("## NOT REGISTERED shapes (tell cannot be removed by construction)\n")
    parts += [f"- `{k}`: {v}" for k, v in sorted(NOT_REGISTERED.items())]
    SCHEMA2.write_text("\n".join(parts) + "\n")


def main() -> None:
    t0 = time.time()
    lins = load_rev2()
    fx = write_fixtures(lins)
    write_superseded()
    write_schema(lins)
    sc_path = M / "manifests" / "c1_batch1_rev2_shortcuts.json"
    cap_path = M / "manifests" / "c1_batch1_rev2_capacity_g20.json"
    sc = json.loads(sc_path.read_text())
    cap = json.loads(cap_path.read_text())
    base = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=ROOT, check=False).stdout.strip()
    manifest = {
        "batch": "c1_batch1_rev2", "base_commit": base, "environment": {"python": platform.python_version(), "platform": platform.platform(), "hash_seed": "PYTHONHASHSEED=0"},
        "note": "Fix round after the independent audit AUDIT_M0_C1_1 under lead rulings 2 (R-1 no redraw conditional on a heuristic's outcome; R-2 strict map; R-3 per-level shape measurement; R-5 structural capacity). No new lineage: revised shapes of existing lineages plus PROPOSED traced shapes. Self-checked only.",
        "commands": ["PYTHONHASHSEED=0 uv run --locked --offline python -m studies.m0.c1_batch1_rev2_capacity --g-part 20 --out studies/m0/manifests/c1_batch1_rev2_capacity_g20.json",
                     "PYTHONHASHSEED=0 uv run --locked --offline python -m studies.m0.c1_shortcut_check_rev2 --per-level 2000 --out studies/m0/manifests/c1_batch1_rev2_shortcuts.json",
                     "PYTHONHASHSEED=0 uv run --locked --offline python -m studies.m0.c1_batch1_rev2_build", "uv run --locked --offline pytest tests/test_m0_*.py"],
        "revised": [{"id": lin.id, "family": lin.family, "supersedes": SUPERSEDES.get(lin.id), "proposed": lin.id in PROPOSED, "fixture": fx[lin.id]} for lin in lins],
        "superseded_kept_on_file": sorted(set(SUPERSEDES.values())),
        "not_registered": NOT_REGISTERED,
        "clusters": {
            "strict_map_over_39": {"count": len(strict_clusters()), "groups": {k: list(v) for k, v in STRICT_GROUPS.items()}},
            "strictest_over_39": {"count": len(strictest_clusters()), "extra_groups": {k: list(v) for k, v in STRICTEST_EXTRA.items()}},
            "current_set": {"lineages": len(current_ids()), "strict_clusters": len(current_strict_clusters()), "strictest_clusters": len(current_strictest_clusters()), "joined_family_groups": [list(g) for g in joined_family_groups()]},
            "author_disagreements_not_unmerging": DISAGREEMENTS,
        },
        "capacity": {k: cap[k] for k in ("g_part", "lineages_written", "pools_per_part", "tuning_per_level", "factor", "demand_even", "demand_worst", "need_even", "need_worst", "cells_total", "cells_below_need_even", "below_need_even")},
        "shortcut_summary_core_levels": {lid: v["summary"]["core_1_5"] for lid, v in sorted(sc["lineages"].items())},
        "source_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(M.glob("*c1*rev2*.py")) + [M / "lineages_c1_clusters.py", M / "c1_shortcut_check.py", M / "lineages_c1_common.py", M / "c1_batch1_build.py"]},
        "seconds": round(time.time() - t0, 1),
    }
    MANIFEST.write_text(json.dumps(manifest, indent=1, sort_keys=True))
    print(json.dumps({"seconds": manifest["seconds"], "lineages": len(lins), "cells_below_need_even": cap["cells_below_need_even"]}))


if __name__ == "__main__":
    main()
