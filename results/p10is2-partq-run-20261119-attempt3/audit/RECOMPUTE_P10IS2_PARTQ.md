# P10-I-S2 Part Q, registered attempt 3: independent recomputation

- Auditor: Claude Opus 5.5 (arbor-auditor), 2026-11-19 (local).
- This is independent engineering and mathematical evidence only. It is not Astra validation and not human approval. `Astra review: NOT_PERFORMED`.
- Subject:
  - run directory `experiments/P10IS2-Q-registered3-20261119`, read-only;
  - freeze `83595e07da303031a0d3ec840c2c40d6408da756`;
  - branch `claude/p10-i-s2-impl` at HEAD `74626ab`;
  - Decision 2 at `results/p10is2-partq-freeze-20261119-attempt3/DECISION_2_PARTQ.md`.
- Scripts and raw outputs: `/Users/daniellaloush/dandush03/ArborLM-sealed/audit-s2-recompute/`, with outputs in `out/`. Failed attempts are kept as `*.attempt1.*`.

## Verdict: REPRODUCED WITH CORRECTIONS

All 341 registered quantities I compared agree with my own recomputation. None differs by more than 1e-6. For every compared floating-point value, the largest difference is 0.0 (exact equality). The only difference in the run comes from a wrong identity in my own checker (D1).

Item by item:
- every accept indicator agrees;
- the 64 regenerated batches are token-identical;
- the 25,792 reused files are byte-identical to the plan's list;
- the manifest is true;
- test (a) gives 0 mismatches on 46,380 real R-gloss-icl prompts;
- the charge is within every cap.

The label I derive is **TEACHERS-QUALIFIED (DISJOINT DRAWS)**, as registered.

"With corrections" covers text and record-keeping items only; no registered number changes:
- the student term of Q2 cannot be recomputed (C1);
- several facts must be printed beside the label (C2 to C5);
- two small text points in Decision 2 (C6).

## 0. Environment and what I opened

**Python environments.**
- Most scripts: `/Users/daniellaloush/dandush03/ArborLM/.venv/bin/python -I -B` (Python 3.12.14, torch 2.8.0).
- r02 and r05 used the run's lock venv, `/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/agent-acd0bce1f7811562f/.venv/bin/python -I -B`.
- r02 additionally prepends the durable package copy `/Users/daniellaloush/dandush03/ArborLM/data/datagen-packages` to `sys.path` (transformers 4.57.1 loaded from there). Its environment was:
  - `OMP_NUM_THREADS=MKL_NUM_THREADS=VECLIB_MAXIMUM_THREADS=6`;
  - `UV_OFFLINE=HF_HUB_OFFLINE=TRANSFORMERS_OFFLINE=1`;
  - `PYTHONDONTWRITEBYTECODE=1`.
- `-B` is set because `-I` ignores `PYTHON*` variables. The durable copy held 0 `.pyc` files before and after.

**Nothing from the repository is imported.** That covers `arborlm.*`, `studies.*` and the study's analysis. I read the frozen code, exported with `git archive 83595e07` into `code83595e0/`, only to learn definitions (the reference construction, the accept-rule inputs, the teacher call, the gloss template, the record layouts) and to explain D1.

**Opened in the run directory.** All files were opened read-only; attempt 2's six stages were reached through attempt 3's symlinks.
- `qualification.json`
- `qfit/{record,values}.json`, plus all 63 batch files per teacher.
- `qcheck/teacher_{A,B}/{stop,result,values}.json`, plus every batch of the drawn blocks (2 for A, 5 for B).
- `generation/{result,pools}.json`, plus all 6,152 (A) and 19,375 (B) batch files.
- `regeneration.json` and `manifest.json`.
- `reuse/`, `regeneration/`, `outputs/` and `analysis/` stage manifests.
- `stages/*.complete.json` and `charged_ledger.json`.
- `outputs/gloss_bank.json`, `outputs/gloss_test.json`, `outputs/step8_record.json`, `outputs/record.json`.
- `outputs/bundle/{partition,accepted,manifest}.json`.
- All 25,792 reused files, hashed as bytes.

