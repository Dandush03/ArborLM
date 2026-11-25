# Review 1 of ADR-0033 addendum 1 (lineage clusters), draft 1

- Reviewer: `arbor-auditor` context, Claude Opus 5.5 (`claude-opus-5-5`), 2026-11-25. I wrote none of the draft, none of ADR-0033's wording under review here, and none of the implementation.
- `Astra review: NOT_PERFORMED`. This is independent engineering and mathematical evidence. It is not Astra validation and not human approval. It approves nothing.
- ArborLM is unproven research. Nothing here is a result about any model. No model was loaded, run or scored; nothing was downloaded or installed; no git state was changed.

## Inputs, by hash

| File | SHA-256 |
|---|---|
| `docs/decisions/ADR-0033-addendum-1-lineage-clusters.md` (draft under review, commit `2c390259`) | read at HEAD `2c390259d607348bbcef3eaf3b8cb25255600472` |
| `docs/decisions/ADR-0033-m0-reference-models-and-evaluation-harness.md` | `7719f6d456113385a44dac37abeb28b36d6d9fb7eb569a65c7e6ccaaf19ec90b` (matches the draft's citation) |
| `addendum1_scripts/power_small_g.py` / `.out.txt` | `6f846f3e…1945` / `6851f2c4…ee50` (match) |
| `HUMAN_LEAD_WORDS.md`, `_2.md`, `_3.md`, `LEAD_RULINGS_2.md` (worktree `agent-a0c9d741…`, HEAD `f122e6bc`) | `94e9d9a2…b9a9`, `005305bf…dac04`, `d0da7d11…c6286` (match), `e2e4128a…b123` (match) |

Not read: any `audit3_*` folder. Read for mechanics only: `studies/m0/core.py` lines 20–40 and 125–155, `studies/m0/power.py` lines 1–20 and 166–195, two lines of `studies/m0/NOTES*.md`.

## Commands and environment

macOS 27.2.1 arm64; uv 0.12.15; Python 3.12.14; torch 2.8.0 (locked). `scipy` and `numpy` are **not** in the lock (checked with `importlib.util.find_spec`), so the exact computations use the standard library only. All commands from the specification worktree root:

```sh
R=docs/reviews/adr-0033-m0-2026-11-20/addendum1_review1
uv run --locked python $R/power_exact_review.py   > $R/power_exact_review.out.txt     # stdlib, ~2 min
uv run --locked python $R/power_sim_review.py     > $R/power_sim_review.out.txt       # torch, ~10 min, seed 20261125
uv run --locked python $R/choice18_review.py      > $R/choice18_review.out.txt        # stdlib
uv run --locked python $R/partition_review.py     > $R/partition_review.out.txt       # stdlib
uv run --locked python $R/partition_step5_review.py > $R/partition_step5_review.out.txt
uv run --locked python $R/capacity_review.py      | tee $R/capacity_review.out.txt
```

None of the scripts imports anything from `studies/` or from the drafter's script. Leftover (kept, not used): `experiments/_scratch/m0_addendum1_review1_20261125/step5_scen.py`, my first step-5 attempt, whose scenario "B" was impossible (20 cross clusters touching R2 with G_R2 = 19). It is my mistake, recorded here; the corrected script asserts the constraint. `power_exact_review.py` contains one dead conditional (`if False else`) left in place; it does not change any number.

## Verdict

**APPROVABLE AFTER REQUIRED CHANGES.** Two blocking findings (B1, B2), ten required (R1–R10), eight notes. Every number of the draft's section 6 and section 10 that I recomputed reproduces, except the two capacity corrections of R1. The fidelity problems are mostly unflagged new rules (R3, R4, R7, R2's timing move), not misstatements of the five answers.

## Q4. Power at small G (recomputed)

Model: n = 20,000 items over G clusters; cluster means N(0, τ² + d·G/n), d = 0.3; test passes if mean − t₀.₉₅,G−1·SE > −δ, SE in the CR1 form (sample s.d. / √G, as the implementation uses); then (mean + δ)/SE is exactly noncentral t on G − 1 df. Target 1 − 0.2/55 = 0.99636. Largest τ at which δ is reachable within the pool:

| δ | G = 11 | 13 | 14 | 15 | 19 | Draft (b) |
|---|---|---|---|---|---|---|
| 0.02 | 0.0060 | 0.0071 | 0.0075 | 0.0079 | 0.0094 | 0.006 / 0.007 / 0.008 / 0.008 / 0.009 |
| 0.03 | 0.0170 | 0.0189 | 0.0197 | 0.0206 | 0.0236 | 0.017 / 0.019 / 0.020 / 0.021 / 0.024 |
| 0.05 | 0.0331 | 0.0366 | 0.0382 | 0.0397 | 0.0453 | 0.033 / 0.037 / 0.038 / 0.040 / 0.045 |

- Reproduced exactly. Table (a) (floor, z sum 4.3289) and table (c) also reproduce to every printed digit. With sw² = d − τ² instead of d nothing moves by more than 0.0001. With a CR0 standard error (divisor G, which ADR-0033 does not exclude) every threshold rises by 0.0004–0.0008 (note N7).
- Direct simulation with discrete outcomes {−1, 0, +1} (400,000 replications per cell) agrees with the exact figures within Monte Carlo error at all nine cells checked, e.g. G = 13, τ = 0.0366, δ = 0.05: 0.9964 (exact 0.9964); G = 19, τ = 0.05, δ = 0.05: 0.9901 (exact 0.9899).
- "At τ = 0.05 the 0.05 margin is unreachable at G = 11 to 19": **confirmed** for the binding condition (power 0.910–0.990 against 0.996). Note that the floor of (a) alone is met at G = 19 (0.0503 > 0.05); the statement is true only because (b) binds, which the draft says.
- τ̂ truncated to zero at G = 13, τ = 0.03, 115 items per cluster: **0.289** (χ² approximation, divisor G − 1 as the implementation pools V), **0.295** in the direct simulation of the registered rule (400 synthetic M0 draws). With a divisor G it would be 0.353. ADR-0033 does not fix the divisor (N7).
- What the draft leaves out, and why it matters (B2): a τ̂ of zero makes not only the floor but also the simulated π(20,000) meet the target (exact power at τ = 0 is 0.9991–0.9995 at δ = 0.02). So the registered reading is itself random at these G. Share of M0 draws that read "reachable within 20,000" (G = 13; first figure the direct simulation of the registered rule, second the χ² approximation):

| True τ | δ = 0.02 | δ = 0.03 | δ = 0.05 | Truly reachable? |
|---|---|---|---|---|
| 0.00 | 0.542 / 0.573 | 0.667 / 0.676 | 0.905 / 0.890 | all three yes |
| 0.01 | 0.552 / 0.536 | 0.670 / 0.641 | 0.902 / 0.869 | 0.02 no; 0.03, 0.05 yes |
| 0.03 | 0.315 / 0.304 | 0.407 / 0.396 | 0.713 / 0.667 | 0.02, 0.03 no (true power 0.66, 0.92); 0.05 yes |
| 0.05 | 0.080 / 0.095 | 0.117 / 0.138 | 0.352 / 0.319 | none (0.05: true power 0.948) |
| 0.10 | 0.003 / 0.002 | 0.005 / 0.003 | 0.018 / 0.012 | none |

Under choice 18(b), with a χ² interval for the variance component (my assumption: ADR-0033 defines no interval for τ̂ below 30 clusters, R8), the share reading reachable at τ = 0, where every margin is truly reachable, is 0.054 / 0.081 / 0.209 at G = 13. So at G ≈ 13: under (a) the reading is close to a coin flip and wrong in both directions; under (b) the private parts read UNDERPOWERED at 0.02 and 0.03 almost whatever the truth. Choice 18 does not merely "decide most of these readings"; at these G it decides whether the reading carries information.

**Stratification (draft section 9 item 1).** One stratum per private part is **unfavourable to passing**, not a relaxation. With the implementation's reading (V pooled over strata; one-cluster strata contribute nothing) 13 clusters over 12 family strata leave 1 degree of freedom: P(τ̂ = 0 | τ = 0.03) = P(χ²₁ ≤ 0.742) ≈ 0.61, against 0.29 with one stratum (arithmetic, normal approximation). One stratum also counts between-family variance in τ̂ and widens the t intervals of 10.2–10.4. It is a change of an analysis rule tied to ADR-0032's approved rule 3 ("cluster bootstrap with strata"), so it still needs the human lead (A4 as drafted).

