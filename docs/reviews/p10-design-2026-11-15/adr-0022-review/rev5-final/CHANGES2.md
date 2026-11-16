# ADR-0022 revision 5, final text — changes from the revision 5 draft (commit 3f19ebb)

Draft by the lead subagent (Claude Fable 5.2, `claude-fable-5-2`). Text only: nothing implemented, downloaded, run or committed. Not an approval. Astra review: NOT_PERFORMED.

Built by `build_final.py`: 64 exact single-occurrence edits applying the Opus confirmation (`confirm-rev5/CONFIRM_REV5.md`, M1–M5, m1–m15) under the lead's rulings.

## Charged rung table (recomputation and second gates stage inside R)

| Rung | Design | Training and scoring (h) | Second gates stage (h) | Recomputation (h) | R (h) |
|---|---|---|---|---|---|
| 1 | 4 × 2,000 | 14.35–35.51 | 0.11–0.40 | 5.82–18.84 | **20.28–54.74** |
| 2 | 3 × 2,000 | 10.84–26.78 | 0.11–0.40 | 4.44–14.28 | **15.39–41.46** |
| 3 | 4 × 1,000 | 10.09–27.17 | 0.11–0.40 | 5.82–18.84 | **16.01–46.41** |
| 4 | 3 × 1,000 | 7.64–20.53 | 0.11–0.40 | 4.44–14.28 | **12.19–35.21** |

| Rung | Design | R charged (h) | cap 36 h, P = 3.5 | cap 36 h, P = 7.0 | cap 72 h, P = 3.5 | cap 72 h, P = 7.0 |
|---|---|---|---|---|---|---|
| 1 | 4 × 2,000 | 20.28–54.74 | does not fit | does not fit | fits for x ≤ 0.40 | fits for x ≤ 0.35 |
| 2 | 3 × 2,000 | 15.39–41.46 | fits for x ≤ 0.03 | does not fit | fits for x ≤ 0.72 | fits for x ≤ 0.65 |
| 3 | 4 × 1,000 | 16.01–46.41 | fits only for x < 0.01 | does not fit | fits for x ≤ 0.59 | fits for x ≤ 0.54 |
| 4 | 3 × 1,000 | 12.19–35.21 | fits for x ≤ 0.17 | fits for x ≤ 0.10 | fits for x ≤ 0.95 | fits for x ≤ 0.88 |

x is the place of the measured speed in the projected range (0 fast end, 1 slow end), figures rounded down. Projections, not measurements.

## Changes

### F01 — header, status line

- **Finding answered:** lead's instruction
- **Reason:** Status after the confirmation.
- **Mode:** replace

Old:

```text
- **Status: DESIGN REVISION 5 — pending an independent confirmation; lead's approval PENDING; nothing implemented, downloaded or run. SPEC: PENDING ASTRA REVIEW.**
```

New:

```text
- **Status: DESIGN REVISION 5 — CONFIRMED BY THE AUDITOR SUBJECT TO M1–M5 AND m1–m15, WHICH THIS TEXT APPLIES; lead's approval PENDING; nothing implemented, downloaded or run. SPEC: PENDING ASTRA REVIEW.**
```

### F02 — header, revision 5 bullet: what it does

- **Finding answered:** m1 (R-m1, extended to what has happened since)
- **Reason:** "does nothing else" was untrue: the text also records human answers and the lead's rulings, and now applies the confirmation.
- **Mode:** replace

Old:

```text
and does nothing else. No threshold, arm, model, data source, replicate count, rung or cap is changed.
```

New:

```text
records the human lead's answers on the package wheels, the link files and the hour cap and the lead's rulings on the first draft (§21), applies the confirmation of that draft (`adr-0022-review/confirm-rev5/CONFIRM_REV5.md`, Opus 5.5: READY SUBJECT TO text edits, M1–M5 and m1–m15; §22), and does nothing else. No threshold, arm, model, replicate count or rung is changed. The cap stays 36 hours in the text; by the human lead's decision recorded in §18 the lead may raise it once, at the rehearsal's headroom check only, to at most 72 hours (§13.3). The charged scope is revision 4's: all S2 processes, the independent recomputation included. A fallback language's data would come from a later export (§14.1).
```

### F03 — header, revision 5 bullet: the rule for open points

- **Finding answered:** m8 (R-m8, without its clause on the recomputation, which is now charged)
- **Reason:** The header's rule claimed more than the J7 choice does.
- **Mode:** replace

Old:

```text
otherwise by the option that is harder for a positive label or counts more time against the cap; each is marked
```

New:

```text
otherwise by the option that is harder for a positive label or counts more time against the cap, except J7, where the re-check's split rule is kept although draws disjoint across replicates would be harder for a positive label (§20); each is marked
```

### F04 — header, oracle bullet

- **Finding answered:** m3
- **Reason:** The sentence had no source.
- **Mode:** replace

Old:

```text
it does not name learned addressing. The human lead's instruction, verbatim: 
```

New:

```text
it does not name learned addressing. The human lead's instruction, verbatim (the human lead's P10 direction in the chat record of 2026-11-15, as confirmed by the lead against that record; §18): 
```

### F05 — header, evidence line

- **Finding answered:** lead's instruction
- **Reason:** The confirmation is review evidence like the earlier reviews.
- **Mode:** insert after

Anchor (unchanged):

```text
 The re-check of revision 4 (`adr-0022-review/RECHECK_REV4.md`, Opus 5.5) has the same standing.
```

Inserted (after the anchor; leading and trailing newlines not shown):

```text
 So has the confirmation of revision 5 (`adr-0022-review/confirm-rev5/CONFIRM_REV5.md`, Opus 5.5).
```

### F06 — revision history, row 5 status

- **Finding answered:** lead's instruction
- **Reason:** Status after the confirmation.
- **Mode:** replace

Old:

```text
| 5 | 2026-11-15 | pending an independent confirmation; lead's approval PENDING | applies
```

New:

```text
| 5 | 2026-11-15 | confirmed by the auditor subject to M1–M5 and m1–m15, which this text applies; lead's approval PENDING | applies
```

### F07 — revision history, row 5 content

- **Finding answered:** M1–M5; M3 (header sentence)
- **Reason:** Adds what the confirmation changed; the row's last sentence claimed no change of cap or data source.
- **Mode:** replace

Old:

```text
the oracle-assisted line above every printed class and line. No threshold, arm, model, data source, replicate count, rung or cap changed. §21 maps every finding. |
```

New:

```text
the oracle-assisted line above every printed class and line. After the confirmation: further listed seeds, each use starting a fresh generator; "none" prefixes of two lengths for the router, with a printed diagnostic; the independent recomputation charged, with a rule for its completion, tolerance and disagreements; the link files approved and the symmetry check made; the wheels recorded as they were approved, confirmation with sizes pending; the cap-extension rule (36 hours, raised by the lead at the rehearsal's headroom check only, to at most 72); the P9 reference test dropped. No threshold, arm, model, replicate count or rung changed. §21 and §22 map every finding. |
```

### F08 — §0 item 6

- **Finding answered:** M3; the human lead's decision on the cap
- **Reason:** With the recomputation charged the projection changes, and the cap may be extended under the lead's limits.
- **Mode:** replace

Old:

```text
The projection (§13) fits the cap with 2× headroom only at the fast end of an unmeasured throughput estimate. The rehearsal rule decides (§13.3); it can end at three replicates, at shortened training, or in **NOT STARTED: BUDGET**.
```

New:

```text
With the independent recomputation charged, the projection (§13) fits the 36-hour cap with 2× headroom only for three shortened replicates, and only at the fast end of an unmeasured throughput estimate; four full-length replicates do not fit 36 hours anywhere on it. The human lead has allowed the hour cap to be extended (§18). Under the lead's limits on its own use (§13.3) the cap may be raised once, at the rehearsal's headroom check, to at most 72 hours, so that four full-length replicates run; on the projection they fit 72 hours in about the faster two-fifths of the range. The rehearsal rule decides (§13.3); it can end at three replicates, at shortened training, or in **NOT STARTED: BUDGET**.
```

### F09 — §3, reference test

- **Finding answered:** m5; lead's ruling (dropped)
- **Reason:** The draft's rule was contradictory: P9's `ScalableMemory` cannot be constructed without a seed, and constructing it runs `seed + 1000·k`.
- **Mode:** replace

Old:

```text
- **Reference test.** On shared inputs the selection and weights equal those of the P9 flat memory forward, imported read-only. The test passes S2's own tensors explicitly to the P9 forward. S2 does not construct P9's `ScalableMemory` from a seed, so P9's `seed + 1000·k` derivation is not exercised (§9, gate G9). If the P9 forward cannot be given the tensors without editing P9, the reference test is dropped and the report says so **[lead's choice]**.
```

New:

```text
- **Reference test against P9: dropped **[lead's choice]**.** Revisions 1–4 required that on shared inputs the selection and weights equal those of the P9 flat memory forward, imported read-only. P9's `ScalableMemory` cannot be constructed without a seed, and constructing it runs its `seed + 1000·k` generators (confirmation, m5), which §9 excludes. The test is not made, and the report says so. The alternative not taken is the confirmation's: construct the P9 module inside a unit test with a test seed and overwrite its keys. The read is unit-tested against the definition above on hand-computed cases, and the lowest-index tie rule is checked by gate G4.
```

### F10 — §5.4, address identifier

- **Finding answered:** m6 (R-m6, verbatim)
- **Reason:** The mapping from (task, word) to the integer the hash takes was unstated.
- **Mode:** insert after

Anchor (unchanged):

```text
as P9's `unit_code` does, and seeds no generator).
```

Inserted (after the anchor; leading and trailing newlines not shown):

```text
 The identifier passed to the hash is 2,001·τ + j, with τ = 0 for A and 1 for B, and j the word's index in the vocabulary table (j = 2,000 for the task marker) **[lead's choice]**.
```

### F11 — §5.4, router "none" prefixes

- **Finding answered:** M2 (R-M2, verbatim, in full)
- **Reason:** With every "none" example decided at token 64 and every task example at about token 8–25, position alone separates the classes, and GEN could pass for that reason.
- **Mode:** replace

Old:

```text
WikiText-2 *train* prefixes of exactly 64 tokens in equal number
```

New:

```text
WikiText-2 *train* prefixes, half cut at exactly 64 tokens and half cut at a length drawn, with seed +3, from the token lengths of the task prompts of that router's streams
```

### F12 — §5.4, router decision position

- **Finding answered:** M2
- **Reason:** Follows from prefixes of two lengths.
- **Mode:** replace

Old:

```text
(the 64th token of a "none" prefix; the last prompt token of a task prompt)
```

New:

```text
(the last token of a "none" prefix, which is the 64th for the half cut at 64 tokens; the last prompt token of a task prompt)
```

### F13 — §5.4, router prefix sampling

- **Finding answered:** M2, M1
- **Reason:** States how the two halves are formed and in what order the +3 sampling generator draws.
- **Mode:** replace

Old:

```text
The "none" prefixes are consecutive non-overlapping 64-token pieces of the tokenized WikiText-2 train file, 8,000 of them sampled with seed +3.
```

New:

```text
The "none" prefixes are consecutive non-overlapping 64-token pieces of the tokenized WikiText-2 train file, 8,000 of them sampled with seed +3; the first 4,000 sampled keep their 64 tokens, and each of the other 4,000 keeps its first tokens up to a length drawn, with replacement, from the token lengths of the task prompts of that router's streams. The sampling generator of §9 draws the prefixes, then those lengths, then the batch order.
```

### F14 — §5.4, router diagnostic

- **Finding answered:** M2 (R-M2, verbatim)
- **Reason:** A printed check that the router is not silent by position.
- **Mode:** insert after

Anchor (unchanged):

```text
A router depends on the replicate and on the set of tasks, not on the arm.
```

Inserted (after the anchor; leading and trailing newlines not shown):

```text
 Beside GEN, the report prints, for each router, the false-trigger rate on the 100 marker-like windows when the decision is taken at the last token of the first marker-like string in tokens 1–64; this diagnostic enters no rule. **[lead's choice]** (the stricter of the two the confirmation offered; the alternative keeps prefixes of exactly 64 tokens and prints the diagnostic only).
```

### F15 — §6.4, string matching

- **Finding answered:** m7 (R-m7, verbatim)
- **Reason:** Case, substring and newline rules for the strata were unstated.
- **Mode:** insert after

Anchor (unchanged):

```text
A window whose only such strings lie after token 64 is in neither stratum and is not used.
```

Inserted (after the anchor; leading and trailing newlines not shown):

```text
 Strings are matched case-sensitively as substrings of the raw text (so "Germany" matches "German"); "a line ending in ':'" means a ':' immediately followed by a newline, both within the span in question **[lead's choice]**.
```

### F16 — §9, further listed seeds

- **Finding answered:** M1 (R-M1, verbatim except the seed of test (c))
- **Reason:** The seed list did not cover every generator, so G9 could not be met. The confirmation put test (c) at 229901, inside the test range; the lead's ruling keeps every listed seed outside it, so it is 220910.
- **Mode:** insert after

Anchor (unchanged):

```text
220905 the GEN window selection.
```

Inserted (after the anchor; leading and trailing newlines not shown):

```text
  Further listed seeds **[lead's choice]**:

  - 220906, the bootstrap resampling of every printed interval;
  - 220907, the 300 seen-item training items;
  - 220908, the 200 items per panel of the timing benchmark;
  - 220909, the 100 fixed sentences of each teacher's tokenizer record;
  - 220910, the 1,000 random id sequences of §14.2 test (c).

  220902–220910 are drawn once, in the data-generation and partition steps, and stored with the data manifest. No later stage draws them again. The partition seed 220901 draws in this order: the assignment of identity groups, then Q, D_cal, D_con, E_A, E_B, E_C, E_open. Every use of a listed seed starts a fresh generator seeded with it. So where §9 gives one seed several uses (+0, +6, +8, +9), each use starts from the same draws in its own shapes. +1 first splits the shared sources (§5.2) and then draws A, then B; +5 draws A, then B. Within a replicate, a fresh +2 generator also orders M-ii's replayed rows, and a fresh +3 generator, after the router's initialization, samples the "none" prefixes and then orders the router's batches. Gate G9 covers every seed and use listed here.

 
```

### F17 — §11.2, class 1

- **Finding answered:** M4
- **Reason:** A cell made NOT_EVALUATED by the recomputation rule needs a place in the class table.
- **Mode:** replace

