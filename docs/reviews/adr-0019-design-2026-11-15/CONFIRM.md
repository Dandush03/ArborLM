# ADR-0019 revision 3 (P9-II): confirmation review

- **Reviewer:** Claude Opus 5.5 (`claude-opus-5-5`), specification auditor, in a context separate from the integration work. No git or GitHub action and no tracked-file edit. Astra review: NOT_PERFORMED. This is not Astra validation and not a human approval.
- **Object:** `ADR-0019-robust-sparse-address-learning.rev3.md` (431 lines) in the session scratchpad. I diffed it against revision 2 and revision 1 and checked it against my `REVIEW.md` (B1–B3, M1–M9, 17 minors), the lead's §18 rulings and the human lead's requirements list.
- **Environment:** as in `REVIEW.md` (macOS 27.2.1 arm64, Python 3.12.14, torch 2.8.0, `uv run --locked`). The new scripts c7 and c8 pass ruff with the same command as before.
- **What I ran:** c7 and c8, re-scoring only, with no training:
  - P9-I **registered** R1 and W7 snapshots (historical and already observed), on the regenerated P9-I registered draw (seeds 182001 + i);
  - the P9-I review's W7 models on the unit-test sets p9i-test-0/1/2.

  My forward reproduces the backbone's next-byte loss of 2.3494 nats recorded in the P9-I review.
- **What I did not run:** nothing on rehearsal sets 3–5 or seeds 190001+, and no registered stage.

## Verdict: **READY AFTER the text edits listed in §4** (paste-ready)

No blocker is open. Two majors remain, and both are rules that a measurement now shows to be vacuous or degenerate:

- **R1:** the LM criterion is vacuous through TESTBED-LIMITED.
- **R2:** the slot-based escape threshold is reached by an untrained model.

Each is fixed by the text below and needs no new cells. The other remaining items are minor. Once the edits in §4 are applied verbatim, the specification is ready for the lead's self-approval without a further review round. If the lead changes any of that text, the changed passage needs a re-check.

## 1. Disposition of the original findings

| Finding | Status in revision 3 |
|---|---|
| B1 paired readings, A0 path | **Fixed.** Paired rule with d ≥ 4 / ≤ −4. NEGATIVE CONTROL FAILED is now paired. ANSWER-ONLY RELIABLE is row 3. A0 comes first in carry-forward. Hypothesis readings are paired, and CONTRADICTED is added. Minor gap: R5. |
| B2 G5 and the LM criterion | G5 is **fixed** (tensor hashes and logits with the memory disabled). The LM criterion is **adopted but vacuous as ruled**: see R1. |
| B3 schedules against 4U | **Fixed.** Schedules are in exposures per fact; the 4U readout decides the class; the U readout of A2 and A4 is MID-SCHEDULE. Ruling 1 (Stage 3 runs only for constant-objective arms) is sound. |
| M1 A5 split, slot-based collapse | The split is **fixed** (A5-C, A5-D, H19-F, H19-G). Slot-based categories are adopted, but the escape threshold is too low: R2. |
| M2 A4 endpoint | **Fixed** (top-k(t) at temperature 0.2; G4 checks the endpoint bit for bit). k_0 as a fraction of N with grid {N/8, N} is sound. |
| M3 AdamW reset, dependence measure, A3 | **Fixed.** The reset is in §4 and G4. SUPERVISION-DEPENDENT is function- and collapse-based. A3 is dropped and the drop recorded. Minor gap: R6. |
| M4 bounds, estimands, probe accuracy | **Fixed.** Bounds are per draw (0.69 / 0.53 / 0.47), §8.7 exists, and probe accuracy is recorded. |
| M5 fresh draws | **Fixed** (draws 9–14). |
| M6 precedence, labels, denominators, LEAKAGE | **Fixed** (stage status, row 6, supervision in the label, 14 and 7 evaluated cells, condition 5). Minor gap: R5. |
| M7 budget | **Fixed** (Budget A 4 h, Budget B 3 h, no reduced Stage 2, Stage 3 by remaining time). Arithmetic checked in §3. |
| M8 G1 reserves, G4, outputs, launch | **Fixed.** |
| M9 A1-S | **Fixed** as ruled: paired reading, and A1-S runs at Stage 2 with any supervised arm. A1-U was not adopted; that is the lead's call. |
| Minors 1–17 | All applied or ruled on as listed in §17, and I accept the rulings. Minor 4 (the probe from the calibration stream) has a side effect: R4. |

