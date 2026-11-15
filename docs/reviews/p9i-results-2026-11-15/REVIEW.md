# P9-I registered run (attempt 2): independent recomputation and review

- **Reviewer:** Claude Opus 5.5 (model id `claude-opus-5-5`), acting as auditor, launched by the lead session. Independent engineering and mathematical evidence only. **Astra review: NOT_PERFORMED. This is not Astra validation and not human approval.**
- **Scope:** ADR-0017 §18 (Part I), §15.3–§15.8. Run `experiments/P9IP-20261115T020303574595Z-674730f6b8a147c0a47cac404321f2df` (attempt 2, freeze `dd39aa6`, code `8261f22`, U = 8,192); committed copies `results/p9i-run-attempt2-2026-11-15/`. Worktree HEAD `a1b4b39`, branch `claude/adr-0017-design`.
- **Environment:** macOS 27.2.1 arm64 (18 cores), Python 3.12.14, torch 2.8.0, `uv run --locked` (no lock change). Scripts and outputs in this folder; `uv run --locked ruff check .` passes.
- **What ran:** record recomputation (s1, s2), independent re-scoring of all 57 registered snapshots (s3), training-log summary (r2), snapshot diagnostics (d3), a gradient check against my own forward at init and at registered snapshots (d5), and **diagnostic trainings on rehearsal draws 0 and 2 and on the unit-test seed sets p9i-test-0/1/2 only** (d1, d2, d4). The diagnostics used no registered data seed, no registered init seed, and re-ran no registered cell. They are **diagnostics, not results**.
- **What did not run:** no registered-seed training, no registered stage, no edit to any existing file, no commit.

## 1. Recomputation: verdict

**No difference in any count, class, annotation or the selection outcome.** Float-level differences only (listed).

| Check | Script / output | Result |
|---|---|---|
| Matrix: 57 cells = §I.7 | s1 | exactly the 57 registered cells |
| Every cell: status completed, mode registered, seed set `p9i-registered`, init seed = cell seed ∈ {1801, 1802}, `matched_updates = run_updates = 8192`, examples 16 × 8,192, 128·8192/F exposures per fact (min = max), one snapshot (u0008192), one eval, 8,192 lines in `updates.jsonl` with indices 1..8,192, finite losses, snapshot `model.pt` hash = `train.json`, committed eval copy byte-identical | s1, r2 | all hold for 57/57 |
| Code identity | s1 | one identity in all 114 train/eval records: source `6407936e…`, spec `db64b68a…` (= ADR at `dd39aa6`), config `7cc20791…` |
| Calibration binding | s1 | `calibration_binding.json`: sha `087bf0b5…` (= file hash), U = 8,192, no failed size; repeated in every train and eval record |
| Data manifest | s1, s3 | sha `e1bec1e3…` (attempt 1 `8d73e555…`); the **fourteen** data hashes identical to attempt 1; every non-identity field identical; `g1.json` byte-identical. Only `identity.source_sha256` and `identity.spec_sha256` differ: generation ran before the freeze commit, so the spec hash is the pre-freeze ADR (`2798a8db…` = ADR at `8261f22`/`c53acaa`). I **regenerated the registered data** from the manifest's seeds (182001–182020) and obtained the same fourteen hashes |
| G2 intervals | s1 (own exact binomial, level 1 − 0.001/8) | [36, 96], [198, 318], [905, 1147] for 2,048 / 8,192 / 32,768 facts — equal to the records; all 8 G2 tests inside; B102 no-memory counts (reported only) also inside |
| C4–C8 (attempt-2 vs attempt-1 gates) | s2 | the lead's comparison output is not in the committed folder; my own check: `g2`, `controls`, `restoration` blocks identical; restoration `model.pt`/`optimizer.pt`/`movement.pt` (N, BB) byte-identical, only `train.json` differs (identity/wall time); attempt 2: G4 passed, no defect, 12 arms reached with the attempt-1 trainable counts |
| Accuracies, unseen, disabled, permuted, distinct slots, share of nearest query > 0.9 | s3 (own forward, all 57 snapshots, both panels) | **every integer count equal to the record**; mean query cosine differs by ≤ 8.8e-9; next-byte losses by ≤ 1.8e-7 nats |
| η, raw classes, class at size, B102 rule, MODEL_STORES_FACTS, LEAKAGE | s1 | equal to `classes.csv` / `analysis.json` for all 14 arm–size pairs; no LEAKAGE in any cell or panel |
| Annotations | s1 | dense comparison NOT COMPARED wherever both cells exist (W7/D7 16,384 and 65,536; BB/BB-D 16,384 and 65,536), none at 4,096 (no D7 or BB-D cell); backbone contrast not printed (both pairs FAILS); LANGUAGE MODELLING DEGRADED for BB at every size |
| Selection | s1 | **NO_INTERFACE_SELECTED (step 4)**; no size NOT_EVALUATED (R1 ≥ 0.967 everywhere) |
| Ledger | s1 | 12 entries, 2,691.0 s of 14,400 s; attempt 2: generate 11.9, gates 5.9, train 1,609.1, evaluate 97.9, analyze 0.6, report 0.6 s; each stage once, each under its cap |