**Opened elsewhere.**
- Attempt 2's `outputs/gloss_test.json`: the failure record.
- The 10 pre-freeze ledgers named by the plan.
- The `charged_ledger.json` and `rehearsal_counting.json` of counting rehearsals 6 and 7.
- The Tatoeba exports and the teacher and student files under `data/p10s2-pre-20261115/downloads/`.

**Not touched.** I opened no sealed rehearsal file. I did not touch the live shared ledger or its preserved copy. I wrote nothing in either run directory. I made no git writes.

## 1. Q1 to Q4, pools and label (`r01_q.py`, out/r01.txt)

**Own code.**
- A Tatoeba parser that splits on `\n` only.
- References: for each key, the set of normalized German or French texts linked to any English sentence that normalizes to that key.
- `normalize`: NFC, lower case, P* removed, whitespace collapsed.
- chrF-norm: n-grams 1 to 6, β = 2, spaces removed, the maximum over references.
- The accept rule, the 24-setting grid, the Wilson interval (z = 1.959963984540054), the selection with its tie order, the Q_check stop, the generation counts with the evaluation-equal drop, the stop rule, and the torch `randperm` draws.

**Inputs.**
- Every Q_fit item has an own-capability reference in my parse (0 missing).
- The stored E-panel references equal my parse on all 4,468 (key, capability) sets.

Thresholds are named as in `[thresholds]` of the plan and config `configs/p10is2_partq.toml` (ADR-0025 sections 4.2, 4.3 and 4.4).

| Quantity | A (German) | B (French) | Threshold | Recorded = mine |
|---|---|---|---|---|
| Q1 own mean chrF-norm on Q_fit (2,000) | 0.763188 | 0.764105 | `q1_own_score_min` ≥ 0.55 | yes, all 2,000 per-item values exact (max diff 0.0) |
| Other teacher on this capability | 0.120886 | 0.125455 | — | yes |
| Untrained student (recorded only, see C1) | 0.143980 | 0.130470 | — | not recomputable |
| Q2 margin = own − max(other, student) | 0.619208 | 0.633634 | `q2_margin_min` ≥ 0.30 | yes; the binding term is the student for both |
| Q3 settings with Wilson lower bound ≥ 0.90 | 4 | 2 | `wilson_lower_bound` 0.90; correct if chrF ≥ `chrf_correct` 0.60 | yes, all 24 × 5 grid cells per teacher exact |
| Q3 selected (τ, range) | −0.20, [0.5, 2.0] | −0.15, [0.5, 2.0] | most permissive; ties to larger τ, then narrower range | yes (no tie arose) |
| Q3 accepted / correct / precision | 324 / 308 / 0.950617 | 128 / 124 / 0.968750 | — | yes |
| Q3 Wilson 95% | [0.921297, 0.969378] | [0.922402, 0.987782] | lower bound ≥ 0.90 | yes |
| Q_fit accept indicators (2,000) | 0 mismatches | 0 mismatches | — | yes |
| Q_check accepted by block | 88, 68 | 30, 29, 26, 38, 28 | stop at first block boundary with ≥ `q4_min_accepted` 150 | yes |
| Q_check stop block / blocks drawn / outputs | 1 / 2 / 1,000 | 4 / 5 / 2,500 | reserve 16 blocks of 500 | yes; stop = last drawn block |
| Q4 accepted / correct | 156 / 150 | 151 / 142 | ≥ 150 accepted | yes |
| Q4 point precision | 0.961538 | 0.940397 | `q4_precision_min` ≥ 0.90 | yes |
| Q4 Wilson 95% (printed, not a gate) | [0.918637, 0.982256] | **[0.890614, 0.968329]** | — | yes; all 1,000 and 2,500 per-item chrF values exact |
| Generation sources / blocks of 20,000 | 196,857 / 10 (pool ended) | 620,000 / 31 (pool not ended) | stop at 24,000 or pool end | yes |
| Accepted before drop / dropped (evaluation-equal) / pool | 24,196 / 9 / **24,187** | 24,805 / 9 / **24,796** | disjoint target 24,000; minimum 10,000 | yes; `pools.json` equals my accepted list item for item |
| Cumulative before the last block | 22,038 | 23,998 | — | stop rule respected for both |
| Yield on generation | 0.122866 | 0.039994 | — | yes |
| Disjoint draws (seeds 250916 / 250917), 3 × 8,000 | identical; pairwise disjoint | identical; pairwise disjoint | — | yes |
| Digest indices (seed 250908, 4 of 63) | [10, 44, 47, 54] | same | — | yes |

