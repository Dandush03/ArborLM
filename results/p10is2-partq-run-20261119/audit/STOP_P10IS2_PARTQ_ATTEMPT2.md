# P10-I-S2 Part Q, registered attempt 2: independent reading of the stop at `outputs`

- **Auditor.** The `arbor-auditor` subagent, model Claude Opus 5.5 (`claude-opus-5-5`), 2026-11-19. I wrote none of the code.
- **Object.** Freeze `55017df4616a81795918e21e0792fa742f77bdc4`, Decision 2 (`931a1c2`), run directory `experiments/P10IS2-Q-registered2-20261118`, all read-only.
- **Scripts.** In `/Users/daniellaloush/dandush03/ArborLM-sealed/audit-s2-stop/` (kept): `own_bpe.py`, which is my pure-Python byte-level BPE from REAUDIT4, validated there on all 144 recorded P10-S2 windows, and `stop1.py`, with its output in `stop1.txt`.
- **Limits observed.** One process, `timeout`, no network, no git writes, no `/tmp`, no teacher generation, no registered seed used by my code.
- **What I read, exactly:**
  - `outputs/gloss_test.json`: the recorded mismatch;
  - `engineering_failures.json`;
  - `stages/*.complete.json`: status, mode, `within_cap`, seconds and cap;
  - `charged_ledger.json`;
  - the `ok` field of `regeneration.json`;
  - the `keys` lists (normalized English sources) of `outputs/teacher_{A,B}/{E_A,E_B,D_cal,E_C,E_open}/batch_*.json`, in this run and in the rehearsal directories. The batch files were loaded whole; only `keys` was used or printed;
  - the freeze record and Decision 2 at `55017df` and `931a1c2`;
  - the measuring record's `charged_before_freeze_seconds` and `charged_ledgers`.
- **What I did not read:** I did **not** open `qfit/`, `qcheck/`, `generation/result.json`, `generation/pools.json`, `partition_counts.json` or anything under `sealed/`.
- **Status.** This audit is independent engineering evidence. It is not Astra validation and not human approval. `Astra review: NOT_PERFORMED`.

## 1. The cause

**The mismatch is real.** The prompt of E_A item `ill wait till 230` (the English "I'll wait till 2:30") decodes, from the recorded whole-string ids, to:
```
 ill = werde\n wait = warten\n till = geöffnet\n 23…
```

My BPE reproduces **both recorded 20-token sequences exactly**. In tokenizer strings:

| | Ids | Tokens |
|---|---|---|
| Segments (the stored pieces, as Part T would concatenate them) | `…, 4205 'net', 198 '\n', 216 ' ', 34 '2'` | the newline segment, then the source-word segment `" 230"` = `' '`, `'2'`, `'3'`, `'0'` |
| Whole string (tokenizing the full text) | `…, 4205 'net', 3805 '\n ', 34 '2', 35 '3'` | the newline and the following space become **one** token, `"\n "` (3805) |

**Why.** The student's tokenizer runs `Digits(individual_digits=true)` **before** the GPT-2 byte-level regex.
1. Digit isolation splits the text right before `2`, so the pre-token ends at `"…\n "`.
2. The whitespace run `"\n "` at the end of a piece is one regex match (`\s+(?!\S)`), and BPE merges it into 3805.
3. Before a letter the split falls differently: `"\n"` stays alone and the space joins the word (`" ill"`, 1899). That is why the same check passes for word-initial source words.

**It is a property of the template together with the segment rule, not of the test.** The template puts a newline segment before each line's source-word segment. The segment rule gives that source word "its own segment with a leading space". For any source word that begins with a digit, on any line but the first, the two segments therefore tokenize differently from the joined text. Checked in isolation:
- `"\n" + " 230"`, `"\n" + " 2"` and `"\n" + " 10"` all differ;
- `"\n" + " ill"` is equal;
- a digit-initial **gloss** word (`" =" + " 230" + "\n"`) is equal.

The test did what ADR-0022 section 14.2 asks: it compared segment ids with whole-string ids and found that the stored segments would feed the student a token sequence the text itself does not produce.

**How many prompts the study would build are affected.** I counted over the public panel sources, where every word is in the vocabulary by construction:

| Panel (capability) | Items | Any digit-initial word | Digit-initial word **after** the first word |
|---|---|---|---|
| E_A (A) | 1,000 | 2 | **1** (`ill wait till 230`) |
| E_B (B) | 1,000 | 0 | 0 |
| D_cal (A) | 500 | 0 | 0 |
| D_cal (B) | 500 | 0 | 0 |

