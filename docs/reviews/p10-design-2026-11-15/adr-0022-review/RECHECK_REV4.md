# Re-check of ADR-0022 revision 4 (post-E8), P10-S2

**Claude (Opus 5.5) review; Astra review: NOT_PERFORMED; not a human approval.**

- Reviewer model: Claude Opus 5.5 (`claude-opus-5-5`). I wrote no part of ADR-0022.
- Object: `docs/decisions/ADR-0022-p10-s2-two-teacher-transfer.md` (701 lines), worktree `.claude/worktrees/p10-design`, branch `claude/p10-design`, HEAD `25cdd46`, which is later than `4e8dc43`.
- Compared against: `docs/reviews/p10-design-2026-11-15/adr-0022-review/CONFIRM.md`, `revisions/ADR-0022-rev4-before-E8.md`, `revisions/ADR-0022-p10-s2-two-teacher-transfer.rev3.md`, ADR-0020 §9.3 / `adr-0020-review/CONFIRM.md` E8, ADR-0021 §6.3, and `studies/p9/model.py` (read-only).
- Commands I ran:
  - `diff` of rev4-before-E8 against the current text;
  - `diff` of §13 in rev3 against rev4;
  - `grep` for S0/S1/ST1/C1/C2 and seed use;
  - `python3 -I recheck_arith.py` (Python 3.15.1, stdlib only, no project import; output in `recheck_arith.out.txt` beside this file);
  - a read of the reviewer's saved Hub JSON under `adr-0022-review/web/` to check revisions, sizes and hashes.
- I used no network, downloaded nothing, trained nothing and made no commit.

## Verdict: READY SUBJECT TO the text edits listed in section 8

C1–C10 and m1–m7 are applied faithfully. The E8 renames are clean. The arithmetic holds, with one rounding difference and one stale parenthetical. Two problems remain.

1. **The seed and initialization plan is incomplete.** If the implementer follows the project's existing convention, generator seeds land inside S2's own calibration and rehearsal ranges. Nothing in the text keeps the appended rows' initialization distinct from stage 1's.
2. **The download scope is inconsistent.** It is recorded differently in §4.2, §14.1 and §18. §18 also contains one claim that is false by arithmetic.

There is no blocker for implementation on synthetic stand-ins. Each major is a text edit.

## 1. C1–C10, m1–m7 and E8

