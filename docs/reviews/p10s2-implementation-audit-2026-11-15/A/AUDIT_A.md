# P10-S2 implementation audit, part A: data, seeds, partitions, filter, leakage, fetch-and-verify

**Claude (Opus 5.5) review; Astra review: NOT_PERFORMED; not a human approval.**

- Audited source: commit `8ad26b5` (branch `claude/p10-s2`), pinned copy at `.../scratchpad/pin-p10s2-8ad26b5` (read-only). Stand-in implementation by Sonnet 5.5. The auditor wrote none of it.
- Specification: `docs/decisions/ADR-0022-p10-s2-two-teacher-transfer.md` revision 5 as pinned. The 30 GB download addendum and `DOWNLOAD_LEDGER.md` are **not** in the pinned tree. They were added after the pin, in commit `14f6e82` on `claude/p10-s2`, and I read them with `git show 14f6e82`. As instructed, the combined-tasks addendum (seed 220911, C1/C2) is out of scope.
- Model that ran this audit: Claude Opus 5.5 (`claude-opus-5-5`).

## Verdict

**READY AFTER LISTED FIXES.** Three blockers and eight majors are listed below.

- **Downloads.** These may start once B1 and the ledger part of M6 are fixed. Each fix is small, and the digests that B1 needs already exist in the reviewer's saved Hub records (§6b).
- **Data generation.** This is not ready until B2 and B3 are fixed. `datagen.py` cannot run as written: it reads WikiText files that do not exist locally. It also skips four of the steps that §14.2 requires.
- **Partition, filter and seed logic.** I reimplemented this from the ADR text and it reproduces the implementation exactly on a synthetic corpus. Two exceptions are defects that the reimplementation exposed (M1, M2).

## Environment and commands

- Interpreter: `/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/agent-a91c79a181109bb9c/.venv/bin/python` (Python 3.12.14, torch 2.8.0, no numpy), on macOS (darwin) and CPU.
- Working directory: the pinned tree. No network was used, no virtual environment was created, and no model or real dataset was loaded. The directory listing of `data/wikitext2` was read; no file content was read.
- Commands, each run from the pinned tree (`$A` is this folder):
  - `python -m pytest tests/test_p10s2_core.py tests/test_p10s2_data.py tests/test_p10s2_text.py tests/test_p10s2_prefreeze.py -q -p no:cacheprovider --basetemp $A/bt`: **80 passed**.
  - `python $A/check_seeds.py` produces `check_seeds.out.txt`.
  - `python $A/check_partitions.py` produces `check_partitions.out.txt`.
  - `python $A/check_filter.py` produces `check_filter.out.txt` (about 5 minutes).
  - `python $A/check_tokenization.py` produces `check_tokenization.out.txt`.
  - `python $A/check_fetch.py $A/scratch` produces `check_fetch.out.txt`. The malicious-pickle probe file was written to scratch and then deleted.
  - `python $A/check_saved_trees.py` produces `check_saved_trees.out.txt`.
- Failed checker attempts are kept in `FAILED_ATTEMPTS.txt` (one, my own bug).

## What was checked and holds

1. **Seeds (`check_seeds.out.txt`).**
   - The registered-run set (4 bases × offsets 0–10, 44 seeds), the data set 220901–220910, the calibration set 221001+100i+o and the rehearsal set 222001+100i+o all equal the sets I parsed from the ADR text. The test range is 229001–229999.
   - All listed registered seeds lie in 220001–228999 and outside the calibration, rehearsal and test ranges. The modes are pairwise disjoint.
   - No S2 seed, in any mode, falls in a listed range of P9, P9-I, the review seeds, P9-II, S0 or S1 (checked against ADR-0021 §6.3 and ADR-0022 §9). None of the 51 seed values in the other configs collides with S2.
   - `SeedPlan.gen` starts a fresh generator for every use.
     - Appended rows use +6, which never duplicates the first-stage keys (+0).
     - M-joint uses +7, the LoRA arms +8 and the E-table +9.
     - M-ii's replay order gets a fresh +2 generator.
     - Training draws use +1 (split, then A, then B) and gold draws use +5 (A, then B).
   - Partition and calibration seeds are refused in registered-run mode, and the G9 source check passes.
   - Informational: a foreign initialization seed f collides with an S2 seed through f + 1000·k only for k ≥ 218.