Key numbers (Panel A / B; seeds 1801, 1802 unless named):

- R1: 4,096 1.0000 all four; 16,384 0.9995/0.9996, 0.9993/0.9996, B102 0.9998/0.9998; 65,536 0.9674/0.9677, 0.9714/0.9720. R2 (16,384) 1.0000.
- N, W7, E7, A4, A4E: inside the G2 interval in every cell and panel (0.0278–0.0439). Most B101 cells of W7, E7, A4 and A4E at 16,384 and 65,536 (and N 65,536 seed 1801) score exactly 230/8,192 or 990/32,768 on both panels and on H1/H2/mixed: a constant prediction.
- BB 4,096: 0.5566/0.5435, 0.6489/0.6494 → η 0.54–0.65; PARTIAL. BB 16,384: 0.0447/0.0457, 0.0448/0.0441, B102 0.0508/0.0486; BB 65,536: 0.0335/0.0342, 0.0335/0.0343.
- BB-0: 4,096 0.0889/0.0835; 16,384 0.0441/0.0446; 65,536 0.0338/0.0333.
- D7: 16,384 0.7867/0.7828, 0.7976/0.8021, B102 0.4393/0.4412; 65,536 0.1306/0.1300, 0.1271/0.1278. D plain 0.0356.

Corrections to the lead's (unverified) reading: (a) distinct slots at 16,384 range **9–232**, not 10–232 (A4E seed 1802, Panel A: 9). (b) D7 B101 at 16,384 is 0.78–0.80 (seed 1801 Panel B 0.7828). (c) BB at 4,096 is 0.54–0.65 (seed 1801 Panel B 0.5435). (d) **BB at 16,384 is not "chance" in the sense of the rules**: 361–374 of 8,192 (B102 398–416) lies *above* the G2 interval [198, 318]; it is FAILS only because it is below 0.25. BB-0 and BB-D at 16,384 are also above the interval. At 65,536 BB is inside the interval.

## 2. Is the failure of the learned interfaces genuine or a defect?

**No implementation defect found. The registered failure is a genuine outcome of the registered procedure, but for W7 at 4,096 it is not robust to the data draw.** Evidence:

**2.1 The implementation does what §I.3.1 specifies, in training as well as at initialization.**
- My own forward reproduces every count of all 57 *trained* snapshots exactly (s3).
- Gradients of the implementation's alphabet loss equal those of my own forward to ≤ 1.3e-4 relative (max abs ≤ 4e-9) for W7, A4, E7 at initialization and at the registered W7-4096, W7-16384, A4-16384 and E7-16384 snapshots (d5).
- The frozen code (`studies.p9i` Trainer, unchanged) and my own trainer, run from the same seed on rehearsal draw 2, follow the same trajectory (mean query cosine 0.9975 vs 0.9974 at update 64; accuracy 0.981 vs 0.984 at 8,192) (d1, d2).
- Did W, the interface and the keys receive gradient and move? Yes, but little in the collapsed state. Registered snapshots (d3): W7 `wq` moved 2.4× (seed 1801) and 8.1× (seed 1802) its initial norm at 4,096, 2.5–3.3× at 16,384, 4.6× at 65,536; A4 q/k/v 1.5–6.6×; every key row moved at 4,096 (mean 0.17 against an initial row norm of about 0.08) and **the keys aligned with the collapsed query** (mean cosine of a unit key to the mean key direction 0.93 at 4,096, 0.47 at 16,384). At the trained W7-4096 snapshot the gradient on `wq` is 2.7e-6 against 1.9e-2 on `wo` (d5). Loss curves (r2): every learned-query arm falls from 4.68–4.78 to 3.465–3.471 nats ≈ ln 32 = 3.466 within about 1,000 updates and then stays there: it learns the alphabet marginal and nothing fact-specific. R1 continues to 0.72–1.12.

