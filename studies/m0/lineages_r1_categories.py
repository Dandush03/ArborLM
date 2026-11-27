# ruff: noqa: E501
"""R1 pilot, family "categories" (intended part B): default rules with exceptions (the most specific rule wins).

This lineage states its convention in the item, so there is no existential-import ambiguity: nothing is asked about empty groups."""

from __future__ import annotations

import random

from studies.m0.core import Built, Retry
from studies.m0.lineages_r1_common import pilot
from studies.m0.vocab import NAMES, PSEUDO

VERBS = ("swim", "glow", "hum", "jump", "float", "climb")


@pilot("categories", "B")
def categories_default_exceptions(level: int, r: random.Random) -> Built:
    """structured: {"chain": [group names, smallest first] (every member of chain[i] is a member of chain[i+1]), "rules": [[group, verb, true|false]],
    "member": name (belongs to chain[0]), "verb": verb}. The rule of the smallest group that has a rule about the verb decides. Answer yes/no: can the member do it."""
    c = 3 + level // 2
    chain = r.sample(PSEUDO, c)
    verbs = r.sample(VERBS, 2)
    rules = []
    for g in chain:
        for v in verbs:
            if r.random() < 0.4:
                rules.append([g, v, r.random() < 0.5])
    ask = verbs[0]
    mine = [x for x in rules if x[1] == ask]
    if not mine:
        raise Retry
    first = min(mine, key=lambda x: chain.index(x[0]))
    want = r.choice(("yes", "no"))
    if first[2] != (want == "yes"):
        raise Retry
    member = r.choice(NAMES)
    r.shuffle(rules)
    chain_text = " ".join(f"Every {chain[i]} is a {chain[i + 1]}." for i in range(c - 1))
    rule_text = " ".join(f"A {g} {'can' if ok else 'cannot'} {v}." for g, v, ok in rules)
    q = (f"{chain_text} {rule_text} When two rules about the same thing disagree, the rule about the smaller (more specific) group wins. "
         f"{member} is a {chain[0]}. Can {member} {ask}? Answer yes or no.")
    return Built(q, {"chain": chain, "rules": rules, "member": member, "verb": ask}, want, "yn", 2)
