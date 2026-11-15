# Confirmation of ADR-0022 revision 5 (P10-S2)

**Claude (Opus 5.5) review; Astra review: NOT_PERFORMED; not a human approval.**

- Reviewer model: Claude Opus 5.5 (`claude-opus-5-5`). I wrote no part of ADR-0022 revision 5, `build.py` or `rulings.py`. Disclosure: the re-check of revision 4 (`RECHECK_REV4.md`) was also written by an Opus 5.5 context. Some text in revision 5 is that re-check's paste-ready edits (E-J1, E-J6, E-J7 among them). I judge those passages here as if someone else had written them. One finding (M2) is a defect in E-J6 itself.
- Object: `docs/decisions/ADR-0022-p10-s2-two-teacher-transfer.md` in `.claude/worktrees/p10-design`, branch `claude/p10-design`, HEAD `3f19ebb`. It is read-only and I edited nothing in that worktree.
- Environment: macOS (darwin) arm64, `python3` 3.15.1, stdlib only, every script run with `-I`, no project import. No network, no download, no training, no commit.
- Scripts and outputs are in this folder (`.../scratchpad/adr-0022-confirm-rev5/`):
  - `scripts/apply_changes.py` → `out/apply_changes.out`
  - `scripts/arith.py` → `out/arith.out`
  - `scripts/charged_counterfactual.py` → `out/charged_counterfactual.out`
  - `scripts/numdiff.py` → `out/numdiff.out`
  - `buildpy_out/` holds a copy of `build.py` and `rulings.py` run as a cross-check.
- Commands (D = `docs/reviews/p10-design-2026-11-15`, W = the p10-design worktree):
  - `git show 3cf3576:docs/decisions/ADR-0022-….md > rev4_3cf3576.md; cmp` against `D/revisions/ADR-0022-rev4.md`. Result: identical.
  - `python3 -I scripts/apply_changes.py D/adr-0022-review/rev5-draft/CHANGES.md D/revisions/ADR-0022-rev4.md W/docs/decisions/ADR-0022-….md out/applied_rev5.md`
  - `python3 -I buildpy_out/build.py D/revisions/ADR-0022-rev4.md buildpy_out`, then `cmp` against revision 5.
  - `python3 -I scripts/arith.py`; `python3 -I scripts/charged_counterfactual.py`; `python3 -I scripts/numdiff.py rev4 rev5`.
  - Read-only `grep`/`sed` of ADR-0017, ADR-0019, ADR-0020, ADR-0021, `studies/p9/model.py`, `src/arborlm/pilot_model.py`, `studies/p9/core.py`, `studies/p9ii/core.py`, `configs/*.toml`, the ledgers under `results/p9i-run-attempt2-2026-11-15/` and `results/p9ii-run-2026-11-15/`, and the reviews `docs/reviews/p9i-*`, `p9ii-*`.

## Verdict: READY SUBJECT TO the text edits of section 8

There is no blocker. Four majors remain:

- **M1 (implementation):** the seed list does not cover every generator, so G9 as written cannot be met.
- **M2 (scientific, PENDING LEAD REVIEW):** the router recipe can pass GEN through a position shortcut.
- **M3 (budget, before the freeze):** the uncharged recomputation narrows what the 36-hour cap covers. The convention it cites is real in kind but not in scale.
- **M4 (before the freeze):** the recomputation now gates reporting, but the text has no rule for a disagreement or a failure.

One more major concerns the download step only:

- **M5 (before downloads):** the wheels approval was given to a question that, as quoted, stated no size, while the lead's own standing correction requires sizes.

Each major can be closed by a text edit or a recorded decision.

## 1. Task 1: reproduction of revision 5 from the change list

- **Exact reproduction.** My own parser applies the 60 Old/New and Anchor/Inserted blocks of `CHANGES.md` to revision 4. Every anchor occurs exactly once, and the result is **byte-identical to revision 5** (`out/apply_changes.out`: `IDENTICAL`).
  - One caveat about `CHANGES.md` as a document. It strips leading newlines from inserted text (`new.strip("\n")` in `build.py`). For C02, C06, C29, C30, C34, C36, C37, C48, C57 (inserts) and C60 (insert-before), my applier had to restore 1–2 newlines. It chose the variant present in revision 5. The only freedom used was therefore whitespace at those ten points, and no content can hide there.
  - The copy of `build.py` plus `rulings.py` also reproduces revision 5 byte for byte. However, `build.py` then crashes when it writes `CHANGES.md`, because it reads `open_for_the_lead_v2.md`, which is not committed (minor m14). The "Open for the lead" part of `CHANGES.md` cannot be regenerated from the repository.
