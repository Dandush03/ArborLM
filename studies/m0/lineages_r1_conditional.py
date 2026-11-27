# ruff: noqa: E501
"""R1 pilot, family "conditional" (intended part B): walking a decision tree, and a weighted-vote threshold with vetoes."""

from __future__ import annotations

import random

from studies.m0.core import Built, Retry
from studies.m0.lineages_r1_common import and_, pilot
from studies.m0.vocab import NAMES, PSEUDO

ACTIONS = ("stop", "turn left", "turn right", "wait", "jump", "knock", "hide", "sing", "run", "sit down")


@pilot("conditional", "B")
def conditional_decision_tree(level: int, r: random.Random) -> Built:
    """structured: {"tree": node, "facts": {attribute: true|false}, "actions": [action]}; a node is ["do", action] or ["if", attribute, node_if_true,
    node_if_false]. Answer: the action at the leaf reached by testing each attribute against the facts."""
    depth = min(5, 2 + level // 2)
    attrs = [f"the {w} light is on" for w in r.sample(PSEUDO, depth + 2)]
    actions = r.sample(ACTIONS, min(2**depth, 3 + (level + 1) // 2))

    def grow(d: int, avail: list[str]) -> list:
        if d == 0:
            return ["do", r.choice(actions)]
        a = r.choice(avail)
        rest = [x for x in avail if x != a]
        return ["if", a, grow(d - 1, rest), grow(d - 1, rest)]

    tree = grow(depth, attrs)
    facts = {a: r.random() < 0.5 for a in attrs}
    node = tree
    while node[0] == "if":
        node = node[2] if facts[node[1]] else node[3]
    leaves: set[str] = set()

    def collect(n: list) -> None:
        if n[0] == "do":
            leaves.add(n[1])
        else:
            collect(n[2])
            collect(n[3])

    collect(tree)
    if len(leaves) < 2:
        raise Retry

    def render(n: list) -> str:
        return n[1] if n[0] == "do" else f"if {n[1]}, then ({render(n[2])}), otherwise ({render(n[3])})"

    state = "; ".join(f"it is {'true' if v else 'false'} that {a}" for a, v in sorted(facts.items()))
    q = f"Your rule is: {render(tree)}. Right now, {state}. What do you do? Choose from {and_(sorted(leaves))}."
    return Built(q, {"tree": tree, "facts": facts, "actions": sorted(leaves)}, node[1], "text", len(leaves))


@pilot("conditional", "B")
def conditional_threshold_rule(level: int, r: random.Random) -> Built:
    """structured: {"members": [[name, weight]], "votes": {name: "yes"|"no"}, "need": T, "vetoes": [name]}. The motion passes when the total weight of
    yes votes is at least T and no veto holder voted no. Answer yes/no: does it pass."""
    n = 4 + level
    ps = r.sample(NAMES, n)
    w = {p: (r.randint(1, 4) if level >= 2 else 1) for p in ps}
    votes = {p: r.choice(("yes", "no")) for p in ps}
    vetoes = r.sample(ps, r.randint(0, 1 + level // 3))
    total = sum(w.values())
    need = r.randint(total // 3 + 1, (2 * total) // 3 + 1)
    yes_w = sum(w[p] for p in ps if votes[p] == "yes")
    passes = yes_w >= need and not any(votes[p] == "no" for p in vetoes)
    want = r.choice(("yes", "no"))
    if passes != (want == "yes"):
        raise Retry
    q = ("A committee votes on a motion. " + ", ".join(f"{p} has weight {w[p]}" for p in ps) + ". The motion passes if the total weight of the members who vote yes is at least "
         f"{need}" + (f", and also no one holding a veto votes no; the veto holders are {and_(vetoes)}." if vetoes else " (nobody has a veto).")
         + " The votes: " + ", ".join(f"{p} {votes[p]}" for p in ps) + ". Does the motion pass? Answer yes or no.")
    return Built(q, {"members": [[p, w[p]] for p in ps], "votes": votes, "need": need, "vetoes": vetoes}, want, "yn", 2)
