# P10-S2 lane C re-check, and the first audit of the combined tasks C1/C2 and the strengthened COMPOSES rule

**Claude (Opus 5.5) review; Astra review: NOT_PERFORMED; not a human approval.**

- Pinned source: `pin-p10s2-fc08681` (commit `fc0868115562c2e972ebe722a8ac448e0dbcdf4c`), read-only; `git status` clean after my work.
- I did not write any of the audited code. The scripts in this folder are mine. `spec_rules.py`, `check_*.py` without `_v2`, and `replay.py` are copies of my predecessor's scripts; they are auditor code, and I reused them where the task asked for it.
- Spec: ADR-0022 rev 5, including all addenda at its end, and `ADR-0022-addendum-combined-tasks.md`, which governs C1, C2 and COMPOSES.
- Environment for every number below:
  - Interpreter: `/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/agent-a91c79a181109bb9c/.venv/bin/python` (Python 3.12.14, torch 2.8.0, no numpy).
  - Platform: macOS-27.2.1-arm64, CPU only, `torch.set_num_threads(2)` where models run.
  - Working directory: the pinned tree. `TMPDIR` and `--basetemp` were inside this folder.
  - Constraints: test seeds 229101–229706 only; no network, no real model or data, no training.
- Commands: `cd <pin> && <python> -W ignore <this folder>/<script> <pin> [args]`. The arguments are listed per script at the end.

## Verdict on the implementation: READY AFTER LISTED FIXES

- Everything my own code could recompute agrees with the implementation:
  - the class and label rules updated for the rulings;
  - the composition rule;
  - the C1/C2 layouts and read positions;
  - cache continuation;
  - GEN's two decision positions;
  - the bootstrap;
  - the oracle-line guard on the predecessor's counterexamples.
- There are no blockers.
- There is one implementation major (N-M1: a registered output requirement is not met on a likely path).
- There is one design major in the addendum's text (N-M2, PENDING LEAD REVIEW).
- Ten minors are listed below.

## Verdict on the addendum's final text: READY, with two clarifications (PENDING LEAD REVIEW)

- The text can be implemented without making a further choice. I wrote C1, C2, the pairing, the reads, the definedness floors, the floor and the four-way rule from the text alone, and the results match the code (see below).
- Neither unreviewed passage introduces a contradiction:
  - C1's parity alternation is consistent with §2, §3 (both the n-even and n-odd counts), §6 and §11.
  - L-sep on C2's switch per answer with step 2 recomputed is consistent with §5.1 ("the one exception"), §7, §10 and §11 item 3.
- The switch per answer does not handicap the adapter baseline. Instead, it adds L-sep to an asymmetry the text does not state (N-M2).
- Clarification 1: N-M2 below.
- Clarification 2: "every line prints n". n is |E_C| (§2), and C1's H rests on about n/2 items. The code prints the replicate count instead (m2).

## Task 1 — C-M1 to C-M6 and the minors

