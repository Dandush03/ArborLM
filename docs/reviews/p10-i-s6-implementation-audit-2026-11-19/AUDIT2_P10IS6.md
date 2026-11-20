# P10-I-S6 second implementation audit, commit 1dce8a2 (ADR-0031 and its addendum of implementation rulings)

- Auditor: `arbor-auditor` subagent, Claude Opus 5.5 (claude-opus-5-5), 2026-11-19. This is independent engineering and mathematical evidence. It is not Astra validation and not a human approval. `Astra review: NOT_PERFORMED`.
- Object: `git archive 1dce8a2` of `claude/p10-i-s6-impl`, unpacked into `/Users/daniellaloush/dandush03/ArborLM-sealed/audit-s6-a2/`. For item 3 I made one throw-away `git clone --no-local` into that folder's `_audit/scratch/clone`. I made no git write to any project repository.
- Constraints kept: no network (`--offline` / `UV_OFFLINE=1`; the `pilot` extra came from the local uv cache); no real training; no sealed value opened; one heavy process at a time; `timeout` on every command.
- Real inputs were read, never written. The shared panel ledger (`data/p10i-shared/panel_ledger.json`, SHA-256 `62f81116…921756`, unchanged) and P10-I-S3's public data manifest and `excluded_spans.json` were read, and so were the pinned WikiText-2 parquets, through copies or pyarrow.
- Environment: macOS arm64 (Apple M5 Max), Python 3.12.14, torch 2.8.0. Every command was run from the archive root as `PYTHONPATH=$PWD timeout <s> uv run --locked --offline [--extra pilot] python _audit/<script>`.
- Scripts: everything is in `audit-s6-a2/_audit/`. The two that carry the key results are appended at the end.

## Verdict: READY AFTER LISTED FIXES

- **What is ready:** the scientific core and the registered path are ready, and so is the fetch, by its code. My adapted reference agrees with the new analysis on 2,400 random registries. The end-to-end test passes. The real `uv run --locked` launch and the real r4 checker behave.
- **What is not ready:** the D0 data command cannot run on the real panel ledger, and the excluded set that ruling 4 prescribes is too small (B1, B2).
- **What else must change before freezing:** six required findings: R6–R9, R11, R12.
- **What does not block the fetch:** R10 (pin completeness) is a check to make by hand at the pin step; ADV-n1 and ADV-n2 can follow.
- **Order:** the P0 parent command can run before those fixes. The real fetch can run now.

## 1. The first audit's findings and the rulings

I adapted my reference (`ref_labels.py`, which still imports nothing from the study) to rulings 1, 2, 3, 6 and 10. The harness (`fuzz_labels.py`) now also generates:
- missing BASE records and missing `used_slots` statistics (expected: INCOMPLETE REGISTRY);
- BASE present but non-finite (cause 1);
- non-finite replays after a finite enabled read (cause 2).

Result of `fuzz_labels.py 2400 0`:
- 2,400 worlds. 73 ended in an expected stop; the other 2,327 reached rows 1–12 (counts 240/72/49/171/114/147/61/454/177/133/282/427) and every trend tag.
- **0 divergences** in row, label, ONE DOUBLING, K\*, R, j†, every class, tag, R16, D[FLAT] or cause ids.
- Every one of the 73 missing-record worlds was refused with INCOMPLETE REGISTRY.

