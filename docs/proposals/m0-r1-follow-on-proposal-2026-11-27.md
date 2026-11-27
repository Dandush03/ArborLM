# M0 follow-on proposal: new private reasoning lineages after R1 (2026-11-27)

**Status: PROPOSAL ONLY. NOT APPROVED.** Nothing here is authored, implemented, generated or run. No lineage may be written before the human lead approves a specification. Drafted by the scientific lead (Claude Fable 5.2) for the coordinating lead, from the committed records on `claude/m0-impl` and ADR-0033 addendum 1 as approved (`2c944302` on `claude/m0-spec`). It follows the human lead's answer "5 agree" (`HUMAN_LEAD_WORDS_15.md`): R1 is not repaired inside M0, and M0 is not held for this.

`SPEC: PENDING ASTRA REVIEW` · `Astra review: NOT_PERFORMED`

## 1. The problem

R1 is registered at 6 lineages in 5 clusters out of 122 written lineages (43 base names, 25 clusters in the map of record): 4 clusters / 5 lineages in the teaching part and 1 cluster / 1 lineage (`R1.temporal_weekday_shift_r6`) in the held-out part. A held-out part of one cluster has no standard error, so every outcome that needs an interval reads NOT EVALUABLE, ONE CLUSTER (addendum section 9 item 5); the teaching part has 3 degrees of freedom, and its strictest count (all borderline pairs merged) is 1. Since the private evaluations stay gate candidates (`HUMAN_LEAD_WORDS_13.md`), R1 can give per-item accuracies and nothing more, and it cannot support any statement about held-out reasoning.

## 2. What the approved text allows

It allows no new lineage by any route. The sentences:

- Section 7 item 5: "**No new lineage and no replacement shape.**" Item 6: "a lineage it drops is not re-authored."
- Section 4 item 7: "no link, no borderline pair, no lineage, no cluster and no cluster identity is added, withdrawn or judged again, by anyone, for any reason". Adding a node is therefore named as a change of the map; it is not a grey area.
- Same item: "the candidate list is hashed at stage 2 and is not extended"; "a later record may differ from an earlier one only by the removal of lineages"; "A lineage removed under any record is not brought back."
- Section 4 item 8: "Exactly one partition is ever computed"; no stream with the label `cluster-partition` is computed again.
- Section 7 item 10: "**The bound is read once.** … After the fresh run no cheap-rule script is run again on any lineage for the record".
- ADR-0033's stage table lets G-gen's record be "made again if either changes" (his G, his domain list). The addendum withdrew the minimum G and says a change of the domain list "changes no lineage, no link, no candidate and no part". A re-record is not a door for new lineages.

What each route would re-open:

| Object | Rule today | What new lineages would need |
|---|---|---|
| Map of record (345 lineages, 92 clusters, 99 borderline pairs) | frozen at its hash | new nodes, and a judgement of each against all 92 clusters; either the map is changed (forbidden) or a second file is created that reads it |
| Partition | computed once | a part for each new cluster without a shuffle |
| Fresh shortcut run | one run, no second | a run of rule scripts on new items: a second run in all but name unless it is a different study's |
| Stage-2 conditions, second solvers, capacity | read once on the survivor list; capacity demand depends on each part's G | all of them again for the new lineages; a larger G in part B raises the demand on `temporal_weekday_shift_r6`, which could then fail a gate it has passed |

So: **any route that puts new lineages into registered R1 is an amendment that overrides the human lead's own decision 21 and the sentences above**, by an explicit exception of the kind ADR-0016 was to ADR-0015. **A route that leaves every M0 record untouched and builds a separate evaluation is a new study** (a new ADR, or a new addendum that adds an evaluation and changes no sentence of addendum 1). There is nothing in between.

## 3. Why R1 lost so many (read from the status record and the audits)

Of 116 unregistered R1 lineages, 28 were superseded by a later version of themselves, 48 carry no single committed reason, and the 40 with a reason fall into six recurring kinds:

