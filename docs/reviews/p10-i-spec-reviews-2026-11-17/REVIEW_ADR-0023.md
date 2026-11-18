# Independent specification review: ADR-0023 (P10-I-S0, addressing and overload), draft 1

- **Reviewer:** the `arbor-auditor` subagent, model Claude Opus 5.5 (`claude-opus-5-5`). I did not write the draft and none of the code it relies on.
- **Draft reviewed:** `docs/decisions/ADR-0023-p10-i-s0-addressing-and-overload.md`. It is untracked; sha256 `c25a4ecbad766f85aeb08f1f5cd762271524edb9df2ae97e12221fd524cffe39`. Worktree HEAD is `c525898`, branch `claude/p10-i-specs`.
- **Standing:** this is a Claude review. It is not Astra validation and not a human approval. `Astra review: NOT_PERFORMED`. Scientific choices are flagged `PENDING LEAD REVIEW`. I did not choose thresholds or gates. No training was run, no registered benchmark was run, and no data was generated.

## Verdict: NOT READY

The design follows the direction on the main points. The registered 0.90 ratio is kept. The draft covers several loads. Durations come from a rule fixed before any registered seed is seen. A failure is stated to be a registered outcome. The records are quoted accurately with one material exception (finding R6).

Three things stop it going to the human lead as it is:

1. **The outcome function is not total and not unambiguous.** It can derive a label while cells are PAUSED. It labels a reference failure as "UNDERTRAINING NOT EXCLUDED". Two readers would combine Line G differently.
2. **Two factual claims are false.** First, the code it says it imports unedited cannot build a cell at 512, 1,024, 2,048 or 8,192 slots. Second, its initialization seeds are P10-S0's derived initialization seeds.
3. **The X8 ceiling cannot be reached under its own ladder.**

All three are fixable in text, in one revision.

## Commands and environment

All of these ran from the worktree root on darwin (Apple silicon).

- **Independent checks** (seeds, the Poisson estimate, Clopper–Pearson bounds, the operating characteristic, the sign test, the cost recomputation): `python3 -I <scratchpad>/adr0023_checks.py "$PWD"`. This is system Python 3.15.1. The script imports nothing from `arborlm` or `studies` and reads `configs/*.toml` with `tomllib`. Appendix A reproduces it verbatim, because the scratchpad is not durable.
- **Feasibility probe:** `timeout 120 uv run --locked python -` with the snippet in Appendix B (venv Python 3.12). It imports only `studies.p9ii.core` and `studies.p10s0.core` constants and constructors. It imports no analysis module and no implementer summary script.
- **Source reading** used `grep` and `sed` over `studies/`, `configs/`, `src/`, `tests/` and `docs/decisions/`, as cited per finding.
- **Failed attempts, kept here as the record:**
  1. My first seed grep returned "no matches found: --include=*.py". zsh expanded the unquoted globs, so it searched nothing. I re-ran it with quoted globs.
  2. An `echo =====` separator failed under zsh (`= not found`), and that command's later output was lost. I re-ran it with `-----`.
  3. The quoted grep for six-digit numbers matched only hex fragments of hashes (`e301851a`, `e930294b`, …), not seeds.

  None of these changed a finding.

## 1. Numbers quoted from records (item 1)

I checked every number in sections 2, 6.2, 6.3, 6.7 and 11 against the record the draft names.

