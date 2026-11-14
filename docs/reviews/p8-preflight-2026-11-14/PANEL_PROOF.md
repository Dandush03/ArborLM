# P8 panel proof (ADR-0015 section 6): Panel A and Panel B

- Run by: auditor role, Claude Code session, model **claude-opus-5-5** (Opus 5.5), from session metadata. Date 2026-11-14 UTC.
- Status: independent engineering evidence. **Not Astra validation. Not human approval.** It does not cover the ADR's separate requirement that the implementer's reconstruction and this one agree byte for byte. I did not open or compare `src/arborlm/p8_panel.py` (untracked implementer file found during the search).
- Scope: reads raw text from the pinned local WikiText-2 parquet files (read only, main checkout `data/wikitext2`). No model was run, nothing was evaluated, nothing was downloaded. No existing file was edited.

## Verdict: **ELIGIBLE-UNUSED-DISJOINT**

| | Panel A | Panel B |
|---|---|---|
| Ranks (zero-based, half-open) | [3072, 3584) | [3584, 4096) |
| Rows x bytes | 512 x 65 = 33,280 | 512 x 65 = 33,280 |
| Panel bytes SHA-256 | `448017f93b994167d898460b236ac1324e2b7cfcba5cb6df1380840bc7b97342` | `1bd4b984c3f7a92882ba5f8b8383314fd2899f69539a3ef2e85e5b25d323607e` |
| Selection record SHA-256, global ranks | `4ddd461a92238209f37f5ae8f37d71a22caeb735792a3e14b8d980aabb8b4866` | `197f497ec04f8abff1c8909e6e89794511cb408b91229de7c1fc4f4111611552` |
| Selection record SHA-256, ranks from 0 | `c3915a41b73bae1a2cc85264816f7e93f139a092aee4b49200d86d1e5e920d7b` | `971b994fd75572d53a6060377f35e3b6652ae8059c95e531800c47ba4fe88403` |
| Duplicates within panel | 0 | 0 |
| Exact overlap: each earlier panel, ranks 0–3071, the other new panel, calibration (train 2048–2559), training pool (train 0–4095), every train chunk | all 0 | all 0 |

Panel bytes are the 512 chunk payloads concatenated in rank order, the serialization of every earlier panel. A selection record is canonical JSON (sorted keys, compact, trailing newline) of `[{rank, row, byte_offset, rank_sha256, chunk_sha256}]`. P2/P5 `*.selected.json` numbered `rank` from 0 within the list; the P7-B record used global ranks. Both forms are given. Which one is frozen is for the lead and implementer to choose.

## 1. Eligibility
There are **16,407** eligible ranked validation candidates (at least 4,096 are required). The validation file has 3,760 rows and 16,425 full chunks. 15 chunks were excluded because they match a train chunk, and 3 were in-split duplicates. All validation and train counters equal P5's recorded `dataset_manifest.json`. The rank keys are strictly increasing, the contents are unique, and every payload is 65 bytes.

## 2. Earlier panels reproduced from the same file (6 of 6)
P1 `2e6b71b9…2200`, P2 `8cd4ab92…5cd2`, P3 `a2d63d4e…24b0`, P4 `4c6fb3f3…c28f`, P5 `d50cbe4c…2b98`, and P7-B stream B `4e2c9d97…0731` all reproduced. Full values and sources are in `panel_confirmation.json`. Additional identity checks also passed:
- The train pool bytes equal P1 `train.bytes`.
- The train selection and first-2560 validation selection equal P5's frozen records.
- The P7-B per-row SHA-256 list and `rows_detail` equal its `panel_record.json`.

## 3. Unused (repository search)
The search covered tracked files, untracked non-ignored files, all 14,995 JSON records under `results/`, and the main checkout's `experiments/`. It found the windows 3072–3583 and 3584–4095 named only by P8 itself: ADR-0015 lines 100, 102 and 224 (committed in `273a115` during this audit), `configs/p8_locality_training.toml:84-85`, and the untracked `src/arborlm/p8_core.py` and `p8_panel.py`. Every other hit is one of these:
- 3072 as the exclusive end of P7-B's [2560, 3072).
- Slot IDs or counts out of 4096.
- Timing or trace numbers.
- `train.selected.json` ordinals, which are training-pool ranks.

No record contains a validation selection entry or interval at or above rank 3072. The highest recorded validation rank is P7-B's 3071. A search cannot rule out unrecorded use outside the repository and `experiments/`.

## 4. Descriptive caveats (not gates)
- The recipe deduplicates exact aligned chunks only. Both panels draw from the same 60 heuristic articles as earlier panels.
  - Panel A shares 353 of its 422 source rows with ranks 0–3071.
  - Panel B shares 372 of its 430 source rows with ranks 0–3071.
  - The two panels share 122 source rows with each other.
  - No panel article title equals a train article title.
- Panel B rank 3715 (row 3148, offset 325) is a 65-byte string that also occurs unaligned in train row 22071 at byte 328. The train chunks covering it are ranks 52035 and 89335, outside the pool and the calibration stream.
- Panel A rank 3214 also occurs unaligned in validation row 3026, inside rank 7538, which is unused.
- The "every train chunk" overlap is zero by construction because of the exclusion rule. The pool and calibration zeros are implied by it but were computed separately.

## Commands (worktree cwd; uv 0.12.15, CPython 3.12.14, pyarrow 21.0.0 from locked extra `pilot`, macOS arm64)
```
uv run --locked --extra pilot python -I docs/reviews/p8-preflight-2026-11-14/independent_panel_p8.py   # -> panel_confirmation.json, outputs/independent_panel_p8_run1.log
uv run --locked --extra pilot python -I docs/reviews/p8-preflight-2026-11-14/neardup_detail.py         # -> outputs/neardup_detail.log
uv run --locked python -I docs/reviews/p8-preflight-2026-11-14/repo_search_focused.py > outputs/repo_search_focused.log
# raw broad grep: outputs/repo_search.log (noisy, kept); environment and file hashes: outputs/environment_and_hashes.txt
uv run --locked ruff check docs/reviews/p8-preflight-2026-11-14/   # passed
```
- Tool SHA-256: `a18b24e94ec1677581d5be466e7a810e61e1f73c796471817e982ad62300a81d`.
- Validation parquet: `204929b7…511c4c`. Train parquet: `e83889ba…53d0c9f7`. Both match the pinned values.
- The `environment_and_hashes.txt` line for itself hashes the file while it was still being written. Ignore that line.
- Failed and superseded attempts are in `failed_attempts/`. Questions of scientific adequacy, such as article sharing, are **PENDING LEAD REVIEW**.