| Item | Where / quote | Faithful? | Note |
|---|---|---|---|
| C1 | §12.3 G5: "(c) **Gate isolation of appended rows:** after the append and before any update, the read r with the appended rows' values replaced by arbitrary values equals r with them at zero, bit for bit … That change is the **append cost** (§6.3), measured and not gated." §3 also: "Appended rows do take top-8 weight from first-stage rows from the moment of the append." | Yes, verbatim | Nit: "arbitrary" should be "arbitrary finite", because 0·inf is NaN. **New issue:** "same distribution as first-stage keys" refers to a distribution that is never stated (finding J2). |
| C2 | §11.1 ACQ1: "G_first ≥ 0.50; **G − max(G_value-perm, G_code-perm) ≥ 0.30**; G_marker-only ≤ 0.25. Control G values use the teacher and Stage 0 scores of the same 300-item subsample". §11.3 reason line present. | Yes, verbatim | ACQ2 says "the same lexical margin and marker-only limit". CONTROL-FAILED (G_perm ≥ 0.50) is kept. That limit is far from the 0.1–0.2 legitimate range, so it does not reintroduce the C2 fragility. |
| C3 | §1 H22-E is verbatim. §11.4 has "TASK-CODED SPARSE RETENTION / NONE \| M-seq's loss of G_first is smaller than L-seq's by ≥ 0.10 …". M-seq-shared is gone from §6.3 and §13.1. | Yes | Remaining mentions are history only (lines 41, 234, 424, 580, 611, 648). |
| C4 | §6.4 has "100 windows that contain any of the strings …", "(selected by rule with the partition seed)", false-trigger counts per stratum, "the keyword router stayed silent", and "GEN is measured for every ST1 and stage-2 memory snapshot". §11.1 has 0.02 nats. | Yes | Departure: E-table and MA-gold snapshots are not scored, stated in §19 "Not applied verbatim" 2. Acceptable. **New ambiguity (J5):** the router reads token 64, but a marker string can occur after token 64, where the router cannot see it. |
| C5 | §5.3: "as the most permissive setting … whose **95% Wilson lower bound** of precision on Q_fit … is ≥ **0.90**. The chosen setting must then show a point precision ≥ **0.90** on Q_check with at least 150 accepted items" | Yes | Recomputed: Wilson at 0.90 is 0.842–0.939 for n = 150 and 0.871–0.923 for n = 500 ✓. To pass on Q_fit, a setting needs an observed precision of about 0.93–0.95. That is the intended effect. Nit: no tie-break among settings with equal accepted share. |
| C6 | §5.2: "Groups larger than 50 sentence pairs … go to the training side by rule. Of the remaining groups, the partition seed assigns groups to the evaluation side until it holds 20% of the remaining pairs (counted in pairs, not groups)" | Yes, verbatim | — |
| C7 | §12.1: "Calibration cells save a snapshot at 1,000 updates. If the rehearsal rule selects U = 1,000, the selection rule and the pilot gate are applied to those snapshots." §9 meaning of "every replicate" is verbatim. §11.3 has "(n replicates, U = …)" and NO-ACQUISITION "within U updates". | Yes | 0.5⁴ = 0.0625, 0.5³ = 0.125, 0.8⁴ = 0.4096 ✓. Constant learning rate makes the 1,000-update snapshot equal to a 1,000-update run ✓. **New interaction (J8):** a re-selection at U = 1,000 can change L, and so the training rates that chose the rung. |
| C8 | §14.2 step 4: conventions, "BOS is not prepended in any input *(lead's choice …)*", stop on 0x0A, whole-sequence decoding, tests (a)–(e). G8 is extended. | Yes; BOS is filled in by the lead | Listed in §19 "Not applied verbatim" 1 and open question 4. Suggested rule in section 8, edit E-m3. |
| C9 | §7: "**L-joint** — ordinary multi-teacher distillation (adapter form) \| one LoRA of rank 84 on the mixed material of both teachers, 2U". §6.3 learned-routing reading is verbatim. §13.1 adds L-joint 1 cell / 2 units. | Yes | 57,600 per rank; rank 84 = 4,838,400, which is −0.232% against M-joint ✓. The new annotation BELOW ADAPTER JOINT is declared as the draft's own (§19). |
| C10 | §10.1: "averaged over the **effective** orders … as sacrebleu 2.5.1's default (`eps_smoothing=False`); an item with no effective order scores 0" | Yes | Agrees with `web/sacrebleu_chrf_v2.5.1.py.txt` lines 160–196. |
| m1 | §17: "Retention in the shared store is retention against crosstalk that the shared top-8 itself creates; …" | Yes | — |
| m2 | §6.3: "In M-ii the first-stage gate g_1 is trainable, like the rows it scales; its change is reported." | Yes | — |
| m3 | §7: "the ACQ2 controls permute the values of the second stage's rows among themselves and the word codes of the second task" | Yes; the choice is the draft's own (§19) | — |
| m4 | §14.1: "The `eng/` link files are used, and their symmetry is checked … if those two files are fetched for the check they add 6.2 MB and are part of row 4's approval." | Yes | **Conflict with §18 "Nothing else may be downloaded"** (J3). |
| m5 | §14.1 line 447: "All Tatoeba files, the fallback's included, are fetched in one session" | Yes | **Conflicts with §4.2 and §18** (J3). |
| m6 | §5.4: "If S0 qualifies an interface, evaluating it in S2 needs a supplement approved by the human lead." §16 also lists it. | Yes | — |
| m7 | §6.3: "rows never selected by any read cannot move, so the floor may be hard to reach, and the share of first-stage rows that changed at all is reported" | Yes | — |

**E8 renames.** The diff of rev4-before-E8 against the current text shows the following changes only:

- the header line;
- §5.4 supplement wording;
- "S1" → "ST1" at §6.2, §6.3, §6.4 (two places), §7 (two rows), §11.1 ACQ1, §11.3 rows 4 and 18, §16 and §19 (C4 row and "Not applied" 2);
- the seed sentence;
- §18.