2. **Partitions, panels and draws (`check_partitions.out.txt`).**
   - I wrote an independent implementation of §5.2: my own normalization, a graph search for components, the assignment, the vocabulary, the panels drawn in the ADR's order (assignment, Q, D_cal, D_con, E_A, E_B, E_C, E_open, with the Q split on its own seed), the no-gold sources, the gold pools and the replicate draws.
   - On a synthetic corpus of 1,752 English sentences it reproduces the implementation exactly: groups, assignment, vocabulary, every panel, both source pools, both gold pools, and the four replicate draws.
   - Other properties hold:
     - Groups above 50 pairs go to training; 0.2002 of the remaining pairs go to evaluation.
     - T_A and T_B are disjoint in English in every replicate.
     - With an odd shared count, the extra shared source goes to neither stream.
     - Sufficiency arithmetic matches (exclusive + half ≥ ⌈8,000 × 1.25⌉, and gold ≥ 8,000).
     - The replicate overlap is reported.
     - No source lies in an evaluation string.
3. **Filter (`check_filter.out.txt`).**
   - My Wilson lower bound, solved as a quadratic, matches `text.wilson` to within 4.9e-14 for n ≤ 600 and every k.
   - The grid has 24 settings, as specified.
   - On 300 random synthetic Q_fit sets, `fit_filter` agrees with my brute force of the ADR rule every time. The rule is: largest accepted share among settings with lower bound ≥ 0.90, then the larger τ, then the narrower range. Constructed ties resolve as the ADR says.
   - Q_check needs a point precision ≥ 0.90 with ≥ 150 accepted items: 135/150 passes, and 149 accepted fails.
   - Numerical note: at n = 500, a lower bound ≥ 0.90 needs a point precision ≥ 0.928; at n = 150 it needs 0.953.
4. **Fetch identities (`check_fetch.out.txt`, `check_saved_trees.out.txt`).**
   - The four revisions, the four weight SHA-256 values and their sizes, and the nine Tatoeba paths and sizes equal the ADR text character for character. The file lists equal rows 1 and 3, and the URLs are `resolve/<pinned sha>/<file>`.
   - The validator refuses an unapproved file and a changed URL.
   - `load_pickle_weights` refuses a malicious pickle (`UnpicklingError`) and refuses a wrong digest before unpickling.
   - The reviewer's saved Hub records, fetched with `/tree/<sha>`, where main equalled the pin at the time, agree with the pins. They give the git-blob SHA-1 of every small file (listed in §6b). The saved `config.json` copies hash to those blob ids and do not contain `_attn_implementation`.
5. **Rehearsal record.** `rehearsal.json` holds only times, peak memory and the rung decision (`rehearsal.py:92-129`), and the data step draws no registered-run seed (`build_bundle(..., "registered-data", 0)`).

## Blockers

**B1. Small model files are downloaded and loaded without any hash check, so the advisory mitigation the ADR relies on does not exist.**

The small files are `config.json`, `generation_config.json`, `tokenizer.json`, `tokenizer_config.json`, `vocab.json`, `merges.txt`, `special_tokens_map.json`, `source.spm` and `target.spm`.

Where it happens:

- `fetch_guard.build_manifest` (`fetch_guard.py:87-94`) gives these files no digest.
- `validate_manifest` (`fetch_guard.py:129-133`) accepts any non-empty `git_sha1` string and never compares it.
- `fetch.run` (`fetch.py:57-58`) verifies only an entry's `sha256`, and only if the manifest supplies one.
- `datagen.run` never hashes them before it calls `LlamaConfig.from_json_file` (`datagen.py:99`), `Tokenizer.from_file` (`:61`), `MarianTokenizer.from_pretrained` and `MarianMTModel.from_pretrained` (`:135-136`). The `.spm` files are parsed by native sentencepiece code.
- The same validator also accepts a manifest whose large pickle entry has its `sha256` removed and carries an arbitrary `git_sha1` (probe "ACCEPTED (29 files)").
  - `datagen.run` (`:166-168`) compares only the digests that `fetch_record.json` recorded at fetch time. It does not re-hash the files on disk, so the student safetensors is never re-checked before `load_file` (`:172`).

Why it matters: ADR §14.2 lists the mitigation for GHSA-29pf-2h5f-8g72 as "the configuration files are hash-pinned". As written, a substituted `config.json` would reach `transformers`.

Fix:

- Pin every small file's git-blob SHA-1 in `fetch_guard.py` as code constants. They are available offline in `check_saved_trees.out.txt`, from `adr-0022-review/web/*_tree.json`.
- In `fetch.run`, verify every file against the code constant (`LARGE[...]` or the small-file table), never against the manifest, and delete the file on a mismatch.
- In `datagen.run`, re-hash every file on disk before its first use.
- Make `validate_manifest` refuse an entry whose digest differs from the code constant, or is missing.

