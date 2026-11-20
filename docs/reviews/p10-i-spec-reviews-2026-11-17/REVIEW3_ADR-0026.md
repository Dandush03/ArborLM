# Third review — draft ADR-0026 revision 3 (P10-I-S3, longer training), for approval readiness

- Reviewer: `arbor-auditor` subagent, model Claude Opus 5.5 (`claude-opus-5-5`), 2026-11-18 UTC. I also wrote the first and the confirmation reviews of this draft. I did not write the draft, the seed registry, the checker, or any code it relies on.
- Reviewed: `docs/decisions/ADR-0026-p10-i-s3-longer-training.md`, SHA-256 `8afe160fc3d5e17b99cbad8612a40bf077f7de5ac42af258fb9cd61a8735a681`, at HEAD `ef5596b6012320c3bd4f6f1d5e47b12d93f5a63d` (branch `claude/p10-i-r`; the session snapshot said `fc14159`, the branch has moved since). Cross-read: ADR-0029 §§11–20, ADR-0027, ADR-0025 §4.1, `REVIEW2_ADR-0026.md`, DIRECTION.md, DELEGATION_2026-11-18.md, SEED_REGISTRY.md (`7211706f…`), `seed_registry_check_r3.py` (`e4623604…`), `src/arborlm/pilot_model.py`, `p4_model.py`, `p4_config.py`, `pilot_data.py`, `engine.py`, `pilot_metrics.py`, `longer_training.py`, configs P1–P4, `pyproject.toml`, P4 records.
- Independent engineering and mathematical evidence. **Not** Astra validation, **not** a human approval. `Astra review: NOT_PERFORMED`.
- Nothing trained, generated or downloaded; no registered checkpoint or sealed value opened; no git write. Files written: this report and, under `experiments/_scratch/reviews3/`, `import_walk_0026.py`, `p4_recompute_0026.py`, `seedcheck_r3_0026.out`, `seedcheck_r3_0026_uv.out`.

## Verdict: READY AFTER THE LISTED EDITS

No blocking finding. Ten REQUIRED findings, all text edits spelled out in section C, plus a rulings section (section D) to be added to the ADR so that the implementer does not guess. One condition outside the text: open choice 1 should go to the human lead, not be taken by delegation (section F). Given the number of edits, the lead should have the applied diff read once before Decision 1 is recorded.

## A. Numbers recomputed (own code, no `arborlm` import)

Command: `python3 -I experiments/_scratch/reviews3/p4_recompute_0026.py .` (system Python 3.15.1, macOS arm64, stdlib only), reading `results/p4-2026-11-12/per-run.csv` and every `b*-{memory,dense}-*/result.json`.

| Draft figure | Recomputed | Status |
|---|---|---|
| C 0.021988695, P 0.022221519, Q −0.006182638; 27/27 each | same | match |
| 10/27 cells, 2/9 parents within −0.005 | 10, 2 | match |
| share 0.78 of means; 0.62–0.90 per cell; best 0.8997 | 0.7805; 0.6193–0.8997 | match |
| SD of C within parent 0.0005–0.0027; 0.005/SD = 1.85 to 9.66 | 0.000518–0.002708; 1.85–9.66 | match |
| step-0 2.378856566 vs 2.378856373 | same | match |
| tree 14.118 s, dense 4.261 s per 512; memory wall 17.686 s | 14.118, 4.261, 17.686 (wall − train = 3.568 s) | match |
| 152,515 = 156,611 − 4,096; 19,064 fresh updates | manifest counts; 152,515/8 = 19,064.4 | match |
| 86% overlap of calibration and registered FRESH streams | E\|A∩B\|/\|A\| = n/N = 131,072/152,515 = 0.859 | match |
| Parameter counts 198,401 / 198,145 / 198,401 | from `pilot_model.Memory` and `p4_model.DenseAdapter` shapes | match |
| ~16 evaluations per M-TREE checkpoint, 12 per M-FLAT, 8 per D-ADAPT | 16; **13** (enabled, replay, disabled, P_all, 4 P_used, X_mean, 4 X); 8 | flat off by one (advisory) |
| Cost rows of §9 | as in REVIEW2 §A (unchanged inputs) | match |
| P10-S0 6.09 h of 22, 0.40–0.63; P10-S1 25.39 h of 53 | `OUTCOME.md` l.37; l.17 | match |