These changes do not affect any number. Remaining bare "S1" (lines 5, 10, 246) all mean the study. "s_c(Stage 0)" is at §10.1. **ST1 does not collide.** `grep -rnE '\bST1\b'` over `docs studies src configs` finds it only in ADR-0022. "V1" / "V_1" remain distinct (version, and value matrix of stage 1). Pre-existing, harmless overload: C1/C2 name both the combined tasks (§6.4, §11.4) and confirmation findings (§19). The E8 request named "St1/St2". There is no stage-2 store symbol, so nothing is missing.

## 2. Task 2: registry, rung rule, hours

**Registry.** All counts are recomputed ✓.

| Group | Cells | Store units | LoRA units |
|---|---|---|---|
| ST1 | 2 | 2 | – |
| M-append-frozen | 2 | 2 | – |
| M-ii | 2 | 4 | – |
| M-seq | 2 | 2 | – |
| M-joint | 1 | 2 | – |
| E-table | 2 | 2 | – |
| MA-gold | 2 | 2 | – |
| LoRA-1 + L-seq | 4 | – | 4 |
| L-joint | 1 | – | 2 |
| **Total** | **18** | **16** | **6** |

- 18 cells give **72 at 4 replicates** and 54 at 3.
- Memory cells for ablations: 11.

**Hours.** My recomputation from the per-unit ranges of §13.3:

| Rung | Design | Registered run R (h) | Text says |
|---|---|---|---|
| 1 | 4 × 2,000 | 14.35–35.51 | 14.4–35.5 ✓ |
| 2 | 3 × 2,000 | 10.84–26.78 | 10.8–26.8 ✓ |
| 3 | 4 × 1,000 | 10.09–27.17 | 10.1–27.2 ✓ |
| 4 | 3 × 1,000 | **7.64**–20.53 | **7.7**–20.5 (rounding only; computed 7.6) |

- In rungs 3 and 4 only training is halved; scoring is not.
- **Cap with twofold headroom.** P + 2R ≤ 36 gives R ≤ 16.25 h at P = 3.5 and R ≤ 14.50 h at P = 7.0. That matches "about 15 hours".
- On the projection, rung 1 fits only at the fast end. Every rung exceeds the cap at the slow end: rung 4 at P = 3.5 gives 18.8–44.6.
- **The parenthetical "(removing M-seq-shared and adding L-joint changes each by about +0.1 to +0.3 h per replicate)" is stale.**
  - The table's figures already include the change.
  - The actual change from rev3 to rev4 is +0.073 to +0.080 h per replicate (−2 store units, +2 LoRA units, −1 scored cell).
  - Read literally, the parenthetical invites adding it a second time. Delete it (E-m1).

**Is every branch determined before observation?** Mostly yes. The rule uses only P, which is charged hours, and R(n, U), which comes from measured rates. Neither is a study outcome. Three gaps remain:

1. **J8a, circularity through L.** Calibration picks L ∈ {4, 12} at U = 2,000. The rehearsal measures rates with that L. If the rule reaches rung 3 or 4, C7 re-applies selection on the 1,000-update snapshots, and that can change L. With L = 4 the backward pass crosses 26 blocks; with L = 12 it crosses 18. The rates behind the rung choice may therefore not belong to the selected design. The text must fix which rates R(n, 1,000) uses. Suggested: the larger of the two L's measured rates, or re-apply the rule with the newly selected L's rates. If the result then fails, move to the next rung.
2. **J8b, scope of P and R.** It is not stated whether these count toward the 36 charged hours:
   - the second gates stage on registered seeds;
   - the post-freeze independent CPU recomputation of every score (§16 step 10);
   - the timing benchmark.

   §13.2 says "all S2 processes". The recomputation could cost the same order of hours as the scoring rows (5.5–18 h at rung 1). State whether it is inside R, or outside the cap.
3. **"Not started" is reachable.** It happens when P + 2R(3, 1,000) > 36, which on the projection happens at the slow end. What happens is stated: "the run is not started and the lead returns to the human lead." There is no printed outcome name, unlike §12.2's "NOT STARTED: STUDENT CANNOT USE THE MEMORY ON THIS TASK". Add "NOT STARTED: BUDGET", recorded with the rehearsal record (E-m2). A re-design after that is a new human decision under §16 "Also reserved … budget".