**B2. `datagen.run` omits steps that §14.2 and §4.1 require, so its outputs would not meet G7 or G8 or the frozen-record rules.**

- Step 1, "hash checks of every downloaded file": missing; see B1. The Tatoeba files (`datagen.py:192-193`) are parsed with no check at all.
  - Their "recorded at first download and frozen" digests live only in `fetch_record.json` inside the git-ignored downloads directory. Nothing commits or freezes them.
- Test (a), segment ids against whole-string ids for every training row, evaluation prompt and R-icl prompt, with 0 required on prompts: `check_segments_vs_whole` is never called on real data.
- Test (b) runs on 100 slices of WikiText validation (`datagen.py:190`). The ADR requires it on "every reference and accepted teacher output".
- The 100-sentence teacher tokenizer record (§4.1, §14.2 step 5, seed 220909) is absent: 220909 is never drawn anywhere.
- Step 6, the chrF cross-check against sacrebleu on 1,000 pairs of Q: `crosscheck_chrf` exists but is never called.
- The link-file symmetry check that §14.1 makes mandatory: `data.link_symmetry` exists but is never called, and the count of one-direction English ids is not reported.

Fix: add each step to `datagen.run`, with stop conditions where the ADR gives one (test (a) = 0 on prompts; chrF within 0.001). Write the Tatoeba digests into a committed record before the data step, and verify them in `datagen.run`.

**B3. `datagen.run` reads `data/wikitext2/wiki.valid.raw` and `wiki.train.raw` (`datagen.py:180-181`), but the local copy is `train-00000-of-00001.parquet` and `validation-00000-of-00001.parquet` (ADR-0004 acquisition, `data/wikitext2/manifest.json`).**

The step would fail after the student conversion. More importantly, "the validation file tokenized once as a whole" (§6.4) and the window grid depend on how the parquet rows are joined into text. The ADR does not define that.

Fix: read the parquet files with the locked `pyarrow` (the `pilot` extra in `uv.lock`, as `src/arborlm/pilot_data.py:_rows` does), after verifying them against the ADR-0004 pins. Define the join explicitly: the rows concatenated in order, each row as stored with its own newline.

**PENDING LEAD REVIEW:** the join rule, because it fixes the GEN panel and the window strata.

## Majors

**M1. Q_fit and Q_check can share identity groups, which makes G1 fail falsely on real data** (`data.py:223-229, 248-253`).

`draw_plain` filters candidates by `used` groups once, before the draw. Two keys of the same group (for example a contraction variant pair, both with German and French references) can therefore both enter Q. The 220902 split can then separate them.

Demonstrated on the synthetic corpus: one group is drawn twice into Q, and `gate_g1` reports "panels Q_check and Q_fit share identity groups". On Tatoeba, multi-key groups among the both-reference sentences are common, so pool-level G1 in the data step would fail. `prefreeze_summary` would then mark the material not teacher-only.

Fix:

- Draw whole groups in `draw_plain` and `draw_stratified`: permute the groups, then take one key per group, or update `used` inside the loop and skip already-used groups.
- Split Q by group.
- Test it with a corpus that has multi-key groups.

**M2. Contraction expansion misses contractions with punctuation attached** (`text.py:37-40`).

`expand_contractions` looks up whitespace tokens verbatim, so "can't.", "don't," and "it's?" are not expanded. Sentence pairs such as "No, I can't." / "No, I cannot." therefore land in different identity groups.

In the synthetic corpus, all 26 such pairs were split, and 7 of them straddle sides; for example "No, apples says I can't." is on the training side while "No, apples says I cannot." is on the evaluation side.

Why it matters: §5.2 requires these to be one group. The same rule feeds the no-gold test (`data.py:264`) and the evaluation strings (`data.py:192-197`). A held-out sentence's contraction variant can therefore be a training-side gold pair, or a no-gold source whose teacher output trains the store.

Fix: strip leading and trailing punctuation (except the apostrophe) from each token before the lookup, then re-attach it, as `my_expand_corrected` in `check_partitions.py` does. Also require `side[group] == "eval"` for evaluation candidates (`data.py:217, 256`); this had no effect here (0 cases) but is cheap.

**M3. Evaluation panels are scored before the freeze. PENDING LEAD REVIEW: the specification conflicts with itself.**