| Draft location | Claim | Record | Result |
|---|---|---|---|
| §2 row 1 | ADDRESSING-QUALIFIED (4,096 AND 16,384), A5-D, μ = 1.0, 512 exposures, 0.5 facts/slot, accepted | `results/p10s0-run-2026-11-16/OUTCOME.md` l.7; ADR-0020 l.809–817 | matches |
| §2 row 2 | 1 of 10, FAILS | `classes.csv` last row (`A5-D,8K/4K,FAILS,…,10,1,10,1,0.005`) | matches |
| §2 row 3 | 0.946–0.956; A6 0.993–0.997; 10/10 no collapse; c6 passed | `docs/reviews/p10s0-results-2026-11-16/REVIEW.md` l.101 | matches |
| §2 row 4 | ten margins, −0.180 … +0.001 | `extras_out.txt` l.82–91 | matches, all ten |
| §2 row 5 | +0.061 (2K/4K), +0.024 (8K/16K) | `extras_out.txt` l.19–20, l.27–28 | matches |
| §2 row 6 | A0 0 of 10, c4 fails in all ten | `extras_out.txt` l.4; `classes.csv` | matches |
| §2 row 8 | 21,941 s (6.09 h) of 22 h | `OUTCOME.md` l.38 | matches |
| §2 row 8 | "Q1 training 13,415 s", cited to `OUTCOME.md` | appears only in `REVIEW.md` l.109 and `stages_out.txt` | **wrong source (R1)** |
| §2 row 9 | F-OQ 0.390 → 0.654 (8,192 → 393,216); 0.392 → 0.637 (16,384 → 786,432) | P10-S1 `OUTCOME.md` l.84, l.87; `audit/AUDIT.md` l.149, l.152 | matches. These are **mean a_use**, not accuracy (see R6) |
| §2 row 10 | 0.948 → 0.996 (8K/4K); 0.991 → 0.999 (2K/1K) | P10-S1 `OUTCOME.md` l.82, l.85 | matches. a_use again, read at U_P → 6·U_P = 49,152, which the draft does not state |
| §2 row 11 | Lane L OMITTED — NOT OVERLOAD-QUALIFIED, `RESULTS.md` l.10 | P10-S1 `RESULTS.md` l.10 | matches |
| §2 remark 1 | seven of ten worse than −0.05 | `extras_out.txt` | matches (d01–d05, d08, d10) |
| §2 remark 2 | last-doubling gain 0.016–0.061, F-OQ 32K/4K | `audit/AUDIT.md` l.63 | number matches. The unit is **bits per fact (i\*)**, which the draft omits (R2) |
| §2 remark 2 | "still rising" sentence not found | not in P10-S1 `OUTCOME.md`, correct. It does exist in ADR-0021 l.53 (§1 fact 11: "8 at 0.96 (4,096 slots, still rising at 65,536 updates)", on the stand-in) | partly mismatched (R3) |
| §3 | A0 escape median 13,664 updates | `extras_out.txt` l.40 (A0 8K/16K) | matches |
| §4.2 | P10-S1 init seeds "2101–2192" | `studies/p10s1/core.py` l.489–495 also uses **2193** (calibration draw 2, revision 5) | stale (folded into finding 5) |
| §6.2 | E[distinct] ≈ 201; P(slot > 10 sites) < 1% at 512 slots | my recomputation: 201.5 (binomial 201.6); 0.0069–0.0073 | matches, under the draft's assumption (finding 15) |
| §6.3 | bounds 0.741 / 0.606 / 0.717 | my recomputation | matches |
| §6.7 | "6–0 … p = 0.031" | 0.03125 | matches, but the rule d ≥ 6 is not a 6–0 split (finding 12) |
| §11 | A5-D 0.0098–0.0102, A6 0.0091–0.0093 (4,096); A5-D 0.0172, A0 0.0144, A6 0.0187 (16,384) | `timing_out.txt` "run" column | matches. Omitted: A0 at 4,096 slots was measured at **0.0144**, not the assumed 0.010 (R5) |
| §11 | 56 / 8 / 18 CPU-h → 9.4 / 1.4 / 3.0 h; total about 15–16 | my recomputation: 55.9 / 8.2 / 18.3 → 15.2 h | matches |
| §11 | 44 + 12 CPU-h for X8 | 43.7 + 11.7 | matches |
| §11 | P10-S1 25.39 h | P10-S1 `OUTCOME.md` l.17 | matches |
| §0 | delegation quote "p10 can be self approve but p10-I need my review" | ADR-0020 l.574 | matches |

Record mismatches, R1–R6:

- **R1 (ADVISORY).** Change the source of "Q1 training 13,415 s" to `docs/reviews/p10s0-results-2026-11-16/REVIEW.md` §5 item 7.
- **R2 (ADVISORY).** State that "last-doubling gain 0.016–0.061" is in bits per fact of i\*. It is not comparable with the draft's 0.01 accuracy step.
- **R3 (ADVISORY).** Cite ADR-0021 §1 fact 11 as the nearest "still rising" text, and note that it describes the stand-in at 65,536 updates.
- **R4.** P10-S1's seeds are stale. This is part of finding 5.
- **R5 (ADVISORY).** Use 0.0144 for A0 at 4,096 slots. Series M then goes from 55.9 to 57.5 CPU-h.
- **R6 (REQUIRED), §6.5, last paragraph.** "the reference is expected … degraded at 8 (0.637–0.654)" treats P10-S1's mean a_use as A6's accuracy. a_use ≤ accuracy by definition (share of correctly answered facts that the read swap breaks). Those cells also ran 6,144 (8K/1K) and 3,072 (32K/4K) exposures per fact, not this study's T. **Change** the sentence to say: "P10-S1's oracle-query store (F-OQ, the R1 reference) had mean a_use 0.654 at 8K/1K after 6,144 exposures and 0.637 at 32K/4K after 3,072. Accuracy is at least that. The expected A6 accuracy at load 8 is therefore above these figures and unmeasured."

## 2. Findings

### BLOCKING

**1. BLOCKING: the outcome function is not total. A label can be derived while cells are missing, and non-evaluability is mislabelled as undertraining.** (§7 rows 1, 2, 5 and 6; §5.2 "Reference validity"; §6.4; §6.6; §12.)

The problems:

- **(a)** Row 1 fires on "a main-grid cell without a record **that is not PAUSED**". So a main grid with PAUSED, missing cells does not stop at row 1 and falls through to rows 2–6. A scientific label can then be computed on an incomplete grid. Nothing says the analysis waits for every PAUSED cell, or what happens if the human lead declines to extend the cap.
- **(b)** Row 5 sends "NOT EVALUABLE at the first failing load" to **OVERLOAD UNRESOLVED … UNDERTRAINING NOT EXCLUDED**. §12 itself says a load with A6 below its floor "is not a failure of addressing". It is not undertraining either. The same happens when Stage R removes a condition at a cell type ("CONDITION n NOT APPLIED"). That makes Line Q NOT EVALUABLE there, the load does not hold, and row 5 again prints "undertraining".
- **(c)** Row 2 covers only class NOT_EVALUATED at load 0.5. A Stage R reference-validity flag at load 0.5, which makes Line Q NOT EVALUABLE there, is not in row 2. It falls to row 3, ANCHOR NOT REPRODUCED. That is a substantive misreading.
- **(d)** §6.6 defines "holds at ℓ" for a line but not for the states NOT READ (Line G when Line A breaks) and NOT EVALUABLE. Does NOT READ in one series count as "not holding" for L_G? The draft does not say. Nor does it say in which series row 6's "which line fails there" and H23-G are read.
- **(e)** Row 4's wording for a failing load above ℓ has only NOT QUALIFIED and UNRESOLVED. It has no NOT EVALUABLE variant (for example, X8 with A6 below 0.50 on two draws).
- **(f)** §5.2 says a condition A6 fails is "not applied", and then that Line Q is NOT EVALUABLE. The draft does not say whether Lines A and G are also not evaluable at that cell type, or whether they are read on the reduced condition set.