## 3. Seeds

As written (§9), the declared seeds are:

| Seeds | Use |
|---|---|
| 220001–220006, 220101–106, 220201–206, 220301–306 | replicate bases with offsets 0–5 |
| 220901 | partition |
| 221001–221999 | calibration |
| 222001–222999 | rehearsal |
| 229001–229999 | tests |

- The declared singletons and ranges are pairwise disjoint (script check).
- They are disjoint from S0, S1, P9, P9-I and P9-II as listed in ADR-0020 §9 and ADR-0021 §6.3.
- They match the siblings' statement "S2 (220001–228999, tests 229001–229999)".
- No sibling initialization seed plus 1000·k (k ≤ 9) lands in S2.

**The text does not define how generator seeds derive.** "base + 0 initialization" is one seed. The study needs several independent generators. **J1 (major):**

- Under the project convention, every one of S2's declared seeds collides with its own ranges. The convention is P9 `ScalableMemory`: keys at seed + 1000, values + 2000, wq + 3000, wo + 4000, router + 5000 (`studies/p9/model.py` lines 236, 272). §3 says the mechanism is "kept from the project's mechanism" and imports the P9 forward as a reference. Under that convention:
  - seed + 1000 lands in **calibration** (221001…);
  - seed + 2000 lands in **rehearsal** (222001…).

  This holds for all four bases, for every offset 0–5 and for the partition seed 220901 (→ 221901, 222901). Calibration seed + 1000 lands in rehearsal. The previous reviewer's concern is confirmed.
- Under the P7-B/P8/P9-sim convention (seed·1000 + index), the seeds leave every namespace, so there is no collision. The "ranges are disjoint" assertion then checks nothing about the seeds actually used.
- Unspecified generators that matter scientifically:
  - **appended-row init.** If stage 2 reuses the stage-1 seed with the same shapes, the appended keys duplicate the first-stage keys exactly. Top-8 would then pick 4 distinct keys twice, and about half the weight would move to new rows at the append. That is a design artefact, not interference;
  - M-joint's 2N rows against ST1's N;
  - LoRA A;
  - E-table;
  - gates;
  - the oracle-code hash seed of u(t, w). Whether codes are common to all replicates or redrawn per replicate changes what replication covers (address overlap). P9 used a fixed `DATA_SEEDS['r1_codes']`, which is a P9 seed;
  - the 60,000-source sample;
  - the Q_fit/Q_check split, the 300-item ablation subsample and the GEN window selection. All three use "the partition seed", with no stream separation.

  The fix (E-J1) is a named offset table. Whether codes are per replicate is **PENDING LEAD REVIEW**.
- **Minor.** §9 names "S1" without its ranges and "P1–P9-II" without listing them. List them as ADR-0021 §6.3 does:
  - S1: 210001–219999, initialization seeds 2101–2105, seed block 2111, 2112, 2121, 2122, 2191–2192, tests 921001–921999.

  Note that ADR-0020's list of S1 omits 2111–2122. This is outside my object; I mention it for the coordinator.

## 4. §18 against §16, and the downloads

| §16 item | §18 | Match? |
|---|---|---|
| 1 downloads | Human: "i approve s2 download"; lead's record covers the student, Tatoeba and the fallback "only if the fallback rule … calls for them" | Answered. The scope is inconsistent with §14.1 (J3). |
| 2 wheels | "the lead reads the approval as covering the package wheels … because the question named them **and the total included them**" | **The total did not include them.** The human was asked about "938 MB". I recompute 938.2 MB = teachers 604.5 + student 272.4 + Tatoeba 53.13 + Spanish data 8.14, with no wheels (J4). The description named the wheels, so the reading has some basis. But this is the lead interpreting, which contradicts "No reserved item is decided by the lead". |
| 3 complementary | "s2.1 yes" → accepted | Yes |
| 4 verification | "s2.2 yes" → filter accepted | Yes. The question said "at least 0.90"; §5.3 now applies it as a Wilson lower bound on fit plus a point estimate on check. That is stricter, so consistent. |
| 5 MPS + packages | "s2.3 yes" → MPS with CPU recomputation; packages read as covered only for the data-generation wheels | Yes for MPS. Packages: the same caveat as item 2, stated honestly. |