1. **A shortened procedure is right too often** (the largest kind): search cut at five steps (`order_compare_r5` +0.45, `road_reachability_r5` +0.44), odd cycles up to length 7 (`graph_bipartite_r5` +0.47), high bits only (`nim_xor_r5` +0.33), a greedy or first-found answer (`minimax_tree_r5`, `mst_cost_r4`, `temporal_critical_path_r5`, `topological_order_r5`), one input ignored (`containers_stack_piles_r4`, `tracking_accounts_r5`).
2. **A step is absent at some level.** `venn_counting_r5`: four truncated formulas, each exact at particular levels, because the level fixed which overlaps were empty.
3. **A convention never varies.** `equivalence_exchange_rates_r6`: a rule that never reads the direction of conversion was right on all 9,000 items at all seven levels.
4. **A surface count predicts the answer**: "most accused" (`one_culprit`), "fewest negated tests" (`attribute_rule_r5` +0.58), counts of sentence kinds (`equivalence_classes_r5`), number of groups (`categories_follow_r5` +0.54), 0.75 × meetings (`activity_selection_r5`).
5. **The option set or a redraw leaks.** Redrawing when the answer is 0 (`event_timeline_r6`, `spatial_relative_directions_r6`); options built from a property of the answer (`kinship_ancestor_r4`); an option that is never the answer (`stable_matching_r5`); and options named per item from a large pool with five or six options, which puts any fitted constant about 1/k below chance and over the two-sided bound (`spatial_grid_walk_r5` −0.165, `swap_tracking_r5` −0.161; not exploitable, and dropped by the rule as written).
6. **Too few distinct items, or a repair that made a new shortcut.** `elimination_josephus` (two parameters), `order_extreme` (two structures per level); `containers_queue_line_r5` (+0.79 from index arithmetic "created by the fix-3 rebuild"); `instant_runoff`, `stable_matching` and `pet_owners` rebuilt and still over.

The habits behind them: starting from textbook puzzle types, where a well-known approximation agrees with the exact method on small cases; making difficulty a matter of size, so that level 0 is small enough for the short cut to be exact; repairing by rejecting items; and writing the rule battery after the lineages, so that each audit round found rules the authors had not tried.

## 4. Options

Arithmetic from addendum section 6 (CR1, t test, 20,000 pool; nothing measured; τ unknown). Smallest margin reachable: at G = 5, 0.076 / 0.123 / 0.244 for τ = 0.03 / 0.05 / 0.10; at G = 13, 0.042 / 0.066 / 0.129. So **at 6 held-out clusters none of the registered margins 0.02, 0.03, 0.05 is reachable unless the clusters differ by under about 0.02; at 12, the 0.05 margin is reachable only for τ up to about 0.035**, and under his choice 18 (b) a part reads reachable in at most about a fifth of draws even then. What more clusters buy is an interval where there is none today (5 or 11 degrees of freedom instead of none). They most likely do not buy an evaluable margin.

Yield, from R1's history: 6 of 122 written lineages (4.9 %), 6 of 43 base names (14 %), 5 of 25 clusters (20 %) — and that 20 % was reached over several repair rounds (versions up to `_r6`), which a single-pass pipeline would not have. A new cluster must also be distinct from, and not borderline to, clusters already in the map, which the map's 99 borderline pairs suggest is hard. Clusters to write for a given number registered: **5 more: about 25 at 20 %, about 100 at 5 %; 11 more: about 55 to 220.** For a set split in half, double these. The discipline of section 5 is meant to raise the yield; it is untested.

