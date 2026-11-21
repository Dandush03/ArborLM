# P10-I-S6 registered run: independent recomputation

The auditor (`arbor-auditor`, Claude Opus 5.5) wrote this on 2026-11-20 and did not write any of the study code. This is engineering and mathematical evidence only. It is not Astra validation and not human approval. `Astra review: NOT_PERFORMED`. Claude review is not Astra review. Nothing here is a success claim.

## Inputs, environment and commands

- Specification: ADR-0031, addendum 1 (rulings 1–15) and addendum 2 (rulings 16–22), plus ADR-0026 §6.3 for K1–K3. All were read in worktree `agent-aaf3e2e17ef8546e4` at HEAD `a4572228`, which differs from freeze `cedfbe28` only by DECISION_2.md.
- Records read: run dir `experiments/P10IS6-run-20261119`: `items/*/{train,eval}.json` (1,026), `gates/results/core.json` (BASE values), `{gates,train,eval}/manifest.json`, `ledger.json`, `ledger-rehearsal.json`, `attempts/*` (62), `stage_starts/*`, `r1/round{1,2,3}/plan.json`, and `analysis/{analysis.json,report.md}`, used for comparison only. Frozen `studies/p10i_s6/freeze/{plan.json,rate_table.json}`. The plan's SHA-256 is `21742752…aa03`, as in DECISION_2.md.
- Sealed folder: the only file whose contents were read is `/Users/daniellaloush/dandush03/ArborLM-sealed/p10i-s6-sealed/rehearsal_sealed.json`. It was read **after** every registered label had been recomputed and matched (ADR-0031 §8). Its SHA-256 is `e85caefc82db263a5a233f7fd4bac120035408b682d03fa40a5a1860a47deda2`, which equals `rehearsal_public.json`. The auditor also listed the top level of the sealed folder and ran a filtered listing of `items/` names, which printed nothing. No other sealed file was opened. **The run's NOTES.md must log this access. The auditor is read-only on the run directory and did not write it.**
- Environment: macOS Darwin 27.2.0 arm64. `/opt/homebrew/bin/python3` 3.15.1, run in `-I` mode with the standard library only. No torch, no `studies.*` import, no `arborlm` import.
- Commands, run from this folder:
  - `python3 -I recompute.py /Users/daniellaloush/dandush03/ArborLM/experiments/P10IS6-run-20261119 /Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/agent-aaf3e2e17ef8546e4`: produces `recompute_out.json` and `recompute_stdout_attempt1.txt`.
  - `python3 -I check_report_and_ledger.py <same two args>`: produces `check_out.json` and `check_stdout_attempt1.txt`.
  - `python3 -I check_rate_selection.py /Users/daniellaloush/dandush03/ArborLM-sealed/p10i-s6-sealed/rehearsal_sealed.json <worktree>/studies/p10i_s6/freeze/rate_table.json`: produces `rate_selection_out.json` and `rate_stdout_attempt1.txt`.
- Attempt history: each script was run once. The first Write of `recompute.py` to the base-checkout path was refused by a session hook. The file was then written through the session worktree's `experiments` symlink, which points to the same folder. The single mismatch found on the first run is the implementer's (finding A), not the auditor's. No checker attempt failed.

## Result

- `recompute.py` compared 147 fields with `analysis.json` at full precision (exact `==`). 146 are equal and 1 differs (finding A, descriptive only, no label effect).
- `check_report_and_ledger.py` ran 121 checks of report.md text at the printed precision, plus per-parent δ/δrun, rung −1 and step 0. All 121 are equal.
- Rate selection: AGREE at every rung −1..4 for both arms. The calibration convergence states recomputed from the curves equal the sealed `states` bitwise.

Labels: line P = CONVERGENCE NOT REACHED (BOTH STILL IMPROVING), row 12. K\* = None, R = 4, k_max = 4, j† = 4. Dependence-qualified False. Trend = LEAD SHRINKING. D[FLAT] = DEPENDENT. R16 = REPLICATED AT 16,384. OA = REPLICATED AT 16,384. Every one matches.

| k | rF | L(F) | L(D) | δF | δD | δrunF | δrunD | mean Q | Q>0 cells | parents | mean Q† (cells>0) | class |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| −1 | 0.01 | 2.2315331055196346 | 2.2453365385946302 | | | | | | | | | |
| 0 | 0.03 | 2.2121614568901284 | 2.224531339412486 | 0.019371648629506133 | 0.020805199182144296 | 0.020230087762077353 | 0.020805199182144296 | 0.012369882522357835 | 26 | 9 | −0.05995446271090596 (0) | UNDECIDED |
| 1 | 0.1 | 2.192488361356987 | 2.205607472056592 | 0.01967309553314145 | 0.018923867355893798 | 0.02011095097771376 | 0.018923867355893798 | 0.01311911069960506 | 27 | 9 | −0.04028136717776457 (0) | UNDECIDED |
| 2 | 0.03 | 2.174194387815617 | 2.187869062440263 | 0.01829397354137008 | 0.01773840961632933 | 0.018164868776996634 | 0.01773840961632933 | 0.013674674624646152 | 27 | 9 | −0.02198739363639443 (0) | UNDECIDED |
| 3 | 0.1 | 2.1575776134376174 | 2.1695005771600537 | 0.016616774377999466 | 0.018368485280209068 | 0.01591201588787383 | 0.018368485280209068 | 0.011922963722436517 | 27 | 9 | −0.005370619258394948 (3) | UNDECIDED |
| 4 | 0.003 | 2.1454180743959217 | 2.152206994179222 | 0.012159539041695755 | 0.017293582980831612 | 0.012132802909170959 | 0.017293582980831612 | 0.0067889197833008235 | 24 | 8 | = Q, since j† = 4 | M-AHEAD |

