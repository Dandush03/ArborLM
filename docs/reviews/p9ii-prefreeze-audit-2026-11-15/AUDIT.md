# P9-II pre-freeze audit (ADR-0019 revision 4) — 2026-11-15

- **Auditor:** Claude Opus 5.5 (model id `claude-opus-5-5`), the arbor-auditor role. I reviewed and confirmed the specification (`docs/reviews/adr-0019-design-2026-11-15/`). I did not write any of the code audited here.
- **Scope:** Part 1, the calibration; Part 2, the implementation (`studies/p9ii/`, launch scripts, config, tests, and the `studies/p9`/`studies/p9i` paths they import); Part 3, the rehearsal, budget and freeze plan.
- **Worktree:** `/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/arborlm-consolidation-experiment-2b31c1`, branch `claude/adr-0019-p9ii`, HEAD `b14bc9f`. No code has changed since the calibration commit `3d779e1`: `git diff --stat 3d779e1 HEAD` lists only files under `results/`. `core.code_identity()` at HEAD equals the identity in the calibration record (source `d58a5ce1…`, spec `dfd43ce7…`, config `d5c9fe0b…`).
- **Environment:** macOS-27.2.1-arm64, Python 3.12.14, torch 2.8.0, uv 0.12.15. Every command is `uv run --locked` (or `.venv/bin/python`) with `PYTHONPATH=.`, run from the worktree. Scratch output went to the session scratchpad. Diagnostic trainings ran single-threaded, with at most five processes at once.
- **Status:** independent engineering and mathematical evidence only. This is not Astra validation and not a human approval. **Astra review: NOT_PERFORMED.**

## Verdicts

| Part | Verdict |
|---|---|
| 1. Calibration | **CONFIRMED.** All 22 accuracies and all 22 final probe accuracies reproduce exactly from my own forward pass. The §6 rule reproduces λ = 1.0, U_pre = 2,048, k_0 = N/8 and μ = 1.0. Only the 22 calibration cells ran, on sets 3 and 4 with init seed 1891. **A2 and A4 are low by design, not because of an implementation defect.** |
| 2. Implementation | **READY AFTER the listed fixes** (M3–M6 in code; B1, M1, M2 and M7 in the freeze plan). Every arm, loss, schedule, class rule, gate and estimator I tested matches the ADR. |
| 3. Rehearsal, budget, freeze plan | **NOT READY.** The projection must be redone with the calibrated values and with per-task overhead. The memory 2× rule fails at 65,536 slots. Stage 2/3 caps need a rule per configuration. The freeze must be committed in the right order. |

Blocker: 1. Majors: 7. Minors: 15. Scientific questions marked **PENDING LEAD REVIEW**: 3.

---

## Part 1 — Calibration audit

### (a) Recomputing the §6 rule from raw records

Script `b2_rescore_calibration.py` writes `outputs/b2_rescore_calibration.{txt,json}` (my first attempt failed: no `PYTHONPATH`; kept as `outputs/b2_attempt1_failed_no_pythonpath.txt`).

`PYTHONPATH=. uv run --locked python docs/reviews/p9ii-prefreeze-audit-2026-11-15/b2_rescore_calibration.py <experiments>/P9IIC-…1a93c3de… <experiments>`

**How the check is independent.** I wrote the forward pass from the ADR text, not from `studies.p9ii` or `studies.p9i`:

- the backbone blocks;
- the W7 window of `h_{t−6..t}`;
- A5-C's `z − m`, using the snapshot's saved buffer;
- the top-8 cosine read at 0.2, with ties broken by lowest slot id;
- R1 oracle codes via splitmix/Box–Muller;
- D7;
- scoring against the alphabet, with ties counted wrong.

The data come from the audited P9 generator for rehearsal sets 3 and 4, restricted to contexts whose facts are all trained (`< 2,048`).

**Results.**

- Every snapshot's backbone equals the frozen backbone.
- The calibration stream has 4,096 trained sites per draw.
- The probe is 512 sites, each fact occurring exactly 2 times.
- max |accuracy(auditor) − recorded| = **0** over the 22 cells.
- max |probe accuracy at u8192 (auditor) − recorded| = **0**.

| Arm | Value | Draw 3 | Draw 4 | Min | Median first success | Decided by |
|---|---|---|---|---|---|---|
| A1 | 0.1 | 0.99878 | 0.99585 | 0.99585 | 2,752 | — |
| A1 | **1.0** | 0.99609 | 0.99609 | 0.99609 | **2,688** | secondary (difference 0.00024 < 0.02) |
| A2 | 1,024 | 0.03711 | 0.06445 | 0.03711 | ∞ | — |
| A2 | **2,048** | 0.12354 | 0.13135 | **0.12354** | ∞ | primary (difference 0.086) |
| A4 | **N/8** | 0.84839 | 0.52051 | **0.52051** | ∞ | primary (difference 0.398) |
| A4 | N | 0.12280 | 0.90259 | 0.12280 | ∞ | — |
| A5-D | 0.1 | 0.99976 | 0.99951 | 0.99951 | 2,752 | — |
| A5-D | **1.0** | 0.99951 | 0.99927 | 0.99927 | **2,464** | secondary (difference 0.00024) |

Pipeline check, draw 3 / draw 4:

| Arm | Draw 3 | Draw 4 |
|---|---|---|
| A0 | 0.39746 | 0.96436 |
| A6 | 1.0 | 1.0 |
| A7 | 0.99683 | 0.99927 |

