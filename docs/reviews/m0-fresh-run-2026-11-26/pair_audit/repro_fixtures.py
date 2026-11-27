"""Pair audit: confirm the generation method reproduces the authoring fixtures and keys byte-for-byte as JSON records
(seed tag 'second-solver-fixtures', 40 per level, role 'second-solver-fixtures'), for all 82 lineages. Writes nothing; prints counts.
Run from the implementation worktree root with uv run --locked python (PYTHONHASHSEED=0, PYTHONPATH=.)."""
import hashlib, json, random, sys
sys.path.insert(0, "/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_pair_audit_20261126/deliver")
import importlib.util
spec = importlib.util.spec_from_file_location("gf", "/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_pair_audit_20261126/deliver/gen_fresh.py")
W = "/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/agent-a0c9d741ea96ce52f"
sys.path.insert(0, W)
from studies.m0.core import draw_items
src = open(spec.origin).read().split("def main():")[0]
ns = {}; exec(compile(src, "gen_fresh_head", "exec"), ns)  # auditor's own file: reuse lineage_map
F = "/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_second_solver_fixtures_20261126"
K = "/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_second_solver_keys_20261126"
surv = json.load(open(W + "/studies/m0/manifests/survivor_list_of_record.json"))["evaluations"]
tot = bad = 0
for ev in ("R1", "R2", "M1", "C1"):
    m = ns["lineage_map"](ev)
    for lid in surv[ev]:
        fx = [json.loads(l) for l in open(f"{F}/{ev}/{lid}/fixtures.jsonl")]
        ks = [json.loads(l) for l in open(f"{K}/{ev}/{lid}/keys.jsonl")]
        taken = set(); j = 0
        for lv in range(7):
            seed = int.from_bytes(hashlib.sha256(f"400002|second-solver-fixtures|{ev}|{lid}|{lv}".encode()).digest()[:8], "big")
            for i, it in enumerate(draw_items(m[lid], "A", lv, 40, random.Random(seed), taken, "second-solver-fixtures")):
                a = {"id": lid, "level": lv, "index": i, "question": it.question, "structured": json.loads(json.dumps(it.structured))}
                tot += 1
                if a != fx[j] or it.answer != ks[j]["key"] or (ks[j]["level"], ks[j]["index"]) != (lv, i):
                    bad += 1
                j += 1
print(f"reproduced {tot} authoring fixture items; differing from fixtures/keys: {bad}")
