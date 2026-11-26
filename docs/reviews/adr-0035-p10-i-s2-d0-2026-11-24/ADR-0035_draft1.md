# ADR-0035 — P10-I-S2-D0 — interference diagnosis: which part of the read costs Part T's first capability

**Status: DRAFT — NOT APPROVED. Draft 1. Nothing under this ADR has been implemented or run. No model, snapshot or item score was loaded to write it.**

- Date: 2026-11-24 (Panama time). Drafted by the `arbor-lead` subagent (Claude Fable 5.2, `claude-fable-5-2`, from its session header). The drafter delegated nothing, read code, ADRs, committed records and snapshot file names only, and computed nothing.
- `SPEC: PENDING ASTRA REVIEW`. `Astra review: NOT_PERFORMED`. Claude review is not Astra review. No independent review of this draft has been made yet.
- Number. ADR-0001 to ADR-0033 are on `main`; ADR-0030 is also an untracked draft in the consolidation worktree; ADR-0034 is P11-S1 on `claude/p11-s1-spec`. No branch or worktree holds a higher number, and numbers are not reused (ADR-0018 was withdrawn and kept). So 0035.
- Study code P10IS2D0. Package `studies/p10is2d0/` (new files only). It needs Part T's tree, which is on `claude/p10-i-s2-impl` (draft PR 28, not merged); D0 is cut from that branch into its own branch and adds no commit to PR 28.
- Immutability. P10-I-S2 Part T's code, configuration, records, labels and run directory are not edited. Its outcome (MILESTONE NOT ESTABLISHED; LOOKUP SUFFICES; DENSE AHEAD; RETENTION-INCONCLUSIVE: NOT CHALLENGED) stands whatever D0 reads. ArborLM is unproven research; nothing below is a success claim.
- Origin. The human lead endorsed on 2026-11-24 an analysis that asks, before any further major training study, how much of Part T's retention loss comes from cross-stage top-k competition, softmax renormalisation and newly appended values, on the existing frozen checkpoints. **The drafter has this endorsement from the orchestrating brief only; it is not yet in a committed record and should be recorded verbatim before approval (AGENTS.md: no approval without a traceable record).**
- Every line D0 prints carries Part T's oracle line and the words `POST-HOC EXPLORATORY DIAGNOSTIC OF AN OBSERVED RUN; NOT A REGISTERED LABEL`.

## 0. What kind of study this is

A post-hoc, exploratory re-read of six observed cells. The outcome of the run is known, and so are rho (0.73 to 0.82), F (0.056 to 0.086) and the append cost (0.013 to 0.057 of G_first). D0 therefore:

- produces no registered label and changes none;
- trains nothing: every condition is a change of the read arithmetic over frozen snapshots;
- yields hypotheses for a later preregistered experiment, not findings about cause. One training run per cell exists, and the second stage was trained under the registered read; a store read in a way it was not trained for is not the store that training under that read would have produced.

## 1. What the registered records already answer (so that D0 does not rediscover it)

1. **The read.** `studies/p10s2/memory.py`, `SparseStore.read`: the keys of all stages are concatenated; one top-8 by cosine (ties to the lowest row index); one softmax at temperature 0.2 over those eight; each weight is multiplied by its stage's gate. A stage with gate 0 still takes slots and softmax mass.
2. **The query does not depend on the store or on training.** `MemoryArm.queries` takes fixed unit vectors from `CodeBook.get(task, j)`, a seeded hash of (replicate seed, task, word index). There is no query projection, shared or per stage. The student is frozen. In M-append, stage 1's keys, values and gate are frozen (`cells.py` lines 91 to 93; gate G4 tests gradient reach).
3. **The zero-gate control exists at the append point.** At the append point the new gate is exactly 0, so the registered annotation APPEND COST (change in G_first of −0.044, −0.013, −0.057, −0.015, −0.046, −0.030) is already a pure competition reading with untrained stage-2 keys: slots and mass, no values. Audit 20 puts it at roughly 13% to 51% of each cell's total loss. What is not known: its split between slots and mass, and the same reading with the trained stage-2 keys.
4. **Isolation by an oracle switch is registered.** M-sep is two M1 stores behind the oracle route, "retention BY CONSTRUCTION"; NO ADVANTAGE OVER SEPARATE ADAPTERS holds True. Mean panel scores (report.txt, A4 readings): M-sep 0.452 / 0.444 (A / B), M-append 0.415 / 0.406, M-joint 0.465 / 0.452, E-table 0.456 / 0.448, D-sep 0.533 / 0.496. **So the ceiling of perfect isolation on this testbed is known: it is M-sep, which is at or below E-table and below D-sep.** No result of D0 can move AGAINST-LOOKUP or AGAINST-DENSE, and acquisition is where lookup and dense are ahead.
5. M-ii (all rows trainable, 32 replayed rows per batch) has rho 0.97 to 1.03, descriptive. The frozen evaluate stage also computed `row_shares` at the append point (weight on new rows; reads touching one). Those values are in the run directory and were **not opened** for this draft.