- **Unlisted changes:** none.
- **Revision 4 baseline:** `revisions/ADR-0022-rev4.md` is identical to commit `3cf3576`.
- **Numbers.** Only these numeric tokens disappear (`out/numdiff.out`):
  - the rung figures 14.4/35.5/10.8/26.8/10.1/27.2, now given as 14.35–35.51, 10.84–26.78, 10.09–27.17;
  - the stale "+0.1 to +0.3";
  - one "2.5" (the sacrebleu sentence) and one punctuation variant of 220301.
- **No threshold value changed. No arm, model, replicate count or rung changed. The cap number (36) did not change.**
- **What changed beyond the re-check's edits and the human answers** (all listed in §20/§21 or in the rulings):
  1. **Scope of the cap (flag).**
     - Revision 4 §13.2 charged "the sum of wall-clock hours over all S2 processes".
     - Revision 5 excludes the independent recomputation from the charged hours, which is lead's ruling 1.
     - The header claims "no … cap is changed". That holds for the number 36, not for what it covers (M3).
  2. **Data source (flag, disclosed).** If the fallback is invoked, its Tatoeba files come from a later weekly export than the primary files (C44). Link rows to English ids absent from the frozen file are then dropped.
  3. **Data check removed unless approved (flag, disclosed).** The link-file symmetry check is not made without the two 6.2 MB files (C43).
  4. **New numeric criteria and settings (additions, not changes):**
     - sufficiency at 8,000 × 1.25;
     - router: AdamW 0.001, 500 × 64, temperature 0.2, 8,000 prefixes of 64 tokens;
     - LoRA α = r;
     - E-table N(0, 0.02) with a gate at 0;
     - window grid of 256 tokens, strata defined on tokens 1–64.
  5. **New label route.** G9 makes a seed defect ENGINEERING-FAILURE (§11.3 row 1). It is stricter.
  6. **New procedure (ruling 7).** A fallback invocation "first returns to the human lead (the fallback is a reserved decision)". §16 does not list it as reserved (m11).
  7. **Accuracy of the header.** It says revision 5 "applies the re-check … and does nothing else". It also records a new human answer and nine lead's rulings (m1).

## 2. Task 2: the re-check's findings and the lead's choices

### 2.1 J1–J14 and the other re-check items

| Item | Resolved? | Note |
|---|---|---|
| J1 seeds | **Partly.** The offset table, direct seeding, listed partition-side streams, S1 ranges and G9 are present. | Unlisted generator uses remain, and G9 forbids them (M1). Whether a shared seed restarts a fresh generator or continues one is unstated (folded into M1). |
| J2 key init | Yes | N(0, 0.02), as `arborlm.pilot_model._matrix` (verified: `normal_(0, 0.02)`). Appended rows use +6. |
| J3 download scope | Yes. §4.2, §14.1, §16 and §18 say one thing. | Wording nit m9. Fallback invocation reserved only in §4.2 (m11). |
| J4 wheels not in the figure | The text is fixed and a later human answer is recorded | The approval's premise is open (M5) |
| J5 marker placement | Yes | Hard negatives can be bypassed by position (M2) |
| J6 router recipe | Implementable | Position confound (M2). A few seed-use ambiguities (M1). "in equal number" against balanced batches is minor (see 2.2). |
| J7 disjoint draws, gold | Yes | Contradicts the header's own selection rule (m8) |
| J8a rates | Yes. Slower of L = 4 and L = 12, the other L measured on 200 updates and charged in P. | — |
| J8b scope | Settled by ruling, not by the re-check's text | M3, M4 |
| J9 | Placed with the lead's approval record | Still open by design; needed before the freeze |
| J10 RET | Yes. V1 for every stage-2 arm. | Stricter for M-ii |
| J11 LoRA, E-table | Yes | — |
| J12 tie-break | Yes | — |
| J13 finite | Yes | — |
| J14 grid | Yes | Matching rule for the strings unstated (m7) |
| §2 stale parenthetical, 7.6, NOT STARTED: BUDGET | Yes | — |
| §3 S1 ranges | Yes. Lists 2101–2105, 2111, 2112, 2121, 2122, 2191–2192, 921001–921999, as ADR-0021 §6.3. | — |
| §4 fallback SHA-256 | Yes. Equals the LFS oid in `web/opus_en-es_tree.json` (`befce0f6…994c`, 312,087,523 B). | — |
| §4 stale sentences | Yes. The header, §14.1 intro, §14.2 wheels and sacrebleu are all fixed. | — |
| §1 C8 BOS (E-m3) | Yes | — |
| §5 oracle line (E-5) | Yes. See section 5. | — |