**2.2 It is address collapse, as in P8.** Panel A, registered snapshots (d3, s3):

| cell | mean query cosine | eff. rank (centred) | distinct top-1 | largest top-1 share | facts with a private slot | fact-independent share of E‖z‖² (init → trained) | identifier share of the fact-dependent variance (init → trained) |
|---|---|---|---|---|---|---|---|
| W7 4,096 s1801 | 0.994 | 3.2 | 1 | 1.00 | 2.3% | 0.57 → 0.95 | 0.62 → 0.25 |
| W7 4,096 s1802 | 0.962 | 1.6 | 2 | 1.00 | 0.1% | 0.50 → 0.94 | 0.54 → 0.76 |
| W7 16,384 s1801 | 0.994 | 2.6 | 4 | 0.53 | 0.8% | 0.56 → 0.97 | 0.61 → 0.44 |
| W7 65,536 s1801 | 0.991 | 5.2 | 5 | 0.45 | 0.1% | 0.56 → 0.97 | 0.61 → 0.75 |
| E7 16,384 s1801 | 0.948 | 1.2 | 4 | 0.66 | 0.2% | 0.37 → 0.91 | 0.57 → 0.67 |
| A4 16,384 s1801 | 1.000 | 1.7 | 4 | 0.57 | 0% | — → 0.99 | — |
| A4E 16,384 s1801 | 1.000 | 1.1 | 2 | 0.95 | 0% | — → 0.98 | — |
| N 16,384 s1801 | 0.087 | 1.2 | 5 | 0.35 | 0.05% | → 0.22 | — |
| BB 4,096 s1801 (PARTIAL) | 0.023 | 13.2 | 1,233 | 0.006 | 8.4% | → 0.02 | — |
| BB 16,384 s1801 | 1.000 | 3.0 | 6 | 0.43 | 0% | → 0.98 | — |

"Private slot" = in the top 8 of exactly one fact (the learned arms have no designated own-fact key, so the requested "rank of the own-fact key" is not defined for them; this is my substitute). Reading: 91–99% of the pre-normalization query is the same vector for every fact (the separator/binding/position common mode); of the small fact-dependent remainder the identifier positions carry 25–76%. A4/A4E attention on the identifier positions is at the uniform level (0.24 against 0.23 for uniform attention). N's queries are spread (cosine 0.09) but carry essentially one direction (effective rank 1.2) and still reach 5 top-1 slots.

**2.3 The collapse happens in the first 64 updates; escape from it is slow and draw-dependent (diagnostics, not results).** With the frozen code or my trainer, W7 at 4,096 slots / 2,048 facts, U = 8,192:

| data | seeds | accuracy at 8,192 (Panel A of that draw) |
|---|---|---|
| rehearsal draw 2 | 500001 (frozen code; my trainer), 500002 (mine), 500003, 500004 (frozen) | 0.981, 0.984, 0.973, 0.937, 0.969 |
| rehearsal draw 0 | 500001 (mine), 500003, 500004 (frozen) | 0.981, 0.984, 0.960 |
| p9i-test-2 | 500001 (frozen) | 0.951 |
| p9i-test-0 | 500001 (frozen) | 0.159 (escape under way, cosine 0.08) |
| p9i-test-1 | 500001 (frozen) | 0.056 (escape starting, cosine 0.59) |
| *registered (for comparison)* | *1801, 1802* | *0.041, 0.041 (cosine 0.994, 0.962)* |

