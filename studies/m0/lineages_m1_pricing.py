# ruff: noqa: E501
"""M1 batch 1, family "pricing": cheapest combination of pack deals (search over pack counts) and tiered (marginal-rate) prices."""

from __future__ import annotations

import random
from fractions import Fraction

from studies.m0.core import Built, Retry
from studies.m0.lineages_m1 import fmt
from studies.m0.lineages_m1_common import DECIMAL, WHOLE, and_, m1  # noqa: F401
from studies.m0.vocab import NAMES, OBJECTS


def _best(n: int, single: int, packs: list[list[int]]) -> int:
    """Cheapest cost of at least n items from singles and packs [[size, price]] (all prices in whole dollars), by dynamic programming over the count bought."""
    top = n + max(p for p, _ in packs)
    inf = 10**9
    cost = [inf] * (top + 1)
    cost[0] = 0
    for i in range(1, top + 1):
        cost[i] = min([cost[i - 1] + single] + [cost[i - p] + q for p, q in packs if i >= p])
    return min(cost[n:])


@m1("pricing")
def min_cost_packs(level: int, r: random.Random) -> Built:
    """structured: {"item": word, "need": N, "single": s, "packs": [[size, price]]} (prices in whole dollars; a pack is not always a bargain). Answer: the least total cost in dollars of buying AT LEAST `need` items,
    using any mix of singles and packs (buying more than needed is allowed). The class of the item is drawn first: half the items are drawn (by repeated parameter draws inside the builder) so that the optimum is
    found by none of five naive plans (singles only; biggest pack floor + singles; biggest pack ceil; best-unit-price pack floor + singles; best-unit-price pack ceil), the other half so that exactly one named naive plan
    (drawn uniformly; no other naive plan reaches the same cost) reaches it."""
    npk = 2 + (level >= 5)
    want = r.choice((-1, -1, -1, -1, -1, 0, 1, 2, 3, 4))
    for _ in range(400):
        single = r.randint(2, 9)
        packs: list[list[int]] = []
        for _ in range(npk):
            size = r.randint(3, 6 + 2 * level + 3 * len(packs))
            packs.append([size, r.randint(max(2, size * single // 2 + 1), size * single + size // 2)])
        if len({p for p, _ in packs}) < npk:
            continue
        packs.sort()
        need = r.randint(max(p for p, _ in packs) + 3, 25 + 10 * level)
        best = _best(need, single, packs)
        big = max(packs, key=lambda p: p[0])
        unit = min(packs, key=lambda pq: Fraction(pq[1], pq[0]))
        naive = [need * single, (need // big[0]) * big[1] + (need % big[0]) * single, -(-need // big[0]) * big[1],
                 (need // unit[0]) * unit[1] + (need % unit[0]) * single, -(-need // unit[0]) * unit[1]]
        if (want == -1 and best not in naive) or (want >= 0 and [i for i in range(5) if naive[i] == best] == [want]):
            break
    else:
        raise Retry
    item = r.choice(OBJECTS)
    deals = " and ".join(f"a pack of {p} {item}s costs {q} dollars" for p, q in packs)
    name = r.choice(NAMES)
    q = (f"At a shop, one {item} costs {single} dollars, and {deals}. {name} needs at least {need} {item}s and wants to spend as little as possible; {name} may buy more than needed and may mix packs and single items. "
         f"What is the smallest total cost, in dollars? {WHOLE}")
    return Built(q, {"item": item, "need": need, "single": single, "packs": packs}, str(best), "number", None)


@m1("pricing")
def tiered_pricing(level: int, r: random.Random) -> Built:
    """structured: {"mode": "bill" | "units", "tiers": [[units_in_tier, cents_per_unit]] for every tier but the last, "last_rate": cents_per_unit above all tiers, "used": U or null, "bill_cents": B or null}.
    Each unit is charged at the rate of the tier it falls in (marginal rates: the first tiers[0][0] units at tiers[0][1], the next tiers[1][0] at tiers[1][1], ..., all further units at last_rate).
    bill: answer the bill for U units in dollars (a number with at most two decimals). units: answer the whole number of units U that gives a bill of B cents. Generator makes U exceed every tier boundary at higher levels."""
    nt = 1 + level // 2 + (level >= 5)
    nt = min(nt, 3)
    rates = sorted(r.sample(range(8, 60 + 6 * level, 2), nt + 1))
    tiers = [[r.randint(10, 40 + 10 * level), rates[i]] for i in range(nt)]
    last = rates[nt]
    cap = sum(u for u, _ in tiers)
    used = r.randint(cap + 1, cap + 20 + 10 * level)

    def bill(u: int) -> int:
        left, tot = u, 0
        for size, rate in tiers:
            take = min(left, size)
            tot += take * rate
            left -= take
        return tot + left * last

    total = bill(used)
    mode = "units" if level >= 3 and r.random() < 0.4 else "bill"
    desc = ", ".join([f"the first {tiers[0][0]} units cost {tiers[0][1]} cents each"] + [f"the next {u} units cost {c} cents each" for u, c in tiers[1:]])
    q0 = f"A utility charges for use in steps: {desc}, and every unit after that costs {last} cents each. Each unit costs the rate of the step it falls in (a higher step does not change what earlier units cost)."
    if mode == "bill":
        q = f"{q0} What is the bill for {used} units, in dollars? {DECIMAL}"
        ans = fmt(Fraction(total, 100))
    else:
        q = f"{q0} A customer's bill is {fmt(Fraction(total, 100))} dollars. How many units did the customer use? {WHOLE}"
        ans = str(used)
    return Built(q, {"mode": mode, "tiers": tiers, "last_rate": last, "used": used if mode == "bill" else None, "bill_cents": total if mode == "units" else None}, ans, "number", None)