**The success line for the secondary criterion** is 0.90 × A6's readout accuracy on the same calibration stream. That is 1.0 on both draws, so the line is 0.90. The selected values agree with `calibration.json`. Its sha256, `ad5d7ee29ccd3f0be8b9875afdd957f35901e0d80f4babca6917916d0cf552cf`, is identical in `results/` and in the run directory.

### (b) What ran

Read from the manifests and `train.json` of all 22 cells:

- The calibrate stage holds exactly the 22 cells of §6, and all 22 completed.
- Every cell has `mode` calibration, `seed_set` rehearsal-3 or rehearsal-4, `init_seed` 1891, `run_updates` 8,192, `trainable_backbone_parameters` 0, and one AdamW.
- The workers ran single-threaded with deterministic algorithms on.
- My training loop reproduces the trainer's per-update losses bit for bit (b4, below). That is a direct check of the alphabet loss, the answer-site-only read, AdamW (lr 0.003, wd 0) and the clip at 1.0.

**Where the calibration sets appear.** A grep of `experiments/` for `"rehearsal-3"` or `"rehearsal-4"` finds only the 22 calibration cells. No P9-II record names `p9ii-draw-*` or `p9ii-reserve-*` or carries a seed in 190001–191599. The gates and the rehearsal used only rehearsal-5.

### (c) A2 near chance despite A1 at 0.996: **DESIGN, not a defect**

Scripts and outputs:

- `b1_a2_trajectories.py` → `outputs/b1_a2_trajectories.txt`: per-64-update diagnostics and per-update logs of the calibration cells.
- `b3_a2_mechanism.py` → `outputs/b3_*`: diagnostic trainings, test seeds only.
- `b4_trainer_matches_loop.py` → `outputs/b4_trainer_matches_loop.txt`.

**End of stage 1: address pretraining succeeded completely.** On all four A2 cells, from update 256 to the switch:

- target top-1 recall 0.996–1.000 and top-8 recall 1.000;
- 256 distinct top-1 slots for 256 probe facts, largest share 0.0039;
- mean cosine between different facts' queries 0.02–0.03;
- mean target score 0.98;
- fact-independent share 0.03;
- L_addr 3.74–3.77, close to its floor of 4.09 nats at a query equal to its key. It is below that floor because τ_a sharpening also uses the spread of the other keys.

**First updates of stage 2: the queries collapse within 64 updates.** At the first diagnostics record after the switch:

| Measure | End of stage 1 | 64 updates later | 128 updates later |
|---|---|---|---|
| Distinct top-1 slots | 256 | 1–4 | |
| Largest top-1 share | 0.0039 | 0.40–1.00 | |
| Target top-1 recall | 1.0 | 0 | |
| Target top-8 recall | 1.0 | 0.02–0.10 | |
| Mean cosine between facts | 0.03 | 0.99 | |
| Fact-independent share | 0.03 | 0.96–0.97 | |
| Mean target score | 0.98 | −0.06 to −0.64 | −0.33 |

The still-logged L_addr climbs from 3.74 to 7.5–8.0 within 32–64 updates, then to 8.8–9.2, which is above ln 4,096 = 8.32.

Per update, the first phase-2 step moves:

- wq by 0.170, against 0.02–0.03 per update at the end of phase 1. The nominal full Adam step is lr·√3,584 = 0.18.
- keys by 0.30 and values by 0.47.

All this while the answer-loss gradient on wq is only 4.5–5.1 × 10⁻⁵ (wo: 4–5 × 10⁻⁴).

**Stage 2 never recovers.** The answer loss falls to 3.47–3.49 = ln 32 (the answer-symbol marginal) within about 1,000 updates and stays there. U_pre = 2,048 cells partly escape late: at 8,192, 115 distinct top-1 slots and accuracy 0.12–0.13.

**Mechanism test** (diagnostic, test seeds p9ii-test-5 and p9ii-test-6, my own loop). The implementer's `run_job` reproduces my registered-recipe loop bit for bit: identical losses at updates 1–3, 1,023–1,027, and identical probe records (b4). Phase-2 variants after the same phase 1:

| Variant | Phase-2 recipe | Accuracy at end | Target top-1 / top-8 at end |
|---|---|---|---|
| R (registered) | fresh AdamW on everything, answer only | test-5: 0.035 after 3,072 updates; test-6: 0.047 after 2,048 | 0 / 0.004–0.006 (collapsed within 64 updates) |
| F | wq and keys frozen | test-5: 0.914; test-6: 0.721 (still rising) | 1.0 / 1.0 |
| K | wq/keys keep their phase-1 Adam moments | test-5: 0.971 | 0.41 / 0.75 |
| S | wq/keys at lr 0.0003 | test-5: 0.967 | 0.80 / 0.98 |
| P | values/wo/gate alone for 256 updates, then everything (fresh AdamW) | test-5: 0.981 | 0.29 / 0.62 |

**Conclusion.** The code follows §4 to the letter, which I checked line by line and with c1:

- phase 1 trains only wq and keys, with L_addr only;
- values, wo and gate do not move;
- at U_pre + 1, L_addr is removed, everything becomes trainable, and AdamW is rebuilt (all moments zero, every counter 1, and my hand-computed first step agrees to 7.5 × 10⁻⁹).

The collapse is a property of the registered recipe. A fresh AdamW at full lr acts on wq and keys while the answer path is still at its random initialization. Adam normalizes the tiny but coherent answer-loss gradient into full-size steps that pull every query onto the same common mode, which is P9-I's collapse. Any one of three single changes avoids it.

