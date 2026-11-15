# ADR-0022 revision 5 — changes from revision 4 (commit 3cf3576 on claude/p10-design)

Draft by the lead subagent (Claude Fable 5.2, `claude-fable-5-2`). Text only: nothing implemented, downloaded, run or committed. Not an approval; not a confirmation. Astra review: NOT_PERFORMED.

Built by `build.py` with the lead's rulings on the first draft applied by `rulings.py`: 60 exact single-occurrence edits. No threshold, arm, model, data source, replicate count, rung or cap is changed.

## Changes

### C01 — header, status line

- **Finding answered:** task item 7
- **Reason:** New status for revision 5.
- **Mode:** replace

Old:

```text
- **Status: DESIGN REVISION 4 — CONFIRMED BY THE AUDITOR SUBJECT TO C1–C10 AND m1–m7, WHICH THIS REVISION APPLIES. SPEC: PENDING ASTRA REVIEW. Nothing is implemented, downloaded or run.**
```

New:

```text
- **Status: DESIGN REVISION 5 — pending an independent confirmation; lead's approval PENDING; nothing implemented, downloaded or run. SPEC: PENDING ASTRA REVIEW.**
```

### C02 — header, after the editorial-corrections line

- **Finding answered:** task items 1, 7
- **Reason:** Says what revision 5 is and where the previous text is.
- **Mode:** insert after

Anchor (unchanged):

```text
The text before these corrections is `docs/reviews/p10-design-2026-11-15/revisions/ADR-0022-rev4-before-E8.md`.
```

Inserted:

```text
- **Revision 5** applies the re-check of revision 4 (`adr-0022-review/RECHECK_REV4.md`, Opus 5.5: READY SUBJECT TO text edits; majors J1–J8, minors J9–J14 and others) and does nothing else. No threshold, arm, model, data source, replicate count, rung or cap is changed. Points the re-check left open are settled by the P9 / P9-II convention where one exists, otherwise by the option that is harder for a positive label or counts more time against the cap; each is marked **[lead's choice]** and listed in §20 with the alternative not taken. §21 maps each change to its finding. The revision 4 text is kept at `docs/reviews/p10-design-2026-11-15/revisions/ADR-0022-rev4.md`.
```

### C03 — header, the two capabilities

- **Finding answered:** re-check §4 (stale sentence); task item 4
- **Reason:** The human lead answered reserved item 3; the header still said the decision was pending.
- **Mode:** replace

Old:

```text
- **Decision that stays with the human lead.** This design uses two translation directions (English→German, English→French) as the two capabilities. They are two capabilities of one kind. **Whether that satisfies "complementary capabilities" is the human lead's decision, not the lead's** (§16).
```

New:

```text
- **The two capabilities.** This design uses two translation directions (English→German, English→French) as the two capabilities. The human lead has accepted them as the two capabilities of this study (§18, item 3). They remain two capabilities of one kind, and §17 limits what a result can mean.
- **Oracle qualification.** Every address and every registered route in S2 is supplied by rule. "Learned memory" in the title names a store whose keys and values are trained; it does not name learned addressing. The human lead's instruction, verbatim: "S1 and S2 must not claim autonomous learned-memory success from oracle-assisted results." §11.3 puts the oracle-assisted line above every printed class, label, annotation and cost line.
```

### C04 — header, evidence line

- **Finding answered:** task item 1
- **Reason:** The re-check is review evidence like the two earlier reviews.
- **Mode:** insert after

Anchor (unchanged):

```text
both Opus 5.5, with the two synthetic probes, are review evidence, not registered results.
```

Inserted:

```text
 The re-check of revision 4 (`adr-0022-review/RECHECK_REV4.md`, Opus 5.5) has the same standing.
```

### C05 — revision history, row 4

- **Finding answered:** task item 7
- **Reason:** Revision 4 is no longer the current text; its re-check is recorded.
- **Mode:** replace

Old:

```text
| 4 | 2026-11-15 | confirmed subject to C1–C10 and m1–m7, which this revision applies |
```

New:

```text
| 4 | 2026-11-15 | applied C1–C10 and m1–m7; re-checked by the auditor: READY SUBJECT TO text edits (J1–J8 major, J9–J14 and others minor; `adr-0022-review/RECHECK_REV4.md`) |
```

### C06 — revision history, row 5

- **Finding answered:** task item 7
- **Reason:** Adds revision 5 to the history.
- **Mode:** insert after

Anchor (unchanged):

```text
"(n, U)" on every label; the meaning of "every replicate" stated. §19 maps every finding. |
```

Inserted:

```text
| 5 | 2026-11-15 | pending an independent confirmation; lead's approval PENDING | applies the re-check of revision 4: generator seeds listed and seeded directly, with seed gate G9; key initialization stated; the download scope stated once (what is approved, what is open with the human lead); marker strings of the GEN panel within tokens 1–64; router training recipe; disjoint training draws and gold sufficiency; the rung rule's rates and charged scope, and NOT STARTED: BUDGET; RET reference; LoRA and E-table initialization; filter tie-break; window grid; BOS from the reference default; the oracle-assisted line above every printed class and line. No threshold, arm, model, data source, replicate count, rung or cap changed. §21 maps every finding. |
```

### C07 — §0 item 6

- **Finding answered:** re-check §2 item 3; task item 6
- **Reason:** Names the unreachable-budget outcome. The reading of the projection is revision 4's, because the recomputation is not charged (lead's ruling 1).
- **Mode:** replace

Old:

```text
The projection (§13) fits the cap with 2× headroom only at the fast end of an unmeasured throughput estimate. The rehearsal rule decides (§13.3); it can end at three replicates, at shortened training, or in "not started".
```

New:

```text
The projection (§13) fits the cap with 2× headroom only at the fast end of an unmeasured throughput estimate. The rehearsal rule decides (§13.3); it can end at three replicates, at shortened training, or in **NOT STARTED: BUDGET**.
```

### C08 — §3, key initialization

- **Finding answered:** J2 (E-J2, verbatim) and J1
- **Reason:** The key distribution was never stated; appended rows must not repeat the stage-1 draw.
- **Mode:** insert after

Anchor (unchanged):

```text
*(lead's choice)*; the report states that the append cost depends on that initialization.
```

Inserted:

```text
 Keys are initialized from a normal distribution with standard deviation 0.02 *(lead's choice; as P9's `_matrix`)*. Appended keys and values are drawn from the same distributions with the stage-2 seed (§9), never with the stage-1 seed. **[lead's choice]** The alternative, keys of unit scale, would make the keys move far less per update under the cosine score; the P9 convention is kept.
```

### C09 — §3, reference test

- **Finding answered:** J1; lead's ruling 6
- **Reason:** P9's memory class seeds its own generators at seed + 1000·k; the reference test must not bring that derivation into S2.
- **Mode:** insert after

Anchor (unchanged):

```text
- **Reference test.** On shared inputs the selection and weights equal those of the P9 flat memory forward, imported read-only.
```

Inserted:

```text
 The test passes S2's own tensors explicitly to the P9 forward. S2 does not construct P9's `ScalableMemory` from a seed, so P9's `seed + 1000·k` derivation is not exercised (§9, gate G9). If the P9 forward cannot be given the tensors without editing P9, the reference test is dropped and the report says so **[lead's choice]**.
```

### C10 — §4.2, fallback hash

- **Finding answered:** re-check §4 (fallback SHA-256)
- **Reason:** The hash is in the reviewer's saved Hub tree in the repository (`adr-0022-review/web/opus_en-es_tree.json`, LFS oid), so it is stated.
- **Mode:** replace

Old:

```text
(Apache-2.0; `pytorch_model.bin` 312,087,523 B; 77,484,009 parameters)
```