## 2. Question

For M-append in each of the six cells: of the loss of first-capability score between M1 and the final store, how much is removed by undoing (i) the displacement of stage-1 rows from the eight slots, (ii) the softmax mass held by stage-2 rows, (iii) the stage-2 values that are added; and what does each undoing cost the second capability? Secondary: does a per-stage read, the form P11-S1 proposes, restore the first capability on these stores, or does a second stage read at full weight on first-capability inputs do harm of its own?

## 3. Inputs (read-only; SHA-256 checked against each manifest before loading)

Per replicate r ∈ {0, 1, 2} and order ∈ {AB, BA}: `rN__M1__ORDER.pt`, `rN__M-append__ORDER_at_append.pt`, `rN__M-append__ORDER.pt` in `experiments/P10IS2-T-registered-20261121/snapshots`; the frozen student; panels E_A and E_B (1,000 items each); the routers; `item_records.json` (SHA-256 in OUTCOME.md) for the gate. M-sep and D-sep have no snapshot of their own (they are assembled from M1 and D1); their scores, and those of E-table, D-append, D-seq, M-seq, M-ii and M-joint, are taken from the registered records and not recomputed. All six cells, both panels, no selection.

## 4. Conditions

Notation. S1, S2: the rows of stages 1 and 2. a_s: cosine of the query with key s. T8(X): the eight largest a_s in X, ties to the lowest row index. σ(X): softmax of a_s / 0.2 over X. g1, g2: the stored gates. G = T8(S1 ∪ S2). p is the protected stage and o the other one. Each read replaces `SparseStore.read`; positions, addresses, route, decoding and scoring are the registered ones.