### 2.2 The 20 [lead's choice] rows of §20 (plus the inline ones)

Columns: implementable without a further choice? / consistent with the P9 or P9-II convention it claims? / easier for a positive label than revision 4?

| Choice | Implementable | Convention claim | Easier than rev 4? |
|---|---|---|---|
| Direct seeding, offsets +0…+10 | **No, not fully** (M1) | Departs from P9's `seed + 1000·k` on purpose; correct, because P9's rule sends all 49 registered seeds into S2's own calibration and rehearsal ranges (`arith.out`: 49/49) | No |
| Partition-side streams 220902–220905 | Yes | — | No |
| Code seed per replicate (+10) | Yes. The pair→identifier mapping for `unit_code` is unstated (m6). | **Consistent.** P9's `DATA_SEEDS` has `r1_codes` as one of its 14 per-set seeds. P9-II and S1 use base + 0…13 per draw. `unit_code` seeds no generator (verified, splitmix64). | No. More variation across replicates makes n-of-n harder. |
| Appended rows +6 | Yes | — | No. It removes the duplicate-key artefact. |
| Shared seeds (+0, +6, +8, +9) | **Ambiguous** whether each use re-seeds (identical tensors) or continues one generator (M1) | — | Neutral |
| Key init N(0, 0.02) | Yes | **Consistent** with `_matrix` | Unknown direction; it is the convention |
| Marker within tokens 1–64 | Yes, given m7 | — | No. Harder than keeping invisible markers. But see M2. |
| Router recipe | Yes | — | **Possibly yes** (M2). "Exactly 64 tokens" for every "none" prefix, while every task example ends at about 8–25 tokens, lets the router separate the classes by position. Every GEN decision is at token 64. Minor: with two tasks there are 16,000 task prompts against 8,000 "none" prefixes, so "in equal number" contradicts itself. The batch-balance sentence governs. |
| Disjoint halves, ×1.25, overlap reported | Yes | — | Not easier than revision 4, which allowed full overlap. **Easier than the alternative it names**, which contradicts the header's rule (m8). |
| Slower of the two read-layer rates | Yes | — | No. More time against the cap. |
| Second gates stage inside R | Yes | — | No |
| Recomputation not charged | Yes | Convention real in kind, not in scale (section 3) | Makes rungs 1–3 reachable (section 3). It does not change any label rule. |
| RET reference V1 | Yes | — | No. Stricter for M-ii. |
| LoRA α = r, A ~ U(±1/√fan-in), B = 0 | Yes. The draw order of the 60 A matrices from +8 is unstated, which is not scientific. | Consistent with ADR-0021's dense control (U(−1/4, 1/4) at fan-in 16) and the usual LoRA initialization | Neutral. The learning rate is calibrated. |
| E-table N(0, 0.02), gate 0 | Yes | As the store | Neutral |
| Filter tie-break | Yes | — | No |
| Window grid | Yes, given m7 | — | No |
| G9 | **No as written** (M1) | — | No |
| Link files not approved → no symmetry check | Yes | — | Slightly. A missing reverse link can leave identity groups unmerged, a small leakage route that G1 checks only through normalized-string equality. Minor; report the count of English ids with a link in only one direction if the files are ever approved. |
| Fallback data from a later export | Yes | — | Neutral |
| P9 reference test: tensors passed explicitly, `ScalableMemory` never built from a seed | **Contradictory** (m5) | — | Neutral |

The details of m5:

- `ScalableMemory.__init__(spec, seed, …)` requires a seed. It always runs `_matrix(seed + 1000, …)` and `_matrix(seed + 2000, …)`.
- So the module cannot be constructed "not from a seed".
- Yet giving it S2's tensors needs no edit of P9: construct it, then overwrite `keys`.
- The drop rule ("if the P9 forward cannot be given the tensors without editing P9") is therefore never triggered, while the prohibition can never be met.

### 2.3 Recomputed seed table (`scripts/arith.py`)

- **Registered seeds:**
  - 220001–220011, 220101–220111, 220201–220211, 220301–220311 (bases + 0…10);
  - 220901–220905;
  - 49 seeds, no duplicates, all inside 220001–228999.
- **Calibration** 221001 + 100·i + o and **rehearsal** 222001 + 100·i + o (i = 0…9, o = 0…10):
  - 110 seeds each, inside 221001–221911 and 222001–222911;
  - disjoint from each other, from the registered set and from tests 229001–229999.
