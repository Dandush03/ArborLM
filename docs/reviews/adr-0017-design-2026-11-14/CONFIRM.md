# ADR-0017 revision 3 — auditor confirmation check (2026-11-14)

- Reviewer: Claude Opus 5.5 (session model `claude-opus-5-5`), auditor role, launched by the Claude lead. This is independent engineering and mathematical evidence. It is **not** Astra review and **not** human approval. Astra review: NOT_PERFORMED.
- Scope: a narrow confirmation that revision 3 (branch `claude/adr-0017-design`, HEAD `488e6ce`) applies `RECHECK.md` W1–W31 and RB1–RB3, checks each lead's choice for defects, and reads revision 3 once end to end for contradictions. Read: the ADR (all 466 lines), `git diff e46d5f8 HEAD` of the ADR and `RESOURCE_BUDGET.md`, `EXECUTION_PLAN.md`, `RESOURCE_BUDGET.md`, the human draft, my `RECHECK.md` and my earlier check outputs `c4`, `r3`.
- Nothing was implemented, trained or evaluated. No ArborLM model was run. One new pure-Python toy (S1, below) was run.
- Environment: Apple M5 Max, macOS 27.2.1 arm64, Python 3.12.14 via `uv run --locked`. S1 command, from the repository root: `uv run --locked python -I <scratchpad>/s1_ema_init_transient.py` (2.3 s). The appendix gives the script with its intermediate-print lines condensed (logic unchanged) and its output; the full script and output stay in the session scratchpad, not in the repository.
- I wrote `REVIEW.md`, `RECHECK.md` and the W texts. Two defects below are in my own W texts (F1 from W22, F8 from W28). I say so where they come up.

## Verdict

**No BLOCKER remains. One MAJOR remains (F1: REGULARIZER-DRIVEN MOVEMENT fires with no regularizer). Every other item is a wording fix.** The fix for F1 is one replacement sentence with one number for the lead to confirm. If F1–F15 below are applied verbatim, the design is **READY FOR HUMAN DECISION 1** without another re-check. If the lead uses a different number in F1, no re-check is needed either, as long as it is a fixed number greater than 1 written before decision 1. "Ready for decision 1" is not approval.

## 1. Status of RB1–RB3 and W1–W31

