# Confirmation read — ADR-0025 with the third review's edits and the lead's choices applied

- Object: `docs/decisions/ADR-0025-p10-i-s2-sequential-teacher-transfer.md` at commit `50cee51` (branch `claude/p10-i-s2`, worktree `.claude/worktrees/agent-a43e44d2d4988e3f8`), 668 lines; diff read against `ef5596b`. Read against my `REVIEW3_ADR-0025.md`, ADR-0022 (rev. 5 with addenda, §§11–13, R16, A-B3, lane rulings), `ADR-0022-addendum-combined-tasks.md`, ADR-0029 §§13, 18–20, ADR-0021 §10.3, ADR-0026 §4/§10, `SEED_REGISTRY.md` (Rev. 3), `DELEGATION_2026-11-18.md`, and the P10-S2/P10-S1/P10-I-R code named below.
- Reader: `arbor-auditor` subagent, Claude Opus 5.5. Read-only on that worktree. Independent engineering review; **not Astra validation, not human approval.** `Astra review: NOT_PERFORMED`.
- No training, generation, network or git write. No script was needed: every check is a grep, a hash or arithmetic, listed in section 6.

## Verdict: CONFIRMED WITH THE LISTED CORRECTIONS

No blocking finding. Every edit E1–E15 is applied as given; F1, F2, F5, F7, F8, F10, F11, F14 read correctly. The lead's choices are computable and fixed before observation. One choice can hide a negative (C3); the others cannot favour the memory. Corrections C1–C10 affect code and C11–C14 affect text only. G-items still open are in section 4.

## 1. Corrections that affect code (old → new)

**C1 — two seeds named for the digest (§6 against §4.3 rule 9).** §6: "250908 teacher tokenizer and digest sentences"; rule 9: "Digest: … the first draw of seed 250914 … Regeneration subsample: … the second draw of seed 250914". The rules contradict each other. Rule 9 also does not say whether one generator serves both teachers.
→ §4.3 rule 9: "**Digest:** 4 whole batches (128 sources) of each teacher's Q_fit run, drawn without replacement by a fresh generator seeded 250908 (the same draw indices for both teachers). **Regeneration subsample:** 32 whole generation batches per teacher, drawn without replacement by a fresh generator seeded 250914 for each teacher, over that teacher's stored generation batches after generation has ended." §6 250908: "teacher tokenizer sentences and digest batches".

**C2 — a non-finite value in a registered Part T cell can be resumed past (§8.6, L4).** "A non-finite value … is treated the same way: ENGINEERING STOP — NON-FINITE VALUE". "The same way" includes "In Part T a stopped cell resumes from its last checkpoint once the cause is recorded". MPS training is not bit-reproducible. A divergence at the registered rate is a property of the arm, so resuming until it does not recur is a re-draw chosen on an observed outcome. It can favour whichever arm diverges.
→ append to the NON-FINITE sentence: "A cell stopped on a non-finite value is not resumed. It is recorded with its last finite checkpoint, and a second attempt is the human lead's decision."

**C3 — row 27 can hide a negative (§8.1, §3 row 27).** "If the subsample's denominator is below 0.30, the cell's control conditions are undefined and the cell counts as a gap undefined." That takes ACQUISITION to row 1 and RETENTION to row 1 (NOT EVALUABLE). Both rows come before the negative rows, which read full-panel quantities only. Row 27's "cannot create a positive one" is true, but the rule can hide ACQUISITION-NEGATIVE or RETENTION-NEGATIVE.
→ "If the subsample's denominator is below 0.30, the cell's control conditions are undefined: the margin and marker-only parts of ACQ1 and ACQ2 fail in that cell, CONTROL-FAILED does not fire on it, and it is printed CONTROLS UNDEFINED. Full-panel quantities, the negative zones and ρ are read as usual." Row 27's "Why" becomes: "… The change can remove a positive and cannot remove a negative." This is the lead's choice; it is **PENDING LEAD REVIEW**. The event is very unlikely: P10-S2's full-panel margins were 0.62 and 0.64.

**C4 — the three-way rate tie (§7.1 rule 1).** "The rate with the higher mean … a difference below 0.01 goes to the smaller rate" was written for two values. With three it can chain: 0.300 / 0.305 / 0.312 gives either 0.003 or 0.001.
→ "Among eligible rates (not DIVERGED), the smallest rate whose mean is within 0.01 of the best mean is taken." Apply the same rule to the L ∈ {4, 12} choice, with L = 4 as the "smaller".