**Evaluation-equal drop.** It is the same whether matched against same-language references only or against all references of E_A, E_B, E_C and E_open: 9 and 9.

**Key-level separation** (out/r06.txt):
- A's and B's generation sources share 0 keys.
- Generation sources overlap 0 keys of every bundle panel (D_cal, D_con, E_A, E_B, E_C, E_open, Q_fit) and 0 keys of the drawn Q_check blocks.
- No source is repeated.
- Identity groups were not rebuilt; this check is at key level only.

**Bundle.** `outputs/bundle/accepted.json` equals `generation/pools.json` for both capabilities.

**Label.** Both teachers pass Q1 to Q4, and both pools are ≥ 24,000. ADR-0025 section 4.3 rule 6 and section 4.4 row 5 therefore give **TEACHERS-QUALIFIED (DISJOINT DRAWS)**, which equals `qualification.json` and `generation/result.json`.

**Against P10-S2's failure.** P10-S2 stopped on these quantities: Q_check accepted 78 / 22 against 150, and pools 7,804 / 2,341 against 8,000. In this run they are 156 / 151 against 150, and 24,187 / 24,796 against 24,000 (the disjoint target; 8,000 per replicate).

**Comparison count.** 341 comparisons in all (out/r01.json "comparisons"). Every one agrees within 1e-6, except D1 below, which is my error.

### D1 (my own mistake, kept)

My checker asserted A_sources + B_sources = A_pool + B_pool − shared_units: 845,642 against 851,172, a difference of 5,530. That identity is wrong, because the pools count items (keys) while `shared_units` counts identity units, and a unit can hold several keys (`split.py:35-41`). The item-level reading is consistent:

| | Pool items | Items to the other capability | Units to the other capability | Keys per unit |
|---|---|---|---|---|
| A | 733,571 | 536,714 (to B) | 532,254 | ≈1.008 |
| B | 782,912 | 134,127 (to A) | 133,057 | ≈1.008 |

The split counts were not independently re-derived, because the partition is not rebuilt.

### Earlier failures of my scripts (kept)

- **`r01_q.attempt1.py`.** It compared Q_check per-item chrF only on accepted items; the record stores the chrF of every drawn output (1,000 and 2,500). It also crashed on a tuple unpack. Both were fixed in `r01_q.py`.
- **`r02_regen.attempt1.py`.** It keyed batches by their stored index, which restarts at 0 in every 625-batch block. It therefore regenerated 32 + 32 wrong (but real) stored batches: draw over n = 625, indices 0 to 570 resolved mostly to the last block. Those 2,048 outputs are also token-identical (out/r02.attempt1.txt). Fixed by global ordering in stored block order.

## 2. Regeneration identity (`r02_regen.py`, out/r02.txt)

