# AMBIGUITIES (r2a)

Genuine ambiguities found (two readings the text supports that give different answers): 0.

Edge cases listed for visibility (my judgement: the text decides them; not counted as ambiguities):
1. R2.crt_smallest L1 i5: "smallest positive whole number that leaves remainder 0 when divided by 10, and leaves remainder 0 when divided by 17". Implemented: 170 (0 is not positive). Alternative reading (0) is excluded by "positive". The only all-zero item in the 280.
2. R2.count_divisible, all 280 items: the threshold t is itself in the list and divisible by m. Implemented: strictly greater, t excluded ("greater than"). An "at least" reading would add t (times its multiplicity) to every answer.
3. R2.cheapest_network, all 280 items: tied costs exist; the minimum total is unique regardless of tie-breaking, so no effect on the answer.
4. R2.binary_search_trace, ask=values with target absent (part of the 136 absent items): the list is every value looked at, ending when lo > hi; no "not found" marker added (SCHEMA says integers only).