**C5 — E-table's rate grid layer (§7.1 rule 1, G1).** It is not stated whether E-table's three-rate grid runs at L = 4 alongside the store or at the store's chosen layer. The 36-unit count fits both.
→ "E-table's rate grid runs after the store's read layer is chosen, at that layer" (more favourable to the baseline, so conservative against the memory). Also add: "a read-layer run that diverges is not eligible; a non-finite loss in the convergence ladder or the pilot stops calibration and returns the work to the human lead."

**C6 — repeated calibration (§6, §7.1 rule 4).** → "In a repetition, draws 2 and 3 take the roles of draws 0 and 1 (the pilot reads M1 of draw 3). Its cap is computed by the same rule from the measuring rehearsal."

**C7 — a non-finite beam score (§8.6 against §4.2).** §8.6 makes any non-finite "score" in a registered record an ENGINEERING STOP. P10-S2's `accepts` (`filtering.py:56–61`), which §4.2 adopts, rejects non-finite beam scores as a registered filter rule.
→ in §8.6, "(a loss, a score, a GEN reading)" becomes "(a loss, a chrF score, a GEN reading; a non-finite teacher beam score is rejected by the filter, counted and printed, as §4.2 says)".

**C8 — config read at import (§11 item 2, F15).** `studies/p10s2/core.py:25,97` loads `configs/p10s2_transfer.toml` at import (`CFG = load_config()`), and `filtering.settings_grid` reads `core.CFG["filter"]`. An import walk lists `.py` files only, so reusing any P10-S2 module puts an unhashed config into the run.
→ append to "The import walk": "Every non-code file a reached module reads at import (for P10-S2's modules, `configs/p10s2_transfer.toml`) joins the set by hash. No grid, threshold or seed of this study is read from P10-S2's config."

**C9 — package mechanism (§13 item 6).**
- "`uv run --locked --with-requirements` on that file is allowed only with `--offline`, when it resolves from the local cache." **Delete this sentence.** It resolves from uv's cache, not from the hash-verified durable copy, so the frozen package manifest would not describe what ran. It is also what ADR-0022's re-check A / R2 forbade (`datagen.sh`: "The requirements file is never an argument of uv run").
- "the one P10-S2 used (`studies/p10s2/launch/datagen.sh`) … under `uv run --locked --offline`" → "P10-S2's mechanism (`studies/p10s2/launch/datagen.sh`, which ran `uv run --locked --extra pilot` with no `--offline`), with `--offline` added and the durable copy's absolute path on `PYTHONPATH`". `datagen.sh` puts `$PWD/data/datagen-packages` on the path, which is relative to the worktree, and the study runs in its own worktree.
- **Scope:** "Part Q's teacher and tokenizer work only: …" → "steps 1–8 of Part Q (step 1's generation-configuration assertion and tokenizer record, and step 8's `sacrebleu` cross-check, included), both Part Q rehearsals, and the regeneration check of the independent recomputation." The current list omits those two items.

**C10 — charged time (L2) and the per-stage cap base (§4.3 rule 7, §10 item 3).**
- "Worker count × wall time of every attempt" → "the sum over worker processes of each process's wall time, every attempt (rehearsals and paused attempts included), as ADR-0022 section 13.2 defines it". The current wording charges allocated workers while they sit idle.
- Per stage, "the time charged before its freeze" is undefined: it could be read as the whole part's pre-freeze charge, counted once for every stage. → "Each registered stage's cap is 2 × its projected time; the part's total cap is the part's charge before its freeze + 2 × the projected time of all its registered stages."
- **Should charged time be wall time on six workers instead? No — keep k·t.** ADR-0022 §13.2 (the predecessor) defines k·t, and ADR-0025's own estimates are sums of unit times, i.e. k·t: §14's 42×5 + 24×8 min = 6.7 h. ADR-0029 charges stage wall time on six workers: "18,700 worker-seconds, 0.87 charged hours on six workers"; `studies/p10ir/core.py:401` "Charged wall time of the study". P10-S1 is mixed: calibration charged as "the sum of the cells' training wall seconds" (`studies/p10s1/calibrate.py:494`), while projections are packed on six workers (ADR-0021 §10.3). Switching would shrink every figure by up to the worker count (2 in Part Q, 3 in Part T) and loosen the 3.0-h rehearsal caps by the same factor. Add one sentence: "ADR-0029 charges stage wall time; figures of the two studies are not on one scale."

## 2. Corrections to text only

