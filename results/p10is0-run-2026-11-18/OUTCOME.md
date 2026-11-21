# P10-I-S0 — outcome record (registered run of 2026-11-18 to 2026-11-20)

Status: OUTCOME RECORDED AS REGISTERED by the scientific lead (Claude Fable 5.2) under the human lead's P10-I delegation of 2026-11-18. Not a success claim. ArborLM is unproven research. Independently recomputed by the arbor-auditor subagent (Claude Opus 5.5); Claude review is not Astra review. `Astra review: NOT_PERFORMED`. The human lead has not yet reviewed this record.

## Identity

- Specification: ADR-0023 and its addenda. Freeze commit `58cef50acb61d5cc2beea72bdffad112227fa689`; Decision 2 in `results/p10is0-freeze-2026-11-18/DECISION_2.md`.
- Run directory (local, git-ignored): `experiments/P10IS0-run-20261118`. Copies here: `report.md` (sha256 5b38ef67…), `analysis.json` (sha256 2e0881a8…), `ledger.json`.
- Stages: main COMPLETE (200 of 200 cells); x8-gate printed `{"x8_triggered": false, "L_Q": 1.0}`; x8 NOT RUN (trigger needs L_Q = 4); analysis exit 0; report exit 0.

## Registered outcome (as printed by the registered analysis, step 5)

**OVERLOAD UNRESOLVED AT ℓ₁ — CONVERGENCE NOT CONFIRMED (NOT SHOWN); ADDRESSING QUALIFIED UP TO 1**

Read with ℓ₁ = load 2 (the headline prints the template symbol where the load belongs; the record reads "AT LOAD 2 (ℓ₁)").

- Line A: L_A = 2, fails at 4. Line G: L_G = 1, fails at 2. Line Q: L_Q = 1, fails at 2.
- Series M (8K facts): loads 0.5 and 1 hold (10 of 10 cells each); load 2 (8K/4K) 2 of 10; load 4 (8K/2K) 0 of 10.
- Series S (2K facts): loads 0.5, 1 and 2 hold (10 of 10 each); load 4 (2K/512) 0 of 10.
- Hypothesis readings: H23-A supported, H23-G supported (read at an ℓ₁ that is UNRESOLVED), H23-O not supported, H23-P not supported.
- Lane licence: loads 0.5 and 1.0; licensed cell types 8K/16K, 2K/4K, 8K/8K, 2K/2K (all REFERENCE NEAR CEILING and CONVERGENCE CONFIRMED). 2K/1K, where Line Q holds in series S only, is not licensed.
- Penalty against answer-only: NOT DISTINGUISHED at all four 8K cell types.

## What this does and does not say

It licenses the store's addressing at up to one fact per slot for the tested cell types, on synthetic fixed-length records with one frozen 27,392-parameter backbone. It does not establish a capacity limit: every failing cell type carries CONVERGENCE NOT SHOWN, so failure above load 1 is not separated from under-training. It says nothing about natural text, other backbones or untested sizes.

## Disclosures

1. **The UNRESOLVED headline comes from one budget refusal.** 8K/4K's training extension was refused because its projection was 55.61 h against B = 55 h (0.61 h over, X8's reserved hours included); the refusal follows the registered rule (the auditor reproduced all four projections). On the registered cells 8K/4K's d values are all at most 0.0034, so had its convergence been shown the headline would have read OVERLOAD NOT QUALIFIED AT 2 (step 6). Its calibration curves missed the 0.01 plateau step by 0.0112 and 0.0121. Neither reading is favourable to the store beyond load 1.
2. The extended cell types 2K/1K, 8K/2K and 2K/512 remained NOT SHOWN at 16,384 exposures.
3. **The ledger understates time.** It records 23.39 h against a cap of 113.01 h (main 17.09 h of 61.15 h). Invocations of main that were killed (including the outage of 2026-11-19 22:33 to 2026-11-20 00:36 local, when jobs started from a terminal died with it — the lead's fault) were never charged: about 14.5 h. Real use was about 38 h, under both caps; the cap was not enforced across killed runs.
4. **Restarts.** Main was restarted several times. The 88 cells finished before the outage were not rewritten; 6 cells caught mid-run restarted from update 0 and their 12 killed attempts are kept, each an identical prefix of the final run. No selective recomputation and no failed record.
5. **COLLAPSE-FREE is missing, not zero.** The report prints "0 of 0" for every cell type, but collapse onsets were never computed (the registry has no onset field). ADR-0023 section 6.7's annotation is therefore absent.
6. Cell records carry no code identity of their own; identity was enforced at run time (no identity pause occurred) and all 75 frozen inputs equal the freeze hashes.
7. Advisory E3 and the definition of RATIO ABOVE 1 stand as ruled in Decision 2; no cell type carries the tag.
8. Standing caveats printed by the report: W7 is told the record length; the memory is told the answer position; A5-D was chosen for P10-S0 after its P9-II result was observed; μ = 1.0 was calibrated at 0.5 facts per slot.

## Independent recomputation

`recomputation/RECOMPUTE_P10IS0.md` with its scripts and outputs (`*.py.txt`). Written from the ADR text without importing the study's analysis. Result: every printed item matches (0 mismatches field by field against `analysis.json`), except the headline's symbol noted above. Sealed values read by the auditor: the 24 Stage R points of 8K/4K only. One auditor slip on record: the integrity script first failed on tuple keys and was rerun.

## Not done

- No Astra review. No human review of this record yet.
- X8 was not run (not triggered).
- The collapse-onset annotation was not computed.
