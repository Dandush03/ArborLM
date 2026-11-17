# P9-II freeze procedure (ADR-0019 sections 9, 12, 16)

Status: procedure only. Nothing in this directory is a freeze: `plan.json` and `stage_caps.json` do not exist until the lead writes them, and every registered stage
refuses to run without them. Astra review: NOT_PERFORMED.

## Order (each step before the next; the freeze commit is step 7)

1. Code passes the audit re-check. Calibration (done, record sha256 in the freeze) and the rehearsal **with the calibration record** (so every arm's phases are measured
   at the calibrated values and the projection binds to the calibration's hash):
   `uv run --locked python -m studies.p9ii.stages rehearse --calibration <calibration.json> --stage-cap-seconds <cap>` (rehearsal set 5; time and memory only).
2. Generation, G1 and the draw plan, in the registered run directory, **before** the freeze commit (generation is allowed before it, as in P9-I, by the explicit
   `--i-understand-freeze-time` flag that the fixed script passes): `sh studies/p9ii/launch/generate.sh <registered-run-dir> <code-commit>`. It generates the fourteen
   registered and two reserve draws, G1-checks each, and writes `draw_plan.json` (a failed draw is replaced by the next unused reserve, recorded as REPLACED BY RESERVE k; an
   exhausted reserve list makes the plan not ok and nothing runs).
3. Measure the wall time of one `work analyze` + `work report` on synthetic full-registry records, and take the gates stage wall time from the rehearsal-set gates run.
4. Write the cap table (one source of truth, a pure function of the projection):
   `uv run --locked python -m studies.p9ii.stages caps --projection <projection.json> --gates-wall-seconds G --analysis-wall-seconds A --report-wall-seconds R --out studies/p9ii/freeze/stage_caps.json`.
   It holds one entry per possible Stage 2 configuration and per Stage 3 selected arm; a stage whose configuration has no entry refuses.
5. Write `studies/p9ii/freeze/plan.json` with the identities the registered stages check:
   `calibration` {`path`, `sha256`}; `projection` {`path`, `sha256`} (its `hyper` must equal the calibration's and its `calibration_sha256` the calibration's hash);
   `stage_caps_sha256`; `run_dir`; `draw_plan` {`sha256` of `<run-dir>/draw_plan.json`}; `data_manifests` {seed-set name: `sha256` of its `data_manifest.json`} for all
   sixteen sets.
6. Write the section 16 freeze record (code hashes, calibration, data identities, gates, caps, launch commands, the lead's five conditions).
7. One freeze commit containing the record, `plan.json` and `stage_caps.json`.
8. Launch, in this order, each with `sh studies/p9ii/launch/<stage>.sh <registered-run-dir> <freeze-commit>`:
   `gates`, `stage1`, `stage1_gate`, `stage2`, `stage3_gate`, `stage3`, `analysis`, `report`.

## The launch scripts (audit m11)

Section 9 says "no free arguments". Each script takes exactly two arguments, the run directory and a commit, and everything else (caps, calibration record, projection,
draw plan, seeds) comes from the frozen plan and the frozen cap table. The two arguments are guarded: the driver refuses unless the working tree is clean, the commit is an
ancestor of HEAD, `studies/`, the config, the ADR and `tests/test_p9ii_*` equal their content at that commit, the frozen inputs verify, and every hash in `plan.json` holds
for the run directory it names. `generate.sh` is run before the freeze (its second argument is the code commit, which must equal a clean HEAD). The scripts are covered by the
source digest. No registered stage is launched by a typed command.

## What the registered stages enforce (audit M3, M4, M7)

- Training and evaluation need `draw_plan.json` with `ok` true and a passed G1 for every draw it names.
- Stage 2 and Stage 3 caps are the table's entry for the configuration their gate selected.
- G2 is computed for every registered draw at the size it is used at; a failed G2 on any draw is a failed gate.
- Stage 3 refuses (NOT RUN — BUDGET (MEMORY)) if twice the largest measured peak of the 65,536-slot items, including the evaluation peak, exceeds 3 GiB per worker.
