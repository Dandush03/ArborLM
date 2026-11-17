# Confirmation review — draft ADR-0026 revision 2 (P10-I-S3, longer training)

- Reviewer: `arbor-auditor` subagent, model Claude Opus 5.5 (`claude-opus-5-5`), 2026-11-17 UTC. I also wrote the first review (`REVIEW_ADR-0026.md`). I did not write the draft, the seed registry, or any code or analysis that either relies on.
- Reviewed: `docs/decisions/ADR-0026-p10-i-s3-longer-training.md`, SHA-256 `fb528450fd7286dc90f5f404c1817e33b1e4ea609c32861e1d2a0e960314f6e3`, at HEAD `26ea57b5b59b8921d0ac8a41e5d9ddc7bb703fa6`, branch `claude/p10-i-specs`, worktree `arborlm-consolidation-experiment-2b31c1`. Cross-read: ADR-0027 (`34ad329e…`), `SEED_REGISTRY.md` (`b3fe7cab…`), DIRECTION.md §4–5, CLOSURE_LEDGER.md, LITERATURE_AND_ROUTING_NOTE.md §3, ADR-0009, `configs/p1_ram_screen.toml`, `p2_optimization_followup.toml`, `p3_longer_training.toml`, `p8_locality_training.toml`, `src/arborlm/pilot_model.py`, `p4_model.py`, `p8_core.py`, P4/P5 records.
- This is independent engineering and mathematical evidence. It is **not** Astra validation and **not** a human approval. `Astra review: NOT_PERFORMED`.
- Nothing was trained, generated or downloaded. No file other than this one was written. No git writes. Sealed recall values of P10-S1 were not opened.

## Verdict: READY AFTER THE LISTED EDITS

The blocking finding of the first review (F1) is fixed: the duration is fixed at 16,384, the tag is a coded rule, and the run is automatic except on a failed gate or a recorded cost refusal. Every number I recomputed matches (section A). What remains is a set of text edits, each spelled out in section C and table D. Two are cross-document: ADR-0027's Route A text does not match ADR-0026's labels, and the draft's seed paragraph still names values that the registry replaced and repeats a "no overlap" statement that is false (my own first-review error, see section A). The two rulings already marked PENDING HUMAN LEAD RULING (open choices 1 and 5) stay with the human lead and are fairly put.

## A. Numbers recomputed, and my own errors

Command: `python3 -I <scratchpad>/r2_0026/budget.py <worktree>` (Python 3.15.1, system `python3`, macOS, standard library only, no `arborlm` import). Script path: `/private/tmp/claude-501/-Users-daniellaloush-dandush03-ArborLM--claude-worktrees-arborlm-consolidation-experiment-2b31c1/cfc0efd5-b7ca-4602-959a-07fe6b8d4e7d/scratchpad/r2_0026/budget.py`. It reads `training_seconds_including_logs_and_saves` from every P4 `b*-memory-*`, `b*-dense-*` and P5 `b*-flat*` `result.json`.

Output: `p4 tree (27, 14.1180) p4 dense (27, 4.2611) p5 flat (27, 3.0620)`; `per run s 451.78 97.98 136.36`; `R1 h 8.168 ext h 6.535`; `reg REP+FRESH h 10.292 REP-U h 4.411`; `per-duration h 9.649 anchor h 4.411`.

