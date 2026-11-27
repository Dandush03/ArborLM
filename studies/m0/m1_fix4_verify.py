# ruff: noqa: E501
"""M1 fix round 4: the implementer's existing second derivation (``m1_fix3_verify``) extended to the fix-4 builders. Implementer's self-check; NOT a second solver from a separate context (R-9), not independent review.

``verify(stem, structured)`` returns the answer string. Delegates to ``m1_fix3_verify.verify`` except where the fix-4 parameter ranges leave its search window: ``average_missing`` (marks up to 160) and ``slot_permutations``
(codes up to 9 digits: enumerated when small, otherwise by enumerating every allowed (first, last) pair and counting the middle fillings directly).
"""

from __future__ import annotations

import itertools
import math
from fractions import Fraction
from typing import Any

from studies.m0.m1_fix3_verify import verify as verify_fix3

ENUMERATE_LIMIT = 600_000


def verify(stem: str, s: dict[str, Any]) -> str:
    if stem == "average_missing":
        top = 400
        sols = [x for x in range(0, top + 1) if Fraction(sum(s["scores"]) + x, s["n"]) * 100 == s["mean_cents"]]
        if len(sols) != 1:
            raise ValueError(f"not unique: {sols[:5]}")
        return str(sols[0])
    if stem == "slot_permutations":
        from studies.m0.lineages_m1_fix3_b import _RULES_FIRST, _RULES_LAST

        digs, ln, rep = s["digits"], s["length"], s["repeat"]
        ok_first, ok_last = _RULES_FIRST[s["first"]], _RULES_LAST[s["last"]]
        n = len(digs)
        if (n**ln if rep else math.perm(n, ln)) <= ENUMERATE_LIMIT:  # every code, leading zeros allowed
            gen = itertools.product(digs, repeat=ln) if rep else itertools.permutations(digs, ln)
            return str(sum(1 for code in gen if ok_first(code[0]) and ok_last(code[-1])))
        total = 0
        for f in digs:
            for last in digs:
                if not (ok_first(f) and ok_last(last)):
                    continue
                if rep:
                    total += n ** (ln - 2)
                elif f != last:
                    total += math.perm(n - 2, ln - 2)
        return str(total)
    return verify_fix3(stem, s)
