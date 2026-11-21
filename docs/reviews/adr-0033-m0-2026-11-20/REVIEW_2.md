# Confirmation review 2 of ADR-0033 (revision 2, commit `44879b4`)

Reviewer: `arbor-auditor` subagent (Claude Opus 5.5, `claude-opus-5-5`), 2026-11-20. Claude review is not Astra review. `Astra review: NOT_PERFORMED`. This is not human approval and not validation, and nothing here is a result.

**What was read.** ADR-0033 at `44879b4` (SHA-256 `80412f5f…e234`), in full.

**Hashes checked (all match the text).**
- `REVIEW_1.md`: `f7aef8b8…1e6c`.
- `SEED_REGISTRY_R5.md`: `19199e46…a865`.
- `seed_registry_check_r5.py`: `8ce47ab5…4611`.

**What was run.**
- `timeout 120 nice -n 19 python3 -I power_check2.py` (Python 3.15.1, `/opt/homebrew/bin/python3`, standard library only, about 1 s of CPU).
- Script: `experiments/_scratch/audits/adr0033_review/power_check2.py`, SHA-256 `0971b4e4…c786`.
- Output, verbatim: `power_check2.out.txt` beside the script.
- Nothing was downloaded or committed.

## Gating answer

**Yes, after the listed edits.** One of them, N1, is BLOCKING. It is an error in the wording I gave for B1, which the drafter adopted verbatim: as written, the power simulation would declare almost every part UNDERPOWERED. I0-a implements that analysis, so N1 must be fixed before Decision 1.

Section 17 holds nearly the right things. Choice 12 is missing from its held table (N6). The box in "For the human lead" still says "stage G-gen" without the rehearsal limit (N5).

## 1. Review 1 findings: status against the text

| Finding | Status |
|---|---|
| B1 | Closed as worded. **The wording itself is wrong (my error): see N1** |
| B2 | Closed. Box, §5, §13, §17, choice 8 and row 9 all agree. The box needs N5 |
| R1 | Closed. Boole's bound in §9.4; P defined |
| R2 | Closed. 20,000 simulations and a 2,000-run confirmation, both with MC SE |
| R3 | Closed. Choice 3, row 6, §6.5, §13 and §17 |
| R4 | Closed, except that G-load runs generated items before the generator record exists (N4) |
| R5 | Closed not as written: batch rule at 1,024. Acceptable (departure 1 below) |
| R6 | Closed not as written: 50 public items; 48 h cap. Acceptable. I recomputed the estimate: 8,200 to 9,800 scorings against 28,500, a ratio of 0.29 to 0.34. At a 1,024-token limit, "a third to two fifths" of the time is plausible |
| R7 | Closed. Under option 3 it needs N3 |
| R8 to R17 | Closed. R17 cites revision 5 by hashes that match |
| C1 | Closed not as written: the recommendation was withdrawn rather than corrected. Acceptable; needs the hedge in objection (d) |
| C2 to C7, C9, C11 | Closed |
| C8, C10 | Put to the human lead as choices 15 and 16. Acceptable |

## 2. The drafter's seven departures

| # | Departure | Ruling |
|---|---|---|
| 1 | Batch rule uses the 1,024-token limit | **Acceptable.** It is conservative: smaller batches cost only time |
| 2 | Public format choice on 50 items; rehearsal cap 48 h, his number | **Acceptable** |
| 3 | Under option 3, R7's rows become properties of the project's code, checked by the equivalence gate | **Acceptable with N3.** The gate as written (64 prompts, 64 new tokens) does not exercise left padding, long contexts or the decoder from ids to text |
| 4 | Hand labelling inside the sealed stage; only counts leave | **Acceptable with an edit:** the 200 outputs per evaluation are drawn by a registered seed, stratified over systems. δ_e is fixed before R1, so the labeller seeing outputs does not bear on it |
| 5 | G-gen rehearsed at proposed numbers; record of record at his G and domain list | **Acceptable with N4** (the generator must be frozen before G-load) |
| 6 | Union gap renamed G_U | **Acceptable.** It removes a clash with G |
| 7 | Templates' own default system messages recommended | **Acceptable.** Both options satisfy ADR-0032's "published template"; my position is neutral |