**PENDING LEAD REVIEW (P1).** Variant K contradicts the ADR's stated reason for the reset ("the second moments … would hold the query projection and the keys nearly still"). Without the reset, the addresses did move (top-1 recall fell to 0.41), and the answers were learned. As registered, A2 is very likely to FAIL at Stage 1, and its H19-C reading will then speak about this recipe, not about staged optimization in general. §6 forbids any change after calibration, and §15 reserves changes of arms for the human lead. My recommendation: keep A2 unchanged and print, beside A2's class, that the registered recipe (moment reset with an untrained answer path) collapses in exploratory diagnostics, citing this audit as exploratory evidence. Alternatively, take the question to the human lead. This is the lead's decision, not mine.

**A4 at 0.52: DESIGN.** Checks in c1:

- k(t) matches the formula at every t for Stages 1 and 2.
- The wide read at k = 512, 181 and 23 equals my own softmax over the k best slots with a difference of 0.0.
- The read at k = 8 equals P9-I's top-8 bit for bit.

In the calibration logs, during the anneal (updates 1–4,095):

- distinct top-1 stays at 2–30 (collapsed by the slot rule);
- the soft mass outside the top 8 falls to 0.002–0.12 within about 512 updates (0.003 on draw 4 from update 128), because collapsed queries at τ = 0.2 concentrate the wide softmax.

Escape comes only after k reaches 8, on the same schedule as A0 (A0 on draw 4 escaped between 4,096 and 6,144). A4 at N/8 scored 0.848 / 0.521 against A0's 0.397 / 0.964. In short, half of A4's updates go to a wide read that does not prevent the collapse.

### (d) "Min Panel A accuracy" and the secondary criterion

- The code measures what §6 says: accuracy on each draw's **calibration stream**, restricted to trained facts (`evaluate.calibration_accuracy`), not Panel A.
- The calibration README says "minimum Panel A accuracy" (minor m1).
- The secondary criterion is implemented as R2 revised it: the median over the two draws of the first probe record at or above 0.90 × A6's readout accuracy, with "never" counted as +∞, then the first value listed.
- One corner case: median{finite, ∞} = ∞ ties with {∞, ∞} (m14). It did not matter here.

---

## Part 2 — Implementation audit

Commands, outputs in `outputs/`:

- `c1_arm_checks.py` (real size, test seeds p9ii-test-7). Two failed attempts are kept:
  - `c1_attempt1_failed_deepcopy_last_query.txt`: my `deepcopy` hit the trainer's non-leaf `last_query` (see m3).
  - `c1_attempt2_failed_argsort_signature.txt`: my own `argsort` call was wrong.
- `c1b_g6_recheck.py`. Re-run because of my own mistake: c1 flagged `addition.last_query` as a "fact-sized tensor" since 128 × 16 = 2,048 elements equals the number of facts. It is the batch's query. The c1 "FAIL" line for G6 is that false positive.
- `c2_classes_enumeration.py 20000 20261115`.
- `c3_synthetic_registry.py`.
- `c4_restoration.py` (p9ii-test-8).
- `c5_preconditions_clone.sh`, in a throw-away clone. The `exit: 0` lines it prints are the exit status of my pipe's `tail`, not of the driver. The refusal messages are the evidence.
- `uv run --locked pytest tests/test_p9ii_*.py -q`: **118 passed** (`outputs/e1_pytest_p9ii.txt`).

### Checked and found faithful

- **A0 is bit-identical to P9-I's W7** over 40 training updates: every loss and every parameter.
- **L_addr** is the mean over 128 sites of −log softmax over all 4,096 cosine scores at τ_a = 0.2. It matches a float64 reference within 1.4 × 10⁻⁷. Its gradients reach wq and keys only (all 4,096 key rows; values, wo and gate get none) and equal autograd of my own formula.
- **A1** total = answer + λ·L_addr. The injection equals `randperm(N, base+40)[:F]`.
- **A1-S** targets do not change when the fact ids change, do change with the update, and are unrelated to the injection. The same fact got the same target in 7 of 23,552 repeats (0.0003 ≈ 1/N).
- **A2**: see Part 1(c).
- **A4**: see Part 1(c). The first update reads k_0, and update T_A + 1 is the first at k = 8. After every step the model is reset to k = 8, so the probes and evaluation always read top-8.
- **A5-C**:
  - m = mean of z over the first 16 training batches (2,048 sites);
  - after each step, m ← 0.99 m + 0.01 × (batch mean of z with pre-step parameters);
  - m is a buffer with no gradient, is unchanged by an evaluation forward, and is restored from checkpoints;
  - the selection uses (z − m)/|z − m|.
- **A5-D**: L_div = log mean_{i≠j} exp(2 q_i·q_j) over the 128 un-centred unit queries. It matches within 4 × 10⁻⁸, and the total is answer + μ·L_div.
- **A6 and A7** reproduce exactly in the rescoring (Part 1).
- **No backbone parameter is trainable.** G5 holds (gates record, plus 118 tests).
- **G6: I tried to break it and could not.** After training A1, A1-S, A2, A5-D, A5-C and A4 for 20 updates, I replaced the trainer's injection and scrambled the data's fact-answer table. The logits on fixed tokens did not change. A model rebuilt from its `state_dict` alone gives identical logits. No module holds a fact table; the only tensor attribute is the 128 × 16 batch query.
- **Schedules scale with exposures per fact.**
  - A2's U_pre goes from 2,048 at Stage 1 to 8,192 at Stage 2; A4's T_A from 4,096 to 16,384; k_0 from 512 to 2,048.
  - Exposures per fact are 512 at Stage 1 U, 128 at Stage 2 U, 512 at Stage 2 4U and 32 at Stage 3.
  - A scheduled arm is refused at Stage 3.
  - At Stage 2 U, A2 and A4 are printed MID-SCHEDULE and enter no rule (synthetic S13).
