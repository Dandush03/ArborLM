# Diagnosis of the failed G4-MPS gate (measuring rehearsal, HEAD 0479d3a)

Diagnosis only. No study code, config or tolerance was changed; nothing was committed; nothing under `<run-dir>/sealed/` was opened; no evaluation item was scored (the rehearsal world's training draw and its parameters only). Scripts and raw outputs are in this directory (`diag.py` parts A and B, `diag2.py`, `diag3.py`, `diag4.py`, `diag5.py`, `diag6.py`; `part*.json`, `part*.log`). Every number below is MEASURED on this machine (torch 2.8.0, macOS arm64, `PYTORCH_ENABLE_MPS_FALLBACK` unset, two registered runs sharing the machine) on the same rehearsal world the gate used: M1, replicate 0, order AB, 20 updates, learning rate 0.003, AdamW with the default eps 1e-8, clip 1.0.

The gate's figure reproduces: 1.4769e-02 (this run) against 1.4769e-02 (record); loss difference 3.36e-05.

## 1. Which tensors, and is the large figure a near-zero-norm artefact?

The trainable tensors of M1 are three: `store.keys.0` (4096 x 16), `store.values.0` (4096 x 576), `store.gates.0` (1, initialised to 0).

| tensor | ||p_cpu|| | ||p_init|| | ||p_cpu - p_init|| (total change) | ||p_mps - p_cpu|| | diff / ||p_cpu|| (the gate's figure) | diff / change |
|---|---|---|---|---|---|---|
| keys | 5.640 | 5.125 | 2.386 | 8.33e-02 | **1.477e-02** (fails 1e-4) | 3.49e-02 |
| values | 33.88 | 30.73 | 14.19 | 3.35e-01 | **9.89e-03** (fails 1e-4) | 2.36e-02 |
| gates | 5.90e-02 | 0 | 5.90e-02 | 2.2e-07 | 3.7e-06 (passes) | 3.7e-06 |

Two tensors fail; the gate (tiny norm, started at zero) passes. So the figure is **not** a near-zero-norm artefact: the failing tensors have large norms and a large total change; the difference is 3.5% of the change keys moved. It is a real divergence of the update direction in a small set of elements: 231 of 65,536 key elements (0.35%) and 6,569 of 2,359,296 value elements (0.28%) are more than half a learning-rate step apart after 20 updates (largest: 6.9 and 4.6 steps); in about 27% of them the two runs moved in opposite directions; the top 1% of key elements carry 99.9% of the squared difference. 16 and 32 key elements moved on one device and not on the other (of about 58,000 that moved).

## 2. Growth update by update, and the per-update loss differences

Max over tensors of the gate's relative difference after update u (loss difference per update in the last column; the loss is about 2.6 to 3.0 throughout):

| u | max rel | worst tensor | |loss_cpu - loss_mps| |
|---|---|---|---|
| 1 | 7.8e-08 | gates | 3.3e-05 |
| 2 | 6.3e-06 | gates | 3.2e-05 |
| 3 | 1.0e-05 | gates | 3.2e-05 |
| 4 | 1.1e-05 | keys | 3.2e-05 |
| 5 | 1.4e-05 | keys | 3.3e-05 |
| 6 | 7.7e-04 | keys | 3.3e-05 |
| 7 | 1.4e-03 | keys | 3.4e-05 |
| 8 | 2.1e-03 | keys | 3.2e-05 |
| 10 | 3.8e-03 | keys | 3.2e-05 |
| 12 | 5.4e-03 | keys | 3.3e-05 |
| 15 | 8.4e-03 | keys | 3.3e-05 |
| 20 | 1.48e-02 | keys | 3.2e-05 |

The relative difference jumps by about 55 times at update 6 (1.4e-05 to 7.7e-04) and then grows roughly linearly (about 7e-04 per update). The loss difference does not grow at all: 3.2e-05 to 3.4e-05 at every update, 30 times inside the 1e-3 tolerance. It is already 3.3e-05 at update 1, where the parameters are identical: a forward-pass difference between the devices of about 1e-5 relative, constant, not an accumulating one.

## 3. Controls

- CPU against CPU twice: **exactly 0.0** (parameters and losses). One thread against six threads on CPU: also exactly 0.0.
- MPS against MPS twice: max relative parameter difference **2.3e-06** (keys 2.3e-06, values 1.2e-06, gates 6.3e-08), loss difference 9.5e-07. MPS is not bit-repeatable at this size, but it repeats about 60 times inside 1e-4.
- CPU float32 against CPU float64: **not obtainable**. The float64 path of the study's modules raises `expected m1 and m2 to have the same dtype, but got: float != double` (the arm or the loss builds float32 tensors); I did not change code to force it (recorded in `partA.json`, `partC1.json`).
- Substitute control for "ordinary rounding drift under this optimiser": CPU against CPU with noise added to the gradients of keys and values (nonzero entries only):
  - **relative** noise 1e-7, 1e-6, 1e-5 per element: max relative parameter difference 2.0e-06, 2.3e-06, 3.1e-06 (far below 1e-4);
  - **absolute** noise 1e-13: 2.2e-06 (keys), 1.7e-06 (values);
  - **absolute** noise 1e-12: **1.07e-02**, 6.8e-03;
  - absolute noise 1e-11: 1.5e-02, 1.1e-02; 1e-10: 3.1e-02, 2.2e-02; 1e-9: 7.9e-02, 6.2e-02; 1e-8: 0.18, 0.16.
  - So on this cell a perturbation of the key and value gradients of **1e-12 in absolute size, against gradients of about 1e-8, is enough to produce the observed figure on CPU alone**, and 1e-13 is not. The step between the two is the transition into the divergent regime (the divergence is chaotic past a threshold, not proportional to the noise).

## 4. Other causes

- No fallback, no MPS warning: `PYTORCH_ENABLE_MPS_FALLBACK` is unset and no MPS-related warning was raised in the 20 updates. Same dtype (float32), same batch order (the same `plan.gen(2, ...)` batches), same code path (`train_cell`); the world and arm are built identically for both devices.
- Where the MPS forward differs from CPU: at identical parameters and the same batch the loss differs by 3.1e-05 (2.88782 against 2.88785 at update 2's parameters) and the gradients differ by a relative 1.3e-04 (keys), 1.1e-04 (values), 1.7e-04 (gate). The memory read uses `index_put(accumulate=True)` (`studies/p10s2/memory.py:344,389`), whose accumulation order on MPS is not fixed (this is the likely source of the MPS-against-MPS 2e-06 and of part of the MPS-against-CPU gap; I did not isolate it per op). I did not find an unsupported or silently substituted op.
- The mechanism that turns that rounding-level difference into 1e-2 is in the **optimiser and the arm's initialisation**, not the device:
  - The gate is initialised to 0, so at update 1 the gradients of keys and values are **exactly zero** (both devices; only the gate moves: to 0.003 after one step). From update 2 on, the key and value gradients are proportional to the gate and tiny: at update 2 the median nonzero gradient is 1.8e-08 (keys) and 5.3e-09 (values), the 90th percentile 1.0e-07 and 2.2e-08, the maximum 8.3e-06 and 2.4e-06; only 20% of the elements receive a gradient at all (the rows addressed), and 36% (keys) and 72% (values) of those nonzero gradients are below 1e-8.
  - AdamW's epsilon is 1e-8, the same size as these gradients. The step of an element is about `lr * m / (sqrt(v) + eps)`: for a gradient of 1e-8 it is half a step, for one of 1e-9 a ninth, for one of 1e-7 almost a full step. The update is therefore a steep function of the gradient's absolute size and sign exactly where the gradients are smallest and where float32 summation noise (about 1e-12 to 1e-9 absolute here) is comparable. A difference of 1e-12 changes the trajectory of an element by whole steps (the control above).
  - This is also why the relative gradient noise of 1e-5 does not reproduce it (it is 1e-13 absolute on a 1e-8 gradient) while MPS's differences, which do not scale with the gradient, do.
  - The jump at update 6 is when enough elements have their first oscillation of sign and the first-moment averaging stops hiding it (not isolated further).

## 5. History

- The figure 1e-4 was **never measured before it was written**. In the review of ADR-0022 (`docs/reviews/p10-design-2026-11-15/adr-0022-review/REVIEW.md:146`) it appears as a bracketed proposal "(relative norm difference <= [1e-4])"; ADR-0022 section 12.3 states it as "(lead's choice)" (ADR-0022 line 406, carried by ADR-0025 section 7.3 and its line 297 and 408). No run record shows a measured MPS-against-CPU parameter difference before that.
- P10-S2 never ran this gate on real data: there is no P10-S2 registered run (the results directory holds `p10s2-datagen-2026-11-16` only). Its own tests run the gate on tiny synthetic worlds and assert only that the figures exist (`tests/test_p10s2_fixB_gates.py:93-100`, 3 updates, no figure asserted).
- Part Q trains nothing. Part T's end-to-end tests ran `g4_mps` at 20 updates on a tiny synthetic world on MPS and it passed there (the freeze requires it; no figure was recorded). Real data, real size: this rehearsal is the first run, and it failed.

## 6. What the difference does and does not matter for

ADR-0025 (and ADR-0022 section 15 item 2, answered "yes" by the human lead): training on MPS is not bit-reproducible; the snapshots are the object; every score is recomputed on CPU from the snapshots.

- **What the gate protects:** against an MPS training path that computes something other than the intended update (a wrong or fallback op, a wrong dtype, a different batch order, a broken optimiser step). The loss condition (3.4e-05 against 1e-3, 30 times inside) says the two devices compute the same forward and loss to about 1e-5 relative on the same batch.
- **What it does not protect, and cannot as written:** the parameter condition does not distinguish a broken device from the ordinary behaviour of this optimiser on this arm. A CPU-only perturbation of 1e-12 in the gradients fails it, so any backend that is not bit-identical to CPU fails it (CPU passes only because CPU against CPU is bit-identical). It measures the conditioning of AdamW on near-eps gradients, not equivalence of the trained memories.
- **What Part T reads:** scores computed on CPU from each snapshot, whichever device trained it. An MPS-trained snapshot differs from the CPU-trained one in a small set of key and value elements; whether that moves any score is not measured here (a function-space comparison of the two arms on the training-side stand-in panel would measure it; I did not run it, because after 20 updates the arm is barely trained).
- No label, threshold, seed or cell depends on the gate; it only decides whether training is allowed to start.

## 7. Options for the lead to put to the human lead

(Not recommended; set out with cost and meaning. Nothing here relaxes the 1e-4 figure to fit the observation.)

**(a) Train on CPU** (the ADR's own rule: "if the rehearsal finds an unsupported MPS operation, training moves to CPU"; G4's MPS comparison then prints NOT APPLICABLE — TRAINING ON CPU BY THE FREEZE; the freeze may record CPU, ADR-0022 section 13.3 / ADR-0025 gate text). Measured seconds per update, steady state (13 minus 3 updates, 10 updates timed), machine shared with two registered runs, batch as in the plan (`partB2.json`):

| arm | CPU s/update | MPS s/update | ratio |
|---|---|---|---|
| M1 | 1.52 | 0.31 | 5.0 |
| D1 | 1.92 | 0.34 | 5.7 |
| M-append | 1.55 | 0.26 | 5.9 |
| M-seq | 1.59 | 0.26 | 6.0 |
| M-ii | 3.21 | 0.45 | 7.1 |
| D-append | 1.73 | 0.36 | 4.8 |
| D-seq | 1.69 | 0.34 | 5.0 |
| M-joint (2U) | 1.62 | 0.27 | 5.9 |
| D-joint (2U) | 1.83 | 0.34 | 5.4 |
| E-table | 1.69 | 0.28 | 6.1 |

Registered train stage (54 cells; 7 per-cell arms x 6 cells, 2 joint arms x 3 cells at 2U, E-table x 6): 120,000 updates at U = 2,000.
- MPS: about 10.7 charged hours at U = 2,000 (21 at 4,000; 43 at 8,000); one stream of the MPS rate measured here, which is higher than the ADR's 5-10 min per 2,000-update unit.
- CPU: about **61 hours** at U = 2,000 (122 at 4,000; 244 at 8,000): about 5.7 times the MPS figure. Calibration (36 units of 2,000 plus the ladder) would be about 5 to 6 times its MPS estimate as well.
- Cost: the caps are computed from the measuring rehearsal's rates, so the whole plan, caps and allowances scale (the measuring rehearsal itself would have to be repeated on CPU: "every rate rehearsed on CPU"). Scientifically: no change to labels; CPU training is bit-reproducible (CPU against CPU is exactly 0.0), which is an improvement in auditability; the human lead's recorded answer (training on MPS) would have to be revisited.

**(b) Keep MPS and amend the gate.** An amendment that does not depend on the observed number would replace the parameter condition by a test of what the study needs and that is well-conditioned, for example: (i) gradient agreement at identical parameters and batch (relative L2 of the gradients, a one-step quantity not subject to Adam's amplification; measured here: 1.1e-04 to 1.7e-04), (ii) function-space agreement of the two trained arms on a fixed probe batch of training-side inputs (logit or readout difference), (iii) the loss condition (unchanged) over the 20 updates. The reason is the measured conditioning property of the optimiser on this arm (section 4), which is a property of AdamW with eps 1e-8 and a gate initialised at zero, not of the observation. Whether anything changes is the human lead's decision; the ADR (section 12.3 "lead's choice") placed the figure with the lead. Cost: an ADR amendment before the gate can be re-run, and a new threshold would need to be fixed from a conditioning argument or from the CPU-only perturbation controls above, not from this record.

**(c) Fix a found defect.** None found: no fallback, no dtype or batch-order difference, no MPS warning; the device difference (forward about 1e-5 relative, `index_put(accumulate=True)` order) is rounding-level and the amplification is in the optimiser and the zero-initialised gate, both fixed by the ADR (initial gate 0; AdamW defaults). Changing the optimiser epsilon, the initialisation of the gate or the arm would change the training of every memory cell and is a scientific change, not a bug fix.

**(d) (for completeness)** Keep MPS, keep the gate, and accept that it cannot pass: the registered run could not start. Not an option unless the gate is amended.

## Not done / limits

- The CPU float32 against float64 control could not be produced without changing the study's modules.
- The per-op source of the MPS forward difference (e.g. `index_put(accumulate=True)`) was not isolated.
- The timings are from a shared machine and a 10-update window; the CPU and MPS rates move with load (the gate's own 20-update M1 run took 34.9 s on CPU and 10.6 s on MPS including start-up).
- No scores of any panel were computed; whether MPS-trained and CPU-trained snapshots differ in score is open (it would be measured on the registered snapshots, not on 20-update arms).
