# Confirmation review — ADR-0025 (P10-I-S2), revision after the first review

- **Object:** `docs/decisions/ADR-0025-p10-i-s2-sequential-teacher-transfer.md`, 513 lines, SHA-256 `e4b166f2c2c1399611581858fbb01ea3dcb97603189d6b6b1b6377e315d60284`, at HEAD `26ea57b` (branch `claude/p10-i-specs`). Line numbers below are this revision's.
- **Reviewer:** the `arbor-auditor` subagent, model Claude Opus 5.5 (as I know it). I wrote the first review (`REVIEW_ADR-0025.md`). I did not write the draft, P10-S2's code or its records. This is independent engineering and mathematical review. It is **not** Astra validation and **not** human approval. `Astra review: NOT_PERFORMED`.
- **Read against:** ADR-0022 rev. 5 in full (§§1–17 and the addenda), `ADR-0022-addendum-combined-tasks.md`, `DIRECTION.md`, `CLOSURE_LEDGER.md`, `SEED_REGISTRY.md`, `results/p10s2-datagen-2026-11-16/prefreeze_record.json`, the P10-S2 bundle `partition.json` (read only), `docs/reviews/p10s2-qualification-2026-11-16/REVIEW.md`, ADR-0020 §12.2, sibling drafts ADR-0026 to ADR-0028 (cross-references only), `git diff c525898 HEAD` of this file.
- No training, generation, network access or long computation. This file is the only file I wrote in the repository. No git write. I did not open P10-S1's sealed recall values.

## Verdict: NOT READY

No finding is blocking. Both blocking findings of the first review are fixed, and so are most of the required ones. What keeps the draft from READY:

- **One projection is wrong.** The source-pool overlap is not the 600,000 lower bound. Measured from P10-S2's partition it is about 669,900. So A's split pool is about 198,500, not 254,000. The draft's conclusion about which teacher may miss the disjoint target is wrong (N1).
- **The revision lost one guard and one rule.** The second-acquisition guard on Δρ is gone (N2), and so is the rule that says how AGAINST-DENSE prints its two quantities (N3).
- **Seven changes from ADR-0022 are missing from the 22-row table** (N4).
- **The timing benchmark's quiet condition cannot be met** as written (N5).
- **Two closure-ledger items are not taken up or declined:** Lane D and ADR-0020 §12.2 (N9). There is also an unresolved conflict with ADR-0026 over WikiText-2 windows (X5).

Several of these need a choice by the lead, not only a text edit. So READY AFTER THE LISTED EDITS does not apply.

## 1. First-review findings

