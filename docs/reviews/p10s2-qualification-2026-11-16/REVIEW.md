# P10-S2 teacher qualification gate — independent recomputation (2026-11-16)

- **Reviewer:** Claude Opus 5.5 (`arbor-auditor`), from the stored outputs of data-generation attempt 8 (code `b3c17e6`), with its own script (`recompute.py`, output `recompute.out`): own chrF (n = 1..6, β = 2, effective orders) and Wilson interval; sacrebleu not used. Independent engineering review; not Astra validation and not human approval. Astra review: NOT_PERFORMED. Written up by the lead (Claude Fable 5.2) from the reviewer's report.
- **Verdict: AGREES WITH NOTED DEFECTS.** The registered rule applied to these data gives TRANSFER-INCONCLUSIVE: TEACHERS-NOT-QUALIFIED.

## Recomputed and matching

- Margins 0.6214 (A) and 0.6425 (B) from the recorded own, other-teacher and student scores.
- Q_fit: A 100 of 104, precision 0.9615, Wilson [0.9053, 0.9849]; B 41 of 41, 1.0000, [0.9143, 1.0000].
- Q_check: A 72 of 78, 0.9231, [0.8422, 0.9643]; B 21 of 22, 0.9545, [0.7820, 0.9919].
- Accepted pools recount exactly from the bundle: 7,804 and 2,341 records, unique keys; every stored record passes the word-ratio range, differs from its source, matches no evaluation reference and is in no panel or gold pool. With the dropped items (5, 1): 7,809 and 2,342 passed the filter.
- Descriptive only (not the gate panel): the reviewer's chrF of the teachers on D_cal is 0.7811 (A) and 0.7713 (B), about 0.12–0.13 crosswise.

## Which sub-condition fails

Point precision on Q_check is at least 0.90 for both teachers. `filter_check.ok` is False only because fewer than 150 items were accepted on Q_check (78, 22): ADR-0022 §5.3 ("point precision ≥ 0.90 on Q_check with at least 150 accepted items"), the table of lead's choices, and `configs/p10s2_transfer.toml` `check_min_accepted = 150`. The accepted-pool condition (≥ 8,000) fails on its own for both teachers, so the gate fails even without the 150 minimum. Both primary teachers fail, so the fallback clause of §4.2 does not apply.

## No false-NOT-QUALIFIED defect found

The length-normalised score matches the library's sequence scores to 2.4e-7 over all 2,033 batches and τ is compared against that mean (`filtering.py:61`); Q_fit and Q_check are disjoint in keys and identity groups; references are German for A and French for B; the 0.60 threshold is applied to the output against the best reference (`filtering.py:86`); the tie key is correct (`filtering.py:103`).

## Findings

1. **Major (auditability).** The gate's per-item inputs are generated in `studies/p10s2/prefreeze.py:167-168` and never stored (`TEACHER_PANELS`, `prefreeze.py:126`, excludes Q; the record keeps aggregates). The Q_fit grid table, the own scores per item, the Q_check items, the τ condition on the pools and the number rejected of 60,000 could not be recomputed without re-running the teachers.
2. **Minor (interpretive).** The length ratio counts whitespace words after punctuation is stripped (`filtering.py:57`); the ADR does not define the word count.
3. **Info.** The sufficiency step reports 79 shared sources where the reviewer counts 78 shared keys (the code counts identity units, `data.py:449-455`); no effect on the gate.

## Not checked

The Q generation itself, the student's Q score, the 60,000-source sample, the partition build, a sacrebleu cross-check, and whether 150 accepted on Q_check is reachable by any passing setting (not computable from stored data; the reviewer judges it implausible, not proven).