## 3. Findings

### N1. BLOCKING (my error in B1's wording). Two-stage resampling from 5 items per cluster counts sampling noise as between-cluster spread.

With G = 300 and the M0 draw "balanced over the G clusters", each cluster has about 5 items. Resampling items within a drawn cluster reproduces that cluster's observed 5-item mean. So the simulated between-cluster variance is τ² + s_w²/m, not τ².

My check (section C of `power_check2.py`; d = 0.3):

| True τ | Clusters × items | Between-cluster SD the naive simulation uses | Largest per-test power at δ = 0.03 (need 0.996) |
|---|---|---|---|
| 0.05 | 300 × 5 | 0.25 | 0.66 |
| 0 | 300 × 5 | 0.25 | 0.67 |

With the method-of-moments correction the reachable power is 1.00 in both cases. The same bias was in my Review 1 proposal at 60 × 25.

Replace the sentence "Each is drawn in two stages within strata: … then n/G_e items with replacement within each drawn cluster." with:

> Each is drawn in two stages within strata. First, G_e clusters are drawn with replacement from the M0 draw's clusters, allocated to strata as the sealed split will be. Each drawn cluster's deviation from its stratum mean is multiplied by λ = √(τ̂² / (τ̂² + s_w²/m̄)), where τ̂² is the method-of-moments between-cluster variance (truncated at 0), s_w² the pooled within-cluster variance and m̄ the mean number of M0-draw items per cluster. The simulated between-cluster variance is therefore τ̂², not τ̂² + s_w²/m̄. Second, n/G_e item differences per cluster are drawn with replacement from the cluster's own items, centred on the cluster's observed mean, and added to its shrunk mean.

Add to the "Floor from the clusters" bullet:

> τ̂_e is printed with its cluster-bootstrap 90 % interval. With about 5 items per cluster it is imprecise: at G = 300 its standard error in τ² is about 0.005, the size of τ² itself at τ = 0.07 (review 2, N1). The point estimate is used, as d_e is, by the approved rule.

**PENDING LEAD REVIEW:** whether the floor should use an upper bound of τ instead.

### N2. REQUIRED. Correct the figure (objection c).

Replace "Review 1's own run gives 19,349 items at τ = 0.10, G = 300, δ = 0.03 (product rule)" with:

> At τ = 0.10, G = 300, δ = 0.03 and d = 0.3, the size under Boole's bound is 20,418 items at 55 tests and 23,125 at 70, both above the 20,000 pool. Review 1's 19,349 used the product rule.

### N3. REQUIRED (option 3). Widen the equivalence gate.

Append to the equivalence-gate bullet of §5:

> The gate also covers:
> - batches at the registered batch size with left padding, every prompt compared with its batch-1 library output;
> - 8 prompts of at least 1,500 tokens, generated to 1,024 new tokens;
> - the project's decoder from ids to text, which must equal the library's decode on every raw output of R1, checked in a one-off step.
>
> Any difference is an engineering stop.

### N4. REQUIRED. The generator must be frozen before any model runs a generated item.

G-load runs "64 tuning items". Add "G-gen's record of record" to G-load's "Needs" in §13.

Add to §6.2's first line:

> The record of record of G-gen precedes G-load.

### N5. REQUIRED. Box consistency.

In the box's last bullet, replace "and stage G-gen" with:

> and a rehearsal of stage G-gen at the proposed numbers; G-gen's record of record waits for your G and domain list.

Add to I0-a in §13:

> Analysis and power simulation use the standard library and the locked `torch` only. `numpy` is not in the lock.

### N6. REQUIRED. §17 held table.

Add the row:

> | The smaller design | 12 | F (the scored size per part) |

### N7. REQUIRED. Answer to objections (a) and (b): what G is, and what a cluster is.

Replace the §6.2 "Families and clusters" requirement with:

> - **Families, lineages and clusters.** At least 12 families (strata). Each rule shape is registered with a lineage: the hand-written base rule, a distinct solution procedure, from which it derives. Shapes made mechanically from one base rule (by changing parameters, order, negation, names or surface frame) share a lineage. **The cluster, for G and for every bootstrap, is the lineage.** G is the number of lineages per part.
> - **G is the number written, not a number tuned.** For a fixed n, more clusters never lower the power, so every lineage that passes the G-gen gates is used. The human lead registers a minimum before G-gen's record (proposed: 300). If fewer can be written, the count written is registered, and the table below shows what it can reach.
> - **Checks.** The auditor reads one rendered item from each of 50 random pairs of lineages in one family and records any pair that is the same procedure. Such a pair is merged into one lineage before the record. M0 also prints, descriptively, the variance component between shapes within a lineage beside τ̂.

Add to §8, after "Why 20,000":

> **What G can reach** (Boole's bound, 55 tests, d = 0.3; smallest δ reachable at 20,000 items / at any number of items; review 2, `power_check2.out.txt`):
>
> | τ | G = 60 | G = 150 | G = 300 | G = 600 | G = 1,200 |
> |---|---|---|---|---|---|
> | 0.03 | 0.024 / 0.017 | 0.020 / 0.011 | 0.018 / 0.008 | 0.018 / 0.005 | 0.017 / 0.004 |
> | 0.05 | 0.033 / 0.028 | 0.024 / 0.018 | 0.021 / 0.013 | 0.019 / 0.009 | 0.018 / 0.006 |
> | 0.10 | 0.058 / 0.056 | 0.039 / 0.035 | 0.030 / 0.025 | 0.024 / 0.018 | 0.021 / 0.013 |
> | 0.15 | 0.086 / 0.084 | 0.056 / 0.053 | 0.041 / 0.038 | 0.031 / 0.027 | 0.025 / 0.019 |
>
> τ is not known before M0, and no model may run before the generators are frozen, so no pilot τ is possible without breaking that order. The human lead chooses G's minimum with this table in view. The lead registers which τ he treats as the planning worst case (proposed: 0.10).

**Option for the human lead only (PENDING LEAD REVIEW; it would amend an approved rule).** Under the approved power rule, templates are clusters, i.e. random effects. The sealed split uses the same templates as development and teaching, and part B already carries the generalisation question. Treating lineages as strata (fixed) instead would remove the τ floor. That is a change to the approved rule's inference target, and it is his to make or refuse. It is not the lead's.

### N8. REQUIRED. Objection (d): hedge for C1's facts.

Add under the §4.2 A/B table:

> Every [D] entry in this table is the reviewer's memory. Before choice 1 is put to the human lead, the lead re-reads each one at its source: the model cards' thinking switch and release dates, and the library's release notes for the Qwen3 and GLM-4 classes. This means reading web pages only; no file is fetched into the ledger. Until then the table lists what to check; it is not a comparison.

### N9. RECOMMENDED. Objection (e): my recommendation on the package route, for the human lead.

**Mine: option 2 for M0.** The drafter recommends option 3; the human lead should see both.

Reasons for option 2:
- In M0 the library is the measuring instrument. A widely used reference implementation at a hashed version is less likely to carry an undetected error than new code for two architectures.
- GLM-4-0414 has post-norms and partial rotary embeddings ([D] UNVERIFIED). Option 3's gate checks only a sample of prompts.
- It is days of work, not one to two weeks.
- M1a can probably attach the memory to library modules by subclassing or forward hooks.

Costs of option 2:
- A large third-party library sits in the registered path. It is pinned, not audited.
- If M1a cannot attach to the library, the condition "the model code M0 measured binds M1 to M5" forces the references to be measured again: one to four days of machine time.

Option 3 is the better choice if he weighs owning and auditing every line of the measuring path above calendar time, or expects M1a to need its own model code anyway.

Option 1 is not recommended by either of us.

## 4. My own errors, kept

- **N1.** The B1 wording I gave in Review 1 resampled items within clusters without shrinkage, which counts within-cluster noise as between-cluster variance. Review 1's section C used the analytic model and was not affected. The prescribed simulation was.
- **Review 1's 19,349.** It used the product rule after I had recommended Boole's bound (N2).

`Astra review: NOT_PERFORMED`. Claude review is not Astra review.