In every run the queries collapse by update 64 (cosine 0.95–0.998, 1–6 distinct top-1 slots) and the loss sits at ≈ ln 32; in most draws `wq` then keeps growing (≈ 9× at 2,048, ≈ 15× at 4,096, ≈ 18× at 8,192) and the queries separate between about 2,000 and 6,000 updates, after which accuracy rises to 0.94–0.98. In the registered draw `wq` grew only 2.4–8.1× by 8,192, so the escape had not begun. Within a draw the outcome hardly depends on the init seed; between draws it does. At 16,384 slots / 8,192 facts (draws 0 and 2, frozen code, seed 500001) the escape had begun but was far from complete at 8,192 updates (0.043 and 0.039; cosine 0.49 and 0.69). A4 stays collapsed on draw 2 with both implementations (0.035, cosine ≈ 1). Two mechanism probes on draw 2 did **not** prevent the early collapse and escaped at the same time as plain W7: a trainable fact-independent bias at the answer site (0.978) and keys initialized at the initial queries (0.981). So the collapse is not caused only by the fact-independent alphabet prior. My hypothesis that it was is refuted.

**Conclusion for task 2.** The forward, the loss and the gradients are as specified, and the frozen code learns W7 at 4,096 within U on most other draws. So chance-level W7 is not explained by a code defect. It is an optimization failure of answer-loss training through top-8 cosine addressing: the queries collapse early, and whether they escape within U depends on the draw. The registered outcome stands as registered: under §I.8.3 W7 would need WORKS at all three sizes, and the 16,384 diagnostics suggest that it would fail there within U on these draws too. **The W7 class at 4,096 (FAILS) is a property of the registered draw. In 9 of 11 diagnostic runs on five other draws the same recipe reached 0.94–0.98.** This sensitivity is not visible from the registered records. `PENDING LEAD REVIEW`: how to state it, and whether it bears on any revision.

## 3. BB

- Class at 4,096: all four raw classes PARTIAL (accuracy ≥ 0.25 and above [36, 96]; η = 0.54–0.65 < 0.90, so row 2 fails whatever the ablations show) → **INTERFACE_PARTIAL**, confirmed. At 16,384 and 65,536: FAILS (16,384 above the interval but < 0.25; B102 FAILS on both panels).
- BB-0 at 4,096 (182/171 of 2,048) and at 16,384 (361/365) is **above** the G2 interval. The MODEL_STORES_FACTS rule (§I.8.1) converts only INTERFACE_WORKS, so it does not apply at any size. Confirmed; the analysis did not apply it.
- BB-0's two seeds are **bit-identical** (same tensors, same update logs) at every size: BB-0 has no seed-dependent initialization and the data order does not depend on the init seed. Its "two seeds" are one run. This does not change a class, because only "either seed" enters the rule.
- Memory dependence at 4,096: disabling the memory drops BB to 126/112 (s1801) and 109/111 (s1802) of 2,048; permuting values drops it to 100/94 and 71/85. Some of these are above the interval, but far below 1,113–1,330. BB's PARTIAL accuracy is carried by the memory. The trained attention concentrates 0.90–0.92 of its mass on the identifier positions in 3 of 4 heads (BB-0: 0.95–0.97), and the queries are spread (cosine 0.02, 1,233 distinct top-1 slots). At 16,384 the attention still attends to the identifier (0.86–0.95), but the memory collapsed (8 distinct slots; gate σ = 0.17; disabled = permuted = trained accuracy). BB's above-interval 0.045 there comes from the attention, not the memory (BB-0 0.044).
- BB at 4,096 was still learning at U (loss 2.65 / 2.36 in the last 2,048 updates; clip active in 7.5% / 13.6% of updates).
- Language modelling (own recomputation on the 2,048 corpus rows, nothing added): before 2.3494 nats (B102 2.3701); after BB 4.183–4.465, BB-D 3.925–4.380, BB-0 4.184–4.694 (rises 0.67–1.00). **LANGUAGE MODELLING DEGRADED** at every size, by far more than the 5% line; the retrained attention largely destroys next-byte prediction (ln 256 = 5.55).
- **What BB shows:** with block-0 attention retrained on the answer loss alone, at 2,048 facts and 512 exposures per fact, the natural query addresses 54–65% of facts within U. It does this while ruining the backbone's language modelling. **What it does not show:** a model that communicates what it needs while remaining a language model; anything at 8,192 or 32,768 facts; WORKS at any size; anything beyond this task and U (§I.13).