- **Disjoint from the other studies:**
  - S0 (200001–209999, 2001–2002, 2091–2092, 920001–920999);
  - S1 (210001–219999, 2101–2105, 2111/2112/2121/2122, 2191–2192, 921001–921999);
  - P9 (170001–171343, 179001–179933, 1701–1702);
  - P9-I (182001–182020, 180101–181900, 1791–1792, 1801–1802, 900001–900233, review 500001–500004, 941001);
  - P9-II (190001–191599, 1891–1892, 1901–1902, 910001–919999).
- **Derived seeds of other studies.** No init seed of S0, S1, P9, P9-I or P9-II plus 1000·k (k ≤ 9) lands in any S2 set.
- **Scan of `configs`, `studies`, `src`.** Numbers in 220001–229999 occur only as P2/P3 parameter counts (225793) and P9-II's reserved-range constant (`(200001, 229999)`). The other three-digit hits are byte values in template pools.
- **Duplicate keys.** Stage-1 rows come from +0 and appended rows from +6, so no store contains two identical initial keys.
  - ST1 of both orders and the appended rows of both orders may start identical if each use re-seeds. They never share a top-8: M-i-separate reads two stores behind the oracle route.
  - M-joint (+7) has its own seed.

## 3. Task 3: "the recomputation is an uncharged audit step, by the P9-I / P9-II convention"

**Is the convention real?** In practice, yes. In writing, no.

- **Ledgers.**
  - P9-I `ledger.json`: 12 entries, 2,691.0 s of 14,400 s. Stages: calibrate, rehearse, generate, gates, train, evaluate, analyze, report. The last entry is 02:32:50 UTC on 2026-11-15, and there is no recompute or audit entry.
  - P9-II `P9II-ledger-A.json`: 28 entries, 2,554.2 s. `-B.json`: 4 entries, 4,089.3 s. Neither has a recompute or audit stage.
- **Reviews.**
  - P9-I pre-freeze audit: "Ran (none of it charged to the P9I ledger, none of it through the study's stage driver)".
  - The P9-I results review re-scored all 57 registered snapshots with its own torch forward (`s3_rescore.py`), outside the ledger.
  - The P9-II results review recomputed from records with stdlib code (`b1_recompute.py`), with no model forward.
- **ADR text.**
  - ADR-0017 Part I's cap is "4 hours of charged execution for calibration, rehearsal and the run together". ADR-0019's Budget A is "calibration + rehearsal + Stage 1" and Budget B is "Stage 2 + Stage 3". Both list their scope, and the recomputation ("Independent recomputation from raw records by the auditor; report", ADR-0019 order of work, step 8 (line 332); ADR-0017 §I.12 step 7) is outside the listed scope.
  - **Neither ADR states that recomputation is uncharged.** The convention is inferred from scope lists and ledgers.

**Is the ruling sound?** As a bookkeeping precedent, yes. As a budget decision, not without telling the human lead.

1. **Scale.** The P9 recomputations cost seconds to minutes. P9-I's whole registered evaluate stage took 97.9 s, and P9-II's was record-only. S2's is projected at 5.8–18.8 h for four replicates and 4.4–14.3 h for three. That is 30–50% of R and up to half of the 36-hour cap. At that scale, leaving it out of the cap is a budget decision, which AGENTS.md reserves to the human lead.
2. **Revision 4's own wording** charged "the sum of wall-clock hours over all S2 processes". Revision 5 narrows that. It is not a change of the number 36, but it is a change of what 36 covers.
3. **The human lead's MPS answer** was given to "May S2 train on the Mac's GPU, with scores recomputed on CPU?". The recomputation is part of what made that departure acceptable, so it belongs to S2, not to an optional audit.
4. **The ADR cannot settle "uncharged" against "charged" by its own declared rule.** For open points the header picks the option that "counts more time against the cap" unless a convention exists. A convention exists only in the sense above.

**What not charging lets through** (`out/charged_counterfactual.out`). Model: one common speed factor x, with x = 0 at the fast end of every projected range and x = 1 at the slow end.

| | P = 3.5 h | P = 7.0 h |
|---|---|---|
| Uncharged (revision 5) | rung 1 for x ≤ 0.08; rung 2 to 0.33; rung 3 to 0.35; rung 4 to 0.65; NOT STARTED: BUDGET above | rung 1 for x ≤ 0.002; rung 2 to 0.22; rung 3 to 0.25; rung 4 to 0.51; NOT STARTED above |
| Charged (the first draft and E-J8) | rung 2 for x ≤ 0.03; rung 4 to 0.18; NOT STARTED above | rung 4 for x ≤ 0.10; NOT STARTED above |

