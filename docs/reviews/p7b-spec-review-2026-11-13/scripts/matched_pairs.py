"""How many registered (parent, seed) pairs are matched in utilization? Published P5 effective slots only.
Usage (repo root): .venv/bin/python -I docs/reviews/p7b-spec-review-2026-11-13/scripts/matched_pairs.py"""
import glob, json, os
P5 = "results/p5-2026-11-13"
eff = {}
for d in sorted(glob.glob(f"{P5}/b*-o*-*-s*")):
    lb = os.path.basename(d)
    b, o, *k, s = lb.split("-")
    k = "-".join(k)
    if k in ("flat", "fixed_tree", "learned_tree"):
        eff[(b, o, s, k)] = json.load(open(f"{d}/result.json"))["final"]["retrieval"]["effective_selected_slots"]
pairs = sorted({key[:3] for key in eff})
assert len(pairs) == 27
for K in ("fixed_tree", "learned_tree"):
    r = [eff[p + (K,)] / eff[p + ("flat",)] for p in pairs]
    print(K, "tree/flat eff ratio: min %.3f median %.3f max %.3f" % (min(r), sorted(r)[13], max(r)),
          "| pairs within +-10%%: %d, +-20%%: %d, tree >= flat: %d" % (sum(abs(x - 1) <= .1 for x in r), sum(abs(x - 1) <= .2 for x in r), sum(x >= 1 for x in r)))