Old:

```text
| 1 | NOT_EVALUATED | ACQ1 fails in any replicate, or a gap is undefined |
```

New:

```text
| 1 | NOT_EVALUATED | ACQ1 fails in any replicate, or a gap is undefined, or a cell of the mechanism is NOT_EVALUATED under the recomputation rule (§13.3) |
```

### F18 — §11.3, row 1

- **Finding answered:** M4 (R-M4)
- **Reason:** A recomputation difference that changes an outcome is an engineering failure.
- **Mode:** replace

Old:

```text
the oracle-routed ensemble's score differing from the teacher's own |
```

New:

```text
the oracle-routed ensemble's score differing from the teacher's own; a recomputation difference that changes a gate, class, annotation or label (§13.3) |
```

### F19 — §11.3, row 2

- **Finding answered:** M4 (R-M4)
- **Reason:** A recomputation that cannot be completed leaves the study incomplete.
- **Mode:** replace

Old:

```text
a registered cell has no record, or a cap stopped a stage; no class is derived
```

New:

```text
a registered cell has no record, or a cap stopped a stage, or the recomputation cannot be completed within the memory limits (§13.3, and then no class is printed); no class is derived
```

### F20 — §11.3, reason line

- **Finding answered:** M4
- **Reason:** The reason of a NOT_EVALUATED class may now be a recomputation difference.
- **Mode:** replace

Old:

```text
lexical margin below 0.30, or marker-only above 0.25.
```

New:

```text
lexical margin below 0.30, marker-only above 0.25, or a recomputation difference beyond tolerance (§13.3).
```

### F21 — §11.3, oracle sentence

- **Finding answered:** m3
- **Reason:** The sentence had no source.
- **Mode:** replace

Old:

```text
**No positive wording without it.** The human lead's instruction, verbatim: 
```

New:

```text
**No positive wording without it.** The human lead's instruction, verbatim (the human lead's P10 direction in the chat record of 2026-11-15, as confirmed by the lead against that record; §18): 
```

### F22 — §12.3, G9

- **Finding answered:** M1
- **Reason:** G9 must accept the further listed seeds and no others.
- **Mode:** replace

Old:

```text
(a replicate base + 0…10, or 220901–220905)
```

New:

```text
(a replicate base + 0…10, or 220901–220910, of which 220902–220910 are used in the data-generation and partition steps only)
```

### F23 — §13.2, charging rule

- **Finding answered:** M3; lead's ruling (earlier ruling withdrawn)
- **Reason:** The recomputation is charged, as revision 4's "all S2 processes" had it.
- **Mode:** replace

Old:

```text
 So is the second gates stage on registered seeds. The independent recomputation of §16 step 10 is not charged (§13.3).
```

New:

```text
 So are the second gates stage on registered seeds and the independent recomputation of every score (§16 step 10): "all S2 processes" has no exception.
```

### F24 — §13.2, cap

- **Finding answered:** the human lead's decision on the cap
- **Reason:** Points at the extension rule.
- **Mode:** insert after

Anchor (unchanged):

```text
**Cap: 36 charged hours for S2.**
```

Inserted (after the anchor; leading and trailing newlines not shown):

```text
 The lead may raise it once, at the rehearsal's headroom check only, to at most 72 hours, under the rule of §13.3 (the human lead's decision, §18).
```

### F25 — §13.3, table row for the recomputation

- **Finding answered:** M3
- **Reason:** The recomputation is inside R.
- **Mode:** replace

Old:

```text
| Independent recomputation of every score (§16 step 10): an audit step after the registered run, **not charged** (§13.3); for information, one repetition of the three scoring rows, an upper estimate |
```

New:

```text
| Independent recomputation of every score (§16 step 10), **charged and inside R** (§13.3); not in the row above; one repetition of the three scoring rows, an upper estimate |
```

### F26 — §13.3, rehearsal row

- **Finding answered:** m13 (R-m13, verbatim)
- **Reason:** The row omitted the runs at the other read layer.
- **Mode:** replace

Old:

```text
| Rehearsal | both | — | — | 1.5–3.0 h |
```

New:

```text
| Rehearsal | both | — | — | 1.5–3.0 h (plus about 0.1–0.2 h for the 200-update runs at the read layer not selected) |
```

### F27 — §13.3, the rule's inequality

- **Finding answered:** the human lead's decision on the cap
- **Reason:** The rule is read against the cap in force.
- **Mode:** replace

Old:

```text
The design is the first of the following for which P + 2·R ≤ 36:
```

New:

```text
The design is the first of the following for which P + 2·R ≤ the cap (36 hours, unless raised by the cap-extension rule below):
```

### F28 — §13.3, rates and scope; cap extension; recomputation rule

- **Finding answered:** M3, M4 (R-M4); the human lead's decision on the cap; lead's rulings
- **Reason:** The recomputation is charged; the cap-extension rule and the recomputation rule are stated.
- **Mode:** replace

Old:

```text
**Rates and scope of the rule (revision 5).** R(n, U) contains, for n replicates: training; every scoring of the registered run; the timing benchmark; and the second gates stage on registered seeds. **The independent recomputation of every score (§16 step 10) is not in R and is not charged to the 36 hours** **[lead's choice]**. It is an audit step performed after the registered run by a separate auditor context, and the project's convention is that such a recomputation is not charged to the study's budget: the Opus recomputations of P9-I and P9-II were not charged to those studies. (The alternative not taken is the recomputation inside R.) For information, it is projected at 5.8–18.8 h for four replicates and 4.4–14.3 h for three, as one repetition of the three scoring rows, an upper estimate. It must respect the per-process memory limits of this section (8 GiB per worker, 24 GiB aggregate), and no result is reported before it completes. For U = 2,000 the training rates are those of the calibrated setting, rehearsed at full length. For U = 1,000 the setting may be re-selected (§12.1), and the read layer may change with it. R(n, 1,000) therefore uses, for every store-type cell, the slower of the rates measured at L = 4 and at L = 12 **[lead's choice]** (the slower rate counts more time against the cap; the re-check's text used the rates of the re-selected setting). The read layer that was not rehearsed at full length is measured on 200 rehearsal updates of each store-type cell type before the rule is applied, and that time is part of P. The second gates stage enters R at the time the rehearsal's gates stage measured. The outcome "none" is recorded as **NOT STARTED: BUDGET** with the rehearsal record. A re-design after it is a new decision of the human lead (§16).
```

New:

```text
**Rates and scope of the rule (revision 5).** R(n, U) contains, for n replicates: training; every scoring of the registered run; the timing benchmark; the second gates stage on registered seeds; and the independent recomputation of every score (§16 step 10). **The recomputation is charged: it is inside R and inside the cap** **[lead's choice]**, as revision 4's "all S2 processes" had it and as the human lead's acceptance of GPU training "with scores recomputed on CPU" presupposes. The lead's earlier ruling that it was an uncharged audit step is withdrawn: the confirmation found the P9-I and P9-II precedent real in kind but not in scale (M3). The recomputation is projected from the rehearsal's measured scoring rates as one repetition of every scoring. For U = 2,000 the training rates are those of the calibrated setting, rehearsed at full length. For U = 1,000 the setting may be re-selected (§12.1), and the read layer may change with it. R(n, 1,000) therefore uses, for every store-type cell, the slower of the rates measured at L = 4 and at L = 12 **[lead's choice]** (the slower rate counts more time against the cap; the re-check's text used the rates of the re-selected setting). The read layer that was not rehearsed at full length is measured on 200 rehearsal updates of each store-type cell type before the rule is applied, and that time is part of P. The second gates stage enters R at the time the rehearsal's gates stage measured. The outcome "none" is recorded as **NOT STARTED: BUDGET** with the rehearsal record, and the work returns to the human lead (§16).

**Cap extension (the human lead's decision of §18; the lead's limits on its own use).** The cap stays 36 hours. At the rehearsal's headroom check only — before any registered seed of S2 is observed, on measured time and memory, never in response to a result — if rung 1 (four replicates, U = 2,000) does not satisfy P + 2·R ≤ 36, the lead raises the cap to the smallest whole number of hours at which rung 1 satisfies it, **up to 72 hours** **[lead's choice]** (the ceiling). If rung 1 would need more than 72 hours, the rung rule applies in its registered order against a 72-hour cap; if no rung fits, the outcome is NOT STARTED: BUDGET and the work returns to the human lead. The raise, the measured projection, and the old and the new cap are recorded in the freeze record. No cell, arm, update count or replicate beyond the registered design is ever added, and the memory limits are unchanged. The cap is raised at no other time and for no other reason.

**The recomputation rule.** No result is reported before the recomputation completes. The recomputation is complete when every registered score has been recomputed on CPU from the snapshots and compared with the registered score. If it uses the frozen scoring code, every score must be bit-identical; if it uses the auditor's own code, every greedy sequence must be identical and every item score must agree within 1e-6 **[lead's choice]** (both cases stand; each score is judged under the case of the code that recomputed it). Every difference is listed. A cell with a difference beyond its tolerance is NOT_EVALUATED, and the recomputed CPU value is the one reported **[lead's choice]** (the stricter reading; §11.2 then gives its mechanism the class NOT_EVALUATED). If a listed difference changes a gate, class, annotation or label — that is, if any of them differs between the registered scores and the recomputed ones — the study label is ENGINEERING-FAILURE. If the recomputation cannot be completed within the memory limits, the label is INCOMPLETE and no class is printed. The recomputation runs within 8 GiB per worker and 24 GiB aggregate.
```

### F29 — §13.3, projection and what fits

- **Finding answered:** M3; lead's instruction (state plainly what fits at 36 h and 72 h)
- **Reason:** The rung figures have the recomputation and the second gates stage inside R; the projection is stated for both caps and both values of P.
- **Mode:** replace

Old:

```text
On the table above, training and scoring come to the figures below (the re-check's recomputation; revision 4 printed 7.7 for 7.64). The second gates stage is projected at 0.11–0.40 h at every rung: it does not depend on n or U. That figure is unmeasured like the others, and the rehearsal's gates stage replaces it.

| Rung | Design | Training and scoring (h) | Second gates stage (h) | R (h) |
|---|---|---|---|---|
| 1 | 4 × 2,000 | 14.35–35.51 | 0.11–0.40 | **14.46–35.90** |
| 2 | 3 × 2,000 | 10.84–26.78 | 0.11–0.40 | **10.95–27.18** |
| 3 | 4 × 1,000 | 10.09–27.17 | 0.11–0.40 | **10.19–27.57** |
| 4 | 3 × 1,000 | 7.64–20.53 | 0.11–0.40 | **7.75–20.93** |

A rung holds only if its R measures at about 15 hours or less (14.5 h at P = 7.0, 16.25 h at P = 3.5), so rung 1 holds only at the fast end. **It is plausible that the rule ends at rung 2 or below, or at NOT STARTED: BUDGET.**
```

New:

```text
On the table above, training and scoring come to the figures below (the re-check's recomputation; revision 4 printed 7.7 for 7.64). The second gates stage is projected at 0.11–0.40 h at every rung: it does not depend on n or U. The recomputation is projected at 5.82–18.84 h for four replicates and 4.44–14.28 h for three, as one repetition of the three scoring rows (an upper estimate, because the timing benchmark is not repeated). All of these are unmeasured, and the rehearsal replaces them.

| Rung | Design | Training and scoring (h) | Second gates stage (h) | Recomputation (h) | R (h) |
|---|---|---|---|---|---|
| 1 | 4 × 2,000 | 14.35–35.51 | 0.11–0.40 | 5.82–18.84 | **20.28–54.74** |
| 2 | 3 × 2,000 | 10.84–26.78 | 0.11–0.40 | 4.44–14.28 | **15.39–41.46** |
| 3 | 4 × 1,000 | 10.09–27.17 | 0.11–0.40 | 5.82–18.84 | **16.01–46.41** |
| 4 | 3 × 1,000 | 7.64–20.53 | 0.11–0.40 | 4.44–14.28 | **12.19–35.21** |

**What fits, stated plainly (projection, not measurement).** A rung fits if R ≤ (cap − P)/2: 16.25 h at 36 hours and P = 3.5, 14.5 h at 36 hours and P = 7.0, 34.25 h and 32.5 h at 72 hours. Below, x is the place of the measured speed in the projected range, 0 at its fast end and 1 at its slow end, taken the same for every row (the confirmation's model; figures rounded down).

| Rung | Design | R charged (h) | cap 36 h, P = 3.5 | cap 36 h, P = 7.0 | cap 72 h, P = 3.5 | cap 72 h, P = 7.0 |
|---|---|---|---|---|---|---|
| 1 | 4 × 2,000 | 20.28–54.74 | does not fit | does not fit | fits for x ≤ 0.40 | fits for x ≤ 0.35 |
| 2 | 3 × 2,000 | 15.39–41.46 | fits for x ≤ 0.03 | does not fit | fits for x ≤ 0.72 | fits for x ≤ 0.65 |
| 3 | 4 × 1,000 | 16.01–46.41 | fits only for x < 0.01 | does not fit | fits for x ≤ 0.59 | fits for x ≤ 0.54 |
| 4 | 3 × 1,000 | 12.19–35.21 | fits for x ≤ 0.17 | fits for x ≤ 0.10 | fits for x ≤ 0.95 | fits for x ≤ 0.88 |

- **At 36 hours:** rung 1 does not fit anywhere. Rungs 2 and 3 fit only at the fastest edge and only with P = 3.5. Rung 4 fits for x ≤ 0.17 (P = 3.5) or x ≤ 0.10 (P = 7.0). Without an extension the plausible outcomes are rung 4 or NOT STARTED: BUDGET.
- **With the extension rule:** rung 1 runs for x ≤ 0.40 (P = 3.5) or x ≤ 0.35 (P = 7.0), with a cap raised to between 45 and 72 hours (48 to 72 at P = 7.0). Beyond that, against 72 hours, rung 2 runs up to x = 0.72 (0.65), rung 4 up to x = 0.95 (0.88), and NOT STARTED: BUDGET above. Rung 3 fits less often than rung 2 and is never the first to fit on this model.
- **It is plausible that the rule ends at rung 1 or rung 2 with a raised cap, and NOT STARTED: BUDGET remains possible at the slow end.**
```

### F30 — §14.1, opening paragraph

- **Finding answered:** M5; the human lead's decision on the link files; m9
- **Reason:** The link files are approved; the wheels' status is stated as it happened.
- **Mode:** replace