## Q5. Capacity

Recomputed the draft's formula: 22,820 (G = 11), 19,470 (13), 18,150 (14), 17,000 (15), 13,640 (19), 1,800 (300). Arithmetic correct. Not the worst case in two respects (R1):
1. The development and sealed pools are each spread evenly, so the largest cluster holds ⌈4,000/G⌉ + ⌈20,000/G⌉, not ⌈24,000/G⌉: 22,830 at G = 11, 17,010 at G = 15, 1,810 at G = 300 (others unchanged).
2. ADR-0033 section 6.5: if no range is interior, "the two reserve levels are scored once and the rule is applied again". Candidates are "every contiguous range of levels", so a reserve level can carry the registered level mix, and the dev and sealed pools with it. The worst case on a reserve level is then the core-level demand, not 10 × 100. Taking 100 tuning items whole for one cluster is over-conservative (the draw is spread over clusters); harmless.

## Q3. Determinism of the partition (my implementation from the text alone)

`partition_review.py` implements section 4 on a made-up list of 34 lineages with 9 links (7 multi-lineage components, 4 cross-evaluation). Points where I had to guess:
1. The exact bytes of `stream(seed, label…)`: ADR-0033 line 576 says only "SHA-256 of the seed with a text label". Separator, encoding, digest truncation and how the digest seeds a generator are not stated (the implementation uses `'|'.join`, the first 8 bytes big-endian, `random.Random`; that is code, not text).
2. The shuffle algorithm (Python `random.shuffle`? a random sort key?).
3. Lineage id format and whether ids are evaluation-prefixed (the implementation uses `R1.<name>`).
4. "Lexicographically" — code-point order assumed.
5. Step 3 when target − x_A exceeds |L_e| (assumed: all of L_e to A).
Under four combinations of guesses 1 and 2 (same seed 400004, same labels), **10 to 15 of the 25 assigned clusters change part** (an earlier draft of this sentence said 24; the script assigns 25). A third party does not get the same split from the text. The alternation (starts with A), the labels, the floor for part A, and the treatment of unregistered lineages were determined.

Seed 400004: reusing the value for the same role (the A/B split) under new labels is sound, since a new label gives an independent stream and no score exists. It needs (i) the role and labels entered in seed registry revision 6 (the draft says so, 12.7), (ii) the mechanics (13.4) chosen and the code hashed **before** any partition is computed on the map of record, and every computed split kept (R9), because earlier family-partition splits on seed 400004 have already been seen (`r1_rev4_parts.md`, the "13 / 14" figure).

## Q6. Cross-evaluation rule

No deadlock: union-find components, then a two-step assignment, always terminates, and no cluster is in both parts by construction. But it can force badly unequal parts. `partition_step5_review.py` (made-up counts): with C1 at 11 clusters of which 10 are cross-evaluation, the parts differ from ⌊G/2⌋/⌈G/2⌉ in 47 % of seeds, |A − B| up to 9, smaller part 3 clusters at the 1st percentile and **1** at the minimum. A part with 1 cluster has a t quantile on 0 degrees of freedom; ADR-0033 has no rule for it (R6). Step 5 also mentions only X clusters exceeding the target in A; part B can be overfull the same way.

Teaching ban (3.3): no direct conflict with section 6.4 item 3 or section 8, but (i) "no item, template or program of its procedure may ever be used for teaching" is unbounded: teaching data written or distilled by the teachers will contain common procedures (sorting, base conversion, percentages); read literally it can make M1.5 impossible, read loosely it is unenforceable (R4); (ii) K0 is "the look-up teaching material M1.5 and M2 will need" (line 326) and is outside the rule (3.5) — precedence is not stated; (iii) line 419 uses "procedure" in the administrative sense ("rests on procedure"), the addendum in the algorithmic sense; (iv) section 18's "drawn only from part A" excludes clusters with no part, which section 8 of the addendum leaves to M1.5.

## Q1. Fidelity to the five answers

