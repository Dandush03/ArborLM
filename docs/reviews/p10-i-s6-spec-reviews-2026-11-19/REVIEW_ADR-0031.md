# Review of ADR-0031 (P10-I-S6, first draft): does the flat memory's lead persist at convergence?

- Reviewer: `arbor-auditor` subagent, model Claude Opus 5.5 (`claude-opus-5-5`), 2026-11-19. Independent of the drafter (Fable 5.2). I wrote none of the text or code under review.
- Object: `docs/decisions/ADR-0031-p10-i-s6-flat-lead-persistence.md`, SHA-256 `fe83a1bc12afe6600ce2d8e1827da834bac3712965603f35df27542a2beadd32` (401 lines, untracked, on branch `claude/p10-ii-s5-design` = main `fd87c71` plus drafts).
- This is engineering and mathematical review evidence only. It is not Astra validation and not a human approval. `Astra review: NOT_PERFORMED`.
- No training, generation, network, git write, sealed value or registered checkpoint was opened. I read only public records: `results/p10i-s3-run-2026-11-18/*`, `studies/p10i_s3/freeze/plan.json`, and the public R1/R2 cost records under `experiments/P10IS3-R1-20261118/` and `experiments/P10IS3-rehearsal-20261118/r2.json` (seconds only, no losses).

## Verdict

**READY AFTER THE LISTED EDITS.** There is no BLOCKING finding. There are 12 REQUIRED findings. Each one is a text edit, spelled out exactly in section C. The edits change the label machinery: the convergence definition, the failed-cell and reading-rung rules, rung 4 hard-coded against a ladder that can be cut, and what the calibration file makes public. For that reason I advise that a reviewer read the applied text once before Decision 1 is recorded. P10-I-S3's approval record shows that this read was skipped once before. I agree with the drafter that the human lead should take Decision 1 himself (section F).

## A. Recomputed and checked figures (my own code; nothing imported from `arborlm` or `studies`)

| Draft figure | Check | Result |
|---|---|---|
| Mean Q +0.0127, 27/27, smallest parent +0.0044 | `experiments/_scratch/audits/adr0031/s3_trend.py` on the public `analysis.json` | 0.012659; parent means 0.0044 to 0.0244; **SD across parents 0.0069** |
| Deltas D +0.0172, F +0.0208 | same | 0.017225, 0.020784. Per-doubling envelope gain, FRESH: D-ADAPT 0.0158 (512→2,048), 0.0208 (2,048→8,192), 0.0172; M-FLAT 0.0203, 0.0219, 0.0208. **No deceleration.** |
| 21,904 s against 16,980 s, ratio 1.29 | Sum of `max_update × unit cost / 6` over the 621 items of the frozen `plan.json` | 16,980 s; ratio 1.290. P10-I-S3's R1 rounds charged 1.37, 1.16 and 1.07 times their projections. |
| Unit costs, full read sets | `plan.json` projection | Match. R2 used a 50-update probe. |
| 19,064 updates; 2,097,152 chunks ≈ 136 MB; WikiText-103 sizes; ledger total 1,188,183,868 | config, card, ledger | Match. 315,466,397 bytes is the whole configuration (three splits), so the train-only download is a little smaller. |
| Parameters and bytes: 198,145 / 198,401; 792,580 / 793,604; 0.13% | `pilot_model`, `p4_model.DenseAdapter` | Match |
| Multiply-adds per position: M-FLAT 132,864 (or 67,328) | `studies/p10i_s3/model.py:87-117`, `pilot_model.py:130-145` | **Wrong.** The keys are normalised once per forward call (4,096 × 16 per batch of 512 positions), not once per position. The right figure is 67,328 + about 128, against 198,400 for the dense arm, a ratio of about 2.94 (F7). |
| R1 4.9 h; registered 6.3 / 12.3 h; smallest design 0.9 / 1.6 / 2.8 h; M-TREE 9.4 h | arithmetic at 6 workers | Match (4.92; 6.32; 12.25; 0.88; 1.58; 2.77; 9.43) |
| R1 extensions "0 to 2.8 h" | The rule allows 4 steps down and 2 up per arm | The worst case is 6 rates per arm: **0 to 4.2 h** (F12) |
| D-2X "3.5 h calibration" | 7 rates × 3 cells × 2 × 2,900 s / 6 workers | **5.6 h** (F12) |