- R-gloss-icl prompts are built only for E_A, E_B and D_cal (ADR §5.2). E_C and E_open are not used for them; E_open has 7 such items but no R-gloss-icl prompt.
- The count above is an upper bound, because a line also needs a lexicon entry. It equals the test's own count (1 of 3,000).
- A replicate's lexicon (from its 8,000-item draw) is a subset of the whole-pool lexicon, so each replicate has **at most this one** affected prompt.

## 2. What ADR-0025 makes of it, read strictly

- **The rules that apply.**
  - L3 (§19): "A stop on a registered test of the data step (**a tokenization test**, …): Not an engineering error to be resumed past: the step stops and returns to the lead, as R16 says."
  - §3 row 28: "A stop on a registered test of the step returns to the lead."
  - §5.2: "zero mismatches are required."
  - §4.4 row 1: QUALIFICATION-ENGINEERING-FAILURE for "a failed gate on study-produced data".
  - §15: "A failed gate on study-produced data stops the run: ENGINEERING-FAILURE. A second attempt needs the human lead's decision."
- **My reading.**
  - The stop is a registered test of the data step, so the step stops and returns to the lead (L3). It is not an ENGINEERING STOP (§8.6 reserves that for code, environment and non-finite errors) and not a refusal.
  - If a Part Q outcome is registered, §4.4 takes the first matching row. A failed required test on prompts built from the study's accepted pools is a failed gate on study-produced data, so the label is **QUALIFICATION-ENGINEERING-FAILURE**, no line is derived (§8.6), and Part T is **NOT STARTED**.
  - The frozen code took the same reading: it wrote `engineering_failures.json`.
  - **The cause is a defect of the specification's own template**, not of the teachers or the data. The label says nothing about teacher quality. The human lead may rule the classification otherwise (for example, "stopped by a specification defect; no outcome registered"). **PENDING THE HUMAN LEAD.**
- **Is the status written anywhere?**
  - No label file exists. The frozen `analysis` refused before running: `require_prerequisites` needs `stages/outputs.complete.json`, and a RegisteredTestStop leaves no completion record.
  - By the specification, row 1 **is** a label derived by rule (first match wins), from records that exist (`engineering_failures.json`).
  - The refusal is therefore a **code defect** relative to §4.4. The registered path has no way to reach `analysis` after an engineering failure, unlike `pipeline.run_all`, which records a failure and then derives the label. The stage-order rule was written for completion and NOT RUN BY RULE only.
  - Until the human lead rules, the record should state the status in words: "stopped at outputs on registered tokenization test (a); by §4.4 row 1 QUALIFICATION-ENGINEERING-FAILURE; label not written by the frozen code because analysis refused on stage order".

## 3. Could the rehearsals have caught it?

**Not with their draws.** All five measuring attempts and the counting rehearsals use the same rehearsal partition seeds (252901–252914), so they share one set of panels. In those panels E_A, E_B and both D_cal panels have **0** items with any digit-initial word (`stop1.txt`, every rehearsal directory). The registered draw (seed 250901) has 2 in E_A, one of them after the first word.

This is **not a divergence between the rehearsal path and the registered path**: the code path is identical (REAUDIT3 and REAUDIT4). It is the draw. The defect itself is deterministic: any digit-initial source word after the first line triggers it.

**What would have caught it before the freeze**, without any teacher output or registered value:
1. A unit test with the real tokenizer on the template boundary: `"\n" + " <digit>…"` against the joined string. It needs no data, and it fails at once. One line of test.
2. Equivalently, test (a) of R-gloss-icl run on synthetic lines for every vocabulary word that begins with a digit.

**My own part in the miss.** My audits checked that test (a) was wired in (R7 of REAUDIT2) and ran on real code paths. I never tested the template's token boundary against this tokenizer's digit isolation. I recorded the risk class (Digits pre-tokenizer) in REAUDIT4 and did not connect it to the template.

## 4. What is valid and readable

**Stage records (`stages/`), all `mode=registered`, all `within_cap=True`:**

| Stage | Charged | Cap |
|---|---|---|
| inputs | 56 s | 144 s |
| partition | 402 s | 900 s |
| qfit | 765 s | 1,728 s |
| qcheck | 470 s | 3,312 s |
| generation | 23,773 s | 30,492 s |
| regeneration | 520 s | 936 s |