| Item | Necessary consequence or new choice |
|---|---|
| One stratum per private part (9.1) | New choice, conservative direction; human lead (touches ADR-0032 rule 3). Flagged (A4) |
| All-pairs check replacing the 50-pair sample (1.5) | Consequence of answer 1 ("using the auditors' maps"); stricter. Lead may accept |
| No partial-level clusters (10.4) | New choice against lead ruling R-5; conservative. Lead, reported to the human lead. Flagged (12.8) |
| Two-step partition on 400004 (4) | New choice; flagged (13.4). Must be taken before computation (R9) |
| Rewriting second solvers (8) | Consequence of approved ADR-0033 lines 275 and 614, not new. The "has not read the source" condition is a tightening; fine |
| **Operational test of "same procedure" (1.1)** | **New text, not flagged as a choice** (12.2 mentions it). It is the drafter's rule, not the auditors' (R7) |
| **Transitive merges inside an evaluation (3.2)** | **New rule reducing G, not in answer 3, not in section 13** (R3) |
| **Partition fixed at G-gen's record instead of at F (4.7)** | **Timing change, not in section 15** (R2) |
| Teaching ban extended to unregistered lineages and to "procedure" (3.3) | Beyond answer 3 (which constrained parts) (R4) |
| Odd count: part A takes ⌊G/2⌋ (4.3) | Drafter's choice (implementation's "ruling needed 5"); mark it |
| "No minimum is registered" (5.1) | Answer 5 said "no minimum of 300"; no minimum at all is a reading; human lead to confirm (R6) |
| Battery gate blocking G-gen's record; repair by construction (7) | Bound flagged; R-1 (no redraw) is a lead ruling carried into the text — say so in A6 |

## Q2. Quotations and line numbers

Every quotation and line number in sections 1–12 matches ADR-0033 at `7719f6d4…` (checked one by one). The 0.0075 rounding remark is right in substance: the true value at τ = 0.03, G = 300 is 0.0074981; ADR-0033's 0.008 came from rounding review 2's four-decimal 0.0075 again (double rounding). Places the propagation table misses (R10): line 3 and line 29 ("a rehearsal of stage G-gen at the proposed numbers"; "G-gen's record of record waits for your G"); line 251 ("its in-teaching-eligible half or its held-out half"); line 409 ("The human lead chooses G's minimum with this table in view"); line 468 ("keeping the pairing, the strata"); line 419's word "procedure"; line 576 ("per-family … streams": unaffected, say so). Counts: LEAD_RULINGS_2 gives C1 strict = **28**, HUMAN_LEAD_WORDS_3 and the draft **29** (N1; not verified which is current).

## Q7. Other points

The draft states plainly (header, line 10) that no model has been loaded, run or scored on any M0 item. Consistent with what I could check: no `results/m0*` directory in either worktree; `transformers`, `accelerate`, `safetensors` not importable in the locked environment. I cannot verify absence of runs elsewhere. Internal inconsistency: 3.3 "Every global cluster is assigned" against 4.1 and 8 (only clusters with a registered lineage) (R5). Undefined: which cross-evaluation pairs "section 3 requires" (1.5); τ̂'s interval below 30 clusters (R8). Favourable framing: the draft's section 6 is not too favourable; if anything it is too certain ("will read") where the reading is random (B2).

## Findings

**B1 (blocking) — the partition is not reproducible from the text.** Replace the first paragraph of section 4's replacement reading with: "`stream(seed, l₁, …, l_k)` is `random.Random(int.from_bytes(SHA256(('|'.join([str(seed), l₁, …, l_k])).encode('utf-8')).digest()[:8], 'big'))` of CPython 3.12; to shuffle a list is to call that object's `shuffle` method on the list sorted by Unicode code-point order of the identities. Lineage ids are the registry ids `<evaluation>.<name>`. The code that computes the partition is `<path>` at SHA-256 `<hash>`; where it and this text disagree, it is an engineering stop." (Or an equivalent fully specified derivation.)

