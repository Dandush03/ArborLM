# P9 testbed calibration — independent audit (ADR-0017 §12 step 4)

- **Auditor:** Claude Opus 5.5, launched as the independent auditor by the Claude lead. I did not write the code or analyses under audit (`studies/p9/`, Sonnet implementers) or the calibration records.
- **Status of this document:** independent engineering and mathematical evidence only. **Not Astra validation (Astra review: NOT_PERFORMED) and not human approval.** Scientific choices are marked `PENDING LEAD REVIEW`.
- **Audited:** commit `479a941` (branch `claude/adr-0017-design`); run `P9C-20261114T182513034263Z-a529fd1946ff4e52b19980bd6d3b6fcd` (read only); `results/p9-calibration-2026-11-14/` (byte-identical to the run's `calibration.json` and `controls.json`, sha256 `c3946107…` and `a6957292…`).
- **What I ran:** only frozen-backbone probes, the R2 rung and oracle-table probes of the frozen upper block, all on **rehearsal draw 0** (data seeds 179001–179033, init seeds 179001/179002). No R0, R0a, R1, tree, dense or regularized arm was built, trained or evaluated; no registered seed was touched. Nothing in `studies/`, `results/`, `configs/`, ADRs or `experiments/` was edited. Nothing committed.
- **Environment:** Apple M5 Max, 48 GB, macOS (Darwin 27.2.0), CPU only; Python 3.12.14, torch 2.8.0, `uv run --locked` (no numpy/scipy in the lock). Every script is in this folder, every output in `outputs/`; commands are at the end.

## Verdict on the lead's three readings

| Reading | Verdict | Key numbers |
|---|---|---|
| (1) The frozen block exposes almost none of the identifier at the answer site; R0 will be near chance | **CONFIRMED, and stronger than stated** | Recorded probes reproduced exactly. Answer-site state: ≤0.4 bits of the 20-bit identifier (logistic), 1.0–1.4 bits with an MLP at 32,768 facts. Every single position carries only its own symbol plus ≈0.1–0.2 bits of each other symbol (5.0–5.6 bits). The 20 bits exist only jointly across the record (concatenation: 19.8–20.0 bits). Block 1 cannot carry even an **oracle** per-fact vector written at earlier record positions to the answer site (0.028–0.047 accuracy vs 0.969 when the same table writes at the site). |
| (2) R2 accuracy follows optimizer updates, not exposures per fact; the 4,096 failure is an artefact of matched exposure | **CONFIRMED** (with one qualification) | At 4,096 slots R2 crosses 0.95 at 2,560–3,584 updates (E = 160–224) and reaches its ceiling by 3,072 (B101) / 5,632 (B102). With the shared readout (wo, gate) warm-started from a converged 16K cell it reaches 0.95 in about 512 updates; with lr 0.01, 0.973 in 1,024. Qualification: at equal update counts the smaller memory is better (2,048 updates: 0.72–0.90 at 4K vs 0.53–0.68 at 16K), so exposures matter, but second-order. |
| (3) B101 plateaus at 0.9697 because one answer symbol is unreachable through its frozen final layers | **PARTLY: one symbol, yes; unreachable, no** | All failures are facts with answer `\` (0x5C): 994/32,768, 235/8,192, 55/2,048. `\` **can** be the strict argmax within Σ (certified margin 1.16 logits; every symbol on both parents has margin ≥ 0.95). The cause is a loss/scoring mismatch. At the optimum of the 256-way training loss for `\`, `[` wins within Σ by 0.23 logits. The converged R2 sits exactly there (p_full 0.01885 vs 0.01895 ceiling; 992/994 predicted `[`). With cross-entropy over Σ, R2 reaches 1.000. |

## 1. Frozen-hidden probes (`probes.py`, `probe_block1.py`, `attention_block1.py`, `position_tables*.py`)

**What is predicted, and on which streams (checked in code and data).** `controls.nearest_stored_state_probe` predicts the answer stored with the nearest (cosine) answer-site state of the calibration stream. That stream holds every fact twice, in contexts not used in training. Evaluation is on Panel A, which holds each fact once in new contexts, restricted to trained facts. `controls.linear_probe_per_position` predicts each of the five identifier **symbols** from the answer-site state. It is a ridge least-squares classifier trained on the calibration stream and tested on Panel A. The split is fair: same facts, different contexts. The "hidden state" is the residual after block 0, where the memory is inserted. My own forward reproduces it to 2·10⁻⁶. Targets were re-read from the tokens and match the bookkeeping.

**Reproduction (own code):** nearest stored state 0.0405 / 0.0391 / 0.0359 (B101, F = 2,048 / 8,192 / 32,768) and 0.0405 / 0.0415 / 0.0352 (B102). The ridge per-position accuracies are identical to the record in every digit shown (e.g. B101 2,048: 0.044, 0.054, 0.064, 0.052, 0.073).

**Stronger, still fair probes** (held-out Panel A; "bits" = 5 − held-out cross-entropy in bits, a variational lower bound on I(symbol; state). Because any 4 of the 5 symbols are independent and uniform, the sum over the best 4 symbols lower-bounds the identifier bits.)

| State | Probe | B101 F=2,048 | B101 8,192 | B101 32,768 | B102 2,048 | B102 8,192 | B102 32,768 |
|---|---|---|---|---|---|---|---|
| answer site, before block 0 | logistic | ≤ 0 bits | — | — | ≤ 0 bits | — | — |
| answer site, after block 0 | logistic | ≈ 0 bits (−0.003) | 0.20 | 0.29 | 0.03 | 0.27 | 0.35 |
| answer site, after block 0 | MLP (256 GELU) | < 0 | 0.40 | 1.01 (best symbol acc 0.135) | < 0 | 0.66 | 1.43 |
| answer site, after block 1 (no memory) | logistic | 0.17 | 0.39 | — | 0.13 | 0.38 | — |
| best identifier position (id5), after block 0 | logistic | 5.45 | 5.11 | 5.02 | 5.58 | 5.21 | 5.12 |
| each id position k | logistic | own symbol 4.92–4.94 bits; each other symbol 0.12–0.19 bits | | | own 4.94–4.95; others 0.13–0.24 | | |
| concatenation of the record's 7 positions | logistic / MLP | 19.82 / 19.64 | 19.86 / 19.93 | 19.87 / 19.99 | 19.81 / 19.65 | 19.85 / 19.91 | 19.86 / 19.98 |

Nearest stored state at each single position never exceeds 0.07 (2,048 facts), 0.044 (8,192) and 0.039 (32,768), on either parent.

**Why.** Attention from the answer site is near-uniform in both blocks and both parents. In block 1 each own-record position gets 0.025–0.051 per head and the earlier records 0.74–0.78 (`outputs/attention_block1.log`). No head concentrates on the identifier bytes. The backbone, trained on natural text, does not aggregate five random symbols at any one position.

**Can reading at every position (R0) rescue it?** I tested this with oracle tables that write a learned vector into the block-0 residual, chosen by an index that one position could at best resolve. Block 1, the final norm and the tied output stay frozen. These are frozen-upper-block probes, not R0: no keys, no query projection, no top-k. Setup: 2,048 facts, 8,192 updates (E = 512), B101, `position_tables.py` and `position_tables_extra.py`.

| Index of the written vector | Accuracy (256-way loss / Σ loss) |
|---|---|
| unigram: (position in record, current byte), at every position | 0.039 / 0.052 |
| + bigram (k, sym_k, sym_k−1) at id2..id5 (10 bits per position, twice what the frozen state carries) | 0.108 / 0.163 |
| + trigram at id3..id5 (15 bits per position) | — / 0.195 |
| per-fact oracle row at id5 only | 0.032 (lr 0.01) / 0.035, 0.035, 0.034 (lr 0.01, 0.003, 0.001) |
| per-fact oracle row at all six positions before the answer site (lr 0.003) | 0.028 / 0.047 |
| **positive control:** per-fact row at the answer site | 0.969 / — |

Training-batch accuracies equal the test accuracies, so these probes are limited by capacity, not by generalization.

**Conclusion.** A query computed from any single frozen state carries about one symbol (≈5 of 20 bits), and the single frozen attention layer after the memory does not carry fact-specific vectors from earlier positions to the answer site. Even oracle n-gram tables give only 0.04–0.20 on 2,048 facts. R0 and R0a should be expected near chance at every size. Reading everywhere cannot rescue them with this backbone. Caveat: these are trained probes with a fixed budget, so this is strong evidence, not a proof. The same blindness applies to the registered **dense adapter**, which also sees one position at a time, so "beats dense" would compare two near-chance arms.

## 2. R2 rung (`r2_snapshots.py`, `r2_train.py`, `unembed_geometry.py`, `backslash.py`)

**Implemented as specified** (`studies/p9/model.py:426-465`, ADR §5.3):
- values, wo and gate only;
- one dedicated slot per fact, found from the first four identifier symbols;
- weight 1, read at the 8 answer sites only;
- AdamW lr 0.003, clip 1.0.

The R2 cells use N rows for F = N/2 facts, so half the rows are never read; this is harmless. My own R2 forward and scorer reproduce **all 54 recorded accuracies** (9 cells × 3 snapshots × 2 panels) exactly. The snapshots' backbones equal the verified parents. The never-updated value rows equal the N(0, 0.02) init of seeds 179001+2000 / 179002+2000 and not 1701/1702, so the init seeds were rehearsal seeds. My own trainer, on the study's rehearsal schedule, reproduces the cells exactly at 512 and 2,048 updates. Examples: 0.06982/0.06738; 0.8848/0.8916; i179002 0.9019/0.9023; B102 0.7231/0.7339.

**Accuracy against updates (records).**

| Updates | 4K (2,048 facts) | 16K (8,192) | 64K (32,768) |
|---|---|---|---|
| 512 | 0.044–0.087 (E=32) | — | — |
| 1,024 | 0.21–0.29 (E=64) | — | — |
| 2,048 | 0.72–0.90 (E=128) | 0.53–0.68 (E=32) | — |
| 4,096 | — | 0.93–0.97 (E=64) | — |
| 8,192 | — | 0.971/0.999 (E=128) | 0.969/0.989 (E=32) |

The answer-site training loss at equal update counts is also close across sizes (`outputs/r2_snapshots.json`, `loss_windows_64`). At 2,048 updates it is 2.04–2.25 / 2.40–2.55 / 2.84–2.98 for 4K / 16K / 64K.

**Direct tests at 4,096 slots** (own trainer, rehearsal seeds):

| Run | Result |
|---|---|
| B101 i179001 | 0.885 at 2,048, 0.953 at 2,560, 0.973 (ceiling) at 3,072, flat to 16,384 |
| B101 i179002 | 0.902 at 2,048, 0.971 at 2,560 |
| B102 | 0.723 at 2,048, 0.963 at 3,584, 0.985 at 4,096, 1.000 at 5,632 |
| lr 0.01 | 0.973 at 1,024 |
| wo and gate warm-started from the converged 16K cell, fresh values | B101 0.948 / 0.953 at 512, 0.972 at 2,048; B102 0.942 / 0.947 at 512, 0.993 at 2,048 |

**Mechanism.** The read has to outweigh the frozen residual. At the end of each calibration cell the mean ‖delta‖ at answer sites is 31 (4K), 73 (16K) and 190 (64K). With Adam at lr 0.003 the shared readout grows by a bounded amount per update: ‖wo‖_F is 34 → 52 over 512 → 2,048 updates at 4K, 120 at 16K, 261 at 64K, and sigmoid(gate) goes 0.40 → 0.70 at 4K against 0.97–1.0 at 16K/64K. A memory four times larger gets four times more updates of this shared readout at equal exposure.

**This confound is larger than the per-row √K effect** that ADR §5.5 states, and it favours larger memories in every arm with shared projections. Lane A's matched-exposure step ratio I_16K/I_4K is exposed to it.

**The 0.9697 plateau** (`unembed_geometry.py`, `backslash.py`):
- At the answer site the LayerNorm output u is mean-zero with ‖u‖ ≤ √32. For a large delta any such u is reachable. Logits are E(γ⊙u + β).
- For each symbol I computed the maximum Σ-margin by primal ascent and certified it by a dual bound on the ball. The two agree to < 0.01. Every symbol on both parents can be the strict Σ-argmax. The minimum margin is 0.95 on B101 (`^`); `\` has 1.16.
- At the maximizer of the **256-way** probability of `\` on B101, `[` wins within Σ by 0.23. The full-vocabulary top byte there is 0x26.
- B102 has no such symbol.
- The trained R2 is exactly at that point.
- R2 trained with cross-entropy over Σ reaches 1.000 at 4K (2,048 updates) and 16K (from 3,072 updates). It also learns much faster: 0.993 at 16K after 2,048 updates (E = 32), against 0.68 with the 256-way loss.

So the plateau comes from three things together: the B101 tied unembedding, the alphabet, and a training loss (`train.py:97-103`, 256-way) that does not match the scoring rule (`core.py:762-783`, argmax within Σ). It is not a code bug. **The honest fix is to align the loss with the scoring rule** (cross-entropy over Σ for every arm). Excluding `\` or changing the alphabet would be a post-hoc patch fitted to B101 on observed rehearsal data, and would leave the mismatch in place.

## 3. `attainable_probability` (`attainable_check2.py`, `unembed_geometry.py`, `ball_check.py`)

The field is computed correctly, and it does **not** contradict R2. It is the largest **full 256-way probability** of the correct byte that the frozen final norm and tied unembedding allow. That is a ceiling on probability, not on accuracy.

- The exact per-symbol ceilings on the reachable set, weighted by the record's own 4,096 queries, are 0.2751 (B101) and 0.2539 (B102). The record has 0.2739 and 0.2530, so its 200 Adam steps reach 99.6% of the ceiling. The optimizer is not weak and the normalisation is right.
- `fraction_at_least_0.95` = 0.0356 is exactly the share of answers `@`, the only symbol whose ceiling is ≥ 0.95 (0.97–0.99). Other symbols range from 0.01 (`^`, `_`) to 0.88 (`T`).
- Converged R2 cells sit at this ceiling: p_full 0.27 / 0.25 while their accuracy is 0.97 / 0.999.

**Recommendation.** Keep the field, but relabel it as the "full-vocabulary probability ceiling". Report beside it the per-symbol Σ-argmax margins, which are the actual readout ceiling for accuracy. It matters for the secondary log-loss metric: the Σ-renormalized ceiling averages only 0.52–0.55, so the log-loss gain is capped near 4.0 bits per fact rather than 5. It also matters for any rule stated in probabilities.

Minor (F5): it is computed on `restrict_stream(panel_a, 2048)`, which also keeps the 2,048 unseen-control queries (`stages.py:755`). This is harmless for a frozen-layer property but undocumented.

## 4. Did the calibration obey its rules? (`g2_check.py`, `g2_lane_d.py`, records)

- **Arms built.** Only R2 cells (9) and the controls. `calibration_guard` (`stages.py:102-116`) is called before anything is built. There is one run directory, 7 minutes long (18:25–18:32 UTC). Peak RSS per worker was ≤ 0.91 GB.
- **Seeds.** Rehearsal only: data seeds 179001–179033, and init seeds 179001/179002 verified from the parameters as described in §2.
- **Records.** Complete. Each cell has train.json, calibrate.json, updates.jsonl and 3 snapshots; the manifest says COMPLETE; the committed copies are byte-identical.
- **G2.** Correct. All 8 primary no-memory counts and the 4 Lane D counts are reproduced exactly with my own forward. My own exact binomial intervals are [36, 96], [198, 318], [905, 1147] and [89, 171]. All tests are inside their intervals.
- **`select_exposure`.** Applied as coded. Sizes failing at E = 128 are excluded, then the smallest E is taken at which every remaining size reaches 0.95.
- **F2 — PENDING LEAD REVIEW, decisive for E.** `stages.finalize_calibration` (`stages.py:772-792`) aggregates by the **minimum over the B101 seeds and the B102 replicate**. The ADR does not specify this, and the code's own docstring flags it PENDING LEAD REVIEW. Two other readings select **E = 64** instead of 128, with 4,096 still failing in both:
  - B101 only (the registered A5 R2 cells), where 16K at E = 64 is 0.969;
  - the mean over runs (0.957).
- **Nothing leaked or was improvised beyond that.** The B102 R2 cells are not registered cells, but §12 allows "the R2 learning curve at each size".
- **F6 (minor) — README wording.**
  - It says "About 2,048 updates give 0.68–0.89 at either size". The records give 0.53–0.90; the B102 runs are lower.
  - It says "4,096 or more give 0.97". B102 at 16K and 4,096 updates gives 0.929.

**Implementation bugs found: none** in the R2 rung, the probes, G2, the controls or the exposure rule as coded.

## 5. Consequences under ADR-0017 as approved

The lead's claim is **confirmed**, and it understates the situation.

- **Capacity classes.** With 4,096 excluded, the 4K→16K step is NOT_EVALUATED (`analysis_a._capacity_facts`). CAPACITY_POSITIVE needs both steps and CAPACITY_PARTIAL needs the 4K→16K step, so **neither can be assigned**.
- **Lane C.** Its gate needs a supported 4K→16K step, so its trained part is H17-LOC NOT EVALUATED.
- **Classes still reachable** for flat and tree come through the 16K→64K step: CAPACITY_NOT_SUPPORTED, UNDERTRAINED, INTERMEDIATE and NOT REPLICATED. Given §1, R0 will be near chance at 16K and 64K. The likely class is **CAPACITY_NOT_SUPPORTED** (failing step 16K→64K; at chance I is set to 0, which counts as plateaued). It becomes UNDERTRAINED if R0 sits just above the G2 interval without plateauing.
- **Lane B.** Formally evaluable, but it needs dose-zero 16K accuracy ≥ 0.25. It will predictably be NOT_EVALUATED.
- **Lane D.** Needs a_A⁰ ≥ 0.5. It will predictably be NOT_EVALUATED for flat, tree and dense alike.
- **D03.** With tree and flat I both 0 it prints TREE_COMPETITIVE (`analysis_a.py:72`, rule r07). That class is vacuous. F7: it should read NOT_EVALUATED at chance; PENDING LEAD REVIEW.
- **D04 EMPTY-SLOT-EFFECT.** It is defined from 4K to 64K, so it is not assessable.
- **Ladder.** Exact 1.0, R2 ≈ 0.97–1.0 (B101 capped by `\`), R1 unknown, R0a/R0 ≈ chance. The material gap lands at R1 − R0a, so decision item 3 applies: investigate the representation. §1 already establishes that.
- **The aggregation choice changes none of this.** If F2 were resolved to E = 64, 4,096 still fails.

## 6. Options for the human lead (assessment only; the human decides)

**(a) Run as registered (E = 128, 4,096 excluded).**
- *Cost:* the budget projects 14–21 h charged at E = 128 (pre-rehearsal, before removing the 4K cells), plus rehearsal.
- *Could establish:* registered R1 behaviour at 16K/64K, which is the only new science (key learning with an oracle query); a formally registered R1 − R0a gap; the Lane C synthetic part and the version-store engineering test, neither of which needs training.
- *Could not establish:* anything about capacity scaling or locality of the natural memory.
- *Assessment:* the outcome is largely predictable from §1 and §5. Low information per hour.

**(b) A new design revision.** Minimal changes for the study to answer "does more memory hold more useful information, and can it be organised for retrieval":

1. **An addressing path the system can use. This is the blocker.** No query computed from one frozen state can identify a fact, and block 1 does not carry per-fact reads from earlier positions. Options, with my assessment:
   - **Windowed query encoder.** The query at the answer site is a learned function of the frozen states of the preceding six positions, say a linear map of their concatenation, which carries ≈19.9 bits. This is minimal and keeps learned keys and values, top-k, the tree and the regularizers meaningful. It is a fair *system* arm only if (i) the dense adapter gets the identical window, otherwise "beats dense" is meaningless; (ii) the encoder parameters enter the parameter match; (iii) the window length is fixed in advance. Note that a 6-byte window aligned with the record is task knowledge, which must be stated. It changes the architecture under test from "memory addressed by the frozen hidden state" (the P4–P8 lineage) to "memory with its own key encoder": a new claim, reported as such. P5 forward invariance (G4) no longer applies to that arm.
   - **Product keys or n-gram hashing of the raw window.** These make the address nearly an oracle code, like R1. Scaling would then test hash collisions and value storage rather than learned retrieval. Weaker as a "system" claim.
   - **Moving the insertion point after block 1.** This does not help: the answer site carries ≤ 0.39 bits there.
   - **A different or trained backbone.** This needs separate training approval and breaks the lineage.
2. **Align the loss with the scoring rule.** Use cross-entropy over Σ at answer sites for every arm. It removes the B101 `\` cap and cuts the updates R2 needs severalfold. I recommend this over an alphabet change or excluding a symbol.
3. **Remove the update-count confound.** Make matched updates co-primary with matched exposure; it is already registered as the "fixed-compute" estimand. A step would count as supported only if supported under both. Or use one fixed update count at every size, which is conservative against large memories, or extend the E menu. With the Σ loss, R2 at 4K reaches 0.934 at E = 64 and 1.000 at E = 128 in my run.
4. **Fix the rule texts left open.** The G3 aggregation (F2), D03 at chance (F7), and the Lane B/D floors stated against the new arm.
5. **Re-audit.**
   - The revised ADR (design auditor).
   - New model code: window encoder and matched dense.
   - The loss change in `train.py`.
   - `select_exposure` aggregation.
   - A **new calibration on a fresh rehearsal draw (draw 1)**, because draw 0 informed the revision. It would cover the probes on the new query input and R2 under the new loss.

*Cost:* a design cycle plus implementation and re-audit of a few modules, before any compute. *Could establish:* a real answer to H17-CAP and H17-LOC for a memory that can address facts. *Could not establish:* anything about the frozen-state-addressed memory of P4–P8, which this calibration has already shown cannot address this task.

**(c) Stop P9.**
- *Cost:* nothing further.
- *Establishes:* a recorded negative testbed result. With these frozen P4 backbones, the identity of a multi-byte key is not available at any single position, and the frozen upper block cannot route fact-specific reads from earlier positions. A hidden-state-addressed memory therefore cannot be tested for capacity on this task.
- *Cannot say:* anything about memory capacity scaling or locality.

My assessment, for the human's information: (a) spends the largest budget on a mostly predictable outcome. (b) is the only option that can answer the question, at the price of changing the system under test. (c) is defensible if that change is out of scope.

## Findings list (graded)

| ID | Grade | Where | Finding |
|---|---|---|---|
| F1 | MAJOR (design, not a code bug) | `train.py:97-103` vs `core.py:762-783` | 256-way training loss against Σ-argmax scoring: caps B101 at 0.9697 (`\`), slows every readout |
| F2 | MAJOR, PENDING LEAD REVIEW | `stages.py:772-792` | G3 aggregation (min over B101 seeds and B102) is unspecified in the ADR and decides E = 128 against 64 |
| F3 | MAJOR (design) | ADR §5.5 | matched exposure gives larger memories more updates of the shared readout; larger than the stated √K row effect |
| F4 | BLOCKER for the scientific question (design) | ADR §5.3, §5.6 | no single frozen state carries the identifier; block 1 cannot route reads; R0, R0a and dense will be near chance |
| F5 | MINOR | `stages.py:755`, `controls.py:240-337` | attainable_probability is the full-vocabulary probability ceiling (not a readout ceiling) and includes unseen queries; label it |
| F6 | MINOR | `results/p9-calibration-2026-11-14/README.md` | two update-count statements omit B102's lower values |
| F7 | MINOR, PENDING LEAD REVIEW | `analysis_a.py:72`, rule r07 | D03 prints TREE_COMPETITIVE when tree and flat are both at chance |

## My own errors and discarded attempts (kept)

- `attainable_check.py` weighted the ceilings by the 2,048 trained queries only. That made the record appear to exceed the ceiling (0.2739 against 0.2685). The record uses 4,096 queries including unseen controls. `attainable_check2.py` corrects the weighting, and the record then sits at 99.6% of the ceiling.
- `ball_check2.py` (projected gradient with a decaying step) under-converged (0.2649). It is superseded by `ball_check.py`, which agrees with the sphere values. The `pmax_*` values in `unembed_geometry.json` are optimizer lower bounds. The margins are certified by the dual bound.
- I started a duplicate `probes.py 2048` by mistake and killed it. The first run's `probes_2048.json` stands.
- Two smoke outputs (a 512-update `r2_train` run and a 256-update `position_tables` run) were deleted before the real runs with the same tags. Their printed values matched the later runs at the same updates.
- My forward differs from the implementer's by ≤ 4·10⁻⁶ in logits; every recorded accuracy is nevertheless reproduced exactly.

## Commands (run from the worktree root; all `uv run --locked`)

```sh
uv run --locked python docs/reviews/p9-calibration-audit-2026-11-14/probes.py 2048
uv run --locked python docs/reviews/p9-calibration-audit-2026-11-14/probes.py 8192 32768
uv run --locked python docs/reviews/p9-calibration-audit-2026-11-14/r2_snapshots.py
uv run --locked python docs/reviews/p9-calibration-audit-2026-11-14/unembed_geometry.py
uv run --locked python docs/reviews/p9-calibration-audit-2026-11-14/backslash.py
uv run --locked python docs/reviews/p9-calibration-audit-2026-11-14/g2_check.py
PYTHONPATH=docs/reviews/p9-calibration-audit-2026-11-14 uv run --locked python docs/reviews/p9-calibration-audit-2026-11-14/g2_lane_d.py
PYTHONPATH=docs/reviews/p9-calibration-audit-2026-11-14 uv run --locked python docs/reviews/p9-calibration-audit-2026-11-14/probe_block1.py
uv run --locked python docs/reviews/p9-calibration-audit-2026-11-14/attention_block1.py
uv run --locked python docs/reviews/p9-calibration-audit-2026-11-14/attainable_check.py   # superseded
uv run --locked python docs/reviews/p9-calibration-audit-2026-11-14/attainable_check2.py
uv run --locked python docs/reviews/p9-calibration-audit-2026-11-14/ball_check.py
uv run --locked python docs/reviews/p9-calibration-audit-2026-11-14/ball_check2.py         # under-converged, kept
sh docs/reviews/p9-calibration-audit-2026-11-14/run_r2_experiments.sh
sh docs/reviews/p9-calibration-audit-2026-11-14/run_position_tables.sh
sh docs/reviews/p9-calibration-audit-2026-11-14/run_position_tables_extra.sh
uv run --locked ruff check .
```