My own discrepancy, recorded: while checking the 86% figure I first computed 74% (n²/N divided by N); that was my error (wrong denominator). The draft is right.

## B. Confirmation-review findings

| Finding | Judgement | Note |
|---|---|---|
| N1 Decision 2 | FIXED | §14 |
| N2 context-free read | FIXED | §1, §3.4, §6.7, §12. Advisory A2 on the batch mean being non-causal |
| N3 disagree / procedural seal | FIXED | What follows the engineering stop is unstated (ruling D19) |
| N4 mean with failed cell; NE row | **PARTLY — NEW PROBLEM** | The absolute sentence "No mean is ever computed over fewer than 27 cells" contradicts the six-parent readout (18 cells) and the three-cell rehearsal tags (C8) |
| N5 ADR-0027 Route A | FIXED | ADR-0027 l.48 now names exactly §12's labels and defers to open choice 13 |
| N6 one wording | FIXED | |
| N7 frozen inputs | **PARTLY** | 12 files named; the import walk finds 20 at module level, 31 with the P3/P4 loaders (C10); tests location vs `testpaths` (C9) |
| N8, N9 | FIXED | except the flat evaluation count |
| Table D seeds and cross-refs | FIXED | ADR-0027 no longer cites 2601 |

## C. Findings (exact edits)

**C1 REQUIRED — §10 row "Any other required cell or evaluation is missing": code and environment errors become a scientific NOT EVALUABLE.** This is the defect ADR-0029 §20 ruling 11 removed. Also "non-finite loss" is undefined: `p4_model.train_step` raises three different `ValueError`s (loss, gradient norm via `clip_grad_norm_(error_if_nonfinite=True)`, parameters) and `p4_model.evaluate` raises on a non-finite NLL; an implementer cannot tell a failed cell from a crash.
Replace that row by two rows:
"| A training or evaluation item ends with an error that is not a non-finite value as defined in section 6.1 (a code error, an assertion, out of memory, a file-system or other environment error) | The item is recorded as `item_error`. The registered analysis refuses while any `item_error` exists; the outcome is ENGINEERING STOP — ITEM ERRORS and no line is labelled (as ADR-0029 section 20, ruling 11). An environment error inside a gate propagates and is never recorded as a failed gate. |"
"| A required cell or evaluation is missing after the run ends and no `item_error` is recorded | Engineering stop (a defect of the plan or the driver); nothing is labelled. Denominators are never reduced. |"
And in §6.1, after "**Failed cells.**", insert: "A failed cell is a registered run in which the training loss, the clipped gradient norm or any trainable parameter becomes non-finite, or whose enabled NLL at U\* is non-finite. A non-finite NLL under an intervention (P_all, P_used, X, X_mean) on a finite checkpoint makes that cell fail D2 or D3, never pass, and is printed."

**C2 REQUIRED — §11 row 1, §10 row 1: an identity difference during a run has no consequence other than "engineering stop … re-freeze".** That is how P10-S1 attempt 1 was lost. After "Identity is checked by file hash, not by the commit at HEAD." insert: "Every task checks the frozen-input hashes when it starts. A difference stops the task as PAUSED — IDENTITY; nothing is recorded as a result; restoring the file bit for bit lets the stage resume. This is not a gate failure of section 10." In §10 row 1 after "A gate fails before training (section 8, stage G)" insert "(an identity difference during stages T, E or A is PAUSED — IDENTITY, section 11)".

**C3 REQUIRED — §5, §7, §9: order of rehearsal, candidate plan and caps; "charged time" undefined; no cap rule.** "R3 … on the frozen plan" cannot precede the freeze; the delegation sets caps "by each ADR's own rule", and this ADR has none ("replaced by the rehearsal's projection"). Replace the last sentence of §5 ("The rehearsal also runs every registered stage …") with: "Order: R1 → R2 → the candidate `plan.json` is written (items, rate table, worker count, caps) → R3 runs every registered stage end to end against that file itself in the DRY profile, and its SHA-256 goes into `rehearsal_public.json` → the freeze refuses unless the file it commits has that hash → Decision 2. The registered caps are in the candidate plan before R3 runs." In §7 row 1 replace "Hour caps: rehearsal 25 h, registered run 48 h, charged time" with "Hour caps in charged hours (wall-clock hours of a stage's supervisor, at the plan's worker count): rehearsal 25 h; registered run = charged so far + 2 × projected remaining from R2's rates (ADR-0029 section 12's rule), written into the candidate plan; 48 h until then". In §9 replace "If the rehearsal projects more than a cap, the lead returns …" with "If the registered cap by that rule exceeds 48 charged hours, the lead returns to the human lead before Decision 2 with the projection; the matrix is not cut."

