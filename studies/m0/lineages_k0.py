# ruff: noqa: E501
"""K0, fictitious facts (ADR-0033 section 6.6): a floor check, not a battery evaluation.

Invented entities and facts; the facts are stated nowhere, so every system should be at chance (four options, 25 %).
A system above the floor band flags GENERATOR GUESSABLE. K0 has one lineage (six surface shapes made mechanically
from one base rule), so it is not a gate candidate and has no part A/B split (part label "K").
"""

from __future__ import annotations

import random

from studies.m0.core import Built, lineage
from studies.m0.vocab import COLOURS, NAMES, OBJECTS, PSEUDO

LETTERS = "ABCD"
FOODS = ("seeds", "moss", "beetles", "river fish", "nectar", "bark", "mushrooms", "snails")


def _cap(w: str) -> str:
    return w[0].upper() + w[1:]


@lineage("K0", "fiction")
def invented_fact(level: int, r: random.Random) -> Built:
    shape = r.randrange(6)
    ent = _cap(r.choice(PSEUDO))
    if shape == 0:
        q, pool = f"What is the capital city of the country of {ent}?", [_cap(w) for w in r.sample(PSEUDO, 4)]
    elif shape == 1:
        q, pool = f"Who first isolated the element {ent.lower()}ium?", r.sample(NAMES, 4)
    elif shape == 2:
        q, pool = f"What colour are the flowers of the {ent.lower()} plant?", r.sample(COLOURS, 4)
    elif shape == 3:
        q, pool = f"In which year was the town of {ent} founded?", [str(y) for y in r.sample(range(1100, 1900), 4)]
    elif shape == 4:
        q, pool = f"What does the {ent.lower()} animal mainly eat?", r.sample(FOODS, 4)
    else:
        q, pool = f"Which everyday object did {r.choice(NAMES)} name after {ent}?", r.sample(OBJECTS, 4)
    right = r.randrange(4)
    opts = "  ".join(f"{LETTERS[i]}) {pool[i]}" for i in range(4))
    return Built(f"{q} {opts} Answer with one letter, A, B, C or D.", {"shape": shape, "entity": ent, "options": pool, "fact_index": right}, LETTERS[right], "letter", 4)
