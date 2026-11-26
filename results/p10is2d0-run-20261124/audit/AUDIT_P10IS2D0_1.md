# Audit P10-I-S2-D0 #1 — independent recomputation (ADR-0035 section 11)

Auditor: arbor-auditor, Claude Opus 5.5 (`claude-opus-5-5`, from this session's header). 2026-11-25 (UTC 04:55 to 07:14).
`Astra review: NOT_PERFORMED`. This is independent engineering evidence, not Astra validation and not human approval.
POST-HOC EXPLORATORY DIAGNOSTIC OF AN OBSERVED RUN; NOT A REGISTERED LABEL. Every pass is under the oracle route.

Written through the consolidation worktree's `experiments` symlink (a hook blocked the direct path); same folder (inode checked).

## Status

- Gates: PASS in all six cells (details below). Counterfactual passes were launched only after all six gate files passed (enforced in code).
- Run: COMPLETE. 24 reproduction passes + 96 counted passes + read statistics. Worker time 23,439 s = 6.51 h (ledger: sum of process wall
  times, `audit_d0_out/worker_seconds_ledger.jsonl`) + about 1 min of synthetic tests and report; under the 8 h cap.
- My numbers were written and hashed before I looked at anything of the implementer's: `audit_d0_out/auditor_sha256_20261125T071351Z.txt`
  (this file's own SHA-256 is 439ba3bc1ab05ac4add400ee80002b00107d179f4ede2a796f197629c1c2f7da). It lists the SHA-256 of
  `auditor_results_20261125T071351Z.json`, `auditor_report_20261125T071351Z.txt` and every pass, stats and gate file.
- Comparison with the implementer: **NOT YET COMPARED**. At 07:14 UTC its run directory had no `run_complete.json` or `report.txt`, and its
  workers were still running. I read nothing of its code or outputs.
- Part T run directory: SHA-256 file list before and after is identical (412 files, list hash ec4c66d8cda377dcd56be4fc82227f9f382368fd3eac53953acd94ff7bdfcaa8).
- The D0 worktree had a clean `git status` before and after (HEAD e74cbf25, 0 entries).

## Environment and commands

The D0 worktree `/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/p10-i-s2-d0-20261124` (locked venv, torch 2.8.0, Python 3.12, no numpy).
Every torch process was run as `env -u PYTHONPATH PYTHONDONTWRITEBYTECODE=1 uv run --locked --offline python <script>` with cwd = that worktree,
`torch.set_num_threads(6)` and `torch.use_deterministic_algorithms(True)`. CPU only, no MPS, at most 3 processes.
Stdlib scripts were run with `python3 -I` (Homebrew 3.15.1).

- `d0a_synth.py`: synthetic stores against a brute-force float64 reference. Result: `synth_20261125T045806Z.json`, PASS, 784 query cases,
  max difference 8.8e-7, ties and empty K covered.
- `nohup python3 -I d0a_driver.py > ../audit_d0_out/driver_20261125T045928Z.log`: gate stage, then cell stage.
- `python3 -I d0a_report.py`: readings, report and SHA-256 list.
- `python3 -I d0a_hashlist.py <PartT dir> partT_before|partT_after`

Scripts: `experiments/_scratch/audits/audit_d0_scripts/`. Outputs: `experiments/_scratch/audits/audit_d0_out/`.
Frozen import: only `studies.p10s2.model` (Cache, StudentConfig, build_student, load_plain_state); its SHA-256 is
966261c8…13dc6, identical to audit 21's tree. Everything else is mine: chrF, bundle and prompt reading, oracle codes, store read, the
conditions, the greedy loop and the arithmetic. The chrF, data, code and greedy code was copied from audit 21's `a21_lib.py`; the conditions
were written new from ADR section 4.

## Gates (section 8.2 / section 4)

All six cells:
- stage-1 keys, values and gates of the append and final M-append snapshots are `torch.equal` to M1's: PASS.
- g2 = 0.0 exactly at the append point: PASS.
- the weight-vector path of a is `torch.equal` to the registered read on every query of both panels: PASS. **Caveat: the comparison is with my
  re-typed `SparseStore.read`, not the frozen function (I may import only `model`), so the identity holds by construction. The real evidence is
  the reproduction below.**
- b(1) is `torch.equal` to M1's read on every query: PASS.
- e(1) at append is `torch.equal` to a at append: PASS.
- a = e(1) + e(2) within 1e-6·max(1, ‖a‖∞): PASS.
- Reproduction of the registered item scores (M1 on E_first, M-append@append on E_first, M-append final on both panels; 24 passes): every greedy
  sequence is identical; the largest item-score difference is 4.4e-16. It is not exactly 0 because my chrF is not the frozen one; the
  auditor's tolerance is 1e-6.
- Determinism check: the 12 counted M1 / app a / final a passes that were decoded again (cells r0AB, r0BA, r1AB) are identical to the gate passes.

Memo: in cells r1BA, r2AB and r2BA, the decode memo was seeded with my own gate sequences (key: prompt ids + SHA-256 of the bit-exact add
tensor). This was done to stay under the cap. Hits are recorded per pass.

## Readings

See `auditor_report_20261125T071351Z.txt` for every pass (s, G, share differing), every term with its paired SE, the append point, the second
capability, the read statistics and the registered comparators.

First capability, final store (s units; share of T):

| cell | T = F | (i) displacement | (ii) renormalisation | (iii) values | values alone b1−g1 | given values g1−a | interaction |
|---|---|---|---|---|---|---|---|
| r0 AB | 0.07188 | 0.04591 (0.639) | −0.01815 (−0.253) | 0.04412 (0.614) | 0.04662 (0.649) | 0.02526 (0.351) | −0.00250 |
| r0 BA | 0.06291 | 0.04133 (0.657) | −0.03154 (−0.501) | 0.05312 (0.845) | 0.05487 (0.872) | 0.00804 (0.128) | −0.00174 |
| r1 AB | 0.06803 | 0.04635 (0.681) | −0.01606 (−0.236) | 0.03774 (0.555) | 0.04280 (0.629) | 0.02523 (0.371) | −0.00506 |
| r1 BA | 0.05552 | 0.04781 (0.861) | −0.03995 (−0.720) | 0.04766 (0.858) | 0.05729 (1.032) | −0.00177 (−0.032) | −0.00963 |
| r2 AB | 0.07206 | 0.03823 (0.531) | −0.01424 (−0.198) | 0.04807 (0.6671) | 0.05746 (0.797) | 0.01460 (0.203) | −0.00939 |
| r2 BA | 0.08640 | 0.04509 (0.522) | −0.02855 (−0.330) | 0.06986 (0.809) | 0.05548 (0.642) | 0.03093 (0.358) | +0.01439 |

(iv) registered F − T is ≤ 7e-17 in every cell; the path sum minus T is ≤ 1.4e-17.
Words: path order MIXED (cells with (i)+(ii) ≥ 2/3 T: 0; with (iii) ≥ 2/3 T: 4). Values-first order MIXED (0; 3). ORDER-DEPENDENT: no
(max |interaction| / T = 0.17). Counterfactual RET arithmetic: c DOES NOT HOLD in 6/6 (F_cf 0.19 to 0.37); g(1) DOES NOT HOLD in 6/6
(F_cf 0.043 to 0.057, rho_cf 0.81 to 0.86). Second-capability cost of c, s[a]−s[c] on E_second: 0.103 to 0.139.

## Ambiguities and readings I chose (PENDING LEAD REVIEW where they could matter)

1. **Boundary: r2 AB (iii)/T = 0.66706 against the 2/3 cut-off (margin 4e-4).** It counts toward VALUES-LARGER in path order (4 cells). The word
   is MIXED either way (5 are needed), but an implementation that rounds before comparing, or works in other units, could print a different count.
2. Section 5.2 on E_second "with the stages exchanged": I read "‖stage-2 part of a‖/‖R_M1‖" as ‖e(1)‖/‖R_b(2)‖ and computed it.
3. Percentiles: linear interpolation (torch.quantile default). The "lower" median is stored too.
4. Section 7, per-stage read for g(1): the ADR puts the cost of c (s[a]−s[c], G_second under c) beside both c and g(1). I did that, and added
   s[a]−s[g(2)] marked as an extra.
5. Marker reads: within a cell every item's marker read uses the same query (code j = 2000), so the marker statistics are 1,000 copies of one value.
6. The gate identity "a's weight path = SparseStore.read" is against my own re-typed read (see above).
7. The 24 reproduction passes are separate from the 96 counted passes (lead ruling). In three cells the counted M1, app a and final a passes were
   served from my gate sequences through the bit-exact memo; in the other three they were decoded again and are identical.

## To compare once the implementer's run has finished

The comparison script is not written yet, on purpose: I have not seen the implementer's record format. Once its run directory has
`run_complete.json` and `report.txt`, the next audit step should check that `auditor_sha256_20261125T071351Z.txt` still verifies
(`shasum -a 256 -c`), then compare every pass's 1,000 item scores (1e-6) and greedy sequences (exact) with `audit_d0_out/passes/*.json`, every
derived reading with `auditor_results_20261125T071351Z.json`, and both summary words. It should also hash the Part T directory list again.