**Does anything still need a human answer before implementation on synthetic stand-ins?** No. All human-reserved items have answers or recorded readings, and stand-in implementation needs no download or wheel. J3 and J4 must be settled before step (5), the downloads. §15 items 1, 4, 5 and 7 are headed "need explicit acceptance" but are neither reserved in §16 nor accepted in §18 (minor J9). Under the "p10 can be self approve" delegation, the lead's approval can state that it accepts them. The §15 item 3 claim, that the human said 36 h is acceptable, rests on a quote that names no figure ("im confortable with does number …"). **PENDING LEAD REVIEW**; I cannot verify its context.

**Download consistency (J3, major).**

- §4.2: "The fallback's files are fetched only if it is invoked **and approved**."
- §14.1 row 6 and line 447: the fallback **data** are fetched in the same session as row 4, always, and opened only if invoked.
- §18: approved "only if the fallback rule of this ADR calls for them, the fallback teacher **and data**", and "Nothing else may be downloaded".

These three statements disagree. In addition, §14.1 line 446 brings in `deu/deu-eng_links` and `fra/fra-eng_links` (6.23 MB) as "part of row 4's approval". No figure shown to the human includes them: 938.2 → 944.4 MB, or 1,259.7 MB with the fallback teacher. That is still under the 1.5 GB cap. An implementer cannot tell what to fetch in the first session.

**Pinned revisions, sizes, licences.** I checked these against the reviewer's saved Hub JSON (`adr-0022-review/web/*_rev.json`, `*_tree.json`), offline. Everything matches:

- revisions:
  - student `93efa2f0…e75a2`;
  - Teacher A `6183067f…b0ca4`;
  - Teacher B `dd7f6540…67f18`;
  - fallback `5bc4493d…ed4ab`;
- weights size and SHA-256 for the student and both teachers;
- file-set totals 272.4 / 300.8 / 303.7 / 315.3 MB;
- licences apache-2.0, cc-by-4.0, apache-2.0, apache-2.0;
- Tatoeba file sizes sum to 53.13 MB; Spanish data 8.14 MB.

Abbreviations in §14.1 agree with §2 and §4. Two minor findings:

- §14.1 row 5 says "pinned now", but the text never states the fallback's SHA-256. The saved tree gives `befce0f620e8e63f83bbb7f0818eb51d541cba28057a7cc14b00466d85c4994c`. Add it to §4.2.
- Stale sentences remain, in each case after an answer was recorded:
  - §14.1 intro "has no answer yet";
  - §14.2 last bullet "left to the human lead … none is fetched before the answer";
  - header line 7;
  - §14.2 table "sacrebleu … not checked by the reviewer". CONFIRM §6 checked existence and licence.

## 5. Oracle routing: bars on autonomous claims

The bars:

- §5.4: "**What cannot be claimed.** That the model decides where to look or knows its task; anything about learned sparse addressing. Every result is **oracle-assisted**."
- §11.3: "Every label is printed with the fixed line: **'oracle-assisted (word-level addresses supplied by rule); … not autonomous learned memory.'**"
- §17: "**Autonomous learned memory.** Addresses and routes are supplied by rule."
- §6.3: "The human lead's phrase may intend more; this reading is stated, not assumed."

Positive-sounding strings the text lets an implementer print **without** the fixed line:

1. Mechanism class lines: "M-append-frozen: ACQUIRES-AND-RETAINS (n, U)". §9 and §11.3 require "(n, U)" on class lines; the oracle line is required only on **labels**.
2. "ROUTER (keyword-level) QUALIFIED".
3. "COMPOSES C1 / C2".
4. The cost lines "TRAINING COST COMPARABLE" and "FEWER VALUE ROWS ACTIVE". These are not autonomy claims, but they are positive-sounding.
5. The title phrase "expandable learned memory" and H22-G's heading "general quality under a learned route".

Annotations are "printed with the label", so in the outcome line they carry the oracle line. Class lines and stand-alone tables do not. Edit E-5 closes this.

## 6. Implementability findings

**Blockers:** none.

**Major:**