**B2 (blocking) — section 6 must tell the human lead that the reading is random at these G.** Replace the bullet "The reading will rest on an imprecise estimate" with: "At about 13 clusters the UNDERPOWERED reading is itself a random variable. τ̂ = 0 makes both the floor and the simulated power meet the target. Under the point estimate (choice 18 a), at G = 13 a part reads δ = 0.02 reachable in about 54 % of M0 draws when τ = 0, 55 % when τ = 0.01 (where it is not reachable), 31 % when τ = 0.03 (true per-test power 0.66) and 8 % when τ = 0.05; δ = 0.05 reads reachable in 35 % of draws at τ = 0.05, where it is not. Under the upper bound (choice 18 b), with a χ² interval, δ = 0.02, 0.03 and 0.05 read reachable in only about 5 %, 8 % and 21 % of draws even when τ = 0. A wrongly reachable reading sizes M5 for a power it does not have. [Review 1 of this addendum, `choice18_review.out.txt`, `power_sim_review.out.txt`.]"

**R1 (required) — capacity worst case.** In section 10 item 2 replace the formula and the reserve line with: "on each of the seven levels: D(G) = 10 × (⌈4,000/G⌉ + ⌈20,000/G⌉ + 100), because section 6.5 lets a reserve level carry the registered level mix." Correct item 3 to 22,830 (G = 11) and 17,010 (G = 15); 1,810 at G = 300.

**R2 (required) — when the map and partition stop changing.** In 4.7 replace "After any model has scored any item" with "After G-gen's record of record, and in any case once any model has been run on any item (ADR-0033 line 257)". Add a row to section 15: "ADR-0033 section 6.4 and section 13 F row: the partition is made at the freeze | Made at G-gen's record, hashed at F | Lead after review".

**R3 (required) — transitive merges.** Add to section 13: "Whether a cross-evaluation component merges lineages of one evaluation that its own map kept apart (section 3 item 2, drafted, lowers G) or binds their part only."

**R4 (required) — scope of the teaching ban.** Replace in 3.3 "and no item, template or program of its procedure" with "and no item, template or program generated by, derived from or written to imitate a lineage of a part-B global cluster". Add: "Whether teaching material from other sources that exercises a part-B procedure is excluded, and how M1.5 checks it, is settled in M1.5's specification. K0 is not a node of the graph; if a K0 generator implements a part-B procedure the auditor lists it and the human lead decides." Align section 11's row for line 709.

**R5 (required).** 3.3: "Every global cluster with at least one registered lineage is assigned…".

**R6 (required; PENDING LEAD REVIEW for the number).** Add to section 4: "Part B can be overfull in the same way as part A (step 5)." Add to section 13: "A rule for a part with very few clusters (the t rule is undefined at 1 cluster and nearly empty at 2), and whether answer 5 means no minimum at all." No number proposed by me.

**R7 (required).** Add to section 15: "Answer 1: 'strict, using the auditors' maps' | Section 1 item 1, an operational test written by the drafter; the map of record is judged under it | Human lead". State whether the existing strict maps are re-judged under it.

**R8 (required).** Choice 18(b) is not computable below 30 clusters: add to section 12 an item "ADR-0033 line 457's cluster-bootstrap 90 % interval of τ̂ has no stated small-sample replacement; one must be registered before choice 18 can be applied."

**R9 (required).** Add to section 4: "The mechanics (section 13 item 4) are chosen, and the partition code hashed, before any partition is computed on the map of record. Every computed partition is kept." Mark the ⌊G/2⌋-to-A rule as the drafter's.

**R10 (required).** Add the propagation rows listed under Q2.

**Notes.** N1: C1 count 28 (LEAD_RULINGS_2) vs 29 (HUMAN_LEAD_WORDS_3 and draft). N2: the stratification change is conservative (Q4). N3: second-solver authors should get fixtures without first-solver answers. N4: borderline pairs not merged sits uneasily with "over-counting is the harmful error"; printing the strictest count beside G is the mitigation. N5: structural distinctness is used for capacity but disjointness and uniqueness remain textual (pre-existing in ADR-0033). N6: 13.5 ± 2.3 for a global shuffle reproduced (hypergeometric, 116 clusters, s.d. 2.29). N7: ADR-0033 fixes neither the divisor of V nor CR0/CR1; the implementation uses G − 1 and CR1, which my figures match. N8: tuning 100 taken whole per cluster is over-conservative.

## What I could not verify

The auditors' cluster judgements and any count (27/38/22/29); the C1 "rate 1.00 for five lineages"; the measured capacity and battery tables; the number of cross-evaluation components; that no model has been run anywhere outside the two worktrees I looked at; the seed registry state beyond the draft's statement.

`Astra review: NOT_PERFORMED`