**What I ran.**
- My own draw: a fresh `torch.Generator` seeded 250914 per teacher, `randperm(n)[:32]`, sorted, over 6,152 (A) and 19,375 (B) stored generation batches. It equals `regeneration.json` for both teachers.
- Source texts from my own parse: the smallest raw English text whose normalization is the key. It equals the pool's `en` on all 24,187 and 24,796 accepted items.
- My own model load, following the registered recipe:
  - all 7 teacher files re-hashed against the plan's `inputs`;
  - `MarianMTModel(MarianConfig.from_dict(config))` with a weights-only state load; only `lm_head.weight` missing, then tied;
  - the pinned `generation_config.json` applied as the `GenerationConfig`.
- Generation call: beam 4, `max_new_tokens` 48, length penalty 1.0. Deterministic algorithms ON. `torch.set_num_threads(6)`, interop 18 (as the plan's platform record). One process, offline, each batch in its stored composition and order.
- The machine was shared with P10-I-S0 and P10-I-S6 at the time.

**Result.**
- A: 1,024 sources, **0 token mismatches**, 0 text mismatches, max |library sequence score − stored score| 1.19e-7.
- B: 1,024 sources, **0 token mismatches**, 0 text mismatches, max |library sequence score − stored score| 1.19e-7.
- Tolerances: tokens 0; scores 1e-4.
- Generate time: 12.5 s (A) and 14.9 s (B).
- This agrees with the registered `regeneration.json`: ok, 0 token mismatches, max score difference 0.0.

**Scope.** This is the same platform (this machine) and the same torch build, so it is not a cross-platform check.

## 3. Reuse validity (`r03_reuse.py`, `r03b_tree.py`, `r04_charge.py`; out/r03*.txt, r04_charge.txt)

**The plan.**
- `studies/p10is2/freeze/partq_plan.json` at 83595e07 has SHA-256 182e043f…3cc13e43, which equals the freeze record and Decision 2 item 4.
- Its reuse block: 25,792 files; freeze_commit 55017df4616a81795918e21e0792fa742f77bdc4; source `experiments/P10IS2-Q-registered2-20261118`; stages inputs, partition, qfit, qcheck, generation, regeneration.

**Reused files.**
- All 25,792 files re-hashed in attempt 2's directory: **0 mismatches**.
- My own tree hash over them equals the plan's b6777dbc…f94f933.
- The six reused stage paths of attempt 2 hold 25,784 files, all listed. The other 8 listed files are attempt 2's `regeneration.json`, `regeneration/manifest.json` and six `stages/*.complete.json`. Attempt 3 has its own versions of these, which is why 7 of them differ when read through attempt-3 paths; they match in attempt 2's directory.
- The six symlinks point into attempt 2.
- Attempt 2's directory has 26,118 entries with no write bit on any of them.

**Reuse records name their source and commit.**
- The `manifest.json` `reused` block equals the plan's: count, commit 55017df, source, stages and tree hash.
- `reuse/manifest.json` reports status COMPLETE.

**The attempt-3 manifest is true.**
- All 259 listed files (`outputs/**`, `qualification.json`, `regeneration.json`) match by hash.
- The only own files not listed are the excluded stage manifests and the `partition_counts.json` symlink. The symlinked file is covered by the reuse block.

**The run is the frozen code.**
- `git log 83595e07..74626ab` holds one commit, and `git diff --stat` shows one file, `results/p10is2-partq-freeze-20261119-attempt3/DECISION_2_PARTQ.md` (+23).
- The run's worktree (`agent-acd0bce1f7811562f`) has an empty `git status --porcelain`; ignored entries are caches and `.venv` only.

**Charges against the attempt-3 caps** (`[stage_caps_attempt3]`):

| Stage | Charged | Cap | Share of cap |
|---|---|---|---|
| reuse | 2.35 s | 72 s | 3.3% |
| regeneration | 410.72 s | 936 s | 43.9% |
| outputs | 623.44 s | 1,296 s | 48.1% |
| analysis | 3.13 s | 36 s | 8.7% |

All four stage records show `within_cap: true`.

**Pre-freeze charge and total.**
- The 10 ledgers named by the plan re-sum today to 47,493.99 s, the plan's figure exactly; none has grown.
- Total: 47,493.99 + 1,039.64 = **48,533.64 s = 13.482 h of 13.83 h (49,788 s)**, leaving 1,254 s of headroom.
- The ledger field `total_seconds` = 49,788 is the cap, not the charge.

## 4. Tokenization test (a) on the real R-gloss-icl prompts (`r05_prompts.py`, out/r05.txt)

**Method.**
- Tokenizer: my own pure-Python byte-level BPE (`own_bpe.py`, SHA-256 3690aef8…, unchanged from the stop audit and validated there on 144/144 recorded P10-S2 windows).
- My own Dice lexicon (ties to the lexicographically smaller word), my own prompt text (" w = g\n" lines + "English:") and my own reading of the amended rule.
- Each prompt was compared against the whole-string tokenization in two ways: my own segments, and the stored `gloss_bank.json` segments.

**Coverage.**
- 8 lexicons: for each capability, the whole accepted pool (the registered test's lexicon) and each of the three disjoint replicate draws (the Part T lexicons).
- 7 bundle panels: D_cal, D_con, E_A, E_B, E_C, E_open, Q_fit.
- That gives 56 panel-lexicon combinations and **46,380 prompts: 0 mismatches** by my rule and 0 by the stored bank.
- The registered test covered 3,000 of these (E_A/A, E_B/B, D_cal/A, D_cal/B; 0 mismatches recorded).

**Bank checks.**
- Every stored bank segment equals my tokenizer: 2,000 source words, 2,000 source words after a newline, 6,337 gloss words, the separator and the newline.
- The last newline is its own segment.
- Every gloss word of all 8 lexicons is in the bank.

**The attempt-2 item.**
- Attempt 2's recorded whole-string ids decode to `' ill = werde\n wait = warten\n till = geöffnet\n 23'`.
- Attempt 3's prompt text for the same item is `' ill = werde\n wait = warten\n till = geöffnet\n 230 = 230\nEnglish:'`. It starts with that text, and its first 20 whole ids equal attempt 2's: **the prompt text is unchanged**.
- Under the amended rule its segments equal its whole tokenization (token 3805 "\n " is now the newline stored with " 230").

## 5. Disclosures and corrections for the report text

**C1. The Q2 student term is recorded, not recomputed.**
- No per-item untrained-student output or score is stored; `qfit/values.json` holds only the two means, by `pipeline.py:38,211`.
- ADR-0025 section 4.3 rule 8 says "every per-item input of the gate is stored"; the student's Q_fit outputs are an input of Q2. This is a record-keeping gap. PENDING LEAD REVIEW.
- It cannot change the label: Q2 would still pass for any student mean up to 0.4632 (A) or 0.4641 (B), against recorded 0.1440 and 0.1305.
- The report must say that this term was not independently recomputed.

**C2. B's Q4 95% Wilson lower bound is 0.8906, below 0.90.**
- Q4 is a point-precision gate on ≥ 150 items (0.9404 ≥ 0.90), so B passes as registered.
- The ADR itself notes that 150 items give an interval of about 0.84 to 0.94. Print the interval beside the pass.

**C3. A's pool is the whole of A's split pool.**
- 196,857 of 196,857 sources were generated; `pool_ended` is true.
- 24,187 clears 24,000 by 187, only because the final partial block added 2,149.
- B needed its 31st block: 23,998 after 30 blocks.
- Both margins are by rule, not chosen. They should be stated, because the DISJOINT label rests on them.

**C4. Provenance of stages 1 to 6.**
- `qualification.json` does not name freeze 55017df or the reuse.
- Decision 2 item 1 promises that "the outcome of attempt 3 will say that stages 1 to 6 were computed under freeze 55017df and reused". The OUTCOME text must say so; the manifest's `reused` block is the machine record.

**C5. What QUALIFIED means.**
- TEACHERS-QUALIFIED (DISJOINT DRAWS) qualifies training material and teachers: filter precision on held-out Q_check items, and enough accepted pairs for three disjoint 8,000-pair draws per capability.
- It is not a transfer, retention or memory result. No student was trained, and Part T has not started (`part_t_started: false`).
- The oracle line must accompany it, as it does in every record: "oracle-assisted (word-level addresses supplied by rule); lexical translation of short closed-vocabulary sentences, two capabilities of one kind; frozen English student; teacher-only training material verified by measured-precision filter; not autonomous learned memory."

**C6. Decision 2 text (minor).**
- "2,030 s and 966 s" for counting rehearsals 6 and 7 are the rehearsal records' wall totals (2,029.65 and 966.26). Their charged ledgers sum to 2,022.07 and 963.28 s.
- Either figure leaves the decision unchanged. Counted into the total, all Part Q charge would be 14.31 h, above 13.83 h. Their exclusion is the ruling adopted in Decision 2 item 6; that reading should stay printed.
- The decision's "2026-11-20 UTC" is consistent with the ledger timestamps (03:50 to 04:08 UTC).

**What Part T still needs before it runs:**
1. A Part T specification freeze of its own, with its own plan, caps and Decision 2. Nothing here freezes Part T.
2. REAUDIT4 A1 remains open: Part T's reader opens Part Q files without checking them against Part Q's manifest. L12 allows Part T to read "the Part Q manifest's files only, by hash". Two kinds of file need that check:
   - the files listed in the attempt-3 manifest (`outputs/bundle/*`, 259 files);
   - reused files, which are covered only by the `reused` block (per-file hashes in the frozen plan and the tree hash), not by `manifest.json` `files`.

   For example, `generation/pools.json` is not in `files`; its digest is in the plan's reuse list. The training material Part T needs is in the listed `outputs/bundle/accepted.json`, which I verified equals `pools.json`.
3. Part T must never read the Q_fit or Q_check per-item scores (L12). The bundle's `partition.json` carries the Q_fit panel keys and references (no scores), so Part T's reader should exclude that panel.

## Commands (from `/Users/daniellaloush/dandush03/ArborLM-sealed/audit-s2-recompute`)

```sh
# R3=/Users/daniellaloush/dandush03/ArborLM/experiments/P10IS2-Q-registered3-20261119 ; R2=…/P10IS2-Q-registered2-20261118
# PY=/Users/daniellaloush/dandush03/ArborLM/.venv/bin/python ; PYL=/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/agent-acd0bce1f7811562f/.venv/bin/python
# PLAN=code83595e0/studies/p10is2/freeze/partq_plan.json   (git archive 83595e07da303031a0d3ec840c2c40d6408da756 | tar -x -C code83595e0)
timeout 3600 $PY -I r01_q.py $R3 out/r01.json > out/r01.txt
OMP_NUM_THREADS=6 MKL_NUM_THREADS=6 VECLIB_MAXIMUM_THREADS=6 UV_OFFLINE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 \
  timeout 5400 $PYL -I -B r02_regen.py $R3 out/r02.json $PLAN > out/r02.txt
timeout 1800 $PY -I r03_reuse.py $PLAN $R3 $R2 > out/r03.txt
timeout 900  $PY -I r03b_tree.py $PLAN $R2 > out/r03b.txt
$PY -I -B r04_charge.py > out/r04_charge.txt
timeout 3000 $PYL -I -B r05_prompts.py $R3 $R2 > out/r05.txt
timeout 900  $PY -I -B r06_disjoint.py $R3 > out/r06.txt
git -C /Users/daniellaloush/dandush03/ArborLM log --oneline 83595e07..74626ab ; git diff --stat 83595e07 74626ab
git -C /Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/agent-acd0bce1f7811562f status --porcelain
```

`Astra review: NOT_PERFORMED`. Claude review is not Astra review. Model: Claude Opus 5.5.
