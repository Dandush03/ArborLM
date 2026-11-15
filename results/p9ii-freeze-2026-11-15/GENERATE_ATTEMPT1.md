# P9-II registered generation, attempt 1 — refused before anything was generated (2026-11-15 UTC)

- `sh studies/p9ii/launch/generate.sh <run-dir> 51c00b2…` was refused sixteen times by the stage driver: "--stage-cap-seconds is required". The fixed script did not pass a stage cap. **No registered or reserve draw was generated and no registered seed was read.** The script then wrote a draw plan with `ok: false` ("14 draws failed G1"), which is wrong as a description: nothing was generated, so nothing failed G1. The run directory `experiments/P9IIP-registered-20261115` holds only that file and is not used again.
- Cause: the script had never been executed. The implementer could not run it (it uses registered seeds) and the auditor's freeze test in a clone used stand-in data manifests instead of generation. This is the same kind of gap as P9-I's first attempt: a path that only the registered run exercises.
- Fix (one flag, three lines of the script): each `generate` call now passes `--stage-cap-seconds 300`. Nothing else changes. The script is part of the source digest, so the code identity changes after the auditor's READY TO FREEZE; the change cannot alter any number a cell computes, and it is listed in the freeze record for the auditor's recomputation.
- Files: `generate_attempt1_refused.log`, `generate_attempt1_refused_draw_plan.json`.
- Astra review: NOT_PERFORMED.
