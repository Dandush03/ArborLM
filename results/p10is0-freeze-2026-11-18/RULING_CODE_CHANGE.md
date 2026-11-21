# P10-I-S0 — ruling on a code change after Stage R (2026-11-19 UTC)

Ruling of the scientific lead (Claude Fable 5.2), taken under the human lead's delegation of 2026-11-18 (`docs/reviews/p10-i-direction-2026-11-17/DELEGATION_2026-11-18.md`, sections 1 and 7). It is not a decision the human lead read and signed; he can overrule it, in which case Stage R is rerun. `Astra review: NOT_PERFORMED`. Claude review is not Astra review.

## What happened

Stage R (the calibration of ADR-0023 section 5) ran once on the real machine under commit 45d97ff, about 6 charged hours, and completed its work: `studies/p10is0/freeze/durations.json` was written whole. Its last line, the public status print, then raised `PublicOutputError`: the leak guard matched the substring "acc" inside a sealed file's random task name (`t1af0a449caccd5.log`). No sealed value was printed or opened. The guard was repaired, two commands were added (`stage-r-status`, read-only, which prints the completion line a clean finish would have printed; `rebind-identity`), and `plan.frozen_paths` gained the rebind record. `stage-r-status` reports Stage R COMPLETE, 1,379 sealed files, no event of section 5.2.

## The ruling

Stage R stands and is not rerun. The four files below differ from the code Stage R ran under; no change in them computes, selects or reads a Stage R measurement, a duration, a flag, an extension decision or a seed, so a rerun would compute the same thing with the same code paths. `durations.json`'s code identity is rebound to commit 2daa30c, once, by the study's own command, before the candidate plan exists.

Basis: the independent audits `audit/REAUDIT6_P10IS0.md` (CONFIRMED — SAFE TO REBIND, with two required fixes) and `audit/REAUDIT7_P10IS0.md` (both fixes confirmed; CONFIRMED — SAFE TO REBIND AND PROCEED), by the arbor-auditor subagent (Claude Opus 5.5), which verified that all 71 files of Stage R's recorded identity equal commit 45d97ff and listed every changed function.

PIN stage_r_commit 45d97ffd3c6cb1d22a6fe2a7a7fc57c924ca01f0
PIN new_commit 2daa30c7cab0b6ebf325060d011d86560ebbc3ad
PIN file studies/p10is0/drivers.py old 18b9f9fc4055e198439442676cc4086e08e55e24d5aab6f2ae205b777a58bd3c new d195489d0dcb0bac477f24695ca324a7540ca338726dc85d069935f6f62a18b1
PIN file studies/p10is0/plan.py old acd844e5bfc3f85d7378827a8a08c14b47e9339265e3227049106627e379d04b new 4e8444065dacfabd8c1f04743a2ab581ad12a380bebc4c4d943ebad88f8bc76f
PIN file studies/p10is0/sealed.py old 133fe4a716fa8ae24d62d9955c2aee235fcd77844ed69fa412ca6f3503c89fb6 new c56f156c324d4746de5fb2bd64ccf74d14bcd25c9243930c7167d28d98a8e60c
PIN file studies/p10is0/stages.py old af467242cc62a2bb98a28857730ffb6fe2dd48b89d1f072766047aaf5fe781b1 new 8d0cb6d12e36b3850d3fb8c0fef2e5264e8426ae4d0324a07816e81c70fba057
PIN ruler Claude Fable 5.2 (scientific lead), under the human lead's delegation of 2026-11-18

## Every change between 45d97ff and 2daa30c in the four files (the auditor's list)

- `drivers.py`: `import re`; new `emit_stage_r_completion`, `cmd_stage_r_status`, `write_events_numbered`, `_changed_since_stage_r`, `rebind_pins`, `cmd_rebind_identity`; new constants `RULING_COSMETIC_FILES`, `REBIND_RECORD`, `PIN_RE`; `write_events` delegates to `write_events_numbered` (same text); `cmd_stage_r` changed in its final print line only. Untouched: `run_waves`, the extension rule, `final_entry`, `read_state`, `cmd_caps`, `cmd_x8`.
- `sealed.py`: `import re`; `PUBLIC_KEYS` gains `sealed_digest` and `sealed_files_sha256`; new constants `OPAQUE_TASK_FILE`, `OPAQUE_DIGEST`, `HEX64`, `MEASURE_WORDS`, `HASH_MAPS`; new `names_a_measure` and `hashes_digest`; `validate_public` adds the hashes-map checks. The guard is called on public output only: it can refuse a print, it cannot change a value.
- `stages.py`: `build_parser` and `main`, for the subcommands `stage-r-status`, `rebind-pins`, `rebind-identity`.
- `plan.py`: `frozen_paths` lists `freeze/durations_identity_rebind.json`.

No other code or config file differs from Stage R's identity. The ladder, the seeds, `items.py` and `adapter.py` are untouched.

## What this ruling does not cover, and what stays open

- Any later change to these or other frozen files: after the rebind the candidate plan, the freeze and the registered stages bind to the new identity and refuse a difference.
- What the audit says remains a matter of the lead's honesty and the audit trail: a pinned commit that itself contained a science change would be accepted by the command, and nothing re-checks this file after the rebind. This file is committed before the rebind and is not amended afterwards.
- Advisory G1 of REAUDIT7, left open by the lead: the digest exemption of the leak guard accepts any lowercase extension after 64 hex characters inside a hashes map (a name, never a value); no code of the study produces such a key. Not fixed, because a fix would be a further code change after Stage R.
- Advisory E3 (the registry checker copy excludes P10-I-R's files) and the definition of RATIO ABOVE 1 stand as recorded earlier, for Decision 2.
