# AMBIGUITIES: m1a (M1, 10 lineages)

No item in the 10 assigned lineages had two readings that I judged plausible and that give different answers. Number of ambiguous items listed: 0.

Readings I considered and rejected (no item ids listed because no answer depends on them):
- division_counting_r3 (pallets): "How many boxes are not on a full pallet?" Whether the leftover boxes go on a partial pallet or stay off pallets, the count is the same: (items // box) mod crate. Loose items that do not fill a box are explicitly "left out" and are not counted.
- consecutive_r3 (step 2): "consecutive numbers that each differ from the next by 2" fixes the sequence once the sum is known; parity is not an extra condition.
- average_missing_r4: the needed score is exactly n*mean - sum. The "out of N" range is only a feasibility condition; it holds for all items, with the needed score equal to N in 3 items.
- crt_congruence_r3: "smallest positive" would matter only if every remainder were 0 (the answer would then be the lcm, not 0). No such item.
- ages_r3: the asked person's name is never the same as the other person's name. If it were, the ask would be ambiguous; the solver raises an error in that case, and it never did.
