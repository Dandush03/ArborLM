# P9-I (ADR-0017 Part I) — pre-freeze audit: calibration and implementation

- **Auditor:** Claude Opus 5.5 (`claude-opus-5-5`), acting as the independent auditor of ADR-0017 Part I. I wrote the design review and confirmation of Part I (`docs/reviews/adr-0018-design-2026-11-14/`); I did not write any code audited here (`studies/p9i/`, `configs/p9i_interface.toml`, `tests/test_p9i_*.py`, the imported `studies/p9/` paths).
- **Date:** 2026-11-14. **Worktree:** `.claude/worktrees/arborlm-consolidation-experiment-2b31c1`, branch `claude/adr-0017-design`, HEAD `e626280`. Code identity of HEAD equals the identity recorded by the calibration and the rehearsal (`source_sha256 5bc82bce…`, `spec_sha256 7dcbcfc1…`, `config_sha256 7cc20791…`); `git diff 939b4bf..HEAD` touches only `results/p9i-*`.
- **Status of this document:** independent engineering and mathematical evidence. It is **not** Astra validation and **not** human approval. **Astra review: NOT_PERFORMED.**
- **Environment:** Apple M5 Max, macOS 27.2.1 arm64, Python 3.12.14, torch 2.8.0 (CPU, float32 unless stated), `uv run --locked`, `PYTHONPATH=.` from the worktree root. Run directories read from `/Users/daniellaloush/dandush03/ArborLM/experiments/`. Every script is beside this file; every output is in `outputs/`. Scripts are kept byte-identical to the versions whose outputs are recorded; the folder's `ruff.toml` ignores style-only rules (including F401) for that reason.

## What I ran and did not run