- The ruling roughly triples the projected speed range in which S2 starts at all, and it makes four replicates or full-length training reachable.
- It changes no label rule. Four replicates make "every replicate" harder; U = 2,000 makes acquisition easier.
- Total machine time stays near 36 h on the projection. The recomputation is smaller than R, so P + R + recompute ≤ P + 2R ≤ 36. In effect the recomputation spends the headroom that the 2× rule keeps for overruns of the registered run.
- **The recomputation has no cap of its own.** Only the memory limits apply.

**Are results unreportable before it completes?** Yes. §13.3 says "no result is reported before it completes", and §16 step 10 puts the recomputation before the outcome report. But nothing defines "completes" or bounds its time, and nothing says what a disagreement or a failure does (M4). A study could therefore sit permanently unreported, or be reported after a disagreement under no rule.

**Rung table (recomputed, `out/arith.out`):**

| Rung | Design | Training + scoring (h) | Second gates stage (h) | R (h) | R + recomputation (h), for comparison |
|---|---|---|---|---|---|
| 1 | 4 × 2,000 | 14.35–35.51 | 0.107–0.397 | 14.46–35.90 | 20.28–54.74 |
| 2 | 3 × 2,000 | 10.84–26.78 | 0.107–0.397 | 10.95–27.18 | 15.39–41.46 |
| 3 | 4 × 1,000 | 10.09–27.17 | 0.107–0.397 | 10.19–27.57 | 16.01–46.41 |
| 4 | 3 × 1,000 | 7.64–20.53 | 0.107–0.397 | 7.75–20.93 | 12.19–35.21 |

- The bound is R ≤ (36 − P)/2, which gives 16.25 h at P = 3.5 and 14.5 h at P = 7.0. The text is correct.
- **Reachable on the projection:**
  - rung 1 only at the very fast end, needing P ≤ 7.08 even at x = 0;
  - rungs 2 and 3 in the fast fifth to third of the range;
  - rung 4 up to about the middle of the range;
  - NOT STARTED: BUDGET in the slower 35–49%.
- The text's "rung 1 holds only at the fast end … plausible that the rule ends at rung 2 or below, or at NOT STARTED: BUDGET" is correct.
- The second-gates-stage figure (4 × 1.6–5.2 min + 0.05 h) is the drafter's unmeasured estimate and is so labelled.
- Nit m13: the "Rehearsal 1.5–3.0 h" row does not include the added 200-update runs at the other read layer. That is about 0.1–0.2 h on the table's rates, inside P.

## 4. Task 4: the download scope and the human answers

**One consistent statement?** Yes, with wording nits.

- §4.2, §14.1 (intro, table total, link-file bullet, one-session bullet), §14.2 (wheels bullet), §15 (standing), §16 (order, items 1–6) and §18 (closing scope statement) all say the same thing:
  - teachers, student and Tatoeba rows 1–4 approved;
  - fallback teacher and Spanish data only if invoked;
  - the wheels for the data-generation step approved;
  - the 6.2 MB link files not approved;
  - nothing else outside the lock.
- The earlier §18 records are kept as written and superseded explicitly, which is acceptable.
- Nits:
  - m9: "930 MB approved and fetched" reads as if the files had been fetched; "No download has been made."
  - m10: §14.2 runs `uv run --locked --with-requirements …`, but the wheels bullet and the §18 record say `uv run --locked --with`.
  - m11: §4.2 makes fallback invocation a reserved decision, but §16 does not list it.
  - m12: "Things the lead must verify" still lists "the symmetry of the link files", which cannot be checked without the unapproved files.

**Does anything rely on an approval not given?**

- **M5, the wheels.** "I approve the package" answered "Approve the package wheels and the 6.2 MB of link files for S2? These were not in the 938 MB figure."
  - The question as quoted gives no size for the wheels. The lead's standing correction (§18) says "No wheel and no link file is fetched until the human lead says so **with their sizes in front of them**", and §14.1 repeats it.
  - Revision 5 extends the approval to "the dependencies the resolver requires", whose names and sizes are unknown.
  - The reading of "the package" is broad for the wheels and narrow for the link files.
  - Both readings may be reasonable, but they are the lead's readings. If the message before the question gave the 23–32 MB figure, the record should quote it. If it did not, the approval falls short of the record's own condition.
  - I recomputed the wheel sizes from `web/pypi_*.json` (macOS arm64, cp312). The seven fixed wheels total 18,169,099 B. Adding numpy gives 23,283,017 B (macOS 14 wheel) or 32,354,319 B (macOS 11 wheel). The "about 23 to 32 MB" figure is correct.
