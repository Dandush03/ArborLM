# Audit P10-I-S2-D0 #2 — comparison of the independent recomputation with the implementer's run

**Verdict: RECOMPUTATION AGREES** (comparison attempt 2; attempt 1 failed because of a defect in my own checker, kept, defect 1 below).

Auditor: arbor-auditor, Claude Opus 5.5 (`claude-opus-5-5`, from this session's header), 2026-11-25 (UTC 07:20 to 07:35). `Astra review: NOT_PERFORMED`.
This is independent engineering evidence, not Astra validation and not human approval. POST-HOC EXPLORATORY DIAGNOSTIC OF AN OBSERVED RUN; NOT A
REGISTERED LABEL. Every pass is under the oracle route. Written through the consolidation worktree's `experiments` link.

## Order kept

1. Before any implementer output was opened, `shasum -a 256 -c audit_d0_out/auditor_sha256_20261125T071351Z.txt` gave 116/116 OK. My numbers
   (audit #1) were written and hashed at 07:13:51 UTC. The implementer's report step ran at 07:24:20 UTC.
2. Then the comparison: `python3 -I audit_d0_scripts/d0a_compare.py` (attempt 1, output `audit_d0_out/compare_20261125T072647Z.json`), then
   `python3 -I audit_d0_scripts/d0a_compare2.py` (attempt 2, output `audit_d0_out/compare_20261125T072658Z.json`). Stdlib only, read-only on both sides.

## Results (attempt 2)

- **Passes:** 120 pairs compared (96 counted + 24 reproduction): 120,000 greedy sequences, **0 differing**; 120,000 item scores, **largest
  difference 4.4e-16** (tolerance 1e-6); the 120 stored pass means agree to 5.6e-17.
- **Derived readings** (702 numbers, tolerance 1e-9; largest difference 1.6e-15):
  - per pass: s, G, share of items differing from the reference pass;
  - first capability: T, (i), (ii), (iii), residual, values-first terms, interaction, every share of T, G units, every standard error;
  - append point: (i), (ii), T, their standard errors, and final-minus-append;
  - second-capability block, including e(1) on E_second and its standard error;
  - counterfactual RET arithmetic for c and g(1): F, rho, the cost s[a]−s[c], G_second under c and under a, and s[a]−s[g(2)];
  - registered-scale arms: 144 values, identical to `registry.json`.
- **Words:** path order MIXED / MIXED; values-first MIXED / MIXED; final wording MIXED / MIXED (no ORDER-DEPENDENT on either side); cells with T ≤ 0:
  none / none. Counterfactual words: c DOES NOT HOLD and g(1) DOES NOT HOLD in all six cells on both sides.
- **The r2 AB boundary:** the implementer's (iii)/T is 0.6670709232254919, identical to mine. Both count it as ≥ 2/3, so both give 4 cells with
  (iii) ≥ 2/3 T in path order and 0 with (i)+(ii) ≥ 2/3 T. Values-first: 3 and 0 on both sides. All 24 per-cell cut-off booleans agree.
- **Read statistics:** 1,584 values (mean, median, p5, p95) plus 360 counts and 18 gate vectors; largest difference 3.7e-8 (float32 reads).
  All their keys map onto mine: `displaced` = 8 − n_p; `other_part` = my ‖e(o)‖/‖R_ref‖. Their `undefined` counts are 0 everywhere.

## Lead Decision 1 and the finalize route

- `git diff e74cbf25 ffd29d74 --stat` touches five files: LEAD_DECISION_1.md, `studies/p10is2d0/finalize.py` (1 line), the new
  `finalize_only.py` and two test files. **No computing file is touched.** The single changed line is the stats loop of `finalize.render`: skip any
  entry that is not a dict with `panel`. `build_records` (the arithmetic) is untouched. Reads, gates, passes, workers and the driver are unchanged.
  `ffd29d74..6bf48cfe` adds records under `results/` only.
- `finalize_only.post_pass` performs the driver's post-pass block line for line: build_records, stats mapping, cost, render, readings, stats,
  gate_record and cost records, the Part T after-manifest and diff, run_complete. The only differences are the commit/note strings and the
  `run_complete.json` fields (`launch_commit` and `finalize_commit` in place of `commit`). Its refusals (exact record counts, no report or
  records present, clean tree, code difference limited to the allowed files) are stricter than the driver's. Nothing in it can change a number.
- `inputs/record_hashes_before_finalize.json` holds 130 entries (96 passes, 24 gate passes, 6 stats, 4 gate files). Every one matches the current
  file bytes, which are the files I compared. No file is unhashed and none is missing.
- Every pass, gate-pass and stats record has an mtime at or before 02:18:05 EST. The fix commit is 02:24:15 EST, so all counted numbers come from
  the launch commit e74cbf25 (`launch.json`). `resumes.json` records the cause.
- My assessment: the decision is technically sound and, in my view, the single-run claim holds. All 96 counted passes were computed once at
  e74cbf25, and the report code that changed only formats text. The output agrees with an independent implementation to 1.6e-15. **One point
  for the human lead (PENDING LEAD REVIEW, not a defect I can settle):** ADR-0035 section 8.3 covers "a resume … from completed per-pass records
  that nobody has opened", but it does not say whether that resume may run at a different commit. Lead Decision 1 treats a report-only code fix
  as such a resume. I can verify the record hashes and timing, but not the statement that the coordinator saw only key names and scalar values
  of one stats file.

## Part T run directory and cost

- The Part T file list after the comparison is identical to my before-list: 412 files, list SHA-256 ec4c66d8…caa8, at three points (before my
  run, after my run, after this comparison). The implementer's own `partt_run_dir_diff.json` is empty.
- **Cost claim 7.714 worker-hours of 8.0: confirmed.** The eight ledgers sum to 27,771.17 s = 7.7142 h, matching `run_complete.json` (7.714214):
  - gate workers 1,923.9 + 1,954.1 + 1,947.2 s (the 24 reproduction passes are included);
  - main workers 7,151.8 + 7,251.2 + 7,264.0 s;
  - orchestrator 278.4 s;
  - finalize 0.44 s.

  The main-worker spans are consistent with their start time (05:17:01Z) and the last record mtime (07:18:05Z). The margin to the cap was
  0.29 h. My recomputation used 6.51 h of its own 8.0.
- The D0 worktree is clean at HEAD 6bf48cfe; nothing of mine was written there.

## Defects (numbered)

1. **Mine, checker:** comparison attempt 1 reported 36 differences. All were in read-statistics p5/p95 for `displaced`: I mapped the implementer's
   `displaced` = 8 − n_p onto my n_p quantiles without reflecting the tails. Reflection swaps them: p5(8 − n) = 8 − p95(n). Attempt 2
   (`d0a_compare2.py`) fixes only that mapping, and all 36 then agree exactly. The attempt-1 script and its output are kept.
2. **Implementer, cosmetic:** `records/cost.json` gives 7.714114 h (27,770.81 s) and `run_complete.json` gives 7.714214 h. The 0.36 s gap is
   the final ledger tick after `cost.json` was written. No consequence.
3. **Implementer, presentation (not a number difference):** in the second-capability block, shares of T2 are `null` (T2 < 0 in every cell). My
   report prints them (they are large and of mixed sign). The ADR says "the same arithmetic … may have either sign" and does not settle whether
   shares of a negative total are printed. Every underlying term agrees.
4. **Implementer, schema:** `run_complete.json` from the finalize route has `launch_commit`/`finalize_commit` and no `commit` key, unlike the
   driver's. Any consumer reading `commit` must be told. No number is affected.
5. **Mine, process (stated in audit #1):** in three cells, my counted M1, app-a and final-a passes came from my own gate sequences through a
   bit-exact memo. In the other three cells they were decoded again and are identical.

No defect changes a number, a word or a cut-off count.