- **Probe.** 256 facts × 2 occurrences, all trained facts. None of its contexts appears in the 8,192 training batches (131,072 contexts hashed) or in Panel A. It runs with no gradient. It rebuilds exactly in my rescoring.
- **Determinism and checkpoint restoration at real size**, straddling A2's switch (split 64, U_pre 96), A4's schedule (T_A 128) and a diagnostics record. Every learned arm is bit-identical on 53–55 tensors (parameters, buffers, optimizer state, anchors), and the diagnostics after the split are identical except for timing. Two identical runs of A5-C, A1-S and A4 are bit-identical.
- **Class rules, enumerated independently** (c2, 20,000 random Stage 1/Stage 2 tables with not-evaluated draws, LM flags and correlated arms). My implementation of §8.3–§8.6 from the ADR text agrees with `classes.py` on every table: zero mismatches over the cell verdict (20,000 random observations), arm class and the UNRELIABLE (LM CAPABILITY REDUCED) label, the paired rule, the negative control, the Stage 1 gate (R5 skip, at most two, preference order), the Stage 3 gate (constant objective, SCHEDULED ARM), outcome rows 2–8 (all hit; row 8 eight times), hypothesis readings B–G and carry-forward.
- **Estimators.**
  - Clopper–Pearson lower bound 8/8 = 0.6877 = 0.05^{1/8}; 7/8 = 0.5293; 4/4 = 0.4729.
  - The exact permutation test equals brute force on 300 random tables.
  - The sign test matches.
- **Seeds.** `core.assert_namespaces_disjoint` runs at import. My grep of `experiments/` confirms no registered or reserve seed appears anywhere, and that sets 3 and 4 appear only in calibration.
- **Ledgers and the 2× rule** are pure functions (tests, plus my recomputation in Part 3).
- **Registered-mode preconditions in a throw-away clone** (c5). The accept path works: a clean tree with freeze = HEAD → plan → calibration and projection hash binding → stage-1 gate on an empty run dir → `NOT RUN — STAGE NOT INTERPRETABLE`, with nothing trained and no ledger charged. It refuses each of:
  - an untracked file;
  - a non-commit;
  - a missing freeze commit;
  - a committed code change after the freeze;
  - a calibration record that does not hash to the plan;
  - a launch script called with one argument;
  - registered generation without the freeze-time flag;
  - `--dry` together with registered mode.
- **Launch scripts.** Every expansion is quoted, the run dir is made absolute, and there is no `eval` and no word splitting. Each calls `stages registered <name>` with `--caps studies/p9ii/freeze/stage_caps.json`.
- **Rehearsal whitelist.** The rehearsal run dir holds only `rehearsal.json` and `rehearsal_evaluate.json` (30 each), the logs and the projection. Every key is on the whitelist. The only loss-like key is the boolean `loss_finite`. There are no snapshots.
- **Manifests record platform, threads and versions.**
- **Failed cells, failed gates, non-finite values and missing cells**: see the synthetic results below.

### The implementer's 13 readings

| # | Reading | Judgement |
|---|---|---|
| 1 | Probe stream restricted to the cell's trained facts | Consistent with "the first 256 trained facts" (§8.1). Reproduced exactly. Hardening in m13. |
| 2 | A4's t counts updates already taken | Consistent ("t < T_A … from T_A on"): T_A updates at the wide read. |
| 3 | A5-C's centre committed after the optimizer step | Consistent: an EMA of batch means, no gradient, one update per step (checked numerically). |
| 4 | A6 reference per panel; a draw is NOT_EVALUATED if A6 < 0.90 on either panel | Consistent. |
| 5 | Condition 4 against both panels | Consistent with "conditions 1, 2 and 4 on both Panels A and B" (the stricter reading). |
| 6 | ADDRESS RECALL = the smaller panel recall, then the median | Acceptable (descriptive, conservative). |
| 7 | A1-S recall against the cell's injection | Acceptable: a chance-level reference. It enters no rule (ADDRESS RECALL is for A1 and A2 only). |
| 8 | DENSE COMPARISON uses the per-draw mean | Acceptable. |
| 9 | Stage status NOT_EVALUATED ⇔ A0's class is NOT_EVALUATED | Acceptable: every arm shares the draws and A6, and arm-specific missing cells fall under row 1. |
| 10 | Permutation test | Correct (equals brute force). |
| 11 | Redundancy in the paired rule | Confirmed: on the paired cells, d = successes(X) − successes(A0), so "more successes" is implied by d ≥ 4. |
| 12 | DRY data | Not registered, not used for any rule. Fine. |
| 13 | `freeze/stage_caps.json` and `plan.json` absent by design | Accepted. Their content is specified in Part 3. |

### Synthetic records of the full registry (c3)

Each scenario writes on-disk records with the registered labels and U = 8,192, then runs `work analyze` and `work report`.