| | (a) Leave R1 as registered | (b) R1 supplement | (c) New evaluation R3 | (d) R3 in stages, with a stop rule |
|---|---|---|---|---|
| What | R1 is reported as descriptive: accuracies, no interval for the held-out part | N new lineages added to R1's held-out part under a new addendum, each through every gate, with its own pre-registered shortcut run | A new private reasoning evaluation from scratch under the whole pipeline: its own map file, its own partition (new label), its own run, its own record | (c), written in registered batches (proposed 12 procedures each); after each batch the count registered is read against a number fixed beforehand, and the work stops if it is under it |
| Re-opens | nothing | decision 21, section 7 items 5, 6 and 10, the candidate list, capacity for the existing held-out lineage | nothing of M0; it reads the frozen map to exclude procedures already there | as (c) |
| Cost | none | authoring, second solvers, pair audit, map judgement, shortcut run, capacity for 25 to 220 clusters; an exception to an approved text | about twice (b) for the same held-out count, since half goes to the teaching part | bounded: one batch, then his decision |
| Risk to M0 | none | high: the held-out part becomes 1 old cluster plus N written later, by other rules, by authors who know the split and M0's state; teaching and held-out parts are no longer comparable; the existing lineage can be lost at the new capacity demand; a precedent for adding after a freeze | low, if R3 is never pooled with R1 and is frozen before any model scores an R3 item | as (c) |
| Can reach | ONE CLUSTER for held-out reasoning in R1; R2's held-out part (6 clusters) is the only private held-out reasoning reading | G of 1 + N in name; an interval that mixes two authoring regimes | intervals on its own G − 1; most likely still UNDERPOWERED at the registered margins below about 13 clusters per part | the same, or a recorded early stop with the measured single-pass yield |

**The assignment rule in (b), and why it is not a second partition.** The only defensible rule is: every supplement cluster goes to the held-out part, stated before any is written; a new lineage linked or borderline to any cluster already in the map is not admitted. No stream is drawn and no cluster is chosen, so nothing is shuffled twice. But it is an assignment made with the first split in view, which is what "computed once" was written to prevent. The drafter does not recommend (b).

**For (c) and (d):** R3 lineages are admitted only if an independent auditor judges them distinct from, and not borderline to, every one of the 92 clusters of the frozen map (which is read and never changed); a re-written version of a procedure whose lineages were dropped is not admitted. R3 is outside M0's registered domain list (adding to it "needs an amendment before the freeze"), so it would serve P11 as a separate instrument and would not change M0's reasoning reading.

## 5. Design discipline for new reasoning lineages

Each rule is checked by the author before submission and by an independent auditor before the run. None changes the bound of 0.15, two-sided, at all seven levels.

1. **Every step at every level.** No component of the procedure is absent, empty or constant at any level, reserve levels included; levels scale sizes, never which steps are needed. (`venn_counting_r5`.)
2. **No truncated procedure is exact or near it.** For depth, search horizon, number of rounds and number of operands, the author states the shortest version of the procedure and shows that at level 0 it is within the bound. If the smallest honest instance cannot do that, the lineage is not written. (`order_compare_r5`, `road_reachability_r5`, `graph_bipartite_r5`, `nim_xor_r5`.)
3. **No single convention decides.** Every direction, order, sign and "which end" is drawn per item, and a rule that fixes any one of them is at chance for closed answers and right on under 10 % of items for open answers, where the base rate is 0; in practice the answer must depend on three or more such independent draws. (`equivalence_exchange_rates_r6`.)
4. **Named approximations are listed first.** For each procedure the author lists the greedy, first-found, majority and "ignore one input" versions before writing the generator, and they go into the battery. A procedure whose textbook approximation agrees on most small cases is not chosen. (`mst_cost_r4`, `minimax_tree_r5`, `instant_runoff_r5`, `stable_matching_r5`.)
5. **Surface counts carry nothing.** Counts of sentences, mentions, negations, entities and option positions are balanced by construction, not by rejection. (`one_culprit`, `attribute_rule_r5`, `equivalence_classes_r5`.)
6. **The fitted constant sits at chance.** Closed answers use a fixed label set with answers uniform over it, or at least eight options at every level; never five or six options named per item from a large pool. (`spatial_grid_walk_r5`, `swap_tracking_r5`.)
7. **Every option can be the answer, and options are not built from the answer's properties.** (`stable_matching_r5`, `kinship_ancestor_r4`.)
8. **No redraw on the answer.** Rejection only where the item would be ill-posed, stated in the item's convention; a zero, empty or "none" answer is a valid answer. (`event_timeline_r6`, `spatial_relative_directions_r6`, `conditional_chain_r5`.)
9. **Capacity before wording.** The count of distinct structures per level is computed against the demand before the lineage is submitted; at least three free structural parameters. (`elimination_josephus`, `order_extreme`.)
10. **The battery is fixed before the lineages, and there is one pass.** The generic cheap-rule battery (constants, option positions, surface counts, truncations, one-convention rules) is committed and hashed before any lineage is written, and authors run it on their own seeds. An independent auditor then adds rules once; the battery is hashed; one run on fresh seeds; a lineage over the bound is dropped. No repair round. (`containers_queue_line_r5`; the successive audit rounds.)

