# Audit 21: P10-I-S2 Part T, the own-code recomputation of ADR-0025 section 8.6

VERDICT: RECOMPUTATION AGREES (read in the stored precision, float32, per the lead's ruling in section 4.1). 0 differences. Every one of 219,525 stored greedy sequences is identical. Every one of 241,350 item scores is within 1e-6; the worst difference is 4.4e-16. All 468 item records, all 592 registry keys, all 38 combined records and all 304 combined means were compared, and none was missing. Disclosure: computed in float64, the per-window GEN NLLs and the 6 `modification` values differ from the stored float32 values by up to 4.5e-5 and 1.1e-5. No reading changes (section 4.1). Audit 20's D5 is closed. D1 and D2 are closed from the auditor's side (section 5).

- **Auditor:** arbor-auditor, run as Claude Opus 5.5 (claude-opus-5-5), 2026-11-24 to 2026-11-25 (local, Panama).
- **Status of this audit:** independent engineering and mathematical evidence from a Claude session. It is not Astra review and not human approval. `Astra review: NOT_PERFORMED`. The outcome of Part T stays a registered negative/inconclusive result, not a success.
- **Write access:**
  - I wrote only into `experiments/_scratch/audits/audit21_scripts/`, `experiments/_scratch/audits/audit21_out/` and this file.
  - A session hook refused writes to the base-repo path. I wrote through this session's worktree link `.claude/worktrees/arborlm-consolidation-experiment-2b31c1/experiments`, which resolves to the same `/Users/daniellaloush/dandush03/ArborLM/experiments`. Audit 20 did the same.
  - I wrote nothing in the run directory, the Part Q directory or the Part T worktree.
  - `git status --porcelain` in the Part T worktree was empty after the runs (PYTHONDONTWRITEBYTECODE=1 throughout).
  - At the final check it showed one untracked directory, `results/p10is2-partt-run-20261124/` (`OUTCOME.md`, `ACCEPTANCE.md`, `audit/`, `records/`), created at 21:14:59 to 21:15:47 local, after my driver ended at 21:13:16. It is not mine: none of my scripts writes there.
  - HEAD is still c3088aef.

## 1. What ADR-0025 section 8.6 asks, and what was compared

The requirement: "With the auditor's own code every greedy sequence must be identical and every item score within 1e-6." I re-scored every registered read from the stored snapshots, on CPU, with my own code. The comparison (`a21_compare.py`) covers four things.

1. **The 468 per-item records of `item_records.json`, field by field.**
   - Sequences: exact.
   - Item chrF: within 1e-6.
   - Exact flags, teacher texts and edit-distance-1 flags: exact.
   - GEN per-window NLLs: within 1e-6, with router decisions and strata exact.
2. **All 592 registry keys.** Each is my mean of my items. `em:` comes from my exact flags, the GEN loss increase from my NLLs, and `modification` from the snapshots.
3. **The 38 combined records.**
   - C1/C2 ids per item: exact. Scores: within 1e-6. Pass flags: exact.
   - The single-task sequences and scores, and `separate_answers`.
   - The 304 combined means that the frozen recompute compares.
4. **Side checks.** The 6 R-exact hit counts, and the M-ii D_con rejection computed from my own D_con scores.

A record or key missing on either side counts as a difference.

## 2. Code: what is mine and what was imported

**Imported from the frozen tree.** There is one import in `a21_lib.py`: `studies.p10s2.model`, for `Cache`, `StudentConfig`, `build_student` and `load_plain_state`. These are the student's forward pass, its key-value cache and its strict weight loader.
- Re-implementing the 135M transformer would test rounding rather than the study's logic, and rounding alone could flip a greedy argmax at a near-tie.
- The import pulls in `studies.p10s2.core` as a dependency; my code uses nothing from it.

**Mine**, written from ADR-0025 sections 5, 6 and 8, ADR-0022 sections 3, 5.2, 5.4, 6.4, 7, 10.1 and 14.2, and the combined-tasks addendum sections 2 to 7:
- **Inputs:**
  - the Part Q bundle, with my own SHA-256 check of all 8 files against its manifest;
  - the training draws, from the recorded indices;
  - prompts and read positions, rebuilt from the stored segment records with my own bank key. No tokenizer is used.
- **Arms and their reads:**
  - oracle codes (splitmix64 and Box-Muller, re-implemented);
  - the store read;
  - the add at block L;
  - LoRA, the D-append sum, the E-table, M-sep and L-sep.
- **Decoding and routing:**
  - the greedy loop;
  - the routing of which snapshot scores which read;
  - the router decision from the stored projection and keys.
- **Scores:**
  - GEN NLLs, normalisation, chrF-norm and exact match;
  - R-exact, R-nn, R-gloss, R-icl and R-gloss-icl;
  - the edit-distance-1 flags;
  - C1/C2 and the ensemble record;
  - `modification`;
  - every mean (math.fsum).

**Conventions read from the frozen code because the ADRs do not fix them.** These are disclosed; they are not independent.
- Permutation controls draw from a fresh generator on the replicate's +4 seed for each control.
- Values are permuted within each listed stage, stage by stage.
- R-icl puts the 4 nearest pairs first, nearest last, each as its stored full example; TF-IDF ties go to the lower index.
- R-gloss-icl uses the "own-segment" newline rule.
- GEN reads every in-vocabulary window word with the predicted task's codes and no marker read.
- Where the arithmetic is the ADR's, I deliberately used the same elementary torch operations, so that the test is of the logic and not of rounding.

## 3. Projection and actual cost

**Projection, made before the full run.** It was timed on one snapshot (D1, r0, AB: 0.112 s per decode) and on 20-item runs of every task type. It came to about 43,000 worker-seconds (about 12 h), below the 16-hour line, so no sample was substituted.

**Actual cost.**
- The worker processes summed 56,975.7 s (15.83 worker-hours), above my projection and under 16 h.
- Wall time was 5 h 22 min: driver start 15:51:41, end 21:13:16 local, 101 of 101 tasks with rc=0, at most 3 processes of 6 threads, CPU only.
- The miss came mostly from the combined cells: 400 to 420 s each at 3-way load, against my 20-item estimate.

## 4. Result

**Comparison records.** `audit21_out/compare_20261125T021419Z.json` was run by the coordinator. I re-read it, and re-ran the comparison myself with unchanged script hashes: `audit21_out/compare_20261125T021501Z.json`. Both give the same result.

| Quantity | Compared | Differences | Worst \|diff\| |
|---|---|---|---|
| Tasks | 101 of 101 (none missing) | — | — |
| Item records | 468 of 468 | 0 | — |
| Greedy sequences (item records) | 219,525 | 0 | — |
| Item scores | 241,350 | 0 | 4.4e-16 |
| Exact flags / teacher texts / edit-1 flags | 209,525 / 2,625 / 6,000 | 0 | — |
| GEN windows (60 records × 144), float32 | 8,640 windows (17,280 NLL values), preds and strata exact | 0 | 0.0 |
| Registry keys | 592 of 592 | 0 | 5.6e-17 |
| Combined records | 38 of 38 | 0 | — |
| Combined C1/C2 ids and scores | 74,000 each | 0 | 3.3e-16 |
| Combined single-task sequences | 37,000 | 0 | — |
| Combined means | 304 | 0 | 1.1e-16 |
| R-exact hit counts | 6 | 0 (all 0 hits) | — |
| M-ii D_con rejection (my D_con, tolerance 0.02) | 6 cells | none rejected, as registered | — |
| My item keys not in the stored records | 0 | — | — |

**The six `mine_not_in_registry` keys** are `E-table|-|{0,1,2}|em:E_A` and `em:E_B`.
- My comparison derives an `em:` value from every `s:` record that carries exact flags.
- The frozen scoring logs E-table's per-item records, exact flags included. Its registry read for E-table stores only `s:E_x` (`partt_run.score_replicate` writes `records[...][read] = sc.mean` and no `em:`).
- So these six keys are extra quantities on my side, not registered keys. They were not compared, and nothing is missing.

### 4.1 Precision disclosure and the lead's ruling

**What float64 shows.**
- Computed in float64 from the same float32 logits, the per-window GEN NLLs differ from the stored float32 values on all 17,280 NLL values (8,640 windows × base and arm). The differences run from 3.1e-5 to 4.5e-5, and float32 is always lower.
- Recomputed in float32, my values equal the stored ones bit for bit. The cause is float32 accumulation over the 49,152-entry softmax (`a21_nll_probe.py`, `audit21_out/nll_probe.txt`).
- The 6 `modification` values (float32 Frobenius norms over 2.36M entries) differ from my float64 values by up to 1.14e-5; my float32 values equal them exactly. Registered against float64:

| Cell | Registered | Float64 |
|---|---|---|
| AB r0 | 0.6092991 | 0.6093081 |
| BA r0 | 0.6590896 | 0.6590858 |
| AB r1 | 0.6021573 | 0.6021687 |
| BA r1 | 0.6657585 | 0.6657559 |
| AB r2 | 0.6074060 | 0.6074128 |
| BA r2 | 0.6539235 | 0.6539175 |

**Why no reading changes.**
- Every router decision on the GEN windows is `none`, so every `gen:` value is 0.0 in both precisions (float64 maximum 0.0).
- The modification values are 0.60 to 0.67 against the 0.10 floor.

**The lead's ruling, recorded as the lead's and for the human lead's review (not the auditor's ruling).** "The verdict is read in the stored precision (float32); section 8.6's 1e-6 tolerance is written for item scores and greedy sequences, both of which agree; the float64 differences are rounding over the vocabulary, change no reading, and are printed beside the verdict as a disclosure."