**C11 — package authority and what Decision 1 covers (§13 item 6, §17).**
- The committed delegation record keeps "any package outside the lock" with the human lead twice: §3, and again in §6's 24-hour grant ("Still outside the delegation: … packages outside the lock"). Adding the second sentence to the record without a reading that names these 28 packages leaves the record contradicting the use.
- "No package outside the lock is put on any process's path before that sentence is in the committed delegation record" → "… before that sentence, and the lead's reading of it naming the use (no download) of these 28 packages in Part Q and stating how it relates to sections 3 and 6 of that record, are in the committed delegation record".
- §17, "Decision 1 itself rests on the first" → "Decision 1 rests on the first sentence, except the Part Q work that needs the packages (steps 1 and 5–8 and both Part Q rehearsals), which waits for the condition of section 13, item 6."
- Whether "auto approve everything" reaches an item the record twice excludes is a reading for the human lead: **PENDING LEAD REVIEW**.

**C12 — row 21 against §4.4.** "none is planned except the fallback's files if the fallback is invoked" → "none is planned; the fallback is outside this study (section 4.4)".

**C13 — span convention (§4.1, G18).** The shared ledger is read by ADR-0026, which records (row, byte span) per row. → append: "End offsets are exclusive. The row ↔ concatenated-offset map is the cumulative byte length of the rows under A-B3, with nothing between rows. The ledger's path is named in the Part Q plan."

**C14 — tokenization test (a) for R-gloss-icl (§5.2).** "for a seeded sample of training sources" names no seed, so G9 cannot check it. ADR-0022 ran test (a) on every prompt. → "on the R-gloss-icl prompts of every E_A, E_B and D_cal item, with a lexicon built from the whole accepted pool".

## 3. The lead's own decisions, judged

| Item | Judgement |
|---|---|
| Row 25 (TASK-CODED guard) | Correct. ADR-0022 §11.4 had no guard, and the guard can only remove a memory-favouring annotation |
| Row 26 (ACQUISITION order) | Correct restoration. ADR-0022 §11.3 reads row 4 NO-ACQUISITION before row 5 CONTROL-FAILED. ADR-0025's "G_first(M1) < 0.25 in every cell" over six cells of both orders equals ADR-0022's "every replicate, both capabilities". The SECOND TEACHER variant and the CONTROL-FAILED scope were accepted earlier. Listing a "Same" item in the changes table is unusual but explained |
| Row 27 | See C3 |
| Row 28 (R16 narrowed) | Consistent with ADR-0022 R16 (l. 998) and L3; conservative. Advisory: after Q4, even a code error during generation (hours long) needs the human lead. A block-wise resume of generation cannot change Q1–Q4, while Part T may resume after scores exist, so the two parts are held to different standards. The lead may wish to allow generation and panel-output resumes |
| Row 29 | Disclosed; 8,000 / 3,409 = 2.35 |
| F9 (engineering stop, nothing labelled) | Consistent with ADR-0029 ruling 11 (§20 l. 464). Part Q uses the same rule (§4.4 last paragraph). The "failed recomputation" clauses are unreachable second guards, and that is stated. No contradiction |
| Non-finite: registered stop, calibration DIVERGED | Sound, subject to C2, C5 and C7 |
| F3/F4 figures | 3.0 h per measuring rehearsal is ample: Part Q's step 1–8 rehearsal with one 20,000-source block per teacher is about 0.5–1 h k·t at 2–3× P10-S2's rates. Raising once to twice matches §13 item 5. Calibration cap 2 × projected equals the charged + 2 × remaining rule at a stage start. L = 4 is ADR-0022 §12.1's first value. The repetition seeds are inside the allocation (section 5) |
| G21 | Sound and conservative. The ordering in §10 (stage 4 after acceptance), §10's rehearsal paragraph and G21 agree. Advisory: the rehearsal's run of the timing benchmark is not quiet, and its figures are only a duration |
| F12 | Computable. Zero tolerance on tokens; beam scores within 1e-4, printed only. Accept indicators are recomputed from stored scores, so no conflict. Add "deterministic algorithms on" to generation as §11 item 10 sets for scoring. Advisory: run the regeneration check on the rehearsals' own batches, so that a platform that does not reproduce is found before the freeze, not as a registered QUALIFICATION-ENGINEERING-FAILURE |
| F13 | Computable. Ids come from stored segments only. Zero mismatches are required, and a mismatch stops the step (L3) |
| F14 | "Share a byte" is computable; see C13 |
| F15 | The refusal rule is sound: files outside the package are added, so the refusal bites on `studies/p10is2/` files outside `partq/` and `common/`. See C8 |
| Fallback rule | Complete. Every Part Q end other than TEACHERS-QUALIFIED leaves Part T NOT STARTED (§4.4, §15): exactly one teacher failing (quality or exhaustion), both failing, DATA-INSUFFICIENT, ENGINEERING-FAILURE, STOPPED BY DECISION, and an unresolved ENGINEERING STOP (no label, so no acceptance). The invocation stays with the human lead (§4.4, §13 item 2, §17) |
| L1–L12 | L1: add who accepts Part Q (section 4, item 1). L2: C10. L3–L12 are consistent. L7's checker hash `e4623604…7594` is verified |
| Approval record | No overclaim, apart from C11's "rests on the first" and the delegation's "unless an independent review says otherwise", which §13 item 6 discloses. "Not reviewed again" was true at writing. "Not Astra / not human approval" lines are present |