| Item | Status | Evidence |
|---|---|---|
| R1 R16 beside a failure label | FIXED | `r16_concrete.py`: one failed M-FLAT cell now gives `MEMORY UNSTABLE … R16: NOT EVALUABLE`; one failed D-ADAPT cell gives `NOT EVALUABLE (… failed cell) … R16: NOT EVALUABLE`. Fuzz: 0 R16 divergences under ruling 1. |
| R2 calibration not interior | FIXED | `calibration.rate_table` raises. `cmd_freeze` checks every flag at −1..k_max for both arms. The e2e freeze refuses an edited `interior` flag. |
| R3 exact integrity | FIXED | `analysis._eq` is exact. A registered analysis off the platform of record is an ENGINEERING STOP (`stages.run_analysis`). |
| R4 parent command | FIXED | `parents.require_identity` and the recomputed digest are in place; a mismatching file is renamed aside and the attempt logged. |
| R5 data command | PARTLY | (a) E covers train and validation: yes. (b) Lexicographic shard order: yes. (e) Ledger of record: yes, and verified on a copy (section 4b). (f) RSS is measured, though only after the fact. (g) Both gates are present, and the reproduction gate is TRUE on the real files: the first 4,096 WikiText-2 ranks hash to `P1_TRAIN_SHA256`, and the compact select equals `pilot_data.select`. **(c) and (d) are NOT FIXED: see B1 and B2.** |
| A1 missing `used_slots` | FIXED | Now INCOMPLETE REGISTRY (also in the fuzz). |
| A2 non-finite replay | FIXED | `nonfinite="value"` gives cause 2 (also in the fuzz). |
| A3 ND at every rung the run serves | FIXED | `analysis.run_bad`; it agrees with my run-level reference. |
| A4 bytewise snapshots | FIXED | `model.bytes_equal`. |
| A5 oracle | FIXED | It has its own key strings, uses the builtin `sum`, covers rows 1–12 and half its worlds share runs. |
| A6 loose tests | FIXED | The swapped-rungs test now asserts the known answers and that they fail; the disjunction is gone. |
| A7 seeds | FIXED | Synthetic backbones use test-range seeds 952701+. The planted toy uses 330793. |
| A8 27 cells | FIXED | Registered `run_analysis` refuses unless 27 cells and 27 OA cells are present. |
| A9 section 12.5 output | FIXED | Per-parent envelope δ, X_mean_dense, statistics at 8,192, and the calibration-against-registered states (read from a file the lead places after the recomputation). |
| A10 `p_used_values` outside `no_grad` | NOT FIXED (no ruling; harmless) | — |
| A11 control memory | FIXED | Not constructed for new parents; the 201 path is a fallback only. |
| A12 tests independent of git | **NOT FIXED** | In my non-git copy 3 tests still fail on the git-ignore check: `test_get_appends_started_rows_first…`, `test_get_checksum_mismatch…`, and the ruling's own `test_no_test_depends_on_the_directory_being_a_git_work_tree`. A fourth failure, `test_the_ledger_of_record_is_the_only_ledger_file`, was caused by MY scratch copies of the ledger inside the archive, not by the code. Totals: 139 passed, 4 failed, for the non-e2e tests in the non-git copy. |
| A13 partial directories | FIXED | Moved to `_kept_aside/`, and the move is logged. |

Rulings 1–13: rulings 1, 2, 3, 5, 6, 7, 8, 11, 12 and 13 are implemented as written. Ruling 10 is implemented as written, with the open case below. Rulings 4 and 9 depend on B1 and B2. What I find wrong or open:

- **Ruling 4 rests on a false statement, and the statement is mine.**
  - My first audit said that walking from rank 8,192, with the ledger and P10-I-S3's panels excluded, equals "continuing after" P10-I-S3. That holds only if the excluded set contains everything P10-I-S3's walk excluded. On the real files it does not.
  - P10-I-S3 excluded P10-S2's GEN windows and ADR-0025's windows. Its `excluded_spans.json` (in `experiments/P10IS3-data-20261118/`, recorded SHA-256 `40e63363…`) reproduces P10-I-S3's two panels exactly. The shared ledger holds P10-I-S3's panels and P10-I-S2-part-Q's 144 windows, but not P10-S2's 100 ordinary windows.
  - Result (`ledger_walk2.py`), walking with ruling 4's set: 87 of the 1,024 new panel chunks lie at ranks below P10-I-S3's last rank (9,416), and 153 overlap spans P10-I-S3 excluded. With P10-I-S3's own excluded spans added, the walk starts at rank 9,418 with 0 overlaps.
  - Correction needed: ruling 4 should name P10-I-S3's `excluded_spans.json` spans as part of the excluded set. PENDING LEAD REVIEW. The direction is neutral.
- **Ruling 10 leaves one case open.** A run that is a failed cell (non-finite enabled read at one snapshot) and also has an integrity break (replay or disabled) at another snapshot. The code skips integrity checks on failed runs, so for M-FLAT this reads row 2 (MEMORY UNSTABLE). Section 12.2 item 2 would read row 1. Both readings are against the memory. A one-line ruling closes it.

## 2. Engineering against sections 15–17, 16a and ADR-0029 section 13