**C4 REQUIRED — §5.1 edge rule reads the tie-selected rate. It can favour the memory.** With "smallest rate within 0.0005 of m", a flat loss near the low end makes the lowest grid rate "selected" though the minimiser is interior. That triggers extensions and can end in RATE-AT-EDGE, which turns a memory NOT COMPETITIVE into INCONCLUSIVE (§6.4). Conversely a minimiser at the top edge is hidden when a lower rate ties, so a dense optimum above the grid is neither searched nor tagged. Replace bullet 4 with: "Edge rule: if, at some duration, the rate attaining m (on an exact tie, the smaller) is the lowest or highest finite rate run, the grid is extended by one half-decade step on that side and the selection repeated, at most twice per side. A rate whose neighbour is non-finite in any calibration cell is not at an edge on that side. If after the extensions the rate attaining m for U\* is still the lowest or highest rate run, the selected rate for U\* is tagged RATE-AT-EDGE. The edge is read from the minimiser, not from the tie-selected rate, so that a flat loss cannot create the tag and an optimum at the end cannot be hidden by the tie rule." Add to §7 row "Rate tie tolerance": "Reason for 0.0005: one tenth of the 0.005 resolution."

**C5 REQUIRED — §3.4 joint permutation has no seed.** "As ADR-0009" uses `p4_model.intervene` with 50000 + index, which registry condition 3 forbids. In §3.4 replace "As ADR-0009." with "ADR-0009's construction (one seeded `randperm(256)` per branch, branches in order, applied to keys and values together), seeded with this study's joint seed; P4's helper is not called." Add to §4 table: "| Joint-permutation seeds | 27 + 3 + 1 | 260131 + c (260131–260157); 269024 + c (269024–269026); 269222 |" and the sentence "These values are free in the study's block but outside the registry's named layout; the registry's ADR-0026 row is extended by the lead and the checker copy includes them before the freeze."

**C6 REQUIRED — §4 seed gate will fail on the current tree.** `uv run --locked --offline --no-sync python docs/reviews/p10-i-direction-2026-11-17/seed_registry_check_r3.py` (uv 0.12.15) → `RESULT: FAIL`, 34 problems in [1], every one a P10-I-R value found in P10-I-R's own `configs/p10ir_routing.toml` and `tests/test_p10ir_*.py` (output kept in `seedcheck_r3_0026_uv.out`). S3's own config and tests will hit the same rule. Append to registry condition (2) in §4: "The copy excludes, by recorded substitutions, the literal scan of this study's own files and of each P10-I study's own config and tests against its own allocation (ADR-0029 section 19, ruling 6); its hash goes into the gate result, and this study's values are checked separately against its allocation rows. Reason: the cited checker returns FAIL on the tree of 2026-11-18 for that cause alone."

**C7 REQUIRED — §4 ledger order conflicts with ADR-0025 §4.1.** ADR-0025 states that its 44 marker-like windows cannot give way and that the exclusion runs toward ADR-0026. Replace "whichever study freezes first writes first." with "whichever study freezes first writes first, with one exception: every marker-like window of ADR-0025's fixed grid (ADR-0025 section 4.1) is excluded by this study's walk whether or not ADR-0025 has frozen, computed from ADR-0025's definition and listed in the plan; ADR-0025's sampled windows are drawn after this study's panels if this study freezes first."

**C8 REQUIRED — §6.1 absolute 27-cell sentence contradicts §6.7 and §5.2.** Replace "No mean is ever computed over fewer than 27 cells." with "No mean that enters a condition, label or tag is computed over fewer than the registered cells (27; three for the rehearsal's tags). The six-parent readout of section 6.7 prints means over 18 cells and counts out of 18 cells and 6 parents, with no label. If an arm has a failed cell in a regime, its δ and PAST BEST are printed as NOT DETERMINED, which counts as NOT CONVERGED wherever a tag is read."

**C9 REQUIRED — §11 "local checks": the study's tests are not collected.** `pyproject.toml` has `testpaths = ["tests"]`; `mypy src/arborlm` does not check `studies/`. Replace "`uv run --locked ruff check .`, `mypy` and `pytest` run locally." with "`uv run --locked ruff check .`, `uv run --locked mypy src/arborlm studies/p10i_s3` and `uv run --locked pytest tests studies/p10i_s3/tests` run locally; a bare `pytest` does not collect this study's tests."