| Scenario | Expected from the ADR | Observed |
|---|---|---|
| S1: A5-C RELIABLE and improves on A0; Stage 2 and Stage 3 run | row 4; Stage 3 POSITIVE | row 4 A5-C (LABEL-FREE); ALSO AT MATCHED UPDATES; SCALE PROBE POSITIVE; H19-F supported ✓ |
| S2: answer-only reliable | row 3; readings at 16,384 | row 3; readings at 16,384 ✓ |
| S3: negative control failed | row 2 INCONCLUSIVE | ✓ |
| S4: nothing reliable / S4b: all fail | rows 7 / 8 | ✓ / ✓ |
| S5: one NOT_EVALUATED draw | classes from 14 cells | ✓ (Stage 3 status, see m5) |
| S5b: two NOT_EVALUATED draws | row 2 | ✓ |
| S6: missing cell | NOT_INTERPRETED (INCOMPLETE), no class | ✓ |
| S7: G2 failed / S7b: G4 defect | NOT_INTERPRETED with descriptive outcome / ENGINEERING_FAIL | ✓ / ✓ |
| S8: non-finite values | NaN fails, +inf flagged, analysis completes | ✓ |
| S9: Stage 2 NOT RUN — BUDGET | Stage 2 and Stage 3 NOT RUN — BUDGET | Stage 3 printed NOT RUN — NO ARM PASSED (**m5**) |
| S10: row 3 with Stage 2 not run | B–G cannot be read at 16,384 | B, C, D, G printed **CONTRADICTED**, read at 4,096 (**M6**) |
| S11: a draw replaced after a G1 failure (generate manifest with a failed task) | complete, as S1 | **NOT_INTERPRETED (INCOMPLETE)** (**M5**) |
| S12: Stage 2 INCOMPLETE | row 6, nothing carried | row 6, but **A5-C carried forward** (**M6**) |
| S13: A2 RELIABLE at 16,384 | Stage 3 NOT RUN — SCHEDULED ARM; MID-SCHEDULE | ✓ |

### Paths not exercised at real size

These were exercised only by the DRY or unit tests, or not at all:

- registered generation and G1 of the 16 draws, and the draw plan on real G1 results;
- registered gates on draw 1;
- a full Stage 2 cell: 32,768 updates at 16,384 slots, the U snapshot inside a 4U run, two readouts, 512 diagnostics records;
- A4 at 16,384 with k_0 = 2,048, and A2 at 16,384 with U_pre = 8,192;
- any Stage 3 cell (65,536) beyond 256 rehearsal updates plus one evaluation;
- the Stage 1 gate and Stage 3 gate on real records;
- every Budget B charge, a `LedgerRefused` in sequence, and a stage stopped at its cap;
- six concurrent 65,536-slot evaluations;
- analysis and report on real records;
- reserve substitution in a real run dir.

---

## Findings

### BLOCKER

**B1 (freeze plan/budget). The evaluation caps leave no headroom because the projection omits per-task process overhead.**

- The rehearsal's `evaluation_wall_seconds` times `evaluate_readout` inside a process that has already started, built its data and loaded the backbone.
- A registered evaluation task is a fresh process per cell. Measured in the rehearse and calibrate manifests as task seconds minus the timed parts, the overhead is **1.8–2.3 s per task** with six workers (`outputs/d1…`, the overhead table in the rehearsal manifest; `d2_task_overhead.py`: 1.0 s unloaded). That is as large as the measured 4,096-slot evaluation itself (2.1–2.5 s).
- Stage 1 evaluation: projected 49.9 s, so the cap is 99.7 s. Expected: 22 rounds × about 4.5 s ≈ 99 s.
- An evaluation stage stopped at its cap is INCOMPLETE, which makes the study NOT_INTERPRETED.

Fix, paste-ready, in `stages.finalize_rehearsal`:

```python
m = core.read_record(run_dir / "rehearse" / "manifest.json", "stage_manifest")
task = {t["label"]: float(t["seconds"]) for t in m["tasks"]}
# for each item: overhead = task[item_label] - train["wall_seconds"] - eval["evaluation_wall_seconds"]
# budget: cell_training_seconds += overhead; cell_evaluation_seconds = readouts * evaluation_seconds + overhead
```

Then derive every cap from these projections.

### MAJOR

**M1 (freeze plan). The projection uses the rehearsed worst-case values, not the calibrated ones.**

- `projection.json` has `hyper` = {k0_fraction 1.0, u_pre 1,024}. The calibrated matrix's A4 phases were never rehearsed: k_0 = 2,048 with mid 128 at 16,384, and k_0 = 512 with mid 64 at 4,096. The rehearsed phases were k_0 = 16,384 with mid 362.
- With the measured k_0 = N rate as a bound, every A4 Stage 2 configuration fails 2× within 10,800 s (11,436–14,457 s), so Stage 2 would be NOT RUN — BUDGET whenever A4 advances, on a bound that does not describe the registered arm.
- The rate cannot be extrapolated: 0.060 s at k = 362 against 0.137 s at k = 16,384, which is not linear in k.
- Stage 2 fits if A4's annealing rate at 16,384 is at most: 0.127 (A4 alone), 0.105 (A5-C or A5-D + A4), 0.085 (A4 + A2), 0.081 (A4 + A1) s/update.
- Separately, `cmd_registered` recomputes the Stage 1 decision with the calibrated values but reads the Stage 2/3 tables computed with the worst-case values, which is inconsistent.

Fix: re-run the rehearsal before the freeze with the calibration record. That is time and memory only, on set 5, about 90 s of Budget A:

```
uv run --locked python -m studies.p9ii.stages rehearse --calibration <experiments>/P9IIC-…/calibration.json --stage-cap-seconds 3600
```

Then, in `finalize_rehearsal` and in `cmd_registered`, refuse when `projection["hyper"] != calibration["hyper"]`. Under the ADR's order of work (calibration, then rehearsal), this re-run is not a change after calibration.

**M2 (freeze plan). The 2× memory headroom ignores the evaluation peaks and fails at 65,536 slots.**