**Training items, counted by me (recommended design):**
- R1: 42 runs to 262,144 updates, up to 78 with extensions.
- Registered: 54 runs with one rate per arm, up to 324 with a different rate at every rung −1..4.
- OA: 54 runs to 16,384.
- Gates: 4 runs (prefix and resume identity).
- Parents: 12, plus 9 old-parent reproductions if F16 is adopted.
- Total: about 166 to 480 training items.
- Projected: 12.0 to 22.5 h at 6 workers. Charged: about 16 to 31 h at a ratio of 1.29 to 1.37.

The draft's "12–23 / 16–30" therefore stands, with the two corrections above. Evaluations are under 0.2 h. Each item is at most about 1 h (one 262,144-update D-ADAPT run is 2,900 s × 1.3).

**Seeds.** I made a copy of the registry checker (`seed_registry_check_r3.py`, SHA-256 `e4623604…` = registry revision 3), extended with every value the draft proposes, and ran it.
- Copy: `experiments/_scratch/adr0031_seedcheck/seed_registry_check_r3_plus_adr0031.py`, SHA-256 `2aba15e2…`.
- Attempt 1: **FAILED through my own error.** `ROOT` resolved through the `experiments` symlink to the main checkout. Kept as `attempt1_FAILED_root_resolved_through_symlink.txt`.
- Attempt 2: `attempt2_output.txt`, `RESULT: FAIL`. All 40 binding failures are P10-I-S3's own config literals against its own allocation. This is the known false positive (ADR-0026 section 4; ADR-0029 section 19, ruling 6). **No binding problem involves ADR-0031.**
- The literal scan finds ADR-0031's values nowhere else except one registry-boundary literal (330701) in P10-I-S3's checker copy.
- ADR-0030's draft uses 310001–319999 and 939001–939999, with no overlap.
- Informational check W1 (adding +1000k to every value): the 320001–329999 data block reaches the initialisation row 330001–339999. This is not binding, because data seeds are not expanded. The registry's sentence that "the row sits 20,000 above the highest P10-I data block" is no longer true (F27).

Commands and environment:
- `timeout 120 uv run --locked python experiments/_scratch/adr0031_seedcheck/seed_registry_check_r3_plus_adr0031.py` (2.7 s).
- `timeout 30 python3 -I experiments/_scratch/audits/adr0031/s3_trend.py results/p10i-s3-run-2026-11-18/analysis.json`.
- Cost ratios: inline `python3 -c` over `experiments/P10IS3-R1-20261118/plans/r1-round*.json` and the frozen `plan.json`. The command text is in this session's log.
- macOS 27.2.1 arm64, uv 0.12.15, Python 3.12.14 (locked), torch 2.8.0.

## B. Findings

### Things that favour the memory, or could

**F1 — REQUIRED — §9.1. A dense arm can be declared converged while it is still improving.**
- The rule as drafted: δ(arm, k) uses the run at r(arm, k−1) for L(k−1) and a different run, at r(arm, k), for L(k). "A rising envelope counts as converged."
- How it goes wrong: if the rate chosen for rung k on three calibration cells transfers badly to the registered cells, the envelope can rise or flatten while that arm is still improving along its own run.
- When it is the dense arm, this reaches row 8 (MEMORY AHEAD, DENSE CONVERGED) or creates a K\*. That is exactly the direction P10-I-S3 points to (the dense arm behind and improving).
- Q† only partly protects. It compares the memory at rung k with the dense arm at j†, which gives the memory more updates than the dense arm when j† < k.
- The along-run δ is printed but decides nothing.
- Change (edit C1): converged = envelope δ < ε **and** along-run δ < ε. This is symmetric and makes convergence harder for both arms.

**F2 — REQUIRED — §8 sealing. The calibration's convergence pattern would be public.**
- `rehearsal_public.json` would hold δ and the convergence state per arm and rung on the calibration cells. That is a preview of the registered label structure: K\*, rows 8–12.
- §8 says the study runs whatever these states are. No pre-run decision needs them.
- Their only effect is to let Decision 2 be taken knowing the likely label.
- Change (edit C4): seal them.

