# ADR-0025 addendum — Part T rulings 47 to 49 (2026-11-21 local, after calibration, before the candidate plan)

Rulings by the lead (Claude Fable 5.2) on the findings of Part T audit 13 (arbor-auditor subagent, Claude Opus 5.5; verdict READY FOR CANDIDATE PLAN with one condition). `Astra review: NOT_PERFORMED`. Nothing here changes a rule, threshold, grid, seed, cell, U, rate or cap rule. These rulings are the lead's and stay on the human lead's review list.

## Ruling 47 — disclosed literal departure from section 7.1 rule 4

ADR-0025 section 7.1 rule 4 says: "No Part T training or scoring file changes after a calibration output exists." After calibration repetition 0 ended, one line of `configs/p10is2_partt.toml` was changed: `caps.study_budget_hours` from 95.68 to 151.0, on the human lead's decision ("Raise to 151 h", `results/p10is2-partt-budget-bound-20261121/APPROVAL.md`). The config is a file that training and scoring read, so the edit departs from the letter of rule 4. The sentence in `ADR-0025-addendum-part-t-budget-bound.md` calling the config "no training or scoring file" is a reading, not a fact, and is corrected here: the departure is literal and is disclosed.

In substance: the changed key is read only by the two bound-check functions (`require_study_budget`, `check_study_budget`) and by no training, scoring, cap, allowance, projection, label or analysis code (audit 13, finding 4). No `studies/p10is2/*.py` file changed, and the calibration record is checked against those files only. Calibration is therefore not repeated. This departure is to be stated again in Part T's freeze record and Decision 2.

## Ruling 48 — Part Q's acceptance record

Ruling L1's `ACCEPTANCE.md` did not exist as a separate file; the acceptance was a section of Part Q's `OUTCOME.md`. The lead has written `results/p10is2-partq-run-20261119-attempt3/ACCEPTANCE.md` with the same acceptance and no new decision. Part T's plan pins that file as `part_q_acceptance`.

## Ruling 49 — which panel ledger Part T pins

Part T pins the shared panel ledger in the state Part Q's plan pinned: `/Users/daniellaloush/dandush03/ArborLM-sealed/p10i-s6-backups/panel_ledger.before-s6.json`, SHA-256 `62f8111614207fec61173af0f91246f1629d744739a4173778af0de293921756`. Part T reads and writes no ledger entry and registers no panel; it only pins the file, which is re-hashed at every registered stage. The live ledger has since received P10-I-S6's 1,024 windows (SHA-256 `ba14c714…3fa8`), none overlapping Part Q's generation windows (audit 13's span check). The live file is not pinned because any later study's append would change its hash and pause every later Part T stage. The pinned file lives outside the repository; no copy is committed.