- **The 36-hour context.**
  - §18 states it under "Recorded by the lead", so it is formally the lead's record.
  - §15 states it as fact ("which answered the lead's message listing S0 16 h, S1 12 h, S2 36 h, total 64 h") without saying it is the lead's account.
  - The message is not in the repository (grep for "64 h"/"total 64": none). ADR-0021 words the same fact as "the numbers shown to the human lead were S0 16 h, S1 12 h, S2 36 h", after a note that "The coordinating session states … The author … did not read the chat record". ADR-0020 says "as relayed by the lead".
  - So it is **not** stated only as the lead's confirmation of context (m2).
- **"The first two clauses answer other questions."** ADR-0020's addendum and ADR-0021 §15 identify them: "yes I do" answered the P9-II acceptance question (ADR-0019 §16), and "yes we can raise to 16" answered S1's cap. The sentence can name them (m15). This also closes "Open for the lead" B.4.

## 5. Task 5: oracle qualification

- **The quote is exact** in both places (header line 9 and §11.3): "S1 and S2 must not claim autonomous learned-memory success from oracle-assisted results." It matches the task text character for character, including the final period.
- **Coverage.** The fixed line heads:
  - every label (§11.3);
  - every mechanism-class line (§11.2 and §11.3, second bullet);
  - every annotation, including ROUTER and COMPOSES in tables of their own (§11.4);
  - every cost line (§11.5);
  - every "(n, U)" class line (§9).
- The "no positive wording" bullet extends it to the named words and to "every other class, mechanism, router, composition or cost line", in reports, captions, the machine-readable record and terminal or log summaries, and requires the analysis to refuse an output that lacks it. **Every printed class, mechanism, router, composition and cost line is covered.**
- Side effect, harmless: the word QUALIFIED would also oblige the pre-freeze G3 teacher-qualification record to carry the line.
- **Provenance gap (m3).** The sentence appears nowhere else in the repository. Unlike every other human quotation in §18, it has no date, no record and no question it answered. The first draft listed it under "Things to verify". Ruling C58 removed that bullet without adding a record.

## 6. Task 6: what an implementer still cannot implement

**Blocker:** none.

**Major:**

- **M1. Unlisted generator uses against G9.** G9 accepts only "a replicate base + 0…10, or 220901–220905" and a source check forbids any other seeding. The text needs a seed, or a stated stream, for:
  - the bootstrap intervals that "every cell prints";
  - the 300 seen-item training items;
  - the 200 items per panel of the timing benchmark;
  - the 100 "fixed" sentences of each teacher's tokenizer record;
  - the 1,000 random id sequences of §14.2 test (c);
  - M-ii's replay sampling;
  - the router's batch sampling;
  - the order of the partition seed's several draws (groups, Q, D_cal, D_con, E_*).

  Also unstated:
  - whether a seed "shared" by several uses (+0, +6, +8, +9) restarts a fresh generator per use or continues one. §9's "within a replicate every arm shares … the initialization of shared parameters" implies restarting, and that is what makes ST1 and MA-gold a paired comparison;
  - whether the partition-side streams 220903–220905 are drawn once and stored, because otherwise rehearsal scoring would need registered seeds that G9 refuses for the rehearsal stage.

  None of this is scientific. Without it, G9 fails or the implementer invents seeds.