| Finding | Judgement | Note |
|---|---|---|
| B1 M-ii, C1/C2, cost removed on a wrong reason | FIXED | M-ii, C1/C2 (twelve arm-cells) and the five measures are restored as descriptive lines. Only TRAINING COST COMPARABLE and MA-gold are removed, each with a reason. The human lead's list is quoted (l. 53). C1/C2 cost checked in §3 below |
| B2 GEN dropped from the positive condition | FIXED | l. 31–33 and l. 331 match ADR-0022 §11.3 rows 6–8 |
| R1 Q1/Q2 called unchanged | FIXED | §3 row 3 |
| R2 population; 0.60 cut | FIXED | l. 96, l. 119. The supply is in fact in P10-S2's bundle (§3 below) |
| R3 sampling risk of Q3 | FIXED | Table l. 124–127 recomputed exactly (§3) |
| R4 overlapping pools | PARTLY FIXED | The split before generation and own-count availability are right. The projection l. 157 and §14 use the 600,000 lower bound as a point value, so the pool sizes and the "B may miss" conclusion are wrong. See N1, which includes my own share of this |
| R5 optional stopping | FIXED | Rules 1–3, l. 145–147 |
| R6 Q_check against the source pool | FIXED | l. 102, l. 105 |
| R7 Part Q outputs; seeds | FIXED | l. 109, l. 248. The sacrebleu cross-check of ADR-0022 §14.2 step 6 is not listed (N4 g) |
| R8 fallback | FIXED | l. 177 |
| R9 hidden retention failure | FIXED | Row 2 is read before row 3, over evaluable cells with at least four required (l. 314) |
| R10 ρ guard, pressure, ACQ1 | FIXED, but the fix introduced a new problem | The first draft's guard "RET read only if G_second ≥ 0.50; otherwise NOT CHALLENGED", which also governed Δρ, was dropped (N2) |
| R11 reading points | FIXED | (i)–(iv) settled. The narrowing of CONTROL-FAILED to M1 and M-append is not disclosed as a change (N4 b) |
| R12 fairness of D-append | FIXED | l. 218, l. 325. "Counted multiply-adds" is not defined (N12) |
| R13 oracle wording | FIXED | Fixed line identical to ADR-0022 §11.3 |
| R14 Part Q rehearsal reveals quality | FIXED, one gap | Sealed subset (l. 378). The rehearsal partition seed is not assigned anywhere (X2) |
| R15 out-of-lock packages | FIXED | l. 402, l. 420 |
| R16 Part Q engineering failure | FIXED, one gap | The regeneration comparison at recomputation (l. 179) has no tolerance and no consequence (N8) |
| R17 PAUSED as an outcome | FIXED | But a PAUSED stage whose extension is refused has no terminal state (N7) |
| R18 recomputation; panel minimums | FIXED, one gap | Tolerances by citation (l. 345). How a NOT EVALUABLE cell enters the "every cell" rules is not stated (N6) |
| A1–A8, A10 | FIXED or ANSWERED | A2's answer (offered, not recommended) is acceptable |
| A9 wall time | FIX INTRODUCED A NEW PROBLEM | The quiet condition is unmeetable at the end of a repetition (N5). No wall-time comparison is registered (correct) |
| Figures 26 s, 36 units, 178 s | FIXED | |

## 2. New findings

**N1 — REQUIRED — §4.3 l. 157, §3 row 6, §13 item 5, §14 table l. 429–433.**
*Problem.* P10-S2's partition bundle has 67,626 training-side, in-vocabulary sentences with both references outside Q/D_cal/D_con (`partition.json` `gold_pool`: 181,970 A keys and 132,151 B keys, 67,626 shared). So the A-exclusive sources number about 64,525 and the B-exclusive about 114,344. The overlap is therefore about 669,900; two independent estimates agree within 150. 600,000 is the lower bound I gave in the first review, and it corresponds to zero both-reference sentences. I called it a bound (R4: "≳ 600,000"), but I then made B-side estimates from it without saying they rest on the bound. That is part of how the drafter came to use it as a value. With the 4/5 split:

| | Draft | Recomputed |
|---|---|---|
| A's sources | 254,000 | about 198,500 |
| B's sources | 664,000 | about 650,100 |
| Expected accepted at P10-S2's yields | 33,000 (A) / 26,000 (B) | about 25,800 (A) / 25,400 (B) |
| Whole-pool generation | 3.5 h | 3.22 h |

The fraction that equalises the two expected counts is 0.804. Both reach 24,000 only for a fraction between 0.748 and 0.820. So 4/5 turns out to be well chosen, but for a reason the draft does not give. A, not only B, is within about 7% of missing the disjoint target.

The split does **not** bias qualification: Q1–Q4 read only both-reference panels, which never pass through the split. It does make the two capabilities' training populations differ. A's material is about one third sentences with a French reference and no German one. B's is about one fifth sentences with a German reference and no French one.

*Change.*
- Replace the projection paragraph with the figures above, labelled "estimated from P10-S2's partition; recomputed exactly at step 4 before any teacher runs".
- State that either capability may fall back to overlapping draws.
- Give 4/5's reason as "the share that equalises expected accepted counts at P10-S2's yields (0.80)".
- In §13 item 4, replace "the supply is not in the records" with "67,626 in P10-S2's partition (bundle `partition.json`); recounted before Decision 1".
- Correct §14's last scenario row to 198,500 / 650,100 and 3.2 h (6.4–9.7 h at six threads).