Change:

- **(i)** Row 1 fires on any main-grid cell without a completed record, PAUSED or not. Analysis runs only when every planned main-grid cell is complete. A study left PAUSED reports **INCOMPLETE — PAUSED** and no scientific label.
- **(ii)** Add a separate row before row 5: **OVERLOAD NOT EVALUABLE AT ℓ — REFERENCE** (A6 below floor, or a reference-validity flag). Make row 5 apply only to convergence.
- **(iii)** Extend row 2 to any Stage R reference-validity flag at load 0.5. Add a stop rule (§12): if Stage R flags any anchor cell type, the work returns to the human lead **before the freeze**. Running 200 cells to print NOT EVALUABLE is not acceptable.
- **(iv)** Give a per-line, per-series state table: HOLDS / FAILS / NOT READ / NOT EVALUABLE. Give its two-series combination rule (for example, HOLDS only if both series HOLD; NOT EVALUABLE if either is NOT EVALUABLE and neither FAILS; otherwise FAILS). State that NOT READ counts as FAILS for L_G.
- **(v)** State that under a reference-validity flag, all three lines are NOT EVALUABLE at that cell type.
- **(vi)** Have the synthetic-registry tests (§10 stage 1) include each of these cases.

**2. BLOCKING: the code the draft says it imports unedited cannot run the new slot counts.** (§3 "Arm code is imported unedited … a gate asserts bit-identity"; §16 "drafter is unsure … 512 and 1,024 slots".)

- `studies/p9ii/core.py` l.251 rejects any slot count outside `SLOTS_BY_SIZE = (4096, 16384, 65536)` in `Cell.__post_init__`. P10-S0 trains and evaluates through that cell: `studies/p10s0/core.py` l.311–313 (`p9ii_cell()`), `studies/p10s0/train.py` l.77 and `studies/p10s0/evaluate.py` l.170. I confirmed this by running it: 512, 1,024, 2,048 and 8,192 each raise `ValueError: unregistered P9II cell` (Appendix B).
- P10-S0's `CELLTYPES` is a fixed registry of 2K/4K, 8K/16K, 8K/4K and 32K/64K.
- The rehearsal whitelists accept only `(4096, 16384, 65536)`: `studies/p10s0/train.py` l.113 and `studies/p9ii/train.py` l.177.

What does work, from reading the code:

- `p9ii.model.build_model` and the memory accept any slot count (`studies/p9i/model.py` l.92–95).
- The trainer takes the fact count from the stream (`studies/p9ii/train.py` l.290), not from the slot registry.
- The generator, panels, held-out templates and read-swap derangement depend on the fact set (2,048 or 8,192), not on slots (`studies/p9/data.py` l.19–30, l.777–785).
- Condition 3's thresholds are fractions of the fixed 256-fact probe set (`studies/p9ii/core.py` l.127, l.188–189).

So the generator and panels work at every proposed size. The training and evaluation path does not, without new code.

Change: §3 and §11 should state that P10-I-S0 needs a new cell type and cell adapter that do not pass through `p9ii.core.Cell`'s registry, plus new rehearsal whitelists. The bit-identity gate should be specified in two parts:

- (a) At 4,096 and 16,384 slots, the new path is bit-identical to P10-S0's path for one forward and one update.
- (b) At each new slot count, the new path's model equals `p9ii.model.build_model(arm, N, seed)` and one update equals a direct reference implementation.

Also add a gate that runs the read swap, the probe-set slot counts and ADDRESS STABLE end to end at 512 and 1,024 slots on the rehearsal draw.

### REQUIRED

**3. REQUIRED: the X8 ceiling is unreachable, and X8 has no cost or cap rule.** (§5.1 ladder and ceiling; §8; §9.)

- The ladder stops at 16,384 exposures, and a plateau at e needs m(4e). So the largest e\* is 4,096 and the largest reachable T is 8,192. "16,384 for X8" can never occur.
- §9 sets the hour cap at the freeze as "twice the projection". But X8's T is only known after its own calibration, which runs after the main grid, so X8 has no projection at the freeze.

Change: either extend the ladder to 32,768 for X8 (its calibration runs then reach 2,097,152 updates per run at 8,192 facts; state the cost), or set X8's ceiling to 8,192. Also do one of the following: include X8 at its ceiling in the frozen projection and cap, or give X8 its own cap rule, fixed now, that uses cost projections only.

**4. REQUIRED: the "blind" rehearsal has no mechanism, and the cuts are chosen after it.** (§5.2.)

"Sealed" is not defined. Stage R necessarily writes probe records every 64 updates and evaluation records with accuracies. Its implementer and launcher see logs. Nothing says where the curves live, who can read them, or how anyone could tell whether they were opened.

Change: state the mechanism, in the style of P9-I and P10-S0, whose rehearsal used a whitelist validator so that no loss or accuracy is written or shown:

- Stage R writes accuracies only to a directory outside the worktree.
- Stdout and logs pass a whitelist validator (time, memory, shapes, counts, identity, and `durations.json` only).
- The sealed file's sha256 is committed at the freeze.
- Only the auditor's recomputation script reads it before the outcome.
- The plateau decision and the "continue up the ladder" decision are made by code, never by a person.