| Draft figure (location) | Recomputed | Status |
|---|---|---|
| 452 / 98 / 136 s per 16,384-update run (§9) | 451.8 / 98.0 / 136.4 | match |
| R1 120 runs, 8.2 h; extensions 0–96 runs, 0–6.5 h (§9) | 8 arm-regimes (tree ×3, flat ×2, dense ×3) × 5 × 3 = 120; 8.17 h; 4 × 8 × 3 = 96, 6.53 h | match |
| Rehearsal 10–16 h; cap 25 h ≈ 1.5 × worst (§9) | 8.2 + 1.5 = 9.7; 8.2 + 6.5 + 1.5 = 16.2; 25 / 16.2 = 1.54 | match (the 1.5 h evaluation row is an estimate, not checkable) |
| Registered 162 runs 10.3 h; REP-U 54 runs 4.4 h; per-duration 0–648 runs, 0–9.6 h; anchor 0–54 runs, 0–4.4 h | 10.29; 4.41; 8 × 27 × 3 = 648, 9.65 h; 4.41 | match |
| Registered 16–32 h; cap 48 h | 16.2–32.2; 48 / 32.2 = 1.49 | match |
| REP-U rehearsal "2.5 h at the least" (open choice 5) | 15 × 451.8 + 15 × 136.4 = 8,822 s = 2.45 h | match |
| Step-0 memory NLL 2.378856566 vs baseline 2.378856373 (§6.2, new) | `results/p4-2026-11-12/README.md` l.19–20; difference 1.9e-7 | match |
| 16,407 eligible validation chunks; 152,515 = 156,611 − 4,096 (§4) | `dataset_manifest.json` counts | match |
| 64 passes, 131,072 target bytes (§3.3); 86% overlap (§5) | 16,384 × 8 / 2,048 = 64; 2,048 × 64; 131,072 / 152,515 = 0.859 | match |
| "about 9,000 evaluations" for primary runs; "4 per D-ADAPT" checkpoint (§9) | With 4 evaluated checkpoints and 16/12/4 per checkpoint: 5,184 + 2,592 + 1,296 = 9,072. But D-ADAPT needs enabled, replay, disabled, 4 X_dense draws, X_mean_dense = 8, not 4 (→ about 10,400) | small undercount, ADVISORY N9 |
| "up to about 5,700 snapshots" (§9) | My count: rehearsal 216 × 5 + primary 216 × 5 + per-duration runs saving their own earlier checkpoints 1,944 + anchors 270 ≈ 4,400 | not reproduced; conservative; ADVISORY N9 |

**My own errors, recorded as the audit policy requires.**
1. First review F7 stated: "the registered seeds expand to 3601–7603 and 3691–7692. I found no collision in `configs/`, `src/`, `studies/` or `tests/`." **That was wrong.** P8 uses addition seeds 601 and 602 (`src/arborlm/p8_core.py:88`, `configs/p8_locality_training.toml:12`), and `Memory(variant, seed)` draws values from seed + 2000 and `wq` from seed + 3000 (`src/arborlm/pilot_model.py:118–124`). So P8's value generator was seeded 2601/2602 and its `wq` 3601/3602, which equal ADR-0026's proposed initialisation seeds 2601/2602 and their key generator. I searched for the expanded S3 values but did not expand the earlier three-digit seeds. The seed registry (§5, row 3) found it; I confirmed it in the source. The draft (§4, l.113) now repeats my wrong statement.
2. First review F3 said the gain kept under a context-free read, B − H_mean, is "naturally bounded between 0 and roughly C". That is not guaranteed: the mean read is one particular constant passed through the nonlinear block 1 at every position, and it can raise the loss above B. The draft copied the claim (§3.4, l.92). See N2.

## B. First-review findings

