# HANDOFF from fix lane A (P10-S2: data, seeds, tokenization, filter, fetch, data generation)

Written by the lane-A implementer (Claude Sonnet 5.5) on branch `claude/p10-s2-fix-A`, base `e7a397e`. Self-check only: not independent review, not Astra validation, not human approval. Every
requirement below is something lane A coded against and could not change itself, because the file belongs to lane B or lane C. Nothing here is measured; no real data, model or network was used.

## 1. For lane B (stages, ledger, budget, freeze, rehearsal, calibration, recompute, gates, launch scripts)

### 1.1 `ledger.py`: the single study ledger (B-B3, A-M6)

`datagen` is coded against two module-level functions of `studies/p10s2/ledger.py` (looked up at run time with `importlib`, so a missing function is a clear stop, not an import error):

- `ledger.charge(stage: str, seconds: float) -> None`: append a charge of `seconds` of wall time to the stage `stage` (`datagen` passes `"datagen"`). It must write the entry also when the process fails (datagen calls it in a `finally`).
- `ledger.remaining() -> float`: the **hours** still available under the study's cap. `datagen.charged_stage` refuses to start if `remaining() * 3600 < --stage-cap-seconds`.

`datagen` also enforces its own stage cap (`--stage-cap-seconds`, the existing required flag) by `StageClock.tick`, called between the long steps and between teacher batches; past the cap it raises `StageCapExceeded`
and the ledger is still charged. Tests use a stub with exactly this interface (`tests/test_p10s2_fixA_datagen.py::StubLedger`). The existing class `Ledger.record(kind, ...)` is not used by datagen any more.

### 1.2 `gates.py`: G9 (A-M4 core half, A-M8)

`core.seed_gate` gained keyword arguments; the old call still works but is the weak check. **G9 must call the strict form**:

```python
core.seed_gate(core.seed_record(), core.planned_seeds(mode, replicates), planned_mode=mode, extra_foreign=core.config_seeds(), stage_mode=mode)
```