## 6. What should not be done

- **Reinstate a dropped lineage, or re-write its procedure under a new name.** "A lineage removed under any record is not brought back"; the human lead's "Let them stand" (`HUMAN_LEAD_WORDS_11.md`) covered all fifteen fresh-run drops.
- **Run a rule script again on any M0 lineage, or change how the fitted constant is read.** The bound is read once; a second reading would be chosen with the first in view.
- **Recompute the partition, or compute any `cluster-partition` stream again.** One changed input reshuffles every cluster, and the first split has been seen.
- **Move a teaching cluster to the held-out part.** It is a choice made with the split in view, it breaks borderline pairs across parts (the teaching part's strictest count is 1: its clusters are tied together), and it would make teaching-eligible material held-out after the fact.
- **Count R3 or a supplement into R1's G, or describe either as repairing R1.**
- **Write any lineage after a model has scored M0 items, with those scores in the author's view.**

## 7. Decisions for the human lead

1. **Which option?** (a) / (b) / (c) / (d). *Recommendation: (a) for M0 as already decided, and (d) as a separate study.*
2. **Is it needed at all?** Whether P11 needs a private held-out reasoning reading beyond R2's 6 held-out clusters. *Recommendation: decide this first; if R2 suffices, stop at (a).*
3. **Target and batch size** for (d): proposed 12 procedures per batch, at most four batches. *Recommendation: as proposed; the numbers are his.*
4. **The stop number**, fixed before batch 1: proposed stop if a batch registers fewer than 3 clusters. *Recommendation: as proposed.*
5. **Admission against the frozen map:** exclude any R3 lineage linked or borderline to an existing cluster, or let a linked one inherit that cluster's part. *Recommendation: exclude.*
6. **The bound for R3:** 0.15 two-sided as in M0, or another reading of the fitted constant. *Recommendation: unchanged; rule 6 of the discipline designs for it.*
7. **Timing:** R3's record before any model scores an R3 item, and its authors given no model result. *Recommendation: yes to both.*

Before any lineage is written, the following need his recorded approval: the specification itself (new ADR), with the discipline, the hashed battery, the admission rule, the partition label and seed, the run seeds, the batch and stop numbers, who authors and who audits, and the statement that R3 is never pooled with R1.

## 8. Non-claims

- No lineage, item, rule or model has been written, generated or run for this proposal. Every figure is copied from committed M0 records or from the addendum's arithmetic; the count of 43 base names is the drafter's own count of lineage ids with their version suffix removed.
- The yields are R1's history, not a forecast; the design discipline is untested and may not raise them.
- Nothing here shows that R1's six registered lineages are free of shortcuts; the gate holds only against the rules that were written.
- More held-out clusters would give intervals; this proposal does not claim they would make any registered margin evaluable, and section 4 says they most likely would not.
- No capability, parity or efficiency claim is made or supported. This is the drafter's proposal, not an approval and not an Astra review.

Astra review: NOT_PERFORMED
