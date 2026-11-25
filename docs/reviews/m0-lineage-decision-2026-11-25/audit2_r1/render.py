# ruff: noqa
"""Render items with auditor seeds through core.build_item (the registered builder path).
mode "reg": the registered builder as is.  mode "unc": the same builder with every heuristic-conditioned redraw disabled
(credit() patched to 0.0 in lineages_r1_new2, _rev2, _rev3), i.e. the plain sample of the lineage's rule.
Usage: render.py OUTDIR N_PER_LEVEL"""
import gzip
import json
import os
import random
import sys
from concurrent.futures import ProcessPoolExecutor

HERE = "/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/arborlm-consolidation-experiment-2b31c1/experiments/_scratch/m0_lineage_audit2_r1_20261125"
sys.path.insert(0, HERE)

REV = ["spatial_grid_walk_r2", "kinship_descendants_r3", "kinship_ancestor_r3", "equivalence_classes_r2", "elimination_bracket_r3",
       "containers_queue_line_r2", "categories_default_exceptions_r3", "conditional_threshold_rule_r3", "boolean_lights_r2",
       "graph_shortest_route_r2", "containers_stack_piles_r3", "categories_follow_r2", "topological_order_r2", "instant_runoff_r2",
       "stable_matching_r2"]
NEW = ["activity_selection", "mst_cost", "nim_xor", "minimax_tree", "venn_counting"]
T5 = ["conditional_decision_tree", "tracking_accounts", "spatial_relative_directions", "order_compare", "temporal_critical_path"]
UNC = ["kinship_descendants_r3", "kinship_ancestor_r3", "elimination_bracket_r3", "conditional_threshold_rule_r3", "containers_stack_piles_r3",
       "topological_order_r2", "instant_runoff_r2", "stable_matching_r2", "activity_selection", "mst_cost"]
JOBS = [(x, "reg") for x in REV + NEW + T5] + [(x, "unc") for x in UNC]


def work(args):
    lid, mode, outdir, n = args
    from registry import all_lineages
    from studies.m0 import core
    if mode == "unc":
        from studies.m0 import lineages_r1_new2, lineages_r1_rev2, lineages_r1_rev3
        for m in (lineages_r1_new2, lineages_r1_rev2, lineages_r1_rev3):
            m.credit = lambda p, it: 0.0
    lin = all_lineages()["R1." + lid]
    path = os.path.join(outdir, f"{lid}.{mode}.jsonl.gz")
    fails = 0
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        for level in range(7):
            rng = random.Random(core.derive_seed(20261125, "audit2", lin.id, mode, str(level)))
            for i in range(n):
                try:
                    it = core.build_item(lin, level, rng, "A", f"{lin.id}/audit2{mode}/L{level}/{i}")
                except RuntimeError:
                    fails += 1
                    continue
                fh.write(json.dumps({"id": it.id, "level": level, "q": it.question, "a": it.answer, "k": it.k, "t": it.answer_type, "s": it.structured}, sort_keys=True) + "\n")
    return lid, mode, fails


if __name__ == "__main__":
    outdir, n = sys.argv[1], int(sys.argv[2])
    os.makedirs(outdir, exist_ok=True)
    with ProcessPoolExecutor(max_workers=8) as ex:
        for lid, mode, fails in ex.map(work, [(a, b, outdir, n) for a, b in JOBS]):
            print(lid, mode, "build failures (500 consecutive retries):", fails, flush=True)