**N2 — REQUIRED — §8.3 AGAINST-DENSE l. 325; §8.1 l. 283.**
*Problem.* The first draft made Δρ NOT EVALUABLE in a cell where either arm had not acquired the second capability ("RET read only if G_second(X) ≥ 0.50"). The revision guards ρ only on G_first(V1) ≥ 0.50. An arm whose second stage learned nothing keeps ρ ≈ 1 trivially. A D-append whose second adapter does not train would then score DENSE AHEAD on retention against an M-append that learned and lost a little, and the reverse holds too.
*Change.* In l. 325, after "Δρ is NOT EVALUABLE if either arm's cell is not evaluable in any cell", add: "or if G_second < 0.50 for either arm in any cell (retention not challenged)". Apply the same guard to the M-seq/D-seq pair and to TASK-CODED SPARSE RETENTION.

**N3 — REQUIRED — §8.3 AGAINST-DENSE l. 325, §1 l. 26.**
*Problem.* AGAINST-DENSE yields two labels, one for ΔG and one for Δρ. §1 gives the line one Positive/Negative/Inconclusive value, and no rule maps the pair to it. The first draft said "The line prints both quantities, for example 'acquisition: DENSE AHEAD; retention: NOT DISTINGUISHED'". The revision dropped that sentence.
*Change.* Restore that sentence. In §1 l. 26 write "Printed as two labels (acquisition, retention); never merged into one".

**N4 — REQUIRED — §3 table (silent changes).**
I diffed ADR-0022 §§4–13 and §11 against ADR-0025 rule by rule. The 22 rows miss these changes:

- (a) The **words-only** ablation (marker read off; ADR-0022 §7) is dropped. l. 216 lists four controls.
- (b) **CONTROL-FAILED** narrowed. ADR-0022 §11.3 row 5 ("any cell", whole label) becomes M1 and M-append only, with the other arms printed (l. 304). The narrowing favours a positive ACQUISITION and must be disclosed.
- (c) **Hour cap.** ADR-0022 had a fixed 36 h, raisable once to 72 h, plus caps of 1.5 GB download and 6 GB new disk. ADR-0025 has P + 2R per part from its rehearsal, extendable (l. 351, §13 item 10). The disk and download caps are gone.
- (d) **ENGINEERING-FAILURE** loses "the oracle-routed ensemble's score differing from the teacher's own" (ADR-0022 §11.3 row 1). §8.6 rewrites the list without it.
- (e) **ρ is defined only if G_first(V1) ≥ 0.50.** This is new for the dense arms and the annotations. Row 14 mentions only the negative-zone order.
- (f) **New thresholds** 0.05 (MEMORY AHEAD and MEMORY ADDS OVER LOOKUP) and "at least four evaluable cells" (l. 314). The latter has no reason given; "a majority of six, as forgetting pressure" would do.
- (g) **sacrebleu cross-check** (ADR-0022 §14.2 step 6) not listed in Part Q. The pilot label is renamed. Intermediate snapshots U/4 and U/2 are new (l. 275) and are not costed.

*Change.* Add one row for each of (a)–(g), or restore (a), (d) and the cross-check.

**N5 — REQUIRED — §10 stage 7 l. 373–376.**
*Problem.* "Load average at most 2.0 at the start and end of each repetition".
- The benchmark runs six CPU threads. At the end of a repetition lasting more than a minute, the 1-minute load average includes those six runnable threads (about 6·(1 − e^(−t/60)), already 3.8 at t = 60 s). So the end condition fails on the benchmark's own load, and every repetition would be marked NOT ISOLATED.
- The figure 2.0 has no reason. The machine has 18 physical cores (`sysctl hw.physicalcpu`).
- "About 15 minutes" is unsourced. ADR-0022 §10.2 does not say which arms are timed.

