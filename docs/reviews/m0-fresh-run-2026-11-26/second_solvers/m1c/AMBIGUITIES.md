# Ambiguities, NAME = m1c (M1, 9 lineages)

Count: 0 items where I found two defensible readings giving different answers.

Readings I considered and why they did not split any item (checked by code over all 2520 items, see `run_solver2.out`):
- M1.tip_split_r3: if the per-person amount were not a whole number of cents, "no more than two decimal places" would leave rounding (half-up, half-even, truncation) open. No item hits this: all 280 are exact in cents.
- M1.speed_distance_r3 (average) and M1.rectangle_r3, M1.ratio_share_r3: "Answer with a whole number" would be ambiguous for a non-whole value; none occurs.
- M1.tiered_pricing units mode: a bill not reached exactly by any whole number of units would be ambiguous; none occurs; cost is strictly increasing so the units are unique.
- M1.recurrence_iterate_r3 add_index: "plus N times its own position" could be read with the position of the earlier number; the parenthetical ("the second number is the first plus 2N") fixes it as the new number's position, and it agrees with that reading on every item.
- M1.prime_factors_r3 factor_count: the worked example (12 = 2 x 2 x 3, three primes) fixes counting with multiplicity.
- M1.quadratic_area_r3 rect_perimeter: a square would make "longer side" degenerate but not ambiguous in value.

Wording observations (no effect on the answer): M1.shopping_r3 pluralises by appending "s", giving "compasss" and "scarfs".
