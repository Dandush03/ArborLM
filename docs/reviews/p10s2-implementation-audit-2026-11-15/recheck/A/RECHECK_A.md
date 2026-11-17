# P10-S2 re-check of lane A (data, seeds, partitions, tokenization, filter, fetch, data generation) after the fixes

**Claude (Opus 5.5) review; Astra review: NOT_PERFORMED; not a human approval.**

- Source re-checked: commit `fc08681` (pinned copy `.../scratchpad/pin-p10s2-fc08681`, read-only). Predecessor: `docs/reviews/p10s2-implementation-audit-2026-11-15/A/AUDIT_A.md` (commit `8ad26b5`). Specification: ADR-0022 revision 5 with every addendum at its end, and `ADR-0022-addendum-combined-tasks.md`.
- Model that ran this re-check: Claude Opus 5.5 (`claude-opus-5-5`). I wrote none of the audited code.
- Environment: `/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/agent-a91c79a181109bb9c/.venv/bin/python` (Python 3.12.14, torch 2.8.0, no numpy, no transformers/tokenizers/pyarrow), macOS, CPU, cwd = the pinned tree. No network, no virtual environment created, no real model or dataset loaded (the `data/wikitext2` listing was read; no content). Test seeds and test-mode stand-ins only; registered seeds appear only as integers in constructed `SeedUse` records, never passed to a generator.
- `$A` below is this folder. Every script is run as `<python> -I $A/<script> <pinned tree> [scratch]` from the pinned tree; outputs are the `.out.txt` next to each script.

| Command | Result |
|---|---|
| `python -m pytest tests/test_p10s2_{core,data,text,prefreeze,fixA_core,fixA_data,fixA_datagen,fixA_fetch}.py -q -p no:cacheprovider --basetemp $A/bt` | **132 passed** (`pytest_laneA.out.txt`) |
| `r_hash_constants.py` | every constant equals the saved Hub trees and the ADR; 0 discrepancies |
| `r_partitions.py` | independent reimplementation under the new rules reproduces the implementation exactly |
| `r_leakage.py` | no evaluation item, reference or teacher output reaches any training or pre-freeze set |
| `r_seeds.py` | seed sets equal the ADR and addenda; strict G9 refuses the predecessor's probes |
| `r_fetch.py $A/scratch_fetch` | all fetch/ledger/fallback/record probes behave as required (scratch deleted) |
| `r_datagen.py $A/scratch_dg` | record-keeping gap found (R3) |
| `r_reads.py` | read positions under ruling C-M5 equal mine, recomputed from token bytes |
| `predecessor_rerun/*.py` | the predecessor's scripts re-run unchanged on `fc08681` (before/after below) |

Failed and superseded checker attempts: `FAILED_ATTEMPTS.txt` (two are my own mistakes).

## Verdict

**READY AFTER LISTED FIXES.**

- **Downloads of the approved model files and the seven Tatoeba files may proceed now**, by the procedure in §6. Every fetch-path item is fixed and verified. No finding below blocks a download.
- **Data generation must wait for R1, R2 and R3.**
  - R1 changes which no-gold sources are drawn, so it must be settled before the 220903 sample.
  - R2: as written, `launch/datagen.sh` would install unhashed wheels before the code can refuse them.
  - R3: a data step stopped by a link-format, window or hash guard keeps no record.

## 1. The predecessor's findings