| Finding | Status | Evidence |
|---|---|---|
| C-M1 missing control | **Fixed.** A missing section, panel or kind gives `Verdict(None, "control record missing")`. `controls()` lists a missing value or code permutation as NOT_EVALUATED, which blocks rows 6–8. | E5 → row 12 with both MAF classes NOT_EVALUATED; E6d (M-joint ablations absent) → 12; E6b (MA-gold value_perm absent) → 12 (`check_edges_v2.out.txt`) |
| C-M2 missing gate record | **Fixed as ruled.** Missing record, or missing G1–G9 (G2 and G3 included) → INCOMPLETE; failed G1, G2, G4–G9 → ENGINEERING-FAILURE; `ok: "true"` is not a pass. | E1, E1b, E2 (G1/G2/G3/G5/G9) → 2; E2f → 1; E2s → 1 |
| C-M3 recomputation | **Fixed.** Verdicts are compared as verdicts, and no number enters them. GEN under each decision, the GEN status, controls and composition classes are compared. | (a) 4e-7 APPEND COST difference → row 7, no change; (b) MSEQ GEN flip → 1; (b2) first-marker flip → 1; (d) composition change → 1 (`check_recompute_v2.out.txt`). Residual edge: m6 |
| C-M4 hidden undefined gap | **Fixed.** An undefined gap gives NOT_EVALUATED first, and the failing clauses are listed beside it. | `acq2(0.4, None, …)` → `ok=None, ('undefined gap', 'acquisition below 0.50')` |
| C-M5 read at punctuation | **Fixed** (`word_letters_end` + `last_token_before`, also used in `windows.cut_windows`). | Pre-split rerun: "here" read at `' here'`, "sat" at `' sat'` (`predecessor_reruns/check_read_position.rerun.out.txt`; the trailing sentence printed there is the predecessor's hard-coded text and is now stale) |
| C-M6 position router | **Implemented as ruled** (see task 2). | — |
| C-m1 missing GEN read as a failure | **Fixed.** Missing or non-finite with no measured failure → `not_evaluated`, and rows 6–8 do not apply (row 12). A measured failure under either decision → row 6, even if another value is missing. | `check_edges_v2.out.txt`, C-m1/GEN lines |
| C-m2 missing ensemble record | **Fixed** (INCOMPLETE). | E3 → 2; E3b differs → 1 |
| C-m3 partial ablation crash | **Fixed** (NOT_EVALUATED). | E6 → 11, no crash. An analogous crash remains for combined records (m4) |
| C-m4 oracle guard by words | **Fixed** for A1–A10 and R1–R5: every line is printed under the oracle line, and every record is refused without it. | `check_oracle_v2.out.txt`. Residual: A12 and R7 (m8) |
| C-m5 suffix on terminal class lines | **Fixed** | the terminal summary in `check_oracle_v2.out.txt` |
| C-m6 report omissions | **Fixed**: intervals (Table 5), single-reference scores, the M-ii GEN sentence, consolidation statistics, updates and rows, E_open scored | report on a synthetic record |
| C-m7 route accuracy on GEN windows | **Fixed**: 200 held-out WikiText train pieces | `routing.train_router` `held_out` |
| C-m8 EXACT-MATCH WEAK floor | Unchanged, stated in the report notes; PENDING LEAD REVIEW | — |
| C-m9 E-table learning rate | Stated in the report notes as a reading | — |
| C-m10 IEEE thresholds | Observation (E7 unchanged) | — |
| C-m11 dead code | Removed | — |

**Random synthetic records** (`check_rules_v2.py`, 20,000 trials, 3–4 replicates):
- My `rules_v2.py` is the predecessor's independent rules updated for the rulings: missing gate → INCOMPLETE; failed gate → ENGINEERING-FAILURE; a NOT_EVALUATED control anywhere blocks rows 6–8; GEN under both decisions at the ST1 and stage-2 snapshots; missing combined record → INCOMPLETE.
- The trials perturb panels, ablations (section, panel or kind absent), GEN pairs, statuses, rejected and inertia flags, the gates record and individual gates, ensembles, combined and assembled records.
- Rows seen: 1: 2,257; 2: 6,765; 5: 119; 6: 139; 7: 7,978; 8: 503; 11: 566; 12: 1,673.
- **0 disagreements in the label row or any class, 0 crashes.** A 300-trial first run also gave 0 (`check_rules_v2.attempt1.out.txt`).
- Rows 3, 4, 9 and 10 do not occur at random. I constructed one case for each, and each agrees.

**Warning annotations "in any replicate or order"** (`check_annotations.py`, 2,000 records):
- 0 mismatches for NO ADVANTAGE, RETRIEVAL SUFFICES, LEXICON-EQUIVALENT, BELOW JOINT BOUND and EXACT-MATCH WEAK.
- TEACHER-EQUIVALENT-TO-GOLD matches the reading "both capabilities in a replicate" exactly. It differs from "either capability" in 918 of 2,000 records (m7).

## Task 2 — GEN measured twice

- **Implemented as ruled, with no new threshold.**
  - `classes.gen_gate(a, m)`: a measured value > 0.02 under either decision → False; otherwise missing → None.
  - `gen_status` applies it to the ST1 and stage-2 snapshots in every replicate.
  - `general_quality` measures the marker stratum at index 63 and at `marker_end`, and the ordinary stratum at 63 in both.
  - In `check_gen.py` (2) I instrumented the call: the first decision read index 63 for all 200 windows; the second read `marker_end` for the 100 marker windows and 63 for the 100 ordinary ones. Both comparisons were exactly equal.
- **Marker-string rule.**
  - I implemented ADR §6.4's text myself: case-sensitive substrings "German", "French", "English", "translation" and ":\n" wholly within the text of tokens 1..decision; the ordinary stratum has none of them anywhere; the decision is at the token holding the last character of the earliest string.
  - I compared my version with `windows.cut_windows` on 3,000 random texts that include "Germany", "german", ":" without a newline, and strings straddling the boundary, using a GPT-2-style pre-splitting tokenizer with window 16 and decision token 8.
  - **0 mismatching texts** (8,308 marker windows, 11 ordinary).
- **The position-only router fails.**
  - Setup: the predecessor's position-only features; a two-task router trained with `routing.train_router` and `RouterSpec.registered()`; the real `evaluate.general_quality` with `hidden_at_ends` replaced by the position feature map; a store arm whose read raises the loss; `marker_end` uniform over 0–63.
  - At token 64 there were 0 triggers, an increase of 0.0000, and the registered decision passes.
  - At the first-marker decision there were 48 of 100 marker windows triggered, an increase of **+0.0536 nats**, and GEN **fails**.
  - My first two arms lowered the loss on the random stand-in model (+0.00003, then −0.0206). Those runs are kept as `check_gen.attempt1/2.out.txt`.
- **Can a router still pass both decisions by a cue other than content?** Partly yes. PENDING LEAD REVIEW; this is not an implementation defect.
  1. **Position.** The shortcut is closed only where `marker_end` falls at positions the router has learned to associate with tasks (task-prompt lengths 9–25). Elsewhere a position router is unprobed: 27 of my 100 positions were in 8–24, yet the trained router triggered on 48, so it extrapolated.
  2. **The colon cue.** Every task prompt ends at the bare ":" of the marker, while "none" prefixes end at arbitrary tokens. A router keyed on "the decision token is a bare ':'", or on "':' right after a language word", is the natural keyword detector. The first-marker decision never lands on that ":". It lands on the token holding the last letter of "German"/"French"/…, or on the "\n" of ":\n".
     - Measured: in 633 marker windows that contain "German:" or "French:" with a bare ":" inside the decision span, the first-marker decision was on that ":" **0** times.
     - Such a router is probed only when token 64 happens to be such a colon. (107 of 633 in my toy, because the decision span was only 8 tokens; it would be far rarer at 64.)
     - If the lead wants GEN to probe this cue, the reading would be "the last token of the first marker-like string, or of the ':' that immediately follows it". That is a lead decision.

## Task 3 — Combined tasks (first audit)

**My implementation from the addendum text:**
- `rules_v2.c1_pairs` and `tested_items`;
- `rules_v2.comp_h` and `comp_class`;
- in `check_continuation.py`, `my_c1` and `my_c2`: layouts in segment ids, read positions "stored position − |BOS| + |[BOS] E S(s1) NL M_T1 a1 NL|", recomputation in full with a plain greedy loop written on `student.forward`, and L-sep on both tasks;
- in `check_composition.py`, `build_record` and `mine_inputs`: tested means and single-task means computed from the items and my own pair list, not from the record's summary fields.

**Pairing and seed.**
- `draw_sigma` uses `partition_gen(mode, "c1_pairing")`. In the config this is 220911, the tenth partition stream.
- `registered-data` holds it; `registered-run` and `registered-analysis` refuse it.
- `pair_list` matches my `c1_pairs`: item j = (σ(j), σ(j+1 mod n)), A first for even j.
- σ and the pair hash are stored in the data manifest, and `build_world` refuses a mismatch.
- The duplicate count is reported. The text says "asserts" and "they stay as they are"; the code reports the count and does not stop, which is the consistent reading.

**Layouts and reads.**
- Read positions agree with the formula for every C1 item, with and without a first answer at the limit, and a1 and the NL after it are never read. 0 mismatches, both without and with a BOS segment.
- The marker is the last prompt token in every E_C prompt.
- C2 reads every source word under A and under B as two separate reads (separate top-8s), summed by `index_put(accumulate=True)`; M_A is read with A's code only and M_B with B's.

**Task 5 — continuation equals recomputation.**
- Arms: Stage 0, a two-stage store (M-append-frozen and M-ii form), a single 2N store (M-joint), M-i-separate, one LoRA (L-joint and L-seq), and L-sep. The arms are randomized so that they change answers, as listed in `check_continuation.out.txt`.
- Limits: the frozen stand-in limit (29) and the forced limits 1, 2 and 3. 10–12 of the 12 first answers reach the limit.
- Each comparison was among the implementation's cache path, its full path, and my own full recomputation.
- **0 token differences in all 24 arm-and-limit combinations, without and with BOS** (`check_continuation.out.txt`, `check_continuation.bos.out.txt`).
- L-sep on C2 equals my construction from §7. The double-feeding fix (`pre = [a1[-1]]` only when the limit was hit; the cache holds ids1 + a1[:-1]) is correct.

**Scoring.**
- C1 first answers are bit-identical to the single-task answers for every arm.
- `_kind_record`'s `tested_by_language` and `tested_sentences`, and `single_mean_on`, equal my recomputation from the items, to within 1e-12.
- n separate single answers.

**The rule.**
- `check_composition.py`: 10,000 random studies, 140,000 composition lines. They include rejected M-ii, missing records, NaN, teacher gaps below and above 0.30, single-task gaps around 0.50, and per-sentence single scores that differ so that the subset selection matters. All four outcomes occur: NOT_EVALUATED 111,596; INCONCLUSIVE 18,543; DOES NOT COMPOSE 8,483; COMPOSES 1,378.
- **0 disagreements, 0 crashes.** A sparse first attempt with 42,000 lines also gave 0, but only 13 COMPOSES lines; it is kept.

**Constructed strategies** (`check_strategies.py`):
- Toy world: 200 sentences of 3–10 words from the stand-in lexicon; German and French words share their trailing digits, so copying between languages scores above 0; Stage 0 echoes the source; chrF is the predecessor's auditor implementation.
- My rule and the implementation agree on every row.

| Strategy | C1 | C2 |
|---|---|---|
| do-nothing (= Stage 0) | NOT_EVALUATED (G = 0) | NOT_EVALUATED |
| first-answer-only (empty second answer) | DOES NOT COMPOSE (H −0.135) | DOES NOT COMPOSE |
| copy-the-first-answer | DOES NOT COMPOSE (H 0.05) | DOES NOT COMPOSE (H_B 0.16) |
| wrong language, right sentence | DOES NOT COMPOSE | DOES NOT COMPOSE |
| echo the source | DOES NOT COMPOSE (H 0.0) | DOES NOT COMPOSE |
| weak single-task arm (G ≈ 0.28) | NOT_EVALUATED | NOT_EVALUATED |
| context-blind capable arm | COMPOSES (H 1.0) | COMPOSES |
| ensemble record (BY CONSTRUCTION) | H = 1.0, never above 1 | H = 1.0 |
| **contaminated: first answer, then the right second answer, on one line** | **COMPOSES (H 0.83 / 0.80)** | **COMPOSES (H_B 0.84)** |
| right answer twice plus the source | INCONCLUSIVE (0.74) | INCONCLUSIVE |

- (In my table the row "right language, wrong sentence" reads COMPOSES on C2 only because C2 has one sentence, so my construction gave the correct French answer there. The label is my misnomer.)
- **Search for a cheap passing strategy.** I tried 500 random mixtures in which each second answer is genuine with probability p and otherwise one of six cheap behaviours.
  - The smallest p that printed COMPOSES was **0.754 on C1 and 0.658 on C2**. The low C2 figure comes from the contamination behaviour.
  - I found **no strategy that passes without producing the correct second answer on most items.**
  - Two passes are cheap in a narrower sense:
    - (a) chrF's recall weighting (β = 2) lets a contaminated second answer pass (m10);
    - (b) on C2 every adapter arm gets H_German = 1 for free (N-M2).
  - Under oracle routes, COMPOSES means only "context-insensitive single-task competence". The second fixed line says so.

**Arms and standing.**
- Combined scoring runs for MAF, MII, M-joint, L-joint and L-seq, and for the assembled M-i-separate and L-sep.
- It does not run for M-seq, E-table, ST1, LoRA-1 or MA-gold, or for the append point (`cells.py` 288–313, 361).
- The combined tasks use the oracle route only: no router lane and no ablation.
- Composition enters no gate, class or label: `study_label` never reads it, and 20,000 random studies agree. It acts only through §11.3 rows 1–2:
  - a missing record → INCOMPLETE (E: "L-joint r2 without combined" → 2);
  - a recomputation change → ENGINEERING-FAILURE (case d).
- Revision 5's ratio C̄/(0.80·S̄) is printed and labelled as replaced.

**L-sep fairness.**
- On C1, the position-wise adapters mirror the store arms: first-segment state is kept, and no second-adapter re-processing of a1 happens. This is fair.
- On C2, the switch per answer favours the baseline rather than handicapping it (N-M2).

## Task 4 — Bootstrap (`check_bootstrap.py`)

- 220906 is drawn only through `bootstrap_generator`. It is held by `registered-analysis` alone and refused by `registered-data` (SeedRefused) and by `registered-run`. It is drawn only when `analyze(bootstrap_mode=…)` is given, which happens only in the printed outcome of `stage_analysis` and `outcome_under_recomputation`. The verdict analyses never draw it.
- One fresh generator per interval: 174 seed uses for 174 intervals with items. Two intervals over the same items under different names are identical, and equal to my own percentile bootstrap.
- The order is fixed (Stage 0 and teacher panels, then Stage 0 and ensemble C1/C2, then registry cells, then assembled arms, then retrieval).
- Re-running gives identical intervals.
- The verdicts are identical with and without intervals (descriptive). No seed is drawn without `bootstrap_mode`.

## Task 6 — Report and the oracle qualification

- `ORACLE_LINE` equals ADR §11.3's fixed line, and `COMBINED_LINE` equals the addendum §9 second line.
- The lead's sentence is quoted exactly 4 times in the ADR and 2 times in the addendum. It is in `core.LEAD_RULE` and the `output` docstring.
- **It is not printed in the report** (m1).
- I found no line in the report that claims autonomous learned memory. The only matches for "autonomous" or "success" are the oracle line itself ("not autonomous learned memory"), the NOT_ESTABLISHED item "Autonomous learned memory: addresses and routes are supplied by rule.", and "A success probability: …" (as a non-claim).

## Findings

### Majors

**N-M1. The composition table loses the second fixed line whenever no line carries a composition word.** Files: `report.py:200`, `output.py:54`, `output.py:check_text`.
- `block()` adds `COMBINED_LINE` only if some line contains COMPOSES, DOES NOT COMPOSE or COMPOSITION INCONCLUSIVE.
- With every line NOT_EVALUATED, the composition table (Table 4: H values, floors, revision 5's ratio) is printed under the oracle line only. Its caption still says "both fixed lines above apply" (`check_oracle_v2.out.txt`, last two lines: COMPOSES → both lines; all NOT_EVALUATED → second line False).
- This is a likely real path: the teacher gap or the single-task gap on E_C fails.
- Addendum §9 ("on every composition line and every composition table") and §11 item 8 require the line, and `check_text` cannot detect its absence.
- **Fix:** at `report.py:200`, head the composition block with both lines unconditionally (for example `"\n".join([ORACLE_LINE, COMBINED_LINE, *composition_lines(...)])`, or a `block(lines, composition=True)` parameter). In `check_text`, require `COMBINED_LINE` as the second line of any block containing "Table 4. Composition", or any `compos\w*` marker, or an "H " per-answer line.

**N-M2 (addendum design; PENDING LEAD REVIEW). On C2, every adapter arm's German answer is its single-task answer by construction, so its H_German(C2) is identically 1.** Files: addendum §5.2 and §7.
- L-joint and L-seq apply one adapter at every position, and route "both" applies it once. L-sep's step 1 is A's adapter on P_A(s).
- In all three, C2's first answer is generated from exactly the single-task input. Measured: 6 of 6 identical for each adapter arm, although all 12 of their single-task answers differ from Stage 0's.
- Stage 0's C2 German score equals its single-task score too, so H_German = (sS − s0S)/(sS − s0S) = 1.
- Store arms are tested on German under summed reads: only 5/6, 4/6 and 3/6 of their C2 German answers equal the single-task ones.
- So "COMPOSES C2" for an adapter rests on the French answer alone, and for a store arm on both. The text does not state this.
- The switch per answer adds L-sep to this group. It is not a handicap to the baseline (AGENTS.md is satisfied); it is an unstated asymmetry in a printed comparison.
- **Fix (no threshold change):** print the adapter arms' C2 German H as "BY CONSTRUCTION (the first answer of C2 is the single-task answer for an adapter)" and state that their C2 line rests on the French answer. Alternatively, the lead may rule otherwise.

### Minors

- **m1.** The report does not print the human lead's sentence (`report.py:180–219`). **Fix:** add `core.LEAD_RULE` verbatim as the first item of the "What S2 cannot establish" block, or of the standing line, and extend `test_p10s2_report` to assert it.
- **m2.** Composition lines print "n replicates = …" but not n = |E_C|, the items per answer (about n/2 in C1), or "(n replicates, U = …)" per line (`report.py:116`; addendum §8 "Every line prints n", §9). **Fix:** add `n items {rec n}; items per answer {len(tested_sentences[a])}` and `design` to each arm line.
- **m3.** A CONSOLIDATION-REJECTED M-ii cell still has its unpublished snapshot's H values printed in the detail (`analysis.py:450`, `report.py:119`), although §7 says "no M-ii combined score exists". If its record lacks the combined section, the study becomes INCOMPLETE (`analysis.py:666`) instead of printing a NOT_EVALUATED line (`check_edges_v2.out.txt`). **Fix:** for rejected cells, write `{"replicate": r, "NOT_EVALUATED": "CONSOLIDATION-REJECTED"}` in the detail and exempt them from the missing-record check.
- **m4.** Partial or malformed combined records crash `analyze` (KeyError or IndexError: an empty C1, missing `tested_sentences`, missing `single.scores`, a short score list; `check_malformed_combined.out.txt`). The analysis also does not check §8's integrity conditions per record (n items equal to |E_C|, the pair hash). **Fix:** validate in `_comb_rec` (`analysis.py:387–394`): `tested_by_language` and `tested_sentences` for A and B, `single.scores` of length n, `rec["n"]` and `pairs_sha256` equal to Stage 0's. Otherwise treat the record as missing (INCOMPLETE).
- **m5.** An entirely empty `assembled` record is exempt from INCOMPLETE (`analysis.py:666`), while a partial one is not. NO ADVANTAGE then prints NOT_EVALUATED. **Fix:** drop the exemption.
- **m6.** A within-tolerance own-code difference that crosses a threshold changes a verdict and gives ENGINEERING-FAILURE: GEN 0.02 against 0.02 + 5e-7 → row 1 (`recompute.py:215–216`). The ruling says "A difference within tolerance never changes a verdict by itself". The effect errs towards failure. **Fix:** compute the recomputed verdicts on `reported_study(registered, recomputed, res)`.
- **m7.** TEACHER-EQUIVALENT-TO-GOLD requires both capabilities within a replicate (`analysis.py:302`). The ADR text has no capability qualifier, and the "warning fires more" reading is "either capability". PENDING LEAD REVIEW (a reading).
- **m8.** `emit_plain` prints "C1 M-ii r0: H_a 0.91 / 0.88 on the second answer" bare, and `check_record` accepts `{"h_by_answer": …}` (A12, R7). Neither is reachable through the report. **Fix:** add `\bH_?a?\b`-style and "single-task G" markers, and `h`, `h_by_answer` key stems.
- **m9** (design; PENDING LEAD REVIEW). GEN's second decision never sits on the ":" after a language word (task 2, item 2).
- **m10** (design; PENDING LEAD REVIEW). COMPOSES tolerates a second answer that repeats the first answer before the right one (H 0.80–0.84 in my toy), because chrF weights recall. The exact-match pass rate, which is printed, is the only sign. A per-cell count of second answers that contain the first answer would make it visible; no threshold changes.

### Tests

- Lane C subset: `pytest -q -p no:cacheprovider --basetemp <mine> tests/test_p10s2_{combined,classes,report,fixC_output,fixC_rules,fixC_scoring,text,model}.py` → **223 passed** (`pytest_laneC.out.txt`).
- All P10-S2 tests: `pytest -q -rf --basetemp <mine> tests/ -k p10s2` → **494 passed, 7 failed, 1 skipped** (`pytest_all_p10s2.out.txt`). All 7 failures come from the environment, not from lane C:
  - Six integration tests check the guard "refuses the real repository / ledger unless the run root is a temporary directory". They fail because the pinned tree itself lives under `/private/tmp`, which the guard treats as a temporary root.
  - `test_the_driver_asserts_the_code_location` fails because the borrowed interpreter imports `arborlm` from another worktree (`agent-a91c79a181109bb9c/src`), not from the pin. The driver's location check correctly refuses this.
  - These guards belong to lane B and should be re-run from a non-temporary checkout with its own environment.

## Discrepancies that were my own mistakes, kept

- **Predecessor's `check_edges.py` re-run.** Its baseline record now gives row 2, because it has no G2/G3 or combined records, and it crashed at E8 because `annotations` now returns a tuple. Neither is a code defect. `check_edges_v2.py` replaces it (`predecessor_reruns/check_edges.rerun.out.txt`).
- **`check_composition` attempt 1.** Too sparse: 13 COMPOSES lines (`check_composition.attempt1_sparse.*`).
- **`check_gen` attempts 1 and 2.** My stand-in arms lowered the loss, so they could not show a failure (`check_gen.attempt1.out.txt`, `check_gen.attempt2.out.txt`).
- **`check_strategies`.** The label "right language, wrong sentence" is wrong for C2 (see task 3).

## Files

| Script | Output | Purpose |
|---|---|---|
| `rules_v2.py`, `synth.py` | — | my rules (classes, labels, COMPOSES, pairing) and synthetic record builder |
| `check_rules_v2.py` (args `20000 check_rules_v2.json`) | `check_rules_v2.out.txt/.json`, `.attempt1.*` | random label/class comparison |
| `check_edges_v2.py`, `check_edges_v2_lib.py` | `check_edges_v2.out.txt` | C-M1/2/4, C-m1/2/3, rows 3/4/9/10, combined edge cases |
| `check_composition.py` (args `10000 check_composition.json`) | `check_composition.out.txt/.json`, `.attempt1_sparse.*` | COMPOSES rule comparison |
| `check_strategies.py` | `check_strategies.out.txt` | constructed strategies and random search |
| `check_continuation.py` (env `BOS=1` for the second run) | `check_continuation.out.txt`, `check_continuation.bos.out.txt` | cache against full recomputation, read positions, first answers, adapter C2 |
| `check_gen.py` | `check_gen.out.txt` (+ attempts 1 and 2), `check_gen.debug.out.txt` | marker rule, decision positions, position router, colon cue |
| `check_bootstrap.py` | `check_bootstrap.out.txt` | 220906 discipline and re-run identity |
| `check_oracle_v2.py` | `check_oracle_v2.out.txt` | A1–A12, R1–R7, report, lead sentence, composition header |
| `check_recompute_v2.py` | `check_recompute_v2.out.txt` | C-M3 cases, threshold edge, composition change |
| `check_annotations.py` (arg `2000`) | `check_annotations.out.txt` | six warning annotations |
| `check_malformed_combined.py` | `check_malformed_combined.out.txt` | m4 |
| predecessor copies | `predecessor_reruns/*` | re-runs |

Temporary directories (pytest basetemp, `tmp/`) were deleted after use; nothing here exceeds 100 MB.