## 4. D7

- Numbers verified (s3): see §1. D7 was still improving at U (loss 1.57 / 1.56 / 2.33 at 16,384; 3.29 at 65,536). Disabled → chance.
- B101 against B102 at 16,384: 0.78–0.80 against 0.44. There is one B102 replicate. Under §6.3 a parent contrast is descriptive only, so this says nothing about parents in general.
- Every interface arm is FAILS, so the dense comparison is NOT COMPARED. The report prints exactly that for W7/D7 and BB/BB-D at 16,384 and 65,536, and nothing at 4,096, where there is no dense cell. This is correct under §I.8.2. No DENSE SUFFICES or BEATS DENSE label exists in this run.
- What D7 means under §I.13: a parameter-matched dense adapter on the same 7-position window of frozen states, trained on the same loss for the same U, recalls 78–80% of 8,192 facts on B101 (44% on B102) and 13% of 32,768. So the window carries the identity, and answer-loss gradient through a dense map can use it. Together with §2, W7's failure is about addressing through a learned top-8 key table, not about missing information. It is not a statement that memory is unnecessary, and it is not a dense-comparison class.

## 5. What may and may not be claimed

May be claimed (registered, recomputed):
- Within U = 8,192 updates, on frozen backbone B101 (B102 replicate where run), with the 32-way answer loss and this synthetic task: no tested interface reached INTERFACE_WORKS at any size. N, W7, E7, A4 and A4E were at chance everywhere. BB was INTERFACE_PARTIAL at 4,096 only, with LANGUAGE MODELLING DEGRADED. **NO_INTERFACE_SELECTED (step 4); ADR-0017 Lanes A–D stay blocked on this backbone.**
- The oracle rungs show that the memory can store and return the answers within the same U (R1 0.967–1.000, R2 1.000). They are references, not systems.
- The learned-query arms collapsed (mean query cosine 0.95–1.00, 1–6 distinct top-1 slots), and the loss reached only the alphabet marginal.

May be stated as auditor diagnostic evidence, not as a registered result (moderate strength):
- "The interface is representable but was not learned through the answer loss within U on the registered draw." Representable: my design-stage probe (a contrastively fitted W7 query with an oracle store, 0.96–1.00), D7 at 0.78–0.80 on the same window, and diagnostic W7 runs on other draws reaching 0.94–0.98 at 4,096 with the frozen code. Not learned: the registered collapse. The strength is limited: the diagnostics are on other draws, cover only 4,096 and 16,384, and number 11 runs. Learning succeeds at 4,096 on most draws and fails or is late on some (2 of 5 non-registered draws, and the registered one). At 16,384 it was incomplete on both draws tried.

May not be claimed:
- Anything about capacity, utilization, locality or incremental learning, or any between-size difference as capacity (exposures per fact differ 16×).
- That the ArborLM concept fails, or more than a statement about this backbone, this loss and this U.
- That W7, E7, A4 or A4E "cannot" address facts; that answer-loss training of W7 is impossible (the diagnostics contradict it); or the reverse, that W7 works (no registered evidence).
- That BB shows a language model communicating what it needs (it was retrained on this task with its next-byte loss unprotected and degraded by 67–100%).
- Anything from D7 as DENSE SUFFICES or BEATS DENSE (NOT COMPARED), or that memory is not needed.
- Generalization to natural language (fixed-length records, random identifiers). W7 is told the record length.

Implications for ADR-0017 Lanes A–D: they **stay blocked** (§I.8.3 step 4). Options for the human lead, listed without recommendation: accept the negative result as registered; register a new study that changes the training of addressing (for example a longer U, an auxiliary addressing objective, or another query initialization), with its own approval and draws; register a study of the draw-sensitivity found in §2.3; or stop the interface line. Each would need its own specification, audit and approvals. `PENDING LEAD REVIEW`.

## 6. Deviations from the frozen procedure