- **M2. Position confound in the router recipe** (scientific, **PENDING LEAD REVIEW**).
  - Every "none" example is a WikiText prefix of exactly 64 tokens, decided at position 64.
  - Every task example is decided at the last token of a 3–10-word prompt, about position 8–25.
  - Every GEN decision is at position 64.
  - A linear probe of the block-L hidden state can separate the classes by position alone. A router that learned that stays silent on all 200 windows whatever their content, which defeats J5's hard-negative stratum and makes the GEN label gate easy to pass for a reason unrelated to keywords. ROUTER QUALIFIED would also look perfect on the same artefact.
  - Revision 4 left the recipe open. Revision 5 (from E-J6, the re-check's own text) pins the confounded version.
- **M3. The recomputation ruling** (budget; section 3). It needs either the human lead's confirmation, with the 4.4–18.8 h figure and its effect on the rung rule in front of them, or the lead's explicit acceptance recorded as a narrowing of what the 36-hour cap covers. The header sentence "no … cap is changed" needs qualifying either way.
- **M4. The recomputation gates reporting but has no rule.** The text does not say:
  - what "completes" means;
  - which tolerance applies (bit-identical if the auditor runs the frozen CPU scoring; a stated tolerance and identical greedy sequences if the auditor's own code is used);
  - what a disagreement does to a gate, class or label;
  - what happens if the recomputation cannot run within the memory limits.

  This was already open in revision 4. It now matters, because the ruling made the recomputation the condition for reporting.
- **M5. The wheels approval premise** (section 4).

**Minor:**

- m1. The header says "does nothing else".
- m2. The 36-hour context is stated as fact in §15.
- m3. The oracle sentence's provenance.
- m5. The P9 reference-test contradiction.
- m6. The mapping from (task, word) to `unit_code`'s integer identifier is unstated.
- m7. The string-matching rule for GEN strata is unstated: case, substring against whole word ("Germany" contains "German"), and where the newline of "a line ending in ':'" must fall.
- m8. J7 adopts the option the ADR itself calls easier ("draws disjoint across replicates … harder to satisfy"), contrary to the header's rule. It is disclosed in open question 7, but the header should name the exception.
- m9. "approved and fetched".
- m10. `--with` against `--with-requirements`.
- m11. Fallback invocation is not in §16's reserved list.
- m12. The verify-list item on link symmetry.
- m13. The rehearsal row of §13.3 omits the other-layer runs.
- m14. `build.py` reads an uncommitted `open_for_the_lead_v2.md`.
- m15. The first two clauses of the wheels answer are not named.

**What must be settled when:**

| Point in the work | Must be settled |
|---|---|
| (a) Implementation on synthetic stand-ins | M1 (the seed list feeds the seeding function and G9). M2 should be decided before the router lane is coded; if not, the "none" prefix length must at least be a parameter. m5, m6, m7. |
| (b) Downloads | M5 (record what was shown, or ask again with sizes); m9, m10, m11. The link files are already handled: no fetch and no check without an answer. |
| (c) The freeze | M2 (if not already done), M3, M4. J9, the acceptance of §15 items 1, 4, 5 and 7 in the lead's approval record. m2, m3, m8, m13. |

## 7. Model

I ran as Claude Opus 5.5 (`claude-opus-5-5`).

## 8. Paste-ready edits

Bracketed text and every **[lead's choice]** is for the lead. Scientific points are marked **PENDING LEAD REVIEW**.

**R-M1 (§9, after "220905 the GEN window selection.")**

> Further listed seeds **[lead's choice]**:
>
> - 220906, the bootstrap resampling of every printed interval;
> - 220907, the 300 seen-item training items;
> - 220908, the 200 items per panel of the timing benchmark;
> - 220909, the 100 fixed sentences of each teacher's tokenizer record;
> - 229901, the 1,000 random id sequences of §14.2 test (c).
>
> 220902–220909 are drawn once, in the data-generation and partition steps, and stored with the data manifest. No later stage draws them again. The partition seed 220901 draws in this order: the assignment of identity groups, then Q, D_cal, D_con, E_A, E_B, E_C, E_open. Every use of a listed seed starts a fresh generator seeded with it. So where §9 gives one seed several uses (+0, +6, +8, +9), each use starts from the same draws in its own shapes. +1 first splits the shared sources (§5.2) and then draws A, then B; +5 draws A, then B. Within a replicate, a fresh +2 generator also orders M-ii's replayed rows, and a fresh +3 generator, after the router's initialization, samples the "none" prefixes and then orders the router's batches.

In G9, replace "220901–220905" with "220901–220909, 229901 in the data-generation step".

**R-M2 (§5.4, router lane; PENDING LEAD REVIEW; offered so that position cannot separate the classes)**

Replace "WikiText-2 *train* prefixes of exactly 64 tokens in equal number" with:

> WikiText-2 *train* prefixes, half cut at exactly 64 tokens and half cut at a length drawn, with seed +3, from the token lengths of the task prompts of that router's streams

Then append:

> Beside GEN, the report prints, for each router, the false-trigger rate on the 100 marker-like windows when the decision is taken at the last token of the first marker-like string in tokens 1–64; this diagnostic enters no rule.

The alternative is to keep the recipe and print the diagnostic only.

**R-M3 (§13.3, after "(The alternative not taken is the recomputation inside R.)")**

> Not charging it narrows what the 36 hours cover compared with revision 4's "all S2 processes". On the projection it is 5.8–18.8 h for four replicates. Charged, it would leave rung 4 or NOT STARTED: BUDGET as the only outcomes on most of the projected range. [The human lead has confirmed this on DATE: "…" / The lead accepts it in the approval record; PENDING the human lead's confirmation.]

In the header, change "No threshold, arm, model, data source, replicate count, rung or cap is changed." to:

> No threshold, arm, model, replicate count, rung or cap value is changed; the charged scope no longer includes the independent recomputation (§13.3), and a fallback language's data would come from a later export (§14.1).

**R-M4 (§13.3, after "no result is reported before it completes.")**

> The recomputation is complete when every registered score has been recomputed on CPU from the snapshots and compared with the registered score. [PENDING LEAD REVIEW: if it uses the frozen scoring code, every score must be bit-identical; if it uses the auditor's own code, every greedy sequence must be identical and every item score must agree within 1e-6.] Every difference is listed. If a listed difference changes a gate, class, annotation or label, the study label is ENGINEERING-FAILURE. If the recomputation cannot be completed within the memory limits, the label is INCOMPLETE and no class is printed.

**R-M5 (§18, after the wheels answer's "(The first two clauses answer other questions.)")**

> The question as put [did / did not] state the wheels' size; [the message before it gave "about 23 to 32 MB for the eight named packages"]. Reading the answer as covering the transitive dependencies, whose names and sizes are recorded at fetch time, is the lead's reading.

If no size was shown, put the wheels back in the open list of §14.1, §16 and §18 until an answer is given with the size in front of the human lead.

**R-m1 (header).** Replace "and does nothing else" with:

> records the human lead's answer on the package wheels and the lead's rulings on the first draft (§21), and does nothing else

**R-m2 (§15 standing).** Replace "which answered the lead's message listing S0 16 h, S1 12 h, S2 36 h, total 64 h (§18)" with:

> which, by the lead's record in §18, answered the lead's message listing S0 16 h, S1 12 h, S2 36 h, total 64 h; that message is not in the repository (ADR-0021 records the same context as relayed by the coordinating session)

In the §18 bullet, add "(the lead's account; the message is not in the repository)".

**R-m3 (closing list "Things the lead must verify", restore):**

> - The source and date of the human lead's sentence on oracle-assisted results quoted in the header and §11.3; it is not in the repository's records.

Alternatively, record that sentence in §18 with its date and the question it answered.

**R-m5 (§3, reference test).** Replace from "The test passes S2's own tensors" to the end of the bullet with:

> The test constructs P9's `ScalableMemory` inside the test only, with a test seed from 229001–229999, replaces its keys with S2's keys, and compares the selection of its flat top-8 and the softmax weights with S2's. P9's internal `seed + 1000·k` generators run only inside this test. G9's registered and source checks cover `studies/p10s2/` and not this test.

**R-m6 (§5.4, address):**

> The identifier passed to the hash is 2,001·τ + j, with τ = 0 for A and 1 for B, and j the word's index in the vocabulary table (j = 2,000 for the task marker) **[lead's choice]**.

**R-m7 (§6.4, window grid):**

> Strings are matched case-sensitively as substrings of the raw text (so "Germany" matches "German"); "a line ending in ':'" means a ':' immediately followed by a newline, both within the span in question **[lead's choice]**.

**R-m8 (header, after "harder for a positive label or counts more time against the cap;"):**

> except J7, where the re-check's split rule is kept although draws disjoint across replicates would be harder for a positive label (§20), and the recomputation, which is not charged (§13.3);

**R-m9 (§14.1 total).** "approved and fetched (rows 1–4)" becomes "approved, to be fetched (rows 1–4)".

**R-m10 (§14.2 wheels bullet and the new §18 bullet).** "installed with `uv run --locked --with`" becomes "installed with `uv run --locked --with-requirements studies/p10s2/requirements-datagen.txt`".

**R-m11 (§16, "Also reserved:").** Add "the invocation of the fallback teacher (§4.2);".

**R-m12 ("Things the lead must verify", second bullet).** "the symmetry of the link files" becomes "the symmetry of the link files (only if the human lead approves the two files)".

**R-m13 (§13.3, rehearsal row).** Add "(plus about 0.1–0.2 h for the 200-update runs at the read layer not selected)".

**R-m15 (§18).** "(The first two clauses answer other questions.)" becomes:

> (The first clause accepts the P9-II outcome, ADR-0019 §16; the second raises S1's cap to 16 hours, ADR-0021.)

**R-m14 (outside the ADR).** Commit `open_for_the_lead_v2.md` beside `build.py`, or make `build.py` write `CHANGES.md` without it.

Astra review: NOT_PERFORMED. This confirmation is not Astra validation and not a human approval.
