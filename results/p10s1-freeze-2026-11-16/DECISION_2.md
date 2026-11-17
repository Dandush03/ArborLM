# P10-S1 — Decision 2: the single registered run (ADR-0021 §22 M4)

Freeze commit: `70d1f83b80973ba3fbd25e968a15f3ad6a405549`

DECISION: RUN

Decided by the scientific lead (Claude Fable 5.2) on 2026-11-16 UTC, under the human lead's standing delegation for the P10 studies (S0, S1, S2), after the human lead's own directions on the capacity grid (ADR-0021 §24), the load-search ceiling (§25.15) and the cap ceiling (§25.16).

The conditions of §8 and of the freeze procedure, as checked:

- **Audits.** No open blocker. The pre-freeze audit's one blocker (the freeze could not record S0's accepted outcome) is closed by the ruling of §25.17 and commit `ab72619`, re-checked independently. One finding rated major concerns record quality only: the registered throughput stage needs a quiet machine and may record THROUGHPUT NOT MEASURED; it does not block the analysis. The lead accepts that and will ask the human lead for a quiet machine before launching that stage.
- **Nothing changed after calibration except what was directed and recorded:** the ceiling C_max (36 → 50 hours) and the freeze's handling of S0's outcome. No threshold, seed, arm or analysis rule changed.
- **The headroom rule holds:** C_need 48.55 hours under C_max 50 hours with no cut; computed cap 49 hours.
- **No registered seed has been observed.** The five registered draws are generated and G1-checked only; no model has been trained or evaluated on them.

This run is executed once. Whatever it gives is recorded, including null and negative results and any stage stopped by its cap. Nothing in its result is autonomous learned memory: addressing is supplied by an oracle. Astra review: NOT_PERFORMED.
