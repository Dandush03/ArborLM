# ruff: noqa: E501
# mypy: disable-error-code="type-arg,no-untyped-call,no-any-return,arg-type,assignment,index,call-overload,var-annotated,list-item,unused-ignore,no-untyped-def"
"""Fitted count-feature lookups (round 4). COPIED from the fourth auditor's ``feature_tells4.py`` and ``kept_tells4.py`` (``docs/reviews/m0-lineage-decision-2026-11-25/audit4_r1/``, Claude Opus 5.5, audit 4 of R1),
feature functions unchanged: a lookup table feature-value -> most frequent answer is fitted on one draw and scored on another; effect = accuracy - 1/k per level (closed answers only). Seed pairs as the auditor used them
(fit 8300 / test 8400 for the first group, 8500 / 8600 for the second). Edits by the round-4 implementer: the dictionaries are keyed by base id (so that the _r6 repaired shapes receive the rules written for their
_r5 / _r4 builders), the feature entries that return None (placeholders in the audit) and the shapes that are not in the round-4 set are not run, the output is rows for ``r1_fix4_table``.
The auditor's kinship_ancestor 'options in the child's own family tree' rule is not copied (that shape is dropped).
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from typing import Any

from studies.m0.core import Lineage
from studies.m0.r1_fix4_gen import items


def _kq(b):  # kind of the asked statement, from the text
    return re.search(r'Consider the statement: "(every|no|some)', b.question).group(1)


FEATS_1 = {
    "knights_knaves": {
        "own statement kind": lambda b: b.structured["statements"][b.structured["who"]][0],
        "own kind + is self in args": lambda b: (b.structured["statements"][b.structured["who"]][0], b.structured["who"] in b.structured["statements"][b.structured["who"]][1]),
    },
    "boolean_lights": {"#presses of switches wired to ask, parity": lambda b: sum(1 for c in b.structured["presses"] if b.structured["ask"] in b.structured["switches"][c]) % 2},
}
FEATS_2 = {
    "conditional_threshold_rule": {"margin sign and |margin|//5": lambda b: (b.structured["margin"] > 0, abs(b.structured["margin"]) // 5),
                                   "#yes - #no votes": lambda b: sum(1 if v == "yes" else -1 if v == "no" else 0 for v in b.structured["votes"].values())},
    "categories_default_exceptions": {"#rules for verb, #true for verb": lambda b: (sum(1 for r in b.structured["rules"] if r[1] == b.structured["verb"]), sum(1 for r in b.structured["rules"] if r[1] == b.structured["verb"] and r[2])),
                                      "chain length": lambda b: len(b.structured["chain"])},
}


def base_of(lid: str) -> str:
    return re.sub(r"_r\d+$", "", lid.split(".", 1)[1])


def _score(lin: Lineage, f, nf: int, nt: int, fit_root: int, test_root: int) -> list[float]:
    row = []
    for lv in range(7):
        fit = items(lin, lv, nf, fit_root)
        test = items(lin, lv, nt, test_root)
        tab: dict[Any, Counter] = defaultdict(Counter)
        for b in fit:
            tab[f(b)][b.answer] += 1
        glob = Counter(b.answer for b in fit).most_common(1)[0][0]
        acc = sum((tab[f(b)].most_common(1)[0][0] if tab.get(f(b)) else glob) == b.answer for b in test) / nt
        row.append(acc - 1 / test[0].k)
    return row


def feature_rows(lin: Lineage, nf: int = 3000, nt: int = 1000) -> list[dict[str, Any]]:
    out = []
    bs = base_of(lin.id)
    for feats, fit_root, test_root in ((FEATS_1, int(__import__("os").environ["M0FR_R1A_FEAT1_FIT"]), int(__import__("os").environ["M0FR_R1A_FEAT1_TEST"])), (FEATS_2, int(__import__("os").environ["M0FR_R1A_FEAT2_FIT"]), int(__import__("os").environ["M0FR_R1A_FEAT2_TEST"]))):
        for name, f in sorted(feats.get(bs, {}).items()):
            vals = _score(lin, f, nf, nt, fit_root, test_root)
            for lv, v in enumerate(vals):
                out.append({"lineage": lin.id, "level": lv, "heuristic": f"feat:{name}", "eff": round(v, 4), "anti": None, "acc_fired": None, "fired": nt, "n": nt})
    return out


__all__ = ["feature_rows"]