**C10 REQUIRED — §11 row 1 item (5): the named list misses files a real import walk finds.** Command: `python3 -I experiments/_scratch/reviews3/import_walk_0026.py src/arborlm pilot_model p4_model pilot_data --toplevel-only` → 20 files. Missing from the twelve: `__init__.py`, `config.py`, `data.py`, `optimization_followup.py`, `p2_config.py`, `p3_config.py`, `records.py`, `watchdog.py`. Loading the P3 parents and the frozen data through the P3/P4 code (`p3_checkpoint`, `p4_parent`, `p4_data`, `p4_checkpoint`) brings it to 31: add `checkpoint.py`, `diagnose_memory.py`, `p2_checkpoint.py`, `p2_data.py`, `p3_checkpoint.py`, `p3_data.py`, `p3_parent.py`, `p4_checkpoint.py`, `p4_data.py`, `p4_parent.py`, `pilot_checkpoint.py`. Replace "and any further file an import walk from these finds, each listed by name in `plan.json`" with "`__init__.py`, `config.py`, `data.py`, `optimization_followup.py`, `p2_config.py`, `p3_config.py`, `records.py`, `watchdog.py`, and every further file reached by a static walk of module-level and function-local imports from every module of `studies/p10i_s3/` (at least the P3/P4 parent and data loaders if they are used), each listed by name and SHA-256 in `plan.json`". In item (6) write "`uv.lock` and `pyproject.toml`"; in item (7) add "the pinned parquet files and every derived chunk file (FRESH, REP, REP-U, panels) by SHA-256".

**Advisory.**
- A1 §13 item 13: add "Expected consequence: section 5.2 expects FRESH arms to be NOT CONVERGED at 16,384; under this option Route A of ADR-0027 is then closed by S3 whatever line 2 shows."
- A2 §3.4 X_mean: add "The batch mean includes reads at later positions and in other chunks of the batch; it can carry batch-level information, which makes D3 harder to meet, not easier."
- A3 §12 row 2: "which remains the other route the direction names" → "which the direction names as the other source of entry evidence (ADR-0027 reads that as P10-I-S1; its open choice 2)".
- A4 §9: "12 per M-FLAT" → "13 per M-FLAT".
- A5 §10 integrity row: "or S computed in a panel order different from the enabled read" is a code assertion; move it to C1's `item_error`.
- A6 §11 platform row: add "`engine.configure_cpu()` settings (one thread, one interop thread, deterministic algorithms), OS build recorded with every gate result".
- A7 §6.2: print M-TREE's RATE-AT-EDGE beside the line-1 label (it changes no label).

## D. Implementer's guesses and recommended rulings (add as a new section "Rulings on implementation questions")

