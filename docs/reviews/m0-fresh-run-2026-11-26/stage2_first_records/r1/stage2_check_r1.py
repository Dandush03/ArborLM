# ruff: noqa
"""M0 stage 2, evaluation R1: the auditor's own fixture check (second solver against builder key) and level-distinctness checks.

Written by the stage-2 auditor (arbor-auditor context, Claude Opus 5.5), 2026-11-26. Reads only: the survivor list of record,
the builders (studies/m0/, unchanged since 7cd0ac5a) through lineages_r1_fix4_clusters.registered_v4(), and the final R1
auditor's text-only solvers (final_r1/solvers_final.py, unchanged since b78e58b1). Computes no cheap-rule rate and runs no rule.

usage (from the implementation worktree root):
  PYTHONHASHSEED=0 PYTHONDONTWRITEBYTECODE=1 uv run --locked python <this> <outdir>

Fixture seed: int.from_bytes(sha256(b"400002|stage2-check|R1")[:8], "big") = 14961762383913329776 (asserted).
Per lineage x and level v the stream is random.Random(int.from_bytes(sha256("<seed>|<x>|<v>")[:8], "big")) (labels, never addition);
50 items per level; on core.Retry the builder is called again on the same stream (budget 500 x 50 retries).
Identity test (levels): for each lineage, every level is built from ONE shared stream seed derived with label "identity"
(sha256("<seed>|identity|<x>")), 20 items each; two levels with identical question sequences would be one generator.
"""
import hashlib, json, os, random, sys, unicodedata, re

W = os.getcwd()
assert os.path.isfile(os.path.join(W, "studies/m0/core.py")), "run from the implementation worktree root"
sys.path.insert(0, W)
SOLV_DIR = os.path.join(W, "docs/reviews/m0-lineage-decision-2026-11-25/final_r1")
sys.path.insert(0, SOLV_DIR)

from studies.m0.core import Retry  # noqa: E402
from studies.m0.lineages_r1_fix4_clusters import registered_v4  # noqa: E402
import solvers_final as SV  # noqa: E402

out = sys.argv[1]
os.makedirs(out, exist_ok=True)

SEED = int.from_bytes(hashlib.sha256(b"400002|stage2-check|R1").digest()[:8], "big")
assert SEED == 14961762383913329776, SEED
N = 50
N_ID = 20


def sub(*labels):
    return int.from_bytes(hashlib.sha256("|".join([str(SEED), *labels]).encode()).digest()[:8], "big")


def norm(t):
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", t).casefold()).strip()


def draw(lin, rng, n):
    items, retries = [], 0
    while len(items) < n:
        try:
            items.append(lin.build_lv(rng))
        except Retry:
            retries += 1
            if retries > 500 * n:
                raise RuntimeError("too many retries")
    return items, retries


surv = json.load(open(os.path.join(W, "studies/m0/manifests/survivor_list_of_record.json")))["evaluations"]["R1"]
assert len(surv) == 10, surv
allv4 = {x.id: x for x in registered_v4()}
missing = [s for s in surv if s not in allv4]
assert not missing, missing
uncovered = [s for s in surv if s not in SV.SOLVERS]

summary = {"fixture_seed": SEED, "items_per_level": N, "lineages": {}}
samples = []
with open(os.path.join(out, "fixtures_r1.jsonl"), "w") as fo:
    for lid in sorted(surv):
        lin = allv4[lid]
        rec = {"solver_covers": lid in SV.SOLVERS, "per_level": [], "mismatch_ids": [], "ambiguous_ids": [], "parse_ids": [], "retries": []}
        texts_by_level = []
        for lv in range(7):
            rng = random.Random(sub(lid, str(lv)))
            class _L:  # bind level
                pass
            lin_lv = _L(); lin_lv.build_lv = (lambda r, lv=lv, lin=lin: lin.build(lv, r))
            items, retries = draw(lin_lv, rng, N)
            rec["retries"].append(retries)
            c = {"n": 0, "agree": 0, "mismatch": 0, "ambiguous": 0, "parse": 0}
            texts_by_level.append({norm(b.question) for b in items})
            for i, b in enumerate(items):
                iid = f"{lid}|L{lv}|{i:02d}"
                c["n"] += 1
                if not rec["solver_covers"]:
                    st, a = "no_solver", None
                else:
                    try:
                        a, st = SV.SOLVERS[lid](b.question)
                    except SV.ParseError as e:
                        a, st = None, "parse:" + str(e)
                if st == "ok" and a == b.answer:
                    c["agree"] += 1; kind = "agree"
                elif st == "ok":
                    c["mismatch"] += 1; kind = "mismatch"; rec["mismatch_ids"].append(iid)
                elif st.startswith("parse"):
                    c["parse"] += 1; kind = "parse"; rec["parse_ids"].append(iid)
                else:
                    c["ambiguous"] += 1; kind = "ambiguous"; rec["ambiguous_ids"].append(iid)
                fo.write(json.dumps({"id": iid, "lineage": lid, "level": lv, "kind": kind, "key": b.answer, "solver": a, "status": st,
                                     "k": b.k, "answer_type": b.answer_type, "q_sha256": hashlib.sha256(b.question.encode()).hexdigest()}, sort_keys=True) + "\n")
                if i < 2:
                    samples.append(f"===== {iid} k={b.k} type={b.answer_type}\n{b.question}\nKEY: {b.answer!r}\n")
            rec["per_level"].append(c)
        # cross-level repeated normalised texts within the fixtures (descriptive)
        rec["cross_level_shared_texts"] = {f"{a}-{b}": len(texts_by_level[a] & texts_by_level[b]) for a in range(7) for b in range(a + 1, 7)}
        # identity test: one shared stream seed for every level
        seqs = []
        for lv in range(7):
            rng = random.Random(sub("identity", lid))
            class _L:
                pass
            lin_lv = _L(); lin_lv.build_lv = (lambda r, lv=lv, lin=lin: lin.build(lv, r))
            items, _ = draw(lin_lv, rng, N_ID)
            seqs.append(tuple(norm(b.question) for b in items))
        rec["identity_equal_level_pairs"] = [f"{a}-{b}" for a in range(7) for b in range(a + 1, 7) if seqs[a] == seqs[b]]
        tot = {k: sum(r[k] for r in rec["per_level"]) for k in rec["per_level"][0]}
        rec["totals"] = tot
        summary["lineages"][lid] = rec
        print(f"{lid:40s} covers={rec['solver_covers']} n={tot['n']} agree={tot['agree']} mismatch={tot['mismatch']} ambiguous={tot['ambiguous']} parse={tot['parse']} "
              f"cross_level_shared={sum(rec['cross_level_shared_texts'].values())} identity_equal={rec['identity_equal_level_pairs']} retries={rec['retries']}", flush=True)

summary["uncovered"] = uncovered
with open(os.path.join(out, "fixture_summary_r1.json"), "w") as f:
    json.dump(summary, f, sort_keys=True, indent=2); f.write("\n")
with open(os.path.join(out, "samples_r1.txt"), "w") as f:
    f.write("\n".join(samples))
print("seed", SEED, "uncovered", uncovered)