Old:

```text
**Approved by the human lead and recorded (§18):** rows 1–4 — the two teachers, the student and the Tatoeba exports; only if the fallback rule of §4.2 is invoked, rows 5 and 6, the fallback teacher and the fallback (Spanish) data; and the package wheels for the one-off data-generation step (§14.2). **Not approved, open with the human lead:** the two symmetry-check link files (6.2 MB, below), about which the lead has asked again; any package outside the lock other than those wheels. Nothing in the open list is fetched before a recorded answer of the human lead, given with the sizes in front of them. Implementation and tests on synthetic stand-ins need none of it. No download has been made.
```

New:

```text
**Approved by the human lead and recorded (§18):** rows 1–4 — the two teachers, the student and the Tatoeba exports; the two symmetry-check link files (6.2 MB, below); only if the fallback rule of §4.2 is invoked, rows 5 and 6, the fallback teacher and the fallback (Spanish) data; and the eight named packages of the one-off data-generation step (§14.2). **Pending with the human lead:** the approval of the packages was given to a question that stated no size, and the lead has asked the human lead to confirm it with the sizes stated, the transitive dependencies included. No wheel is fetched before that confirmation is recorded. **Not approved:** any other package outside the lock. Implementation and tests on synthetic stand-ins need none of this. No download has been made.
```

### F31 — §14.1, total row

- **Finding answered:** m9 (R-m9); the human lead's decision on the link files; M5
- **Reason:** "approved and fetched" read as if the files had been fetched; the link files are approved.
- **Mode:** replace

Old:

```text
**930 MB approved and fetched (rows 1–4); 8.1 MB + 315.3 MB more only if the fallback is invoked (1,253 MB in all). Not in these figures: the package wheels (approved, §14.2; about 23 to 32 MB for the eight named packages, their dependencies recorded at fetch time); 6.2 MB of symmetry-check link files (not approved)**
```

New:

```text
**930 MB approved, to be fetched (rows 1–4), and 6.2 MB of symmetry-check link files, approved (936 MB together); 8.1 MB + 315.3 MB more only if the fallback is invoked (1,260 MB in all). Not in these figures: the package wheels (§14.2; the eight named packages approved, about 23 to 32 MB; confirmation with all sizes pending)**
```

### F32 — §14.1, link files

- **Finding answered:** the human lead's decision on the link files; confirmation §2.2 (count of one-direction links)
- **Reason:** The link files are approved and the symmetry check is made.
- **Mode:** replace

Old:

```text
**They were in no figure shown to the human lead and are not approved.** The human lead's answer on the package wheels did not name them, and the lead has asked again (§18). The symmetry check against them is made only if the human lead approves them; they are then fetched in the same session as row 4. Without them the check is not made, and the data manifest and the report say that the symmetry of the link files was not checked **[lead's choice]**.
```

New:

```text
**The human lead has approved them (§18).** They are fetched in the same session as row 4, and the symmetry check is made. The count of English sentence ids that have a link in only one direction is reported.
```

### F33 — §14.1, one session

- **Finding answered:** the human lead's decision on the link files
- **Reason:** The link files are approved.
- **Mode:** replace

Old:

```text
The five files of row 4 (and the two link files, if approved) are fetched in one session
```

New:

```text
The five files of row 4 and the two link files are fetched in one session
```

### F34 — §14.2, package wheels

- **Finding answered:** M5 (R-M5); m10 (R-m10)
- **Reason:** Records exactly what was asked and answered; the command is the one §14.2 runs.
- **Mode:** replace

Old:

```text
- **Package wheels are themselves downloads. The human lead has approved them (§18):** the eight packages named above and the dependencies the resolver requires for them, pinned with exact versions and hashes in the requirements file of the freeze, installed with `uv run --locked --with`; `uv.lock` and `pyproject.toml` do not change. The 938 MB figure did not include them. From the reviewer's saved index records (`adr-0022-review/web/pypi_*.json`), the wheels of the eight named packages for macOS arm64 and Python 3.12 total about 23 MB, or about 32 MB if numpy's larger wheel is the one selected. The transitive dependencies are not in those records; their names, versions, hashes and sizes are recorded at fetch time. Nothing else is installed outside the lock without a further answer. By §16 the wheels are fetched with the downloads, after implementation on synthetic stand-ins.
```

New:

```text
- **Package wheels are themselves downloads.** What happened, exactly (§18): the human lead said "yes I do, yes we can raise to 16 and I approve the package" in answer to a question that named the wheels and gave no size. The lead then told the human lead that the eight named packages are about 23 to 32 MB, with the transitive dependencies to be recorded at fetch time. The human lead's next message raised no objection and did not restate the approval. **Status: the eight packages named above are approved. The lead has asked the human lead to confirm with the sizes stated, the transitive dependencies included, and no wheel is fetched before that confirmation is recorded.** Reading the answer as covering the transitive dependencies, whose names and sizes are recorded at fetch time, is the lead's reading. The packages are pinned with exact versions and hashes in the requirements file of the freeze and installed with `uv run --locked --with-requirements studies/p10s2/requirements-datagen.txt`; `uv.lock` and `pyproject.toml` do not change. The 938 MB figure did not include them. From the reviewer's saved index records (`adr-0022-review/web/pypi_*.json`), the wheels of the eight named packages for macOS arm64 and Python 3.12 total about 23 MB, or about 32 MB if numpy's larger wheel is the one selected. The transitive dependencies are not in those records. Nothing else is installed outside the lock without a further answer.
```

### F35 — §15, item 3 context

- **Finding answered:** m2 (R-m2, verbatim)
- **Reason:** The context was stated as fact; it is the lead's account.
- **Mode:** replace

Old:

```text
which answered the lead's message listing S0 16 h, S1 12 h, S2 36 h, total 64 h (§18)
```

New:

```text
which, by the lead's record in §18, answered the lead's message listing S0 16 h, S1 12 h, S2 36 h, total 64 h; that message is not in the repository (ADR-0021 records the same context as relayed by the coordinating session)
```

### F36 — §15, item 6

- **Finding answered:** M5
- **Reason:** The confirmation with sizes is pending.
- **Mode:** replace

Old:

```text
Item 6 rests on the human lead's approval of the package wheels (§18) and reaches no other package.
```

New:

```text
Item 6 rests on the human lead's approval of the eight named packages (§18), whose confirmation with sizes is pending (§14.2), and reaches no other package.
```

### F37 — §16, order, step 1

- **Finding answered:** M5; the human lead's decision on the link files
- **Reason:** What is still pending is the wheels' confirmation, not the link files.
- **Mode:** replace

Old:

```text
recorded in §18, except the link files.
```

New:

```text
recorded in §18; the confirmation of the package wheels with their sizes is pending.
```

### F38 — §16, order, step 5

- **Finding answered:** M5
- **Reason:** No wheel before the confirmation is recorded.
- **Mode:** replace

Old:

```text
(5) Downloads of the approved files (§14.1) and of the approved wheels (§14.2); data-generation step.
```

New:

```text
(5) Downloads of the approved files (§14.1); the wheels (§14.2) once the human lead's confirmation with sizes is recorded; data-generation step.
```

### F39 — §16, order, step 10

- **Finding answered:** M3, M4
- **Reason:** Points at the recomputation rule.
- **Mode:** replace

Old:

