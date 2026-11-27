# ruff: noqa
"""Audit 3 (C1), step 8: my own strict cluster map under "procedure = the program's algorithm", written from my reading of the generators
(before opening any author note), and its comparison with studies/m0/lineages_c1_clusters.py (imported ONLY to compare).

Rule I apply (strict): two lineages are one cluster when a solver who can trace one has the other's state-update rule, i.e. the same loop
skeleton and the same kind of state update, differing only in data, operators, the recurrence's coefficients or argument map, or what is
printed.  Connected components are taken.  Borderline pairs are listed apart ("strictest") and not merged.
Run from the audited worktree:  PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 uv run --locked --offline python a8_clusters.py
"""
import math, os, sys

sys.path.insert(0, os.getcwd())

CURRENT = ["C1.bfs_queue", "C1.binary_search", "C1.bracket_matching", "C1.bubble_pass", "C1.bytecode_loop_r2", "C1.cellular_update_r2",
           "C1.circle_elimination_r2", "C1.coin_change_table", "C1.cond_chain", "C1.counter_list", "C1.digit_peel", "C1.euclid_gcd", "C1.fast_power_r2",
           "C1.fib_like", "C1.fib_shapes_recursive", "C1.func_branch", "C1.func_compose", "C1.grid_path_table", "C1.insertion_sort", "C1.kadane_scan",
           "C1.list_build", "C1.loop_sum", "C1.majority_vote_scan_r2", "C1.merge_two_sorted_r2", "C1.minmax_track", "C1.mirror_pointers", "C1.nested_pairs",
           "C1.partition_pass", "C1.postfix_evaluation", "C1.recursive_calls_r2", "C1.run_length_scan", "C1.shared_lists", "C1.sieve_marking_r2", "C1.slices",
           "C1.string_build", "C1.string_methods", "C1.string_pair_table", "C1.turtle_walk_r2", "C1.union_find_links", "C1.while_counter"]
TRACED = {"C1.insertion_sort_traced": "C1.insertion_sort", "C1.fast_power_traced": "C1.fast_power_r2", "C1.euclid_gcd_traced": "C1.euclid_gcd",
          "C1.kadane_scan_traced": "C1.kadane_scan", "C1.bracket_matching_traced": "C1.bracket_matching"}

MERGES = [  # (a, b, reason)
    ("C1.loop_sum", "C1.string_build", "for over an index range, test i % m, fold into one accumulator (int vs str)"),
    ("C1.loop_sum", "C1.list_build", "for over an index range, evaluate an expression of i, fold (append then sum/max)"),
    ("C1.loop_sum", "C1.nested_pairs", "conditional accumulation over an index range; nested_pairs over a 2-D range (weakest member)"),
    ("C1.func_branch", "C1.func_compose", "substitute literal arguments into small non-recursive function bodies"),
    ("C1.slices", "C1.string_methods", "evaluate a chain of sequence operations on a literal (string_methods contains slices)"),
    ("C1.coin_change_table", "C1.string_pair_table", "fill a DP table cell by cell from earlier cells"),
    ("C1.coin_change_table", "C1.grid_path_table", "ways[a] += ways[a-c] is grid path-count best[j] += best[j-1]; grid max/min ~ LCS max(up,left)+local"),
    ("C1.euclid_gcd", "C1.cond_chain", "remainder vs subtractive Euclid on two variables"),
    ("C1.fib_like", "C1.fib_shapes_recursive", "same linear recurrence, iterative vs recursive"),
    ("C1.fib_shapes_recursive", "C1.recursive_calls_r2", "NEW vs map: recursive integer function, call tree expanded; split/mutual/listfold differ from two/tri only in the argument map and coefficients (as B4 merges different recurrences filled by one table method)"),
    ("C1.bytecode_loop_r2", "C1.turtle_walk_r2", "interpret a coded command list: fetch, dispatch by an if-chain, update a small state"),
    ("C1.bracket_matching", "C1.postfix_evaluation", "array stack with pointer: push on one token class, pop and act on the other"),
]
BORDERLINE = [
    ("C1.euclid_gcd", "C1.while_counter", "numeric while loops (map S1)"), ("C1.euclid_gcd", "C1.digit_peel", "map S1"), ("C1.euclid_gcd", "C1.fast_power_r2", "map S1"),
    ("C1.bubble_pass", "C1.insertion_sort", "in-place reordering (map S2)"), ("C1.bubble_pass", "C1.partition_pass", "map S2"),
    ("C1.mirror_pointers", "C1.run_length_scan", "string pointer scans (map S3)"),
    ("C1.postfix_evaluation", "C1.bytecode_loop_r2", "MINE: coded-instruction interpreters with randomly assigned op codes (stack vs accumulator)"),
    ("C1.kadane_scan", "C1.minmax_track", "MINE: running-best scan; kadane contains the minmax update"),
]


def components(ids, pairs):
    par = {i: i for i in ids}

    def f(x):
        while par[x] != x:
            x = par[x]
        return x

    for a, b, _ in pairs:
        if a in par and b in par:
            ra, rb = f(a), f(b)
            if ra != rb:
                par[max(ra, rb)] = min(ra, rb)
    out = {}
    for i in ids:
        out.setdefault(f(i), []).append(i)
    return {k: sorted(v) for k, v in sorted(out.items())}


def need(G):
    return 10 * (math.ceil(24000 / G) + 100)


def main():
    mine = components(CURRENT, MERGES)
    mine_strictest = components(CURRENT, MERGES + BORDERLINE)
    print("my strict clusters:", len(mine))
    for k, v in mine.items():
        print("  ", k, v)
    print("my strictest (+ map S1-S3 + my two borderline):", len(mine_strictest))
    print("my strict + map S1-S3 only:", len(components(CURRENT, MERGES + BORDERLINE[:6])))
    print("lenient (every lineage its own cluster):", len(CURRENT))
    from studies.m0 import lineages_c1_clusters as M
    ids = list(M.current_ids())
    assert sorted(ids) == sorted(CURRENT), (set(ids) ^ set(CURRENT))
    mp = M.current_strict_clusters()
    print("map strict:", len(mp), " map strictest:", len(M.current_strictest_clusters()))
    mine_of = {m: k for k, v in mine.items() for m in v}
    map_of = {m: k for k, v in mp.items() for m in v}
    dis = []
    for a in CURRENT:
        for b in CURRENT:
            if a < b and (mine_of[a] == mine_of[b]) != (map_of[a] == map_of[b]):
                dis.append((a, b, "same in mine" if mine_of[a] == mine_of[b] else "same in map"))
    print("pairwise disagreements:", len(dis))
    for d in dis:
        print("  ", d)
    print("traced shapes join:", {k: mine_of[v] for k, v in TRACED.items()})
    for nclu in (len(mine), len(mp), len(mine_strictest), 22, 23):
        g = nclu // 2
        print(f"clusters {nclu}: parts {g}/{nclu - g}; worst-case need at G={g}: {need(g)}; at G={nclu - g}: {need(nclu - g)}")
    print("need at G=20:", need(20), " even-spread (fix round) at G=20:", 10 * (math.ceil(24000 / 20 / 5) + 100))


if __name__ == "__main__":
    main()
