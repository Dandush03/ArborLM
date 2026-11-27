# Ambiguities found (m1b, EVAL M1)

Genuine ambiguities (two readings the text supports that give different answers): **0**.

Considered and judged resolved by the text (listed as evidence about the wording, not as ambiguities):

1. M1.grid_perimeter_r3 - "perimeter" of a figure with enclosed empty cells or several pieces. A reader using the everyday meaning (outer boundary of one shape) would differ from the text's definition on figures with enclosed gaps. The text defines the perimeter explicitly as the number of unit sides belonging to exactly one square, which counts every side bordering an empty cell, enclosed or not, and every piece. I implemented the definition. Measured (`check_extra.py`): 67 of 280 items have an empty cell not 4-connected to the outside (all such gaps are bounded only by squares meeting at corners or by sides); 276 of 280 figures have more than one piece. Items with an enclosed empty cell (level, index): (0,36); (1,6),(1,8),(1,16),(1,20),(1,32),(1,38),(1,39); (2,4),(2,14),(2,16),(2,23),(2,25),(2,30),(2,32),(2,36),(2,39); (3,0),(3,9),(3,14),(3,22),(3,29),(3,31),(3,35),(3,38),(3,39); (4,0),(4,2),(4,3),(4,6),(4,7),(4,10),(4,21),(4,27),(4,28),(4,29),(4,30),(4,33),(4,36),(4,37),(4,39); (5,3),(5,4),(5,5),(5,19),(5,23),(5,27),(5,28),(5,33),(5,38),(5,39); (6,2),(6,11),(6,12),(6,13),(6,14),(6,16),(6,20),(6,22),(6,23),(6,24),(6,25),(6,27),(6,30),(6,33),(6,34),(6,37).

2. M1.percent_change_r3 - rounding to cents after each step vs exact. No item has a non-whole-cent intermediate price, so both readings agree on all 280.

3. M1.mixture_r4, M1.median_list_r3, M1.percent_change_r3 - "no more than two decimal places": no exact value in these 840 items needs more than two decimals, so no rounding rule is exercised.

4. M1.last_digit_power_r3 - `structured.op` is `sum` for the 80 single-term items whose text says "the product of N factors, each equal to B". A structured-field labelling observation only; one term makes sum and product equal.