| Item | Status | Note (lead's choice checked for defects, not for taste) |
|---|---|---|
| RB1 | APPLIED | via W1–W4 |
| RB2 | APPLIED | via W7 |
| RB3 | APPLIED | via W12, W13 |
| W1 | APPLIED | §6.1 |
| W2 | APPLIED | Floor 0.25: no defect. It matches the Lane B floor (§8.3) and the A10 floor (§8.2). |
| W3 | APPLIED | §8.2 |
| W4 | APPLIED | §8.7 item 5 |
| W5 | APPLIED | Learning rate 0.012: no defect. The row-lazy arm moves 4.0·lr per exposure at every size, against AdamW's 3.9–4.0 at 4K (r3 part 5, c4). Gap: OPTIMIZER-ARM UNINFORMATIVE still passes decision item 1 silently → F6. |
| W6 | APPLIED | |
| W7 | APPLIED | Without b: no defect. Numerical note → F4. u₀ (my own W7 choice): see S1 below. Optional, not required. |
| W8 | APPLIED | "ratio" has no stated reference → F3 |
| W9 | APPLIED WITH CHANGE | α_c = 1 replaced by 0.05 instead of adding 0.05; still 8 cells. Acceptable. At random selection, α_c = 0.25 costs 0.25 · ln 32 · (0.998 − 1/8)/(7/8) = 0.86 nats, below the chance-level answer loss. |
| W10 | APPLIED | Support-length ratio ≤ 1.10: no defect |
| W11 | APPLIED | |
| W12 | APPLIED | The §8.3 header still names only the dose-zero reference → F2 |
| W13 | APPLIED | Unconstrained layout for flat and tree, with a branch-constrained control: acceptable, and stated as W13 asked |
| W14 | APPLIED | §8.4, §13 |
| W15 | APPLIED WITH CHANGE | Fresh optimizer state for every phase-B arm: acceptable. It is explicit, the same for all arms, and meets the draft's "no silent carry-over". Tree memory-only not run: acceptable. It was never in the matrix (D2 = 7 configurations × 2 = 14), and the draft's memory-only comparison is met by the flat arm. |
| W16 | APPLIED | |
| W17 | APPLIED | Lane D's 4,096-fact sets have no G2 interval, but §3 gates Lane D on G1–G4 for A and B → F5 |
| W18 | APPLIED | |
| W19 | APPLIED | |
| W20 | APPLIED | |
| W21 | APPLIED | |
| W22 | APPLIED, **DEFECTIVE (MAJOR)** | "More than half" is always met: under AdamW with no regularizer, 0.876 / 0.899 / 0.900 of a sparse row's movement falls on updates without gradient (my `c4` output; ADR §5.5 says "about 90%"). The annotation therefore prints on every B1 and C1 cell and means nothing. The fault is in my W22 wording (an absolute share); the lead's "half" inherits it. → F1 |
| W23 | APPLIED | §8 opening and §12 step 4. §0 item 3 is narrower → F7 |
| W24 | APPLIED | §12 step 5. `EXECUTION_PLAN.md` 2.1 is stale (§3 below) |
| W25 | APPLIED | |
| W26 | APPLIED | 4K ladder rule in §8.2; dependencies in §10. Optional: add analysis dependencies for the ladder (A5, A5b, A6, A7) and Lane D (D1, D2). |
| W27 | APPLIED WITH CHANGE | My items 7 and 8 are resolved by returning to two workers and 8 GiB, not by listing them: acceptable. Item 10 is resolved by restoring the controls: acceptable. Not done and not listed: the draft §10 "medians, full distributions, parent-level paired contrasts" → F9. My §5 sentence for §0 item 1 was not a W item and was not applied → F10. |
| W28 | APPLIED WITH CHANGE | Key-32 cells are not costed at twice key-16. The budget discloses this: acceptable for a projection that the rehearsal replaces. My own reduction-4 text had two errors → F8. |
| W29 | APPLIED | |
| W30 | APPLIED WITH CHANGE | TREE_AHEAD at ≥ 1.03 added: acceptable. It is an annotation with no decision-map use. |
| W31 | APPLIED | §6.3 |

## 2. Contradictions and gaps found in one end-to-end read

- **§8.3 header against C1.** The header says "against its dose-zero 16K cell". The paragraph below it says C1 cells are classed against B1 α_u = 0.25. → F2
- **§0 against §4 of RECHECK.md.** All items are covered except "medians, full distributions, parent-level paired contrasts" → F9.
- **§0 item 3** says calibration changes "only the exposure count". §8 also allows TASK_CEILING_FAIL. → F7
- **Header line 9 and §12 step 1** say "not yet re-checked". **§16 row M13** still says "16 tests"; §8.1 now has 8. **§17** says W9 and W30 were "applied as written", but both were changed, and the W28 key-32 costing was not applied. → F11–F13
- **§8.1 G2** has no interval at 4,096 facts, which Lane D needs (§3). → F5
- **§8.7 item 1:** "OPTIMIZER-DEPENDENT: not assessed" needs human acceptance (budget reduction 4), but OPTIMIZER-ARM UNINFORMATIVE, which is equally uninformative, does not. → F6
- **`RESOURCE_BUDGET.md` reduction 4 (my W28 text):** EMPTY-SLOT-EFFECT is defined from 4K to 64K, not 16K→64K. Dropping A5 R1 at 64K also removes the ladder term R2 − R1. → F8
- **`RESOURCE_BUDGET.md` aggregate RSS:** "2 × 3 GiB plus four simulation workers" within 8 GiB leaves about 0.5 GiB per simulation worker. No line says so, and the rehearsal list does not test it. → F14
- **Checked consistent:**
  - §10 blocks against §7 doses (α_u 0/0.25/1; α_c 0/0.05/0.25) and §8.5 arms (6 trained arms + joint = 7 configurations, 14 cells; no tree memory-only);
  - 100 cells;
  - §11 against the budget (two workers, about 5.8 h at E = 32, 8 GiB);
  - the D01–D10 table against the blocks;
  - λ_u and λ_c normalisation (the worst value costs α · ln 32 in both);
  - G3 "not run" against §8.6 INCOMPLETE (the matrix is amended before the freeze, so there is no conflict).
- **My own discrepancy (no consequence):** ADR §5.5 quotes 4.0 / 7.9 / 15.1 lr per exposure (my `c4`, late steady state). My `r3` part 5 gave 3.93 / 7.6 / 14.51, which is an average over 32 events including warm-up. They differ by ≤ 4%. No rule depends on it.

**S1 (optional, about my own W7 choice of u₀).** With u₀ = the first batch's ū, the hinge is active at the start even in a perfectly spread memory. In the toy (16K, 128 answer sites × 8 uniform-random hard selections per update, b = 1/64), it switches off after **57** updates (hard only) or **27** updates (π = 0.1 on the other 56 candidates), out of 2,048 at E = 32. That is 1.3–2.8% of training under an artificial push. With u₀ = uniform 1/N the hinge is never active in a spread memory. A collapsed memory then shows up after about one pass instead. Either is defensible and the choice is now stated, so no fix is required. PENDING LEAD REVIEW if the lead prefers uniform.

**Optional (no fix required):** the E ratio of a C1 cell is taken against the dose-zero flat cell, so it mixes the usage term with the co-access term. Reporting the E of the B1 α_u = 0.25 cell beside it would separate them, since the traces already exist (D09).

## 3. Stale lines in `EXECUTION_PLAN.md`, with replacements

Family 2, Lane-B lazy arms, three workers and 12 GiB no longer appear. The worker count (line 48) now agrees with ADR §11.

| Line | Now | Replace with |
|---|---|---|
| 1 | `(design revision 2)` | `(design revision 3)` |
| 13 | `0.5 Revision answering the review … ADR-0017 revision 2` | `0.5 Revisions answering the review and re-check \| Fable \| ADR-0017 revisions 2 and 3 \| —` |
| 14 (after) | — | add row `0.6b Confirmation check of revision 3 \| Opus \| CONFIRM.md \| fixes F1–F15 applied verbatim, else revise` |
| 23 | `exact and nearest-neighbour controls` | `exact retrieval, no-memory baseline, frozen-hidden probes (nearest stored answer-site state; 32-way linear probe per identifier position), attainable answer probability` |
| 24 | `objectives, lazy optimizer` | `objectives (global usage floor with the b-free gradient of ADR §7; λ_c on R_co − 1/8), row-lazy Adam on key and value tables only at learning rate 0.012 (A10)` |
| 25 | `evaluation: information, supports, knock-outs, group ablations` | `evaluation: I_acc with the chance floor, seven-position knock-outs, minimal supports, specificity, value-only group ablations, hard and soft usage, per-row movement split, LEAKAGE check` |
| 26 | `sparse co-access layouts` | `sparse co-access layouts; identity, frequency-packing, random-partition and (tree) branch-constrained control layouts; pages per query and cross-query reuse` |
| 27 | `Lane D: sequential phases, replay, version store` | `Lane D: sequential phases from V1 parameters with a fresh optimizer state for every phase-B arm (V1 optimizer state stored for the restoration test only), replay, version store` |
| 32 | `(collapsed, degenerate, entropy inflation, undertrained, incomplete, ceiling failure)` | `(collapsed, degenerate, entropy inflation, undertrained, incomplete, ceiling failure, near-chance step, COLLAPSED before DEGENERATE, SOFT-USAGE ONLY, LEAKAGE, OPTIMIZER-ARM UNINFORMATIVE, seed disagreement → INTERMEDIATE)` |
| 38 | `selects E by the registered rule; no compared arm is run` | `selects E by the registered rule and may mark a size TASK_CEILING_FAIL; nothing else changes (ADR §8 opening); no compared arm is run` |
| 39 | `record schema is a whitelist (time, RSS, finiteness, shapes), checked by the auditor` | `records written only through a validator whose allowed keys are the whitelist (time, RSS, finiteness, shapes); stdout and stderr to a file the auditor checks for loss or accuracy values; no progress display shows loss` |
| 40 | `any registered reduction chosen now` | `any registered reduction chosen now, with its rule change (RESOURCE_BUDGET.md)` |
| 48 | `two training workers, four simulation workers.` | `two training workers, four simulation workers, 8 GiB aggregate (a third training worker only if granted at decision 2).` |
| 70 | `Lane C's trained interpretation needs Lane A's 16,384-slot class and Lane B's utilization class.` | `Lane C's trained interpretation needs the architecture's 4K→16K step supported (Lane A 4K and 16K cells, including B102) and its B1 α_u = 0.25, α_c = 0 cell UTILIZATION_PRESERVED or IMPROVED (Lane B).` |
| 71 | `Lane D is independent after the common freeze.` | `Lane D is independent in training after the common freeze; it is NOT_EVALUATED if 16,384 slots is TASK_CEILING_FAIL.` |

## 4. Paste-ready fixes

- **F1 (MAJOR; §6.3, replace the REGULARIZER-DRIVEN MOVEMENT sentence):** "**REGULARIZER-DRIVEN MOVEMENT** is printed with a B1 or C1 class when, in both seeds, the cell's cumulative key movement on updates where the row had no task gradient is more than 1.5 times that of its §8.3 reference cell of the same seed (the dose-zero 16K cell for B1; the B1 cell with α_u = 0.25, α_c = 0 for C1). The share of key movement on such updates is reported for every cell but is not compared with a fixed fraction: under AdamW it is about 0.9 with no regularizer at all (§5.5; auditor check c4: 0.876 / 0.899 / 0.900)." [1.5: PENDING LEAD REVIEW. Any fixed number > 1 written before decision 1 is acceptable without re-check.]
- **F2 (§8.3 header):** "### 8.3 Utilization (per architecture and seed, against its reference: the dose-zero 16K cell for B1, the B1 cell with α_u = 0.25, α_c = 0 for C1; both seeds; both panels; first match wins)"
- **F3 (§7, SOFT-USAGE ONLY):** replace "while its hard entropy-effective-slot ratio is below 1.05" with "while its hard entropy-effective-slot ratio to its §8.3 reference is below 1.05".
- **F4 (§7, after "… at the three sizes."):** "H uses 0 · ln 0 = 0. ∂R_glob/∂u is evaluated at u_t, which contains b·ū_t, so it is finite on every slot where ∂ū_t/∂θ ≠ 0; no ε is added. It is implemented as λ_u·⟨g_t, ū_t⟩ with g_t = ∂R_glob/∂u at the detached u_t."
- **F5 (§8.1 G2, append):** "Lane D adds, per primary panel, the no-memory baseline on sets A and B (4,096 facts each): a separate family of 4 tests at level 1 − 0.001/4, whose interval is 'chance' in Lane D."
- **F6 (§8.7 item 1, append):** "If the annotation reads OPTIMIZER-ARM UNINFORMATIVE or 'OPTIMIZER-DEPENDENT: not assessed', this item needs the human lead's explicit acceptance of that."
- **F7 (§0 item 3, replace "able to change only the exposure count from a fixed menu"):** "able to change only the exposure count from a fixed menu and to mark a size TASK_CEILING_FAIL (§8 opening)".
- **F8 (`RESOURCE_BUDGET.md` reduction 4; corrects my W28):** replace "Rule change: EMPTY-SLOT-EFFECT, OPTIMIZER-DEPENDENT and KEY-WIDTH-LIMITED at 16K→64K, and the 64K ladder terms R1 − R0a and R0a − R0, are not assessed;" with "Rule change: EMPTY-SLOT-EFFECT (defined from 4K to 64K), KEY-WIDTH-LIMITED, OPTIMIZER-DEPENDENT at 16K→64K, and the 64K ladder terms R2 − R1, R1 − R0a and R0a − R0, are not assessed;".
- **F9 (§6.3, append):** "Every quantity used by a class is reported with its median and full per-fact distribution. The B101 − B102 contrast is reported for A1 and A2 as descriptive; no other parent-level contrast exists with one replicate parent (draft §10)."
- **F10 (§0 item 1, append):** "The draft's question whether more memory 'supports computation rather than merely a lookup table' (draft §5 item 2) is therefore not answered by this study."
- **F11 (header, replace "Revision 3 has not been re-checked."):** "Revision 3 was confirmed by Opus 5.5 (`CONFIRM.md`), with fixes F1–F15 applied verbatim." **(§12 step 1):** "1. Auditor re-check of this revision (done: `RECHECK.md`, `CONFIRM.md`)."
- **F12 (§16, under the heading):** "Revision-2 entries. Where §17 differs (for example, G2 now has 8 tests), §17 governs."
- **F13 (§17, replace the row "Remaining W items"):** "| Remaining W items | W4, W6, W11, W16, W21, W24–W26, W29, W31 applied as written; W9 applied with α_c = 1 replaced by 0.05 (no new cells); W30 applied with TREE_AHEAD added; W28 applied except that key-32 cells are not yet costed at twice key-16 (disclosed in the budget); confirmation fixes F1–F15 (`CONFIRM.md`) |"
- **F14 (`RESOURCE_BUDGET.md`, "What the rehearsal must settle", add item 5):** "5. RSS of a simulation worker at 65,536 slots: with two training workers at 3 GiB, the 8 GiB aggregate leaves about 0.5 GiB for each of four simulation workers."
- **F15 (`EXECUTION_PLAN.md`):** the replacements in §3 above.

## Appendix — S1 script and output

```python
import math, random
N, F = 16384, 8192
b = 128 / F
lnM = math.log(min(N, 8 * F) / 2)
def batch(rng, pi_out):
    u = [0.0] * N
    for _ in range(128):
        c = rng.sample(range(N), 64)
        for s in c[:8]:
            u[s] += 1.0
        for s in c[8:]:
            u[s] += pi_out
    t = sum(u)
    return [x / t for x in u]
def H(u):
    return -sum(x * math.log(x) for x in u if x > 0)
for pi_out in (0.0, 0.1):
    for init in ("first_batch", "uniform"):
        rng = random.Random(179001)
        ub = batch(rng, pi_out)
        u = ub[:] if init == "first_batch" else [1.0 / N] * N
        first_off = None
        for t in range(1, 2049):
            ub = batch(rng, pi_out)
            u = [(1 - b) * a + b * c for a, c in zip(u, ub)]
            if first_off is None and H(u) >= lnM:
                first_off = t
            if first_off is not None and t >= 256:
                break
        print(pi_out, init, first_off)
```

Output (summary lines): `pi_out 0.0, first_batch: hinge off at update 57`; `pi_out 0.0, uniform: 1`; `pi_out 0.1, first_batch: 27`; `pi_out 0.1, uniform: 1`. H(u) at t = 1 with u₀ = first batch: 6.96 (hard) and 8.25 (soft), against ln M = 9.011. Steady state: about 9.64–9.68.