- `stage_mode` is the mode of the stage that is gated (`"registered-run"` in every registered stage, `"registered-data"` for the data-generation step, `"registered-analysis"` for the analysis stage's 220906, `"rehearsal"`, `"calibration"`, `"test"`). With it every recorded use must carry exactly that mode (a `"test"` use next to a registered one is refused), the record must be non-empty, `planned` must be non-empty and the recorded set must equal the planned set. `allow_partial=True` relaxes "equal" to "recorded is a subset of planned" for a stage known to draw only part of it.
- `core.planned_seeds(mode, replicates=None)` builds the planned set for **every** replicate (44 seeds for four registered replicates; `run_gates` planned replicate 0 only). For `"registered-data"` it is the eleven data-step seeds; for `"registered-analysis"` it is `[220906]`.
- The +10 code seed is now a recorded use: `SeedPlan.code_seed()` calls `core.record_code_seed_use`, which appends a `SeedUse(kind="code-hash")`. `World.codes(r)` goes through it, so G9 sees it. (`memory.CodeBook(seed, V)` called directly records nothing, as before.)
- **G9's listed seeds are 220901-220912** (`core.listed_partition_seeds()`; `core.listed_registered_seeds()` includes all twelve). 220912 is the equivalence injection vector's own seed (`PARTITION_STREAMS["equivalence_injection"]`).
- **220906 is drawn in the analysis stage only** (ruling "One further ruling - bootstrap intervals"). It is not in `partition_seeds("registered-data")` and `seeded_generator(220906, ..., "registered-data")` is refused. The analysis stage runs under the new mode `"registered-analysis"` (allowed set `{220906}`); G9 for that stage: `stage_mode="registered-analysis"`, `planned=[220906]` (`allow_partial=True` if no interval is printed). This is recorded in `core.PARTITION_USES["bootstrap"]` and in `core.seed_table()`.
- `SeedUse` has a new defaulted field `kind` (`"generator"` or `"code-hash"`); the record dicts returned by `seed_gate` carry it.
- `config`: `configs/p10s2_transfer.toml` `[seeds] partition_streams` still ends at 220911 (a file under `configs/` is immutable for this task). The code holds 220912 in `core.PARTITION_STREAMS`. `tests/test_p10s2_core.py` still asserts the config list as it is. If the lead wants the config list to name 220912, that needs an approved amendment.

### 1.3 `stages.py`: the timing benchmark (A-M8)

220908 is drawn once, in the data step, and stored. `stage_timing` (`stages.py:178`, `idx = list(range(min(n_items, len(p.examples))))`) must use the stored indices instead of the first items:

```python
idx = world.timing_items[name]   # World.timing_items: dict panel name -> sorted item indices (E_A, E_B), 200 each in the registered data
```

`World.timing_items` (new field with a default) is filled by `worldio.build_world` from `bundle.extra["timing_items"]`. A world built without a bundle has `{}`; a registered stage should refuse an empty `timing_items`.

### 1.4 `freeze.py`: two more pre-freeze conditions (A-B2)

`prefreeze_summary` keeps its shape. Add beside it, in `freeze.write_freeze` next to the whole-string check:

```python
from .prefreeze import tokenization_required_ok
if not tokenization_required_ok(json.loads(prefreeze.read_text())):
    raise FreezeRefused("refused: test (a) of section 14.2 step 4 is absent or has a mismatch on a prompt or an R-icl prompt (0 required)")
```

The record also carries `chrf_crosscheck` (`ok`), `g9_data_step` (`ok`), `steps.check_c`, `tokenization.b_roundtrip` (listed failures, no stop rule in the ADR) and `generation_config` (per teacher: `length_penalty` used, the file's `length_penalty`, `num_beams`, `bad_words_ids`, the first-batch score comparison). `datagen` itself stops on test (a), the chrF cross-check, the score comparison and G9 of the data step; the freeze may re-check them.

### 1.5 `gates.py`: G8 over every read layer (minor 8)

`datagen` writes `bundle.extra["equivalence"]` (the record of the first read layer, unchanged shape) and `bundle.extra["equivalence_layers"]` (dict `"4"`, `"12"` -> record). G8 should call `equivalence.verify_all(student, extra["equivalence_layers"])` (new, returns `{"ok", "layers", "tolerance"}`; not ok when no record is given).

### 1.6 `launch/datagen.sh`

- The locked `pyarrow` (WikiText parquet) is the `pilot` extra of `uv.lock`: the command line needs `--extra pilot` (before `--with-requirements`). `tests/test_p10s2_prefreeze.py::test_prefreeze_scripts_pass_the_stage_cap_and_every_required_flag` was made tolerant of it (it accepts the script with or without it).
- Unverified: whether `uv run --with-requirements` enforces the `--hash=` entries of a requirements file. `datagen` therefore refuses to run while any pin of `requirements-datagen.txt` has no hash (`datagen.check_requirements_hashed`), but whether uv then installs with hashes required was not checked (no network). The lead should check it on the first install, or install with `uv pip install --require-hashes`.
- `datagen` has one new optional flag, `--wikitext-dir` (default `<repo>/data/wikitext2`). The four required flags are unchanged.

### 1.7 Not done in lane A, noted for lane B

- B-M8 (the device): `worldio.RunConfig.registered(..., device="auto")` and `train.select_device("auto")` are the places that silently fall back; `worldio.py` is lane A's file but the device freeze is a lane-B decision (`train.py` is not mine), so it was left unchanged.
- A-M3 (evaluation panels scored before the freeze: `rehearsal.measure_rates`, `gates.g2`) is lane B's per the ruling.
- A-M4 `run_gates` plans replicate 0 only: see 1.2.

## 2. For lane C (analysis, classes, report, output, routing, evaluate, cells, combined)

- **Bootstrap generator.** Every printed interval draws its generator with `core.bootstrap_generator(mode, interval_name)` (mode `"registered-analysis"` in the registered analysis stage, `"test"` in tests): a fresh generator on the listed seed 220906 per interval, called in the order of the registry. `text.bootstrap_interval(values, generator)` is unchanged. The analysis stage must not construct the generator any other way.
- **Read position (C-M5).** `tokenization.tokenize_segment(..., with_words=True)` and `windows.cut_windows` now place the read at the last token that starts before the end of the word's letters (`tokenization.word_letters_end`, `last_token_before`), never at a following punctuation token. The bank records written by the data step differ from earlier synthetic ones in this respect; `Example.reads` consumers are unchanged.
- **Router sampling (A-M5)** is `routing.py` (lane C): `gen_s = plan.gen(3, "router sampling")` after `Router(...)`, used for the prefixes, then the lengths, then the batches. Not touched by lane A.
- **Teacher outputs.** The audit's note that only own-capability outputs on E_A, E_B and D_cal are generated (and E_C) is unchanged (`prefreeze.py` still stores `E_<c>`, `D_cal`, `E_C` per teacher); the ADR text (section 6.1 / 14.2 step 5: both teachers on every panel, plus D_con and E_open) is ambiguous about which outputs a stage reads, so lane A did not widen it. **PENDING LEAD REVIEW.**

## 3. Tests owned by other lanes that fail because of lane A's interface changes

Full `pytest tests/test_p10s2_*.py` on this branch (measured, one run, CPU, `--basetemp` in the scratch folder): **286 passed, 1 failed** in 287 s. The one failure:

- `tests/test_p10s2_train.py::test_seeds_of_the_training_uses_follow_the_table` (line 203): `assert set(offs) <= {0, 2, 6, 7, 8, 9} and offs.count(2) == 18 + 2`. The +10 oracle-code seed is now a recorded use (audit M4: "G9 cannot see it"), so `core.seed_record()` after `cells.train_replicate` holds one `+10` entry (measured: offsets `{0: 4, 2: 20, 6: 2, 7: 1, 8: 3, 9: 2, 10: 1}`). The assertion should read `set(offs) <= {0, 2, 6, 7, 8, 9, 10} and offs.count(10) == 1 and offs.count(2) == 18 + 2`. Not edited by lane A (not one of its files).

Tests that lane A changed because its own interface changed (all in files it owns): `tests/test_p10s2_core.py` (the registered-data partition seeds are eleven, 220906 moved to the analysis stage, 220912 added), `tests/test_p10s2_prefreeze.py` (the manifest now carries the code constants and the fallback is a recorded committed decision; the "no test imports fetch or datagen" rule now exempts only `tests/test_p10s2_fixA_*.py`; the datagen launch-script assertion tolerates `--extra pilot`; the requirements header test follows the new header).

Interface changes lane B or lane C code could meet: `core.partition_seeds("registered-data")` no longer has `"bootstrap"`; `core.MODES` has `"registered-analysis"`; `fetch_guard.build_manifest(fallback_human_decision=...)` takes a mapping `{"path", "commit"}` and `fetch_guard.validate_manifest` takes a keyword `root`; `datagen.run` takes `led`, `stage_cap_seconds`, and its record has new keys. No other module of the package imports those.

## 4. Pending lead review, ambiguities and what lane A could not do

Quoted so the lead can choose; lane A did not.

1. **Panel representative per identity group.** "Panels are drawn per identity group" (ruling A-M1). Implemented: among the candidates whose group is not used, one representative key per group (the first in sorted order), then the earlier seeded permutation. The audit also allowed "update `used` inside the loop"; that would let the seeded draw choose the key within a group. Neither changes the ADR's draw order when no group has two keys.
2. **Identity unit of a no-gold source.** "T_A and T_B disjoint in identity groups". A no-gold source has `group == -1`; lane A treats its contraction-expanded normalized string as its unit (`data.source_unit`), so that "can't go" and "cannot go" cannot be split between T_A and T_B. The shared units are split in a permutation of the *sorted unit names* (the earlier code permuted sorted keys). `sufficiency_after_filter` counts per unit and is a lower bound when a shared unit has several keys.
3. **The pool of the 100 tokenizer-record sentences (220909).** The ADR names no pool. Implemented: the capability's own generation sources (`data.tokenizer_record_sentences`), A then B from one generator. The record is the sentence, the Marian source ids, the teacher's translation and its target ids.
4. **The link-resolution guard.** `data.LINK_RESOLVE_MIN_SHARE = 0.5` is an engineering guard value chosen by lane A (a swapped or wrong link file resolves near 0), not a scientific threshold. **PENDING LEAD REVIEW** if a different share is wanted.
5. **New-token limit (minor 5).** Pooled: the 99.5th percentile over the gold references of D_cal in both languages. The audit's alternative is one limit per language. **PENDING LEAD REVIEW.**
6. **R-icl prompts in test (a).** The demos are the 4 nearest accepted pairs from the *whole* accepted pool of the capability; a replicate's draw is a subset, so the prompts differ and the layout is the same. A replicate-level check would need the registered path to tokenize, which it never does.
7. **Beam score.** The filter uses the recomputed score (sum of transition scores over the non-pad generated positions, EOS counted, divided by their number; `length_penalty=1.0` is passed explicitly). It is compared with `sequences_scores` on the **first batch** only (tolerance 1e-5, stop on a difference); later batches record the maximum difference without stopping. The ruling says "asserted equal on the first real data"; a stop on later batches is not coded.
8. **Chrf cross-check pairs.** The 1,000 pairs are teacher A's outputs on all of Q against the German references (Q has 1,000 items). The ADR says "1,000 pairs of Q" without naming the side.
9. **Test (b)** has no stop rule in the ADR: failures are counted and listed in the record (`tokenization.b_roundtrip`), and `required_ok` (the stop condition) is test (a) on prompts and R-icl prompts only.
10. **Requirements with hashes (minor 9; checklist item 7) was NOT done.** Resolving `requirements-datagen.txt` with hashes needs the network (`uv pip compile --generate-hashes`), which lane A did not use. The file now says so, and `datagen` refuses while any pin has no hash. The lead has to resolve it once, record the wheel bytes in the download ledger, and commit the result.
11. **Nothing was executed against the network or real data.** `fetch._download`, `datagen.run`, `HFTokenizer`, `HFReference`, `MarianTeacher`, `crosscheck_chrf` and `package_versions` are never called by any test (`# pragma: no cover`). Their behaviour with the real packages is the first-real-data list of the audit (section "What the stand-ins cannot exercise") and is unverified.
12. The worktree's `.venv` is the one `uv run --locked --offline` uses (git-ignored); lane A made no second environment.