- **Three, not two, mistyped launch commands** appear in `$TMPDIR/p9i_run2.log` (copied to `outputs/stage_log_p9i_run2_copy.log`): `evaluate 900`, `analyze 300`, `report 300`. Each was refused by argparse ("invalid choice") before anything ran. There is no manifest or ledger entry for them. The stages then ran once each.
- No sign of a re-run (s2): one manifest per stage; one ledger entry per stage for this run; 57 train and 57 evaluate tasks; each cell holds only `eval/u0008192`, `snapshots/u0008192`, `train.json` and `updates.jsonl`; no traceback in any worker log. Stage timestamps are consistent: gates 02:04:00–02:04:06, train 02:04:10–02:30:59, evaluate 02:31:09–02:32:47, analyze 02:32:48, report 02:32:49 (UTC).
- The C4–C8 comparison output required by §15.8 before training is not in the committed folder, and only 3.5 s separate the end of gates from the start of train. I cannot confirm from the records that it ran then. My own recheck (s2) shows that C4–C8 hold, so nothing turns on it. Recording that output would close the gap.
- Data generation ran before the freeze commit, so the data manifest carries the pre-freeze spec hash. This is by design, because the freeze record embeds the data-manifest hash.

## 7. My own errors and failed attempts (kept)

1. `s1_recompute.py` first draft contained a malformed expression in the exposure check and a malformed conditional in the LM loop. Both were fixed before the first run, so no output was produced with them.
2. `s3_rescore.py` first invocation failed (`ModuleNotFoundError: studies`, PYTHONPATH not set). The second failed because zsh did not word-split the label list (`OSError: File name too long`). The third (all 57) succeeded. The failed outputs were overwritten in `outputs/s3_rescore_all57.jsonl`/`.stderr`, not kept. This is recorded here instead.
3. Seven diagnostic runs launched as detached subshells were killed at about 4,096 updates when the launching call ended. Their partial outputs are kept as `outputs/d2_*_attempt1_KILLED_at_4096.jsonl`, and they were re-run to completion in a background task.
4. Mechanism hypothesis refuted: I expected the fact-independent alphabet prior to drive the collapse. The W7bias probe collapsed just the same.
5. The docstring of `d2_their_trainer_draw2.py` mentions a `--lockstep K` option that I did not implement. The gradient comparison it was meant for is `d5_gradient_check.py`. I left the script unchanged so that it stays byte-identical to its outputs.
6. The diagnostics ran with 2 threads and without `use_deterministic_algorithms`, whereas the registered stages ran single-threaded and deterministic. Trajectories agree closely but not bit for bit.

## Commands (from the worktree root; E = `/Users/daniellaloush/dandush03/ArborLM/experiments`, R = E/`P9IP-20261115T020303574595Z-674730f6b8a147c0a47cac404321f2df`, A1 = E/`P9IP-20261114T235955649302Z-8756ef5f9d1541bd9e0efaece6f7c27b`, D = this folder)

```sh
uv run --locked python D/s1_recompute.py R A1 results/p9i-run-attempt2-2026-11-15 > D/outputs/s1_recompute.txt
uv run --locked python D/s2_attempt_comparison.py A1 R > D/outputs/s2_attempt_comparison.txt
uv run --locked python D/r2_training_logs.py R A1 > D/outputs/r2_training_logs.txt
ls R/cells | xargs env PYTHONPATH=. uv run --locked python D/s3_rescore.py R E > D/outputs/s3_rescore_all57.jsonl
PYTHONPATH=. uv run --locked python D/d3_snapshot_diagnostics.py R E <15 labels, see output> > D/outputs/d3_snapshot_diagnostics.jsonl
PYTHONPATH=. uv run --locked python D/d5_gradient_check.py R E > D/outputs/d5_gradient_check.txt
PYTHONPATH=. uv run --locked python D/d1_diag_train.py --draw {0,2} --variant {W7,W7bias,W7keyinit,A4,R1} --seed {500001,500002}      # DIAGNOSTIC
PYTHONPATH=. uv run --locked python D/d2_their_trainer_draw2.py --draw {0,2} --arm {W7,A4} --slots {4096,16384} --facts {2048,8192} --seed {500001,500003,500004}   # DIAGNOSTIC
PYTHONPATH=. uv run --locked python D/d4_their_trainer_seedsets.py --testset {0,1,2} --arm W7 --slots 4096 --facts 2048 --seed 500001 --save <scratchpad>   # DIAGNOSTIC
uv run --locked ruff check .
```

Astra review: NOT_PERFORMED. Claude review is not Astra review, and this document is not a human approval.