**plan.py, items and the stage driver.** These are sound:
- The candidate plan carries definitions only (items, rate table, caps, hashes).
- Every worker re-derives the registered items from the config and the rate table (`verify_plan`) and reads its items from the plan only.
- Identity is checked at every task start over every file under `studies/p10i_s6` except `printing/`, the config, the tests, the imported P10-I-S3/P10-S2 files, the `results/` globs, the import-walk `src` files, `uv.lock`, `pyproject.toml`, the data manifest files and the new parent files.
- The registered entry point refuses without a clean tree, an ancestor freeze commit, frozen files equal at HEAD, the platform, a committed Decision 2 and a verified freeze record. The e2e test and my real launch both show the Decision-2 refusal.

**Runner and items.** These match the requirements:
- Finished items are skipped.
- An identity refusal exits 75 → PAUSED — IDENTITY, with no failed record; only an attempt file is written.
- An error becomes `item_error`, the analysis refuses, and the result is an ENGINEERING STOP, never NOT EVALUABLE.
- The pause file is checked between tasks, before an item, and at rung snapshots (exit 76).
- Partial directories are kept aside.
- The keep-awake `caffeinate` is a child of the `uv` process that `exec` replaced, so `own_family` counts it; the e2e test confirms "caffeinate" is in the family on this machine.
- The completion record is written before any print, and `announce` swallows print errors.

**Cost and caps.**
- One formula: `caps_from_projection(charged = 0, projected)` is used by the candidate plan, the freeze and `caps-proposal`. The registered ledger is separate from the rehearsals' ledger, which is a defensible reading of "charged so far".
- My own count for the 16× ladder (`cost_count.py`):
  - One rate per arm: 54 registered training items plus 54 OA items, 14,155,776 registered updates.
  - A rate per rung: 324 + 54 items, 27,869,184 updates.
  - All counts equal the code's.
- The projection, re-derived by my own formula with P10-I-S3's unit costs: 6.98 h (one rate) to 13.26 h (a rate per rung), identical to `cost.project_hours`. The cap is twice that.
- Findings: R7 (the freeze does not tie the projection to R2's record) and R8 (R2's probes are too short), below.

**COMPUTING and ORCHESTRATION (requirement 6).** Several files classed as ORCHESTRATION, or in neither list, compute numbers:
- `stages.py` computes the BASE values the analysis reads (`run_core_gates`), slices the pools and panels (`real_resources`), and runs the prefix and resume gates.
- `rehearsal.py` builds the calibration curves and runs NEG-REF on calibration checkpoints.
- `d0.py` and `p0.py` are in neither list.

Workers hash every file at start, so an edit would still pause the run. But stage records claim the identity of the computing code while omitting `stages.py`, and the e2e test even asserts that omission. **R11 (REQUIRED, neutral):** move `stages`, `rehearsal`, `d0` and `p0` into COMPUTING. (`testing.py` is used only as a load template, so its values are overwritten.)

**Freeze.** The freeze:
- re-derives the plan from code and config (ADR and platform excluded);
- refuses provisional caps, another plan hash, a stage that is not COMPLETE, a non-interior table, rate tables that differ, and changed rule files;
- reruns the seed gate.

The addendum is hashed for provenance (`adr_provenance`). Against section 15's frozen-input list, three things are missing:
- the nine old parent checkpoints (their digests are checked against P4 at load, but they are not hashed in the plan);
- the shared panel ledger;
- the WikiText-103 and WikiText-2 parquets (the pins file and the derived table are hashed).

These are ADV-n3.