| Finding | Judgement | Notes |
|---|---|---|
| F1 BLOCKING, discretionary duration | **FIXED** | §5.2: U\* fixed; tag δ < ε by code; "runs at 16,384 whatever the tags"; probe removed; §7 "no extension path"; §10 only two not-run paths. Remaining hole: Decision 2 has no stated grounds for refusal (N1). |
| F2 unsealed calibration statistics | **PARTLY FIXED** | Whitelist and sealed file are good. Consequence of an auditor "disagree" is undefined, and the sealing is procedural only (N3). |
| F3 what X measures | **PARTLY FIXED** | X_mean in D3, X descriptive, wording narrowed. The stated bound on B − H_mean is false, and B − H_mean with its above-baseline count is not in the printed list of §6.7 (N2). |
| F4 stricter than P4 | FIXED | §3.4 l.101, §12. Checked against ADR-0009 l.83–85: P4 flag 2 = mean P ≥ 0.005, 22/27 cells with C > 0 and P > 0, 8/9 parents; no ratio. S3's line 1 adds the 0.5·C ratio on two controls and is strictly harder. |
| F5 unique data confounded | FIXED (pending ruling) | REP-U added, costed, contrast table correct. See N7 for the missing flat arm and the REP-U gate wording. |
| F6 calibration parents | FIXED | §5, §6.7 six-parent readout, §12. |
| F7 seed offsets | **FIX INTRODUCED A NEW PROBLEM** | Roles and counts listed; calibration index 0–2 defined; reuse across arms stated. But §4 still names 2601–2699 and 926001–926999, says the review found no overlap (false, section A error 1), and describes registered init seeds as "one set per parent" (the registry: one per seed position, shared by all nine parents). Table D. |
| F8 panel rule | FIXED | Byte spans, siblings, ledger, stop case. Start rank 8,192 unexplained (N9). |
| F9 precedence and definitions | **PARTLY FIXED** | Order table for line 2, losing arm, float64 mean, exact comparisons, rate tie rule, D1 omission: all done. Not done: line 1 has no NOT EVALUABLE row in its label table, and the mean is undefined when a memory cell is non-finite (N4). |
| F10 labels against ADR-0027 Route A | **NOT FIXED (pair)** | ADR-0026 §12 is now correct. ADR-0027 l.48 still uses labels ADR-0026 no longer has and pre-empts open choice 13 (N5, table D). |
| F11 planted positive, prefix identity, read equality | FIXED | §11 rows 4–6, §8 G, §10 row 1. Advisory on the planted construction (N8). |
| F12 budget | FIXED | Section A. |
| F13 routing trend | FIXED | ΔG printed. G_prior has no reading rule (N9). |
| F14 threshold reasons | FIXED | |
| F15 wording | FIXED | |
| F16 stop cases | FIXED | |

## C. New findings

**N1 — REQUIRED — §14 Decision 2, §5.2 bullet 4, §10 row 3: Decision 2 is an unconditioned refusal point after rehearsal output exists.** The draft says the study is "not run only for a cost or engineering reason", but Decision 2 is a human approval with no stated grounds, taken after the human lead has seen `rehearsal_public.json` (rate table, δ per arm and regime). The ADR cannot bind the human lead, but it must say how a refusal is recorded. Change: append to §14 Decision 2: "If Decision 2 is refused on any ground other than a §10 cost or engineering stop, the refusal and its reason are recorded in this ADR before any sealed file is opened, and the study's outcome is recorded as NOT RUN (DECISION 2 REFUSED: <reason>). The sealed file is then published unopened-by-rule with that record." Also state in §14 that every open choice of §13 is ruled at Decision 1, before the rehearsal.

**N2 — REQUIRED — §3.4 l.92, §1 l.21, §6.7 l.268: false bound on the context-free read; its harm is not printed.** "The gain kept, B − H_mean, lies between 0 and about C" is not guaranteed (section A error 2). If the mean read raises the loss above B, X_mean exceeds C and D3 is met partly by harm, the same problem F3 raised for X, in weaker form. Also the mean read is one constant, not the best constant, so D3 shows that this context-free read does not suffice, not that none would. Change: (a) §3.4 l.92 "Shows" cell → "Whether the batch-mean read, applied at every position, keeps the gain. It is expected, not guaranteed, to keep between 0 and about C; B − H_mean is printed per cell with the count of cells in which H_mean > B." (b) §6.7: after "B − H_used, B − H_x" insert "B − H_mean". (c) §1 line 1 positive cell: replace "(the gain depends on the query)" with "(the batch-mean read does not keep the gain; a better constant is not tested)". (d) §12 bullet 2: add "D3 tests one context-free read, the batch mean."