No wall-time comparison is registered on the benchmark, and DIRECTION §7 is respected.
*Change.* Read the condition **before** each repetition: load average ≤ 2.0 after at least 60 s with no study process running. Record the end reading without testing it. Give the reason ("at most two busy cores of 18 besides the benchmark's six"). List the timed arms. Write "duration: an estimate, measured in the Part T rehearsal".

**N6 — REQUIRED — §8.3, §8.6 l. 345.**
*Problem.* A cell that is NOT EVALUABLE on recomputation has no stated effect on "in every cell" rules. Example: does it count against "G_first(M1) < 0.25 in every cell" or "RET passes in every cell"? ADR-0022 §11.2 row 1 made the mechanism NOT_EVALUATED.
*Change.* Add to §8.6: "A cell NOT EVALUABLE under the recomputation rule makes every line that reads that arm's cell NOT EVALUABLE: RECOMPUTATION (its per-cell table printed). The cell never counts as passing or as in a negative zone."

**N7 — REQUIRED — §4.4 l. 175, §8.6 l. 344, §15.**
*Problem.* PAUSED is a state. If the human lead declines an extension, no label is ever written. The combination (paused, not extended) reaches no label.
*Change.* Add a label: "STOPPED AT A RESOURCE CAP BY DECISION (stage, counts reached)". It is registered only when the human lead records that the stage will not resume. It is not negative, and the per-teacher or per-cell table is printed.

**N8 — REQUIRED — §4.4 l. 179.**
*Problem.* The recomputation regenerates 1,000 sources per teacher and "compares outputs". No tolerance or consequence is stated.
*Change.* Add: "Token sequences must be identical. Any difference is QUALIFICATION-ENGINEERING-FAILURE."

**N9 — REQUIRED — closure ledger rows 58 and 87; §13.**
*Problem.* Lane D (H17-INC) and ADR-0020 §12.2 (sequential addition of facts) are CARRIED INTO P10-I-S2 (candidate), "depends on ADR-0025 containing a retention measure for the first set". The draft mentions neither. Ledger row 124's "word count undefined" (length-ratio filter) is also not taken up. The thread count is.
*Change.* Add a §13 item. Suggested: "Lane D and ADR-0020 §12.2 are not taken up. RETENTION here is of a lexical capability under oracle task codes, not of a first set of facts, and §12.2's conditions (ρ against A6, set-A clusters) do not apply. The disposition is the human lead's (ledger §10 item 3)." In §4.2, define the word count as P10-S2's filter computed it (whitespace tokens after normalization, `studies/p10s2/filtering.py:57`).

**N10 — REQUIRED — §4.3 rule 6 l. 155; §6 "+1 training draw".**
*Problem.* "Disjoint draws" cannot come from three independent per-replicate +1 seeds. The text does not say how the disjointness is constructed. It also does not say whether the disjoint/overlapping decision is joint or per capability.
*Change.* "If both capabilities reach 24,000, one permutation per capability (seed 250916, listed) orders its accepted pool. Replicate r takes positions 8,000·r to 8,000·r + 7,999. Otherwise each replicate draws with its +1 seed from the whole pool. The decision is joint."

