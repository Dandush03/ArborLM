# ruff: noqa: E501
"""R1 pilot, family "boolean_state" (intended part A): parity of switch presses over a set of lamps."""

from __future__ import annotations

import random

from studies.m0.core import Built, Retry
from studies.m0.lineages_r1_common import and_, pilot
from studies.m0.vocab import COLOURS


@pilot("boolean_state", "A")
def boolean_lights(level: int, r: random.Random) -> Built:
    """structured: {"lamps": n, "initial": [0|1] (lamp 1..n), "switches": {colour: [lamp numbers it toggles]}, "presses": [colour], "ask": lamp number}.
    Each press toggles every lamp its switch is wired to. Answer yes/no: is lamp `ask` on at the end."""
    nl = 4 + level
    ns = 3 + level // 3
    cols = r.sample(COLOURS, ns)
    init = [r.randrange(2) for _ in range(nl)]
    wiring = {c: sorted(r.sample(range(1, nl + 1), r.randint(1, nl // 2 + 1))) for c in cols}
    presses = [r.choice(cols) for _ in range(3 + 2 * level)]
    state = list(init)
    for c in presses:
        for lamp in wiring[c]:
            state[lamp - 1] ^= 1
    want = r.choice(("yes", "no"))
    cand = [i + 1 for i in range(nl) if state[i] == (1 if want == "yes" else 0)]
    if not cand:
        raise Retry
    ask = r.choice(cand)
    on = [i + 1 for i in range(nl) if init[i]]
    q = (f"There are {nl} lamps numbered 1 to {nl}. At the start, " + (f"{'lamp' if len(on) == 1 else 'lamps'} {and_([str(x) for x in on])} {'is' if len(on) == 1 else 'are'} on and the rest are off. " if on else "all lamps are off. ")
         + " ".join(f"The {c} switch toggles {'lamp' if len(wiring[c]) == 1 else 'lamps'} {and_([str(x) for x in wiring[c]])} (each one goes from on to off or from off to on)." for c in cols)
         + f" The switches are pressed in this order: {', '.join(presses)}. Is lamp {ask} on at the end? Answer yes or no.")
    return Built(q, {"lamps": nl, "initial": init, "switches": wiring, "presses": presses, "ask": ask}, want, "yn", 2)