## 4. What an implementer would still guess

1. Who accepts Part Q "as registered", and where. Proposed for L1: "by the lead under `DELEGATION_2026-11-18.md` §2 item 1, after the independent recomputation agrees; recorded in `results/p10is2-partq-freeze-<date>/ACCEPTANCE.md`; an ENGINEERING STOP is not accepted."
2. G15 covers only Q3. If a teacher fails Q1 or Q2, do its Q3 and Q4 still run? Proposed: every remaining Q step of both teachers runs; a failed Q3 leaves that teacher without Q4.
3. The expected WikiText-2 hash source for L10. Proposed: the SHA-256 frozen in P10-S2's data manifest (A-B3).
4. The cap under which the counting rehearsals run ("under those caps": which stage's cap?).
5. Items C1, C4–C7, C9, C10 and C13 until applied.

## 5. Seeds, against `SEED_REGISTRY.md` Rev. 3 §4.2

All new values lie inside ADR-0025's allocated rows. None is used by any code or config in `studies/`, `configs/`, `tests/` or `src/`. The only grep hits for 250918, 251301, 33026x and 33027x are digits inside floats in audit JSON outputs. The ADR correctly avoids 330231 + 10·2 + j, which would equal the rehearsal seeds 330251 + j; the code must use the listed values and not that formula for i ≥ 2.

The registry must add, at its next revision and before the Part Q freeze:
- **Partition-side row:** "250918 route-accuracy WikiText-2 train pieces"; counts 18 used, 81 spare. Also amend 250908 per C1.
- **Calibration row:** "i = 0, 1; a repetition (ADR-0025 §7.1 rule 4) i = 2, 3: bases 251201, 251301, same offsets (+1, +2, +4, +10, +13)"; spare 6 sets.
- **Initialisation row:** "repeated calibration draws 2, 3: 330261 + j and 330271 + j, j = 0..7 (330261–330268, 330271–330278)"; used 66, spare 33 (330279–330297 and 330229–330230, 330249–330250, 330259–330260).

## 6. Commands and environment

Environment: Darwin arm64, zsh; `git`, `grep`, `sed`, `shasum` only. No Python was run and no repository package was imported. The worktree `W=/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/agent-a43e44d2d4988e3f8`.
```
git -C $W log --oneline -3; git -C $W diff --stat ef5596b 50cee51; git -C $W diff ef5596b 50cee51 -- docs/decisions/ADR-0025-...md
grep -n (2509|2510|...|3302|ADR-0025) $W/docs/reviews/p10-i-direction-2026-11-17/SEED_REGISTRY.md; sed -n 150,215p (same)
grep -rl {250918,251201,251301,33026,33027} $W/{docs,studies,configs,tests,src}
shasum -a 256 seed_registry_check_r3.py (e4623604…7594) requirements-datagen.txt (d549380e…8867); grep -c '^[a-z0-9]' requirements-datagen.txt (28)
sed -n 50,65p studies/p10s2/filtering.py; sed -n 145,190p studies/p10s2/core.py; grep CFG/toml studies/p10s2/core.py; head studies/p10s2/launch/datagen.sh
grep -n charged ADR-0021, ADR-0022 (§13.2 l. 435), ADR-0029 (l. 249, 462); studies/p10s1/calibrate.py:493-500; studies/p10ir/core.py:398-425
sed -n 302,401p ADR-0022 (§11–12); grep R16, A-B3, lane rulings; grep ADR-0029 headings and rulings 6, 11; grep ledger ADR-0026
existence checks of every path the ADR cites (all present; the durable copy under the main checkout's data/ does not exist yet, as expected before §11 item 1)
```
Discrepancies of my own: none this read. The REVIEW3 checker attempt that failed earlier (`check3_0025.attempt1_failed.out`) is kept beside this file.

`Astra review: NOT_PERFORMED`. This read is not human approval.
