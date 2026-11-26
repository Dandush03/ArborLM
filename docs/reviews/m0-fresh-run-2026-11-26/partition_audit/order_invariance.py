"""Input-order invariance of the implementer's partition() and of partition_audit.partition().

On the real map and candidate list, with non-registered seeds, permute the order of lineages (dict
insertion), links, borderline pairs and candidates, and flip the orientation of pairs; the full
JSON output of each implementation must be byte-identical to its unpermuted output.
Prints a SHA-256 of the implementer's output per seed so runs under different PYTHONHASHSEED can be
compared.
Usage: python order_invariance.py IMPL_PARTITION_PY MAP CANDIDATES
"""
import hashlib
import importlib.util
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import partition_audit as pa  # noqa: E402

SEEDS = [1, 2, 99, 123456789, 400005, 399999]


def main():
    ip, mp, cp = sys.argv[1:4]
    spec = importlib.util.spec_from_file_location("impl_p", ip)
    impl = importlib.util.module_from_spec(spec); spec.loader.exec_module(impl)
    d, le, links, bp = pa.load_map(mp)
    cands = pa.load_candidates(cp)
    rng = random.Random(5)
    bad = 0
    for s in SEEDS:
        assert s != 400004
        base_i = json.dumps(impl.partition(le, links, bp, cands, s), sort_keys=True)
        base_m = json.dumps(pa.partition(le, links, bp, cands, s), sort_keys=True)
        for _ in range(25):
            items = list(le.items()); rng.shuffle(items); le2 = dict(items)
            l2 = [tuple(reversed(x)) if rng.random() < .5 else x for x in links]; rng.shuffle(l2)
            b2 = [tuple(reversed(x)) if rng.random() < .5 else x for x in bp]; rng.shuffle(b2)
            c2 = list(cands); rng.shuffle(c2)
            bad += json.dumps(impl.partition(le2, l2, b2, c2, s), sort_keys=True) != base_i
            bad += json.dumps(pa.partition(le2, l2, b2, c2, s), sort_keys=True) != base_m
        print(s, "impl_out_sha256", hashlib.sha256(base_i.encode()).hexdigest()[:16],
              "mine_out_sha256", hashlib.sha256(base_m.encode()).hexdigest()[:16])
    print("PERMUTATION MISMATCHES:", bad, "of", len(SEEDS) * 25 * 2)


if __name__ == "__main__":
    main()
