# ruff: noqa
"""Audit 4 (C1), step 6b: does keeping the drawn variable name 'count' un-renamed (the predecessor's KEEP list) split one skeleton?
K2 (literals blanked + executed path) of the OLD counter_list and cellular_update_r2 under my keep list and under the predecessor's.
Throwaway seed 61, 4,000 draws per level 2. Run from the audited worktree with uv run --locked --offline python <this>."""
import ast, hashlib, os, random, sys
sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.dirname(__file__))
import s6_capacity as S


def k2(src, keep):
    t = S.Blank().visit(S.rename(ast.parse(src), keep))
    return S.k2_of.__wrapped__(src) if False else hashlib.sha1((ast.dump(t) + "|" + S.k2_of(src).split("|")[-1]).encode()).hexdigest()


def main():
    from studies.m0.c1grammar import render
    from studies.m0.core import Retry
    allx = S.by_id()
    for lid in ("C1.counter_list", "C1.cellular_update_r2"):
        r = random.Random(61)
        new, old, withcount = set(), set(), 0
        n = 0
        while n < 4000:
            try:
                b = allx[lid].build(2, r)
            except Retry:
                continue
            n += 1
            src = render(b.structured["program"])
            # the line path is name independent; the skeleton is what the keep list changes
            path = S.k2_of(src)  # (my keep list) hash of skeleton+path
            new.add(path)
            t = S.Blank().visit(S.rename(ast.parse(src), S.KEEP_OLD))
            old.add(hashlib.sha1((ast.dump(t) + "|" + path).encode()).hexdigest())
            withcount += "count" in src
        print(lid, "L2 draws", n, "K2 my keep", len(new), "K2 predecessor keep", len(old), "items with a variable 'count'", withcount)


if __name__ == "__main__":
    main()