```text
(10) Independent recomputation of every score from snapshots; outcome report.
```

New:

```text
(10) Independent recomputation of every score from snapshots, charged and under the rule of §13.3; outcome report.
```

### F40 — §16, reserved item 2

- **Finding answered:** M5
- **Reason:** States the approval as it was given.
- **Mode:** replace

Old:

```text
their dependencies recorded at fetch time). **Answered: approved.**
```

New:

```text
their dependencies recorded at fetch time). **Answered: the eight named packages approved, to a question that stated no size. The lead has asked for confirmation with the sizes stated, the transitive dependencies included; no wheel is fetched before it is recorded.**
```

### F41 — §16, reserved item 6

- **Finding answered:** the human lead's decision on the link files
- **Reason:** The link files are approved.
- **Mode:** replace

Old:

```text
6. The two symmetry-check link files (6.2 MB, §14.1). **Open: not approved.** The answer on item 2 did not name them; the lead has asked again.
```

New:

```text
6. The two symmetry-check link files (6.2 MB, §14.1). **Answered: approved.**
```

### F42 — §16, also reserved

- **Finding answered:** m11 (R-m11, verbatim); the cap ceiling
- **Reason:** §4.2 made the fallback invocation a reserved decision; §16 did not list it. A cap above the lead's ceiling goes back to the human lead.
- **Mode:** replace

Old:

```text
Also reserved: any change of thresholds, arms, models, data or budget after the freeze;
```

New:

```text
Also reserved: the invocation of the fallback teacher (§4.2); any cap above 72 hours (§13.3); any change of thresholds, arms, models, data or budget after the freeze;
```

### F43 — §18, the first two clauses

- **Finding answered:** m15 (R-m15, verbatim); M5 (R-M5)
- **Reason:** Names the two clauses and records what was shown about sizes.
- **Mode:** replace

Old:

```text
(The first two clauses answer other questions.)
```

New:

```text
(The first clause accepts the P9-II outcome, ADR-0019 §16; the second raises S1's cap to 16 hours, ADR-0021.) The question as put did not state the wheels' size. After the answer the lead told the human lead that the eight named packages are about 23 to 32 MB, with the transitive dependencies to be recorded at fetch time; the human lead's next message, quoted below, raised no objection and did not restate the approval. Reading the answer as covering the transitive dependencies, whose names and sizes are recorded at fetch time, is the lead's reading.
```

### F44 — §18, wheels bullet

- **Finding answered:** M5; m10 (R-m10)
- **Reason:** States the status as ruled; the command is the one §14.2 runs.
- **Mode:** replace

Old:

```text
- **The package wheels for the one-off data-generation step are approved:** the eight packages named in §14.2 and the dependencies the resolver requires for them, pinned in the requirements file of the freeze, installed with `uv run --locked --with`; `uv.lock` and `pyproject.toml` do not change. The eight named packages come to about 23 to 32 MB; the transitive dependencies are recorded at fetch time.
```

New:

```text
- **The eight packages named in §14.2 are approved** for the one-off data-generation step, pinned in the requirements file of the freeze, installed with `uv run --locked --with-requirements studies/p10s2/requirements-datagen.txt`; `uv.lock` and `pyproject.toml` do not change. They come to about 23 to 32 MB. **The lead has asked the human lead to confirm with the sizes stated, the transitive dependencies included; no wheel is fetched before that confirmation is recorded.**
```

### F45 — §18, link files bullet

- **Finding answered:** the human lead's decision on the link files
- **Reason:** The later answer approves them.
- **Mode:** replace

Old:

```text
- **The two symmetry-check link files (6.2 MB) were not named in the answer and stay not approved.** The lead has asked again. Until an answer names them they are not fetched and the symmetry check is not made (§14.1).
```

New:

```text
- The two symmetry-check link files (6.2 MB) were not named in this answer. The lead asked again; the answer is recorded below.
```

### F46 — §18, 36-hour context

- **Finding answered:** m2 (R-m2)
- **Reason:** Marks the context as the lead's account.
- **Mode:** replace

Old:

```text
it answered the lead's message listing S0 16 h, S1 12 h, S2 36 h, total 64 h.
```

New:

```text
it answered the lead's message listing S0 16 h, S1 12 h, S2 36 h, total 64 h (the lead's account of the chat record; the message is not in the repository).
```

### F47 — §18, new record

- **Finding answered:** the human lead's decision on the link files and the cap; M3; m3
- **Reason:** Records the decision verbatim with its question, the lead's limits on its own use of the cap extension, the withdrawal of the earlier ruling on the recomputation, and the source of the oracle sentence.
- **Mode:** insert before

Anchor (unchanged):

```text
**Download scope as revision 5 states it**
```

Inserted (before the anchor; leading and trailing newlines not shown):

```text
**Human lead's decision on the link files and the hour cap — 2026-11-15 (UTC), verbatim:**

> I Aprove the link files with 6.2mb and you can extend the hour cap if needed across all p10

It answered the lead's question: "Do you also approve the 6.2 MB of Tatoeba link files for S2's symmetry check? If not, the check is skipped and the report says so."

Recorded by the lead:

- **The two symmetry-check link files (6.2 MB) are approved.** They are fetched in the same session as the Tatoeba exports, and the symmetry check is made (§14.1).
- **The hour cap may be extended.** The lead's limits on its own use of this in S2 (§13.3): the cap stays 36 hours in the text. At the rehearsal's headroom check only — before any registered seed of S2 is observed, on measured time and memory, never in response to a result — if four full-length replicates do not fit, the lead raises the cap to the smallest whole number of hours at which they fit, up to 72 hours; beyond that the rung rule applies against 72 hours, and NOT STARTED: BUDGET returns the work to the human lead. The raise, the measured projection, and the old and the new cap go into the freeze record. No cell, arm, update count or replicate is added, and the memory limits are unchanged. The human lead's words do not extend to downloads, models, data, thresholds or designs.
- **The independent recomputation is charged** (§13.2, §13.3). The lead's earlier ruling that it was an uncharged audit step is withdrawn after the confirmation (M3).
- **The package wheels.** This message raised no objection to the sizes the lead had stated and did not restate the approval. The lead has asked the human lead to confirm with the sizes stated, the transitive dependencies included; no wheel is fetched before that confirmation is recorded.

**The human lead's sentence on oracle-assisted results**, quoted in the header and in §11.3: "S1 and S2 must not claim autonomous learned-memory success from oracle-assisted results." Its source is the human lead's P10 direction in the chat record of 2026-11-15, as confirmed by the lead against that record. It is not otherwise in the repository.
```

### F48 — §18, download scope statement

- **Finding answered:** M5; the human lead's decision on the link files
- **Reason:** One statement of the scope after the later answer.
- **Mode:** replace

Old:

```text
- Approved by the human lead and recorded above: the two teachers, the student, the Tatoeba data; the fallback teacher and the fallback (Spanish) data only if the fallback rule of §4.2 is invoked; the package wheels for the one-off data-generation step.
- Not approved, open with the human lead: the 6.2 MB of symmetry-check link files; any package outside the lock other than those wheels.
- Nothing in the open list is fetched before a recorded answer.
```

New:

```text
- Approved by the human lead and recorded above: the two teachers, the student, the Tatoeba data; the two symmetry-check link files (6.2 MB); the fallback teacher and the fallback (Spanish) data only if the fallback rule of §4.2 is invoked; the eight named packages of the one-off data-generation step.
- Pending with the human lead: the confirmation of the package wheels with their sizes stated, the transitive dependencies included. No wheel is fetched before it is recorded.
- Not approved: any other package outside the lock.
```

### F49 — §18, approval line

- **Finding answered:** lead's instruction
- **Reason:** The confirmation has been made and is applied.
- **Mode:** replace

Old:

```text
Lead's approval: PENDING. Revision 5 answers the re-check (majors J1–J8, minors J9–J14 and others; §21) and awaits an independent confirmation.
```

New:

```text
Lead's approval: PENDING. Revision 5 answers the re-check (majors J1–J8, minors J9–J14 and others; §21) and applies its confirmation (M1–M5, m1–m15; §22).
```

### F50 — §19, not applied verbatim, item 5

- **Finding answered:** the human lead's decision on the link files
- **Reason:** The link files are approved.
- **Mode:** replace

Old:

```text
 *Revision 5: these two files are not approved and are open with the human lead (§14.1, §18).*
```

New:

```text
 *Revision 5: the human lead has approved these two files (§18).*
```

### F51 — §20, rulings list, cap

- **Finding answered:** the human lead's decision on the cap
- **Reason:** Keeps the list in step with §13.3.
- **Mode:** insert after

Anchor (unchanged):

```text
- Cap of 36 charged hours with 2× headroom; charged as the sum over processes.
```

Inserted (after the anchor; leading and trailing newlines not shown):

```text
 The lead may raise it once, at the rehearsal's headroom check only, to at most 72 hours (§13.3).
```

### F52 — §20, seeds row

- **Finding answered:** M1
- **Reason:** Keeps the list in step with §9.
- **Mode:** replace

Old:

```text
partition-side streams 220901–220905; every generator seeded directly
```

New:

```text
partition-side streams 220901–220910; every use starts a fresh generator seeded directly
```

### F53 — §20, choice table: streams

- **Finding answered:** M1
- **Reason:** Keeps the list in step with §9.
- **Mode:** replace

Old:

```text
| J1 partition-side streams | listed seeds 220902–220905 |
```

New:

```text
| J1 partition-side streams | listed seeds 220902–220910 (M1), drawn once and stored |
```

### F54 — §20, choice table: router

- **Finding answered:** M2
- **Reason:** Keeps the list in step with §5.4.
- **Mode:** replace

Old:

```text
8,000 "none" prefixes of 64 tokens; hidden state at block L;
```

New:

```text
8,000 "none" prefixes, half of 64 tokens and half cut to task-prompt lengths (M2), with a printed diagnostic; hidden state at block L;
```

### F55 — §20, choice table: scope of R

- **Finding answered:** M3
- **Reason:** The recomputation is charged.
- **Mode:** replace

Old:

```text
| J8b scope of R | second gates stage inside R and the 36 hours; the independent recomputation not charged (the P9-I / P9-II convention), within the memory limits, and no result reported before it completes | the recomputation inside R | §13.2, §13.3 |
```

New:

```text
| J8b scope of R | second gates stage and independent recomputation inside R and inside the cap; no result reported before the recomputation completes | the recomputation as an uncharged audit step (the lead's earlier ruling, withdrawn after the confirmation) | §13.2, §13.3 |
```

### F56 — §20, choice table: reference test

- **Finding answered:** m5
- **Reason:** The test is dropped.
- **Mode:** replace

Old:

```text
| P9 reference test | tensors passed explicitly to the P9 forward; `ScalableMemory` never constructed from a seed; the test is dropped, and the report says so, if that needs an edit of P9 | constructing the P9 module with a seed | §3 |
```

New:

```text
| P9 reference test | dropped; the report says so; the read is unit-tested against its definition | the confirmation's R-m5: the P9 module constructed inside a unit test with a test seed and its keys overwritten | §3 |
```

### F57 — §20, choice table: link files

- **Finding answered:** the human lead's decision on the link files
- **Reason:** The row described a choice that no longer exists; rows for the choices of this pass are added.
- **Mode:** replace

Old:

```text
| Link files not approved | the symmetry check is not made and the report says so | not starting the data-generation step without it | §14.1 |
```

New:

```text
| Cap extension ceiling | 72 hours; raised only at the rehearsal's headroom check, to the smallest whole number of hours at which rung 1 fits | no ceiling, or another figure | §13.3, §18 |
| Recomputation tolerance | bit-identical with the frozen scoring code; identical greedy sequences and item scores within 1e-6 with the auditor's own code | one of the two cases only | §13.3 |
| Recomputation disagreement | the cell is NOT_EVALUATED and the recomputed CPU value is reported; ENGINEERING-FAILURE if a gate, class, annotation or label differs | listing the difference without changing the cell | §11.2, §11.3, §13.3 |
| M1 further seeds | 220906–220910, drawn once and stored; test (c) at 220910 | the confirmation's 229901 for test (c), which lies in the test range | §9, G9 |
| m6 hash identifier | 2,001·τ + j | another mapping | §5.4 |
| m7 string matching | case-sensitive substrings; ':' immediately followed by a newline | whole-word or case-insensitive matching | §6.4 |
```

### F58 — §21, row J3

- **Finding answered:** the human lead's decision on the link files
- **Reason:** Keeps the map true after the later answer.
- **Mode:** replace

Old:

```text
fallback teacher and data only if invoked; link files and wheels open.
```

New:

```text
fallback teacher and data only if invoked; the link files approved later and the wheels as recorded in §18.
```

### F59 — §21, row J4

- **Finding answered:** M5
- **Reason:** Keeps the map true.
- **Mode:** replace

Old:

```text
the human lead's later approval of the wheels recorded; the link files stay open;
```

New:

```text
the human lead's later approval of the wheels recorded as it was given (M5); the link files approved later;
```

### F60 — §21, row J8

- **Finding answered:** M3
- **Reason:** The recomputation is charged.
- **Mode:** replace

Old:

```text
second gates stage inside R and shown in the rung table; recomputation not charged, by the P9-I / P9-II convention; NOT STARTED: BUDGET |
```

New:

```text
second gates stage and recomputation inside R and shown in the rung table (the recomputation as the re-check's E-J8 had it); NOT STARTED: BUDGET |
```

### F61 — §21, not applied verbatim, item 4

- **Finding answered:** M3
- **Reason:** The charging now agrees with the re-check's text.
- **Mode:** replace

Old:

```text
The re-check's text also charged the independent recomputation inside R; by the lead's ruling it is not charged, following the P9-I / P9-II convention (§13.3).
```

New:

```text
The re-check's text also charged the independent recomputation inside R, and so does this text (§13.3, §22).
```

### F62 — open questions, item 7

- **Finding answered:** M3, M4
- **Reason:** Names the heaviest choices as they now stand.
- **Mode:** replace

Old:

```text
the oracle-code seed per replicate; the recomputation outside the charged hours.
```

New:

```text
the oracle-code seed per replicate; the 72-hour ceiling of the cap extension; the rule that a recomputation difference beyond tolerance makes a cell NOT_EVALUATED.
```

### F63 — things to verify, first bullet

- **Finding answered:** M5; m12
- **Reason:** The link files are approved; what is pending is the wheels' confirmation.
- **Mode:** replace