- `budget.memory_headroom` reads only the training peaks (0.73 GiB) and reports ok.
- The recorded evaluation peaks are higher. In `rehearsal_evaluate.json` and the pool's task peaks, A0 at 65,536 reaches **1.529 GiB, and 2× = 3.06 GiB > 3 GiB** per worker. A1 and A5-D reach 1.513, A5-C 1.488, A6 1.417.
- At 16,384 the maximum is 1.444 GiB (2× = 2.89 GiB, which passes). At 4,096 it is lower.
- Aggregate: 6 × 1.53 × 2 = 18.4 GiB ≤ 24, which passes.

Fix: `memory_headroom` takes `max(train peak, sampled, evaluation peak, pool task peak)` per size and reports per stage. **PENDING LEAD REVIEW (P2):** whether Stage 3 may run, given that its evaluation fails the 2× rule by 2%.

**M3 (code, `stages.cmd_registered`). Stage 2 and Stage 3 caps are single numbers.**

- The caps come from `stage_caps.json` as one value per stage, but §10 makes each stage's cap twice the projection of the configuration the gate selected.
- One fixed number either exceeds Budget B, so `LedgerRefused` fires even when the gate says run (for example, 2 × 7,176 s of training for A4 + A1), or sits below the larger configurations, so the stage is stopped at its cap and becomes INCOMPLETE.

Fix:

```python
if stage in (2, 3):
    gate = core.read_record(run_dir / ("stage_gate_1.json" if stage == 2 else "stage_gate_3.json"), "stage_gate")
    proj = core.read_record(Path(args.projection), "projection")
    row = proj["stage2_table"][budget.config_key(gate["advancing"])] if stage == 2 else proj["stage3_table"][gate["selected"]]
    cap_train, cap_eval = 2 * row["training_seconds"], 2 * row["evaluation_seconds"]
```

**M4 (code). The per-draw gates are not enforced at training time.**

- (a) Registered `train` and `evaluate` never check the draw's G1 result or the draw plan's `ok`. `seeds_named` reads `seed_set_of` even when `ok` is False, and without `draw_plan.json` it silently uses unreplaced registered draws.
- (b) G2 is computed only on the gates draw (draw 1), though §9 makes it per draw and size.
- (c) `gates.json` carries draw 1's G1 only.

Fix:

- In `run_cells_stage` (registered), require `draw_plan.json` with `ok` true, and `g1_passed` true in the data manifest of every seed set the stage uses.
- In registered `seeds_named`, refuse when there is no plan.
- Have the gates stage loop over the draw plan, compute `controls_record` (G2) for each draw, and record `g2_by_draw`.
- In `assess`, return NOT_INTERPRETED if any G2 failed.

**M5 (code, `stages.work_analyze`). A legitimate reserve substitution makes the study NOT_INTERPRETED.**

- When G1 fails, `work_generate` exits 1, and the pool records the task as failed in `run_dir/generate-<name>/manifest.json`.
- `work_analyze` counts failed tasks from every manifest, so the study comes out NOT_INTERPRETED (INCOMPLETE). Synthetic S11 confirms this.
- The ADR expects a substitution in about 13% of runs.

Fix:

```python
failed = sorted(f"{m['stage']}:{t['label']}" for m in manifests for t in m["tasks"]
                if t["status"] != "completed" and not str(m["stage"]).startswith("generate-"))
```

G1 is then governed by the draw plan, through M4.

**M6 (code, `analysis.analyze_study`). Stage-2-dependent readings are computed from a Stage 2 that is not COMPLETE.**

- In row 3 with Stage 2 not run, H19-B to H19-G are read at 4,096 and printed CONTRADICTED (S10). The ADR reads them at 16,384 in row 3, where nothing exists.
- With Stage 2 INCOMPLETE, the readings and the carried-forward interface come from the incomplete stage (S12).

Fix:

```python
s2_complete = r2 is not None and s2status == C.COMPLETE
readings = C.hypothesis_readings(r1.size, r1.details["h19a_inputs"], reading_stage=r2.size if (outcome.row == 3 and s2_complete) else None)
if outcome.row == 3 and not s2_complete:
    for k in ("H19-B", "H19-C", "H19-D", "H19-F", "H19-G"):
        readings[k] = {"reading": f"not read (Stage 2 {s2status})"}
carried = C.carry_forward(r2.size) if s2_complete else None
```

**M7 (freeze plan). The freeze must be committed in the right order.**

- `check_preconditions` refuses unless `studies/`, the config, the ADR and `tests/test_p9ii_*` at HEAD equal the freeze commit.
- So the §16 freeze record, including the data identities, must be inside the freeze commit. Edit the ADR after it and every registered stage refuses.
- Order:
  1. Apply the fixes and pass this audit's re-check.
  2. Re-run the rehearsal with the calibration record.
  3. Generate and G1-check the 16 draws, then build the draw plan, into the registered run dir. This needs no model, and the generate manifests record the code identity, which must equal the frozen code.
  4. Write `plan.json`, `stage_caps.json` and the §16 freeze record.
  5. Make one freeze commit.
  6. Launch `gates.sh` with that commit.

### minor