**N3 — REQUIRED — §5.3: the auditor's "disagree" has no consequence, and the seal is procedural.** Change: add after the table: "If the auditor's recomputation disagrees, the auditor and the implementer reconcile on code and on the DRY and synthetic files only; no one reads the sealed file. If they cannot reconcile, that is an engineering stop before Decision 2 under section 10. The auditor's checker prints only `agree`, `disagree` and the names (not values) of disagreeing fields; its source is part of the review record. The seal is procedural: the sealed archive is stored outside every agent's working directory, its SHA-256 is recorded in `rehearsal_public.json`, and every session that touches it is logged in the run's `NOTES.md`." Also add to §10: "Auditor reports disagree and reconciliation fails | Engineering stop before Decision 2."

**N4 — REQUIRED — §6.1 l.181, §6.2 l.205–209, §10 l.347: undefined mean with a failed cell; no NOT EVALUABLE row for line 1.** A non-finite memory cell "counts as failing every condition", but the mean over 27 cells is then NaN in a direct computation, or the mean of 26 under a `nanmean`; two people get different labels. Line 1's label table has no precedence row for §10 cases although §1 and §10 produce NOT EVALUABLE for line 1. Change: (a) §6.1, after the definition of "Mean": "If any of the 27 cells of the arm is a failed cell (section 10), every mean condition of that arm is false and the failed cell counts as failing every per-cell and per-parent count; no mean is computed over fewer than 27 cells." (b) §6.2 regime label table: insert first row "| A stop or integrity case of section 10 applies to M-TREE in the regime, or BASE is missing | NOT EVALUABLE |" and state "computed in this order; the first rule that applies decides".

**N5 — REQUIRED — ADR-0027 l.48 against ADR-0026 §6.5 and §12: label names and the convergence clause do not match.** See table D. ADR-0027 additionally decides open choice 13 ("with the FRESH regime CONVERGED") and in a different form (all arms of the regime, not D-ADAPT). Change: ADR-0027 l.48 must read, word for word: "(A1) the registered label of line 1 is DEPENDENT (ADR-0026 section 6.5: the FRESH regime label, arm M-TREE); (A2) the registered label of COMPETITIVENESS[TREE] is COMPETITIVE or MEMORY AHEAD (FRESH). Whether a qualifying label still qualifies when D-ADAPT's registered FRESH convergence tag is NOT CONVERGED is ADR-0026 open choice 13, as ruled at Decision 1 of ADR-0026. REP and REP-U regime labels, CAPACITY WITHOUT DEMONSTRATED DEPENDENCE, NOT COMPETITIVE, INCONCLUSIVE, NOT EVALUABLE and COMPETITIVENESS[FLAT] never satisfy Route A."

**N6 — REQUIRED — §12 l.391 and §13 item 13 l.415: two different conditions for the same open choice.** §12 says "carries '(DENSE STILL IMPROVING)' or a NOT CONVERGED tag"; §13 says "when D-ADAPT is NOT CONVERGED in FRESH". Under §6.4, "(DENSE STILL IMPROVING)" is appended only when the dense arm is the losing arm, so a COMPETITIVE label with the dense arm ahead and still improving carries no tag; and "a NOT CONVERGED tag" also catches M-TREE. Change both to: "D-ADAPT's registered FRESH convergence tag (section 5.2, last bullet) is NOT CONVERGED, whichever arm is losing."