**F3 — REQUIRED — §19. The licensing table claims a cause the measurements do not identify.**
- Row "DENSE CAUGHT UP / … / row-9 label" says "The 16,384-update lead was a property of unfinished training in this setting."
- That holds only if R16 reproduced the lead on the new parents and corpus. Otherwise the cause (duration, parents or corpus) is not identified.
- Change (edit C11).

**F4 — REQUIRED (disclosure) — §18. The likely outcome of the recommended design is not stated.**
- The S3 curves show a constant gain per doubling of about 0.017–0.022 from 2,048 to 16,384 updates.
- Reaching ε by 262,144 needs that gain to fall about twentyfold within four doublings. Nothing in the record shows it bending.
- So CONVERGENCE NOT REACHED (BOTH STILL IMPROVING) is the most likely registered outcome of a 16–31-hour study. The draft says this only of the smallest design.
- This is not a bias, but the human lead must weigh it at open choice 2.
- Change (edit C10). `PENDING LEAD REVIEW`: whether an "ordering identified without convergence" rule is wanted. Any such rule would be chosen knowing P10-I-S3, so it is the human lead's call, not mine.

**F5 — ADVISORY — §12.3 note (d).** "LEAD GROWING" is likely to print beside CONVERGENCE NOT REACHED (S3's lead grew from −0.002 at 512 to +0.0127). It will read as encouraging. Print it in one sentence with each arm's δ at k_max against |mean Q(k_max)|, as S3's OUTCOME did ("both arms are still improving by more per doubling than the lead").

**F6 — ADVISORY — label name.** "DENSE CAUGHT UP AT CONVERGENCE" asserts a history: the dense arm was behind and then caught up. The class only measures LEVEL. Rename it "LEVEL AT CONVERGENCE".

**F7 — REQUIRED — §5. The compute description is wrong in a way that frames the memory well.**
- The 132,864 figure is wrong (section A).
- The sentence "the memory reads 8 of 4,096 value rows" omits that every position scores all 65,536 key parameters.
- Change (edit C6).

**F8 — ADVISORY — §11, "content-qualified".**
- D[FLAT] = DEPENDENT can be reached through harm. F2 passes when wrong values hurt, as it did for the tree.
- V_mean is not "content against W_q, W_o and gate". With all value rows equal, the read is one constant vector at every position, and W_q has no effect. It is a second context-free read.
- What actually shows that the lead is not a constant bias is F3: X_mean ≥ 0.5·C ≈ 0.07 is much larger than the lead.
- Change: fix the V_mean text (edit C7) and call it "dependence-qualified".

**Checked and found not to favour the memory:**
- The one-sided Q† clause.
- "Settled" plus the same class at every later rung (symmetric).
- The grid: identical for both arms and centred on the value both arms chose.
- Thresholds: none moved.
- K2 dropped: it only ever entered COMPETITIVE, never MEMORY AHEAD.
- The exclusion by whole article: conservative.
- No larger dense arm: matched within 1,024 bytes. A wider dense arm is larger in both bytes and compute.
- MEMORY UNSTABLE: a memory failure counts against the memory.
- Re-anchors R16 and OA: they change no label.

**F9 — ADVISORY.** The 0.0005 rate tie tolerance now enters δ directly, because the envelope switches rates. It is half of ε. Edit C1 removes most of the effect. `PENDING LEAD REVIEW`: whether to keep 0.0005.

**F10 — ADVISORY.** Near-duplicates at other offsets (shared Wikipedia templates) are not caught by the aligned 65-byte exclusion. A key–value memory may exploit them more than the dense arm. P10-I-S3 had the same exposure. Print, without any rule, the share of panel chunks whose 32-byte shingles occur in the registered pool.

### Rule completeness and computability

**F11 — REQUIRED — §12.2/§9.2. With a failed cell, the reading rung R is undefined.**
- NOT EVALUABLE item 4 (Cd(R)) and D[FLAT] need R. R needs K\*. K\* needs both arms' L, which are undefined when an arm has a failed cell.
- ADR-0026's rule "NOT DETERMINED counts as NOT CONVERGED" was not carried over.
- Change (edit C2).

**F12 — REQUIRED — §17 limits / §18 cost.** Correct the extension and D-2X figures and state the R1 ratio (edit C14).

**F13 — REQUIRED — "rung 4" is hard-coded.**
- §6.5 can cut the ladder before calibration. But conv(arm), rows 8–12, note (c), the trend Q(4) − Q(0) and the limits all name rung 4.
- Change (edit C3): define k_max.

**F14 — REQUIRED — §15. Frozen inputs and imports.**
- `results/` is read at run time. `studies/p10i_s3/parents.py` reads `results/p3-lt-2026-11-12/*/manifest.json` and `order.json`, and `results/p4-2026-11-12/*-baseline/result.json`. The adapter identity gate reads the latter. The draft says nothing under `results/` is a run-time input.
- `core.envelope` is not a convergence envelope. It is P10-I-S3's record header and stamps `study: "P10IS3"` (`core.py:256`).
- These read P10-I-S3's config, seed layout or arm list implicitly:
  - `model.evaluate_reads` takes S3's `core.Seeds`, adds X and joint reads, and has no V_mean.
  - `calibration.require_outside_repo` defaults to S3's `seal.forbidden_roots`.
  - `calibration.rate_table` iterates S3's `ARM_REGIMES`.
  - `core.Thresholds.from_config()` and `core.Seeds()` with no argument load S3's config.
  - `data.corpus_from_parquet(…, cfg)`.
  - `planted.planted_positive` / `neg_ref_check` take S3's `Seeds` and `Thresholds`.
- Change (edit C5).

**F15 — REQUIRED — §11 and §16. The registered panel and the DRY profile.**
- V_mean weights are said to come "from the registered-panel enabled read". On calibration and DRY checkpoints that would evaluate a trained addition on the registered panel before the run, which ADR-0026 ruling 15 forbids. That ruling is not carried over.
- Change (edits C7, C8).

**F16 — ADVISORY — §7.** The identity gate on one old parent exercises one backbone seed and one order seed. Reproducing all nine costs seconds; make it all nine.
- The adapter must also bypass `p2_data.order_ids`' whitelist, not only `p2_config.Cell`.
- The control memory (`Memory("learned_tree", 201)`) is built after the backbone and is frozen. Omit it, or declare 201 a re-use.
- The new parents are trained on the same 2,048 WikiText-2 chunks, so "fresh" means new seeds only. Say so.

**F17 — REQUIRED — §6.4.** The order of operations of the pool is open: global de-duplication then assignment to pools; file order; strip semantics. Rulings G7–G10 (edit C9).

**F18 — REQUIRED (edit C9) — §6.5. The calibration pool can cut the ladder.**
- My estimate: about 7.5–7.7 M eligible chunks after exclusion (WikiText-2's eligible share of 0.933 applied to 539.3 MB of text, minus about 2% for WikiText-2's articles). That is about 2.5 M in the mod-3 calibration pool (19% margin) and about 5.0 M in the registered pool.
- If the calibration pool is short, the rule cuts U_max for both pools although the registered pool would suffice.
- Fix a fallback now, from counts only (edit C9).
- D0 must record: candidate chunks, articles and chunks removed, duplicates, both pool sizes, and the eligible validation spans left for the panels.

**F19 — REQUIRED (edit C8) — sharing the machine.** "Its stages pause … while another study's quiet-machine stage runs" has no mechanism. Items last up to about 1 h, so a pause only takes effect between items. Ruling G20.

**F20 — ADVISORY.** D0's 8 GiB guard is tight for a literal `select` over about 7.7 M chunks: Python objects come to about 5–6 GB. Use compact binary digests and arrays, with the equality gate against `select` on WikiText-2.
- Also state that RSS counts the file-backed pages of the 0.5 GB memory-mapped table in each worker. That is about 0.5 GB per worker; within the guards but worth knowing.

**F21 — ADVISORY.** OA uses rates calibrated on the new parents (S3 used rates calibrated on old ones). Say so beside OA. Also state OA's failed-cell and integrity handling (G18).

**F22 — ADVISORY.** State that no check in this study compares two different computations up to a tolerance except NEG-REF; ADR-0026's joint-permutation check, which failed on float32 ties, is not used. All other identities compare the same computation bitwise, and the top-8 tie-break by slot index is deterministic. A tie rule exists for rates (the smaller rate) and for j† (the larger rung). The mean order is fixed by G6.

**F23 — ADVISORY.** Rows 8 and 9 should carry "(ONE DOUBLING OF EVIDENCE)" when the converged arm is converged only at k_max (edit C12).

**F24 — REQUIRED (edit C13).** §21 does not say who takes Decision 2 or where it is recorded, or what happens if the post-run recomputation disagrees (G25, G26).

**F25 — ADVISORY.** Download.
- The draft cites the 50 GB delegation; the ledger header still cites 30 GB (2026-11-15). Either covers 0.32 GB; cite the record.
- Name the parquet files from the repository listing at the pinned revision and write them into the ledger rows before the fetch. Expected size and SHA-256 come from the LFS metadata, as for WikiText-2.
- Read the parquet with `pyarrow` in `-I` mode, in its own directory.

**F26 — ADVISORY.** The D[FLAT] harm counts use strict ">" (cells with H_used > B). Say so.

**F27 — ADVISORY.** Seed registry: add ADR-0031's rows (the checker copy above shows how) and correct the "20,000 above" sentence. Add a test that no ADR-0031 data seed is ever expanded by +1000k.

## C. Edits (old text → new text; line numbers refer to SHA-256 `fe83a1bc…`)

**C1 (F1, F9; §4 and §9.1).**
- §4, after the δ row (l. 68), add the row:
  > `| δrun(arm, k) | The 27-cell mean NLL of the run at r(arm, k) at update U_{k−1} minus the same at U_k (U_{−2} := 4,096 is not used; δrun is defined for k = 0..k_max). |`
- l. 141, replace "An arm is **converged at rung k** if δ(arm, k) < ε, with ε = 0.001 nats/byte (a rising envelope counts as converged)." with:
  > "An arm is **converged at rung k** if δ(arm, k) < ε **and** δrun(arm, k) < ε, with ε = 0.001 nats/byte (a rise counts as below ε for the quantity that rises; both conditions are required). Reason: a rate chosen per rung on three calibration cells can transfer badly, so that the envelope rises or flattens while the arm still improves along its run; without the second condition such a dense arm would be declared converged while behind."
- l. 141, replace "Per-parent δ and the along-run δ (the same run's previous snapshot) are printed and decide nothing." with "Per-parent δ and δrun are printed; per-parent δ decides nothing."
- l. 385, replace "**ε on the envelope per doubling** as the convergence measure (recommended), against the along-run δ of ADR-0026." with "**ε on both the envelope and the along-run improvement per doubling** (recommended), against either alone."

**C2 (F11; §12.2, after "Nothing is rerun at another rate.", l. 222).** Add:
> "If an arm has a failed cell on a run a rule reads, its L at the rungs that run serves, its δ, δrun and convergence state are NOT DETERMINED, which counts as not converged; if K\* cannot be computed for that reason, R = k_max. A run stops at the non-finite error; its later snapshots are recorded as not produced (failed cell), which is not a missing record of section 12.1. A non-finite event after U_k fails the run for every rung it serves."

**C3 (F13; §4, new row after U_k).** Add:
> `| k_max | The index of U_max after the ceiling rule of section 6.5 (4 unless that rule cuts the ladder). Wherever this ADR writes "rung 4", "conv(arm)", "Q(4)", "K\* = 4" or "the last rung", read k_max. |`

**C4 (F2; §8, l. 133).** Replace "`rehearsal_public.json` holds the rate table, the interior flags, δ and the convergence state per arm and rung on the calibration cells, gate results, seconds and storage, and the sealed archive's SHA-256;" with:
> "`rehearsal_public.json` holds the rate table, the interior flags, gate results, seconds and storage, and the sealed archive's SHA-256; δ, δrun and the convergence states of the calibration cells are in the sealed archive only, because no decision before the registered run uses them and their preview would let Decision 2 be taken knowing the likely label;"

**C5 (F14; §15).**
- l. 292, replace "This ADR and everything under `docs/` and `results/` are not run-time inputs" with:
  > "The compact records the parent loaders and the adapter identity gate read at run time (`results/p3-lt-2026-11-12/b*-control/manifest.json` and `order.json`, `results/p4-2026-11-12/b*-baseline/result.json`) are frozen inputs by SHA-256. This ADR, everything under `docs/`, and every other file under `results/` are not run-time inputs".
- l. 294, replace "`core.py` (`EngineeringStop`, `FailedCell`, `jsonable`, `envelope`)" with "`core.py` (`EngineeringStop`, `FailedCell`, `jsonable`)", and add after "on a fixture.":
  > "Not imported as they stand, because they read P10-I-S3's config, seed layout or arm list: `core.envelope` (it stamps `study: P10IS3`), `core.Seeds` and `core.Thresholds.from_config` without an explicit argument, `model.evaluate_reads`, `calibration.rate_table`, `calibration.require_outside_repo` without `forbidden_roots`, `data.corpus_from_parquet`, `planted.planted_positive` and `planted.neg_ref_check`."

**C6 (F7; §5).**
- l. 78, replace the M-FLAT multiply-add cell with:
  > "W_q 512; key scores 4,096 × 16 = 65,536; values 8 × 32 = 256; W_o 1,024: **67,328**, plus the normalisation of the 4,096 × 16 keys once per forward call (about 128 per position at 512 positions) and a top-8 selection over 4,096 scores"
- l. 82, replace "In multiply-adds per position the dense arm uses 1.5 to 2.9 times the flat memory's, and at every position all of its parameters are active while the memory reads 8 of 4,096 value rows." with:
  > "In multiply-adds per position the dense arm uses about 2.9 times the flat memory's (198,400 against about 67,456). At every position the dense arm uses all its parameters; the memory uses all 65,536 key parameters, W_q, W_o and 8 of 4,096 value rows."

**C7 (F8, F15; §11, V_mean row, l. 180).**
- Replace "(NEG-REF's construction, ADR-0026 ruling 9, with the weights from the registered-panel enabled read). The stored content is removed without placing any wrong value. V_mean = H_vmean − H." with:
  > "(NEG-REF's construction, ADR-0026 ruling 9, with the weights from the enabled read of the same checkpoint on the panel being evaluated: the registered panel in registered mode only, the calibration panel otherwise). With every value row equal the read is one vector at every position whatever the query, so V_mean is a second context-free read built from the stored values. V_mean = H_vmean − H."
- Replace "It answers how much of the gain is content and how much is the added W_q, W_o and gate." with "It shows whether a constant built from the stored values keeps the gain; it does not separate content from W_o and the gate."
- l. 247, replace "**content-qualified**" with "**dependence-qualified**".

**C8 (F15, F19; §16, after l. 325).** Add:
> "ADR-0026 section 16 rulings 1–3 and 5–18 apply with M-TREE, REP and REP-U removed; ruling 4 is replaced by section 6.4. Ruling 15 binds: no trained addition is evaluated on the registered panel outside registered mode. Pause for another study's quiet stage: the lead creates the run directory's pause file; workers start no new item while it exists; an item in progress finishes (or, if the resume-identity gate passed, stops at its next rung snapshot and resumes from it); the other study's quiet stage starts only when this study's process family is empty."

**C9 (F17, F18; §6.4 and §6.5).**
- l. 106, after "The implementation may stream," add:
  > "The order is fixed: (1) the train files are read in lexicographic order of file name, rows numbered consecutively across files; (2) articles are segmented on `str.strip()` of each row; (3) articles with a chunk digest (hex SHA-256 of the 65-byte payload, at `select`'s offsets, before any de-duplication) in E are removed; (4) `select`'s cutting, de-duplication and ranking are applied once to all remaining rows; (5) each kept chunk goes to the pool of the article holding its kept occurrence."
- l. 116, after "No calibration or registered value can move U_max.", add:
  > "If the calibration pool is short and defining it instead as the articles with number mod 2 = 1 gives both pools at least 2,097,152 chunks, that definition is used; this is decided by code from counts alone, before any calibration run, and printed."

**C10 (F4; §18, after l. 358).** Add:
> "**Expectation, not a measurement [KNOWN]:** in P10-I-S3's FRESH regime the envelope's gain per doubling did not fall between 2,048 and 16,384 updates (D-ADAPT 0.0208 then 0.0172, M-FLAT 0.0219 then 0.0208 per doubling). To meet ε at the last rung an arm's gain must fall about twentyfold within four doublings. If the curves keep their shape, the recommended design most likely ends in CONVERGENCE NOT REACHED (BOTH STILL IMPROVING), which claims nothing about the ordering. The human lead weighs this at open choice 2."

**C11 (F3, F6; §19 l. 367; §12.3 row 5; §1 table).**
- Rename DENSE CAUGHT UP AT CONVERGENCE to LEVEL AT CONVERGENCE everywhere.
- Replace "The 16,384-update lead was a property of unfinished training in this setting." with:
  > "If R16 is REPLICATED AT 16,384: the 16,384-update lead did not hold once both arms had converged in this setting. Otherwise the lead was not reproduced on new parents and data even at 16,384, and the label does not say whether duration or the change of parents and corpus removed it."

**C12 (F23; l. 243 note (c)).** Replace "A label read with K\* = 4 carries "(ONE DOUBLING OF EVIDENCE)"." with:
> "A label read with K\* = k_max, or a label of rows 8 or 9 whose converged arm is not converged at k_max − 1, carries "(ONE DOUBLING OF EVIDENCE)"."

**C13 (F24; §21).**
- Replace "- Decision 1: approve" with "- Decision 1 (the human lead): approve".
- Replace "- Decision 2: after" with "- Decision 2 (the human lead, unless he delegates it in writing at Decision 1; recorded in `results/p10i-s6-freeze-<date>/DECISION_2.md`): after".
- Add the sentence:
  > "If the independent recomputation disagrees with the frozen analysis, the frozen labels are recorded as written with the disagreement beside them; no label is changed without a recorded amendment."

**C14 (F12; §18).**
- Replace "0 to 2.8 h" with "0 to 4.2 h (up to four rates below and two above per arm)".
- Replace "about 7 h registered and 3.5 h calibration" with "about 7 h registered and 5.6 h calibration".
- After "(21,904 s against 16,980 s)", add "; P10-I-S3's first calibration round charged 1.37 times its projection".

**C15 (rulings).** Insert section D below as a new §16a "Rulings for the implementer".

## D. Implementer's guesses and recommended rulings

| # | Guess | Ruling |
|---|---|---|
| G1 | Is rung −1 run on registered cells? | Yes. The 27 cells × 2 arms at r(arm, −1) to 8,192, sharing a run when the rate is equal; reads enabled, replay and disabled; "a rule reads" includes them. Cost +≤0.2 h |
| G2 | Snapshots and evaluations of each registered run | Snapshot at 8,192 and at every rung up to the run's maximum, with optimizer state. Enabled read at U_{k−1} of the run at r(arm, k) for δrun |
| G3 | Failed cell, K\* and R | Edit C2 |
| G4 | Exception types | A failed cell is the non-finite errors of `p4_model.train_step` and `evaluate` as the code raises them (identified by type and message in a test); everything else is `item_error` |
| G5 | Mean arithmetic | Python float `sum` in cell order c = 0..26, divided by 27; parent mean likewise over s = 0..2; δ is the difference of those floats |
| G6 | Pool construction order | Edit C9 |
| G7 | E | Hex SHA-256 of each 65-byte payload of the WikiText-2 train and validation parquet at `select`'s offsets, before de-duplication and before cross-split exclusion |
| G8 | Calibration cell index | c = calibration parent q = 0..2 in seed formulas (329001 + c, 329031 + 4c + j) |
| G9 | New parents' control memory | Not constructed (the backbone draw comes first and is unaffected); if the identity gate needs it, 201 is a declared re-use |
| G10 | Identity gate scope | All nine old parents (F16) |
| G11 | NEG-REF and V_mean weights | Calibration panel on calibration checkpoints at k_max (ADR-0026 ruling 9); edit C7 |
| G12 | Reads per rung | M-FLAT at rungs 0..k_max on the run at r(M-FLAT, k): enabled, replay, disabled, P_used × 4, X_mean, V_mean. D-ADAPT: enabled, replay, disabled, X_mean_dense. Rung −1 and δrun points: G1 and G2 |
| G13 | j† domain | Rungs 0..k_max only; tie to the larger rung |
| G14 | Extension counting | Per arm, across all durations −1..k_max; at most 4 steps down and 2 up per arm; each new rate run to U_max on all three calibration cells |
| G15 | Prefix and resume gate cells | Calibration cell 0 at rate 0.01. Prefix: 8,192. Resume: stop at 16,384, resume to 32,768 |
| G16 | uint8 table | Batch = table[rows].long(); a gate shows bitwise equality with the int64 path of `studies/p10i_s3/data.py` on WikiText-2 ranks |
| G17 | OA and R16 failures | R16 follows line P's integrity and failed-cell state; OA prints NOT EVALUABLE (cause) and changes nothing; BASE on the old parents is in stage G |
| G18 | Pause mechanism | Edit C8 |
| G19 | Decision 2 and disagreement | Edit C13 |
| G20 | Download file names | From the repository listing at the pinned revision, written to the ledger rows with LFS size and SHA-256 before the fetch |
| G21 | Harm counts | Strict ">" (F26) |
| G22 | RSS measure | As P10-I-S3 (process RSS including file-backed pages), stated in the plan |

## E. Questions put to me

- **New backbones.** Twelve are warranted.
  - Across-parent SD of Q in P10-I-S3 was 0.0069, about six times a 3-cell parent mean's SE of 0.0012. The observation is conditional on those nine correlated parents.
  - Separate calibration parents need at least three new backbones anyway.
  - Training cost is negligible: 12 × 1,024 updates of a 27,392-parameter model.
  - The real cost is the adapter and its identity gate.
  - "Old nine plus new draws" saves almost nothing, and rests the primary evidence on the parents that produced the observation.
- **Sharing the machine.** It may share. P10-I-S0 uses 6 workers and this study 6, which is 12 of 16. RSS is within 12 GiB. It must pause for ADR-0028/0030 measured stages (edit C8).
- **Labels.** I enumerated (integrity, dense failure, Cd floor, memory failure) × (convergence 2^5 per arm) × (class 4^5). With C1–C3 every combination reaches exactly one row of §12.3, plus the non-label outcomes: ENGINEERING STOP (named), ITEM ERRORS, INCOMPLETE REGISTRY, PAUSED — IDENTITY, PAUSED, INCOMPLETE (PAUSED AT CAP), NOT RUN. Without C2 the rows are ill-defined under a failed cell.
- **Route A.** "No automatic opening of ADR-0027" is consistent with ADR-0027 §3: COMPETITIVENESS[FLAT] never qualifies, the 19,064-update bound, M-TREE only.

## F. Open choices: which may not be taken by delegation

| # | Recommended option sound? | By delegation? |
|---|---|---|
| 1 Corpus and download | Yes | The download itself is within the standing download delegation; the corpus defines the evidence: human lead |
| 2 U_max | Yes, with C10 disclosed | **No.** Cost against a likely null |
| 3 New parents | Yes (3a) | **No.** New training (CLAUDE.md standing rule) |
| 4 Tree out | Yes | May be |
| 5 No larger dense arm | Yes | **No.** It decides the fairness of the comparison |
| 6 Thresholds unchanged | Yes | **No.** Thresholds |
| 7 Label structure | Yes, with C1, C2, C3, C11, C12 | **No.** It could favour the memory |
| 8 Every rung runs | Yes | May be |
| 9 Route A not automatic | Yes | May be |
| 10 Constant rate | Yes | May be |
| 11 Who approves | Yes, the human lead | — |
| 12 Caps, panel size | Yes | May be |
| 13 Convergence measure | Yes, with C1 | **No.** It could favour the memory |

**I agree that the human lead should take Decision 1 himself.** Reasons:
- The study was conceived after observing an encouraging result, which is the setting where selection and threshold drift happen.
- It includes new backbone training.
- The committed delegation record (`DELEGATION_2026-11-18.md` §2.3) covers continuing "until the P10-I studies that can be entered have a registered outcome". It was written before this study existed, and it excludes "a new redesign study after P10-I". Whether any standing delegation covers this study is for the human lead to confirm.
- He asked for it in his own words.

`Astra review: NOT_PERFORMED`. Claude review is not Astra review.
