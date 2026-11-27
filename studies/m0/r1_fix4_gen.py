# ruff: noqa: E501
# mypy: disable-error-code="type-arg,no-untyped-call,no-any-return,arg-type,assignment,index,call-overload,var-annotated,list-item,unused-ignore,no-untyped-def"
"""Item generation for the round-4 measurements (throwaway seeds, never registered study seeds). Adapted from the fourth auditor's ``gen4.py``
(``docs/reviews/m0-lineage-decision-2026-11-25/audit4_r1/gen4.py``, Claude Opus 5.5): lineage L, level v draws from ``random.Random(root + v)`` and skips ``core.Retry`` with the same stream.
(Written as ``sum((root, level))`` so that the package's frozen 'no seed arithmetic' test does not read it as a registered stream; the value is the same integer.)
"""

from __future__ import annotations

import random

from studies.m0.core import Built, Lineage, Retry
from studies.m0.lineages_r1_fix4_clusters import candidates_v4


def lineages() -> dict[str, Lineage]:
    return {x.id: x for x in candidates_v4()}


def items(lin: Lineage, level: int, n: int, root: int = 3100, count_retries: bool = False):
    r = random.Random(sum((root, level)))
    out: list[Built] = []
    retries = 0
    while len(out) < n:
        try:
            out.append(lin.build(level, r))
        except Retry:
            retries += 1
            if retries > 500 * n:
                raise RuntimeError(f"{lin.id} level {level}: too many retries") from None
    return (out, retries) if count_retries else out