**N7 — REQUIRED — §11 row 1 l.359: the frozen-input set is not exact.** Missing or unstated: (a) the file list of "the imported `src/arborlm/` files" (name them: at least `pilot_model.py`, `pilot_data.py`, `p4_model.py` and every module they import); (b) where the planted-positive and synthetic-registry tests live; if under `tests/`, they are outside the set; (c) thresholds outside §6 that the run uses: ε = 0.001 (§5.2), the rate grid, tie tolerance 0.0005, edge rule, PAST BEST margin 0.005, the 1e-6 tolerances, the LOADED threshold 4; (d) the seed plan and the copy of the seed checker (registry §4.3 condition 5); (e) `rehearsal_public.json` and the sealed file's hash; (f) the shared panel ledger; (g) the approved ADR text itself: not a run-time input, but its identity at approval is what the audit compares the code with. Change l.359 to: "…`configs/p10i_s3_longer_training.toml` (which carries every threshold, tolerance, grid and margin of sections 5, 6 and 7), the tests of this study (which live under `studies/p10i_s3/tests/`), the seed plan and the extended seed checker under `studies/p10i_s3/freeze/`, `rehearsal_public.json` and the sealed file's SHA-256, the panel ledger by SHA-256, the `src/arborlm/` files `<list>` by SHA-256, … This ADR's SHA-256 at Decision 1 and at Decision 2 is recorded in `plan.json`; the ADR is not checked at run time, and any later edit of it is an amendment with a record."

**N8 — ADVISORY — §11 planted-positive row.** For X_mean ≥ 0.5·C to hold by construction, the planted corrections of the disjoint query sets must have (near) zero mean across the batch; otherwise the batch mean keeps part of the gain. State it in the test's construction.

**N9 — ADVISORY — miscellaneous.**
- §3.3 l.67: the REP-U gate "no study used them for training or evaluation" is stricter than needed and may fail on a harmless use (for example P1 and P2/P3 *ranked* 4,096 train chunks, `configs/p1_ram_screen.toml:11`, `p3_longer_training.toml:10`, but consumed 256 × 8 = 2,048). The scientific requirement is that no batch of the P2/P3 lineage of the nine parents contained them; state the gate that way and apply the same gate to FRESH ranks ≥ 4,096. Cite P1's consumption arithmetic since "P1 to P3" is claimed.
- §3.3: M-FLAT is absent from REP-U without a reason. Adding it costs 27 × 98 s = 0.73 h registered and 15 × 98 s = 0.41 h rehearsal (more with grid extensions). Without it, COMPETITIVENESS[FLAT] and any flat contrast cannot be split into seen versus unseen data. Either add it or state the reason.
- §4 l.111: why the panel walk starts at validation rank 8,192 rather than 4,096 is not stated.
- §5.2 l.162: "lowest descriptive checkpoint" for PAST BEST: state whether it is along the primary-rate run and on the 27-cell mean.
- §6.6: G_prior has no reading rule; say it is printed without a label.
- §8 R2: the LOADED threshold 4 has no reason.
- §9: D-ADAPT evaluations per checkpoint are 8, not 4; the 5,700-snapshot figure is not reproduced (section A).
- §13 item 1: add the direction's own qualifier, "16,384 … only if the rehearsal and the budget support it": under this draft only the budget can fail to support it.

## D. Cross-reference mismatches