Also fix the decision on the cuts (drop A0, drop X8) **before** Stage R, or allow it on cost only. `durations.json` is a function of A5-D's overload curves: a NOT SHOWN entry forecasts an UNRESOLVED row. Leaking that is minor, but the cut choice should not be able to use it.

**5. REQUIRED: the proposed initialization seeds collide with P10-S0's derived initialization seeds.** (§4.2.)

- The memory initializers derive generator seeds as init + 1000k for k = 1–5: keys +1000, values +2000, `wq` +3000, `wo` +4000, router +5000 (`studies/p9/model.py` l.236, l.272–275; `studies/p10s1/core.py` l.819 `DERIVED_INIT_OFFSETS`).
- P10-S0's init seeds 2001, 2002, 2091 and 2092 therefore derive 3001, 3002, 3091 and 3092. Those are exactly ADR-0023's proposed init, rehearsal and calibration seeds.
- ADR-0023's own derived seeds (4001 … 8092) overlap P10-S0's derived set in 4001–7092. For example, ADR-0023 keys at init 3001 use generator 4001, which is P10-S0's values generator at init 2001.
- P10-S1's gate G9 already treats 3091 as "S0's derived initialization seed (2091 + 1000)" and rejects it (`tests/test_p10s1_rev5_model_and_guards.py` l.185).
- So the sentence "None overlaps an earlier study" is false.

The data ranges are clean. 300001–309999 and 930001–930999 hit no seed in `studies/`, `configs/`, `src/`, `tests/` or `docs/decisions/`, nor any P1–P8 config seed or its derived set.

The sibling drafts are clean against ADR-0023: ADR-0027 uses 270001–279999 with init 2701–2799, and ADR-0028 uses 280001–289999. ADR-0024 to ADR-0026 do not exist in this worktree, so I could not check them.

