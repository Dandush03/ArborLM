# ADR-0025 addendum: the G4-MPS amendment (ruling 39)

**Status: ADDENDUM — decision of the human lead recorded.** Recorded by the implementer from the lead coordinator's message of 2026-11-20. Existing ADR and ruling files are not edited. `Astra review: NOT_PERFORMED`.

## The decision

On 2026-11-20 at about 16:15 Panama time the lead coordinator put to the human lead, with the implementer's diagnosis: "Which do you want: amend the gate, or train on CPU?", recommending the amendment and stating that it is a gate changed after observing its failure and that gradient agreement had already been measured at 0.011–0.017 %. The human lead answered: **"I will go with the amend as well since its the dense computing"**.

## The observation

The Part T measuring rehearsal on real data (run directory `/Users/daniellaloush/dandush03/ArborLM/experiments/P10IS2-T-measuring-20261120`, HEAD 0479d3a, kept as the record of the failed attempt) completed its gates stage in 1,613 s; gate G4-MPS FAILED: `max_loss_difference` 3.36e-05 (tolerance 1e-3, passes), `max_relative_parameter_difference` 1.477e-02 (tolerance 1e-4, fails), 20 updates, device mps; every other gate passed (G8 skipped as stand-in); `train` refused (ENGINEERING-FAILURE, as designed). The diagnosis (`results/p10is2-partt-g4mps-diagnosis-2026-11-20/DIAGNOSIS.md`, with its scripts as `*.py.txt` and its raw output, tracked here) found, MEASURED: the failing tensors are `store.keys.0` (1.48e-2) and `store.values.0` (9.9e-3); the gate's own tensor passes; CPU against CPU is exactly 0.0; MPS against MPS 2.3e-06; no fallback, no MPS warning, same dtype and batch order; at identical parameters the gradients agree to 1.1e-04 to 1.7e-04 and the loss to 3e-05; the key and value gradients are exactly zero at update 1 (the gate is initialised at 0) and about 1e-8 afterwards, the size of AdamW's eps; on CPU alone, absolute noise of 1e-12 in those gradients reproduces the figure and 1e-13 does not. The parameter condition therefore measures the conditioning of AdamW on near-eps gradients, not equivalence of the devices.

## The old rule (quoted)

ADR-0022 section 12.3, carried by ADR-0025 section 7.3: "the same 20 updates on MPS agree with CPU in loss within 1e-3 and in parameters within a relative norm difference of 1e-4 *(lead's choice)*." Config: `mps_loss_tolerance = 1.0e-3`, `mps_parameter_relative_tolerance = 1.0e-4`.

## The new rule (ruling 39), in full

Gate G4-MPS compares the same cell (M1, replicate 0, order AB), built twice from its listed seeds, trained for the same `g4_repeat_updates` (20) updates on the same batches, once on CPU and once on the world's MPS device. It passes only if both conditions hold:

1. **UNCHANGED, gating.** Every one of the 20 per-update losses of the CPU run and the MPS run is within `mps_loss_tolerance` = 1e-3 (absolute).
2. **REPLACES the parameter condition, gating: gradient agreement at identical parameters.** Along the CPU run's trajectory, at each of the 20 updates, before the optimiser step, the gradient of the same batch's loss is computed on CPU and on MPS from the SAME parameter values (the CPU run's, copied to MPS). For every trainable tensor: if ||g_cpu|| > 0, then ||g_mps − g_cpu|| / ||g_cpu|| ≤ `mps_gradient_relative_tolerance` = 1e-3; if ||g_cpu|| is exactly 0, then ||g_mps|| must be exactly 0. The largest figure over tensors and updates is recorded with the tensor and update where it occurs. **Reason for 1e-3, fixed without reference to the observed figures:** it is the figure already registered for the loss condition of the same gate; a correct device on float32 agrees far inside it and a wrong operation does not.
3. **RECORDED, NOT GATING.** The old relative parameter difference after 20 updates, per tensor, with the old tolerance (`mps_parameter_relative_tolerance` = 1e-4) named as superseded; and the MPS-against-MPS repeat figure.

**If the exact-zero clause of (2) fails on the real world, it is not adjusted: the work stops and is reported to the lead coordinator.**

## Disclosures

- The parameter tolerance 1e-4 was written without a measurement (ADR-0022 section 12.3, "lead's choice"; it appears as a bracketed proposal in the ADR-0022 review) and first ran on real data on 2026-11-20, where it failed at 1.48e-2 with the losses agreeing to 3.4e-5. **The amendment was made after that observation.**
- Gradient agreement had been measured at 1.1e-4 to 1.7e-4 before the 1e-3 figure was fixed, so the new condition is known to pass on the diagnosed cell.
- No device defect was found; the op responsible for the forward difference of about 1e-5 relative was not isolated (a likely candidate is `index_put(accumulate=True)` in the memory read; not shown).
- Whether MPS-trained and CPU-trained snapshots differ in score is unmeasured.
- No registered value of Part T exists and no sealed value was opened.

## What is unchanged

No label rule, label threshold, seed, cell or cap rule changes. The loss tolerance (1e-3) and the 20 updates are unchanged. Every score is still recomputed on CPU from the snapshots. Training on MPS remains not bit-reproducible (ADR-0025). The other gates, the freeze's requirement that G4-MPS RAN and PASSED on this machine (a skipped gate is not a pass) and the counting-rehearsal check of `g4_mps.passed` are unchanged and follow the new record. The Part T code that implements the rule: `partt_gates.g4_mps`, `compare_runs` (loss condition and the recorded old figure), `compare_gradients`, `gradients_along`.