| File | Line | What it says | What it must say |
|---|---|---|---|
| ADR-0027 | 48 | "(A1) … **DEPENDENT, BOTH REGIMES** or **DEPENDENT, FRESH ONLY**" | "(A1) the registered label of line 1 is DEPENDENT (FRESH, M-TREE)" — ADR-0026 §6.5 has no regime-combination labels |
| ADR-0027 | 48 | "(A2) … COMPETITIVE or MEMORY AHEAD, BOTH REGIMES or FRESH ONLY" | "(A2) … COMPETITIVE or MEMORY AHEAD (FRESH)" |
| ADR-0027 | 48 | "with the FRESH regime CONVERGED" | Remove; refer to ADR-0026 open choice 13 as ruled (convergence tags are per arm, not per regime) |
| ADR-0027 | 48 | "and no INCONCLUSIVE tag" | Remove; INCONCLUSIVE is a label in ADR-0026 §6.4, already excluded by the qualifying list |
| ADR-0027 | 48 | "REPEATED DATA ONLY … fail Route A" | "REP and REP-U regime labels, CAPACITY WITHOUT DEMONSTRATED DEPENDENCE … fail Route A" (the label REPEATED DATA ONLY no longer exists) |
| ADR-0027 | 131 | "ADR-0026 initialisation 2601–2691" | "ADR-0026 initialisation 330301–330399 (SEED_REGISTRY.md §4.2)" |
| ADR-0026 | 113 | "proposes … 2601–2699 for initialization, and 926001–926999 for tests; the review found no overlap … including the component seeds" | "Initialisation seeds are in the P10-I row: registered 330301, 330302, 330303 (seed positions 0, 1, 2), calibration 330391, dry rehearsal 330392, test mode 330398, 330399; tests 935001–935999; streams and permutations 260001–269999 as laid out in SEED_REGISTRY.md §4.2. The first proposal, 2601–2699, collided with P8 (601/602 + 2000; registry §5) and was replaced." |
| ADR-0026 | 117 | "Registered initialization seeds — 3 — One set per parent" | "3 — one per seed position (0, 1, 2), shared by all nine parents; each expands to five component seeds (seed + 1000 … + 5000; DenseAdapter + 3000, + 4000)" |
| ADR-0026 | 118 | "Calibration …; dry-rehearsal initialization seed — 1; 1" | add row "Test-mode initialisation seeds — 2 — 330398, 330399" |
| ADR-0026 | 124 | "Test seeds — up to 999" | "Test seeds — 935001–935999" |
| ADR-0026 | §4 (after l.126) | — | add: "The study does not call P4's or P5's permutation helpers (`src/arborlm/p4_model.py:266-270`, `p5_model.py:258-262`), which hard-code 40000 + index … 70000 + index (registry §4.3 condition 3). The freeze gate re-runs a copy of the registry checker with R2 (k ≤ 10) and R3 expanded (condition 5)." |
| ADR-0026 | 391, 415 | open choice 13 in two forms | one form, as N6 |

Registry against draft roles and counts (registry §4.2 l.157–163): streams 81 = 27 × 3 regimes (260001 + 3c + g); P_all 27 + 3 + 1; P_used 108 + 12 + 4; X 108 + 12 + 4; calibration 9 streams with c = 0–2; dry 3 streams. All agree with the draft's table. Seed checker run: `uv run --locked --offline python docs/reviews/p10-i-direction-2026-11-17/seed_registry_check.py` → `RESULT: PASS`; it still lists the draft's 2601–2602 collisions with P8 (lines 56–65 of its output), which is the replaced proposal.

Closure ledger: the two rows carried into P10-I-S3 (l.25 P4 dense; l.27 P5 dense-reference) are taken up in §2, line 2 and §12. Row l.24 (P3-LT, closed) is acknowledged in §2. Nothing is declined.

## E. Open choices reserved for the human lead

| # | Choice | Really the human lead's? |
|---|---|---|
| 1 | Fixed duration meets "convergence-based" | Yes; it reads the direction. Fairly put; add the direction's "only if supported" qualifier (N9). |
| 2 | Rate fairness | Yes, as confirmation; the rule itself is written. |
| 3, 4 | Dependence and competitiveness thresholds | Yes; scientific thresholds fixed at Decision 1. |
| 5 | REP-U | Yes (scope and cost). Fairly put. |
| 6 | Routing interaction descriptive | Yes; it reads the routing note. |
| 7 | No by-construction arm | Yes. |
| 8, 9 | Repeated-data order; schedule | Design choices the draft has already made with reasons; asking is fine. |
| 10 | Registered label = FRESH label | Yes. |
| 11, 12 | Caps; anchor | Yes (budget). |
| 13 | Tags and S4 entry | Yes, but it must be ruled at Decision 1, before observation, and ADR-0027 must then copy the ruling instead of deciding it (N1, N5, N6). |

Not parked but should be stated: the grounds and record of a refused Decision 2 (N1).

`Astra review: NOT_PERFORMED`. This review is not an approval.
