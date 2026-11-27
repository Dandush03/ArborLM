"""Judgements v2 = judgements.py (attempt 1, kept unchanged) with corrections found on re-checking coverage of the earlier maps.
Changes (each also visible in MAP_REASONS.md):
 1. audit3_c1 s2 counted the C1 map's strictest groups S1 (B5, while_counter, digit_peel, fast_power) and S2 (bubble, insertion,
    partition) in its 'strictest' bound: they are earlier BORDERLINE judgements. Attempt 1 recorded bubble~insertion,
    insertion~partition and while_counter~digit_peel as NONE from audit_c1's near-miss list alone. Under the brief (an undecided
    pair the earlier auditor had as BORDERLINE stays BORDERLINE) they become BORDERLINE, and the remaining S1 pairs are added.
 2. Two 'weak' cross-evaluation likenesses of the earlier maps were not recorded: R2.count_divisible~C1.counter_list and
    R2.longest_palindromic_substring~C1.mirror_pointers. Added as NONE.
 3. The odd expression in one add() call of attempt 1 (a constant conditional) is harmless; the pair is R1.road_reachability~C1.bfs_queue."""
import judgements as J1
P = []
S1SRC = "audit3_c1 s2 'strictest' (the C1 map's S1 numeric while-loop group; audit_c1 near-miss)"
S2SRC = "audit3_c1 s2 'strictest' (the C1 map's S2 in-place reordering group; audit_c1 near-miss)"
override = {
    ("C1.bubble_pass", "C1.insertion_sort"): ("BORDERLINE", S2SRC, "BORDERLINE", "In-place reordering passes; adjacent swaps per pass versus shifting into a hole: the test leans distinct but does not settle it against the earlier strictest grouping."),
    ("C1.insertion_sort", "C1.partition_pass"): ("BORDERLINE", S2SRC, "BORDERLINE", "In-place reordering; insertion versus Lomuto partition (as above)."),
    ("C1.digit_peel", "C1.while_counter"): ("BORDERLINE", S1SRC, "BORDERLINE", "Numeric while loops; digit extraction versus affine growth / Collatz / subtraction: per-step updates differ."),
}
for a, b, earlier, src, mine, reason in J1.P:
    k = (a, b) if a < b else (b, a)
    if k in override:
        e2, s2, m2, r2 = override.pop(k)
        P.append((k[0], k[1], e2, s2, m2, r2))
    else:
        P.append((a, b, earlier, src, mine, reason))
assert not override, override
P.append(("C1.euclid_gcd", "C1.while_counter", "BORDERLINE", S1SRC, "BORDERLINE", "Numeric while loops; Euclid's remainder step versus affine growth / Collatz / subtraction."))
P.append(("C1.fast_power", "C1.while_counter", "BORDERLINE", S1SRC, "BORDERLINE", "Numeric while loops; square-and-multiply over the bits versus while_counter's maps."))
P.append(("C1.euclid_gcd", "C1.fast_power", "BORDERLINE", S1SRC, "BORDERLINE", "Numeric while loops; remainder step versus squaring chain."))
P.append(("C1.digit_peel", "C1.fast_power", "BORDERLINE", S1SRC + "; audit_c1 near-miss", "BORDERLINE", "The exponent loop is a base-2 digit peel, with a carried squaring chain on top."))
P.append(("C1.counter_list", "R2.count_divisible", "NONE", "lineages_r2_fix3_clusters.CROSS_EVAL weak; audit3_r2 weak", "NONE", "Bucket tally of residues versus a predicate-gated sum."))
P.append(("C1.mirror_pointers", "R2.longest_palindromic_substring", "NONE", "audit4_r2 s5 weak", "NONE", "Converging pair comparison versus expand-around-centre search over all centres."))
