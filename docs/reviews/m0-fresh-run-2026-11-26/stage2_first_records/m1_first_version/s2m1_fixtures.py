# ruff: noqa
"""M0 stage 2, evaluation M1: builder key against the final auditor's text-only second solver on a fresh fixture set.
Auditor's own script (arbor-auditor). Standard library plus the implementation worktree's generators (studies.m0.core,
studies.m0.lineages_m1_fix4) and the solver under test (final_m1/solve_text_a5.py). Computes no cheap-rule rate.
Fixture seed: int.from_bytes(sha256(b"400002|stage2-check|M1")[:8], "big"); not a run seed, not a dry-run seed.
Per lineage and level the stream is core.stream(FIXTURE_SEED, "stage2-check", "M1", lineage_id, str(level)); 50 items per level.
Run from the implementation worktree root:
  PYTHONHASHSEED=0 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. uv run --locked python <this> <out.json>"""
import hashlib, json, sys
from fractions import Fraction

FIXTURE_SEED = int.from_bytes(hashlib.sha256(b"400002|stage2-check|M1").digest()[:8], "big")
N = 50
SOLVER_DIR = "docs/reviews/m0-lineage-decision-2026-11-25/final_m1"
sys.path.insert(0, SOLVER_DIR)

from studies.m0.core import build_item, stream
from studies.m0.lineages_m1_fix4 import load_all
from solve_text_a5 import solve


def stem(lid):
    s = lid.split(".", 1)[1]
    for suf in ("_r4", "_r3", "_r2"):
        if s.endswith(suf):
            s = s[: -len(suf)]
    return s


def main(out):
    surv = json.load(open("studies/m0/manifests/survivor_list_of_record.json"))["evaluations"]["M1"]
    lins = {x.id: x for x in load_all()}
    missing = [i for i in surv if i not in lins]
    assert not missing, missing
    res = {}
    tot = {"items": 0, "mismatches": 0, "solver_errors": 0, "no_unique_answer": 0}
    for lid in sorted(surv):
        lin = lins[lid]
        r_l = {"items": 0, "mismatches": 0, "mismatch_ids": [], "solver_errors": 0, "error_ids": [], "no_unique_answer": 0, "no_unique_ids": [], "per_level_items": {}}
        for L in range(7):
            rng = stream(FIXTURE_SEED, "stage2-check", "M1", lid, str(L))
            for i in range(N):
                it = build_item(lin, L, rng, "A", f"s2m1/{lid}/L{L}/{i}")
                r_l["items"] += 1
                try:
                    v, iss = solve(stem(lid), it.question)
                except Exception as e:
                    r_l["solver_errors"] += 1
                    r_l["error_ids"].append([it.id, repr(e)[:200]])
                    continue
                if iss:
                    r_l["no_unique_answer"] += 1
                    r_l["no_unique_ids"].append([it.id, iss])
                if v != Fraction(it.answer):
                    r_l["mismatches"] += 1
                    r_l["mismatch_ids"].append([it.id, str(v), it.answer])
            r_l["per_level_items"][str(L)] = N
        res[lid] = r_l
        for k in tot:
            tot[k] += r_l[k]
        print(f"{lid}: items {r_l['items']} mismatches {r_l['mismatches']} solver_errors {r_l['solver_errors']} no_unique {r_l['no_unique_answer']}", flush=True)
    doc = {"fixture_seed": FIXTURE_SEED, "per_level": N, "stream_labels": ["stage2-check", "M1", "<lineage id>", "<level>"], "lineages": res, "totals": tot}
    with open(out, "w") as f:
        json.dump(doc, f, sort_keys=True, indent=2)
        f.write("\n")
    print("TOTAL", json.dumps(tot, sort_keys=True))
    print("FIXTURE_SEED", FIXTURE_SEED)


if __name__ == "__main__":
    main(sys.argv[1])