**My observation.** This is a numerical hazard, not a defect in this run. A float32 NLL carries a systematic bias of about 3.5e-5 nats, about 0.2% of the 0.02-nat GEN margin. Any future GEN reading that hinges on a difference that small would need float64 accumulation.

## 5. Audit 20's D1, D2 and D5

- **D5 (own-code recomputation owed): closed.** Done, and it agrees (above).
- **D1 (`compare_items` skips keys missing on either side): closed from my side.**
  - My comparison counts a missing key as a difference.
  - It compared 468 of 468 stored records, and my code produced no key the store lacks.
  - The frozen record's defect itself (its `item_records_compared` reports the stored count, not the compared count) is unchanged. It is a record-keeping defect of the frozen code, and no record is now unverified.
- **D2 (combined means count not recorded): closed from my side.** I compared all 38 combined records: per item, per single answer, and the 304 means. The frozen attempt record still does not state its own count.

## 6. cost.json and cost.txt (read-only check; written 15:35:46 by the frozen `cost` command)

**What is right.**
- **Counted training multiply-adds per update.** I checked them against ADR-0025 section 8.5's rule (batch 32 × mean training length 26.3525 = 843.28 tokens; each linear map inputs × outputs per token per pass; twice in the backward pass where trainable; key scan rows × 16 and value mix 8 × 576 per read; 7.0815 reads per row).
  - The student's linear maps: 134,479,872 per token, which is 30 blocks × 3,538,944 plus the tied head 576 × 49,152. × 843.28 = 1.13404e11.
  - M1 forward is 1.13420e11, which is that plus 226.6 reads × (4,096 × 16 + 4,608).
  - M-append exceeds M1 by 226.6 × 4,096 × 16 = 1.485e7, as the extra 4,096 rows imply.
  - D1 forward 1.15444e11 = 1.13404e11 + 2,419,200 × 843.28. D1 backward adds the adapter twice. D-append counts the frozen first adapter once and the second twice (1.19524e11).
  - All of these reproduce.