- **m1.** The calibration README says "minimum Panel A accuracy"; the rule and the code use the calibration stream (§6). It also says "A4 reaches at most about half", but A4 reached 0.848 (draw 3, N/8) and 0.903 (draw 4, N); 0.521 is the minimum.
- **m2.** The rehearsal ran after calibration without the calibration record (procedural). Folded into M1.
- **m3.** `Trainer.compute_losses` leaves `IIMemory.last_query` with its autograd graph between updates. That holds a batch graph and blocks `deepcopy`; numbers are unaffected. Fix: `iimemory.last_query = None` after the auxiliary loss is formed. Optional: it touches training code (see P3).
- **m4.** The G6 gate varies only `r1_seed`. The fact tables it is "offered" are ignored, and the injection is never involved. Strengthen it as in c1b: train, then change the injection and a fact table. The property holds.
- **m5.** When Stage 2 is NOT RUN — BUDGET, Stage 3 prints "NOT RUN — NO ARM PASSED" (S5, S8, S9); §10 says NOT RUN — BUDGET. Separately, "NOT RUN — STAGE NOT INTERPRETABLE" is not an ADR status. Fix: `s3_not_run = s2_not_run` when Stage 2 did not run, and INCOMPLETE when the Stage 3 gate refused for missing cells.
- **m6.** `work_analyze` labels a Stage 2 that the gate allowed but whose manifest is missing as NOT RUN — BUDGET. That is a guess; the reason should be read from the ledger refusal.
- **m7.** `RESULTS.md` omits labels §8.4 and §8.5 say are printed: NEGATIVE CONTROL FAILED, SUPERVISION-DEPENDENT, ADDRESS RECALL/STABLE, the four category counts, SCALE PROBE, MID-SCHEDULE / ALSO AT MATCHED UPDATES, d(A2 vs A1), and A6's r. They are in `results.json` only. Two different "median escape update" values are printed under one name: escaped cells only in the class table, censored cells in `draw_sensitivity`.
- **m8.** The §8.2 cost items are not recorded: CPU seconds (only wall time is), active retrieval work per query (except A4's `read_k`), analytical FLOPs, and separate CPU seconds for L_addr, top-k(t) and L_div. They can be derived after the run from rehearsal rate differences (A1 − A0, A5-D − A0, A4 phases − k8). Let the report do it.
- **m9.** SUPERVISION-DEPENDENT's "more than half of the cells" counts cells on NOT_EVALUATED draws in the denominator.
- **m10.** The `evaluate.lm_flagged` docstring says a non-finite A6 rise is NOT_INTERPRETED by the analysis; the analysis does no such thing.
- **m11.** The launch scripts take two free arguments (run dir, freeze commit), though §9 says "no free arguments". Both are guarded by the preconditions (c5). Generation (16 typed commands) and the draw plan have no fixed script; add one.
- **m12.** The caps live in two places: `plan["caps"]` and `stage_caps.json` (the launch scripts use the file). Keep one, or assert equality.
- **m13.** `build_probe` would admit unseen-control facts if an all-unseen context came first (`restrict_stream` keeps such contexts). The calibration streams I checked have 0 unseen rows, so there is no effect. Hardening: `if value < facts`.
- **m14.** Calibration tie rule: median{finite, ∞} = ∞ ties with {∞, ∞}. No effect here.
- **m15.** For A2, `train.json`'s `trainable_parameters` and `parameters_by_group` report the phase-1 set; `trainable_parameters_by_phase` gives both. Label it.

### PENDING LEAD REVIEW

- **P1.** A2's registered recipe collapses at the switch (Part 1c).
- **P2.** The Stage 3 memory headroom (M2).
- **P3.** Whether the engineering fixes (M3–M6, B1/M1/M2 in `budget.py`, `stages.py` and `analysis.py`) count as "changes after calibration" under condition 4. None of them touches `model.py`, `train.py`, `diagnostics.py`, `evaluate.py` or the training constants in `core.py`. I recommend that the freeze record list per-file sha256 values showing those files unchanged since `3d779e1`, so the calibration provably binds the code that trains and scores the cells.

---

## Part 3 — Rehearsal, budget and freeze plan

### Recomputed projections

`d1_projection_recompute.py` uses plain json, no `studies` import. Output: `outputs/d1_projection_recompute.txt`.

**Reproducing `projection.json`.** With the rehearsed values, every number matches:

- Stage 1: 2,029.2 s (training 1,979.3 s, evaluation 49.9 s). Doubled, 4,058.4 s against 13,970.2 s remaining in Budget A (429.8 s charged). Fits.
- Stage 2:

| Configuration | Projected | Doubled | Fits 10,800 s |
|---|---|---|---|
| A0 only | 1,133.7 s | 2,267 s | yes |
| A5-C | 1,652.0 s | | yes |
| A5-D | 1,663.5 s | | yes |
| A2 | 2,810.9 s | | yes |
| A1 | 2,937.8 s | | yes |
| A5-C + A5-D | 2,380.3 s | | yes |
| A5-C + A2 / A5-D + A2 | 3,228.8 / 3,237.1 s | | yes |
| A5-C + A1 / A5-D + A1 | 3,355.6 / 3,364.0 s | | yes |
| A2 + A1 | 3,446.2 s | 6,892 s | yes |
| A4 | 5,718.2 s | 11,436 s | **no** |
| A5-C + A4 / A5-D + A4 | 6,435.0 / 6,441.6 s | | **no** |
| A4 + A2 | 7,120.8 s | | **no** |
| A4 + A1 | 7,228.6 s | 14,457 s | **no** |

- Stage 3: 308.6 s (A0), 499.5 s (A5-C, A5-D) and 705.0 s (A1), out of what Stage 2 leaves.

**With the calibrated values**, A4 is bounded by the k_0 = N rate. Stage 1 is 2,025.1 s. Every A4 configuration is unchanged and still does not fit. A2's configurations fall by about 3 s.

**Is the worst case acceptable as an upper estimate?**

- For Stage 1, yes: twice the bound fits with a wide margin.
- For Stage 2, no. The bound decides NOT RUN — BUDGET for every A4 configuration, and that decision would rest on a phase the registered arm never runs.
- The ADR defines the rehearsal as "every distinct (arm, size, phase) of the matrix". After calibration, the matrix's A4 phases are k_0 = N/8 and mid = √(8·N/8). The fixed rule is to re-run the rehearsal with the calibration record (M1), with the projection that includes per-task overhead (B1). Do not extrapolate.

### `studies/p9ii/freeze/stage_caps.json`

Produced by a pure function of the re-run projection.

| Key | Value | Rule |
|---|---|---|
| `gates` | 2 × the measured gates stage wall | 7.95 s on rehearsal set 5; floor about 60 s, stated as such |
| `stage1.train` / `stage1.evaluate` | 2 × the overhead-inclusive projections | Doubled training and evaluation of the overhead-inclusive Stage 1 projection |
| Stage 2 and Stage 3 | no fixed number | Per configuration, read by the driver from the stage gate record (M3) |
| `analysis` / `report` | 2 × a measured time | Not rehearsed at real size. Time `work analyze` + `work report` on the synthetic full registry (as in c3) and record 2 × that, with a stated floor |

### `studies/p9ii/freeze/plan.json`

- `calibration`: {path `<experiments>/P9IIC-20261115T071159540788Z-1a93c3ded92e40628c2abb9bd4235188/calibration.json`, sha256 `ad5d7ee29ccd3f0be8b9875afdd957f35901e0d80f4babca6917916d0cf552cf`}.
- `projection`: {the re-run rehearsal's `projection.json`, its sha256}. Its `hyper` must equal the calibration's.
- Recommended additions:
  - `run_dir`, the registered run directory;
  - `draw_plan`, with path and sha256;
  - `data_manifests`, the sha256 of each of the 16 `data_manifest.json`;
  - `caps`, equal to `stage_caps.json` or removed (m12).

### The freeze record in ADR §16 (inside the freeze commit, M7)

1. **Code.** The freeze commit is the commit that contains the record; launch passes its hash.
   - `source_sha256`, `config_sha256`, `frozen_source_sha256`.
   - Per-file sha256 of `studies/p9ii/*.py`, the launch scripts and the imported `studies/p9`/`studies/p9i` modules.
   - An explicit statement of which files changed since the calibration commit `3d779e1` (P3).
2. **Calibration.** Record sha256 `ad5d7ee2…cf552cf`. Selected values λ = 1.0, U_pre = 2,048, k_0/N = 1/8, μ = 1.0. Run dir. This audit's CONFIRMED verdict.
3. **Data identities.** All 14 registered and 2 reserve draws are generated and G1-checked at freeze time, as §9 and §12 step 6 require and as P9-I did. For each: seed-set name, base seed, `data_manifest.json` sha256 and stream hashes, G1 pass/fail. Then the draw plan with any replacement, `ok` true.
4. **Gates on rehearsal seeds.** `experiments/P9IIG-rehearsal-gates-20261115T071128Z`: G1, G2, G4, G5 and G6 passed, no G4 defect. The registered gates (`gates.sh`) run first on registered draw 1, plus G2 per draw (M4).
5. **Stage caps and projections.** The re-run projection path and sha256; every cap with its rule; the Stage 2 table and Stage 3 table; memory headroom per size (M2); Budget A charged so far, Budget B 0.
6. **Launch commands.** The exact eight invocations, `sh studies/p9ii/launch/<stage>.sh <registered-run-dir> <freeze-commit>`, in the order gates, stage1, stage1_gate, stage2, stage3_gate, stage3, analysis, report. Also the one-time generation and draw-plan commands that were used.
7. **The lead's five conditions,** each with its evidence, as below.
8. **Environment and status lines.** "Astra review: NOT_PERFORMED", and the delegation wording.

### The lead's conditions, today

| Condition | Holds? |
|---|---|
| The audits end with no open blocker or major | **No.** B1 and M1–M7 are open. A re-check is needed after the fixes. |
| The rehearsal shows 2× headroom | **Not yet.** Time: Stage 1 yes. Stage 2 yes for every configuration without A4; A4 configurations unknown until the calibrated rehearsal (M1). The evaluation caps have no real headroom (B1). Memory: fails at 65,536 slots (1.53 GiB × 2 > 3 GiB, M2). |
| Nothing changed after calibration except the calibrated values | **Holds so far.** No file changed since `3d779e1`, and the identity equals the calibration's. The required fixes change non-training code (P3, the lead's decision). |
| No registered seed has been observed | **Holds.** No registered or reserve set has been generated, and none appears in `experiments/` or in any P9-II record. |

## Numbers recomputed

| What | Where |
|---|---|
| 22 calibration accuracies and 22 probe accuracies (exact); the §6 selections | b2 |
| A2 trajectories (end of stage 1; first updates of stage 2; per-update movements) | b1 |
| Diagnostic variants R/F/K/S/P on test draws; the trainer equals my loop bit for bit | b3, b4 |
| L_addr / L_div values and gradients; A4 reads; A5-C EMA; the A2 first-step formula | c1 |
| 20,000-table rule enumeration; Clopper–Pearson bounds; permutation and sign tests | c2 |
| Every Stage 1/2/3 projection in `projection.json` (exact) and the calibrated-value bounds | d1 |
| Per-task overhead (1.8–2.3 s) and evaluation memory peaks (1.529 GiB) | d1, d2 |

## What I did not do

- I ran no registered stage, generated no registered or reserve data, and trained or evaluated on no rehearsal set 3, 4 or 5. Diagnostic trainings used only P9-II test seeds (910501+, 910601+, 910701+, 910801+, 910901+).
- I edited no existing file and made no commit.
- I did not run the full repository test suite, only `tests/test_p9ii_*.py` (118 passed).
- I did not run the DRY stage.