`outputs`: 819.2 s charged, no completion record. `analysis`: refused, nothing charged.

**Charge.** Attempt 2's ledger holds **26,804.0 s = 7.446 h**:

| Stage | Seconds |
|---|---|
| inputs | 55.9 |
| partition | 401.6 |
| qfit | 764.6 |
| qcheck | 469.7 |
| generation | 23,772.6 |
| regeneration | 520.4 |
| outputs | 819.2 |

- With the charge before the freeze in the frozen measuring record (15,832.8 s), the cumulative Part Q charge is **42,636.8 s = 11.84 h** against the **15.15 h** total cap (54,540 s). That leaves 11,903 s.
- **Finding (REQUIRED for any further attempt):** the run's ledger checks `remaining = 54,540 − (this run's charges)` and ignores the 15,832.8 s already charged before the freeze. The code would therefore have allowed the run up to 54,540 s by itself, where the rule allows 38,707 s. It did not matter here.

**Regeneration identity: PASS** (`regeneration.json` `ok: true`; nothing else read).

**Qualification counts (Q_check counts, pool sizes): not read and not reported.**
- Under row 1 the first match wins, so rows 3–5 are not derived.
- §8.6 says no line is derived.
- §15 says "No result is reported before the recomputation is complete."
- The Q_check and pool figures are exactly the inputs of rows 3–5 (the quantities P10-S2 failed on), so the specification does not let them be read or reported now. They sit in public (unsealed) registered files. Whether anyone has opened them matters for item 5.

## 5. What a third attempt would need

**The smallest change that removes the cause** is an amendment of the R-gloss-icl segment rule in ADR-0025 §5.2 and §4.1 step 8, with matching code in Part Q's gloss bank:
- store the source-word segment of every line **after the first** as the tokenization of `"\n" + " " + word`, with the newline folded into the next line's first segment (and the first line as `" " + word`);
- or, equivalently, store each complete line `" w = g\n"` tokenized whole.

Either way the stored segments equal the whole string for any tokenizer boundary. Test (a) stays exactly as specified, and the R-gloss-icl content (which words, which glosses, in what order) is unchanged.

**Not acceptable:**
- changing the test, which would relax a required test after it failed;
- dropping digit-initial source words, which would change the baseline's content to fit the test.

Neither moves any Q value, but both change what was registered.

**Reuse against redo of the completed stages** (inputs to regeneration, including 6.6 h of generation):
- ADR row 28: "after that point [a value of Q1–Q4 computed] a second attempt is the human lead's decision." Q values exist (`qfit` and `qcheck` are complete).
- The fix changes a frozen file, so it needs a new freeze, and nothing in ADR-0025 carries records across freezes. Reuse would need an explicit ruling by the human lead. The case for reuse:
  - the cause lies wholly in step 8;
  - stages 1–6 are deterministic under the same seeds and layout, and the regeneration check passed;
  - redoing them with the same seeds is expected to reproduce them bit for bit;
  - reuse should therefore be verified by hash and by re-running the regeneration subsample.
- Redoing costs about 7.4 charged hours, with generation at about 6.6 h.

**Seeds consumed** (none may be replaced by fresh ones: a re-draw after an observed stop would be chosen on an outcome):
- before the freeze (the ledger): 250907;
- in stages 1–6: 250901, 250902, 250903, 250904, 250905, 250908, 250909, 250910 and 250914;
- in step 8, before the gloss test (the bundle was built in memory, not written): 250906, 250911, 250912 and 250913;
- 250916 and 250917 only if generation reached DISJOINT draws. I did not check, because that would reveal a result.

**Decisions for the human lead himself:**
1. The classification: row 1 QUALIFICATION-ENGINEERING-FAILURE as registered, or a specification-defect stop with no outcome registered.
2. Whether a third attempt happens at all (row 28 and §15).
3. The amendment of ADR-0025's segment rule after a freeze.
4. Reuse of attempt 2's completed stages, or a redo.
5. His acceptance of a record stating whether anyone has opened attempt 2's `qfit/`, `qcheck/` or `generation/` records. If anyone has, a re-run decision could be chosen on observed values (the rationale of row 28).

**Code fixes with any third attempt:**
- the registered `analysis` derives the row-1 label after an engineering-failure record;
- the total-cap check subtracts the charge before the freeze;
- the template unit test of §3 is added.