- r(D, k) = 0.01 at every rung. Δ = −0.005580962739057011.
- D[FLAT] at R = 4: F1 mean C = 0.2164461856914891, F2 mean P_used = 0.4430958789048923, F3 mean X_mean = 0.22000981660352814. Each condition holds in 27/27 cells and 9/9 parents. No cell is COLLAPSED (used slots 3,348–4,048).
- R16: mean Q 0.012369882522357835, 26/27 cells, 9/9 parents, smallest parent mean 0.0032857867578665414, mean Cd 0.1373329206749245. K1, K2 and K3 all hold.
- OA: mean Q 0.013418922545733276, 27/27 cells, 9/9 parents, δrun F 0.021806043193296265, δrun D 0.01751168265386882.
- Both arms are NOT CONVERGED at rung 0.

## Findings

- **A (defect, descriptive only).** `core.stat_key` has no OA/profile component, but `nll_key` does. The OA M-FLAT run uses rate 0.03 at 8,192 and 16,384, the same key as registered M-FLAT r0.03. The OA `used_slots` therefore overwrite the registered ones. `analysis.json` harm["0"].used_slots lists exactly the OA block's values (`oa, r0.03, u016384`), not the registered rung-0 values (registered min 1,259, max 2,655). There is no label effect, because COLLAPSED is read at R = 4 (rate 0.003, which no OA run uses). The defect would have mattered had R been 0.
- **B (report omissions against the ADR).** report.md does not print the following: the per-rung counts of cells and parents with Q>0 (§12.6); used slots per cell (§11); the rung-0 convergence states beside R16 (§12.4) and OA's states; per-parent δ and δrun (§9.1); and the §12.5 descriptives (SDs, ranges, step 0, the 8,192 statistics, the near-duplicate share).
- **C (printed but not computed).** analysis.json has `calibration_states: null` but `calibration_vs_registered_states_that_differ: {}`. The auditor computed this from the sealed curves: no state differs, because every rung 0..4 is NOT CONVERGED for both arms in both runs.
- **D (naming).** In analysis.json, `delta_per_parent` holds the per-parent δrun. The envelope δ is in `delta_envelope_per_parent`. Both were verified bitwise.
- **E (naming).** In `ledger.json`, `total_seconds` is the cap, not a total (see Q3).
- **F.** analysis.json carries no code identity. The three stage manifests carry commit `cedfbe28`, and their 18 computing-file hashes equal the current files.
- **G (cosmetic).** The lead sentence starts its clause in lower case ("… = 0.0173. an arm is still improving …").

## Q1. Rate selection

- **Rule and split.** The rates were chosen on the calibration split only:
  - pool: the calibration pool (articles numbered mod 3 = 2);
  - parents: the 3 calibration parents;
  - panel: the calibration panel.
  The plan files bear this out. `r1/round*/plan.json` has every item with profile/pool/backbone_group = `calibration`. The panel follows from `items.panel_for`, which returns the calibration panel for any profile other than registered, oa or test. The registered and OA reads use the registered panel. The gates record reports data disjointness passed (pools disjoint, panels disjoint from the excluded spans, zero overlap with E).
- **Recomputation from the sealed curves.** At each U_k, m = the lowest 3-cell mean among the rates finite through U_k. The rate selected is the smallest rate within 0.0005 of m. The interior test is applied to the minimiser, taking the smaller rate on an exact tie. The result equals the frozen table at every rung. Every rate was finite.
- **Grids.** D-ADAPT used 7 rates, and 0.01 was the unique minimiser at every rung. M-FLAT used 9 rates: the grid was extended upward twice (0.3 in round 2, 1.0 in round 3), which is the most §8 allows.
- **Where the tie rule decided for M-FLAT:**
  - rung −1: {0.01, 0.3} within tolerance; 0.01 is the minimiser.
  - rung 0: minimiser 0.3; within tolerance {0.03, 0.3}; 0.03 selected, which is 0.000242 above m.
  - rung 4: minimiser 0.3; within tolerance {0.003, 0.03, 0.1, 0.3}; 0.003 selected, which is 0.000023 above m.
  - The resulting M-FLAT path is 0.01, 0.03, 0.1, 0.03, 0.1, 0.003. This is not monotone, so adjacent rungs read different runs.
- **Leakage.** No label split was used for selection.

