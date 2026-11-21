This folder will hold, once the specification is frozen (ADR-0026 section 11): `plan.json` (the candidate and then the frozen plan), `rate_table.json` (written by `write-rate-table` from R1's public file),
`seed_plan.json` and `seed_registry_check.py` (written at candidate-plan time), and `freeze_record.json`. Nothing here is a result; no file in it exists before the candidate plan.
Every writer creates this folder if it is missing, so a clean checkout needs only this note.
