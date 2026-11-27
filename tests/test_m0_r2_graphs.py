# ruff: noqa: E501
"""R2 batch 1, family graphs: mechanical checks and test-local brute-force cross-checks (not the registered second solvers)."""

from __future__ import annotations

import itertools

from studies.m0.core import ALL_LEVELS, build_item, stream
from studies.m0.lineages_r2_common import check_family_r2, load_batch1

LIN = {x.id: x for x in load_batch1()}


def items(lid: str, per: int = 40):  # type: ignore[no-untyped-def]
    for lv in ALL_LEVELS:
        r = stream(953806, "t", lid, str(lv))
        for i in range(per):
            yield build_item(LIN[lid], lv, r, "A", f"t/{lv}/{i}")


def test_family_checks() -> None:
    assert check_family_r2("graphs") == []


def test_cheapest_network_against_all_edge_subsets() -> None:
    for it in items("R2.cheapest_network", 4):
        towns, cables = it.structured["towns"], it.structured["cables"]
        if len(cables) > 14:
            continue
        best = None
        for mask in range(1 << len(cables)):
            sel = [cables[i] for i in range(len(cables)) if mask >> i & 1]
            comp = {t: t for t in towns}

            def find(x: str) -> str:
                while comp[x] != x:
                    x = comp[x]
                return x

            for a, b, _w in sel:
                comp[find(a)] = find(b)
            if len({find(t) for t in towns}) == 1:
                c = sum(w for _a, _b, w in sel)
                best = c if best is None else min(best, c)
        assert it.answer == str(best)


def test_deferred_acceptance_result_is_stable_and_proposer_optimal() -> None:
    for it in items("R2.deferred_acceptance_partner", 12):
        s = it.structured
        props, resps = s["proposers"], s["responders"]
        n = len(props)

        def stable_matchings() -> list[dict[str, str]]:
            out = []
            for perm in itertools.permutations(resps):
                m = dict(zip(props, perm, strict=True))
                inv = {v: k for k, v in m.items()}
                blocking = any(
                    s["prefs_p"][p].index(r) < s["prefs_p"][p].index(m[p]) and s["prefs_r"][r].index(p) < s["prefs_r"][r].index(inv[r])
                    for p in props for r in resps
                )
                if not blocking:
                    out.append(m)
            return out

        if n <= 5:
            ms = stable_matchings()
            assert ms
            # proposer-optimal: nobody in the first group does better in another stable matching
            best = {p: min((m[p] for m in ms), key=lambda r, p=p: s["prefs_p"][p].index(r)) for p in props}
            assert it.answer == best[s["who"]]
