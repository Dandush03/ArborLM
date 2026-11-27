# ruff: noqa
"""Cross-evaluation map (M0), step 1c (added after reading the audit overlap lists): render items of NOT REGISTERED lineages that
are members of SURVIVING strict clusters, since under the addendum's graph (section 3 item 1: nodes registered or not) such a member
can carry a cross-evaluation link for its whole cluster. Throwaway seeds random.Random(f"xeval-map-sample|{lid}|{level}").

Run: PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<impl worktree> uv run --locked --project <impl worktree> python s02b_unregistered_members_of_surviving_clusters.py > s02b_unregistered_members_of_surviving_clusters.out.txt
"""
import random


def main():
    from studies.m0.core import Retry, REGISTRY, _load_all
    from studies.m0.c1grammar import render
    from studies.m0.lineages_r1_fix4_clusters import candidates_v4
    import studies.m0.lineages_r1_fix3_d, studies.m0.lineages_r1_rev4  # noqa: F401  (registers the R1 kinship/category shapes)

    _load_all()
    byid = {x.id: x for ev in REGISTRY.values() for x in ev}
    byid.update({x.id: x for x in candidates_v4()})
    want = ["C1.loop_sum", "R1.kinship_ancestor_r4", "R1.kinship_cousins_r5", "R1.event_timeline_r6", "R1.spatial_relative_directions_r6",
            "R1.minimax_tree_r5", "R1.elimination_bracket_r5", "R1.attribute_rule_r5", "R1.one_culprit", "R1.conditional_chain_r5",
            "R2.count_letter", "M1.coins_r3"]
    for lid in want:
        lin = byid.get(lid)
        if lin is None:
            print(f"=== {lid}: not found by this loader\n")
            continue
        for lv in (0, 3):
            r = random.Random(f"xeval-map-sample|{lid}|{lv}")
            for _ in range(500):
                try:
                    b = lin.build(lv, r)
                    break
                except Retry:
                    continue
            q = b.question
            if lid.startswith("C1.") and isinstance(b.structured, dict) and "program" in b.structured:
                q = "[program]\n" + render(b.structured["program"])
            print(f"=== {lid} L{lv} (module {lin.build.__module__})  answer={b.answer!r}\n{q[:900]}\n")


if __name__ == "__main__":
    main()