1. NLL arithmetic: as `p4_model.evaluate`: per-batch `loss_for(..., "sum")` in float32, accumulated as a Python float, divided by 32,768. BASE, disabled and every intervention use this one path ("in float64" in §6.1 is replaced by this).
2. Optimizer: `engine.optimizer_for` (foreach=False, fused=False, amsgrad=False), then the rate is written into `param_groups[0]["lr"]` before the first step; step order as `p4_model.train_step`. M-FLAT needs its own wrapper, since `FrozenModel`/`optimizer_names` accept only 198,401 parameters.
3. Streams: one CPU `torch.Generator` seeded with the stream seed. REP and REP-U: successive `randperm(2048)` per epoch. FRESH: one `randperm(152,515)` over the pool in rank order. Update k takes entries 8k to 8k+7.
4. Data beyond rank 4,095: `pilot_data.select` on the pinned parquet (main checkout `data/wikitext2/`) with count = all eligible. A gate shows that the first 4,096 train ranks and the recorded validation panels reproduce bitwise. New chunk files are written and hashed.
5. "Finite at c" in the rate search: no non-finite event through update c and a finite calibration NLL at c.
6. Resume: a paused or killed training cell restarts from update 0 and its partial checkpoints are discarded. Evaluation is resumable per (run, checkpoint).
7. X_dense: position σ[t] keeps its own residual and adds the adapter delta computed from h of σ[t+1]. X_mean_dense: the delta gate·W2·gelu(W1 h) is replaced by its batch mean and the residual is kept.
8. Prior-off read: visit = 2, use_prior = False. Exhaustive read: visit = 16, use_prior = True.
9. NEG-REF: the usage weights are the summed softmax read weights per slot on the calibration-panel enabled read. "Must not return DEPENDENT" means that no NEG-REF cell meets D2's or D3's per-cell condition.
10. Step 0: enabled and disabled only. Checkpoints 512 to U\*: the full control set.
11. §6.3 order row 1: for [TREE] it applies to M-TREE or D-ADAPT, for [FLAT] to M-FLAT or D-ADAPT. M-FLAT follows the memory failed-cell rule. The RATE-AT-EDGE tag for [FLAT] reads M-FLAT's rate.
12. Mean over draws: the four NLLs are averaged, then H is subtracted.
13. Losing arm when the means are exactly equal: no STILL IMPROVING tag.
14. A cap is reached and the extension is refused: the outcome is INCOMPLETE (PAUSED AT CAP) and nothing is labelled.
15. DRY profile: trained DRY additions are evaluated on the calibration panel only. The registered panel is read only by the BASE gates. DRY values go into the sealed archive.
16. Analysis registry keys carry arm, regime, rate, checkpoint, read and draw (the ADR-0029 §13 lesson). The synthetic registry also covers line 1's order rows, the failed-cell rule, NOT DETERMINED δ and §6.6.
17. Worker count k and the per-worker RSS guard are fixed in the candidate plan from R2, with k × 2 GiB ≤ the aggregate guard.
18. After an engineering stop before Decision 2: a fix needs an amendment, and R1 is re-run on the same calibration seeds. The unread sealed archive of the stopped attempt is kept and never opened before the registered outcome.

## E. Machine sharing and wall time

Confirmed: no wall-time or CPU-time reading enters any rule, label or tag (§1, §6, §8, §12). R2's seconds set caps only. Training and evaluation are deterministic single-thread float32 (`engine.configure_cpu`), so load cannot change a result, and no stage must run alone. It can share the machine with these conditions:
- (a) Not during another study's quiet-condition stage: ADR-0025 stage 7 requires "no study process running", ADR-0024 §16 and its MC-T timing, ADR-0027's measured-cost stages, ADR-0028's benchmarks. S3 would make those NOT MEASURED.
- (b) The aggregate RSS guards of the concurrent studies must leave room for the human lead's work. 24 GiB here plus P10-I-R's 18 GiB is 42 of 48 GiB, which is too close. When running alongside another study, cap S3 at 12 GiB (six workers), and keep the total workers of both studies at or below 16 of 18 cores.
- (c) Implement and run in a separate worktree from any running study (the frozen-worktree rule).
- (d) Under load, charged hours grow and can reach a cap. The result is PAUSED, not invalid.

## F. Open choices under the delegation

| # | Recommended option sound? | Take by delegation? |
|---|---|---|
| 1 fixed 16,384 with tag | Sound: FRESH cannot reach 32,768, so a convergence rule has nothing to choose | **No.** It departs from the text of binding DIRECTION §4 ("a rehearsal … sets a preregistered convergence-based duration"). AGENTS.md says stop on disagreeing documents, and the precedent is ADR-0029 §16 item 8, where the human lead ruled departures from direction himself. Put one question to the human lead |
| 5 keep REP-U | Sound; it serves DIRECTION §4 bullet 4; about 7 h; favours neither arm | Yes |
| 13 no entry when D-ADAPT is NOT CONVERGED | Sound and conservative | Yes, with A1's consequence stated |
| 2–4, 6–12 | Sound. Option 4's alternative (K1 alone) would favour the memory, and the recommended option avoids it | Yes. None needs a download, an out-of-lock package, administrator access or a paid service. The cost (26–48 single-thread hours) is within DELEGATION §4's estimate |

The decision not to run M-FLAT in REP-U is sound. No registered label reads it, and the consequence is stated.

## G. Seeds

§4's table equals SEED_REGISTRY §4.2's ADR-0026 rows (streams 260001 + 3c + g; P_all 260101 + c; P_used 260201 + 4c + j, up to 260308; X 260401 + 4c + j, up to 260508; calibration 269001–269062; dry 269201–269254; init 330301–330303, 330391, 330392, 330398, 330399; tests 935001–935999). The checker's [2] finds no collision for the 260001–269999 block. What is missing is the joint-permutation seed (C5). The gate as written would fail (C6).

`Astra review: NOT_PERFORMED`. This review is not an approval.