New:

```text
(Apache-2.0; `pytorch_model.bin` 312,087,523 B, SHA-256 `befce0f620e8e63f83bbb7f0818eb51d541cba28057a7cc14b00466d85c4994c` from the reviewer's saved Hub tree, `adr-0022-review/web/opus_en-es_tree.json`, to be checked at download; 77,484,009 parameters)
```

### C11 — §4.2, when the fallback is fetched

- **Finding answered:** J3; task item 3 (supersedes E-J3's "same session"); lead's ruling 7
- **Reason:** One statement of the download scope: fallback teacher and fallback data only if the fallback rule is invoked.
- **Mode:** replace

Old:

```text
The fallback's files are fetched only if it is invoked and approved (§14.1).
```

New:

```text
The fallback teacher's files and the fallback's Tatoeba files (Spanish; rows 5 and 6 of §14.1) are fetched only if the rule above invokes the fallback. The human lead's approval covers them for that case only (§18). If the fallback is invoked, the invocation first returns to the human lead (the fallback is a reserved decision); partitions and panels are then rebuilt by the same rules and seeds with the fallback language in place of the failed one, before any training.
```

### C12 — §5.2, sufficiency rule

- **Finding answered:** J7 (E-J7, verbatim, with the split rule the re-check left pending)
- **Reason:** No rule made T_A^r and T_B^r disjoint when the pools overlap; the gold draw was not in the sufficiency rule.
- **Mode:** insert after

Anchor (unchanged):

```text
or an accepted pool 8,000, the study stops with TRANSFER-INCONCLUSIVE: DATA-INSUFFICIENT.
```

Inserted:

```text
 English sources in both accepted pools are split, by the training-draw seed of each replicate, into two halves assigned to A and B before drawing. Sufficiency requires, for each capability, its exclusive accepted sources plus its half ≥ 8,000 × 1.25 *(lead's choice)*, and 8,000 gold pairs per capability outside Q, D_cal and D_con; otherwise DATA-INSUFFICIENT. **[lead's choice]** The half is the smaller one when the shared count is odd; the gold pairs are in-vocabulary pairs of 3 to 10 words. All replicates draw from one accepted pool per capability, so their training draws overlap. The share of training items common to each pair of replicates is reported, and §9's reading of "every replicate" is given with that share.
```

### C13 — §5.3, generation sample

- **Finding answered:** J1
- **Reason:** Names the seed of the source sample.
- **Mode:** insert after

Anchor (unchanged):

```text
At most 60,000 sources per capability, a seeded sample *(lead's choice)*
```

Inserted:

```text
 (seed 220903, §9)
```

### C14 — §5.3, filter tie-break

- **Finding answered:** J12
- **Reason:** No rule chose between settings with the same accepted share.
- **Mode:** insert after

Anchor (unchanged):

```text
against the best reference — is ≥ **0.90**.
```

Inserted:

```text
 Among settings with the same accepted share, the one with the larger τ is taken, then the narrower length-ratio range **[lead's choice]**.
```

### C15 — §5.3, verification

- **Finding answered:** task item 4 (recorded answer on item 4)
- **Reason:** The acceptance is the human lead's, recorded in §18, not a ruling of the lead.
- **Mode:** replace

Old:

```text
is met in this sense and no other; the lead has ruled this acceptable, and it is named in the label line (§11.3).
```

New:

```text
is met in this sense and no other; the human lead has accepted the filter as the verification of the teachers' outputs (§18, item 4), and it is named in the label line (§11.3).
```

### C16 — §5.4, address

- **Finding answered:** J1
- **Reason:** Says which seed the oracle codes use and that the hash seeds no generator.
- **Mode:** insert after

Anchor (unchanged):

```text
the code u(t, w) is a fixed random unit vector in R^16 from a seeded hash of the pair
```

Inserted:

```text
 (seed +10 of the replicate, §9; the hash takes that listed seed and the pair as inputs, as P9's `unit_code` does, and seeds no generator)
```

### C17 — §5.4, router lane

- **Finding answered:** J6 (E-J6, verbatim, then the points it left open)
- **Reason:** The router decides a label gate (GEN) and had no training recipe.
- **Mode:** insert after

Anchor (unchanged):

```text
the prompts differ in a marker word, and a pass says nothing about fine-grained addressing.
```

Inserted:

```text
 Router training: AdamW, learning rate 0.001, 500 updates of batch 64 *(lead's choice)*, on the stored prompts of the current stage's training streams only (never D_cal, D_con or an evaluation panel) and on WikiText-2 *train* prefixes of exactly 64 tokens in equal number; the projection is initialized from seed +3. The decision position in training matches GEN's (the 64th token of a "none" prefix; the last prompt token of a task prompt). **[lead's choice]** In detail, all **[lead's choice]**: "the current stage's training streams" are the prompts of T^r of every task the router of that snapshot must know — one stream for an ST1 router, T_A^r and T_B^r for a stage-2 or joint router; prompts only, and no teacher is run. Every batch holds the same number of examples of each class (each task, and "none") as nearly as 64 allows, the remainder going to "none". The "none" prefixes are consecutive non-overlapping 64-token pieces of the tokenized WikiText-2 train file, 8,000 of them sampled with seed +3. The hidden state is the output of block L, where the store would be read. The loss is cross-entropy over the cosine scores divided by the read temperature 0.2. The projection and then the router keys are drawn from N(0, 0.02) by one generator seeded +3; every router is trained from that initialization and is not continued from an earlier stage's router. A router depends on the replicate and on the set of tasks, not on the arm.
```

### C18 — §6.4, "before"

- **Finding answered:** J10
- **Reason:** §6.4's "before" (parent snapshot) and §11.1's "after Stage 1" differed for M-ii.
- **Mode:** replace

Old:

```text
"before" is the parent snapshot's score.
```

New:

```text
"before" is the parent snapshot's score, except in the RET gate and the retention negative zone, where it is V1 for every stage-2 arm (§11.1).
```

### C19 — §6.4, marker-like windows

- **Finding answered:** J5 (E-J5, verbatim)
- **Reason:** A marker string after token 64 is invisible to the router, so such a window is not a hard negative.
- **Mode:** replace

Old:

```text
"translation" or a line ending in ":"** (selected by rule with the partition seed)
```

New:

```text
"translation" or a line ending in ":", with at least one such string within tokens 1–64 of the window (the part the router sees)** (selected by rule with the GEN-window seed 220905, §9)
```

### C20 — §6.4, window grid

- **Finding answered:** J14, J5
- **Reason:** How windows are cut from the validation stream was unstated.
- **Mode:** insert after

Anchor (unchanged):

```text
This data is used for nothing else.
```

Inserted:

```text
 **Window grid **[lead's choice]**.** The validation file is tokenized once as a whole in the data-generation step and cut from its first token into consecutive, non-overlapping windows of 256 tokens; a trailing remainder is dropped. A window is in the marker-like stratum if one of the strings lies wholly within the text of its tokens 1–64, and in the ordinary stratum if it contains none of the strings anywhere. A window whose only such strings lie after token 64 is in neither stratum and is not used. 100 windows of each stratum are sampled with the GEN-window seed. If either stratum has fewer than 100 windows on this grid, neither the grid nor the rule is changed and the work returns to the lead before the freeze.
```

### C21 — §7, LoRA form

- **Finding answered:** J11
- **Reason:** LoRA scaling and initialization were unspecified.
- **Mode:** insert after

Anchor (unchanged):

```text
Placement is fixed, not tuned; calibration tunes only its learning rate.
```

Inserted:

```text
 LoRA form **[lead's choice]**: the update is (α/r)·B·A with α = r, a scale of 1; A is drawn uniform on ±1/√(fan-in), the conventional initialization (as ADR-0021 does for its dense control), from seed +8; B is zero, so an untrained adapter changes nothing; no dropout.
```

### C22 — §7, E-table row

- **Finding answered:** J11
- **Reason:** E-table initialization and gate were unspecified; it starts as the store does.
- **Mode:** replace

Old:

```text
added at layer L at the same positions as the store's reads; no keys, no top-k |
```

New:

```text
added at layer L at the same positions as the store's reads; no keys, no top-k; vectors drawn from N(0, 0.02) with seed +9 and multiplied by one linear scalar gate with initial value 0, as the store's values are **[lead's choice]** |
```

### C23 — §7, ablation subsample

- **Finding answered:** J1
- **Reason:** The subsample has its own listed seed instead of sharing the partition seed.
- **Mode:** replace

Old:

```text
drawn once with the partition seed and the same for every cell and replicate
```

New:

```text
drawn once with the ablation-subsample seed 220904 (§9) and the same for every cell and replicate
```

### C24 — §9, seeds

- **Finding answered:** J1 (E-J1, verbatim except the named streams); re-check §3 minor (S1 ranges); task item 2
- **Reason:** Generator seeds were not defined; under P9's seed + 1000·k every S2 seed would land in S2's own calibration or rehearsal range. The re-check's hash of (220901, stream name) would leave the listed sets, so the streams get listed seeds.
- **Mode:** replace

Old:

```text
- Seeds: replicate bases 220001, 220101, 220201, 220301 (base + 0 initialization, + 1 training draw, + 2 batch order, + 3 router, + 4 permutation controls, + 5 gold draw); partition seed 220901; calibration 221001–221999; rehearsal 222001–222999; tests 229001–229999. The implementation asserts the ranges are disjoint from each other and from every seed of P1–P9-II, S0 (200001–209999, 2001–2002, 2091–2092, 920001–920999) and S1, and writes the hash of every panel and stream to the data manifest.
```

New:

```text
- Seeds: replicate bases 220001, 220101, 220201, 220301, each with these offsets:
  - +0 stage-1 store (keys, then values, from one generator in that order);
  - +1 training draw;
  - +2 batch order;
  - +3 router;
  - +4 permutation controls;
  - +5 gold draw;
  - +6 stage-2 appended rows;
  - +7 M-joint store;
  - +8 LoRA initialization;
  - +9 E-table initialization;
  - +10 oracle-code hash **[lead's choice]** (per replicate, as every data draw of P9-II and of S1 carries its own code seed; the alternative is one fixed code seed for all replicates).

  Within a replicate, the M-seq and M-ii arms start from the snapshots they continue. Partition seed 220901. The other partition-side streams each have a listed seed **[lead's choice]**: 220902 the Q split, 220903 the 60,000-source sample, 220904 the ablation subsample, 220905 the GEN window selection. (The re-check's text took these streams by a hash of (220901, stream name); a hashed seed would leave the listed sets.) Calibration draws use 221001 + 100·i and rehearsal draws 222001 + 100·i with the same offsets, i = 0…9; tests use 229001–229999. Every generator is seeded directly by a listed seed: **no "+1000·k" derivation is used**, and no seed is obtained by hashing or by arithmetic on another seed beyond the offsets listed here. One seed serves the uses that §9 pairs, in a fixed order **[lead's choice]**: +0 initializes ST1 of both orders and MA-gold of both capabilities; +6 the appended rows of both orders (keys, then values); +8 LoRA-1 of both orders and, with its own shapes, L-joint; +9 E-table of both capabilities; +1 and +5 draw capability A, then B.

  The implementation asserts that every seed actually passed to a generator lies in the listed sets and is disjoint from:
  - P1–P9-II (as listed in ADR-0021 §6.3);
  - S0 (200001–209999, 2001–2002, 2091–2092, 920001–920999);
  - S1 (210001–219999, 2101–2105, 2111, 2112, 2121, 2122, 2191–2192, 921001–921999).

  Every listed registered seed lies in S2's namespace 220001–228999 and outside S2's calibration (221001–221999), rehearsal (222001–222999) and test (229001–229999) ranges; gate G9 (§12.3) asserts it on the seeds actually used. The implementation writes the hash of every panel and stream to the data manifest.
```

### C25 — §9, class and label lines

- **Finding answered:** re-check §5 (E-5); task item 5
- **Reason:** "(n, U)" was required on class lines but the oracle-assisted line was not.
- **Mode:** insert after

Anchor (unchanged):

```text
- Every class and label line prints "(n replicates, U = …)"
```

Inserted:

```text
, under the oracle-assisted line of §11.3
```

### C26 — §11.1, RET

- **Finding answered:** J10 (E-J10, verbatim)
- **Reason:** States the reference snapshot of RET for every stage-2 arm.
- **Mode:** replace

Old:

```text
| RET | s_first after Stage 2 ≥ s_first after Stage 1 − 0.03, and G_first after ≥ 0.90 × G_first before |
```

New:

```text
| RET | s_first after Stage 2 ≥ s_first after Stage 1 − 0.03, and G_first after ≥ 0.90 × G_first before. "after Stage 1" and "before" mean V1 (the ST1 snapshot) for every stage-2 arm, including M-ii **[lead's choice]** (the alternative is the parent snapshot, which for M-ii is M-append-frozen's) |
```

### C27 — §11.2, class lines

- **Finding answered:** re-check §5 (E-5); task item 5
- **Reason:** A mechanism-class line could be printed without the oracle-assisted line.
- **Mode:** insert after

Anchor (unchanged):

```text
M-i-separate and L-sep are printed **BY CONSTRUCTION** and receive no class.
```

Inserted:

```text
 Every class line is printed under the oracle-assisted line of §11.3.
```

### C28 — §11.3, row 1

- **Finding answered:** J1; task item 2
- **Reason:** The new seed gate G9 is an engineering gate like the others.
- **Mode:** replace

Old:

```text
a defect found by gates G1, G4–G8;
```

New:

```text
a defect found by gates G1, G4–G9;
```

### C29 — §11.3, after the fixed line

- **Finding answered:** re-check §5 (E-5, verbatim, first bullet); task item 5
- **Reason:** Positive-sounding class, router, composition and cost lines could be printed without the fixed line.
- **Mode:** insert after

Anchor (unchanged):

```text
teacher-only training material verified by measured-precision filter; not autonomous learned memory."**
```

Inserted:

```text
- The same line heads every mechanism-class line, every annotation and every table of the outcome report that prints a class or label, and every cost line.
- **No positive wording without it.** The human lead's instruction, verbatim: "S1 and S2 must not claim autonomous learned-memory success from oracle-assisted results." The words ACQUIRES-AND-RETAINS, TRANSFER-POSITIVE, QUALIFIED, COMPOSES, TRAINING COST COMPARABLE and FEWER VALUE ROWS ACTIVE, and every other class, mechanism, router, composition or cost line, are therefore printed only directly under that line: in the outcome report, in every table and figure caption, in the machine-readable outcome record (as a field of the same record), and in any summary a script writes to the terminal or to a log. The analysis refuses to write an output in which such a line lacks it, and the report test on synthetic records (§13.3, rehearsal content) checks every such line.
```

### C30 — §11.4, annotations

- **Finding answered:** re-check §5 (E-5); task item 5
- **Reason:** ROUTER QUALIFIED and COMPOSES could appear in a table of their own without the line.
- **Mode:** insert after

Anchor (unchanged):

```text
| Cost lines | always printed (§11.5) |
```

Inserted:

```text
Every annotation, the ROUTER and COMPOSES lines included, is printed under the oracle-assisted line of §11.3, also when it appears in a table of its own.
```

### C31 — §11.5, cost lines

- **Finding answered:** re-check §5 (E-5); task item 5
- **Reason:** Cost lines are positive-sounding and carried no qualification.
- **Mode:** insert after

Anchor (unchanged):

```text
None is an efficiency result. Logical counts are never reported as measured efficiency.
```

Inserted:

```text
 Each cost line is printed under the oracle-assisted line of §11.3.
```

### C32 — §12.3, G5(c)

- **Finding answered:** J13 (E-J13, verbatim)
- **Reason:** 0 · inf is NaN; the isolation test holds for finite values.
- **Mode:** replace

Old:

```text
replaced by arbitrary values equals r with them at zero
```

New:

```text
replaced by arbitrary finite values equals r with them at zero
```

### C33 — §12.3, G5 key initialization

- **Finding answered:** J2
- **Reason:** Points G5's sentence at the stated distribution and seed.
- **Mode:** insert after

Anchor (unchanged):

```text
Appended keys are initialized from the same distribution as first-stage keys *(lead's choice)*, and the report states that the append cost depends on that initialization.
```

Inserted:

```text
 The distribution is normal with standard deviation 0.02, drawn with the stage-2 seed (§3, §9).
```

### C34 — §12.3, new gate G9

- **Finding answered:** J1; task item 2
- **Reason:** A gate must assert the namespace on the seeds actually used, not on declared ranges.
- **Mode:** insert after

Anchor (unchanged):

```text
including the stored injection-point logits and the stored greedy sequences of §14.2 step 4.
```

Inserted:

```text
- **G9** seeds (§9). Every generator in `studies/p10s2/` is seeded through one function, which records the seed and its purpose and refuses a seed outside the set allowed for the running stage. The gate asserts, on the seeds planned for the registry and again on the seeds actually recorded: every seed of the registered run is one of the listed registered seeds (a replicate base + 0…10, or 220901–220905), lies in 220001–228999 and lies outside 221001–221999, 222001–222999 and 229001–229999; every calibration seed lies in 221001–221999, every rehearsal seed in 222001–222999 and every test seed in 229001–229999; no recorded seed lies in a range of P1–P9-II, S0 or S1 listed in §9. A source check asserts that no generator is seeded anywhere else and that the global default generator is not used. The recorded seed list is written to the run record. A seed outside its set stops the run.
```

### C35 — §13.2, charging rule

- **Finding answered:** J8b
- **Reason:** States what is charged: the second gates stage is; the recomputation is not (lead's ruling 1).
- **Mode:** insert after

Anchor (unchanged):

```text
The data-generation step, calibration, pilot, rehearsal and the registered run are all charged.
```

Inserted:

```text
 So is the second gates stage on registered seeds. The independent recomputation of §16 step 10 is not charged (§13.3).
```

### C36 — §13.3, projection table

- **Finding answered:** J8b
- **Reason:** The table had no row for the second gates stage, which is inside R, nor for the recomputation, which is stated for information.
- **Mode:** insert after

Anchor (unchanged):

```text
| **Registered run** | | | | **14.4–35.5 h** |
```

Inserted:

```text
| Second gates stage on registered seeds (inside R; not in the row above): four scorings of E_A and E_B at the rate above, plus at most 0.05 h for the repeated updates, the general panel and the hash checks | both | — | — | 0.1–0.4 h |
| Independent recomputation of every score (§16 step 10): an audit step after the registered run, **not charged** (§13.3); for information, one repetition of the three scoring rows, an upper estimate | CPU | — | — | 5.8–18.8 h |
```

### C37 — §13.3, after the rung list

- **Finding answered:** J8a, J8b, re-check §2 item 3 (E-J8, adapted); lead's ruling 1
- **Reason:** Fixes which rates the rule uses after a re-selection at U = 1,000, what R contains, and the name of the outcome "none".
- **Mode:** insert after

Anchor (unchanged):

```text
5. none: the run is not started and the lead returns to the human lead.
```

Inserted:

```text
**Rates and scope of the rule (revision 5).** R(n, U) contains, for n replicates: training; every scoring of the registered run; the timing benchmark; and the second gates stage on registered seeds. **The independent recomputation of every score (§16 step 10) is not in R and is not charged to the 36 hours** **[lead's choice]**. It is an audit step performed after the registered run by a separate auditor context, and the project's convention is that such a recomputation is not charged to the study's budget: the Opus recomputations of P9-I and P9-II were not charged to those studies. (The alternative not taken is the recomputation inside R.) For information, it is projected at 5.8–18.8 h for four replicates and 4.4–14.3 h for three, as one repetition of the three scoring rows, an upper estimate. It must respect the per-process memory limits of this section (8 GiB per worker, 24 GiB aggregate), and no result is reported before it completes. For U = 2,000 the training rates are those of the calibrated setting, rehearsed at full length. For U = 1,000 the setting may be re-selected (§12.1), and the read layer may change with it. R(n, 1,000) therefore uses, for every store-type cell, the slower of the rates measured at L = 4 and at L = 12 **[lead's choice]** (the slower rate counts more time against the cap; the re-check's text used the rates of the re-selected setting). The read layer that was not rehearsed at full length is measured on 200 rehearsal updates of each store-type cell type before the rule is applied, and that time is part of P. The second gates stage enters R at the time the rehearsal's gates stage measured. The outcome "none" is recorded as **NOT STARTED: BUDGET** with the rehearsal record. A re-design after it is a new decision of the human lead (§16).
```

### C38 — §13.3, projection sentence

- **Finding answered:** re-check §2 (E-m1: stale parenthetical, 7.6); J8b; lead's ruling 1
- **Reason:** The parenthetical invited adding a change twice; rung 4 computes to 7.64. The second gates stage is inside R and is shown.
- **Mode:** replace

Old:

```text
On the projection above the registered run is 14.4–35.5 h at rung 1, 10.8–26.8 h at rung 2, 10.1–27.2 h at rung 3 and 7.7–20.5 h at rung 4 (removing M-seq-shared and adding L-joint changes each by about +0.1 to +0.3 h per replicate). A rung holds only if its registered run measures at about 15 hours or less, so rung 1 holds only at the fast end. **It is plausible that the rule ends at rung 2 or below, or at "not started".**
```

New:

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

### C39 — §13.3, rehearsal content

- **Finding answered:** J8a
- **Reason:** The rates of the read layer not selected must be measured for the rule.
- **Mode:** insert after

Anchor (unchanged):

```text
one store cell, one M-ii cell and one LoRA cell for the full U;
```

Inserted:

```text
 200 updates of each store-type cell type at the read layer that calibration did not select (for the rule's rates);
```

### C40 — §14.1, opening paragraph

- **Finding answered:** J3, J4; re-check §4 (stale "no answer yet"); task items 3 and 4
- **Reason:** One statement of what is approved and what is open.
- **Mode:** replace

Old:

```text
The lead has asked the human lead about the student and the data and has no answer yet. The human lead's words cover "two small teachers"; everything else in this table is outside those words.
```

New:

```text
**Approved by the human lead and recorded (§18):** rows 1–4 — the two teachers, the student and the Tatoeba exports; only if the fallback rule of §4.2 is invoked, rows 5 and 6, the fallback teacher and the fallback (Spanish) data; and the package wheels for the one-off data-generation step (§14.2). **Not approved, open with the human lead:** the two symmetry-check link files (6.2 MB, below), about which the lead has asked again; any package outside the lock other than those wheels. Nothing in the open list is fetched before a recorded answer of the human lead, given with the sizes in front of them. Implementation and tests on synthetic stand-ins need none of it. No download has been made.
```

### C41 — §14.1, row 6

- **Finding answered:** J3; task item 3
- **Reason:** The fallback data are fetched only if the fallback is invoked.
- **Mode:** replace

Old:

```text
| 6 | Fallback data — fetched in the same session as row 4 so that all Tatoeba files come from one weekly export; opened only if the fallback is invoked |
```

New:

```text
| 6 | Fallback data, only if invoked |
```

### C42 — §14.1, total row

- **Finding answered:** J3, J4; task item 3
- **Reason:** The totals follow the scope above and name what is outside them.
- **Mode:** replace

Old:

```text
**930 MB primary; 938 MB with the fallback data fetched in the same session; 1,253 MB if the fallback teacher is invoked**
```

New:

```text
**930 MB approved and fetched (rows 1–4); 8.1 MB + 315.3 MB more only if the fallback is invoked (1,253 MB in all). Not in these figures: the package wheels (approved, §14.2; about 23 to 32 MB for the eight named packages, their dependencies recorded at fetch time); 6.2 MB of symmetry-check link files (not approved)**
```

### C43 — §14.1, symmetry-check link files

- **Finding answered:** J3, J4; task item 3
- **Reason:** The 6.2 MB were in no figure shown to the human lead and cannot be "part of row 4's approval".
- **Mode:** replace

Old:

```text
if those two files are fetched for the check they add 6.2 MB and are part of row 4's approval.
```

New:

```text
those two files add 6.2 MB. **They were in no figure shown to the human lead and are not approved.** The human lead's answer on the package wheels did not name them, and the lead has asked again (§18). The symmetry check against them is made only if the human lead approves them; they are then fetched in the same session as row 4. Without them the check is not made, and the data manifest and the report say that the symmetry of the link files was not checked **[lead's choice]**.
```

### C44 — §14.1, one session

- **Finding answered:** J3; task item 3
- **Reason:** "All Tatoeba files, the fallback's included, in one session" contradicted §4.2 and §18.
- **Mode:** replace

Old:

```text
- **One session.** All Tatoeba files, the fallback's included, are fetched in one session, because a later fetch would come from a different weekly export.
```

New:

```text
- **One session.** The five files of row 4 (and the two link files, if approved) are fetched in one session, because a later fetch would come from a different weekly export. The fallback's Tatoeba files are not fetched with them. If the fallback is invoked, they come from a later weekly export: link rows whose English sentence id is absent from the frozen English file are dropped and counted, the dates of both sessions are recorded, and the report states the mix **[lead's choice]**.
```

### C45 — §14.2 step 4, BOS

- **Finding answered:** re-check §1 C8 (E-m3, verbatim)
- **Reason:** BOS is decided by a rule instead of by the lead's expectation.
- **Mode:** replace

Old:

```text
BOS is not prepended in any input *(lead's choice; the same convention in the equivalence logits and every registered input)*
```

New:

```text
BOS follows the reference tokenizer's default for this model, read from the pinned `tokenizer.json`/`tokenizer_config.json` and recorded in the data-generation step; the draft expects "not prepended" (the same convention in the equivalence logits and every registered input)
```

### C46 — §14.2, sacrebleu row

- **Finding answered:** re-check §4 (stale sentence)
- **Reason:** `CONFIRM.md` §6 checked existence, licence and advisories.
- **Mode:** replace

Old:

```text
analysis-only cross-check; exists on PyPI, Apache-2.0; not checked by the reviewer
```

New:

```text
analysis-only cross-check; exists on PyPI, Apache-2.0, no advisories (`CONFIRM.md` §6); brings portalocker, regex, tabulate, colorama, lxml and numpy
```

### C47 — §14.2, package wheels

- **Finding answered:** J4; re-check §4 (stale sentence); lead's ruling 4
- **Reason:** The human lead has approved the wheels; the sentence said the question was left open.
- **Mode:** replace

Old:

```text
- Package wheels are themselves downloads. Whether they may be fetched is left to the human lead (§16); none is fetched before the answer.
```

New:

```text
- **Package wheels are themselves downloads. The human lead has approved them (§18):** the eight packages named above and the dependencies the resolver requires for them, pinned with exact versions and hashes in the requirements file of the freeze, installed with `uv run --locked --with`; `uv.lock` and `pyproject.toml` do not change. The 938 MB figure did not include them. From the reviewer's saved index records (`adr-0022-review/web/pypi_*.json`), the wheels of the eight named packages for macOS arm64 and Python 3.12 total about 23 MB, or about 32 MB if numpy's larger wheel is the one selected. The transitive dependencies are not in those records; their names, versions, hashes and sizes are recorded at fetch time. Nothing else is installed outside the lock without a further answer. By §16 the wheels are fetched with the downloads, after implementation on synthetic stand-ins.
```

### C48 — §15, standing of the departures

- **Finding answered:** J9; re-check §4 (§15 item 3); lead's rulings 3, 4 and 8
- **Reason:** Departures 1, 4, 5 and 7 were neither reserved for the human lead nor accepted anywhere.
- **Mode:** insert after

Anchor (unchanged):

```text
7. Data without a revision identifier: frozen by recorded hash, not by pin.
```

Inserted:

```text
**Standing of each item at revision 5.** Item 2 rests on the human lead's answer recorded in §18 (training on MPS with every score recomputed on CPU). Item 3 rests on the human lead's sentence "im confortable with does number …" quoted in §18, which answered the lead's message listing S0 16 h, S1 12 h, S2 36 h, total 64 h (§18). Item 6 rests on the human lead's approval of the package wheels (§18) and reaches no other package. Items 1, 4, 5 and 7 are neither reserved for the human lead in §16 nor yet accepted: their acceptance is for the lead's approval record in §18, under the delegation "we can change it to  p10 can be self approve but p10-I need my review". This revision does not record that acceptance.
```

### C49 — §16, order of work

- **Finding answered:** J3, J4; task item 3
- **Reason:** The order of work must show that the data-generation step waits for the open answers.
- **Mode:** replace

Old:

```text
**Order.** (1) The human lead's answers on the five reserved items below. (2) Lead's approval, recorded in §18. (3) Implementation review as the work proceeds. (4) Implementation with tests on synthetic stand-ins, before any download. (5) Downloads; data-generation step.
```

New:

```text
**Order.** (1) The human lead's answers on the reserved items below: recorded in §18, except the link files. (2) Lead's approval, recorded in §18. (3) Implementation review as the work proceeds. (4) Implementation with tests on synthetic stand-ins, before any download. (5) Downloads of the approved files (§14.1) and of the approved wheels (§14.2); data-generation step.
```

### C50 — §16, reserved items

- **Finding answered:** J3, J4; re-check §4; task items 3 and 4
- **Reason:** The list now shows which items are answered and which are open, in the words of §14.1 and §18.
- **Mode:** replace

Old:

```text
The five items the auditor left for the human lead; the lead does not decide them:

1. The downloads of the student (272.4 MB), the Tatoeba data (53.1 MB), and the fallback teacher and data (315.3 MB + 8.1 MB) (§14.1).
2. Whether the package wheels for the data-generation step count as downloads (§14.2).
3. Whether two translation directions are "complementary capabilities".
4. Whether a filter of measured precision counts as "suitable verification" (§5.3).
5. Acceptance of training on MPS and of packages outside the lock (§15 items 2 and 6).
```

New:

```text
The five items the auditor left for the human lead, with their state at revision 5 (§18 holds the words), and a sixth from the re-check. The lead does not decide them:

1. The downloads of the two teachers (300.8 MB + 303.7 MB), the student (272.4 MB) and the Tatoeba data (53.1 MB), and, only if the fallback rule is invoked, the fallback teacher and data (315.3 MB + 8.1 MB) (§14.1). **Answered: approved.**
2. The package wheels for the data-generation step (§14.2; about 23 to 32 MB for the eight named packages, their dependencies recorded at fetch time). **Answered: approved.**
3. Whether two translation directions are "complementary capabilities". **Answered: yes.**
4. Whether a filter of measured precision counts as "suitable verification" (§5.3). **Answered: yes.**
5. Acceptance of training on MPS and of packages outside the lock (§15 items 2 and 6). **Training on MPS with scores recomputed on CPU: answered, yes. Packages outside the lock: approved for the data-generation wheels of item 2 and for nothing else.**
6. The two symmetry-check link files (6.2 MB, §14.1). **Open: not approved.** The answer on item 2 did not name them; the lead has asked again.

Nothing in an open item is fetched or installed before a recorded answer.
```

### C51 — §18, end of the approval record

- **Finding answered:** J3, J4, J9; task items 3 and 4; lead's rulings 3, 4 and 8
- **Reason:** Records the human lead's answer on the wheels and the context of the 36-hour sentence; states the download scope once, without rewriting the earlier records; places the acceptance of §15 departures with the lead's approval record; updates the pending line.
- **Mode:** replace

Old:

```text
Lead's approval: PENDING revision 5, which answers the re-check (majors J1–J8), and its confirmation.
```

New:

```text
**Human lead's answer on the package wheels — 2026-11-15 (UTC), verbatim:**

> "yes I do, yes we can raise to 16 and I approve the package"

The third clause answered the lead's question: "Approve the package wheels and the 6.2 MB of link files for S2? These were not in the 938 MB figure." (The first two clauses answer other questions.)

Recorded by the lead:

- **The package wheels for the one-off data-generation step are approved:** the eight packages named in §14.2 and the dependencies the resolver requires for them, pinned in the requirements file of the freeze, installed with `uv run --locked --with`; `uv.lock` and `pyproject.toml` do not change. The eight named packages come to about 23 to 32 MB; the transitive dependencies are recorded at fetch time.
- **The two symmetry-check link files (6.2 MB) were not named in the answer and stay not approved.** The lead has asked again. Until an answer names them they are not fetched and the symmetry check is not made (§14.1).
- **Context of the second quotation at the head of this section** ("im confortable with does number …"): it answered the lead's message listing S0 16 h, S1 12 h, S2 36 h, total 64 h. The human lead has since raised S1's cap to 16 h; S2's 36 h is unchanged. §15 item 3 rests on it.

**Download scope as revision 5 states it** (one statement for §4.2, §14.1, §14.2 and §16; it adds no approval and removes none):

- Approved by the human lead and recorded above: the two teachers, the student, the Tatoeba data; the fallback teacher and the fallback (Spanish) data only if the fallback rule of §4.2 is invoked; the package wheels for the one-off data-generation step.
- Not approved, open with the human lead: the 6.2 MB of symmetry-check link files; any package outside the lock other than those wheels.
- Nothing in the open list is fetched before a recorded answer. Implementation and tests on synthetic stand-ins need none of it.
- The re-check's paste-ready edits to the earlier records (E-J3 for item 1, E-J4 for item 2 and for the last bullet) are not applied to those records: the lead's correction keeps them as written and supersedes them. E-J3's "fetched in the same session" is not adopted (§14.1).

**§15 departures 1, 4, 5 and 7 (J9).** Their acceptance is for the lead's approval record, under the delegation "we can change it to  p10 can be self approve but p10-I need my review". It is not given in this revision.

Lead's approval: PENDING. Revision 5 answers the re-check (majors J1–J8, minors J9–J14 and others; §21) and awaits an independent confirmation.
```

### C52 — §19, not applied verbatim, item 1

- **Finding answered:** re-check §1 C8 (E-m3)
- **Reason:** The BOS choice is replaced by the re-check's rule.
- **Mode:** insert after

Anchor (unchanged):

```text
because the student was trained with whichever convention its authors used.
```

Inserted:

```text
 *Revision 5: replaced by the re-check's rule; BOS follows the reference tokenizer's default (§14.2).*
```

### C53 — §19, not applied verbatim, item 5

- **Finding answered:** J3, J4
- **Reason:** The two link files are not covered by any approval.
- **Mode:** insert after

Anchor (unchanged):

```text
which the download table did not list before; they are now named under row 4.
```

Inserted:

```text
 *Revision 5: these two files are not approved and are open with the human lead (§14.1, §18).*
```

### C54 — §20, table row BOS and keys

- **Finding answered:** J2; E-m3
- **Reason:** Keeps the list of choices in step with §3 and §14.2.
- **Mode:** replace

Old:

```text
| BOS convention; appended-key initialization | not prepended; same distribution as first-stage keys | §14.2, §3 |
```

New:

```text
| BOS convention; key initialization | the reference tokenizer's default (expected: not prepended); normal, standard deviation 0.02, appended rows drawn with the stage-2 seed | §14.2, §3 |
```

### C55 — §20, table row seeds

- **Finding answered:** J1
- **Reason:** Keeps the list of choices in step with §9.
- **Mode:** replace

Old:

```text
| Seeds | replicate bases 220001, 220101, 220201, 220301; partition 220901 | §9 |
```

New:

```text
| Seeds | replicate bases 220001, 220101, 220201, 220301 with offsets +0…+10; partition-side streams 220901–220905; every generator seeded directly | §9 |

**Choices made in revision 5 where the re-check left a point open** (each marked **[lead's choice]** in the text; rule used: the P9 / P9-II convention where one exists, otherwise the option that is harder for a positive label or counts more time against the cap):

| Point | Choice | Alternative not taken | Section |
|---|---|---|---|
| J1 seed derivation | every generator seeded directly by a listed seed; offsets +0…+10 per replicate | P9's `seed + 1000·k`, which lands in S2's own calibration and rehearsal ranges with the present bases | §9, G9 |
| J1 partition-side streams | listed seeds 220902–220905 | a hash of (220901, stream name), which leaves the listed sets | §9 |
| J1 oracle-code seed | per replicate (+10) | one fixed code seed for all replicates | §5.4, §9 |
| J1 appended rows | own seed +6, keys then values | reuse of the stage-1 seed (duplicates the first-stage keys) | §3, §9 |
| J1 seeds shared between cells | +0 for ST1 of both orders and MA-gold; +8 for LoRA-1 and L-joint; +9 for E-table of both capabilities | a separate seed per cell | §9 |
| J2 key initialization | normal, standard deviation 0.02, as P9's `_matrix` | unit-scale keys | §3 |
| J5 marker placement | at least one marker-like string within tokens 1–64 of every window of that stratum; windows with such strings only later are not used | keep such windows and report their share | §6.4 |
| J6 router recipe | AdamW, 0.001, 500 updates of batch 64; prompts of every task the router must know; balanced classes; 8,000 "none" prefixes of 64 tokens; hidden state at block L; cross-entropy over cosine scores at temperature 0.2; trained from seed +3 for every snapshot | the second stream only at stage 2; the final layer's hidden state; continuing the earlier router | §5.4 |
| J7 disjoint draws | shared accepted sources split in halves by each replicate's training-draw seed; pool ≥ 8,000 × 1.25 per capability; 8,000 gold pairs per capability; overlap between replicates reported | draws disjoint across replicates (pool ≥ n × 8,000), harder to satisfy; one split fixed by the partition seed | §5.2 |
| J8a rates after re-selection | the slower of the rates at L = 4 and L = 12 | the rates of the re-selected setting | §13.3 |
| J8b scope of R | second gates stage inside R and the 36 hours; the independent recomputation not charged (the P9-I / P9-II convention), within the memory limits, and no result reported before it completes | the recomputation inside R | §13.2, §13.3 |
| P9 reference test | tensors passed explicitly to the P9 forward; `ScalableMemory` never constructed from a seed; the test is dropped, and the report says so, if that needs an edit of P9 | constructing the P9 module with a seed | §3 |
| J10 RET reference | V1 for every stage-2 arm | the parent snapshot (M-append-frozen's for M-ii) | §6.4, §11.1 |
| J11 LoRA form | α = r; A uniform on ±1/√(fan-in), B zero; no dropout | α = 2r; A normal with standard deviation 0.02 | §7 |
| J11 E-table | N(0, 0.02) with a linear scalar gate at 0, as the store | zero vectors without a gate | §7 |
| J12 filter tie-break | larger τ, then the narrower length-ratio range | first in grid order | §5.3 |
| J14 window grid | consecutive non-overlapping 256-token windows from the first token; fewer than 100 in a stratum returns to the lead | overlapping windows; filling a short stratum from the other | §6.4 |
| Seed gate | G9, with a failure counted under ENGINEERING-FAILURE like G4–G8 | an assertion outside the gate list | §11.3, §12.3 |
| Link files not approved | the symmetry check is not made and the report says so | not starting the data-generation step without it | §14.1 |
| Fallback data from a later export | link rows to English ids absent from the frozen file dropped and counted | fetching the 8.1 MB with row 4, as revision 4's table said | §14.1 |
```

### C56 — open questions, item 4

- **Finding answered:** re-check §1 C8 (E-m3)
- **Reason:** The BOS question is settled by rule.
- **Mode:** replace

Old:

```text
4. BOS: "not prepended" is written as the lead's choice; confirm against the reference tokenizer's default before the freeze.
```

New:

```text
4. BOS: settled by rule in revision 5 (the reference tokenizer's default, recorded in the data-generation step).
```

### C57 — open questions, added

- **Finding answered:** task item 2
- **Reason:** Points the lead at the choices this revision made by rule.
- **Mode:** insert after

Anchor (unchanged):

```text
6. Should the equivalence tolerance (1e-3) be replaced by a measured run-to-run difference of the reference, as the auditor prefers?
```

Inserted:

```text
7. The choices of revision 5 listed at the end of §20, each with its alternative. The heaviest in consequence: training draws that overlap between replicates; the oracle-code seed per replicate; the recomputation outside the charged hours.
```

### C58 — things to verify, first bullet

- **Finding answered:** re-check §4 (stale); task item 3
- **Reason:** The reserved items are answered except the link files.
- **Mode:** replace

Old:

```text
- The human lead's answers on the five reserved items of §16.
```

New:

```text
- The human lead's answer still open: the two symmetry-check link files (§16); the lead has asked again.
```

### C59 — things to verify, package set

- **Finding answered:** re-check §4 (stale sacrebleu sentence)
- **Reason:** The reviewer did check sacrebleu; the resolution is run when the wheels are fetched.
- **Mode:** replace

Old:

```text
- That the package set of §14.2 resolves with torch 2.8.0 on Python 3.12; `sacrebleu` 2.5.1 was not checked by the reviewer.
```

New:

```text
- That the package set of §14.2 resolves with torch 2.8.0 on Python 3.12. Not run; it is run when the approved wheels are fetched (§16 step 5).
```

### C60 — new §21

- **Finding answered:** task item 7
- **Reason:** Maps each change to its finding.
- **Mode:** insert before

Anchor (unchanged):

```text
## Open questions for the lead
```

Inserted:

```text
## 21. Map of the re-check of revision 4 (`RECHECK_REV4.md`) to revision 5

| Finding | Change | Where |
|---|---|---|
| J1 (major) generator seeds | Offsets +0…+10 per replicate; listed stream seeds 220902–220905; direct seeding, no +1000·k; S1's ranges listed; gate G9 on the seeds actually used; G9 in ENGINEERING-FAILURE | §3, §5.3, §5.4, §7, §9, §11.3, §12.3 |
| J2 (major) key initialization | Normal, standard deviation 0.02; appended rows from the stage-2 seed | §3, §12.3 |
| J3 (major) download scope | One statement: rows 1–4 approved; fallback teacher and data only if invoked; link files and wheels open. E-J3's "same session" for the fallback data not adopted | §4.2, §14.1, §16, §18 |
| J4 (major) wheels not in the figure | The figure's content stated; the human lead's later approval of the wheels recorded; the link files stay open; sizes from the saved index records where they exist | §14.1, §14.2, §16, §18 |
| J5 (major) marker placement | At least one marker-like string within tokens 1–64 | §6.4 |
| J6 (major) router recipe | E-J6, with data, balance, layer, loss and initialization stated | §5.4 |
| J7 (major) disjoint draws, gold | E-J7; overlap between replicates reported | §5.2 |
| J8 (major) rung rule | Slower of the two read layers' rates at U = 1,000; second gates stage inside R and shown in the rung table; recomputation not charged, by the P9-I / P9-II convention; NOT STARTED: BUDGET | §0, §13.2, §13.3 |
| J9 departures 1, 4, 5, 7 | Acceptance placed with the lead's approval record; not given here | §15, §18 |
| J10 RET reference | V1 for every stage-2 arm | §6.4, §11.1 |
| J11 LoRA scaling, E-table | α = r, conventional initialization; E-table as the store | §7 |
| J12 filter tie-break | Larger τ, then the narrower range | §5.3 |
| J13 finite values | "arbitrary finite values" | §12.3 |
| J14 window grid | Consecutive non-overlapping windows; strata defined | §6.4 |
| Re-check §2: stale parenthetical, 7.6, unnamed outcome | Parenthetical deleted; 7.6–20.5 h; NOT STARTED: BUDGET | §0, §13.3 |
| Re-check §3 minor: S1 ranges | Listed | §9 |
| Re-check §4: fallback SHA-256 | Added from the reviewer's saved Hub tree | §4.2 |
| Re-check §4: stale sentences | Header; §14.1 opening; §14.2 wheels and sacrebleu; §5.3; closing lists | header, §5.3, §14.1, §14.2, closing lists |
| Re-check §1 C8: BOS (E-m3) | The reference tokenizer's default, recorded | §14.2, §19, §20 |
| Re-check §5: oracle line (E-5) | The line heads every class, annotation, router, composition and cost line; no positive wording without it | header, §9, §11.2–§11.5 |

**Not applied verbatim (listed, not resolved silently):**

1. **E-J1, named streams.** The re-check took them by a hash of (220901, stream name). Revision 5 gives each a listed seed, because the lead's instruction for this revision is that every seed actually used stays inside 220001–228999 and outside the calibration, rehearsal and test ranges.
2. **E-J3.** The re-check's text fetched the fallback's Tatoeba files in the same session as row 4. Revision 5 follows the lead's correction in §18: fallback teacher and fallback data only if the fallback rule is invoked.
3. **E-J3 and E-J4, edits to the §18 records.** Not made. The earlier records are kept as written; the lead's correction supersedes them and the statement at the end of §18 gives the scope.
4. **E-J8.** The re-check's text used the rates of the re-selected setting; revision 5 uses the slower of the two read layers' rates. The re-check's text also charged the independent recomputation inside R; by the lead's ruling it is not charged, following the P9-I / P9-II convention (§13.3).
5. **E-J9.** The re-check's sentence records the lead's acceptance. Revision 5 does not record it; it is left to the lead's approval record.
6. **Additions beyond the re-check's text**, each marked **[lead's choice]**: the details of the router recipe, the window grid, the LoRA and E-table forms, the filter tie-break, gate G9, the handling of a later fallback export, the rule for the P9 reference test, the rebuilding of partitions for a fallback language, and the projection of the second gates stage.
```

## Open for the lead

State after the lead's rulings on the first draft (applied by `rulings.py`, which `build.py` executes).

### A. Choices, each marked **[lead's choice]** in the text and listed in §20

Rule used: the P9 / P9-II convention where one exists; otherwise the option that is harder for a positive label or counts more time against the cap. Rows 11 and 20 are the lead's rulings.

| # | Point | Choice taken | Alternative not taken |
|---|---|---|---|
| 1 | J1 seed derivation | Every generator seeded directly by a listed seed; per-replicate offsets +0…+10 (the re-check's E-J1 table) | P9's `seed + 1000·k`, which lands in S2's calibration and rehearsal ranges with the present bases |
| 2 | J1 partition-side streams | Listed seeds 220902 (Q split), 220903 (source sample), 220904 (ablation subsample), 220905 (GEN windows) | The re-check's hash of (220901, stream name), which leaves the listed sets |
| 3 | J1 oracle-code seed | Per replicate (base + 10) | One fixed code seed for all replicates |
| 4 | J1 appended rows | Own seed +6, keys then values | Reusing the stage-1 seed, which duplicates the first-stage keys |
| 5 | J1 seeds shared between cells | +0 for ST1 of both orders and MA-gold; +8 for LoRA-1 and L-joint; +9 for E-table of both capabilities; +1 and +5 draw A then B | A separate seed per cell |
| 6 | J2 key initialization | Normal, standard deviation 0.02 (P9's `_matrix`) | Unit-scale keys |
| 7 | J5 marker placement | At least one marker-like string within tokens 1–64; windows with such strings only later are in neither stratum | Keep those windows and report their share |
| 8 | J6 router recipe | Re-check's E-J6. Added: prompts of every task the router must know; balanced classes; 8,000 "none" prefixes; hidden state at block L; cross-entropy over cosine scores at temperature 0.2; trained from seed +3 for every snapshot | Second stream only at stage 2; final-layer hidden state; continuing the stage-1 router |
| 9 | J7 disjoint draws | Re-check's E-J7; overlap between replicates reported | Draws disjoint across replicates (pool ≥ n × 8,000); one split fixed by the partition seed |
| 10 | J8a rates after re-selection at U = 1,000 | The slower of the rates at L = 4 and L = 12; the unrehearsed read layer measured on 200 updates, charged in P | The re-check's E-J8: the rates of the re-selected setting |
| 11 | J8b scope of R (lead's ruling 1) | Second gates stage inside R and the 36 hours. Independent recomputation not charged, by the P9-I / P9-II convention; within the per-process memory limits; no result reported before it completes | The recomputation inside R (the first draft, and the re-check's E-J8) |
| 12 | J10 RET reference | V1 for every stage-2 arm, M-ii included | The parent snapshot |
| 13 | J11 LoRA form | α = r; A uniform on ±1/√(fan-in), B zero; no dropout | α = 2r; A normal with standard deviation 0.02 |
| 14 | J11 E-table | N(0, 0.02) vectors with one linear scalar gate at 0, as the store | Zero vectors, no gate |
| 15 | J12 filter tie-break | Larger τ, then the narrower length-ratio range | First in grid order |
| 16 | J14 window grid | Consecutive non-overlapping 256-token windows; fewer than 100 in a stratum returns to the lead before the freeze | Overlapping windows; filling a short stratum from the other |
| 17 | Seed gate | New gate G9; §11.3 row 1 reads "G1, G4–G9" | An assertion outside the gate list |
| 18 | Link files not approved | The symmetry check is not made and the report says so | Not starting the data-generation step without the check |
| 19 | Fallback data from a later export | Link rows to English ids absent from the frozen English file are dropped and counted; both dates recorded | Fetching the 8.1 MB with row 4 |
| 20 | P9 reference test (lead's ruling 6) | Tensors passed explicitly to the P9 forward; `ScalableMemory` never constructed from a seed; the test is dropped, and the report says so, if that needs an edit of P9 | Constructing the P9 module with a seed |

### B. Still open

1. **The two symmetry-check link files (6.2 MB).** Not approved; the lead has asked the human lead again. Choice 18 holds until an answer names them.
2. **The second gates stage's projection is mine and unmeasured.** 0.11–0.40 h at every rung: four scorings of E_A and E_B at the table's 1.6–5.2 min (G2 and G4 each score twice), plus at most 0.05 h for the repeated 20-update runs, the general panel and the hash checks. The ADR had no figure for it. The text says the rehearsal's gates stage replaces it.
3. **The convention statement on P9-I and P9-II.** The text says their Opus recomputations were not charged to those studies' budgets, on the lead's ruling. I did not check ADR-0017 or ADR-0019 for a sentence that says so; the confirmation review should.
4. **"The first two clauses answer other questions."** In §18 I wrote this of "yes I do, yes we can raise to 16"; I know only that the second concerns S1's cap. Correct the wording if the first clause should be named.
5. **Title.** "Expandable learned memory" is kept; a header bullet says what "learned" covers.
6. **Outside this ADR.** `docs/reviews/p10-design-2026-11-15/EXECUTION_PLAN.md` line 21 says "registered run 7.7–35.5 h"; with the second gates stage R is 7.75–35.90 h. The re-check notes that ADR-0020's list of S1's seeds omits 2111–2122.
7. **Not in the re-check and not touched:** open questions 1–3, 5 and 6 of revision 4.

### C. Paste-ready edits of the re-check not applied as written

- **E-J1**: verbatim except the named-stream sentence (A.2).
- **E-J3 (§4.2 and §18 item 1)**: not adopted (A.19; lead's ruling 5); the §18 record is not rewritten.
- **E-J4 (§18)**: the record is not rewritten; the lead's correction supersedes it, and the end of §18 states the scope.
- **E-J8**: the rates sentence (A.10) and the charging of the recomputation (A.11) differ.
- **E-J9**: the acceptance sentence is not written; §15 and §18 leave it to the lead's approval record (lead's ruling 8).
- All other paste-ready edits (E-J2, E-J5, E-J6, E-J7, E-m1, E-m3, E-5, E-J10, E-J13, the fallback SHA-256) are applied with the auditor's words.

### D. Lead's rulings applied in this pass

1. Recomputation not charged; second gates stage inside R; rung table restored with the gates stage shown (§0, §13.2, §13.3).
2. The human lead's sentence on oracle-assisted results quoted verbatim (header, §11.3).
3. Context of the 36-hour sentence recorded (§15, §18).
4. Package wheels recorded as approved, with the verbatim answer and the question; link files stay not approved (§14.1, §14.2, §16, §18).
5. Spanish data: draft kept.
6. P9 reference test rule (§3).
7. Fallback partitions sentence (§4.2).
8. §15 departures 1, 4, 5, 7: left for the lead's approval record.
9. Header points to `docs/reviews/p10-design-2026-11-15/revisions/ADR-0022-rev4.md`.

### E. Checks made while drafting

- `build.py` asserts every anchor occurs exactly once and recomputes: the rung figures (14.35–35.51, 10.84–26.78, 10.09–27.17, 7.64–20.53), the gates-stage figure, the bound 14.5–16.25 h, the 930 / 1,253 MB totals, the wheel sums from the saved records, and that all 49 listed registered seeds lie in 220001–228999 and outside the calibration, rehearsal and test ranges.
- The fallback SHA-256 was read from `docs/reviews/p10-design-2026-11-15/adr-0022-review/web/opus_en-es_tree.json`.
- No independent review of this draft has been made.
