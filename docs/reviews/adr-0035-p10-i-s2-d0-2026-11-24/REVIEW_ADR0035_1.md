# Review 1 of draft ADR-0035 (P10-I-S2-D0, interference diagnosis), draft 1

- Reviewer: `arbor-auditor` subagent, Claude Opus 5.5 (`claude-opus-5-5`), 2026-11-24. Independent engineering and mathematical review. This is not Astra validation and not human approval.
- Read-only review. No snapshot was loaded or scored. `row_shares` and the `extras` records were not opened. Only registered values were read: `registry.json`, `report.txt`, `charged_ledger.json`, audits 20 and 21, and the key skeleton of `item_records.json` (keys only).
- Code read: Part T worktree `/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/agent-acd0bce1f7811562f`, branch `claude/p10-i-s2-impl` at `f6dff34d201fb02f3ff77e5a33c17400a686f286`. Files: `studies/p10s2/memory.py` (SparseStore.read, CodeBook, MemoryArm, row_shares), `studies/p10s2/cells.py`, `studies/p10s2/evaluate.py`, `studies/p10s2/train.py` (train_arm, reads_of), `studies/p10is2/quantities.py`, `labels.py`, `annotations.py`, `partt_gates.py`. Also ADR-0034 draft 9 on `claude/p11-s1-spec`, section 4.2.
- Environment for the numbers: `/opt/homebrew/bin/python3` (Python 3.15.1), run with `-I`, standard library `json` only. Scripts were inline `python3 -I -c` reads of `results/p10is2-partt-run-20261124/records/registry.json`. They averaged `s:E_A` and `s:E_B` per arm, recomputed F, rho, APPEND COST and its share of the loss, and summed the evaluate rows of `charged_ledger.json`. `shasum -a 256` was run on both copies of `item_records.json`.

## Verdict

**SOUND AFTER THE LISTED CHANGES**: six REQUIRED changes and nine ADVISORY ones, listed at the end. None changes the design. Five are precision and text fixes. One (R5) is the approval record.

## 1. Correctness against the code

- **SparseStore.read** (memory.py 128–139):
  - concatenates every stage's keys, values and gates;
  - computes cosine as `q @ (k/|k|)ᵀ`;
  - takes the top 8 with a stable descending sort, so ties go to the lowest row index;
  - applies a softmax at 0.2 over the 8 selected rows;
  - sums `w · g_stage · V`.

  Draft §1.1 and §4 describe this correctly. A gate-0 stage does take slots and softmax mass.