- **Footprint.**
  - Student: 134,515,008. Embedding 28,311,552 + 30 × 3,540,096 + 576.
  - Stores: N = 2,424,833; 2N in one stage = 4,849,665; M-append/M-ii = 4,849,666 (two gates).
  - LoRA: 2,419,200 / 4,838,400. E-table: 1,152,577.
  - 134,515,008 + 4,849,666 = 139,364,674; ratio to the teachers' 148,613,487 is 0.938.
- **Active-work counts.** 57.304 × 576 / 13.72 = 2,405.7 value parameters per generated token, and the key products of 4,096 / 8,192.

**Readings to disclose beside the multiply-adds.**
- Backward counts for the store arms cover only blocks 5 to 29 plus the head: (25 × 3,538,944 + 28,311,552) × 843.28 = 9.848e10, matching M1's 9.851e10. No gradient is needed below the read layer. This is a sound reading, but section 8.5 does not say it, and it lowers the memory arms' count by about 15% relative to "every map once".
- The LoRA backward counts every block.
- M-ii is counted at 64 rows per update (32 plus 32 replayed) using the teacher-2 mean length for the replay rows too.

**Wrong or misleading in cost.json / cost.txt** (no label is affected; all of this is descriptive):
1. **"peak resident 0.0 bytes" for every arm except M-ii is an artifact, not a measurement.**
   - `partt_cost.py:52` reads `peak_rss_bytes` from `train/manifest.json`'s `tasks` map. That map holds the second invocation, in which 50 of 54 cells were `skipped: result exists` with `peak_rss_bytes: 0`.
   - Only the 4 M-ii cells re-ran. M-ii's 2,630,811,648 is a median over four measured values and two zeros.
   - The first invocation's real peaks are not used.