- **J1.** Generator seed derivation is undefined. The P9 convention collides with S2's calibration and rehearsal ranges. Appended-row init may duplicate stage-1 keys. The code-hash seed and its per-replicate status are unspecified (section 3).
- **J2.** The initial distribution of the keys is never stated. Only the values are given (N(0, 0.02)), and the appended keys are "the same distribution as first-stage keys". Under cosine scoring with Adam, the key scale sets the effective angular learning rate of the keys. At lr 0.003, keys of norm 0.08 (sd 0.02, width 16) rotate a lot per step; keys of norm 4 (sd 1) barely move. That is a scientific choice the implementer would have to make.
- **J3.** Download scope contradiction (§4.2, §14.1 row 6 and line 446–447, §18).
- **J4.** False premise in the §18 reading of item 2. It does not block stand-ins; correct it before downloads.
- **J5.** GEN hard negatives. The marker string may occur after token 64, which the router (decision at token 64) cannot see. Such windows are not hard negatives for the router, so GEN can pass trivially on part of that stratum. State that the string occurs within tokens 1–64, or report the share that do.
- **J6.** The router-training recipe is unspecified, yet the router decides a label gate (GEN). Missing:
  - optimizer, learning rate and updates;
  - the number of "none" prefixes and their length;
  - which stored prompts (training streams only? not D_cal?);
  - whether "none" prefixes are cut at 64 tokens, to match the GEN decision point.
- **J7.** No rule for drawing T_A^r and T_B^r disjoint in English when the two no-gold pools overlap. Someone must decide who gets the shared sources. The sufficiency rule checks each pool ≥ 8,000 separately, which does not guarantee two disjoint 8,000-item draws. A pool of exactly 8,000 makes all replicates draw the same items. Gold^r 8,000 pairs per capability is not in the sufficiency rule.
- **J8.** Rung rule:
  - (a) rates at the wrong L after re-selection at U = 1,000;
  - (b) whether the second gates stage and the step-10 recomputation are inside P/R or the 36 h.

**Minor:**

- **J9.** §15 departures 1, 4, 5 and 7 are not recorded as accepted.
- **J10.** RET reference for M-ii. "after Stage 1" (V1) against §6.4's "before is the parent snapshot's score" (M-append-frozen). State that RET and the retention negative zone compare with V1 for every stage-2 arm.
- **J11.** LoRA scaling (α) and E-table initialization and gate are unspecified.
- **J12.** There is no tie-break among filter settings with equal accepted share.
- **J13.** G5(c) should say "arbitrary finite values".
- **J14.** The GEN window grid (overlapping or not, how windows are cut from the validation stream) is unstated.
- Section 2 items: the stale parenthetical, 7.6 against 7.7, and the unnamed "not started" outcome.
- Section 4 items: the fallback SHA-256 and the stale sentences.
- The S1 ranges should be listed in §9.

## 7. Model

I ran as Claude Opus 5.5 (`claude-opus-5-5`).

## 8. Paste-ready edits