**Side observation for the lead (outside this review's scope):** ADR-0027's init range 2701–2799 contains 2701 and 2702 (P9's derived 1701 + 1000 and 1702 + 1000) and 2791 and 2792 (P9-I's derived 1791 + 1000 and 1792 + 1000).

Change: choose init seeds whose +1000k derived sets avoid every earlier init seed and every earlier derived set. One option is a block at or above 9001 with spacing over 5,000 from earlier seeds; check it with code. Update the cited namespace list from the code, not from ADR-0020 §7: add P10-S1's 2193, the review-diagnostic seeds 500001–500004 and 941001, and P10-S2's actual 220901–220912. Gate G9 must check derived seeds as P10-S1's `seed_check` does.

Separately (ADVISORY): Stage R uses init 3091 on both calibration draws. P10-S1's revision 5 changed exactly this so that the two calibration runs differ in initialization as well as data (`studies/p10s1/core.py` l.493). Use a different init seed per calibration draw.

**6. REQUIRED: the plateau rule has no floor, and a decline counts as a plateau.** (§5.1.)

- **(a)** P10-S1 revision 5 had to add a floor, i\*(U/2) ≥ 0.473 bits, because "without it every calibration cell met the rule … before it had learned" (ADR-0021 l.349 and l.578). This study's own record has a flat-then-escape case: A0 collapses at update 64 and escapes at a median of 13,664 updates (max 30,656). The draft's rule could plateau on a flat early segment. The §14 engineering-lessons table does not carry this lesson.
- **(b)** "A decline counts as no further gain" lets T = 2·e\* sit beyond a decline. The failure under study is held-out-template generalisation (P10-S0). That is a quantity that can **fall** with longer training as the model fits the trained templates. T would then be read on the falling side, and with CONVERGENCE CONFIRMED (a negative median passes ≤ 0.02) a failure would be worded "NOT QUALIFIED; … not a training-length artefact".

Change (`PENDING LEAD REVIEW` for the numbers):

- (a) Add a floor fixed now: for example, both arms' m_P at e\* must be at least the cell type's evaluability floor (0.90 at load 0.5, 0.50 above it).
- (b) Do one of the following: make the plateau two-sided (|Δ| ≤ 0.01), or keep it one-sided and have the label print **DECLINE IN REHEARSAL** and the registered **m(T) − m(T/2) < −0.02** as **DECLINING AT T**. In the latter case, a failure at a declining load is worded UNRESOLVED, not NOT QUALIFIED.
- Add both to §14.

**7. REQUIRED: the training-length ceiling has no extension rule. This is the case the human lead objected to.** (§5.1 "Ceiling"; §9 row 4.)

DIRECTION §5 allows a design ceiling to be extended "only under a rule written in the specification", and the human lead's stated concern is "we close experiment due to self impose caps". As drafted, a loaded cell type that does not plateau by 8,192 exposures prints CONVERGENCE NOT SHOWN, and the study's answer at that load is UNRESOLVED. That is an end caused by a convenience ceiling.

P10-S1 measured F-OQ at load 8 still gaining 0.016–0.061 bits per doubling at 3,072–6,144 exposures, so this outcome is plausible at loads 4 and 8.

Change: either (a) add a rule, fixed now and applied by code inside Stage R before the freeze and without observing a registered seed, that extends the ladder by up to k more doublings within a stated hour budget when a cell type is NOT SHOWN; or (b) state in §9 why no extension is written, so that the human lead decides this knowingly at Decision 1. `PENDING LEAD REVIEW`.

**8. REQUIRED: the positive meaning overclaims on held-out templates, and A6 is not "ideal addressing" under overload.** (§1 outcome table, "Positive"; §6.5 bullet 1 and the last bullet; §3 table, A6 row.)

- **(a)** Condition 4 compares held-out accuracy with the cell's **own** panel accuracy, not with the oracle. A pass therefore guarantees held-out accuracy ≥ 0.90 × 0.90 = 0.81 of A6's panel accuracy, not "at least 0.90 … on trained and on held-out templates".
- **(b)** Under overload, A6 is a random-code oracle. Its codes collide by chance (Poisson load per slot), whereas a learned query can in principle balance the load. So A6 is not "what the store holds under ideal addressing", and the ratio can exceed 1.
- **(c)** "Because both arms must plateau before T is set, the ratio is not an artefact of one arm still rising" is false wherever the cell type is NOT SHOWN, and it rests on calibration draws only.

Change:

- (a) Reword the positive meaning: "keeps at least 0.90 of the oracle-query reference's accuracy on trained-template panels, and on held-out templates at least 0.90 of its own panel accuracy".
- (b) Replace "ideal addressing" with "the oracle-query (random-code) reference". Print the ratio itself, and add "RATIO ABOVE 1" as a descriptive tag.
- (c) Qualify the plateau sentence: "where the cell type was SHOWN in rehearsal (calibration draws)".

**9. REQUIRED: the operating characteristic of "both series" × "every lower load" is not stated, and the negative meaning is worded too strongly.** (§1 "Negative"; §6.6; §16.)

Let p be the per-cell success probability, with cells independent. P(RELIABLE in one 10-cell series) is:

| p | One series | Both series | Lines hold at 0.5, 1 and 2 in both (L_Q ≥ 2) |
|---|---|---|---|
| 0.90 | 0.736 | 0.542 | about 0.16 |
| 0.95 | 0.914 | 0.835 | about 0.58 |
| 0.97 | 0.965 | 0.932 | about 0.81 |
| 0.99 | 0.996 | 0.991 | — |

So at a true per-cell success rate of 0.95, the study reports "OVERLOAD NOT QUALIFIED" about four times in ten. The rule is conservative against false positives, which is consistent with "never lower the threshold". But §1's "Negative" meaning ("The recipe as calibrated does not carry over …; P10-S0's finding is then not a training-length artefact") states more than a count rule with this false-negative rate supports.

Change:

- Print this table in §6.6.
- Reword the negative meaning to "did not meet the registered RELIABLE criterion in both series at ℓ, at the registered T".
- Replace "not a training-length artefact" with "not explained by training length up to T".

The rule itself is a scientific choice (`PENDING LEAD REVIEW`); I do not propose a different one.

On one init seed per draw: P10-S1's corrected seed-block record shows the data draw dominating the spread in 24 of 28 comparisons (`results/p10s1-run-2026-11-17/ERRATUM_SEED_BLOCK.md`). That supports the choice better than the uncited "P9-I's diagnostics and P10-S0 found outcomes clustered by draw" (ADVISORY: cite it or drop it).

The anchor is read under the 10-cell rule, whereas P10-S0 read the anchor under the 20-cell rule (two seeds; RELIABLE needs no draw with both seeds failed). State that this is a different test from S0's (ADVISORY).

**10. REQUIRED: "only the slot count changes" across loads is false.** (§3 "Comparisons, one change each".)

T is set per cell type, so across loads both the slot count and T change (by rule). The memory tensors also change shape under the same seed.

Change: "across loads within a series: the slot count, and T as set by the rule of section 5; the same facts, streams, panels and initialization seed per draw."

**11. REQUIRED: the cost range omits the ceiling case, and the rates are best-case.** (§11.)

The central figures reproduce, and so does "one step higher" (my figure is 28.9 h against the draft's "about 31"). But if every cell type reaches the 8,192-exposure ceiling, Stage R trains to 16,384 exposures (1,048,576 updates per run at 8,192 facts; the longest single run is 5.45 h at 16,384 slots). The totals are then about 216 (M), 29 (S) and 71 (Stage R) CPU-h, or **about 54 h without X8**, above the stated "15 to 50".

The rates are P10-S0's registered-run rates. Those were 0.57–0.91 of that study's "alone" rehearsal rates and 0.34–0.67 of its busy rates (`timing_out.txt`), so the projection is optimistic for a machine that is also the human lead's working computer.

Change: add the all-at-ceiling row, with and without X8, and state that the rates are the quiet registered-run rates.

**12. REQUIRED: the rationale for the paired-comparison threshold is wrong.** (§6.7.)

"6–0 is the smallest split of ten pairs with a two-sided exact p below 0.05 (0.031)" is true for 6–0. But the rule is d = (A5-D only) − (A0 only) ≥ 6, which also fires at 7–1 (p = 0.070) and 8–2 (p = 0.109).

Change: either make the rule "d ≥ 6 **and** the exact two-sided sign-test p < 0.05", or keep d ≥ 6 and drop the p-value rationale. ADR-0020 also required "X has more successes"; d ≥ 6 implies that.

**13. REQUIRED: the lane licence in §15 extrapolates beyond tested cell types and drops the regime tag.** (§15 items 1 and 2.)

"A cell whose load is at most L_Q and whose slot count lies in 512–16,384" licenses (facts, slots) pairs never run. For example, load 2 at 16,384 slots means 32,768 facts, and only 2,048 and 8,192 facts are tested. It also licenses a REFERENCE DEGRADED qualification without its tag.

Item 2 is inconsistent as well. Row 5 with L_Q = 1 gives no lane at any load, while row 6 with L_Q = 1 gives a lane at load 1 or below. A convergence status at the *failing* load revokes a licence at loads where Line Q held.

Change:

- License only the tested cell types (or the tested fact counts at loads ≤ L_Q) unless the human lead rules otherwise (`PENDING LEAD REVIEW`).
- Carry the reference-regime tag into the lane label.
- Make item 2 depend on L_Q only.

**14. REQUIRED: the draft and the closure ledger disagree.** (§3 "Not run"; `docs/reviews/p10-i-direction-2026-11-17/CLOSURE_LEDGER.md` l.81–85.)

The ledger maps "A5-D against A0 at 16,384", "Record-length-free variant", "65,536 slots" and "Condition 6 decided no class" to **CARRIED INTO P10-I-S0** (the first three marked "(candidate)"). The draft says WX and the 65,536 probe are "not this study's question" and says nothing about condition 6's design note.

Change: either the ledger names another destination (or CLOSED AS RECORDED) for those rows, or the draft states how it disposes of each. The draft should also add one sentence on condition 6 under a degraded reference. P10-S1's DEP condition (a_use ≥ 0.95 × raw accuracy) failed for the reference itself at low accuracy (P10-S1 `ACCEPTANCE.md` ruling 1), and Stage R's reference-validity flag could then make loaded cell types NOT EVALUABLE. `PENDING LEAD REVIEW`.

### ADVISORY

**15. Condition 3 at 512 slots (§6.2).**

My recomputation agrees with the drafter: 201.5 expected distinct slots, and a 0.69–0.73% chance that some slot exceeds 10 sites under uniform placement with both occurrences of a fact on one slot. Under balanced placement at load 4 the figure is 212, with at most 8 sites per slot. If the two occurrences land independently it is 324, with that chance at 5 × 10⁻⁶. So condition 3 is reachable at every proposed size.

It is an absolute count, though. At 512 slots it passes an address that uses a quarter of the slots, so it detects gross collapse only. Add, descriptively, the share of slots that are top-1 for any fact on the full Panel A, beside A6's figure.

**16. Quiet machine and concurrency (§10).** The draft states that no stage needs a quiet machine, which meets DIRECTION §7's requirement. Record the load average periodically, not only at stage start. State how this study's 18 GiB aggregate interacts with sibling P10-I studies running at the same time.

**17. μ and A0 (§3; §16 items 7 and 8).**

The un-recalibrated μ matters more than §3 says. L_div pushes the batch's 128 queries apart, while at load ≥ 1 several facts **must** share a slot, so the penalty partly opposes the configuration that overload requires. The draft words a failure correctly as "a failure of the recipe as calibrated", and §13 states it. A0 in series M is the only way to tell a penalty-induced failure from a load-induced one, so I advise against the "drop A0" cut, or at least fixing that cut before Stage R (finding 4).

The missing dense baseline does not affect the addressing question as posed, provided §13's exclusions stand.

**18. Probe cadence (§4.3).** After 4,096 updates, probes come every 1,024 updates, which makes the escape and COLLAPSE-FREE statistics coarser than P10-S0's every-64. State that their resolution differs from S0's.

**19. Units (§5.1 "Reason for the figure").** "The ceiling for loads up to 4 is above that [393,216 updates]" is true for series M (524,288) but not for series S (131,072 updates). Compare in exposures: 8,192 against P10-S1's 6,144 and 3,072.

**20. Stage R procedure (§5.2).** "Each run continues up the ladder only until the plateau rule can be decided for its cell type" needs a defined, code-driven procedure. For example: all four runs of a cell type are trained in doubling rounds from snapshots, and the rule is evaluated after each round. This needs a resume-from-snapshot test in §10 stage 1.

## 3. The binding constraints, one by one (item 2)

| Constraint (DIRECTION §4) | Status |
|---|---|
| Duration from a preregistered convergence rule fixed by a rehearsal without observing a registered seed | Met in structure: calibration draws, a separate init seed, the rule fixed before Stage R. Weakened by findings 4 (blindness mechanism), 6 (floor and decline) and 7 (no extension rule). X8's calibration runs after the main grid, but on calibration draws and under the fixed rule; acceptable |
| Overload at several loads, so that a failure locates where addressing breaks | Met (1, 2, 4, and 8 conditionally), at power-of-two resolution. The location is unambiguous only after finding 1 (iv) |
| 0.90 of oracle not lowered | Met. Condition 1 is never dropped. The 0.50 floor and the REFERENCE DEGRADED tag are fixed with reasons (§6.5). The reason for the floor is sound (below 0.50 the cell tests the store). Wording per finding 8 |
| A failure is a registered outcome, not a reason to extend | Stated (§1, §9). The m(T) − m(T/2) check on registered draws is a sound device. It only changes NOT QUALIFIED to UNRESOLVED, it cannot create a pass, and it triggers nothing. But §7 should add: "UNRESOLVED is a registered outcome; it is not a basis for a further run on these cells without a new, human-approved ADR". Otherwise "UNDERTRAINING NOT EXCLUDED" becomes the argument for an extension the direction rules out. Its trigger set also wrongly includes NOT EVALUABLE (finding 1 (b)) |

## 4. Limits table against DIRECTION §5 (item 8)

- **Classification:**
  - Resource caps: hours and memory.
  - Design ceilings: T, loads, draws, reserves, calibration draws.
  - Scientific thresholds.

  This is complete, apart from the ladder's top and X8's cap (findings 3 and 7).
- **PAUSED and resumable:** present, but see finding 1 (a).
- **"No limit extended because a partial result looks close":** present.
- **Engineering lessons (§14):** they cover the frozen-ADR commit, resumability, a stage listing unplanned cells, aggregation rules, reference validity, the count gate, platform ties and CI. Missing are the plateau floor (finding 6) and the projection's dependence on machine load (finding 11).

`Astra review: NOT_PERFORMED`. This review is not Astra validation and not a human approval.

## Appendix A: independent check script (verbatim; run as `python3 -I adr0023_checks.py "$PWD"`)

```python
"""Independent checks for the ADR-0023 spec review (auditor's own code; imports nothing from arborlm or studies)."""
import math, sys, tomllib, pathlib
from math import comb, exp, factorial
root = pathlib.Path(sys.argv[1])

print("== 1. seeds: derived init seeds = init + 1000k, k=1..5 (studies/p9/model.py _matrix(seed+1000k))")
D = lambda inits: {i + 1000 * k for i in inits for k in range(1, 6)}
prior_inits = {"P9": {1701, 1702}, "P9-I": {1791, 1792, 1801, 1802}, "P9-II": {1891, 1892, 1901, 1902},
               "P10-S0": {2001, 2002, 2091, 2092}, "P10-S1": {2101, 2102, 2103, 2104, 2105, 2111, 2121, 2112, 2122, 2191, 2192, 2193}}
p23_inits = {3001, 3002, 3091, 3092}
p27_inits = set(range(2701, 2800))
for name, s in prior_inits.items():
    print(f"  ADR-0023 inits ∩ {name} derived: {sorted(p23_inits & D(s))}")
    print(f"  ADR-0023 derived ∩ {name} derived: {sorted(D(p23_inits) & D(s))[:12]}")
    print(f"  ADR-0027 inits 2701-2799 ∩ {name} derived: {sorted(p27_inits & D(s))}")
legacy = set()
def walk(v, key):
    if isinstance(v, dict):
        for k, x in v.items(): walk(x, k)
    elif isinstance(v, list):
        for x in v: walk(x, key)
    elif isinstance(v, int) and not isinstance(v, bool) and "seed" in key.lower() and "offset" not in key.lower():
        legacy.add(v)
for p in sorted((root / "configs").glob("*.toml")):
    if p.name.startswith(("p9", "p10")): continue
    walk(tomllib.loads(p.read_text()), "")
print("  legacy P1-P8 config seeds:", sorted(legacy))
allp23 = p23_inits | D(p23_inits) | set(range(300001, 310000)) | set(range(930001, 931000))
print("  ADR-0023 (incl. derived) ∩ legacy:", sorted(allp23 & legacy), " ∩ legacy-derived:", sorted(allp23 & D(legacy)))

print("== 2. condition 3 at 512 slots, 256 probe facts, two sites per fact, top-1 stable across occurrences")
lam = 256 / 512
print(f"  uniform-random: E[distinct] = {512 * (1 - exp(-lam)):.1f} (exact binomial {512 * (1 - (1 - 1/512) ** 256):.1f})")
p6 = 1 - sum(exp(-lam) * lam ** k / factorial(k) for k in range(6))
print(f"  P(slot gets >=6 facts, i.e. >10 sites) Poisson={p6:.3e}; union bound over 512 slots = {512 * p6:.4f}")
pb = 1 - sum(comb(256, k) * (1/512) ** k * (1 - 1/512) ** (256 - k) for k in range(6))
print(f"  binomial per-slot {pb:.3e}; union bound {512*pb:.4f}; 1-(1-p)^512 = {1-(1-pb)**512:.4f}")
for N in (1024, 2048):
    print(f"  slots {N}: E[distinct] = {N * (1 - (1 - 1/N) ** 256):.1f}")
print(f"  unstable worst case (512 independent sites over 512 slots): E[distinct] = {512 * (1 - (1 - 1/512) ** 512):.1f}; P(slot>10 sites) union {512*(1-sum(comb(512,k)*(1/512)**k*(1-1/512)**(512-k) for k in range(11))):.2e}")
p0 = comb(2048 - 4, 256) / comb(2048, 256)
print(f"  balanced 4 facts/slot, random 256-subset: E[distinct] = {512 * (1 - p0):.1f}; max facts in slot <= 4 -> <= 8 sites")

print("== 3. Clopper-Pearson one-sided 95% lower bounds")
def cp_lower(k, n, a=0.05):
    if k == 0: return 0.0
    lo, hi = 0.0, 1.0
    for _ in range(200):
        mid = (lo + hi) / 2
        tail = sum(comb(n, j) * mid ** j * (1 - mid) ** (n - j) for j in range(k, n + 1))
        if tail < a: lo = mid
        else: hi = mid
    return lo
for k, n in ((10, 10), (9, 10), (9, 9), (8, 9), (19, 20), (20, 20)):
    print(f"  {k}/{n}: {cp_lower(k, n):.3f}")

print("== 4. 'both series' and RELIABLE (<=1 failure of 10) operating characteristic, per-cell success p")
for p in (0.80, 0.85, 0.90, 0.95, 0.97, 0.99):
    one = p ** 10 + 10 * p ** 9 * (1 - p)
    nine = p ** 9 + 9 * p ** 8 * (1 - p)
    print(f"  p={p:.2f}: P(RELIABLE one series)={one:.3f}  both series={one*one:.3f}  (9 evaluated: {nine:.3f})")

print("== 5. sign test 6-0 two-sided exact p:", 2 * 0.5 ** 6, " 5-0:", 2 * 0.5 ** 5)

print("== 6. cost: drafter's assumptions (s/update) and T guesses")
R = {16384: {"A5-D": 0.0172, "A0": 0.0144, "A6": 0.0187}, 8192: dict.fromkeys(("A5-D", "A0", "A6"), 0.013),
     4096: {"A5-D": 0.0102, "A0": 0.010, "A6": 0.0091}, 2048: dict.fromkeys(("A5-D", "A0", "A6"), 0.010),
     1024: dict.fromkeys(("A5-D", "A0", "A6"), 0.010), 512: dict.fromkeys(("A5-D", "A0", "A6"), 0.010)}
M = [(16384, 1024), (8192, 2048), (4096, 2048), (2048, 4096)]
S = [(4096, 1024), (2048, 2048), (1024, 2048), (512, 4096)]
def block(F, cells, arms, T_of, draws=10, rates=R):
    return sum(e * F / 128 * rates[n][a] * draws for n, e in [(n, T_of(n, e)) for n, e in cells] for a in arms) / 3600
def stageR(F, cells, T_of, rates=R):
    return sum(2 * T_of(n, e) * F / 128 * rates[n][a] * 2 for n, e in cells for a in ("A5-D", "A6")) / 3600
g = lambda n, e: e
m, s, r = block(8192, M, ("A5-D", "A0", "A6"), g), block(2048, S, ("A5-D", "A6"), g), stageR(8192, M, g) + stageR(2048, S, g)
print(f"  central: M {m:.1f} CPU-h, S {s:.1f}, Stage R {r:.1f}; six-worker h {m/6:.1f}/{s/6:.1f}/{r/6:.1f}; total+1.5 = {(m+s+r)/6+1.5:.1f}")
R2 = {k: dict(v) for k, v in R.items()}; R2[4096]["A0"] = 0.0144
print(f"  with A0 at 4,096 slots at its measured 0.0144: M {block(8192, M, ('A5-D','A0','A6'), g, rates=R2):.1f}")
up = lambda n, e: 2 * e
m2, s2, r2 = block(8192, M, ("A5-D", "A0", "A6"), up), block(2048, S, ("A5-D", "A6"), up), stageR(8192, M, up) + stageR(2048, S, up)
print(f"  one ladder step up: total {(m2+s2+r2)/6+1.5:.1f} h")
ceil = lambda n, e: 8192
m3, s3 = block(8192, M, ("A5-D", "A0", "A6"), ceil), block(2048, S, ("A5-D", "A6"), ceil)
r3 = stageR(8192, M, ceil) + stageR(2048, S, ceil)
print(f"  all at ceiling T=8,192 e (Stage R to 16,384 e): M {m3:.0f}, S {s3:.0f}, R {r3:.0f} CPU-h; six-worker {(m3+s3+r3)/6+1.5:.1f} h")
x8 = 8192 * 8192 / 128 * 0.010 * 3 * 10 / 3600; x8c = 2 * 8192 * 8192 / 128 * 0.010 * 2 * 2 / 3600
print(f"  X8 at T=8,192 e: {x8:.1f} CPU-h; calibration {x8c:.1f}; six-worker ~{(x8 + x8c)/6:.1f}")
print(f"  longest single Stage R run at ceiling, 8K facts, 16,384 slots, A6: {16384*64*0.0187/3600:.2f} h")
print("== 7. exposures of P10-S1's loaded run lengths: 8K/1K", 393216 * 128 / 8192, " 32K/4K", 786432 * 128 / 32768)
```

Key output:

- ADR-0023 inits ∩ P10-S0 derived = [3001, 3002, 3091, 3092].
- ADR-0023 derived ∩ P10-S0 derived starts with [4001, 4002, 4091, 4092, 5001, …].
- ADR-0027 inits ∩ P9 derived = [2701, 2702]; ∩ P9-I derived = [2791, 2792].
- The ADR-0023 data, test and derived seeds hit no legacy config seed.
- E[distinct] = 201.5. Union bound 0.0069–0.0073.
- Clopper–Pearson bounds: 0.741 / 0.606 / 0.717 / 0.571.
- Operating characteristic at p = 0.95: 0.914 for one series, 0.835 for both.
- Cost: central 55.9 / 8.2 / 18.3 CPU-h, 15.2 h; one step up 28.9 h; all at ceiling 216 / 29 / 71 CPU-h, 54.1 h; X8 43.7 + 11.7 CPU-h.
- Longest single Stage R run: 5.45 h.
- Exposures of P10-S1's loaded run lengths: 6,144 and 3,072.

## Appendix B: feasibility probe (run as `timeout 120 uv run --locked python -`)

```python
import studies.p9ii.core as c
print("SLOTS_BY_SIZE", c.SLOTS_BY_SIZE)
for n in (512, 1024, 2048, 8192):
    try:
        c.Cell(1, "A5-D", n, 1, 0, None, "x"); print(n, "p9ii Cell OK")
    except Exception as e:
        print(n, "p9ii Cell ->", type(e).__name__, e)
import studies.p10s0.core as s0
print("P10-S0 CELLTYPES", list(s0.CELLTYPES))
```

Output:

- `SLOTS_BY_SIZE (4096, 16384, 65536)`.
- Each of 512, 1,024, 2,048 and 8,192 gives `ValueError unregistered P9II cell: x`.
- `P10-S0 CELLTYPES ['2K/4K', '8K/16K', '8K/4K', '32K/64K']`.
- Torch also printed a NumPy-missing warning, which is irrelevant here.
