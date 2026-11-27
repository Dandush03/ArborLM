# AMBIGUITIES: r2b (EVAL R2)

Genuine ambiguities found (two readings giving different answers on an item in these fixtures): **0**.

Points I considered and why each is not listed as an item-level ambiguity:

1. R2.grid_sum, diagonal on non-square grids (46 items, shapes 3x4, 4x5, 5x6; rows < cols). Implemented reading: cells (1,1), (2,2), ... while both indices exist, i.e. min(rows, cols) cells. The text "(cells (1,1), (2,2), and so on)" supports this; I found no other reading that yields a defined, different sum (a "corner to corner" diagonal does not exist on a non-square grid of cells). Wording note only: a reader might call the diagonal of a non-square grid ill-defined.
2. R2.min_heap_ops, equal children during remove-smallest ("the smaller of the numbers in positions 2p and 2p+1" does not say which to pick on a tie). No item has repeated values, so this never arises here; the solver would raise if it did.
3. R2.string_rewrite_nonidentity, self-overlapping patterns (aa, bb, cc) and whether a step rescans its own output. The text fixes both ("scanning left to right over non-overlapping matches in the string as it is when the step starts"); no ambiguity.
4. R2.luhn_check, check-digit position. The text says the new digit is the rightmost digit of the new number, so it is position 1 (not doubled); no ambiguity. Uniqueness of the check digit is asserted for every item.