**N11 — ADVISORY.** 0.8⁶ = 0.262 (l. 418) assumes six independent cells. The two orders share a replicate's draw, as ADR-0022 §9 said. The control G on the 300-item subsample has its own denominator, which can fall below 0.30 when the full panel's is above it; state what happens then. "No arm is in overload" (l. 231): name the reference (P10-S0's overload was 2 facts per slot). "Transformers and seven companions" (l. 402): the requirements file pins 28 packages, 8 named and 20 transitive.

**N12 — ADVISORY.** Define "counted training multiply-adds per update" (forward and backward, batch 32, which operations), or cite a definition.

**N13 — ADVISORY.** The sealed Part Q rehearsal still shows the chosen filter setting and the yields. These are monotone in Q_fit precision. Nothing may change after it, so the leak is harmless; state it.

## 3. Numbers checked (my own code)

| Draft | Quoted | Recomputed | Result |
|---|---|---|---|
| l. 122 | 35/53/69/84 items for 0–3 errors | 35, 53, 69, 84 | match |
| l. 126–127 | tolerated errors 4/0 at 104/41; 29/8 at 416/164 | 4, 0, 29, 8 | match |
| l. 131 | one in six below 0.90 at true 0.92, 150–160 items | 0.146 (150), 0.184 (156), 0.141 (160) | acceptable |
| l. 157 | pools 254,000 / 664,000; accepted 33,000 / 26,000 | about 198,500 / 650,100; 25,800 / 25,400 | **wrong (N1)** |
| l. 157 | Q_check about 1,000 (A) / 3,400 (B) | 962 / 3,409 at Q_check shares | match |
| l. 431–432 | 77,000/256,000, 1.3 h; 185,000/615,000, 3.0 h | 1.26 h; 3.04 h | match |
| l. 433 | 254,000/664,000, 3.5 h | 3.22 h on corrected pools | wrong input (N1) |
| l. 427 | 12.3 / 14.1 ms; 0.095 / 0.36 s | 12.34 / 14.07 ms; 0.0948 / 0.3605 s | match |
| l. 441 | 42 store-type and 24 LoRA units; 7–13 h, 27–52 h | 14 and 8 per replicate; 6.7–13.0 h; 26.8–52.0 h | match |
| l. 442 | 36 units (22 / 14), 4–7 h | 18 + 2 + 16; 3.7–7.2 h | match |
| l. 443 | scoring 4–14 h | 4.1–13.7 h | match |
| l. 444, 448 | C1/C2 1.2–4.8 h; with recomputation about 2.5–9.8 h | 12 × 2.0–7.8 min, plus 0–1.3 min for D-sep's C2 switch, per replicate: 0.40–1.58 h. Three replicates plus Stage 0 (2.0–7.8 min): 1.23–4.88 h. Doubled for recomputation: **2.47–9.75 h** | match. The addendum's own three-replicate figure is 2.07–8.19 h for ten arm-cells |
| l. 446 | totals about 20–60 h / 40–100 h | 21.2–57.8 h / 41.2–96.8 h | match. Part T rehearsal, gates, routers and U/4–U/2 scoring are not included; say so |
| l. 401–406 | 936,320,520 B; 126,182,132 B; 1,188,183,868 B | `fetch_record.json`; `DOWNLOAD_LEDGER.md` l. 37 | match |
| l. 231 | 0.49 / 0.98; 1,152,577 | 4,002/8,192, 4,002/4,096; 2,001·576 + 1 | match |

## 4. Cross-references

| File | Line | What it says | What it must say |
|---|---|---|---|
| ADR-0025 | 253 | initialisation and test seeds "assigned in the programme-wide registry the lead will write" | "assigned in `SEED_REGISTRY.md` §4.2: initialisation 330201 + 10r + j, roles j = 0..7 as listed; calibration 330231 + 10i + j (i = 0, 1); rehearsal 330251 + j; test mode 330298, 330299; tests 934001–934999" |
| ADR-0025 / SEED_REGISTRY | 251, 378; registry l. 153 | Part T rehearsal "252001 + 100·i" with no count; Part Q rehearsal "on a rehearsal partition seed", not assigned in either file | count i = 0 only. Assign Part Q rehearsal partition-side seeds (for example 252901–252914, mirroring 250901–250914) and register them. Add 250916 if N10 is adopted |
| ADR-0025 | 243 | "The review found no overlap …" | "Checked by `seed_registry_check.py` at `26ea57b`: RESULT: PASS" (I re-ran it: PASS) |
| CLOSURE_LEDGER | 58, 87, 164 | Lane D and ADR-0020 §12.2 carried into P10-I-S2 (candidate) | ADR-0025 must take them up or decline them explicitly (N9) |
| CLOSURE_LEDGER | 124 | "Word count undefined" carried into P10-I-S2 | ADR-0025 §4.2 defines the word count (N9) |
| ADR-0026 | 111 | WikiText-2 validation panels go into a ledger that "ADR-0025 and ADR-0027 must exclude; whichever study freezes first writes first" | ADR-0025 §5.5 must cite the ledger. It cannot exclude spans without losing windows: the marker-like stratum is all 44 windows of the grid (`prefreeze_record.json` fixed-input checks), and step 2 requires 44. The two drafts must agree that ADR-0025's 44 windows are reserved first, or ADR-0026 must exclude them. Return to the lead |

## 5. Choices reserved for the human lead (§13)

Items 1, 2 (fallback invocation), 6, 8, 9, 10, 11, 12 and 14 are properly the human lead's (approval, budget, scope, downloads, the lead's own P10 list).