Old:

```text
- The human lead's answer still open: the two symmetry-check link files (§16); the lead has asked again.
```

New:

```text
- The human lead's confirmation of the package wheels with their sizes stated, the transitive dependencies included (§14.2, §16); those sizes are not yet established.
```

### F64 — new §22

- **Finding answered:** lead's instruction
- **Reason:** Maps M1–M5 and m1–m15 to their changes.
- **Mode:** insert before

Anchor (unchanged):

```text
## Open questions for the lead
```

Inserted (before the anchor; leading and trailing newlines not shown):

```text
## 22. Map of the confirmation of revision 5 (`confirm-rev5/CONFIRM_REV5.md`) to this text

| Finding | Change | Where |
|---|---|---|
| M1 seed list incomplete | Further listed seeds 220906–220910, drawn once and stored; order of the partition seed's draws; every use of a listed seed starts a fresh generator; +2 and +3 uses named; G9 extended | §9, §12.3, §20 |
| M2 router position shortcut | R-M2 in full: half of the "none" prefixes at 64 tokens, half at task-prompt lengths; printed diagnostic that enters no rule | §5.4, §20 |
| M3 recomputation charging | Charged: inside R and inside the cap; rung figures with it; the human lead's decision on the cap recorded with the lead's limits (36 hours, raised only at the rehearsal's headroom check, to at most 72); what fits at 36 and 72 hours stated | header, §0, §13.2, §13.3, §16, §18, §20 |
| M4 recomputation rule | R-M4: complete, tolerance, differences, failure within the memory limits; NOT_EVALUATED cells with the recomputed value reported; class and label tables extended | §11.2, §11.3, §13.3, §16 |
| M5 wheels premise | Recorded as it happened; eight named packages approved; confirmation with sizes pending; no wheel before it is recorded | §14.1, §14.2, §15, §16, §18 |
| m1 header "does nothing else" | Reworded | header |
| m2 36-hour context | Stated as the lead's account of the chat record | §15, §18 |
| m3 oracle sentence's provenance | Source stated in the header, §11.3 and §18 | header, §11.3, §18 |
| m4 | The confirmation lists no m4 | — |
| m5 P9 reference test | Dropped; the report says so | §3, §20 |
| m6 hash identifier | 2,001·τ + j | §5.4 |
| m7 string matching | Case-sensitive substrings; ':' followed by a newline | §6.4 |
| m8 J7 against the header's rule | The header names the exception | header |
| m9 "approved and fetched" | "approved, to be fetched" | §14.1 |
| m10 `--with` | `--with-requirements studies/p10s2/requirements-datagen.txt` | §14.2, §18 |
| m11 fallback invocation | Added to §16's reserved list | §16 |
| m12 verify-list item on link symmetry | No longer conditional: the files are approved and the check is made | §14.1, closing lists |
| m13 rehearsal row | Other-layer runs added | §13.3 |
| m14 build script input | This build script is self-contained (outside the ADR) | — |
| m15 first two clauses | Named | §18 |

**Not applied verbatim (listed, not resolved silently):**

1. **R-M1, the seed of test (c).** The confirmation gave 229901, which lies in the test range. By the lead's ruling every listed seed lies in 220001–228999 and outside the calibration, rehearsal and test ranges, so it is 220910; "220902–220909" became "220902–220910" and G9 lists 220901–220910.
2. **R-M3.** Its text explained an uncharged recomputation. The lead withdrew that ruling: the recomputation is charged, and the header sentence, §13.2 and §13.3 say so instead.
3. **R-M4.** The bracketed tolerance is kept as two cases, without its PENDING tag. Added by the lead's ruling: a cell with a difference beyond tolerance is NOT_EVALUATED and the recomputed CPU value is reported. The class table, the label table and the reason line are extended to carry the rule.
4. **R-M5.** The brackets are filled with what happened: the question stated no size; the sizes were told afterwards; the next message did not restate the approval. The wheels are not put back in the open list: by the lead's ruling the eight named packages are approved and no wheel is fetched before the confirmation with sizes is recorded.
5. **R-m1.** Extended to name the later human answers and this confirmation.
6. **R-m3.** Not restored as a verify bullet: the source is stated instead.
7. **R-m5.** Not adopted: by the lead's ruling the reference test is dropped. The sentence that the read is unit-tested against its definition is this draft's.
8. **R-m8.** Its second clause, on an uncharged recomputation, is omitted, because the recomputation is charged.
9. **R-m12.** Not applied: the two files are approved.
10. **M2, details.** How the second half of the prefixes is cut (first tokens kept; lengths drawn with replacement; order of the +3 sampling generator) is this draft's.
```

## Could not apply verbatim, or had to choose

Listed in the ADR's §22 under "Not applied verbatim". In short:

1. **R-M1, test (c) seed**: 220910 instead of the confirmation's 229901 (inside the test range; the lead's ruling keeps listed seeds out of it).
2. **R-M3**: superseded by the lead's ruling; the recomputation is charged.
3. **R-M4**: both tolerance cases kept; the lead's stricter reading added (NOT_EVALUATED cell, recomputed CPU value reported). To carry it I extended §11.2 class 1, §11.3 rows 1 and 2 and the reason line. How the two consequences combine is my reading: a difference beyond tolerance always makes the cell NOT_EVALUATED; the study is ENGINEERING-FAILURE only if a gate, class, annotation or label differs between the registered and the recomputed scores. Both the registered scoring and the recomputation run on CPU, so "the recomputed CPU value" is the precise form of "the CPU value".
4. **R-M5**: brackets filled with the lead's account; wheels kept approved, not returned to the open list.
5. **R-m1, R-m8**: adapted to the charged recomputation and to the later answers.
6. **R-m3, R-m12**: not applied; the source is stated, and the link files are approved.
7. **R-m5**: not adopted; the reference test is dropped. I added one sentence: the read is unit-tested against its definition on hand-computed cases and the tie rule is checked by G4.
8. **M2 details** (mine): the first 4,000 sampled prefixes keep 64 tokens; each of the other 4,000 keeps its first tokens up to a length drawn with replacement from the task-prompt lengths of that router's streams; the +3 sampling generator draws prefixes, then lengths, then batch order.
9. **Cap extension, one reading of mine**: when rung 1 would need more than 72 hours, I wrote "the rung rule applies in its registered order against a 72-hour cap", as instructed, and did not add a rule for recording a smaller cap for the rung that then fits.
10. **Link files**: I added "the count of English sentence ids that have a link in only one direction is reported" (the confirmation's suggestion in its section 2.2). What an asymmetry does to the partition is still unstated, as in revision 4.

## Still open or not established

- The sizes of the transitive dependencies of the eight packages are not established; the human lead's confirmation needs them.
- The number of bootstrap resamples behind "every cell prints a bootstrap interval" is not stated anywhere in the ADR; seed 220906 now covers the draw but not the count. Not raised by the confirmation, not changed.
- The second-gates-stage figure (0.11–0.40 h) and the recomputation figure are projections, unmeasured.
- §15 departures 1, 4, 5 and 7 remain for the lead's approval record.
- Outside this ADR: `docs/reviews/p10-design-2026-11-15/EXECUTION_PLAN.md` still gives S2's registered run as 7.7–35.5 h and a 36-hour cap without the extension rule.
- This text has had no review after these edits.
