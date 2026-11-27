# Ambiguities found in the R1 wording (NAME = r1)

No item was found where I judge two readings genuinely supported by the text. No solver raised its own "not determined" error on any of the 2800 items (knights: exactly one consistent world in all 280; exchange and weekday graphs are trees, so no inconsistency; categories: a deciding rule exists, no group has conflicting rules).

Readings I considered and rejected, listed because they are evidence about the wording (`diagnostics.out`):

1. R1.venn_counting_r5, all 200 items of levels 2-6 (3 or 4 groups; every index 0-39 at levels 2, 3, 4, 5, 6). Alternative reading: "k are in both the A and the B groups" / "all of the A, B and C groups" means exactly those groups (exclusive region counts). Under that reading the answer differs on all 200 items. I implemented the inclusive reading, which the sentence "Each person is counted once in each number that applies to them" supports (a person in all three groups is in both A and B, so that number applies to them), as does SCHEMA.md ("including those in more"). A model that reads the numbers as exclusive regions gets these items wrong; the wording is standard but not mathematically explicit.
2. R1.conditional_threshold_rule_r4, 64 items with net == D (list in `diagnostics.out`): "at least" vs "more than". The text says "at least"; not ambiguous, listed because these items are sensitive to the boundary.
3. R1.compass_turns, 136 items whose answer depends on left = counterclockwise / right = clockwise (seen from above). Standard; not ambiguous.
4. R1.swap_tracking_r5, 245 items whose answer would change if the rotate sentence were read in the reverse direction. The sentence names each hand-over explicitly; not ambiguous.