| Item | Status | Evidence (before → after) |
|---|---|---|
| B1 small files unhashed; the manifest supplies its own digest | **Fixed** | `check_fetch`: arbitrary `git_sha1` "ACCEPTED (29 files)" → refused; large file with SHA-256 removed "ACCEPTED" → refused. Every file is verified against a code constant (`fetch_guard.py:73-106`, `verify_against_constant`), never against the manifest. A same-size tampered `config.json` is refused by digest, deleted, and its ledger row says `failed`. Re-hash before use is in `verify_tree`, `read_verified_bytes` and the immediate re-check of the safetensors (`datagen.py:451-453`). |
| B2 missing data-step steps | **Fixed**, with R2 and R3 below | All of these are present: Tatoeba against the tracked record, read as bytes (`datagen.py:209-213`); tests (a), (b) on every reference and output, (c), (d) and (e) at L = 4 and 12; the 220909 record; chrF cross-check (stop above 0.001); link resolution and symmetry. |
| B3 WikiText parquet and join | **Fixed** | `read_wikitext` checks the ADR-0004 pins (sizes 6,357,543 / 657,209 B equal the local files' sizes), reads with locked `pyarrow` and joins with `"".join(rows)`, as the lead ruled. Provenance goes into the manifest. Not runnable here (no pyarrow). |
| M1 multi-key groups in Q | **Fixed** | Predecessor corpus: "panels Q_check and Q_fit share identity groups" → G1 ok. My corpus has 42 multi-key both-reference groups, 0 repeated groups in any panel, and 0 panel pairs sharing a group. |
| M2 "can't." / "cannot." | **Fixed** | Predecessor: 26 of 26 pairs split, 7 straddling the sides → 0. Mine: 59 pairs (mid-sentence, "can't.", curly "can’t,", quoted "'it's'") → 0 split. |
| M3 evaluation panels before the freeze | **Fixed in lane A's scope** | The rehearsal world scores D_cal only (`r_leakage`: 0 evaluation sentences in its scoring sets and its combined set). See R14 for the GEN windows. |
| M4 G9 vacuity and mode label | **Fixed** | `seed_gate([], [], stage_mode=...)`: ok=True → False. A "test" use in a registered process: ok=True → refused. 220906 in the data step is refused. One of the 11 data seeds missing → refused. The +10 seed is recorded as `code-hash`. All replicates are planned. |
| M5 router generator | **Fixed** | One `plan.gen(3` with 4 uses → an initialization generator, then a fresh `plan.gen(3, "router sampling")` for the prefixes, then the lengths, then the batches (`routing.py:112-137`). |
| M6 ledger, fallback, overwrite | **Fixed** | The ledger row is `started` before each download call (29 of 29) and `completed` after. The running total equals the sum. A session that would reach 30 GB is refused before any download. The fallback manifest is 9 files (rows 5 and 6). Free text and uncommitted records are refused. Mixing in a primary file is refused. Primary files are unchanged after a fallback session. A non-fresh folder and an existing file are refused (`os.link`, `xb`). |
| M7 beam score | **Fixed** (verify on first data) | Recomputed from transition scores, with EOS counted and padding excluded; the hand case matches. The step stops on the first batch beyond 1e-5. A cached transformers 5.14.0 source (`~/.cache/uv/...`, not 4.57.1) divides by `cur_len + 1 - decoder_prompt_len`, i.e. EOS counted, which agrees with the ruling. 4.57.1 itself is unverified offline. |
| M8 listed seeds | **Fixed** | 220908 timing indices, 220909 record and 220912 injection vector are drawn in the data step. 220906 is analysis-only. G9 lists 220901–220912. |
| minor 1 NFC | Fixed | An NFD source gives the same ids and reads as its NFC form. |
| minor 2 `splitlines` | Fixed | U+2028 and U+0085 are kept inside the sentence. |
| minor 3 link columns | Fixed | `check_link_resolution` stops below 0.5 (engineering guard, accepted). |
| minor 4 +inf | Fixed | `check_filter` re-run: +inf is now refused. |
| minor 5 pooled limit | Accepted by the lead | — |
| minor 6 side check | Fixed | `data.py:275` |
| minor 7 size/cap | Fixed | Sizes are checked for every model file; the cap is per session and cumulative; small files count; free space is checked; the destination must be under `data/`. |
| minor 8 (d) at L = 12; (b), (e) on train text | Fixed | — |
| minor 9 requirements | Still unhashed, as expected. Enforcement is placed too late: see R2. | — |
| minor 10 BOS conventions | Recorded | — |
| minor 11 | Noted as allowed | — |
| minor 12 newlines | Fixed | Refused in prompts and targets; never accepted by the filter. |

Filter: the predecessor's `check_filter.py` re-run unchanged. Wilson matches to 4.9e-14, and the brute force agrees on 300 of 300. Tie rules and the Q_check bar are unchanged; only `accepts` changed.

## 2. Hash constants and safe loading

- **Constants match the saved trees and the ADR** (`r_hash_constants.out.txt`, my own parsing of the source text):
  - All 25 git-blob SHA-1 values (40 hex), all 4 SHA-256 values (64 hex), the 4 revisions and every size equal `adr-0022-review/web/*_tree.json` and `*_rev.json` character for character. 0 discrepancies.
  - The four large digests and sizes also appear verbatim in the ADR.
  - None of the 25 small files is an LFS file in the trees, so the git-blob id is the hash of the content.
- **The sizes sum as the ADR states:**
  - Teacher A 300,768,445 B (300.8 MB), teacher B 303,749,394 (303.7), student 272,437,465 (272.4).
  - Tatoeba row 4: 53,134,809 (53.1). Link files: 6,230,407 (6.2).
  - Rows 1–4: 930.1 MB. With the link files: 936,320,520 B (936 MB).
  - Fallback 315,306,933 (315.3) plus 8,138,925 (8.1).
  - Small files of rows 1–3: 9,138,858 B, as the predecessor summed.
- **No file is used before it is verified.**
  - The manifest cannot supply or weaken a digest: it must equal the constant or it is refused. Verification uses the constant, and the kind and size come from the constants, not the manifest.
  - Model files are re-hashed from disk before use. The student's config, `tokenizer.json` and `tokenizer_config.json` are parsed from the verified bytes.
  - Tatoeba files are compared with the tracked record as read. The WikiText files are checked against the ADR-0004 pins.
- **Weights-only loading.**
  - Every `torch.load` in the package passes `weights_only=True`.
  - A malicious pickle is refused (`UnpicklingError`), and a wrong digest is refused before unpickling.
  - The safetensors file is parsed by safetensors and is not executable.
- **Remote code.**
  - `trust_remote_code` appears nowhere, so it stays False.
  - The teachers load through the concrete `MarianTokenizer` and `MarianMTModel` with `local_files_only=True` from a local path. Concrete classes do not follow `auto_map`.
  - A `config.json` carrying `auto_map` and `_attn_implementation_internal` (the GHSA-29pf-2h5f-8g72 vector) is refused at fetch, by size or by digest, and again before use by `verify_downloads` or `read_verified_bytes`.
  - The pinned configs contain no such key (keys starting with "_": `_name_or_path`, `_num_labels` only).
  - Residual risk (R4, R5): the offline variables use `setdefault`, and extra files in a teacher folder are not refused.
- **SHA-1 (informational).** It is collision-weak but not second-preimage-weak. The constants are pre-existing upstream blobs, so substituting a file would need a second preimage. Acceptable.

## 3. The download path as it will run

- **Source and transport:**
  - URLs are built from the pinned 40-hex revisions only (`resolve/<sha>/<file>`); a `resolve/main` URL is refused. All URLs are HTTPS.
  - TLS: `ssl.create_default_context()` is asserted to be `CERT_REQUIRED` with host-name checking. In this interpreter it loads 123 CA certificates from `/private/etc/ssl/cert.pem`.
  - Redirects to non-HTTPS addresses are refused, but the redirect host is not restricted (R6).
- **Destination:**
  - It must be under the git-ignored `data/` (resolved path) and be fresh. `fetch.main` also checks `git check-ignore`.
  - Files are never overwritten: the `.part` file is opened `xb`, then `os.link`.
- **Ledger:**
  - A row is written before each file and completed after it, and on failure it records the bytes fetched.
  - A session that would take the total to 30 GB or more is refused before anything is fetched. Running totals are rewritten consistently.
  - The study ledger records a `fetch` start marker and end entry.
- **Fallback:** only with `{"path", "commit"}` naming a file that exists at that commit, and only rows 5 and 6, into a different fresh folder.
- **Tatoeba:**
  - The seven files must be in one manifest, and therefore one session.
  - `freeze_tatoeba_record` writes `studies/p10s2/records/tatoeba_session.json`, a tracked path that is not ignored, from the re-hashed bytes compared with `fetch_record.json`.
  - Once the record exists, it must be committed and clean. A changed file, or a later weekly export in another folder, is refused against it.
  - A second primary Tatoeba session is not itself refused (R7).

## 4. `datagen`

- **Order and steps.** As `_run` executes them:
  1. Requirements check.
  2. Hashes: models against constants, Tatoeba against the record, WikiText against the pins.
  3. Conversion; the plain-file SHA-256 is recorded.
  4. Equivalence and (d), (e) at L = 4 and 12; injection vector from 220912.
  5. (c) on 1,000 sequences from 220910.
  6. Corpus parse, link resolution and symmetry.
  7. Teacher load: re-hash, weights-only, local.
  8. `build_bundle`:
     - Partition and panel hashes, before any teacher output exists.
     - 220909 record and 220908 timing draw.
     - Generation on sources and on Q with both teachers.
     - Filter fit and check, qualification.
     - Both teachers on E_A, E_B, E_C, E_open, D_cal and D_con, stored and not scored.
     - 220911 permutation, with its digest and the duplicate count.
     - Whole-string check of the combined layouts.
     - chrF cross-check.
     - Tests (a) and (b).
  9. Stops: test (a) on prompts or R-icl; chrF above 0.001; G9 on the data step (strict, all 11 seeds required); the score mismatch. The freeze also refuses on the combined whole-string check and on test (a).
- **Ledger and cap.** The step runs under `Ledger.measure("datagen")` and the `StageGuard` watchdog. It refuses to start if the ledger has less than the cap, and a tick past the cap stops it (shown). The cap is 6,480 s; see R16.
- **Requirements.** `check_requirements_hashed` refuses the current file (8 unhashed pins). It is called inside Python, after `uv run --with-requirements` has already installed the packages (R2).
- **Combined-tasks addendum, data parts:**
  - The 220911 σ and the pair digest are in `bundle.extra`, and `build_world` re-checks the digest.
  - The duplicate-English count is reported. It is 0 by construction: E_C items are unique normalized keys.
  - The whole-string check is implemented and enforced at the freeze. Its classifier is imperfect (R9).
- **Both teachers on every panel.** Both teachers generate on every panel §6.1 names, and the outputs are stored. On whether "not computed" is the only workable reading of the other teacher's score: **it is not** (R13).

## 5. Leakage end to end (`r_leakage.out.txt`, `r_partitions.out.txt`)

- **Sets checked.** On the stand-in bundle and world (test seeds), no evaluation sentence (E_A, E_B, E_C, E_open), no reference, and no teacher output on one appears as a source, a target or a shared identity group in any of the following:
  - the accepted pools and gold pools;
  - all four replicate streams;
  - the 1,843 training rows of the bank;
  - Q_fit, Q_check, D_cal and D_con;
  - the router prompts of both replicates;
  - the 220909 sentences and the seen-item order;
  - the rehearsal world's scoring and combined sets.
- **Exclusion of evaluation references.** 0 accepted outputs equal an evaluation reference, and pool-level G1 is ok.
- **E_open coverage.** The dry stand-in happens to have no E_open item. My partition corpus has 10, and none of their strings reaches the source pools ("in an evaluation string: 0").
- **Remaining defect: R1.** No-gold sources can share identity groups with Q, D_cal and D_con:
  - 21 such sources for capability A in my corpus.
  - Replicate draws took 4 and 1 such groups.
  - G1 passes them.
  - This is not a leak into evaluation; it is a breach of the literal G1.

## 6. Remaining findings

Numbering: R12 (option lines in the requirements check) is folded into R2; R15 (SHA-1 strength) is the informational note in §2.

**R1 (major; must be settled before data generation).** T streams can share identity groups with Q, D_cal and D_con, and G1 cannot see it. Literal G1 says "every pair of panels and streams is disjoint in identity groups".

- Where: `data.py:336` (`source_pool`) does not exclude the groups of the training-side panels, although `gold_pool` at `:335` does. `gate_g1` (`data.py:511, 520-522`) checks stream groups against evaluation panels only.
- Demonstration: a French-only sentence sharing a French reference with a D_cal item becomes a no-German source in that item's group.
- Fix:
  - In `source_pool`, drop keys whose `group_of_key.get(k, -1)` is in the groups of Q_fit, Q_check, D_cal or D_con.
  - In `gate_g1`, compare stream groups with the groups of all panels.
- **PENDING LEAD REVIEW:** the readings note of the freeze README (item 7) does not mention training-side panels. The lead should confirm that the literal text applies.

**R2 (major; before data generation).** "Installed with hashes required" is not enforced.

- `launch/datagen.sh:18` runs `uv run --locked --extra pilot --with-requirements ...`, which resolves, downloads and installs before Python starts.
- `datagen.py:443` refuses unhashed pins only afterwards. With today's file, running the launch script would fetch 8 unhashed packages and their dependencies from PyPI without a ledger row.
- `uv run` (uv 0.12.15) has no `--require-hashes` option. Whether it verifies hashes present in a `--with-requirements` file is unverified offline.
- `unhashed_requirements` skips every option line (`datagen.py:143`), so `-e ./x`, `-r other.txt` and `--extra-index-url http://...` pass.
- Fix:
  - A pre-flight in `datagen.sh`, before `exec`, on the locked environment only, that runs `check_requirements_hashed`.
  - Make the check refuse any option line except `--hash` continuations.
  - Make the step stop if `package_versions()` differs from the eight pins.
  - **PENDING LEAD REVIEW:** the mechanism that guarantees hash-checked installation. One example: verify, before the first run, that the uv overlay was built in hash-checking mode (`UV_REQUIRE_HASHES=1`, if `uv run` honours it), or install the overlay with `uv pip install --require-hashes`.

**R3 (major; before data generation).** A failed step keeps no record unless it raised `DatagenStop` (`datagen.py:434`).

- `FetchRefused`, `LinkFormatError`, `WindowsInsufficient` (the ADR's "returns to the lead"), `ValueError` from a newline, `SeedRefused` and `PendingLeadReview` propagate with no `prefreeze_record.json`.
- Demonstrated: a `FetchRefused` stop leaves no record file, while a `DatagenStop` stop keeps one.
- Fix: in `run`, after the start, catch `BaseException`, write the record with `stopped` set to the type and message (and the window counts for `WindowsInsufficient`), then re-raise.

**R4 (minor).** `datagen.py:424-425` uses `os.environ.setdefault`. A pre-set `HF_HUB_OFFLINE=0` survives (shown). Fix: assign `"1"` unconditionally; this is mitigated by `local_files_only=True` and local paths.

**R5 (minor).** `datagen.py:353-359`: the teacher folder is not checked for files beyond the seven verified ones before `from_pretrained`, which looks for other weight and tokenizer files. Fix: require `set(os.listdir(downloads/label)) == {pytorch_model.bin, *MARIAN_FILES}`.

**R6 (minor).** `fetch.py:34-38` restricts redirects to HTTPS but not to hosts. Tatoeba has no constant at its first download. Fix: for Tatoeba, accept only `downloads.tatoeba.org`; record `r.geturl()` and `Last-Modified` in `fetch_record.json`.

**R7 (minor).** `fetch_session` accepts a second primary manifest with the Tatoeba files into another fresh folder, so a later weekly export can be downloaded. The committed record still refuses it at use. Fix: refuse Tatoeba rows when the tracked record exists or the download ledger already has completed Tatoeba rows.

**R8 (minor; procedure).** The paths do not line up.

- `fetch.py` suggests `data/p10s2-downloads-<date>/`, while `launch/datagen.sh` reads `<run-dir>/downloads`.
- `datagen.sh` cannot pass `--wikitext-dir`, and the default `ROOT/data/wikitext2` does not exist in a fresh worktree; the pinned tree has no `data/`.
- Both ledgers are per checkout.
- Fix: document the paths, or let the script take the WikiText folder. §7 gives the paths to use.

**R9 (minor).** `prefreeze.py:266-268` classifies only the first differing token of the whole-string check. A mismatch inside the reference can mask a later boundary mismatch. Fix: also require the whole-string ids outside the reference span to equal the segment ids, aligned from both ends.

**R10 (minor).** `data.py:106-108` takes `parts[2]` of `split("\t")`, so a sentence containing a tab is truncated silently. Fix: `split("\t", 2)`, and count rows with more than three fields.

**R11 (minor).** `datagen.py:318` uses `load_state_dict(strict=False)`, which hides key mismatches; they would surface only as an equivalence failure. Fix: assert that the missing keys are a subset of `{"lm_head.weight"}` and that there are no unexpected keys.

**R13 (PENDING LEAD REVIEW; not a data-step change).**

- The README returns §6.1's "other teacher's score" on a single-language panel as needing a choice.
- §4.3 item 2 already defines "the other teacher's score on that capability": the other teacher's output against this capability's references on Q, computed at `prefreeze.py:135`.
- Applying the same definition to E_A, E_B, E_open, D_cal, D_con and E_C needs no new choice, and the outputs are stored. "Not computed" is therefore not the only workable reading.

**R14 (PENDING LEAD REVIEW; lane B).** The rehearsal world keeps the registered GEN windows (`rehearsal.py:144`), and `stage_evaluate` computes GEN on them before the freeze. §6.4 says "This data is used for nothing else". Ruling A-M3 names evaluation panels only.

**R16 (PENDING LEAD REVIEW).** The data step is capped at 6,480 s (provisional). It covers:

- up to 2 × 60,000 beam-4 translations;
- both teachers on Q and on six panels;
- tests (a)–(e) and the cross-check.

If the cap is reached, the step stops with a record. Whether a capped data step may be re-run is not stated (§16: "Nothing is re-run with changed settings").

## 7. Ordered procedure for the first real download (rows 1–4 plus the link files)

Run every step from **one** checkout of the S2 branch at a clean commit. Its `experiments/P10S2/ledger.jsonl` and `DOWNLOAD_LEDGER.md` are the ledgers.

1. **Offline checks:**
   - `uv run --locked pytest tests/test_p10s2_fixA_fetch.py tests/test_p10s2_fixA_datagen.py -q`
   - `uv run --locked python -c "import ssl;print(ssl.create_default_context().cert_store_stats())"`: expect `x509_ca` > 0.
   - Confirm that `uv run --locked` does not need to sync, i.e. the environment exists; otherwise the locked packages are a download too.
2. **Write the manifest outside the destination:**
   - `mkdir -p experiments/P10S2 && uv run --locked python -c "from studies.p10s2 import fetch_guard as g; print(g.manifest_json(g.build_manifest()))" > experiments/P10S2/manifest-primary.json`
   - Expect 29 files: teacher_a 7, teacher_b 7, student 8, tatoeba 7.
3. **Fetch** into a fresh folder that `datagen.sh` will find as `<run-dir>/downloads`:
   - `uv run --locked python -m studies.p10s2.fetch --i-have-recorded-human-approval --manifest experiments/P10S2/manifest-primary.json --dest data/p10s2-pre-<YYYYMMDD>/downloads`
   - Expected on success: no output and exit code 0.
   - Expected files: 29 under the destination, plus `fetch_record.json`. Model files have exactly the constant sizes; Tatoeba sizes may differ from the 14-Nov-2026 listing.
   - Expected ledger: 29 rows in `DOWNLOAD_LEDGER.md`, all `completed`, with a running total near 936,320,520 B.
   - Expected study ledger: a `fetch` start marker and end entry.
   - On a refusal: `refused: ...` on stderr and exit code 2. On a network error: a traceback, with the ledger row `failed: URLError` and the `.part` file deleted.
   - After any failure, keep the partial folder, record it, and repeat the whole manifest into a **new** fresh folder (the Tatoeba files must come from one session).
4. **Commit `DOWNLOAD_LEDGER.md`.**
5. **Freeze the Tatoeba digests before anything else reads them:**
   - `uv run --locked python -c "from pathlib import Path; from studies.p10s2 import fetch_guard as g; print(g.freeze_tatoeba_record(Path('data/p10s2-pre-<YYYYMMDD>/downloads'), g.ROOT / g.TATOEBA_RECORD))"`
   - Expect `status: written: commit it before the freeze`, 7 files with SHA-256 and bytes, and the session date.
   - Commit `studies/p10s2/records/tatoeba_session.json` immediately.
   - Re-run the same command: expect `verified against the committed record`.
6. **Verify the model files offline:**
   - `uv run --locked python -c "from pathlib import Path; from studies.p10s2 import fetch_guard as g, datagen; print(len(g.verify_tree(Path('data/p10s2-pre-<YYYYMMDD>/downloads'), datagen.model_names())))"`
   - Expect `22`.
7. **Wheels and data generation: only after R1–R3 are fixed and re-checked.**
   - Resolve `requirements-datagen.txt` with hashes for Python 3.12 against torch 2.8.0. Review it and commit it.
   - Write the wheels' ledger row before the install.
   - Copy `data/wikitext2` into this checkout's `data/`; it is verified against the ADR-0004 pins at use.
   - Run `sh studies/p10s2/launch/datagen.sh data/p10s2-pre-<YYYYMMDD> <clean HEAD>`.

The download is unsafe, and should be stopped and returned, if any of the following holds:

- a file is used before step 6;
- `DOWNLOAD_LEDGER.md` is not committed;
- the Tatoeba record is not committed before data generation;
- the fallback is fetched without a committed decision record.

## 8. What only the first real data can verify (checklist for the lead)

1. Beam score: the explicit mean (EOS counted) equals `sequences_scores` within 1e-5 on the first batch of each teacher. Record each `generation_config.json` (`num_beams`, `length_penalty`, `bad_words_ids`, `max_length`). Real 4.57.1 behaviour is unverified offline.
2. Link files:
   - Column order: the English id first in `eng/eng-*_links`. Resolution shares (guard 0.5) for all four files.
   - The one-direction English id counts against the `deu/` and `fra/` files.
   - Malformed-line counts. Sentences containing tabs (R10).
3. Groups and sizes:
   - The group-size distribution and the largest group (a reference such as "Ja." can create a giant component); pairs sent to training by the more-than-50 rule; the evaluation share.
   - Sufficiency: E_A and E_B at least 500, E_C at least 250, available sources at least 10,000 per capability, gold at least 8,000.
   - The count of no-gold sources whose group is a Q, D_cal or D_con group (R1).
4. WikiText:
   - Row count and characters of the joined text.
   - Both GEN strata at least 100 on the 256-token grid; otherwise `WindowsInsufficient`, which needs R3 to leave a record.
5. Tokenizer:
   - `bos_prepended_by_default` is False and `add_bos_token` is absent or false.
   - Test (a) shows 0 mismatches on prompts and R-icl prompts.
   - Test (c): 0 failures on 1,000 sequences (no stop is specified; read the count).
   - Test (b): count of failures.
   - The combined whole-string check reports `required_mismatches` = [].
6. Student equivalence at L = 4 and 12: maximum logit difference at most 1e-3, identical top-1, injection, and greedy cache against `generate`.
7. Teachers:
   - They load offline from the local folder with exactly the seven files (R5).
   - Both 100-sentence records are present.
   - The newline-output counts.
8. chrF cross-check: maximum difference at most 0.001 on 1,000 Q pairs.
9. G9 on the data step: ok, with all 11 seeds recorded (220906 absent).
10. Wall time against the 6,480 s cap (R16); the charged hours in the study ledger.