Items 3, 4, 5 and 7 are design choices the lead has already made and recommends. Showing them is acceptable, but item 5 must carry N1's corrected reasoning.

Item 13 restates choices the human lead already answered in ADR-0022 (two directions as capabilities, MPS). R-gloss-icl does not need him.

Missing from the list:
- the Lane D / ADR-0020 §12.2 disposition (ledger §10 item 3);
- the ADR-0026 window conflict;
- the scheduling of the 15-minute quiet benchmark on his working computer (DIRECTION §7).

Item 7's consequence (no forgetting in M-seq means RETENTION cannot be positive and the milestone is NOT ESTABLISHED) is stated in §13. NOT CHALLENGED — NO FORGETTING PRESSURE is a distinct printed label (l. 317). **§16 does not state it.** Add: "Retention on a task where the unprotected store does not forget. Then RETENTION is INCONCLUSIVE: NOT CHALLENGED, which is neither retention nor its absence."

## 6. Length (513 against 300–450)

The following can be cut without losing a rule:

| Section | Cut | Lines saved |
|---|---|---|
| §18 review record | to five lines plus a pointer to this folder | about 30 |
| §2 background | to the six rows a rule uses | about 8 |
| §13 items 3–7 | to one line each, since the reasons are in §§3–4 | about 10 |
| §14 | U = 8,000 column and the Part Q rationale prose | about 8 |
| §16 | items repeated from §5.4 | about 4 |

That reaches about 450. The rules in §§3–11 should not be shortened.

## 7. Commands and environment

```
python3 -I .../scratchpad/rev2_0025/checks2.py            # Wilson table, binomial risks, projections, cost arithmetic (output checks2.out)
python3 -I -c '<read-only json of results/p10s2-datagen-2026-11-16/prefreeze_record.json>'
python3 -I -c '<read-only json of agent-a91c79a181109bb9c/data/p10s2-pre-20261115/data/bundle/partition.json: gold-pool key sets and their intersection>'
uv run --locked python docs/reviews/p10-i-direction-2026-11-17/seed_registry_check.py   # RESULT: PASS
git diff c525898 HEAD -- docs/decisions/ADR-0025-...; grep over the files listed in the header
```

The scratchpad is `/private/tmp/claude-501/-Users-daniellaloush-dandush03-ArborLM--claude-worktrees-arborlm-consolidation-experiment-2b31c1/cfc0efd5-b7ca-4602-959a-07fe6b8d4e7d/scratchpad/rev2_0025/`.

Environment: Python 3.15.1 (standard library only, no repository package imported) for my checks; uv 0.12.15 with the locked environment for the registry checker. Darwin arm64.

The overlap figure in N1 is an estimate. It is exact for P10-S2's partition only up to the few thousand blocked or contraction-only keys, and it will change with the new partition.

No checker attempt failed. The one correction of my own earlier work is the use of the 600,000 lower bound in the first review (N1).

`Astra review: NOT_PERFORMED`. This review is not human approval.