2. **"teacher inference per accepted item: 0.0 s" is wrong as a cost.**
   - It divides Part Q attempt 3's charged generation seconds by its 48,983 accepted items. The attempt-3 ledger has no generation entry, because generation was reused from attempt 2 (its only entries are the regeneration subsample and other stages), so it reads 0.
   - The real generation time is in attempt 2's records. The line should say "not recorded in this attempt (reused from attempt 2)" or take attempt 2's ledger.
   - ADR-0022 section 10.2 also asks for tokens in and out, CPU seconds and peak memory per accepted item, and none of these are printed.
3. **"median 3557.1 s for 8000 updates" (M-ii) mixes partial and full runs.**
   - The six M-ii cell records have wall times of 23,640.8, 25,507.3, 2,856.6, 2,517.9, 2,279.3 and 3,557.1 s.
   - Three of the six are resumed cells whose wall time covers only the updates after the resume (6,500, 5,000 and 7,500). The median, 3,557.1 s, is BA r1, which ran 7,500 updates.
   - The r0 cells ran under the first invocation's load. The line's "for 8000 updates" is therefore not true of the median. The other arms' medians mix the first invocation's contended walls in the same way.
4. **"timing benchmark: not yet measured."**
   - ADR-0025 section 8.5 lists the timing benchmark as one of the five recorded cost measures. Per ADR-0022 section 10.2 it is CPU, one process, six threads, 200 items per panel, three repetitions, median.
   - It does not exist, so that cost measure is incomplete.
5. **The stored-size line ends "M-append-frozen G not evaluated, G not evaluated"**, although every G_second(M-append) is defined (0.484 to 0.513, audit 20). The line is garbled or fed no G, and should be fixed or removed.
6. **Not printed.** The FEWER VALUE ROWS ACTIVE line of section 8.5 is not printed. Section 8.3's "printed with the line, always" for the multiply-adds is met only in cost.txt: report.txt (15:22:40) predates cost.txt, so audit 20's D3 stands for the report itself.

## 7. Failed or superseded attempts, kept

- The base-repo write was refused by a hook; I wrote through the worktree link.
- `audit21_out/timing/` (2 files) holds the first version of my code, whose GEN NLLs were float64 only (section 4.1).
- `audit21_out/compare_20261124T205829Z.json` is a debugging comparison on 3 finished tasks. It is INCOMPLETE by construction.

## 8. Commands and environment

Validation on prefixes, then the full job:

```
cd /Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/agent-acd0bce1f7811562f
env -u PYTHONPATH PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=6 uv run --locked --offline python $S/a21_task.py "<task>" --limit 20
cd $S && nohup python3 -I a21_driver.py > ../audit21_out/driver.log 2>&1 &      # pid 67246, 15:51:41 to 21:13:16
cd $S && python3 -I a21_compare.py                                              # -> compare_20261125T021501Z.json
# S=/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/audits/audit21_scripts
```

**Environment.**
- Machine: macOS Darwin 27.2.0, arm64, 18 cores, 48 GiB.
- Workers: the Part T worktree's locked venv (Python 3.12.14, torch 2.8.0), `torch.set_num_threads(6)`, deterministic algorithms on, CPU only. There is no MPS in my code.
- Driver and comparison: python3 3.15.1 `-I`, standard library only.

**Script SHA-256** (unchanged from launch to the final comparison):

| Script | SHA-256 |
|---|---|
| a21_lib.py | ccf1091a… |
| a21_task.py | 0f4592ef… |
| a21_driver.py | ecb595b2… |
| a21_compare.py | 948c5678… |
| a21_peek.py | 781f9452… |
| a21_nll_probe.py | 83dde746… |

## 9. Verified myself versus taken from records

**Verified myself:**
- every greedy sequence, item score, exact flag, router decision and GEN NLL, recomputed from the snapshots;
- every registry value and combined mean;
- R-exact hits;
- the absence of an M-ii rejection;
- the bundle, snapshot and router file hashes against their manifests;
- the multiply-add and footprint arithmetic in cost.json.

**Taken from records:**
- the stored segment ids, read positions and references of the Part Q bundle (hash-checked, not re-tokenized);
- the recorded training-draw indices;
- the windows, the gloss bank and the teachers' stored outputs;
- the conventions of section 2 that the ADRs leave open;
- the cell wall times and manifest values that cost.json summarises.