| Code | Read | What it removes |
|---|---|---|
| a | Σ over G of σ(G)_s · g_stage(s) · V_s | Nothing: the registered read |
| b(p) | Σ over T8(Sp) of σ(T8(Sp))_s · g_p · V_s | Everything from stage o: an oracle bank switch |
| c | b(1) + b(2) | Competition; each stage is read at full weight. No task identity beyond the address |
| d(p) | K = G ∩ Sp; Σ over K of σ(K)_s · g_p · V_s; the zero vector if K is empty | Mass taken by stage o and its values; displacement stays |
| e(p) | Σ over G ∩ Sp of σ(G)_s · g_p · V_s (stage o's gate set to 0) | Stage o's values; displacement and mass loss stay |
| g(p) | b(p) + Σ over G ∩ So of σ(G)_s · g_o · V_s | Competition; stage o's values stay exactly as in the registered read |

Identities, tested as tensors: a = e(1) + e(2); at the append point e(1) = a; b(1) on any M-append store = M1's read.

Changes from the brief, with reasons. (1) **g(p) is added.** The per-stage read c gives stage 2 a softmax mass of 1, where the registered read gives it only the mass of its rows among the eight, so c is not "the registered read without competition". g(p) is, and makes the decomposition of section 6 clean; c is kept as the design check for P11-S1. (2) **b(1) is kept as a gate, not as a finding** (section 5.1). (3) No condition is dropped. (4) A fourth factor, the movement of stage-2 keys during training, is read by taking d(1) at both the append point and the final store.

Passes of greedy decoding per cell. On E_first: M1; the append store under a and d(1); the final store under a, b(1), c, d(1), e(1), g(1). On E_second: the final store under a, b(2), c, d(2), e(2), g(2), and e(1) (the zero-gate control's cost to the second capability). Sixteen passes per cell, 96 in all.

## 5. Readings

### 5.1 What condition b can and cannot show

On the first capability b(1) is M1 **by construction**: same frozen rows, same store-independent queries, same frozen student, hence the same read vector bit for bit and the same greedy output. It is also M-sep's first-capability score. It shows only that the snapshots and the D0 code are intact; it is not evidence that isolation "works". The informative readings are c, d, e and g on the first capability, and all conditions on the second. b(2) is **not** trivial: stage 2 was trained while stage-1 rows shared its top-8 and added their values, so b(2) against a says whether the second capability lives in its own rows or leans on (or is hindered by) stage 1. The pair (b(1) on E_first, b(2) on E_second) is what an oracle bank switch would give on these stores.

### 5.2 Read statistics (no decoding), per cell, at the append point and at the final store

Over every read of every item of E_first, word reads and marker reads separately; mean, median, 5th and 95th percentile:

- n1 = number of stage-1 rows among the eight; 8 − n1 is the count of displaced stage-1 rows (G ∩ S1 is always the top n1 of T8(S1), so these are one reading);
- m1 = softmax mass on stage-1 rows; the M1-weight that the displaced rows carried in M1's own softmax; whether M1's top row is kept;
- ‖R_x − R_M1‖ / ‖R_M1‖ for x ∈ {a, c, d(1), e(1), g(1)}; ‖stage-2 part of a‖ / ‖R_M1‖; g1 and g2.

The same on E_second with the stages exchanged, final store only.

### 5.3 Scores, per cell and panel

For each pass: mean chrF-norm s (maximum over references, as ADR-0025 section 8.1); G with the registered denominators read from the registry; the share of items whose greedy output differs from the reference pass (M1 on E_first; a on E_second). Every contrast is a paired per-item difference with its standard error (sd / √1000). No resampling and no seed: D0 is deterministic on CPU.

## 6. Decomposition (exact arithmetic)

For the first capability, final store, s on E_first:

- total T = s[b(1)] − s[a] (equal to the registered F once the gates pass);
- (i) slot displacement = s[b(1)] − s[d(1)];
- (ii) softmax renormalisation = s[d(1)] − s[e(1)];
- (iii) stage-2 values = s[e(1)] − s[a];
- (iv) residual = registered F − T, printed; it is zero unless a gate was wrongly passed.

(i) + (ii) + (iii) = T **exactly, because this is one path**, not because the effects are additive. Mass loss is defined only given displacement; the values term can be taken first instead: values alone = s[b(1)] − s[g(1)], then competition given values = s[g(1)] − s[a]. **Interaction = (iii) − (s[b(1)] − s[g(1)])**, printed for every cell. If it is large against the terms, the attribution depends on the order and is reported as such, with both orders. Each term is also given in G units and as a share of T.

At the append point: (i) = s[M1] − s[d(1) at append]; (ii) = s[d(1) at append] − s[a at append]; (iii) is zero by identity. The difference between the append-point and final values of (i) + (ii) is the effect of trained stage-2 keys on competition.

For the second capability the same arithmetic with p = 2 is printed as "effect of stage-1 rows on the second capability's read"; it is not a retention loss and may have either sign.

## 7. Wording fixed in advance (descriptive; none is a label)

- First capability: COMPETITION-LARGER if ((i) + (ii)) / T ≥ 2/3 in at least five of six cells; VALUES-LARGER if (iii) / T ≥ 2/3 in at least five of six; otherwise MIXED. Printed with the interaction, and ORDER-DEPENDENT is added if |interaction| ≥ T / 3 in any cell.
- Per-stage read: for c and for g(1), ADR-0025's RET arithmetic (F ≤ 0.03 and rho ≥ 0.90, unchanged) applied to the counterfactual read is printed per cell as COUNTERFACTUAL RET ARITHMETIC: HOLDS / DOES NOT HOLD, always beside the second capability's cost s[a] − s[c] on E_second and G_second under c. It is not RET.
- These cut-offs were written knowing the totals and the append costs of section 1. They exist to keep the summary sentence from being chosen after the numbers; the numbers are the result.

## 8. Order of work and gates

1. Tests on synthetic stores with known answers for every read of section 4 and every identity, before any real snapshot is opened.
2. **Reproduction gate.** With the unmodified read, D0's code reproduces the registered per-item scores of M1 (E_first), M-append at append (E_first) and M-append final (both panels) in all six cells, largest difference ≤ 1e-6, and identical greedy sequences. Then the tensor identities of section 4 on the real snapshots. A failure is an engineering stop: nothing else is read, and the cause returns to the lead.
3. Read statistics, then all scoring passes, in one run from one fixed launch script. The report is written by code from a fixed template after the last pass; no partial table is looked at.
4. Independent recomputation (section 11), then the report is given to the human lead.

## 9. Forking paths: what remains and how it is limited

Remaining risk. The conditions were chosen after the outcome, the append cost and the read code were seen. The cut-offs of section 7 were set knowing the totals. There are 96 passes and many contrasts on six cells that share three replicates; no significance is claimed and no contrast is singled out. A counterfactual read of a store trained under another read can mislead in either direction.

Limits. Conditions, readings, cells, panels, arithmetic, wording and the order of reporting are fixed here before anything is computed. All six cells and both capabilities are read; none is dropped or averaged away (per-cell values always, means only beside them). Every reading is reported. Anything computed after the report is read is marked `UNREGISTERED, AFTER D0 WAS READ` and kept apart. D0 is run once; a second run needs the human lead.

## 10. Compute bound

CPU only; no MPS; no training; no download; no quiet machine needed (no reading is a time). Basis: Part T's evaluate stage charged 11.47 h for the whole design; audit 21 measured 0.112 s per greedy decode on CPU and ran 1.33 times over its projection. D0 decodes 96 × 1,000 sequences: about 10,800 worker-seconds, about 14,300 with the same overrun, **about 4 worker-hours [E]**; the read statistics are minutes.

**Proposed cap: 8 worker-hours for D0's own run and 8 worker-hours for the independent recomputation, 16 in all**, each the sum of the wall time of the computing processes, at most three processes of six threads. At a cap the stage stops; completed records are kept and the result is reported as INCOMPLETE with no summary sentence. An extension is the human lead's decision. Every wait has a deadline.

## 11. Files, roles and audit

New files only; no existing file is edited.

- `docs/decisions/ADR-0035-p10-i-s2-d0-interference-diagnosis.md` (this text, once approved for filing).
- `studies/p10is2d0/` (`__init__.py`, `reads.py`, `run.py`, `report.py`); `tests/test_p10is2d0_*.py`. Frozen `studies.p10s2` modules are imported, never changed.
- `results/p10is2-d0-<date>/`: `records/` (read statistics, per-item scores, contrasts, gate record, input hashes, cost), `report.txt`, `audit/`.
- Run directory `experiments/P10IS2-D0-<date>/` (git-ignored). The Part T run directory is opened read-only.

Roles. Implementation by `arbor-implementer` from this ADR. Independent audit by `arbor-auditor` in a separate context, given the ADR, the code and the records and not the lead's reading: it reviews the code before the run, then recomputes every reading with its own read functions and its own chrF (importing at most `studies.p10s2.model`, as in audit 21) and compares. The model that actually ran each task is recorded from session metadata. The lead verifies both before relying on them.

## 12. Reported whatever the result

The gate record; every table of sections 5 and 6 for every cell and panel, including readings that show nothing, negative shares and conditions that make the first capability worse; the interaction; the second capability's cost beside every first-capability gain; the registered scores of M-sep, E-table, D-append, D-seq, D-sep, M-seq, M-ii and M-joint in the same table for scale; cost against the cap; every failed attempt and every disagreement with the audit.

## 13. What D0 does not show

- **Oracle task identity.** Every address carries the task by rule. Rows of the two capabilities are told apart by the oracle code, not by anything learned.
- **Isolation by construction is not learning.** b(1) equal to M1 is an identity. A per-stage read that preserves the first capability does so because nothing can reach its rows; that is no evidence of retention as a property of the memory, and no multi-teacher claim follows from it.
- **Nothing about acquisition.** E-table and the dense adapter are ahead on acquisition, the first one included. Isolating the read cannot change that; its ceiling here is M-sep.
- **Not causal for training.** D0 attributes a read-time difference on stores trained under the registered read. Whether a store trained under an isolated read acquires and retains is a training question.
- One small frozen English student, lexical translation of closed-vocabulary sentences, three replicates, U = 8,000, NOT CONVERGED AT U.

## 14. Relation to P11-S1 (ADR-0034, draft 9, not approved)

ADR-0034 section 4.2 already reads each block with its own top-8, its own softmax (with a no-read entry) and its own gate, and sums g_j · r_j. Appending a block at gate 0 leaves the logits bit-identical (gate G-ATT). **P11-S1's read therefore has no cross-stage slot competition and no shared softmax: mechanisms (i) and (ii) cannot occur there.** What remains is (iii), which ADR-0034 states itself: once trained, block 2 adds its read on every input.

So D0's main value is to explain Part T and to check that design choice on existing data. Condition c is P11-S1's read without the no-read entry and with oracle codes in place of learned query heads. If c and g(1) hold the first capability, the choice is consistent with Part T's stores. If c harms it while g(1) does not, a second stage read at full weight on first-capability inputs is the cost, which bears on the no-read entry and on the risks listed in ADR-0034; that would be written as a note for its next review. D0 changes nothing in ADR-0034 by itself, and transfers weakly: different student, learned addresses, natural text.

## 15. Follow-up

The endorsed analysis also asks for a minimal bank-isolation experiment compared with E-table, LoRA and separate modules. That is a separate proposal, written after D0 is read, with its own approval. The drafter notes now that on Part T's testbed its ceiling (M-sep) and its comparators (E-table, D-sep, D-append) are registered, and that P11-S1 already contains per-block reads with LoRA, dense and look-up comparators; the proposal may reduce to a note on ADR-0034.

## 16. Decision requested from the human lead

**Approve P10-I-S2-D0 as specified in this ADR (implementation, one run and one independent recomputation, within the 16 worker-hour cap): yes / no.** Nothing else is requested. No new training, merge, publication or change to any registered outcome is covered by a yes.