What the code does:

- `rehearsal.measure_rates` scores a rehearsal-trained store on E_A and E_B (`rehearsal.py:115`).
- It runs `stage0_scores`: the student and the stored teacher outputs on E_A and E_B (`:118`).
- It runs `score_snapshot` with GEN, the learned route and the combined panels (`:117`).
- It times scoring on `next(iter(ctx.panels))`, which is E_A (`:119`).
- `gates.g2` (`gates.py:35-43`) scores E_A and E_B and records the list of panels whose gap is undefined. If the pre-freeze gates stage that §12.3 requires ("at real size on rehearsal seeds before the freeze") were run, that list would be written before the freeze.

What the ADR says: §12.1 and §14.2 step 5 say evaluation panels and outputs "are not scored before the registered run". G2 and the pre-freeze gates stage need E-panel scoring.

The rehearsal currently discards the scores and records only times, so no number leaks today, but the code computes them.

Fix (proposed): before the freeze, time and test scoring on D_cal, or on a training-side panel of the same size and composition. Run G2's E-panel gap check only in the registered gates stage. The lead must rule on the conflict.

**M4. Gate G9 can pass vacuously and can be fooled by a mode label** (`core.py:242-286`, `gates.py:268-271, 278`).

- `seed_gate([], [])` returns ok.
- Every recorded use is judged by the mode string its caller passed, so a `"test"` or `"rehearsal"` use inside a registered process passes. The probe passes with a 229001 "test" use next to a registered one.
- `run_gates` plans only replicate 0's seeds.
- The +10 oracle-code seed is never recorded, because the hash seeds no generator, so G9 cannot see it.

The ADR asks that G9 "inspects the seeds used" and that "every seed of the registered run is one of the listed registered seeds".

Fix:

- Pass the stage's mode to `g9` and require every recorded use to carry that mode (registered-run in a registered process).
- Require a non-empty record that equals, as a set, the planned set for the stages run.
- Plan all replicates.
- Record `code_seed()` uses.

**M5. The router draws its initialization and its sampling from one +3 generator** (`routing.py:111-133`).

§9 says "a fresh +3 generator, after the router's initialization, samples the 'none' prefixes and then orders the router's batches". §5.4 says "the sampling generator of §9 draws the prefixes, then those lengths, then the batch order".

The code makes one `plan.gen(3)` and uses it for `Router(...)`, `randperm`, `randint` (lengths) and `randint` (batches); `check_tokenization.out.txt` confirms one `plan.gen(3` call and four uses. The draws are still deterministic, but they are not the registered ones.

Fix: `gen_s = plan.gen(3, "router sampling")` after `Router(...)`, used for the prefixes, then the lengths, then the batches.

**M6. The fetch does not write the download ledger, and a fallback fetch would overwrite the frozen Tatoeba bytes** (`fetch.py:47-65`, `fetch_guard.py:87-89, 111`).

- The lead's rule (`HUMAN_DECISIONS_2026-11-15.md`, commit `14f6e82`) requires a ledger row in `docs/reviews/p10-design-2026-11-15/DOWNLOAD_LEDGER.md` "written before a fetch is started and completed after it". `fetch.py` writes only `fetch_record.json`, at the end.
- `build_manifest(fallback_human_decision=...)` lists every primary file again. `run()` writes `dest/tatoeba/eng_sentences.tsv.bz2` with `tmp.rename(dest)`, which would replace the first-session export with a later weekly one. The ADR requires the primary files to stay frozen and the fallback files to come from a later export.
- The fallback is unlocked by any non-empty string.

Fix:

- Append a ledger row (date, study, what, source, revision or hash, licence, declared bytes, running total, status "started") before each file, and complete it afterwards. Refuse if the running total would reach 30 GB.
- Make the fallback manifest contain rows 5 and 6 only.
- Refuse to overwrite any existing file; verify it instead.
- Require the fallback decision to name a committed record (path and commit).

**M7. `sequences_scores` is used unverified as the §5.3 score** (`datagen.py:144-146`).

In `transformers` beam search, `sequences_scores` is the sum of processed log-probabilities divided by (generated length)^`length_penalty`. Three things are unknown until the step runs: the generation config's `length_penalty` for these models, whether the length counts the EOS token or the decoder start token, and whether logits processors such as the pad-token ban change the summed values.

The ADR's definition is "sum of the token log-probabilities of the returned hypothesis divided by its token count". The code only carries a comment ("to verify").