**E-J1 (§9, replace the seed sentence's parenthesis and add a sentence):**

> Seeds: replicate bases 220001, 220101, 220201, 220301, each with these offsets:
>
> - +0 stage-1 store (keys, then values, from one generator in that order);
> - +1 training draw;
> - +2 batch order;
> - +3 router;
> - +4 permutation controls;
> - +5 gold draw;
> - +6 stage-2 appended rows;
> - +7 M-joint store;
> - +8 LoRA initialization;
> - +9 E-table initialization;
> - +10 oracle-code hash *(lead's choice: per replicate; PENDING LEAD REVIEW against one fixed code seed for all replicates)*.
>
> Within a replicate, the M-seq and M-ii arms start from the snapshots they continue. Partition seed 220901, with named streams (partition, Q split, 60,000-source sample, ablation subsample, GEN window selection) taken by a hash of (220901, stream name). Calibration draws use 221001 + 100·i and rehearsal draws 222001 + 100·i with the same offsets. Every generator is seeded directly by a listed seed: **no "+1000·k" derivation is used**. The implementation asserts that every seed actually passed to a generator lies in the listed sets and is disjoint from:
>
> - P1–P9-II (as listed in ADR-0021 §6.3);
> - S0 (200001–209999, 2001–2002, 2091–2092, 920001–920999);
> - S1 (210001–219999, 2101–2105, 2111, 2112, 2121, 2122, 2191–2192, 921001–921999).

**E-J2 (§3, after the value-initialization sentence):**

> Keys are initialized from a normal distribution with standard deviation 0.02 *(lead's choice; as P9's `_matrix`)*. Appended keys and values are drawn from the same distributions with the stage-2 seed (§9), never with the stage-1 seed.

**E-J3 (§4.2, last sentence, replace):**

> The fallback teacher's files are fetched only if the rule above invokes it. The fallback's Tatoeba files are fetched in the same session as row 4 of §14.1 and opened only if the fallback is invoked.

**E-J3, §18 item 1 (replace from "and, only if"):**

> … the Tatoeba data (53.1 MB) together with the fallback's Tatoeba files (8.1 MB), fetched in the same session and opened only if the fallback is invoked; the fallback teacher (315.3 MB) only if the fallback rule calls for it. The two symmetry-check link files of §14.1 (6.2 MB) were not in the figure shown to the human lead *(PENDING LEAD REVIEW: either fetch them under this approval and say so, or drop the symmetry check against them and check symmetry within the `eng/` files only)*.

**E-J4 (§18 item 2, replace "because the question named them and the total included them"):**

> because the message describing the downloads named them; the 938 MB total did not include them (it is the teachers, the student and the Tatoeba files). This is the lead's reading, not an answer from the human lead.

**E-J4, §18 last bullet:**

> All five reserved items have a recorded answer; items 2 and 5 (packages) rest on the lead's reading of that answer.

**E-J5 (§6.4, after "a line ending in ':'"):**

> , with at least one such string within tokens 1–64 of the window (the part the router sees)

**E-J6 (§5.4, router lane, append):**

> Router training: AdamW, learning rate 0.001, 500 updates of batch 64 *(lead's choice)*, on the stored prompts of the current stage's training streams only (never D_cal, D_con or an evaluation panel) and on WikiText-2 *train* prefixes of exactly 64 tokens in equal number; the projection is initialized from seed +3. The decision position in training matches GEN's (the 64th token of a "none" prefix; the last prompt token of a task prompt).

**E-J7 (§5.2, sufficiency rule, append; PENDING LEAD REVIEW for the split rule):**

> English sources in both accepted pools are split, by the training-draw seed of each replicate, into two halves assigned to A and B before drawing. Sufficiency requires, for each capability, its exclusive accepted sources plus its half ≥ 8,000 × 1.25 *(lead's choice)*, and 8,000 gold pairs per capability outside Q, D_cal and D_con; otherwise DATA-INSUFFICIENT.

**E-J8 (§13.3, after the rung list):**

> R(n, 1,000) uses the training rates of the setting re-selected at U = 1,000 (§12.1). If that setting was not the one rehearsed, its rates are measured on 200 rehearsal updates before the rule is applied. The second gates stage is inside R. The independent recomputation of §16 step 10 is charged and is inside R. The outcome "none" is recorded as **NOT STARTED: BUDGET** with the rehearsal record.

**E-m1 (§13.3):** delete "(removing M-seq-shared and adding L-joint changes each by about +0.1 to +0.3 h per replicate)" and write "7.6–20.5 h at rung 4".

**E-m3 (§14.2 step 4, BOS):**

> BOS follows the reference tokenizer's default for this model, read from the pinned `tokenizer.json`/`tokenizer_config.json` and recorded in the data-generation step; the draft expects "not prepended".

**E-5 (§11.3, after the fixed line):**

> The same line heads every mechanism-class line, every annotation and every table of the outcome report that prints a class or label, and every cost line.

**E-J10 (§11.1 RET):**

> "after Stage 1" and "before" mean V1 (the ST1 snapshot) for every stage-2 arm, including M-ii.

**E-J13 (§12.3 G5(c)):** "arbitrary finite values".

**E-J9 (§18, the lead's approval line, when written):**

> The lead accepts §15 departures 1, 4, 5 and 7 under the P10 delegation.

**§4.2:** add "SHA-256 `befce0f620e8e63f83bbb7f0818eb51d541cba28057a7cc14b00466d85c4994c`" (from the reviewer's saved Hub tree; to be checked at download).

Astra review: NOT_PERFORMED. This re-check is not Astra validation and not a human approval.