- **Queries.** `MemoryArm.queries` stacks `CodeBook.get(task, j)`, which is `unit_code(seed, ident, 16)`: no projection and no trained parameter. Reads come from `reads_of`: prompt word positions plus the marker, under the oracle route (the example's own task). They do not depend on decoding. Scoring runs one item per call (`generate`, batch 1). Read statistics per item are therefore well defined and the same under every condition.
- **Freezing.** In `cells.py` lines 90–93, M-append clones the in-memory ST1 store, appends a stage whose gate is `torch.zeros(1)`, then freezes stage 0 and sets only stage 1 trainable. `train_arm` builds AdamW over `arm.trainable()` only, so stage-1 tensors are never touched. Gate G4 covers gradient reach, as `partt_gates.py` line 4 states. The `@append` snapshot is saved before any update, so g2 = 0 exactly there.
- **Claimed identity: b(1) on an M-append store equals M1's read bit for bit.** Mathematically it holds: same stage-1 tensors, same queries, same frozen student. Bit identity follows from the code **only if b(p) is computed with the unmodified `SparseStore.read` on a store holding stage p's tensors alone**. That is the same op sequence and the same shapes as the M1 read.
  - If D0 instead slices stage 1's columns out of the full-store cosine matrix, the matmul has a different N dimension.
  - Bit identity of each element is then not guaranteed by the code; BLAS tiling may differ.
  - A one-ulp change can flip a top-8 tie or a softmax weight and, rarely, a greedy token.

  The draft does not fix the implementation (R3).
- **G ∩ S1 equals the top n1 of T8(S1)** (§5.2). This is true because stage-1 rows have lower indices than stage-2 rows and the sort is stable, so the restriction to S1 keeps S1's own order. The same holds for p = 2. It again assumes the cosines are computed identically in both places (R3).
- **e(1) = a at the append point.** This holds exactly in value because g2 = 0.0.
- **a = e(1) + e(2).** This holds mathematically but is **not bitwise** in float32: the eight-term sum is regrouped. The draft says the identities are "tested as tensors" but gives no tolerance (R3).
- **d, e, g.** Each is uniquely defined given G and σ(G) from the registered computation. d(p) for an empty K gives the zero vector, which reaches the student as `x + 0 = x`, the same as no read.
- **b(1) and M-sep.** b(1) on E_first equals M-sep's first-capability score per replicate. `CompositeStoreArm` routes the first task's reads to `ST1/{first}{second}`, which is that cell's M1. Registry check: the mean of M1|AB|r s:E_A over r = 0.451980 = M-sep s:E_A mean, 0.451980.

## 2. Decomposition arithmetic

- **The path.** T = s[b1] − s[a], and (i) + (ii) + (iii) telescope along b(1) → d(1) → e(1) → a. Each term is uniquely defined.
  - d(1) is the read of the top n1 own rows, renormalised.
  - e(1) is the same rows at their σ(G) weights.
  - a adds stage 2's registered contribution.
- **The second order.** g(1) gives b(1) → g(1) → a. In read space, g(1) − a = b(1) − e(1), so this order is "values first, then competition". The interaction (iii) − (s[b1] − s[g1]) equals (s[g1] − s[a]) − ((i) + (ii)). Its definition is single and the draft handles the order question honestly.
- **What the draft leaves unstated:**
  - (a) The (i)/(ii) split has only one order; mass-without-displacement is not defined. So the displacement–mass interaction is not estimated (A2).
  - (b) The §7 wording uses the path order only (A3).
  - (c) The residual (iv) is bounded by the gate tolerance; it is not exactly zero unless the tolerance is 0 (A8).
  - (d) The reference vector for the E_second read statistics, "with the stages exchanged", is not named. R_M1 has no counterpart on E_second (R6).
- **Units.** F is in s units: `quantities.py` defines F(X) = s_first(V1) − s_first(X). T therefore matches F in units. APPEND COST is in G units, G = (s − s_S0)/(s_teacher − s_S0). The draft keeps these apart correctly.
- **Append-point arithmetic.** (i) + (ii) at append equals s[M1] − s[a@append], because e(1) = a there. The final value is s[b1] − s[e1]. e(1) does not depend on g2 or V2, and stage 1 and the queries are fixed. So the difference between the two is attributable to stage-2 key movement alone. This claim is correct.

## 3. Forking paths and overclaim

- **Fixed before any reading:** conditions, the 16 passes per cell (I counted 9 on E_first and 7 on E_second; 96 in all), cells, panels, terms, wording cut-offs, run-once, and the post-read marking. The two wording labels are mutually exclusive whenever T > 0, and T = F > 0 in all six cells.
- **Left open:**
  - the E_second reference (R6);
  - the identity tolerances (R3);
  - the retry rule after a failed gate (R4);
  - the SD convention (n − 1) and the G formula's source (A6);
  - the run-directory copy: two copies exist with the same `item_records.json` hash (A, under R4).
- **Overclaim, §1.4: "the ceiling of perfect isolation on this testbed is known: it is M-sep".** This holds for the first capability only, where b(1) ≡ M1 ≡ M-sep.
  - On the second capability, b(2) reads M-append's stage 2. That stage was trained with stage 1 present, so it is not ST1 of the second capability and can score above or below M-sep.
  - c and g(1) on E_first can also exceed M1 if stage 2 helps.
  - The registered M-ii panel mean (0.455 on E_A) is itself above M-sep (0.452).
  - §13 repeats the claim ("its ceiling here is M-sep") (R2).
- **Elsewhere the caveats are adequate.** §0, §13 and §14 state plainly that D0 is not causal for training and says nothing about learning, multi-teacher transfer or P11-S1 beyond "a note for its next review".
- **§14's description of ADR-0034** matches draft 9 §4.2: per-block top-8, a softmax with a no-read entry, per-block gates, and the sum g_j·r_j. ADR-0034 is unreviewed at draft 9, as the D0 draft says.
- PENDING LEAD REVIEW (scientific, not a defect):
  - Stage 2 never saw first-capability queries in training, so c on E_first tests a read that was never trained to be quiet on those inputs. This is the role of the no-read entry, and §14 already says so.
  - APPEND COST's share of the loss differs sharply by order: AB 0.37 / 0.51 / 0.39 against BA 0.13 / 0.16 / 0.22. The report should not average this away; §9 already forbids that.

## 4. Reproduction gate

- **Feasible.** `item_records.json` (SHA-256 54589c9f…af938, matching OUTCOME.md; both copies identical) holds `items`, `exact` and `sequences` for every key the gate needs:
  - `M1|o|r|s:E_*`
  - `M-append@append|o|r|s:E_*`
  - `M-append|o|r|s:E_*`
- **Tolerance.** 1e-6 together with identical sequences is tight enough. Audit 21's own code reached a worst case of 4.4e-16, and the frozen recompute ran at tolerance 0. D0 reuses the frozen chrF, so it should require exact equality (A1).
- **Missing:**
  - (a) `torch.equal` of the stage-1 keys, values and gate in both M-append snapshots against M1's;
  - (b) g2 == 0.0 exactly at append;
  - (c) the identity tolerances;
  - (d) the pinned environment: the locked venv, torch 2.8.0, deterministic algorithms, 6 threads, as in the registered evaluate stage;
  - (e) the failure procedure beyond "engineering stop". Keep the failed attempt, compute and open no counterfactual score in it, and allow a re-attempt only by a recorded lead decision. Say whether that re-attempt counts as D0's single run (R4).
- **Identity checks on real snapshots.** These compute counterfactual read tensors. The record should hold only pass/fail and the largest deviation.

## 5. Compute and safety

- **Arithmetic checks out.** 96 × 1,000 × 0.112 s = 10,752 s; × 1.33 = 14,300 s ≈ 4.0 h. Evaluate charged 41,296.95 s = 11.47 h by my sum of `charged_ledger.json`. Audit 21's overrun: 56,976 / ~43,000 = 1.33.
- **Caveats:**
  - The 0.112 s figure was timed on a D1 (dense) snapshot.
  - Audit 21 realised about 0.22 worker-s per sequence over all its work. At that rate the independent recomputation projects to about 6 h of its 8 h cap. That fits, with a thinner margin than the draft implies (A4).
- **Safety.** CPU only, no training, no download, new files only, and the Part T run directory read-only are all stated. The sealed-value issue does not arise, because the run and its recompute are complete and hashed. The independent recomputation by a different agent with its own read functions and chrF is specified (§11). Write paths are new directories. The Part T run directory appears in two places; name the absolute path that is read.

## 6. Quoted "already registered" numbers

Recomputed from `registry.json` (panel means over cells):

| Quantity | Draft | Registry | Status |
|---|---|---|---|
| M-sep A / B | 0.452 / 0.444 | 0.451980 / 0.443491 | **B misquoted: 0.443** (double-rounded from report.txt's 0.4435) |
| E-table A / B | 0.456 / 0.448 | 0.455934 / 0.447819 | correct |
| D-sep A / B | 0.533 / 0.496 | 0.532466 / 0.496417 | **A misquoted: 0.532** (double-rounded from 0.5325) |
| M-append A / B | 0.415 / 0.406 | 0.415060 / 0.405694 | correct |
| M-joint A / B | 0.465 / 0.452 | 0.465199 / 0.452189 | correct |

- **APPEND COST (G):** −0.0437, −0.0128, −0.0565, −0.0146, −0.0462, −0.0301 (0AB, 0BA, 1AB, 1BA, 2AB, 2BA). This matches the report's −0.044, −0.013, −0.057, −0.015, −0.046, −0.030. It is a zero-gate competition reading with untrained stage-2 keys, as stated: `annotations.append_cost` takes G(M-append@append) − G(M1), and g2 = 0 at the append snapshot.
- **Share of the total loss in G:** 0.370, 0.127, 0.505, 0.164, 0.390, 0.218. "Roughly 13% to 51%" is correct.
- **F:** 0.0719, 0.0629, 0.0680, 0.0555, 0.0721, 0.0864, so "0.056–0.086" is correct.
- **rho:** 0.770, 0.800, 0.782, 0.824, 0.766, 0.726, so "0.73–0.82" is correct.
- **M-ii rho:** 0.973–1.025 per audit 20, so "0.97–1.03" is correct.
- **NO ADVANTAGE OVER SEPARATE ADAPTERS holds True:** correct (report.txt line 104).
- **Evaluate 11.47 h:** correct.
- **The M-append panel means mix capabilities.** They pool first and second capability across the two orders, while the M-sep means are per capability. The text should say so (A9).

## 7. Open items

- **The human lead's endorsement and delegation are not in a committed record.** This **blocks approval**, under AGENTS.md (traceable record). It is cheap to fix: record both verbatim in the approval record before or with the approval (R5).
- **The base is the unmerged PR 28.** This is bookkeeping, provided D0 pins the base commit (`f6dff34d…`) and records the hashes of the frozen `studies/p10s2` modules it imports. Then a later change to PR 28 cannot silently change D0's code (R4).
- **New `tests/test_p10is2d0_*.py` files.** Bookkeeping. CLAUDE.md allows new files; existing tests stay untouched. The tests use synthetic stores only.

## Changes

REQUIRED

- **R1 (§1.4).** Replace "M-sep 0.452 / 0.444" with "M-sep 0.452 / 0.443". Replace "D-sep 0.533 / 0.496" with "D-sep 0.532 / 0.496".
- **R2 (§1.4 and §13).** Replace "So the ceiling of perfect isolation on this testbed is known: it is M-sep, which is at or below E-table and below D-sep." with: "So, for the first capability, the oracle bank switch reproduces M1 exactly, which is M-sep's first-capability score; M-sep is at or below E-table and below D-sep. For the second capability, and for reads c and g, M-sep is a reference, not a ceiling: stage 2 of M-append was trained with stage 1 present and can score above or below it."
  - In §13, replace "its ceiling here is M-sep" with "the registered isolated reference here is M-sep".
- **R3 (§4, after "Identities").** Add: "b(p) is computed by the unmodified `SparseStore.read` on a store holding stage p's tensors alone. Conditions a, d, e and g take the selection and σ(G) from one registered-code computation over the full store, and differ only in the per-slot weight vector. The gate requires:
  - stage-1 keys, values and gate of both M-append snapshots `torch.equal` to M1's;
  - g2 = 0.0 exactly at append;
  - b(1) `torch.equal` to M1's read on every query;
  - e(1) at append `torch.equal` to a at append;
  - a = e(1) + e(2) to a largest absolute difference ≤ 1e-6 · max(1, ‖a‖∞).

  The gate record holds only pass/fail and the largest deviation."
- **R4 (§8.2).** Append: "Environment: the locked venv of the Part T tree at commit f6dff34d201fb02f3ff77e5a33c17400a686f286 (torch 2.8.0), deterministic algorithms, 6 threads, CPU. Inputs: the run directory at <absolute path>, with the SHA-256 of the imported frozen modules recorded. If the gate fails:
  - the attempt is kept, and no counterfactual score is computed or opened;
  - a re-attempt needs a recorded lead decision;
  - a re-attempt is not a second run of D0, provided no reading beyond the gate record was produced."
- **R5 (front matter).** Before approval, record verbatim the human lead's endorsement of 2026-11-24 and the delegation of the approval decision to the lead in the approval record, and cite it here.
- **R6 (§5.2, last line).** Replace "The same on E_second with the stages exchanged, final store only." with "The same on E_second with the stages exchanged, final store only: n2 and m2, the b(2)-weight of displaced stage-2 rows, whether b(2)'s top row is kept, and ‖R_x − R_b(2)‖ / ‖R_b(2)‖ for x ∈ {a, c, d(2), e(2), g(2)}."

ADVISORY

- **A1.** In §8.2, require exact equality (0) for D0's own reproduction, because it uses the frozen chrF. Keep 1e-6 for the independent recomputation.
- **A2.** In §6, add: "The split between (i) and (ii) has one order only; their interaction is not estimated."
- **A3.** In §7, also print the summary word computed with the values-first order.
- **A4.** In §10, state that 0.112 s was timed on a D1 snapshot, and that at audit 21's realised rate (about 0.22 worker-s per sequence) the recomputation projects to about 6 h of its 8 h.
- **A5.** In §4's pass list, call e(1) on E_second "stage 2 switched off (trained keys)" rather than "the zero-gate control", so it is not confused with APPEND COST.
- **A6.** In §5.3, define the SD as the sample SD (n − 1). Define G as `quantities.py`'s (s − s_S0)/(s_teacher − s_S0), with the registry values.
- **A7.** Optional: after the gate, D0's code may compare its append-point, words-only stage-2 weight with the registered `row_shares` as a consistency check. Otherwise state that `row_shares` is not used.
- **A8.** In §6(iv), replace "it is zero unless a gate was wrongly passed" with "it is bounded by the gate tolerance".
- **A9.** In §1.4, note that the M-append panel means pool the first and second capability across orders.