Fix: compute the score explicitly with `model.compute_transition_scores(gen.sequences, gen.scores, gen.beam_indices, normalize_logits=False)`, summing over the non-pad generated tokens and dividing by their count. Assert agreement with `sequences_scores` within 1e-5 on the first batch and record the result. If they disagree, use the explicit value and report it.

**PENDING LEAD REVIEW:** whether EOS counts as a token.

**M8. Listed partition-side seeds are not used as §9 says.**

- 220906 (bootstrap) and 220908 (timing items) are never drawn. `stage_timing` takes the first n items (`stages.py:178`).
- 220909 is missing (B2).
- 220910 is also used for the unlisted equivalence injection vector (`datagen.py:184`); G9 passes it (probe).

§9 says 220902–220910 "are drawn once, in the data-generation and partition steps, and stored". Drawing the bootstrap indices later would break that rule.

Fix:

- Draw and store the 220908 timing indices and the 220909 sentences in the data step.
- For the bootstrap, either store per-panel resample indices from 220906 in the data step or have the lead rule on a post-freeze use (**PENDING LEAD REVIEW**).
- Replace the injection vector's seed with a deterministic, seedless vector, or a lead-listed seed.

## Minors

1. **No NFC before tokenization** (`tokenization.py:214-228`, `world.py:46-50`). The probe shows that an NFD source gets the same key but different ids and reads. Fix: NFC-normalize source and target text before `prompt_segments` and `target_segments`.
2. **`parse_sentences` uses `str.splitlines()`** (`data.py:74`). This splits on U+2028, U+0085, U+000B and similar characters inside a sentence, and silently truncates it (probe: "first part second part" becomes "first part"). Fix: use `split("\n")`, strip "\r", and count malformed lines.
3. **`parse_links` does not check column order or resolution** (`data.py:81-89`). If the columns were swapped, the data would look insufficient rather than fail loudly. Fix: report the share of rows whose first id is English and whose second is in the target file, and stop below a stated share.
4. **`accepts` admits a +inf score** (`filtering.py:51`; probe True). Fix: require `math.isfinite(o.score)`.
5. **The new-token limit uses German D_cal references only** (`prefreeze.py:126`). §5.4 says "the gold references of D_cal". Fix: include `refs["B"]`. **PENDING LEAD REVIEW:** one limit for both languages, or one per language.
6. **Evaluation candidates are chosen by string membership** (`data.py:217, 256`), not by `side[group] == "eval"`; see M2.
7. **Size and cap checks in `_download` are loose** (`fetch.py:41`).
   - The size check is skipped for every file if "tatoeba" appears anywhere in the destination path.
   - The byte cap is per file, not cumulative.
   - Small files have `size` None, so they count 0 toward the declared total.
   - The 6 GB disk cap is not enforced.
   - The destination is not forced under the git-ignored `data/`.
8. **Equivalence tests (d) and (e)** (`datagen.py:186`).
   - Test (d) runs at L = 4 only; add L = 12, since calibration may choose it.
   - Tests (e) and (b) use WikiText *validation* text, which §6.4 reserves for GEN ("used for nothing else"). Use the train text or task prompts instead.
9. **`requirements-datagen.txt` is incomplete and stale.** It has 8 pins and no hashes or transitive dependencies. Its header, and the docstrings of `fetch.py` and `datagen.py`, still say the wheels await confirmation, which the 30 GB addendum (`14f6e82`, not in the pin) supersedes. Fix: resolve once with hashes, for example with `uv pip compile --generate-hashes` for Python 3.12 against torch 2.8.0, commit the result, and install with `--require-hashes`.
10. **`HFTokenizer.bos_id` reads `tokenizer.json` only** (`datagen.py:63-70`). Also record `tokenizer_config.json`'s `add_bos_token` and `clean_up_tokenization_spaces` (§14.2 names both files).
11. **The two ablation subsamples use identical positions** (`prefreeze.py:125`). E_A and E_B each draw from a fresh 220904 generator, so they use the same index positions. This is allowed by the ADR's wording ("the same for every cell"); noted only.
12. **Sources and targets are not checked for newlines.** A Tatoeba sentence or teacher output containing "\n" would break the prompt layout and the stop rule. Fix: assert that none contains one, and count drops.

## Outside lane A (one line each, for auditors B and C)

