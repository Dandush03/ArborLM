# P10-S2 data-generation step (ADR-0022 §4.3, §5.2–§5.3, §14.2) — 2026-11-16

- **Status:** the pre-freeze data step ran complete on its eighth attempt and its registered qualification gate FAILED. **Outcome by the registered rule (ADR-0022 outcome table, row 3): TRANSFER-INCONCLUSIVE: TEACHERS-NOT-QUALIFIED — the study stops before the freeze.** No student was trained; no calibration, rehearsal, freeze or registered run exists. Not accepted by the human lead at the time of writing. Astra review: NOT_PERFORMED.
- **Code:** commit `b3c17e6`. Configuration sha256 `64385c8c…0931`. Bundle manifest sha256 `c1e47430…82ad` (the bundle itself is git-ignored under `data/p10s2-pre-20261115/data/bundle/`). Wall time 2,100 s; peak resident memory 5,677 MiB (limit 8 GiB).
- **Independent recomputation:** Opus 5.5, `docs/reviews/p10s2-qualification-2026-11-16/` — AGREES WITH NOTED DEFECTS. The outcome is confirmed from the record's counts and the stored pools; the gate's per-item inputs on Q were not stored, so the per-item gate could not be recomputed.

## The gate (panel Q: 500 fitting + 500 check items; A = English→German, `opus-mt-en-de`; B = English→French, `opus-mt-en-fr`)

| Condition (§4.3) | Required | A | B |
|---|---|---|---|
| 1. Own score (mean sentence chrF) | ≥ 0.55 | 0.7675 — pass | 0.7754 — pass |
| 2. Margin over the larger of the other teacher (0.120 / 0.125) and the untrained student (0.146 / 0.133) | ≥ 0.30 | 0.6214 — pass | 0.6425 — pass |
| 3a. Filter chosen on Q_fit (most permissive setting with 95% Wilson lower bound ≥ 0.90) | exists | τ −0.20, ratio [0.5, 2.0]: 104 of 500 accepted, precision 0.9615, Wilson lower 0.9053 | τ −0.15, ratio [0.6, 1.6]: 41 of 500, precision 1.000, Wilson lower 0.9143 |
| 3b. Q_check: point precision | ≥ 0.90 | 0.9231 (72 of 78) — pass | 0.9545 (21 of 22) — pass |
| 3c. Q_check: accepted items | ≥ 150 | 78 — **fail** | 22 — **fail** |
| 3d. Accepted pool (of 60,000 generation sources) | ≥ 8,000 | 7,804 — **fail** | 2,341 — **fail** |

Two settings of the filter grid passed the Q_fit rule for each teacher. The sufficiency step agrees: 7,763 and 2,300 accepted sources available against 10,000 needed (DATA-INSUFFICIENT). Both primary teachers fail, so the one-time fallback teacher of §4.2 does not apply (it replaces one failed teacher).

## What this means and does not mean

- Both teachers translate the panel well and are clearly separated from each other and from the untrained student. They fail on the amount of teacher-only material the acceptance filter lets through, not on translation quality.
- The filter, as registered, accepts 21% (A) and 8% (B) of outputs on Q_fit. A 500-item Q_check then cannot plausibly yield 150 accepted items, and 60,000 sources cannot yield 8,000 for B. This is a shortfall of the registered design's sizing against its own filter; it is recorded, not repaired. No threshold is changed.
- S2's question (does two-teacher transfer into the frozen student work under oracle addressing) is **not tested**. Nothing here supports or contradicts it.

## Attempts (all kept in `datagen_attempts/`)

| Attempt | Code | End |
|---|---|---|
| 1 | — | `pyarrow` missing (launched without the pilot extra) |
| 2 | — | WikiText-2 files absent in the worktree |
| 3 | — | the teacher loader rejected by transformers 4.57.1 (code had only run on stand-ins); fixed in `f3fd77d` |
| 4 | `f3fd77d` | registered-test stop: 44 marker-like GEN windows, fewer than 100; ruled in the ADR-0022 addendum of 2026-11-16 (`lead_release.json`) |
| 5 | `6c22377` | stopped by the lead after about 15 minutes: the teachers' pinned `generation_config.json` (`renormalize_logits: true`) was not applied since `f3fd77d` (found by audit); fixed in `4ce9d77`; charged at the stage cap, 1.8 h |
| 6 | `4ce9d77` | memory guard, 8.09 GiB of 8.00 |
| 7 | `460ebf1` | memory guard, 9.38 GiB (the example bank held in memory with the teachers and corpus) |
| 8 | `b3c17e6` | complete; the gate fails as above |

## Notes for reproduction

- Teacher outputs differ between 2 and 18 CPU threads (digests differ); the run used the machine's default thread count.
- The gate's per-item inputs (teacher outputs and scores on Q, and the rejected generation outputs) are not persisted; an independent per-item recomputation needs a re-run of the teachers.

## Files

`prefreeze_record.json`, `bundle_manifest.json`, `datagen_attempts/`, `SHA256SUMS`.