**Every branch on a rehearsal flag** (P10-I-S2's class of defect):

| # | Branch | Where |
|---|---|---|
| 1 | Config overrides apply in rehearsal; a registered plan with overrides is refused | `cfg_for` |
| 2 | Synthetic resources are refused for a registered plan unless the config declares `[synthetic]` | `resources_for` |
| 3 | The registered panel is read only in registered mode | `real_resources(registered_mode)` and `panel_for` |
| 4 | Platform gate; the real checker runs only when registered; 9+9 against 3+3 parents; the BASE panel | `run_core_gates` |
| 5 | Gates must have passed only when registered | `run_stage`, `work_main` |
| 6 | `verify_plan` in workers only when registered | `worker_precheck` |
| 7 | Separate ledgers | `ledger_of` |
| 8 | The 27-cell assertion, full against scaled thresholds, the platform stop | `run_analysis` |
| 9 | DRY items: dry seeds, calibration pool and panel, registered parent group, 3 cells and 3 OA cells | `registered_items(profile="dry")` |
| 10 | R3 runs its own rehearsal plan, not `freeze/plan.json`; the candidate's SHA-256 is recorded | `run_r3` |

None of these can hide a scientific failure. A registered-only failure in 2, 4, 5, 6 or 8 stops the run as a refusal or an engineering stop at the gates or analysis stage. The real checker (4) is also run by the freeze, and in my item-3 check.

Untested before the registered run: the registered pool slice `(0, n_reg)` and the registered panel `panels.bytes[:512]` are read by no rehearsal. D0 writes both in that order, so the order is consistent by construction. ADV-n4: a registered-mode gate that compares the registered panel's SHA-256 with the D0 manifest.

**Leaks of sealed calibration values.** I found none:
- `rehearsal_public.json` holds the rate table, interior flags, gate booleans, seconds (including the round count), storage, the sealed SHA-256 and rule hashes, all behind `public_guard`.
- Calibration states are written only into the sealed archive.
- Worker logs, gate records with BASE values from R1, R2 and R3, the R3 analysis and the R3 report all go under the sealed directory.
- Prints carry statuses, seconds and paths only.

**R9 (REQUIRED, neutral):** `run_r1` checks that the sealed directory lies outside every git working tree only when it writes the archive at the end (`write_sealed`). Every calibration evaluation record (NLLs) is written into `--sealed-dir` before that. A mistaken sealed directory inside a working tree would receive sealed values first. Fix: call `require_outside_repo(sealed_dir)` at the start of R1, R2 and R3.

**Other required and advisory items.**
- **R7 (REQUIRED, neutral):** the freeze recomputes the projection from the plan's own `projection.unit_costs`. It never compares `projection.r2_sha256` with the R2 record or with `rehearsal_public.r2_record_sha256`, so the unit costs, and with them the cap, could be typed. Fix: the freeze reads R2's record by that hash and requires equality.
- **R8 (REQUIRED, neutral, cost only):** `[rehearsal] r2_updates = 50`.
  - The per-update rate is (whole-process seconds − overhead) / 50.
  - At about 0.008 s/update, 50 updates take about 0.4 s against an overhead of several seconds (start-up plus hashing a 0.5 GB table).
  - Jitter of 0.5 s in the overhead alone moves the rate by more than 100% and can make it negative. The cap is multiplied by 262,144 updates.
  - Fix: about 2,048 updates or more per probe, and refuse a non-positive rate.
- ADV-n5: the freeze does not re-check the 40 h bound, and `--over-cap-approved` is a bare flag with no reference to a recorded approval.
- ADV-n6: R2's probes are not charged to the rehearsal ledger (they run through `runner.run_tasks` directly).
- ADV-n7: requirement 4 — a failed fetch deletes its `.part` file, so the evidence is lost.

## 3. The end-to-end test, and the check it leaves out

- `uv run --locked --offline --extra pilot pytest -q -p no:cacheprovider tests/test_p10i_s6_e2e.py -x` → **2 passed in 391.6 s**, run once.
- **What the registered path does that the test does not:**
  1. The real `uv run --locked` in the repository: venv sync and creation, and that it leaves the tree clean for the clean-tree check. The test uses a shim that runs the test's own python.
  2. The real r4 seed checker over the whole repository with `--own` globs. The test uses a stub that prints PASS.
  3. The real configuration, ladder and grid. The test injects a tiny config with a `[synthetic]` section.
  4. `real_resources`: the memory-mapped chunk table, `panels.bytes` slicing, old parents through `p10i_s3.parents.load_backbone`, and new parents from files. Every registered launch in the test is synthetic.
  5. The real panel ledger format. The test fabricates the P10-I-S3 `data.ledger` structure, which the real file does not have (B1).
  6. The real adapter identity gate against the P4 digests. The test computes its "recorded" digests with the same code.
  7. The real parquet readers and pointer files.
- **The smallest additional check, run once** (`_audit/real_launch.sh`, throw-away clone of 1dce8a2, offline):
  - The unmodified `launch/gates.sh` through the real `uv run --locked` created `.venv` in the clone. It passed the clean-tree, ancestor, frozen-file and platform checks and refused exactly at Decision 2, with exit 2.
  - `git status --porcelain` was empty afterwards.
  - `gates.seed_gate(cfg, root=clone, run_checker=True)` with the REAL r4 checker gave `passed True`, `RESULT: PASS`, returncode 0, 12 own allocation rows. The tree was still clean.
- The same clone exposed **R6 (REQUIRED, neutral):** `launch/prepare-data.sh` (D0) and `fetch.sh` run `uv run --locked` without `--extra pilot`. In a fresh environment `import pyarrow` fails (`ModuleNotFoundError`), and D0 needs it (`pilot_data._rows`). Fix: add `--extra pilot` to `prepare-data.sh`. `fetch.sh` does not need pyarrow.

## 4. Data and parent commands against the real inputs (read-only)

### 4a. The shared panel ledger

The real format is `{"format": "p10i-panel-ledger-v1", "p10is2": {…, "unit": "byte offsets in the concatenation of the rows of the WikiText-2 validation parquet file, rows in file order, nothing between them"}, "windows": [1,168 × {start, end, first_row, last_row, source, …}]}`. The 1,168 windows are:
- 512 "P10-I-S3 panel registered";
- 512 "P10-I-S3 panel calibration";
- 144 "P10IS2-partq GEN" windows (44 marker-like, 100 ordinary).

The implementer's assumption about the unit is right. `d0._convert` on every real window, with UTF-8 row lengths and no separators, reproduces all 144 recorded `per_row` triples and every `first_row` / `last_row` (0 mismatches). My concatenated length is 1,144,248 bytes, equal to P10-I-S3's recorded `row_layout_total_bytes`. All 1,024 P10-I-S3 panel windows map onto validation ranks 8,193–9,416.

(The ledger's `row_bytes_sha256` is not the SHA-256 of the concatenated UTF-8 rows. That value is `8ef74978…`; whatever the field hashes, the conversion is confirmed by the per-row check.)

**B1 (BLOCKING for D0, neutral):**
- `d0.spans_in_ledger` reads `ledger["ledger"]["panels"]` and `["excluded_windows"]`, a format the real file does not have. On a copy of the real ledger, `d0.prepare` raises `KeyError 'ledger'` after the chunk table has already been written (`d0_real_probe.py`). The leftover table then makes a second run refuse with `FileExistsError`.
- `append_ledger` would write the same invented structure. If the reader alone were fixed, the writer would replace `format`, `p10is2` and `windows`.
- The ledger copy is unchanged after the probe; no real file was touched.
- Fix: read `windows[].start/end`; append 1,024 window objects in the file's own format (start, end, first_row, last_row, source "P10-I-S6 panel registered" / "… calibration"), keeping every existing key; test on a copy of the real file; write the chunk table only after the panels succeed.

**B2 (BLOCKING for D0 until ruled, neutral):** the excluded set must also hold P10-I-S3's `excluded_spans.json` spans (section 1, ruling 4). Note the format: `--extra-excluded` expects a JSON list of triples, while that file is an object whose `spans` key holds the triples.

### 4b. Fetch and the download ledger of record

- `fetch.get` on a COPY of `docs/reviews/p10-design-2026-11-15/DOWNLOAD_LEDGER.md` with two fixture shards (`fetch_copy.py`):
  - It appended rows in the ledger's own nine-column format with Study `P10-I-S6`, status `completed`, and the running total continuing from 1,188,183,868 to 1,188,187,213.
  - Old rows were unchanged.
  - A hash mismatch appended a `failed: FetchRefused` row whose bytes still count in the running total, as P10-S2's failed row does.
- The pin step is sound in design. It reads `raw/<revision>/wikitext-103-raw-v1/<name>`, requires an exact Git-LFS pointer (`oid sha256` and `size`), refuses to overwrite, and refuses non-train names. HF stores these files through Xet; WikiText-2's resolved URLs were `xet-bridge`. A non-pointer reply is an engineering stop, so the step is safe.
- **R10 (REQUIRED, neutral):** `pin` does not check that the named shards are complete. A missed shard silently shrinks the corpus. Fix: require every index `0..N−1` of `train-NNNNN-of-N`, and a total at or below the card's configuration download size.

**Values to verify by hand before the download** (from the config, the ADR and `data/wikitext2/README.upstream.md`, the card the project holds, SHA-256 `d5aabf14…`):

| Value | Expected |
|---|---|
| Repository | `Salesforce/WikiText` |
| Revision | `b08601e04326c79dfdd32d625aee71d232d685c3` (the same revision as the WikiText-2 acquisition) |
| Configuration | `wikitext-103-raw-v1` |
| Card `data_files` glob for train | `wikitext-103-raw-v1/train-*` |
| Card train split | 546,500,949 bytes of text, 1,801,350 rows |
| Card configuration `download_size` | 315,466,397 bytes, which includes test and validation (test 1,305,088 and validation 1,159,288 bytes of text) |

The repository records NO shard file names, sizes or SHA-256 values for WikiText-103. Read them from the Hub's file view at that revision and compare them with what `pin` writes:
- the shard count N and the names `train-00000-of-0000N.parquet` …;
- each LFS size;
- each `oid sha256`;
- that the sum of the train sizes is below 315,466,397 and close to it, the test and validation shards being small.

For the record, the pinned WikiText-2 values are: train `e83889ba…` (6,357,543 bytes) and validation `204929b7…` (657,209 bytes).

### 4c. The P2→P3 lineage and the identity gate

- **The gate as coded is a real test.**
  - For each of the nine old parents (backbone 101 + p // 3, order 301 + p % 3) it trains the recipe for 1,024 updates on the P1 frozen `train.bytes`. `p0` refuses unless that file hashes to `P1_TRAIN_SHA256`; I confirmed the real first 4,096 WikiText-2 ranks reproduce that hash.
  - The order is `randperm(2048)` seeded with the order seed. The batch is `(s−1)·8 mod 2048`, which equals P2's `(s−1)·8` and P3's `batch_offset`.
  - It compares the full-backbone `p4_model.backbone_digest` with `backbone_sha256` in `results/p4-2026-11-12/b*-o*-baseline/result.json`.
  - Those P4 digests were computed independently of this code, from the P3 checkpoints. P10-I-S3's `load_backbone` checks the same digests against the checkpoints.
- The old parents were recorded on the same platform (Apple M5 Max, macOS 27.2.1, Python 3.12.14, torch 2.8.0; `results/p3-lt-2026-11-12/*/environment.json`).
- **Reasons the gate could fail without a defect in the adapter:**
  - a different thread count or deterministic-algorithm setting (`p0` calls `configure_process`);
  - a different torch or Accelerate build after an OS or `uv.lock` change;
  - P3's restore of the P2 optimizer at update 256 not being exactly the continuous state (a P3 implementation detail the gate would reveal);
  - the old recipe's global RNG use when building `Memory(…, 201)`. The code handles that by retrying with 201 constructed, as a declared re-use.
  - Each would be an ENGINEERING STOP before any new parent is trained, as section 7 requires.

## 5. What I would not freeze on, and what stays for the rehearsals

**Not before D0 or the freeze:** B1, B2, R6 (D0); R7, R8, R9, R11 (freeze and rehearsals); R10 (at the pin step); the ruling-10 open case; A12. The P0 parent command and the real fetch can proceed now; B1, B2 and R6 must be fixed before D0.

**For the rehearsals (untestable without real data):**
- the real pool sizes and `k_max`;
- D0's RSS against 8 GiB, and the near-duplicate share;
- the adapter identity gate on the real old parents;
- prefix and resume identity on the real table;
- R2's unit costs (after R8), and whether calibration is interior;
- NEG-REF and the planted positive on real calibration checkpoints;
- the Hub's pointer-file text and the real shard list;
- the registered pool slice and registered panel, which only the registered gates read (ADV-n4).

## My own discrepancies, kept

1. My first audit's statement that ruling 4's start equals "continuing after" P10-I-S3 is false on the real files (section 1). Ruling 4 relied on it.
2. One of the four test failures in my non-git copy (`test_the_ledger_of_record_is_the_only_ledger_file`) was caused by my own ledger copies inside the archive.
3. My first fetch probe refused because my scratch output sat inside the archive root. I reran it with `root` set to the study folder.
4. I could not identify what the ledger's `row_bytes_sha256` hashes. The conversion was confirmed per row instead.

## Appended scripts

### `_audit/ledger_walk2.py`

```
# Auditor: does the ruling-4 excluded set (shared ledger + S3 panels) give "continuing after" P10-I-S3? Compare with S3's own excluded set (excluded_spans.json of S3's data dir, read-only).
import json, collections
from pathlib import Path
import pyarrow.parquet as pq
from studies.p10i_s6 import d0
from studies.p10i_s3.data import walk_panels, overlaps
LED = json.load(open("/Users/daniellaloush/dandush03/ArborLM/data/p10i-shared/panel_ledger.json"))
S3X = json.load(open("/Users/daniellaloush/dandush03/ArborLM/experiments/P10IS3-data-20261118/excluded_spans.json"))
S3M = json.load(open("/Users/daniellaloush/dandush03/ArborLM/experiments/P10IS3-data-20261118/data_manifest.json"))
WT2 = Path("/Users/daniellaloush/dandush03/ArborLM/data/wikitext2")
rows = lambda p: pq.read_table(p, columns=["text"]).column(0).to_pylist()
val, train = rows(WT2 / "validation-00000-of-00001.parquet"), rows(WT2 / "train-00000-of-00001.parquet")
lens = [len(r.encode()) for r in val]; starts=[]; t=0
for n in lens: starts.append(t); t+=n
print("S3 row_layout_total_bytes", S3X["row_layout_total_bytes"], "mine", t)
ledger_spans = [s for w in LED["windows"] for s in d0._convert(w, starts, lens)]
s3x = [tuple(s) for s in S3X["spans"]]
_, vs, _ = d0.validation_candidates(train, val)
s3reg, s3cal = S3M["panels"]["registered"], S3M["panels"]["calibration"]
# reproduce S3's own walk
r3 = walk_panels(vs, s3x, 8192, 512, 2)
print("S3 walk reproduced from its excluded_spans:", r3 == [s3reg, s3cal])
A = walk_panels(vs, ledger_spans, 8192, 512, 2)
B = walk_panels(vs, ledger_spans + s3x, 8192, 512, 2)
last = max(s3reg + s3cal)
C = walk_panels(vs, ledger_spans, last + 1, 512, 2)
by = collections.defaultdict(list)
for s in s3x: by[s[0]].append(s)
ov = lambda P: sum(1 for r in P[0] + P[1] if any(overlaps(vs[r], q) for q in by[vs[r][0]]))
for name, P in (("ruling 4 (ledger + S3 panels), start 8192", A), ("ledger + S3's own excluded spans, start 8192", B), ("ledger, start after S3's last rank", C)):
    print(name, "| ranks", min(P[0]), "-", max(P[1]), "| ranks below S3's last rank", sum(1 for r in P[0] + P[1] if r <= last), "| chunks overlapping S3's excluded (P10-S2 / ADR-0025) spans", ov(P))
print("B == C:", B == C)
```

### `_audit/real_launch.sh`

```
#!/bin/sh
# Auditor (item 3): the smallest check the e2e test does not make -- the REAL `uv run --locked` launch of one registered stage
# (unmodified launch script gates.sh) and the REAL r4 seed checker, on a throw-away clone of 1dce8a2. No network (UV_OFFLINE=1).
# Expected: gates.sh refuses at the Decision-2 check (no freeze/Decision 2 exists) AFTER passing the clean-tree, ancestor and platform checks
# inside a uv-created .venv; the tree stays clean; the real checker prints RESULT: PASS through seed_gate(run_checker=True).
set -u
SRC=/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/agent-aaf3e2e17ef8546e4
D=/Users/daniellaloush/dandush03/ArborLM-sealed/audit-s6-a2/_audit/scratch/clone
rm -rf "$D"
git clone -q --no-local "$SRC" "$D" && git -C "$D" checkout -q --detach 1dce8a2 && echo "clone at $(git -C "$D" rev-parse HEAD)"
echo "--- 1. gates.sh through the real uv run --locked (offline)"
UV_OFFLINE=1 timeout 900 "$D/studies/p10i_s6/launch/gates.sh" "$D/experiments/run-x" HEAD; echo "exit=$?"
echo "--- 2. tree after the launch (must be empty)"; git -C "$D" status --porcelain --untracked-files=all | head
echo "--- 3. the real r4 checker through the study's seed gate"
cd "$D" && UV_OFFLINE=1 timeout 900 uv run --locked python -c "
from pathlib import Path
from studies.p10i_s6 import core, gates
r = gates.seed_gate(core.load_config(), root=Path('.'), run_checker=True)
print('passed', r['passed'], 'problems', r['problems'][:3], 'result_line', r['checker'].get('result_line'), 'returncode', r['checker'].get('returncode'), 'own rows', r['checker'].get('own_allocation_rows'))
" 2>&1 | grep -v "NumPy\|_conversion"
echo "--- 4. tree after the checker"; git -C "$D" status --porcelain --untracked-files=all | head
```

Other scripts, kept in place: ref_labels.py and fuzz_labels.py (adapted from the first audit), r16_concrete.py, cost_count.py, ledger_real.py, d0_real_probe.py, fetch_copy.py.

`Astra review: NOT_PERFORMED`. Claude review is not Astra review.
