# Second solvers, NAME = m1c, EVAL = M1 (9 lineages)

Written by an `arbor-auditor` context (Claude Opus 5.5) from the answer-free fixtures and SCHEMA.md only.
Not Astra validation, not human approval. `Astra review: NOT_PERFORMED`.

Items are keyed by (`id`, `level`, `index`): in these fixtures `id` is the lineage id (280 lines share it), so `answers_m1c.jsonl` carries `level` and `index` as given.

Every solver computes from `structured`. Every lineage also has a text parser (`TEXT_PARSERS` in `solver2_m1c.py`); `run_solver2.py` checked, for all 2520 items, that the inputs parsed from the question text equal `structured` exactly and that solving from the text-parsed inputs gives the same answer (0 mismatches, 0 parse failures). So each answer is supported by both `structured` and the text. Arithmetic is exact (integers / `fractions.Fraction`); an integer answer that is not whole, or a money answer that is not a whole number of cents, raises instead of rounding. None raised.

Templates: counted after removing the four attribution preambles ("X of Y wrote this problem for a maths club.", "X from Y found this problem in a puzzle book.", "This problem comes from a quiz held in Y, set by X.", "At a maths club in Y, X is asked this.") and replacing numbers and names (script `work/templates2.py`).

## M1.prime_factors_r3
Trial-division factorisation of `n`; divisors = prod(e+1); largest = max prime; distinct_sum = sum of distinct primes; factor_count = sum of exponents (with multiplicity).
Templates: 4 (one per `ask`), each with the 4 preambles.
Hand-checked: L0 i5 n=3087=3^2*7^3, factor_count 5; L3 i17 n=54961=17*53*61, largest 61; L6 i33 n=18425=5^2*11*67, distinct_sum 83.

## M1.quadratic_area_r3
product / rect_area: x(x+d)=A, x=(sqrt(d^2+4A)-d)/2 (smaller number / width). squares: x^2+(x+d)^2=T, x=(sqrt(8T-4d^2)-2d)/4. rect_perimeter: L+W=P/2, LW=A, answer longer side L. Exact integer square root; root verified by substitution.
Templates: 10 (product, squares; rect_area and rect_perimeter each with 4 nouns: banner, poster, garden, playing field), each with the 4 preambles.
Hand-checked: L0 i5 136*192=26112 -> 136; L3 i17 146*319=46574 -> 146; L6 i33 57^2+220^2=51649 -> 57.

## M1.ratio_share_r3
share = total*parts[who]/sum(parts) (must be whole). Text parser also checks the asked name occurs exactly once among the named people and that the name count equals the number of parts.
Templates: 3 (2, 3 or 4 people); no preamble.
Hand-checked: L0 i5 50*(14/25)=28; L3 i17 155*(5/31)=25; L6 i33 1178*(2/31)=76.

## M1.rectangle_r3
half = P/2. excess: w=(half-e)/2, L=w+e. ratio: w=half/(k+1), L=k*w. Answer L*w (must be whole).
Templates: 2 (excess, ratio); no preamble.
Hand-checked: L0 i5 6*22=132; L3 i17 47*188=8836; L6 i33 70*127=8890.

## M1.recurrence_iterate_r3
sum_prev_two: a_n=a_{n-1}+a_{n-2}. affine: a_n=mult*a_{n-1}+add (add negative for "minus"). add_index: a_k=a_{k-1}+add*k for k>=2 (k = position of the new number). Answer a_position (position 1 = first number).
Templates: 5 (sum_prev_two; affine plus; affine minus; add_index with "plus its own position"; add_index with "plus N times its own position"), each with the 4 preambles. The text parser checks that the parenthetical example ("second is the first plus 2a, third is the second plus 3a") agrees with the rule for every add_index item.
Hand-checked: L0 i5 affine 181,x3+28 -> 571,1741,5251,15781,47371,142141; L3 i17 122,142 -> pos 9 = 4568; L6 i33 26,71 -> pos 21 = F19*26+F20*71 = 4181*26+6765*71 = 589021.

## M1.shopping_r3
change = paid - sum(count*price), in cents, written in dollars (whole -> no point; else up to two decimals, trailing zero stripped).
Templates: 1 structure ("X buys <list>. X pays with $P. How many dollars of change does X get back?") with 2-6 item clauses (item counts: 2:40, 3:40, 4:80, 5:80, 6:40) and 25 nouns (singular when count is 1; plural by adding "s", giving "compasss" and "scarfs"). The coarse template count (279) only reflects noun combinations.
Hand-checked: L0 i5 1500-456=1044 -> 10.44; L3 i17 9500-8780=720 -> 7.2; L6 i33 23000-20990=2010 -> 20.1.

## M1.speed_distance_r3
total = sum(hours*speed); average = total / sum(hours) (must be whole).
Templates: 2 question forms (total distance; average speed) x 2-5 legs, "1 hour" singular. 28 coarse templates only from hour/hours combinations.
Hand-checked: L0 i5 144+245=389; L3 i17 58+300+207=565; L6 i33 198+567+480+377+264=1886.

## M1.tiered_pricing
cost(u) fills each step in order (min(remaining, size)*rate), the rest at last_rate. bill mode: cost(used)/100 in dollars, money format. units mode: smallest u with cost(u) >= bill; must equal bill exactly (all rates > 0, so cost is strictly increasing and the u is unique).
Templates: 5 (bill or units mode x 1-3 listed steps; observed: bill with 1, 2, 3 steps; units with 2, 3 steps); no preamble.
Hand-checked: L0 i5 12*50+1*54=654 -> 6.54; L3 i17 756+3886=4642, (4846-4642)/68=3 -> 91; L6 i33 312+592+2924=3828, (6438-3828)/90=29 -> 135.

## M1.tip_split_r3
each = bill*(100+tip)/(100*people); money format. Every item is an exact whole number of cents (the half-up rounding branch never fired).
Templates: 1; no preamble.
Hand-checked: L0 i5 273.70/5=54.74; L3 i17 306.60/4=76.65; L6 i33 224/5=44.8.

## Commands and environment
`python3 -I -B run_solver2.py > run_solver2.out` (from this directory; macOS system `python3`, Python 3.15.1, standard library only). Template enumeration: `python3 -I -B work/templates2.py <lineage ids>`. Hand-check listing: `work/handcheck_items.out` (the item values and solver answers; the arithmetic above was done by hand in this context). `work/templates.py` is an earlier, finer template counter (kept).
