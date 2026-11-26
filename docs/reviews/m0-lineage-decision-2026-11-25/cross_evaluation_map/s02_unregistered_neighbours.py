# ruff: noqa
"""Cross-evaluation map (M0), step 1b: render one level-3 item of selected NOT REGISTERED lineages that look like neighbours
of a survivor in another evaluation (possible bridges in the addendum's graph, whose nodes include unregistered lineages).
Throwaway seeds random.Random(f"xeval-map-sample|{lid}|3"). Read-only on the implementation worktree.

Run: PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<impl worktree> uv run --locked --project <impl worktree> python s02_unregistered_neighbours.py > s02_unregistered_neighbours.out.txt
"""
import random

WANT = {
    "R2": ["R2.gcd_euclid", "R2.modular_power", "R2.permutation_power", "R2.prime_factor_query", "R2.stack_machine",
           "R2.bracket_match", "R2.to_base_wide", "R2.kth_smallest", "R2.count_letter", "R2.coin_change_min",
           "R2.multiples_between", "R2.max_subarray_sum", "R2.palindrome_check"],
    "C1": ["C1.bfs_queue", "C1.coin_change_table_f3", "C1.bubble_pass", "C1.partition_pass_f3", "C1.mirror_pointers",
           "C1.majority_vote_scan_f3", "C1.cellular_update_f3", "C1.string_pair_table", "C1.grid_path_table"],
}


def main():
    from studies.m0.r2_fix4_set import fix4_set
    from studies.m0.lineages_c1_fix4 import all_written
    from studies.m0.c1grammar import render
    from studies.m0.core import Retry

    S = {"R2": dict(fix4_set()), "C1": dict(all_written())}
    for ev, ids in WANT.items():
        for lid in ids:
            if lid not in S[ev]:
                print(f"=== {lid}: not in the fix-4 loader\n")
                continue
            lin = S[ev][lid]
            r = random.Random(f"xeval-map-sample|{lid}|3")
            for _ in range(500):
                try:
                    b = lin.build(3, r)
                    break
                except Retry:
                    continue
            q = b.question
            if ev == "C1" and isinstance(b.structured, dict) and "program" in b.structured:
                q = "[program]\n" + render(b.structured["program"])
            print(f"=== {lid} (module {lin.build.__module__})  answer={b.answer!r}\n{q[:1500]}\n")


if __name__ == "__main__":
    main()