## 2. The lead's rulings

### Condition 3 is reachable and is not passable alone (c7)

The probe (the first 512 sites of the calibration stream, cell's facts only) holds **475 distinct facts at 4,096, 506 at 16,384 and 512 at 65,536**. Only about 37, about 6 and 0 facts respectively appear twice. Condition 3 therefore needs at least 238 / 253 / 256 distinct top-1 slots and no slot top-1 for more than 10 sites (share ≤ 0.02).

| Model | Probe accuracy | Distinct top-1 / facts | Largest share (count) | Condition 3 |
|---|---|---|---|---|
| R1 4,096 seeds 1801 / 1802 (P9-I registered) | 1.000 / 1.000 | 0.998 / 0.992 | 0.0039 (2) | holds |
| R1 16,384 (both seeds) | 1.000 | 1.000 | 0.0039 (2) | holds |
| R1 65,536 seed 1801 | 0.965 | 1.000 | 0.0020 (1) | holds |
| W7 escaped (p9i-test-2) | 0.953 | 0.928 | 0.0059 (3) | holds |
| W7 partially escaped (test-0) | 0.172 | 0.492 | 0.045 (23) | fails |
| W7 collapsed (test-1; P9-I registered 4,096) | 0.05 | 0.024; 0.002–0.004 | 0.53; 1.00 | fails |
| W7 at initialization (untrained) | 0.023 | 0.331 | 0.039 (20) | fails |
| R1 codes with untrained keys and values (spread, consistent, useless) | 0.023 | 0.959 | 0.0059 (3) | **holds** |

Every genuinely working model passes with a wide margin. A spread-but-useless arm passes condition 3, but it fails condition 1 by a factor of 40, and conditions 2 and 4 cannot make up for that. Condition 3 does not let a degenerate model through. Its job is to reject "accurate through a few hub slots", and it does that.

### Onset threshold "distinct top-1 ≤ 32"

This is sensible. Collapsed models show 1–13, untrained ones 162. The threshold sits well between the two at every size because probe facts number 475–512.

### Escape threshold "≥ 0.25 × probe facts": unsound (R2)

The untrained W7 query already reaches 0.331. So:

- "never collapsed and separated" is reached by a query that has learned nothing;
- escape can fire while accuracy is still about 0.17 (test-0 is at 0.49);
- the calibration tie-break ("earlier median escape update; never escapes counts as later") ranks a never-collapsed cell behind a collapsed-then-recovered one. That is a perverse ordering.

### TESTBED-LIMITED is a loophole as drafted (R1, c8)

With the memory active on the backbone's corpus rows, against the backbone's 2.3494 nats:

| Model | Next-byte loss rise |
|---|---|
| A6 (= R1), 4,096 / 16,384 / 65,536 | +14.3–14.7% / +13.9% / +13.6% |
| Escaped W7 | +13.4% |
| Partly escaped W7 | +8–9% |
| Collapsed W7 4,096 (P9-I registered) | **+5.05%** |

Consequences:

- A6 will be above 5% in every draw at every size, so TESTBED-LIMITED will be printed everywhere. The criterion then bars nothing, including an arm that damages next-byte prediction far more than the oracle does.
- Without the clause, every working arm, and even the collapsed baseline, would be LM CAPABILITY REDUCED.

The absolute 5% line cannot work in this testbed. Only a comparison with A6 on the same draw is informative.

### Other rulings

- **Ruling 4** (at most two arms advance besides A0, Stage 2 ≤ 40 cells, Budget B 3 h): sound. The arithmetic is in §3.
- **Ruling 7** (denominators): sound.
- **Ruling 8** (row 4 does not require IMPROVES ON A0, with the paired label printed): sound. The label prevents over-reading.
- **The drafter's three readings:**
  - slot-based categories: accepted, with R2;
  - an LM-flagged arm is neither RELIABLE nor carried: accepted, with R1;
  - no substitution for a scheduled first arm: sound, because Stage 3 is a probe.

## 3. Precedence and recount

### Precedence

- **Classes** (§8.4): NOT_EVALUATED → RELIABLE (≤ 1 failed of ≥ 14 / ≥ 7 evaluated, no LM flag) → UNRELIABLE → FAILS. Complete. An arm with 16/16 successes and the LM flag prints UNRELIABLE; the reason should be printed with it (R7).
- **Outcome** (§8.6): complete and exclusive.
  - A0 RELIABLE goes to row 3 before rows 4–6.
  - Stage 2 not COMPLETE goes to row 6.
  - NEGATIVE CONTROL FAILED with no label-free arm reliable goes to row 2.
  - A1-S is excluded from rows 4–8.
- **One wasted path (R5).** If NEGATIVE CONTROL FAILED at 4,096 and the only RELIABLE arms are A1 or A2, the Stage 1 gate ("at least one arm other than A1-S is RELIABLE") still runs Stage 2 with A0 alone, while the outcome is already INCONCLUSIVE.

### Cells

- Calibration: 4 × 2 × 2 + 6 = **22**.
- Stage 1: 7 × 16 + 2 × 8 = **128**.
- Stage 2: (1 + 2 + 1) × 8 + 2 × 4 = **40** at most; 8 + 8 = **16** at least.
- Stage 3: 4 × 2 = **8**, or 3 × 2 = **6** when A0 is the selected arm.
- Total at most **198**. All confirmed.

### Budget (rates from c5; makespan with six workers)

**Budget A (4 h).** Calibration takes 4 rounds × 92 s = 0.10 h; Stage 1 takes 22 rounds × 92 s = 0.56 h, plus 0.06 h of evaluation. Twice Stage 1 is 1.24 h against about 3.7 h remaining.

**Budget B (3 h).** Largest Stage 2 makespan by rate:

| Rate | Rounds × time per cell | Training | Twice, plus evaluation |
|---|---|---|---|
| W7 | 7 × 462 s | 0.90 h | 1.9 h |
| Slowest P9-I | 7 × 639 s | 1.24 h | 2.6 h |

Stage 3 needs 2 × 0.29 = 0.58 h of what remains after Stage 2's actual charge (at least 1.7 h projected). All confirmed.

Caveat: A4's read at k = N at 16,384 for 2U updates is unmeasured. The "most expensive measured phase" rule in §10 covers it, but only after the rehearsal.

## 4. Remaining findings and paste-ready text

### R1 (major) — the LM criterion is vacuous through TESTBED-LIMITED

Replace §8.4 "LM capability" parts (b) and (c), and ruling 5 (c), with:

> (b) **The system with the memory active, relative to the oracle reference.** For each cell, r = (next-byte loss with the addition active − frozen backbone's) / frozen backbone's, on the backbone's 2,048 corpus rows. A cell is flagged if r > r(A6, same draw and size) + 0.05 *(lead's choice)*. An arm flagged in more than one cell at a size prints **LM CAPABILITY REDUCED** there: it is not RELIABLE, does not advance and cannot be carried forward. r is printed for every arm and for A6. (c) The absolute rise is printed beside it for every arm. In the review's measurement A6 itself raised the loss by 13.6–14.7%, an escaped W7 by 13.4% and a collapsed W7 by 5.05%. The criterion therefore measures damage beyond what any memory read at the fixed positions causes, which is a property of this testbed, and says nothing about a deployed system (§13).

Delete TESTBED-LIMITED everywhere: §3, §8.4, §17, §18.

### R2 (major) — the escape threshold is below the untrained level

Replace the §8.1 definitions of Escape and Separated with:

> **Escape:** the first later record from which, to the end, the slot part of success condition 3 holds (distinct top-1 ≥ 0.50 × probe facts and largest top-1 share ≤ 0.02). **Separated** (for cells with no collapse onset): the same condition holds at the readout. (An untrained W7 query has 0.33 × probe facts and largest share 0.039 in the review's measurement, so a lower threshold would call an unlearned query separated.)

Replace the tie-break in §6 with:

> … the secondary criterion: the earlier median, over the two draws, of the time to first success (§8.7; a cell that never succeeds counts as later than any that does).

### R3 (minor; a listed human criterion) — "address recall" has no registered criterion

Add to §8.4 "Annotations":

> **ADDRESS RECALL** (A1, A2): the median over cells of top-8 recall of s(f) on Panels A and B ≥ 0.90 *(lead's choice)*. **ADDRESS STABLE** (every learned arm): the median over cells of the share of facts with the same top-1 slot on Panels A and B ≥ 0.80 *(lead's choice; an escaped exploratory W7 had 0.89)*. Both are printed per arm and size, enter no class, and are carried with the interface.

### R4 (minor) — the probe holds few repeated facts

The text claims "every fact twice", but the first 512 sites hold 475–512 distinct facts, so address stability between two occurrences rests on about 37 / 6 / 0 facts. Replace the §8.1 probe definition with:

> **Probe set.** For the first 256 trained facts in the order of their first appearance in the draw's calibration stream, both of their occurrences in that stream (512 answer sites, 256 probe facts).

If this is adopted, condition 3's and onset's absolute counts change (0.50 × 256 = 128; onset ≤ 32 stays sensible). Fix it before calibration. Otherwise, keep the current probe and drop the probe-level stability statistic.

### R5 (minor) — the Stage 1 gate when the negative control fails

Replace with:

> Stage 2 is run if at least one arm is eligible to advance (RELIABLE at Stage 1, not A1-S, and not skipped because NEGATIVE CONTROL FAILED).

### R6 (minor; control 3) — no direct comparison of A1 and A2

Add:

> The paired difference d(A2 against A1) on the same draw and seed is printed at each size, descriptively, as the effect of removing the address supervision.

### R7 (minor) — the LM flag is invisible in the class

Add:

> An arm that meets row 2's count but carries LM CAPABILITY REDUCED is printed as **UNRELIABLE (LM CAPABILITY REDUCED)**.

## 5. Human lead's requirements

| Requirement | Status |
|---|---|
| Controls 1–9 | All present (G6; §4 table; A2 with reset and SUPERVISION-DEPENDENT, plus R6; §8.2 cost; pairing; A6 / A7 / NLL; §13; calibration draws, calibration-stream probe and fresh draws; A1-S paired). |
| Diagnostics | Present. Address stability during training is weak until R4. |
| Draw sensitivity | §8.7 and the per-draw bounds. |
| Capacity stages | Present, with the progression gate and Budget B. 65,536 is a probe that can only be positive or uninformative, as stated. |
| Registered criteria | Present, except address recall (R3), with the LM criterion only after R1. |
| Resources | Present. |
| "Not rescuing by thresholds" | Respected. Every bracketed number is fixed before calibration. R1–R4 are design corrections made before any calibration or registered observation. Each one makes a rule stricter or able to discriminate; none makes a rule easier to pass. |

## Commands (worktree root; R = this folder; S = scratchpad; RUN = the P9-I attempt-2 run directory)

```sh
PYTHONPATH=. uv run --locked python R/c7_probe_condition3.py S RUN > R/outputs/c7_probe_condition3.json 2> R/outputs/c7_probe_condition3.stderr
PYTHONPATH=. uv run --locked python R/c8_lm_capability.py S RUN > R/outputs/c8_lm_capability.json 2> R/outputs/c8_lm_capability.stderr
uv run --locked ruff check --config docs/reviews/ruff.toml --extend-ignore E501,I001,E401,E702,F841,E701,E402,F401 R/*.py
```

Process note: c8 was re-run after renaming a variable for ruff (E741). Its output was byte-identical, checked with `cmp`. For that check I put a temporary copy in `/tmp` and deleted it afterwards.

Astra review: NOT_PERFORMED. A Claude review is not an Astra review, and this document is not a human approval.
