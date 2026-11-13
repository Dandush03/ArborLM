"""Self-checks of rev3_layouts.py on hand-built and random small affinities (auditor's own code)."""

import itertools
import random
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, __file__.rsplit("/", 1)[0])
import rev3_layouts as L  # noqa: E402


def brute_best_swap_exists(pages, A, group_of=None):
    base = L.within_page_affinity(pages, A)
    for P, Q in itertools.permutations(range(len(pages)), 2):
        for x in pages[P]:
            for y in pages[Q]:
                if group_of and group_of[x] != group_of[y]:
                    continue
                pg = [list(p) for p in pages]
                pg[P][pg[P].index(x)] = y
                pg[Q][pg[Q].index(y)] = x
                if L.within_page_affinity(pg, A) > base:
                    # only swaps the rule may consider: Q must hold a slot with affinity to x
                    if any(A.get(x, {}).get(z, 0) for z in pages[Q]):
                        return True
    return False


def rand_case(rng, n, density):
    A = {}
    for i in range(n):
        for j in range(i + 1, n):
            if rng.random() < density:
                v = rng.randint(1, 5)
                A.setdefault(i, {})[j] = v
                A.setdefault(j, {})[i] = v
    f = [rng.randint(0, 20) for _ in range(n)]
    for i in A:
        f[i] = max(f[i], 1)
    return A, f


def main():
    rng = random.Random(5)
    # 1. a case where refinement must make a specific swap
    # pages [0,1] [2,3]; A(0,2)=5 A(1,3)=5 A(0,1)=1 -> swap 1<->2 gives 10 > 1
    A = {0: {1: 1, 2: 5}, 1: {0: 1, 3: 5}, 2: {0: 5}, 3: {1: 5}}
    f = [4, 3, 2, 1]
    pages, info = L.refine([[0, 1], [2, 3]], A, f)
    # attempt 1 expected [[0, 2], [1, 3]] (my error: x=0 is visited first and swapping 0<->3
    # reaches the same objective 10; the rule takes it). Correct expectation:
    assert pages == [[3, 1], [2, 0]], pages
    print("specific swap:", pages, info)
    # 2. random cases: monotone objective, local optimum w.r.t. considered swaps on convergence
    nconv = 0
    for t in range(300):
        n = rng.choice([8, 12, 16, 24])
        R = rng.choice([2, 3, 4])
        n -= n % R
        A, f = rand_case(rng, n, rng.choice([0.1, 0.3, 0.6]))
        S = list(range(n))
        g = L.greedy_pages(S, R, f, A)
        before = L.within_page_affinity(g, A)
        out, info = L.refine(g, A, f)
        after = L.within_page_affinity(out, A)
        assert after >= before
        assert sorted(s for p in out for s in p) == S
        if info["converged"]:
            nconv += 1
            assert not brute_best_swap_exists(out, A), (t, out)
        # constrained: two groups
        gof = {s: (0 if s < n // 2 else 1) for s in S}
        if (n // 2) % R == 0:
            g2 = L.greedy_pages(S[: n // 2], R, f, A) + L.greedy_pages(S[n // 2:], R, f, A)
            o2, i2 = L.refine(g2, A, f, gof)
            assert all(len({gof[s] for s in p}) == 1 for p in o2)
            assert L.within_page_affinity(o2, A) >= L.within_page_affinity(g2, A)
            if i2["converged"]:
                assert not brute_best_swap_exists(o2, A, gof)
    print("random cases ok; converged", nconv, "of 300")
    # 3. zero affinity: greedy == frequency order; refine makes no swap
    f = [rng.randint(0, 9) for _ in range(L.SLOTS)]
    for R in (1, 2, 8, 32):
        pg, info = L.coax(R, f, {})
        assert [s for p in pg for s in p] == L.layout_freq(f) and info["swaps"] == 0
    print("zero affinity ok")
    # 4. partitions: distinct, covering, deterministic
    parts = [L.partition_groups(s) for s in (91601, 91602, 91603, 91604, 91605)]
    for p in parts:
        assert sorted(s for g in p for s in g) == list(range(L.SLOTS))
    assert len({tuple(tuple(sorted(g)) for g in p) for p in parts}) == 5
    print("partitions ok")


if __name__ == "__main__":
    main()