- G7 in the registered gates stage compares the data files with a manifest computed from the same files at run time (`stages.py:273, 327`), so it cannot fail. The real protection is `read_bundle` plus the plan's `data_manifest_sha256` (`freeze.py:94`). The model and Tatoeba files are never checked by G7.
- No pre-freeze gates stage on rehearsal seeds exists; the rehearsal only times `g4` and `g5`. `cmd_rehearse` calls `int(args.layer)` with a default of None (`stages.py:381`).
- `datagen` ignores `--stage-cap-seconds` and charges nothing to the hour ledger.
- §6.1 and §14.2 step 5 ask for both teachers on every panel, plus outputs on D_con, E_C and E_open. Only own-capability outputs for E_A, E_B and D_cal are generated (`prefreeze.py:135-138`).

## What the stand-ins cannot exercise: verify on the first real data

1. `sequences_scores` against the explicit per-token mean (M7). Record `length_penalty`, `num_beams` and `bad_words_ids` from each teacher's `generation_config.json`.
2. Link files:
   - Column order: the English id first in `eng/eng-*_links`.
   - The share of rows that resolve.
   - The symmetry with `deu/deu-eng` and `fra/fra-eng`, with the count of one-direction English ids reported.
3. Group sizes:
   - The group size distribution, and the size of the largest group: a common reference like "Ja." makes one giant component.
   - How many pairs go to training through the more-than-50 rule.
   - The evaluation share.
4. Sufficiency:
   - E_A and E_B at least 500 and E_C at least 250.
   - Per capability, exclusive accepted sources plus half the shared ones at least 10,000.
   - Gold at least 8,000 outside Q, D_cal and D_con.
5. `WindowsInsufficient`: whether both strata have at least 100 windows on the 256-token grid once the parquet join is fixed (B3).
6. BOS default (expected: not prepended). Test (a) must show 0 mismatches on prompts. Test (c) on 1,000 random id sequences checks Python's `errors="replace"` against the Rust `from_utf8_lossy` of `tokenizers`, and the decoding of special tokens.
7. The teachers' tokenizer records reproduce (B2), and Marian loading of the pinned German repository works offline (`HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`, network off).
8. The student equivalence at L = 4 and L = 12, and the greedy key–value cache.
9. The chrF cross-check: a maximum difference of 0.001 or less on 1,000 Q pairs.

## Pre-download checklist for the lead

Before the first real download:

1. Fix B1: pin the git-blob SHA-1 of every small file from `check_saved_trees.out.txt`, and verify every file against code constants, never against the manifest. Re-run a test that feeds the validator a manifest with a missing or wrong digest and expects refusal.
2. Fix the ledger part of M6, or write the ledger rows by hand: one row before each fetch starts and the completed row after, with a running total below 30 GB. The primary set is about 0.93 GB plus the small files (9,138,858 B, about 9.1 MB, summed from the saved trees); the wheels are extra.
3. Make the fallback manifest list rows 5 and 6 only, and refuse to overwrite existing files (M6). Do not invoke the fallback without a committed record of the human lead's decision.
4. Use a fresh destination under the git-ignored `data/`, for example `data/p10s2-downloads-<UTC date>/`. Fetch all seven Tatoeba files in one session.
5. Commit the Tatoeba SHA-256 values, the session date and the file sizes into a tracked record immediately after the session. This is what "frozen at first download" requires; a file inside the git-ignored directory does not satisfy it.
6. Confirm that the interpreter's TLS verification works, and do not disable it. The Hub `resolve` URLs redirect to a CDN, so integrity rests on the hashes alone; B1 must hold before anything is loaded.
7. Before installing wheels: resolve `requirements-datagen.txt` with hashes, record the total wheel bytes in the ledger, and install with hashes required.

The fetch is unsafe if any of these holds:

- A file is used before its digest is verified against a constant in reviewed code.
- A small configuration or tokenizer file is unverified, which is the case now.
- The manifest can supply or omit the digest it is checked against, which is the case now.
- Existing frozen files can be overwritten, which is the case now.
- The ledger total is not kept.
- Any loader is called with remote code, network access, or `weights_only=False`.

Corrupted or attacker-controlled files would have these effects:

- **Pickle weights:** refused by digest and then by the weights-only unpickler (verified).
- **Safetensors:** caught by the fetch-time digest. It is not re-checked at load (B1).
- **`config.json`, tokenizer files and `.spm` files:** loaded unchecked today (B1). A malicious `config.json` is the advisory's code-execution vector, and a malformed `.spm` reaches native code.
- **Tatoeba:** nothing to compare against beyond the first-session digest. A different weekly export is silently accepted on first download; this is by design, which is why item 5 exists.