Ran (none of it charged to the P9I ledger, none of it through the study's stage driver):

| Script | What | Data touched |
|---|---|---|
| `a1_calibration_rule.py` | §I.6 rule recomputed from the 18 per-cell calibration records | draw-1 calibration records (observed) |
| `a2_rescore_snapshots.py` | independent forward + ties-wrong scoring of calibration snapshots (binding cells) | draw-1 panels regenerated, calibration snapshots |
| `a6_loss_replay.py` | forward-only replay of the recorded per-update loss from snapshots | draw-1 training batches regenerated |
| `a10_g2_controls.py` | no-memory baseline, G2 intervals (own binomial), exact retrieval | draw-1 panels |
| `a3_rehearsal_replay.py` | 8 rehearsal cells re-trained 64 updates on draw 2, compared bit for bit with the rehearsal run | rehearsal draw 2 |
| `a4_arm_forward.py` | every arm's forward against my own implementation; causality; E7 window; BB parameter set; backbone immutability; D7 match | random bytes (test seed 900001), verified B101 backbone |
| `a5_classes_enumeration.py` | §I.8.1–8.3 re-implemented; 20,000 random + structured synthetic tables | synthetic |
| `a7_restoration.py` | checkpoint restoration, 10 arms, 2 × 24 updates | rehearsal draw 2 |
| `a8_next_byte.py` | BB next-byte loss against my own computation; 5% rule input | backbone corpus rows |
| `a9_generate_timing.py` | data generation + G1 at full size (the rehearsal did not time it) | rehearsal draw 2 |
| `a11_registry_seeds.py` | 57-cell matrix from the §I.7 table; seed disjointness | none |
| `a12_preconditions.py` | registered-mode accept / refuse paths in a throw-away clone | none |
| `uv run --locked pytest tests/test_p9i_*.py` | 111 passed (50 s) | test seeds |

Not run: no registered stage; no registered-seed data generated or read (182001+); no training or evaluation on draw 1 (the draw-1 work above is forward-only on already-observed snapshots and batches); no interface arm on draw 1; no accuracy read on draw 2 (the replay compares tensors only). I did not edit any existing file and did not commit.

Failed checker attempts (kept): `outputs/a4_arm_forward_attempt1_FAILED_auditor_bug.txt` (my `argsort(-1, stable=True)` call; fixed to `dim=-1`), `outputs/a8_next_byte_attempt1_FAILED_auditor_bug.txt` (my source slicing). Both were my mistakes, not the implementer's.

## Discrepancy that was my own mistake

**ADR-0017 §15.4 item 1 corrects my confirmation edit R3(d), and the correction is right.** My R3(d) said "P9 uses AdamW at 0.003 for the projections and gate, and row-lazy Adam at 0.012 for the key and value tables". That is false for P9 in general: §5.1 specifies one AdamW (lr 0.003, wd 0, clip 1.0) for the memory; the row-lazy optimizer is §5.6's arm A10 only; `studies/p9/train.build_optimizer` builds one AdamW for every `adamw` cell and `RowLazyAdam` only for `lazy` (A10) cells; the P9 calibration this design rests on used one AdamW (`P9C-…/cells/CAL-A5-flat-R2-n4096-…/u0001024/optimizer.pt`: one optimizer, one group, lr 0.003, wd 0). I generalised from A10. The lead resolved the contradiction in favour of §5.1, which is what P9-I actually ran (below). The correction altered approved text before any calibration; it should be listed among the items the lead approves at decision 2 (it is recorded in §15.4, so this is a note, not a finding).

---

## PART 1 — Calibration audit

Run `experiments/P9IC-20261114T225847947431Z-b0cf703a0d7c4f7ab8f308c3de6ddf78` (commit `939b4bf`, same code identity as HEAD).

### (a) The §I.6 rule, recomputed

`a1_calibration_rule.py` (own code; no `core.select_updates`) → `outputs/a1_calibration_rule.txt`.

Minimum over B101 seeds 1791/1792 and Panels A/B, as count / F:

| Slots / facts | Rung | 1,024 | 2,048 | 4,096 | 8,192 | 16,384 |
|---|---|---|---|---|---|---|
| 4,096 / 2,048 | R2 | 1871 (0.9136) | 2048 | 2048 | 2048 | 2048 |
| 4,096 / 2,048 | R1 | 608 (0.2969) | 1865 (0.9106) | 2045 (0.9985) | 2048 | 2048 |
| 16,384 / 8,192 | R2 | 6309 (0.7701) | 7988 (0.9751) | 8192 | 8192 | 8192 |
| 16,384 / 8,192 | R1 | 782 (0.0955) | 3498 (0.4270) | 7972 (0.9731) | 8185 (0.9991) | 8191 (0.9999) |
| 65,536 / 32,768 | R2 | 13262 (0.4047) | 30419 (0.9283) | 32668 (0.9969) | 32768 | 32768 |
| 65,536 / 32,768 | R1 | 1902 (0.0580) | 3289 (0.1004) | 14090 (0.4300) | **31622 (0.9650)** | 32672 (0.9971) |

- U = 2,048 fails (R1 16K 0.427, R2 64K 0.928, R1 64K 0.100); U = 4,096 fails only on R1 at 65,536 (0.430); **U = 8,192 passes every size** (smallest margin R1 64K 0.965 ≥ 0.90). No size fails (each size has a joint qualifying U). **U = 8,192, no failed size** — identical to the run's `calibration.json` (all 30 minima equal bit for bit) and to the lead's reading.
- Binding cell R1 at 65,536: seed 1791 A 0.42999 / B 0.43048 at 4,096 and A = B = 0.96503 at 8,192; seed 1792 A 0.45636 / B 0.45874 at 4,096 and A 0.96634 / B 0.96796 at 8,192. Matches the README (0.430 → 0.965).
- B102 replicate at 8,192 (reported only): R1 1.0000 / 0.9999 / 0.9804, R2 1.000 everywhere; the README rounds 0.9999 to 1.000 (fine).
- Every record: arm and mode `calibration`, status completed, 16,384 updates run, 16 × 16,384 contexts, init seed = cell seed, 0 trainable backbone parameters, snapshots at 1,024 … 16,384, every fact exposed exactly 16,384·128/F times (1,024 / 256 / 64 at the end); every accuracy is an integer count over F.

**Independent re-scoring from snapshots** (`a2_rescore_snapshots.py`): my own backbone blocks (LayerNorm, causal 4-head attention, exact GELU), my own R1 codes (splitmix64 + Box–Muller from the §5.3 definition), my own R2 slot table from the fact table, my own top-8 (stable descending sort, ties to the lowest slot id), gate · wo read added at 8r+6 only, my own answer extraction from the tokens and strict ties-wrong alphabet argmax. Data regenerated from `p9core.rehearsal_seeds(1)` with `studies.p9.data`.

Outputs `outputs/a2_rescore_float32.txt` (12 min 17 s, two threads) and `outputs/a2_rescore_4096.txt`. Auditor count / run count per panel (the run's count = recorded accuracy × F):

| Cell | Update | Panel A | Panel B |
|---|---|---|---|
| R1 65,536 B101 s1791 | 4,096 | 14090 / 14090 | 14106 / 14106 |
| R1 65,536 B101 s1791 | 8,192 | 31622 / 31622 | 31622 / 31622 |
| R1 65,536 B101 s1792 | 4,096 | 14954 / 14954 | 15032 / 15032 |
| R1 65,536 B101 s1792 | 8,192 | 31665 / 31665 | 31718 / 31718 |
| R2 65,536 B101 s1791 | 2,048 | 30419 / 30419 | 30432 / 30432 |
| R2 65,536 B101 s1791 | 8,192 | 32768 / 32768 | 32768 / 32768 |
| R2 65,536 B101 s1792 | 2,048 | 30427 / 30427 | 30439 / 30439 |
| R2 65,536 B101 s1792 | 8,192 | 32768 / 32768 | 32768 / 32768 |
| R1 16,384 B101 s1791 | 8,192 | 8187 / 8187 | 8188 / 8188 |
| R1 16,384 B101 s1792 | 8,192 | 8187 / 8187 | 8185 / 8185 |
| R1 65,536 B102 s1791 | 8,192 | 32141 / 32141 | 32125 / 32125 |
| R2 4,096 B101 s1791 | 1,024 | 1880 / 1880 | 1871 / 1871 |
| R1 4,096 B101 s1791 | 1,024; 2,048 | 608 / 608; 1865 / 1865 | 628 / 628; 1894 / 1894 |

**28 of 28 panel counts identical** (count difference 0 everywhere), including both rule-deciding cells (R1 64K at 4,096 and 8,192 updates in both seeds; R2 64K at 2,048). Every trained fact appears exactly once per panel (F of F). The backbone inside each snapshot equals the verified frozen backbone. Unseen-control counts at 65,536 slots (2,048 controls; descriptive, not a calibration rule): 51–77 correct, all inside the chance interval [36, 96], so no LEAKAGE in the oracle rungs.

**Forward-only loss replay** (`a6_loss_replay.py` → `outputs/a6_loss_replay.txt`): for snapshot u, the batch of update u+1 rebuilt from draw 1's training schedule over the first F facts, my forward, 32-way alphabet cross-entropy at the 8 answer sites, compared with line u+1 of `updates.jsonl`: R2 4K s1791 at u = 1,024 (1.2098699 vs 1.2098697) and 8,192 (0.6751066 vs 0.6751066); R1 4K B102 at 2,048 (0.9882945, equal); R1 16K s1792 at 4,096 (0.9193992, equal). The recorded 256-way loss matches too. This shows the run trained on draw 1's stream with the alphabet loss at answer sites.

### (b) What ran, on which draw and seeds

- The run directory holds exactly the 18 calibration cells (R1, R2 × 3 sizes × {B101 s1791, B101 s1792, B102 s1791}) plus `calibration_controls.json`; the stage manifest lists 19 tasks, all completed, mode `calibration`. `core.Cell` refuses a `CAL` cell of any arm other than R1/R2, and `calibration_guard` refuses before anything is built.
- Draw 1: `calibration_controls.json` names seed set `rehearsal-1`; my re-scoring and loss replay with draw-1 data reproduce the recorded accuracies and losses exactly, which another draw would not. R1 codes seed 179112 (draw 1's `r1_codes`).
- Init seeds 1791/1792 (train records). No registered seed observed: the only P9I run directories are `P9IC-…` and `P9IH-…`; the ledger has exactly those two entries; no `P9IP` (generate) directory exists; tests reference 182001 only as constants and build data only from test seeds 900001+ (`grep`). Registered data seeds 182001–182020 overlap with nothing observed (`a11`: draws 0–9, 180101–181900, P9 registered seeds, test seeds — zero overlap each).

### (c) Loss, optimizer, matched updates, answer-site reads

- **Alphabet loss:** shown by the loss replay above.
- **Single AdamW:** every calibration snapshot's `optimizer.pt` holds one optimizer with one parameter group, lr 0.003, betas (0.9, 0.999), eps 1e-8, wd 0; R1 group = {keys, values, wo, gate}, R2 = {values, wo, gate}. No row-lazy state.
- **Matched updates:** every cell ran 16,384 updates with snapshots at the five marks; U is read from snapshots (constant learning rate).
- **Answer-site-only reads:** R1/R2 select at `read_positions_for` = 8r+6 only (P9 rungs `R0a/R1/R2`); my forward adds the read only at those positions and reproduces every count exactly.
- **Backbone untouched:** the backbone tensors inside every re-scored snapshot equal the verified frozen backbone of the cell's parent (`backbone_equals_frozen` True).

### (d) G2 and the controls

`a10_g2_controls.py` → `outputs/a10_g2_controls.txt`. My forward of the frozen backbone with nothing added, ties-wrong, and my exact binomial central interval (level 1 − 0.001/8, lgamma):

| Test | Auditor count | Interval | Run's count |
|---|---|---|---|
| A/2048, A/8192, A/32768, A/unseen | 68, 262, 1030, 53 | [36, 96], [198, 318], [905, 1147], [36, 96] | identical |
| B/2048, B/8192, B/32768, B/unseen | 74, 286, 1074, 58 | same | identical |

All 8 inside: **G2 passes**. The B102 no-memory counts (reported, not in G2) also match (60/237/1025/49 and 66/258/1067/57). Exact retrieval: the fact table's answers equal the answer bytes of every trained-fact context in both panels, so the dictionary lookup scores 1.000 at every size, as recorded.

### Verdict, Part 1

**CALIBRATION CONFIRMED: U = 8,192 updates, no size failed, G2 passes.** Every number of the lead's reading that I recomputed agrees; I found no discrepancy in the calibration.

---

## PART 2 — Implementation audit

### What holds (checked by my own code or by reading)

**Arms (`a4_arm_forward.py` → `outputs/a4_arm_forward.txt`).** All addition parameters (and BB's attention) were re-drawn at a large scale so that the memory term matters; logits of every arm vs my reference written from §I.3: max |difference| 2.9e-6 … 1.3e-5 (float32 rounding) for N, W7, E7, A4, A4E, D, D7, BB, BB-D, BB-0. R1/R2 are covered by the exact re-scoring of Part 1.
- What is read and where: N/BB read W·h_t; W7 W·[h_{t−6};…;h_t] (oldest first, 16 × 224); E7 the same on e = token + position embedding; A4/A4E one causal 4 × 8 bias-free attention (q from x_t, k/v over x_0…x_t, 1/√8, no norm, no output projection) then W; D/BB-D the adapter on h_t, D7 on the 224-wide window. Every addition is **exactly zero at all 55 non-answer positions** for every arm.
- **Causality / leakage:** for every arm, changing any input byte p leaves the logits of every answer site s < p bit-identical (62 positions × 6 contexts). So no query sees the answer byte (position s+1) or any later position. No non-oracle arm reads the fact table, the fact ids or `identifier_codes`; only R1/R2 do (reading).
- **E7/A4E use embeddings with no block:** their queries are bit-identical when block 0 is perturbed (W7, A4, N change, as they must). E7's query at site t changes for every byte in t−6…t and for no byte outside.
- Parameter counts: N 198,145; W7/E7/A4/A4E +3,072 each; D7 hidden 786 / 3,090 / 12,306 with **exactly** W7's count at all three sizes (201,217 / 791,041 / 3,150,337); D plain matches N exactly (3,096 / 12,312 / 49,176 hidden).
- **BB trains exactly** `blocks.0.qkv.{weight,bias}` and `blocks.0.attn_out.{weight,bias}` = **4,224** parameters; after three BB steps the shared frozen backbone object is bit-identical and has no `requires_grad`; in the model's own copy only those four tensors moved (FFN, norms, block 1, embeddings unchanged). In the rehearsal snapshots, BB/BB-D/BB-0 differ from the verified frozen backbone in exactly those four tensors and every other arm in none (`a3`).
- Gradient reach: every trainable tensor of every arm receives a non-zero finite gradient; no frozen tensor carries one.

**Training.** Loss = `F.cross_entropy` over logits restricted to bytes 0x40–0x5F at input positions 8r+6 against the byte at 8r+7 (read and replayed). One AdamW (`arborlm.engine.optimizer_for`, lr 0.003, wd 0) over every trainable tensor including BB's attention, one global clip 1.0; rehearsal optimizers: 1 optimizer, 1 group, 3–9 tensors as expected per arm (`a3`). Every registered cell runs exactly U updates (`updates = max_updates = U`, snapshot at U). Determinism: 8 rehearsal cells (N, BB, A4E, BB-D, BB-0, D7, W7, E7) re-trained in a new process reproduce the rehearsal's `model.pt` and `optimizer.pt` bit for bit; checkpoint restoration is bit-identical for 10 arms (A4E, W7, E7, A4, D7, BB-D, BB-0, R1, R2, BB; the implementer's gate covers only N and BB).

**Evaluation (read; numerics spot-checked).** Accuracy = strict ties-wrong argmax within Σ (P9's `score_answer_sites`, identical to my scorer on ~400k sites). η is formed per size, seed, parent and panel in `classes`. Value permutation is a cyclic derangement (no slot keeps its value); disabling zeroes the addition; "chance" = inside the 8-test G2 interval for the panel's fact count. LEAKAGE = unseen-fact count outside the same interval. Minimal supports use P9's routine on a selection that exists only at the answer site, so candidates are exactly that read (= "restricted to the answer-site read"); p_f^nomem is the arm's own memory-disabled probability (for BB this keeps the trained attention — a stated reading). BB next-byte loss: 256-way over the 2,048 rows × 64 targets with nothing added; my float64 computation 2.3494174 vs theirs 2.3494175 (B101); BB at initialization gives a rise of exactly 0; `degraded` ⇔ rise > 0.05 (`a8`).

**Classes (`a5_classes_enumeration.py` → `outputs/a5_classes_enumeration.txt`).** My implementation of §I.8.1 (both steps, B102 rule with rows 2–4 against B102's R1 per §15.4.5, MODEL_STORES_FACTS after the B102 rule), §I.8.2 (dense comparison paired min-of-four, NOT COMPARED for non-WORKS/PARTIAL classes, for A4/A4E and for MODEL_STORES_FACTS per §15.4.6; four-way backbone contrast not printed when both arms FAIL) and §I.8.3 steps 0–4 agrees with `analyze_classes` on **20,000 random tables with 0 disagreements**; every class, annotation value and selection outcome (steps 0, 1, 2, 3, 4) occurs. Implementer's choices: 0/0 → 1 in the backbone contrast (reads "equal" → ADDS NOTHING; reachable only when both arms score 0 on a seed–panel pair), +∞ for a positive accuracy over 0, η = +∞ / 0 for R1 = 0 (unreachable: R1 < 0.5 makes the size NOT_EVALUATED first), NOT_JOINT as a failed size (§15.4.2) — all consistent with the ADR. Boundary checks: η = 0.9/1.0 → WORKS; 0.45/0.5 → PARTIAL (accuracy < 0.5).

**Registry and seeds (`a11`).** The 57 cells built from the §I.7 table equal `core.cells()`; calibration cells are the 18 of §I.6; registered data seeds 182001–182020 are disjoint from every observed or reserved range.

**Stage driver.** Failed tasks keep a failed record and are refused on re-run (P9 pool: a task with an existing failed or result file is never relaunched); an evaluate task with no completed train task is skipped (fail-closed). The ledger holds 829.3 + 101.0 = **930.3 s** of 14,400 s; each pool stage refuses to start if the remainder is below its own cap and is charged its wall time. Lead's stage caps sum to 6,000 s; 930 + 6,000 = 6,930 s ≤ 14,400 s.

**Registered-mode preconditions** (accept path, untested by the implementer; `a12_preconditions.py` → `outputs/a12_preconditions.txt`, in a throw-away clone at `e626280`): freeze = HEAD → ACCEPTED (returns commit and tree); freeze = HEAD~1 and `939b4bf` → ACCEPTED (only `results/` differ); no freeze commit → REFUSED; an untracked file → REFUSED; the ADR edited after the freeze commit → REFUSED (see M3).

**Rehearsal whitelist.** Run `P9IH-…`: 115 JSON files; the only key matching loss/accuracy/nll/entropy/margin/correct/bits is the boolean `loss_finite`; 57 worker logs contain only library warnings and `{"label", "evaluation_seconds"}` lines; no loss, accuracy or count. All 57 tasks completed. The draw is not recorded in the records; I confirmed draw 2 and the rehearsal init seeds (179201/179202) by bit-exact replay (`a3`). Recomputed projection from the 57 rehearsal records: training 2.32 h summed at U = 8,192; 1,407 s makespan with six workers (longest cell BB-D 65,536 s1802, 404 s); evaluation 353 s summed, 59 s makespan; peak RSS 0.48 GiB training, 1.49 GiB evaluation. Data generation + full G1 on draw 2: 10.2 s single-thread (`a9`) against the 300 s generate cap.

### Findings

No BLOCKER. Three MAJOR, all in the analysis/run plumbing, none in the model, training, scoring or class code.

#### M1 (MAJOR) — classes and a selection are derived when registered cells are missing or failed

§8.6 (applied by §I.9): "`INCOMPLETE`: any registered cell lacks a record; **no class is derived** for a lane with a missing mandatory cell; the denominator is never reduced." `work_analyze` marks the status INCOMPLETE but still calls `classes.analyze_classes` and writes a selection, and `analyze_classes` silently skips missing inputs. On synthetic tables (`a5`): a missing BB-0 cell turns BB's MODEL_STORES_FACTS into INTERFACE_WORKS and the selection into **BB**; one missing BB seed at 65,536 moves the selection to **A4**; a missing B102 replicate skips the B102 demotion (INTERMEDIATE → INTERFACE_WORKS). A run that loses a cell could therefore print a selected interface that the complete matrix would not give.

Fix (paste into `studies/p9i/stages.py`, `work_analyze`, replacing the `result = classes.analyze_classes(...)` line and keeping the rest):

```python
    incomplete = bool(missing or failed_tasks)
    if incomplete:
        result = {
            "classes": {}, "details": {}, "annotations": {}, "backbone_contrast": {},
            "size_status": {str(s): size_status.get(s) for s in sizes},
            "selection": {"outcome": "INCOMPLETE", "step": None, "inconclusive_sizes": {},
                          "scope": ["no class is derived: registered cells lack a record (ADR-0017 section 8.6)"]},
        }
    else:
        result = classes.analyze_classes(table, lm, size_status, sizes=sizes)
```

and add `"INCOMPLETE"` to `classes.OUTCOMES`. A descriptive per-cell table may still be printed by `report`, labelled "descriptive, no class".

#### M2 (MAJOR) — failed gates and LEAKAGE do not stop interpretation

Asked specifically: the implementer records a failing G2 as `g2_passed: False` and leaves the status alone. On the **status** that is right: §8.6 defines only `ENGINEERING_FAIL` (identity, determinism, checkpoint or gradient-reach defects **only**) and `INCOMPLETE`; a G2 failure is neither. But G1–G4 are gates **to interpretation** (§3 table, §8.1, §I.9), and §8.1 says of LEAKAGE that the lane "is not interpreted until the auditor explains it". The code still derives classes and prints a selected interface when G2 fails or any cell is flagged LEAKAGE. Conversely it maps a G1 failure to `ENGINEERING_FAIL`, which §8.6's "only" excludes.

What it should do: keep the status (COMPLETE / INCOMPLETE / ENGINEERING_FAIL from G4 defects only); when G1 or G2 fails or any LEAKAGE flag is set, write the classes as descriptive, set `interpretable: false`, and replace the selection outcome with `NOT_INTERPRETED` with the reasons; the report shows this first. Paste into `work_analyze` after `leakage = …`:

```python
    g2_ok = None if gates is None else bool(gates["g2_passed"])
    status = "ENGINEERING_FAIL" if defects else ("INCOMPLETE" if missing or failed_tasks or gates is None else "COMPLETE")
    gate_reasons = [r for r, bad in (("G1 failed", not g1_ok), ("G2 failed", g2_ok is False),
                                     (f"LEAKAGE: {', '.join(leakage)}", bool(leakage))) if bad]
    if gate_reasons:
        result["selection"] = {"outcome": "NOT_INTERPRETED", "step": None, "inconclusive_sizes": {},
                               "scope": ["gate to interpretation failed (ADR-0017 sections 3, 8.1, I.9): " + "; ".join(gate_reasons)
                                         + "; classes are descriptive until the auditor explains it and the human lead decides"]}
```

(delete the earlier `status = …` line that uses `not g1_ok`), write `"interpretable": not gate_reasons` into `analysis.json`, add `"NOT_INTERPRETED"` to `classes.OUTCOMES`, and in `report.render_markdown` print `**NOT INTERPRETED**` with the reasons above the selection when `analysis.get("interpretable") is False`. **PENDING LEAD REVIEW:** whether a G2 failure observed in the gates stage (before any training) should also stop the training stage; the ADR does not say, and the code above does not stop it.

#### M3 (MAJOR, process) — decision 2 cannot be recorded "here" (in the ADR) after the freeze without the registered run refusing

§15.3 says the lead "records the approval here before the run"; §I.12 orders freeze → decision 2 → run. `check_preconditions` requires the ADR at HEAD to equal the ADR at the freeze commit. In the clone, appending a decision-2 line to the ADR after the freeze commit makes every registered stage **REFUSED** ("…ADR-0017….md at HEAD differs from the freeze commit"). The check is right to fail closed; the order of record is undefined. Either reading below closes it; it must be fixed in text before the freeze, with no code change:

- (preferred) Add to §15.3 after "records the approval here before the run": "The approval is recorded in the freeze commit itself: the commit that freezes code, configs, data identities and this ADR also carries the decision-2 entry, and its hash is the `--freeze-commit` of every registered stage. Nothing in `studies/`, `configs/p9i_interface.toml`, `tests/test_p9i_*` or this ADR changes after it." or
- record decision 2 in a new file (e.g. `docs/decisions/ADR-0017-P9I-decision-2.md`, not hashed by `check_preconditions`) and amend §15.3's "here" to point to it.

#### Minor

1. **Registered U and failed sizes are not bound to the audited calibration record.** In registered mode `updates_for` accepts `--updates` with no `--calibration`, and any file can be passed as `--calibration`. Fix: in `updates_for`, `if args.mode == REGISTERED and record is None: raise pool.StageRefused("refused: a registered stage needs --calibration")`; and refuse unless `file_sha256(args.calibration)` equals the hash written into the freeze record. The audited record is `calibration.json`, sha256 `087bf0b5885859a78781e32cb0e0ce8d3b154dfcc471965cf82f06718c509f44` (identical in the run directory and in `results/p9i-calibration-2026-11-14/`).
2. **Registered evaluation does not require the data manifest** (`work_evaluate` calls `verified_data(args, require_manifest=False)`); use `require_manifest=not args.dry and args.mode == REGISTERED` as `work_train` does. Also nothing ties the run's `data_manifest.json` hashes to the freeze; record them in the freeze commit.
3. **Template pool not asserted for the registered set.** P9 asserts `pool == TEMPLATE_POOL` only for a seed set named `registered`; P9I's is `p9i-registered`. In `work_generate`, for `args.mode == REGISTERED`, add `if study.pool != p9core.TEMPLATE_POOL: raise StageError("template pool differs from the registered pool")`.
4. **Report omissions.** `RESULTS.md` / `cells.csv` do not show η, value-permutation/disabled accuracies, minimal-support shares, or the BB / BB-D / BB-0 next-byte losses before/after that §I.3.2 and §I.8.3 say are reported and carried. They are in the eval records; add columns `eta_{A,B}`, `permuted_accuracy_{A,B}`, `disabled_accuracy_{A,B}`, `support_share_{A,B}`, `lm_before_nats`, `lm_after_nats`, `lm_relative_rise` to `_rows_cells` (η = accuracy / the same-seed, same-parent R1 accuracy).
5. **Rehearsal records do not name the draw.** Add `"seed_set"` (string) to `REHEARSAL_RECORD_KEYS`/validators and write `job.data.seeds.name`. (I confirmed draw 2 by replay.)
6. **Stale text.** `evaluate.py` docstring still marks the 0.9-cosine reading "PENDING LEAD REVIEW" although §15.4 item 4 settled it; the ADR status line says "Nothing of Part I has run". Update both at the freeze (the ADR line is part of M3's freeze edit).
7. **No common U across live sizes.** If every size qualified at some U but no single U qualified at all live sizes, `select_updates` returns None with no failed size and the run refuses. The ADR has no rule for this; moot at U = 8,192. PENDING LEAD REVIEW only if a recalibration ever happens.
8. **`float(loss)` on a tensor that requires grad** produces a PyTorch warning in every training log; cosmetic (`float(loss.detach())`).
9. **G1 horizon.** P9's G1 checks "no panel context in training" over 512 / 128 / 128 epochs at 2,048 / 8,192 / 32,768 facts; P9-I at U = 8,192 needs 512 / 128 / 32, so it is covered. It would not cover 4,096 slots at U = 16,384. Note only.
10. **Snapshot hashes** recorded in `train.json` are not verified when `evaluate` loads a snapshot; add a `file_sha256` comparison in `evaluate_cell`.

### Verdicts

- **Calibration: CONFIRMED.** U = 8,192 updates, no size failed, G2 passes; binding cell R1 at 65,536 slots (0.430 at 4,096, 0.965 at 8,192). Only controls, R1 and R2 ran, on draw 1, seeds 1791/1792 (B101) and 1791 (B102), with the alphabet loss, one AdamW, matched updates and answer-site reads; no registered seed was observed.
- **Implementation: READY AFTER the fixes of M1, M2 and M3.** The model, training, scoring, evaluation and class code are a faithful implementation of §18 and §15.4 by every check above. The minors may be applied at the same time and do not block. After the fixes: re-run `uv run --locked ruff check .`, `uv run --locked mypy src/arborlm supplements/p8s studies/p9 studies/p9i`, `uv run --locked pytest`, plus tests for M1 (a missing cell gives outcome INCOMPLETE and no classes) and M2 (G2 failed or a LEAKAGE flag gives NOT_INTERPRETED; a G1 failure is not ENGINEERING_FAIL). A short auditor re-check of those diffs suffices; nothing measured here needs to be repeated, because none of the fixes touches a model, the training or the calibration.

Astra review: NOT_PERFORMED. This audit is not human approval.