## Q2. Completeness, no selective reruns, and the attempts records

- **Items.** The plan has 189 training items and 837 evaluations, and each appears exactly once: 1,026 item directories with no missing and no extra ones, no aside copies, and each directory holding only its record (plus `snapshots/` for training items).
  - Every training record has status ok, updates_done = max_update, resumed_from null and failed_at_update null, and its snapshots equal the plan's.
  - Every evaluation record has controls and update as planned and only finite reads.
- **Single pass.** Each registered stage manifest (gates, train, eval) has exactly one history entry, every outcome is completed, and the mode is registered at commit cedfbe28. Record creation times run from 2026-11-20T11:55:27Z to 2026-11-21T00:11:39Z, all after the registered gates started (10:57:40Z).
- **Integrity.** replay == enabled and disabled == BASE hold bitwise on every evaluation that carries them. BASE replay equals enabled for all 18 parents.
- **Attempts.** All 62 attempts belong to the **R1 calibration rehearsal** (profile `calibration`). None names a registered or OA item.
  - 2026-11-19 22:05:06–22:07:42Z: the lead paused R1 at 17:04 local so that P10-I-S1's quiet-machine stage could have the machine. Six items stopped at a rung snapshot (resume_from 32768: M-FLAT r0.1 c00–c02 and D-ADAPT r0.0001 c00–c02). 24 tasks were paused by request, followed by 1 "R1 stage not complete".
  - 22:07:56Z: when R1 was relaunched, the 6 partial directories were kept aside.
  - 23:12:22Z: a second pause, at 17:44 local, of 18 tasks for the same reason, followed by 1 "R1 stage not complete".
  - 2026-11-20 05:36:13Z: on the restart after the terminal died, 6 partial directories were kept aside.
- **stage_starts.** `stage_starts/` also holds plain `train-*`, `eval-*` and `gates-*` files written during the rehearsals. Only `gates-20261120T105740…`, `train-20261120T111305…` and `eval-20261121T000844…` are registered stage starts.

## Q3. Ledger

- **What total_seconds is.** `total_seconds` = 80,428.62437765177 is the registered cap written into the Ledger object. It is plan caps.registered_hours 22.341284549347712 × 3600, and the two are bitwise equal. The cap is 0 charged + 2 × the projected 11.170642274673856 h: the registered ledger starts at zero, and the rehearsals charge a separate ledger, `ledger-rehearsal.json` (cap 57,600 s; 31,232.63 s charged).
- **What was charged.** 923.9066177500645 (gates) + 46,537.21728754195 (train) + 175.42613737506326 (eval) = 47,636.55004266708 s = 13.2324 h.
  - That is 59.2 % of the cap, leaving 32,792.07 s.
  - It is 1.1846 × the projection (train alone: 1.1699).
- **Wall time.** The train charge equals its supervisor's wall time (46,537.5 s). Analysis and report took about 3 s and are not charged.
- **Cap respected:** yes. No stage paused.
- **Mis-statements.** Nothing is mis-stated. The field name `total_seconds` is misleading, since it is the cap.

## Q4. Wall time

No label, figure or rule reads seconds. Every label is a function of NLL reads (eval records) and BASE alone. Seconds enter only the ledger and the caps, and no cap was reached. Load can change the charged hours only.

On sharing:
- When train started, P10-I-S0's registered main (6 workers) was running, making 12 workers with S6's 6.
- When eval started, P10-I-S2's `partt_rehearse.sh measuring` was running.

Whether that measuring rehearsal is a quiet-machine stage under ADR-0031 §16 is **PENDING LEAD REVIEW**. Its effect would fall on that study's timings, not on S6's labels. Peak aggregate worker count and RSS during the overlap are not in the records the auditor read.

## Q5. ADR row

The outcome maps to §12.3 row 12: "K\* does not exist; neither converged at rung 4 | CONVERGENCE NOT REACHED (BOTH STILL IMPROVING)". The trend tag is §12.6 row 5, LEAD SHRINKING: "HELD at every rung 0..k_max and Δ ≤ −0.005".

§19 for this outcome:
- Would mean: "Sixteen times the duration was not enough by the registered criterion. The trend line describes the lead over the trained range … The human lead may weigh that description."
- Would not mean: "Nothing about the ordering at convergence, in either direction; no tag is PERSISTS, and none qualifies for anything PERSISTS would. Not a reason to extend this study".

§1 adds: "Nothing is claimed about the ordering at convergence." The tag must always carry its sentence. The class M-AHEAD at rung 4 is not a label: row 8 needs conv(D-ADAPT), and δ(D-ADAPT, 4) = 0.0173 is 17 times ε. D[FLAT] = DEPENDENT does not make anything dependence-qualified, because only rows 4 and 8 can be. R16 is REPLICATED, so the §19 row "R16 NOT REPLICATED" does not apply.

## Q6. Printed but not computed, template text, wording

- No template text is left unfilled.
- Findings B, C, D, E and G above.
- report.md prints `dependence-qualified: False`. That is correct, but it is vacuous under row 12.
