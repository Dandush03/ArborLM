"""Pair audit: fresh items the solver authors never saw. Same builders and calls as the fixture builder's build.py
(lineage objects as loadall.py; core.draw_items(lin, "A", level, N, rng, taken, role); `taken` shared across the 7 levels of a lineage),
N = 200 per level, role "pair-audit", seed int.from_bytes(sha256(f"400002|pair-audit|{EVAL}|{lineage_id}|{level}").digest()[:8], "big").
If draw_items raises (fewer than N distinct items reachable) the shortfall is recorded and that level is redrawn from the same seed with
allow_short=True (taken restored to its state before the level). Writes work/items_<EVAL>.jsonl (with key) and deliver/gen_<EVAL>.log.
Run from the implementation worktree root:  PYTHONHASHSEED=0 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. uv run --locked python <this> <EVAL>"""
import hashlib, json, os, random, sys, time
W = "/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/agent-a0c9d741ea96ce52f"
sys.path.insert(0, W)
from studies.m0.core import draw_items

OUT = "/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_pair_audit_20261126"
N = int(os.environ.get("PAIR_AUDIT_N", "200"))


def lineage_map(ev):
    if ev == "R1":
        from studies.m0.lineages_r1_fix4_clusters import candidates_v4, registered_v4
        d = {x.id: x for x in candidates_v4()}
        d.update({x.id: x for x in registered_v4()})
        return d
    if ev == "R2":
        from studies.m0.r2_fix4_set import fix4_set
        return fix4_set()
    if ev == "M1":
        from studies.m0.lineages_m1_fix4 import load_registered
        return {x.id: x for x in load_registered()}
    if ev == "C1":
        from studies.m0.lineages_c1_fix4 import all_written
        return all_written()
    raise SystemExit("bad eval")


def seed_int(ev, lid, lv):
    return int.from_bytes(hashlib.sha256(f"400002|pair-audit|{ev}|{lid}|{lv}".encode()).digest()[:8], "big")


def main():
    ev = sys.argv[1]
    only = sys.argv[2:]  # optional lineage subset
    surv = json.load(open(W + "/studies/m0/manifests/survivor_list_of_record.json"))["evaluations"][ev]
    m = lineage_map(ev)
    suffix = ("_" + "_".join(x.split(".")[1] for x in only)) if only else ""
    items_path = f"{OUT}/work/items_{ev}{suffix}.jsonl"
    log_path = f"{OUT}/deliver/gen_{ev}{suffix}.log"
    with open(items_path, "x") as fo, open(log_path, "x") as fl:
        for lid in surv:
            if only and lid not in only:
                continue
            lin = m[lid]
            taken = set()
            t0 = time.time()
            for lv in range(7):
                seed = seed_int(ev, lid, lv)
                before = set(taken)
                try:
                    items = draw_items(lin, "A", lv, N, random.Random(seed), taken, "pair-audit")
                    short = ""
                except RuntimeError as e:
                    taken = before
                    items = draw_items(lin, "A", lv, N, random.Random(seed), taken, "pair-audit", allow_short=True)
                    short = f" SHORT({e})"
                for i, it in enumerate(items):
                    fo.write(json.dumps({"id": lid, "level": lv, "index": i, "question": it.question,
                                         "structured": json.loads(json.dumps(it.structured)), "key": it.answer}) + "\n")
                fl.write(f"{lid} L{lv} seed={seed} items={len(items)}{short}\n")
            fl.write(f"{lid} done {time.time() - t0:.1f}s\n")
            fl.flush()
            print(lid, f"{time.time() - t0:.1f}s", flush=True)


main()
